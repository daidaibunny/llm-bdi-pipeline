"""
Runtime controller that routes DFA progress guards to a domain-level ASL library.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from plan_library.models import PlanLibrary

from .dfa_adapter import DFAAchievementRequest
from .dfa_adapter import adapt_dfa_guarded_transition_to_achievement_request
from .dfa_adapter import inspect_dfa_guard_to_achievement_request
from .library_executor import LibraryExecutionResult
from .library_executor import execute_library_from_state


@dataclass(frozen=True)
class DFAProgressExecutionResult:
	"""Execution result for one DFA progress attempt through the lifted library."""

	progressed: bool
	source_dfa_state: str
	target_dfa_state: str | None
	request: DFAAchievementRequest | None
	execution: LibraryExecutionResult | None
	failed_attempts: tuple[dict[str, object], ...] = ()
	failure_reason: str | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"progressed": self.progressed,
			"source_dfa_state": self.source_dfa_state,
			"target_dfa_state": self.target_dfa_state,
			"request": self.request.to_dict() if self.request is not None else None,
			"execution": _execution_to_dict(self.execution),
			"failed_attempts": [dict(attempt) for attempt in self.failed_attempts],
			"failure_reason": self.failure_reason,
		}


@dataclass(frozen=True)
class DFARunExecutionResult:
	"""Execution result for repeatedly progressing a DFA until acceptance."""

	accepted: bool
	initial_dfa_state: str
	final_dfa_state: str
	initial_state: frozenset[str]
	final_state: frozenset[str]
	progress_steps: tuple[DFAProgressExecutionResult, ...]
	primitive_steps: tuple[str, ...]
	failure_reason: str | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"accepted": self.accepted,
			"initial_dfa_state": self.initial_dfa_state,
			"final_dfa_state": self.final_dfa_state,
			"initial_state": sorted(self.initial_state),
			"final_state": sorted(self.final_state),
			"progress_steps": [step.to_dict() for step in self.progress_steps],
			"primitive_steps": list(self.primitive_steps),
			"failure_reason": self.failure_reason,
		}


def progress_requests_from_dfa_state(
	*,
	dfa_payload: Mapping[str, Any],
	current_dfa_state: str,
	domain_key: str,
	domain_file: str | Path | None = None,
	declared_predicates: Sequence[object] | Mapping[str, int | None] = (),
) -> tuple[DFAAchievementRequest, ...]:
	"""Return all schema-valid outgoing DFA requests that reduce distance to acceptance."""

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
	"""Return support diagnostics for outgoing DFA progress transitions."""

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


def execute_dfa_progress_step(
	*,
	plan_library: PlanLibrary,
	domain_file: str | Path,
	domain_key: str,
	dfa_payload: Mapping[str, Any],
	current_dfa_state: str,
	current_state: frozenset[str],
	declared_predicates: Sequence[object] | Mapping[str, int | None] = (),
	max_execution_steps: int = 2000,
	max_depth: int = 200,
	backtrack_on_body_failure: bool = False,
) -> DFAProgressExecutionResult:
	"""Try each progress guard and execute the first one solved by the library."""

	requests = progress_requests_from_dfa_state(
		dfa_payload=dfa_payload,
		current_dfa_state=current_dfa_state,
		domain_key=domain_key,
		domain_file=domain_file,
		declared_predicates=declared_predicates,
	)
	failed_attempts: list[dict[str, object]] = []
	for request in requests:
		execution = execute_library_from_state(
			plan_library=plan_library,
			domain_file=domain_file,
			problem_name=f"dfa:{request.source_state}->{request.target_state}",
			initial_state=current_state,
			goal_facts=request.goal_facts,
			goal_atoms=request.state_literals,
			max_steps=max_execution_steps,
			max_depth=max_depth,
			backtrack_on_body_failure=backtrack_on_body_failure,
		)
		if execution.solved:
			return DFAProgressExecutionResult(
				progressed=True,
				source_dfa_state=str(request.source_state or current_dfa_state),
				target_dfa_state=request.target_state,
				request=request,
				execution=execution,
				failed_attempts=tuple(failed_attempts),
			)
		failed_attempts.append(
			{
				"target_dfa_state": request.target_state,
				"raw_guard": request.raw_guard,
				"goal_facts": list(request.goal_facts),
				"failure_reason": execution.failure_reason,
			},
		)
	return DFAProgressExecutionResult(
		progressed=False,
		source_dfa_state=str(current_dfa_state or "").strip(),
		target_dfa_state=None,
		request=None,
		execution=None,
		failed_attempts=tuple(failed_attempts),
		failure_reason=(
			"no executable DFA progress transition"
			if requests
			else "no DFA progress transition from current state"
		),
	)


def execute_dfa_until_accepting(
	*,
	plan_library: PlanLibrary,
	domain_file: str | Path,
	domain_key: str,
	dfa_payload: Mapping[str, Any],
	initial_state: frozenset[str],
	initial_dfa_state: str | None = None,
	declared_predicates: Sequence[object] | Mapping[str, int | None] = (),
	max_progress_steps: int = 64,
	max_execution_steps_per_progress: int = 2000,
	max_depth: int = 200,
	backtrack_on_body_failure: bool = False,
) -> DFARunExecutionResult:
	"""Execute DFA progress requests through the library until an accepting state."""

	if max_progress_steps < 0:
		raise ValueError("max_progress_steps must be non-negative.")
	accepting_states = _accepting_states(dfa_payload)
	current_dfa_state = str(
		initial_dfa_state
		or dfa_payload.get("initial_state")
		or "",
	).strip()
	if not current_dfa_state:
		raise ValueError("DFA payload must include an initial_state or receive initial_dfa_state.")
	current_state = frozenset(initial_state)
	progress_steps: list[DFAProgressExecutionResult] = []
	primitive_steps: tuple[str, ...] = ()

	while current_dfa_state not in accepting_states:
		if len(progress_steps) >= max_progress_steps:
			return DFARunExecutionResult(
				accepted=False,
				initial_dfa_state=str(initial_dfa_state or dfa_payload.get("initial_state") or ""),
				final_dfa_state=current_dfa_state,
				initial_state=frozenset(initial_state),
				final_state=current_state,
				progress_steps=tuple(progress_steps),
				primitive_steps=primitive_steps,
				failure_reason="DFA progress step limit exceeded",
			)
		step_result = execute_dfa_progress_step(
			plan_library=plan_library,
			domain_file=domain_file,
			domain_key=domain_key,
			dfa_payload=dfa_payload,
			current_dfa_state=current_dfa_state,
			current_state=current_state,
			declared_predicates=declared_predicates,
			max_execution_steps=max_execution_steps_per_progress,
			max_depth=max_depth,
			backtrack_on_body_failure=backtrack_on_body_failure,
		)
		progress_steps.append(step_result)
		if not step_result.progressed or step_result.execution is None or step_result.target_dfa_state is None:
			return DFARunExecutionResult(
				accepted=False,
				initial_dfa_state=str(initial_dfa_state or dfa_payload.get("initial_state") or ""),
				final_dfa_state=current_dfa_state,
				initial_state=frozenset(initial_state),
				final_state=current_state,
				progress_steps=tuple(progress_steps),
				primitive_steps=primitive_steps,
				failure_reason=step_result.failure_reason,
			)
		current_dfa_state = step_result.target_dfa_state
		current_state = frozenset(step_result.execution.final_state)
		primitive_steps = primitive_steps + tuple(step_result.execution.steps)

	return DFARunExecutionResult(
		accepted=True,
		initial_dfa_state=str(initial_dfa_state or dfa_payload.get("initial_state") or ""),
		final_dfa_state=current_dfa_state,
		initial_state=frozenset(initial_state),
		final_state=current_state,
		progress_steps=tuple(progress_steps),
		primitive_steps=primitive_steps,
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


def _execution_to_dict(execution: LibraryExecutionResult | None) -> dict[str, object] | None:
	if execution is None:
		return None
	return {
		"problem_name": execution.problem_name,
		"solved": execution.solved,
		"steps": list(execution.steps),
		"final_state": sorted(execution.final_state),
		"failure_reason": execution.failure_reason,
	}
