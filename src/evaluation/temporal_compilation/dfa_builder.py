"""
Deterministic automaton compilation for evaluation temporal queries.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict

from .ltlf_to_dfa import LTLfToDFA


class DFABuilder:
	"""Compile one validated LTLf formula into a renderer-facing DFA payload."""

	def __init__(self) -> None:
		self.converter = LTLfToDFA()

	def build(self, grounding_result: Any) -> Dict[str, Any]:
		total_start = time.perf_counter()
		formula_str = self._normalise_formula_string(self._formula_string(grounding_result))
		if not formula_str:
			raise ValueError("Temporal grounding result contains no LTLf formula.")

		convert_start = time.perf_counter()
		dfa_dot, metadata = self.converter.convert(formula_str)
		convert_seconds = time.perf_counter() - convert_start

		return {
			"formula": formula_str,
			"dfa_dot": dfa_dot,
			"dfa_path": "dfa.dot",
			"construction": metadata.get("construction") or "generic_ltlf2dfa",
			"num_states": int(metadata.get("num_states") or self._count_states(dfa_dot)),
			"num_transitions": int(
				metadata.get("num_transitions") or self._count_transitions(dfa_dot)
			),
			"alphabet": list(metadata.get("alphabet") or ()),
			"initial_state": metadata.get("initial_state"),
			"accepting_states": list(metadata.get("accepting_states") or ()),
			"free_variables": list(metadata.get("free_variables") or ()),
			"guarded_transitions": [
				dict(item)
				for item in (metadata.get("guarded_transitions") or ())
				if isinstance(item, dict)
			],
			"timing_profile": {
				"convert_seconds": convert_seconds,
				"total_seconds": time.perf_counter() - total_start,
			},
		}

	@staticmethod
	def _formula_string(grounding_result: Any) -> str:
		if isinstance(grounding_result, str):
			return grounding_result.strip()
		if hasattr(grounding_result, "ltlf_formula"):
			return str(getattr(grounding_result, "ltlf_formula") or "").strip()
		if hasattr(grounding_result, "combined_formula_string"):
			return str(grounding_result.combined_formula_string()).strip()
		formulas = list(getattr(grounding_result, "formulas", ()) or ())
		if not formulas:
			return ""
		if len(formulas) == 1:
			return str(formulas[0].to_string()).strip()
		return " & ".join(f"({formula.to_string()})" for formula in formulas)

	@staticmethod
	def _normalise_formula_string(formula_str: str) -> str:
		text = re.sub(r"\s+", " ", str(formula_str or "").strip())
		if not text:
			return ""
		depth = 0
		for character in text:
			if character == "(":
				depth += 1
			elif character == ")":
				depth -= 1
				if depth < 0:
					raise ValueError("LTLf formula has unbalanced parentheses.")
		if depth != 0:
			raise ValueError("LTLf formula has unbalanced parentheses.")
		return text

	@staticmethod
	def _count_states(dfa_dot: str) -> int:
		states = set()
		for line in str(dfa_dot or "").splitlines():
			grouped_match = re.search(r"node\s+\[.*?];\s*([^;]+);", line)
			if grouped_match:
				tokens = re.findall(r"[A-Za-z0-9_]+", grouped_match.group(1))
				states.update(token for token in tokens if token != "init")
				continue
			single_match = re.search(r"([A-Za-z0-9_]+)\s*\[\s*shape\s*=\s*", line)
			if single_match:
				token = single_match.group(1)
				if token != "init":
					states.add(token)
		return len(states)

	@staticmethod
	def _count_transitions(dfa_dot: str) -> int:
		transition_count = 0
		for line in str(dfa_dot or "").splitlines():
			if "->" not in line:
				continue
			total_edges = line.count("->")
			init_edges = len(re.findall(r"init\s*->", line))
			transition_count += max(0, total_edges - init_edges)
		return transition_count


def build_dfa_from_ltlf(grounding_result: Any) -> Dict[str, Any]:
	"""Compatibility wrapper for code paths that expect a module-level builder function."""
	return DFABuilder().build(grounding_result)
