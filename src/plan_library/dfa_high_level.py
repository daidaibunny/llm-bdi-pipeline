"""
Generate high-level AgentSpeak(L) plans directly from DFA transitions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from temporal_specification.pddl_mapping import map_event_expression_to_pddl_context

from .models import AgentSpeakBodyStep, AgentSpeakPlan, AgentSpeakTrigger, PlanLibrary


def build_high_level_plan_library_from_dfa(
	*,
	domain_key: str,
	domain_name: str,
	instruction_id: str,
	dfa_payload: Dict[str, Any],
) -> PlanLibrary:
	"""Build a DFA-driven high-level plan library with `!g` as the only entrypoint."""

	initial_state = str(dfa_payload.get("initial_state") or "").strip()
	if not initial_state:
		raise ValueError("DFA payload must include an initial_state.")

	accepting_states = tuple(
		str(state).strip()
		for state in (dfa_payload.get("accepting_states") or ())
		if str(state).strip()
	)
	plans: List[AgentSpeakPlan] = []
	for accepting_state in accepting_states:
		plans.append(
			AgentSpeakPlan(
				plan_name=f"{instruction_id}_accept_{accepting_state}",
				trigger=AgentSpeakTrigger(event_type="achievement_goal", symbol="g"),
				context=(f"dfa_state({accepting_state})",),
				body=(),
				source_instruction_ids=(instruction_id,),
			),
		)

	for index, transition in enumerate(dfa_payload.get("guarded_transitions") or (), start=1):
		if not isinstance(transition, dict):
			continue
		source_state = str(transition.get("source_state") or "").strip()
		target_state = str(transition.get("target_state") or "").strip()
		if not source_state or not target_state:
			continue
		if source_state in accepting_states:
			continue
		raw_label = str(transition.get("raw_label") or "true").strip() or "true"
		guard_context = map_event_expression_to_pddl_context(raw_label, domain_key=domain_key)
		context = (f"dfa_state({source_state})",) + tuple(
			literal for literal in guard_context if literal != "true"
		)
		plans.append(
			AgentSpeakPlan(
				plan_name=f"{instruction_id}_transition_{index}_{source_state}_{target_state}",
				trigger=AgentSpeakTrigger(event_type="achievement_goal", symbol="g"),
				context=context,
				body=(
					AgentSpeakBodyStep("belief_deletion", "dfa_state", (source_state,)),
					AgentSpeakBodyStep("belief_addition", "dfa_state", (target_state,)),
					AgentSpeakBodyStep("subgoal", "g"),
				),
				source_instruction_ids=(instruction_id,),
				binding_certificate=(
					{
						"source_state": source_state,
						"target_state": target_state,
						"raw_label": raw_label,
					},
				),
			),
		)

	return PlanLibrary(
		domain_name=domain_name,
		plans=tuple(plans),
		initial_beliefs=(f"dfa_state({initial_state})",),
		metadata={
			"generation_mode": "dfa_high_level",
			"instruction_id": instruction_id,
			"initial_state": initial_state,
			"accepting_states": list(accepting_states),
			"transition_count": len(
				tuple(item for item in (dfa_payload.get("guarded_transitions") or ()) if isinstance(item, dict)),
			),
		},
	)


def build_high_level_plan_library(
	*,
	domain_key: str,
	domain_name: str,
	dfa_payloads: Dict[str, Dict[str, Any]],
) -> PlanLibrary:
	"""Merge per-query DFA high-level plans into one AgentSpeak(L) library."""

	plans: List[AgentSpeakPlan] = []
	initial_beliefs: List[str] = []
	metadata_payloads: Dict[str, Any] = {}
	for instruction_id, dfa_payload in dfa_payloads.items():
		query_library = build_high_level_plan_library_from_dfa(
			domain_key=domain_key,
			domain_name=domain_name,
			instruction_id=instruction_id,
			dfa_payload=dfa_payload,
		)
		plans.extend(query_library.plans)
		initial_beliefs.extend(query_library.initial_beliefs)
		metadata_payloads[instruction_id] = query_library.metadata

	return PlanLibrary(
		domain_name=domain_name,
		plans=tuple(plans),
		initial_beliefs=tuple(dict.fromkeys(initial_beliefs)),
		metadata={
			"generation_mode": "dfa_high_level",
			"queries": metadata_payloads,
		},
	)
