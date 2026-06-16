from __future__ import annotations

from pathlib import Path

from domain_level_planning.experiments import run_domain_level_experiment


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAB_ROOT = PROJECT_ROOT / "src" / "domains" / "labworkflow"


def test_labworkflow_refinement_experiment_learns_goal_dependency() -> None:
	report = run_domain_level_experiment(
		experiment_name="labworkflow-dependency",
		domain_file=LAB_ROOT / "domain.pddl",
		training_problem_files=(LAB_ROOT / "problems" / "p01.pddl",),
		evaluation_problem_files=(
			LAB_ROOT / "problems" / "p01.pddl",
			LAB_ROOT / "problems" / "p02.pddl",
		),
		use_counterexample_refinement=True,
		max_refinement_rounds=1,
		max_execution_steps=100,
		max_depth=50,
	)

	assert report["coverage"]["coverage_ratio"] == 1.0
	assert report["plan_library"]["domain_name"] == "labworkflow"
	assert report["refinement_trace"]["converged"] is True
	assert report["refinement_trace"]["rounds"][0]["refinement_constraints"][0][
		"constraint_type"
	] == "counterexample_goal_ordering"
	assert "goal_reagent_logged(Y) & goal_analysis_done(X, Y)" in report["asl"]
