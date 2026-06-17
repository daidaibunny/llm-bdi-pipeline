from __future__ import annotations

from pathlib import Path

from domain_level_planning.gp_backends import BackendManifest
from domain_level_planning.gp_backends import LearnerSketchesRunConfig
from domain_level_planning.library_synthesis import (
	ExternalSketchPolicySource,
	synthesize_domain_level_asl_library,
)
from domain_level_planning.refinement import RefinementConstraint
from plan_library.rendering import render_plan_library_asl
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "domain.pddl"
BLOCKS_P01 = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "problems" / "p01.pddl"


def test_unified_pipeline_reports_schema_causal_interference_orderings() -> None:
	result = synthesize_domain_level_asl_library(
		domain_file=BLOCKS_DOMAIN,
		training_problem_files=(BLOCKS_P01,),
	)

	layer_c = result.report["evidence_matrix"]["layer_c_goal_composer"]
	# Schema causal interference must contribute composer ordering candidates that
	# do not depend on training traces.
	assert layer_c["causal_interference_candidate_count"] >= 1
	assert layer_c["delete_threat_ordering_candidate_count"] >= 1
	assert layer_c["delete_threat_ordering_selected_count"] >= 1
	assert layer_c["trace_ordering_selected_count"] >= 1
	candidate_evidence = layer_c["composer_candidate_evidence"]
	assert any(
		item["verdict"] == "schema_causal_ordering"
		and item["selected"] is True
		and item["body"] == ("on(Y, Z)", "g")
		for item in candidate_evidence
	)
	assert all(
		item["rejection_reason"] is None
		or item["rejection_reason"]
		in {
			"not_required_for_bounded_training_states",
			"higher_cost_or_redundant_composer",
		}
		for item in candidate_evidence
	)
	asl = render_plan_library_asl(result.plan_library)
	assert "+!g : goal_on(Y, Z) & goal_on(X, Y) & not on(Y, Z) <-" in asl


def test_unified_pipeline_combines_external_sketch_and_schema_candidates(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, policy_file = _write_generic_domain_problem_and_policy(tmp_path)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		external_sketch_policies=(
			ExternalSketchPolicySource(
				name="paper-sketch-smoke",
				policy_file=policy_file,
			),
		),
	)
	asl = render_plan_library_asl(result.plan_library)

	assert result.report["generation_mode"] == "unified_goal_conditioned_modular_synthesis"
	assert result.report["synthesis_profile"] == "bootstrap"
	assert result.report["pddl_support"]["is_compilable"] is True
	assert result.report["pddl_support"]["requirements"] == [":strips"]
	assert result.report["pddl_support"]["unsupported_reasons"] == []
	assert result.report["pddl_support"]["unsupported_diagnostics"] == []
	assert result.plan_library.metadata["pddl_support"] == result.report["pddl_support"]
	assert result.report["paper_quality_checks"] == (
		"transition_progress",
		"bounded_all_reachable_states",
		"acyclic_high_level_decision_trace",
		"goal_state_fixed_point",
	)
	assert result.report["domain_level_contract"]["passed"] is True
	assert all(result.report["domain_level_contract"]["checked_layers"].values())
	assert result.report["domain_level_contract"]["supported_asl_subset"]["body_steps"] == (
		"PDDL primitive action calls and PDDL predicate subgoal calls only"
	)
	assert result.report["domain_level_contract"]["execution_semantics"]["plan_selection"] == (
		"deterministic_first_applicable_asl_order"
	)
	assert result.report["bounded_validation"]["passed"] is True
	assert result.report["bounded_validation"]["counterexample_count"] == 0
	assert result.report["external_policy_count"] == 1
	policy_audits = result.report["paper_policy_audits"]
	assert policy_audits[0]["feature_binding_diagnostics"][0]["status"] == "bound"
	assert policy_audits[0]["feature_binding_diagnostics"][0]["binding_kind"] == (
		"goal_aligned_concept_count"
	)
	assert policy_audits[0]["feature_binding_diagnostics"][0]["rejection_reason"] is None
	backend_matrix = {
		entry["name"]: entry
		for entry in result.report["backend_audit_matrix"]
	}
	assert backend_matrix["learner-sketches"]["paper_role"] == (
		"serialized-width sketch learner for qualitative DLPlan policies"
	)
	assert backend_matrix["learner-sketches"]["resource_profile"]["guard_required"] is True
	assert "Layer B/C sketch evidence" in backend_matrix["learner-sketches"]["reusable_evidence"]
	assert "description-logic policy learner baseline" in backend_matrix["d2l"]["paper_role"]
	consumption = result.report["external_backend_consumption_summary"]
	assert consumption["policy_count"] == 1
	assert consumption["ready_policy_count"] == 1
	assert consumption["compiled_rule_count"] == 1
	assert consumption["rejected_rule_count"] == 0
	assert consumption["candidate_count"] == result.report["external_candidate_count"]
	assert consumption["rejected_source_count"] == 0
	assert consumption["policies"] == (
		{
			"source_name": "paper-sketch-smoke",
			"ready_for_executable_asl": True,
			"feature_count": 1,
			"bound_feature_count": 1,
			"unsupported_feature_count": 0,
			"rule_count": 1,
			"compiled_rule_count": 1,
			"rejected_rule_count": 0,
			"candidate_count": result.report["external_candidate_count"],
			"rejection_reasons": (),
		},
	)
	assert consumption["source_gate_reports"] == (
		{
			"source_name": "paper-sketch-smoke",
			"backend_name": "learner-sketches",
			"accepted": True,
			"consumption_role": {
				"drives_layer_b": True,
				"drives_layer_c": True,
				"consumed_by_synthesis": True,
				"consumption_mode": "parsed_bound_policy_rules",
				"blocking_gap": None,
			},
			"rejection_reason": None,
		},
	)
	assert result.report["external_policy_source_gate_reports"] == (
		{
			"source_name": "paper-sketch-smoke",
			"backend_name": "learner-sketches",
			"accepted": True,
			"consumption_role": {
				"drives_layer_b": True,
				"drives_layer_c": True,
				"consumed_by_synthesis": True,
				"consumption_mode": "parsed_bound_policy_rules",
				"blocking_gap": None,
			},
			"rejection_reason": None,
		},
	)
	assert result.report["candidate_sources"]["external_sketch"] >= 1
	assert result.report["candidate_sources"]["schema"] >= 1
	assert result.report["output_candidate_sources"]["external_sketch"] >= 1
	assert result.report["paper_profile_ready"] is True
	assert result.report["paper_profile_failures"] == ()
	rule_reports = result.report["external_rule_binding_reports"]
	assert len(rule_reports) == 1
	assert rule_reports[0]["compiled"] is True
	assert "+!g : goal_done(X0) & not done(X0) <-" in asl
	assert "\t!done(X0);" in asl
	assert "+!done(X) : ready(X) <-" in asl
	assert "\tfinish(X)." in asl
	assert "!achieve_" not in asl
	assert "!transition_" not in asl
	assert "dfa_state" not in asl


