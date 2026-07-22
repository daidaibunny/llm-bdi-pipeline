from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from evaluation.temporal_goal_validation import ExecutionTraceValidationResult
from scripts.run_direct_temporal_reference import DirectTemporalTask
from scripts.run_direct_temporal_reference import load_completed_records
from scripts.run_direct_temporal_reference import run_direct_temporal_task
from scripts.run_direct_temporal_reference import run_tide_temporal_task
from scripts.run_direct_temporal_reference import stage_failure_status
from scripts.run_direct_temporal_reference import summarize_temporal_reference_records
from scripts.run_direct_temporal_reference import tide_process_failure_status
from scripts.run_direct_temporal_reference import unsupported_tide_status
from scripts.run_external_planning_references import GuardedCommandResult


def test_temporal_summary_separates_unsupported_cases_from_solver_failures() -> None:
	records = [
		{
			"status": "valid",
			"supported": True,
			"success": True,
			"action_count": 4,
			"elapsed_seconds": 2.0,
		},
		{
			"status": "planner_timeout",
			"supported": True,
			"success": False,
			"action_count": 0,
			"elapsed_seconds": 1800.0,
		},
		{
			"status": "unsupported_numeric_pddl",
			"supported": False,
			"success": False,
			"action_count": 0,
			"elapsed_seconds": 0.0,
		},
	]

	summary = summarize_temporal_reference_records(records, timeout_seconds=1800)

	assert summary["case_count"] == 3
	assert summary["supported_case_count"] == 2
	assert summary["unsupported_case_count"] == 1
	assert summary["valid_trace_count"] == 1
	assert summary["coverage_on_supported"] == 0.5
	assert summary["overall_coverage"] == 1 / 3
	assert summary["par2_seconds_on_supported"] == 1801.0


def test_temporal_stage_failure_uses_stage_specific_status(tmp_path: Path) -> None:
	stderr_file = tmp_path / "stderr.txt"
	stderr_file.write_text("native compiler exception", encoding="utf-8")

	assert stage_failure_status("compiler", stderr_file) == "compiler_failed"
	assert stage_failure_status("planner", stderr_file) == "planner_failed"
	assert (
		unsupported_tide_status(ValueError("negation on literals only"))
		== "unsupported_formula_operator"
	)


def test_tide_frontend_diagnostics_are_not_reported_as_planning_failures(
	tmp_path: Path,
) -> None:
	stderr_file = tmp_path / "stderr.txt"
	stderr_file.write_text(
		"Predicate not found for AP: arm_empty\n",
		encoding="utf-8",
	)

	assert tide_process_failure_status(stderr_file) == "adapter_error"


