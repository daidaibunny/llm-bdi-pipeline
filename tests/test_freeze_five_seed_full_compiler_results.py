from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.freeze_five_seed_full_compiler_results import (
	build_five_seed_result_dataset,
	render_domain_table,
	render_main_table,
	render_result_macros,
	validate_source_aggregate,
)


def test_build_five_seed_result_dataset_reports_seed_variation(tmp_path: Path) -> None:
	summary_files = _write_summary_set(tmp_path)

	result = build_five_seed_result_dataset(
		summary_files,
		compiler_freeze={"revision": "0123456789abcdef", "closure_sha256": "abc"},
		expected_domains=("depots", "logistics"),
		expected_case_count=2,
	)

	assert [row["success_count"] for row in result["seed_results"]] == [1, 1, 0, 1, 1]
	assert result["aggregate"]["pooled_success_count"] == 4
	assert result["aggregate"]["pooled_evaluation_count"] == 10
	assert result["aggregate"]["mean_success_rate"] == pytest.approx(0.4)
	assert result["aggregate"]["sample_sd_success_rate"] == pytest.approx(
		0.22360679774997896,
	)
	assert result["aggregate"]["all_seed_success_case_count"] == 0
	assert result["aggregate"]["seed_sensitive_case_count"] == 1
	assert result["aggregate"]["all_seed_failure_case_count"] == 1
	assert result["aggregate"]["at_least_one_seed_success_case_count"] == 1
	assert result["protocol"]["validation_workers"] == 8
	assert result["protocol"]["jason_timeout_seconds"] == 1800
	assert result["protocol"]["plan_verifier_timeout_seconds"] == 1800
	assert result["protocol"]["jason_java_stack_size"] == "64m"
	assert result["case_outcomes"]["persistent_failures"] == [
		{"domain": "depots", "test_id": "p12"},
	]
	assert result["case_outcomes"]["pattern_counts"] == {
		"00000": 1,
		"11011": 1,
	}


def test_build_five_seed_result_dataset_rejects_success_without_val(
	tmp_path: Path,
) -> None:
	summary_files = _write_summary_set(tmp_path)
	seed_zero = json.loads(summary_files[0].read_text(encoding="utf-8"))
	seed_zero["validations"][0]["plan_verifier_success"] = False
	summary_files[0].write_text(json.dumps(seed_zero), encoding="utf-8")

	with pytest.raises(ValueError, match="successful case lacks VAL acceptance"):
		build_five_seed_result_dataset(
			summary_files,
			expected_domains=("depots", "logistics"),
			expected_case_count=2,
		)


def test_rendered_latex_uses_machine_values(tmp_path: Path) -> None:
	result = build_five_seed_result_dataset(
		_write_summary_set(tmp_path),
		expected_domains=("depots", "logistics"),
		expected_case_count=2,
	)

	macros = render_result_macros(result)
	main_table = render_main_table(result)
	domain_table = render_domain_table(result)

	assert "\\newcommand{\\AtomicFiveSeedMeanSuccessPercent}{40.00}" in macros
	assert "\\newcommand{\\AtomicFiveSeedSampleSDPercent}{22.36}" in macros
	assert "Seed & Valid/2 & Logistics & Depots" in main_table
	assert "0 & 1/2 & 1/1 & 0/1" in main_table
	assert "The other 0 domains complete for all seeds" in main_table
	assert "Mean (\\%)" not in main_table
	assert "Domain & Test & Seed 0 & Seed 1 & Seed 2 & Seed 3 & Seed 4" in domain_table
	assert "logistics & 1 & 1 & 1 & 0 & 1 & 1" in domain_table
	for table in (main_table, domain_table):
		assert "[htbp]" in table
		assert "\\small" in table
		assert "\\scriptsize" not in table
		assert table.index("\\caption{") > table.index("\\end{tabular}")


def test_validate_source_aggregate_matches_five_child_runs(tmp_path: Path) -> None:
	result = build_five_seed_result_dataset(
		_write_summary_set(tmp_path),
		expected_domains=("depots", "logistics"),
		expected_case_count=2,
	)
	aggregate_file = tmp_path / "five_seed_summary.json"
	aggregate_file.write_text(
		json.dumps(_source_aggregate(result)),
		encoding="utf-8",
	)

	provenance = validate_source_aggregate(
		aggregate_file,
		result=result,
		project_root=tmp_path,
	)

	assert provenance["run_id"] == "fixture-five-seed"
	assert provenance["path"] == "five_seed_summary.json"
	assert len(provenance["sha256"]) == 64
	assert provenance["moose_internal_workers"] == 1
	assert provenance["jason_workers_per_repetition"] == 8