def test_unified_pipeline_consumes_reverse_role_external_sketch(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, policy_file = _write_binary_domain_problem_and_policy(
		tmp_path,
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		external_sketch_policies=(
			ExternalSketchPolicySource(
				name="reverse-role-sketch",
				policy_file=policy_file,
			),
		),
	)
	asl = render_plan_library_asl(result.plan_library)

	assert result.report["paper_profile_ready"] is True
	assert result.report["external_backend_consumption_summary"]["ready_policy_count"] == 1
	assert result.report["external_rule_binding_reports"] == (
		{
			"source_name": "reverse-role-sketch",
			"rule_index": 1,
			"raw_rule": "(:rule (:conditions ) (:effects (:e_n_inc f_link)))",
			"compiled": True,
			"missing_condition_bindings": [],
			"missing_effect_bindings": [],
			"empty_body": False,
		},
	)
	policy_audit = result.report["paper_policy_audits"][0]
	assert policy_audit["feature_binding_diagnostics"][0]["binding_kind"] == (
		"goal_aligned_reverse_role_count"
	)
	assert policy_audit["feature_binding_diagnostics"][0]["status"] == "bound"
	assert result.report["output_candidate_sources"]["external_sketch"] == 1
	assert "+!g : goal_link(X1, X0) & not link(X1, X0) <-" in asl
	assert "\t!link(X1, X0);" in asl


def test_unified_pipeline_blocks_audit_only_external_backends(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, policy_file = _write_generic_domain_problem_and_policy(tmp_path)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		external_sketch_policies=(
			ExternalSketchPolicySource(
				name="d2l-policy-smoke",
				policy_file=policy_file,
				backend_name="d2l",
			),
		),
	)

	assert result.report["external_policy_count"] == 1
	assert result.report["consumable_external_policy_count"] == 0
	assert result.report["rejected_external_policy_count"] == 1
	assert result.report["external_candidate_count"] == 0
	assert result.report["paper_policy_audits"] == ()
	assert result.report["external_rule_binding_reports"] == ()
	assert result.report["external_policy_source_gate_reports"] == (
		{
			"source_name": "d2l-policy-smoke",
			"backend_name": "d2l",
			"accepted": False,
			"consumption_role": {
				"drives_layer_b": False,
				"drives_layer_c": False,
				"consumed_by_synthesis": False,
				"consumption_mode": "audit_only_feature_policy_baseline",
				"blocking_gap": "no_verified_d2l_policy_parser_or_asl_binding",
			},
			"rejection_reason": "no_verified_d2l_policy_parser_or_asl_binding",
		},
	)
	assert result.report["external_backend_consumption_summary"][
		"rejected_source_count"
	] == 1
	assert result.report["external_backend_consumption_summary"][
		"source_gate_reports"
	] == result.report["external_policy_source_gate_reports"]
	assert "external_d2l" not in render_plan_library_asl(result.plan_library)


def test_unified_pipeline_reports_architecture_contract_and_current_gaps(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, policy_file = _write_generic_domain_problem_and_policy(tmp_path)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		external_sketch_policies=(
			ExternalSketchPolicySource(
				name="paper-sketch-smoke",
				policy_file=policy_file,
			),
		),
	)

	contract = result.report["architecture_contract"]
	assert result.report["theoretical_contract"] == "bounded_class_guarantee"
	assert "universal PDDL generalized-planning completeness" in contract["guarantee"]
	assert "universal completeness for arbitrary PDDL domains" in contract["non_goals"]
	assert "runtime full-trace planning for each new problem" in contract["non_goals"]
	assert "read-only goal descriptors" in contract["goal_fact_semantics"]
	assert "not primitive actions" in contract["goal_fact_semantics"]
	hypothesis = contract["hypothesis_class"]
	assert hypothesis["name"] == "goal_conditioned_modular_sketch_asl"
	assert any(
		"PDDL predicates" in item
		for item in hypothesis["feature_language"]["state_features"]
	)
	assert any(
		"goal_<predicate>" in item
		for item in hypothesis["feature_language"]["goal_features"]
	)
	assert hypothesis["module_language"]["heads"] == (
		"declared PDDL predicate achievement goals and zero-argument +!g"
	)
	assert "declared PDDL primitive action" in (
		hypothesis["module_language"]["body_calls"]
	)
	assert "matching schema arities" in hypothesis["module_language"]["body_calls"]
	assert "goal-conditioned +!g rules" in hypothesis["composer_language"]["rule_shape"]
	assert "bounded reachable states" in hypothesis["progress_language"]["validation_scope"]
	assert hypothesis["correctness_language"]["claim_scope"] == (
		"bounded training/counterexample/held-out transition systems"
	)
	assert "arbitrary PDDL domains" in hypothesis["exclusions"]
	assert "rejected object-specific, distance, or vocabulary-mismatched features" in (
		hypothesis["feature_language"]["external_features"]
	)
	gap_summary = result.report["architecture_gap_summary"]
	assert gap_summary["in_progress"] >= 1
	assert gap_summary["partially_done"] >= 4
	assert gap_summary["done_current_fragment"] == 1

	decisions = {decision["id"]: decision for decision in contract["decisions"]}
	assert decisions["D3"]["status"] == "accepted"
	assert "goal_<predicate>" in decisions["D3"]["decision"]
	assert decisions["D6"]["status"] == "open"
	assert decisions["D7"]["status"] == "accepted"
	assert "object-specific DLPlan features" in decisions["D7"]["decision"]

	gaps = {gap["id"]: gap for gap in contract["gaps"]}
	assert set(gaps) == {f"G{index}" for index in range(1, 13)}
	assert gaps["G2"]["layer"] == "Layer B"
	assert gaps["G2"]["status"] == "partially_done"
	assert "trace slicing" in gaps["G2"]["current_state"]
	assert "anti-unified" in gaps["G2"]["current_state"]
	assert "recursion descent" in gaps["G2"]["current_state"]
	assert "repair diagnostics" in gaps["G2"]["current_state"]
	assert "provenance manifests" in gaps["G2"]["current_state"]
	assert "paper-profile exclusion" in gaps["G2"]["current_state"]
	assert "multi-strategy module learner" in gaps["G2"]["required_improvement"]
	assert "repair diagnostics" in gaps["G2"]["required_improvement"]
	assert gaps["G3"]["layer"] == "Layer C"
	assert gaps["G3"]["status"] == "partially_done"
	assert "main research gap" in gaps["G3"]["gap"]
	assert "counterexample failure classification" in gaps["G3"]["current_state"]
	assert "delete-threat" in gaps["G3"]["current_state"]
	assert "primitive-precondition repair evidence" in gaps["G3"]["current_state"]
	assert "selector hard groups" in gaps["G3"]["current_state"]
	assert "Atomic-progress refinement constraints" in gaps["G3"]["current_state"]
	assert "Goal-bound primitive-precondition failures" in gaps["G3"]["current_state"]
	assert "Explicit counterexample goal-ordering constraints" in (
		gaps["G3"]["current_state"]
	)
	assert "rejected binding diagnostics" in gaps["G3"]["current_state"]
	assert "undeclared predicates" in gaps["G3"]["current_state"]
	assert "repair evidence" in gaps["G3"]["current_state"]
	assert "wrong predicate arities" in gaps["G3"]["current_state"]
	assert "wrong-arity repair failing actions" in gaps["G3"]["current_state"]
	assert "wrong-arity atomic-progress diagnostics" in gaps["G3"]["current_state"]
	assert "Negative precondition repairs are rejected explicitly" in (
		gaps["G3"]["current_state"]
	)
	assert "provenance manifests" in gaps["G3"]["current_state"]
	assert "per-rule composer evidence verdicts" in gaps["G3"]["current_state"]
	assert "current explicit goal-ordering and goal-bound primitive-precondition" in (
		gaps["G3"]["required_improvement"]
	)
	assert "termination diagnostic counts" in gaps["G9"]["current_state"]
	assert "diagnostic group types" in gaps["G9"]["current_state"]
	assert gaps["G5"]["status"] == "partially_done"
	assert "object-specific" in gaps["G5"]["current_state"]
	assert "distance" in gaps["G5"]["current_state"]
	assert "vocabulary-mismatch" in gaps["G5"]["current_state"]
	assert "goal-aligned concept/role intersection" in gaps["G5"]["current_state"]
	assert "distinct rejection diagnostics" in gaps["G5"]["current_state"]
	assert "object-specific or distance features" in gaps["G5"]["required_improvement"]
	assert gaps["G6"]["layer"] == "external backends"
	assert gaps["G6"]["status"] == "partially_done"
	assert "learner-sketches" in gaps["G6"]["current_state"]
	assert "h-policy-learner" in gaps["G6"]["current_state"]
	assert "d2l" in gaps["G6"]["current_state"]
	assert "verified policy-to-ASL adapters" in gaps["G6"]["required_improvement"]
	assert gaps["G7"]["layer"] == "ASL compiler"
	assert gaps["G7"]["status"] == "partially_done"
	assert "deterministic first-applicable" in gaps["G7"]["current_state"]
	assert "primitive-action precondition handling" in gaps["G7"]["required_improvement"]
	assert gaps["G8"]["layer"] == "validation"
	assert gaps["G8"]["status"] == "partially_done"
	assert "library size and runtime metrics" in gaps["G8"]["current_state"]
	assert "ablations" in gaps["G8"]["required_improvement"]
	assert gaps["G9"]["layer"] == "counterexample refinement"
	assert gaps["G9"]["status"] == "partially_done"
	assert "negative precondition repairs" in gaps["G9"]["current_state"]
	assert "failure classes" in gaps["G9"]["required_improvement"]
	assert gaps["G10"]["layer"] == "PDDL scope"
	assert gaps["G10"]["status"] == "done_current_fragment"
	assert "STRIPS" in gaps["G10"]["current_state"]
	assert "machine-readable diagnostics" in gaps["G10"]["current_state"]
	assert gaps["G11"]["layer"] == "no-hardcoding"
	assert gaps["G11"]["status"] == "partially_done"
	assert "rule manifest leakage" in gaps["G11"]["current_state"]
	assert "domain-specific" in gaps["G11"]["required_improvement"]
	assert gaps["G12"]["layer"] == "TEG"
	assert gaps["G12"]["status"] == "partially_done"
	assert "DFA guards can be translated" in gaps["G12"]["current_state"]
	assert "runtime controller" in gaps["G12"]["current_state"]
	assert "temporal artifact pipeline" in gaps["G12"]["current_state"]
	assert "repeated progress steps" in gaps["G12"]["current_state"]
	assert "accepted/rejected DFA guard diagnostics" in gaps["G12"]["current_state"]
	assert "negative/disjunctive guard semantics" in gaps["G12"]["required_improvement"]
	assert "beyond smoke tests" in gaps["G12"]["required_improvement"]


def test_unified_pipeline_reports_evidence_matrix_by_layer(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, policy_file = _write_generic_domain_problem_and_policy(tmp_path)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		external_sketch_policies=(
			ExternalSketchPolicySource(
				name="paper-sketch-smoke",
				policy_file=policy_file,
			),
		),
	)

	matrix = result.report["evidence_matrix"]
	layer_b = matrix["layer_b_atomic_modules"]
	layer_c = matrix["layer_c_goal_composer"]
	sources = matrix["sources"]
	assert layer_b["target"] == "PDDL predicate achievement-goal modules"
	assert layer_b["candidate_count"] >= layer_b["selected_rule_count"] >= 1
	assert layer_b["training_transition_progress_constraint_count"] == 1
	assert layer_b["repair_constraint_count"] == 0
	assert layer_b["matched_repair_constraint_count"] == 0
	assert layer_b["rejected_repair_constraint_count"] == 0
	assert layer_b["repair_constraint_binding_reports"] == ()
	assert layer_b["training_goal_progression_count"] == 1
	assert layer_b["training_atomic_achievement_count"] == 1
	assert layer_b["trace_justified_selected_rule_count"] >= 1
	assert layer_b["anti_unified_pattern_count"] == 1
	assert layer_b["training_anti_unified_pattern_count"] == 1
	assert layer_b["anti_unified_support_count"] == 1
	assert layer_b["anti_unified_last_achiever_support_count"] == 1
	assert layer_b["anti_unified_patterns"][0]["target_predicate"] == "done"
	assert layer_b["anti_unified_patterns"][0]["target_arguments"] == ["X"]
	assert layer_b["anti_unified_patterns"][0]["action_name"] == "finish"
	assert layer_b["anti_unified_patterns"][0]["action_arguments"] == ["X"]
	assert layer_b["anti_unified_patterns"][0]["enabling_preconditions"] == ["ready(X)"]
	assert layer_b["selected_atomic_rule_evidence"]
	evidence_by_rule = {
		item["rule_name"]: item
		for item in layer_b["selected_atomic_rule_evidence"]
	}
	assert evidence_by_rule["done_via_finish"]["verdict"] == "trace_justified"
	assert evidence_by_rule["done_via_finish"]["trace_support_count"] == 1
	assert evidence_by_rule["done_via_finish"]["source"] == "schema"
	assert evidence_by_rule["done_already_true"]["verdict"] == "schema_no_action_body"
	assert layer_b["recursion_descent"]["contract"] == (
		"missing_positive_precondition_before_same_goal_recursion"
	)
	assert layer_b["recursion_descent"]["ranking_contract"] == (
		"same_predicate_recursion_must_follow_bounded_acyclic_relation"
	)
	assert result.report["recursion_descent_audit"] == layer_b["recursion_descent"]
	assert layer_c["target"] == "goal-conditioned conjunctive-goal composer rules"
	assert layer_c["candidate_count"] >= layer_c["selected_rule_count"] >= 1
	assert layer_c["training_state_coverage_constraint_count"] >= 1
	assert layer_c["selected_composer_rule_evidence"]
	assert layer_c["output_composer_rule_evidence"]
	composer_verdicts = {
		item["rule_name"]: item["verdict"]
		for item in layer_c["selected_composer_rule_evidence"]
	}
	output_composer_verdicts = {
		item["rule_name"]: item["verdict"]
		for item in layer_c["output_composer_rule_evidence"]
	}
	assert output_composer_verdicts["external_paper_sketch_smoke_1"] == (
		"external_policy_bound"
	)
	assert composer_verdicts["g_satisfy_goal_done"] == "schema_goal_dispatch"
	assert sources["schema"]["candidate_count"] >= 1
	assert sources["schema"]["layer_counts"]["atomic"] >= 1
	assert sources["external_sketch"]["policy_count"] == 1
	assert sources["external_sketch"]["candidate_count"] == 1
	assert sources["external_sketch"]["compiled_rule_count"] == 1
	assert sources["external_sketch"]["rejected_rule_count"] == 0
	assert sources["training_transition_systems"]["problem_count"] == 1
	assert sources["training_transition_systems"]["goal_progression_count"] == 1
	assert sources["training_transition_systems"]["atomic_achievement_count"] == 1
	assert sources["counterexample_transition_systems"]["problem_count"] == 0
	selected_manifest = result.report["selected_rule_manifest"]
	output_manifest = result.report["output_rule_manifest"]
	assert len(selected_manifest) == result.report["selected_rule_count"]
	assert len(output_manifest) == result.report["output_rule_count"]
	external_manifest = next(
		item for item in output_manifest if item["source"] == "external_sketch"
	)
	assert external_manifest["name"] == "external_paper_sketch_smoke_1"
	assert external_manifest["layer"] == "composer"
	assert external_manifest["rationale"] == "external_policy:paper-sketch-smoke"
	assert external_manifest["head"] == {
		"kind": "subgoal",
		"symbol": "g",
		"arguments": [],
	}
	assert external_manifest["body"] == [
		{"kind": "subgoal", "symbol": "done", "arguments": ["X0"]},
		{"kind": "subgoal", "symbol": "g", "arguments": []},
	]
	assert external_manifest["capabilities"] == [
		"external_policy_paper_sketch_smoke_1",
	]
	assert all("achieve_" not in item["name"] for item in output_manifest)
	assert all("transition_" not in item["name"] for item in output_manifest)
	assert all("dfa_state" not in item["name"] for item in output_manifest)
	manifest_audit = result.report["rule_manifest_audit"]
	assert manifest_audit["passed"] is True
	assert manifest_audit["selected_rule_count"] == result.report["selected_rule_count"]
	assert manifest_audit["output_rule_count"] == result.report["output_rule_count"]
	assert manifest_audit["no_synthetic_names"] is True
	assert manifest_audit["no_grounded_terms"] is True
	assert manifest_audit["violation_count"] == 0
	assert manifest_audit["violations"] == []


def test_unified_pipeline_reports_unsupported_external_features_without_guessing(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, policy_file = _write_generic_domain_problem_and_policy(
		tmp_path,
		policy_feature='(f_bad "n_concept_distance(c_one_of(a),r_primitive(done,0,1),c_primitive(done,0))")',
		policy_rule="(:rule (:conditions (:c_n_gt f_bad)) (:effects (:e_n_dec f_bad)))",
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		external_sketch_policies=(
			ExternalSketchPolicySource(
				name="unsupported-sketch",
				policy_file=policy_file,
			),
		),
	)

	assert result.rejected_external_features == {
		"unsupported-sketch:f_bad": (
			"n_concept_distance(c_one_of(a),r_primitive(done,0,1),c_primitive(done,0))"
		),
	}
	assert result.report["external_candidate_count"] == 0
	assert result.report["candidate_sources"]["schema"] > 0
	consumption = result.report["external_backend_consumption_summary"]
	assert consumption["policy_count"] == 1
	assert consumption["ready_policy_count"] == 0
	assert consumption["compiled_rule_count"] == 0
	assert consumption["rejected_rule_count"] == 1
	assert consumption["candidate_count"] == 0
	assert consumption["rejected_source_count"] == 0
	assert consumption["policies"] == (
		{
			"source_name": "unsupported-sketch",
			"ready_for_executable_asl": False,
			"feature_count": 1,
			"bound_feature_count": 0,
			"unsupported_feature_count": 1,
			"rule_count": 1,
			"compiled_rule_count": 0,
			"rejected_rule_count": 1,
			"candidate_count": 0,
			"rejection_reasons": (
				"object_specific_dlplan_feature_requires_principled_lifting",
			),
		},
	)
	assert consumption["source_gate_reports"][0]["accepted"] is True
	assert consumption["source_gate_reports"][0]["backend_name"] == "learner-sketches"
	policy_audit = result.report["paper_policy_audits"][0]
	assert policy_audit["feature_binding_diagnostics"] == (
		{
			"feature_id": "f_bad",
			"expression": (
				"n_concept_distance(c_one_of(a),r_primitive(done,0,1),"
				"c_primitive(done,0))"
			),
			"status": "unsupported",
			"binding_kind": "unsupported",
			"condition_operators": (),
			"effect_operators": (),
			"action_candidate_count": 0,
			"promoted_effect_operators": (),
			"rejection_reason": (
				"object_specific_dlplan_feature_requires_principled_lifting"
			),
		},
	)
	assert result.report["paper_profile_ready"] is False
	assert result.report["external_rule_binding_reports"][0]["compiled"] is False
	assert result.report["external_rule_binding_reports"][0]["missing_condition_bindings"] == [
		"f_bad:c_n_gt",
	]
	assert result.report["external_rule_binding_reports"][0]["missing_effect_bindings"] == [
		"f_bad:e_n_dec",
	]


def test_paper_profile_requires_external_learned_policy(tmp_path: Path) -> None:
	domain_file, problem_file, _ = _write_generic_domain_problem_and_policy(tmp_path)

	with pytest.raises(ValueError, match="requires at least one external learned sketch policy"):
		synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=(problem_file,),
			synthesis_profile="paper",
		)


def test_paper_profile_rejects_uncompiled_external_policy_rules(tmp_path: Path) -> None:
	domain_file, problem_file, policy_file = _write_generic_domain_problem_and_policy(
		tmp_path,
		policy_feature='(f_bad "n_concept_distance(c_one_of(a),r_primitive(done,0,1),c_primitive(done,0))")',
		policy_rule="(:rule (:conditions (:c_n_gt f_bad)) (:effects (:e_n_dec f_bad)))",
	)

	with pytest.raises(ValueError, match="did not compile"):
		synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=(problem_file,),
			external_sketch_policies=(
				ExternalSketchPolicySource(
					name="unsupported-sketch",
					policy_file=policy_file,
				),
			),
			synthesis_profile="paper",
		)


