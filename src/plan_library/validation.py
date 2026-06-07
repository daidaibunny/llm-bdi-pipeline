"""
Structural validation for DFA-driven AgentSpeak(L) plan libraries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .models import LibraryValidationRecord, PlanGenerationSummary, PlanLibrary


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
	"""Build a validation record for one DFA-driven plan library."""

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
	"""Validate the generated plan library against the high-level DFA contract."""

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

	has_initial_state = any(
		str(belief or "").strip().startswith("dfa_state(")
		for belief in tuple(plan_library.initial_beliefs or ())
	)
	if not has_initial_state:
		warnings.append("Plan library is missing an initial dfa_state belief.")

	entrypoint_valid = all(
		str(plan.trigger.event_type or "").strip() == "achievement_goal"
		and str(plan.trigger.symbol or "").strip() == "g"
		and not tuple(plan.trigger.arguments or ())
		for plan in plans
	)
	if not entrypoint_valid:
		warnings.append("Every high-level plan must use the `!g` achievement-goal entrypoint.")

	contexts_valid = all(
		any(str(literal or "").strip().startswith("dfa_state(") for literal in plan.context)
		for plan in plans
	)
	if not contexts_valid:
		warnings.append("Every high-level plan context must include the current DFA state.")

	body_valid = True
	for plan in plans:
		body = tuple(plan.body or ())
		if not body:
			continue
		if len(body) < 3:
			body_valid = False
			warnings.append(f"Transition plan '{plan.plan_name}' has an incomplete DFA update body.")
			continue
		if body[-1].kind != "subgoal" or body[-1].symbol != "g":
			body_valid = False
			warnings.append(f"Transition plan '{plan.plan_name}' does not recurse to `!g`.")
		if body[0].kind != "belief_deletion" or body[1].kind != "belief_addition":
			body_valid = False
			warnings.append(f"Transition plan '{plan.plan_name}' does not update DFA state beliefs.")

	return PlanLibraryStructuralValidation(
		checked_layers={
			"unique_plan_names": unique_plan_names,
			"initial_state_belief": has_initial_state,
			"goal_entrypoint": entrypoint_valid,
			"dfa_contexts": contexts_valid,
			"dfa_transition_bodies": body_valid,
		},
		warnings=tuple(dict.fromkeys(warnings)),
	)
