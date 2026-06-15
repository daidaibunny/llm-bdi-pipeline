from __future__ import annotations

from pathlib import Path

from domain_level_planning.library_verifier import (
	validate_library_on_bounded_transition_systems,
)
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary


def test_bounded_verifier_reports_structured_counterexamples_for_refinement(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_tiny_domain_and_problem(tmp_path)
	empty_library = PlanLibrary(
		domain_name="tiny",
		plans=(
			AgentSpeakPlan(
				plan_name="g_noop",
				trigger=AgentSpeakTrigger(
					event_type="achievement_goal",
					symbol="g",
				),
				context=("goal_done", "not done"),
				body=(),
			),
		),
	)

	report = validate_library_on_bounded_transition_systems(
		plan_library=empty_library,
		domain_file=domain_file,
		problem_files=(problem_file,),
		max_reachable_states=4,
		max_execution_steps=4,
		max_depth=4,
	)

	assert report.passed is False
	assert report.failure_count > 0
	assert report.counterexamples
	counterexample = report.counterexamples[0]
	assert counterexample.problem_name == "tiny-p1"
	assert counterexample.state_index >= 0
	assert "execution failed" in counterexample.failure_reason
	assert counterexample.goal_facts == ("goal_done",)
	assert counterexample.goal_atoms == ("done",)
	assert counterexample.to_dict()["state"] == list(counterexample.state)
	assert report.to_dict()["counterexample_count"] == len(report.counterexamples)
	assert report.problem_reports[0].counterexamples == report.counterexamples


def _write_tiny_domain_and_problem(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain tiny)
		 (:requirements :strips)
		 (:predicates (ready) (done))
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
		(define (problem tiny-p1)
		 (:domain tiny)
		 (:objects)
		 (:init (ready))
		 (:goal (and (done)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file
