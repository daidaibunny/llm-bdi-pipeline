from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_compare_experiment_reports_script_writes_reproducible_table(
	tmp_path: Path,
) -> None:
	bootstrap_report = tmp_path / "bootstrap.json"
	paper_report = tmp_path / "paper.json"
	output = tmp_path / "comparison.json"
	_write_report(
		bootstrap_report,
		name="bootstrap-smoke",
		label="bootstrap_schema_only",
		solved_count=1,
		failed_count=1,
		paper_profile_ready=False,
		schema_only_bootstrap=True,
	)
	_write_report(
		paper_report,
		name="paper-smoke",
		label="paper_external_sketch",
		solved_count=2,
		failed_count=0,
		paper_profile_ready=True,
		schema_only_bootstrap=False,
	)

	subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "compare_domain_level_experiments.py"),
			"--report",
			str(bootstrap_report),
			"--report",
			str(paper_report),
			"--output",
			str(output),
		),
		cwd=PROJECT_ROOT,
		check=True,
	)

	table = json.loads(output.read_text(encoding="utf-8"))
	assert table["report_count"] == 2
	assert table["best_by_coverage"] == "paper_external_sketch"
	assert table["rows"][0]["label"] == "bootstrap_schema_only"
	assert table["rows"][0]["schema_only_bootstrap"] is True
	assert table["rows"][1]["label"] == "paper_external_sketch"
	assert table["rows"][1]["paper_profile_ready"] is True


def _write_report(
	path: Path,
	*,
	name: str,
	label: str,
	solved_count: int,
	failed_count: int,
	paper_profile_ready: bool,
	schema_only_bootstrap: bool,
) -> None:
	total = solved_count + failed_count
	path.write_text(
		json.dumps(
			{
				"experiment_name": name,
				"experiment_protocol": {
					"synthesis_profile": "paper" if paper_profile_ready else "bootstrap",
					"external_policy_count": 1 if paper_profile_ready else 0,
					"ablations": [
						{
							"label": label,
							"counterexample_refinement": False,
						},
					],
					"baselines": [],
				},
				"coverage": {
					"solved_count": solved_count,
					"failed_count": failed_count,
					"coverage_ratio": solved_count / total,
				},
				"paper_quality_summary": {
					"paper_profile_ready": paper_profile_ready,
					"schema_only_bootstrap": schema_only_bootstrap,
					"selected_external_sketch_candidate_count": 1
					if paper_profile_ready
					else 0,
					"output_external_sketch_candidate_count": 1
					if paper_profile_ready
					else 0,
					"blocking_failure_count": 0 if paper_profile_ready else 1,
				},
				"plan_library": {
					"plan_count": 3 if paper_profile_ready else 2,
					"primitive_action_call_count": 2,
					"subgoal_call_count": 1,
				},
			},
			indent=2,
			sort_keys=True,
		),
		encoding="utf-8",
	)
