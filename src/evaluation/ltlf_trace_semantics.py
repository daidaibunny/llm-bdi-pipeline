"""Direct finite-trace semantics for the declared benchmark LTLf fragment."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any


def evaluate_formula_ast_on_trace(
	formula: Mapping[str, Any],
	trace: Sequence[Mapping[str, bool]],
) -> bool:
	"""Evaluate one structured LTLf formula on a non-empty valuation trace.

	This evaluator is deliberately independent of MONA and ``ltlf2dfa``. It is
	used as a semantic oracle for conformance tests, not as the runtime monitor.
	"""

	states = tuple(trace)
	if not states:
		raise ValueError("LTLf semantics requires a non-empty finite trace.")
	return _evaluate(formula, states, 0)


def _evaluate(
	node: Mapping[str, Any],
	trace: tuple[Mapping[str, bool], ...],
	position: int,
) -> bool:
	operator = str(node.get("operator") or "").strip()
	if operator == "atom":
		atom_id = str(node.get("atom_id") or "").strip()
		if not atom_id:
			raise ValueError("LTLf atom node requires a non-empty atom_id.")
		return bool(trace[position].get(atom_id, False))
	if operator == "not":
		return not _evaluate(_node(node.get("operand"), operator), trace, position)
	if operator == "and":
		raw_operands = node.get("operands")
		if not isinstance(raw_operands, Sequence) or isinstance(
			raw_operands,
			(str, bytes),
		):
			raise ValueError("LTLf and node requires an operands array.")
		operands = tuple(_node(item, operator) for item in raw_operands)
		if not operands:
			raise ValueError("LTLf and node requires at least one operand.")
		return all(_evaluate(operand, trace, position) for operand in operands)
	if operator == "next":
		return position + 1 < len(trace) and _evaluate(
			_node(node.get("operand"), operator),
			trace,
			position + 1,
		)
	if operator == "eventually":
		operand = _node(node.get("operand"), operator)
		return any(_evaluate(operand, trace, index) for index in range(position, len(trace)))
	if operator == "until":
		left = _node(node.get("left"), operator)
		right = _node(node.get("right"), operator)
		return any(
			_evaluate(right, trace, witness)
			and all(_evaluate(left, trace, prior) for prior in range(position, witness))
			for witness in range(position, len(trace))
		)
	raise ValueError(f"Unsupported LTLf formula operator {operator!r}.")


def _node(value: object, parent_operator: str) -> Mapping[str, Any]:
	if not isinstance(value, Mapping):
		raise ValueError(f"LTLf {parent_operator} node has a malformed child.")
	return value
