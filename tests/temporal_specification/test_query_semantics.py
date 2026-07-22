from __future__ import annotations

import pytest

from temporal_specification.query_semantics import LTLfQueryKind
from temporal_specification.query_semantics import classify_ltlf_query
from temporal_specification.query_semantics import execution_ltlf_formula


@pytest.mark.parametrize(
	("formula", "expected_kind"),
	(
		("a0", LTLfQueryKind.ACHIEVEMENT),
		("a0 & !a1", LTLfQueryKind.ACHIEVEMENT),
		("on(X,Y) & clear(Y)", LTLfQueryKind.ACHIEVEMENT),
		("fixed(X) & usable(U)", LTLfQueryKind.ACHIEVEMENT),
		("F(a0)", LTLfQueryKind.TEMPORALLY_EXTENDED),
		("a0 & X(a1)", LTLfQueryKind.TEMPORALLY_EXTENDED),
		("a0 U a1", LTLfQueryKind.TEMPORALLY_EXTENDED),
	),
)
def test_classify_ltlf_query_distinguishes_achievement_and_temporal_formulas(
	formula: str,
	expected_kind: LTLfQueryKind,
) -> None:
	assert classify_ltlf_query(formula) == expected_kind


def test_execution_ltlf_formula_embeds_achievement_completion() -> None:
	assert execution_ltlf_formula("on(X,Y) & clear(Y)") == (
		"F(on(X,Y) & clear(Y))"
	)


def test_execution_ltlf_formula_preserves_temporally_extended_formula() -> None:
	formula = "F(on(X,Y) & X(clear(Y)))"

	assert execution_ltlf_formula(formula) == formula


def test_execution_ltlf_formula_rejects_empty_formula() -> None:
	with pytest.raises(ValueError, match="must be non-empty"):
		execution_ltlf_formula("  ")
