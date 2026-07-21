from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import freeze_external_reference_results


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = PROJECT_ROOT / "paper_artifacts/gp2pl_evaluation/v1"
RESULT_FILE = RELEASE_ROOT / "external_reference_results.json"


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


def test_registered_external_reference_result_is_complete_portable_and_manifested() -> None:
	result = json.loads(RESULT_FILE.read_text(encoding="utf-8"))

	assert result["artifact_kind"] == "gp2pl_external_reference_results"
	assert result["protocol"]["achievement_case_count"] == 1228
	assert result["protocol"]["temporal_case_count"] == 1228
	assert result["protocol"]["record_count"] == 2456
	assert len(result["records"]) == 2456
	assert len(
		{(record["record_kind"], record["case_id"]) for record in result["records"]}
	) == 2456
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
	assert "provenance" not in result

	manifest = json.loads((RELEASE_ROOT / "manifest.json").read_text(encoding="utf-8"))
	assert manifest["external_reference_record_count"] == 2456
	for relative_path in manifest["files"]:
		artifact = RELEASE_ROOT / relative_path
		assert artifact.is_file()
