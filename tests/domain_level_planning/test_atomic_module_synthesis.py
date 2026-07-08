from __future__ import annotations

from pathlib import Path

from domain_level_planning.atomic_module_synthesis import (
	_order_contexts_for_matching,
	_select_branches_with_clingo,
	synthesize_atomic_minimal_literal_module_library,
)
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.rendering import render_plan_library_asl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "blocksworld-tower" / "domain.pddl"


def test_context_order_uses_bound_goal_arguments_before_unbound_buckets() -> None:
	context = _order_contexts_for_matching(
		(
			"at(Z, C)",
			"in-city(C, D)",
			"in-city(A, D)",
			"at(X, A)",
			"in-city(A, B)",
			"in-city(Y, B)",
		),
		(
			"obj_tp(A, location)",
			"obj_tp(B, city)",
			"obj_tp(C, location)",
			"obj_tp(D, city)",
			"obj_tp(X, package)",
			"obj_tp(Y, location)",
			"obj_tp(Z, truck)",
		),
		initial_bound_variables=("X", "Y"),
	)

	assert context[:3] == (
		"obj_tp(X, package)",
		"obj_tp(Y, location)",
		"at(X, A)",
	)
	assert context.index("at(X, A)") < context.index("in-city(A, B)")
	assert context.index("in-city(C, D)") < context.index("at(Z, C)")
	assert context.index("at(Z, C)") < context.index("obj_tp(Z, truck)")


def test_context_order_places_only_bound_inequalities_before_pddl_filters() -> None:
	context = _order_contexts_for_matching(
		(
			"surface(B)",
			"B != X",
			"B != Z",
			"clear(B)",
			"on(Z, X)",
			"at(B, A)",
			"at(Z, A)",
		),
		(
			"obj_tp(X, crate)",
			"obj_tp(B, surface)",
		),
		initial_bound_variables=("X",),
	)

	assert context.index("obj_tp(X, crate)") < context.index("on(Z, X)")
	assert context.index("on(Z, X)") < context.index("B != Z")
	assert context.index("at(B, A)") < context.index("obj_tp(B, surface)")
	assert context.index("obj_tp(B, surface)") < context.index("B != X")
	assert context.index("obj_tp(B, surface)") < context.index("B != Z")
	assert context.index("B != X") < context.index("surface(B)")
	assert context.index("B != Z") < context.index("surface(B)")
	assert context.index("B != X") < context.index("clear(B)")
	assert context.index("B != Z") < context.index("clear(B)")


def test_clingo_selector_removes_context_subsumed_duplicate_branch() -> None:
	weaker_context_branch = AgentSpeakPlan(
		plan_name="deliver_with_weaker_context",
		trigger=AgentSpeakTrigger("achievement_goal", "delivered", ("X",)),
		context=("at(X, Y)",),
		body=(AgentSpeakBodyStep("action", "drop", ("X", "Y")),),
	)
	stronger_context_branch = AgentSpeakPlan(
		plan_name="deliver_with_extra_context",
		trigger=AgentSpeakTrigger("achievement_goal", "delivered", ("X",)),
		context=("at(X, Y)", "clear(Y)"),
		body=(AgentSpeakBodyStep("action", "drop", ("X", "Y")),),
	)
	necessary_recursive_branch = AgentSpeakPlan(
		plan_name="deliver_prepare_at",
		trigger=AgentSpeakTrigger("achievement_goal", "delivered", ("X",)),
		context=("not at(X, Y)",),
		body=(
			AgentSpeakBodyStep("subgoal", "at", ("X", "Y")),
			AgentSpeakBodyStep("subgoal", "delivered", ("X",)),
		),
	)

	selection = _select_branches_with_clingo(
		(
			weaker_context_branch,
			stronger_context_branch,
			necessary_recursive_branch,
		),
	)

	assert selection.plans == (weaker_context_branch, necessary_recursive_branch)
	assert selection.report.backend == "clingo_asp_minimize"
	assert selection.report.raw_candidate_count == 3
	assert selection.report.selected_candidate_count == 2
	assert selection.report.obligation_count == 3