def test_direct_temporal_runner_filters_compiler_actions_before_validation(
	tmp_path: Path,
	monkeypatch,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain tiny)
			(:requirements :strips)
			(:predicates (at ?x))
			(:action place
				:parameters (?x)
				:precondition (and)
				:effect (at ?x)))
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem tiny-1)
			(:domain tiny)
			(:objects item)
			(:init)
			(:goal (and)))
		""",
		encoding="utf-8",
	)
	executable = tmp_path / "fond4ltlf"
	executable.write_text("#!/bin/sh\n", encoding="utf-8")
	(executable.parent / "python").write_text("#!/bin/sh\n", encoding="utf-8")
	mona_executable = tmp_path / "mona-bin" / "mona"
	mona_executable.parent.mkdir()
	mona_executable.write_text("#!/bin/sh\n", encoding="utf-8")
	task = DirectTemporalTask(
		domain="tiny",
		sample_id="tiny_1",
		profile="eventually",
		domain_file=domain_file,
		problem_file=problem_file,
		benchmark_case={
			"bindings": {"X": "item"},
			"declared_parameters": [],
			"constraints": [],
			"atoms": [
				{
					"symbol": "a0",
					"kind": "predicate",
					"predicate": "at",
					"args": ["X"],
				},
			],
			"ltlf_formula": "F(a0)",
		},
		audit_row={"sample_id": "tiny_1"},
		output_dir=tmp_path / "case",
	)
	commands: list[tuple[str, ...]] = []
	timeouts: list[float] = []
	locks: list[Path | None] = []

	def fake_run_guarded_command(
		command,
		*,
		output_dir,
		timeout_seconds,
		max_rss_gb,
		extra_env=None,
		artifact_stem="planner",
		exclusive_lock_file=None,
	):
		timeouts.append(float(timeout_seconds))
		locks.append(exclusive_lock_file)
		del max_rss_gb
		command_tuple = tuple(str(item) for item in command)
		commands.append(command_tuple)
		stdout_file = output_dir / f"{artifact_stem}.stdout.txt"
		stderr_file = output_dir / f"{artifact_stem}.stderr.txt"
		stdout_file.parent.mkdir(parents=True, exist_ok=True)
		stdout_file.write_text("", encoding="utf-8")
		stderr_file.write_text("", encoding="utf-8")
		if artifact_stem == "compiler":
			assert extra_env is not None
			assert extra_env["PATH"].split(os.pathsep)[0] == str(
				mona_executable.parent,
			)
			compiled_domain = Path(command_tuple[command_tuple.index("-outd") + 1])
			compiled_problem = Path(command_tuple[command_tuple.index("-outp") + 1])
			compiled_domain.write_text(
				domain_file.read_text(encoding="utf-8"),
				encoding="utf-8",
			)
			compiled_problem.write_text(
				problem_file.read_text(encoding="utf-8"),
				encoding="utf-8",
			)
		else:
			(task.output_dir / "compiled.plan").write_text(
				"(place item)\n(trans-0)\n",
				encoding="utf-8",
			)
		return GuardedCommandResult(
			command=command_tuple,
			exit_code=0,
			elapsed_seconds=0.25,
			stdout_file=stdout_file,
			stderr_file=stderr_file,
			runtime_lock_wait_seconds=0.0,
		)

	def fake_validate_execution_trace(**kwargs):
		assert Path(kwargs["plan_file"]).read_text(encoding="utf-8") == "(place item)\n"
		assert kwargs["mona_executable"] == mona_executable
		return ExecutionTraceValidationResult(
			replay_valid=True,
			val_attempted=True,
			val_success=True,
			gold_accepted=True,
			prediction_accepted=True,
			action_count=1,
			state_count=2,
			neutral_problem_file="neutral.pddl",
			legality_certificate="pddl_replay_and_external_val",
		)

	monkeypatch.setattr(
		"scripts.run_direct_temporal_reference.run_guarded_command",
		fake_run_guarded_command,
	)
	monkeypatch.setattr(
		"scripts.run_direct_temporal_reference.validate_execution_trace",
		fake_validate_execution_trace,
	)
	monkeypatch.setattr(
		"scripts.run_direct_temporal_reference.container_path",
		lambda path: str(path),
	)
	monkeypatch.setattr(
		"scripts.run_direct_temporal_reference.moose_runtime_command",
		lambda arguments, **_: tuple(arguments),
	)

	record = run_direct_temporal_task(
		task,
		fond4ltlf_executable=executable,
		mona_executable=mona_executable,
		timeout_seconds=1800,
		max_rss_gb=8.0,
		plan_verifier_command="val",
		plan_verifier_timeout_seconds=1800,
	)

	assert len(commands) == 2
	assert timeouts == [1800.0, 1799.75]
	assert locks == [None, None]
	assert commands[0][2:4] == (
		"--runtime-dir",
		str(task.output_dir / "ltlf2dfa_runtime"),
	)
	assert record["method"] == "FOND4LTLf + LAMA"
	assert record["supported"] is True
	assert record["status"] == "valid"
	assert record["success"] is True
	assert record["action_count"] == 1
	assert record["compiler_timeout_seconds"] == 1800.0
	assert record["compiler_lock_wait_seconds"] == 0.0
	assert record["runtime_lock_wait_seconds"] == 0.0
	assert record["planner_timeout_seconds"] == 1799.75
	assert Path(record["plan_file"]).read_text(encoding="utf-8") == "(place item)\n"


def test_direct_resume_retries_infrastructure_results(tmp_path: Path) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text("(define (domain d))", encoding="utf-8")
	problem_file.write_text("(define (problem p) (:domain d))", encoding="utf-8")

	def task_for(sample_id: str) -> DirectTemporalTask:
		return DirectTemporalTask(
			domain="d",
			sample_id=sample_id,
			profile="eventually",
			domain_file=domain_file,
			problem_file=problem_file,
			benchmark_case={},
			audit_row={},
			output_dir=tmp_path / sample_id,
		)

	infra_task = task_for("infra")
	planner_task = task_for("planner")
	for task, status in ((infra_task, "adapter_error"), (planner_task, "planner_failed")):
		task.output_dir.mkdir()
		(task.output_dir / "result.json").write_text(
			json.dumps(
				{
					"variant": "fond4ltlf_lama",
					"sample_id": task.sample_id,
					"domain_sha256": hashlib.sha256(
						domain_file.read_bytes(),
					).hexdigest(),
					"problem_sha256": hashlib.sha256(
						problem_file.read_bytes(),
					).hexdigest(),
					"status": status,
				},
			),
			encoding="utf-8",
		)

	completed = load_completed_records((infra_task, planner_task))

	assert set(completed) == {"planner"}


def test_tide_runner_projects_and_independently_validates_official_plan(
	tmp_path: Path,
	monkeypatch,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "original.pddl"
	domain_file.write_text(
		"""
