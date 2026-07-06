from __future__ import annotations

from pathlib import Path

from scripts.run_full_test_jason_validation import append_linear_single_body_full_test_wrappers
from scripts.run_full_test_jason_validation import build_compile_atomic_library_command
from scripts.run_full_test_jason_validation import full_test_wrapper_lines
from scripts.run_full_test_jason_validation import prepare_domain_for_full_test
from scripts.run_full_test_jason_validation import query_entry_proposition
from scripts.run_full_test_jason_validation import resolve_batch_root
from scripts.run_full_test_jason_validation import render_fact_atom
from scripts.run_full_test_jason_validation import safe_goal_fragment
from scripts.run_full_test_jason_validation import safe_path_fragment
from scripts.run_full_test_jason_validation import _jason_runtime_status_label
from scripts.run_full_test_jason_validation import _plan_verifier_status_label
from utils.pddl_parser import PDDLFact


def test_resolve_batch_root_selects_latest_timestamp(tmp_path: Path) -> None:
	(tmp_path / "20260704-120000").mkdir()
	(tmp_path / "20260705-090000").mkdir()

	resolved = resolve_batch_root(tmp_path, "latest")

	assert resolved == tmp_path / "20260705-090000"


def test_safe_goal_fragment_matches_existing_domain_goal_naming() -> None:
	assert safe_goal_fragment("domain-with-dash") == "domain_with_dash"
	assert safe_goal_fragment("blocks") == "blocks"


def test_safe_path_fragment_keeps_problem_ids_readable() -> None:
	assert safe_path_fragment("instance-26") == "instance-26"
	assert safe_path_fragment("p 01/problem") == "p_01_problem"


def test_query_entry_proposition_strips_top_level_goal_prefix() -> None:
	assert query_entry_proposition("g_miconic_test_41") == "miconic_test_41"
	assert query_entry_proposition("custom_goal") == "custom_goal_entry"


def test_render_fact_atom_matches_generated_asl_identifier_rules() -> None:
	assert render_fact_atom(PDDLFact("at-ferry", ["loc-1"])) == "at_ferry(loc_1)"
	assert render_fact_atom(PDDLFact("handempty", [])) == "handempty"


def test_full_test_compile_command_defaults_to_validated_policy_lifting(tmp_path: Path) -> None:
	command = build_compile_atomic_library_command(
		readable_policy=tmp_path / "ferry.model.readable",
		domain_file=tmp_path / "domain.pddl",
		domain="ferry",
		library_root=tmp_path / "libraries",
		atomic_library_mode="validated-policy-lifting",
	)

	assert "--validated-policy-lifting" in command
	assert "--domain-file" in command


def test_full_test_compile_command_accepts_legacy_post_moose_alias(
	tmp_path: Path,
) -> None:
	command = build_compile_atomic_library_command(
		readable_policy=tmp_path / "ferry.model.readable",
		domain_file=tmp_path / "domain.pddl",
		domain="ferry",
		library_root=tmp_path / "libraries",
		atomic_library_mode="post-moose-recursive",
	)

	assert "--validated-policy-lifting" in command
	assert "--post-moose-recursive" not in command


def test_full_test_compile_command_can_request_faithful_mode(tmp_path: Path) -> None:
	command = build_compile_atomic_library_command(
		readable_policy=tmp_path / "ferry.model.readable",
		domain_file=tmp_path / "domain.pddl",
		domain="ferry",
		library_root=tmp_path / "libraries",
		atomic_library_mode="faithful",
	)

	assert "--validated-policy-lifting" not in command


def test_validation_status_labels_split_jason_and_val_outcomes() -> None:
	assert _jason_runtime_status_label({"status": "plan_verifier_failed"}) == "ok"
	assert _plan_verifier_status_label(
		{
			"status": "plan_verifier_failed",
			"plan_verifier_attempted": True,
			"plan_verifier_success": False,
		},
	) == "fail"
	assert _jason_runtime_status_label({"status": "timeout", "timed_out": True}) == "timeout"
	assert _plan_verifier_status_label({"plan_verifier_attempted": False}) == "not_attempted"


def test_full_test_wrapper_uses_linear_single_body(tmp_path: Path) -> None:
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

	record = append_linear_single_body_full_test_wrappers(
		domain="ferry",
		plan_library_asl=asl_file,
		problem_files=(problem_file,),
		max_output_bytes=1024 * 1024,
	)
	text = asl_file.read_text(encoding="utf-8")

	assert record["wrapper_mode"] == "linear_single_body_without_json_metadata"
	assert "tg_state" not in text
	assert "ferry_test_1." in text
	assert "+!g_ferry_test_1 : ferry_test_1 <-" in text
	assert "\t!at(car1, loc1);" in text
	assert "\t!at(car2, loc2)." in text
	assert "\t!at(X, loc1);" not in text
	assert "not at(car1, loc1)" not in text
	assert "at(car1, loc1) & not at(car2, loc2)" not in text


