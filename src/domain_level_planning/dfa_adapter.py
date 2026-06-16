"""
Adapt DFA transition guards into domain-level achievement-goal requests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep
from temporal_specification.pddl_mapping import map_event_expression_to_pddl_context


@dataclass(frozen=True)
class DFAAchievementRequest:
	"""Achievement-goal request issued by a DFA transition guard."""

	raw_guard: str
	state_literals: tuple[str, ...]
	goal_facts: tuple[str, ...]
	body_steps: tuple[AgentSpeakBodyStep, ...]
	source_state: str | None = None
	target_state: str | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"raw_guard": self.raw_guard,
			"source_state": self.source_state,
			"target_state": self.target_state,
			"state_literals": list(self.state_literals),
			"goal_facts": list(self.goal_facts),
			"achievement_subgoals": [
				step.to_dict() for step in self.body_steps
			],
		}


def adapt_dfa_guarded_transition_to_achievement_request(
	transition: Mapping[str, object],
	*,
	domain_key: str,
) -> DFAAchievementRequest:
	"""Adapt one DFA guarded transition into achievement-goal requests."""

	request = adapt_dfa_guard_to_achievement_request(
		str(transition.get("raw_label") or "true"),
		domain_key=domain_key,
	)
	return DFAAchievementRequest(
		raw_guard=request.raw_guard,
		state_literals=request.state_literals,
		goal_facts=request.goal_facts,
		body_steps=request.body_steps,
		source_state=_optional_text(transition.get("source_state")),
		target_state=_optional_text(transition.get("target_state")),
	)


def adapt_dfa_guard_to_achievement_request(
	raw_guard: str,
	*,
	domain_key: str,
) -> DFAAchievementRequest:
	"""Translate a positive conjunctive DFA guard into goal facts and subgoals.

	Current achievement-goal libraries support positive conjunctive state
	requests only. Negative, false, or disjunctive guards are rejected rather than
	silently compiled into mutable goal descriptors or query-specific plans.
	"""

	state_literals = tuple(
		literal
		for literal in map_event_expression_to_pddl_context(
			raw_guard,
			domain_key=domain_key,
		)
		if literal and literal != "true"
	)
	if any(_is_unsupported_literal(literal) for literal in state_literals):
		raise ValueError(
			"DFA guard adapter currently supports positive conjunctive "
			f"achievement requests only; received {raw_guard!r}.",
		)
	parsed_atoms = tuple(_parse_atom(literal) for literal in state_literals)
	return DFAAchievementRequest(
		raw_guard=str(raw_guard or "").strip() or "true",
		state_literals=state_literals,
		goal_facts=tuple(
			_call(f"goal_{predicate}", arguments)
			for predicate, arguments in parsed_atoms
		),
		body_steps=tuple(
			AgentSpeakBodyStep("subgoal", predicate, arguments)
			for predicate, arguments in parsed_atoms
		),
	)


def _is_unsupported_literal(literal: str) -> bool:
	text = str(literal or "").strip()
	return (
		not text
		or text.lower() == "false"
		or text.lower().startswith("not ")
		or "|" in text
	)


def _parse_atom(atom: str) -> tuple[str, tuple[str, ...]]:
	text = str(atom or "").strip()
	if "(" not in text:
		return text, ()
	if not text.endswith(")"):
		raise ValueError(f"Invalid DFA guard atom for achievement request: {atom!r}.")
	predicate, raw_arguments = text.split("(", 1)
	return (
		predicate.strip(),
		tuple(
			argument.strip()
			for argument in raw_arguments[:-1].split(",")
			if argument.strip()
		),
	)


def _call(predicate: str, arguments: Sequence[str]) -> str:
	args = tuple(arguments)
	return predicate if not args else f"{predicate}({', '.join(args)})"


def _optional_text(value: object) -> str | None:
	text = str(value or "").strip()
	return text or None
