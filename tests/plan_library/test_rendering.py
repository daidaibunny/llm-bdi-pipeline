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
