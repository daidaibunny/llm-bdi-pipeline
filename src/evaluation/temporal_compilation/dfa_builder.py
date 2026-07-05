"""
Deterministic automaton compilation for evaluation temporal queries.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Sequence, Tuple

from .ltlf_to_dfa import LTLfToDFA
from utils.symbol_normalizer import SymbolNormalizer


class DFABuilder:
	"""Compile one validated LTLf formula into a renderer-facing DFA payload."""

	def __init__(self) -> None:
		self.converter = LTLfToDFA()

	def build(self, grounding_result: Any) -> Dict[str, Any]:
		total_start = time.perf_counter()
		formula_str = self._normalise_formula_string(self._formula_string(grounding_result))
		if not formula_str:
			raise ValueError("Temporal grounding result contains no LTLf formula.")

		ordered_atoms = self._parse_nested_eventually_next_sequence(formula_str)
		if ordered_atoms:
			return self._build_ordered_sequence_payload(
				formula_str=formula_str,
				ordered_atoms=ordered_atoms,
				total_start=total_start,
			)

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
		characters: list[str] = []
		open_parentheses = 0
		for character in text:
			if character == "(":
				open_parentheses += 1
				characters.append(character)
				continue
			if character == ")":
				if open_parentheses <= 0:
					continue
				open_parentheses -= 1
				characters.append(character)
				continue
			characters.append(character)
		if open_parentheses > 0:
			characters.extend(")" for _ in range(open_parentheses))
		return "".join(characters).strip()

	@classmethod
	def _parse_nested_eventually_next_sequence(cls, formula_str: str) -> Tuple[str, ...]:
		"""Parse F(a & X(F(b ...))) formulas into singleton progress atoms."""

		def parse_eventually(text: str) -> Tuple[str, ...]:
			current = text.strip()
			if not current.startswith("F(") or not current.endswith(")"):
				return ()
			inner = current[2:-1].strip()
			parts = cls._split_top_level_conjunction(inner)
			if len(parts) == 1:
				atom = parts[0].strip()
				return (atom,) if cls._is_singleton_atom_text(atom) else ()
			if len(parts) != 2:
				return ()
			first_atom, next_formula = parts[0].strip(), parts[1].strip()
			if not cls._is_singleton_atom_text(first_atom):
				return ()
			if not next_formula.startswith("X(") or not next_formula.endswith(")"):
				return ()
			tail = parse_eventually(next_formula[2:-1].strip())
			return (first_atom, *tail) if tail else ()

		atoms = parse_eventually(str(formula_str or "").strip())
		return atoms if atoms and all(cls._is_singleton_atom_text(atom) for atom in atoms) else ()

	@staticmethod
	def _split_top_level_conjunction(text: str) -> Tuple[str, ...]:
		parts: list[str] = []
		start = 0
		depth = 0
		for index, character in enumerate(str(text or "")):
			if character == "(":
				depth += 1
				continue
			if character == ")":
				depth -= 1
				if depth < 0:
					return ()
				continue
			if character == "&" and depth == 0:
				part = text[start:index].strip()
				if not part:
					return ()
				parts.append(part)
				start = index + 1
		if depth != 0:
			return ()
		final_part = str(text or "")[start:].strip()
		if not final_part:
			return ()
		parts.append(final_part)
		return tuple(parts)

	@staticmethod
	def _is_singleton_atom_text(text: str) -> bool:
		return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*(?:\([^()]*\))?", str(text or "").strip()) is not None

	@classmethod
	def _build_ordered_sequence_payload(
		cls,
		*,
		formula_str: str,
		ordered_atoms: Sequence[str],
		total_start: float,
	) -> Dict[str, Any]:
		"""Build the exact linear DFA for nested eventually-next singleton atoms."""

		atoms = tuple(str(atom).strip() for atom in ordered_atoms if str(atom).strip())
		accepting_state = str(len(atoms) + 1)
		guarded_transitions: list[Dict[str, Any]] = []
		for index, atom in enumerate(atoms, start=1):
			source_state = str(index)
			target_state = str(index + 1)
			guarded_transitions.append(
				{
					"source_state": source_state,
					"target_state": source_state,
					"guards": ("0",),
					"raw_label": f"~{atom}",
				},
			)
			guarded_transitions.append(
				{
					"source_state": source_state,
					"target_state": target_state,
					"guards": ("1",),
					"raw_label": atom,
				},
			)
		guarded_transitions.append(
			{
				"source_state": accepting_state,
				"target_state": accepting_state,
				"guards": ("X",),
				"raw_label": "true",
			},
		)
		dfa_dot = cls._render_ordered_sequence_dot(
			accepting_state=accepting_state,
			guarded_transitions=tuple(guarded_transitions),
		)
		return {
			"formula": formula_str,
			"dfa_dot": dfa_dot,
			"dfa_path": "dfa.dot",
			"construction": "ordered_singleton_sequence_fast_path",
			"num_states": len(atoms) + 1,
			"num_transitions": len(guarded_transitions),
			"alphabet": list(atoms),
			"initial_state": "1",
			"accepting_states": [accepting_state],
			"free_variables": list(atoms),
			"guarded_transitions": guarded_transitions,
			"timing_profile": {
				"convert_seconds": 0.0,
				"total_seconds": time.perf_counter() - total_start,
			},
		}

	@staticmethod
	def _render_ordered_sequence_dot(
		*,
		accepting_state: str,
		guarded_transitions: Sequence[Dict[str, Any]],
	) -> str:
		lines = [
			"digraph ORDERED_SINGLETON_SEQUENCE_DFA {",
			" rankdir = LR;",
			" center = true;",
			" edge [fontname = Courier];",
			" node [height = .5, width = .5];",
			f" node [shape = doublecircle]; {accepting_state};",
			" node [shape = circle]; 1;",
			' init [shape = plaintext, label = ""];',
			" init -> 1;",
		]
		for transition in guarded_transitions:
			lines.append(
				" "
				+ str(transition["source_state"])
				+ " -> "
				+ str(transition["target_state"])
				+ f' [label="{transition["raw_label"]}"];',
			)
		lines.append("}")
		return "\n".join(lines)

	@classmethod
	def _normalise_ordered_sequence_formula_for_ltlf2dfa(cls, formula_str: str) -> str:
		normalizer = SymbolNormalizer()
		normalized_symbol_formula = normalizer.normalize_formula_string(formula_str)
		ordered_symbols = cls._parse_total_ordered_task_event_sequence(normalized_symbol_formula)
		if not ordered_symbols:
			return formula_str
		ordered_atoms = cls._extract_formula_atoms_in_order(formula_str)
		normalized_atoms = tuple(
			normalizer.normalize_formula_string(atom)
			for atom in ordered_atoms
		)
		if normalized_atoms != ordered_symbols:
			return formula_str
		return cls._build_until_chain_formula(ordered_atoms)

	@classmethod
	def _extract_formula_atoms_in_order(cls, formula_str: str) -> Tuple[str, ...]:
		ordered_atoms: list[str] = []
		text = str(formula_str or "")
		index = 0
		while index < len(text):
			if not (text[index].isalpha() or text[index] == "_"):
				index += 1
				continue
			start = index
			index += 1
			while index < len(text) and (text[index].isalnum() or text[index] == "_"):
				index += 1
			token = text[start:index]
			if token in {"F", "G", "X", "WX", "U", "R", "W", "M", "true", "false"}:
				continue
			if index < len(text) and text[index] == "(":
				depth = 1
				index += 1
				while index < len(text) and depth > 0:
					if text[index] == "(":
						depth += 1
					elif text[index] == ")":
						depth -= 1
					index += 1
				ordered_atoms.append(text[start:index].strip())
				continue
			ordered_atoms.append(token.strip())
		return tuple(atom for atom in ordered_atoms if atom)

	@staticmethod
	def _build_until_chain_formula(ordered_atoms: Sequence[str]) -> str:
		atoms = tuple(str(atom).strip() for atom in ordered_atoms if str(atom).strip())
		if not atoms:
			return ""
		if len(atoms) == 1:
			return f"F({atoms[0]})"
		parts = [f"F({atoms[-1]})"]
		for index in range(len(atoms) - 1):
			parts.append(f"((!{atoms[index + 1]}) U {atoms[index]})")
		return " & ".join(parts)

	@classmethod
	def _parse_total_ordered_task_event_sequence(cls, formula_str: str) -> Tuple[str, ...]:
		token_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[()&]")
		tokens = token_pattern.findall(str(formula_str or "").strip())
		if not tokens:
			return ()

		def is_atom(token: str) -> bool:
			return token not in {"F", "&", "(", ")"}

		position = 0
		ordered_symbols: List[str] = []
		pending_closure_counts: List[int] = []

		while True:
			if position >= len(tokens) or tokens[position] != "F":
				return ()
			position += 1

			open_parentheses = 0
			while position < len(tokens) and tokens[position] == "(":
				open_parentheses += 1
				position += 1
			if open_parentheses <= 0:
				return ()

			redundant_parentheses = 0
			while position < len(tokens) and tokens[position] == "(":
				redundant_parentheses += 1
				position += 1

			if position >= len(tokens) or not is_atom(tokens[position]):
				return ()
			ordered_symbols.append(tokens[position])
			position += 1

			for _ in range(redundant_parentheses):
				if position >= len(tokens) or tokens[position] != ")":
					return ()
				position += 1

			if position < len(tokens) and tokens[position] == "&":
				position += 1
				if position < len(tokens) and tokens[position] == "F":
					pending_closure_counts.append(open_parentheses)
					continue
				if position < len(tokens) and is_atom(tokens[position]):
					ordered_symbols.append(tokens[position])
					position += 1
					position = cls._consume_ordered_task_event_closures(
						tokens,
						position,
						open_parentheses,
					)
					while pending_closure_counts:
						position = cls._consume_ordered_task_event_closures(
							tokens,
							position,
							pending_closure_counts.pop(),
						)
					break
				return ()

			position = cls._consume_ordered_task_event_closures(
				tokens,
				position,
				open_parentheses,
			)
			while pending_closure_counts:
				position = cls._consume_ordered_task_event_closures(
					tokens,
					position,
					pending_closure_counts.pop(),
				)
			break

		if position != len(tokens):
			return ()
		return tuple(ordered_symbols)

	@staticmethod
	def _consume_ordered_task_event_closures(
		tokens: Sequence[str],
		position: int,
		closure_count: int,
	) -> int:
		for _ in range(closure_count):
			if position >= len(tokens) or tokens[position] != ")":
				return len(tokens) + 1
			position += 1
		return position

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
