"""
Domain-level lifted AgentSpeak(L) library contract checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from plan_library.models import AgentSpeakPlan, PlanLibrary

SUPPORTED_ASL_SUBSET = {
	"plan_heads": "PDDL predicate achievement goals or query-specific +!g_* temporal wrappers",
	"contexts": (
		"implicit conjunction of atom, not atom, equality, or inequality "
		"context literals only; reserved obj_tp(Variable, Type) sort "
		"contexts may appear as compiler metadata"
	),
	"body_steps": (
		"PDDL primitive action calls, PDDL predicate subgoal calls, and "
		"query-specific +!g_* wrapper subgoal calls"
	),
	"initial_beliefs": "empty except zero-arity query entry propositions",
}

EXECUTION_SEMANTICS = {
	"plan_selection": "deterministic_first_applicable_asl_order",
	"context_semantics": (
		"order-independent implicit conjunction over supported context literals; "
		"positive context atoms bind variables before negated context atoms are checked"
	),
	"negation_semantics": (
		"negation-as-absence over the current state"
	),
	"temporal_state_semantics": (
		"linear query wrappers execute certified singleton-literal subgoals in "
		"stored order; branching DFA goals require an external controller"
	),
	"primitive_action_semantics": "PDDL STRIPS simulator applies declared actions",
	"primitive_precondition_semantics": (
		"primitive action preconditions are checked at execution time; "
		"violations produce validation diagnostics"
	),
}


@dataclass(frozen=True)
class DomainLevelLibraryContractReport:
	"""Validation result for the reusable lifted-library contract."""

	passed: bool
	checked_layers: dict[str, bool]
	violations: tuple[str, ...] = ()

	def to_dict(self) -> dict[str, object]:
		return {
			"passed": self.passed,
			"checked_layers": dict(self.checked_layers),
			"violations": list(self.violations),
			"supported_asl_subset": dict(SUPPORTED_ASL_SUBSET),
			"execution_semantics": dict(EXECUTION_SEMANTICS),
		}


def audit_domain_level_library_contract(
	plan_library: PlanLibrary,
	*,
	declared_predicates: Sequence[object] = (),
	declared_actions: Sequence[object] = (),
) -> DomainLevelLibraryContractReport:
	"""Check that a generated library stays domain-level, lifted, and clean."""

	violations: list[str] = []
	plans = tuple(plan_library.plans or ())
	predicate_arities = _declared_arities(declared_predicates)
	action_arities = _declared_arities(declared_actions)
	initial_beliefs_scoped = _initial_beliefs_are_query_entries(plan_library)
	if not initial_beliefs_scoped:
		violations.append(
			"Initial beliefs must be empty or zero-arity query entry propositions.",
		)

	no_synthetic_names = _collect_synthetic_name_violations(plan_library, violations)
	plan_head_subset = _collect_plan_head_subset_violations(plans, violations)
	lifted_heads = _collect_head_lifting_violations(plans, violations)
	body_step_subset = _collect_body_step_subset_violations(plans, violations)
	lifted_body_calls = _collect_body_lifting_violations(plans, violations)
	context_subset = _collect_context_subset_violations(plans, violations)
	lifted_contexts = _collect_context_lifting_violations(plans, violations)
	variable_binding_safety = _collect_variable_binding_violations(plans, violations)
	declared_pddl_symbols = _collect_declared_pddl_symbol_violations(
		plans,
		declared_predicates=predicate_arities,
		declared_actions=action_arities,
		violations=violations,
	)
	checked_layers = {
		"initial_beliefs_scoped": initial_beliefs_scoped,
		"no_synthetic_names": no_synthetic_names,
		"plan_head_subset": plan_head_subset,
		"body_step_subset": body_step_subset,
		"context_subset": context_subset,
		"declared_pddl_symbols": declared_pddl_symbols,
		"lifted_plan_heads": lifted_heads,
		"lifted_body_calls": lifted_body_calls,
		"lifted_contexts": lifted_contexts,
		"variable_binding_safety": variable_binding_safety,
	}
	return DomainLevelLibraryContractReport(
		passed=all(checked_layers.values()),
		checked_layers=checked_layers,
		violations=tuple(dict.fromkeys(violations)),
	)


def _collect_plan_head_subset_violations(
	plans: Iterable[AgentSpeakPlan],
	violations: list[str],
) -> bool:
	passed = True
	for plan in tuple(plans or ()):
		if str(plan.trigger.event_type or "").strip() == "achievement_goal":
			continue
		passed = False
		violations.append(
			(
				f"Plan {plan.plan_name!r} uses unsupported plan trigger kind "
				f"{plan.trigger.event_type!r}; supported plan heads are achievement goals only."
			),
		)
	return passed


def _collect_synthetic_name_violations(
	plan_library: PlanLibrary,
	violations: list[str],
) -> bool:
	passed = True
	for label, value in _library_strings(plan_library):
		if _contains_synthetic_name(value):
			passed = False
			violations.append(f"Synthetic name appears in {label}: {value!r}.")
	return passed


def _collect_head_lifting_violations(
	plans: Iterable[AgentSpeakPlan],
	violations: list[str],
) -> bool:
	passed = True
	for plan in tuple(plans or ()):
		if _is_query_wrapper_symbol(plan.trigger.symbol) and tuple(plan.trigger.arguments or ()):
			passed = False
			violations.append(
				(
					f"Query temporal wrapper head +!{plan.trigger.symbol} "
					f"must not take arguments: {plan.plan_name!r}."
				),
			)
		for argument in tuple(plan.trigger.arguments or ()):
			if not _is_lifted_variable(argument):
				passed = False
				violations.append(
					f"Plan head contains grounded argument {argument!r} in {plan.plan_name!r}.",
				)
	return passed


def _collect_body_step_subset_violations(
	plans: Iterable[AgentSpeakPlan],
	violations: list[str],
) -> bool:
	passed = True
	allowed_kinds = {"action", "primitive_action", "subgoal"}
	for plan in tuple(plans or ()):
		for step in tuple(plan.body or ()):
			if step.kind not in allowed_kinds:
				passed = False
				violations.append(
					(
						f"Plan {plan.plan_name!r} contains unsupported body step kind "
						f"{step.kind!r}; supported kinds are action, subgoal, and "
						"query-specific +!g_* wrapper subgoals only."
					),
				)
	return passed


def _collect_body_lifting_violations(
	plans: Iterable[AgentSpeakPlan],
	violations: list[str],
) -> bool:
	passed = True
	for plan in tuple(plans or ()):
		for step in tuple(plan.body or ()):
			if _is_query_wrapper_symbol(step.symbol) and not tuple(step.arguments or ()):
				continue
			for argument in tuple(step.arguments or ()):
				if not _is_lifted_variable(argument):
					passed = False
					violations.append(
						f"Body step {step.symbol!r} contains grounded argument "
						f"{argument!r} in {plan.plan_name!r}.",
					)
	return passed


def _collect_context_subset_violations(
	plans: Iterable[AgentSpeakPlan],
	violations: list[str],
) -> bool:
	passed = True
	for plan in tuple(plans or ()):
		for context in tuple(plan.context or ()):
			if _is_supported_context_literal(context):
				continue
			passed = False
			violations.append(
				(
					f"Plan {plan.plan_name!r} contains unsupported context expression "
					f"{context!r}; supported contexts are atom or not atom literals only."
				),
			)
	return passed


def _collect_context_lifting_violations(
	plans: Iterable[AgentSpeakPlan],
	violations: list[str],
) -> bool:
	passed = True
	for plan in tuple(plans or ()):
		for context in tuple(plan.context or ()):
			for atom, arguments in _context_atoms(context):
				if atom == _OBJECT_TYPE_CONTEXT_PREDICATE:
					if _obj_tp_context_is_lifted(arguments):
						continue
					passed = False
					violations.append(
						(
							f"Reserved object type context {context!r} in "
							f"{plan.plan_name!r} must have shape "
							"obj_tp(Variable, type_constant)."
						),
					)
					continue
				for argument in arguments:
					if not _is_lifted_variable(argument):
						passed = False
						violations.append(
							f"Context atom {atom!r} contains grounded argument "
							f"{argument!r} in {plan.plan_name!r}.",
						)
	return passed


def _collect_variable_binding_violations(
	plans: Iterable[AgentSpeakPlan],
	violations: list[str],
) -> bool:
	"""Require every body variable to be bound by the head or positive context."""

	passed = True
	for plan in tuple(plans or ()):
		bound_variables = {
			argument
			for argument in tuple(plan.trigger.arguments or ())
			if _is_lifted_variable(argument)
		}
		for context in tuple(plan.context or ()):
			if str(context or "").strip().lower().startswith("not "):
				continue
			for _symbol, arguments in _context_atoms(context):
				bound_variables.update(
					argument
					for argument in arguments
					if _is_lifted_variable(argument)
				)
		for step in tuple(plan.body or ()):
			if _is_query_wrapper_symbol(plan.trigger.symbol):
				continue
			for argument in tuple(step.arguments or ()):
				if not _is_lifted_variable(argument):
					continue
				if argument in bound_variables:
					continue
				passed = False
				violations.append(
					(
						f"Body step {step.symbol!r} contains unbound variable "
						f"{argument!r} in {plan.plan_name!r}; variables must be "
						"bound by the plan head or positive context literals."
					),
				)
	return passed


def _collect_declared_pddl_symbol_violations(
	plans: Iterable[AgentSpeakPlan],
	*,
	declared_predicates: Mapping[str, int | None],
	declared_actions: Mapping[str, int | None],
	violations: list[str],
) -> bool:
	if not declared_predicates and not declared_actions:
		return True
	passed = True
	for plan in tuple(plans or ()):
		if (
			not _is_query_wrapper_symbol(plan.trigger.symbol)
			and plan.trigger.symbol not in declared_predicates
		):
			passed = False
			violations.append(
				(
					f"Plan {plan.plan_name!r} uses undeclared PDDL predicate "
					f"{plan.trigger.symbol!r} as plan head."
				),
			)
		elif not _is_query_wrapper_symbol(plan.trigger.symbol) and not _arity_matches(
			declared_predicates[plan.trigger.symbol],
			len(tuple(plan.trigger.arguments or ())),
		):
			passed = False
			violations.append(
				(
					f"Plan {plan.plan_name!r} uses PDDL predicate "
					f"{_schema_signature(plan.trigger.symbol, declared_predicates[plan.trigger.symbol])} "
					f"with wrong arity {len(tuple(plan.trigger.arguments or ()))} "
					"as plan head."
				),
			)
		for context in tuple(plan.context or ()):
			if (
				_is_query_wrapper_symbol(plan.trigger.symbol)
				and context == _query_entry_proposition(plan.trigger.symbol)
			):
				continue
			for symbol, arguments in _context_atoms(context):
				if symbol == "=":
					continue
				if symbol == _OBJECT_TYPE_CONTEXT_PREDICATE:
					if len(arguments) != 2:
						passed = False
						violations.append(
							(
								f"Plan {plan.plan_name!r} uses reserved context "
								f"{context!r} with wrong arity {len(arguments)}."
							),
						)
					continue
				predicate = symbol
				if predicate not in declared_predicates:
					passed = False
					violations.append(
						(
							f"Plan {plan.plan_name!r} uses undeclared PDDL predicate "
							f"{predicate!r} in context {context!r}."
						),
					)
				elif not _arity_matches(declared_predicates[predicate], len(arguments)):
					passed = False
					violations.append(
						(
							f"Plan {plan.plan_name!r} uses PDDL predicate "
							f"{_schema_signature(predicate, declared_predicates[predicate])} "
							f"with wrong arity {len(arguments)} in context {context!r}."
						),
					)
		for step in tuple(plan.body or ()):
			if step.kind == "subgoal":
				if _is_query_wrapper_symbol(step.symbol):
					continue
				if step.symbol not in declared_predicates:
					passed = False
					violations.append(
						(
							f"Plan {plan.plan_name!r} uses undeclared PDDL predicate "
							f"{step.symbol!r} as body subgoal."
						),
					)
				elif not _arity_matches(
					declared_predicates[step.symbol],
					len(tuple(step.arguments or ())),
				):
					passed = False
					violations.append(
						(
							f"Plan {plan.plan_name!r} uses PDDL predicate "
							f"{_schema_signature(step.symbol, declared_predicates[step.symbol])} "
							f"with wrong arity {len(tuple(step.arguments or ()))} "
							"as body subgoal."
						),
					)
				continue
			if step.kind in {"action", "primitive_action"}:
				if step.symbol not in declared_actions:
					passed = False
					violations.append(
						(
							f"Plan {plan.plan_name!r} uses undeclared PDDL action "
							f"{step.symbol!r}."
						),
					)
				elif not _arity_matches(
					declared_actions[step.symbol],
					len(tuple(step.arguments or ())),
				):
					passed = False
					violations.append(
						(
							f"Plan {plan.plan_name!r} uses PDDL action "
							f"{_schema_signature(step.symbol, declared_actions[step.symbol])} "
							f"with wrong arity {len(tuple(step.arguments or ()))}."
						),
					)
	return passed


def _library_strings(plan_library: PlanLibrary) -> Iterable[tuple[str, str]]:
	for belief in tuple(plan_library.initial_beliefs or ()):
		yield "initial belief", str(belief)
	for plan in tuple(plan_library.plans or ()):
		yield "plan name", str(plan.plan_name)
		yield "plan head", str(plan.trigger.symbol)
		for context in tuple(plan.context or ()):
			yield f"context in {plan.plan_name}", str(context)
		for step in tuple(plan.body or ()):
			yield f"body step in {plan.plan_name}", str(step.symbol)


def _contains_synthetic_name(value: str) -> bool:
	text = str(value or "").strip().lower()
	return (
		"achieve_" in text
		or "transition_" in text
		or "dfa_state" in text
		or "tg_state" in text
	)


def _is_query_wrapper_symbol(symbol: str) -> bool:
	return bool(re.fullmatch(r"g_[A-Za-z0-9_]+", str(symbol or "").strip()))


def _initial_beliefs_are_query_entries(plan_library: PlanLibrary) -> bool:
	entries = {
		_query_entry_proposition(plan.trigger.symbol)
		for plan in tuple(plan_library.plans or ())
		if _is_query_wrapper_symbol(plan.trigger.symbol)
	}
	return all(
		str(belief or "").strip() in entries
		for belief in tuple(plan_library.initial_beliefs or ())
	)


def _query_entry_proposition(goal_name: str) -> str:
	text = str(goal_name or "").strip()
	if text.startswith("g_") and len(text) > 2:
		return text[2:]
	return f"{text}_entry" if text else "query_entry"


def _context_atoms(context: str) -> Iterable[tuple[str, tuple[str, ...]]]:
	text = str(context or "").strip()
	if text.lower().startswith("not "):
		text = text[4:].strip()
	if not text or text.lower() == "true":
		return
	if "(" not in text and re.fullmatch(_PDDL_SYMBOL_PATTERN, text):
		yield text, ()
		return
	if text.startswith("=") and text.endswith(")"):
		arguments = tuple(
			argument.strip()
			for argument in text[2:-1].split(",")
			if argument.strip()
		)
		yield "=", arguments
		return
	for match in re.finditer(
		rf"(?<![A-Za-z0-9_-])({_PDDL_SYMBOL_PATTERN})\s*\(([^()]*)\)",
		context,
	):
		symbol = match.group(1)
		arguments = tuple(
			argument.strip()
			for argument in match.group(2).split(",")
			if argument.strip()
		)
		yield symbol, arguments


def _is_supported_context_literal(context: str) -> bool:
	text = str(context or "").strip()
	if not text or text.lower() == "true":
		return True
	if any(operator in text for operator in ("|", "&", "==", "!=", "\\==")):
		return False
	if text.lower().startswith("not "):
		text = text[4:].strip()
		if not text:
			return False
	return _is_atom_literal(text)


def _is_atom_literal(text: str) -> bool:
	if "(" not in text:
		return bool(re.fullmatch(_PDDL_SYMBOL_PATTERN, text))
	if text.startswith("="):
		return bool(re.fullmatch(r"=\s*\(\s*[^()]+,\s*[^()]+\s*\)", text))
	return bool(
		re.fullmatch(
			rf"{_PDDL_SYMBOL_PATTERN}\s*\(\s*[^()]*\s*\)",
			text,
		),
	)


def _is_lifted_variable(argument: str) -> bool:
	text = str(argument or "").strip()
	if ":" in text:
		text = text.split(":", 1)[0].strip()
	return bool(text) and text[0].isupper()


def _obj_tp_context_is_lifted(arguments: Sequence[str]) -> bool:
	if len(tuple(arguments or ())) != 2:
		return False
	variable, type_name = tuple(arguments)
	return _is_lifted_variable(variable) and _is_type_constant(type_name)


def _is_type_constant(argument: str) -> bool:
	text = str(argument or "").strip()
	return bool(re.fullmatch(_PDDL_SYMBOL_PATTERN, text)) and not _is_lifted_variable(text)


def _declared_arities(items: Sequence[object] | Mapping[str, int]) -> dict[str, int | None]:
	if isinstance(items, Mapping):
		return {
			str(name).strip(): int(arity)
			for name, arity in items.items()
			if str(name).strip()
		}
	arities: dict[str, int | None] = {}
	for item in tuple(items or ()):
		name = str(getattr(item, "name", item) or "").strip()
		if not name:
			continue
		parameters = getattr(item, "parameters", None)
		arities[name] = len(tuple(parameters or ())) if parameters is not None else None
	return arities


def _arity_matches(expected: int | None, observed: int) -> bool:
	return expected is None or expected == observed


def _schema_signature(symbol: str, arity: int | None) -> str:
	return f"{symbol}/{arity}" if arity is not None else symbol


_PDDL_SYMBOL_PATTERN = r"[A-Za-z_][A-Za-z0-9_-]*"
_OBJECT_TYPE_CONTEXT_PREDICATE = "obj_tp"
