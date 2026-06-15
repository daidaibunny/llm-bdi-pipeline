from __future__ import annotations

import pytest

from plan_library.models import AgentSpeakBodyStep, AgentSpeakPlan, AgentSpeakTrigger, PlanLibrary
from plan_library.rendering import render_plan_library_asl


def test_render_plan_library_preserves_compound_context_expressions() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="compound",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("goal_on(Y,Z) & (not on(Y,Z) | clear(Y))", "X != Y"),
				body=(AgentSpeakBodyStep("subgoal", "on", ("Y", "Z")),),
			),
		),
	)

	asl = render_plan_library_asl(plan_library)

	assert "+!g : goal_on(Y, Z) & (not on(Y, Z) | clear(Y)) & X \\\\== Y <-" in asl
	assert "\t!on(Y, Z)." in asl


def test_render_plan_library_allows_goal_descriptors_only_in_contexts() -> None:
	valid_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="uses_goal_context",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("goal_done(X)", "not done(X)"),
				body=(AgentSpeakBodyStep("subgoal", "done", ("X",)),),
			),
		),
	)

	asl = render_plan_library_asl(valid_library)

	assert "+!g : goal_done(X) & not done(X) <-" in asl
	assert "\t!done(X)." in asl


@pytest.mark.parametrize(
	"plan_library",
	(
		PlanLibrary(
			domain_name="generic",
			initial_beliefs=("goal_done(a)",),
			plans=(),
		),
		PlanLibrary(
			domain_name="generic",
			plans=(
				AgentSpeakPlan(
					plan_name="bad_trigger",
					trigger=AgentSpeakTrigger("achievement_goal", "goal_done", ("X",)),
				),
			),
		),
		PlanLibrary(
			domain_name="generic",
			plans=(
				AgentSpeakPlan(
					plan_name="bad_subgoal",
					trigger=AgentSpeakTrigger("achievement_goal", "g"),
					context=("true",),
					body=(AgentSpeakBodyStep("subgoal", "goal_done", ("X",)),),
				),
			),
		),
		PlanLibrary(
			domain_name="generic",
			plans=(
				AgentSpeakPlan(
					plan_name="bad_action",
					trigger=AgentSpeakTrigger("achievement_goal", "g"),
					context=("true",),
					body=(AgentSpeakBodyStep("action", "goal_done", ("X",)),),
				),
			),
		),
		PlanLibrary(
			domain_name="generic",
			plans=(
				AgentSpeakPlan(
					plan_name="bad_belief_update",
					trigger=AgentSpeakTrigger("achievement_goal", "g"),
					context=("true",),
					body=(AgentSpeakBodyStep("belief_addition", "goal_done", ("X",)),),
				),
			),
		),
	),
)
def test_render_plan_library_rejects_goal_descriptors_in_mutable_positions(
	plan_library: PlanLibrary,
) -> None:
	with pytest.raises(ValueError, match="Read-only goal descriptor atoms"):
		render_plan_library_asl(plan_library)


def test_render_plan_library_rejects_invalid_generated_asl_context() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="bad",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("goal_on(Y,Z) &",),
			),
		),
	)

	with pytest.raises(ValueError, match="Invalid AgentSpeak"):
		render_plan_library_asl(plan_library)
