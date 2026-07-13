from __future__ import annotations

import os
from pathlib import Path

from evaluation.temporal_goal_validation import ExecutionTraceValidationResult
from scripts.run_direct_temporal_reference import DirectTemporalTask
from scripts.run_direct_temporal_reference import run_direct_temporal_task
from scripts.run_direct_temporal_reference import summarize_temporal_reference_records
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

	def fake_run_guarded_command(
		command,
		*,
		output_dir,
		timeout_seconds,
		max_rss_gb,
		extra_env=None,
		artifact_stem="planner",
	):
		del timeout_seconds, max_rss_gb
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
		)

	def fake_validate_execution_trace(**kwargs):
		assert Path(kwargs["plan_file"]).read_text(encoding="utf-8") == "(place item)\n"
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
	assert record["method"] == "FOND4LTLf + LAMA"
	assert record["supported"] is True
	assert record["status"] == "valid"
	assert record["success"] is True
	assert record["action_count"] == 1
	assert Path(record["plan_file"]).read_text(encoding="utf-8") == "(place item)\n"