def test_paper_profile_accepts_bound_external_policy_and_bounded_validation(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, policy_file = _write_generic_domain_problem_and_policy(tmp_path)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		external_sketch_policies=(
			ExternalSketchPolicySource(
				name="paper-sketch-smoke",
				policy_file=policy_file,
			),
		),
		synthesis_profile="paper",
	)

	assert result.report["synthesis_profile"] == "paper"
	assert result.report["paper_profile_ready"] is True
	assert result.report["paper_profile_failures"] == ()
	assert result.report["selected_candidate_sources"]["external_sketch"] == 1
	assert result.report["output_candidate_sources"]["external_sketch"] == 1


def test_paper_profile_rejects_audit_only_external_policy_sources(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, policy_file = _write_generic_domain_problem_and_policy(tmp_path)

	with pytest.raises(ValueError, match="rejected external learned policy source"):
		synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=(problem_file,),
			external_sketch_policies=(
				ExternalSketchPolicySource(
					name="paper-sketch-smoke",
					policy_file=policy_file,
				),
				ExternalSketchPolicySource(
					name="d2l-policy-smoke",
					policy_file=policy_file,
					backend_name="d2l",
				),
			),
			synthesis_profile="paper",
		)


def test_paper_profile_excludes_unobserved_schema_action_modules(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, policy_file = _write_unobserved_action_domain_problem_and_policy(
		tmp_path,
	)

	bootstrap = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		external_sketch_policies=(
			ExternalSketchPolicySource(
				name="paper-sketch-smoke",
				policy_file=policy_file,
			),
		),
	)
	layer_b = bootstrap.report["evidence_matrix"]["layer_b_atomic_modules"]
	verdict_by_rule = {
		item["rule_name"]: item["verdict"]
		for item in layer_b["selected_atomic_rule_evidence"]
	}
	assert verdict_by_rule["done_via_finish"] == "trace_justified"
	assert layer_b["evidence_weighted_action_rule_count"] >= 1
	assert layer_b["unobserved_schema_action_rule_count"] >= 1
	unobserved_schema_rules = tuple(
		item
		for item in layer_b["selected_atomic_rule_evidence"]
		if item["verdict"] == "schema_unobserved_action_body"
	)
	assert len(unobserved_schema_rules) == 1
	assert unobserved_schema_rules[0]["head"] == "bonus(X)"
	bootstrap_costs = {
		item["name"]: item["cost"]
		for item in bootstrap.report["selected_rule_manifest"]
	}
	assert bootstrap_costs["done_via_finish"] < bootstrap_costs["bonus_via_grant-bonus"]
	assert bootstrap.report["paper_profile_ready"] is False
	assert any(
		"unjustified schema action atomic rule" in failure
		and "head=bonus(X)" in failure
		for failure in bootstrap.report["paper_profile_failures"]
	)

	paper = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		external_sketch_policies=(
			ExternalSketchPolicySource(
				name="paper-sketch-smoke",
				policy_file=policy_file,
			),
		),
		synthesis_profile="paper",
	)
	paper_layer_b = paper.report["evidence_matrix"]["layer_b_atomic_modules"]
	paper_verdicts = {
		item["rule_name"]: item["verdict"]
		for item in paper_layer_b["selected_atomic_rule_evidence"]
	}
	assert paper.report["paper_profile_ready"] is True
	assert paper.report["paper_profile_failures"] == ()
	assert paper.report["paper_profile_excluded_schema_capabilities"] == (
		"module_bonus_action_grant-bonus",
	)
	assert paper_verdicts["done_via_finish"] == "trace_justified"
	assert not any(
		item["verdict"] == "schema_unobserved_action_body"
		for item in paper_layer_b["selected_atomic_rule_evidence"]
	)
	assert not any(
		item["head"] == {
			"kind": "subgoal",
			"symbol": "bonus",
			"arguments": ["X"],
		}
		and item["body"]
		for item in paper.report["output_rule_manifest"]
	)


