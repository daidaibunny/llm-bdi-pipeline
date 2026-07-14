from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from threading import Event

import pytest

from evaluation.external_reference_planners import ExternalReferenceMethod
from scripts.run_external_planning_references import MOOSE_RUNTIME_LOCK
from scripts.run_external_planning_references import GuardedCommandResult
from scripts.run_external_planning_references import ReferenceTask
from scripts.run_external_planning_references import build_moose_reference_arguments
from scripts.run_external_planning_references import exclusive_runtime_slot
from scripts.run_external_planning_references import load_completed_records
from scripts.run_external_planning_references import model_batch_manifest_metadata
from scripts.run_external_planning_references import parse_guard_failure
from scripts.run_external_planning_references import reference_runtime_lock
from scripts.run_external_planning_references import resolve_model_batch
from scripts.run_external_planning_references import run_reference_task
from scripts.run_external_planning_references import stage_raw_moose_model
from scripts.run_external_planning_references import summarize_records
from scripts.run_external_planning_references import validate_enhsp_runtime


def test_moose_reference_arguments_distinguish_policy_and_lama() -> None:
	raw = build_moose_reference_arguments(
		method=ExternalReferenceMethod.RAW_MOOSE,
		domain_file="/project/domain.pddl",
		problem_file="/project/problem.pddl",
		plan_file="/project/raw.plan",
		model_file="/project/domain.model",
	)
	lama = build_moose_reference_arguments(
		method=ExternalReferenceMethod.LAMA,
		domain_file="/project/domain.pddl",
		problem_file="/project/problem.pddl",
		plan_file="/project/lama.plan",
	)

	assert raw == (
		"policy",
		"/project/domain.model",
		"/project/domain.pddl",
		"/project/problem.pddl",
		"--bound",
		"0",
		"--plan-file",
		"/project/raw.plan",
	)
	assert lama == (
		"search",
		"lama-first",
		"/project/domain.pddl",
		"/project/problem.pddl",
		"--plan-file",
		"/project/lama.plan",
	)
	with pytest.raises(ValueError, match="model"):
		build_moose_reference_arguments(
			method=ExternalReferenceMethod.RAW_MOOSE,
			domain_file="/project/domain.pddl",
			problem_file="/project/problem.pddl",
			plan_file="/project/raw.plan",
		)


def test_resolve_model_batch_requires_every_selected_domain(tmp_path: Path) -> None:
	older = tmp_path / "older"
	newer = tmp_path / "newer"
	for root in (older, newer):
		(root / "run_logs" / "ferry").mkdir(parents=True)
		(root / "run_logs" / "ferry" / "ferry.model").write_bytes(b"model")
	(newer / "run_logs" / "gripper").mkdir(parents=True)
	(newer / "run_logs" / "gripper" / "gripper.model").write_bytes(b"model")

	assert resolve_model_batch(tmp_path, "latest", ("ferry", "gripper")) == newer
	assert resolve_model_batch(tmp_path, "older", ("ferry",)) == older
	with pytest.raises(ValueError, match="complete MOOSE model batch"):
		resolve_model_batch(tmp_path, "older", ("ferry", "gripper"))


def test_model_batch_manifest_metadata_records_seeded_training_contract(
	tmp_path: Path,
) -> None:
	manifest = {
		"timestamp_id": "seed-two",
		"domains": ["ferry"],
		"settings": {
			"random_seed": 2,
			"num_workers": 1,
			"num_permutations": 3,
			"goal_max_size": 1,
			"train_timeout_seconds": 43200,
			"max_rss_gb": 16.0,
		},
	}
	(tmp_path / "batch_manifest.json").write_text(
		json.dumps(manifest),
		encoding="utf-8",
	)
	artifact_root = tmp_path / "run_logs/ferry"
	artifact_root.mkdir(parents=True)
	(artifact_root / "ferry.model").write_bytes(b"model")
	(artifact_root / "ferry.model.readable").write_text("policy", encoding="utf-8")

	metadata = model_batch_manifest_metadata(tmp_path)

	assert metadata["timestamp_id"] == "seed-two"
	assert metadata["settings"]["random_seed"] == 2
	assert len(metadata["sha256"]) == 64
	assert len(metadata["artifact_sha256"]) == 64
	assert metadata["artifacts"][0]["domain"] == "ferry"


