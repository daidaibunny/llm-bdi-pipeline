"""
Append query-specific temporal goals to a domain-level atomic ASL library.

The input side is expected to provide a validated LTLf JSON object and a DFA
payload. This module only checks the DFA interface required by the ASL layer and
turns progress transitions into calls to existing atomic predicate modules.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary
from utils.symbol_normalizer import SymbolNormalizer
from utils.pddl_parser import PDDLDomain
from utils.pddl_parser import PDDLParser

from .lifted_ltlf_goal_schema import LTLfAtomSpec
from .dfa_controller import inspect_progress_requests_from_dfa_state
from .dfa_controller import progress_transitions_from_dfa_state
from .lifted_ltlf_goal_schema import LiftedLTLfGoalCase
from .atomic_module_synthesis import _ParsedAction
from .atomic_module_synthesis import _numeric_condition_contexts
from .pddl_support import assert_compilable_pddl_files
from .certified_effects import threat_safe_positive_literal_order
from .certified_effects import preservation_safe_plan_selection
from .certified_effects import query_local_preservation_alias_plans
from .certified_effects import negative_guard_establishment_alias_plans
from .transition_repair_tree import TransitionRepairLiteral
from .transition_repair_tree import compile_flat_transition_repair_controller
from .transition_repair_tree import compile_transition_repair_tree


_DFA_GUARD_TRANSITION_WRAPPER_MODE = "runtime_monitored_dfa_product"
TEMPORAL_MONITOR_CHECKPOINT_ACTION = "temporal_monitor_checkpoint"


class TemporalCompilerVariant(str, Enum):
	"""Registered query-compiler variants for paired temporal experiments."""

	DFA_AWARE_UNPROTECTED = "dfa_aware_unprotected"
	CERTIFIED_FLAT = "certified_flat"
	CERTIFIED_BALANCED = "certified_balanced"
	COMPLETION_BOUNDARY_MONITOR = "completion_boundary_monitor"


class TemporalMonitorObservationBoundary(str, Enum):
	"""World-state boundary at which the runtime DFA consumes one valuation."""

	PRIMITIVE_STEP = "primitive_step"
	ATOMIC_MODULE_COMPLETION = "atomic_module_completion"


@dataclass(frozen=True)
class _TemporalCompilerSettings:
	variant: TemporalCompilerVariant
	certified_serialization: bool
	controller_structure: str
	controller_strategy: str
	monitor_observation_boundary: TemporalMonitorObservationBoundary
	enforce_primitive_prefix_invariants: bool


def _temporal_compiler_settings(
	variant: TemporalCompilerVariant | str,
) -> _TemporalCompilerSettings:
	try:
		resolved = (
			variant
			if isinstance(variant, TemporalCompilerVariant)
			else TemporalCompilerVariant(variant)
		)
	except ValueError as error:
		raise ValueError(f"temporal_compiler_variant_unknown: {variant!r}") from error
	if resolved == TemporalCompilerVariant.DFA_AWARE_UNPROTECTED:
		return _TemporalCompilerSettings(
			variant=resolved,
			certified_serialization=False,
			controller_structure="flat",
			controller_strategy="monitored_unprotected_flat_replay",
			monitor_observation_boundary=(
				TemporalMonitorObservationBoundary.PRIMITIVE_STEP
			),
			enforce_primitive_prefix_invariants=False,
		)
	if resolved == TemporalCompilerVariant.CERTIFIED_FLAT:
		return _TemporalCompilerSettings(
			variant=resolved,
			certified_serialization=True,
			controller_structure="flat",
			controller_strategy="monitored_certified_flat_replay",
			monitor_observation_boundary=(
				TemporalMonitorObservationBoundary.PRIMITIVE_STEP
			),
			enforce_primitive_prefix_invariants=True,
		)
	if resolved == TemporalCompilerVariant.CERTIFIED_BALANCED:
		return _TemporalCompilerSettings(
			variant=resolved,
			certified_serialization=True,
			controller_structure="balanced",
			controller_strategy="monitored_balanced_repair_tree",
			monitor_observation_boundary=(
				TemporalMonitorObservationBoundary.PRIMITIVE_STEP
			),
			enforce_primitive_prefix_invariants=True,
		)
	return _TemporalCompilerSettings(
		variant=resolved,
		certified_serialization=True,
		controller_structure="balanced",
		controller_strategy="completion_monitored_balanced_repair_tree",
		monitor_observation_boundary=(
			TemporalMonitorObservationBoundary.ATOMIC_MODULE_COMPLETION
		),
		enforce_primitive_prefix_invariants=False,
	)


def _canonical_payload_fingerprint(payload: object) -> str:
	encoded = json.dumps(
		payload,
		sort_keys=True,
		separators=(",", ":"),
		default=str,
	).encode("utf-8")
	return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class GuardTransitionDFADiagnostic:
	"""Validation result for the conjunctive DFA guard interface contract."""

	valid: bool
	errors: tuple[dict[str, object], ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"valid": self.valid,
			"errors": [dict(error) for error in self.errors],
		}


@dataclass(frozen=True)
class DFALiteral:
	"""One parsed DFA transition literal."""

	predicate: str
	arguments: tuple[str, ...]
	polarity: str = "positive"

	@property
	def atom(self) -> str:
		return _call(self.predicate, self.arguments)


@dataclass(frozen=True)
class _TemporalPlanEffects:
	"""Net primitive effects of one action-only atomic branch."""

	adds: frozenset[tuple[str, tuple[str, ...]]]
	deletes: frozenset[tuple[str, tuple[str, ...]]]
	numeric_deltas: tuple[tuple[str, tuple[str, ...], int], ...]


@dataclass(frozen=True)
class _AchievementHelperCall:
	"""One query-local helper call with its certificate-preserving arguments."""

	symbol: str
	arguments: tuple[str, ...]


def validate_guard_transition_dfa(
	dfa_payload: Mapping[str, Any],
	*,
	allow_true_accepting_self_loops: bool = True,
	declared_arities: Mapping[str, int] | None = None,
) -> GuardTransitionDFADiagnostic:
	"""Check that every relevant DFA transition guard uses conjunction and negation."""

	accepting_states = {
		str(state).strip()
		for state in tuple(dfa_payload.get("accepting_states") or ())
		if str(state).strip()
	}
	errors: list[dict[str, object]] = []
	guarded_transitions = dfa_payload.get("guarded_transitions")
	if not isinstance(guarded_transitions, Sequence) or isinstance(
		guarded_transitions,
		(str, bytes),
	):
		return GuardTransitionDFADiagnostic(
			valid=False,
			errors=(
				{
					"error_type": "dfa_parser_error",
					"message": "DFA payload must contain a guarded_transitions list.",
				},
			),
		)
	for index, transition in enumerate(tuple(guarded_transitions or ()), start=1):
		if not isinstance(transition, Mapping):
			errors.append(
				{
					"transition_index": index,
					"error_type": "dfa_parser_error",
					"message": "DFA transition record must be a JSON object.",
				},
			)
			continue
		source_state = str(transition.get("source_state") or "").strip()
		target_state = str(transition.get("target_state") or "").strip()
		raw_label = str(transition.get("raw_label") or "true").strip() or "true"
		if (
			allow_true_accepting_self_loops
			and raw_label.lower() == "true"
			and source_state == target_state
			and source_state in accepting_states
		):
			continue
		try:
			literals = _parse_guard_literals(raw_label)
		except ValueError as error:
			errors.append(
				{
					"transition_index": index,
					"source_state": source_state,
					"target_state": target_state,
					"raw_label": raw_label,
					"error_type": "unsupported_guard_expression",
					"message": str(error),
				},
			)
			continue
		for literal in literals:
			if declared_arities is None:
				continue
			if literal.predicate not in declared_arities:
				errors.append(
					{
						"transition_index": index,
						"source_state": source_state,
						"target_state": target_state,
						"raw_label": raw_label,
						"predicate": literal.predicate,
						"error_type": "unsupported_predicate",
						"message": (
							"DFA transition references a predicate or numeric "
							"resource function that is not declared in the PDDL "
							"domain."
						),
					},
				)
				continue
			expected_arity = int(declared_arities[literal.predicate])
			actual_arity = len(literal.arguments)
			if expected_arity != actual_arity:
				errors.append(
					{
						"transition_index": index,
						"source_state": source_state,
						"target_state": target_state,
						"raw_label": raw_label,
						"predicate": literal.predicate,
						"expected_arity": expected_arity,
						"actual_arity": actual_arity,
						"error_type": "wrong_arity",
						"message": (
							"DFA transition predicate or numeric resource function "
							"arity does not match the PDDL domain declaration."
						),
					},
				)
	return GuardTransitionDFADiagnostic(valid=not errors, errors=tuple(errors))


def append_temporal_goal_to_library(
	*,
	plan_library: PlanLibrary,
	goal_name: str,
	dfa_payload: Mapping[str, Any],
	domain_file: str | Path,
	allow_true_accepting_self_loops: bool = True,
	compiler_variant: TemporalCompilerVariant | str = (
		TemporalCompilerVariant.CERTIFIED_BALANCED
	),
) -> PlanLibrary:
	"""Append one query-specific temporal goal wrapper to an atomic ASL library."""

	settings = _temporal_compiler_settings(compiler_variant)
	if _has_existing_goal_trigger(plan_library, goal_name):
		raise ValueError(
			"duplicate_temporal_goal: Plan library already contains an "
			f"achievement-goal entry for {goal_name!r}."
		)
	pddl_support = assert_compilable_pddl_files(domain_file=domain_file)
	domain = PDDLParser.parse_domain(domain_file)
	declared_arities = _declared_temporal_goal_arities(domain)
	diagnostic = validate_guard_transition_dfa(
		dfa_payload,
		allow_true_accepting_self_loops=allow_true_accepting_self_loops,
		declared_arities=declared_arities,
	)
	if not diagnostic.valid:
		first_error = diagnostic.errors[0]
		raise ValueError(
			"DFA payload does not satisfy the conjunctive guard-transition contract: "
			f"{first_error['error_type']}: {first_error['message']}"
		)
	append_record: dict[str, Any] = {
		"goal_name": goal_name,
		"pddl_support": pddl_support.to_dict(),
		"dfa_initial_state": dfa_payload.get("initial_state"),
		"dfa_accepting_states": list(dfa_payload.get("accepting_states") or ()),
		"progress_request_diagnostics": _progress_request_diagnostics(
			dfa_payload=dfa_payload,
			domain_key=domain.name,
			domain_file=domain_file,
			declared_arities=declared_arities,
		),
	}
	plans = list(plan_library.plans)
	transition_path = _monitored_progress_objectives(
		dfa_payload=dfa_payload,
		declared_arities=declared_arities,
	)
	progress_plans = _guard_transition_wrapper_plans(
		goal_name=goal_name,
		transition_path=transition_path,
		accepting_states=tuple(dfa_payload.get("accepting_states") or ()),
		domain=domain,
		plan_library=plan_library,
		settings=settings,
	)
	entry_proposition = _query_entry_proposition(goal_name)
	append_record["wrapper_mode"] = _DFA_GUARD_TRANSITION_WRAPPER_MODE
	append_record["temporal_compiler_variant"] = settings.variant.value
	append_record["transition_controller_strategy"] = settings.controller_strategy
	append_record["controller_structure"] = settings.controller_structure
	append_record["certified_serialization"] = settings.certified_serialization
	append_record["monitor_observation_boundary"] = (
		settings.monitor_observation_boundary.value
	)
	append_record["primitive_prefix_source_invariants_enforced"] = (
		settings.enforce_primitive_prefix_invariants
	)
	append_record["experiment_contract"] = {
		"compiler_variant": settings.variant.value,
		"atomic_library_fingerprint": _canonical_payload_fingerprint(
			plan_library.to_dict(),
		),
		"dfa_fingerprint": _canonical_payload_fingerprint(dfa_payload),
		"paired_variant_contract": (
			"same atomic library, DFA, query binding, and Jason runtime"
		),
	}
	append_record["runtime_monitor_required"] = True
	append_record["runtime_monitor_accepting_belief"] = (
		dfa_monitor_accepting_belief(goal_name)
	)
	append_record["query_entry_proposition"] = entry_proposition
	append_record["progress_plan_count"] = len(progress_plans)
	append_record["progress_transition_count"] = len(transition_path)
	append_record["negative_guard_count"] = sum(
		1
		for literals, _transition in transition_path
		for literal in literals
		if literal.polarity == "negative"
	)
	append_record["negative_guard_policy"] = (
		"completion_context_with_conditional_may_add_preservation"
	)
	append_record["negative_atomic_module_supported"] = False
	append_record["negative_guard_establishment_supported"] = True
	append_record["accepting_plan_count"] = 1
	append_record["progress_state_coverage"] = _progress_transition_state_coverage(
		transition_path=transition_path,
	)
	plans.extend(progress_plans)
	initial_beliefs = _initial_beliefs_with_query_entry(
		plan_library=plan_library,
		entry_proposition=entry_proposition,
	)
	return PlanLibrary(
		domain_name=plan_library.domain_name,
		plans=tuple(plans),
		initial_beliefs=initial_beliefs,
		metadata={
			**dict(plan_library.metadata or {}),
			"temporal_goal_append": append_record,
			"temporal_goal_append_history": _append_history(
				plan_library.metadata,
				append_record,
			),
		},
	)


def append_lifted_temporal_goal_case_to_library(
	*,
	plan_library: PlanLibrary,
	goal_case: LiftedLTLfGoalCase,
	domain_file: str | Path,
	dfa_builder: Any,
	compiler_variant: TemporalCompilerVariant | str = (
		TemporalCompilerVariant.CERTIFIED_BALANCED
	),
) -> tuple[PlanLibrary, Mapping[str, Any]]:
	"""Compile one lifted LTLf goal case to DFA and append it to a library."""

	dfa_payload = _rewrite_dfa_payload_labels_from_lifted_atoms(
		dfa_builder.build(goal_case.ltlf_formula),
		goal_case=goal_case,
	)
	updated = append_temporal_goal_to_library(
		plan_library=plan_library,
		goal_name=goal_case.goal_name,
		dfa_payload=dfa_payload,
		domain_file=domain_file,
		compiler_variant=compiler_variant,
	)
	return updated, dfa_payload


def _has_existing_goal_trigger(plan_library: PlanLibrary, goal_name: str) -> bool:
	goal = str(goal_name or "").strip()
	return any(
		plan.trigger.event_type == "achievement_goal"
		and plan.trigger.symbol == goal
		for plan in plan_library.plans
	)


def _append_history(
	metadata: Mapping[str, Any],
	append_record: Mapping[str, Any],
) -> list[dict[str, Any]]:
	history_payload = metadata.get("temporal_goal_append_history")
	if isinstance(history_payload, Sequence) and not isinstance(
		history_payload,
		(str, bytes),
	):
		history = [
			dict(item)
			for item in history_payload
			if isinstance(item, Mapping)
		]
	else:
		legacy_record = metadata.get("temporal_goal_append")
		history = [dict(legacy_record)] if isinstance(legacy_record, Mapping) else []
	history.append(dict(append_record))
	return history


def _progress_request_diagnostics(
	*,
	dfa_payload: Mapping[str, Any],
	domain_key: str,
	domain_file: str | Path,
	declared_arities: Mapping[str, int],
) -> list[dict[str, object]]:
	diagnostics: list[dict[str, object]] = []
	for source_state in _source_states(dfa_payload):
		diagnostics.extend(
			inspect_progress_requests_from_dfa_state(
				dfa_payload=dfa_payload,
				current_dfa_state=source_state,
				domain_key=domain_key,
				domain_file=domain_file,
				declared_predicates=declared_arities,
			),
		)
	return diagnostics


def _source_states(dfa_payload: Mapping[str, Any]) -> tuple[str, ...]:
	return tuple(
		dict.fromkeys(
			str(transition.get("source_state") or "").strip()
			for transition in tuple(dfa_payload.get("guarded_transitions") or ())
			if isinstance(transition, Mapping)
			and str(transition.get("source_state") or "").strip()
		),
	)


def _rewrite_dfa_payload_labels_from_lifted_atoms(
	dfa_payload: Mapping[str, Any],
	*,
	goal_case: LiftedLTLfGoalCase,
) -> dict[str, Any]:
	"""Restore LTLf propositional labels into lifted PDDL literal labels."""

	invocation_bindings = {
		str(parameter).strip(): str(value).strip()
		for parameter, value in dict(goal_case.bindings or {}).items()
		if str(parameter).strip() and str(value).strip()
	}
	symbol_map = _lifted_atom_symbol_map(
		goal_case.atoms,
		invocation_bindings=invocation_bindings,
	)
	if not symbol_map:
		return dict(dfa_payload)
	rewritten_transitions: list[dict[str, Any]] = []
	rewrite_count = 0
	for transition in tuple(dfa_payload.get("guarded_transitions") or ()):
		if not isinstance(transition, Mapping):
			rewritten_transitions.append(dict(transition) if isinstance(transition, dict) else transition)
			continue
		raw_label = str(transition.get("raw_label") or "true").strip() or "true"
		rewritten_label = _rewrite_guard_label(raw_label, symbol_map=symbol_map)
		rewrite_count += int(rewritten_label != raw_label)
		rewritten_transitions.append(
			{
				**dict(transition),
				"raw_label": rewritten_label,
				"original_raw_label": raw_label if rewritten_label != raw_label else transition.get("original_raw_label"),
			},
		)
	payload = dict(dfa_payload)
	payload["guarded_transitions"] = rewritten_transitions
	payload["lifted_atom_binding"] = {
		"atom_count": len(goal_case.atoms),
		"rewritten_transition_count": rewrite_count,
		"invocation_bindings": invocation_bindings,
		"symbols": sorted(
			{
				key
				for key in symbol_map
				if key and not key.startswith("not ")
			},
		),
	}
	return payload


def _lifted_atom_symbol_map(
	atoms: Sequence[LTLfAtomSpec],
	*,
	invocation_bindings: Mapping[str, str],
) -> dict[str, str]:
	normalizer = SymbolNormalizer()
	symbol_map: dict[str, str] = {}
	for atom in tuple(atoms or ()):
		predicate = str(atom.predicate or "").strip()
		lifted_arguments = tuple(
			str(argument).strip()
			for argument in tuple(atom.args or ())
			if str(argument).strip()
		)
		arguments = tuple(
			invocation_bindings.get(argument, argument)
			for argument in lifted_arguments
		)
		if not predicate:
			continue
		pddl_atom = _call(predicate, arguments)
		candidates = {
			str(atom.symbol or "").strip(),
			_symbol_for(predicate, lifted_arguments),
			pddl_atom,
			pddl_atom.replace(" ", ""),
		}
		if arguments:
			candidates.add(normalizer.create_propositional_symbol(predicate, arguments))
		for candidate in tuple(candidates):
			_register_symbol_mapping(symbol_map, candidate, pddl_atom)
	return symbol_map


def _register_symbol_mapping(symbol_map: dict[str, str], symbol: str, pddl_atom: str) -> None:
	key = str(symbol or "").strip()
	if not key:
		return
	symbol_map[key] = pddl_atom
	symbol_map[key.lower()] = pddl_atom


def _rewrite_guard_label(raw_label: str, *, symbol_map: Mapping[str, str]) -> str:
	text = str(raw_label or "").strip() or "true"
	if text.lower() in {"true", "false"}:
		return text
	parts = _split_top_level_conjunction(text)
	if len(parts) <= 1:
		return _rewrite_literal_text(text, symbol_map=symbol_map)
	return " & ".join(
		_rewrite_literal_text(part, symbol_map=symbol_map)
		for part in parts
	)


def _rewrite_literal_text(raw_literal: str, *, symbol_map: Mapping[str, str]) -> str:
	text = _strip_balanced_parentheses(str(raw_literal or "").strip())
	if not text:
		return text
	polarity = ""
	for prefix in ("not ", "!", "~"):
		if text.lower().startswith(prefix):
			polarity = "not "
			text = text[len(prefix) :].strip()
			break
	atom_text = _strip_balanced_parentheses(text)
	mapped_atom = symbol_map.get(atom_text) or symbol_map.get(atom_text.lower())
	if mapped_atom is None:
		return f"{polarity}{atom_text}" if polarity else atom_text
	return f"{polarity}{mapped_atom}" if polarity else mapped_atom


def _split_top_level_conjunction(label: str) -> tuple[str, ...]:
	parts: list[str] = []
	start = 0
	depth = 0
	for index, character in enumerate(str(label or "")):
		if character == "(":
			depth += 1
		elif character == ")":
			depth = max(0, depth - 1)
		elif character == "&" and depth == 0:
			parts.append(label[start:index].strip())
			start = index + 1
	parts.append(str(label or "")[start:].strip())
	return tuple(part for part in parts if part)


def _symbol_for(predicate: str, args: Sequence[str]) -> str:
	items = [predicate, *tuple(args or ())]
	return "_".join(str(item).strip() for item in items if str(item).strip())


def _monitored_progress_objectives(
	*,
	dfa_payload: Mapping[str, Any],
	declared_arities: Mapping[str, int],
) -> tuple[tuple[tuple[DFALiteral, ...], Mapping[str, str]], ...]:
	"""Group same-target progress edges into monitor-confirmed repair objectives."""

	grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
	for transition in _all_progress_transitions(dfa_payload):
		key = (transition["source_state"], transition["target_state"])
		grouped.setdefault(key, []).append(transition)
	objectives: list[tuple[tuple[DFALiteral, ...], Mapping[str, str]]] = []
	for (source_state, target_state), transitions in grouped.items():
		parsed = tuple(
			_parse_guard_literals(transition["raw_label"])
			for transition in transitions
		)
		for literals in parsed:
			for literal in literals:
				_validate_declared_literal(literal, declared_arities=declared_arities)
		common = tuple(
			literal
			for literal in parsed[0]
			if all(literal in literals for literals in parsed[1:])
		)
		source_invariants = _source_state_invariant_literals(
			dfa_payload,
			source_state=source_state,
			progress_literals=common,
		)
		objectives.append(
			(
				common,
				{
					"source_state": source_state,
					"target_state": target_state,
					"raw_label": " & ".join(
						(
							literal.atom
							if literal.polarity == "positive"
							else f"not {literal.atom}"
						)
						for literal in common
					) or "true",
					"source_guard_labels": tuple(
						transition["raw_label"] for transition in transitions
					),
					"source_invariant_literals": source_invariants,
				},
			)
		)
	return tuple(objectives)


def _source_state_invariant_literals(
	dfa_payload: Mapping[str, Any],
	*,
	source_state: str,
	progress_literals: Sequence[DFALiteral],
) -> tuple[DFALiteral, ...]:
	"""Return literals common to all source-state waiting self-loop cubes."""

	self_loop_cubes = tuple(
		_parse_guard_literals(str(transition.get("raw_label") or ""))
		for transition in tuple(dfa_payload.get("guarded_transitions") or ())
		if str(transition.get("source_state") or "") == source_state
		and str(transition.get("target_state") or "") == source_state
		and str(transition.get("raw_label") or "").strip().lower() != "true"
	)
	if not self_loop_cubes:
		return ()
	progress_atoms = {literal.atom for literal in progress_literals}
	return tuple(
		literal
		for literal in self_loop_cubes[0]
		if literal.atom not in progress_atoms
		and all(literal in cube for cube in self_loop_cubes[1:])
	)


def dfa_monitor_state_belief(goal_name: str, state: object) -> str:
	"""Return the reserved query-local percept for one runtime DFA state."""

	goal = _safe_query_identifier(goal_name)
	state_token = _safe_query_identifier(str(state or "state"))
	return f"{goal}_monitor_state_{state_token}"


def dfa_monitor_accepting_belief(goal_name: str) -> str:
	"""Return the reserved query-local DFA acceptance percept."""

	return f"{_safe_query_identifier(goal_name)}_monitor_accepting"


def _safe_query_identifier(value: str) -> str:
	text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "")).strip("_").lower()
	if not text:
		return "query"
	return f"q_{text}" if text[0].isdigit() else text


def _guard_transition_wrapper_plans(
	*,
	goal_name: str,
	transition_path: Sequence[
		tuple[tuple[DFALiteral, ...], Mapping[str, str]]
	],
	accepting_states: Sequence[object],
	domain: PDDLDomain,
	plan_library: PlanLibrary,
	settings: _TemporalCompilerSettings,
) -> tuple[AgentSpeakPlan, ...]:
	"""Compile every DFA progress edge into one query-local transition helper."""

	entry_proposition = _query_entry_proposition(goal_name)
	transition_names = tuple(
		f"{goal_name}_trans_{index}"
		for index in range(1, len(tuple(transition_path)) + 1)
	)
	plans: list[AgentSpeakPlan] = [
		AgentSpeakPlan(
			plan_name=f"{goal_name}_monitor_accepting",
			trigger=AgentSpeakTrigger("achievement_goal", goal_name, ()),
			context=(entry_proposition, dfa_monitor_accepting_belief(goal_name)),
			body=(),
			binding_certificate=(
				{
					"artifact_family": "temporal_goal_dfa_append",
					"wrapper_mode": _DFA_GUARD_TRANSITION_WRAPPER_MODE,
					"wrapper_role": "runtime_monitor_accepting_entry",
					"query_entry_proposition": entry_proposition,
					"accepting_states": [str(state) for state in accepting_states],
				},
			),
		),
	]
	for (literals, transition), transition_name in zip(
		tuple(transition_path),
		transition_names,
	):
		source_state = str(transition.get("source_state") or "")
		plans.append(
			AgentSpeakPlan(
				plan_name=f"{transition_name}_monitor_dispatch",
				trigger=AgentSpeakTrigger("achievement_goal", goal_name, ()),
				context=(
					entry_proposition,
					dfa_monitor_state_belief(goal_name, source_state),
				),
				body=(
					AgentSpeakBodyStep("subgoal", transition_name, ()),
					AgentSpeakBodyStep("subgoal", goal_name, ()),
				),
				binding_certificate=(
					{
						"artifact_family": "temporal_goal_dfa_append",
						"wrapper_mode": _DFA_GUARD_TRANSITION_WRAPPER_MODE,
						"wrapper_role": "runtime_monitor_state_dispatch",
						"query_entry_proposition": entry_proposition,
						"source_state": source_state,
						"target_state": str(transition.get("target_state") or ""),
						"objective_literals": [literal.atom for literal in literals],
					},
				),
			),
		)
	for transition_index, ((literals, transition), transition_name) in enumerate(
		zip(tuple(transition_path), transition_names),
		start=1,
	):
		positive_literals = tuple(
			literal for literal in literals if literal.polarity == "positive"
		)
		negative_literals = tuple(
			literal for literal in literals if literal.polarity == "negative"
		)
		if not settings.certified_serialization:
			positive_literals = tuple(sorted(positive_literals, key=_canonical_literal_key))
			negative_literals = tuple(sorted(negative_literals, key=_canonical_literal_key))
		source_invariants = tuple(transition.get("source_invariant_literals") or ())
		certified_source_invariants = (
			source_invariants if settings.enforce_primitive_prefix_invariants else ()
		)
		(
			positive_literals,
			serialization_certificate,
			preservation_alias_plans,
			preservation_helper_by_predicate,
			negative_establishment_alias_plans,
			negative_establishment_helper_by_index,
		) = (
			(
				_certified_positive_literal_serialization(
					positive_literals,
					negative_literals=negative_literals,
					source_invariants=certified_source_invariants,
					plan_library=plan_library,
					domain=domain,
					helper_prefix=transition_name,
				)
				if settings.certified_serialization
				else _canonical_unprotected_literal_serialization(
				positive_literals,
				negative_literals=negative_literals,
				source_invariants=certified_source_invariants,
				plan_library=plan_library,
				domain=domain,
				helper_prefix=transition_name,
			)
			)
		)
		plans.extend(preservation_alias_plans)
		plans.extend(negative_establishment_alias_plans)
		type_contexts = _guard_variable_type_contexts(literals, domain=domain)
		source_state_belief = dfa_monitor_state_belief(
			goal_name,
			str(transition.get("source_state") or ""),
		)
		completion_context = (
			entry_proposition,
			*type_contexts,
			f"not {source_state_belief}",
		)
		certificate = {
			"artifact_family": "temporal_goal_dfa_append",
			"wrapper_mode": _DFA_GUARD_TRANSITION_WRAPPER_MODE,
			"query_entry_proposition": entry_proposition,
			"transition_index": transition_index,
			"source_state": str(transition.get("source_state") or ""),
			"target_state": str(transition.get("target_state") or ""),
			"raw_label": str(transition.get("raw_label") or ""),
			"completion_condition": "source_state_exit",
			"completion_source_state_belief": source_state_belief,
			"serialization_certificate": serialization_certificate,
			"monitor_observation_boundary": (
				settings.monitor_observation_boundary.value
			),
			"source_invariant_literals": [
				literal.atom if isinstance(literal, DFALiteral) else str(literal)
				for literal in source_invariants
			],
			"primitive_prefix_source_invariants_enforced": (
				settings.enforce_primitive_prefix_invariants
			),
		}
		negative_repair_literals = tuple(
			TransitionRepairLiteral(
				atom=literal.atom,
				achievement_symbol=(
					negative_establishment_helper_by_index.get(index, (None, ()))[0]
				),
				achievement_arguments=(
					negative_establishment_helper_by_index.get(index, (None, ()))[1]
				),
				polarity="negative",
			)
			for index, literal in enumerate(negative_literals)
		)
		if not positive_literals and not any(
			literal.achievement_symbol for literal in negative_repair_literals
		):
			plans.append(
				AgentSpeakPlan(
					plan_name=f"{transition_name}_done",
					trigger=AgentSpeakTrigger("achievement_goal", transition_name, ()),
					context=completion_context,
					body=(),
					binding_certificate=(
						{**certificate, "wrapper_role": "transition_done"},
					),
				),
			)
			continue
		shared_context = (entry_proposition, *type_contexts)
		observation_only_literals = set(
			serialization_certificate.get("observation_only_literals", ()),
		)
		positive_repair_literals: list[TransitionRepairLiteral] = []
		for literal in positive_literals:
			helper = (
				preservation_helper_by_predicate.get(literal.atom)
				or preservation_helper_by_predicate.get(literal.predicate)
			)
			if literal.atom in observation_only_literals:
				achievement_symbol = None
				achievement_arguments: tuple[str, ...] = ()
			elif isinstance(helper, _AchievementHelperCall):
				achievement_symbol = helper.symbol
				achievement_arguments = helper.arguments
			elif helper:
				achievement_symbol = helper
				achievement_arguments = literal.arguments
			elif _literal_has_achievement_branch(
				literal,
				plan_library=plan_library,
			):
				achievement_symbol = literal.predicate
				achievement_arguments = literal.arguments
			else:
				achievement_symbol = None
				achievement_arguments = ()
			positive_repair_literals.append(
				TransitionRepairLiteral(
					atom=literal.atom,
					achievement_symbol=achievement_symbol,
					achievement_arguments=achievement_arguments,
				),
			)
		repair_literals = (
			(*tuple(positive_repair_literals), *negative_repair_literals)
			if serialization_certificate.get("repair_positive_before_negative") is True
			else (*negative_repair_literals, *tuple(positive_repair_literals))
		)
		monitor_checkpoint_action = (
			TEMPORAL_MONITOR_CHECKPOINT_ACTION
			if settings.monitor_observation_boundary
			== TemporalMonitorObservationBoundary.ATOMIC_MODULE_COMPLETION
			else None
		)
		if settings.controller_structure == "flat":
			controller_compilation = compile_flat_transition_repair_controller(
				transition_symbol=transition_name,
				shared_context=shared_context,
				repair_literals=repair_literals,
				completion_context=completion_context,
				certificate=certificate,
				wrapper_mode=_DFA_GUARD_TRANSITION_WRAPPER_MODE,
				controller_strategy=settings.controller_strategy,
				monitor_checkpoint_action=monitor_checkpoint_action,
			)
		else:
			controller_compilation = compile_transition_repair_tree(
				transition_symbol=transition_name,
				shared_context=shared_context,
				positive_literals=repair_literals,
				completion_context=completion_context,
				certificate=certificate,
				wrapper_mode=_DFA_GUARD_TRANSITION_WRAPPER_MODE,
				controller_strategy=settings.controller_strategy,
				monitor_checkpoint_action=monitor_checkpoint_action,
			)
		plans.extend(controller_compilation.plans)
	return tuple(plans)


def _canonical_literal_key(literal: DFALiteral) -> tuple[str, tuple[str, ...]]:
	return literal.predicate, literal.arguments


def _canonical_unprotected_literal_serialization(
	literals: Sequence[DFALiteral],
	*,
	negative_literals: Sequence[DFALiteral],
	source_invariants: Sequence[DFALiteral],
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	helper_prefix: str,
) -> tuple[
	tuple[DFALiteral, ...],
	Mapping[str, object],
	tuple[AgentSpeakPlan, ...],
	Mapping[str, str | _AchievementHelperCall],
	tuple[AgentSpeakPlan, ...],
	Mapping[int, tuple[str, tuple[str, ...]]],
]:
	"""Build the evaluation-only canonical baseline without positive protection."""

	literal_tuple = tuple(literals)
	negative_literal_tuple = tuple(negative_literals)
	establishment_aliases, establishment_helpers, establishment = (
		negative_guard_establishment_alias_plans(
			tuple((literal.predicate, literal.arguments) for literal in literal_tuple),
			negative_literals=tuple(
				(literal.predicate, literal.arguments)
				for literal in negative_literal_tuple
			),
			plan_library=plan_library,
			domain=domain,
			helper_prefix=helper_prefix,
		)
	)
	certificate: dict[str, object] = {
		"certificate_kind": "evaluation_only_canonical_unprotected_serialization",
		"ordered_literal_indexes": list(range(len(literal_tuple))),
		"canonical_positive_literal_order": [literal.atom for literal in literal_tuple],
		"canonical_negative_literal_order": [
			literal.atom for literal in negative_literal_tuple
		],
		"threat_edges": [],
		"module_summaries_complete": False,
		"conditional_effects_checked": False,
		"positive_sibling_preservation_checked": False,
		"source_invariant_preservation_checked": False,
		"source_invariant_count": len(tuple(source_invariants)),
		"repair_positive_before_negative": True,
		"evaluation_only": True,
	}
	certificate.update(establishment)
	return (
		literal_tuple,
		certificate,
		(),
		{},
		establishment_aliases,
		establishment_helpers,
	)


def _certified_positive_literal_serialization(
	literals: Sequence[DFALiteral],
	*,
	negative_literals: Sequence[DFALiteral] = (),
	source_invariants: Sequence[DFALiteral] = (),
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	helper_prefix: str,
) -> tuple[
	tuple[DFALiteral, ...],
	Mapping[str, object],
	tuple[AgentSpeakPlan, ...],
	Mapping[str, str | _AchievementHelperCall],
	tuple[AgentSpeakPlan, ...],
	Mapping[int, tuple[str, tuple[str, ...]]],
]:
	literal_tuple = tuple(literals or ())
	negative_literal_tuple = tuple(negative_literals or ())
	declared_numeric_functions = {function.name for function in domain.functions}
	all_literals = (*literal_tuple, *negative_literal_tuple)
	numeric_literals = tuple(
		literal
		for literal in all_literals
		if literal.predicate in declared_numeric_functions
	)
	literal_signatures = tuple(
		(literal.predicate, literal.arguments) for literal in literal_tuple
	)
	negative_literal_signatures = tuple(
		(literal.predicate, literal.arguments) for literal in negative_literal_tuple
	)
	if numeric_literals and literal_tuple:
		try:
			(
				ordered_indexes,
				certificate,
				mixed_aliases,
				mixed_helpers,
			) = _mixed_numeric_literal_order(
				literal_tuple,
				negative_literals=negative_literal_tuple,
				source_invariants=tuple(source_invariants),
				plan_library=plan_library,
				domain=domain,
				helper_prefix=helper_prefix,
			)
		except ValueError as error:
			if not str(error).startswith(
				"cyclic_conjunctive_transition_not_certified"
			):
				raise
			direct_guard = _single_action_whole_guard_plans(
				literal_tuple,
				negative_literals=negative_literal_tuple,
				domain=domain,
				helper_prefix=helper_prefix,
			)
			if direct_guard is None:
				raise
			(
				ordered_indexes,
				certificate_payload,
				aliases,
				helper_by_predicate,
			) = direct_guard
			return (
				tuple(literal_tuple[index] for index in ordered_indexes),
				certificate_payload,
				aliases,
				helper_by_predicate,
				(),
				{},
			)
		establishment_aliases, establishment_helpers, establishment = (
			negative_guard_establishment_alias_plans(
				literal_signatures,
				negative_literals=negative_literal_signatures,
				plan_library=plan_library,
				domain=domain,
				helper_prefix=helper_prefix,
			)
		)
		certificate.update(establishment)
		return (
			tuple(literal_tuple[index] for index in ordered_indexes),
			certificate,
			mixed_aliases,
			mixed_helpers,
			establishment_aliases,
			establishment_helpers,
		)
	if not literal_tuple:
		establishment_aliases, establishment_helpers, establishment = (
			negative_guard_establishment_alias_plans(
				(),
				negative_literals=negative_literal_signatures,
				plan_library=plan_library,
				domain=domain,
				helper_prefix=helper_prefix,
			)
		)
		certificate = {
			"certificate_kind": "negative_context_only_transition",
			"ordered_literal_indexes": [],
			"threat_edges": [],
			"module_summaries_complete": True,
			"negative_guard_count": len(negative_literal_tuple),
			"negative_guard_literals": [
				literal.atom for literal in negative_literal_tuple
			],
			"negative_guard_preservation_checked": True,
			"negative_guard_preserved": True,
			"negative_guard_threats": [],
		}
		certificate.update(establishment)
		return (
			(),
			certificate,
			(),
			{},
			establishment_aliases,
			establishment_helpers,
		)
	if source_invariants and not numeric_literals:
		if len(literal_tuple) != 1:
			raise ValueError(
				"source_invariant_conjunctive_progress_not_certified: primitive-prefix "
				"preservation currently requires one positive progress literal.",
			)
		aliases, helper_by_predicate, source_certificate = (
			_source_invariant_safe_alias_plans(
				literal_tuple[0],
				source_invariants=tuple(source_invariants),
				completion_negative_literals=negative_literal_tuple,
				plan_library=plan_library,
				domain=domain,
				helper_prefix=helper_prefix,
			)
		)
		return (
			literal_tuple,
			source_certificate,
			aliases,
			helper_by_predicate,
			(),
			{},
		)
	if len(literal_tuple) <= 1 and not negative_literal_tuple:
		indexes = tuple(range(len(literal_tuple)))
		return (
			literal_tuple,
			{
				"certificate_kind": "singleton_transition_identity_serialization",
				"ordered_literal_indexes": list(indexes),
				"threat_edges": [],
				"module_summaries_complete": True,
			},
			(),
			{},
			(),
			{},
		)
	try:
		ordered_indexes, certificate = threat_safe_positive_literal_order(
			literal_signatures,
			plan_library=plan_library,
			domain=domain,
			negative_literals=negative_literal_signatures,
		)
	except ValueError as error:
		if not str(error).startswith(
			(
				"uncertified_conjunctive_transition",
				"cyclic_conjunctive_transition_not_certified",
				"negative_guard_not_preserved",
			),
		):
			raise
		direct_guard = _single_action_whole_guard_plans(
			literal_tuple,
			negative_literals=negative_literal_tuple,
			domain=domain,
			helper_prefix=helper_prefix,
		)
		if direct_guard is not None:
			(
				ordered_indexes,
				certificate_payload,
				aliases,
				helper_by_predicate,
			) = direct_guard
			return (
				tuple(literal_tuple[index] for index in ordered_indexes),
				certificate_payload,
				aliases,
				helper_by_predicate,
				(),
				{},
			)
		selection = preservation_safe_plan_selection(
			literal_signatures,
			plan_library=plan_library,
			domain=domain,
			negative_literals=negative_literal_signatures,
		)
		if selection is None:
			raise
		aliases, helper_by_predicate = query_local_preservation_alias_plans(
			selection,
			helper_prefix=helper_prefix,
		)
		certificate_payload = selection.certificate.to_dict()
		certificate_payload["negative_guard_literals"] = [
			literal.atom for literal in negative_literal_tuple
		]
		establishment_aliases, establishment_helpers, establishment = (
			negative_guard_establishment_alias_plans(
				literal_signatures,
				negative_literals=negative_literal_signatures,
				plan_library=plan_library,
				domain=domain,
				helper_prefix=helper_prefix,
			)
		)
		certificate_payload.update(establishment)
		return (
			tuple(literal_tuple[index] for index in selection.ordered_indexes),
			certificate_payload,
			aliases,
			helper_by_predicate,
			establishment_aliases,
			establishment_helpers,
		)
	certificate_payload = certificate.to_dict()
	certificate_payload["negative_guard_literals"] = [
		literal.atom for literal in negative_literal_tuple
	]
	establishment_aliases, establishment_helpers, establishment = (
		negative_guard_establishment_alias_plans(
			literal_signatures,
			negative_literals=negative_literal_signatures,
			plan_library=plan_library,
			domain=domain,
			helper_prefix=helper_prefix,
		)
	)
	certificate_payload.update(establishment)
	return (
		tuple(literal_tuple[index] for index in ordered_indexes),
		certificate_payload,
		(),
		{},
		establishment_aliases,
		establishment_helpers,
	)


def _single_action_whole_guard_plans(
	literals: Sequence[DFALiteral],
	*,
	negative_literals: Sequence[DFALiteral],
	domain: PDDLDomain,
	helper_prefix: str,
) -> tuple[
	tuple[int, ...],
	dict[str, object],
	tuple[AgentSpeakPlan, ...],
	Mapping[str, _AchievementHelperCall],
] | None:
	"""Find one PDDL action whose net effects establish an entire guard."""

	positive_tuple = tuple(literals)
	negative_tuple = tuple(negative_literals)
	numeric_functions = {function.name for function in domain.functions}
	boolean_positive_indexes = tuple(
		index
		for index, literal in enumerate(positive_tuple)
		if literal.predicate not in numeric_functions
	)
	boolean_negative_tuple = tuple(
		literal
		for literal in negative_tuple
		if literal.predicate not in numeric_functions
	)
	numeric_positive_tuple = tuple(
		literal
		for literal in positive_tuple
		if literal.predicate in numeric_functions
	)
	numeric_negative_tuple = tuple(
		literal
		for literal in negative_tuple
		if literal.predicate in numeric_functions
	)
	if not positive_tuple or not boolean_positive_indexes or numeric_negative_tuple:
		return None
	query_variables = {
		argument
		for literal in (*positive_tuple, *negative_tuple)
		for argument in (
			literal.arguments[:-1]
			if literal.predicate in numeric_functions
			else literal.arguments
		)
		if _is_agentspeak_variable(argument)
	}
	aliases_by_anchor: dict[int, list[AgentSpeakPlan]] = {}
	numeric_contexts_by_anchor: dict[int, tuple[str, ...]] = {}
	for action_index, pddl_action in enumerate(domain.actions, start=1):
		action = _ParsedAction.from_pddl(pddl_action)
		for anchor_index in boolean_positive_indexes:
			anchor = positive_tuple[anchor_index]
			if query_variables - set(anchor.arguments):
				continue
			for anchor_effect in action.add_effects:
				binding = _extend_schema_binding(
					{},
					schema=anchor_effect,
					literal=anchor,
					action=action,
				)
				if binding is None:
					continue
				for sibling_index in boolean_positive_indexes:
					if sibling_index == anchor_index:
						continue
					sibling = positive_tuple[sibling_index]
					binding = _bind_literal_from_effects(
						binding,
						literal=sibling,
						effects=action.add_effects,
						action=action,
					)
					if binding is None:
						break
				if binding is None:
					continue
				for forbidden in boolean_negative_tuple:
					candidate = _bind_literal_from_effects(
						binding,
						literal=forbidden,
						effects=action.delete_effects,
						action=action,
					)
					if candidate is not None:
						binding = candidate
				for numeric_literal in numeric_positive_tuple:
					candidate = _compatible_numeric_effect_binding(
						action=action,
						literal=numeric_literal,
						binding=binding,
					)
					if candidate is None:
						binding = None
						break
					binding = candidate
				if binding is None:
					continue
				binding = _complete_action_binding(action, binding)
				adds = tuple(
					_map_schema_literal(effect, binding=binding)
					for effect in action.add_effects
				)
				deletes = tuple(
					_map_schema_literal(effect, binding=binding)
					for effect in action.delete_effects
				)
				if not all(
					any(_same_dfa_atom(effect, literal) for effect in adds)
					for index, literal in enumerate(positive_tuple)
					if index in boolean_positive_indexes
				):
					continue
				numeric_predecessor_contexts: list[str] = []
				numeric_effects_certified = True
				for numeric_literal in numeric_positive_tuple:
					if (
						not numeric_literal.arguments
						or re.fullmatch(
							r"[+-]?\d+",
							numeric_literal.arguments[-1],
						)
						is None
					):
						numeric_effects_certified = False
						break
					target_value = int(numeric_literal.arguments[-1])
					delta = _bound_numeric_effect_delta(
						action=action,
						binding=binding,
						function=numeric_literal.predicate,
						arguments=numeric_literal.arguments[:-1],
					)
					if delta is None or delta == 0:
						numeric_effects_certified = False
						break
					numeric_predecessor_contexts.append(
						_call(
							numeric_literal.predicate,
							(
								*numeric_literal.arguments[:-1],
								str(target_value - delta),
							),
						),
					)
				if not numeric_effects_certified:
					continue
				guards: list[str] = []
				negative_established = True
				for forbidden in boolean_negative_tuple:
					if any(_same_dfa_atom(effect, forbidden) for effect in deletes):
						pass
					else:
						negative_established = False
						break
					for effect in adds:
						guard = _atom_non_unification_guard(effect, forbidden)
						if guard is None:
							negative_established = False
							break
						if guard:
							guards.append(guard)
					if not negative_established:
						break
				if not negative_established:
					continue
				context = _single_action_guard_context(
					action=action,
					binding=binding,
					guards=guards,
				)
				if context is None:
					continue
				context = tuple(
					dict.fromkeys((*context, *numeric_predecessor_contexts))
				)
				helper_symbol = _safe_query_identifier(
					f"{helper_prefix}_establish_guard_{anchor.predicate}_{anchor_index + 1}"
				)
				aliases_by_anchor.setdefault(anchor_index, []).append(
					AgentSpeakPlan(
						plan_name=f"{helper_symbol}_{action.name}_{action_index}",
						trigger=AgentSpeakTrigger(
							"achievement_goal",
							helper_symbol,
							anchor.arguments,
						),
						context=context,
						body=(
							AgentSpeakBodyStep(
								"action",
								action.name,
								tuple(binding[parameter] for parameter in action.parameters),
							),
						),
						binding_certificate=(
							{
								"artifact_family": "temporal_goal_dfa_append",
								"wrapper_role": "query_local_whole_guard_branch",
								"certificate_kind": "pddl_single_action_whole_guard",
								"source_action": action.name,
								"positive_guard_literals": [
									literal.atom for literal in positive_tuple
								],
								"negative_guard_literals": [
									literal.atom for literal in negative_tuple
								],
								"numeric_guard_literals": [
									literal.atom for literal in numeric_positive_tuple
								],
								"numeric_predecessor_contexts": list(
									numeric_predecessor_contexts
								),
							},
						),
					),
				)
				numeric_contexts_by_anchor[anchor_index] = tuple(
					numeric_predecessor_contexts
				)
	if not aliases_by_anchor:
		return None
	anchor_index = min(aliases_by_anchor)
	aliases = tuple(aliases_by_anchor[anchor_index])
	helper_symbol = aliases[0].trigger.symbol
	ordered = (anchor_index, *tuple(
		index for index in range(len(positive_tuple)) if index != anchor_index
	))
	return ordered, {
		"certificate_kind": "pddl_single_action_whole_guard",
		"ordered_literal_indexes": list(ordered),
		"threat_edges": [],
		"module_summaries_complete": True,
		"negative_guard_count": len(negative_tuple),
		"negative_guard_literals": [literal.atom for literal in negative_tuple],
		"negative_guard_preservation_checked": True,
		"negative_guard_preserved": True,
		"negative_guard_threats": [],
		"negative_guard_establishment_checked": True,
		"negative_guard_establishable": True,
		"negative_guard_establishers": {
			literal.atom: [plan.plan_name for plan in aliases]
			for literal in negative_tuple
		},
		"observation_only_literals": [],
		"whole_guard_repair_literals": [
			literal.atom for literal in positive_tuple
		],
		"repair_positive_before_negative": True,
		"numeric_guard_literals": [literal.atom for literal in numeric_positive_tuple],
		"numeric_predecessor_contexts": list(
			numeric_contexts_by_anchor.get(anchor_index, ())
		),
	}, aliases, {
		literal.atom: _AchievementHelperCall(
			symbol=helper_symbol,
			arguments=positive_tuple[anchor_index].arguments,
		)
		for literal in positive_tuple
	}


def _compatible_numeric_effect_binding(
	*,
	action: _ParsedAction,
	literal: DFALiteral,
	binding: Mapping[str, str],
) -> dict[str, str] | None:
	"""Extend a schema binding with one matching constant-delta numeric effect."""

	for effect in action.numeric_effects:
		candidate = _bind_numeric_effect_to_literal(
			action=action,
			effect=effect,
			literal=literal,
		)
		if candidate is None:
			continue
		merged = dict(binding)
		if any(
			parameter in merged and merged[parameter] != argument
			for parameter, argument in candidate.items()
		):
			continue
		merged.update(candidate)
		return merged
	return None


def _extend_schema_binding(
	binding: Mapping[str, str],
	*,
	schema,
	literal: DFALiteral,
	action: _ParsedAction,
) -> dict[str, str] | None:
	if schema.predicate != literal.predicate or len(schema.arguments) != len(literal.arguments):
		return None
	result = dict(binding)
	for schema_argument, literal_argument in zip(schema.arguments, literal.arguments):
		if schema_argument not in action.parameters:
			if schema_argument != literal_argument:
				return None
			continue
		previous = result.get(schema_argument)
		if previous is not None and previous != literal_argument:
			return None
		result[schema_argument] = literal_argument
	return result


def _bind_literal_from_effects(
	binding: Mapping[str, str],
	*,
	literal: DFALiteral,
	effects: Sequence,
	action: _ParsedAction,
) -> dict[str, str] | None:
	for effect in effects:
		candidate = _extend_schema_binding(
			binding,
			schema=effect,
			literal=literal,
			action=action,
		)
		if candidate is not None:
			return candidate
	return None


def _complete_action_binding(
	action: _ParsedAction,
	binding: Mapping[str, str],
) -> dict[str, str]:
	result = dict(binding)
	used = set(result.values())
	index = 0
	for parameter in action.parameters:
		if parameter in result:
			continue
		while f"V{index}" in used:
			index += 1
		result[parameter] = f"V{index}"
		used.add(result[parameter])
		index += 1
	return result


def _map_schema_literal(schema, *, binding: Mapping[str, str]) -> DFALiteral:
	return DFALiteral(
		schema.predicate,
		tuple(binding.get(argument, argument) for argument in schema.arguments),
		"positive" if schema.is_positive else "negative",
	)


def _same_dfa_atom(left: DFALiteral, right: DFALiteral) -> bool:
	return left.predicate == right.predicate and left.arguments == right.arguments


def _atom_non_unification_guard(left: DFALiteral, right: DFALiteral) -> str | None:
	if left.predicate != right.predicate or len(left.arguments) != len(right.arguments):
		return ""
	differences = [
		(left_argument, right_argument)
		for left_argument, right_argument in zip(left.arguments, right.arguments)
		if left_argument != right_argument
	]
	if not differences:
		return None
	constant_difference = next(
		(
			pair
			for pair in differences
			if not _is_agentspeak_variable(pair[0])
			and not _is_agentspeak_variable(pair[1])
		),
		None,
	)
	if constant_difference is not None:
		return ""
	variable_difference = next(
		(
			pair
			for pair in differences
			if _is_agentspeak_variable(pair[0])
			or _is_agentspeak_variable(pair[1])
		),
		None,
	)
	if variable_difference is None:
		return None
	left_argument, right_argument = variable_difference
	return f"{left_argument} \\== {right_argument}"


def _single_action_guard_context(
	*,
	action: _ParsedAction,
	binding: Mapping[str, str],
	guards: Sequence[str],
	reserved_variables: Sequence[str] = (),
) -> tuple[str, ...] | None:
	contexts: list[str] = []
	for parameter in action.parameters:
		argument = binding[parameter]
		type_name = action.parameter_types.get(parameter, "object")
		if type_name != "object":
			contexts.append(f"obj_tp({argument}, {type_name})")
	for precondition in action.preconditions:
		literal = _map_schema_literal(precondition, binding=binding)
		call = literal.atom
		contexts.append(call if precondition.is_positive else f"not {call}")
	used_numeric_variables = {
		argument
		for argument in binding.values()
		if _is_agentspeak_variable(argument)
	}
	used_numeric_variables.update(reserved_variables)
	for condition in action.numeric_preconditions:
		contexts.extend(
			_numeric_condition_contexts(
				condition=condition,
				variable_map=binding,
				used_variables=used_numeric_variables,
			),
		)
	contexts.extend(guard for guard in guards if guard)
	bound = {
		argument
		for argument in binding.values()
		if not _is_agentspeak_variable(argument)
	}
	for context in contexts:
		if not context.startswith("not "):
			bound.update(re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", context))
	if any(
		_is_agentspeak_variable(argument) and argument not in bound
		for argument in binding.values()
	):
		return None
	return tuple(dict.fromkeys(contexts))


def _mixed_numeric_literal_order(
	literals: Sequence[DFALiteral],
	*,
	negative_literals: Sequence[DFALiteral],
	source_invariants: Sequence[DFALiteral],
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	helper_prefix: str,
) -> tuple[
	tuple[int, ...],
	dict[str, object],
	tuple[AgentSpeakPlan, ...],
	Mapping[str, str],
]:
	"""Order mixed Boolean/numeric goals from complete primitive effect summaries."""

	literal_tuple = tuple(literals)
	negative_tuple = tuple(negative_literals)
	numeric_functions = {function.name for function in domain.functions}
	actions_by_name = {
		action.name: _ParsedAction.from_pddl(action) for action in domain.actions
	}
	effects_by_literal: list[tuple[_TemporalPlanEffects, ...]] = []
	selected_plans_by_literal: list[tuple[AgentSpeakPlan, ...]] = []
	for literal in literal_tuple:
		matching = tuple(
			plan
			for plan in plan_library.plans
			if _plan_trigger_matches_literal(plan, literal)
			and bool(plan.body)
		)
		numeric_candidates: tuple[AgentSpeakPlan, ...] = ()
		if literal.predicate in numeric_functions:
			numeric_candidates = _direct_numeric_progress_plans(
				literal,
				domain=domain,
				plan_library=plan_library,
				binding_literals=(
					*tuple(source_invariants),
					*tuple(negative_literals),
				),
				protected_literals=tuple(source_invariants),
			)
			matching = (
				*matching,
				*numeric_candidates,
			)
		effects: list[_TemporalPlanEffects] = []
		selected_plans: list[AgentSpeakPlan] = []
		for plan in matching:
			summary = _action_only_temporal_effects(
				plan,
				literal=literal,
				actions_by_name=actions_by_name,
			)
			if summary is None:
				continue
			if any(
				_effects_may_establish_literal(
					summary,
					literal=forbidden,
					numeric_functions=numeric_functions,
				)
				for forbidden in negative_tuple
			):
				continue
			effects.append(summary)
			selected_plans.append(plan)
		if literal.predicate in numeric_functions and len(literal_tuple) == 1:
			selected_plans.extend(
				plan
				for plan in numeric_candidates
				if plan.binding_certificate
				and plan.binding_certificate[0].get("certificate_kind")
				in {
					"lexicographic_numeric_precondition_preparation",
					"lexicographic_numeric_requirement_preparation",
					"repeatable_source_invariant_preserving_numeric_progress",
				}
			)
		effects_by_literal.append(tuple(effects))
		selected_plans_by_literal.append(tuple(selected_plans))

	threat_edges: set[tuple[int, int]] = set()
	establishment_edges: set[tuple[int, int]] = set()
	for achiever_index, branch_effects in enumerate(effects_by_literal):
		for protected_index, protected in enumerate(literal_tuple):
			if achiever_index == protected_index:
				continue
			if any(
				_effects_may_threaten_literal(
					effects,
					protected=protected,
					numeric_functions=numeric_functions,
				)
				for effects in branch_effects
			):
				threat_edges.add((achiever_index, protected_index))
			if (
				not selected_plans_by_literal[protected_index]
				and any(
					_effects_may_establish_literal(
						effects,
						literal=protected,
						numeric_functions=numeric_functions,
					)
					for effects in branch_effects
				)
			):
				establishment_edges.add((achiever_index, protected_index))
	ordering_edges = threat_edges | establishment_edges
	ordered = _stable_literal_topological_order(len(literal_tuple), ordering_edges)
	if ordered is None:
		raise ValueError(
			"cyclic_conjunctive_transition_not_certified: mixed Boolean/numeric "
			"effect threats have no preservation-safe serialization.",
		)
	aliases, helper_by_predicate = _mixed_numeric_alias_plans(
		literal_tuple,
		selected_plans_by_literal=selected_plans_by_literal,
		helper_prefix=helper_prefix,
	)
	repair_positive_before_negative = bool(negative_tuple) and any(
		certificate.get("negative_guard_established") is True
		or certificate.get("negative_guard_established_by_final_action") is True
		for plans in selected_plans_by_literal
		for plan in plans
		for certificate in plan.binding_certificate
	)
	certificate = {
		"certificate_kind": "mixed_boolean_numeric_effect_order",
		"effect_summary_method": "pddl_action_only_net_boolean_and_integer_delta",
		"ordered_literal_indexes": list(ordered),
		"threat_edges": [list(edge) for edge in sorted(threat_edges)],
		"side_effect_establishment_edges": [
			list(edge) for edge in sorted(establishment_edges)
		],
		"module_summaries_complete": True,
		"numeric_effects_checked": True,
		"negative_guard_count": len(negative_tuple),
		"negative_guard_literals": [literal.atom for literal in negative_tuple],
		"negative_guard_preservation_checked": True,
		"negative_guard_preserved": True,
		"negative_guard_threats": [],
		"repair_positive_before_negative": repair_positive_before_negative,
		"observation_only_literals": [
			literal.atom
			for literal, plans in zip(literal_tuple, selected_plans_by_literal)
			if not plans
		],
		"observation_only_negative_literals": [
			literal.atom
			for literal in negative_tuple
			if literal.predicate in numeric_functions
		],
		"source_invariant_literals": [
			literal.atom for literal in source_invariants
		],
		"selected_action_only_branches": {
			literal.atom: [plan.plan_name for plan in plans]
			for literal, plans in zip(literal_tuple, selected_plans_by_literal)
		},
	}
	return ordered, certificate, aliases, helper_by_predicate


def _direct_numeric_progress_plans(
	literal: DFALiteral,
	*,
	domain: PDDLDomain,
	plan_library: PlanLibrary,
	binding_literals: Sequence[DFALiteral] = (),
	protected_literals: Sequence[DFALiteral] = (),
) -> tuple[AgentSpeakPlan, ...]:
	"""Compile schema-certified primitive progress toward one numeric equality."""

	if not literal.arguments or re.fullmatch(r"[+-]?\d+", literal.arguments[-1]) is None:
		return ()
	target_arguments = literal.arguments[:-1]
	target_value = int(literal.arguments[-1])
	plans: list[AgentSpeakPlan] = []
	for action_index, pddl_action in enumerate(domain.actions, start=1):
		action = _ParsedAction.from_pddl(pddl_action)
		for effect_index, effect in enumerate(action.numeric_effects, start=1):
			binding = _bind_numeric_effect_to_literal(
				action=action,
				effect=effect,
				literal=literal,
			)
			if binding is None:
				continue
			plans.extend(
				_repeating_numeric_source_preserving_plans(
					literal,
					action=action,
					base_binding=binding,
					protected_literals=protected_literals,
					binding_literals=binding_literals,
					action_index=action_index,
					effect_index=effect_index,
				),
			)
			binding = _extend_action_binding_from_guard_literals(
				action=action,
				binding=binding,
				literals=binding_literals,
			)
			binding = _complete_action_binding(action, binding)
			negative_binding_literals = tuple(
				item for item in binding_literals if item.polarity == "negative"
			)
			mapped_deletes = tuple(
				_map_schema_literal(item, binding=binding)
				for item in action.delete_effects
			)
			mapped_adds = tuple(
				_map_schema_literal(item, binding=binding)
				for item in action.add_effects
			)
			source_preservation_guards = _step_effect_preservation_guards(
				protected_literals=protected_literals,
				adds=mapped_adds,
				deletes=mapped_deletes,
				numeric_effects=action.numeric_effects,
				binding=binding,
				numeric_functions={function.name for function in domain.functions},
			)
			deletes_all_negative = all(
				any(_same_dfa_atom(deleted, forbidden) for deleted in mapped_deletes)
				for forbidden in negative_binding_literals
			)
			delta = _bound_numeric_effect_delta(
				action=action,
				binding=binding,
				function=literal.predicate,
				arguments=target_arguments,
			)
			if delta is None or delta == 0:
				continue
			used_variables = {
				argument
				for argument in binding.values()
				if _is_agentspeak_variable(argument)
			}
			value_variable = _fresh_agentspeak_variable(used_variables, prefix="N")
			reserved_variables = (
				()
				if _numeric_preconditions_reference_only_target_fluent(
					action=action,
					binding=binding,
					function=literal.predicate,
					arguments=target_arguments,
				)
				else (value_variable,)
			)
			numeric_progress_guard = _numeric_progress_guard(
				value_variable=value_variable,
				target_value=target_value,
				delta=delta,
				exact_step=bool(
					protected_literals and source_preservation_guards is None
				),
			)
			negative_guards = (
				tuple(
					f"not {forbidden.atom}"
					for forbidden in negative_binding_literals
				)
				if not deletes_all_negative
				else ()
			)
			context = _single_action_guard_context(
				action=action,
				binding=binding,
				guards=(*negative_guards, *(source_preservation_guards or ())),
				reserved_variables=reserved_variables,
			)
			if context is None:
				continue
			progress_context = (
				_call(literal.predicate, (*target_arguments, value_variable)),
				numeric_progress_guard,
			)
			plans.append(
				AgentSpeakPlan(
					plan_name=(
						f"numeric_progress_{literal.predicate}_{action.name}_"
						f"{action_index}_{effect_index}"
					),
					trigger=AgentSpeakTrigger(
						"achievement_goal",
						literal.predicate,
						literal.arguments,
					),
					context=tuple(dict.fromkeys((*progress_context, *context))),
					body=(
						AgentSpeakBodyStep(
							"action",
							action.name,
							tuple(binding[parameter] for parameter in action.parameters),
						),
					),
					binding_certificate=(
						{
							"artifact_family": "temporal_goal_dfa_append",
							"wrapper_role": "query_local_numeric_progress_branch",
							"certificate_kind": (
								"unit_monotone_numeric_progress"
								if abs(delta) == 1
								else "exact_numeric_predecessor"
							),
							"source_action": action.name,
							"numeric_function": literal.predicate,
							"target_value": target_value,
							"net_delta": delta,
							"completion_observer": "primitive_step_dfa_monitor",
							"negative_guard_established": deletes_all_negative,
							"source_invariant_preservation_guards": list(
								source_preservation_guards or ()
							),
							"source_invariant_violation_only_at_target": bool(
								protected_literals and source_preservation_guards is None
							),
						},
					),
				),
			)
			for precondition in action.preconditions:
				if not precondition.is_positive:
					continue
				if negative_binding_literals and not deletes_all_negative:
					continue
				missing = _map_schema_literal(precondition, binding=binding)
				if not _literal_has_achievement_branch(
					missing,
					plan_library=plan_library,
				):
					continue
				for support_index, support_plan in enumerate(
					(
						plan
						for plan in plan_library.plans
						if _plan_trigger_matches_literal(plan, missing) and plan.body
					),
					start=1,
				):
					support_effects = _action_only_temporal_effects(
						support_plan,
						literal=missing,
						actions_by_name={
							item.name: _ParsedAction.from_pddl(item)
							for item in domain.actions
						},
					)
					if support_effects is None:
						continue
					if any(
						function == literal.predicate
						for function, _arguments, _delta in support_effects.numeric_deltas
					):
						continue
					if not _effects_may_establish_literal(
						support_effects,
						literal=missing,
						numeric_functions=set(),
					):
						continue
					if any(
						_action_only_plan_may_delete_literal(
							support_plan,
							goal=missing,
							protected=protected,
							domain=domain,
						)
						for protected in protected_literals
					):
						continue
					grounded_context, grounded_body = _ground_action_only_plan(
						support_plan,
						goal=missing,
						reserved_variables=tuple(binding.values()),
					)
					preparation_context = tuple(
						dict.fromkeys(
							(
								*progress_context,
								*(item.atom for item in negative_binding_literals),
								*grounded_context,
							)
						)
					)
					plans.append(AgentSpeakPlan(
						plan_name=(
							f"numeric_prepare_{literal.predicate}_{missing.predicate}_"
							f"{action_index}_{effect_index}_{support_index}"
						),
						trigger=AgentSpeakTrigger(
							"achievement_goal",
							literal.predicate,
							literal.arguments,
						),
						context=preparation_context,
						body=(
							*grounded_body,
							AgentSpeakBodyStep(
								"subgoal",
								literal.predicate,
								literal.arguments,
							),
						),
						binding_certificate=(
							{
								"artifact_family": "temporal_goal_dfa_append",
								"wrapper_role": (
									"query_local_numeric_precondition_preparation"
								),
								"certificate_kind": (
									"lexicographic_numeric_precondition_preparation"
								),
								"prepared_literal": missing.atom,
								"numeric_function": literal.predicate,
								"numeric_distance_unchanged_by_preparation": True,
								"negative_guard_established_by_final_action": (
									deletes_all_negative
								),
								"ranking_components": [
									"missing_positive_precondition_count",
									"absolute_numeric_target_distance",
								],
							},
						),
					))
			plans.extend(
				_numeric_precondition_preparation_plans(
					literal,
					target_action=action,
					target_binding=binding,
					target_progress_context=progress_context,
					domain=domain,
					binding_literals=binding_literals,
					protected_literals=protected_literals,
					action_index=action_index,
					effect_index=effect_index,
				),
			)
	return tuple(plans)


def _repeating_numeric_source_preserving_plans(
	literal: DFALiteral,
	*,
	action: _ParsedAction,
	base_binding: Mapping[str, str],
	protected_literals: Sequence[DFALiteral],
	binding_literals: Sequence[DFALiteral],
	action_index: int,
	effect_index: int,
) -> tuple[AgentSpeakPlan, ...]:
	"""Compile a repeatable numeric step separated from protected source atoms."""

	if not protected_literals:
		return ()
	binding = _complete_action_binding(action, base_binding)
	target_arguments = literal.arguments[:-1]
	target_value = int(literal.arguments[-1])
	delta = _bound_numeric_effect_delta(
		action=action,
		binding=binding,
		function=literal.predicate,
		arguments=target_arguments,
	)
	if delta is None or delta == 0:
		return ()
	adds = tuple(
		_map_schema_literal(item, binding=binding) for item in action.add_effects
	)
	deletes = tuple(
		_map_schema_literal(item, binding=binding) for item in action.delete_effects
	)
	preservation_guards = _step_effect_preservation_guards(
		protected_literals=protected_literals,
		adds=adds,
		deletes=deletes,
		numeric_effects=action.numeric_effects,
		binding=binding,
		numeric_functions={literal.predicate},
	)
	if preservation_guards is None:
		return ()
	negative_literals = tuple(
		item for item in binding_literals if item.polarity == "negative"
	)
	negative_guards = _step_effect_preservation_guards(
		protected_literals=negative_literals,
		adds=adds,
		deletes=deletes,
		numeric_effects=action.numeric_effects,
		binding=binding,
		numeric_functions={literal.predicate},
	)
	if negative_guards is None:
		return ()
	used_variables = {
		argument for argument in binding.values() if _is_agentspeak_variable(argument)
	}
	value_variable = _fresh_agentspeak_variable(used_variables, prefix="N")
	reserved_variables = (
		()
		if _numeric_preconditions_reference_only_target_fluent(
			action=action,
			binding=binding,
			function=literal.predicate,
			arguments=target_arguments,
		)
		else (value_variable,)
	)
	context = _single_action_guard_context(
		action=action,
		binding=binding,
		guards=(*preservation_guards, *negative_guards),
		reserved_variables=reserved_variables,
	)
	if context is None:
		return ()
	return (
		AgentSpeakPlan(
			plan_name=(
				f"numeric_repeat_preserving_{literal.predicate}_{action.name}_"
				f"{action_index}_{effect_index}"
			),
			trigger=AgentSpeakTrigger(
				"achievement_goal",
				literal.predicate,
				literal.arguments,
			),
			context=tuple(dict.fromkeys((
				_call(literal.predicate, (*target_arguments, value_variable)),
				_numeric_progress_guard(
					value_variable=value_variable,
					target_value=target_value,
					delta=delta,
				),
				*context,
			))),
			body=(
				AgentSpeakBodyStep(
					"action",
					action.name,
					tuple(binding[parameter] for parameter in action.parameters),
				),
				AgentSpeakBodyStep(
					"subgoal",
					literal.predicate,
					literal.arguments,
				),
			),
			binding_certificate=(
				{
					"artifact_family": "temporal_goal_dfa_append",
					"wrapper_role": "query_local_numeric_progress_branch",
					"certificate_kind": (
						"repeatable_source_invariant_preserving_numeric_progress"
					),
					"source_action": action.name,
					"numeric_function": literal.predicate,
					"target_value": target_value,
					"net_delta": delta,
					"source_invariant_preservation_guards": list(
						preservation_guards
					),
					"ranking_components": ["absolute_numeric_target_distance"],
				},
			),
		),
	)


def _numeric_precondition_preparation_plans(
	literal: DFALiteral,
	*,
	target_action: _ParsedAction,
	target_binding: Mapping[str, str],
	target_progress_context: Sequence[str],
	domain: PDDLDomain,
	binding_literals: Sequence[DFALiteral],
	protected_literals: Sequence[DFALiteral],
	action_index: int,
	effect_index: int,
) -> tuple[AgentSpeakPlan, ...]:
	"""Prepare monotone numeric prerequisites without changing the target fluent."""

	numeric_functions = {function.name for function in domain.functions}
	completion_negative_literals = tuple(
		item for item in binding_literals if item.polarity == "negative"
	)
	plans: list[AgentSpeakPlan] = []
	for condition_index, condition in enumerate(
		target_action.numeric_preconditions,
		start=1,
	):
		requirement = _constant_bound_numeric_requirement(
			condition,
			binding=target_binding,
		)
		if requirement is None:
			continue
		function, arguments, comparator, bound = requirement
		if function == literal.predicate and tuple(arguments) == tuple(literal.arguments[:-1]):
			continue
		for support_action_index, pddl_support_action in enumerate(
			domain.actions,
			start=1,
		):
			support_action = _ParsedAction.from_pddl(pddl_support_action)
			for support_effect_index, support_effect in enumerate(
				support_action.numeric_effects,
				start=1,
			):
				support_binding = _bind_numeric_effect_to_literal(
					action=support_action,
					effect=support_effect,
					literal=DFALiteral(function, (*arguments, str(bound))),
				)
				if support_binding is None:
					continue
				support_binding = _complete_action_binding(
					support_action,
					support_binding,
				)
				delta = _bound_numeric_effect_delta(
					action=support_action,
					binding=support_binding,
					function=function,
					arguments=arguments,
				)
				if delta is None or not _delta_progresses_numeric_requirement(
					comparator=comparator,
					bound=bound,
					delta=delta,
				):
					continue
				if _bound_numeric_effect_delta(
					action=support_action,
					binding=support_binding,
					function=literal.predicate,
					arguments=literal.arguments[:-1],
				) is not None:
					continue
				adds = tuple(
					_map_schema_literal(item, binding=support_binding)
					for item in support_action.add_effects
				)
				deletes = tuple(
					_map_schema_literal(item, binding=support_binding)
					for item in support_action.delete_effects
				)
				preservation_guards = _step_effect_preservation_guards(
					protected_literals=(
						*tuple(protected_literals),
						*completion_negative_literals,
					),
					adds=adds,
					deletes=deletes,
					numeric_effects=support_action.numeric_effects,
					binding=support_binding,
					numeric_functions=numeric_functions,
				)
				if preservation_guards is None:
					continue
				mapped_target_preconditions = tuple(
					_map_schema_literal(item, binding=target_binding)
					for item in target_action.preconditions
					if item.is_positive
				)
				if any(
					deleted.predicate == protected.predicate
					and _argument_tuples_may_unify(
						deleted.arguments,
						protected.arguments,
					)
					for deleted in deletes
					for protected in mapped_target_preconditions
				):
					continue
				used_variables = {
					argument
					for argument in support_binding.values()
					if _is_agentspeak_variable(argument)
				}
				used_variables.update(
					variable
					for context_item in target_progress_context
					for variable in re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", context_item)
				)
				value_variable = _fresh_agentspeak_variable(
					used_variables,
					prefix="N",
				)
				progress_guard = _numeric_requirement_progress_guard(
					value_variable=value_variable,
					comparator=comparator,
					bound=bound,
					delta=delta,
				)
				if progress_guard is None:
					continue
				context = _single_action_guard_context(
					action=support_action,
					binding=support_binding,
					guards=tuple(
						(
							*tuple(
								item.atom
								if item.polarity == "positive"
								else f"not {item.atom}"
								for item in protected_literals
							),
							*preservation_guards,
						)
					),
					reserved_variables=(value_variable,),
				)
				if context is None:
					continue
				plans.append(AgentSpeakPlan(
					plan_name=(
						f"numeric_prepare_requirement_{literal.predicate}_{function}_"
						f"{action_index}_{effect_index}_{condition_index}_"
						f"{support_action_index}_{support_effect_index}"
					),
					trigger=AgentSpeakTrigger(
						"achievement_goal",
						literal.predicate,
						literal.arguments,
					),
					context=tuple(dict.fromkeys((
						*target_progress_context,
						_call(function, (*arguments, value_variable)),
						progress_guard,
						*context,
					))),
					body=(
						AgentSpeakBodyStep(
							"action",
							support_action.name,
							tuple(
								support_binding[parameter]
								for parameter in support_action.parameters
							),
						),
						AgentSpeakBodyStep(
							"subgoal",
							literal.predicate,
							literal.arguments,
						),
					),
					binding_certificate=(
						{
							"artifact_family": "temporal_goal_dfa_append",
							"wrapper_role": (
								"query_local_numeric_precondition_preparation"
							),
							"certificate_kind": (
								"lexicographic_numeric_requirement_preparation"
							),
							"prepared_numeric_function": function,
							"prepared_comparator": comparator,
							"prepared_bound": bound,
							"net_delta": delta,
							"target_numeric_function_unchanged": True,
							"source_invariants_preserved": True,
							"ranking_components": [
								"numeric_precondition_deficit",
								"absolute_numeric_target_distance",
							],
						},
					),
				))
	return tuple(plans)


def _source_invariant_safe_alias_plans(
	literal: DFALiteral,
	*,
	source_invariants: Sequence[DFALiteral],
	completion_negative_literals: Sequence[DFALiteral],
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	helper_prefix: str,
) -> tuple[tuple[AgentSpeakPlan, ...], Mapping[str, str], dict[str, object]]:
	"""Select action-only branches preserving a DFA source state until completion."""

	actions_by_name = {
		action.name: _ParsedAction.from_pddl(action) for action in domain.actions
	}
	numeric_functions = {function.name for function in domain.functions}
	selected = tuple(
		plan
		for plan in plan_library.plans
		if plan.body
		and _plan_trigger_matches_literal(plan, literal)
		and _plan_has_primitive_prefix_source_invariant_certificate(
			plan,
			goal=literal,
			source_invariants=source_invariants,
			completion_negative_literals=completion_negative_literals,
			actions_by_name=actions_by_name,
			numeric_functions=numeric_functions,
		)
	)
	certificate: dict[str, object] = {
		"certificate_kind": "primitive_prefix_source_invariant_preservation",
		"ordered_literal_indexes": [0],
		"threat_edges": [],
		"module_summaries_complete": True,
		"source_invariant_literals": [item.atom for item in source_invariants],
		"source_invariant_safe_branches": {
			literal.atom: [plan.plan_name for plan in selected],
		},
		"observation_only_literals": [] if selected else [literal.atom],
	}
	if not selected:
		return (), {}, certificate
	helper_symbol = _safe_query_identifier(
		f"{helper_prefix}_source_safe_{literal.predicate}",
	)
	direct_aliases = tuple(
		AgentSpeakPlan(
			plan_name=f"{helper_symbol}_branch_{index}_{plan.plan_name}",
			trigger=AgentSpeakTrigger(
				plan.trigger.event_type,
				helper_symbol,
				plan.trigger.arguments,
			),
			context=plan.context,
			body=plan.body,
			source_instruction_ids=plan.source_instruction_ids,
			binding_certificate=(
				*plan.binding_certificate,
				{
					"artifact_family": "temporal_goal_dfa_append",
					"wrapper_role": "query_local_source_invariant_safe_branch",
					"certificate_kind": (
						"primitive_prefix_source_invariant_preservation"
					),
					"source_atomic_plan": plan.plan_name,
					"source_invariants": [item.atom for item in source_invariants],
					"completion_negative_literals": [
						item.atom for item in completion_negative_literals
					],
					"observation_boundary": "successful_primitive_action",
				},
			),
		)
		for index, plan in enumerate(selected, start=1)
	)
	preparation_aliases = _source_invariant_preparation_aliases(
		literal,
		direct_plans=selected,
		helper_symbol=helper_symbol,
		source_invariants=source_invariants,
		completion_negative_literals=completion_negative_literals,
		plan_library=plan_library,
		domain=domain,
		actions_by_name=actions_by_name,
		numeric_functions=numeric_functions,
	)
	aliases = (*direct_aliases, *preparation_aliases)
	certificate["source_invariant_preparation_branches"] = [
		plan.plan_name for plan in preparation_aliases
	]
	return aliases, {literal.atom: helper_symbol}, certificate


def _plan_has_primitive_prefix_source_invariant_certificate(
	plan: AgentSpeakPlan,
	*,
	goal: DFALiteral,
	source_invariants: Sequence[DFALiteral],
	completion_negative_literals: Sequence[DFALiteral],
	actions_by_name: Mapping[str, _ParsedAction],
	numeric_functions: set[str],
	allow_source_violation_on_goal_establishment: bool = True,
) -> bool:
	"""Prove that no primitive prefix leaves the DFA source state prematurely."""

	trigger_binding = {
		formal: actual
		for formal, actual in zip(plan.trigger.arguments, goal.arguments)
		if _is_agentspeak_variable(formal)
	}
	goal_established = False
	for step in plan.body:
		if step.kind != "action":
			return False
		action = actions_by_name.get(step.symbol)
		if action is None or len(action.parameters) != len(step.arguments):
			return False
		step_arguments = tuple(
			trigger_binding.get(argument, argument) for argument in step.arguments
		)
		binding = dict(zip(action.parameters, step_arguments))
		adds = tuple(
			_map_schema_literal(effect, binding=binding) for effect in action.add_effects
		)
		deletes = tuple(
			_map_schema_literal(effect, binding=binding) for effect in action.delete_effects
		)
		step_establishes_goal = any(_same_dfa_atom(effect, goal) for effect in adds)
		if not goal_established:
			source_violated = any(
				_step_effects_may_violate_literal(
					invariant,
					adds=adds,
					deletes=deletes,
					numeric_effects=action.numeric_effects,
					binding=binding,
					numeric_functions=numeric_functions,
				)
				for invariant in source_invariants
			)
			if source_violated and not (
				allow_source_violation_on_goal_establishment
				and step_establishes_goal
			):
				return False
			if any(
				_step_effects_may_violate_literal(
					forbidden,
					adds=adds,
					deletes=deletes,
					numeric_effects=action.numeric_effects,
					binding=binding,
					numeric_functions=numeric_functions,
				)
				for forbidden in completion_negative_literals
			):
				return False
		goal_established = goal_established or step_establishes_goal
	return goal_established


def _source_invariant_preparation_aliases(
	literal: DFALiteral,
	*,
	direct_plans: Sequence[AgentSpeakPlan],
	helper_symbol: str,
	source_invariants: Sequence[DFALiteral],
	completion_negative_literals: Sequence[DFALiteral],
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	actions_by_name: Mapping[str, _ParsedAction],
	numeric_functions: set[str],
) -> tuple[AgentSpeakPlan, ...]:
	"""Prepare one producer precondition under a strict lexicographic certificate."""

	aliases: list[AgentSpeakPlan] = []
	for direct_index, direct_plan in enumerate(direct_plans, start=1):
		if len(direct_plan.body) != 1 or direct_plan.body[0].kind != "action":
			continue
		direct_step = direct_plan.body[0]
		direct_action = actions_by_name.get(direct_step.symbol)
		if direct_action is None:
			continue
		trigger_binding = {
			formal: actual
			for formal, actual in zip(direct_plan.trigger.arguments, literal.arguments)
			if _is_agentspeak_variable(formal)
		}
		step_arguments = tuple(
			trigger_binding.get(argument, argument) for argument in direct_step.arguments
		)
		binding = dict(zip(direct_action.parameters, step_arguments))
		binding = _extend_action_binding_from_guard_literals(
			action=direct_action,
			binding=binding,
			literals=source_invariants,
		)
		binding = _complete_action_binding(direct_action, binding)
		mapped_preconditions = tuple(
			_map_schema_literal(precondition, binding=binding)
			for precondition in direct_action.preconditions
		)
		positive_preconditions = tuple(
			item for item in mapped_preconditions if item.polarity == "positive"
		)
		known_source_atoms = {
			item.atom for item in source_invariants if item.polarity == "positive"
		}
		for missing_index, missing in enumerate(positive_preconditions, start=1):
			if missing.atom in known_source_atoms:
				continue
			other_preconditions = tuple(
				item for item in positive_preconditions if item != missing
			)
			for support_index, support_plan in enumerate(
				(
					plan
					for plan in plan_library.plans
					if plan.body and _plan_trigger_matches_literal(plan, missing)
				),
				start=1,
			):
				if not _plan_has_primitive_prefix_source_invariant_certificate(
					support_plan,
					goal=missing,
					source_invariants=source_invariants,
					completion_negative_literals=completion_negative_literals,
					actions_by_name=actions_by_name,
					numeric_functions=numeric_functions,
					allow_source_violation_on_goal_establishment=False,
				):
					continue
				if any(
					_action_only_plan_may_delete_literal(
						support_plan,
						goal=missing,
						protected=protected,
						domain=domain,
					)
					for protected in other_preconditions
				):
					continue
				support_effects = _action_only_temporal_effects(
					support_plan,
					literal=missing,
					actions_by_name=actions_by_name,
				)
				if support_effects is None:
					continue
				if _effects_may_establish_literal(
					support_effects,
					literal=literal,
					numeric_functions=numeric_functions,
				):
					continue
				if _support_changes_numeric_precondition_function(
					support_effects,
					direct_action=direct_action,
				):
					continue
				grounded_context, grounded_body = _ground_action_only_plan(
					support_plan,
					goal=missing,
					reserved_variables=tuple(binding.values()),
				)
				direct_context = _producer_preparation_context(
					action=direct_action,
					binding=binding,
					missing=missing,
					source_invariants=source_invariants,
				)
				aliases.append(AgentSpeakPlan(
					plan_name=(
						f"{helper_symbol}_prepare_{direct_index}_{missing_index}_"
						f"{support_index}_{support_plan.plan_name}"
					),
					trigger=AgentSpeakTrigger(
						"achievement_goal",
						helper_symbol,
						literal.arguments,
					),
					context=tuple(dict.fromkeys((*direct_context, *grounded_context))),
					body=(
						*grounded_body,
						AgentSpeakBodyStep("subgoal", helper_symbol, literal.arguments),
					),
					binding_certificate=(
						{
							"artifact_family": "temporal_goal_dfa_append",
							"wrapper_role": (
								"query_local_source_invariant_preparation"
							),
							"certificate_kind": (
								"lexicographic_source_invariant_preparation"
							),
							"prepared_literal": missing.atom,
							"source_atomic_plan": support_plan.plan_name,
							"ranking_components": [
								"missing_positive_producer_precondition_count",
							],
							"other_producer_preconditions_preserved": True,
							"source_invariants_preserved": True,
						},
					),
				))
	return tuple(aliases)


def _producer_preparation_context(
	*,
	action: _ParsedAction,
	binding: Mapping[str, str],
	missing: DFALiteral,
	source_invariants: Sequence[DFALiteral],
) -> tuple[str, ...]:
	contexts: list[str] = []
	for parameter in action.parameters:
		type_name = action.parameter_types.get(parameter, "object")
		if type_name != "object":
			contexts.append(f"obj_tp({binding[parameter]}, {type_name})")
	for invariant in source_invariants:
		contexts.append(
			invariant.atom
			if invariant.polarity == "positive"
			else f"not {invariant.atom}"
		)
	contexts.append(f"not {missing.atom}")
	for precondition in action.preconditions:
		mapped = _map_schema_literal(precondition, binding=binding)
		if mapped == missing:
			continue
		contexts.append(
			mapped.atom if mapped.polarity == "positive" else f"not {mapped.atom}"
		)
	used_variables = {
		argument for argument in binding.values() if _is_agentspeak_variable(argument)
	}
	for condition in action.numeric_preconditions:
		contexts.extend(
			_numeric_condition_contexts(
				condition=condition,
				variable_map=binding,
				used_variables=used_variables,
			),
		)
	return tuple(dict.fromkeys(contexts))


def _support_changes_numeric_precondition_function(
	effects: _TemporalPlanEffects,
	*,
	direct_action: _ParsedAction,
) -> bool:
	functions = {
		str(expression.value).strip().lower()
		for condition in direct_action.numeric_preconditions
		for expression in (condition.left, condition.right)
		if expression.kind != "constant"
	}
	return any(function in functions for function, _arguments, _delta in effects.numeric_deltas)


def _step_effects_may_violate_literal(
	literal: DFALiteral,
	*,
	adds: Sequence[DFALiteral],
	deletes: Sequence[DFALiteral],
	numeric_effects: Sequence[Any],
	binding: Mapping[str, str],
	numeric_functions: set[str],
) -> bool:
	if literal.predicate in numeric_functions:
		arguments = literal.arguments[:-1]
		return any(
			str(effect.fluent.function).strip().lower() == literal.predicate
			and _argument_tuples_may_unify(
				tuple(
					binding.get(argument, argument)
					for argument in tuple(effect.fluent.args or ())
				),
				arguments,
			)
			for effect in numeric_effects
		)
	threatening = deletes if literal.polarity == "positive" else adds
	return any(
		effect.predicate == literal.predicate
		and _argument_tuples_may_unify(effect.arguments, literal.arguments)
		for effect in threatening
	)


def _step_effect_preservation_guards(
	*,
	protected_literals: Sequence[DFALiteral],
	adds: Sequence[DFALiteral],
	deletes: Sequence[DFALiteral],
	numeric_effects: Sequence[Any],
	binding: Mapping[str, str],
	numeric_functions: set[str],
) -> tuple[str, ...] | None:
	"""Derive minimal non-unification guards for one primitive action."""

	guards: list[str] = []
	for protected in protected_literals:
		if protected.predicate in numeric_functions:
			protected_atom = DFALiteral(
				protected.predicate,
				protected.arguments[:-1],
			)
			threatening = tuple(
				DFALiteral(
					str(effect.fluent.function).strip().lower(),
					tuple(
						binding.get(argument, argument)
						for argument in tuple(effect.fluent.args or ())
					),
				)
				for effect in numeric_effects
				if str(effect.fluent.function).strip().lower() == protected.predicate
			)
		else:
			protected_atom = DFALiteral(protected.predicate, protected.arguments)
			threatening = deletes if protected.polarity == "positive" else adds
		for effect in threatening:
			if effect.predicate != protected_atom.predicate:
				continue
			guard = _atom_non_unification_guard(effect, protected_atom)
			if guard is None:
				return None
			if guard:
				guards.append(guard)
	return tuple(dict.fromkeys(guards))


def _extend_action_binding_from_guard_literals(
	*,
	action: _ParsedAction,
	binding: Mapping[str, str],
	literals: Sequence[DFALiteral],
) -> dict[str, str]:
	"""Bind action parameters from source invariants and signed guard atoms."""

	result = dict(binding)
	for literal in literals:
		schemas = (
			action.delete_effects
			if literal.polarity == "negative"
			else tuple(item for item in action.preconditions if item.is_positive)
		)
		for schema in schemas:
			candidate = _extend_schema_binding(
				result,
				schema=schema,
				literal=DFALiteral(
					literal.predicate,
					literal.arguments,
					"positive",
				),
				action=action,
			)
			if candidate is None:
				relaxed = {
					parameter: argument
					for parameter, argument in result.items()
					if not _is_agentspeak_variable(argument)
				}
				candidate = _extend_schema_binding(
					relaxed,
					schema=schema,
					literal=DFALiteral(
						literal.predicate,
						literal.arguments,
						"positive",
					),
					action=action,
				)
				if candidate is not None:
					substitutions = {
						result[parameter]: argument
						for parameter, argument in candidate.items()
						if parameter in result
						and _is_agentspeak_variable(result[parameter])
						and result[parameter] != argument
					}
					candidate = {
						**{
							parameter: substitutions.get(argument, argument)
							for parameter, argument in result.items()
						},
						**candidate,
					}
			if candidate is not None:
				result = candidate
				break
	return result


def _ground_action_only_plan(
	plan: AgentSpeakPlan,
	*,
	goal: DFALiteral,
	reserved_variables: Sequence[str] = (),
) -> tuple[tuple[str, ...], tuple[AgentSpeakBodyStep, ...]]:
	"""Instantiate one lifted action-only plan at a query literal."""

	trigger_variables = {
		argument
		for argument in plan.trigger.arguments
		if _is_agentspeak_variable(argument)
	}
	all_variables = {
		variable
		for context in plan.context
		for variable in re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", context)
	}
	all_variables.update(
		argument
		for step in plan.body
		for argument in step.arguments
		if _is_agentspeak_variable(argument)
	)
	actual_variables = {
		argument for argument in goal.arguments if _is_agentspeak_variable(argument)
	}
	reserved_variable_set = {
		argument for argument in reserved_variables if _is_agentspeak_variable(argument)
	}
	used_variables = (
		all_variables | actual_variables | trigger_variables | reserved_variable_set
	)
	local_renaming: dict[str, str] = {}
	for variable in sorted(
		(all_variables - trigger_variables)
		& (actual_variables | reserved_variable_set),
	):
		local_renaming[variable] = _fresh_agentspeak_variable(
			used_variables,
			prefix=variable,
		)
		used_variables.add(local_renaming[variable])
	renamed_contexts = tuple(
		_substitute_agentspeak_variables(context, local_renaming)
		for context in plan.context
	)
	renamed_body = tuple(
		AgentSpeakBodyStep(
			step.kind,
			step.symbol,
			tuple(local_renaming.get(argument, argument) for argument in step.arguments),
		)
		for step in plan.body
	)
	binding = {
		formal: actual
		for formal, actual in zip(plan.trigger.arguments, goal.arguments)
		if _is_agentspeak_variable(formal)
	}
	contexts = tuple(
		_substitute_agentspeak_variables(context, binding)
		for context in renamed_contexts
	)
	body = tuple(
		AgentSpeakBodyStep(
			step.kind,
			step.symbol,
			tuple(binding.get(argument, argument) for argument in step.arguments),
		)
		for step in renamed_body
	)
	return contexts, body


def _substitute_agentspeak_variables(
	context: str,
	binding: Mapping[str, str],
) -> str:
	result = context
	for variable in sorted(binding, key=len, reverse=True):
		result = re.sub(
			rf"\b{re.escape(variable)}\b",
			binding[variable],
			result,
		)
	return result


def _action_only_plan_may_delete_literal(
	plan: AgentSpeakPlan,
	*,
	goal: DFALiteral,
	protected: DFALiteral,
	domain: PDDLDomain,
) -> bool:
	"""Check every primitive prefix for a delete that may hit a protected atom."""

	binding = {
		formal: actual
		for formal, actual in zip(plan.trigger.arguments, goal.arguments)
		if _is_agentspeak_variable(formal)
	}
	actions = {
		action.name: _ParsedAction.from_pddl(action)
		for action in domain.actions
	}
	for step in plan.body:
		action = actions.get(step.symbol)
		if step.kind != "action" or action is None:
			return True
		step_arguments = tuple(binding.get(argument, argument) for argument in step.arguments)
		action_binding = dict(zip(action.parameters, step_arguments))
		for effect in action.delete_effects:
			deleted = _map_schema_literal(effect, binding=action_binding)
			if _atom_non_unification_guard(deleted, protected) != "":
				return True
	return False


def _bind_numeric_effect_to_literal(
	*,
	action: _ParsedAction,
	effect,
	literal: DFALiteral,
) -> dict[str, str] | None:
	if (
		str(effect.fluent.function).strip().lower() != literal.predicate
		or len(tuple(effect.fluent.args or ())) != len(literal.arguments) - 1
		or effect.operator not in {"increase", "decrease"}
		or effect.amount.kind != "constant"
		or re.fullmatch(r"[+-]?\d+", str(effect.amount.value)) is None
	):
		return None
	binding: dict[str, str] = {}
	for schema_argument, query_argument in zip(
		tuple(effect.fluent.args or ()),
		literal.arguments[:-1],
	):
		if schema_argument not in action.parameters:
			if schema_argument != query_argument:
				return None
			continue
		previous = binding.get(schema_argument)
		if previous is not None and previous != query_argument:
			return None
		binding[schema_argument] = query_argument
	return binding


def _bound_numeric_effect_delta(
	*,
	action: _ParsedAction,
	binding: Mapping[str, str],
	function: str,
	arguments: Sequence[str],
) -> int | None:
	delta = 0
	found = False
	for effect in action.numeric_effects:
		if effect.operator not in {"increase", "decrease"}:
			return None
		if effect.amount.kind != "constant" or re.fullmatch(
			r"[+-]?\d+",
			str(effect.amount.value),
		) is None:
			return None
		mapped_arguments = tuple(
			binding.get(argument, argument) for argument in tuple(effect.fluent.args or ())
		)
		if (
			str(effect.fluent.function).strip().lower() != function
			or mapped_arguments != tuple(arguments)
		):
			continue
		amount = int(str(effect.amount.value))
		delta += amount if effect.operator == "increase" else -amount
		found = True
	return delta if found else None


def _numeric_preconditions_reference_only_target_fluent(
	*,
	action: _ParsedAction,
	binding: Mapping[str, str],
	function: str,
	arguments: Sequence[str],
) -> bool:
	function_terms = tuple(
		expression
		for condition in action.numeric_preconditions
		for expression in (condition.left, condition.right)
		if expression.kind != "constant"
	)
	return bool(function_terms) and all(
		str(expression.value).strip().lower() == function
		and tuple(
			binding.get(argument, argument)
			for argument in tuple(expression.args or ())
		) == tuple(arguments)
		for expression in function_terms
	)


def _constant_bound_numeric_requirement(
	condition: Any,
	*,
	binding: Mapping[str, str],
) -> tuple[str, tuple[str, ...], str, int] | None:
	left = condition.left
	right = condition.right
	comparator = str(condition.comparator)
	if left.kind != "constant" and right.kind == "constant":
		expression = left
		bound_text = str(right.value)
	elif left.kind == "constant" and right.kind != "constant":
		expression = right
		bound_text = str(left.value)
		comparator = {
			">": "<",
			">=": "<=",
			"<": ">",
			"<=": ">=",
		}.get(comparator, comparator)
	else:
		return None
	if re.fullmatch(r"[+-]?\d+", bound_text) is None:
		return None
	return (
		str(expression.value).strip().lower(),
		tuple(
			binding.get(argument, argument)
			for argument in tuple(expression.args or ())
		),
		comparator,
		int(bound_text),
	)


def _delta_progresses_numeric_requirement(
	*,
	comparator: str,
	bound: int,
	delta: int,
) -> bool:
	del bound
	if comparator in {">", ">="}:
		return delta > 0
	if comparator in {"<", "<="}:
		return delta < 0
	return comparator == "=" and delta != 0


def _numeric_requirement_progress_guard(
	*,
	value_variable: str,
	comparator: str,
	bound: int,
	delta: int,
) -> str | None:
	if comparator == ">=":
		return f"{value_variable} < {bound}" if delta > 0 else None
	if comparator == ">":
		return f"{value_variable} <= {bound}" if delta > 0 else None
	if comparator == "<=":
		return f"{value_variable} > {bound}" if delta < 0 else None
	if comparator == "<":
		return f"{value_variable} >= {bound}" if delta < 0 else None
	if comparator == "=" and delta != 0:
		return f"{value_variable} == {bound - delta}"
	return None


def _numeric_progress_guard(
	*,
	value_variable: str,
	target_value: int,
	delta: int,
	exact_step: bool = False,
) -> str:
	if exact_step:
		return f"{value_variable} == {target_value - delta}"
	if delta == 1:
		return f"{value_variable} < {target_value}"
	if delta == -1:
		return f"{value_variable} > {target_value}"
	return f"{value_variable} == {target_value - delta}"


def _fresh_agentspeak_variable(used: set[str], *, prefix: str) -> str:
	if prefix not in used:
		return prefix
	index = 0
	while f"{prefix}{index}" in used:
		index += 1
	return f"{prefix}{index}"


def _mixed_numeric_alias_plans(
	literals: Sequence[DFALiteral],
	*,
	selected_plans_by_literal: Sequence[Sequence[AgentSpeakPlan]],
	helper_prefix: str,
) -> tuple[tuple[AgentSpeakPlan, ...], Mapping[str, str]]:
	aliases: list[AgentSpeakPlan] = []
	helper_by_predicate: dict[str, str] = {}
	for literal_index, (literal, selected_plans) in enumerate(
		zip(literals, selected_plans_by_literal),
		start=1,
	):
		plans = tuple(selected_plans)
		if not plans:
			continue
		helper_symbol = _safe_query_identifier(
			f"{helper_prefix}_repair_{literal.predicate}_{literal_index}"
		)
		helper_by_predicate[literal.atom] = helper_symbol
		aliases.append(
			AgentSpeakPlan(
				plan_name=f"{helper_symbol}_already_satisfied",
				trigger=AgentSpeakTrigger(
					"achievement_goal",
					helper_symbol,
					literal.arguments,
				),
				context=(literal.atom,),
				body=(),
				binding_certificate=(
					{
						"artifact_family": "temporal_goal_dfa_append",
						"wrapper_role": "query_local_numeric_completion_base",
						"certificate_kind": "observed_numeric_target_base_case",
						"observed_literal": literal.atom,
					},
				),
			),
		)
		for branch_index, plan in enumerate(plans, start=1):
			rewritten_body = tuple(
				AgentSpeakBodyStep(step.kind, helper_symbol, step.arguments)
				if step.kind == "subgoal"
				and step.symbol == plan.trigger.symbol
				and tuple(step.arguments) == tuple(plan.trigger.arguments)
				else step
				for step in plan.body
			)
			aliases.append(
				AgentSpeakPlan(
					plan_name=(
						f"{helper_symbol}_branch_{branch_index}_{plan.plan_name}"
					),
					trigger=AgentSpeakTrigger(
						plan.trigger.event_type,
						helper_symbol,
						plan.trigger.arguments,
					),
					context=plan.context,
					body=rewritten_body,
					source_instruction_ids=plan.source_instruction_ids,
					binding_certificate=(
						*plan.binding_certificate,
						{
							"artifact_family": "temporal_goal_dfa_append",
							"wrapper_role": "query_local_mixed_numeric_safe_branch",
							"source_atomic_plan": plan.plan_name,
							"effect_summary_method": (
								"pddl_action_only_net_boolean_and_integer_delta"
							),
						},
					),
				),
			)
	return tuple(aliases), helper_by_predicate


def _literal_has_achievement_branch(
	literal: DFALiteral,
	*,
	plan_library: PlanLibrary,
) -> bool:
	return any(
		plan.body and _plan_trigger_matches_literal(plan, literal)
		for plan in plan_library.plans
	)


def _plan_trigger_matches_literal(plan: AgentSpeakPlan, literal: DFALiteral) -> bool:
	if (
		plan.trigger.symbol != literal.predicate
		or len(plan.trigger.arguments) != len(literal.arguments)
	):
		return False
	binding: dict[str, str] = {}
	for formal, actual in zip(plan.trigger.arguments, literal.arguments):
		if _is_agentspeak_variable(formal):
			previous = binding.get(formal)
			if previous is not None and previous != actual:
				return False
			binding[formal] = actual
		elif formal != actual:
			return False
	return True


def _action_only_temporal_effects(
	plan: AgentSpeakPlan,
	*,
	literal: DFALiteral,
	actions_by_name: Mapping[str, _ParsedAction],
) -> _TemporalPlanEffects | None:
	trigger_binding = {
		formal: actual
		for formal, actual in zip(plan.trigger.arguments, literal.arguments)
		if _is_agentspeak_variable(formal)
	}
	boolean_state: dict[tuple[str, tuple[str, ...]], bool] = {}
	numeric_deltas: dict[tuple[str, tuple[str, ...]], int] = {}
	for step in plan.body:
		if step.kind != "action":
			return None
		action = actions_by_name.get(step.symbol)
		if action is None or len(action.parameters) != len(step.arguments):
			return None
		step_arguments = tuple(trigger_binding.get(argument, argument) for argument in step.arguments)
		binding = dict(zip(action.parameters, step_arguments))
		for effect in action.delete_effects:
			boolean_state[
				(
					effect.predicate,
					tuple(binding.get(argument, argument) for argument in effect.arguments),
				)
			] = False
		for effect in action.add_effects:
			boolean_state[
				(
					effect.predicate,
					tuple(binding.get(argument, argument) for argument in effect.arguments),
				)
			] = True
		for effect in action.numeric_effects:
			if (
				effect.operator not in {"increase", "decrease"}
				or effect.amount.kind != "constant"
				or re.fullmatch(r"[+-]?\d+", str(effect.amount.value)) is None
			):
				return None
			key = (
				str(effect.fluent.function).strip().lower(),
				tuple(
					binding.get(argument, argument)
					for argument in tuple(effect.fluent.args or ())
				),
			)
			amount = int(str(effect.amount.value))
			if effect.operator == "decrease":
				amount = -amount
			numeric_deltas[key] = numeric_deltas.get(key, 0) + amount
	return _TemporalPlanEffects(
		adds=frozenset(atom for atom, value in boolean_state.items() if value),
		deletes=frozenset(atom for atom, value in boolean_state.items() if not value),
		numeric_deltas=tuple(
			sorted(
				(function, arguments, delta)
				for (function, arguments), delta in numeric_deltas.items()
				if delta != 0
			),
		),
	)


def _effects_may_threaten_literal(
	effects: _TemporalPlanEffects,
	*,
	protected: DFALiteral,
	numeric_functions: set[str],
) -> bool:
	if protected.predicate in numeric_functions:
		protected_key = protected.arguments[:-1]
		return any(
			function == protected.predicate
			and _argument_tuples_may_unify(arguments, protected_key)
			for function, arguments, _delta in effects.numeric_deltas
		)
	return any(
		predicate == protected.predicate
		and _argument_tuples_may_unify(arguments, protected.arguments)
		for predicate, arguments in effects.deletes
	)


def _effects_may_establish_literal(
	effects: _TemporalPlanEffects,
	*,
	literal: DFALiteral,
	numeric_functions: set[str],
) -> bool:
	if literal.predicate in numeric_functions:
		return any(
			function == literal.predicate
			and _argument_tuples_may_unify(arguments, literal.arguments[:-1])
			for function, arguments, _delta in effects.numeric_deltas
		)
	return any(
		predicate == literal.predicate
		and _argument_tuples_may_unify(arguments, literal.arguments)
		for predicate, arguments in effects.adds
	)


def _argument_tuples_may_unify(
	left: Sequence[str],
	right: Sequence[str],
) -> bool:
	if len(left) != len(right):
		return False
	return all(
		left_argument == right_argument
		or _is_agentspeak_variable(left_argument)
		or _is_agentspeak_variable(right_argument)
		for left_argument, right_argument in zip(left, right)
	)


def _stable_literal_topological_order(
	literal_count: int,
	edges: set[tuple[int, int]],
) -> tuple[int, ...] | None:
	incoming = {index: 0 for index in range(literal_count)}
	outgoing = {index: set() for index in range(literal_count)}
	for source, target in edges:
		if target not in outgoing[source]:
			outgoing[source].add(target)
			incoming[target] += 1
	ready = [index for index in range(literal_count) if incoming[index] == 0]
	ordered: list[int] = []
	while ready:
		current = ready.pop(0)
		ordered.append(current)
		for target in sorted(outgoing[current]):
			incoming[target] -= 1
			if incoming[target] == 0:
				ready.append(target)
		ready.sort()
	return tuple(ordered) if len(ordered) == literal_count else None


def _guard_variable_type_contexts(
	literals: Sequence[DFALiteral],
	*,
	domain: PDDLDomain,
) -> tuple[str, ...]:
	"""Range-restrict lifted guard variables using declared PDDL object types."""

	parameter_types = {
		str(predicate.name): tuple(
			_parameter_type(parameter) for parameter in tuple(predicate.parameters or ())
		)
		for predicate in tuple(domain.predicates or ())
	}
	parameter_types.update(
		{
			str(function.name): (
				*tuple(
					_parameter_type(parameter)
					for parameter in tuple(function.parameters or ())
				),
				None,
			)
			for function in tuple(domain.functions or ())
		},
	)
	contexts: list[str] = []
	for literal in literals:
		for argument, type_name in zip(
			literal.arguments,
			parameter_types.get(literal.predicate, ()),
		):
			if not _is_agentspeak_variable(argument) or not type_name:
				continue
			context = f"obj_tp({argument}, {type_name})"
			if context not in contexts:
				contexts.append(context)
	return tuple(contexts)


def _parameter_type(parameter: str) -> str:
	text = str(parameter or "").strip()
	if " - " not in text:
		return "object"
	return text.rsplit(" - ", 1)[1].strip() or "object"


def _is_agentspeak_variable(argument: str) -> bool:
	text = str(argument or "").strip()
	return bool(text) and (text[0].isupper() or text[0] == "_")


def _progress_transition_state_coverage(
	*,
	transition_path: Sequence[
		tuple[tuple[DFALiteral, ...], Mapping[str, str]]
	],
) -> dict[str, object]:
	source_states = tuple(
		str(transition.get("source_state") or "").strip()
		for _literals, transition in tuple(transition_path)
	)
	return {
		"valid": True,
		"required_states": list(source_states),
		"covered_states": list(source_states),
		"uncovered_states": [],
		"progress_state_count": len(source_states),
		"covered_progress_state_count": len(source_states),
		"progress_transition_count": len(transition_path),
		"progress_transition_count_by_state": {
			state: source_states.count(state) for state in source_states
		},
		"plan_count_by_state": {state: 1 for state in source_states},
	}


def _initial_beliefs_with_query_entry(
	*,
	plan_library: PlanLibrary,
	entry_proposition: str,
) -> tuple[str, ...]:
	return tuple(
		dict.fromkeys(
			(
				*tuple(plan_library.initial_beliefs or ()),
				entry_proposition,
			),
		),
	)


def _query_entry_proposition(goal_name: str) -> str:
	text = str(goal_name or "").strip()
	if text.startswith("g_") and len(text) > 2:
		return text[2:]
	return f"{text}_entry" if text else "query_entry"


def _required_initial_state(dfa_payload: Mapping[str, Any]) -> str:
	return _required_state_label(dfa_payload.get("initial_state"), role="initial_state")


def _required_state_label(value: object, *, role: str) -> str:
	state = str(value or "").strip()
	if not state:
		raise ValueError(f"dfa_state_error: DFA payload is missing {role}.")
	return state


def _all_progress_transitions(dfa_payload: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
	progress_transitions: list[dict[str, str]] = []
	for source_state in _source_states(dfa_payload):
		progress_transitions.extend(
			progress_transitions_from_dfa_state(
				dfa_payload=dfa_payload,
				current_dfa_state=source_state,
			),
		)
	return tuple(progress_transitions)


def _parse_guard_literals(raw_label: str) -> tuple[DFALiteral, ...]:
	"""Parse one MONA guard in the supported conjunction-and-negation fragment."""

	text = str(raw_label or "").strip()
	if not text:
		raise ValueError("DFA transition guard must be non-empty.")
	if text.lower() == "true":
		return ()
	if text.lower() == "false":
		raise ValueError("False DFA transition guards cannot be compiled as progress helpers.")
	if "|" in text or " or " in f" {text.lower()} ":
		raise ValueError("Disjunctive DFA transition guards are not supported.")
	parts = _split_top_level_conjunction_strict(text)
	literals: list[DFALiteral] = []
	for part in parts:
		literal = _parse_literal(part)
		if literal is None:
			raise ValueError(
				"DFA transition guards must contain only declared predicate or numeric "
				f"resource literals joined by conjunction; received {raw_label!r}.",
			)
		if literal not in literals:
			literals.append(literal)
	return tuple(literals)


def _split_top_level_conjunction_strict(raw_guard: str) -> tuple[str, ...]:
	parts: list[str] = []
	start = 0
	depth = 0
	for index, character in enumerate(str(raw_guard or "")):
		if character == "(":
			depth += 1
		elif character == ")":
			depth -= 1
			if depth < 0:
				raise ValueError("DFA transition guard has unbalanced parentheses.")
		elif character == "&" and depth == 0:
			part = raw_guard[start:index].strip()
			if not part:
				raise ValueError("DFA transition guard contains an empty conjunction term.")
			parts.append(part)
			start = index + 1
	if depth != 0:
		raise ValueError("DFA transition guard has unbalanced parentheses.")
	final_part = str(raw_guard or "")[start:].strip()
	if not final_part:
		raise ValueError("DFA transition guard contains an empty conjunction term.")
	parts.append(final_part)
	return tuple(parts)


def _parse_literal(raw_label: str) -> DFALiteral | None:
	text = str(raw_label or "").strip()
	if not text:
		return None
	if text.lower() in {"true", "false"}:
		return None
	if "|" in text or "&" in text:
		return None
	polarity = "positive"
	for prefix in ("not ", "!", "~"):
		if text.lower().startswith(prefix):
			polarity = "negative"
			text = text[len(prefix) :].strip()
			break
	text = _strip_balanced_parentheses(text)
	if not _SINGLE_ATOM_RE.fullmatch(text):
		return None
	if "(" not in text:
		return DFALiteral(predicate=text, arguments=(), polarity=polarity)
	if not text.endswith(")"):
		return None
	predicate, raw_arguments = text.split("(", 1)
	arguments = tuple(
		argument.strip()
		for argument in raw_arguments[:-1].split(",")
		if argument.strip()
	)
	return DFALiteral(
		predicate=predicate.strip(),
		arguments=arguments,
		polarity=polarity,
	)


def _validate_declared_literal(
	literal: DFALiteral,
	*,
	declared_arities: Mapping[str, int],
) -> None:
	if literal.predicate not in declared_arities:
		raise ValueError(
			"DFA transition references undeclared PDDL predicate or numeric "
			f"resource function {literal.predicate!r}.",
		)
	declared_arity = declared_arities[literal.predicate]
	if declared_arity != len(literal.arguments):
		raise ValueError(
			(
				"DFA transition references PDDL predicate or numeric resource "
				"function "
				f"{literal.predicate}/{declared_arity} with wrong arity "
				f"{len(literal.arguments)}."
			),
		)


def _declared_temporal_goal_arities(domain: PDDLDomain) -> dict[str, int]:
	arities = {
		str(predicate.name): len(tuple(predicate.parameters or ()))
		for predicate in tuple(getattr(domain, "predicates", ()) or ())
	}
	for function in tuple(getattr(domain, "functions", ()) or ()):
		arities[str(function.name)] = len(tuple(function.parameters or ())) + 1
	return arities


def _strip_balanced_parentheses(text: str) -> str:
	current = str(text or "").strip()
	while current.startswith("(") and current.endswith(")") and _outer_parentheses_wrap(current):
		current = current[1:-1].strip()
	return current


def _outer_parentheses_wrap(text: str) -> bool:
	depth = 0
	for index, character in enumerate(text):
		if character == "(":
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0 and index != len(text) - 1:
				return False
			if depth < 0:
				return False
	return depth == 0


def _call(predicate: str, arguments: Sequence[str]) -> str:
	args = tuple(arguments or ())
	return predicate if not args else f"{predicate}({', '.join(args)})"


_SINGLE_ATOM_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*(?:\([^()]*\))?")
