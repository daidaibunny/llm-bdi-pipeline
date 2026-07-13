from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from evaluation.temporal_benchmark import build_temporal_goal_benchmark_bundle
from evaluation.temporal_benchmark import validate_temporal_goal_benchmark_bundle
from evaluation.temporal_benchmark import write_temporal_goal_benchmark


def test_build_temporal_benchmark_preserves_semantics_without_hidden_gold(
	tmp_path: Path,
) -> None:
	inputs = _benchmark_inputs(tmp_path)

	bundle = build_temporal_goal_benchmark_bundle(
		**inputs,
		source_delivery_archive={"filename": "delivery.tar.gz", "sha256": "a" * 64},
		validation_implementation_commit="b" * 40,
	)

	assert bundle["artifact_kind"] == "multi_domain_lifted_ltlf_teg_benchmark"
	assert bundle["counts"] == {
		"domain_count": 1,
		"execution_attempted_count": 0,
		"problem_case_count": 2,
		"translation_equivalent_count": 1,
		"unique_translation_input_count": 1,
		"witness_accepted_count": 2,
	}
	case = bundle["domains"]["tiny"]["cases"]["tiny_p01"]
	assert case["translation_id"] == "tpl_1"
	assert case["profile"] == "ordered_two_milestone"
	assert case["atoms"][0] == {
		"args": ["X"],
		"kind": "numeric_equality",
		"function": "level",
		"symbol": "a0",
		"value": 1,
	}
	assert case["bindings"] == {"X": "object1"}
	assert case["translation_validation"]["equivalent"] is True
	assert case["execution_validation"] == {"status": "not_attempted"}
	serialized = json.dumps(bundle, sort_keys=True)
	assert '"gold_formula"' not in serialized
	assert '"witness_actions"' not in serialized
	assert '"state_fingerprints"' not in serialized


def test_build_temporal_benchmark_preserves_archive_normalization_provenance(
	tmp_path: Path,
) -> None:
	inputs = _benchmark_inputs(tmp_path)
	normalization = {
		"method": "release_relative_metadata_paths_v1",
		"source_sha256": "d" * 64,
		"normalized_files": [
			"artifacts/temporal_predictions/run-1/run_config.json",
		],
	}

	bundle = build_temporal_goal_benchmark_bundle(
		**inputs,
		source_delivery_archive={
			"filename": "delivery.tar.gz",
			"sha256": "a" * 64,
			"normalization": normalization,
		},
		validation_implementation_commit="b" * 40,
	)

	assert bundle["provenance"]["source_delivery_archive"]["normalization"] == (
		normalization
	)


def test_build_temporal_benchmark_fails_closed_on_incomplete_membership(
	tmp_path: Path,
) -> None:
	inputs = _benchmark_inputs(tmp_path)
	worklist = _read_jsonl(inputs["worklist_file"])
	worklist[0]["member_sample_ids"] = ["tiny_p01"]
	_write_jsonl(inputs["worklist_file"], worklist)

	with pytest.raises(ValueError, match="membership"):
		build_temporal_goal_benchmark_bundle(
			**inputs,
			source_delivery_archive={"filename": "delivery.tar.gz", "sha256": "a" * 64},
			validation_implementation_commit="b" * 40,
		)


def test_write_temporal_benchmark_emits_bundle_manifest_and_domain_views(
	tmp_path: Path,
) -> None:
	inputs = _benchmark_inputs(tmp_path)
	output = tmp_path / "paper-benchmark"

	manifest = write_temporal_goal_benchmark(
		**inputs,
		output_dir=output,
		source_delivery_archive={"filename": "delivery.tar.gz", "sha256": "a" * 64},
		validation_implementation_commit="b" * 40,
	)

	bundle_file = output / "benchmark.json"
	domain_file = output / "domains/tiny.json"
	assert manifest["benchmark_sha256"] == _sha256(bundle_file)
	assert manifest["domain_datasets"] == [
		{
			"case_count": 2,
			"domain": "tiny",
			"path": "domains/tiny.json",
			"sha256": _sha256(domain_file),
		},
	]
	assert json.loads((output / "manifest.json").read_text()) == manifest
	validate_temporal_goal_benchmark_bundle(
		json.loads(bundle_file.read_text()),
		benchmark_root=output,
		domains_root=tmp_path / "src/domains",
	)


def test_bundle_validation_rejects_modified_domain_dataset(tmp_path: Path) -> None:
	inputs = _benchmark_inputs(tmp_path)
	output = tmp_path / "paper-benchmark"
	write_temporal_goal_benchmark(
		**inputs,
		output_dir=output,
		source_delivery_archive={"filename": "delivery.tar.gz", "sha256": "a" * 64},
		validation_implementation_commit="b" * 40,
	)
	domain_file = output / "domains/tiny.json"
	domain_file.write_text(domain_file.read_text() + "\n")

	with pytest.raises(ValueError, match="SHA-256"):
		validate_temporal_goal_benchmark_bundle(
			json.loads((output / "benchmark.json").read_text()),
			benchmark_root=output,
			domains_root=tmp_path / "src/domains",
		)


