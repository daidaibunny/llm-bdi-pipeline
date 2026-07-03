from __future__ import annotations

import pytest

from domain_level_planning.dfa_controller import (
	inspect_progress_requests_from_dfa_state,
	progress_requests_from_dfa_state,
	progress_transitions_from_dfa_state,
)
from plan_library.models import AgentSpeakBodyStep


def test_dfa_controller_filters_non_progress_transitions() -> None:
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "done"},
			{"source_state": "q0", "target_state": "q0", "raw_label": "ready"},
			{"source_state": "q0", "target_state": "dead", "raw_label": "lost"},
			{"source_state": "dead", "target_state": "dead", "raw_label": "true"},
		],
	}

	assert progress_transitions_from_dfa_state(
		dfa_payload=dfa_payload,
		current_dfa_state="q0",
	) == (
		{"source_state": "q0", "target_state": "q1", "raw_label": "done"},
	)


def test_dfa_controller_returns_all_shorter_acceptance_edges() -> None:
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1", "q2"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "done"},
			{"source_state": "q0", "target_state": "q2", "raw_label": "ready"},
			{"source_state": "q0", "target_state": "q0", "raw_label": "wait"},
		],
	}

	assert progress_transitions_from_dfa_state(
		dfa_payload=dfa_payload,
		current_dfa_state="q0",
	) == (
		{"source_state": "q0", "target_state": "q1", "raw_label": "done"},
		{"source_state": "q0", "target_state": "q2", "raw_label": "ready"},
	)


def test_dfa_controller_returns_progress_achievement_requests(
	tmp_path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain tiny)
		 (:requirements :strips)
		 (:predicates (ready) (done))
		)
		""",
		encoding="utf-8",
	)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1", "q2"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "done"},
			{"source_state": "q0", "target_state": "q2", "raw_label": "ready"},
			{"source_state": "q0", "target_state": "q0", "raw_label": "wait"},
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


def test_dfa_controller_reports_progress_request_diagnostics(tmp_path) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain tiny)
		 (:requirements :strips)
		 (:predicates (ready) (done))
		)
		""",
		encoding="utf-8",
	)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1", "q2"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "not done"},
			{"source_state": "q0", "target_state": "q2", "raw_label": "ready"},
		],
	}

	diagnostics = inspect_progress_requests_from_dfa_state(
		dfa_payload=dfa_payload,
		current_dfa_state="q0",
		domain_key="tiny",
		domain_file=domain_file,
	)

	assert [diagnostic["target_state"] for diagnostic in diagnostics] == ["q1", "q2"]
	assert [diagnostic["supported"] for diagnostic in diagnostics] == [False, True]
	assert diagnostics[0]["rejection_reason"] == "unsupported_negative_guard"
	assert diagnostics[1]["request"]["goal_facts"] == ["goal_ready"]


def test_dfa_controller_rejects_empty_current_state() -> None:
	with pytest.raises(ValueError, match="current_dfa_state must be non-empty"):
		progress_transitions_from_dfa_state(
			dfa_payload={"guarded_transitions": []},
			current_dfa_state="",
		)
