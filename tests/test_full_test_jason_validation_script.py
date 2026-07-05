from __future__ import annotations

from pathlib import Path

from scripts.run_full_test_jason_validation import append_state_monitor_full_test_wrappers
from scripts.run_full_test_jason_validation import build_compile_atomic_library_command
from scripts.run_full_test_jason_validation import resolve_batch_root
from scripts.run_full_test_jason_validation import render_fact_atom
from scripts.run_full_test_jason_validation import safe_goal_fragment
from scripts.run_full_test_jason_validation import safe_path_fragment
from utils.pddl_parser import PDDLFact


def test_resolve_batch_root_selects_latest_timestamp(tmp_path: Path) -> None:
	(tmp_path / "20260704-120000").mkdir()
	(tmp_path / "20260705-090000").mkdir()

	resolved = resolve_batch_root(tmp_path, "latest")

	assert resolved == tmp_path / "20260705-090000"


def test_safe_goal_fragment_matches_existing_domain_goal_naming() -> None:
	assert safe_goal_fragment("8puzzle-1tile") == "d_8puzzle_1tile"
	assert safe_goal_fragment("blocks") == "blocks"


def test_safe_path_fragment_keeps_problem_ids_readable() -> None:
	assert safe_path_fragment("instance-26") == "instance-26"
	assert safe_path_fragment("p 01/problem") == "p_01_problem"


def test_render_fact_atom_matches_generated_asl_identifier_rules() -> None:
	assert render_fact_atom(PDDLFact("at-ferry", ["loc-1"])) == "at_ferry(loc_1)"
	assert render_fact_atom(PDDLFact("handempty", [])) == "handempty"


def test_full_test_compile_command_defaults_to_post_moose_recursive(tmp_path: Path) -> None:
	command = build_compile_atomic_library_command(
		readable_policy=tmp_path / "ferry.model.readable",
		domain_file=tmp_path / "domain.pddl",
		domain="ferry",
		library_root=tmp_path / "libraries",
		atomic_library_mode="post-moose-recursive",
	)

	assert "--post-moose-recursive" in command
	assert "--domain-file" in command


def test_full_test_compile_command_can_request_faithful_mode(tmp_path: Path) -> None:
	command = build_compile_atomic_library_command(
		readable_policy=tmp_path / "ferry.model.readable",
		domain_file=tmp_path / "domain.pddl",
		domain="ferry",
		library_root=tmp_path / "libraries",
		atomic_library_mode="faithful",
	)

	assert "--post-moose-recursive" not in command


def test_full_test_wrapper_uses_query_local_dfa_state_monitor(tmp_path: Path) -> None:
	asl_file = tmp_path / "plan_library.asl"
	problem_file = tmp_path / "p01.pddl"
	asl_file.write_text("/* base */\n", encoding="utf-8")
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain ferry)
		 (:objects car1 car2 loc1 loc2)
		 (:init)
		 (:goal (and (at car1 loc1) (at car2 loc2)))
		)
		""",
		encoding="utf-8",
	)

	record = append_state_monitor_full_test_wrappers(
		domain="ferry",
		plan_library_asl=asl_file,
		problem_files=(problem_file,),
		max_output_bytes=1024 * 1024,
	)
	text = asl_file.read_text(encoding="utf-8")

	assert record["wrapper_mode"] == "query_local_dfa_state_monitor_without_json_metadata"
	assert "tg_state(g_ferry_test_1, s0)." in text
	assert "+!g_ferry_test_1 : tg_state(g_ferry_test_1, s0) <-" in text
	assert "\t!at(car1, loc1);" in text
	assert "\t-tg_state(g_ferry_test_1, s0);" in text
	assert "\t+tg_state(g_ferry_test_1, s1);" in text
	assert "+!g_ferry_test_1 : tg_state(g_ferry_test_1, s1) <-" in text
	assert "+!g_ferry_test_1 : tg_state(g_ferry_test_1, s2) <-" in text
	assert "not at(car1, loc1)" not in text
	assert "at(car1, loc1) & not at(car2, loc2)" not in text