def test_clingo_selector_removes_alpha_equivalent_prepare_branch() -> None:
	first_prepare = AgentSpeakPlan(
		plan_name="at_prepare_at_robby_A",
		trigger=AgentSpeakTrigger("achievement_goal", "at", ("X", "Y")),
		context=("not at_robby(A)", "room(A)"),
		body=(
			AgentSpeakBodyStep("subgoal", "at_robby", ("A",)),
			AgentSpeakBodyStep("subgoal", "at", ("X", "Y")),
		),
	)
	second_prepare = AgentSpeakPlan(
		plan_name="at_prepare_at_robby_B",
		trigger=AgentSpeakTrigger("achievement_goal", "at", ("X", "Y")),
		context=("not at_robby(B)", "room(B)"),
		body=(
			AgentSpeakBodyStep("subgoal", "at_robby", ("B",)),
			AgentSpeakBodyStep("subgoal", "at", ("X", "Y")),
		),
	)

	selection = _select_branches_with_clingo((first_prepare, second_prepare))

	assert len(selection.plans) == 1
	assert selection.plans[0].plan_name in {
		"at_prepare_at_robby_A",
		"at_prepare_at_robby_B",
	}
	assert selection.report.raw_candidate_count == 2
	assert selection.report.selected_candidate_count == 1
	assert selection.report.obligation_count == 2


def test_blocks_atomic_minimal_literal_modules_are_compact_recursive_and_lifted() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=BLOCKS_DOMAIN,
		seed_predicates=("on",),
		source_backend="moose_schema_minimal_modules",
		source_name="blocks-smoke",
	)
	asl = render_plan_library_asl(library)

	assert 17 <= len(library.plans) <= 25
	assert {plan.trigger.symbol for plan in library.plans} == {
		"clear",
		"handempty",
		"holding",
		"on",
		"ontable",
	}
	assert library.metadata["generation_mode"] == "atomic_minimal_literal_module_library"
	assert library.metadata["library_quality"]["compact_recursive_module_ready"] is True
	assert library.metadata["atomic_module_synthesis"]["module_predicates"] == [
		"clear",
		"handempty",
		"holding",
		"on",
		"ontable",
	]
	selector_report = library.metadata["atomic_module_synthesis"]
	assert selector_report["selector_backend"] == "clingo_asp_minimize"
	assert selector_report["selector_objective"] == [
		"minimize selected branch count",
		"then minimize selected context literal count",
		"then minimize selected body step count",
	]
	assert selector_report["branch_certification_rules"] == [
		(
			"static context literals must be range-restricted by head variables or "
			"previous positive dynamic literals"
		),
		"negative context literals must be range-restricted and cannot bind new variables",
		(
			"same-predicate recursive prepare branches require a deleted dynamic "
			"obstruction-relation certificate"
		),
	]
	assert selector_report["raw_candidate_count"] >= len(library.plans)
	assert selector_report["selector_obligation_count"] == selector_report["raw_candidate_count"]
	assert len(selector_report["selected_branch_ids"]) == len(library.plans)
	role_by_predicate = {
		record["predicate"]: record
		for record in library.metadata["atomic_module_synthesis"]["predicate_roles"]
	}
	assert role_by_predicate["holding"]["role"] == "producible_fluent"
	assert role_by_predicate["holding"]["emitted_module"] is True
	assert role_by_predicate["handempty"]["role"] == "producible_fluent"
	assert role_by_predicate["handempty"]["emitted_module"] is True
	assert role_by_predicate["ontable"]["role"] == "producible_fluent"
	assert role_by_predicate["ontable"]["emitted_module"] is True
	assert all(
		record["coverage_status"] == "ok"
		for record in library.metadata["atomic_module_synthesis"]["predicate_roles"]
	)

	assert "+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not clear(X)" in asl
	assert "\t!clear(X);" in asl
	assert "\t!on(X, Y)." in asl
	assert "+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not clear(Y)" in asl
	assert "\t!clear(Y);" in asl
	assert "+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not holding(X)" in asl
	assert "\t!holding(X);" in asl
	assert "pick_up(X);\n\tunstack" not in asl
	assert "obj_tp(X, block) & obj_tp(Y, block) & clear(X) & clear(Y) & ontable(X) & handempty" in asl
	assert "obj_tp(X, block) & obj_tp(Y, block) & clear(X) & clear(Y) & handempty & on(X, Z) & obj_tp(Z, block)" in asl
	assert "\tunstack(X, Z);" in asl
	assert "\tstack(X, Y)." in asl
	assert "obj_tp(X, block) & handempty & on(Y, X) & obj_tp(Y, block) & clear(Y)" in asl
	assert "\tunstack(Y, X);" in asl
	assert "\tput_down(Y)." in asl
	assert "obj_tp(X, block) & on(Y, X) & obj_tp(Y, block) & not clear(Y)" in asl
	assert "+!holding(X) : holding(X)" in asl
	assert "pick_up(X)." in asl
	assert "unstack(X, Y)." in asl
	assert "+!handempty : handempty" in asl
	assert "put_down(X)." in asl
	assert "+!ontable(X) : ontable(X)" in asl
	assert "+!ontable(X) : obj_tp(X, block) & not holding(X)" in asl

	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl
	assert "teg_state" not in asl
	assert "type_" not in asl
	assert "block0" not in asl
	assert "block1" not in asl
	assert "!on(Y, X)" not in asl
	clear_recursive_plans = [
		plan
		for plan in library.plans
		if plan.trigger.symbol == "clear"
		and any(
			step.kind == "subgoal"
			and step.symbol == "clear"
			and step.arguments != plan.trigger.arguments
			for step in plan.body
		)
	]
	assert len(clear_recursive_plans) == 1
	clear_certificate = clear_recursive_plans[0].binding_certificate[0][
		"recursive_progress_certificate"
	]
	assert clear_certificate == {
		"certificate_kind": "deleted_dynamic_obstruction_relation",
		"relation_predicate": "on",
		"relation_arguments": ["Y", "X"],
		"deleting_action": "unstack",
	}


