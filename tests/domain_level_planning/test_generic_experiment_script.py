from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


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
