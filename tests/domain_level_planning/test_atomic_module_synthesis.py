from __future__ import annotations

from pathlib import Path

from domain_level_planning.atomic_module_synthesis import (
	synthesize_atomic_minimal_literal_module_library,
)
from plan_library.rendering import render_plan_library_asl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "blocks" / "domain.pddl"


def test_blocks_atomic_minimal_literal_modules_are_compact_recursive_and_lifted() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=BLOCKS_DOMAIN,
		seed_predicates=("on",),
		source_backend="moose_schema_minimal_modules",
		source_name="blocks-smoke",
	)
	asl = render_plan_library_asl(library)

	assert len(library.plans) == 8
	assert {plan.trigger.symbol for plan in library.plans} == {"clear", "on"}
	assert library.metadata["generation_mode"] == "atomic_minimal_literal_module_library"
	assert library.metadata["library_quality"]["compact_recursive_module_ready"] is True
	assert library.metadata["atomic_module_synthesis"]["module_predicates"] == [
		"clear",
		"on",
	]

	assert "+!on(X, Y) : type_block(X) & type_block(Y) & not clear(X)" in asl
	assert "\t!clear(X);" in asl
	assert "\t!on(X, Y)." in asl
	assert "pick_up(X);\n\tunstack" not in asl
	assert "on(X, Z) & clear(X) & handempty & clear(Y)" in asl
	assert "\tunstack(X, Z);" in asl
	assert "\tstack(X, Y)." in asl
	assert "on(Y, X) & clear(Y) & handempty" in asl
	assert "\tunstack(Y, X);" in asl
	assert "\tput_down(Y)." in asl
	assert "on(Y, X) & not clear(Y)" in asl

	assert "!holding" not in asl
	assert "!handempty" not in asl
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl
	assert "teg_state" not in asl
	assert "block0" not in asl
	assert "block1" not in asl


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


def test_logistics_atomic_modules_use_type_guards_and_airplane_bridge() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "logistics" / "domain.pddl",
		seed_predicates=("at",),
		source_backend="moose_schema_minimal_modules",
		source_name="logistics-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "type_package(X)" in asl
	assert "type_truck(Z)" in asl
	assert "type_airplane(Z)" in asl
	assert "load_airplane(X, Z, A);\n\tfly_airplane(Z, A, Y);\n\tunload_airplane(X, Z, Y)." in asl
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
