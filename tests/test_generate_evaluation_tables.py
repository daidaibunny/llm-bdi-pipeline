from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_evaluation_tables import (
	build_evaluation_result_dataset,
)


def test_build_evaluation_result_dataset_separates_translation_and_execution_checks(
	tmp_path: Path,
) -> None:
	fixture = _write_fixture(tmp_path)

	result = build_evaluation_result_dataset(**fixture)

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
	assert result["conformance"]["semantic_success_count"] == 1
	assert result["conformance"]["zero_action_success_count"] == 1
	assert "provenance" not in result
	assert "run_id" not in json.dumps(result)
	assert "sha256" not in json.dumps(result)


def _write_fixture(root: Path) -> dict[str, Path]:
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
	_write_json(
		benchmark_root / "manifest.json",
		{
			"benchmark_id": "toy-benchmark",
			"benchmark_file": "benchmark.json",
			"counts": benchmark["counts"],
		},
	)
	model_root = benchmark_root / "model_run"
	model_root.mkdir()
	(model_root / "translation_predictions.jsonl").write_text(
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
	(atomic_domain / "plan_library.asl").write_text(
		"+!goal : true <- true.\n",
		encoding="utf-8",
	)
	_write_json(
		atomic_domain / "plan_library.json",
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
			"source_revision": {
				"commit": "0123456789abcdef",
				"tracked_changes": False,
			},
			"started_at": "2026-07-13T00:00:00",
			"completed_at": "2026-07-13T00:00:10",
			"atomic_library_inputs": {
				"toy": {},
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
	(conformance_root / "suite.json").write_text("{}\n", encoding="utf-8")
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
			"records": [
				{"kind": "finite_trace_semantics", "success": True},
				{"kind": "zero_action_end_to_end", "success": True},
			],
		},
	)
	_write_json(
		conformance_root / "manifest.json",
		{
			"release_validation": {
				"filename": conformance_result.name,
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
	path.write_text(
		json.dumps(payload, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
