from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from evaluation.temporal_goal_validation import compare_gold_and_prediction
from evaluation.temporal_goal_validation import expand_translation_predictions
from evaluation.temporal_goal_validation import rewrite_problem_with_neutral_goal
from evaluation.temporal_goal_validation import validate_execution_trace
from evaluation.temporal_goal_validation import validate_prediction_on_witness
from temporal_specification.prediction_validation import validate_prediction_payload


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_expand_translation_predictions_covers_each_problem_once() -> None:
	worklist = [
		{
			"translation_id": "tpl_1",
			"sample_id": "sample_1",
			"member_sample_ids": ["sample_1", "sample_2"],
		},
	]
	predictions = [
		{
			"translation_id": "tpl_1",
			"prediction": {"sample_id": "sample_1"},
		},
	]

	expanded = expand_translation_predictions(
		worklist_rows=worklist,
		prediction_rows=predictions,
		expected_sample_ids={"sample_1", "sample_2"},
	)

	assert set(expanded) == {"sample_1", "sample_2"}
	assert expanded["sample_2"]["prediction"]["sample_id"] == "sample_1"


def test_expand_translation_predictions_rejects_duplicate_membership() -> None:
	with pytest.raises(ValueError, match="exactly once"):
		expand_translation_predictions(
			worklist_rows=[
				{
					"translation_id": "tpl_1",
					"sample_id": "sample_1",
					"member_sample_ids": ["sample_1", "sample_1"],
				},
			],
			prediction_rows=[
				{"translation_id": "tpl_1", "prediction": {"sample_id": "sample_1"}},
			],
			expected_sample_ids={"sample_1"},
		)


def test_compare_gold_and_prediction_accepts_semantic_reordering(monkeypatch) -> None:
	monkeypatch.setenv(
		"MONA_BIN",
		str(PROJECT_ROOT / ".external" / "mona-1.4" / "Front" / "mona"),
	)
	audit = _audit_row(
		formula={
			"operator": "eventually",
			"operand": {
				"operator": "and",
				"operands": [
					{"operator": "atom", "atom_id": "a0"},
					{"operator": "atom", "atom_id": "a1"},
				],
			},
		},
	)
	prediction = _validated_prediction("F(a0 & a1)", reverse_atom_meanings=True)

	result = compare_gold_and_prediction(audit_row=audit, prediction=prediction)

	assert result.equivalent is True
	assert result.counterexample_trace == ()


def test_compare_gold_and_prediction_returns_distinguishing_trace(monkeypatch) -> None:
	monkeypatch.setenv(
		"MONA_BIN",
		str(PROJECT_ROOT / ".external" / "mona-1.4" / "Front" / "mona"),
	)
	audit = _audit_row(
		formula={
			"operator": "eventually",
			"operand": {
				"operator": "and",
				"operands": [
					{"operator": "atom", "atom_id": "a0"},
					{"operator": "atom", "atom_id": "a1"},
				],
			},
		},
	)
	prediction = _validated_prediction("F(a0)")

	result = compare_gold_and_prediction(audit_row=audit, prediction=prediction)

	assert result.equivalent is False
	assert result.counterexample_trace
	assert result.gold_accepts_counterexample != result.prediction_accepts_counterexample


def test_compare_gold_and_unsatisfiable_prediction_is_semantic_mismatch(monkeypatch) -> None:
	monkeypatch.setenv(
		"MONA_BIN",
		str(PROJECT_ROOT / ".external" / "mona-1.4" / "Front" / "mona"),
	)
	audit = _audit_row(
		formula={
			"operator": "eventually",
			"operand": {"operator": "atom", "atom_id": "a0"},
		},
	)
	prediction = _validated_prediction("F(a0 & !a0)")

	result = compare_gold_and_prediction(audit_row=audit, prediction=prediction)

	assert result.equivalent is False
	assert result.prediction_accepts_counterexample is False


