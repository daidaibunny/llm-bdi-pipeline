"""Retry boundary for natural-language to lifted LTLf translation errors."""

from __future__ import annotations

from enum import Enum
from typing import Any


class TranslationErrorCode(str, Enum):
	"""Stable validation outcomes for predicted lifted LTLf payloads."""

	E_JSON_FORMAT = "E_JSON_FORMAT"
	E_LTLF_SYNTAX = "E_LTLF_SYNTAX"
	E_UNKNOWN_SYMBOL = "E_UNKNOWN_SYMBOL"
	E_ATOM_KIND = "E_ATOM_KIND"
	E_ARITY_MISMATCH = "E_ARITY_MISMATCH"
	E_TYPE_MISMATCH = "E_TYPE_MISMATCH"
	E_DECLARED_PARAMETER_MISMATCH = "E_DECLARED_PARAMETER_MISMATCH"
	E_CONSTRAINT_MISMATCH = "E_CONSTRAINT_MISMATCH"
	E_UNSUPPORTED_OPERATOR = "E_UNSUPPORTED_OPERATOR"
	E_FORMULA_ATOM_MISMATCH = "E_FORMULA_ATOM_MISMATCH"
	E_DFA_UNSAT = "E_DFA_UNSAT"
	E_LLM_TIMEOUT = "E_LLM_TIMEOUT"
	E_NETWORK = "E_NETWORK"
	E_LTLF2DFA_FAILURE = "E_LTLF2DFA_FAILURE"
	E_MONA_FAILURE = "E_MONA_FAILURE"
	E_MONA_TIMEOUT = "E_MONA_TIMEOUT"
	E_DFA_FORMAT = "E_DFA_FORMAT"


RETRY_HINTS: dict[TranslationErrorCode, str] = {
	TranslationErrorCode.E_JSON_FORMAT: (
		"Return JSON only with exactly the eight required top-level keys."
	),
	TranslationErrorCode.E_LTLF_SYNTAX: (
		"Correct parentheses and operator placement without changing the source meaning."
	),
	TranslationErrorCode.E_UNKNOWN_SYMBOL: (
		"Use only catalogue predicates/functions, declared parameters, domain constants, "
		"and atom symbols defined in the atom table."
	),
	TranslationErrorCode.E_ATOM_KIND: (
		"Use kind predicate or numeric_equality and provide exactly the fields required "
		"for that kind."
	),
	TranslationErrorCode.E_ARITY_MISMATCH: (
		"Match every predicate or numeric function's catalogue argument count."
	),
	TranslationErrorCode.E_TYPE_MISMATCH: (
		"Use each declared parameter only in catalogue positions compatible with its "
		"PDDL type or subtype."
	),
	TranslationErrorCode.E_DECLARED_PARAMETER_MISMATCH: (
		"Copy the declared parameters exactly; do not add, omit, rename, or ground them."
	),
	TranslationErrorCode.E_CONSTRAINT_MISMATCH: (
		"Copy the public external constraints exactly and do not encode them as atoms."
	),
	TranslationErrorCode.E_UNSUPPORTED_OPERATOR: (
		"Use only F, X, U, &, and !; preserve the source query's meaning."
	),
	TranslationErrorCode.E_FORMULA_ATOM_MISMATCH: (
		"Define every a<number> formula symbol exactly once, in first-occurrence order, "
		"and remove unused atom definitions."
	),
	TranslationErrorCode.E_DFA_UNSAT: (
		"The predicted formula is inconsistent; retranslate the source query using only "
		"its stated requirements."
	),
}

NON_RETRYABLE_ERROR_CODES = frozenset(
	{
		TranslationErrorCode.E_LLM_TIMEOUT,
		TranslationErrorCode.E_NETWORK,
		TranslationErrorCode.E_LTLF2DFA_FAILURE,
		TranslationErrorCode.E_MONA_FAILURE,
		TranslationErrorCode.E_MONA_TIMEOUT,
		TranslationErrorCode.E_DFA_FORMAT,
	},
)


def build_retry_feedback(
	*,
	previous_ltlf: str,
	error_code: TranslationErrorCode,
	error_detail: str,
	attempt: int,
) -> dict[str, Any]:
	"""Build feedback only for failures the translation model can correct."""

	code = TranslationErrorCode(error_code)
	if code in NON_RETRYABLE_ERROR_CODES:
		raise ValueError(f"{code.value} is not model-correctable")
	if attempt < 2:
		raise ValueError("retry attempt must be at least 2")
	detail = str(error_detail or "").strip()
	if not detail:
		raise ValueError("error_detail must be non-empty")
	return {
		"previous_ltlf": str(previous_ltlf or "").strip(),
		"error_type": code.value,
		"error_detail": detail,
		"hint": RETRY_HINTS[code],
		"attempt": int(attempt),
	}
