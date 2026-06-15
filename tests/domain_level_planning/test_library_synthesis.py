from __future__ import annotations

from pathlib import Path

from domain_level_planning.gp_backends import BackendManifest
from domain_level_planning.gp_backends import LearnerSketchesRunConfig
from domain_level_planning.library_synthesis import (
	ExternalSketchPolicySource,
	synthesize_domain_level_asl_library,
)
from plan_library.rendering import render_plan_library_asl
import pytest


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
	assert result.report["paper_quality_checks"] == (
		"transition_progress",
		"bounded_all_reachable_states",
		"acyclic_high_level_decision_trace",
		"goal_state_fixed_point",
	)
	assert result.report["bounded_validation"]["passed"] is True
	assert result.report["bounded_validation"]["counterexample_count"] == 0
	assert result.report["external_policy_count"] == 1
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
	assert result.report["bounded_validation"]["checked_problem_count"] == 2
	transition_system_names = tuple(
		transition["problem_name"]
		for transition in result.plan_library.metadata["counterexample_transition_systems"]
	)
	assert transition_system_names == ("counterexample-p1",)


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
