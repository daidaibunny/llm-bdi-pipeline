"""
Adapt DFA transition guards into domain-level achievement-goal requests.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep
from temporal_specification.pddl_mapping import map_event_expression_to_pddl_context
from utils.pddl_parser import PDDLParser


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
	domain_file: str | Path | None = None,
	declared_predicates: Sequence[object] | Mapping[str, int | None] = (),
) -> DFAAchievementRequest:
	"""Adapt one DFA guarded transition into achievement-goal requests."""

	request = adapt_dfa_guard_to_achievement_request(
		str(transition.get("raw_label") or "true"),
		domain_key=domain_key,
		domain_file=domain_file,
		declared_predicates=declared_predicates,
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
	domain_file: str | Path | None = None,
	declared_predicates: Sequence[object] | Mapping[str, int | None] = (),
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
	_validate_guard_atoms(
		parsed_atoms,
		declared_predicates=_predicate_arities(
			domain_file=domain_file,
			declared_predicates=declared_predicates,
		),
	)
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


def _validate_guard_atoms(
	parsed_atoms: Sequence[tuple[str, tuple[str, ...]]],
	*,
	declared_predicates: Mapping[str, int | None],
) -> None:
	if not declared_predicates:
		return
	for predicate, arguments in parsed_atoms:
		if predicate not in declared_predicates:
			raise ValueError(
				f"DFA guard references undeclared PDDL predicate {predicate!r}.",
			)
		declared_arity = declared_predicates[predicate]
		if declared_arity is not None and declared_arity != len(arguments):
			raise ValueError(
				(
					"DFA guard references PDDL predicate "
					f"{predicate}/{declared_arity} with wrong arity {len(arguments)}."
				),
			)


def _predicate_arities(
	*,
	domain_file: str | Path | None,
	declared_predicates: Sequence[object] | Mapping[str, int | None],
) -> Mapping[str, int | None]:
	arities: dict[str, int | None] = {}
	if domain_file is not None:
		arities.update(_declared_arities(PDDLParser.parse_domain(domain_file).predicates))
	arities.update(_declared_arities(declared_predicates))
	return arities


def _declared_arities(symbols: Sequence[object] | Mapping[str, int | None]) -> dict[str, int | None]:
	if isinstance(symbols, Mapping):
		return {str(name): arity for name, arity in symbols.items()}
	arities: dict[str, int | None] = {}
	for symbol in tuple(symbols or ()):
		name = getattr(symbol, "name", None)
		if name is not None:
			parameters = getattr(symbol, "parameters", None)
			arities[str(name)] = None if parameters is None else len(tuple(parameters))
			continue
		arities[str(symbol)] = None
	return arities


def _call(predicate: str, arguments: Sequence[str]) -> str:
	args = tuple(arguments)
	return predicate if not args else f"{predicate}({', '.join(args)})"


def _optional_text(value: object) -> str | None:
	text = str(value or "").strip()
	return text or None