def test_unified_pipeline_rejects_unsupported_pddl_before_synthesis(tmp_path: Path) -> None:
	domain_file, problem_file, _ = _write_generic_domain_problem_and_policy(tmp_path)
	domain_file.write_text(
		domain_file.read_text(encoding="utf-8").replace(
			"(:requirements :strips)",
			"(:requirements :strips :conditional-effects)",
		),
		encoding="utf-8",
	)

	with pytest.raises(ValueError, match="requirement :conditional-effects is not supported"):
		synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=(problem_file,),
		)


def test_layer_b_selects_one_evidence_backed_action_strategy_per_goal(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_multi_strategy_domain_and_problem(tmp_path)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
	)
	selected_names = set(result.report["selected_rule_names"])
	layer_b = result.report["evidence_matrix"]["layer_b_atomic_modules"]

	assert "done_via_finish" in selected_names
	assert "done_via_backup_finish" not in selected_names
	assert layer_b["atomic_action_strategy_group_count"] == 1
	assert layer_b["selected_atomic_action_strategy_count"] == 1
	assert layer_b["selected_unobserved_schema_action_strategy_count"] == 0
	strategy_groups = layer_b["atomic_action_strategy_groups"]
	assert len(strategy_groups) == 1
	assert strategy_groups[0]["head"] == "done(X)"
	candidates = {
		candidate["rule_name"]: candidate
		for candidate in strategy_groups[0]["candidates"]
	}
	assert candidates["done_via_finish"]["selected"] is True
	assert candidates["done_via_finish"]["verdict"] == "trace_justified"
	assert candidates["done_via_backup_finish"]["selected"] is False
	assert candidates["done_via_backup_finish"]["verdict"] == "schema_unobserved_action_body"
	assert candidates["done_via_backup_finish"]["rejection_reason"] == (
		"dominated_by_trace_supported_strategy"
	)


def test_external_policy_rules_are_rendered_before_schema_fallbacks(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, policy_file = _write_generic_domain_problem_and_policy(tmp_path)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		external_sketch_policies=(
			ExternalSketchPolicySource(
				name="paper-sketch-smoke",
				policy_file=policy_file,
			),
		),
	)
	asl = render_plan_library_asl(result.plan_library)

	assert asl.index("plan=external_paper_sketch_smoke_1") < asl.index("plan=g_satisfy_goal_done")


def test_atomic_action_rules_are_rendered_before_recursive_prepare_rules(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_prepare_order_domain_and_problem(tmp_path)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
	)
	asl = render_plan_library_asl(result.plan_library)

	assert asl.index("plan=holding_via_grab") < asl.index("plan=holding_prepare_ready_for_grab")


def test_synthesis_profile_rejects_unknown_values(tmp_path: Path) -> None:
	domain_file, problem_file, _ = _write_generic_domain_problem_and_policy(tmp_path)

	with pytest.raises(ValueError, match="either 'bootstrap' or 'paper'"):
		synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=(problem_file,),
			synthesis_profile="oracle",
		)


def test_paper_profile_can_run_learner_sketches_backend_automatically(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, _ = _write_generic_domain_problem_and_policy(tmp_path)
	backend = _write_fake_learner_sketches_backend(tmp_path)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		learner_sketches_backend=backend,
		learner_sketches_runs=(
			LearnerSketchesRunConfig(
				domain_file=domain_file,
				problems_directory=tmp_path,
				workspace=tmp_path / "auto-learner-workspace",
				width=1,
				python_executable="python3",
				use_resource_guard=False,
			),
		),
		synthesis_profile="paper",
	)

	assert result.report["paper_profile_ready"] is True
	assert result.report["manual_external_policy_count"] == 0
	assert result.report["auto_learner_sketches_run_count"] == 1
	assert result.report["auto_learner_sketches_policy_count"] == 1
	assert result.report["external_policy_count"] == 1
	assert result.report["auto_learner_sketches_runs"][0]["succeeded"] is True
	assert result.report["selected_candidate_sources"]["external_sketch"] == 1


def test_synthesis_fails_when_auto_learner_sketches_produces_no_policy(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, _ = _write_generic_domain_problem_and_policy(tmp_path)
	backend_path = tmp_path / "learner-sketches-empty"
	(backend_path / "learning").mkdir(parents=True)
	(backend_path / "learning" / "main.py").write_text("print('no policy')\n", encoding="utf-8")

	with pytest.raises(RuntimeError, match="did not produce a minimized policy"):
		synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=(problem_file,),
			learner_sketches_backend=BackendManifest(
				name="learner-sketches",
				path=backend_path,
				url="https://github.com/bonetblai/learner-sketches.git",
				expected_commit="7a7ea6a",
				present=True,
			),
			learner_sketches_runs=(
				LearnerSketchesRunConfig(
					domain_file=domain_file,
					problems_directory=tmp_path,
					workspace=tmp_path / "empty-workspace",
					python_executable="python3",
					use_resource_guard=False,
				),
			),
		)


def test_counterexample_problems_add_selector_constraints_without_polluting_training(
	tmp_path: Path,
) -> None:
	domain_file, training_problem, counterexample_problem = _write_counterexample_domain(
		tmp_path,
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(training_problem,),
		counterexample_problem_files=(counterexample_problem,),
	)

	assert result.report["training_problem_count"] == 1
	assert result.report["counterexample_problem_count"] == 1
	assert result.report["selector_training_progress_constraint_count"] == 1
	assert result.report["selector_counterexample_progress_constraint_count"] == 2
	assert result.report["selector_training_state_coverage_constraint_count"] > 0
	assert result.report["selector_counterexample_state_coverage_constraint_count"] > 0
	refinement = result.report["counterexample_refinement_constraints"]
	assert refinement["problem_count"] == 1
	assert refinement["transition_progress_required_group_count"] == 2
	assert refinement["state_coverage_required_group_count"] > 0
	assert refinement["required_group_count"] == (
		refinement["transition_progress_required_group_count"]
		+ refinement["state_coverage_required_group_count"]
	)
	assert refinement["problem_names"] == ("counterexample-p1",)
	assert result.report["bounded_validation"]["checked_problem_count"] == 2
	transition_system_names = tuple(
		transition["problem_name"]
		for transition in result.plan_library.metadata["counterexample_transition_systems"]
	)
	assert transition_system_names == ("counterexample-p1",)


