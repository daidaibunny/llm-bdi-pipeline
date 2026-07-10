from __future__ import annotations

import pytest

from temporal_specification.errors import (
	NON_RETRYABLE_ERROR_CODES,
	TranslationErrorCode,
	build_retry_feedback,
)


def test_schema_error_builds_model_correctable_feedback() -> None:
	feedback = build_retry_feedback(
		previous_ltlf="F(a0 | a1)",
		error_code=TranslationErrorCode.E_UNSUPPORTED_OPERATOR,
		error_detail="operator | at character 5 is not allowed",
		attempt=2,
	)

	assert feedback == {
		"previous_ltlf": "F(a0 | a1)",
		"error_type": "E_UNSUPPORTED_OPERATOR",
		"error_detail": "operator | at character 5 is not allowed",
		"hint": "Use only F, X, U, &, and !; preserve the source query's meaning.",
		"attempt": 2,
	}


@pytest.mark.parametrize("error_code", sorted(NON_RETRYABLE_ERROR_CODES))
def test_infrastructure_errors_cannot_be_sent_as_semantic_retries(
	error_code: TranslationErrorCode,
) -> None:
	with pytest.raises(ValueError, match="not model-correctable"):
		build_retry_feedback(
			previous_ltlf="F(a0)",
			error_code=error_code,
			error_detail="backend failed",
			attempt=2,
		)


def test_retry_attempt_must_follow_the_initial_attempt() -> None:
	with pytest.raises(ValueError, match="at least 2"):
		build_retry_feedback(
			previous_ltlf="F(a0)",
			error_code=TranslationErrorCode.E_LTLF_SYNTAX,
			error_detail="unbalanced parentheses",
			attempt=1,
		)