def test_validate_prediction_on_real_hidden_witness(monkeypatch) -> None:
	monkeypatch.setenv(
		"MONA_BIN",
		str(PROJECT_ROOT / ".external" / "mona-1.4" / "Front" / "mona"),
	)
	audit_path = (
		PROJECT_ROOT
		/ "artifacts"
		/ "temporal_nl_benchmarks"
		/ "temporal-nl-v1-20260711-final"
		/ "domains"
		/ "blocksworld-on"
		/ "construction_audit.jsonl"
	)
	audit = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
	prediction = _validated_prediction_from_audit(audit)

	result = validate_prediction_on_witness(
		audit_row=audit,
		prediction=prediction,
		domain_file=PROJECT_ROOT / "src/domains/blocksworld-on/domain.pddl",
		problem_file=PROJECT_ROOT / audit["problem_file"],
	)

	assert result.replay_valid is True
	assert result.state_fingerprints_match is True
	assert result.gold_accepted is True
	assert result.prediction_accepted is True


def test_rewrite_problem_with_neutral_goal_preserves_other_sections(tmp_path: Path) -> None:
	source = PROJECT_ROOT / "src/domains/blocksworld-on/test/p-50-0.pddl"
	target = tmp_path / "neutral.pddl"

	rewrite_problem_with_neutral_goal(source, target)

	original = source.read_text(encoding="utf-8")
	rewritten = target.read_text(encoding="utf-8")
	assert "(:goal (and))" in rewritten
	assert "(:init" in rewritten
	assert "(:objects" in rewritten
	assert rewritten != original


def test_validate_execution_trace_uses_neutral_goal_val_and_gold_dfa(
	tmp_path: Path,
	monkeypatch,
) -> None:
	monkeypatch.setenv(
		"MONA_BIN",
		str(PROJECT_ROOT / ".external" / "mona-1.4" / "Front" / "mona"),
	)
	monkeypatch.setattr(
		"evaluation.temporal_goal_validation.run_external_plan_verifier",
		lambda **kwargs: SimpleNamespace(
			attempted=True,
			success=True,
			error=None,
		),
	)
	audit_path = (
		PROJECT_ROOT
		/ "artifacts/temporal_nl_benchmarks"
		/ "temporal-nl-v1-20260711-final"
		/ "domains/blocksworld-on/construction_audit.jsonl"
	)
	audit = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
	prediction = _validated_prediction_from_audit(audit)
	plan_file = tmp_path / "witness.plan"
	plan_file.write_text("\n".join(audit["witness_actions"]) + "\n", encoding="utf-8")

	result = validate_execution_trace(
		audit_row=audit,
		prediction=prediction,
		domain_file=PROJECT_ROOT / "src/domains/blocksworld-on/domain.pddl",
		problem_file=PROJECT_ROOT / audit["problem_file"],
		plan_file=plan_file,
		output_dir=tmp_path / "validation",
		plan_verifier_command="Validate",
	)

	assert result.replay_valid is True
	assert result.val_success is True
	assert result.gold_accepted is True
	assert result.prediction_accepted is True
	assert result.success is True


