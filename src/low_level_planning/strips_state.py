"""
Small STRIPS state transition helper for generated Fast Downward traces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from utils.pddl_parser import PDDLAction, PDDLDomain, PDDLFact, PDDLParser

from .models import LowLevelAction
from .pddl_goal import context_literal_to_fact


@dataclass(frozen=True)
class GroundActionSemantics:
	"""Grounded preconditions and effects for one primitive action."""

	positive_preconditions: frozenset[str]
	negative_preconditions: frozenset[str]
	add_effects: frozenset[str]
	delete_effects: frozenset[str]
	positive_equalities: frozenset[tuple[str, str]] = frozenset()
	negative_equalities: frozenset[tuple[str, str]] = frozenset()


class STRIPSStateSimulator:
	"""Apply grounded STRIPS actions over the PDDL subset used by benchmarks."""

	def __init__(self, domain_file: str) -> None:
		self.domain = PDDLParser.parse_domain(domain_file)
		self._actions_by_name = {
			action.name.lower(): action
			for action in self.domain.actions
		}

	def initial_state_from_problem(self, problem_file: str) -> frozenset[str]:
		"""Return the positive initial facts of one PDDL problem as signatures."""

		problem = PDDLParser.parse_problem(problem_file)
		return frozenset(
			fact_to_signature(fact)
			for fact in problem.init_facts
			if fact.is_positive
		)

	def apply_plan(
		self,
		*,
		state: Iterable[str],
		actions: Iterable[LowLevelAction],
	) -> frozenset[str]:
		"""Apply a sequence of grounded actions and return the successor state."""

		current_state = frozenset(state)
		for action in actions:
			current_state = self.apply_action(state=current_state, action=action)
		return current_state

	def apply_action(
		self,
		*,
		state: Iterable[str],
		action: LowLevelAction,
	) -> frozenset[str]:
		"""Apply one grounded action, raising when preconditions are not met."""

		current_state = frozenset(state)
		semantics = self.ground_action(action)
		missing = semantics.positive_preconditions - current_state
		violated = semantics.negative_preconditions & current_state
		equality_violated = any(
			left != right
			for left, right in semantics.positive_equalities
		)
		inequality_violated = any(
			left == right
			for left, right in semantics.negative_equalities
		)
		if missing or violated or equality_violated or inequality_violated:
			raise ValueError(
				"Action preconditions are not satisfied for "
				f"{action.name}({', '.join(action.arguments)})."
			)
		return frozenset((current_state - semantics.delete_effects) | semantics.add_effects)

	def ground_action(self, action: LowLevelAction) -> GroundActionSemantics:
		"""Ground the domain action schema matching one planner action."""

		schema = self._actions_by_name.get(action.name.lower())
		if schema is None:
			raise ValueError(f"Unknown action returned by planner: {action.name}")
		substitution = {
			_parameter_name(parameter): argument
			for parameter, argument in zip(schema.parameters, action.arguments)
		}
		(
			positive_preconditions,
			negative_preconditions,
			positive_equalities,
			negative_equalities,
		) = _parse_fact_set(
			schema.preconditions,
			substitution=substitution,
		)
		add_effects, delete_effects, _, _ = _parse_fact_set(
			schema.effects,
			substitution=substitution,
		)
		return GroundActionSemantics(
			positive_preconditions=frozenset(positive_preconditions),
			negative_preconditions=frozenset(negative_preconditions),
			add_effects=frozenset(add_effects),
			delete_effects=frozenset(delete_effects),
			positive_equalities=frozenset(positive_equalities),
			negative_equalities=frozenset(negative_equalities),
		)


def fact_to_signature(fact: PDDLFact) -> str:
	"""Return the project-standard signature for one positive fact."""

	return fact.predicate if not fact.args else f"{fact.predicate}({', '.join(fact.args)})"


def signatures_to_facts(signatures: Iterable[str]) -> Tuple[PDDLFact, ...]:
	"""Convert positive fact signatures back to PDDL facts."""

	return tuple(context_literal_to_fact(signature) for signature in sorted(set(signatures)))


def _parameter_name(parameter: str) -> str:
	return str(parameter or "").strip().split()[0]


def _parse_fact_set(
	expression: str,
	*,
	substitution: dict[str, str],
) -> tuple[set[str], set[str], set[tuple[str, str]], set[tuple[str, str]]]:
	text = str(expression or "").strip()
	if not text:
		return set(), set(), set(), set()
	expressions = _inner_expressions(text)
	if not expressions and text.startswith("("):
		expressions = (text,)
	positive: set[str] = set()
	negative: set[str] = set()
	positive_equalities: set[tuple[str, str]] = set()
	negative_equalities: set[tuple[str, str]] = set()
	for item in expressions:
		item_text = item.strip()
		if _is_numeric_effect_expression(item_text):
			continue
		if item_text.lower().startswith("(not"):
			inner = _inner_expressions(item_text)
			if inner:
				inner_text = inner[0].strip()
				if _is_equality_expression(inner_text):
					negative_equalities.add(
						_ground_equality(inner_text, substitution=substitution),
					)
				elif not _is_numeric_effect_expression(inner_text):
					negative.add(_ground_atom(inner_text, substitution=substitution))
			continue
		if item_text.lower().startswith("(and"):
			(
				nested_positive,
				nested_negative,
				nested_positive_equalities,
				nested_negative_equalities,
			) = _parse_fact_set(
				item_text,
				substitution=substitution,
			)
			positive.update(nested_positive)
			negative.update(nested_negative)
			positive_equalities.update(nested_positive_equalities)
			negative_equalities.update(nested_negative_equalities)
			continue
		if _is_equality_expression(item_text):
			positive_equalities.add(
				_ground_equality(item_text, substitution=substitution),
			)
			continue
		positive.add(_ground_atom(item_text, substitution=substitution))
	return positive, negative, positive_equalities, negative_equalities


def _ground_atom(expression: str, *, substitution: dict[str, str]) -> str:
	tokens = str(expression or "").strip("() \n\t").split()
	if not tokens:
		raise ValueError("Cannot ground an empty PDDL atom.")
	predicate = tokens[0]
	args = tuple(substitution.get(token, token) for token in tokens[1:])
	return predicate if not args else f"{predicate}({', '.join(args)})"


def _ground_equality(
	expression: str,
	*,
	substitution: dict[str, str],
) -> tuple[str, str]:
	tokens = str(expression or "").strip("() \n\t").split()
	if len(tokens) != 3 or tokens[0] != "=":
		raise ValueError(f"Cannot ground unsupported equality expression: {expression}")
	return substitution.get(tokens[1], tokens[1]), substitution.get(tokens[2], tokens[2])


def _is_equality_expression(expression: str) -> bool:
	tokens = str(expression or "").strip("() \n\t").split()
	return len(tokens) == 3 and tokens[0] == "="


def _is_numeric_effect_expression(expression: str) -> bool:
	tokens = str(expression or "").strip("() \n\t").split(maxsplit=1)
	return bool(tokens) and tokens[0].lower() in {
		"increase",
		"decrease",
		"assign",
		"scale-up",
		"scale-down",
	}


def _inner_expressions(expression: str) -> tuple[str, ...]:
	text = str(expression or "").strip()
	if not text.startswith("("):
		return ()
	if text.lower().startswith("(and"):
		start = text.find(" ", 1)
		inner = text[start:-1] if start != -1 else ""
		return _top_level_expressions(inner)
	if text.lower().startswith("(not"):
		inner_start = text.find("(", 1)
		if inner_start == -1:
			return ()
		inner_end = _find_matching_paren(text, inner_start)
		return (text[inner_start:inner_end + 1],)
	return ()


def _top_level_expressions(text: str) -> tuple[str, ...]:
	expressions: list[str] = []
	start = None
	depth = 0
	for index, character in enumerate(text):
		if character == "(":
			if depth == 0:
				start = index
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0 and start is not None:
				expressions.append(text[start:index + 1])
				start = None
	return tuple(expressions)


def _find_matching_paren(text: str, start: int) -> int:
	depth = 0
	for index in range(start, len(text)):
		if text[index] == "(":
			depth += 1
		elif text[index] == ")":
			depth -= 1
			if depth == 0:
				return index
	raise ValueError(f"Unmatched parenthesis at index {start}.")