def test_validate_source_aggregate_rejects_changed_domain_count(
	tmp_path: Path,
) -> None:
	result = build_five_seed_result_dataset(
		_write_summary_set(tmp_path),
		expected_domains=("depots", "logistics"),
		expected_case_count=2,
	)
	aggregate = _source_aggregate(result)
	aggregate["aggregate_domains"]["logistics"][
		"successful_cases_across_repetitions"
	] += 1
	aggregate_file = tmp_path / "five_seed_summary.json"
	aggregate_file.write_text(json.dumps(aggregate), encoding="utf-8")

	with pytest.raises(ValueError, match="aggregate domain logistics"):
		validate_source_aggregate(
			aggregate_file,
			result=result,
			project_root=tmp_path,
		)


def _write_summary_set(root: Path) -> dict[int, Path]:
	summary_files: dict[int, Path] = {}
	for seed in range(5):
		validations = [
			_validation(
				domain="logistics",
				test_id="p1_01",
				success=seed != 2,
			),
			_validation(domain="depots", test_id="p12", success=False),
		]
		summary = {
			"artifact_kind": "full_test_jason_validation_from_moose_asl_batch",
			"completed_at": f"2026-07-14T0{seed}:00:00",
			"input_snapshot": {
				"manifest_sha256": "a" * 64,
				"success": True,
				"task_count": 2,
			},
			"resumed_validation_count": 0,
			"run_id": f"formal-seed{seed}",
			"settings": {
				"atomic_library_mode": "validated-policy-lifting",
				"compiler_variant": "full",
				"jason_java_stack_size": "64m",
				"method": "Full Compiler",
				"num_workers": 8,
				"plan_verifier_timeout_seconds": 1800,
				"require_plan_verifier": True,
				"timeout_seconds": 1800,
				"write_per_test_runtime_asl": True,
			},
			"source_revision": {
				"available": True,
				"commit": f"{seed}" * 40,
				"tracked_changes": False,
				"untracked_files": False,
			},
			"success": all(row["success"] for row in validations),
			"validations": validations,
		}
		path = root / f"seed{seed}.json"
		path.write_text(json.dumps(summary), encoding="utf-8")
		summary_files[seed] = path
	return summary_files


def _validation(*, domain: str, test_id: str, success: bool) -> dict[str, object]:
	return {
		"action_count": 3 if success else None,
		"action_count_complete": success,
		"domain": domain,
		"error": None if success else "execution success marker not found in runtime output",
		"exit_code": 0,
		"plan_verifier_attempted": success,
		"plan_verifier_success": True if success else None,
		"problem_file": f"/fixture/{domain}/test/{test_id}.pddl",
		"status": "success" if success else "failed",
		"success": success,
		"timed_out": False,
	}


def _source_aggregate(result: dict[str, object]) -> dict[str, object]:
	seed_results = result["seed_results"]
	domain_rows = result["domains"]
	assert isinstance(seed_results, list)
	assert isinstance(domain_rows, list)
	return {
		"schema_version": 1,
		"run_id": "fixture-five-seed",
		"protocol": "five_independent_moose_synthesis_repetitions",
		"seeds": [0, 1, 2, 3, 4],
		"evidence_merged": False,
		"moose_internal_workers": 1,
		"moose_seed_parallelism": 5,
		"cross_seed_jason_parallelism": 1,
		"jason_workers_per_repetition": 8,
		"aggregate_domains": {
			row["domain"]: {
				"completed_repetitions": 5,
				"mean_seed_coverage": row["mean_success_rate"],
				"sample_stddev_seed_coverage": row[
					"sample_sd_success_rate"
				],
				"successful_cases_across_repetitions": sum(
					row["success_counts"],
				),
				"total_cases_across_repetitions": row["test_count"] * 5,
			}
			for row in domain_rows
		},
		"repetitions": [
			{
				"seed": seed_row["seed"],
				"validation_run_id": seed_row["run_id"],
				"moose_exit_code": 0,
				"validation_exit_code": (
					0 if seed_row["failure_count"] == 0 else 1
				),
				"evidence": {
					row["domain"]: {"generation_success": True}
					for row in domain_rows
				},
				"validation": {
					row["domain"]: {
						"success": row["success_counts"][seed_row["seed"]],
						"total": row["test_count"],
						"timeout": 0,
						"coverage": (
							row["success_counts"][seed_row["seed"]]
							/ row["test_count"]
						),
					}
					for row in domain_rows
				},
			}
			for seed_row in seed_results
		],
	}