def test_validate_execution_trace_accepts_zero_action_singleton_state(
	tmp_path: Path,
	monkeypatch,
) -> None:
	monkeypatch.setenv(
		"MONA_BIN",
		str(PROJECT_ROOT / ".external" / "mona-1.4" / "Front" / "mona"),
	)
	verifier_calls: list[dict[str, object]] = []
	monkeypatch.setattr(
		"evaluation.temporal_goal_validation.run_external_plan_verifier",
		lambda **kwargs: verifier_calls.append(kwargs),
	)
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	plan_file = tmp_path / "empty.plan"
	domain_file.write_text(
		"""
(define (domain tiny)
 (:requirements :strips :typing)
 (:types item)
 (:predicates (ready ?x - item))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
(define (problem tiny-problem)
 (:domain tiny)
 (:objects object1 - item)
 (:init (ready object1))
 (:goal (and))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	plan_file.write_text("", encoding="utf-8")
	audit = _audit_row(formula={"operator": "atom", "atom_id": "a0"})
	prediction = _validated_prediction("a0")

	result = validate_execution_trace(
		audit_row=audit,
		prediction=prediction,
		domain_file=domain_file,
		problem_file=problem_file,
		plan_file=plan_file,
		output_dir=tmp_path / "validation",
		plan_verifier_command="Validate",
	)

	assert verifier_calls == []
	assert result.action_count == 0
	assert result.state_count == 1
	assert result.replay_valid is True
	assert result.val_attempted is False
	assert result.val_success is None
	assert result.gold_accepted is True
	assert result.prediction_accepted is True
	assert result.legality_certificate == "vacuous_zero_action_pddl_replay"
	assert result.success is True


def _audit_row(*, formula: dict[str, object]) -> dict[str, object]:
	return {
		"sample_id": "tiny_1",
		"gold_atoms": [
			{
				"atom_id": "a0",
				"kind": "predicate",
				"predicate": "ready",
				"arguments": ["X"],
			},
			{
				"atom_id": "a1",
				"kind": "predicate",
				"predicate": "done",
				"arguments": ["X"],
			},
		],
		"gold_formula_ast": formula,
		"assignment": {"X": "object1"},
		"witness_actions": [],
		"state_fingerprints": [],
	}


def _validated_prediction(formula: str, *, reverse_atom_meanings: bool = False):
	catalog = {
		"domain": "tiny",
		"predicates": [
			{"name": "ready", "argument_types": ["item"]},
			{"name": "done", "argument_types": ["item"]},
		],
		"numeric_functions": [],
		"constants": [],
		"type_parents": {"item": "object"},
	}
	used = []
	atom_meanings = (
		(("a0", "done"), ("a1", "ready"))
		if reverse_atom_meanings
		else (("a0", "ready"), ("a1", "done"))
	)
	for symbol, predicate in atom_meanings:
		if symbol in formula:
			used.append(
				{
					"symbol": symbol,
					"kind": "predicate",
					"predicate": predicate,
					"args": ["X"],
				},
			)
	payload = {
		"schema_version": 1,
		"sample_id": "tiny_1",
		"temporal_logic": "LTLf",
		"ltlf_formula": formula,
		"atoms": used,
		"declared_parameters": [{"name": "X", "pddl_type": "item"}],
		"constraints": [],
		"status": "supported",
	}
	return validate_prediction_payload(
		payload,
		expected_sample={
			"sample_id": "tiny_1",
			"declared_parameters": payload["declared_parameters"],
			"constraints": [],
		},
		catalog=catalog,
	)


def _validated_prediction_from_audit(audit: dict[str, object]):
	formula = _render_audit_formula(audit["gold_formula_ast"])
	atoms = []
	for atom in audit["gold_atoms"]:
		item = {
			"symbol": atom["atom_id"],
			"kind": atom["kind"],
			"args": atom["arguments"],
		}
		if atom["kind"] == "predicate":
			item["predicate"] = atom["predicate"]
		else:
			item["function"] = atom["function"]
			item["value"] = atom["value"]
		atoms.append(item)
	catalog_path = (
		PROJECT_ROOT
		/ "artifacts/temporal_nl_benchmarks/temporal-nl-v1-20260711-final"
		/ audit["catalog_file"]
	)
	catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
	payload = {
		"schema_version": 1,
		"sample_id": audit["sample_id"],
		"temporal_logic": "LTLf",
		"ltlf_formula": formula,
		"atoms": atoms,
		"declared_parameters": audit["declared_parameters"],
		"constraints": audit["constraints"],
		"status": "supported",
	}
	return validate_prediction_payload(payload, expected_sample=audit, catalog=catalog)


def _render_audit_formula(node) -> str:
	operator = node["operator"]
	if operator == "atom":
		return node["atom_id"]
	if operator == "not":
		return f"!({_render_audit_formula(node['operand'])})"
	if operator == "and":
		return "(" + " & ".join(_render_audit_formula(item) for item in node["operands"]) + ")"
	if operator == "next":
		return f"X({_render_audit_formula(node['operand'])})"
	if operator == "eventually":
		return f"F({_render_audit_formula(node['operand'])})"
	if operator == "until":
		return f"({_render_audit_formula(node['left'])}) U ({_render_audit_formula(node['right'])})"
	raise AssertionError(operator)
