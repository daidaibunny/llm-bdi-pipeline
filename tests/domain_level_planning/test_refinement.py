from __future__ import annotations

from pathlib import Path

from domain_level_planning.library_executor import evaluate_library_on_problem
from domain_level_planning.refinement import synthesize_with_counterexample_refinement
from plan_library.rendering import render_plan_library_asl


def test_counterexample_refinement_adds_failed_problem_and_learns_goal_ordering(
	tmp_path: Path,
) -> None:
	domain_file, single_goal_problem, dependent_problem = _write_ordering_domain(tmp_path)

	refined = synthesize_with_counterexample_refinement(
		domain_file=domain_file,
		training_problem_files=(single_goal_problem,),
		heldout_problem_files=(dependent_problem,),
		max_refinement_rounds=1,
		max_execution_steps=20,
		max_depth=20,
	)

	assert refined.converged is True
	assert len(refined.rounds) == 2
	assert refined.rounds[0].heldout_evaluations[0].solved is False
	assert refined.rounds[0].heldout_evaluations[0].counterexample is not None
	assert refined.rounds[0].added_counterexample_problem_files == (
		str(dependent_problem.resolve()),
	)
	assert refined.rounds[1].heldout_evaluations[0].solved is True
	assert str(dependent_problem.resolve()) in refined.rounds[1].training_problem_files

	asl = render_plan_library_asl(refined.final_result.plan_library)
	assert "+!g : goal_z_base(Y) & goal_a_top(X, Y) & not z_base(Y) <-" in asl
	assert "\t!z_base(Y);" in asl
	assert "!achieve_" not in asl
	assert "!transition_" not in asl
	assert "dfa_state" not in asl

	execution = evaluate_library_on_problem(
		plan_library=refined.final_result.plan_library,
		domain_file=domain_file,
		problem_file=dependent_problem,
		max_steps=20,
		max_depth=20,
	)
	assert execution.solved is True
	assert execution.steps == ("make_base(b)", "make_top(a, b)")


def _write_ordering_domain(tmp_path: Path) -> tuple[Path, Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	single_goal_problem = tmp_path / "single-goal.pddl"
	dependent_problem = tmp_path / "dependent-goals.pddl"
	domain_file.write_text(
		"""
		(define (domain ordering-mini)
		 (:requirements :strips :typing)
		 (:types object)
		 (:predicates
		  (seed ?x - object)
		  (a_top ?x - object ?y - object)
		  (z_base ?x - object)
		 )
		 (:action make_base
		  :parameters (?x - object)
		  :precondition (seed ?x)
		  :effect (z_base ?x)
		 )
		 (:action make_top
		  :parameters (?x - object ?y - object)
		  :precondition (and (seed ?x) (seed ?y))
		  :effect (and (a_top ?x ?y) (not (seed ?y)))
		 )
		)
		""",
		encoding="utf-8",
	)
	single_goal_problem.write_text(
		"""
		(define (problem single-goal)
		 (:domain ordering-mini)
		 (:objects a b - object)
		 (:init (seed a) (seed b))
		 (:goal (and (a_top a b)))
		)
		""",
		encoding="utf-8",
	)
	dependent_problem.write_text(
		"""
		(define (problem dependent-goals)
		 (:domain ordering-mini)
		 (:objects a b - object)
		 (:init (seed a) (seed b))
		 (:goal (and (z_base b) (a_top a b)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, single_goal_problem, dependent_problem
