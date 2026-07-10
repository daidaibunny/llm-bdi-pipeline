"""
Structural validation for current domain-level AgentSpeak(L) libraries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .models import LibraryValidationRecord, PlanGenerationSummary, PlanLibrary


_DISALLOWED_CONTROLLER_STATE_PREFIXES = ("dfa_state(", "tg_state(")
_DISALLOWED_CONTROLLER_STATE_STEPS = {"dfa_state", "tg_state"}


@dataclass(frozen=True)
class PlanLibraryStructuralValidation:
	"""Structured validation outcome for one generated AgentSpeak(L) plan library."""

	checked_layers: Dict[str, bool]
	warnings: Tuple[str, ...] = ()


def build_library_validation_record(
	*,
	domain_name: str,
	plan_library: PlanLibrary,
	generation_summary: PlanGenerationSummary,
) -> LibraryValidationRecord:
	"""Build a validation record for one generated plan library."""

	plan_validation = validate_plan_library_structure(plan_library=plan_library)
	checked_layers = dict(plan_validation.checked_layers)
	failure_reason = None
	if not all(checked_layers.values()):
		for layer_name, passed in checked_layers.items():
			if not passed:
				failure_reason = f"{layer_name} failed"
				break
	elif generation_summary.plans_generated <= 0:
		failure_reason = "No AgentSpeak(L) plans were generated from the DFA transitions."

	return LibraryValidationRecord(
		library_id=domain_name,
		passed=all(checked_layers.values()) and generation_summary.plans_generated > 0,
		plan_count=len(tuple(plan_library.plans or ())),
		checked_layers=checked_layers,
		warnings=tuple(dict.fromkeys(plan_validation.warnings)),
		failure_reason=failure_reason,
	)


def validate_plan_library_structure(
	*,
	plan_library: PlanLibrary,
) -> PlanLibraryStructuralValidation:
	"""Validate a current atomic-library plus temporal-wrapper artifact."""

	warnings: List[str] = []
	plans = tuple(plan_library.plans or ())
	plan_names = [
		str(plan.plan_name or "").strip()
		for plan in plans
		if str(plan.plan_name or "").strip()
	]
	unique_plan_names = len(plan_names) == len(set(plan_names))
	if not unique_plan_names:
		warnings.append("Generated plan names are not unique.")

	has_no_controller_state_beliefs = not any(
		str(belief or "").strip().startswith(_DISALLOWED_CONTROLLER_STATE_PREFIXES)
		for belief in tuple(plan_library.initial_beliefs or ())
	)
	if not has_no_controller_state_beliefs:
		warnings.append("Current ASL libraries must not expose dfa_state or tg_state beliefs.")

	plan_heads_valid = all(
		str(plan.trigger.event_type or "").strip() == "achievement_goal"
		and _is_current_plan_head(plan)
		for plan in plans
	)
	if not plan_heads_valid:
		warnings.append(
			"Plans must use PDDL predicate achievement heads or query-specific `!g_*` wrappers.",
		)

	contexts_valid = all(
		not any(
			str(literal or "").strip().startswith(_DISALLOWED_CONTROLLER_STATE_PREFIXES)
			for literal in plan.context
		)
		for plan in plans
	)
	if not contexts_valid:
		warnings.append("Plan contexts must not depend on dfa_state or tg_state controller beliefs.")

	body_valid = True
	for plan in plans:
		body = tuple(plan.body or ())
		if any(step.symbol in _DISALLOWED_CONTROLLER_STATE_STEPS for step in body):
			body_valid = False
			warnings.append(
				f"Transition plan '{plan.plan_name}' still manipulates controller state beliefs."
			)
		if _is_query_wrapper_symbol(plan.trigger.symbol):
			certificate = _guard_transition_certificate(plan)
			if certificate is None or not _guard_transition_plan_is_valid(
				plan,
				certificate=certificate,
			):
				body_valid = False
				warnings.append(
					(
						f"Temporal wrapper plan '{plan.plan_name}' is not a certified "
						"DFA guard-transition entry, completion, or repair plan."
					),
				)

	return PlanLibraryStructuralValidation(
		checked_layers={
			"unique_plan_names": unique_plan_names,
			"no_controller_state_beliefs": has_no_controller_state_beliefs,
			"plan_heads": plan_heads_valid,
			"transition_contexts": contexts_valid,
			"context_driven_bodies": body_valid,
		},
		warnings=tuple(dict.fromkeys(warnings)),
	)


def _is_current_plan_head(plan) -> bool:
	symbol = str(plan.trigger.symbol or "").strip()
	if _is_query_wrapper_symbol(symbol):
		return not tuple(plan.trigger.arguments or ())
	return bool(symbol)


def _is_query_wrapper_symbol(symbol: str) -> bool:
	text = str(symbol or "").strip()
	return text.startswith("g_") and len(text) > 2


def _guard_transition_certificate(plan) -> dict | None:
	for certificate in tuple(plan.binding_certificate or ()):
		if (
			isinstance(certificate, dict)
			and certificate.get("artifact_family") == "temporal_goal_dfa_append"
			and certificate.get("wrapper_mode") == "dfa_guard_transition_replay"
		):
			return certificate
	return None


def _guard_transition_plan_is_valid(plan, *, certificate: dict) -> bool:
	role = str(certificate.get("wrapper_role") or "").strip()
	entry_proposition = str(certificate.get("query_entry_proposition") or "").strip()
	context = tuple(plan.context or ())
	body = tuple(plan.body or ())
	if not entry_proposition or entry_proposition not in context:
		return False
	if role == "transition_sequence_entry":
		return (
			context == (entry_proposition,)
			and bool(body)
			and all(
				step.kind == "subgoal"
				and step.symbol.startswith(f"{plan.trigger.symbol}_trans_")
				and not tuple(step.arguments or ())
				for step in body
			)
		)
	if role == "transition_done":
		return not body and "_trans_" in plan.trigger.symbol
	if role == "transition_positive_literal_repair":
		return (
			len(body) == 2
			and body[0].kind == "subgoal"
			and body[0].symbol != plan.trigger.symbol
			and body[1].kind == "subgoal"
			and body[1].symbol == plan.trigger.symbol
			and not tuple(body[1].arguments or ())
		)
	return False