def test_stage_raw_moose_model_copies_external_batch_artifact(
	tmp_path: Path,
) -> None:
	model_file = tmp_path / "external-batch" / "ferry.model"
	model_file.parent.mkdir()
	model_file.write_bytes(b"immutable model evidence")
	compatibility_root = tmp_path / "case" / "moose_compatible_pddl"
	compatibility_root.mkdir(parents=True)

	staged = stage_raw_moose_model(
		model_file=model_file,
		compatibility_root=compatibility_root,
	)

	assert staged == compatibility_root / "ferry.model"
	assert staged.read_bytes() == model_file.read_bytes()
	assert staged.stat().st_size == model_file.stat().st_size


def test_parse_guard_failure_distinguishes_timeout_and_memory() -> None:
	assert parse_guard_failure("paper: timeout exceeded") == "timeout"
	assert parse_guard_failure("paper: memory limit exceeded") == "memory_limit"
	assert parse_guard_failure("Unable to locate a Java Runtime") == "tool_unavailable"
	assert (
		parse_guard_failure("container creation failed: failed to find loop device")
		== "runner_error"
	)
	assert (
		parse_guard_failure(
			"FileNotFoundError: /work/out/compiled_domain-compiled_problem",
		)
		== "runner_error"
	)
	assert parse_guard_failure("plain planner error") == "planner_failed"


def test_moose_hosted_methods_share_one_cross_process_runtime_lock() -> None:
	assert reference_runtime_lock(ExternalReferenceMethod.RAW_MOOSE) == MOOSE_RUNTIME_LOCK
	assert reference_runtime_lock(ExternalReferenceMethod.LAMA) == MOOSE_RUNTIME_LOCK
	assert reference_runtime_lock(ExternalReferenceMethod.ENHSP_HMRPHJ) is None


def test_exclusive_runtime_slot_serializes_threads_and_process_lock_file(
	tmp_path: Path,
) -> None:
	lock_file = tmp_path / "runtime.lock"
	first_entered = Event()
	release_first = Event()
	second_entered = Event()

	def hold_first_slot() -> None:
		with exclusive_runtime_slot(lock_file):
			first_entered.set()
			assert release_first.wait(timeout=2)

	def enter_second_slot() -> None:
		assert first_entered.wait(timeout=2)
		with exclusive_runtime_slot(lock_file):
			second_entered.set()

	with ThreadPoolExecutor(max_workers=2) as executor:
		first = executor.submit(hold_first_slot)
		assert first_entered.wait(timeout=2)
		second = executor.submit(enter_second_slot)
		assert not second_entered.wait(timeout=0.1)
		release_first.set()
		first.result(timeout=2)
		second.result(timeout=2)

	assert second_entered.is_set()


def test_lama_task_enters_host_runtime_lock(tmp_path: Path, monkeypatch) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text("(define (domain d))", encoding="utf-8")
	problem_file.write_text("(define (problem p) (:domain d))", encoding="utf-8")
	task = ReferenceTask(
		method=ExternalReferenceMethod.LAMA,
		domain="d",
		domain_file=domain_file,
		problem_file=problem_file,
		output_dir=tmp_path / "case",
	)
	observed_locks: list[Path | None] = []

	def fake_guarded_command(
		command,
		*,
		output_dir,
		timeout_seconds,
		max_rss_gb,
		exclusive_lock_file,
	):
		del timeout_seconds, max_rss_gb
		observed_locks.append(exclusive_lock_file)
		stdout_file = output_dir / "planner.stdout.txt"
		stderr_file = output_dir / "planner.stderr.txt"
		stdout_file.write_text("", encoding="utf-8")
		stderr_file.write_text("native planner failed", encoding="utf-8")
		return GuardedCommandResult(
			command=tuple(command),
			exit_code=1,
			elapsed_seconds=0.1,
			stdout_file=stdout_file,
			stderr_file=stderr_file,
		)

	monkeypatch.setattr(
		"scripts.run_external_planning_references.reference_command",
		lambda *args, **kwargs: ("planner",),
	)
	monkeypatch.setattr(
		"scripts.run_external_planning_references.run_guarded_command",
		fake_guarded_command,
	)

	record = run_reference_task(
		task,
		timeout_seconds=1800,
		max_rss_gb=8.0,
		enhsp_jar=tmp_path / "enhsp.jar",
		plan_verifier_command="val",
		plan_verifier_timeout_seconds=1800,
	)

	assert observed_locks == [MOOSE_RUNTIME_LOCK]
	assert record["status"] == "planner_failed"


