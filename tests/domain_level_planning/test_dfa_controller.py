from __future__ import annotations

import pytest

from domain_level_planning.dfa_controller import progress_transitions_from_dfa_state


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


def test_dfa_controller_rejects_empty_current_state() -> None:
	with pytest.raises(ValueError, match="current_dfa_state must be non-empty"):
		progress_transitions_from_dfa_state(
			dfa_payload={"guarded_transitions": []},
			current_dfa_state="",
		)
