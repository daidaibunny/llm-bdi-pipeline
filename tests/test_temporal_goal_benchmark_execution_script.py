from __future__ import annotations

import pytest

from scripts.run_temporal_goal_benchmark_execution import (
	benchmark_prediction,
)
from scripts.run_temporal_goal_benchmark_execution import summarize_execution_records
from scripts.run_temporal_goal_benchmark_execution import verify_invocation_binding


def test_benchmark_prediction_preserves_predicate_and_numeric_atoms() -> None:
	prediction = benchmark_prediction(
		"numeric_ferry_p0_03",
		{
			"ltlf_formula": "F(a0 & X(F(a1)))",
			"atoms": [
				{
					"symbol": "a0",
					"kind": "predicate",
					"predicate": "at-ferry",
					"args": ["X"],
				},
				{
					"symbol": "a1",
					"kind": "numeric_equality",
					"function": "ferry-capacity",
					"args": [],
					"value": 3,
				},
			],
			"declared_parameters": [{"name": "X", "pddl_type": "location"}],
			"constraints": [],
		},
	)

	assert prediction.sample_id == "numeric_ferry_p0_03"
	assert prediction.atoms[0].semantic_key == (
		"predicate",
		"at-ferry",
		("X",),
		None,
	)
	assert prediction.atoms[1].semantic_key == (
		"numeric_equality",
		"ferry-capacity",
		(),
		3,
	)


def test_verify_invocation_binding_rejects_release_audit_mismatch() -> None:
	with pytest.raises(ValueError, match="invocation binding differs"):
		verify_invocation_binding(
			sample_id="tiny_p01",
			benchmark_case={"bindings": {"X": "a"}},
			audit_row={"assignment": {"X": "b"}},
		)


def test_summarize_execution_records_keeps_failure_stages_distinct() -> None:
	summary = summarize_execution_records(
		(
			{
				"domain": "tiny",
				"profile": "ordered_two_milestone",
				"status": "success",
				"success": True,
			},
			{
				"domain": "tiny",
				"profile": "persistence_until",
				"status": "unsupported_temporal_controller",
				"success": False,
			},
			{
				"domain": "other",
				"profile": "ordered_two_milestone",
				"status": "jason_timeout",
				"success": False,
			},
		),
	)

	assert summary["total"] == 3
	assert summary["success_count"] == 1
	assert summary["status_counts"] == {
		"jason_timeout": 1,
		"success": 1,
		"unsupported_temporal_controller": 1,
	}
	assert summary["domains"]["tiny"]["success_count"] == 1
	assert summary["profiles"]["persistence_until"]["success_count"] == 0
