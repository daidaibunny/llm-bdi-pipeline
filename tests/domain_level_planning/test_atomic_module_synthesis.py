from __future__ import annotations

from pathlib import Path

from domain_level_planning.atomic_module_synthesis import (
	_select_branches_with_clingo,
	synthesize_atomic_minimal_literal_module_library,
)
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.rendering import render_plan_library_asl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "blocks" / "domain.pddl"


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

	assert "+!on(X, Y) : not clear(X)" in asl
	assert "\t!clear(X);" in asl
	assert "\t!on(X, Y)." in asl
	assert "+!on(X, Y) : not clear(Y)" in asl
	assert "\t!clear(Y);" in asl
	assert "+!on(X, Y) : not holding(X)" in asl
	assert "\t!holding(X);" in asl
	assert "pick_up(X);\n\tunstack" not in asl
	assert "on(X, Z) & clear(X) & handempty & clear(Y)" in asl
	assert "\tunstack(X, Z);" in asl
	assert "\tstack(X, Y)." in asl
	assert "on(Y, X) & clear(Y) & handempty" in asl
	assert "\tunstack(Y, X);" in asl
	assert "\tput_down(Y)." in asl
	assert "on(Y, X) & not clear(Y)" in asl
	assert "+!holding(X) : holding(X)" in asl
	assert "pick_up(X)." in asl
	assert "unstack(X, Y)." in asl
	assert "+!handempty : handempty" in asl
	assert "put_down(X)." in asl
	assert "+!ontable(X) : ontable(X)" in asl
	assert "+!ontable(X) : not holding(X)" in asl

	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl
	assert "teg_state" not in asl
	assert "type_" not in asl
	assert "block0" not in asl
	assert "block1" not in asl
	assert "!on(Y, X)" not in asl


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


def test_logistics_atomic_modules_use_pddl_typing_without_type_guards() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "logistics" / "domain.pddl",
		seed_predicates=("at",),
		source_backend="moose_schema_minimal_modules",
		source_name="logistics-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "type_" not in asl
	assert "type_" not in str(library.metadata["atomic_module_synthesis"])
	assert "load_truck(X, X," not in asl
	assert "load_airplane(X, X," not in asl
	assert "drive_truck(X," not in asl
	assert "fly_airplane(X," not in asl
	assert "load_airplane(X, Z, A);\n\tfly_airplane(Z, A, Y);\n\tunload_airplane(X, Z, Y)." not in asl
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
	assert "board(Z, X);\n\tup(Z, Y);\n\tdepart(Y, X)." in asl
	assert "board(Z, X);\n\tdown(Z, Y);\n\tdepart(Y, X)." in asl
