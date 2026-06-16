from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_labworkflow_dependency_script_reports_non_blocksworld_ordering(
	tmp_path: Path,
) -> None:
	output = tmp_path / "labworkflow.json"

	subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "run_labworkflow_dependency_experiment.py"),
			"--output",
			str(output),
		),
		cwd=PROJECT_ROOT,
		check=True,
	)

	report = json.loads(output.read_text(encoding="utf-8"))
	assert report["experiment_name"] == "labworkflow-dependency"
	assert report["coverage"]["solved_count"] == 2
	assert report["coverage"]["failed_count"] == 0
	assert report["domain_level_contract"]["passed"] is True
	assert report["no_synthetic_names"] is True

	trace = report["refinement_trace"]
	assert trace["converged"] is True
	assert trace["rounds"][0]["heldout_evaluations"][1]["solved"] is False
	constraint = trace["rounds"][0]["refinement_constraints"][0]
	assert constraint["failure_kind"] == "goal_ordering_failure"
	assert constraint["target_layer"] == "layer_c_goal_composer"
	assert constraint["lifted_orderings"] == [
		["goal_reagent_logged(Y)", "goal_analysis_done(X, Y)"],
	]
	assert trace["rounds"][1]["heldout_evaluations"][1]["solved"] is True

	assert "+!g : goal_reagent_logged(Y) & goal_analysis_done(X, Y)" in report["asl"]
	assert "\t!reagent_logged(Y);" in report["asl"]
	assert "!achieve_" not in report["asl"]
	assert "!transition_" not in report["asl"]
	assert "dfa_state" not in report["asl"]
