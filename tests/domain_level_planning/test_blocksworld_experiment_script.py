from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_blocksworld_first20_script_writes_reproducible_json_report(
	tmp_path: Path,
) -> None:
	output = tmp_path / "blocksworld-smoke.json"

	subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "run_blocksworld_first20_experiment.py"),
			"--output",
			str(output),
			"--train-count",
			"1",
			"--eval-count",
			"2",
		),
		cwd=PROJECT_ROOT,
		check=True,
	)

	report = json.loads(output.read_text(encoding="utf-8"))
	assert report["experiment_name"] == "blocksworld-first20"
	assert report["train_problem_count"] == 1
	assert report["evaluation_problem_count"] == 2
	assert report["coverage"]["solved_count"] == 2
	assert report["coverage"]["failed_count"] == 0
	assert report["failure_analysis"]["failed_problem_count"] == 0
	assert report["failure_analysis"]["failure_reason_counts"] == {}
	assert report["failure_analysis"]["step_count_summary"]["max"] >= 0
	assert report["domain_level_contract"]["passed"] is True
	assert report["no_synthetic_names"] is True
	assert report["generated_output_audit"]["passed"] is True
	assert report["generated_output_audit"]["no_synthetic_names"] is True
	assert report["generated_output_audit"]["no_grounded_plan_terms"] is True
	assert report["plan_library"]["primitive_action_call_count"] > 0
	assert report["plan_library"]["subgoal_call_count"] > 0
	assert report["plan_library"]["asl_line_count"] > 0
	assert report["runtime_seconds"]["synthesis"] >= 0
	assert report["runtime_seconds"]["evaluation_total"] >= 0
	assert len(report["runtime_seconds"]["evaluation_by_problem"]) == 2
	assert "+!g : goal_on" in report["asl"]