def test_enhsp_runtime_rejects_macos_java_launcher_without_jdk(
	tmp_path: Path,
	monkeypatch,
) -> None:
	jar_file = tmp_path / "enhsp.jar"
	jar_file.write_bytes(b"jar")
	monkeypatch.setattr(
		"scripts.run_external_planning_references.shutil.which",
		lambda command: "/usr/bin/java" if command == "java" else None,
	)

	class FailedJava:
		returncode = 1
		stderr = "Unable to locate a Java Runtime"

	monkeypatch.setattr(
		"scripts.run_external_planning_references.subprocess.run",
		lambda *args, **kwargs: FailedJava(),
	)

	with pytest.raises(ValueError, match="working Java runtime"):
		validate_enhsp_runtime(jar_file)


def test_resume_retries_infrastructure_failures_but_keeps_planner_outcomes(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text("(define (domain d))", encoding="utf-8")

	def task_for(name: str) -> ReferenceTask:
		problem_file = tmp_path / f"{name}.pddl"
		problem_file.write_text(
			f"(define (problem {name}) (:domain d))",
			encoding="utf-8",
		)
		return ReferenceTask(
			method=ExternalReferenceMethod.LAMA,
			domain="d",
			domain_file=domain_file,
			problem_file=problem_file,
			output_dir=tmp_path / name,
		)

	infra_task = task_for("infra")
	planner_task = task_for("planner")
	for task, status in ((infra_task, "runner_error"), (planner_task, "planner_failed")):
		task.output_dir.mkdir()
		(task.output_dir / "result.json").write_text(
			json.dumps(
				{
					"variant": "lama",
					"domain": "d",
					"test": task.problem_file.stem,
					"domain_sha256": hashlib.sha256(
						domain_file.read_bytes(),
					).hexdigest(),
					"problem_sha256": hashlib.sha256(
						task.problem_file.read_bytes(),
					).hexdigest(),
					"status": status,
				},
			),
			encoding="utf-8",
		)

	completed = load_completed_records((infra_task, planner_task))

	assert set(completed) == {"lama:d:planner"}
	assert completed["lama:d:planner"]["status"] == "planner_failed"


def test_summary_counts_only_val_accepted_plans_as_valid() -> None:
	records = [
		{
			"method": "LAMA",
			"status": "valid",
			"plan_verifier_success": True,
			"action_count": 4,
			"elapsed_seconds": 2.0,
		},
		{
			"method": "LAMA",
			"status": "plan_verifier_failed",
			"plan_verifier_success": False,
			"action_count": 3,
			"elapsed_seconds": 3.0,
		},
		{
			"method": "MRP+HJ",
			"status": "timeout",
			"plan_verifier_success": None,
			"action_count": 0,
			"elapsed_seconds": 1800.0,
		},
	]

	summary = summarize_records(records, timeout_seconds=1800)

	assert summary["case_count"] == 3
	assert summary["valid_trace_count"] == 1
	assert summary["methods"]["LAMA"]["valid_trace_count"] == 1
	assert summary["methods"]["LAMA"]["coverage"] == 0.5
	assert summary["methods"]["MRP+HJ"]["par2_seconds"] == 3600.0
