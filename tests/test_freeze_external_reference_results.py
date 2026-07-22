from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import freeze_external_reference_results


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = PROJECT_ROOT / "paper_artifacts/gp2pl_evaluation/v1"
RESULT_FILE = RELEASE_ROOT / "external_reference_results.json"


def test_direct_temporal_row_separates_unsupported_cases_from_par2() -> None:
	row = freeze_external_reference_results._direct_temporal_row(
		method="TIDE + LAMA",
		scope="Supported Boolean TEG",
		records=(
			{
				"supported": True,
				"success": True,
				"status": "valid",
				"elapsed_seconds": 2.0,
				"execution_validation": {
					"replay_valid": True,
					"val_success": True,
					"gold_accepted": True,
					"prediction_accepted": True,
				},
			},
			{
				"supported": True,
				"success": False,
				"status": "no_plan",
				"elapsed_seconds": 20.0,
			},
			{
				"supported": False,
				"success": False,
				"status": "unsupported_numeric_pddl",
				"elapsed_seconds": 0.0,
			},
		),
	)

	assert row["method"] == "TIDE + LAMA"
	assert row["case_count"] == 2
	assert row["supported_case_count"] == 2
	assert row["unsupported_case_count"] == 1
	assert row["valid_trace_count"] == 1
	assert row["par2_seconds"] == pytest.approx(1801.0)


def test_direct_temporal_row_requires_replay_and_both_dfa_oracles() -> None:
	row = freeze_external_reference_results._direct_temporal_row(
		method="TIDE + LAMA",
		scope="Supported Boolean TEG",
		records=(
			{
				"supported": True,
				"success": True,
				"status": "valid",
				"elapsed_seconds": 2.0,
				"execution_validation": {
					"val_success": True,
					"gold_accepted": True,
					"prediction_accepted": True,
				},
			},
		),
	)

	assert row["valid_trace_count"] == 0
	assert row["par2_seconds"] == pytest.approx(3600.0)


def test_temporal_freeze_rejects_a_different_case_set_with_the_same_size(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	monkeypatch.setitem(
		freeze_external_reference_results.TEMPORAL_CONTRACT,
		"count",
		2,
	)
	benchmark = {
		"domains": {
			"example": {
				"cases": {
					"case_a": {},
					"case_b": {},
				},
			},
		},
	}
	payload = {
		"selected_case_count": 2,
		"results": [
			{"sample_id": "case_a"},
			{"sample_id": "case_c"},
		],
	}

	with pytest.raises(ValueError, match="identifiers differ"):
		freeze_external_reference_results._validate_temporal_case_set(
			payload,
			benchmark=benchmark,
		)


def test_tide_freeze_rejects_a_changed_search_configuration() -> None:
	payload = {
		"method": "TIDE + LAMA",
		"variant": "tide_lama",
		"parameters": {
			"tide_configuration": "different",
			"tide_internal_runs_per_case": 1,
			"tide_subproblem_timeout_ms": 60_000,
		},
	}

	with pytest.raises(ValueError, match="search protocol"):
		freeze_external_reference_results._validate_tide_temporal_toolchain(payload)


def test_registered_external_reference_result_is_complete_portable_and_manifested() -> None:
	result = json.loads(RESULT_FILE.read_text(encoding="utf-8"))

	assert result["artifact_kind"] == "gp2pl_external_reference_results"
	assert result["schema_version"] == 2
	assert result["protocol"]["achievement_case_count"] == 1228
	assert result["protocol"]["temporal_case_count_per_method"] == 1228
	assert result["protocol"]["tide_num_workers"] == 12
	assert result["protocol"]["record_count"] == 3684
	assert len(result["records"]) == 3684
	assert len(
		{
			(record["record_kind"], record["method"], record["case_id"])
			for record in result["records"]
		}
	) == 3684
	assert "/Users/" not in RESULT_FILE.read_text(encoding="utf-8")

	rows = {row["method"]: row for row in result["rows"]}
	assert rows["MOOSE"]["par2_seconds"] is None
	assert rows["Raw MOOSE extension"]["par2_seconds"] is None
	assert rows["LAMA"]["valid_trace_count"] == 591
	assert rows["LAMA"]["par2_seconds"] == pytest.approx(1178.449831605116)
	assert rows["MRP+HJ"]["valid_trace_count"] == 253
	assert rows["MRP+HJ"]["par2_seconds"] == pytest.approx(1127.3508548983668)
	assert rows["FOND4LTLf + LAMA"]["supported_case_count"] == 492
	assert rows["FOND4LTLf + LAMA"]["unsupported_case_count"] == 736
	assert rows["FOND4LTLf + LAMA"]["valid_trace_count"] == 298
	assert rows["FOND4LTLf + LAMA"]["par2_seconds"] == pytest.approx(
		1457.5163589505448,
	)
	assert rows["TIDE + LAMA"]["supported_case_count"] == 868
	assert rows["TIDE + LAMA"]["unsupported_case_count"] == 360
	assert rows["TIDE + LAMA"]["valid_trace_count"] == 675
	assert rows["TIDE + LAMA"]["par2_seconds"] == pytest.approx(
		821.0181061779431,
	)
	assert result["status_counts"]["direct_temporal_by_method"]["TIDE + LAMA"] == {
		"no_plan": 188,
		"planner_timeout": 5,
		"unsupported_numeric_formula": 207,
		"unsupported_numeric_pddl": 153,
		"valid": 675,
	}
	domains = {row["domain"]: row for row in result["domain_rows"]}
	assert len(domains) == 16
	assert domains["barman"]["tide_lama"] == {
		"supported_case_count": 90,
		"valid_trace_count": 63,
	}
	assert domains["blocksworld-clear"]["fond4ltlf_lama"] == {
		"supported_case_count": 19,
		"valid_trace_count": 0,
	}
	assert domains["numeric-ferry"]["fond4ltlf_lama"] is None
	assert domains["numeric-ferry"]["tide_lama"] is None
	assert domains["numeric-ferry"]["lama"] is None
	assert domains["numeric-ferry"]["mrp_hj"] == {
		"supported_case_count": 90,
		"valid_trace_count": 60,
	}
	for record in result["records"]:
		if record["record_kind"] == "direct_temporal" and record["valid"] is True:
			assert all(
				record["execution_validation"].get(key) is True
				for key in (
					"replay_valid",
					"val_success",
					"gold_accepted",
					"prediction_accepted",
				)
			)
	assert "provenance" not in result

	manifest = json.loads((RELEASE_ROOT / "manifest.json").read_text(encoding="utf-8"))
	assert manifest["external_reference_record_count"] == 3684
	for relative_path in manifest["files"]:
		release_file = RELEASE_ROOT / relative_path
		assert release_file.is_file()


def test_external_reference_table_distinguishes_failure_from_unsupported() -> None:
	result = json.loads(RESULT_FILE.read_text(encoding="utf-8"))
	table = freeze_external_reference_results.render_external_table(
		{
			"external": result["rows"],
			"external_domains": result["domain_rows"],
		},
	)

	assert "Entries are valid/supported" in table
	assert "0/19" in table
	assert "barman &" in table
	assert "63/90" in table
	assert "numeric-ferry &" in table
	assert "--" in table
