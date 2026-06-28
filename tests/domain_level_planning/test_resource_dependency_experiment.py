from __future__ import annotations

from pathlib import Path

from domain_level_planning.experiments import run_domain_level_experiment
from tests.domain_level_planning.resource_dependency_fixture import (
	write_resource_dependency_fixture,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_resource_dependency_refinement_experiment_learns_goal_dependency(
	tmp_path: Path,
) -> None:
	fixture = write_resource_dependency_fixture(tmp_path / "resource-dependency")
	report = run_domain_level_experiment(
		experiment_name="resource-dependency",
		domain_file=fixture.domain_file,
		training_problem_files=(fixture.problems[0],),
		evaluation_problem_files=(
			fixture.problems[0],
			fixture.problems[1],
		),
		use_counterexample_refinement=True,
		max_refinement_rounds=1,
		max_execution_steps=100,
		max_depth=50,
	)

	assert report["coverage"]["coverage_ratio"] == 1.0
	assert report["paper_quality_summary"]["synthesis_profile"] == "bootstrap"
	assert report["paper_quality_summary"]["schema_only_bootstrap"] is False
	assert report["plan_library"]["domain_name"] == "resource-dependency"
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


def test_resource_dependency_refinement_generalizes_goal_dependency_stress(
	tmp_path: Path,
) -> None:
	fixture = write_resource_dependency_fixture(tmp_path / "resource-dependency")
	stress_problems = fixture.problems[1:6]

	report = run_domain_level_experiment(
		experiment_name="resource-dependency-scalable",
		domain_file=fixture.domain_file,
		training_problem_files=(fixture.problems[0],),
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


def test_resource_dependency_stress_fails_without_layer_c_ordering(
	tmp_path: Path,
) -> None:
	fixture = write_resource_dependency_fixture(tmp_path / "resource-dependency")
	stress_problems = fixture.problems[1:6]

	report = run_domain_level_experiment(
		experiment_name="resource-dependency-scalable-no-layer-c",
		domain_file=fixture.domain_file,
		training_problem_files=(fixture.problems[0],),
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
