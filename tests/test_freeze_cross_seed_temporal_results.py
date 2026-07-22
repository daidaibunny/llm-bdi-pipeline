from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.freeze_cross_seed_temporal_results import (
	build_cross_seed_temporal_dataset,
)
from scripts.freeze_cross_seed_temporal_results import merge_into_paired_result


def test_build_cross_seed_temporal_dataset_reports_seed_sensitivity(
	tmp_path: Path,
) -> None:
	summary_files = _write_summary_set(tmp_path)

	result = build_cross_seed_temporal_dataset(
		summary_files,
		expected_domains=("demo",),
		expected_case_count=2,
	)

	assert [row["success_count"] for row in result["seed_results"]] == [
		2,
		2,
		1,
		2,
		2,
	]
	assert result["aggregate"]["pooled_success_count"] == 9
	assert result["aggregate"]["pooled_evaluation_count"] == 10
	assert result["aggregate"]["mean_success_rate"] == pytest.approx(0.9)
	assert result["aggregate"]["sample_sd_success_rate"] == pytest.approx(
		0.22360679774997896,
	)
	assert result["aggregate"]["all_seed_success_case_count"] == 1
	assert result["aggregate"]["seed_sensitive_case_count"] == 1
	assert result["aggregate"]["all_seed_failure_case_count"] == 0
	assert result["aggregate"]["action_count_invariant_case_count"] == 1
	assert result["aggregate"]["action_count_variant_case_count"] == 0
	assert result["aggregate"]["action_count_unavailable_case_count"] == 1
	assert result["case_outcomes"]["pattern_counts"] == {
		"11011": 1,
		"11111": 1,
	}
	assert result["case_outcomes"]["seed_sensitive_cases"] == [
		{"domain": "demo", "pattern": "11011", "sample_id": "demo_b"},
	]
	assert result["protocol"]["validated_seed_zero_correction_count"] == 1
	assert len(result["case_records"]) == 10
	assert "controller_fingerprint" not in result["case_records"][0]


def test_build_cross_seed_temporal_dataset_rejects_success_without_val(
	tmp_path: Path,
) -> None:
	summary_files = _write_summary_set(tmp_path)
	payload = json.loads(summary_files[1].read_text(encoding="utf-8"))
	payload["results"][0]["execution_validation"]["val_success"] = False
	summary_files[1].write_text(json.dumps(payload), encoding="utf-8")

	with pytest.raises(ValueError, match="successful case lacks complete validation"):
		build_cross_seed_temporal_dataset(
			summary_files,
			expected_domains=("demo",),
			expected_case_count=2,
		)


def test_build_cross_seed_temporal_dataset_rejects_wrong_atomic_seed(
	tmp_path: Path,
) -> None:
	summary_files = _write_summary_set(tmp_path)
	payload = json.loads(summary_files[3].read_text(encoding="utf-8"))
	payload["atomic_batch_root"] = str(tmp_path / "paper-seed2-full")
	summary_files[3].write_text(json.dumps(payload), encoding="utf-8")

	with pytest.raises(ValueError, match="seed 3 atomic batch binding"):
		build_cross_seed_temporal_dataset(
			summary_files,
			expected_domains=("demo",),
			expected_case_count=2,
		)


