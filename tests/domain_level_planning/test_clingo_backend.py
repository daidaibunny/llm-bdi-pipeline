from __future__ import annotations

from domain_level_planning import (
	ClingoRequiredRuleGroup,
	ClingoSketchRuleSelector,
	LiftedCall,
	LiftedPlanRule,
)
import pytest


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


def test_clingo_selector_supports_hard_rule_constraints() -> None:
	selector = ClingoSketchRuleSelector()

	result = selector.select(
		candidate_rules=(
			LiftedPlanRule(
				name="cheap_clear_rule",
				head=LiftedCall("subgoal", "clear", ("X",)),
				context=(),
				capabilities=("clear_progress",),
				cost=1,
			),
			LiftedPlanRule(
				name="expensive_clear_rule",
				head=LiftedCall("subgoal", "clear", ("X",)),
				context=(),
				capabilities=("clear_progress",),
				cost=10,
			),
		),
		required_capabilities=("clear_progress",),
		required_rule_names=("expensive_clear_rule",),
	)

	assert result.selected_rule_names == ("expensive_clear_rule",)
	assert result.cost == 10


def test_clingo_selector_supports_required_rule_groups() -> None:
	selector = ClingoSketchRuleSelector()

	result = selector.select(
		candidate_rules=(
			LiftedPlanRule(
				name="progress_by_action",
				head=LiftedCall("subgoal", "done", ("X",)),
				context=(),
				capabilities=("done_progress",),
				cost=10,
			),
			LiftedPlanRule(
				name="progress_by_module",
				head=LiftedCall("subgoal", "done", ("X",)),
				context=(),
				capabilities=("done_progress",),
				cost=2,
			),
			LiftedPlanRule(
				name="irrelevant",
				head=LiftedCall("subgoal", "ready", ("X",)),
				context=(),
				capabilities=("done_progress",),
				cost=1,
			),
		),
		required_capabilities=("done_progress",),
		required_rule_groups=(
			ClingoRequiredRuleGroup(
				name="counterexample_progress_done",
				rule_names=("progress_by_action", "progress_by_module"),
			),
		),
		forbidden_rule_names=("irrelevant",),
	)

	assert result.selected_rule_names == ("progress_by_module",)
	assert result.cost == 2


def test_clingo_selector_rejects_unknown_rule_constraints() -> None:
	selector = ClingoSketchRuleSelector()

	with pytest.raises(ValueError, match="unknown required rules"):
		selector.select(
			candidate_rules=(
				LiftedPlanRule(
					name="known",
					head=LiftedCall("subgoal", "done", ("X",)),
					context=(),
					capabilities=("done_progress",),
				),
			),
			required_capabilities=("done_progress",),
			required_rule_names=("missing",),
		)
