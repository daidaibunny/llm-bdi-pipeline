"""Shared semantics for ordinary achievement and temporally extended queries."""

from __future__ import annotations

import re
from enum import Enum


_PDDL_ATOM_APPLICATION_RE = re.compile(
	r"\b[a-z][A-Za-z0-9_-]*\s*\([^()]*\)",
)
_TEMPORAL_OPERATOR_RE = re.compile(r"(?<![A-Za-z0-9_])(F|X|U)(?![A-Za-z0-9_])")


class LTLfQueryKind(str, Enum):
	"""Semantic query classes exposed by the unified LTLf input contract."""

	ACHIEVEMENT = "achievement_goal"
	TEMPORALLY_EXTENDED = "temporal_extended_goal"


def classify_ltlf_query(formula: str) -> LTLfQueryKind:
	"""Classify an LTLf formula by whether it contains a temporal operator.

	Predicate applications are removed before scanning so a parameter named ``X``
	is not confused with the strong-next operator.
	"""

	text = str(formula or "").strip()
	if not text:
		raise ValueError("LTLf query formula must be non-empty.")
	operator_surface = _PDDL_ATOM_APPLICATION_RE.sub("atom", text)
	if _TEMPORAL_OPERATOR_RE.search(operator_surface):
		return LTLfQueryKind.TEMPORALLY_EXTENDED
	return LTLfQueryKind.ACHIEVEMENT


def execution_ltlf_formula(formula: str) -> str:
	"""Return the formula consumed by the common LTLf2DFA/MONA execution path.

	An atemporal formula is an ordinary achievement condition. Its completion
	semantics is embedded canonically as ``F(formula)``; a formula that already
	contains a temporal operator is preserved exactly.
	"""

	text = str(formula or "").strip()
	kind = classify_ltlf_query(text)
	if kind == LTLfQueryKind.ACHIEVEMENT:
		return f"F({text})"
	return text
