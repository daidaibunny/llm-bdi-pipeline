"""
Parser for lifted LTLf query JSON produced by the external Input component.

This module intentionally performs local file I/O and schema validation only.
It does not call a language model.

Paper correspondence: Section 5 receives a typed, externally bound parametric
LTLf specification. Parameters are instantiated per invocation rather than
quantified or exhaustively grounded before automaton construction.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from temporal_specification.query_semantics import LTLfQueryKind
from temporal_specification.query_semantics import classify_ltlf_query


@dataclass(frozen=True)
class LTLfAtomSpec:
	"""One predicate atom declared in a lifted LTLf goal case."""

	symbol: str
	predicate: str
	args: tuple[str, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"symbol": self.symbol,
			"predicate": self.predicate,
			"args": list(self.args),
		}


@dataclass(frozen=True)
class LiftedLTLfGoalCase:
	"""One ordinary achievement or temporally extended lifted query case."""

	query_id: str
	goal_name: str
	problem_file: str
	source_text: str
	ltlf_formula: str
	atoms: tuple[LTLfAtomSpec, ...]
	bindings: Mapping[str, str]
	atom_vocabulary: str = "pddl_fluents"
	status: str = "supported"

	def to_dict(self) -> dict[str, object]:
		return {
			"query_id": self.query_id,
			"goal_name": self.goal_name,
			"problem_file": self.problem_file,
			"source_text": self.source_text,
			"ltlf_formula": self.ltlf_formula,
			"atoms": [atom.to_dict() for atom in self.atoms],
			"bindings": dict(self.bindings),
			"atom_vocabulary": self.atom_vocabulary,
			"status": self.status,
		}


@dataclass(frozen=True)
class LiftedLTLfGoalDataset:
	"""Validated lifted LTLf query dataset."""

	schema_version: int
	goal_specification_kind: str
	temporal_logic: str
	domain: str
	cases: tuple[LiftedLTLfGoalCase, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"schema_version": self.schema_version,
			"goal_specification_kind": self.goal_specification_kind,
			"temporal_logic": self.temporal_logic,
			"domain": self.domain,
			"cases": {case.query_id: case.to_dict() for case in self.cases},
		}


def load_lifted_ltlf_goal_dataset(path: str | Path) -> LiftedLTLfGoalDataset:
	"""Load and validate a lifted LTLf query dataset from disk."""

	payload = json.loads(Path(path).read_text(encoding="utf-8"))
	return parse_lifted_ltlf_goal_dataset(payload)


def parse_lifted_ltlf_goal_dataset(payload: Mapping[str, Any]) -> LiftedLTLfGoalDataset:
	"""Validate and parse the external Input module's lifted LTLf query JSON."""

	if not isinstance(payload, Mapping):
		raise ValueError("Lifted LTLf query dataset must be a JSON object.")
	schema_version = int(payload.get("schema_version") or 0)
	if schema_version != 1:
		raise ValueError("schema_version must be 1.")
	goal_specification_kind = str(payload.get("goal_specification_kind") or "").strip()
	try:
		declared_query_kind = LTLfQueryKind(goal_specification_kind)
	except ValueError as error:
		raise ValueError(
			"goal_specification_kind must be achievement_goal or "
			"temporal_extended_goal.",
		) from error
	temporal_logic = str(payload.get("temporal_logic") or "").strip()
	if temporal_logic != "LTLf":
		raise ValueError("temporal_logic must be LTLf.")
	domain = str(payload.get("domain") or "").strip()
	if not domain:
		raise ValueError("domain must be non-empty.")
	raw_cases = payload.get("cases")
	if not isinstance(raw_cases, Mapping):
		raise ValueError("cases must be a JSON object.")
	cases = tuple(
		_parse_case(query_id, case_payload)
		for query_id, case_payload in sorted(raw_cases.items())
	)
	for case in cases:
		actual_query_kind = classify_ltlf_query(case.ltlf_formula)
		if actual_query_kind != declared_query_kind:
			if declared_query_kind == LTLfQueryKind.ACHIEVEMENT:
				raise ValueError(
					"achievement_goal cases must not contain temporal operators.",
				)
			raise ValueError(
				"temporal_extended_goal cases must contain at least one temporal operator.",
			)
	return LiftedLTLfGoalDataset(
		schema_version=schema_version,
		goal_specification_kind=goal_specification_kind,
		temporal_logic=temporal_logic,
		domain=domain,
		cases=cases,
	)


