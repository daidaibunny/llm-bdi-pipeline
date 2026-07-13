from __future__ import annotations

from collections import Counter

from domain_level_planning.transition_repair_tree import TransitionRepairLiteral
from domain_level_planning.transition_repair_tree import compile_transition_repair_tree
from plan_library.models import AgentSpeakBodyStep


def test_balanced_repair_tree_bounds_trigger_fanout_and_depth() -> None:
	literals = tuple(
		TransitionRepairLiteral(
			atom=f"done(item{index})",
			achievement_symbol="done",
			achievement_arguments=(f"item{index}",),
		)
		for index in range(1, 9)
	)

	compilation = compile_transition_repair_tree(
		transition_symbol="g_query_trans_1",
		shared_context=("query",),
		positive_literals=literals,
		completion_context=("query", *(literal.atom for literal in literals)),
		certificate={"serialization_certificate": {"threat_edges": []}},
	)

	trigger_counts = Counter(plan.trigger.symbol for plan in compilation.plans)
	assert max(trigger_counts.values()) == 2
	assert compilation.literal_count == 8
	assert compilation.tree_height == 4
	assert compilation.root_symbol == "g_query_trans_1_repair_1_8"
	assert compilation.done_symbol == "g_query_trans_1_done"
	root = compilation.plans[0]
	assert root.trigger.symbol == "g_query_trans_1"
	assert root.body == (
		AgentSpeakBodyStep("subgoal", "g_query_trans_1_repair_1_8", ()),
		AgentSpeakBodyStep("subgoal", "g_query_trans_1_done", ()),
	)
	internal = next(
		plan
		for plan in compilation.plans
		if plan.trigger.symbol == "g_query_trans_1_repair_1_8"
	)
	assert internal.body == (
		AgentSpeakBodyStep("subgoal", "g_query_trans_1_repair_1_4", ()),
		AgentSpeakBodyStep("subgoal", "g_query_trans_1_repair_5_8", ()),
	)


def test_singleton_transition_tree_preserves_atomic_achievement_call() -> None:
	compilation = compile_transition_repair_tree(
		transition_symbol="g_query_trans_1",
		shared_context=("query", "obj_tp(X, item)"),
		positive_literals=(
			TransitionRepairLiteral(
				atom="done(X)",
				achievement_symbol="done",
				achievement_arguments=("X",),
			),
		),
		completion_context=("query", "obj_tp(X, item)", "done(X)"),
		certificate={"serialization_certificate": {"threat_edges": []}},
	)

	leaves = tuple(
		plan
		for plan in compilation.plans
		if plan.trigger.symbol == "g_query_trans_1_repair_1_1"
	)
	assert len(leaves) == 2
	assert leaves[0].context[-1] == "done(X)"
	assert leaves[0].body == ()
	assert leaves[1].context[-1] == "not done(X)"
	assert leaves[1].body == (AgentSpeakBodyStep("subgoal", "done", ("X",)),)
	assert compilation.tree_height == 1


def test_transition_tree_checks_the_supplied_completion_context_before_returning() -> None:
	literals = (
		TransitionRepairLiteral("left", "left", ()),
		TransitionRepairLiteral("right", "right", ()),
	)
	compilation = compile_transition_repair_tree(
		transition_symbol="g_query_trans_1",
		shared_context=("query", "not blocked"),
		positive_literals=literals,
		completion_context=("query", "left", "right", "not blocked"),
		certificate={"serialization_certificate": {"threat_edges": [[0, 1]]}},
	)

	done_plans = tuple(
		plan
		for plan in compilation.plans
		if plan.trigger.symbol == "g_query_trans_1_done"
	)
	assert len(done_plans) == 2
	assert done_plans[0].context == ("query", "left", "right", "not blocked")
	assert done_plans[0].body == ()
	assert done_plans[1].context == ("query", "not blocked")
	assert done_plans[1].body == (
		AgentSpeakBodyStep("subgoal", "g_query_trans_1", ()),
	)
	assert done_plans[0].binding_certificate[0]["wrapper_role"] == (
		"transition_repair_tree_done"
	)
	assert done_plans[1].binding_certificate[0]["wrapper_role"] == (
		"transition_repair_tree_replay"
	)


def test_negative_guard_leaf_calls_only_a_certified_establishment_helper() -> None:
	compilation = compile_transition_repair_tree(
		transition_symbol="g_query_trans_1",
		shared_context=("query",),
		positive_literals=(
			TransitionRepairLiteral(
				atom="available(item)",
				achievement_symbol="g_query_trans_1_establish_not_available_1",
				polarity="negative",
			),
		),
		completion_context=("query", "not available(item)"),
		certificate={"serialization_certificate": {"negative_guard_count": 1}},
	)

	leaves = tuple(
		plan
		for plan in compilation.plans
		if plan.trigger.symbol == "g_query_trans_1_repair_1_1"
	)
	assert len(leaves) == 2
	assert leaves[0].context == ("query", "not available(item)")
	assert leaves[0].body == ()
	assert leaves[1].context == ("query", "available(item)")
	assert leaves[1].body == (
		AgentSpeakBodyStep(
			"subgoal",
			"g_query_trans_1_establish_not_available_1",
			(),
		),
	)
	assert leaves[1].binding_certificate[0]["literal_polarity"] == "negative"