def _benchmark_inputs(tmp_path: Path) -> dict[str, Path]:
	domain_dir = tmp_path / "src/domains/tiny"
	(domain_dir / "test").mkdir(parents=True)
	(domain_dir / "domain.pddl").write_text("(define (domain tiny))\n")
	for problem_name in ("p01", "p02"):
		(domain_dir / f"test/{problem_name}.pddl").write_text(
			f"(define (problem {problem_name}) (:domain tiny))\n",
		)
	handoff_manifest = tmp_path / "handoff_manifest.json"
	handoff_manifest.write_text(
		json.dumps(
			{
				"benchmark_id": "tiny-temporal-v1",
				"prompt_source_commit": "c" * 40,
				"required_primary_llm_call_count": 1,
				"row_count": 2,
			},
		),
	)
	manifest_file = tmp_path / "natural_language_manifest.jsonl"
	manifest_rows = [
		{
			"sample_id": f"tiny_{problem_name}",
			"domain": "tiny",
			"problem_file": f"src/domains/tiny/test/{problem_name}.pddl",
			"source_text": "Reach level one, then later become done.",
			"profile": "ordered_two_milestone",
			"construction_tier": "primary",
			"declared_parameters": [{"name": "X", "pddl_type": "item"}],
			"constraints": [],
			"semantic_signature": "semantic-1",
		}
		for problem_name in ("p01", "p02")
	]
	_write_jsonl(manifest_file, manifest_rows)
	worklist_file = tmp_path / "translation_worklist.jsonl"
	_write_jsonl(
		worklist_file,
		[
			{
				**manifest_rows[0],
				"translation_id": "tpl_1",
				"translation_input_signature": "input-1",
				"representative_sample_id": "tiny_p01",
				"member_sample_ids": ["tiny_p01", "tiny_p02"],
			},
		],
	)
	prediction = {
		"schema_version": 1,
		"sample_id": "tiny_p01",
		"temporal_logic": "LTLf",
		"ltlf_formula": "F(a0 & X(F(a1)))",
		"atoms": [
			{
				"symbol": "a0",
				"kind": "numeric_equality",
				"function": "level",
				"args": ["X"],
				"value": 1,
			},
			{
				"symbol": "a1",
				"kind": "predicate",
				"predicate": "done",
				"args": ["X"],
			},
		],
		"declared_parameters": [{"name": "X", "pddl_type": "item"}],
		"constraints": [],
		"status": "supported",
	}
	predictions_file = tmp_path / "translation_predictions.jsonl"
	_write_jsonl(
		predictions_file,
		[
			{
				"schema_version": 1,
				"translation_id": "tpl_1",
				"outcome": "accepted",
				"attempt_count": 1,
				"model_id": "test-model",
				"model_parameters": {"temperature": 0},
				"prompt_config": "full",
				"prompt_source_commit": "c" * 40,
				"raw_response": json.dumps(prediction),
				"prediction": prediction,
				"terminal_error": None,
			},
		],
	)
	translation_results_file = tmp_path / "translation_results.jsonl"
	_write_jsonl(
		translation_results_file,
		[
			{
				"translation_id": "tpl_1",
				"sample_id": "tiny_p01",
				"status": "semantically_equivalent",
				"success": True,
				"dfa_equivalence": {
					"equivalent": True,
					"gold_state_count": 3,
					"prediction_state_count": 3,
					"explored_product_state_count": 3,
				},
			},
		],
	)
	problem_results_file = tmp_path / "problem_results.jsonl"
	_write_jsonl(
		problem_results_file,
		[
			{
				"sample_id": f"tiny_{problem_name}",
				"domain": "tiny",
				"translation_id": "tpl_1",
				"status": "witness_accepted",
				"success": True,
				"witness_validation": {
					"action_count": 2,
					"state_count": 3,
					"replay_valid": True,
					"state_fingerprints_match": True,
					"gold_accepted": True,
					"prediction_accepted": True,
				},
			}
			for problem_name in ("p01", "p02")
		],
	)
	datasets = tmp_path / "validated_append_datasets"
	datasets.mkdir()
	(datasets / "tiny.json").write_text(
		json.dumps(
			{
				"schema_version": 1,
				"goal_specification_kind": "temporal_extended_goal",
				"temporal_logic": "LTLf",
				"domain": "tiny",
				"cases": {
					f"tiny_{problem_name}": {
						"goal_name": f"g_tiny_{problem_name}",
						"problem_file": f"src/domains/tiny/test/{problem_name}.pddl",
						"source_text": "Reach level one, then later become done.",
						"ltlf_formula": "F(a0 & X(F(a1)))",
						"atoms": [
							{"symbol": "a0", "predicate": "level", "args": ["X", "1"]},
							{"symbol": "a1", "predicate": "done", "args": ["X"]},
						],
						"bindings": {"X": f"object{index}"},
						"atom_vocabulary": "pddl_fluents",
						"status": "supported",
					}
					for index, problem_name in enumerate(("p01", "p02"), start=1)
				},
			},
			sort_keys=True,
		),
	)
	return {
		"handoff_manifest_file": handoff_manifest,
		"manifest_file": manifest_file,
		"worklist_file": worklist_file,
		"predictions_file": predictions_file,
		"translation_results_file": translation_results_file,
		"problem_results_file": problem_results_file,
		"validated_append_datasets_dir": datasets,
		"domains_root": tmp_path / "src/domains",
	}


def _read_jsonl(path: Path) -> list[dict[str, object]]:
	return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
	path.write_text(
		"".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
		encoding="utf-8",
	)


def _sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()
