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
	assert report["experiment_protocol"]["scope"] == (
		"bounded_domain_level_lifted_asl_evaluation"
	)
	assert report["experiment_protocol"]["runtime_planner"] == "none"
	assert report["experiment_protocol"]["baselines"] == []
	assert report["experiment_protocol"]["ablations"] == [
		{
			"label": "bootstrap_counterexample_refinement",
			"synthesis_profile": "bootstrap",
			"external_policy_count": 0,
			"counterexample_refinement": True,
			"use_synthesis_planner_traces": False,
			"runtime_planner": "none",
			"mechanism_status": {
				"counterexample_refinement": "enabled",
				"external_sketch_evidence": "disabled",
				"layer_c_ordering": "enabled",
				"offline_synthesis_planner_traces": "disabled",
				"paper_profile_gate": "disabled",
			},
			"disabled_synthesis_mechanisms": [],
			"enabled_mechanisms": [
				"counterexample_refinement",
				"layer_c_ordering",
			],
			"disabled_mechanisms": [
				"external_sketch_evidence",
				"offline_synthesis_planner_traces",
				"paper_profile_gate",
			],
		},
	]
	assert report["paper_quality_summary"][
		"selected_external_sketch_candidate_count"
	] == 0
	assert report["paper_quality_summary"]["output_external_sketch_candidate_count"] == 0
	assert report["paper_quality_summary"]["selected_external_sketch_rule_names"] == []
	assert report["paper_quality_summary"]["output_external_sketch_rule_names"] == []
	assert report["coverage"]["solved_count"] == 2
	assert report["coverage"]["failed_count"] == 0
	assert report["failure_analysis"]["failed_problem_count"] == 0
	assert report["failure_analysis"]["failure_reason_counts"] == {}
	assert report["failure_analysis"]["step_count_summary"]["max"] >= 0
	assert report["domain_level_contract"]["passed"] is True
	assert report["domain_level_contract"]["goal_descriptor_usage"]["read_only"] is True
	assert report["domain_level_contract"]["goal_descriptor_usage"][
		"context_descriptors"
	]
	assert report["no_synthetic_names"] is True
	assert report["generated_output_audit"]["passed"] is True
	assert report["generated_output_audit"]["no_synthetic_names"] is True
	assert report["generated_output_audit"]["no_grounded_plan_terms"] is True
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
	assert report["plan_library"]["primitive_action_call_count"] > 0
	assert report["plan_library"]["subgoal_call_count"] > 0
	assert report["plan_library"]["asl_line_count"] > 0
	assert report["learning_audit"]["layer_b_atomic_modules"][
		"atomic_action_strategy_group_count"
	] > 0
	assert report["learning_audit"]["layer_c_goal_composer"][
		"composer_candidate_count"
	] > 0
	assert report["runtime_seconds"]["synthesis"] >= 0
	assert report["runtime_seconds"]["evaluation_total"] >= 0
	assert len(report["runtime_seconds"]["evaluation_by_problem"]) == 2

	trace = report["refinement_trace"]
	assert trace["converged"] is True
	assert trace["refinement_summary"]["converged"] is True
	assert trace["refinement_summary"]["round_count"] == 2
	assert trace["refinement_summary"]["constraint_count"] == 1
	assert trace["refinement_summary"]["constraints_by_target_layer"] == {
		"layer_c_goal_composer": 1,
	}
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


def test_labworkflow_dependency_script_accepts_explicit_ablation_label(
	tmp_path: Path,
) -> None:
	output = tmp_path / "labworkflow-custom-ablation.json"

	subprocess.run(
		(
			sys.executable,
			str(PROJECT_ROOT / "scripts" / "run_labworkflow_dependency_experiment.py"),
			"--output",
			str(output),
			"--ablation-label",
			"custom_labworkflow_profile",
		),
		cwd=PROJECT_ROOT,
		check=True,
	)

	report = json.loads(output.read_text(encoding="utf-8"))
	assert report["experiment_protocol"]["ablations"] == [
		{
			"label": "custom_labworkflow_profile",
			"synthesis_profile": "bootstrap",
			"external_policy_count": 0,
			"counterexample_refinement": True,
			"use_synthesis_planner_traces": False,
			"runtime_planner": "none",
			"mechanism_status": {
				"counterexample_refinement": "enabled",
				"external_sketch_evidence": "disabled",
				"layer_c_ordering": "enabled",
				"offline_synthesis_planner_traces": "disabled",
				"paper_profile_gate": "disabled",
			},
			"disabled_synthesis_mechanisms": [],
			"enabled_mechanisms": [
				"counterexample_refinement",
				"layer_c_ordering",
			],
			"disabled_mechanisms": [
				"external_sketch_evidence",
				"offline_synthesis_planner_traces",
				"paper_profile_gate",
			],
		},
	]
