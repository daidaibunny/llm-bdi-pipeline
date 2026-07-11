from __future__ import annotations

import pytest

from plan_library import rendering
from plan_library.models import AgentSpeakBodyStep, AgentSpeakPlan, AgentSpeakTrigger, PlanLibrary
from plan_library.rendering import render_plan_library_asl


def test_render_plan_library_omits_redundant_per_plan_comments() -> None:
	plan = AgentSpeakPlan(
		plan_name="achieve_done",
		trigger=AgentSpeakTrigger("achievement_goal", "done"),
		context=("ready",),
		body=(AgentSpeakBodyStep("action", "finish"),),
		source_instruction_ids=("rule-17",),
		binding_certificate=({"certificate_kind": "schema_executable"},),
	)
	plan_library = PlanLibrary(domain_name="generic", plans=(plan,))

	asl = render_plan_library_asl(plan_library)
	payload = plan_library.to_dict()

	assert "/* Generated AgentSpeak(L) Plan Library */" in asl
	assert "/* plan=" not in asl
	assert "source_instruction_ids=" not in asl
	assert "+!done : ready <-" in asl
	assert payload["plans"][0]["plan_name"] == "achieve_done"
	assert payload["plans"][0]["source_instruction_ids"] == ["rule-17"]
	assert payload["plans"][0]["binding_certificate"] == [
		{"certificate_kind": "schema_executable"},
	]


def test_render_plan_library_preserves_compound_context_expressions() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="compound",
				trigger=AgentSpeakTrigger("achievement_goal", "g_query_1"),
				context=("ready(Y,Z) & (not on(Y,Z) | clear(Y))", "X != Y"),
				body=(AgentSpeakBodyStep("subgoal", "on", ("Y", "Z")),),
			),
		),
	)

	asl = render_plan_library_asl(plan_library)

	assert "+!g_query_1 : ready(Y, Z) & (not on(Y, Z) | clear(Y)) & X \\== Y <-" in asl
	assert "\t!on(Y, Z)." in asl


def test_render_plan_library_writes_jason_single_backslash_inequality() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="inequality",
				trigger=AgentSpeakTrigger("achievement_goal", "ready", ("X",)),
				context=("X != table", "not (= X table)"),
				body=(),
			),
		),
	)

	asl = render_plan_library_asl(plan_library)

	assert "X \\== table" in asl
	assert "X \\\\== table" not in asl


def test_render_plan_library_preserves_numeric_comparison_contexts() -> None:
	plan_library = PlanLibrary(
		domain_name="numeric",
		plans=(
			AgentSpeakPlan(
				plan_name="resource_guard",
				trigger=AgentSpeakTrigger(
					"achievement_goal",
					"in",
					("P", "V"),
				),
				context=("capacity(V,N)", "N >= 1", "M < N"),
				body=(AgentSpeakBodyStep("action", "pick-up", ("V", "P")),),
			),
		),
	)

	asl = render_plan_library_asl(plan_library)

	assert "+!in(P, V) : capacity(V, N) & N >= 1 & M < N <-" in asl
	assert "\tpick_up(V, P)." in asl


def test_render_plan_library_orders_dynamic_binders_before_type_guards() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="typed_dynamic_binder",
				trigger=AgentSpeakTrigger("achievement_goal", "done"),
				context=(
					"obj_tp(X, cell)",
					"position(crafting_table)",
					"tree_cell(X)",
					"N > 0",
				),
				body=(AgentSpeakBodyStep("action", "finish", ("X",)),),
			),
		),
	)

	asl = render_plan_library_asl(plan_library)

	assert (
		"+!done : position(crafting_table) & tree_cell(X) & obj_tp(X, cell) & N > 0 <-"
		in asl
	)


def test_render_plan_library_places_bound_inequalities_after_type_guards() -> None:
	plan_library = PlanLibrary(
		domain_name="depots-like",
		plans=(
			AgentSpeakPlan(
				plan_name="clear_via_safe_drop",
				trigger=AgentSpeakTrigger("achievement_goal", "clear", ("X",)),
				context=(
					"surface(B)",
					"B != X",
					"B != Z",
					"clear(B)",
					"on(Z, X)",
					"obj_tp(X, crate)",
					"obj_tp(B, surface)",
				),
				body=(
					AgentSpeakBodyStep("action", "lift", ("Y", "Z", "X", "A")),
					AgentSpeakBodyStep("action", "drop", ("Y", "Z", "B", "A")),
				),
			),
		),
	)

	asl = render_plan_library_asl(plan_library)

	assert (
		"+!clear(X) : obj_tp(X, crate) & on(Z, X) & surface(B) "
		"& obj_tp(B, surface) & B \\== X & B \\== Z & clear(B) <-"
		in asl
	)


def test_rendering_keeps_large_ground_transition_context_order_in_linear_work(
	monkeypatch,
) -> None:
	context = ("query", *(f"at(item{index}, target)" for index in range(5000)))
	original = rendering._parse_context_item_for_ordering
	parse_count = 0

	def counted(item: str):
		nonlocal parse_count
		parse_count += 1
		return original(item)

	monkeypatch.setattr(rendering, "_parse_context_item_for_ordering", counted)

	assert rendering._ordered_context_items(context) == context
	assert parse_count <= len(context)


def test_render_plan_library_preserves_signed_numeric_terms() -> None:
	plan_library = PlanLibrary(
		domain_name="numeric",
		plans=(
			AgentSpeakPlan(
				plan_name="negative_resource_guard",
				trigger=AgentSpeakTrigger(
					"achievement_goal",
					"resource",
					("-2",),
				),
				context=("resource(N)", "N == -2"),
				body=(AgentSpeakBodyStep("subgoal", "resource", ("-2",)),),
			),
		),
	)

	asl = render_plan_library_asl(plan_library)

	assert "+!resource(-2) : resource(N) & N == -2 <-" in asl
	assert "\t!resource(-2)." in asl
	assert "t_2" not in asl


def test_render_plan_library_renders_query_wrapper_contexts() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="query_wrapper",
				trigger=AgentSpeakTrigger("achievement_goal", "g_query_1"),
				context=("not done(X)",),
				body=(AgentSpeakBodyStep("subgoal", "done", ("X",)),),
			),
		),
	)

	asl = render_plan_library_asl(plan_library)

	assert "+!g_query_1 : not done(X) <-" in asl
	assert "\t!done(X)." in asl


def test_render_plan_library_rejects_invalid_generated_asl_context() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="bad",
				trigger=AgentSpeakTrigger("achievement_goal", "g_query_1"),
				context=("ready(Y,Z) &",),
			),
		),
	)

	with pytest.raises(ValueError, match="Invalid AgentSpeak"):
		render_plan_library_asl(plan_library)
