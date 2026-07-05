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
		if _is_query_wrapper_symbol(plan.trigger.symbol) and body:
			last_step = body[-1]
			is_recursive_progress_plan = (
				last_step.kind == "subgoal"
				and last_step.symbol == plan.trigger.symbol
				and not tuple(last_step.arguments or ())
			)
			is_linear_single_body_plan = _is_linear_single_body_plan(plan)
			if not is_recursive_progress_plan and not is_linear_single_body_plan:
				body_valid = False
				warnings.append(
					(
						f"Temporal wrapper plan '{plan.plan_name}' does not recurse "
						f"to `!{plan.trigger.symbol}` or compile a certified "
						"linear single-body sequence."
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


def _is_linear_single_body_plan(plan) -> bool:
	if not tuple(plan.body or ()):
		return False
	if not all(step.kind == "subgoal" for step in tuple(plan.body or ())):
		return False
	for certificate in tuple(plan.binding_certificate or ()):
		if (
			isinstance(certificate, dict)
			and certificate.get("artifact_family") == "temporal_goal_dfa_append"
			and certificate.get("wrapper_mode") == "linear_single_body"
		):
			return True
	return False
