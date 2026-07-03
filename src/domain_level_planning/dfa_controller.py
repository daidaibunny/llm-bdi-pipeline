"""
DFA transition utilities for the temporal append layer.

The current framework keeps temporal controller state outside the ASL library.
This module only identifies outgoing transitions that reduce graph distance to
an accepting DFA state. It does not execute an old in-repository generalized
planner or full-trace simulator.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Mapping, Sequence

from .dfa_adapter import DFAAchievementRequest
from .dfa_adapter import adapt_dfa_guarded_transition_to_achievement_request
from .dfa_adapter import inspect_dfa_guard_to_achievement_request


def progress_requests_from_dfa_state(
	*,
	dfa_payload: Mapping[str, Any],
	current_dfa_state: str,
	domain_key: str,
	domain_file: str | Path | None = None,
	declared_predicates: Sequence[object] | Mapping[str, int | None] = (),
) -> tuple[DFAAchievementRequest, ...]:
	"""Return schema-valid achievement requests for accepting-progress edges."""

	return tuple(
		adapt_dfa_guarded_transition_to_achievement_request(
			transition,
			domain_key=domain_key,
			domain_file=domain_file,
			declared_predicates=declared_predicates,
		)
		for transition in progress_transitions_from_dfa_state(
			dfa_payload=dfa_payload,
			current_dfa_state=current_dfa_state,
		)
	)


def inspect_progress_requests_from_dfa_state(
	*,
	dfa_payload: Mapping[str, Any],
	current_dfa_state: str,
	domain_key: str,
	domain_file: str | Path | None = None,
	declared_predicates: Sequence[object] | Mapping[str, int | None] = (),
) -> tuple[dict[str, object], ...]:
	"""Return support diagnostics for accepting-progress DFA transitions."""

	diagnostics: list[dict[str, object]] = []
	for transition in progress_transitions_from_dfa_state(
		dfa_payload=dfa_payload,
		current_dfa_state=current_dfa_state,
	):
		diagnostic = inspect_dfa_guard_to_achievement_request(
			transition["raw_label"],
			domain_key=domain_key,
			domain_file=domain_file,
			declared_predicates=declared_predicates,
		).to_dict()
		diagnostic["source_state"] = transition["source_state"]
		diagnostic["target_state"] = transition["target_state"]
		diagnostics.append(diagnostic)
	return tuple(diagnostics)


def progress_transitions_from_dfa_state(
	*,
	dfa_payload: Mapping[str, Any],
	current_dfa_state: str,
) -> tuple[dict[str, str], ...]:
	"""Return outgoing DFA transition records that reduce distance to acceptance."""

	state = str(current_dfa_state or "").strip()
	if not state:
		raise ValueError("current_dfa_state must be non-empty.")
	accepting_states = _accepting_states(dfa_payload)
	transitions = _normalise_transitions(dfa_payload)
	distances = _distances_to_accepting(transitions, accepting_states)
	return tuple(
		transition
		for transition in transitions
		if _is_progress_transition(
			transition,
			current_dfa_state=state,
			distances=distances,
			accepting_states=accepting_states,
		)
	)


def _normalise_transitions(dfa_payload: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
	transitions: list[dict[str, str]] = []
	for item in tuple(dfa_payload.get("guarded_transitions") or ()):
		if not isinstance(item, Mapping):
			continue
		source_state = str(item.get("source_state") or "").strip()
		target_state = str(item.get("target_state") or "").strip()
		if not source_state or not target_state:
			continue
		transitions.append(
			{
				"source_state": source_state,
				"target_state": target_state,
				"raw_label": str(item.get("raw_label") or "true").strip() or "true",
			},
		)
	return tuple(transitions)


def _accepting_states(dfa_payload: Mapping[str, Any]) -> frozenset[str]:
	return frozenset(
		str(state).strip()
		for state in tuple(dfa_payload.get("accepting_states") or ())
		if str(state).strip()
	)


def _distances_to_accepting(
	transitions: tuple[dict[str, str], ...],
	accepting_states: frozenset[str],
) -> dict[str, int]:
	reverse_edges: dict[str, set[str]] = {}
	for transition in transitions:
		reverse_edges.setdefault(transition["target_state"], set()).add(
			transition["source_state"],
		)
	distances = {state: 0 for state in accepting_states}
	queue = deque(accepting_states)
	while queue:
		state = queue.popleft()
		for predecessor in reverse_edges.get(state, ()):
			if predecessor in distances:
				continue
			distances[predecessor] = distances[state] + 1
			queue.append(predecessor)
	return distances


def _is_progress_transition(
	transition: Mapping[str, str],
	*,
	current_dfa_state: str,
	distances: Mapping[str, int],
	accepting_states: frozenset[str],
) -> bool:
	if transition["source_state"] != current_dfa_state:
		return False
	if current_dfa_state in accepting_states:
		return False
	if current_dfa_state not in distances:
		return False
	target_state = transition["target_state"]
	return target_state in distances and distances[target_state] < distances[current_dfa_state]
