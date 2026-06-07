from __future__ import annotations

from plan_library import (
	AgentSpeakBodyStep,
	AgentSpeakPlan,
	AgentSpeakTrigger,
	PlanGenerationSummary,
	PlanLibrary,
)
from plan_library.validation import build_library_validation_record


def test_library_validation_accepts_dfa_high_level_contract() -> None:
	plan_library = PlanLibrary(
		domain_name="blocks",
		initial_beliefs=("dfa_state(q0)",),
		plans=(
			AgentSpeakPlan(
				plan_name="accept",
				trigger=AgentSpeakTrigger(event_type="achievement_goal", symbol="g"),
				context=("dfa_state(q1)",),
			),
			AgentSpeakPlan(
				plan_name="transition",
				trigger=AgentSpeakTrigger(event_type="achievement_goal", symbol="g"),
				context=("dfa_state(q0)", "on(b1, b2)"),
				body=(
					AgentSpeakBodyStep("belief_deletion", "dfa_state", ("q0",)),
					AgentSpeakBodyStep("belief_addition", "dfa_state", ("q1",)),
					AgentSpeakBodyStep("subgoal", "g"),
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
			initial_belief_count=1,
		),
	)

	assert record.passed is True
	assert all(record.checked_layers.values())


def test_library_validation_rejects_missing_initial_dfa_belief() -> None:
	plan_library = PlanLibrary(
		domain_name="blocks",
		plans=(
			AgentSpeakPlan(
				plan_name="accept",
				trigger=AgentSpeakTrigger(event_type="achievement_goal", symbol="g"),
				context=("dfa_state(q1)",),
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
			initial_belief_count=0,
		),
	)

	assert record.passed is False
	assert record.checked_layers["initial_state_belief"] is False
