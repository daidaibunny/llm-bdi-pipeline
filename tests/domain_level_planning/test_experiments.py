from __future__ import annotations

from pathlib import Path

from domain_level_planning.experiments import run_domain_level_experiment
from tests.domain_level_planning.test_library_synthesis import (
	_write_counterexample_domain,
)


def test_domain_level_experiment_reports_reproducible_coverage_and_asl(
	tmp_path: Path,
) -> None:
	domain_file, training_problem, heldout_problem = _write_counterexample_domain(
		tmp_path,
	)

	report = run_domain_level_experiment(
		experiment_name="counterexample-mini-smoke",
		domain_file=domain_file,
		training_problem_files=(training_problem,),
		evaluation_problem_files=(training_problem, heldout_problem),
		max_execution_steps=100,
		max_depth=50,
	)

	assert report["experiment_name"] == "counterexample-mini-smoke"
	assert report["generation_mode"] == "unified_goal_conditioned_modular_synthesis"
	assert report["train_problem_count"] == 1
	assert report["evaluation_problem_count"] == 2
	assert report["coverage"]["solved_count"] == 2
	assert report["coverage"]["coverage_ratio"] == 1.0
	assert report["coverage"]["failed_problem_names"] == []
	assert report["evaluation_results"][0]["problem_file"].endswith("training.pddl")
	assert report["evaluation_results"][0]["solved"] is True
	assert report["evaluation_results"][0]["step_count"] == 1
	assert report["evaluation_results"][1]["problem_file"].endswith("counterexample.pddl")
	assert report["evaluation_results"][1]["solved"] is True
	assert report["evaluation_results"][1]["step_count"] == 2
	assert report["domain_level_contract"]["passed"] is True
	assert report["bounded_validation"]["passed"] is True
	assert report["no_synthetic_names"] is True
	assert report["plan_library"]["plan_count"] > 0
	assert "+!g : goal_base(X) & not base(X) <-" in report["asl"]
	assert "!achieve_" not in report["asl"]
	assert "!transition_" not in report["asl"]
	assert "dfa_state" not in report["asl"]
