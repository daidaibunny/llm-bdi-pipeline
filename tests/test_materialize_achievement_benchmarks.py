from __future__ import annotations

import pytest

from scripts.materialize_achievement_benchmarks import _normalize_problem_domain_reference


def test_problem_domain_reference_is_normalized_from_actual_domain_schema() -> None:
	content = b"""
(define (problem p01)
  (:domain source-alias)
  (:objects x)
  (:init)
  (:goal (and)))
"""

	normalized, changed = _normalize_problem_domain_reference(
		content,
		expected_domain_name="materialized-domain",
	)

	assert changed is True
	assert b"(:domain materialized-domain)" in normalized
	assert b"(:objects x)" in normalized


def test_problem_domain_reference_normalization_is_idempotent() -> None:
	content = b"(define (problem p01) (:domain tiny) (:init) (:goal (and)))\n"

	normalized, changed = _normalize_problem_domain_reference(
		content,
		expected_domain_name="tiny",
	)

	assert normalized == content
	assert changed is False


def test_problem_domain_reference_normalization_fails_closed() -> None:
	with pytest.raises(ValueError, match="exactly one"):
		_normalize_problem_domain_reference(
			b"(define (problem p01) (:init) (:goal (and)))\n",
			expected_domain_name="tiny",
		)
