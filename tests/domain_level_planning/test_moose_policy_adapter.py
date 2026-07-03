from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from domain_level_planning.moose_policy_adapter import (
	compile_moose_readable_policy_to_asl_library,
	parse_moose_readable_policy,
	policy_program_from_moose_readable_policy,
)
from plan_library.rendering import render_plan_library_asl


PROJECT_ROOT = Path(__file__).resolve().parents[2]


FERRY_READABLE_POLICY = """
 precedence : (1, 1, 0, 0)
       vars : car0 location0
     s_cond : (at-ferry location0) (on car0)
     g_cond : (at car0 location0)
    actions : (debark car0 location0)

 precedence : (1, 3, 0, 0)
       vars : car0 location0 location1
     s_cond : (at car0 location0) (at-ferry location0) (empty-ferry)
     g_cond : (at car0 location1)
    actions : (board car0 location0) (sail location0 location1) (debark car0 location1)
"""


def test_parse_moose_readable_policy_extracts_lifted_rules() -> None:
	rules = parse_moose_readable_policy(FERRY_READABLE_POLICY)

	assert len(rules) == 2
	assert rules[0].variables == ("car0", "location0")
	assert rules[0].goal_conditions[0].predicate == "at"
	assert rules[0].goal_conditions[0].arguments == ("car0", "location0")
	assert rules[1].actions[0].predicate == "board"
	assert rules[1].actions[-1].arguments == ("car0", "location1")


def test_moose_readable_policy_becomes_lifted_policy_program() -> None:
	program = policy_program_from_moose_readable_policy(
		FERRY_READABLE_POLICY,
		domain_name="ferry",
		source_name="ferry-seed0",
		policy_file=Path("ferry-seed0.model.readable"),
	)

	assert program.backend_name == "moose"
	assert program.representation == "moose_first_order_decision_list"
	assert len(program.rules) == 2
	assert program.modules[0].goal_symbol == "at"
	assert program.rules[0].effects == (
		("primitive_action:debark(Car0, Location0)", "call"),
	)


def test_moose_readable_policy_compiles_to_atomic_asl_library() -> None:
	library = compile_moose_readable_policy_to_asl_library(
		FERRY_READABLE_POLICY,
		domain_name="ferry",
		source_name="ferry-seed0",
	)
	asl = render_plan_library_asl(library)

	assert [plan.trigger.symbol for plan in library.plans] == ["at", "at"]
	assert library.plans[0].trigger.arguments == ("Car0", "Location0")
	assert library.plans[1].context == (
		"at(Car0, Location0)",
		"at-ferry(Location0)",
		"empty-ferry",
	)
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl
	assert "+!at(Car0, Location1)" in asl
	assert "\tboard(Car0, Location0);" in asl
	assert "\tsail(Location0, Location1);" in asl
	assert "\tdebark(Car0, Location1)." in asl


def test_moose_readable_compile_asl_cli_materializes_atomic_library(
	tmp_path: Path,
) -> None:
	policy_file = tmp_path / "ferry-seed0.model.readable"
	output_dir = tmp_path / "atomic-library"
	policy_file.write_text(FERRY_READABLE_POLICY, encoding="utf-8")

	result = subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "gp_backend_audit.py"),
			"moose-readable-compile-asl",
			"--policy-file",
			str(policy_file),
			"--domain-name",
			"ferry",
			"--output-dir",
			str(output_dir),
		),
		check=True,
		capture_output=True,
		text=True,
	)

	library_json = json.loads(
		(output_dir / "plan_library.json").read_text(encoding="utf-8"),
	)
	metadata = json.loads(
		(output_dir / "atomic_library_metadata.json").read_text(encoding="utf-8"),
	)
	asl = (output_dir / "plan_library.asl").read_text(encoding="utf-8")

	assert "wrote atomic ASL library" in result.stdout
	assert library_json["domain_name"] == "ferry"
	assert len(library_json["plans"]) == 2
	assert metadata["backend"] == "moose"
	assert metadata["compiled_singleton_rule_count"] == 2
	assert "+!at(Car0, Location1)" in asl
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl
