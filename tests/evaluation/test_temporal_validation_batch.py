from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.temporal_validation_batch import parse_translation_prediction_record
from evaluation.temporal_validation_batch import run_temporal_goal_validation_batch
from domain_level_planning.lifted_ltlf_goal_schema import load_lifted_ltlf_goal_dataset
from temporal_input.nl_benchmark import replay_ground_action_trace


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_parse_translation_prediction_record_requires_auditable_metadata() -> None:
	record = parse_translation_prediction_record(_prediction_record())

	assert record.translation_id == "tpl_1"
	assert record.outcome == "accepted"
	assert record.attempt_count == 1

	with pytest.raises(ValueError, match="exactly"):
		parse_translation_prediction_record({**_prediction_record(), "extra": True})

	with pytest.raises(ValueError, match="raw_response"):
		parse_translation_prediction_record(
			{**_prediction_record(), "raw_response": "{}"},
		)


def test_temporal_validation_batch_produces_translation_problem_and_append_artifacts(
	tmp_path: Path,
	monkeypatch,
) -> None:
	monkeypatch.setenv(
		"MONA_BIN",
		str(PROJECT_ROOT / ".external/mona-1.4/Front/mona"),
	)
	domain_dir = tmp_path / "src/domains/tiny"
	(domain_dir / "test").mkdir(parents=True)
	domain_file = domain_dir / "domain.pddl"
	problem_file = domain_dir / "test/p01.pddl"
	domain_file.write_text(
		"""
(define (domain tiny)
  (:requirements :strips :typing)
  (:types item)
  (:predicates (seed ?x - item) (done ?x - item))
  (:action finish
    :parameters (?x - item)
    :precondition (seed ?x)
    :effect (and (not (seed ?x)) (done ?x))))
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
(define (problem tiny-p01)
  (:domain tiny)
  (:objects object1 - item)
  (:init (seed object1))
  (:goal (seed object1)))
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	replay = replay_ground_action_trace(
		domain_file=domain_file,
		problem_file=problem_file,
		action_lines=("(finish object1)",),
	)
	handoff = tmp_path / "handoff"
	benchmark = tmp_path / "benchmark"
	(handoff / "domains/tiny").mkdir(parents=True)
	(benchmark / "domains/tiny").mkdir(parents=True)
	manifest_row = {
		"sample_id": "tiny_p01",
		"domain": "tiny",
		"problem_file": "src/domains/tiny/test/p01.pddl",
		"catalog_file": "domains/tiny/catalog.json",
		"status": "constructed_temporal_query",
		"source_text": "Given parameter X, eventually predicate done holds for X.",
		"declared_parameters": [{"name": "X", "pddl_type": "item"}],
		"constraints": [],
		"parameter_semantics": "externally_bound",
		"semantic_signature": "semantic-1",
	}
	worklist_row = {
		**manifest_row,
		"translation_id": "tpl_1",
		"translation_input_signature": "input-1",
		"member_sample_ids": ["tiny_p01"],
		"member_count": 1,
	}
	catalog = {
		"schema_version": 1,
		"domain": "tiny",
		"predicates": [
			{"name": "seed", "argument_types": ["item"]},
			{"name": "done", "argument_types": ["item"]},
		],
		"numeric_functions": [],
		"constants": [],
		"type_parents": {"item": "object"},
	}
	audit_row = {
		**manifest_row,
		"gold_atoms": [
			{
				"atom_id": "a0",
				"kind": "predicate",
				"predicate": "done",
				"arguments": ["X"],
			},
		],
		"gold_formula_ast": {
			"operator": "eventually",
			"operand": {"operator": "atom", "atom_id": "a0"},
		},
		"assignment": {"X": "object1"},
		"witness_actions": ["(finish object1)"],
		"state_fingerprints": [state.fingerprint() for state in replay.states],
	}
	_write_jsonl(handoff / "natural_language_manifest.jsonl", [manifest_row])
	_write_jsonl(handoff / "translation_worklist.jsonl", [worklist_row])
	(handoff / "handoff_manifest.json").write_text(
		json.dumps({"prompt_source_commit": "abc123"}),
		encoding="utf-8",
	)
	(handoff / "domains/tiny/catalog.json").write_text(
		json.dumps(catalog),
		encoding="utf-8",
	)
	_write_jsonl(benchmark / "domains/tiny/construction_audit.jsonl", [audit_row])
	predictions_file = tmp_path / "predictions.jsonl"
	_write_jsonl(predictions_file, [_prediction_record()])

	summary = run_temporal_goal_validation_batch(
		handoff_root=handoff,
		benchmark_root=benchmark,
		predictions_file=predictions_file,
		output_dir=tmp_path / "validation",
		project_root=tmp_path,
		domains_root=tmp_path / "src/domains",
	)

	assert summary["translation_success_count"] == 1
	assert summary["problem_success_count"] == 1
	dataset = json.loads(
		(tmp_path / "validation/validated_append_datasets/tiny.json").read_text(
			encoding="utf-8",
		),
	)
	assert dataset["cases"]["tiny_p01"]["ltlf_formula"] == "F(a0)"
	assert dataset["cases"]["tiny_p01"]["bindings"] == {"X": "object1"}
	parsed_dataset = load_lifted_ltlf_goal_dataset(
		tmp_path / "validation/validated_append_datasets/tiny.json",
	)
	assert parsed_dataset.cases[0].atoms[0].symbol == "a0"


def _prediction_record() -> dict[str, object]:
	prediction = {
		"schema_version": 1,
		"sample_id": "tiny_p01",
		"temporal_logic": "LTLf",
		"ltlf_formula": "F(a0)",
		"atoms": [
			{
				"symbol": "a0",
				"kind": "predicate",
				"predicate": "done",
				"args": ["X"],
			},
		],
		"declared_parameters": [{"name": "X", "pddl_type": "item"}],
		"constraints": [],
		"status": "supported",
	}
	return {
		"schema_version": 1,
		"translation_id": "tpl_1",
		"outcome": "accepted",
		"attempt_count": 1,
		"model_id": "test-model",
		"model_parameters": {"temperature": 0},
		"prompt_config": "full",
		"prompt_source_commit": "abc123",
		"raw_response": json.dumps(prediction),
		"prediction": prediction,
		"terminal_error": None,
	}


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		"".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
		encoding="utf-8",
	)