def test_ferry_bridge_sequence_keeps_negative_precondition_and_movement_module() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "ferry" / "domain.pddl",
		seed_predicates=("at",),
		source_backend="moose_schema_minimal_modules",
		source_name="ferry-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "+!at(X, Y)" in asl
	assert "board(X, Z);\n\tsail(Z, Y);\n\tdebark(X, Y)." in asl
	assert "not at_ferry(Y)" in asl
	assert "+!at_ferry(X)" in asl
	assert "sail(Y, X)." in asl


def test_numeric_resource_preconditions_compile_to_context_guards(tmp_path: Path) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
(define (domain numeric-transport)
  (:requirements :strips :typing :numeric-fluents)
  (:types vehicle package location)
  (:predicates
    (at ?x ?l - location)
    (in ?p - package ?v - vehicle)
  )
  (:functions
    (capacity ?v - vehicle)
  )
  (:action pick-up
    :parameters (?v - vehicle ?p - package ?l - location)
    :precondition (and (at ?v ?l) (at ?p ?l) (>= (capacity ?v) 1))
    :effect (and
      (not (at ?p ?l))
      (in ?p ?v)
      (decrease (capacity ?v) 1)
    )
  )
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)

	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=("in",),
		source_backend="moose_schema_minimal_modules",
		source_name="numeric-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "capacity(Y, N)" in asl
	assert "N >= 1" in asl
	assert "\tpick_up(Y, X, Z)." in asl
	assert "+!>=" not in asl
	assert ">=(" not in asl
	assert "decrease" not in asl


def test_static_predicates_are_context_only_not_atomic_goal_modules() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "logistics" / "domain.pddl",
		seed_predicates=("at",),
		source_backend="moose_schema_minimal_modules",
		source_name="logistics-smoke",
	)
	asl = render_plan_library_asl(library)
	role_by_predicate = {
		record["predicate"]: record
		for record in library.metadata["atomic_module_synthesis"]["predicate_roles"]
	}

	assert role_by_predicate["in-city"]["role"] == "static_context"
	assert role_by_predicate["in-city"]["emitted_module"] is False
	assert "+!in_city" not in asl
	assert role_by_predicate["in"]["role"] == "producible_fluent"
	assert role_by_predicate["in"]["emitted_module"] is True
	assert "+!in(X, Y)" in asl


def test_depots_drop_is_on_producer_when_extra_variables_are_precondition_bound() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "depots" / "domain.pddl",
		seed_predicates=("on",),
		source_backend="moose_schema_minimal_modules",
		source_name="depots-smoke",
	)
	asl = render_plan_library_asl(library)

	drop_plans = [
		plan
		for plan in library.plans
		if plan.trigger.symbol == "on"
		and plan.body == (AgentSpeakBodyStep("action", "drop", ("Z", "X", "Y", "A")),)
	]

	assert len(drop_plans) == 1
	plan = drop_plans[0]
	assert plan.trigger.arguments == ("X", "Y")
	assert "lifting(Z, X)" in plan.context
	assert "at(Y, A)" in plan.context
	assert "at(Z, A)" in plan.context
	assert "clear(Y)" in plan.context
	assert "\tdrop(Z, X, Y, A)." in asl
	assert "type_" not in asl


