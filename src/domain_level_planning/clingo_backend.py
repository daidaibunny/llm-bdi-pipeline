"""
Clingo-backed selection for lifted modular-sketch rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import clingo

from .models import LiftedPlanRule


@dataclass(frozen=True)
class ClingoSelectionResult:
	"""Selected sketch rules and the corresponding Clingo optimization value."""

	rules: tuple[LiftedPlanRule, ...]
	cost: int
	selected_rule_names: tuple[str, ...]


@dataclass(frozen=True)
class ClingoRequiredRuleGroup:
	"""A hard ASP constraint requiring at least one named candidate rule."""

	name: str
	rule_names: tuple[str, ...]


class ClingoSketchRuleSelector:
	"""Select a minimum-cost rule set satisfying required sketch capabilities."""

	def select(
		self,
		*,
		candidate_rules: Iterable[LiftedPlanRule],
		required_capabilities: Iterable[str],
		required_rule_names: Iterable[str] = (),
		forbidden_rule_names: Iterable[str] = (),
		required_rule_groups: Iterable[ClingoRequiredRuleGroup] = (),
	) -> ClingoSelectionResult:
		rules = tuple(candidate_rules)
		required = tuple(dict.fromkeys(required_capabilities))
		if not rules:
			raise ValueError("Clingo sketch selection requires at least one candidate rule.")
		if not required:
			raise ValueError("Clingo sketch selection requires at least one capability.")

		required_rule_atoms = _validate_rule_names(
			rules,
			required_rule_names,
			label="required",
		)
		forbidden_rule_atoms = _validate_rule_names(
			rules,
			forbidden_rule_names,
			label="forbidden",
		)
		conflicts = tuple(sorted(set(required_rule_atoms).intersection(forbidden_rule_atoms)))
		if conflicts:
			raise ValueError(
				"Clingo sketch selection received conflicting required and forbidden "
				f"rules: {conflicts}.",
			)
		required_groups = _validate_required_rule_groups(rules, required_rule_groups)

		program = _build_selection_program(
			rules,
			required,
			required_rule_atoms=required_rule_atoms,
			forbidden_rule_atoms=forbidden_rule_atoms,
			required_rule_groups=required_groups,
		)
		control = clingo.Control(["--models=0"])
		control.add("base", [], program)
		control.ground([("base", [])])
		selected_names: tuple[str, ...] | None = None
		optimal_cost = 0
		with control.solve(yield_=True) as handle:
			for model in handle:
				selected_names = tuple(
					symbol.arguments[0].name
					for symbol in model.symbols(shown=True)
					if symbol.name == "select" and symbol.arguments
				)
				cost_values = tuple(model.cost or ())
				optimal_cost = int(cost_values[0]) if cost_values else 0
			result = handle.get()
		if not result.satisfiable or selected_names is None:
			raise RuntimeError("Clingo could not select a satisfying modular-sketch library.")

		selected = set(selected_names)
		selected_rules = tuple(rule for rule in rules if _atom(rule.name) in selected)
		if len(selected_rules) != len(selected):
			raise RuntimeError("Clingo selected a rule that was not present in the candidates.")
		return ClingoSelectionResult(
			rules=selected_rules,
			cost=optimal_cost,
			selected_rule_names=tuple(rule.name for rule in selected_rules),
		)


def _build_selection_program(
	rules: tuple[LiftedPlanRule, ...],
	required_capabilities: tuple[str, ...],
	*,
	required_rule_atoms: tuple[str, ...] = (),
	forbidden_rule_atoms: tuple[str, ...] = (),
	required_rule_groups: tuple[tuple[str, tuple[str, ...]], ...] = (),
) -> str:
	lines: list[str] = []
	for rule in rules:
		rule_atom = _atom(rule.name)
		lines.append(f"rule({rule_atom}).")
		lines.append(f"cost({rule_atom},{int(rule.cost)}).")
		for capability in rule.capabilities:
			lines.append(f"cap({rule_atom},{_atom(capability)}).")
	for capability in required_capabilities:
		lines.append(f"required({_atom(capability)}).")
	for rule_atom in required_rule_atoms:
		lines.append(f"required_rule({rule_atom}).")
	for rule_atom in forbidden_rule_atoms:
		lines.append(f"forbidden_rule({rule_atom}).")
	for group_name, rule_atoms in required_rule_groups:
		lines.append(f"required_group({group_name}).")
		for rule_atom in rule_atoms:
			lines.append(f"group_rule({group_name},{rule_atom}).")
	lines.append("{ select(R) } :- rule(R).")
	lines.append(":- required(C), not 1 { select(R) : cap(R,C) }.")
	if required_rule_atoms:
		lines.append(":- required_rule(R), not select(R).")
	if forbidden_rule_atoms:
		lines.append(":- forbidden_rule(R), select(R).")
	if required_rule_groups:
		lines.append(":- required_group(G), not 1 { select(R) : group_rule(G,R) }.")
	lines.append("#minimize { Cost,R : select(R), cost(R,Cost) }.")
	lines.append("#show select/1.")
	return "\n".join(lines)


def _validate_rule_names(
	rules: tuple[LiftedPlanRule, ...],
	rule_names: Iterable[str],
	*,
	label: str,
) -> tuple[str, ...]:
	rule_atoms = {_atom(rule.name) for rule in rules}
	normalized = tuple(dict.fromkeys(_atom(rule_name) for rule_name in tuple(rule_names or ())))
	missing = tuple(rule_atom for rule_atom in normalized if rule_atom not in rule_atoms)
	if missing:
		raise ValueError(
			f"Clingo sketch selection received unknown {label} rules: {missing}.",
		)
	return normalized


def _validate_required_rule_groups(
	rules: tuple[LiftedPlanRule, ...],
	required_rule_groups: Iterable[ClingoRequiredRuleGroup],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
	rule_atoms = {_atom(rule.name) for rule in rules}
	groups: list[tuple[str, tuple[str, ...]]] = []
	for group in tuple(required_rule_groups or ()):
		group_name = _atom(group.name)
		member_atoms = tuple(dict.fromkeys(_atom(rule_name) for rule_name in group.rule_names))
		if not member_atoms:
			raise ValueError(
				f"Required rule group {group.name!r} does not contain any candidate rules.",
			)
		missing = tuple(rule_atom for rule_atom in member_atoms if rule_atom not in rule_atoms)
		if missing:
			raise ValueError(
				f"Required rule group {group.name!r} contains unknown rules: {missing}.",
			)
		groups.append((group_name, member_atoms))
	return tuple(groups)


def _atom(value: str) -> str:
	text = re.sub(r"[^A-Za-z0-9_]", "_", str(value or "").strip().lower())
	while "__" in text:
		text = text.replace("__", "_")
	text = text.strip("_") or "item"
	if not text[0].isalpha():
		text = f"r_{text}"
	return text