def test_termination_refinement_diagnostics_are_reported_in_synthesis(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, _ = _write_generic_domain_problem_and_policy(tmp_path)
	recursive_constraint = RefinementConstraint(
		failure_kind="recursive_loop",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_recursive_loop",
		problem_file=str(problem_file),
		problem_name="p1",
		failure_reason="recursive loop on !done(a)",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X)",),
		required_rule_group_types=("counterexample_recursion_descent",),
	)
	nontermination_constraint = RefinementConstraint(
		failure_kind="nontermination",
		target_layer="execution_semantics",
		constraint_type="counterexample_nontermination",
		problem_file=str(problem_file),
		problem_name="p1",
		failure_reason="step limit exceeded",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X)",),
		required_rule_group_types=("counterexample_nontermination",),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(recursive_constraint, nontermination_constraint),
	)

	refinement = result.report["counterexample_refinement_constraints"]
	assert refinement["recursive_loop_constraint_count"] == 1
	assert refinement["nontermination_constraint_count"] == 1
	assert refinement["termination_diagnostics"] == (
		{
			"constraint_type": "counterexample_recursive_loop",
			"failure_kind": "recursive_loop",
			"target_layer": "layer_b_atomic_modules",
			"lifted_missing_goals": ("done(X)",),
			"failure_reason": "recursive loop on !done(a)",
			"generative": False,
			"non_generative_reason": "requires_recursion_ranking_or_descent_certificate",
		},
		{
			"constraint_type": "counterexample_nontermination",
			"failure_kind": "nontermination",
			"target_layer": "execution_semantics",
			"lifted_missing_goals": ("done(X)",),
			"failure_reason": "step limit exceeded",
			"generative": False,
			"non_generative_reason": "requires_execution_or_ranking_semantics_change",
		},
	)
	assert "counterexample_recursion_descent" in refinement["diagnostic_group_types"]
	assert "counterexample_nontermination" in refinement["diagnostic_group_types"]


