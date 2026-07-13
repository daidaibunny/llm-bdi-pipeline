from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.generate_aaai_result_tables import (
	build_paper_result_dataset,
	render_domain_table,
	render_profile_table,
	render_result_macros,
)


def test_build_paper_result_dataset_requires_clean_execution_revision(
	tmp_path: Path,
) -> None:
	fixture = _write_fixture(tmp_path, tracked_changes=True)

	with pytest.raises(ValueError, match="tracked source changes"):
		build_paper_result_dataset(**fixture)


def test_build_paper_result_dataset_verifies_atomic_library_hashes(
	tmp_path: Path,
) -> None:
	fixture = _write_fixture(tmp_path)
	atomic_asl = fixture["atomic_library_root"] / "toy" / "plan_library.asl"
	atomic_asl.write_text("tampered\n", encoding="utf-8")

	with pytest.raises(ValueError, match="atomic ASL hash mismatch"):
		build_paper_result_dataset(**fixture)


def test_build_paper_result_dataset_separates_translation_and_execution_checks(
	tmp_path: Path,
) -> None:
	fixture = _write_fixture(tmp_path)

	result = build_paper_result_dataset(**fixture)

	assert result["translation"] == {
		"json_valid_count": 1,
		"dfa_equivalent_count": 1,
		"total": 1,
	}
	assert result["execution"]["success_count"] == 1
	assert result["execution"]["gold_dfa_accept_count"] == 1
	assert result["execution"]["prediction_dfa_accept_count"] == 1
	assert result["domains"][0]["candidate_count"] == 3
	assert result["domains"][0]["evidence_candidate_count"] == 1
	assert result["domains"][0]["schema_candidate_count"] == 2
	assert result["domains"][0]["selected_branch_count"] == 2
	assert result["profiles"][0]["median_action_count"] == 1
	assert result["conformance"]["run_id"] == "clean-conformance"
	assert result["conformance"]["source_commit"] == "fedcba9876543210"
	assert result["conformance"]["semantic_success_count"] == 1
	assert result["conformance"]["zero_action_success_count"] == 1


def test_render_result_macros_uses_machine_counts() -> None:
	result = {
		"benchmark": {"domain_count": 16, "problem_count": 1228},
		"translation": {
			"total": 475,
			"json_valid_count": 475,
			"dfa_equivalent_count": 475,
		},
		"execution": {
			"success_count": 1228,
			"jason_success_count": 1228,
			"val_success_count": 1228,
			"gold_dfa_accept_count": 1228,
			"prediction_dfa_accept_count": 1228,
			"median_action_count": 2,
			"median_runtime_seconds": 5.4,
			"wall_runtime_seconds": 980,
		},
		"atomic": {
			"candidate_count": 100,
			"selected_branch_count": 80,
			"library_size_bytes": 2048,
		},
		"conformance": {
			"run_id": "clean-conformance",
			"semantic_case_count": 14,
			"semantic_success_count": 14,
			"zero_action_case_count": 2,
			"zero_action_success_count": 2,
		},
		"provenance": {
			"execution_run_id": "clean-run",
			"execution_commit": "0123456789abcdef",
		},
	}

	macros = render_result_macros(result)

	assert "\\newcommand{\\TEGProblemCount}{1,228}" in macros
	assert "\\newcommand{\\TranslationEquivalentCount}{475}" in macros
	assert "\\newcommand{\\TEGMedianRuntimeSeconds}{5.4}" in macros
	assert "\\newcommand{\\TEGExecutionCommit}{01234567}" in macros
	assert "\\newcommand{\\AtomicRemovedBranchCount}{20}" in macros
	assert "\\newcommand{\\AtomicReductionPercent}{20}" in macros
	assert "\\newcommand{\\TEGWallRuntimeMinutes}{16.3}" in macros
	assert "\\newcommand{\\ConformanceSemanticSuccessCount}{14}" in macros
	assert "\\newcommand{\\ConformanceZeroActionSuccessCount}{2}" in macros


