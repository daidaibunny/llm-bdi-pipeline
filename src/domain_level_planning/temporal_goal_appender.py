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
from utils.pddl_parser import PDDLDomain
from utils.pddl_parser import PDDLParser

from .lifted_ltlf_goal_schema import LTLfAtomSpec
from .dfa_controller import inspect_progress_requests_from_dfa_state
from .dfa_controller import progress_transitions_from_dfa_state
from .lifted_ltlf_goal_schema import LiftedLTLfGoalCase
from .pddl_support import assert_compilable_pddl_files
from .certified_effects import threat_safe_positive_literal_order
from .certified_effects import preservation_safe_action_only_plan_selection
from .certified_effects import query_local_preservation_alias_plans
from .transition_repair_tree import TransitionRepairLiteral
from .transition_repair_tree import compile_transition_repair_tree


_DFA_GUARD_TRANSITION_WRAPPER_MODE = "dfa_guard_transition_replay"


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
) -> PlanLibrary:
	"""Append one query-specific temporal goal wrapper to an atomic ASL library."""

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
	transition_path = _unique_accepting_progress_path(
		dfa_payload=dfa_payload,
		declared_arities=declared_arities,
	)
	if transition_path is None:
		raise ValueError(
			"nonlinear_temporal_goal_not_supported: current ASL append emits a "
			"sequence of query-local transition helpers and therefore supports only "
			"one progress path from the initial DFA state to an "
			"accepting state. Branching or state-dependent temporal goals require "
			"an external DFA/reward-machine controller."
		)
	progress_plans = _guard_transition_wrapper_plans(
		goal_name=goal_name,
		transition_path=transition_path,
		domain=domain,
		plan_library=plan_library,
	)
	entry_proposition = _query_entry_proposition(goal_name)
	append_record["wrapper_mode"] = _DFA_GUARD_TRANSITION_WRAPPER_MODE
	append_record["transition_controller_strategy"] = (
		"balanced_transition_repair_tree"
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
	append_record["negative_achievement_supported"] = False
	append_record["accepting_plan_count"] = 0
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


def _unique_accepting_progress_path(
	*,
	dfa_payload: Mapping[str, Any],
	declared_arities: Mapping[str, int],
) -> tuple[tuple[tuple[DFALiteral, ...], Mapping[str, str]], ...] | None:
	"""Return the unique accepting-progress path represented by the DFA."""

	progress_transitions = _all_progress_transitions(dfa_payload)
	if not progress_transitions:
		return None
	initial_state = _required_initial_state(dfa_payload)
	accepting_states = frozenset(
		str(state).strip()
		for state in tuple(dfa_payload.get("accepting_states") or ())
		if str(state).strip()
	)
	if not accepting_states:
		return None
	transitions_by_source: dict[str, list[dict[str, str]]] = {}
	for transition in progress_transitions:
		transitions_by_source.setdefault(transition["source_state"], []).append(transition)
	current_state = initial_state
	visited: set[str] = set()
	path: list[tuple[tuple[DFALiteral, ...], Mapping[str, str]]] = []
	while current_state not in accepting_states:
		if current_state in visited:
			return None
		visited.add(current_state)
		outgoing = transitions_by_source.get(current_state) or []
		if len(outgoing) != 1:
			return None
		transition = outgoing[0]
		literals = _parse_guard_literals(transition["raw_label"])
		for literal in literals:
			_validate_declared_literal(literal, declared_arities=declared_arities)
		path.append((literals, transition))
		current_state = transition["target_state"]
	if len(path) != len(progress_transitions):
		return None
	return tuple(path)


def _guard_transition_wrapper_plans(
	*,
	goal_name: str,
	transition_path: Sequence[
		tuple[tuple[DFALiteral, ...], Mapping[str, str]]
	],
	domain: PDDLDomain,
	plan_library: PlanLibrary,
) -> tuple[AgentSpeakPlan, ...]:
	"""Compile every DFA progress edge into one query-local transition helper."""

	entry_proposition = _query_entry_proposition(goal_name)
	transition_names = tuple(
		f"{goal_name}_trans_{index}"
		for index in range(1, len(tuple(transition_path)) + 1)
	)
	plans: list[AgentSpeakPlan] = [
		AgentSpeakPlan(
			plan_name=f"{goal_name}_trans_sequence",
			trigger=AgentSpeakTrigger("achievement_goal", goal_name, ()),
			context=(entry_proposition,),
			body=tuple(
				AgentSpeakBodyStep("subgoal", transition_name, ())
				for transition_name in transition_names
			),
			binding_certificate=(
				{
					"artifact_family": "temporal_goal_dfa_append",
					"wrapper_mode": _DFA_GUARD_TRANSITION_WRAPPER_MODE,
					"wrapper_role": "transition_sequence_entry",
					"query_entry_proposition": entry_proposition,
					"progress_transition_count": len(transition_names),
				},
			),
		),
	]
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
		(
			positive_literals,
			serialization_certificate,
			preservation_alias_plans,
			preservation_helper_by_predicate,
		) = (
			_certified_positive_literal_serialization(
				positive_literals,
				negative_literals=negative_literals,
				plan_library=plan_library,
				domain=domain,
				helper_prefix=transition_name,
			)
		)
		plans.extend(preservation_alias_plans)
		type_contexts = _guard_variable_type_contexts(literals, domain=domain)
		guard_context = (
			entry_proposition,
			*type_contexts,
			*tuple(literal.atom for literal in positive_literals),
			*tuple(f"not {literal.atom}" for literal in negative_literals),
		)
		certificate = {
			"artifact_family": "temporal_goal_dfa_append",
			"wrapper_mode": _DFA_GUARD_TRANSITION_WRAPPER_MODE,
			"query_entry_proposition": entry_proposition,
			"transition_index": transition_index,
			"source_state": str(transition.get("source_state") or ""),
			"target_state": str(transition.get("target_state") or ""),
			"raw_label": str(transition.get("raw_label") or ""),
			"serialization_certificate": serialization_certificate,
		}
		if not positive_literals:
			plans.append(
				AgentSpeakPlan(
					plan_name=f"{transition_name}_done",
					trigger=AgentSpeakTrigger("achievement_goal", transition_name, ()),
					context=guard_context,
					body=(),
					binding_certificate=(
						{**certificate, "wrapper_role": "transition_done"},
					),
				),
			)
			continue
		shared_context = (
			entry_proposition,
			*type_contexts,
			*tuple(f"not {item.atom}" for item in negative_literals),
		)
		repair_literals = tuple(
			TransitionRepairLiteral(
				atom=literal.atom,
				achievement_symbol=preservation_helper_by_predicate.get(
					literal.predicate,
					literal.predicate,
				),
				achievement_arguments=literal.arguments,
			)
			for literal in positive_literals
		)
		tree_compilation = compile_transition_repair_tree(
			transition_symbol=transition_name,
			shared_context=shared_context,
			positive_literals=repair_literals,
			final_guard_context=guard_context,
			certificate=certificate,
		)
		plans.extend(tree_compilation.plans)
	return tuple(plans)


def _certified_positive_literal_serialization(
	literals: Sequence[DFALiteral],
	*,
	negative_literals: Sequence[DFALiteral] = (),
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	helper_prefix: str,
) -> tuple[
	tuple[DFALiteral, ...],
	Mapping[str, object],
	tuple[AgentSpeakPlan, ...],
	Mapping[str, str],
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
	if numeric_literals and len(all_literals) > 1:
		raise ValueError(
			"uncertified_numeric_conjunctive_transition: numeric resource atoms in a "
			"multi-literal DFA guard require numeric effect-preservation certificates.",
		)
	if not literal_tuple:
		return (
			(),
			{
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
			},
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
		)
	literal_signatures = tuple(
		(literal.predicate, literal.arguments) for literal in literal_tuple
	)
	negative_literal_signatures = tuple(
		(literal.predicate, literal.arguments) for literal in negative_literal_tuple
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
				"cyclic_conjunctive_transition_not_certified",
				"negative_guard_not_preserved",
			),
		):
			raise
		selection = preservation_safe_action_only_plan_selection(
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
		return (
			tuple(literal_tuple[index] for index in selection.ordered_indexes),
			certificate_payload,
			aliases,
			helper_by_predicate,
		)
	certificate_payload = certificate.to_dict()
	certificate_payload["negative_guard_literals"] = [
		literal.atom for literal in negative_literal_tuple
	]
	return (
		tuple(literal_tuple[index] for index in ordered_indexes),
		certificate_payload,
		(),
		{},
	)


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
