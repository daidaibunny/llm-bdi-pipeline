from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.run_domain_level_experiment import _read_baseline_records


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_generic_domain_level_experiment_script_runs_any_pddl_split(
	tmp_path: Path,
) -> None:
	output = tmp_path / "generic-labworkflow.json"
	lab_root = PROJECT_ROOT / "src" / "domains" / "labworkflow"

	subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "run_domain_level_experiment.py"),
			"--experiment-name",
			"generic-labworkflow-smoke",
			"--domain-file",
			str(lab_root / "domain.pddl"),
			"--train-problem",
			str(lab_root / "problems" / "p01.pddl"),
			"--eval-problem",
			str(lab_root / "problems" / "p01.pddl"),
			"--eval-problem",
			str(lab_root / "problems" / "p02.pddl"),
			"--use-counterexample-refinement",
			"--max-refinement-rounds",
			"1",
			"--max-steps",
			"100",
			"--max-depth",
			"50",
			"--ablation-label",
			"generic_counterexample_refinement",
			"--output",
			str(output),
		),
		cwd=PROJECT_ROOT,
		check=True,
	)

	report = json.loads(output.read_text(encoding="utf-8"))
	assert report["experiment_name"] == "generic-labworkflow-smoke"
	assert report["coverage"]["solved_count"] == 2
	assert report["coverage"]["failed_count"] == 0
	assert report["experiment_protocol"]["ablations"] == [
		{
			"label": "generic_counterexample_refinement",
			"synthesis_profile": "bootstrap",
			"external_policy_count": 0,
			"counterexample_refinement": True,
			"runtime_planner": "none",
		},
	]
	assert report["validation_scope"]["evaluation_problem_count"] == 2
	assert report["no_synthetic_names"] is True
	assert report["generated_output_audit"]["passed"] is True


def test_generic_domain_level_experiment_script_accepts_completed_baseline_json(
	tmp_path: Path,
) -> None:
	output = tmp_path / "generic-labworkflow-baseline.json"
	baseline_json = tmp_path / "baselines.json"
	baseline_json.write_text(
		json.dumps(
			[
				{
					"label": "offline-planner",
					"solver_family": "classical_planner",
					"solved_count": 2,
					"failed_count": 0,
					"coverage_ratio": 1.0,
				},
			],
		),
		encoding="utf-8",
	)
	lab_root = PROJECT_ROOT / "src" / "domains" / "labworkflow"

	subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "run_domain_level_experiment.py"),
			"--experiment-name",
			"generic-labworkflow-baseline-smoke",
			"--domain-file",
			str(lab_root / "domain.pddl"),
			"--train-problem",
			str(lab_root / "problems" / "p01.pddl"),
			"--eval-problem",
			str(lab_root / "problems" / "p01.pddl"),
			"--eval-problem",
			str(lab_root / "problems" / "p02.pddl"),
			"--baseline-json",
			str(baseline_json),
			"--max-steps",
			"100",
			"--max-depth",
			"50",
			"--output",
			str(output),
		),
		cwd=PROJECT_ROOT,
		check=True,
	)

	report = json.loads(output.read_text(encoding="utf-8"))
	assert report["experiment_protocol"]["runtime_planner"] == "none"
	assert report["experiment_protocol"]["baselines"] == [
		{
			"label": "offline-planner",
			"domain_name": "",
			"solver_family": "classical_planner",
			"solved_count": 2,
			"failed_count": 0,
			"coverage_ratio": 1.0,
			"runtime_planner": "offline_baseline_only",
			"notes": "",
		},
	]


def test_generic_experiment_baseline_json_requires_completed_coverage_fields(
	tmp_path: Path,
) -> None:
	baseline_json = tmp_path / "bad-baseline.json"
	baseline_json.write_text(
		json.dumps({"label": "missing-coverage"}),
		encoding="utf-8",
	)

	with pytest.raises(ValueError, match="missing required baseline field"):
		_read_baseline_records((baseline_json,))
