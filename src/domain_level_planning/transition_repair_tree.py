"""Compile one certified conjunctive DFA transition into a balanced ASL repair tree."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger


_WRAPPER_MODE = "dfa_guard_transition_replay"
_CONTROLLER_STRATEGY = "balanced_transition_repair_tree"


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
	controller_strategy: str = _CONTROLLER_STRATEGY


def compile_transition_repair_tree(
	*,
	transition_symbol: str,
	shared_context: Sequence[str],
	positive_literals: Sequence[TransitionRepairLiteral],
	final_guard_context: Sequence[str],
	certificate: Mapping[str, object],
) -> TransitionRepairTreeCompilation:
	"""Compile ordered guard literals into a balanced, replaying transition controller.

	The caller supplies a certified literal order. This function only constructs a
	balanced binary control-flow tree, so it is invariant to predicate and domain names.
	"""

	literals = tuple(positive_literals)
	if not literals:
		raise ValueError(
			"balanced_transition_repair_tree_requires_positive_literal: "
			"negative-only guards compile directly without a repair tree."
		)
	transition = str(transition_symbol).strip()
	if not transition:
		raise ValueError("transition_symbol must not be empty")
	shared = tuple(dict.fromkeys(str(item).strip() for item in shared_context if str(item).strip()))
	final_context = tuple(
		dict.fromkeys(str(item).strip() for item in final_guard_context if str(item).strip())
	)
	root_symbol = _range_symbol(transition, 1, len(literals))
	done_symbol = f"{transition}_done"
	base_certificate = {
		**dict(certificate),
		"artifact_family": "temporal_goal_dfa_append",
		"wrapper_mode": _WRAPPER_MODE,
		"controller_strategy": _CONTROLLER_STRATEGY,
		"transition_symbol": transition,
		"tree_root_symbol": root_symbol,
		"done_symbol": done_symbol,
		"positive_literal_count": sum(
			literal.polarity == "positive" for literal in literals
		),
		"negative_literal_count": sum(
			literal.polarity == "negative" for literal in literals
		),
		"final_guard_recheck": True,
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
	)
	plans.extend(
		(
			AgentSpeakPlan(
				plan_name=f"{done_symbol}_success",
				trigger=AgentSpeakTrigger("achievement_goal", done_symbol, ()),
				context=final_context,
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
	)
	right_height = _append_tree_plans(
		plans=plans,
		transition_symbol=transition_symbol,
		shared_context=shared_context,
		literals=literals,
		start=midpoint + 1,
		end=end,
		base_certificate=base_certificate,
	)
	return 1 + max(left_height, right_height)


def _range_symbol(transition_symbol: str, start: int, end: int) -> str:
	return f"{transition_symbol}_repair_{start}_{end}"
