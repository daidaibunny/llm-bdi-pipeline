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
	assert report["generated_output_audit"]["passed"] is True
	assert report["generated_output_audit"]["no_synthetic_names"] is True
	assert report["generated_output_audit"]["no_grounded_plan_terms"] is True
	assert report["generated_output_audit"]["no_initial_beliefs"] is True
	assert report["generated_output_audit"]["goal_descriptors_read_only"] is True
	assert report["generated_output_audit"]["supported_asl_subset"] is True
	assert report["generated_output_audit"]["declared_pddl_symbols"] is True
	assert report["generated_output_audit"]["violation_count"] == 0
	assert report["generated_output_audit"]["violations"] == []
	assert set(report["generated_output_audit"]["checked_layers"]) >= {
		"no_initial_beliefs",
		"no_synthetic_names",
		"goal_descriptors_read_only",
		"plan_head_subset",
		"body_step_subset",
		"context_subset",
		"declared_pddl_symbols",
		"lifted_plan_heads",
		"lifted_body_calls",
		"lifted_contexts",
	}
	assert report["refinement_analysis"] == {
		"enabled": False,
		"converged": None,
		"round_count": 0,
		"constraint_count": 0,
		"constraints_by_type": {},
		"constraints_by_failure_kind": {},
		"constraints_by_target_layer": {},
		"first_round_failed_heldout_count": 0,
		"final_round_failed_heldout_count": 0,
	}
	assert report["plan_library"]["plan_count"] > 0
	assert report["plan_library"]["primitive_action_call_count"] > 0
	assert report["plan_library"]["subgoal_call_count"] > 0
	assert report["plan_library"]["asl_line_count"] > 0
	assert report["runtime_seconds"]["synthesis"] >= 0
	assert report["runtime_seconds"]["evaluation_total"] >= 0
	assert len(report["runtime_seconds"]["evaluation_by_problem"]) == 2
	assert all(
		item["duration_seconds"] >= 0
		for item in report["runtime_seconds"]["evaluation_by_problem"]
	)
	assert "+!g : goal_base(X) & not base(X) <-" in report["asl"]
	assert "!achieve_" not in report["asl"]
	assert "!transition_" not in report["asl"]
	assert "dfa_state" not in report["asl"]


def test_domain_level_experiment_reports_failure_analysis(
	tmp_path: Path,
) -> None:
	domain_file, training_problem, _heldout_problem = _write_counterexample_domain(
		tmp_path,
	)
	failing_problem = tmp_path / "impossible.pddl"
	failing_problem.write_text(
		"""
		(define (problem impossible-p1)
		 (:domain counterexample-mini)
		 (:objects c - object)
		 (:init)
		 (:goal (and (top c)))
		)
		""",
		encoding="utf-8",
	)

	report = run_domain_level_experiment(
		experiment_name="counterexample-failure-analysis",
		domain_file=domain_file,
		training_problem_files=(training_problem,),
		evaluation_problem_files=(training_problem, failing_problem),
		max_execution_steps=100,
		max_depth=50,
	)

	assert report["coverage"]["solved_count"] == 1
	assert report["coverage"]["failed_count"] == 1
	assert report["failure_analysis"]["failed_problem_count"] == 1
	assert report["failure_analysis"]["failure_reason_counts"] == {
		"no applicable plan for !base(c)": 1,
	}
	assert report["failure_analysis"]["failed_problems"] == [
		{
			"problem_name": "impossible-p1",
			"problem_file": str(failing_problem.resolve()),
			"failure_reason": "no applicable plan for !base(c)",
			"step_count": 0,
		},
	]
	assert report["failure_analysis"]["step_count_summary"] == {
		"min": 0,
		"max": 1,
		"mean": 0.5,
	}