def test_merge_into_paired_result_updates_existing_release(tmp_path: Path) -> None:
	result = build_cross_seed_temporal_dataset(
		_write_summary_set(tmp_path),
		expected_domains=("demo",),
		expected_case_count=2,
	)
	release_root = tmp_path / "release"
	release_root.mkdir()
	paired_result_file = release_root / "paired_ablation_results.json"
	seed_zero_records = [
		{
			**record,
			"duration_seconds": float(record["duration_seconds"]) + 100.0,
			"variant": "certified_balanced",
		}
		for record in result["case_records"]
		if record["seed"] == 0
	]
	paired_result_file.write_text(
		json.dumps(
			{
				"artifact_kind": "gp2pl_paired_ablation_results",
				"temporal": [
					{"par2_seconds": 102.0, "variant": "certified_balanced"},
				],
				"temporal_records": seed_zero_records,
			},
		),
		encoding="utf-8",
	)
	manifest_file = release_root / "manifest.json"
	manifest_file.write_text(
		json.dumps({"files": ["paired_ablation_results.json"]}),
		encoding="utf-8",
	)

	merge_into_paired_result(
		result,
		paired_result_file=paired_result_file,
		update_manifest=True,
	)

	paired = json.loads(paired_result_file.read_text(encoding="utf-8"))
	assert paired["temporal_cross_seed"]["aggregate"]["pooled_success_count"] == 9
	assert len(paired["temporal_cross_seed_records"]) == 10
	assert [
		row["duration_seconds"]
		for row in paired["temporal_records"]
		if row["variant"] == "certified_balanced"
	] == [1.0, 2.0]
	assert paired["temporal"][0]["par2_seconds"] == result["seed_results"][0][
		"par2_seconds"
	]
	manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
	assert manifest["paired_ablation_temporal_cross_seed_record_count"] == 10
	assert manifest["paired_ablation_temporal_cross_seed_seed_count"] == 5
	assert manifest["files"] == ["paired_ablation_results.json"]


def _write_summary_set(root: Path) -> dict[int, Path]:
	paths: dict[int, Path] = {}
	seed_zero_results = [
		_result(sample_id="demo_a", success=True, duration=1.0, action_count=1),
		_result(sample_id="demo_b", success=True, duration=2.0, action_count=2),
	]
	seed_zero = {
		"completed_at": "2026-07-16T12:00:00",
		"incremental_result_updates": [
			{
				"domain": "demo",
				"sample_id": "demo_b",
				"status": "success",
				"variant": "certified_balanced",
			},
		],
		"temporal_atomic_input": {
			"batch_id": "paper-seed0-full",
			"evidence_batch_id": "evidence-seed0",
		},
		"temporal_runs": [
			{
				"benchmark_sha256": "a" * 64,
				"parameters": _parameters(),
				"results": seed_zero_results,
				"variant": "certified_balanced",
			},
		],
	}
	path = root / "seed0.json"
	path.write_text(json.dumps(seed_zero), encoding="utf-8")
	paths[0] = path

	for seed in range(1, 5):
		results = [
			_result(sample_id="demo_a", success=True, duration=1.0 + seed, action_count=1),
			_result(
				sample_id="demo_b",
				success=seed != 2,
				duration=2.0 + seed,
				action_count=2,
			),
		]
		summary = {
			"artifact_kind": "temporal_goal_execution_validation",
			"atomic_batch_root": str(root / f"paper-seed{seed}-full"),
			"benchmark_sha256": "a" * 64,
			"completed_at": f"2026-07-22T1{seed}:00:00",
			"parameters": _parameters(),
			"results": results,
			"selected_case_count": 2,
			"temporal_compiler_variant": "certified_balanced",
		}
		path = root / f"seed{seed}.json"
		path.write_text(json.dumps(summary), encoding="utf-8")
		paths[seed] = path
	return paths


def _parameters() -> dict[str, object]:
	return {
		"jason_java_stack_size": "64m",
		"jason_timeout_seconds": 1800,
		"num_workers": 6,
		"plan_verifier_timeout_seconds": 1800,
		"temporal_compiler_variant": "certified_balanced",
	}


def _result(
	*,
	sample_id: str,
	success: bool,
	duration: float,
	action_count: int,
) -> dict[str, object]:
	return {
		"action_count": action_count if success else None,
		"controller_fingerprint": "not-public",
		"domain": "demo",
		"duration_seconds": duration,
		"execution_validation": (
			{
				"action_count": action_count,
				"gold_accepted": True,
				"prediction_accepted": True,
				"replay_valid": True,
				"success": True,
				"val_attempted": True,
				"val_success": True,
			}
			if success
			else None
		),
		"goal_name": f"g_{sample_id}",
		"jason_status": "success" if success else "failed",
		"profile": "ordered_two_milestone",
		"sample_id": sample_id,
		"status": "success" if success else "jason_failed",
		"success": success,
		"temporal_compiler_variant": "certified_balanced",
	}
