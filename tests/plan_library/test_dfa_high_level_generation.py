from __future__ import annotations

from plan_library.dfa_high_level import (
	LowLevelPlanningRequest,
	LowLevelPlanningResponse,
	build_high_level_plan_library_from_dfa,
)
from plan_library.models import AgentSpeakBodyStep
from plan_library.rendering import render_plan_library_asl


def test_progress_transitions_render_without_dfa_state_beliefs() -> None:
	dfa_payload = {
		"initial_state": "1",
		"accepting_states": ["3"],
		"guarded_transitions": [
			{
				"source_state": "1",
				"target_state": "dead",
				"raw_label": "~do_put_on_b1_b2",
			},
			{
				"source_state": "1",
				"target_state": "2",
				"raw_label": "do_put_on_b1_b2",
			},
			{
				"source_state": "2",
				"target_state": "3",
				"raw_label": "true",
			},
		],
	}

	plan_library = build_high_level_plan_library_from_dfa(
		domain_key="blocksworld",
		domain_name="BLOCKS",
		instruction_id="query_1",
		dfa_payload=dfa_payload,
		low_level_planner=_fake_low_level_planner,
	)
	asl = render_plan_library_asl(plan_library)

	assert "dfa_state" not in asl
	assert "+!g : on(b1, b2) <-" in asl
	assert "+!g : not on(b1, b2) <-" in asl
	assert "\tfake_action(b1, b2);" in asl
	assert "\t!g." in asl


def test_only_progress_outgoing_transitions_become_actionable_plans() -> None:
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q2"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "deliver_pkg_a"},
			{"source_state": "q0", "target_state": "dead", "raw_label": "~deliver_pkg_a"},
			{"source_state": "q1", "target_state": "q2", "raw_label": "deliver_pkg_b"},
			{"source_state": "q1", "target_state": "dead", "raw_label": "~deliver_pkg_b"},
			{"source_state": "dead", "target_state": "dead", "raw_label": "true"},
		],
	}

	plan_library = build_high_level_plan_library_from_dfa(
		domain_key="transport",
		domain_name="transport",
		instruction_id="query_2",
		dfa_payload=dfa_payload,
		low_level_planner=_fake_low_level_planner,
	)

	actionable_plans = tuple(plan for plan in plan_library.plans if plan.body)
	assert len(actionable_plans) == 2
	assert all(
		plan.binding_certificate[0]["is_progress_transition"] is True
		for plan in actionable_plans
	)
	assert {
		tuple(plan.binding_certificate[0]["target_context"])
		for plan in actionable_plans
	} == {("at(pkg, a)",), ("at(pkg, b)",)}


def _fake_low_level_planner(request: LowLevelPlanningRequest) -> LowLevelPlanningResponse:
	return LowLevelPlanningResponse(
		body_steps=(AgentSpeakBodyStep("action", "fake-action", ("b1", "b2")),),
		certificate={"fake_planner": True},
	)
