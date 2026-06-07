"""
Generate context-driven AgentSpeak(L) plans from DFA progress transitions.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Tuple

from temporal_specification.pddl_mapping import map_event_expression_to_pddl_context

from .models import AgentSpeakBodyStep, AgentSpeakPlan, AgentSpeakTrigger, PlanLibrary


@dataclass(frozen=True)
class LowLevelPlanningRequest:
	"""Transition-level request passed to the low-level planner adapter."""

	plan_name: str
	instruction_id: str
	source_state: str
	target_state: str
	context: Tuple[str, ...]
	target_context: Tuple[str, ...]
	source_context: Tuple[str, ...]
	cumulative_context: Tuple[str, ...]
	raw_label: str


@dataclass(frozen=True)
class LowLevelPlanningResponse:
	"""Low-level ASL body fragment for one generated transition plan."""

	body_steps: Tuple[AgentSpeakBodyStep, ...]
	certificate: Dict[str, Any]
	warnings: Tuple[str, ...] = ()


LowLevelPlannerFactory = Callable[[LowLevelPlanningRequest], LowLevelPlanningResponse]


def build_high_level_plan_library_from_dfa(
	*,
	domain_key: str,
	domain_name: str,
	instruction_id: str,
	dfa_payload: Dict[str, Any],
	low_level_planner: LowLevelPlannerFactory | None = None,
) -> PlanLibrary:
	"""Build a context-driven plan library from DFA transitions that progress."""

	initial_state = str(dfa_payload.get("initial_state") or "").strip()
	if not initial_state:
		raise ValueError("DFA payload must include an initial_state.")

	accepting_states = frozenset(
		str(state).strip()
		for state in (dfa_payload.get("accepting_states") or ())
		if str(state).strip()
	)
	transitions = tuple(
		_normalise_transition(transition)
		for transition in (dfa_payload.get("guarded_transitions") or ())
		if isinstance(transition, dict)
	)
	transitions = tuple(transition for transition in transitions if transition is not None)
	distances = _distances_to_accepting(transitions, accepting_states)
	progress_transitions = tuple(
		transition
		for transition in transitions
		if _is_progress_transition(transition, distances, accepting_states)
	)
	progress_transitions = tuple(
		sorted(
			progress_transitions,
			key=lambda transition: (
				-distances.get(transition["source_state"], -1),
				transition["source_state"],
				transition["target_state"],
				transition["raw_label"],
			),
		),
	)
	prefixes_by_state = _progress_prefixes_by_state(
		initial_state=initial_state,
		progress_transitions=progress_transitions,
		domain_key=domain_key,
	)
	plans: List[AgentSpeakPlan] = []
	warnings: List[str] = []

	for accepting_context in _accepting_contexts(accepting_states, prefixes_by_state):
		plans.append(
			AgentSpeakPlan(
				plan_name=f"{instruction_id}_accept_{len(plans) + 1}",
				trigger=AgentSpeakTrigger(event_type="achievement_goal", symbol="g"),
				context=accepting_context or ("true",),
				body=(),
				source_instruction_ids=(instruction_id,),
			),
		)

	for index, transition in enumerate(progress_transitions, start=1):
		source_state = transition["source_state"]
		target_state = transition["target_state"]
		raw_label = transition["raw_label"]
		if target_state in accepting_states and raw_label.lower() == "true":
			continue
		target_context = _context_from_label(raw_label, domain_key=domain_key)
		source_prefixes = prefixes_by_state.get(source_state) or ((),)
		blocking_contexts = _blocking_contexts(
			source_state=source_state,
			target_transition=transition,
			progress_transitions=progress_transitions,
			all_transitions=transitions,
			distances=distances,
			domain_key=domain_key,
		)
		for prefix_index, source_prefix in enumerate(source_prefixes, start=1):
			cumulative_context = _deduplicate_literals(source_prefix + target_context)
			for blocking_index, blocking_context in enumerate(blocking_contexts, start=1):
				context = _deduplicate_literals(source_prefix + blocking_context)
				plan_name = (
					f"{instruction_id}_transition_{index}_{prefix_index}_{blocking_index}_"
					f"{source_state}_{target_state}"
				)
				body_steps, certificate, plan_warnings = _build_low_level_body(
					low_level_planner=low_level_planner,
					request=LowLevelPlanningRequest(
						plan_name=plan_name,
						instruction_id=instruction_id,
						source_state=source_state,
						target_state=target_state,
						context=context,
						target_context=target_context,
						source_context=source_prefix,
						cumulative_context=cumulative_context,
						raw_label=raw_label,
					),
				)
				warnings.extend(plan_warnings)
				plans.append(
					AgentSpeakPlan(
						plan_name=plan_name,
						trigger=AgentSpeakTrigger(event_type="achievement_goal", symbol="g"),
						context=context or ("true",),
						body=body_steps + (AgentSpeakBodyStep("subgoal", "g"),),
						source_instruction_ids=(instruction_id,),
						binding_certificate=(
							{
								"source_state": source_state,
								"target_state": target_state,
								"raw_label": raw_label,
								"context": list(context),
								"target_context": list(target_context),
								"cumulative_context": list(cumulative_context),
								"is_progress_transition": True,
								**certificate,
							},
						),
					),
				)

	return PlanLibrary(
		domain_name=domain_name,
		plans=tuple(plans),
		initial_beliefs=(),
		metadata={
			"generation_mode": "context_driven_progress",
			"instruction_id": instruction_id,
			"initial_state": initial_state,
			"accepting_states": sorted(accepting_states),
			"transition_count": len(transitions),
			"progress_transition_count": len(progress_transitions),
			"warnings": list(dict.fromkeys(warnings)),
		},
	)


def build_high_level_plan_library(
	*,
	domain_key: str,
	domain_name: str,
	dfa_payloads: Dict[str, Dict[str, Any]],
	low_level_planners: Dict[str, LowLevelPlannerFactory] | None = None,
) -> PlanLibrary:
	"""Merge per-query context-driven high-level plans into one library."""

	plans: List[AgentSpeakPlan] = []
	metadata_payloads: Dict[str, Any] = {}
	for instruction_id, dfa_payload in dfa_payloads.items():
		query_library = build_high_level_plan_library_from_dfa(
			domain_key=domain_key,
			domain_name=domain_name,
			instruction_id=instruction_id,
			dfa_payload=dfa_payload,
			low_level_planner=(low_level_planners or {}).get(instruction_id),
		)
		plans.extend(query_library.plans)
		metadata_payloads[instruction_id] = query_library.metadata

	return PlanLibrary(
		domain_name=domain_name,
		plans=tuple(plans),
		initial_beliefs=(),
		metadata={
			"generation_mode": "context_driven_progress",
			"queries": metadata_payloads,
		},
	)


def _normalise_transition(transition: Dict[str, Any]) -> Dict[str, str] | None:
	source_state = str(transition.get("source_state") or "").strip()
	target_state = str(transition.get("target_state") or "").strip()
	if not source_state or not target_state:
		return None
	raw_label = str(transition.get("raw_label") or "true").strip() or "true"
	return {
		"source_state": source_state,
		"target_state": target_state,
		"raw_label": raw_label,
	}


def _distances_to_accepting(
	transitions: Tuple[Dict[str, str], ...],
	accepting_states: frozenset[str],
) -> Dict[str, int]:
	reverse_edges: dict[str, set[str]] = {}
	for transition in transitions:
		reverse_edges.setdefault(transition["target_state"], set()).add(transition["source_state"])
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
	transition: Dict[str, str],
	distances: Dict[str, int],
	accepting_states: frozenset[str],
) -> bool:
	source_state = transition["source_state"]
	target_state = transition["target_state"]
	if source_state in accepting_states:
		return False
	if source_state not in distances or target_state not in distances:
		return False
	return distances[target_state] < distances[source_state]


def _progress_prefixes_by_state(
	*,
	initial_state: str,
	progress_transitions: Tuple[Dict[str, str], ...],
	domain_key: str,
	max_prefixes_per_state: int = 16,
) -> Dict[str, Tuple[Tuple[str, ...], ...]]:
	prefixes: dict[str, list[Tuple[str, ...]]] = {initial_state: [()]}
	queue = deque([initial_state])
	queued = {initial_state}
	transitions_by_source: dict[str, list[Dict[str, str]]] = {}
	for transition in progress_transitions:
		transitions_by_source.setdefault(transition["source_state"], []).append(transition)
	while queue:
		source_state = queue.popleft()
		queued.discard(source_state)
		for transition in transitions_by_source.get(source_state, ()):
			target_state = transition["target_state"]
			label_context = _context_from_label(transition["raw_label"], domain_key=domain_key)
			for prefix in prefixes.get(source_state, [()]):
				next_prefix = _deduplicate_literals(prefix + label_context)
				state_prefixes = prefixes.setdefault(target_state, [])
				if next_prefix in state_prefixes:
					continue
				if len(state_prefixes) >= max_prefixes_per_state:
					continue
				state_prefixes.append(next_prefix)
				if target_state not in queued:
					queue.append(target_state)
					queued.add(target_state)
	return {state: tuple(state_prefixes) for state, state_prefixes in prefixes.items()}


def _accepting_contexts(
	accepting_states: Iterable[str],
	prefixes_by_state: Dict[str, Tuple[Tuple[str, ...], ...]],
) -> Tuple[Tuple[str, ...], ...]:
	contexts: list[Tuple[str, ...]] = []
	for accepting_state in accepting_states:
		for context in prefixes_by_state.get(accepting_state, ()):
			if context not in contexts:
				contexts.append(context)
	return tuple(contexts)


def _blocking_contexts(
	*,
	source_state: str,
	target_transition: Dict[str, str],
	progress_transitions: Tuple[Dict[str, str], ...],
	all_transitions: Tuple[Dict[str, str], ...],
	distances: Dict[str, int],
	domain_key: str,
) -> Tuple[Tuple[str, ...], ...]:
	progress_from_source = tuple(
		transition
		for transition in progress_transitions
		if transition["source_state"] == source_state
	)
	if len(progress_from_source) > 1:
		return ((),)

	blockers = []
	for transition in all_transitions:
		if transition["source_state"] != source_state:
			continue
		if transition == target_transition:
			continue
		if transition["target_state"] in distances:
			continue
		context = _context_from_label(transition["raw_label"], domain_key=domain_key)
		if context:
			blockers.append(context)
	if blockers:
		return tuple(blockers)
	return (_negate_context(_context_from_label(target_transition["raw_label"], domain_key=domain_key)),)


def _build_low_level_body(
	*,
	low_level_planner: LowLevelPlannerFactory | None,
	request: LowLevelPlanningRequest,
) -> tuple[Tuple[AgentSpeakBodyStep, ...], Dict[str, Any], Tuple[str, ...]]:
	if low_level_planner is None:
		raise RuntimeError(
			f"Low-level planner is required to render primitive actions for {request.plan_name}.",
		)
	response = low_level_planner(request)
	if not response.body_steps:
		raise RuntimeError(
			"Low-level planner did not return primitive actions for "
			f"{request.plan_name}: {response.certificate}",
		)
	return response.body_steps, response.certificate, response.warnings


def _context_from_label(raw_label: str, *, domain_key: str) -> Tuple[str, ...]:
	return tuple(
		literal
		for literal in map_event_expression_to_pddl_context(raw_label, domain_key=domain_key)
		if literal and literal != "true"
	)


def _negate_context(context: Tuple[str, ...]) -> Tuple[str, ...]:
	if not context:
		return ()
	return tuple(_negate_literal(literal) for literal in context)


def _negate_literal(literal: str) -> str:
	text = str(literal or "").strip()
	if text.lower().startswith("not "):
		return text[4:].strip()
	return f"not {text}"


def _deduplicate_literals(literals: Tuple[str, ...]) -> Tuple[str, ...]:
	return tuple(dict.fromkeys(literal for literal in literals if literal and literal != "true"))
