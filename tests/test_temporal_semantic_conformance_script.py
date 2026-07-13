from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from scripts.run_temporal_semantic_conformance import load_conformance_suite
from scripts.run_temporal_semantic_conformance import run_semantic_cases
from scripts.run_temporal_semantic_conformance import run_zero_action_case
from scripts.run_temporal_semantic_conformance import verify_conformance_release


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_tracked_semantic_conformance_cases_match_direct_and_mona_semantics(
	monkeypatch,
) -> None:
	monkeypatch.setenv(
		"MONA_BIN",
		str(PROJECT_ROOT / ".external/mona-1.4/Front/mona"),
	)
	verify_conformance_release(
		PROJECT_ROOT / "paper_artifacts/temporal_semantic_conformance/v1",
	)
	suite = load_conformance_suite(
		PROJECT_ROOT / "paper_artifacts/temporal_semantic_conformance/v1/suite.json",
	)

	records = run_semantic_cases(suite)

	assert len(records) == 14
	assert all(record["success"] for record in records)
	assert {record["expected_acceptance"] for record in records} == {False, True}


@pytest.mark.skipif(
	not (shutil.which("java") and shutil.which("javac") and shutil.which("mvn")),
	reason="real zero-action conformance requires java, javac, and Maven",
)
def test_zero_action_predicate_and_numeric_cases_execute_end_to_end(
	tmp_path: Path,
	monkeypatch,
) -> None:
	monkeypatch.setenv(
		"MONA_BIN",
		str(PROJECT_ROOT / ".external/mona-1.4/Front/mona"),
	)
	suite_root = PROJECT_ROOT / "paper_artifacts/temporal_semantic_conformance/v1"
	suite = load_conformance_suite(suite_root / "suite.json")

	records = tuple(
		run_zero_action_case(
			case,
			suite_root=suite_root,
			output_dir=tmp_path / str(case["case_id"]),
			timeout_seconds=30,
			jason_java_stack_size="64m",
		)
		for case in suite["zero_action_cases"]
	)

	assert len(records) == 2
	assert all(record["success"] for record in records)
	assert all(record["action_count"] == 0 for record in records)
	assert all(record["state_count"] == 1 for record in records)
	assert all(record["val_attempted"] is False for record in records)
	assert all(
		record["legality_certificate"] == "vacuous_zero_action_pddl_replay"
		for record in records
	)
