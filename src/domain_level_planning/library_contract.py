"""
Domain-level lifted AgentSpeak(L) library contract checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep, AgentSpeakPlan, PlanLibrary

SUPPORTED_ASL_SUBSET = {
	"plan_heads": "PDDL predicate achievement goals or zero-argument +!g only",
	"contexts": (
		"implicit conjunction of atom, not atom, equality, or inequality "
		"context literals only"
	),
	"body_steps": "PDDL primitive action calls and PDDL predicate subgoal calls only",
	"initial_beliefs": "empty for domain-level reusable libraries",
}

EXECUTION_SEMANTICS = {
	"plan_selection": "deterministic_first_applicable_asl_order",
	"context_semantics": (
		"order-independent implicit conjunction over supported context literals; "
		"positive context atoms bind variables before negated context atoms are checked"
	),
	"negation_semantics": (
		"negation-as-absence over the current state, goal descriptor set, "
		"or derived ready-context set"
	),
	"goal_state_semantics": "fixed point: +!g has no applicable unsatisfied-goal plan",
	"primitive_action_semantics": "PDDL STRIPS simulator applies declared actions",
	"primitive_precondition_semantics": (
		"primitive action preconditions are checked at execution time; "
		"violations produce primitive-precondition counterexamples"
	),
}


@dataclass(frozen=True)
class DomainLevelLibraryContractReport:
	"""Validation result for the reusable lifted-library contract."""

	passed: bool
	checked_layers: dict[str, bool]
	violations: tuple[str, ...] = ()
	goal_descriptor_usage: Mapping[str, object] | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"passed": self.passed,
			"checked_layers": dict(self.checked_layers),
			"violations": list(self.violations),
			"supported_asl_subset": dict(SUPPORTED_ASL_SUBSET),
			"execution_semantics": dict(EXECUTION_SEMANTICS),
			"goal_descriptor_usage": dict(self.goal_descriptor_usage or {}),
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
	route_context_arities = _runtime_route_context_arities(plan_library)
	no_initial_beliefs = not tuple(plan_library.initial_beliefs or ())
	if not no_initial_beliefs:
		violations.append("Domain-level libraries must not emit problem-specific initial beliefs.")

	no_synthetic_names = _collect_synthetic_name_violations(plan_library, violations)
	goal_descriptors_read_only = _collect_goal_descriptor_violations(
		plan_library,
		violations,
		declared_predicates=predicate_arities,
		route_context_arities=route_context_arities,
	)
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
		route_context_arities=route_context_arities,
		violations=violations,
	)
	goal_descriptor_usage = _goal_descriptor_usage(
		plan_library,
		declared_predicates=predicate_arities,
		route_context_arities=route_context_arities,
	)
	checked_layers = {
		"no_initial_beliefs": no_initial_beliefs,
		"no_synthetic_names": no_synthetic_names,
		"goal_descriptors_read_only": goal_descriptors_read_only,
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
		goal_descriptor_usage=goal_descriptor_usage,
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


def _collect_goal_descriptor_violations(
	plan_library: PlanLibrary,
	violations: list[str],
	*,
	declared_predicates: Mapping[str, int | None] | None = None,
	route_context_arities: Mapping[str, int | None] | None = None,
) -> bool:
	passed = True
	for belief in tuple(plan_library.initial_beliefs or ()):
		symbol = _atom_symbol(belief)
		if _is_read_only_context_symbol(
			symbol,
			declared_predicates=declared_predicates,
			route_context_arities=route_context_arities,
		):
			passed = False
			violations.append(
				f"Read-only {_read_only_context_label(symbol)} emitted as initial belief: {belief!r}.",
			)
	for plan in tuple(plan_library.plans or ()):
		if _is_read_only_context_symbol(
			plan.trigger.symbol,
			declared_predicates=declared_predicates,
			route_context_arities=route_context_arities,
		):
			passed = False
			violations.append(
				f"Read-only {_read_only_context_label(plan.trigger.symbol)} "
				f"used as plan head: {plan.plan_name!r}.",
			)
		for step in tuple(plan.body or ()):
			if _is_read_only_context_symbol(
				step.symbol,
				declared_predicates=declared_predicates,
				route_context_arities=route_context_arities,
			):
				passed = False
				violations.append(
					(
						f"Read-only {_read_only_context_label(step.symbol)} "
						f"used in body step of plan {plan.plan_name!r}."
					),
			)
	return passed


def _goal_descriptor_usage(
	plan_library: PlanLibrary,
	*,
	declared_predicates: Mapping[str, int | None] | None = None,
	route_context_arities: Mapping[str, int | None] | None = None,
) -> dict[str, object]:
	context_descriptors: list[dict[str, object]] = []
	mutable_locations: list[dict[str, str]] = []
	for belief in tuple(plan_library.initial_beliefs or ()):
		if _is_read_only_context_symbol(
			_atom_symbol(belief),
			declared_predicates=declared_predicates,
			route_context_arities=route_context_arities,
		):
			mutable_locations.append(
				{"location": "initial_belief", "descriptor": str(belief)},
			)
	for plan in tuple(plan_library.plans or ()):
		if _is_read_only_context_symbol(
			plan.trigger.symbol,
			declared_predicates=declared_predicates,
			route_context_arities=route_context_arities,
		):
			mutable_locations.append(
				{"location": "plan_head", "descriptor": plan.trigger.symbol},
			)
		for context in tuple(plan.context or ()):
			for symbol, arguments in _context_atoms(context):
				if not _is_read_only_context_symbol(
					symbol,
					declared_predicates=declared_predicates,
					route_context_arities=route_context_arities,
				):
					continue
				context_descriptors.append(
					{
						"descriptor": _format_atom(symbol, arguments),
						"pddl_predicate": _read_only_context_pddl_predicate(symbol),
						"arguments": list(arguments),
						"plan_name": plan.plan_name,
						"negated": str(context or "").strip().lower().startswith("not "),
					},
				)
		for step in tuple(plan.body or ()):
			if _is_read_only_context_symbol(
				step.symbol,
				declared_predicates=declared_predicates,
				route_context_arities=route_context_arities,
			):
				mutable_locations.append(
					{"location": f"body_step:{step.kind}", "descriptor": step.symbol},
				)
	return {
		"context_descriptors": context_descriptors,
		"mutable_locations": mutable_locations,
		"read_only": not mutable_locations,
	}


def _collect_head_lifting_violations(
	plans: Iterable[AgentSpeakPlan],
	violations: list[str],
) -> bool:
	passed = True
	for plan in tuple(plans or ()):
		if plan.trigger.symbol == "g" and tuple(plan.trigger.arguments or ()):
			passed = False
			violations.append(f"Top-level composer head +!g must not take arguments: {plan.plan_name!r}.")
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
						f"{step.kind!r}; supported kinds are action and subgoal only."
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
			if step.symbol == "g" and not tuple(step.arguments or ()):
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
	route_context_arities: Mapping[str, int | None],
	violations: list[str],
) -> bool:
	if not declared_predicates and not declared_actions:
		return True
	passed = True
	for plan in tuple(plans or ()):
		if plan.trigger.symbol != "g" and plan.trigger.symbol not in declared_predicates:
			passed = False
			violations.append(
				(
					f"Plan {plan.plan_name!r} uses undeclared PDDL predicate "
					f"{plan.trigger.symbol!r} as plan head."
				),
			)
		elif plan.trigger.symbol != "g" and not _arity_matches(
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
			for symbol, arguments in _context_atoms(context):
				if symbol == "=":
					continue
				if symbol in declared_predicates:
					predicate = symbol
				elif _is_read_only_context_symbol(
					symbol,
					declared_predicates=declared_predicates,
					route_context_arities=route_context_arities,
				):
					if symbol in route_context_arities:
						if not _arity_matches(route_context_arities[symbol], len(arguments)):
							passed = False
							violations.append(
								(
									f"Plan {plan.plan_name!r} uses route context "
									f"{_schema_signature(symbol, route_context_arities[symbol])} "
									f"with wrong arity {len(arguments)} in context {context!r}."
								),
							)
						continue
					predicate = _read_only_context_pddl_predicate(symbol)
				else:
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
				if step.symbol == "g":
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


def _is_read_only_context_symbol(
	symbol: str,
	*,
	declared_predicates: Mapping[str, int | None] | None = None,
	route_context_arities: Mapping[str, int | None] | None = None,
) -> bool:
	text = str(symbol or "").strip()
	if text in dict(route_context_arities or {}):
		return True
	if text.startswith("goal_"):
		return True
	if not text.startswith("ready_"):
		return False
	declared = dict(declared_predicates or {})
	if text in declared:
		return False
	if not declared:
		return True
	return text[len("ready_") :] in declared


def _read_only_context_label(symbol: str) -> str:
	text = str(symbol or "").strip()
	if text.startswith("route_step_"):
		return "route-step context"
	if text.startswith("ready_"):
		return "ready context"
	return "goal descriptor"


def _read_only_context_pddl_predicate(symbol: str) -> str:
	text = str(symbol or "").strip()
	if text.startswith("goal_"):
		return text[len("goal_") :]
	if text.startswith("ready_"):
		return text[len("ready_") :]
	return text


def _runtime_route_context_arities(plan_library: PlanLibrary) -> dict[str, int]:
	arities: dict[str, int] = {}
	for feature in tuple(plan_library.metadata.get("runtime_route_features") or ()):
		if not isinstance(feature, Mapping):
			continue
		symbol = str(feature.get("symbol") or "").strip()
		if not symbol:
			continue
		arities[symbol] = len(tuple(feature.get("context_arguments") or ()))
	return arities


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
	return "achieve_" in text or "transition_" in text or "dfa_state" in text


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


def _format_atom(symbol: str, arguments: Sequence[str]) -> str:
	return symbol if not tuple(arguments or ()) else f"{symbol}({', '.join(arguments)})"


def _atom_symbol(atom: str) -> str:
	text = str(atom or "").strip()
	if "(" not in text:
		return text
	return text.split("(", 1)[0].strip()


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
