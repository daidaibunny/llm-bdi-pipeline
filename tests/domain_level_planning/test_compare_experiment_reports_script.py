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
	macros_output = tmp_path / "results.tex"
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
			"--latex-macros-output",
			str(macros_output),
		),
		cwd=PROJECT_ROOT,
		check=True,
	)

	table = json.loads(output.read_text(encoding="utf-8"))
	macros = macros_output.read_text(encoding="utf-8")
	assert table["report_count"] == 2
	assert table["best_by_coverage"] == "paper_external_sketch"
	assert table["rows"][0]["label"] == "bootstrap_schema_only"
	assert table["rows"][0]["schema_only_bootstrap"] is True
	assert table["rows"][1]["label"] == "paper_external_sketch"
	assert table["rows"][1]["paper_profile_ready"] is True
	assert table["paper_table_rows"][0]["solved"] == "1/2"
	assert "\\ResultBootstrapSchemaOnlySolved}{1/2}" in macros
	assert "\\ResultPaperExternalSketchCoveragePercent}{100.0\\%}" in macros


def test_compare_experiment_reports_preserves_baseline_scope_metadata(
	tmp_path: Path,
) -> None:
	report = tmp_path / "paper.json"
	output = tmp_path / "comparison.json"
	_write_report(
		report,
		name="paper-smoke",
		label="paper_external_sketch",
		solved_count=2,
		failed_count=0,
		paper_profile_ready=True,
		schema_only_bootstrap=False,
		baselines=[
			{
				"label": "fast_downward_lama_per_problem",
				"domain_name": "BLOCKS",
				"solver_family": "classical_planner",
				"solved_count": 2,
				"failed_count": 0,
				"coverage_ratio": 1.0,
				"runtime_planner": "offline_baseline_only",
				"comparison_scope": "per_problem_trace_baseline",
				"domain_level_artifact": False,
				"coverage_semantics": "executed_and_strips_validated",
				"evidence_source": "Fast Downward",
				"notes": "not a domain-level library",
			},
		],
	)

	subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "compare_domain_level_experiments.py"),
			"--report",
			str(report),
			"--output",
			str(output),
		),
		cwd=PROJECT_ROOT,
		check=True,
	)

	table = json.loads(output.read_text(encoding="utf-8"))
	assert table["baseline_count"] == 1
	baseline = table["baselines"][0]
	assert baseline["comparison_scope"] == "per_problem_trace_baseline"
	assert baseline["coverage_semantics"] == "executed_and_strips_validated"
	assert baseline["domain_level_artifact"] is False
	assert table["paper_table_rows"][1]["notes"] == (
		"per_problem_trace_baseline; executed_and_strips_validated; "
		"not a domain-level library"
	)


def _write_report(
	path: Path,
	*,
	name: str,
	label: str,
	solved_count: int,
	failed_count: int,
	paper_profile_ready: bool,
	schema_only_bootstrap: bool,
	baselines: list[dict[str, object]] | None = None,
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
					"baselines": baselines or [],
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
