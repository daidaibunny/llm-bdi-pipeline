from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.generate_aaai_comparison_tables import build_comparison_dataset
from scripts.generate_aaai_comparison_tables import render_atomic_table
from scripts.generate_aaai_comparison_tables import render_external_table
from scripts.generate_aaai_comparison_tables import render_temporal_table


ATOMIC_VARIANTS = (
	("validated_evidence_adapter", "Evidence Adapter"),
	("action_only_closure", "Action Closure"),
	("maximal_certified_program", "Maximal Certified"),
	("full", "Full Compiler"),
)
TEMPORAL_VARIANTS = (
	("dfa_aware_unprotected", "Unprotected DFA"),
	("certified_flat", "Certified Flat"),
	("certified_balanced", "Certified Balanced"),
	("completion_boundary_monitor", "Completion Monitor"),
)


def test_build_comparison_dataset_aggregates_registered_matrix(tmp_path: Path) -> None:
	paired = _write_json(tmp_path / "paired.json", _paired_fixture())
	raw_summaries = tuple(
		(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
		for seed in range(5)
	)
	instance_summary = _write_json(tmp_path / "instances.json", _instance_fixture())
	direct_summary = _write_json(tmp_path / "direct.json", _direct_fixture())
	challenge_summary = _write_json(tmp_path / "challenge.json", _challenge_fixture())

	result = build_comparison_dataset(
		paired_results_file=paired,
		raw_moose_summaries=raw_summaries,
		instance_reference_summary_file=instance_summary,
		direct_temporal_summary_file=direct_summary,
		challenge_summary_file=challenge_summary,
	)

	assert [row["method"] for row in result["atomic"]] == [
		name for _variant, name in ATOMIC_VARIANTS
	]
	assert result["atomic"][0]["compiled_count"] == 5
	assert result["atomic"][0]["compiled_total"] == 5
	assert result["atomic"][0]["covered_target_count"] == 5
	assert result["atomic"][0]["producible_target_count"] == 10
	assert result["atomic"][0]["valid_trace_count"] == 5
	assert result["atomic"][0]["test_count"] == 10
	assert result["atomic"][0]["mean_branch_count"] == 1
	assert result["atomic"][3]["mean_branch_count"] == 4
	assert result["atomic_joint_action_case_count"] == 5

	assert [row["method"] for row in result["temporal"]] == [
		name for _variant, name in TEMPORAL_VARIANTS
	]
	assert result["temporal"][0]["valid_trace_count"] == 1
	assert result["temporal"][2]["valid_trace_count"] == 2
	assert result["temporal_joint_action_case_count"] == 1
	assert result["temporal"][2]["median_joint_action_count"] == 3

	external = {row["method"]: row for row in result["external"]}
	assert external["Raw MOOSE"]["valid_trace_count"] == 5
	assert external["Raw MOOSE"]["case_count"] == 10
	assert external["LAMA"]["valid_trace_count"] == 1
	assert external["MRP+HJ"]["valid_trace_count"] == 1
	assert external["FOND4LTLf + LAMA"]["supported_case_count"] == 1
	assert external["FOND4LTLf + LAMA"]["unsupported_case_count"] == 1
	assert result["challenges"]["success_count"] == 13


def test_build_comparison_dataset_rejects_incomplete_atomic_pairing(
	tmp_path: Path,
) -> None:
	payload = _paired_fixture()
	payload["atomic_runs"] = payload["atomic_runs"][:-1]
	paired = _write_json(tmp_path / "paired.json", payload)

	with pytest.raises(ValueError, match="atomic run matrix"):
		build_comparison_dataset(
			paired_results_file=paired,
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_comparison_tables_use_short_descriptive_headers(tmp_path: Path) -> None:
	result = build_comparison_dataset(
		paired_results_file=_write_json(tmp_path / "paired.json", _paired_fixture()),
		raw_moose_summaries=tuple(
			(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
			for seed in range(5)
		),
		instance_reference_summary_file=_write_json(
			tmp_path / "instances.json",
			_instance_fixture(),
		),
		direct_temporal_summary_file=_write_json(
			tmp_path / "direct.json",
			_direct_fixture(),
		),
		challenge_summary_file=_write_json(
			tmp_path / "challenge.json",
			_challenge_fixture(),
		),
	)

	atomic = render_atomic_table(result)
	temporal = render_temporal_table(result)
	external = render_external_table(result)
	combined = atomic + temporal + external

	assert "Method & Compiled & Targets & Valid & Branches & KiB & Compile s" in atomic
	assert "Method & Built & Valid & PAR-2 s & Actions & Plans & Fan-out" in temporal
	assert "Method & Scope & Valid & Unsupported & PAR-2 s" in external
	assert "Evidence Adapter" in atomic
	assert "Certified Balanced" in temporal
	assert "FOND4LTLf + LAMA" in external
	assert "C0" not in combined
	assert "T0" not in combined


def _paired_fixture() -> dict[str, object]:
	atomic_runs = []
	for seed in range(5):
		for index, (variant, method) in enumerate(ATOMIC_VARIANTS, start=1):
			validations = [
				_validation("p1", valid=True, actions=index),
				_validation("p2", valid=variant == "full", actions=index + 1),
			]
			atomic_runs.append(
				{
					"seed": seed,
					"variant": variant,
					"method": method,
					"domains": {
						"toy": {
							"compile_success": True,
							"compile_seconds": float(index),
							"readable_policy_sha256": f"raw-{seed}",
							"evidence_program_fingerprint": f"normalized-{seed}",
							"library_metrics": {
								"covered_target_count": 1 if index == 1 else 2,
								"producible_target_count": 2,
								"selected_branch_count": index,
								"context_literal_count": index * 2,
								"body_step_count": index * 3,
								"asl_bytes": index * 1024,
							},
						},
					},
					"summary": {"validations": validations},
				},
			)
	temporal_runs = []
	for index, (variant, method) in enumerate(TEMPORAL_VARIANTS, start=1):
		results = [
			_temporal_result("s1", valid=True, actions=index),
			_temporal_result("s2", valid=index >= 3, actions=index + 1),
		]
		temporal_runs.append(
			{
				"variant": variant,
				"method": method,
				"benchmark_sha256": "benchmark",
				"atomic_library_inputs": {
					"toy": {
						"plan_library_json_sha256": "json",
						"plan_library_asl_sha256": "asl",
					},
				},
				"results": results,
			},
		)
	return {
		"success": True,
		"infrastructure_complete": True,
		"paired_inputs_verified": True,
		"source_revision": _clean_revision(),
		"domains": ["toy"],
		"registered_seeds": [0, 1, 2, 3, 4],
		"atomic_pairing": {"paired": True},
		"temporal_pairing": {"paired": True},
		"atomic_runs": atomic_runs,
		"temporal_runs": temporal_runs,
	}


def _validation(problem: str, *, valid: bool, actions: int) -> dict[str, object]:
	return {
		"domain": "toy",
		"problem_file": f"/test/{problem}.pddl",
		"success": valid,
		"plan_verifier_success": valid,
		"status": "success" if valid else "failed",
		"duration_seconds": 1.0 if valid else 1800.0,
		"action_count": actions,
	}


def _temporal_result(sample: str, *, valid: bool, actions: int) -> dict[str, object]:
	return {
		"sample_id": sample,
		"status": "success" if valid else "jason_failed",
		"success": valid,
		"jason_status": "success" if valid else "failed",
		"duration_seconds": 2.0 if valid else 1800.0,
		"action_count": actions,
		"controller_plan_count": 3,
		"max_trigger_fanout": 2,
		"append_seconds": 0.1,
		"execution_validation": {
			"val_attempted": valid,
			"val_success": valid,
			"gold_accepted": valid,
			"prediction_accepted": valid,
		},
	}


def _raw_fixture(seed: int) -> dict[str, object]:
	return {
		"success": True,
		"source_revision": _clean_revision(),
		"variants": ["raw_moose"],
		"results": [
			_external_result("Raw MOOSE", "p1", valid=True),
			_external_result("Raw MOOSE", "p2", valid=False),
		],
		"seed": seed,
	}


def _instance_fixture() -> dict[str, object]:
	return {
		"success": True,
		"source_revision": _clean_revision(),
		"variants": ["lama", "enhsp_hmrphj"],
		"results": [
			_external_result("LAMA", "p1", valid=True),
			_external_result("MRP+HJ", "n1", valid=True),
		],
	}


def _external_result(method: str, problem: str, *, valid: bool) -> dict[str, object]:
	return {
		"method": method,
		"domain": "toy",
		"problem_file": f"/test/{problem}.pddl",
		"status": "valid" if valid else "timeout",
		"plan_verifier_success": valid,
		"elapsed_seconds": 1.0 if valid else 1800.0,
		"action_count": 1 if valid else None,
	}


def _direct_fixture() -> dict[str, object]:
	return {
		"success": True,
		"source_revision": _clean_revision(),
		"selected_case_count": 2,
		"results": [
			{
				"sample_id": "s1",
				"status": "success",
				"supported": True,
				"success": True,
				"elapsed_seconds": 2.0,
				"action_count": 1,
				"execution_validation": {
					"val_success": True,
					"gold_accepted": True,
					"prediction_accepted": True,
				},
			},
			{
				"sample_id": "s2",
				"status": "unsupported_numeric_pddl",
				"supported": False,
				"success": False,
			},
		],
	}


def _challenge_fixture() -> dict[str, object]:
	return {
		"success": True,
		"source_revision": _clean_revision(),
		"case_count": 13,
		"success_count": 13,
		"records": [{"success": True} for _ in range(13)],
	}


def _clean_revision() -> dict[str, object]:
	return {
		"available": True,
		"commit": "0123456789abcdef",
		"tracked_changes": False,
		"untracked_files": False,
	}


def _write_json(path: Path, payload: dict[str, object]) -> Path:
	path.write_text(json.dumps(payload), encoding="utf-8")
	return path
