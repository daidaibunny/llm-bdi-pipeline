"""Native command and compatibility contracts for external planning references."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
import re
from typing import Any
from typing import Mapping
from typing import Sequence

from utils.pddl_parser import PDDLParser


_FOND4LTLF_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*$")
_FORMULA_ATOM = re.compile(r"\ba\d+\b")
_PLAN_ACTION = re.compile(r"^\(\s*([^\s()]+)(?:\s|\))", flags=re.IGNORECASE)
_COMPILATION_ACTION = re.compile(r"^trans-\d+$", flags=re.IGNORECASE)
_REQUIREMENTS = re.compile(
	r"\(\s*:requirements(?P<body>[^)]*)\)",
	flags=re.IGNORECASE,
)
_ADL_REQUIREMENTS = {
	":negative-preconditions",
	":disjunctive-preconditions",
	":existential-preconditions",
	":universal-preconditions",
	":quantified-preconditions",
	":conditional-effects",
}
_FOND4LTLF_REQUIREMENTS = {
	":strips",
	":typing",
	":equality",
	":adl",
	":non-deterministic",
}
_NUMERIC_REQUIREMENTS = {
	":numeric-fluents",
	":fluents",
	":action-costs",
}


class ExternalReferenceMethod(str, Enum):
	"""Registered native task-level references with short paper names."""

	RAW_MOOSE = "raw_moose"
	LAMA = "lama"
	ENHSP_HMRPHJ = "enhsp_hmrphj"
	FOND4LTLF_LAMA = "fond4ltlf_lama"

	@property
	def display_name(self) -> str:
		"""Return the concise method title used in paper tables and progress logs."""

		return {
			ExternalReferenceMethod.RAW_MOOSE: "Raw MOOSE",
			ExternalReferenceMethod.LAMA: "LAMA",
			ExternalReferenceMethod.ENHSP_HMRPHJ: "MRP+HJ",
			ExternalReferenceMethod.FOND4LTLF_LAMA: "FOND4LTLf + LAMA",
		}[self]


def reference_methods_for_domain(
	domain_file: str | Path,
) -> tuple[ExternalReferenceMethod, ...]:
	"""Select achievement references from PDDL features, never a domain name."""

	domain = PDDLParser.parse_domain(domain_file)
	per_instance = (
		ExternalReferenceMethod.ENHSP_HMRPHJ
		if tuple(domain.functions)
		else ExternalReferenceMethod.LAMA
	)
	return ExternalReferenceMethod.RAW_MOOSE, per_instance


def build_enhsp_command(
	*,
	jar_file: str | Path,
	domain_file: str | Path,
	problem_file: str | Path,
	plan_file: str | Path,
) -> tuple[str, ...]:
	"""Build the exact ENHSP MRP+HJ command used by the MOOSE evaluation."""

	return (
		"java",
		"-jar",
		str(jar_file),
		"-o",
		str(domain_file),
		"-f",
		str(problem_file),
		"-sp",
		str(plan_file),
		"-planner",
		"sat-hmrphj",
	)


def build_fond4ltlf_command(
	*,
	executable: str | Path,
	domain_file: str | Path,
	problem_file: str | Path,
	formula: str,
	output_domain_file: str | Path,
	output_problem_file: str | Path,
) -> tuple[str, ...]:
	"""Build the official FOND4LTLf 0.0.4 compilation command."""

	return (
		str(executable),
		"-d",
		str(domain_file),
		"-p",
		str(problem_file),
		"-g",
		str(formula),
		"-outd",
		str(output_domain_file),
		"-outp",
		str(output_problem_file),
	)


def build_ground_fond4ltlf_formula(case: Mapping[str, Any]) -> str:
	"""Ground one validated parametric formula using FOND4LTLf's atom convention."""

	bindings_raw = case.get("bindings")
	if not isinstance(bindings_raw, Mapping):
		raise ValueError("FOND4LTLf reference requires an explicit invocation binding.")
	bindings = {str(key): str(value).lower() for key, value in bindings_raw.items()}
	atoms_raw = case.get("atoms")
	if not isinstance(atoms_raw, Sequence) or isinstance(atoms_raw, (str, bytes)):
		raise ValueError("FOND4LTLf reference requires an atom table.")
	symbols: dict[str, str] = {}
	for index, raw_atom in enumerate(atoms_raw):
		if not isinstance(raw_atom, Mapping):
			raise ValueError(f"FOND4LTLf atom {index} is not an object.")
		kind = str(raw_atom.get("kind") or "predicate")
		if kind != "predicate":
			raise ValueError(
				"FOND4LTLf 0.0.4 reference does not support numeric equality atoms.",
			)
		symbol = str(raw_atom.get("symbol") or "").strip()
		predicate = str(raw_atom.get("predicate") or "").strip().lower()
		arguments_raw = raw_atom.get("args")
		if not isinstance(arguments_raw, Sequence) or isinstance(
			arguments_raw,
			(str, bytes),
		):
			raise ValueError(f"FOND4LTLf atom {symbol or index} has no argument array.")
		arguments = tuple(
			bindings.get(str(argument), str(argument).lower())
			for argument in arguments_raw
		)
		for identifier in (predicate, *arguments):
			if not _FOND4LTLF_IDENTIFIER.fullmatch(identifier):
				raise ValueError(
					"FOND4LTLf underscore encoding requires each predicate and object "
					f"identifier to match [a-z][a-z0-9]*: {identifier!r}.",
				)
		if not symbol or symbol in symbols:
			raise ValueError(f"FOND4LTLf atom symbol is missing or duplicated: {symbol!r}.")
		symbols[symbol] = "_".join((predicate, *arguments))

	formula = str(case.get("ltlf_formula") or "").strip()
	if not formula:
		raise ValueError("FOND4LTLf reference requires a non-empty LTLf formula.")

	def replace(match: re.Match[str]) -> str:
		symbol = match.group(0)
		if symbol not in symbols:
			raise ValueError(f"LTLf formula references unknown atom {symbol!r}.")
		return symbols[symbol]

	grounded = _FORMULA_ATOM.sub(replace, formula)
	if _FORMULA_ATOM.search(grounded):
		raise ValueError("LTLf formula grounding left unresolved atom symbols.")
	return grounded


