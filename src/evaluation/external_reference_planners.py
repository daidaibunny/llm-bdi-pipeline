"""Native command and compatibility contracts for external planning references."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
import re
from typing import Any
from typing import Mapping
from typing import Sequence

from lark.exceptions import LarkError
from ltlf2dfa.ltlf import LTLfAnd
from ltlf2dfa.ltlf import LTLfAtomic
from ltlf2dfa.ltlf import LTLfEventually
from ltlf2dfa.ltlf import LTLfFormula
from ltlf2dfa.ltlf import LTLfNext
from ltlf2dfa.ltlf import LTLfNot
from ltlf2dfa.ltlf import LTLfUntil
from ltlf2dfa.parser.ltlf import LTLfParser

from utils.pddl_parser import PDDLParser


_FOND4LTLF_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*$")
_PDDL_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]*$", flags=re.IGNORECASE)
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
_REMOVABLE_DECLARATIVE_REQUIREMENTS = {":action-costs"}


class ExternalReferenceMethod(str, Enum):
	"""Registered native task-level references with short paper names."""

	RAW_MOOSE = "raw_moose"
	LAMA = "lama"
	ENHSP_HMRPHJ = "enhsp_hmrphj"
	FOND4LTLF_LAMA = "fond4ltlf_lama"
	TIDE_LAMA = "tide_lama"

	@property
	def display_name(self) -> str:
		"""Return the concise method title used in paper tables and progress logs."""

		return {
			ExternalReferenceMethod.RAW_MOOSE: "Raw MOOSE",
			ExternalReferenceMethod.LAMA: "LAMA",
			ExternalReferenceMethod.ENHSP_HMRPHJ: "MRP+HJ",
			ExternalReferenceMethod.FOND4LTLF_LAMA: "FOND4LTLf + LAMA",
			ExternalReferenceMethod.TIDE_LAMA: "TIDE + LAMA",
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


def build_tide_command(
	*,
	executable: str | Path,
	domain_file: str | Path,
	problem_file: str | Path,
	subproblem_timeout_ms: int = 60_000,
) -> tuple[str, ...]:
	"""Build the official TIDE feedback, heuristic, cache, and LAMA command."""

	if subproblem_timeout_ms <= 0:
		raise ValueError("TIDE subproblem timeout must be positive.")
	return (
		str(executable),
		str(domain_file),
		str(problem_file),
		"1",
		"-f",
		"-h",
		"-c",
		"--planner",
		"fd",
		"--search",
		"lama-first",
		"--timeout",
		str(int(subproblem_timeout_ms)),
	)


def build_tide_pddl_goal(
	*,
	ltlf_formula: str,
	atoms: Sequence[Mapping[str, Any]],
	bindings: Mapping[str, Any],
) -> str:
	"""Render the persisted bound LTLf query as TIDE temporal PDDL syntax."""

	bound_values = {str(key): str(value) for key, value in bindings.items()}
	atom_expressions: dict[str, str] = {}
	for index, atom in enumerate(atoms):
		atom_id = str(atom.get("atom_id") or atom.get("symbol") or "").strip()
		kind = str(atom.get("kind") or "predicate").strip()
		if not atom_id or atom_id in atom_expressions:
			raise ValueError(f"TIDE atom {index} has a missing or duplicate identifier.")
		if kind != "predicate":
			raise ValueError("TIDE does not support numeric equality temporal atoms.")
		predicate = str(atom.get("predicate") or "").strip()
		arguments_raw = atom.get("arguments", atom.get("args"))
		if not predicate or not isinstance(arguments_raw, Sequence) or isinstance(
			arguments_raw,
			(str, bytes),
		):
			raise ValueError(f"TIDE atom {atom_id!r} is malformed.")
		arguments: list[str] = []
		for raw_argument in arguments_raw:
			argument = str(raw_argument)
			grounded = bound_values.get(argument, argument)
			if not _PDDL_IDENTIFIER.fullmatch(grounded):
				raise ValueError(
					f"TIDE atom {atom_id!r} has invalid PDDL object {grounded!r}.",
				)
			arguments.append(grounded)
		if not _PDDL_IDENTIFIER.fullmatch(predicate):
			raise ValueError(
				f"TIDE atom {atom_id!r} has invalid predicate {predicate!r}.",
			)
		atom_expressions[atom_id] = "(" + " ".join((predicate, *arguments)) + ")"

	formula_text = str(ltlf_formula).strip()
	if not formula_text:
		raise ValueError("TIDE requires a non-empty LTLf formula.")
	try:
		formula = LTLfParser()(formula_text)
	except (LarkError, ValueError) as error:
		raise ValueError(f"TIDE could not parse the persisted LTLf formula: {error}") from error

	def render(node: LTLfFormula) -> str:
		if isinstance(node, LTLfAtomic):
			atom_id = str(node.s).strip()
			if atom_id not in atom_expressions:
				raise ValueError(f"TIDE formula references unknown atom {atom_id!r}.")
			return atom_expressions[atom_id]
		if isinstance(node, LTLfNot):
			if not isinstance(node.f, LTLfAtomic):
				raise ValueError("TIDE adapter supports negation on literals only.")
			return f"(not {render(node.f)})"
		if isinstance(node, LTLfNext):
			return f"(next {render(node.f)})"
		if isinstance(node, LTLfEventually):
			return f"(eventually {render(node.f)})"
		if isinstance(node, LTLfAnd):
			rendered = tuple(render(operand) for operand in node.formulas)
			if not rendered:
				raise ValueError("TIDE conjunction must not be empty.")
			return "(and " + " ".join(rendered) + ")"
		if isinstance(node, LTLfUntil):
			if len(node.formulas) != 2:
				raise ValueError("TIDE strong-until requires exactly two operands.")
			left, right = (render(operand) for operand in node.formulas)
			return f"(until {left} {right})"
		raise ValueError(
			"TIDE adapter does not support formula operator "
			f"{type(node).__name__!r}.",
		)

	return render(formula)


def ensure_tide_domain_compatible(domain_text: str) -> None:
	"""Reject PDDL constructs outside the official deterministic TIDE runtime."""

	code = _mask_pddl_comments(str(domain_text)).lower()
	functions_start = re.search(r"\(\s*:functions\b", code)
	if functions_start is not None:
		functions_end = _matching_parenthesis(code, functions_start.start())
		functions_block = code[functions_start.start() : functions_end + 1]
		function_names = {
			match.group(1)
			for match in re.finditer(r"\(\s*([a-z][a-z0-9_-]*)\b", functions_block)
		}
		if function_names - {"total-cost"}:
			raise ValueError(
				"TIDE with Fast Downward does not support resource numeric PDDL.",
			)
	if re.search(r"\(\s*:durative-action\b", code):
		raise ValueError("TIDE reference supports instantaneous PDDL actions only.")
	if re.search(r"\(\s*(?:oneof|probabilistic)\b", code):
		raise ValueError("TIDE reference supports deterministic PDDL effects only.")


def rewrite_pddl_problem_goal(problem_text: str, temporal_goal: str) -> str:
	"""Replace exactly one PDDL goal block with a rendered TIDE temporal goal."""

	goal = str(temporal_goal).strip()
	if not goal.startswith("(") or not goal.endswith(")"):
		raise ValueError("TIDE temporal goal must be one PDDL expression.")
	text = str(problem_text)
	code = _mask_pddl_comments(text)
	matches = tuple(re.finditer(r"\(\s*:goal\b", code, flags=re.IGNORECASE))
	if len(matches) != 1:
		raise ValueError(f"Expected exactly one PDDL :goal block; found {len(matches)}.")
	start = matches[0].start()
	end = _matching_parenthesis(code, start)
	return text[:start] + f"(:goal {goal})" + text[end + 1 :]


def extract_tide_plan_actions(plan_artifact: str) -> tuple[str, ...]:
	"""Extract primitive PDDL actions from TIDE's plan section only."""

	lines = str(plan_artifact).splitlines()
	try:
		plan_start = next(
			index for index, line in enumerate(lines) if line.strip().lower() == "plan:"
		)
	except StopIteration as error:
		raise ValueError("TIDE plan artifact has no Plan section.") from error
	result: list[str] = []
	for raw_line in lines[plan_start + 1 :]:
		line = raw_line.strip()
		if line.lower() == "dfa path:":
			break
		if not line:
			continue
		if _PLAN_ACTION.match(line) is None or not line.endswith(")"):
			raise ValueError(f"Malformed TIDE plan action: {line!r}.")
		result.append(line)
	else:
		raise ValueError("TIDE plan artifact has no DFA Path boundary.")
	return tuple(result)


