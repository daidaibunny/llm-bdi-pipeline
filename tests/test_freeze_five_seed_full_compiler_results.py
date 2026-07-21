from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.freeze_five_seed_full_compiler_results import (
	build_five_seed_result_dataset,
	render_domain_table,
	render_main_table,
	render_result_macros,
)


def test_build_five_seed_result_dataset_reports_seed_variation(tmp_path: Path) -> None:
	summary_files = _write_summary_set(tmp_path)

	result = build_five_seed_result_dataset(
		summary_files,
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
	assert len(result["case_records"]) == 10
	assert set(result["case_records"][0]) == {
		"action_count",
		"domain",
		"jason_run_seconds",
		"seed",
		"status",
		"test_id",
		"timed_out",
		"val_success",
		"valid",
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


def test_build_five_seed_result_dataset_uses_jason_process_time(
	tmp_path: Path,
) -> None:
	summary_files = _write_summary_set(tmp_path)
	seed_zero = json.loads(summary_files[0].read_text(encoding="utf-8"))
	validation = seed_zero["validations"][0]
	validation.pop("jason_run_seconds")
	output_dir = tmp_path / "runtime" / "logistics-p1-01"
	output_dir.mkdir(parents=True)
	(output_dir / "jason_validation.json").write_text(
		json.dumps({"timing_profile": {"run_seconds": 7.5}}),
		encoding="utf-8",
	)
	validation["output_dir"] = str(output_dir)
	validation["duration_seconds"] = 99.0
	summary_files[0].write_text(json.dumps(seed_zero), encoding="utf-8")

	result = build_five_seed_result_dataset(
		summary_files,
		expected_domains=("depots", "logistics"),
		expected_case_count=2,
	)

	row = next(
		row
		for row in result["case_records"]
		if row["seed"] == 0 and row["domain"] == "logistics"
	)
	assert row["jason_run_seconds"] == 7.5


def test_rendered_latex_uses_machine_values(tmp_path: Path) -> None:
	result = build_five_seed_result_dataset(
		_write_summary_set(tmp_path),
		expected_domains=("depots", "logistics"),
		expected_case_count=2,
	)

	macros = render_result_macros(result)
	main_table = render_main_table(result)
	domain_table = render_domain_table(result)
	main_table_text = " ".join(main_table.split())

	assert "\\newcommand{\\AtomicFiveSeedMeanSuccessPercent}{40.00}" in macros
	assert "\\newcommand{\\AtomicFiveSeedSampleSDPercent}{22.36}" in macros
	assert "Scope & Cases/seed & Valid/seed & Coverage (\\%)" in main_table
	assert "All 2 domains & 2 & 0--1 & 40.0 $\\pm$ 22.4" in main_table
	assert "Logistics & 1 & 0--1 & 80.0 $\\pm$ 44.7" in main_table
	assert "Depots & 1 & 0 & 0.0 $\\pm$ 0.0" in main_table
	assert "Seed 0" not in main_table
	assert "sample standard deviation" in main_table_text
	assert "standard deviation (SD)" not in main_table_text
	assert "predeclared evidence seeds" in main_table_text
	assert "compiled independently" not in main_table_text
	assert "Domain & Test & Seed 0 & Seed 1 & Seed 2 & Seed 3 & Seed 4" in domain_table
	assert "Coverage (\\%)" in domain_table
	assert "Mean (\\%)" not in domain_table
	assert "SD (pp)" not in domain_table
	assert "logistics & 1 & 1 & 1 & 0 & 1 & 1 & 80.0 $\\pm$ 44.7" in domain_table
	assert "$n=5$" in domain_table
	assert "independently compiled atomic cores" in domain_table
	for table in (main_table, domain_table):
		assert "[htbp]" in table
		assert "\\small" in table
		assert "\\scriptsize" not in table
		assert table.index("\\caption{") > table.index("\\end{tabular}")


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
		"jason_run_seconds": 1.25,
		"plan_verifier_attempted": success,
		"plan_verifier_success": True if success else None,
		"problem_file": f"/fixture/{domain}/test/{test_id}.pddl",
		"status": "success" if success else "failed",
		"success": success,
		"timed_out": False,
	}
