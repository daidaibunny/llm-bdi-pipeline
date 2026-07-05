"""
Append query-specific temporal goals to a domain-level atomic ASL library.

The input side is expected to provide a validated LTLf JSON object and a DFA
payload. This module only checks the DFA interface required by the ASL layer and
turns progress transitions into calls to existing atomic predicate modules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary
from utils.symbol_normalizer import SymbolNormalizer
from utils.pddl_parser import PDDLParser

from .lifted_ltlf_goal_schema import LTLfAtomSpec
from .dfa_controller import inspect_progress_requests_from_dfa_state
from .dfa_controller import progress_transitions_from_dfa_state
from .lifted_ltlf_goal_schema import LiftedLTLfGoalCase


_TEMPORAL_STATE_PREDICATE = "tg_state"
_TEMPORAL_WRAPPER_MODE = "query_local_dfa_state_monitor"


@dataclass(frozen=True)
class SingletonLiteralDFADiagnostic:
	"""Validation result for the singleton-literal DFA interface contract."""

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


def validate_singleton_literal_dfa(
	dfa_payload: Mapping[str, Any],
	*,
	allow_true_accepting_self_loops: bool = True,
	declared_arities: Mapping[str, int] | None = None,
	allow_negative_literals: bool = False,
) -> SingletonLiteralDFADiagnostic:
	"""Check that every relevant DFA transition guard is one literal."""

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
		return SingletonLiteralDFADiagnostic(
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
		literal = _parse_literal(raw_label)
		if literal is None:
			errors.append(
				{
					"transition_index": index,
					"source_state": source_state,
					"target_state": target_state,
					"raw_label": raw_label,
					"error_type": "non_singleton_literal_guard",
					"message": "DFA transition guard must contain exactly one literal.",
				},
			)
			continue
		if literal.polarity == "negative" and not allow_negative_literals:
			errors.append(
				{
					"transition_index": index,
					"source_state": source_state,
					"target_state": target_state,
					"raw_label": raw_label,
					"predicate": literal.predicate,
					"error_type": "negative_literal_template_not_supported",
					"message": (
						"Negative DFA transition literals are not supported by the "
						"atomic template compiler yet."
					),
				},
			)
			continue
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
						"DFA transition references a predicate that is not "
						"declared in the PDDL domain."
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
						"DFA transition predicate arity does not match the PDDL "
						"domain declaration."
					),
				},
			)
	return SingletonLiteralDFADiagnostic(valid=not errors, errors=tuple(errors))


def append_temporal_goal_to_library(
	*,
	plan_library: PlanLibrary,
	goal_name: str,
	dfa_payload: Mapping[str, Any],
	domain_file: str | Path,
	allow_true_accepting_self_loops: bool = True,
) -> PlanLibrary:
	"""Append one query-specific temporal goal wrapper to an atomic ASL library."""

	if _has_existing_goal_trigger(plan_library, goal_name):
		raise ValueError(
			"duplicate_temporal_goal: Plan library already contains an "
			f"achievement-goal entry for {goal_name!r}."
		)
	domain = PDDLParser.parse_domain(domain_file)
	declared_arities = {
		str(predicate.name): len(tuple(predicate.parameters or ()))
		for predicate in domain.predicates
	}
	diagnostic = validate_singleton_literal_dfa(
		dfa_payload,
		allow_true_accepting_self_loops=allow_true_accepting_self_loops,
		declared_arities=declared_arities,
		allow_negative_literals=True,
	)
	if not diagnostic.valid:
		first_error = diagnostic.errors[0]
		raise ValueError(
			"DFA payload does not satisfy the singleton-literal transition contract: "
			f"{first_error['error_type']}: {first_error['message']}"
		)
	append_record: dict[str, Any] = {
		"goal_name": goal_name,
		"dfa_initial_state": dfa_payload.get("initial_state"),
		"dfa_accepting_states": list(dfa_payload.get("accepting_states") or ()),
		"wrapper_mode": _TEMPORAL_WRAPPER_MODE,
		"progress_request_diagnostics": _progress_request_diagnostics(
			dfa_payload=dfa_payload,
			domain_key=domain.name,
			domain_file=domain_file,
			declared_arities=declared_arities,
		),
	}
	plans = list(plan_library.plans)
	progress_plans = _temporal_progress_plans(
		goal_name=goal_name,
		dfa_payload=dfa_payload,
		declared_arities=declared_arities,
	)
	append_record["progress_plan_count"] = len(progress_plans)
	progress_state_coverage = _progress_state_coverage(
		goal_name=goal_name,
		dfa_payload=dfa_payload,
		progress_plans=progress_plans,
	)
	append_record["progress_state_coverage"] = progress_state_coverage
	if not progress_state_coverage["valid"]:
		raise ValueError(
			"dfa_progress_state_coverage_error: every DFA state with an "
			"acceptance-progress transition must have at least one generated "
			f"ASL goal plan. Uncovered states: {progress_state_coverage['uncovered_states']}",
		)
	plans.extend(progress_plans)
	accepting_plans = _temporal_accepting_plans(
		goal_name=goal_name,
		dfa_payload=dfa_payload,
	)
	plans.extend(accepting_plans)
	return PlanLibrary(
		domain_name=plan_library.domain_name,
		plans=tuple(plans),
		initial_beliefs=_initial_beliefs_with_temporal_state(
			plan_library=plan_library,
			goal_name=goal_name,
			dfa_payload=dfa_payload,
		),
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

	symbol_map = _lifted_atom_symbol_map(goal_case.atoms)
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
		"symbols": sorted(
			{
				key
				for key in symbol_map
				if key and not key.startswith("not ")
			},
		),
	}
	return payload


def _lifted_atom_symbol_map(atoms: Sequence[LTLfAtomSpec]) -> dict[str, str]:
	normalizer = SymbolNormalizer()
	symbol_map: dict[str, str] = {}
	for atom in tuple(atoms or ()):
		predicate = str(atom.predicate or "").strip()
		arguments = tuple(str(argument).strip() for argument in tuple(atom.args or ()) if str(argument).strip())
		if not predicate:
			continue
		pddl_atom = _call(predicate, arguments)
		candidates = {
			str(atom.symbol or "").strip(),
			_symbol_for(predicate, arguments),
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


def _temporal_progress_plans(
	*,
	goal_name: str,
	dfa_payload: Mapping[str, Any],
	declared_arities: Mapping[str, int],
) -> tuple[AgentSpeakPlan, ...]:
	progress_transitions = _all_progress_transitions(dfa_payload)
	plans: list[AgentSpeakPlan] = []
	for transition in progress_transitions:
		literal = _required_progress_literal(transition["raw_label"])
		_validate_declared_literal(literal, declared_arities=declared_arities)
		if literal.polarity == "negative":
			raise ValueError(
				"negative_literal_template_not_supported: Cannot compile negative "
				"DFA progress literal into an atomic achievement subgoal yet: "
				f"{transition['raw_label']!r}."
			)
		source_state = _required_state_label(transition["source_state"], role="source_state")
		target_state = _required_state_label(transition["target_state"], role="target_state")
		plan_index = len(plans) + 1
		context = (_temporal_state_atom(goal_name, source_state),)
		plans.append(
			AgentSpeakPlan(
				plan_name=f"{goal_name}_progress_{plan_index}",
				trigger=AgentSpeakTrigger(
					event_type="achievement_goal",
					symbol=goal_name,
					arguments=(),
				),
				context=context,
				body=(
					AgentSpeakBodyStep("subgoal", literal.predicate, literal.arguments),
					AgentSpeakBodyStep(
						"belief_deletion",
						_TEMPORAL_STATE_PREDICATE,
						(goal_name, source_state),
					),
					AgentSpeakBodyStep(
						"belief_addition",
						_TEMPORAL_STATE_PREDICATE,
						(goal_name, target_state),
					),
					AgentSpeakBodyStep("subgoal", goal_name, ()),
				),
				binding_certificate=(
					{
						"artifact_family": "temporal_goal_dfa_append",
						"wrapper_mode": _TEMPORAL_WRAPPER_MODE,
						"source_state": source_state,
						"target_state": target_state,
						"raw_label": transition["raw_label"],
						"context": list(context),
						"state_belief": context[0],
					},
				),
			),
		)
	return tuple(plans)


def _temporal_accepting_plans(
	*,
	goal_name: str,
	dfa_payload: Mapping[str, Any],
) -> tuple[AgentSpeakPlan, ...]:
	initial_state = _required_initial_state(dfa_payload)
	accepting_states = tuple(
		str(state).strip()
		for state in tuple(dfa_payload.get("accepting_states") or ())
		if str(state).strip()
	)
	plans: list[AgentSpeakPlan] = []
	for state in accepting_states:
		accepting_state = _required_state_label(state, role="accepting_state")
		context = (_temporal_state_atom(goal_name, accepting_state),)
		plans.append(
			AgentSpeakPlan(
				plan_name=f"{goal_name}_accepting_{len(plans) + 1}",
				trigger=AgentSpeakTrigger(
					event_type="achievement_goal",
					symbol=goal_name,
					arguments=(),
				),
				context=context,
				body=(
					AgentSpeakBodyStep(
						"belief_deletion",
						_TEMPORAL_STATE_PREDICATE,
						(goal_name, accepting_state),
					),
					AgentSpeakBodyStep(
						"belief_addition",
						_TEMPORAL_STATE_PREDICATE,
						(goal_name, initial_state),
					),
				),
				binding_certificate=(
					{
						"artifact_family": "temporal_goal_dfa_append",
						"wrapper_mode": _TEMPORAL_WRAPPER_MODE,
						"role": "accepting_state",
						"accepting_state": accepting_state,
						"reset_state": initial_state,
						"context": list(context),
					},
				),
			),
		)
	return tuple(plans)


def _progress_state_coverage(
	*,
	goal_name: str,
	dfa_payload: Mapping[str, Any],
	progress_plans: Sequence[AgentSpeakPlan],
) -> dict[str, object]:
	"""Report whether every accepting-progress DFA state has a goal plan."""

	progress_transitions = _all_progress_transitions(dfa_payload)
	required_states = tuple(
		sorted(
			{
				str(transition.get("source_state") or "").strip()
				for transition in progress_transitions
				if str(transition.get("source_state") or "").strip()
			},
		),
	)
	covered_states = tuple(
		sorted(
			{
				str(certificate.get("source_state") or "").strip()
				for plan in tuple(progress_plans or ())
				if plan.trigger.event_type == "achievement_goal"
				and plan.trigger.symbol == goal_name
				and _plan_recurses_to_goal(plan, goal_name)
				for certificate in tuple(plan.binding_certificate or ())
				if isinstance(certificate, Mapping)
				and certificate.get("artifact_family") == "temporal_goal_dfa_append"
				and str(certificate.get("source_state") or "").strip()
			},
		),
	)
	uncovered_states = tuple(
		state for state in required_states if state not in set(covered_states)
	)
	progress_transition_count_by_state = {
		state: sum(
			1
			for transition in progress_transitions
			if str(transition.get("source_state") or "").strip() == state
		)
		for state in required_states
	}
	plan_count_by_state = {
		state: sum(
			1
			for plan in tuple(progress_plans or ())
			for certificate in tuple(plan.binding_certificate or ())
			if isinstance(certificate, Mapping)
			and str(certificate.get("source_state") or "").strip() == state
		)
		for state in required_states
	}
	return {
		"valid": not uncovered_states,
		"required_states": list(required_states),
		"covered_states": list(covered_states),
		"uncovered_states": list(uncovered_states),
		"progress_state_count": len(required_states),
		"covered_progress_state_count": len(covered_states),
		"progress_transition_count": len(progress_transitions),
		"progress_transition_count_by_state": progress_transition_count_by_state,
		"plan_count_by_state": plan_count_by_state,
	}


def _plan_recurses_to_goal(plan: AgentSpeakPlan, goal_name: str) -> bool:
	return any(
		step.kind == "subgoal"
		and step.symbol == goal_name
		and not tuple(step.arguments or ())
		for step in tuple(plan.body or ())
	)


def _initial_beliefs_with_temporal_state(
	*,
	plan_library: PlanLibrary,
	goal_name: str,
	dfa_payload: Mapping[str, Any],
) -> tuple[str, ...]:
	return _deduplicate_literals(
		(
			*tuple(plan_library.initial_beliefs or ()),
			_temporal_state_atom(goal_name, _required_initial_state(dfa_payload)),
		),
	)


def _required_initial_state(dfa_payload: Mapping[str, Any]) -> str:
	return _required_state_label(dfa_payload.get("initial_state"), role="initial_state")


def _required_state_label(value: object, *, role: str) -> str:
	state = str(value or "").strip()
	if not state:
		raise ValueError(f"dfa_state_error: DFA payload is missing {role}.")
	return state


def _temporal_state_atom(goal_name: str, state: str) -> str:
	return _call(
		_TEMPORAL_STATE_PREDICATE,
		(str(goal_name or "").strip(), _required_state_label(state, role="state")),
	)


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


def _deduplicate_literals(literals: Sequence[str]) -> tuple[str, ...]:
	return tuple(dict.fromkeys(str(literal).strip() for literal in literals if str(literal).strip()))


def _required_progress_literal(raw_label: str) -> DFALiteral:
	literal = _parse_literal(raw_label)
	if literal is None:
		raise ValueError(f"DFA progress transition is not a singleton literal: {raw_label!r}.")
	return literal


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
			f"DFA transition references undeclared PDDL predicate {literal.predicate!r}.",
		)
	declared_arity = declared_arities[literal.predicate]
	if declared_arity != len(literal.arguments):
		raise ValueError(
			(
				"DFA transition references PDDL predicate "
				f"{literal.predicate}/{declared_arity} with wrong arity "
				f"{len(literal.arguments)}."
			),
		)


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