def test_goal_ordering_refinement_constraint_synthesizes_composer_candidate(
	tmp_path: Path,
) -> None:
	domain_file, training_problem, dependent_problem = _write_counterexample_domain(
		tmp_path,
	)
	constraint = RefinementConstraint(
		failure_kind="goal_ordering_failure",
		target_layer="layer_c_goal_composer",
		constraint_type="counterexample_goal_ordering",
		problem_file=str(dependent_problem),
		problem_name="counterexample-p1",
		failure_reason="missing goals after bad ordering",
		ground_missing_goals=("base(a)",),
		ground_satisfied_goals=("top(a)",),
		lifted_missing_goals=("base(X)",),
		lifted_satisfied_goals=("top(X)",),
		lifted_orderings=(("goal_base(X)", "goal_top(X)"),),
		required_rule_group_types=(
			"counterexample_goal_ordering",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(training_problem,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]

	assert result.report["explicit_goal_ordering_candidate_count"] == 1
	assert result.report["candidate_sources"]["counterexample_goal_ordering"] == 1
	assert result.report["selected_candidate_sources"]["counterexample_goal_ordering"] == 1
	assert refinement["goal_ordering_required_group_count"] == 1
	assert refinement["required_group_types"] == ("counterexample_goal_ordering",)
	assert refinement["goal_ordering_required_groups"][0]["rule_names"] == (
		"g_counterexample_order_base_before_top_1",
	)
	assert "g_counterexample_order_base_before_top_1" in (
		result.report["selected_rule_names"]
	)

	asl = render_plan_library_asl(result.plan_library)
	assert "+!g : goal_base(X) & goal_top(X) & not base(X) <-" in asl
	assert "\t!base(X);" in asl
	assert "\t!g." in asl
	assert "!achieve_" not in asl
	assert "!transition_" not in asl
	assert "dfa_state" not in asl


def test_invalid_goal_ordering_refinement_is_reported_without_guessing(
	tmp_path: Path,
) -> None:
	domain_file, training_problem, dependent_problem = _write_counterexample_domain(
		tmp_path,
	)
	constraint = RefinementConstraint(
		failure_kind="goal_ordering_failure",
		target_layer="layer_c_goal_composer",
		constraint_type="counterexample_goal_ordering",
		problem_file=str(dependent_problem),
		problem_name="counterexample-p1",
		failure_reason="missing goals after bad ordering",
		lifted_orderings=(("goal_base(X)", "goal_top(Y)"),),
		required_rule_group_types=(
			"counterexample_goal_ordering",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(training_problem,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_goal_ordering_constraints"][0]

	assert result.report["explicit_goal_ordering_candidate_count"] == 0
	assert refinement["goal_ordering_required_group_count"] == 0
	assert refinement["rejected_goal_ordering_constraint_count"] == 1
	assert rejected["matched"] is False
	assert rejected["earlier_goal"] == "goal_base(X)"
	assert rejected["later_goal"] == "goal_top(Y)"
	assert rejected["rejection_reason"] == "disconnected_goal_ordering_variables"
	assert result.report["paper_profile_ready"] is False
	assert any(
		"unmatched goal-ordering refinement constraint" in failure
		for failure in result.report["paper_profile_failures"]
	)

	with pytest.raises(ValueError, match="unmatched goal-ordering refinement"):
		synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=(training_problem,),
			refinement_constraints=(constraint,),
			synthesis_profile="paper",
		)


def test_goal_ordering_refinement_rejects_undeclared_predicates(
	tmp_path: Path,
) -> None:
	domain_file, training_problem, dependent_problem = _write_counterexample_domain(
		tmp_path,
	)
	constraint = RefinementConstraint(
		failure_kind="goal_ordering_failure",
		target_layer="layer_c_goal_composer",
		constraint_type="counterexample_goal_ordering",
		problem_file=str(dependent_problem),
		problem_name="counterexample-p1",
		failure_reason="missing goals after bad ordering",
		lifted_orderings=(("goal_ready(X)", "goal_unknown(X)"),),
		required_rule_group_types=(
			"counterexample_goal_ordering",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(training_problem,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_goal_ordering_constraints"][0]
	asl = render_plan_library_asl(result.plan_library)

	assert result.report["explicit_goal_ordering_candidate_count"] == 0
	assert refinement["goal_ordering_required_group_count"] == 0
	assert rejected["rejection_reason"] == "undeclared_goal_ordering_predicate"
	assert "!unknown(X)" not in asl
	assert "goal_unknown(X)" not in asl


def test_goal_ordering_refinement_rejects_wrong_predicate_arity(
	tmp_path: Path,
) -> None:
	domain_file, training_problem, dependent_problem = _write_counterexample_domain(
		tmp_path,
	)
	constraint = RefinementConstraint(
		failure_kind="goal_ordering_failure",
		target_layer="layer_c_goal_composer",
		constraint_type="counterexample_goal_ordering",
		problem_file=str(dependent_problem),
		problem_name="counterexample-p1",
		failure_reason="missing goals after bad ordering",
		lifted_orderings=(("goal_base(X, Y)", "goal_top(X)"),),
		required_rule_group_types=(
			"counterexample_goal_ordering",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(training_problem,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_goal_ordering_constraints"][0]
	asl = render_plan_library_asl(result.plan_library)

	assert result.report["explicit_goal_ordering_candidate_count"] == 0
	assert refinement["goal_ordering_required_group_count"] == 0
	assert rejected["rejection_reason"] == "wrong_goal_ordering_predicate_arity"
	assert "!base(X, Y)" not in asl
	assert "goal_base(X, Y)" not in asl


def test_refinement_repair_constraints_become_selector_required_groups(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_precondition_repair_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="primitive_precondition_failure",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_precondition_repair",
		problem_file=str(problem_file),
		problem_name="repair-p1",
		failure_reason="Action preconditions are not satisfied for finish(a).",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X)",),
		failing_action="finish",
		failing_action_arguments=("a",),
		lifted_failing_action="finish(X)",
		missing_preconditions=("armed(a)",),
		lifted_missing_preconditions=("armed(X)",),
		required_rule_group_types=(
			"counterexample_transition_progress",
			"counterexample_atomic_precondition_repair",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)

	refinement = result.report["counterexample_refinement_constraints"]
	assert refinement["explicit_repair_constraint_count"] == 1
	assert refinement["repair_required_group_count"] == 1
	assert refinement["repair_required_groups"][0]["constraint_type"] == (
		"counterexample_atomic_precondition_repair"
	)
	assert refinement["repair_required_groups"][0]["rule_names"] == (
		"done_prepare_armed_for_finish",
	)
	layer_b = result.report["evidence_matrix"]["layer_b_atomic_modules"]
	assert layer_b["repair_constraint_count"] == 1
	assert layer_b["matched_repair_constraint_count"] == 1
	assert layer_b["rejected_repair_constraint_count"] == 0
	assert layer_b["repair_constraint_binding_reports"][0]["rule_names"] == (
		"done_prepare_armed_for_finish",
	)
	assert result.report["selector_repair_constraint_count"] == 1
	assert "done_prepare_armed_for_finish" in result.report["selected_rule_names"]


def test_atomic_progress_refinement_constraints_become_selector_required_groups(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, _ = _write_counterexample_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="missing_module_or_context",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_progress",
		problem_file=str(problem_file),
		problem_name="training-p1",
		failure_reason="no applicable plan for !base(b)",
		ground_missing_goals=("base(b)",),
		lifted_missing_goals=("base(X)",),
		required_rule_group_types=("counterexample_atomic_progress",),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	layer_b = result.report["evidence_matrix"]["layer_b_atomic_modules"]

	assert refinement["atomic_progress_required_group_count"] == 1
	assert refinement["rejected_atomic_progress_constraint_count"] == 0
	assert refinement["required_group_types"] == ("counterexample_atomic_progress",)
	assert refinement["atomic_progress_required_groups"][0]["rule_names"] == (
		"base_via_make_base",
	)
	assert "base_via_make_base" in result.report["selected_rule_names"]
	assert layer_b["atomic_progress_constraint_count"] == 1
	assert layer_b["matched_atomic_progress_constraint_count"] == 1


def test_state_coverage_refinement_synthesizes_composer_candidate(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, _ = _write_counterexample_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="missing_composer_or_context",
		target_layer="layer_c_goal_composer",
		constraint_type="counterexample_state_coverage",
		problem_file=str(problem_file),
		problem_name="training-p1",
		failure_reason="no applicable plan for !g",
		ground_missing_goals=("base(b)",),
		lifted_missing_goals=("base(X)",),
		required_rule_group_types=("counterexample_state_coverage",),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	layer_c = result.report["evidence_matrix"]["layer_c_goal_composer"]

	assert result.report["state_coverage_synthesized_candidate_count"] == 1
	assert result.report["candidate_sources"]["counterexample_state_coverage"] == 1
	assert result.report["selected_candidate_sources"]["counterexample_state_coverage"] == 1
	assert refinement["explicit_state_coverage_required_group_count"] == 1
	assert refinement["matched_explicit_state_coverage_constraint_count"] == 1
	assert refinement["required_group_types"] == (
		"counterexample_explicit_state_coverage",
	)
	assert refinement["explicit_state_coverage_required_groups"][0]["rule_names"] == (
		"g_satisfy_goal_base",
	)
	assert layer_c["state_coverage_synthesized_candidate_count"] == 1
	assert layer_c["matched_explicit_state_coverage_constraint_count"] == 1
	output_evidence = {
		record["rule_name"]: record
		for record in layer_c["output_composer_rule_evidence"]
	}
	assert output_evidence["g_satisfy_goal_base"]["verdict"] == (
		"counterexample_state_coverage_synthesized"
	)


def test_atomic_progress_refinement_rejects_undeclared_predicates(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, _ = _write_counterexample_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="missing_module_or_context",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_progress",
		problem_file=str(problem_file),
		problem_name="training-p1",
		failure_reason="no applicable plan for !unknown(b)",
		ground_missing_goals=("unknown(b)",),
		lifted_missing_goals=("unknown(X)",),
		required_rule_group_types=("counterexample_atomic_progress",),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_atomic_progress_constraints"][0]

	assert refinement["atomic_progress_required_group_count"] == 0
	assert refinement["rejected_atomic_progress_constraint_count"] == 1
	assert rejected["rejection_reason"] == "undeclared_atomic_progress_predicate"
	assert rejected["target_predicates"] == ("unknown",)
	assert rejected["undeclared_predicates"] == ("unknown",)
	assert rejected["producer_actions_by_predicate"] == {}
	assert rejected["producible_target_predicates"] == ()


def test_atomic_progress_refinement_reports_wrong_arity_predicates(
	tmp_path: Path,
) -> None:
	domain_file, problem_file, _ = _write_counterexample_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="missing_module_or_context",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_progress",
		problem_file=str(problem_file),
		problem_name="training-p1",
		failure_reason="no applicable plan for !base(b, c)",
		ground_missing_goals=("base(b, c)",),
		lifted_missing_goals=("base(X, Y)",),
		required_rule_group_types=("counterexample_atomic_progress",),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_atomic_progress_constraints"][0]

	assert refinement["atomic_progress_required_group_count"] == 0
	assert refinement["rejected_atomic_progress_constraint_count"] == 1
	assert rejected["rejection_reason"] == "wrong_atomic_progress_predicate_arity"
	assert rejected["target_predicates"] == ("base",)
	assert rejected["wrong_arity_predicates"] == ("base",)
	assert rejected["producer_actions_by_predicate"] == {"base": ("make_base",)}
	assert rejected["producible_target_predicates"] == ("base",)


def test_atomic_progress_refinement_reports_unproducible_declared_predicates(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_unmatched_repair_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="missing_module_or_context",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_progress",
		problem_file=str(problem_file),
		problem_name="unmatched-repair-p1",
		failure_reason="no applicable plan for !calibrated(a)",
		ground_missing_goals=("calibrated(a)",),
		lifted_missing_goals=("calibrated(X)",),
		required_rule_group_types=("counterexample_atomic_progress",),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_atomic_progress_constraints"][0]

	assert refinement["atomic_progress_required_group_count"] == 0
	assert refinement["rejected_atomic_progress_constraint_count"] == 1
	assert rejected["rejection_reason"] == "unproducible_atomic_progress_predicate"
	assert rejected["target_predicates"] == ("calibrated",)
	assert rejected["producer_actions_by_predicate"] == {}
	assert rejected["producible_target_predicates"] == ()
	assert rejected["unproducible_target_predicates"] == ("calibrated",)
	assert any(
		(
			"reason=unproducible_atomic_progress_predicate" in failure
			and "unproducible=('calibrated',)" in failure
			and "producers={}" in failure
		)
		for failure in result.report["paper_profile_failures"]
	)


def test_unmatched_refinement_repair_constraints_are_reported_without_guessing(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_unmatched_repair_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="primitive_precondition_failure",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_precondition_repair",
		problem_file=str(problem_file),
		problem_name="unmatched-repair-p1",
		failure_reason="Action preconditions are not satisfied for finish(a).",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X)",),
		failing_action="finish",
		failing_action_arguments=("a",),
		lifted_failing_action="finish(X)",
		missing_preconditions=("calibrated(a)",),
		lifted_missing_preconditions=("calibrated(X)",),
		required_rule_group_types=(
			"counterexample_transition_progress",
			"counterexample_atomic_precondition_repair",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)

	refinement = result.report["counterexample_refinement_constraints"]
	assert result.report["repair_synthesized_candidate_count"] == 0
	assert refinement["explicit_repair_constraint_count"] == 1
	assert refinement["repair_required_group_count"] == 0
	assert refinement["rejected_repair_constraint_count"] == 1
	assert refinement["rejected_repair_constraints"][0]["target_predicates"] == ("done",)
	assert refinement["rejected_repair_constraints"][0]["precondition_predicates"] == (
		"calibrated",
	)
	assert refinement["rejected_repair_constraints"][0]["failing_action"] == "finish"
	assert refinement["rejected_repair_constraints"][0]["required_capabilities"] == (
		"module_done_prepare_calibrated_for_finish",
	)
	assert refinement["rejected_repair_constraints"][0]["rejection_reason"] == (
		"unproducible_precondition_predicate"
	)
	assert "module_calibrated_action_" not in " ".join(
		refinement["rejected_repair_constraints"][0]["available_capabilities"],
	)
	assert result.report["paper_profile_ready"] is False
	assert any(
		"unmatched primitive-precondition repair" in failure
		for failure in result.report["paper_profile_failures"]
	)

	with pytest.raises(ValueError, match="unmatched primitive-precondition repair"):
		synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=(problem_file,),
			refinement_constraints=(constraint,),
			synthesis_profile="paper",
		)


def test_unmatched_repair_reports_producible_precondition_without_prepare_rule(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_producible_but_unmatched_repair_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="primitive_precondition_failure",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_precondition_repair",
		problem_file=str(problem_file),
		problem_name="producible-unmatched-p1",
		failure_reason="Action preconditions are not satisfied for finish(a, b).",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X)",),
		failing_action="finish",
		failing_action_arguments=("a", "b"),
		lifted_failing_action="finish(X, Y)",
		missing_preconditions=("linked(a, b)",),
		lifted_missing_preconditions=("linked(X, Y)",),
		required_rule_group_types=(
			"counterexample_transition_progress",
			"counterexample_atomic_precondition_repair",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)

	rejected = result.report["counterexample_refinement_constraints"][
		"rejected_repair_constraints"
	][0]
	assert rejected["rejection_reason"] == "no_matching_lifted_prepare_rule"
	assert rejected["required_capabilities"] == (
		"module_done_prepare_linked_for_finish",
	)
	assert "module_linked_action_make_link" in rejected["available_capabilities"]
	assert "module_done_action_finish" in rejected["available_capabilities"]


def test_goal_bound_repair_synthesizes_missing_prepare_candidate(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_goal_bound_repair_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="primitive_precondition_failure",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_precondition_repair",
		problem_file=str(problem_file),
		problem_name="goal-bound-repair-p1",
		failure_reason="Action preconditions are not satisfied for finish(a, b).",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X)",),
		failing_action="finish",
		failing_action_arguments=("a", "b"),
		lifted_failing_action="finish(X, Y)",
		missing_preconditions=("linked(a, b)",),
		lifted_missing_preconditions=("linked(X, Y)",),
		required_rule_group_types=(
			"counterexample_transition_progress",
			"counterexample_atomic_precondition_repair",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]

	assert result.report["repair_synthesized_candidate_count"] == 1
	assert result.report["candidate_sources"]["counterexample_repair"] == 1
	assert result.report["selected_candidate_sources"]["counterexample_repair"] == 1
	assert refinement["repair_required_group_count"] == 1
	assert refinement["rejected_repair_constraint_count"] == 0
	assert refinement["repair_required_groups"][0]["rule_names"] == (
		"done_repair_prepare_linked_for_finish",
	)
	assert "done_repair_prepare_linked_for_finish" in result.report["selected_rule_names"]
	layer_b = result.report["evidence_matrix"]["layer_b_atomic_modules"]
	assert layer_b["repair_synthesized_candidate_count"] == 1
	assert layer_b["matched_repair_constraint_count"] == 1

	asl = render_plan_library_asl(result.plan_library)
	assert "+!done(X) : goal_linked(X, Y) & not linked(X, Y) <-" in asl
	assert "\t!linked(X, Y);" in asl
	assert "\t!done(X)." in asl
	assert "!achieve_" not in asl
	assert "!transition_" not in asl
	assert "dfa_state" not in asl


def test_repair_refinement_rejects_undeclared_target_predicate(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_goal_bound_repair_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="primitive_precondition_failure",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_precondition_repair",
		problem_file=str(problem_file),
		problem_name="bad-target-repair-p1",
		failure_reason="Action preconditions are not satisfied for finish(a, b).",
		ground_missing_goals=("unknown(a)",),
		lifted_missing_goals=("unknown(X)",),
		failing_action="finish",
		failing_action_arguments=("a", "b"),
		lifted_failing_action="finish(X, Y)",
		missing_preconditions=("linked(a, b)",),
		lifted_missing_preconditions=("linked(X, Y)",),
		required_rule_group_types=(
			"counterexample_transition_progress",
			"counterexample_atomic_precondition_repair",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_repair_constraints"][0]
	asl = render_plan_library_asl(result.plan_library)

	assert result.report["repair_synthesized_candidate_count"] == 0
	assert refinement["repair_required_group_count"] == 0
	assert rejected["rejection_reason"] == "undeclared_repair_predicate"
	assert rejected["target_predicates"] == ("unknown",)
	assert rejected["undeclared_predicates"] == ("unknown",)
	assert "!unknown(X)" not in asl
	assert "+!unknown(X)" not in asl


def test_repair_refinement_rejects_undeclared_precondition_predicate(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_goal_bound_repair_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="primitive_precondition_failure",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_precondition_repair",
		problem_file=str(problem_file),
		problem_name="bad-precondition-repair-p1",
		failure_reason="Action preconditions are not satisfied for finish(a, b).",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X)",),
		failing_action="finish",
		failing_action_arguments=("a", "b"),
		lifted_failing_action="finish(X, Y)",
		missing_preconditions=("unknown(a, b)",),
		lifted_missing_preconditions=("unknown(X, Y)",),
		required_rule_group_types=(
			"counterexample_transition_progress",
			"counterexample_atomic_precondition_repair",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_repair_constraints"][0]
	asl = render_plan_library_asl(result.plan_library)

	assert result.report["repair_synthesized_candidate_count"] == 0
	assert refinement["repair_required_group_count"] == 0
	assert rejected["rejection_reason"] == "undeclared_repair_predicate"
	assert rejected["precondition_predicates"] == ("unknown",)
	assert rejected["undeclared_predicates"] == ("unknown",)
	assert "!unknown(X, Y)" not in asl


def test_repair_refinement_rejects_wrong_target_predicate_arity(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_goal_bound_repair_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="primitive_precondition_failure",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_precondition_repair",
		problem_file=str(problem_file),
		problem_name="bad-target-arity-repair-p1",
		failure_reason="Action preconditions are not satisfied for finish(a, b).",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X, Y)",),
		failing_action="finish",
		failing_action_arguments=("a", "b"),
		lifted_failing_action="finish(X, Y)",
		missing_preconditions=("linked(a, b)",),
		lifted_missing_preconditions=("linked(X, Y)",),
		required_rule_group_types=(
			"counterexample_transition_progress",
			"counterexample_atomic_precondition_repair",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_repair_constraints"][0]
	asl = render_plan_library_asl(result.plan_library)

	assert result.report["repair_synthesized_candidate_count"] == 0
	assert refinement["repair_required_group_count"] == 0
	assert rejected["rejection_reason"] == "wrong_repair_predicate_arity"
	assert rejected["target_predicates"] == ("done",)
	assert "!done(X, Y)" not in asl


def test_repair_refinement_rejects_wrong_precondition_predicate_arity(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_goal_bound_repair_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="primitive_precondition_failure",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_precondition_repair",
		problem_file=str(problem_file),
		problem_name="bad-precondition-arity-repair-p1",
		failure_reason="Action preconditions are not satisfied for finish(a, b).",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X)",),
		failing_action="finish",
		failing_action_arguments=("a", "b"),
		lifted_failing_action="finish(X, Y)",
		missing_preconditions=("linked(a, b)",),
		lifted_missing_preconditions=("linked(X)",),
		required_rule_group_types=(
			"counterexample_transition_progress",
			"counterexample_atomic_precondition_repair",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_repair_constraints"][0]
	asl = render_plan_library_asl(result.plan_library)

	assert result.report["repair_synthesized_candidate_count"] == 0
	assert refinement["repair_required_group_count"] == 0
	assert rejected["rejection_reason"] == "wrong_repair_predicate_arity"
	assert rejected["precondition_predicates"] == ("linked",)
	assert "!linked(X)" not in asl


def test_repair_refinement_rejects_undeclared_failing_action(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_goal_bound_repair_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="primitive_precondition_failure",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_precondition_repair",
		problem_file=str(problem_file),
		problem_name="bad-action-repair-p1",
		failure_reason="Action preconditions are not satisfied for missing(a, b).",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X)",),
		failing_action="missing",
		failing_action_arguments=("a", "b"),
		lifted_failing_action="missing(X, Y)",
		missing_preconditions=("linked(a, b)",),
		lifted_missing_preconditions=("linked(X, Y)",),
		required_rule_group_types=(
			"counterexample_transition_progress",
			"counterexample_atomic_precondition_repair",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_repair_constraints"][0]

	assert result.report["repair_synthesized_candidate_count"] == 0
	assert refinement["repair_required_group_count"] == 0
	assert rejected["rejection_reason"] == "undeclared_repair_failing_action"
	assert rejected["failing_action"] == "missing"


def test_repair_refinement_rejects_wrong_failing_action_arity(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_goal_bound_repair_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="primitive_precondition_failure",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_precondition_repair",
		problem_file=str(problem_file),
		problem_name="bad-action-arity-repair-p1",
		failure_reason="Action preconditions are not satisfied for finish(a).",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X)",),
		failing_action="finish",
		failing_action_arguments=("a",),
		lifted_failing_action="finish(X)",
		missing_preconditions=("linked(a, b)",),
		lifted_missing_preconditions=("linked(X, Y)",),
		required_rule_group_types=(
			"counterexample_transition_progress",
			"counterexample_atomic_precondition_repair",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_repair_constraints"][0]

	assert result.report["repair_synthesized_candidate_count"] == 0
	assert refinement["repair_required_group_count"] == 0
	assert rejected["rejection_reason"] == "wrong_repair_failing_action_arity"
	assert rejected["failing_action"] == "finish"


def test_repair_refinement_rejects_negative_precondition_repairs(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_negative_repair_domain(tmp_path)
	constraint = RefinementConstraint(
		failure_kind="primitive_precondition_failure",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_precondition_repair",
		problem_file=str(problem_file),
		problem_name="negative-repair-p1",
		failure_reason="Action preconditions are not satisfied for finish(a).",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X)",),
		failing_action="finish",
		failing_action_arguments=("a",),
		lifted_failing_action="finish(X)",
		missing_preconditions=("not blocked(a)",),
		lifted_missing_preconditions=("not blocked(X)",),
		required_rule_group_types=(
			"counterexample_transition_progress",
			"counterexample_atomic_precondition_repair",
		),
	)

	result = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		refinement_constraints=(constraint,),
	)
	refinement = result.report["counterexample_refinement_constraints"]
	rejected = refinement["rejected_repair_constraints"][0]
	asl = render_plan_library_asl(result.plan_library)

	assert result.report["repair_synthesized_candidate_count"] == 0
	assert refinement["repair_required_group_count"] == 0
	assert rejected["rejection_reason"] == "negative_repair_precondition_unsupported"
	assert rejected["target_predicates"] == ("done",)
	assert rejected["precondition_predicates"] == ("blocked",)
	assert rejected["negative_precondition_predicates"] == ("blocked",)
	assert rejected["required_capabilities"] == ()
	assert "prepare_blocked_for_finish" not in asl
	assert any(
		"reason=negative_repair_precondition_unsupported" in failure
		for failure in result.report["paper_profile_failures"]
	)

	with pytest.raises(ValueError, match="negative_repair_precondition_unsupported"):
		synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=(problem_file,),
			refinement_constraints=(constraint,),
			synthesis_profile="paper",
		)


def _write_generic_domain_problem_and_policy(
	tmp_path: Path,
	*,
	policy_feature: str = '(f_done "n_count(c_equal(c_primitive(done,0),c_primitive(done_g,0)))")',
	policy_rule: str = "(:rule (:conditions ) (:effects (:e_n_inc f_done)))",
) -> tuple[Path, Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	policy_file = tmp_path / "policy.txt"
	domain_file.write_text(
		"""
		(define (domain generic)
		 (:requirements :strips)
		 (:predicates
		  (ready ?x)
		  (done ?x)
		 )
		 (:action finish
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p1)
		 (:domain generic)
		 (:objects a)
		 (:init (ready a))
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)
	policy_file.write_text(
		f"""
		(:policy
		(:booleans )
		(:numericals {policy_feature})
		{policy_rule}
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file, policy_file


def _write_binary_domain_problem_and_policy(tmp_path: Path) -> tuple[Path, Path, Path]:
	domain_file = tmp_path / "binary-domain.pddl"
	problem_file = tmp_path / "binary-problem.pddl"
	policy_file = tmp_path / "binary-policy.txt"
	domain_file.write_text(
		"""
		(define (domain generic-binary)
		 (:requirements :strips)
		 (:predicates
		  (ready ?x ?y)
		  (link ?x ?y)
		 )
		 (:action connect
		  :parameters (?x ?y)
		  :precondition (ready ?x ?y)
		  :effect (link ?x ?y)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem binary-p1)
		 (:domain generic-binary)
		 (:objects a b)
		 (:init (ready a b))
		 (:goal (and (link a b)))
		)
		""",
		encoding="utf-8",
	)
	policy_file.write_text(
		"""
		(:policy
		(:booleans )
		(:numericals
		 (f_link "n_count(c_equal(r_primitive(link,1,0),r_primitive(link_g,1,0)))")
		)
		(:rule (:conditions ) (:effects (:e_n_inc f_link)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file, policy_file


def _write_unobserved_action_domain_problem_and_policy(
	tmp_path: Path,
) -> tuple[Path, Path, Path]:
	domain_file = tmp_path / "unobserved-action-domain.pddl"
	problem_file = tmp_path / "unobserved-action-problem.pddl"
	policy_file = tmp_path / "unobserved-action-policy.txt"
	domain_file.write_text(
		"""
		(define (domain generic-unobserved-action)
		 (:requirements :strips)
		 (:predicates
		  (ready ?x)
		  (done ?x)
		  (bonus ?x)
		 )
		 (:action finish
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (done ?x)
		 )
		 (:action grant-bonus
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (bonus ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p1)
		 (:domain generic-unobserved-action)
		 (:objects a)
		 (:init (ready a))
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)
	policy_file.write_text(
		"""
		(:policy
		(:booleans )
		(:numericals (f_done "n_count(c_equal(c_primitive(done,0),c_primitive(done_g,0)))"))
		(:rule (:conditions ) (:effects (:e_n_inc f_done)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file, policy_file


def _write_multi_strategy_domain_and_problem(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "multi-strategy-domain.pddl"
	problem_file = tmp_path / "multi-strategy-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain generic-multi-strategy)
		 (:requirements :strips)
		 (:predicates
		  (ready ?x)
		  (done ?x)
		 )
		 (:action finish
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (done ?x)
		 )
		 (:action backup_finish
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p1)
		 (:domain generic-multi-strategy)
		 (:objects a)
		 (:init (ready a))
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_fake_learner_sketches_backend(tmp_path: Path) -> BackendManifest:
	backend_path = tmp_path / "learner-sketches"
	learning = backend_path / "learning"
	learning.mkdir(parents=True)
	(learning / "main.py").write_text(
		"""
from __future__ import annotations

import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--domain_filepath")
parser.add_argument("--problems_directory")
parser.add_argument("--workspace")
parser.add_argument("--width", type=int)
parser.add_argument("--max_num_states_per_instance")
parser.add_argument("--max_time_per_instance")
args = parser.parse_args()
output = Path(args.workspace) / "output"
output.mkdir(parents=True, exist_ok=True)
(output / f"sketch_minimized_{args.width}.txt").write_text(
	'''
	(:policy
	(:booleans )
	(:numericals (f_done "n_count(c_equal(c_primitive(done,0),c_primitive(done_g,0)))"))
	(:rule (:conditions ) (:effects (:e_n_inc f_done)))
	)
	''',
	encoding="utf-8",
)
print("fake learner completed")
		""",
		encoding="utf-8",
	)
	return BackendManifest(
		name="learner-sketches",
		path=backend_path,
		url="https://github.com/bonetblai/learner-sketches.git",
		expected_commit="7a7ea6a",
		present=True,
	)


def _write_prepare_order_domain_and_problem(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "prepare-domain.pddl"
	problem_file = tmp_path / "prepare-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain prepare-order)
		 (:requirements :strips)
		 (:predicates
		  (ready ?x)
		  (holding ?x)
		 )
		 (:action make_ready
		  :parameters (?x)
		  :precondition ()
		  :effect (ready ?x)
		 )
		 (:action grab
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (holding ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem prepare-p1)
		 (:domain prepare-order)
		 (:objects a)
		 (:init (ready a))
		 (:goal (and (holding a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_unmatched_repair_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "unmatched-repair-domain.pddl"
	problem_file = tmp_path / "unmatched-repair-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain unmatched-repair-mini)
		 (:requirements :strips)
		 (:predicates
		  (armed ?x)
		  (calibrated ?x)
		  (done ?x)
		 )
		 (:action arm
		  :parameters (?x)
		  :precondition ()
		  :effect (armed ?x)
		 )
		 (:action finish
		  :parameters (?x)
		  :precondition (armed ?x)
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem unmatched-repair-p1)
		 (:domain unmatched-repair-mini)
		 (:objects a)
		 (:init)
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_producible_but_unmatched_repair_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "producible-unmatched-domain.pddl"
	problem_file = tmp_path / "producible-unmatched-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain producible-unmatched-mini)
		 (:requirements :strips)
		 (:predicates
		  (seed ?x)
		  (linked ?x ?y)
		  (done ?x)
		 )
		 (:action make_link
		  :parameters (?x ?y)
		  :precondition (seed ?x)
		  :effect (linked ?x ?y)
		 )
		 (:action finish
		  :parameters (?x ?y)
		  :precondition (linked ?x ?y)
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem producible-unmatched-p1)
		 (:domain producible-unmatched-mini)
		 (:objects a b)
		 (:init (seed a))
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_goal_bound_repair_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "goal-bound-repair-domain.pddl"
	problem_file = tmp_path / "goal-bound-repair-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain goal-bound-repair-mini)
		 (:requirements :strips)
		 (:predicates
		  (seed ?x)
		  (linked ?x ?y)
		  (done ?x)
		 )
		 (:action make_link
		  :parameters (?x ?y)
		  :precondition (seed ?x)
		  :effect (linked ?x ?y)
		 )
		 (:action finish
		  :parameters (?x ?y)
		  :precondition (linked ?x ?y)
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem goal-bound-repair-p1)
		 (:domain goal-bound-repair-mini)
		 (:objects a b)
		 (:init (seed a))
		 (:goal (and (linked a b) (done a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_negative_repair_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "negative-repair-domain.pddl"
	problem_file = tmp_path / "negative-repair-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain negative-repair-mini)
		 (:requirements :strips :negative-preconditions)
		 (:predicates
		  (blocked ?x)
		  (done ?x)
		 )
		 (:action block
		  :parameters (?x)
		  :precondition ()
		  :effect (blocked ?x)
		 )
		 (:action finish
		  :parameters (?x)
		  :precondition (not (blocked ?x))
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem negative-repair-p1)
		 (:domain negative-repair-mini)
		 (:objects a)
		 (:init)
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_counterexample_domain(tmp_path: Path) -> tuple[Path, Path, Path]:
	domain_file = tmp_path / "counterexample-domain.pddl"
	training_problem = tmp_path / "training.pddl"
	counterexample_problem = tmp_path / "counterexample.pddl"
	domain_file.write_text(
		"""
		(define (domain counterexample-mini)
		 (:requirements :strips :typing)
		 (:types object)
		 (:predicates
		  (ready ?x - object)
		  (base ?x - object)
		  (top ?x - object)
		 )
		 (:action make_base
		  :parameters (?x - object)
		  :precondition (ready ?x)
		  :effect (base ?x)
		 )
		 (:action make_top
		  :parameters (?x - object)
		  :precondition (base ?x)
		  :effect (top ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	training_problem.write_text(
		"""
		(define (problem training-p1)
		 (:domain counterexample-mini)
		 (:objects a - object)
		 (:init (ready a))
		 (:goal (and (base a)))
		)
		""",
		encoding="utf-8",
	)
	counterexample_problem.write_text(
		"""
		(define (problem counterexample-p1)
		 (:domain counterexample-mini)
		 (:objects b - object)
		 (:init (ready b))
		 (:goal (and (base b) (top b)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, training_problem, counterexample_problem


def _write_precondition_repair_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "repair-domain.pddl"
	problem_file = tmp_path / "repair-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain repair-mini)
		 (:requirements :strips)
		 (:predicates
		  (seed ?x)
		  (armed ?x)
		  (done ?x)
		 )
		 (:action arm
		  :parameters (?x)
		  :precondition (seed ?x)
		  :effect (armed ?x)
		 )
		 (:action finish
		  :parameters (?x)
		  :precondition (armed ?x)
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem repair-p1)
		 (:domain repair-mini)
		 (:objects a)
		 (:init (seed a))
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file