def parse_tide_statistics(statistics_text: str) -> dict[str, float]:
	"""Parse the official TIDE single-problem statistics artifact."""

	patterns = {
		"average_dfa_seconds": r"Average DFA construction time:\s*([0-9.eE+-]+)",
		"average_search_seconds": r"Average search time:\s*([0-9.eE+-]+)",
		"average_total_seconds": r"Average total time:\s*([0-9.eE+-]+)",
		"average_expanded_nodes": r"Average number of expanded nodes:\s*([0-9.eE+-]+)",
		"average_plan_length": r"Average plan length:\s*([0-9.eE+-]+)",
		"average_backtracks": r"Average number of backtracks:\s*([0-9.eE+-]+)",
	}
	result: dict[str, float] = {}
	for field, pattern in patterns.items():
		match = re.search(pattern, str(statistics_text), flags=re.IGNORECASE)
		if match is None:
			raise ValueError(f"TIDE statistics are missing {field}.")
		result[field] = float(match.group(1))
	return result


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
	if set(requirements) & (
		_NUMERIC_REQUIREMENTS - _REMOVABLE_DECLARATIVE_REQUIREMENTS
	):
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
		if requirement in _ADL_REQUIREMENTS | _REMOVABLE_DECLARATIVE_REQUIREMENTS:
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


def _mask_pddl_comments(text: str) -> str:
	return re.sub(
		r";[^\r\n]*",
		lambda match: " " * len(match.group(0)),
		str(text),
	)


def _matching_parenthesis(text: str, start: int) -> int:
	depth = 0
	for index in range(start, len(text)):
		if text[index] == "(":
			depth += 1
		elif text[index] == ")":
			depth -= 1
			if depth == 0:
				return index
	raise ValueError("Unbalanced PDDL expression.")
