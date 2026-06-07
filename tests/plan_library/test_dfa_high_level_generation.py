from __future__ import annotations

from plan_library.dfa_high_level import build_high_level_plan_library_from_dfa
from plan_library.rendering import render_plan_library_asl


def test_dfa_transition_guards_render_as_goal_contexts() -> None:
	dfa_payload = {
		"initial_state": "1",
		"accepting_states": ["3"],
		"guarded_transitions": [
			{
				"source_state": "1",
				"target_state": "2",
				"raw_label": "do_put_on_b1_b2 & ~do_clear_b3",
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
	)
	asl = render_plan_library_asl(plan_library)

	assert "dfa_state(1)." in asl
	assert "+!g : dfa_state(1) & on(b1, b2) & not clear(b3) <-" in asl
	assert "-dfa_state(1);" in asl
	assert "+dfa_state(2);" in asl
	assert "\t!g." in asl
	assert "+!g : dfa_state(3) <-" in asl
	assert "true." in asl


def test_every_transition_plan_uses_g_entrypoint_and_recurses() -> None:
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "deliver_pkg_loc"},
		],
	}

	plan_library = build_high_level_plan_library_from_dfa(
		domain_key="transport",
		domain_name="transport",
		instruction_id="query_2",
		dfa_payload=dfa_payload,
	)

	assert {plan.trigger.symbol for plan in plan_library.plans} == {"g"}
	transition_plan = next(plan for plan in plan_library.plans if plan.body)
	assert transition_plan.body[-1].kind == "subgoal"
	assert transition_plan.body[-1].symbol == "g"