def _parse_case(query_id: object, payload: object) -> LiftedLTLfGoalCase:
	query_id_text = str(query_id or "").strip()
	if not query_id_text:
		raise ValueError("case id must be non-empty.")
	if not isinstance(payload, Mapping):
		raise ValueError(f"case {query_id_text} must be a JSON object.")
	ltlf_formula = str(payload.get("ltlf_formula") or "").strip()
	if not ltlf_formula:
		raise ValueError(f"{query_id_text} is missing ltlf_formula.")
	goal_name = str(payload.get("goal_name") or f"g_{query_id_text}").strip()
	if not _ASL_GOAL_NAME_RE.fullmatch(goal_name):
		raise ValueError(f"{query_id_text} has invalid goal_name {goal_name!r}.")
	return LiftedLTLfGoalCase(
		query_id=query_id_text,
		goal_name=goal_name,
		problem_file=str(payload.get("problem_file") or "").strip(),
		source_text=str(payload.get("source_text") or payload.get("query_text") or "").strip(),
		ltlf_formula=ltlf_formula,
		atoms=_parse_atoms(payload.get("atoms") or ()),
		bindings={
			str(key).strip(): str(value).strip()
			for key, value in dict(payload.get("bindings") or {}).items()
			if str(key).strip() and str(value).strip()
		},
		atom_vocabulary=str(payload.get("atom_vocabulary") or "pddl_fluents").strip(),
		status=str(payload.get("status") or "supported").strip(),
	)


def _parse_atoms(raw_atoms: object) -> tuple[LTLfAtomSpec, ...]:
	if not isinstance(raw_atoms, Sequence) or isinstance(raw_atoms, (str, bytes)):
		raise ValueError("atoms must be a JSON list.")
	atoms: list[LTLfAtomSpec] = []
	for index, raw_atom in enumerate(raw_atoms, start=1):
		if isinstance(raw_atom, str):
			atoms.append(_parse_atom_string(raw_atom))
			continue
		if not isinstance(raw_atom, Mapping):
			raise ValueError(f"atom #{index} must be a string or JSON object.")
		predicate = str(raw_atom.get("predicate") or "").strip()
		args = tuple(str(arg).strip() for arg in tuple(raw_atom.get("args") or ()) if str(arg).strip())
		symbol = str(raw_atom.get("symbol") or _symbol_for(predicate, args)).strip()
		if not predicate:
			raise ValueError(f"atom #{index} is missing predicate.")
		atoms.append(LTLfAtomSpec(symbol=symbol, predicate=predicate, args=args))
	return tuple(atoms)


def _parse_atom_string(atom: str) -> LTLfAtomSpec:
	text = str(atom or "").strip()
	if "(" not in text:
		return LTLfAtomSpec(symbol=text, predicate=text, args=())
	if not text.endswith(")"):
		raise ValueError(f"Invalid atom string {atom!r}.")
	predicate, raw_args = text.split("(", 1)
	args = tuple(arg.strip() for arg in raw_args[:-1].split(",") if arg.strip())
	return LTLfAtomSpec(
		symbol=_symbol_for(predicate.strip(), args),
		predicate=predicate.strip(),
		args=args,
	)


def _symbol_for(predicate: str, args: Sequence[str]) -> str:
	items = [predicate, *tuple(args or ())]
	return "_".join(str(item).strip() for item in items if str(item).strip())


_ASL_GOAL_NAME_RE = re.compile(r"[a-z][A-Za-z0-9_]*")
