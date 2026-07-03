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
from .dfa_controller import progress_transitions_from_dfa_state
from .lifted_ltlf_goal_schema import LiftedLTLfGoalCase


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

	declared_arities = {
		str(predicate.name): len(tuple(predicate.parameters or ()))
		for predicate in PDDLParser.parse_domain(domain_file).predicates
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
	plans = list(plan_library.plans)
	progress_plans = _temporal_progress_plans(
		goal_name=goal_name,
		dfa_payload=dfa_payload,
		declared_arities=declared_arities,
	)
	plans.extend(progress_plans)
	plans.append(
		AgentSpeakPlan(
			plan_name=f"{goal_name}_accepting",
			trigger=AgentSpeakTrigger(
				event_type="achievement_goal",
				symbol=goal_name,
				arguments=(),
			),
			context=("true",),
			body=(),
			binding_certificate=(
				{
					"synthesis_family": "temporal_goal_dfa_append",
					"role": "accepting_fallback",
				},
			),
		),
	)
	return PlanLibrary(
		domain_name=plan_library.domain_name,
		plans=tuple(plans),
		initial_beliefs=plan_library.initial_beliefs,
		metadata={
			**dict(plan_library.metadata or {}),
			"temporal_goal_append": {
				"goal_name": goal_name,
				"dfa_initial_state": dfa_payload.get("initial_state"),
				"dfa_accepting_states": list(dfa_payload.get("accepting_states") or ()),
				"progress_plan_count": len(progress_plans),
				"requires_external_dfa_state": True,
			},
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
	source_states = tuple(
		dict.fromkeys(
			str(transition.get("source_state") or "").strip()
			for transition in tuple(dfa_payload.get("guarded_transitions") or ())
			if isinstance(transition, Mapping)
			and str(transition.get("source_state") or "").strip()
		),
	)
	progress_transitions: list[dict[str, str]] = []
	for source_state in source_states:
		progress_transitions.extend(
			progress_transitions_from_dfa_state(
				dfa_payload=dfa_payload,
				current_dfa_state=source_state,
			),
		)
	plans: list[AgentSpeakPlan] = []
	for index, transition in enumerate(progress_transitions, start=1):
		literal = _required_progress_literal(transition["raw_label"])
		_validate_declared_literal(literal, declared_arities=declared_arities)
		if literal.polarity == "negative":
			raise ValueError(
				"negative_literal_template_not_supported: Cannot compile negative "
				"DFA progress literal into an atomic achievement subgoal yet: "
				f"{transition['raw_label']!r}."
			)
		plans.append(
			AgentSpeakPlan(
				plan_name=f"{goal_name}_progress_{index}",
				trigger=AgentSpeakTrigger(
					event_type="achievement_goal",
					symbol=goal_name,
					arguments=(),
				),
				context=(f"not {literal.atom}",),
				body=(
					AgentSpeakBodyStep("subgoal", literal.predicate, literal.arguments),
					AgentSpeakBodyStep("subgoal", goal_name, ()),
				),
				binding_certificate=(
					{
						"synthesis_family": "temporal_goal_dfa_append",
						"source_state": transition["source_state"],
						"target_state": transition["target_state"],
						"raw_label": transition["raw_label"],
					},
				),
			),
		)
	return tuple(plans)


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
