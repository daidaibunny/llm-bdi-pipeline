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


class ClingoSketchRuleSelector:
	"""Select a minimum-cost rule set satisfying required sketch capabilities."""

	def select(
		self,
		*,
		candidate_rules: Iterable[LiftedPlanRule],
		required_capabilities: Iterable[str],
	) -> ClingoSelectionResult:
		rules = tuple(candidate_rules)
		required = tuple(dict.fromkeys(required_capabilities))
		if not rules:
			raise ValueError("Clingo sketch selection requires at least one candidate rule.")
		if not required:
			raise ValueError("Clingo sketch selection requires at least one capability.")

		program = _build_selection_program(rules, required)
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
	lines.extend(
		(
			"{ select(R) } :- rule(R).",
			":- required(C), not 1 { select(R) : cap(R,C) }.",
			"#minimize { Cost,R : select(R), cost(R,Cost) }.",
			"#show select/1.",
		),
	)
	return "\n".join(lines)


def _atom(value: str) -> str:
	text = re.sub(r"[^A-Za-z0-9_]", "_", str(value or "").strip().lower())
	while "__" in text:
		text = text.replace("__", "_")
	text = text.strip("_") or "item"
	if not text[0].isalpha():
		text = f"r_{text}"
	return text
