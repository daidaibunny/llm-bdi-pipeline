from __future__ import annotations

from plan_library import (
	AgentSpeakBodyStep,
	AgentSpeakPlan,
	AgentSpeakTrigger,
	PlanGenerationSummary,
	PlanLibrary,
)
from plan_library.validation import build_library_validation_record


def test_library_validation_accepts_current_atomic_and_temporal_contract() -> None:
	plan_library = PlanLibrary(
		domain_name="blocks",
		plans=(
			AgentSpeakPlan(
				plan_name="on_via_stack",
				trigger=AgentSpeakTrigger(
					event_type="achievement_goal",
					symbol="on",
					arguments=("X", "Y"),
				),
				context=("holding(X)", "clear(Y)"),
				body=(AgentSpeakBodyStep("action", "stack", ("X", "Y")),),
			),
			AgentSpeakPlan(
				plan_name="g_query_1_linear_sequence",
				trigger=AgentSpeakTrigger(event_type="achievement_goal", symbol="g_query_1"),
				body=(
					AgentSpeakBodyStep("subgoal", "on", ("X", "Y")),
				),
				binding_certificate=(
					{
						"artifact_family": "temporal_goal_dfa_append",
						"wrapper_mode": "linear_single_body",
					},
				),
			),
		),
	)

	record = build_library_validation_record(
		domain_name="blocks",
		plan_library=plan_library,
		generation_summary=PlanGenerationSummary(
			domain_name="blocks",
			dfa_count=1,
			transition_count=1,
			plans_generated=2,
			initial_belief_count=0,
		),
	)

	assert record.passed is True
	assert all(record.checked_layers.values())


def test_library_validation_rejects_exposed_dfa_state_belief() -> None:
	plan_library = PlanLibrary(
		domain_name="blocks",
		initial_beliefs=("dfa_state(q0)",),
		plans=(
			AgentSpeakPlan(
				plan_name="accept",
				trigger=AgentSpeakTrigger(event_type="achievement_goal", symbol="g_query_1"),
				context=("on(b1, b2)",),
			),
		),
	)

	record = build_library_validation_record(
		domain_name="blocks",
		plan_library=plan_library,
		generation_summary=PlanGenerationSummary(
			domain_name="blocks",
			dfa_count=1,
			transition_count=0,
			plans_generated=1,
			initial_belief_count=1,
		),
	)

	assert record.passed is False
	assert record.checked_layers["no_controller_state_beliefs"] is False
