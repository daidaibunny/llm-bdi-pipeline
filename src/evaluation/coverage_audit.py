"""Post-hoc reporting; unknown outcomes remain in every declared denominator."""

from __future__ import annotations

from evaluation.execution_coverage import Call, UnsupportedModel
from utils.pddl_parser import PDDLProblem


def metric_bounds(counts: dict[str, int]) -> dict[str, float] | None:
	"""Logical bounds, not sampling confidence intervals; empty scopes are N/A."""
	if any(counts[key] < 0 for key in ("pass", "fail", "unknown", "total")):
		raise ValueError("Negative metric count")
	if sum(counts[key] for key in ("pass", "fail", "unknown")) != counts["total"]:
		raise ValueError("Metric counts do not sum to the denominator")
	if counts["total"] == 0:
		return None
	return {"lower": counts["pass"] / counts["total"],
		"upper": (counts["pass"] + counts["unknown"]) / counts["total"]}


def problem_targets(problem: PDDLProblem) -> tuple[Call, ...]:
	"""The fixed atomic-goal population, not a conjunction-success surrogate."""
	targets = set()
	for fact in problem.goal_facts:
		if not fact.is_positive:
			raise UnsupportedModel("Atomic audit requires positive predicate goals")
		targets.add(Call(fact.predicate, tuple(fact.args)))
	for condition in problem.numeric_goal_conditions:
		left, right = condition.left, condition.right
		if left.kind == "constant":
			left, right = right, left
		if condition.comparator != "=" or left.kind != "fluent" or right.kind != "constant":
			raise UnsupportedModel("Atomic audit requires constant integer equality goals")
		targets.add(Call(left.value, tuple(left.args) + (str(int(right.value)),)))
	if not targets:
		raise UnsupportedModel("The declared goal population is empty")
	return tuple(sorted(targets))
