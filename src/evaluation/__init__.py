"""Evaluation support exports."""

from __future__ import annotations

from typing import Any

__all__ = [
	"DFABuilder",
	"LTLfToDFA",
	"compare_gold_and_prediction",
	"build_dfa_from_ltlf",
	"run_temporal_goal_validation_batch",
	"validate_execution_trace",
	"validate_prediction_on_witness",
]


def __getattr__(name: str) -> Any:
	if name in {
		"DFABuilder",
		"LTLfToDFA",
		"build_dfa_from_ltlf",
	}:
		from .temporal_compilation import (
			DFABuilder,
			LTLfToDFA,
			build_dfa_from_ltlf,
		)

		return {
			"DFABuilder": DFABuilder,
			"LTLfToDFA": LTLfToDFA,
			"build_dfa_from_ltlf": build_dfa_from_ltlf,
		}[name]
	if name in {
		"compare_gold_and_prediction",
		"validate_execution_trace",
		"validate_prediction_on_witness",
	}:
		from .temporal_goal_validation import (
			compare_gold_and_prediction,
			validate_execution_trace,
			validate_prediction_on_witness,
		)

		return {
			"compare_gold_and_prediction": compare_gold_and_prediction,
			"validate_execution_trace": validate_execution_trace,
			"validate_prediction_on_witness": validate_prediction_on_witness,
		}[name]
	if name == "run_temporal_goal_validation_batch":
		from .temporal_validation_batch import run_temporal_goal_validation_batch

		return run_temporal_goal_validation_batch
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
