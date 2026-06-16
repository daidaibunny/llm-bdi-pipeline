from __future__ import annotations

from pathlib import Path

from domain_level_planning.dfa_controller import (
	execute_dfa_progress_step,
	progress_requests_from_dfa_state,
)
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary


def test_dfa_controller_executes_guard_through_domain_level_library(tmp_path: Path) -> None:
	domain_file = _write_tiny_domain(tmp_path)
	plan_library = _tiny_plan_library()
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "done"},
		],
	}

	result = execute_dfa_progress_step(
		plan_library=plan_library,
		domain_file=domain_file,
		domain_key="tiny",
		dfa_payload=dfa_payload,
		current_dfa_state="q0",
		current_state=frozenset({"ready"}),
	)

	assert result.progressed is True
	assert result.source_dfa_state == "q0"
	assert result.target_dfa_state == "q1"
	assert result.request is not None
	assert result.request.goal_facts == ("goal_done",)
	assert result.request.body_steps == (AgentSpeakBodyStep("subgoal", "done", ()),)
	assert result.execution is not None
	assert result.execution.solved is True
	assert result.execution.steps == ("finish",)
	assert "done" in result.execution.final_state
	assert result.failed_attempts == ()


def test_dfa_controller_exposes_all_progress_requests_from_branching_state(
	tmp_path: Path,
) -> None:
	domain_file = _write_tiny_domain(tmp_path)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1", "q2"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "done"},
			{"source_state": "q0", "target_state": "q2", "raw_label": "ready"},
			{"source_state": "dead", "target_state": "dead", "raw_label": "true"},
		],
	}

	requests = progress_requests_from_dfa_state(
		dfa_payload=dfa_payload,
		current_dfa_state="q0",
		domain_key="tiny",
		domain_file=domain_file,
	)

	assert [request.target_state for request in requests] == ["q1", "q2"]
	assert [request.goal_facts for request in requests] == [
		("goal_done",),
		("goal_ready",),
	]
	assert [request.body_steps for request in requests] == [
		(AgentSpeakBodyStep("subgoal", "done", ()),),
		(AgentSpeakBodyStep("subgoal", "ready", ()),),
	]


def test_dfa_controller_rejects_guard_outside_pddl_schema(tmp_path: Path) -> None:
	domain_file = _write_tiny_domain(tmp_path)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "unknown"},
		],
	}

	try:
		progress_requests_from_dfa_state(
			dfa_payload=dfa_payload,
			current_dfa_state="q0",
			domain_key="tiny",
			domain_file=domain_file,
		)
	except ValueError as exc:
		assert "undeclared PDDL predicate 'unknown'" in str(exc)
	else:
		raise AssertionError("Expected undeclared DFA guard predicate to fail.")


def _tiny_plan_library() -> PlanLibrary:
	return PlanLibrary(
		domain_name="tiny",
		plans=(
			AgentSpeakPlan(
				plan_name="g_satisfy_done",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("goal_done", "not done"),
				body=(
					AgentSpeakBodyStep("subgoal", "done"),
					AgentSpeakBodyStep("subgoal", "g"),
				),
			),
			AgentSpeakPlan(
				plan_name="done_already",
				trigger=AgentSpeakTrigger("achievement_goal", "done"),
				context=("done",),
				body=(),
			),
			AgentSpeakPlan(
				plan_name="done_via_finish",
				trigger=AgentSpeakTrigger("achievement_goal", "done"),
				context=("ready",),
				body=(AgentSpeakBodyStep("action", "finish"),),
			),
		),
	)


def _write_tiny_domain(tmp_path: Path) -> Path:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain tiny)
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
	return domain_file
