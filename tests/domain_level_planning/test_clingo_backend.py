from __future__ import annotations

from domain_level_planning import ClingoSketchRuleSelector, LiftedCall, LiftedPlanRule


def test_clingo_selector_minimizes_rule_cost_for_required_capabilities() -> None:
	selector = ClingoSketchRuleSelector()

	result = selector.select(
		candidate_rules=(
			LiftedPlanRule(
				name="expensive_clear_rule",
				head=LiftedCall("subgoal", "clear", ("X",)),
				context=("not clear(X)",),
				capabilities=("clear_progress",),
				cost=10,
			),
			LiftedPlanRule(
				name="cheap_clear_rule",
				head=LiftedCall("subgoal", "clear", ("X",)),
				context=("on(Y, X)",),
				capabilities=("clear_progress",),
				cost=1,
			),
			LiftedPlanRule(
				name="on_rule",
				head=LiftedCall("subgoal", "on", ("X", "Y")),
				context=("clear(X)", "clear(Y)"),
				capabilities=("on_progress",),
				cost=2,
			),
		),
		required_capabilities=("clear_progress", "on_progress"),
	)

	assert result.selected_rule_names == ("cheap_clear_rule", "on_rule")
	assert result.cost == 3