def normalize_fond4ltlf_domain(domain_text: str) -> str:
	"""Normalize only PDDL declarations unsupported by FOND4LTLf's own parser."""

	normalized = str(domain_text).lower()
	code = re.sub(
		r";[^\r\n]*",
		lambda match: " " * len(match.group(0)),
		normalized,
	)
	if re.search(r"\(\s*:functions\b", code) or re.search(
		r"\(\s*(?:increase|decrease|assign|scale-up|scale-down)\b",
		code,
	):
		raise ValueError("FOND4LTLf 0.0.4 reference does not support numeric PDDL.")
	match = _REQUIREMENTS.search(code)
	if match is None:
		return normalized
	requirements = tuple(
		token.lower()
		for token in re.findall(r":[a-z][a-z0-9-]*", match.group("body"), flags=re.IGNORECASE)
	)
	if set(requirements) & _NUMERIC_REQUIREMENTS:
		raise ValueError("FOND4LTLf 0.0.4 reference does not support numeric PDDL.")
	unsupported = set(requirements) - (
		_FOND4LTLF_REQUIREMENTS | _ADL_REQUIREMENTS | _NUMERIC_REQUIREMENTS
	)
	if unsupported:
		raise ValueError(
			"FOND4LTLf 0.0.4 parser does not support PDDL requirements: "
			+ ", ".join(sorted(unsupported)),
		)
	output_requirements: list[str] = []
	for requirement in requirements:
		if requirement in _ADL_REQUIREMENTS:
			continue
		if requirement not in output_requirements:
			output_requirements.append(requirement)
	if set(requirements) & _ADL_REQUIREMENTS and ":adl" not in output_requirements:
		output_requirements.append(":adl")
	replacement = "(:requirements " + " ".join(output_requirements) + ")"
	return normalized[: match.start()] + replacement + normalized[match.end() :]


def filter_compilation_actions(
	compiled_plan: str,
	*,
	original_action_names: set[str] | frozenset[str],
) -> tuple[str, ...]:
	"""Remove only FOND4LTLf DFA-update actions from a solved compiled plan."""

	original = {str(name).lower() for name in original_action_names}
	result: list[str] = []
	for raw_line in str(compiled_plan).splitlines():
		line = raw_line.strip()
		if not line or line.startswith(";"):
			continue
		match = _PLAN_ACTION.match(line)
		if match is None:
			raise ValueError(f"Malformed planner action line: {line!r}.")
		action_name = match.group(1).lower()
		if action_name in original:
			result.append(line)
			continue
		if _COMPILATION_ACTION.fullmatch(action_name):
			continue
		raise ValueError(f"Compiled plan contains unknown action {action_name!r}.")
	return tuple(result)
