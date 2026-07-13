from __future__ import annotations

import pytest

from evaluation.ltlf_trace_semantics import evaluate_formula_ast_on_trace


@pytest.mark.parametrize(
	("formula", "trace", "expected"),
	(
		({"operator": "atom", "atom_id": "a0"}, ({"a0": True},), True),
		({"operator": "atom", "atom_id": "a0"}, ({"a0": False},), False),
		(
			{
				"operator": "not",
				"operand": {"operator": "atom", "atom_id": "a0"},
			},
			({"a0": False},),
			True,
		),
		(
			{
				"operator": "and",
				"operands": [
					{"operator": "atom", "atom_id": "a0"},
					{"operator": "atom", "atom_id": "a1"},
				],
			},
			({"a0": True, "a1": False}, {"a0": False, "a1": True}),
			False,
		),
		(
			{
				"operator": "eventually",
				"operand": {"operator": "atom", "atom_id": "a0"},
			},
			({"a0": False}, {"a0": True}),
			True,
		),
		(
			{
				"operator": "next",
				"operand": {"operator": "atom", "atom_id": "a0"},
			},
			({"a0": True},),
			False,
		),
		(
			{
				"operator": "next",
				"operand": {"operator": "atom", "atom_id": "a0"},
			},
			({"a0": False}, {"a0": True}),
			True,
		),
		(
			{
				"operator": "until",
				"left": {"operator": "atom", "atom_id": "a0"},
				"right": {"operator": "atom", "atom_id": "a1"},
			},
			({"a0": False, "a1": True},),
			True,
		),
		(
			{
				"operator": "until",
				"left": {"operator": "atom", "atom_id": "a0"},
				"right": {"operator": "atom", "atom_id": "a1"},
			},
			({"a0": False, "a1": False}, {"a0": True, "a1": True}),
			False,
		),
	),
)
def test_direct_finite_trace_semantics(
	formula: dict[str, object],
	trace: tuple[dict[str, bool], ...],
	expected: bool,
) -> None:
	assert evaluate_formula_ast_on_trace(formula, trace) is expected


def test_direct_finite_trace_semantics_rejects_empty_trace() -> None:
	with pytest.raises(ValueError, match="non-empty"):
		evaluate_formula_ast_on_trace(
			{"operator": "atom", "atom_id": "a0"},
			(),
		)
