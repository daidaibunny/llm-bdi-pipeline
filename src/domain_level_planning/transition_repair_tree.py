"""Compile one certified DFA transition into a balanced binary transition-repair tree.

Paper correspondence: Section 5 and Proposition 4 define this tree after the
literal order and preserving branch portfolio have already been certified. The
tree changes indexing and trigger fan-out only; it introduces no new planning or
temporal semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger


_DEFAULT_WRAPPER_MODE = "dfa_guard_transition_replay"
_DEFAULT_CONTROLLER_STRATEGY = "balanced_transition_repair_tree"
_FLAT_CONTROLLER_STRATEGY = "monitored_certified_flat_replay"


@dataclass(frozen=True)
class TransitionRepairLiteral:
	"""One ordered signed guard literal and its certified repair call."""

	atom: str
	achievement_symbol: str | None
	achievement_arguments: tuple[str, ...] = ()
	polarity: str = "positive"


@dataclass(frozen=True)
class TransitionRepairTreeCompilation:
	"""Structured plans and complexity certificate for one transition controller."""

	plans: tuple[AgentSpeakPlan, ...]
	transition_symbol: str
	root_symbol: str
	done_symbol: str
	literal_count: int
	tree_height: int
	controller_strategy: str = _DEFAULT_CONTROLLER_STRATEGY


def compile_transition_repair_tree(
	*,
	transition_symbol: str,
	shared_context: Sequence[str],
	positive_literals: Sequence[TransitionRepairLiteral],
	completion_context: Sequence[str],
	certificate: Mapping[str, object],
	wrapper_mode: str = _DEFAULT_WRAPPER_MODE,
	controller_strategy: str = _DEFAULT_CONTROLLER_STRATEGY,
	monitor_checkpoint_action: str | None = None,
) -> TransitionRepairTreeCompilation:
	"""Compile ordered guard literals into a balanced, replaying transition controller.

	The caller supplies a certified literal order. This function only constructs a
	balanced binary control-flow tree, so it is invariant to predicate and domain names.
	"""

	literals = tuple(positive_literals)
	if not literals:
		raise ValueError(
			"balanced_transition_repair_tree_requires_positive_literal: "
			"negative-only guards compile directly without a transition-repair tree."
		)
	transition = str(transition_symbol).strip()
	if not transition:
		raise ValueError("transition_symbol must not be empty")
	shared = tuple(dict.fromkeys(str(item).strip() for item in shared_context if str(item).strip()))
	completion = tuple(
		dict.fromkeys(str(item).strip() for item in completion_context if str(item).strip())
	)
	root_symbol = _range_symbol(transition, 1, len(literals))
	done_symbol = f"{transition}_done"
	base_certificate = {
		**dict(certificate),
		"artifact_family": "temporal_goal_dfa_append",
		"wrapper_mode": str(wrapper_mode),
		"controller_strategy": str(controller_strategy),
		"transition_symbol": transition,
		"tree_root_symbol": root_symbol,
		"done_symbol": done_symbol,
		"positive_literal_count": sum(
			literal.polarity == "positive" for literal in literals
		),
		"negative_literal_count": sum(
			literal.polarity == "negative" for literal in literals
		),
		"completion_context_checked": True,
		"monitor_checkpoint_action": monitor_checkpoint_action,
	}
	plans: list[AgentSpeakPlan] = [
		AgentSpeakPlan(
			plan_name=f"{transition}_repair_tree",
			trigger=AgentSpeakTrigger("achievement_goal", transition, ()),
			context=shared,
			body=(
				AgentSpeakBodyStep("subgoal", root_symbol, ()),
				AgentSpeakBodyStep("subgoal", done_symbol, ()),
			),
			binding_certificate=(
				{
					**base_certificate,
					"wrapper_role": "transition_repair_tree_entry",
				},
			),
		),
	]
	tree_height = _append_tree_plans(
		plans=plans,
		transition_symbol=transition,
		shared_context=shared,
		literals=literals,
		start=1,
		end=len(literals),
		base_certificate=base_certificate,
		monitor_checkpoint_action=monitor_checkpoint_action,
	)
	plans.extend(
		(
			AgentSpeakPlan(
				plan_name=f"{done_symbol}_success",
				trigger=AgentSpeakTrigger("achievement_goal", done_symbol, ()),
				context=completion,
				body=(),
				binding_certificate=(
					{
						**base_certificate,
						"wrapper_role": "transition_repair_tree_done",
					},
				),
			),
			AgentSpeakPlan(
				plan_name=f"{done_symbol}_replay",
				trigger=AgentSpeakTrigger("achievement_goal", done_symbol, ()),
				context=shared,
				body=(AgentSpeakBodyStep("subgoal", transition, ()),),
				binding_certificate=(
					{
						**base_certificate,
						"wrapper_role": "transition_repair_tree_replay",
					},
				),
			),
		)
	)
	return TransitionRepairTreeCompilation(
		plans=tuple(plans),
		transition_symbol=transition,
		root_symbol=root_symbol,
		done_symbol=done_symbol,
		literal_count=len(literals),
		tree_height=tree_height,
		controller_strategy=str(controller_strategy),
	)


def compile_flat_transition_repair_controller(
	*,
	transition_symbol: str,
	shared_context: Sequence[str],
	repair_literals: Sequence[TransitionRepairLiteral],
	completion_context: Sequence[str],
	certificate: Mapping[str, object],
	wrapper_mode: str = _DEFAULT_WRAPPER_MODE,
	controller_strategy: str = _FLAT_CONTROLLER_STRATEGY,
	monitor_checkpoint_action: str | None = None,
) -> TransitionRepairTreeCompilation:
	"""Compile one ordered guard as flat same-trigger repair siblings.

	This is an evaluation controller, not the historical sequence-only wrapper.
	Every applicable sibling repairs exactly one unmet literal and then rechecks the
	same monitored DFA transition.
	"""

	literals = tuple(repair_literals)
	if not literals:
		raise ValueError(
		"flat_transition_repair_controller_requires_literal: negative-only "
		"observation guards compile directly without a repair controller.",
		)
	transition = str(transition_symbol).strip()
	if not transition:
		raise ValueError("transition_symbol must not be empty")
	shared = tuple(
		dict.fromkeys(str(item).strip() for item in shared_context if str(item).strip())
	)
	completion = tuple(
		dict.fromkeys(str(item).strip() for item in completion_context if str(item).strip())
	)
	base_certificate = {
		**dict(certificate),
		"artifact_family": "temporal_goal_dfa_append",
		"wrapper_mode": str(wrapper_mode),
		"controller_strategy": str(controller_strategy),
		"transition_symbol": transition,
		"positive_literal_count": sum(
			literal.polarity == "positive" for literal in literals
		),
		"negative_literal_count": sum(
			literal.polarity == "negative" for literal in literals
		),
		"completion_context_checked": True,
		"monitor_checkpoint_action": monitor_checkpoint_action,
	}
	plans: list[AgentSpeakPlan] = [
		AgentSpeakPlan(
			plan_name=f"{transition}_done",
			trigger=AgentSpeakTrigger("achievement_goal", transition, ()),
			context=completion,
			body=(),
			binding_certificate=(
				{**base_certificate, "wrapper_role": "transition_flat_done"},
			),
		),
	]
	for literal_index, literal in enumerate(literals, start=1):
		if literal.polarity not in {"positive", "negative"}:
			raise ValueError(
				"transition_repair_literal_polarity_invalid: expected positive or negative."
			)
		if not literal.achievement_symbol:
			continue
		unmet_context = (
			f"not {literal.atom}" if literal.polarity == "positive" else literal.atom
		)
		body = [
			AgentSpeakBodyStep(
				"subgoal",
				literal.achievement_symbol,
				literal.achievement_arguments,
			),
		]
		if monitor_checkpoint_action:
			body.append(AgentSpeakBodyStep("action", monitor_checkpoint_action, ()))
		body.append(AgentSpeakBodyStep("subgoal", transition, ()))
		plans.append(
			AgentSpeakPlan(
				plan_name=f"{transition}_repair_{literal_index}",
				trigger=AgentSpeakTrigger("achievement_goal", transition, ()),
				context=(*shared, unmet_context),
				body=tuple(body),
				binding_certificate=(
					{
						**base_certificate,
						"wrapper_role": "transition_flat_repair",
						"literal_index": literal_index,
						"literal_atom": literal.atom,
						"literal_polarity": literal.polarity,
						"achievement_symbol": literal.achievement_symbol,
						"achievement_arguments": list(literal.achievement_arguments),
					},
				),
			),
		)
	return TransitionRepairTreeCompilation(
		plans=tuple(plans),
		transition_symbol=transition,
		root_symbol=transition,
		done_symbol=transition,
		literal_count=len(literals),
		tree_height=1,
		controller_strategy=str(controller_strategy),
	)


def _append_tree_plans(
	*,
	plans: list[AgentSpeakPlan],
	transition_symbol: str,
	shared_context: tuple[str, ...],
	literals: tuple[TransitionRepairLiteral, ...],
	start: int,
	end: int,
	base_certificate: Mapping[str, object],
	monitor_checkpoint_action: str | None,
) -> int:
	symbol = _range_symbol(transition_symbol, start, end)
	if start == end:
		literal = literals[start - 1]
		if literal.polarity not in {"positive", "negative"}:
			raise ValueError(
				"transition_repair_literal_polarity_invalid: expected positive or negative."
			)
		satisfied_context = (
			literal.atom if literal.polarity == "positive" else f"not {literal.atom}"
		)
		unmet_context = (
			f"not {literal.atom}" if literal.polarity == "positive" else literal.atom
		)
		leaf_certificate = {
			**dict(base_certificate),
			"literal_index": start,
			"literal_atom": literal.atom,
			"achievement_symbol": literal.achievement_symbol,
			"achievement_arguments": list(literal.achievement_arguments),
			"literal_polarity": literal.polarity,
			"tree_range": [start, end],
		}
		plans.append(
			AgentSpeakPlan(
				plan_name=f"{symbol}_satisfied",
				trigger=AgentSpeakTrigger("achievement_goal", symbol, ()),
				context=(*shared_context, satisfied_context),
				body=(),
				binding_certificate=(
					{
						**leaf_certificate,
						"wrapper_role": "transition_repair_tree_leaf_satisfied",
					},
				),
			),
		)
		if literal.achievement_symbol:
			plans.append(
				AgentSpeakPlan(
					plan_name=f"{symbol}_achieve",
					trigger=AgentSpeakTrigger("achievement_goal", symbol, ()),
					context=(*shared_context, unmet_context),
					body=(
						AgentSpeakBodyStep(
							"subgoal",
							literal.achievement_symbol,
							literal.achievement_arguments,
						),
						*(
							(AgentSpeakBodyStep("action", monitor_checkpoint_action, ()),)
							if monitor_checkpoint_action
							else ()
						),
					),
					binding_certificate=(
						{
							**leaf_certificate,
							"wrapper_role": "transition_repair_tree_leaf_achievement",
						},
					),
				),
			)
		return 1
	midpoint = (start + end) // 2
	left_symbol = _range_symbol(transition_symbol, start, midpoint)
	right_symbol = _range_symbol(transition_symbol, midpoint + 1, end)
	plans.append(
		AgentSpeakPlan(
			plan_name=f"{symbol}_dispatch",
			trigger=AgentSpeakTrigger("achievement_goal", symbol, ()),
			context=shared_context,
			body=(
				AgentSpeakBodyStep("subgoal", left_symbol, ()),
				AgentSpeakBodyStep("subgoal", right_symbol, ()),
			),
			binding_certificate=(
				{
					**dict(base_certificate),
					"wrapper_role": "transition_repair_tree_internal",
					"tree_range": [start, end],
					"left_child_symbol": left_symbol,
					"right_child_symbol": right_symbol,
				},
			),
		),
	)
	left_height = _append_tree_plans(
		plans=plans,
		transition_symbol=transition_symbol,
		shared_context=shared_context,
		literals=literals,
		start=start,
		end=midpoint,
		base_certificate=base_certificate,
		monitor_checkpoint_action=monitor_checkpoint_action,
	)
	right_height = _append_tree_plans(
		plans=plans,
		transition_symbol=transition_symbol,
		shared_context=shared_context,
		literals=literals,
		start=midpoint + 1,
		end=end,
		base_certificate=base_certificate,
		monitor_checkpoint_action=monitor_checkpoint_action,
	)
	return 1 + max(left_height, right_height)


def _range_symbol(transition_symbol: str, start: int, end: int) -> str:
	return f"{transition_symbol}_repair_{start}_{end}"
