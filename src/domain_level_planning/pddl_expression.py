"""
Small PDDL expression helpers for schema-level lifted synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


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
			return (
				LiftedLiteral(
					predicate=str(child[0]),
					arguments=tuple(str(argument) for argument in child[1:]),
					is_positive=False,
				),
			)
		return ()
	if head in {"or", "forall", "exists", "when", "imply"}:
		return ()
	return (
		LiftedLiteral(
			predicate=str(expression[0]),
			arguments=tuple(str(argument) for argument in expression[1:]),
			is_positive=True,
		),
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
