from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.public_temporal_dataset import find_nonportable_metadata_paths
from evaluation.public_temporal_dataset import verify_public_temporal_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_nonportable_metadata_scan_reports_json_value_location(tmp_path: Path) -> None:
	(tmp_path / "portable.json").write_text(
		json.dumps({"path": "domains/ferry.json"}),
		encoding="utf-8",
	)
	(tmp_path / "local.json").write_text(
		json.dumps({"nested": {"path": "/Users/example/result.json"}}),
		encoding="utf-8",
	)

	assert find_nonportable_metadata_paths(tmp_path) == (
		"local.json:nested:path=/Users/example/result.json",
	)


def test_public_dataset_verifier_rejects_machine_local_metadata(tmp_path: Path) -> None:
	(tmp_path / "manifest.json").write_text(
		json.dumps({"local": "/private/tmp/result"}),
		encoding="utf-8",
	)

	with pytest.raises(ValueError, match="machine-local absolute path"):
		verify_public_temporal_dataset(tmp_path)


def test_tracked_public_temporal_dataset_is_complete_and_portable() -> None:
	report = verify_public_temporal_dataset(
		PROJECT_ROOT / "paper_artifacts/temporal_goal_benchmark/v1",
	)

	assert report == {
		"benchmark_id": "temporal-nl-v1-20260711-final",
		"domain_count": 16,
		"problem_case_count": 1228,
		"unique_translation_input_count": 475,
	}
