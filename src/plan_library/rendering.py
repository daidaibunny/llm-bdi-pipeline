"""
Render structured AgentSpeak(L) plan libraries as textual `.asl` programs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import re

from .models import AgentSpeakBodyStep, AgentSpeakPlan, PlanLibrary


def render_plan_library_asl(plan_library: PlanLibrary) -> str:
	"""Render a structured plan library into a readable AgentSpeak(L) file."""

	validate_generated_asl_library(plan_library)
	lines: List[str] = [
		"/* Generated AgentSpeak(L) Plan Library */",
		f"/* Domain: {plan_library.domain_name} */",
		"",
	]
	for belief in plan_library.initial_beliefs:
		lines.append(f"{_render_atom(belief)}.")
	if plan_library.initial_beliefs:
		lines.append("")
	for plan in plan_library.plans:
		lines.extend(_render_plan(plan))
		lines.append("")
	return "\n".join(lines).rstrip() + "\n"


def _render_plan(plan: AgentSpeakPlan) -> List[str]:
	trigger = _call(
		plan.trigger.symbol,
		tuple(_raw_argument(argument) for argument in plan.trigger.arguments),
	)
	context = " & ".join(
		_render_context_item(literal)
		for literal in _ordered_context_items(plan.context)
	) or "true"
	body_items = [_render_body_step(step) for step in plan.body]
	if not body_items:
		body_items = ["true"]
	source_ids = ", ".join(plan.source_instruction_ids) if plan.source_instruction_ids else "none"
	lines = [
		f"/* plan={plan.plan_name} | source_instruction_ids={source_ids} */",
		f"+!{trigger} : {context} <-",
	]
	for index, body_item in enumerate(body_items):
		suffix = ";" if index < len(body_items) - 1 else "."
		lines.append(f"\t{body_item}{suffix}")
	return lines


def _ordered_context_items(context: tuple[str, ...]) -> tuple[str, ...]:
	"""Order context guards so dynamic binders run before static type filters."""

	return tuple(
		item
		for _, item in sorted(
			enumerate(context),
			key=lambda indexed: (_context_item_order_bucket(indexed[1]), indexed[0]),
		)
	)


def _context_item_order_bucket(item: str) -> int:
	text = str(item or "").strip()
	if _is_positive_simple_context_atom(text) and not _is_obj_tp_context_atom(text):
		return 0
	if _is_obj_tp_context_atom(text):
		return 1
	return 2


def _is_positive_simple_context_atom(text: str) -> bool:
	if not text or text.lower().startswith("not "):
		return False
	if any(operator in text for operator in ("&", "|", "\\==", "!=", ">=", "<=", "==", ">", "<")):
		return False
	return _simple_atom_symbol(text) is not None


def _is_obj_tp_context_atom(text: str) -> bool:
	return _simple_atom_symbol(text) == "obj_tp"


def _simple_atom_symbol(text: str) -> str | None:
	if not text or text.startswith("="):
		return None
	if "(" not in text:
		return sanitize_identifier(text)
	if not text.endswith(")"):
		return None
	symbol, raw_args = text.split("(", 1)
	if not symbol.strip() or "(" in raw_args[:-1] or ")" in raw_args[:-1]:
		return None
	return sanitize_identifier(symbol)


def _render_body_step(step: AgentSpeakBodyStep) -> str:
	call = _call(step.symbol, step.arguments)
	if step.kind == "subgoal":
		return f"!{call}"
	if step.kind == "belief_addition":
		return f"+{call}"
	if step.kind == "belief_deletion":
		return f"-{call}"
	return call


def _call(symbol: str, arguments) -> str:
	if not arguments:
		return _jason_functor(symbol)
	return f"{_jason_functor(symbol)}({', '.join(_render_term(argument) for argument in arguments)})"


def _raw_argument(argument: str) -> str:
	text = str(argument or "").strip()
	if ":" in text:
		return text.split(":", 1)[0].strip()
	return text


def _render_context_literal(literal: str) -> str:
	text = str(literal or "").strip()
	if not text:
		return "true"
	if text.startswith("!"):
		return f"not {_render_atom(text[1:].strip())}"
	if text.lower().startswith("not "):
		atom = text[4:].strip()
		equality = _parse_equality_atom(atom)
		if equality is not None:
			left, right = equality
			return f"{_render_term(left)} \\== {_render_term(right)}"
		return f"not {_render_atom(atom)}"
	equality = _parse_equality_atom(text)
	if equality is not None:
		left, right = equality
		return f"{_render_term(left)} == {_render_term(right)}"
	if "!=" in text:
		left, right = text.split("!=", 1)
		return f"{_render_term(left)} \\== {_render_term(right)}"
	if "==" in text:
		left, right = text.split("==", 1)
		return f"{_render_term(left)} == {_render_term(right)}"
	return _render_atom(text)


def _render_context_item(literal: str) -> str:
	rendered = _render_context_expression(str(literal or "").strip())
	if rendered.precedence < _CONTEXT_PRECEDENCE["&"]:
		return f"({rendered.text})"
	return rendered.text


@dataclass(frozen=True)
class _RenderedContextExpression:
	text: str
	precedence: int


_CONTEXT_PRECEDENCE = {
	"|": 1,
	"&": 2,
	"not": 3,
	"comparison": 4,
	"atom": 5,
}


def _render_context_expression(expression: str) -> _RenderedContextExpression:
	text = str(expression or "").strip()
	if not text:
		raise ValueError("Invalid AgentSpeak context expression: empty expression.")
	text = _strip_balanced_outer_parentheses(text)
	for operator in ("|", "&"):
		parts = _split_top_level_operator(text, operator)
		if len(parts) > 1:
			rendered_parts = tuple(_render_context_expression(part) for part in parts)
			precedence = _CONTEXT_PRECEDENCE[operator]
			return _RenderedContextExpression(
				text=f" {operator} ".join(
					_maybe_parenthesize_context(part, precedence)
					for part in rendered_parts
				),
				precedence=precedence,
			)
	if _starts_with_not_operator(text):
		child = _render_context_expression(text[3:].strip())
		return _RenderedContextExpression(
			text=f"not {_maybe_parenthesize_context(child, _CONTEXT_PRECEDENCE['not'])}",
			precedence=_CONTEXT_PRECEDENCE["not"],
		)
	for operator, rendered_operator in (
		("\\==", "\\=="),
		("!=", "\\=="),
		(">=", ">="),
		("<=", "<="),
		("==", "=="),
		(">", ">"),
		("<", "<"),
	):
		parts = _split_top_level_operator(text, operator)
		if len(parts) == 2:
			left, right = parts
			return _RenderedContextExpression(
				text=f"{_render_term(left)} {rendered_operator} {_render_term(right)}",
				precedence=_CONTEXT_PRECEDENCE["comparison"],
			)
		if len(parts) > 2:
			raise ValueError(
				f"Invalid AgentSpeak context expression with repeated {operator!r}: {text}",
			)
	return _RenderedContextExpression(
		text=_render_context_literal(text),
		precedence=_CONTEXT_PRECEDENCE["atom"],
	)


def _starts_with_not_operator(text: str) -> bool:
	return text.lower().startswith("not ") and bool(text[3:].strip())


def _maybe_parenthesize_context(
	rendered: _RenderedContextExpression,
	parent_precedence: int,
) -> str:
	if rendered.precedence < parent_precedence:
		return f"({rendered.text})"
	return rendered.text


def _split_top_level_operator(text: str, operator: str) -> tuple[str, ...]:
	parts: list[str] = []
	start = 0
	depth = 0
	index = 0
	while index < len(text):
		character = text[index]
		if character == "(":
			depth += 1
			index += 1
			continue
		if character == ")":
			depth -= 1
			if depth < 0:
				raise ValueError(f"Invalid AgentSpeak context expression: {text}")
			index += 1
			continue
		if depth == 0 and text.startswith(operator, index):
			part = text[start:index].strip()
			if not part:
				raise ValueError(f"Invalid AgentSpeak context expression: {text}")
			parts.append(part)
			index += len(operator)
			start = index
			continue
		index += 1
	if depth != 0:
		raise ValueError(f"Invalid AgentSpeak context expression: {text}")
	if parts:
		part = text[start:].strip()
		if not part:
			raise ValueError(f"Invalid AgentSpeak context expression: {text}")
		parts.append(part)
	return tuple(parts or (text.strip(),))


def _strip_balanced_outer_parentheses(text: str) -> str:
	current = text
	while current.startswith("(") and current.endswith(")") and _outer_parentheses_wrap(current):
		current = current[1:-1].strip()
	return current


def _outer_parentheses_wrap(text: str) -> bool:
	depth = 0
	for index, character in enumerate(text):
		if character == "(":
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0 and index != len(text) - 1:
				return False
			if depth < 0:
				raise ValueError(f"Invalid AgentSpeak context expression: {text}")
	return depth == 0


def _render_atom(atom: str) -> str:
	text = str(atom or "").strip()
	if not text:
		return "true"
	equality = _parse_equality_atom(text)
	if equality is not None:
		left, right = equality
		return f"{_render_term(left)} == {_render_term(right)}"
	if "(" not in text:
		return _jason_functor(text)
	if not text.endswith(")"):
		return _jason_functor(text)
	symbol, raw_args = text.split("(", 1)
	args = tuple(argument.strip() for argument in raw_args[:-1].split(",") if argument.strip())
	return _call(symbol, args)


def _render_term(term: str) -> str:
	text = str(term or "").strip()
	if not text:
		return "item"
	if _is_agentspeak_variable(text):
		return text
	if re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", text):
		return text
	if re.fullmatch(r"[a-z][A-Za-z0-9_]*", text):
		return text
	return sanitize_identifier(text)


def _parse_equality_atom(atom: str) -> tuple[str, str] | None:
	text = str(atom or "").strip()
	if not text.startswith("=") or not text.endswith(")"):
		return None
	raw_arguments = text[2:-1] if text.startswith("=(") else ""
	arguments = tuple(
		argument.strip()
		for argument in raw_arguments.split(",")
		if argument.strip()
	)
	if len(arguments) != 2:
		return None
	return arguments[0], arguments[1]


def _jason_functor(symbol: str) -> str:
	return sanitize_identifier(str(symbol or "").strip())


def _is_agentspeak_variable(token: str) -> bool:
	return re.fullmatch(r"[A-Z][A-Za-z0-9_]*", str(token or "").strip()) is not None


def sanitize_identifier(value: str) -> str:
	text = str(value or "").strip().replace("-", "_")
	buffer: list[str] = []
	for character in text:
		if character.isalnum() or character == "_":
			buffer.append(character.lower())
		else:
			buffer.append("_")
	sanitized = "".join(buffer).strip("_")
	while "__" in sanitized:
		sanitized = sanitized.replace("__", "_")
	if not sanitized:
		sanitized = "item"
	if not sanitized[0].isalpha():
		sanitized = f"t_{sanitized}"
	return sanitized


def validate_generated_asl_library(plan_library: PlanLibrary) -> None:
	"""Validate the AgentSpeak(L) subset emitted by this renderer."""

	for belief in plan_library.initial_beliefs:
		_render_atom(belief)
	for plan in plan_library.plans:
		_call(plan.trigger.symbol, tuple(_raw_argument(argument) for argument in plan.trigger.arguments))
		for context in plan.context:
			_render_context_expression(context)
		for step in plan.body:
			if step.kind not in {
				"action",
				"primitive_action",
				"subgoal",
				"belief_addition",
				"belief_deletion",
			}:
				raise ValueError(
					f"Invalid AgentSpeak body step kind {step.kind!r} in plan {plan.plan_name!r}.",
				)
			_call(step.symbol, step.arguments)
