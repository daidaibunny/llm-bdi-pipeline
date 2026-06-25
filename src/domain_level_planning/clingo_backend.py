"""
Clingo-backed selection for lifted modular-sketch rules.
"""

from __future__ import annotations

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

		rule_ids = tuple(f"r{index}" for index, _rule in enumerate(rules))
		capability_ids = _capability_ids(rules, required)
		required_rule_atoms = _validate_rule_names(
			rules,
			required_rule_names,
			label="required",
			rule_ids=rule_ids,
		)
		forbidden_rule_atoms = _validate_rule_names(
			rules,
			forbidden_rule_names,
			label="forbidden",
			rule_ids=rule_ids,
		)
		conflicts = tuple(sorted(set(required_rule_atoms).intersection(forbidden_rule_atoms)))
		if conflicts:
			raise ValueError(
				"Clingo sketch selection received conflicting required and forbidden "
				f"rules: {conflicts}.",
			)
		required_groups = _validate_required_rule_groups(
			rules,
			required_rule_groups,
			rule_ids=rule_ids,
		)

		program = _build_selection_program(
			rules,
			required,
			rule_ids=rule_ids,
			capability_ids=capability_ids,
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
		selected_rules = tuple(
			rule for index, rule in enumerate(rules) if rule_ids[index] in selected
		)
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
	rule_ids: tuple[str, ...],
	capability_ids: dict[str, str],
	required_rule_atoms: tuple[str, ...] = (),
	forbidden_rule_atoms: tuple[str, ...] = (),
	required_rule_groups: tuple[tuple[str, tuple[str, ...]], ...] = (),
) -> str:
	lines: list[str] = []
	for index, rule in enumerate(rules):
		rule_atom = rule_ids[index]
		lines.append(f"rule({rule_atom}).")
		lines.append(f"cost({rule_atom},{int(rule.cost)}).")
		for capability in rule.capabilities:
			lines.append(f"cap({rule_atom},{capability_ids[capability]}).")
	for capability in required_capabilities:
		lines.append(f"required({capability_ids[capability]}).")
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
	rule_ids: tuple[str, ...],
) -> tuple[str, ...]:
	rule_id_set = set(rule_ids)
	normalized_rule_ids: list[str] = []
	missing_names: list[str] = []
	for rule_name in tuple(rule_names or ()):
		matching_rule_ids = _rule_ids_for_name(
			rules=rules,
			rule_ids=rule_ids,
			rule_name=str(rule_name),
		)
		if not matching_rule_ids:
			missing_names.append(str(rule_name))
			continue
		normalized_rule_ids.extend(matching_rule_ids)
	normalized = tuple(dict.fromkeys(normalized_rule_ids))
	if missing_names:
		raise ValueError(
			f"Clingo sketch selection received unknown {label} rules: "
			f"{tuple(dict.fromkeys(missing_names))}.",
		)
	missing = tuple(rule_id for rule_id in normalized if rule_id not in rule_id_set)
	if missing:
		raise ValueError(
			f"Clingo sketch selection received unknown {label} rules: {missing}.",
		)
	return normalized


def _validate_required_rule_groups(
	rules: tuple[LiftedPlanRule, ...],
	required_rule_groups: Iterable[ClingoRequiredRuleGroup],
	*,
	rule_ids: tuple[str, ...],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
	rule_id_set = set(rule_ids)
	groups: list[tuple[str, tuple[str, ...]]] = []
	for index, group in enumerate(tuple(required_rule_groups or ())):
		group_name = f"g{index}"
		missing_names: list[str] = []
		member_rule_ids: list[str] = []
		for rule_name in group.rule_names:
			matching_rule_ids = _rule_ids_for_name(
				rules=rules,
				rule_ids=rule_ids,
				rule_name=str(rule_name),
			)
			if not matching_rule_ids:
				missing_names.append(str(rule_name))
				continue
			member_rule_ids.extend(matching_rule_ids)
		if missing_names:
			raise ValueError(
				f"Required rule group {group.name!r} contains unknown rules: "
				f"{tuple(dict.fromkeys(missing_names))}.",
			)
		member_atoms = tuple(
			dict.fromkeys(member_rule_ids),
		)
		if not member_atoms:
			raise ValueError(
				f"Required rule group {group.name!r} does not contain any candidate rules.",
			)
		missing = tuple(rule_id for rule_id in member_atoms if rule_id not in rule_id_set)
		if missing:
			raise ValueError(
				f"Required rule group {group.name!r} contains unknown rules: {missing}.",
			)
		groups.append((group_name, member_atoms))
	return tuple(groups)


def _rule_ids_for_name(
	*,
	rules: tuple[LiftedPlanRule, ...],
	rule_ids: tuple[str, ...],
	rule_name: str,
) -> tuple[str, ...]:
	return tuple(
		rule_ids[index]
		for index, rule in enumerate(rules)
		if rule.name == rule_name
	)


def _capability_ids(
	rules: tuple[LiftedPlanRule, ...],
	required_capabilities: tuple[str, ...],
) -> dict[str, str]:
	capabilities = tuple(
		dict.fromkeys(
			tuple(required_capabilities)
			+ tuple(
				capability
				for rule in rules
				for capability in tuple(rule.capabilities or ())
			),
		),
	)
	return {
		capability: f"c{index}"
		for index, capability in enumerate(capabilities)
	}
