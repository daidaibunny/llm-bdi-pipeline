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

	assert "+!on(X, Y) : not clear(X)" in asl
	assert "\t!clear(X);" in asl
	assert "\t!on(X, Y)." in asl
	assert "+!on(X, Y) : on(X, Z) & clear(X) & handempty & clear(Y)" in asl
	assert "\tunstack(X, Z);" in asl
	assert "\tstack(X, Y)." in asl
	assert "+!clear(X) : on(Y, X) & clear(Y) & handempty" in asl
	assert "\tunstack(Y, X);" in asl
	assert "\tput_down(Y)." in asl
	assert "+!clear(X) : on(Y, X) & not clear(Y)" in asl

	assert "!holding" not in asl
	assert "!handempty" not in asl
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl
	assert "teg_state" not in asl
	assert "block0" not in asl
	assert "block1" not in asl
