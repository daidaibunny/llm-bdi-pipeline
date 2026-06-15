from __future__ import annotations

from pathlib import Path

from domain_level_planning.library_executor import evaluate_library_on_problem
from domain_level_planning.library_verifier import (
	validate_library_on_bounded_transition_systems,
)
from domain_level_planning.library_synthesis import synthesize_domain_level_asl_library
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary
from plan_library.rendering import render_plan_library_asl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_ROOT = PROJECT_ROOT / "src" / "domains" / "blocksworld"
BLOCKS_DOMAIN = BLOCKS_ROOT / "domain.pddl"
BLOCKS_PROBLEMS = tuple(sorted((BLOCKS_ROOT / "problems").glob("p*.pddl")))


def test_lifted_blocksworld_library_from_one_training_problem_solves_first_20() -> None:
	result = synthesize_domain_level_asl_library(
		domain_file=BLOCKS_DOMAIN,
		training_problem_files=(BLOCKS_PROBLEMS[0],),
	)
	plan_library = result.plan_library
	asl = render_plan_library_asl(plan_library)

	assert len(plan_library.plans) == 29
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl

	results = tuple(
		evaluate_library_on_problem(
			plan_library=plan_library,
			domain_file=BLOCKS_DOMAIN,
			problem_file=problem_file,
			max_steps=10000,
			max_depth=1000,
		)
		for problem_file in BLOCKS_PROBLEMS[:20]
	)

	assert [result.problem_name for result in results] == [
		f"p{index:02d}"
		for index in range(1, 21)
	]
	assert all(result.solved for result in results), [
		(result.problem_name, result.failure_reason)
		for result in results
		if not result.solved
	]
	assert [len(result.steps) for result in results] == [
		12,
		30,
		24,
		32,
		64,
		66,
		44,
		88,
		76,
		74,
		94,
		90,
		90,
		128,
		102,
		116,
		122,
		126,
		120,
		172,
	]

	bounded_validation = result.report["bounded_validation"]
	assert bounded_validation["passed"] is True
	assert bounded_validation["execution_semantics"] == "deterministic_first_applicable_asl"
	assert bounded_validation["checked_problem_count"] == 1
	assert bounded_validation["checked_state_count"] > 1
	assert bounded_validation["failure_count"] == 0


def test_bounded_verifier_checks_all_reachable_states_for_small_domain(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_tiny_switch_domain(tmp_path)
	plan_library = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
	).plan_library

	report = validate_library_on_bounded_transition_systems(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_files=(problem_file,),
		max_reachable_states=10,
		max_execution_steps=10,
		max_depth=10,
	)

	assert report.passed is True
	assert report.checked_problem_count == 1
	assert report.checked_state_count == 2
	assert report.problem_reports[0].goal_state_count == 1
	assert report.problem_reports[0].max_execution_steps == 1


def test_executor_can_disable_planner_style_body_failure_backtracking(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_two_action_domain(tmp_path)
	plan_library = PlanLibrary(
		domain_name="two-action",
		plans=(
			AgentSpeakPlan(
				plan_name="bad_first",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("goal_done", "ready"),
				body=(AgentSpeakBodyStep("action", "wrong"),),
			),
			AgentSpeakPlan(
				plan_name="good_second",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("goal_done", "ready"),
				body=(AgentSpeakBodyStep("action", "finish"),),
			),
		),
	)

	with_backtracking = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
		backtrack_on_body_failure=True,
	)
	without_backtracking = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
		backtrack_on_body_failure=False,
	)

	assert with_backtracking.solved is True
	assert with_backtracking.steps == ("finish",)
	assert without_backtracking.solved is False
	assert "preconditions" in str(without_backtracking.failure_reason).lower()
	assert "wrong" in str(without_backtracking.failure_reason)


def _write_tiny_switch_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain tiny-switch)
		 (:requirements :strips)
		 (:predicates (ready) (done))
		 (:action finish
		  :parameters ()
		  :precondition (ready)
		  :effect (and (not (ready)) (done))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem tiny-p1)
		 (:domain tiny-switch)
		 (:objects)
		 (:init (ready))
		 (:goal (and (done)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_two_action_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain two-action)
		 (:requirements :strips)
		 (:predicates (ready) (wrong-ready) (done))
		 (:action wrong
		  :parameters ()
		  :precondition (wrong-ready)
		  :effect (done)
		 )
		 (:action finish
		  :parameters ()
		  :precondition (ready)
		  :effect (done)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem two-action-p1)
		 (:domain two-action)
		 (:objects)
		 (:init (ready))
		 (:goal (and (done)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file
