from __future__ import annotations

from pathlib import Path

from domain_level_planning.library_synthesis import (
	ExternalSketchPolicySource,
	synthesize_domain_level_asl_library,
)
from plan_library.rendering import render_plan_library_asl


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
	assert result.report["paper_quality_checks"] == (
		"transition_progress",
		"bounded_all_reachable_states",
		"acyclic_high_level_decision_trace",
		"goal_state_fixed_point",
	)
	assert result.report["bounded_validation"]["passed"] is True
	assert result.report["external_policy_count"] == 1
	assert result.report["candidate_sources"]["external_sketch"] >= 1
	assert result.report["candidate_sources"]["schema"] >= 1
	assert "+!g : goal_done(X0) & not done(X0) <-" in asl
	assert "\t!done(X0);" in asl
	assert "+!done(X) : ready(X) <-" in asl
	assert "\tfinish(X)." in asl
	assert "!achieve_" not in asl
	assert "!transition_" not in asl
	assert "dfa_state" not in asl


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
