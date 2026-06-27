from __future__ import annotations

from pathlib import Path
import time

import pytest

from domain_level_planning import experiments as experiments_module
from domain_level_planning.experiments import compare_domain_level_experiment_reports
from domain_level_planning.experiments import format_comparison_latex_macros
from domain_level_planning.experiments import run_domain_level_experiment
from domain_level_planning.experiments import _generated_output_audit
from domain_level_planning.library_synthesis import ExternalSketchPolicySource
from tests.domain_level_planning.test_library_synthesis import (
	_write_generic_domain_problem_and_policy,
)
from tests.domain_level_planning.test_library_synthesis import (
	_write_counterexample_domain,
)
from tests.domain_level_planning.test_library_synthesis import (
	_write_multi_hop_causal_domain_and_problem,
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
	assert report["experiment_protocol"] == {
		"scope": "bounded_domain_level_lifted_asl_evaluation",
		"training_source": "provided_pddl_training_problems",
		"evaluation_source": "provided_pddl_evaluation_problems",
		"synthesis_profile": "bootstrap",
		"external_policy_count": 0,
		"disabled_synthesis_mechanisms": [],
		"mechanism_status": {
			"counterexample_refinement": "disabled",
			"external_sketch_evidence": "disabled",
			"layer_c_ordering": "enabled",
			"offline_synthesis_planner_traces": "disabled",
			"paper_profile_gate": "disabled",
		},
		"runtime_planner": "none",
		"baselines": [],
		"ablations": [],
		"limitations": [
			"coverage is measured only over the listed evaluation PDDL problems",
			"no IPC-wide baseline table is implied by this smoke protocol",
		],
	}
	paper_quality = report["paper_quality_summary"]
	assert paper_quality["synthesis_profile"] == "bootstrap"
	assert paper_quality["paper_profile_ready"] is False
	assert paper_quality["schema_only_bootstrap"] is True
	assert paper_quality["external_policy_count"] == 0
	assert paper_quality["selected_external_sketch_candidate_count"] == 0
	assert paper_quality["output_external_sketch_candidate_count"] == 0
	assert paper_quality["selected_external_sketch_rule_names"] == []
	assert paper_quality["output_external_sketch_rule_names"] == []
	assert paper_quality["external_policy_required_for_paper_profile"] is True
	assert paper_quality["blocking_failure_count"] == len(
		paper_quality["blocking_failures"],
	)
	assert "paper profile requires at least one external learned sketch policy" in (
		paper_quality["blocking_failures"]
	)
	assert any(
		"unjustified schema action atomic rule" in failure
		for failure in paper_quality["blocking_failures"]
	)
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
	assert report["domain_level_contract"]["goal_descriptor_usage"]["read_only"] is True
	assert report["domain_level_contract"]["goal_descriptor_usage"][
		"context_descriptors"
	]
	assert report["pddl_to_asl_symbol_map"] == report["synthesis_report"][
		"pddl_to_asl_symbol_map"
	]
	assert report["pddl_to_asl_symbol_map"]["changed_actions"] == {}
	assert report["bounded_validation"]["passed"] is True
	assert report["validation_scope"] == {
		"bounded_validation_problem_count": 1,
		"bounded_validation_source": "training_and_counterexample_problem_files",
		"bounded_validation_problem_names": ["training-p1"],
		"evaluation_problem_count": 2,
		"evaluation_source": "evaluation_problem_files",
		"coverage_is_heldout_runtime_execution": True,
	}
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
	assert report["learning_audit"]["layer_b_atomic_modules"][
		"atomic_action_strategy_group_count"
	] >= 1
	assert report["learning_audit"]["layer_b_atomic_modules"][
		"atomic_module_proof_count"
	] >= report["learning_audit"]["layer_b_atomic_modules"][
		"justified_atomic_module_proof_count"
	]
	assert report["learning_audit"]["layer_b_atomic_modules"][
		"unjustified_atomic_module_proof_count"
	] >= 1
	assert report["learning_audit"]["layer_b_atomic_modules"][
		"atomic_action_strategy_candidate_count"
	] >= report["learning_audit"]["layer_b_atomic_modules"][
		"selected_atomic_action_strategy_candidate_count"
	]
	assert report["learning_audit"]["layer_b_atomic_modules"][
		"atomic_strategy_portfolio_group_count"
	] == report["learning_audit"]["layer_b_atomic_modules"][
		"atomic_action_strategy_group_count"
	]
	assert report["learning_audit"]["layer_c_goal_composer"][
		"composer_candidate_count"
	] >= report["learning_audit"]["layer_c_goal_composer"][
		"selected_composer_candidate_count"
	]
	assert report["learning_audit"]["layer_c_goal_composer"][
		"composer_rule_proof_count"
	] >= report["learning_audit"]["layer_c_goal_composer"][
		"justified_composer_rule_proof_count"
	]
	assert report["learning_audit"]["layer_c_goal_composer"][
		"unjustified_composer_rule_proof_count"
	] == 0
	assert "schema_goal_dispatch" in report["learning_audit"]["layer_c_goal_composer"][
		"composer_candidate_verdict_counts"
	]
	assert isinstance(
		report["learning_audit"]["layer_c_goal_composer"][
			"composer_ordering_kind_counts"
		],
		dict,
	)
	assert report["runtime_seconds"]["synthesis"] >= 0
	assert report["runtime_seconds"]["evaluation_total"] >= 0
	assert len(report["runtime_seconds"]["evaluation_by_problem"]) == 2
	assert all(
		item["duration_seconds"] >= 0
		for item in report["runtime_seconds"]["evaluation_by_problem"]
	)
	assert "+!g : goal_base(X) & ready_base(X) & not base(X) <-" in report["asl"]
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
	assert report["failure_analysis"]["failure_kind_counts"] == {
		"no_applicable_plan": 1,
	}
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


def test_domain_level_experiment_records_per_problem_evaluation_timeout(
	tmp_path: Path,
	monkeypatch,
) -> None:
	domain_file, training_problem, _heldout_problem = _write_counterexample_domain(
		tmp_path,
	)

	def slow_evaluation(*args, **kwargs):
		time.sleep(1)
		return {}

	monkeypatch.setattr(experiments_module, "_evaluate_problem", slow_evaluation)

	report = run_domain_level_experiment(
		experiment_name="counterexample-timeout-analysis",
		domain_file=domain_file,
		training_problem_files=(training_problem,),
		evaluation_problem_files=(training_problem,),
		max_execution_steps=100,
		max_depth=50,
		evaluation_timeout_seconds=0.01,
	)

	assert report["coverage"]["solved_count"] == 0
	assert report["coverage"]["failed_count"] == 1
	assert report["evaluation_results"] == [
		{
			"problem_file": str(training_problem.resolve()),
			"problem_name": "training-p1",
			"solved": False,
			"step_count": 0,
			"steps": [],
			"failure_reason": (
				"evaluation timeout exceeded timeout_seconds=0.01 "
				"for problem training-p1"
			),
		},
	]
	assert report["runtime_seconds"]["evaluation_by_problem"][0]["timed_out"] is True


def test_domain_level_experiment_reports_schema_binding_depth(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_multi_hop_causal_domain_and_problem(tmp_path)

	report = run_domain_level_experiment(
		experiment_name="multi-hop-binding-smoke",
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		evaluation_problem_files=(problem_file,),
		max_execution_steps=100,
		max_depth=50,
	)

	layer_c = report["learning_audit"]["layer_c_goal_composer"]
	assert layer_c["composer_ordering_kind_counts"][
		"schema_causal_precondition_binding_support"
	] == 1
	assert layer_c["max_schema_binding_ordering_candidate_depth"] == 2
	assert layer_c["max_schema_binding_ordering_selected_depth"] == 2
	assert layer_c["max_schema_binding_ordering_depth"] == 2
	assert layer_c["goal_agenda_support_edge_count"] == 1
	assert layer_c["selected_goal_agenda_support_edge_count"] == 1
	assert layer_c["goal_agenda_delete_threat_edge_count"] == 0
	assert layer_c["selected_goal_agenda_acyclic"] is True
	assert "assigned(X, Y) & station_tool(Y, Z)" in report["asl"]


def test_domain_level_experiment_can_run_paper_profile_with_external_policy(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, policy_file = _write_generic_domain_problem_and_policy(
		tmp_path,
	)

	report = run_domain_level_experiment(
		experiment_name="paper-profile-smoke",
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		evaluation_problem_files=(problem_file,),
		external_sketch_policies=(
			ExternalSketchPolicySource(
				name="paper-sketch-smoke",
				policy_file=policy_file,
			),
		),
		synthesis_profile="paper",
		max_execution_steps=100,
		max_depth=50,
	)

	assert report["coverage"]["solved_count"] == 1
	assert report["synthesis_report"]["synthesis_profile"] == "paper"
	assert report["synthesis_report"]["paper_profile_ready"] is True
	assert report["synthesis_report"]["external_policy_count"] == 1
	assert report["synthesis_report"]["selected_candidate_sources"]["external_sketch"] == 1
	assert report["experiment_protocol"]["synthesis_profile"] == "paper"
	assert report["experiment_protocol"]["external_policy_count"] == 1
	assert report["paper_quality_summary"] == {
		"synthesis_profile": "paper",
		"paper_profile_ready": True,
		"schema_only_bootstrap": False,
		"external_policy_count": 1,
		"selected_external_sketch_candidate_count": 1,
		"output_external_sketch_candidate_count": 1,
		"selected_external_sketch_rule_names": ["external_paper_sketch_smoke_1"],
		"output_external_sketch_rule_names": ["external_paper_sketch_smoke_1"],
		"external_policy_required_for_paper_profile": False,
		"blocking_failure_count": 0,
		"blocking_failures": [],
	}


def test_domain_level_experiment_can_write_failed_paper_profile_report(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, _policy_file = _write_generic_domain_problem_and_policy(
		tmp_path,
	)

	with pytest.raises(ValueError, match="external learned sketch policy"):
		run_domain_level_experiment(
			experiment_name="paper-profile-fail-fast",
			domain_file=domain_file,
			training_problem_files=(problem_file,),
			evaluation_problem_files=(problem_file,),
			synthesis_profile="paper",
			max_execution_steps=100,
			max_depth=50,
		)

	report = run_domain_level_experiment(
		experiment_name="paper-profile-diagnostic",
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		evaluation_problem_files=(problem_file,),
		synthesis_profile="paper",
		max_execution_steps=100,
		max_depth=50,
		fail_on_paper_profile_failure=False,
	)

	assert report["synthesis_report"]["paper_profile_ready"] is False
	assert "paper profile requires at least one external learned sketch policy" in (
		report["synthesis_report"]["paper_profile_failures"]
	)
	assert report["paper_quality_summary"]["blocking_failure_count"] > 0


def test_domain_level_experiment_records_explicit_ablation_metadata(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, _policy_file = _write_generic_domain_problem_and_policy(
		tmp_path,
	)

	report = run_domain_level_experiment(
		experiment_name="bootstrap-ablation-smoke",
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		evaluation_problem_files=(problem_file,),
		ablation_label="bootstrap_schema_only",
		max_execution_steps=100,
		max_depth=50,
	)

	assert report["experiment_protocol"]["ablations"] == [
		{
			"label": "bootstrap_schema_only",
			"synthesis_profile": "bootstrap",
			"external_policy_count": 0,
			"counterexample_refinement": False,
			"use_synthesis_planner_traces": False,
			"runtime_planner": "none",
			"mechanism_status": {
				"counterexample_refinement": "disabled",
				"external_sketch_evidence": "disabled",
				"layer_c_ordering": "enabled",
				"offline_synthesis_planner_traces": "disabled",
				"paper_profile_gate": "disabled",
			},
			"disabled_synthesis_mechanisms": [],
			"enabled_mechanisms": ["layer_c_ordering"],
			"disabled_mechanisms": [
				"external_sketch_evidence",
				"counterexample_refinement",
				"offline_synthesis_planner_traces",
				"paper_profile_gate",
			],
		},
	]


def test_domain_level_experiment_records_completed_baseline_metadata(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, _policy_file = _write_generic_domain_problem_and_policy(
		tmp_path,
	)

	report = run_domain_level_experiment(
		experiment_name="baseline-smoke",
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		evaluation_problem_files=(problem_file,),
		baselines=(
			{
				"label": "external-planner-offline",
				"solver_family": "classical_planner",
				"solved_count": 1,
				"failed_count": 0,
				"coverage_ratio": 1.0,
				"runtime_planner": "offline_baseline_only",
			},
		),
		max_execution_steps=100,
		max_depth=50,
	)

	assert report["experiment_protocol"]["baselines"] == [
		{
			"label": "external-planner-offline",
			"domain_name": "",
			"solver_family": "classical_planner",
			"solved_count": 1,
			"failed_count": 0,
			"coverage_ratio": 1.0,
			"runtime_planner": "offline_baseline_only",
			"notes": "",
		},
	]
	assert report["experiment_protocol"]["runtime_planner"] == "none"


def test_compare_domain_level_experiment_reports_builds_ablation_table(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, policy_file = _write_generic_domain_problem_and_policy(
		tmp_path,
	)
	bootstrap = run_domain_level_experiment(
		experiment_name="bootstrap-ablation",
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		evaluation_problem_files=(problem_file,),
		ablation_label="bootstrap_schema_only",
		max_execution_steps=100,
		max_depth=50,
	)
	paper = run_domain_level_experiment(
		experiment_name="paper-ablation",
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		evaluation_problem_files=(problem_file,),
		external_sketch_policies=(
			ExternalSketchPolicySource(
				name="paper-sketch-smoke",
				policy_file=policy_file,
			),
		),
		synthesis_profile="paper",
		ablation_label="paper_external_sketch",
		max_execution_steps=100,
		max_depth=50,
	)

	table = compare_domain_level_experiment_reports((bootstrap, paper))

	assert table["report_count"] == 2
	assert table["best_by_coverage"] in {"bootstrap_schema_only", "paper_external_sketch"}
	assert table["baseline_count"] == 0
	rows = {row["label"]: row for row in table["rows"]}
	assert rows["bootstrap_schema_only"]["schema_only_bootstrap"] is True
	assert rows["bootstrap_schema_only"]["runtime_planner"] == "none"
	assert rows["bootstrap_schema_only"]["enabled_mechanisms"] == [
		"layer_c_ordering",
	]
	assert rows["bootstrap_schema_only"]["disabled_mechanisms"] == [
		"external_sketch_evidence",
		"counterexample_refinement",
		"offline_synthesis_planner_traces",
		"paper_profile_gate",
	]
	assert rows["bootstrap_schema_only"]["evaluation_problem_count"] == 1
	assert rows["bootstrap_schema_only"]["paper_blocking_failure_count"] == (
		bootstrap["paper_quality_summary"]["blocking_failure_count"]
	)
	assert rows["bootstrap_schema_only"]["coverage_delta_vs_best_library"] == 0.0
	assert rows["paper_external_sketch"]["paper_profile_ready"] is True
	assert rows["paper_external_sketch"]["selected_external_sketch_candidate_count"] == 1
	assert rows["paper_external_sketch"]["enabled_mechanisms"] == [
		"external_sketch_evidence",
		"layer_c_ordering",
		"paper_profile_gate",
	]
	assert rows["paper_external_sketch"]["plan_count"] == paper["plan_library"]["plan_count"]
	assert rows["paper_external_sketch"]["coverage_delta_vs_best_library"] == 0.0

	paper_rows = {row["label"]: row for row in table["paper_table_rows"]}
	assert paper_rows["bootstrap_schema_only"] == {
		"row_type": "library",
		"label": "bootstrap_schema_only",
		"domain_name": bootstrap["plan_library"]["domain_name"],
		"solved": "1/1",
		"coverage_percent": 100.0,
		"plan_count": bootstrap["plan_library"]["plan_count"],
		"runtime_planner": "none",
		"mechanism_summary": "enabled: layer_c_ordering",
		"paper_profile_ready": False,
		"coverage_delta_vs_best_library": 0.0,
		"notes": "schema-only bootstrap",
	}

	macros = format_comparison_latex_macros(table)
	assert "\\ResultBootstrapSchemaOnlySolved}{1/1}" in macros
	assert "\\ResultPaperExternalSketchCoveragePercent}{100.0\\%}" in macros
	assert "\\ResultPaperExternalSketchMechanisms}" in macros


def test_compare_domain_level_experiment_reports_summarizes_completed_baselines(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, _policy_file = _write_generic_domain_problem_and_policy(
		tmp_path,
	)
	report = run_domain_level_experiment(
		experiment_name="baseline-comparison",
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		evaluation_problem_files=(problem_file,),
		baselines=(
			{
				"label": "planner-offline",
				"solver_family": "classical_planner",
				"domain_name": "baseline-mini",
				"coverage_ratio": 1.0,
				"solved_count": 1,
				"failed_count": 0,
				"notes": "per-problem planner trace baseline",
			},
		),
		max_execution_steps=100,
		max_depth=50,
	)

	table = compare_domain_level_experiment_reports((report,))

	assert table["baseline_count"] == 1
	assert table["best_baseline_by_coverage"] == "planner-offline"
	assert table["best_baseline_delta_vs_library"] == 0.0
	assert table["baselines"] == [
		{
			"report_label": "baseline-comparison",
			"label": "planner-offline",
			"domain_name": "baseline-mini",
			"solver_family": "classical_planner",
			"solved_count": 1,
			"failed_count": 0,
			"evaluation_problem_count": 1,
			"coverage_ratio": 1.0,
			"library_coverage_ratio": 1.0,
			"coverage_delta_vs_library": 0.0,
			"runtime_planner": "offline_baseline_only",
			"notes": "per-problem planner trace baseline",
			"comparison_scope": "coverage_baseline",
			"domain_level_artifact": False,
			"evidence_source": "",
			"coverage_semantics": "executed",
			"validation": None,
		},
	]
	assert table["paper_table_rows"][-1] == {
		"row_type": "baseline",
		"label": "planner-offline",
		"domain_name": "baseline-mini",
		"solver_family": "classical_planner",
		"solved": "1/1",
		"coverage_percent": 100.0,
		"plan_count": None,
		"runtime_planner": "offline_baseline_only",
		"mechanism_summary": "baseline",
		"paper_profile_ready": None,
		"coverage_delta_vs_library": 0.0,
		"notes": "per-problem planner trace baseline",
	}


def test_generated_output_audit_includes_plan_head_subset() -> None:
	audit = _generated_output_audit(
		{
			"passed": False,
			"checked_layers": {
				"no_synthetic_names": True,
				"lifted_plan_heads": True,
				"lifted_body_calls": True,
				"lifted_contexts": True,
				"no_initial_beliefs": True,
				"goal_descriptors_read_only": True,
				"plan_head_subset": False,
				"body_step_subset": True,
				"context_subset": True,
				"declared_pddl_symbols": True,
			},
			"violations": ["Plan 'bad' uses unsupported plan trigger kind."],
		},
	)

	assert audit["supported_asl_subset"] is False
	assert audit["violations"] == ["Plan 'bad' uses unsupported plan trigger kind."]