def test_render_domain_table_uses_readable_grouped_columns() -> None:
	result = {
		"domains": [
			{
				"domain": "toy",
				"train_count": 1,
				"test_count": 2,
				"evidence_candidate_count": 3,
				"schema_candidate_count": 4,
				"selected_branch_count": 5,
				"library_size_bytes": 1024,
				"execution_total": 2,
				"jason_success_count": 2,
				"val_success_count": 2,
				"gold_dfa_accept_count": 2,
				"prediction_dfa_accept_count": 2,
				"median_runtime_seconds": 1.5,
			},
		],
	}

	table = render_domain_table(result)

	assert "\\begin{table*}[t]" in table
	assert "\\tiny" not in table
	assert "\\footnotesize" in table
	assert "\\multicolumn{2}{c}{Corpus}" in table
	assert "\\multicolumn{4}{c}{Atomic library}" in table
	assert "\\multicolumn{2}{c}{Temporal execution}" in table
	assert "End-to-end" in table
	assert "toy & 1 & 2 & 3 & 4 & 5 & 1.0 & 2/2 & 1.5" in table
	assert "Jason, neutral-goal VAL, gold-DFA acceptance, and predicted-DFA" in table


def test_render_profile_table_names_each_pipeline_oracle() -> None:
	result = {
		"profiles": [
			{
				"profile": "ordered_two_milestone",
				"query_count": 4,
				"translation_count": 2,
				"dfa_equivalent_count": 2,
				"controller_compiled_count": 4,
				"jason_success_count": 4,
				"val_success_count": 4,
				"gold_dfa_accept_count": 4,
				"prediction_dfa_accept_count": 4,
				"median_action_count": 2,
				"median_runtime_seconds": 1.5,
			},
		],
	}

	table = render_profile_table(result)

	assert "\\begin{table*}[t]" in table
	assert "\\tiny" not in table
	assert "\\footnotesize" in table
	assert "Eq./total" in table
	assert "Controller" in table
	assert "Jason" in table
	assert "VAL" in table
	assert "Gold DFA" in table
	assert "Pred. DFA" in table
	assert "Ordered-2 & 2/2 & 4 & 4 & 4 & 4 & 4 & 4 & 2 & 1.5" in table


