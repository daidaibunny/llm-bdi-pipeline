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
	"""Validate a current atomic library plus temporal-wrapper plan set."""

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
			and certificate.get("wrapper_mode") in {
				"dfa_guard_transition_replay",
				"runtime_monitored_dfa_product",
			}
		):
			return certificate
	return None


def _guard_transition_plan_is_valid(plan, *, certificate: dict) -> bool:
	role = str(certificate.get("wrapper_role") or "").strip()
	entry_proposition = str(certificate.get("query_entry_proposition") or "").strip()
	context = tuple(plan.context or ())
	body = tuple(plan.body or ())
	serialization = certificate.get("serialization_certificate")
	if isinstance(serialization, dict):
		negative_guard_count = int(serialization.get("negative_guard_count") or 0)
		if negative_guard_count:
			negative_guard_literals = tuple(
				str(item).strip()
				for item in tuple(serialization.get("negative_guard_literals") or ())
				if str(item).strip()
			)
			establishment_valid = (
				serialization.get("certificate_kind")
				== "negative_context_only_transition"
				or serialization.get("negative_guard_establishment_checked") is True
			)
			if not (
				serialization.get("negative_guard_preservation_checked") is True
				and serialization.get("negative_guard_preserved") is True
				and len(negative_guard_literals) == negative_guard_count
				and establishment_valid
			):
				return False
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
	if role == "runtime_monitor_accepting_entry":
		return (
			len(context) == 2
			and context[0] == entry_proposition
			and context[1].endswith("_monitor_accepting")
			and not body
		)
	if role == "runtime_monitor_state_dispatch":
		return (
			len(context) == 2
			and context[0] == entry_proposition
			and "_monitor_state_" in context[1]
			and len(body) == 2
			and body[0].kind == "subgoal"
			and body[0].symbol.startswith(f"{plan.trigger.symbol}_trans_")
			and not tuple(body[0].arguments or ())
			and _is_nullary_subgoal(body[1], plan.trigger.symbol)
		)
	if role == "transition_done":
		return not body and "_trans_" in plan.trigger.symbol
	transition_symbol = str(certificate.get("transition_symbol") or "").strip()
	tree_root_symbol = str(certificate.get("tree_root_symbol") or "").strip()
	done_symbol = str(certificate.get("done_symbol") or "").strip()
	if role == "transition_repair_linear_entry":
		ordered_leaf_symbols = tuple(certificate.get("ordered_leaf_symbols") or ())
		expected_symbols = (*ordered_leaf_symbols, done_symbol)
		return (
			plan.trigger.symbol == transition_symbol
			and bool(ordered_leaf_symbols)
			and len(body) == len(expected_symbols)
			and all(
				_is_nullary_subgoal(step, symbol)
				for step, symbol in zip(body, expected_symbols, strict=True)
			)
		)
	if role == "transition_repair_tree_entry":
		return (
			len(body) == 2
			and plan.trigger.symbol == transition_symbol
			and _is_nullary_subgoal(body[0], tree_root_symbol)
			and _is_nullary_subgoal(body[1], done_symbol)
		)
	if role == "transition_repair_tree_internal":
		left_symbol = str(certificate.get("left_child_symbol") or "").strip()
		right_symbol = str(certificate.get("right_child_symbol") or "").strip()
		return (
			len(body) == 2
			and _is_nullary_subgoal(body[0], left_symbol)
			and _is_nullary_subgoal(body[1], right_symbol)
		)
	if role in {
		"transition_repair_tree_leaf_satisfied",
		"transition_repair_linear_leaf_satisfied",
	}:
		literal_atom = str(certificate.get("literal_atom") or "").strip()
		literal_polarity = str(certificate.get("literal_polarity") or "positive")
		expected_context = (
			literal_atom if literal_polarity == "positive" else f"not {literal_atom}"
		)
		return bool(literal_atom) and expected_context in context and not body
	if role in {
		"transition_repair_tree_leaf_achievement",
		"transition_repair_linear_leaf_achievement",
	}:
		literal_atom = str(certificate.get("literal_atom") or "").strip()
		literal_polarity = str(certificate.get("literal_polarity") or "positive")
		expected_context = (
			f"not {literal_atom}" if literal_polarity == "positive" else literal_atom
		)
		achievement_symbol = str(certificate.get("achievement_symbol") or "").strip()
		achievement_arguments = tuple(certificate.get("achievement_arguments") or ())
		achievement_body_valid = (
			bool(body)
			and body[0].kind == "subgoal"
			and body[0].symbol == achievement_symbol
			and tuple(body[0].arguments or ()) == achievement_arguments
		)
		monitor_checkpoint_action = str(
			certificate.get("monitor_checkpoint_action") or ""
		).strip()
		if monitor_checkpoint_action:
			achievement_body_valid = (
				achievement_body_valid
				and len(body) == 2
				and body[1].kind == "action"
				and body[1].symbol == monitor_checkpoint_action
				and not tuple(body[1].arguments or ())
			)
		else:
			achievement_body_valid = achievement_body_valid and len(body) == 1
		return (
			bool(literal_atom)
			and expected_context in context
			and achievement_body_valid
		)
	if role in {
		"transition_repair_tree_done",
		"transition_repair_linear_done",
	}:
		return plan.trigger.symbol == done_symbol and not body
	if role in {
		"transition_repair_tree_replay",
		"transition_repair_linear_replay",
	}:
		return (
			plan.trigger.symbol == done_symbol
			and len(body) == 1
			and _is_nullary_subgoal(body[0], transition_symbol)
		)
	return False


def _is_nullary_subgoal(step, symbol: str) -> bool:
	return bool(symbol) and (
		step.kind == "subgoal"
		and step.symbol == symbol
		and not tuple(step.arguments or ())
	)
