from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

from scripts.run_temporal_goal_benchmark_execution import (
	benchmark_prediction,
)
from scripts.run_temporal_goal_benchmark_execution import summarize_execution_records
from scripts.run_temporal_goal_benchmark_execution import verify_invocation_binding


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_shell_entrypoint_accepts_no_domain_arguments_on_bash_3(
	tmp_path: Path,
) -> None:
	bin_dir = tmp_path / "bin"
	bin_dir.mkdir()
	capture_file = tmp_path / "uv-arguments.txt"
	fake_uv = bin_dir / "uv"
	fake_uv.write_text(
		'#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$CAPTURE_FILE"\n',
		encoding="utf-8",
	)
	fake_uv.chmod(0o755)
	fake_mona = bin_dir / "mona"
	fake_mona.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
	fake_mona.chmod(0o755)
	environment = {
		**os.environ,
		"PATH": f"{bin_dir}:{os.environ['PATH']}",
		"CAPTURE_FILE": str(capture_file),
		"MONA_BIN": str(fake_mona),
		"RUN_ID": "shell-no-domain-test",
	}

	completed = subprocess.run(
		("bash", "scripts/run_temporal_goal_benchmark_execution.sh"),
		cwd=PROJECT_ROOT,
		env=environment,
		capture_output=True,
		text=True,
		check=False,
	)

	assert completed.returncode == 0, completed.stderr
	arguments = capture_file.read_text(encoding="utf-8").splitlines()
	assert arguments[:3] == [
		"run",
		"python",
		"scripts/run_temporal_goal_benchmark_execution.py",
	]
	assert "--domain" not in arguments


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