def test_logistics_atomic_modules_compile_pddl_typing_to_obj_tp_guards() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "logistics" / "domain.pddl",
		seed_predicates=("at",),
		source_backend="moose_schema_minimal_modules",
		source_name="logistics-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "type_" not in asl
	assert "type_" not in str(library.metadata["atomic_module_synthesis"])
	assert "obj_tp(X, package)" in asl
	assert "obj_tp(Y, location)" in asl
	assert "obj_tp(Z, truck)" in asl
	assert "obj_tp(Z, airplane)" in asl
	assert "load_truck(X, Z, A);\n\tdrive_truck(Z, A, Y, B);\n\tunload_truck(X, Z, Y)." in asl
	assert (
		"drive_truck(Z, C, A, D);\n\tload_truck(X, Z, A);\n\t"
		"drive_truck(Z, A, Y, B);\n\tunload_truck(X, Z, Y)."
		in asl
	)
	assert (
		"load_airplane(X, Z, A);\n\tfly_airplane(Z, A, Y);\n\tunload_airplane(X, Z, Y)."
		in asl
	)
	assert (
		"fly_airplane(Z, B, A);\n\tload_airplane(X, Z, A);\n\t"
		"fly_airplane(Z, A, Y);\n\tunload_airplane(X, Z, Y)."
		in asl
	)
	assert "load_truck(X, X," not in asl
	assert "load_airplane(X, X," not in asl
	assert "load_airplane(X, Z, A);\n\tunload_airplane(X, Z, Y)." not in asl
	assert "load_truck(X, Z, A);\n\tunload_truck(X, Z, Y)." not in asl


def test_miconic_rejects_simultaneous_lift_location_direct_branch() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "miconic" / "domain.pddl",
		seed_predicates=("served",),
		source_backend="moose_schema_minimal_modules",
		source_name="miconic-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "board(Z, X);\n\tdepart(Y, X)." not in asl
	assert "board(Z, X);\n\tup(Z, Y);\n\tdepart(Y, X)." not in asl
	assert "board(Z, X);\n\tdown(Z, Y);\n\tdepart(Y, X)." not in asl
	assert "obj_tp(X, passenger)" in asl
	assert "obj_tp(Y, floor)" in asl
	assert len({plan.plan_name for plan in library.plans}) == len(library.plans)
	assert (
		"+!served(X) : obj_tp(X, passenger) & destin(X, Y) "
		"& obj_tp(Y, floor) & not lift_at(Y)"
		in asl
	)
	assert "\t!lift_at(Y);\n\t!served(X)." in asl
	assert "+!served(X) : obj_tp(X, passenger) & not boarded(X)" in asl
	assert "\t!boarded(X);\n\t!served(X)." in asl


def test_gripper_rejects_unranked_same_predicate_navigation_recursion() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "gripper" / "domain.pddl",
		seed_predicates=("at",),
		source_backend="moose_schema_minimal_modules",
		source_name="gripper-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "+!at_robby(X) : at_robby(X)" in asl
	assert "+!at_robby(X) : room(X) & at_robby(Y) & room(Y)" in asl
	assert "move(Y, X)." in asl
	assert "room(Y) & not at_robby(Y)" not in asl
	assert "!at_robby(Y);\n\t!at_robby(X)." not in asl
	at_plan_names = [
		plan.plan_name
		for plan in library.plans
		if plan.trigger.symbol == "at"
	]
	assert at_plan_names.index("at_via_pick_then_move_then_drop") < at_plan_names.index(
		"at_prepare_at-robby_Y",
	)
	assert at_plan_names.index("at_via_pick_then_move_then_drop") < at_plan_names.index(
		"at_prepare_at-robby_A",
	)


def test_miconic_static_above_does_not_bind_unbounded_navigation_context() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "miconic" / "domain.pddl",
		seed_predicates=("served",),
		source_backend="moose_schema_minimal_modules",
		source_name="miconic-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "+!lift_at(X) : lift_at(X)" in asl
	assert "+!lift_at(X) : obj_tp(X, floor) & above(Y, X) & obj_tp(Y, floor) & lift_at(Y)" in asl
	assert "+!lift_at(X) : obj_tp(X, floor) & above(X, Y) & obj_tp(Y, floor) & lift_at(Y)" in asl
	assert "above(Y, X) & not lift_at(Y)" not in asl
	assert "above(X, Y) & not lift_at(Y)" not in asl
