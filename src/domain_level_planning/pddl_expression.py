"""
Small PDDL expression helpers for schema-level lifted synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

NUMERIC_EFFECT_OPERATORS = frozenset(
	{
		"increase",
		"decrease",
		"assign",
		"scale-up",
		"scale-down",
	}
)

UNSUPPORTED_LOGICAL_OPERATORS = frozenset(
	{
		"or",
		"forall",
		"exists",
		"when",
		"imply",
		"preference",
	}
)


@dataclass(frozen=True)
class LiftedLiteral:
	"""A lifted predicate literal parsed from a PDDL expression."""

	predicate: str
	arguments: tuple[str, ...] = ()
	is_positive: bool = True

	def signature(self) -> str:
		atom = (
			self.predicate
			if not self.arguments
			else f"{self.predicate}({', '.join(_var(argument) for argument in self.arguments)})"
		)
		return atom if self.is_positive else f"not {atom}"


def parse_pddl_literals(expression: str) -> tuple[LiftedLiteral, ...]:
	"""Parse positive and negative predicate literals from a PDDL expression."""

	text = str(expression or "").strip()
	if not text:
		return ()
	parsed = _parse_expression(text)
	return tuple(_literals_from_expression(parsed))


def parameter_variables(parameters: Iterable[str]) -> tuple[str, ...]:
	"""Return AgentSpeak-style variables from PDDL parameter declarations."""

	return tuple(_var(parameter) for parameter in parameters)


def _literals_from_expression(expression: object) -> Iterable[LiftedLiteral]:
	if not isinstance(expression, tuple) or not expression:
		return ()
	head = str(expression[0]).lower()
	if head == "and":
		literals: list[LiftedLiteral] = []
		for child in expression[1:]:
			literals.extend(_literals_from_expression(child))
		return tuple(literals)
	if head == "not" and len(expression) == 2:
		child = expression[1]
		if isinstance(child, tuple) and child:
			if _is_numeric_effect_expression(child):
				return ()
			return (
				LiftedLiteral(
					predicate=str(child[0]),
					arguments=_literal_arguments(child[1:]),
					is_positive=False,
				),
			)
		return ()
	if _is_numeric_effect_expression(expression):
		return ()
	if head in UNSUPPORTED_LOGICAL_OPERATORS:
		raise ValueError(
			f"Unsupported PDDL expression operator {head!r} in compilable STRIPS subset.",
		)
	return (
		LiftedLiteral(
			predicate=str(expression[0]),
			arguments=_literal_arguments(expression[1:]),
			is_positive=True,
		),
	)


def _literal_arguments(arguments: Iterable[object]) -> tuple[str, ...]:
	return tuple(str(argument) for argument in arguments if not isinstance(argument, tuple))


def _is_numeric_effect_expression(expression: object) -> bool:
	return (
		isinstance(expression, tuple)
		and bool(expression)
		and str(expression[0]).lower() in NUMERIC_EFFECT_OPERATORS
	)


def _parse_expression(text: str) -> object:
	tokens = _tokens(text)
	if not tokens:
		return ()
	expression, cursor = _parse_tokens(tokens, 0)
	if cursor != len(tokens):
		raise ValueError(f"Could not parse full PDDL expression: {text}")
	return expression


def _tokens(text: str) -> tuple[str, ...]:
	buffer: list[str] = []
	token = []
	for character in text:
		if character in "()":
			if token:
				buffer.append("".join(token))
				token = []
			buffer.append(character)
		elif character.isspace():
			if token:
				buffer.append("".join(token))
				token = []
		else:
			token.append(character)
	if token:
		buffer.append("".join(token))
	return tuple(buffer)


def _parse_tokens(tokens: tuple[str, ...], cursor: int) -> tuple[object, int]:
	if cursor >= len(tokens):
		raise ValueError("Unexpected end of PDDL expression.")
	if tokens[cursor] != "(":
		return tokens[cursor], cursor + 1
	cursor += 1
	items: list[object] = []
	while cursor < len(tokens) and tokens[cursor] != ")":
		item, cursor = _parse_tokens(tokens, cursor)
		items.append(item)
	if cursor >= len(tokens):
		raise ValueError("Unmatched parenthesis in PDDL expression.")
	return tuple(items), cursor + 1


def _var(parameter: str) -> str:
	name = str(parameter or "").strip()
	if " - " in name:
		name = name.split(" - ", 1)[0].strip()
	name = name.lstrip("?")
	if not name:
		return "X"
	return f"{name[0].upper()}{name[1:]}"
