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
	assert report["paper_quality_summary"]["synthesis_profile"] == "bootstrap"
	assert report["paper_quality_summary"]["schema_only_bootstrap"] is False
	assert report["plan_library"]["domain_name"] == "labworkflow"
	assert report["refinement_analysis"] == {
		"enabled": True,
		"converged": True,
		"round_count": 2,
		"constraint_count": 1,
		"constraints_by_type": {"counterexample_goal_ordering": 1},
		"constraints_by_failure_kind": {"goal_ordering_failure": 1},
		"constraints_by_target_layer": {"layer_c_goal_composer": 1},
		"first_round_failed_heldout_count": 1,
		"final_round_failed_heldout_count": 0,
	}
	assert report["refinement_trace"]["converged"] is True
	assert report["refinement_trace"]["rounds"][0]["refinement_constraints"][0][
		"constraint_type"
	] == "counterexample_goal_ordering"
	assert "goal_reagent_logged(Y) & goal_analysis_done(X, Y)" in report["asl"]


def test_labworkflow_refinement_generalizes_goal_dependency_stress() -> None:
	stress_problems = tuple(
		LAB_ROOT / "problems" / f"p{index:02d}.pddl"
		for index in range(2, 7)
	)

	report = run_domain_level_experiment(
		experiment_name="labworkflow-scalable-dependency",
		domain_file=LAB_ROOT / "domain.pddl",
		training_problem_files=(LAB_ROOT / "problems" / "p01.pddl",),
		evaluation_problem_files=stress_problems,
		use_counterexample_refinement=True,
		max_refinement_rounds=1,
		max_execution_steps=500,
		max_depth=100,
	)

	assert report["coverage"]["solved_count"] == len(stress_problems)
	assert report["coverage"]["failed_count"] == 0
	assert report["refinement_analysis"]["converged"] is True
	assert report["refinement_analysis"]["first_round_failed_heldout_count"] == len(
		stress_problems,
	)
	assert report["refinement_analysis"]["final_round_failed_heldout_count"] == 0
	assert report["refinement_analysis"]["constraints_by_type"][
		"counterexample_goal_ordering"
	] >= 1
	assert "goal_reagent_logged(Y) & goal_analysis_done(X, Y)" in report["asl"]
	assert "reagent_logged(r1)" not in report["asl"]


def test_labworkflow_dependency_stress_fails_without_layer_c_ordering() -> None:
	stress_problems = tuple(
		LAB_ROOT / "problems" / f"p{index:02d}.pddl"
		for index in range(2, 7)
	)

	report = run_domain_level_experiment(
		experiment_name="labworkflow-scalable-dependency-no-layer-c",
		domain_file=LAB_ROOT / "domain.pddl",
		training_problem_files=(LAB_ROOT / "problems" / "p01.pddl",),
		evaluation_problem_files=stress_problems,
		use_counterexample_refinement=True,
		disabled_synthesis_mechanisms=("layer_c_ordering",),
		max_refinement_rounds=1,
		max_execution_steps=500,
		max_depth=100,
	)

	assert report["coverage"]["solved_count"] < len(stress_problems)
	assert report["coverage"]["failed_count"] > 0
	assert report["refinement_analysis"]["converged"] is False
	assert report["experiment_protocol"]["mechanism_status"]["counterexample_refinement"] == (
		"enabled"
	)
	assert report["experiment_protocol"]["mechanism_status"]["layer_c_ordering"] == (
		"disabled"
	)
