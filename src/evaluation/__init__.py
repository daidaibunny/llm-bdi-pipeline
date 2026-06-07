"""Evaluation support exports."""

from __future__ import annotations

from typing import Any

__all__ = [
	"DFABuilder",
	"LTLfToDFA",
	"build_dfa_from_ltlf",
]


def __getattr__(name: str) -> Any:
	if name in {
		"DFABuilder",
		"LTLfToDFA",
		"build_dfa_from_ltlf",
	}:
		from .temporal_compilation import (
			DFABuilder,
			LTLfToDFA,
			build_dfa_from_ltlf,
		)

		return {
			"DFABuilder": DFABuilder,
			"LTLfToDFA": LTLfToDFA,
			"build_dfa_from_ltlf": build_dfa_from_ltlf,
		}[name]
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