def _write_fixture(
	root: Path,
	*,
	tracked_changes: bool = False,
) -> dict[str, Path]:
	benchmark_root = root / "benchmark"
	benchmark_root.mkdir()
	benchmark = {
		"benchmark_id": "toy-benchmark",
		"counts": {
			"domain_count": 1,
			"problem_case_count": 1,
			"unique_translation_input_count": 1,
		},
		"domains": {
			"toy": {
				"cases": {
					"toy_p01": {
						"profile": "ordered_two_milestone",
						"translation_id": "tpl-1",
					},
				},
			},
		},
	}
	benchmark_file = benchmark_root / "benchmark.json"
	_write_json(benchmark_file, benchmark)
	benchmark_sha = _sha256(benchmark_file)
	_write_json(
		benchmark_root / "manifest.json",
		{
			"benchmark_id": "toy-benchmark",
			"benchmark_file": "benchmark.json",
			"benchmark_sha256": benchmark_sha,
			"counts": benchmark["counts"],
		},
	)
	model_root = benchmark_root / "model_run"
	model_root.mkdir()
	predictions = model_root / "translation_predictions.jsonl"
	predictions.write_text(
		json.dumps(
			{
				"translation_id": "tpl-1",
				"outcome": "accepted",
				"prediction": {"status": "supported"},
			},
		)
		+ "\n",
		encoding="utf-8",
	)
	_write_json(
		model_root / "run_config.json",
		{
			"completed_record_count": 1,
			"translation_predictions_sha256": _sha256(predictions),
		},
	)
	validation_root = benchmark_root / "validation"
	validation_root.mkdir()
	(validation_root / "translation_validation_results.jsonl").write_text(
		json.dumps(
			{
				"translation_id": "tpl-1",
				"status": "semantically_equivalent",
				"success": True,
			},
		)
		+ "\n",
		encoding="utf-8",
	)
	_write_json(
		benchmark_root / "release_validation.json",
		{
			"benchmark_id": "toy-benchmark",
			"benchmark_sha256": benchmark_sha,
			"frozen_predictions_sha256": _sha256(predictions),
			"delivered_validation_matches_independent": {
				"normalized_summary_exact": True,
				"translation_results_exact": True,
				"problem_results_exact": True,
				"domain_datasets_exact": True,
			},
		},
	)

	domain_root = root / "domains" / "toy"
	(domain_root / "train").mkdir(parents=True)
	(domain_root / "test").mkdir()
	(domain_root / "train" / "train.pddl").write_text("", encoding="utf-8")
	(domain_root / "test" / "test.pddl").write_text("", encoding="utf-8")

	atomic_root = root / "atomic"
	atomic_domain = atomic_root / "toy"
	atomic_domain.mkdir(parents=True)
	atomic_asl = atomic_domain / "plan_library.asl"
	atomic_asl.write_text("+!goal : true <- true.\n", encoding="utf-8")
	atomic_json = atomic_domain / "plan_library.json"
	_write_json(
		atomic_json,
		{
			"plans": [{}, {}],
			"metadata": {
				"evidence_module": {"source_provider": "moose"},
				"pddl_support": {"is_compilable": True},
				"library_quality": {
					"validated_policy_lifting_ready": True,
				},
				"atomic_module_synthesis": {
					"candidate_source_counts": {
						"joint_unique": 3,
						"validated_evidence": 1,
						"schema": 2,
					},
					"plan_count": 2,
					"selector_backend": "clingo_asp_minimize",
					"predicate_roles": [],
				},
			},
		},
	)

	execution_summary = root / "execution.json"
	_write_json(
		execution_summary,
		{
			"run_id": "clean-run",
			"benchmark_id": "toy-benchmark",
			"benchmark_sha256": benchmark_sha,
			"source_revision": {
				"commit": "0123456789abcdef",
				"tracked_changes": tracked_changes,
			},
			"started_at": "2026-07-13T00:00:00",
			"completed_at": "2026-07-13T00:00:10",
			"atomic_library_inputs": {
				"toy": {
					"plan_library_asl_sha256": _sha256(atomic_asl),
					"plan_library_json_sha256": _sha256(atomic_json),
				},
			},
			"results": [
				{
					"sample_id": "toy_p01",
					"domain": "toy",
					"profile": "ordered_two_milestone",
					"status": "success",
					"success": True,
					"jason_status": "success",
					"action_count": 1,
					"duration_seconds": 2.5,
					"execution_validation": {
						"val_attempted": True,
						"val_success": True,
						"gold_accepted": True,
						"prediction_accepted": True,
					},
				},
			],
		},
	)

	conformance_root = root / "conformance"
	conformance_root.mkdir()
	conformance_suite = conformance_root / "suite.json"
	conformance_suite.write_text("{}\n", encoding="utf-8")
	conformance_suite_sha = _sha256(conformance_suite)
	conformance_result = conformance_root / "release_validation.json"
	_write_json(
		conformance_result,
		{
			"run_id": "clean-conformance",
			"success": True,
			"source_revision": {
				"commit": "fedcba9876543210",
				"tracked_changes": False,
			},
			"semantic_case_count": 1,
			"zero_action_case_count": 1,
			"success_count": 2,
			"suite_sha256": conformance_suite_sha,
			"records": [
				{"kind": "finite_trace_semantics", "success": True},
				{"kind": "zero_action_end_to_end", "success": True},
			],
		},
	)
	_write_json(
		conformance_root / "manifest.json",
		{
			"files": {"suite.json": conformance_suite_sha},
			"release_validation": {
				"filename": conformance_result.name,
				"sha256": _sha256(conformance_result),
			},
		},
	)
	return {
		"benchmark_root": benchmark_root,
		"execution_summary_file": execution_summary,
		"atomic_library_root": atomic_root,
		"domain_root": root / "domains",
		"conformance_root": conformance_root,
	}


def _write_json(path: Path, payload: object) -> None:
	path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()
