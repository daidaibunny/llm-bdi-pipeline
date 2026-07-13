from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.external_reference_planners import ExternalReferenceMethod
from scripts.run_external_planning_references import build_moose_reference_arguments
from scripts.run_external_planning_references import model_batch_manifest_metadata
from scripts.run_external_planning_references import parse_guard_failure
from scripts.run_external_planning_references import resolve_model_batch
from scripts.run_external_planning_references import summarize_records


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

	metadata = model_batch_manifest_metadata(tmp_path)

	assert metadata["timestamp_id"] == "seed-two"
	assert metadata["settings"]["random_seed"] == 2
	assert len(metadata["sha256"]) == 64


def test_parse_guard_failure_distinguishes_timeout_and_memory() -> None:
	assert parse_guard_failure("paper: timeout exceeded") == "timeout"
	assert parse_guard_failure("paper: memory limit exceeded") == "memory_limit"
	assert parse_guard_failure("plain planner error") == "planner_failed"


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