(define (domain tiny)
 (:requirements :strips)
 (:predicates (at ?x))
 (:action place
  :parameters (?x)
  :precondition (and)
  :effect (at ?x)))
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
(define (problem tiny-1)
 (:domain tiny)
 (:objects item)
 (:init)
 (:goal (and)))
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	task = DirectTemporalTask(
		domain="tiny",
		sample_id="tiny_1",
		profile="eventually",
		domain_file=domain_file,
		problem_file=problem_file,
		benchmark_case={
			"bindings": {"X": "item"},
			"declared_parameters": [],
			"constraints": [],
			"atoms": [
				{
					"symbol": "a0",
					"kind": "predicate",
					"predicate": "at",
					"args": ["X"],
				},
			],
			"ltlf_formula": "F(a0)",
		},
		audit_row={
			"gold_formula_ast": {},
		},
		output_dir=tmp_path / "case",
	)
	mona_executable = tmp_path / "mona"
	mona_executable.write_text("#!/bin/sh\n", encoding="utf-8")
	commands: list[tuple[str, ...]] = []

	def fake_run_guarded_command(
		command,
		*,
		output_dir,
		timeout_seconds,
		max_rss_gb,
		extra_env=None,
		artifact_stem="planner",
		exclusive_lock_file=None,
	):
		del timeout_seconds, max_rss_gb, extra_env, exclusive_lock_file
		command_tuple = tuple(str(item) for item in command)
		commands.append(command_tuple)
		stdout_file = output_dir / f"{artifact_stem}.stdout.txt"
		stderr_file = output_dir / f"{artifact_stem}.stderr.txt"
		stdout_file.parent.mkdir(parents=True, exist_ok=True)
		stdout_file.write_text("", encoding="utf-8")
		stderr_file.write_text("", encoding="utf-8")
		result_dir = (
			output_dir
			/ "solutions/tide/fd/lama-first/tiny/problem"
		)
		result_dir.mkdir(parents=True)
		(result_dir / "problem_plan_1").write_text(
			"""
Plan:
(gp2pla706c616365 gp2plo6974656d)

DFA Path:
1 -> 2

Product Path:
diagnostic only
""".strip()
			+ "\n",
			encoding="utf-8",
		)
		(result_dir / "stats.txt").write_text(
			"""
For 1 runs:
Average DFA construction time: 0.1 seconds
First DFA construction time: 0.1 seconds
Average DFA construction time (without first): 0 seconds
Average search time: 0.2 seconds
Average total time: 0.3 seconds
Average number of expanded nodes: 4
Average plan length: 1
Average number of backtracks: 0
""".strip()
			+ "\n",
			encoding="utf-8",
		)
		return GuardedCommandResult(
			command=command_tuple,
			exit_code=0,
			elapsed_seconds=0.4,
			stdout_file=stdout_file,
			stderr_file=stderr_file,
			runtime_lock_wait_seconds=0.0,
		)

	def fake_validate_execution_trace(**kwargs):
		assert Path(kwargs["plan_file"]).read_text(encoding="utf-8") == (
			"(place item)\n"
		)
		return ExecutionTraceValidationResult(
			replay_valid=True,
			val_attempted=True,
			val_success=True,
			gold_accepted=True,
			prediction_accepted=True,
			action_count=1,
			state_count=2,
			neutral_problem_file="neutral.pddl",
			legality_certificate="pddl_replay_and_external_val",
		)

	monkeypatch.setattr(
		"scripts.run_direct_temporal_reference.run_guarded_command",
		fake_run_guarded_command,
	)
	monkeypatch.setattr(
		"scripts.run_direct_temporal_reference.validate_execution_trace",
		fake_validate_execution_trace,
	)
	monkeypatch.setattr(
		"scripts.run_direct_temporal_reference._tide_runtime_error",
		lambda **_: None,
	)

	record = run_tide_temporal_task(
		task,
		tide_root=tmp_path / "tide",
		tide_image="gp2pl-tide:test",
		mona_executable=mona_executable,
		timeout_seconds=1800,
		max_rss_gb=8.0,
		subproblem_timeout_ms=60_000,
		plan_verifier_command="val",
		plan_verifier_timeout_seconds=1800,
	)

	assert len(commands) == 1
	assert commands[0][:4] == (
		"docker",
		"run",
		"--rm",
		"--platform",
	)
	assert record["method"] == "TIDE + LAMA"
	assert record["variant"] == "tide_lama"
	assert record["supported"] is True
	assert record["status"] == "valid"
	assert record["success"] is True
	assert record["action_count"] == 1
	assert record["tide_statistics"]["average_backtracks"] == 0.0
	assert "(:goal (eventually (gp2plp_6174 gp2plo6974656d)))" in (
		task.output_dir / "problem.pddl"
	).read_text(encoding="utf-8")