def test_full_test_wrapper_compacts_uniform_gripper_goal_set_when_opted_in(
	tmp_path: Path,
) -> None:
	problem_file = tmp_path / "p01.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain gripper)
		 (:objects ball1 ball2 rooma roomb)
		 (:init
		   (ball ball1) (ball ball2)
		   (at ball1 rooma) (at ball2 rooma)
		 )
		 (:goal (and (at ball1 roomb) (at ball2 roomb)))
		)
		""",
		encoding="utf-8",
	)

	lines, plan_count = full_test_wrapper_lines(
		domain="gripper",
		index=1,
		problem_file=problem_file,
		compact_completion_wrappers=True,
	)
	text = "\n".join(lines)

	assert plan_count == 2
	assert "+!g_gripper_test_1 : gripper_test_1 & ball(X) & not at(X, roomb) <-" in text
	assert "\t!at(X, roomb);" in text
	assert "\t!g_gripper_test_1." in text
	assert "+!g_gripper_test_1 : gripper_test_1 <-" in text
	assert "!at(ball1, roomb)" not in text


def test_full_test_wrapper_keeps_uniform_goal_set_linear_by_default(tmp_path: Path) -> None:
	problem_file = tmp_path / "p01.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain gripper)
		 (:objects ball1 ball2 rooma roomb)
		 (:init (ball ball1) (ball ball2))
		 (:goal (and (at ball1 roomb) (at ball2 roomb)))
		)
		""",
		encoding="utf-8",
	)

	lines, plan_count = full_test_wrapper_lines(
		domain="gripper",
		index=1,
		problem_file=problem_file,
	)
	text = "\n".join(lines)

	assert plan_count == 1
	assert "+!g_gripper_test_1 : gripper_test_1 <-" in text
	assert "\t!at(ball1, roomb);" in text
	assert "\t!at(ball2, roomb)." in text
	assert "not at(X, roomb)" not in text


def test_full_test_wrapper_compacts_uniform_miconic_goal_set_when_opted_in(
	tmp_path: Path,
) -> None:
	problem_file = tmp_path / "p01.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain miconic)
		 (:objects p1 p2 f1 f2)
		 (:init
		   (origin p1 f1) (origin p2 f2)
		   (destin p1 f2) (destin p2 f1)
		 )
		 (:goal (and (served p1) (served p2)))
		)
		""",
		encoding="utf-8",
	)

	lines, plan_count = full_test_wrapper_lines(
		domain="miconic",
		index=1,
		problem_file=problem_file,
		compact_completion_wrappers=True,
	)
	text = "\n".join(lines)

	assert plan_count == 2
	assert "+!g_miconic_test_1 : miconic_test_1 & destin(X, A) & not served(X) <-" in text
	assert "\t!served(X);" in text
	assert "!served(p1)" not in text


def test_full_test_wrapper_keeps_mixed_destination_goals_linear(tmp_path: Path) -> None:
	problem_file = tmp_path / "p01.pddl"
	problem_file.write_text(
		"""
		(define (problem p01)
		 (:domain ferry)
		 (:objects car1 car2 loc1 loc2 loc3)
		 (:init (at car1 loc1) (at car2 loc2))
		 (:goal (and (at car1 loc2) (at car2 loc3)))
		)
		""",
		encoding="utf-8",
	)

	lines, plan_count = full_test_wrapper_lines(
		domain="ferry",
		index=1,
		problem_file=problem_file,
	)
	text = "\n".join(lines)

	assert plan_count == 1
	assert "+!g_ferry_test_1 : ferry_test_1 <-" in text
	assert "\t!at(car1, loc2);" in text
	assert "\t!at(car2, loc3)." in text


def test_prepare_domain_can_filter_test_problem_names(
	tmp_path: Path,
	monkeypatch,
) -> None:
	domain_root = tmp_path / "src" / "domains" / "ferry"
	(domain_root / "test").mkdir(parents=True)
	(domain_root / "domain.pddl").write_text("(define (domain ferry))\n", encoding="utf-8")
	for name in ("p2_01.pddl", "p2_02.pddl", "p1_01.pddl"):
		(domain_root / "test" / name).write_text(
			"""
			(define (problem probe)
			 (:domain ferry)
			 (:goal (and (at car1 loc1)))
			)
			""",
			encoding="utf-8",
		)
	batch_root = tmp_path / "batch"
	(batch_root / "run_logs" / "ferry").mkdir(parents=True)
	(batch_root / "run_logs" / "ferry" / "ferry.model.readable").write_text(
		"policy\n",
		encoding="utf-8",
	)

	def fake_command(*, readable_policy, domain_file, domain, library_root, atomic_library_mode):
		return ("true",)

	def fake_run_logged_command(command, *, stdout_file, stderr_file, timeout_seconds):
		plan_dir = tmp_path / "run" / "domain_libraries" / "ferry"
		plan_dir.mkdir(parents=True, exist_ok=True)
		(plan_dir / "plan_library.asl").write_text("/* base */\n", encoding="utf-8")

		class Result:
			success = True

			def to_dict(self):
				return {"success": True}

		return Result()

	monkeypatch.setattr("scripts.run_full_test_jason_validation.PROJECT_ROOT", tmp_path)
	monkeypatch.setattr(
		"scripts.run_full_test_jason_validation.build_compile_atomic_library_command",
		fake_command,
	)
	monkeypatch.setattr(
		"scripts.run_full_test_jason_validation.run_logged_command",
		fake_run_logged_command,
	)

	record, tasks = prepare_domain_for_full_test(
		domain="ferry",
		batch_root=batch_root,
		run_root=tmp_path / "run",
		timeout_seconds=1,
		atomic_library_mode="validated-policy-lifting",
		write_domain_long_asl=False,
		max_domain_long_asl_bytes=1024,
		test_name_regex=r"^p2_0[12]\.pddl$",
	)

	assert record["success"] is True
	assert [task.problem_file.name for task in tasks] == ["p2_01.pddl", "p2_02.pddl"]
