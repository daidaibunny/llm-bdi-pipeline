"""
Schema-level diagnostics for mutually inconsistent achievement goals.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Mapping, Sequence

from utils.pddl_parser import PDDLDomain

from .pddl_expression import LiftedLiteral, parse_pddl_literals


@dataclass(frozen=True)
class GoalMutexDiagnostic:
	"""One pair of goal atoms supported by symmetric add/delete schema evidence."""

	first_goal: str
	second_goal: str
	first_producer_action: str
	second_producer_action: str
	first_add_deletes_second: str
	second_add_deletes_first: str

	def to_dict(self) -> dict[str, str]:
		"""Return a stable report representation."""

		return {
			"first_goal": self.first_goal,
			"second_goal": self.second_goal,
			"first_producer_action": self.first_producer_action,
			"second_producer_action": self.second_producer_action,
			"first_add_deletes_second": self.first_add_deletes_second,
			"second_add_deletes_first": self.second_add_deletes_first,
		}


@dataclass(frozen=True)
class _ProducerDeletePattern:
	action_name: str
	add_effect: LiftedLiteral
	delete_effect: LiftedLiteral


def schema_goal_mutexes(
	*,
	domain: PDDLDomain,
	goal_atoms: Sequence[str],
) -> tuple[GoalMutexDiagnostic, ...]:
	"""Return goal pairs with symmetric add/delete evidence in the PDDL schemas.

	This is a conservative diagnostic for the current positive-conjunctive
	achievement-goal fragment. It does not try to prove arbitrary PDDL
	unsatisfiability; it catches common STRIPS state-invariant violations where
	achieving one goal necessarily deletes the other and the reverse transition is
	represented by the domain schemas as well.
	"""

	patterns = _producer_delete_patterns(domain)
	diagnostics: list[GoalMutexDiagnostic] = []
	positive_goals = tuple(
		dict.fromkeys(str(atom).strip() for atom in goal_atoms if atom),
	)
	for first, second in combinations(positive_goals, 2):
		first_to_second = _matching_pattern(
			patterns=patterns,
			added_goal=first,
			deleted_goal=second,
		)
		if first_to_second is None:
			continue
		second_to_first = _matching_pattern(
			patterns=patterns,
			added_goal=second,
			deleted_goal=first,
		)
		if second_to_first is None:
			continue
		diagnostics.append(
			GoalMutexDiagnostic(
				first_goal=first,
				second_goal=second,
				first_producer_action=first_to_second.action_name,
				second_producer_action=second_to_first.action_name,
				first_add_deletes_second=_literal_signature(
					first_to_second.delete_effect,
				),
				second_add_deletes_first=_literal_signature(
					second_to_first.delete_effect,
				),
			),
		)
	return tuple(diagnostics)


def _producer_delete_patterns(
	domain: PDDLDomain,
) -> tuple[_ProducerDeletePattern, ...]:
	patterns: list[_ProducerDeletePattern] = []
	for action in tuple(domain.actions or ()):
		action_name = str(action.name or "")
		if not action_name:
			continue
		effects = parse_pddl_literals(str(action.effects or ""))
		add_effects = tuple(effect for effect in effects if effect.is_positive)
		delete_effects = tuple(effect for effect in effects if not effect.is_positive)
		for add_effect in add_effects:
			for delete_effect in delete_effects:
				if add_effect.predicate == delete_effect.predicate:
					continue
				patterns.append(
					_ProducerDeletePattern(
						action_name=action_name,
						add_effect=add_effect,
						delete_effect=delete_effect,
					),
				)
	return tuple(patterns)


def _matching_pattern(
	*,
	patterns: Sequence[_ProducerDeletePattern],
	added_goal: str,
	deleted_goal: str,
) -> _ProducerDeletePattern | None:
	for pattern in tuple(patterns or ()):
		substitution = _match_literal_to_atom(pattern.add_effect, added_goal, {})
		if substitution is None:
			continue
		if (
			_match_literal_to_atom(pattern.delete_effect, deleted_goal, substitution)
			is not None
		):
			return pattern
	return None


def _match_literal_to_atom(
	literal: LiftedLiteral,
	atom: str,
	substitution: Mapping[str, str],
) -> dict[str, str] | None:
	predicate, arguments = _parse_atom(atom)
	if literal.predicate != predicate:
		return None
	lifted_arguments = tuple(literal.arguments or ())
	if len(lifted_arguments) != len(arguments):
		return None
	merged = dict(substitution)
	for lifted, grounded in zip(lifted_arguments, arguments):
		if _is_pddl_variable(lifted):
			current = merged.get(lifted)
			if current is not None and current != grounded:
				return None
			merged[lifted] = grounded
			continue
		if lifted != grounded:
			return None
	return merged


def _parse_atom(atom: str) -> tuple[str, tuple[str, ...]]:
	text = str(atom or "").strip()
	if "(" not in text:
		return text, ()
	if not text.endswith(")"):
		return text, ()
	predicate, raw_arguments = text.split("(", 1)
	return (
		predicate.strip(),
		tuple(
			argument.strip()
			for argument in raw_arguments[:-1].split(",")
			if argument.strip()
		),
	)


def _literal_signature(literal: LiftedLiteral) -> str:
	atom = (
		literal.predicate
		if not literal.arguments
		else f"{literal.predicate}({', '.join(literal.arguments)})"
	)
	return atom if literal.is_positive else f"not {atom}"


def _is_pddl_variable(token: str) -> bool:
	return str(token or "").strip().startswith("?")
