"""Native command and compatibility contracts for external planning references."""

from __future__ import annotations

from dataclasses import dataclass
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
_TIDE_SYMBOL_PREFIX = "gp2pl"


type _PDDLSExpression = str | list["_PDDLSExpression"]


@dataclass(frozen=True)
class TidePDDLTask:
	"""One semantics-preserving PDDL task normalized for TIDE's AP parser."""

	domain_text: str
	problem_text: str
	temporal_goal: str


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


def normalize_tide_pddl_task(
	*,
	domain_text: str,
	problem_text: str,
	temporal_goal: str,
) -> TidePDDLTask:
	"""Normalize one supported PDDL task to TIDE's identifier and type contracts.

	TIDE serializes grounded propositions with ``_`` and reconstructs the
	predicate by scanning that string. Category-specific hexadecimal names keep
	that delimiter out of objects while giving every predicate one delimiter,
	which also makes zero-arity predicates decodable. The transformation is a
	bijective alpha-renaming; returned plans are decoded before validation.
	"""

	ensure_tide_domain_compatible(domain_text)
	domain = _parse_pddl_document(domain_text, label="domain")
	problem = _parse_pddl_document(problem_text, label="problem")
	goal = _parse_pddl_expression(temporal_goal, label="temporal goal")
	_replace_problem_goal(problem, goal)
	symbols = _tide_symbol_table(domain, problem)
	normalized_domain = _transform_tide_domain(domain, symbols)
	normalized_problem = _transform_tide_problem(problem, symbols)
	normalized_goal = _transform_tide_expression(
		goal,
		symbols,
		temporal_context=True,
	)
	return TidePDDLTask(
		domain_text=_render_pddl_document(normalized_domain),
		problem_text=_render_pddl_document(normalized_problem),
		temporal_goal=_render_pddl_expression(normalized_goal),
	)


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


def extract_tide_plan_actions(
	plan_artifact: str,
	*,
	decode_normalized_symbols: bool = False,
) -> tuple[str, ...]:
	"""Extract primitive PDDL actions from TIDE's plan section only."""

	lines = str(plan_artifact).splitlines()
	try:
		plan_start = next(
			index for index, line in enumerate(lines) if line.strip().lower() == "plan:"
		)
	except StopIteration as error:
		raise ValueError("TIDE plan output has no Plan section.") from error
	result: list[str] = []
	for raw_line in lines[plan_start + 1 :]:
		line = raw_line.strip()
		if line.lower() == "dfa path:":
			break
		if not line:
			continue
		if _PLAN_ACTION.match(line) is None or not line.endswith(")"):
			raise ValueError(f"Malformed TIDE plan action: {line!r}.")
		result.append(
			_decode_tide_plan_action(line) if decode_normalized_symbols else line,
		)
	else:
		raise ValueError("TIDE plan output has no DFA Path boundary.")
	return tuple(result)


@dataclass(frozen=True)
class _TideSymbolTable:
	types: frozenset[str]
	predicates: frozenset[str]
	functions: frozenset[str]
	objects: frozenset[str]


def _parse_pddl_document(text: str, *, label: str) -> list[_PDDLSExpression]:
	expression = _parse_pddl_expression(text, label=label)
	if not isinstance(expression, list) or not expression:
		raise ValueError(f"TIDE {label} must be one non-empty PDDL expression.")
	if str(expression[0]).lower() != "define":
		raise ValueError(f"TIDE {label} must start with a PDDL define form.")
	return expression


def _parse_pddl_expression(text: str, *, label: str) -> _PDDLSExpression:
	code = re.sub(r";.*$", "", str(text), flags=re.MULTILINE)
	tokens = tuple(re.findall(r"\(|\)|[^\s()]+", code))
	if not tokens:
		raise ValueError(f"TIDE {label} is empty.")

	def parse(cursor: int) -> tuple[_PDDLSExpression, int]:
		if cursor >= len(tokens):
			raise ValueError(f"TIDE {label} has an incomplete expression.")
		token = tokens[cursor]
		if token != "(":
			if token == ")":
				raise ValueError(f"TIDE {label} has an unexpected closing parenthesis.")
			return token.lower(), cursor + 1
		items: list[_PDDLSExpression] = []
		cursor += 1
		while cursor < len(tokens) and tokens[cursor] != ")":
			item, cursor = parse(cursor)
			items.append(item)
		if cursor >= len(tokens):
			raise ValueError(f"TIDE {label} has an unmatched opening parenthesis.")
		return items, cursor + 1

	result, cursor = parse(0)
	if cursor != len(tokens):
		raise ValueError(f"TIDE {label} contains more than one top-level expression.")
	return result


def _replace_problem_goal(
	problem: list[_PDDLSExpression],
	goal: _PDDLSExpression,
) -> None:
	indices = [
		index
		for index, form in enumerate(problem)
		if isinstance(form, list) and form and str(form[0]).lower() == ":goal"
	]
	if len(indices) != 1:
		raise ValueError(f"Expected exactly one PDDL :goal block; found {len(indices)}.")
	problem[indices[0]] = [":goal", goal]


def _tide_symbol_table(
	domain: list[_PDDLSExpression],
	problem: list[_PDDLSExpression],
) -> _TideSymbolTable:
	_definition_name(domain, "domain")
	_definition_name(problem, "problem")
	types: set[str] = set()
	predicates: set[str] = set()
	functions: set[str] = set()
	objects: set[str] = set()

	for form in domain[2:]:
		if not isinstance(form, list) or not form:
			continue
		head = str(form[0]).lower()
		if head == ":types":
			for children, parent in _typed_groups(form[1:], label="type declaration"):
				types.update(children)
				if parent not in {"object", "number"}:
					types.add(parent)
		elif head == ":constants":
			for names, _ in _typed_groups(form[1:], label="constant declaration"):
				objects.update(names)
		elif head == ":predicates":
			predicates.update(
				str(schema[0]).lower()
				for schema in form[1:]
				if isinstance(schema, list) and schema
			)
		elif head == ":functions":
			functions.update(
				str(schema[0]).lower()
				for schema in form[1:]
				if isinstance(schema, list) and schema
			)
	for form in problem[2:]:
		if not isinstance(form, list) or not form:
			continue
		if str(form[0]).lower() == ":objects":
			for names, _ in _typed_groups(form[1:], label="object declaration"):
				objects.update(names)

	return _TideSymbolTable(
		types=frozenset(types),
		predicates=frozenset(predicates),
		functions=frozenset(functions),
		objects=frozenset(objects),
	)


def _definition_name(document: list[_PDDLSExpression], kind: str) -> str:
	if len(document) < 2 or not isinstance(document[1], list):
		raise ValueError(f"TIDE PDDL document is missing its {kind} declaration.")
	header = document[1]
	if len(header) != 2 or str(header[0]).lower() != kind:
		raise ValueError(f"TIDE PDDL document is missing its {kind} declaration.")
	return str(header[1]).lower()


def _typed_groups(
	items: Sequence[_PDDLSExpression],
	*,
	label: str,
) -> tuple[tuple[tuple[str, ...], str], ...]:
	if any(not isinstance(item, str) for item in items):
		raise ValueError(f"TIDE {label} uses an unsupported nested type expression.")
	tokens = [str(item).lower() for item in items]
	groups: list[tuple[tuple[str, ...], str]] = []
	pending: list[str] = []
	index = 0
	while index < len(tokens):
		token = tokens[index]
		if token == "-":
			if not pending or index + 1 >= len(tokens):
				raise ValueError(f"TIDE {label} has a malformed typed list.")
			groups.append((tuple(pending), tokens[index + 1]))
			pending = []
			index += 2
			continue
		pending.append(token)
		index += 1
	if pending:
		groups.append((tuple(pending), "object"))
	return tuple(groups)


def _ordered_type_groups(
	items: Sequence[_PDDLSExpression],
) -> tuple[tuple[tuple[str, ...], str], ...]:
	groups = _typed_groups(items, label="type declaration")
	parent_by_child: dict[str, str] = {}
	declared: set[str] = set()
	children_by_parent: dict[str, list[str]] = {}
	parent_order: dict[str, int] = {}
	for children, parent in groups:
		parent_order.setdefault(parent, len(parent_order))
		bucket = children_by_parent.setdefault(parent, [])
		for child in children:
			if child in parent_by_child and parent_by_child[child] != parent:
				raise ValueError(f"TIDE type {child!r} has multiple parents.")
			parent_by_child[child] = parent
			declared.add(child)
			if child not in bucket:
				bucket.append(child)
	for parent in children_by_parent:
		if parent not in {"object", "number"} and parent not in declared:
			raise ValueError(f"TIDE type declaration references unknown parent {parent!r}.")

	depth_cache: dict[str, int] = {"object": 0, "number": 0}

	def depth(type_name: str, visiting: frozenset[str] = frozenset()) -> int:
		if type_name in depth_cache:
			return depth_cache[type_name]
		if type_name in visiting:
			raise ValueError("TIDE type hierarchy must be acyclic.")
		parent = parent_by_child.get(type_name, "object")
		result = depth(parent, visiting | {type_name}) + 1
		depth_cache[type_name] = result
		return result

	ordered_parents = sorted(
		children_by_parent,
		key=lambda parent: (depth(parent), parent_order[parent]),
	)
	return tuple((tuple(children_by_parent[parent]), parent) for parent in ordered_parents)


def _transform_tide_domain(
	domain: list[_PDDLSExpression],
	symbols: _TideSymbolTable,
) -> list[_PDDLSExpression]:
	result: list[_PDDLSExpression] = ["define"]
	result.append(["domain", _encode_tide_symbol(_definition_name(domain, "domain"), "d")])
	for form in domain[2:]:
		if not isinstance(form, list) or not form:
			result.append(form)
			continue
		head = str(form[0]).lower()
		if head == ":types":
			result.append(_transform_type_form(form))
		elif head == ":constants":
			result.append(_transform_typed_form(form, name_kind="o"))
		elif head == ":predicates":
			result.append(
				[
					":predicates",
					*(
						_transform_schema(schema, head_kind="p_")
						for schema in form[1:]
					),
				],
			)
		elif head == ":functions":
			result.append(_transform_function_form(form))
		elif head == ":action":
			result.append(_transform_action_form(form, symbols))
		else:
			result.append(_transform_tide_expression(form, symbols))
	return result


def _transform_tide_problem(
	problem: list[_PDDLSExpression],
	symbols: _TideSymbolTable,
) -> list[_PDDLSExpression]:
	result: list[_PDDLSExpression] = ["define"]
	result.append(
		["problem", _encode_tide_symbol(_definition_name(problem, "problem"), "q")],
	)
	for form in problem[2:]:
		if not isinstance(form, list) or not form:
			result.append(form)
			continue
		head = str(form[0]).lower()
		if head == ":domain" and len(form) == 2:
			result.append([":domain", _encode_tide_symbol(str(form[1]), "d")])
		elif head == ":objects":
			result.append(_transform_typed_form(form, name_kind="o"))
		elif head == ":goal" and len(form) == 2:
			result.append(
				[
					":goal",
					_transform_tide_expression(
						form[1],
						symbols,
						temporal_context=True,
					),
				],
			)
		else:
			result.append(_transform_tide_expression(form, symbols))
	return result


def _transform_type_form(form: list[_PDDLSExpression]) -> list[_PDDLSExpression]:
	result: list[_PDDLSExpression] = [":types"]
	for children, parent in _ordered_type_groups(form[1:]):
		result.extend(_encode_tide_symbol(child, "t") for child in children)
		result.extend(("-", _encode_tide_type(parent)))
	return result


def _transform_typed_form(
	form: list[_PDDLSExpression],
	*,
	name_kind: str,
) -> list[_PDDLSExpression]:
	result: list[_PDDLSExpression] = [str(form[0]).lower()]
	for names, type_name in _typed_groups(form[1:], label=str(form[0])):
		result.extend(
			_encode_tide_variable(name)
			if name_kind == "v"
			else _encode_tide_symbol(name, name_kind)
			for name in names
		)
		if type_name != "object" or any("-" == str(item) for item in form[1:]):
			result.extend(("-", _encode_tide_type(type_name)))
	return result


def _transform_schema(
	schema: _PDDLSExpression,
	*,
	head_kind: str,
) -> list[_PDDLSExpression]:
	if not isinstance(schema, list) or not schema:
		raise ValueError("TIDE predicate or function schema is malformed.")
	result: list[_PDDLSExpression] = [_encode_tide_symbol(str(schema[0]), head_kind)]
	for names, type_name in _typed_groups(schema[1:], label="schema parameters"):
		result.extend(_encode_tide_variable(name) for name in names)
		if type_name != "object" or any("-" == str(item) for item in schema[1:]):
			result.extend(("-", _encode_tide_type(type_name)))
	return result


def _transform_function_form(
	form: list[_PDDLSExpression],
) -> list[_PDDLSExpression]:
	result: list[_PDDLSExpression] = [":functions"]
	for item in form[1:]:
		if isinstance(item, list) and item:
			name = str(item[0]).lower()
			head = name if name == "total-cost" else _encode_tide_symbol(name, "f")
			transformed = _transform_schema([name, *item[1:]], head_kind="f")
			transformed[0] = head
			result.append(transformed)
		else:
			value = str(item).lower()
			result.append("-" if value == "-" else _encode_tide_type(value))
	return result


def _transform_action_form(
	form: list[_PDDLSExpression],
	symbols: _TideSymbolTable,
) -> list[_PDDLSExpression]:
	if len(form) < 2:
		raise ValueError("TIDE action declaration is missing its name.")
	result: list[_PDDLSExpression] = [
		":action",
		_encode_tide_symbol(str(form[1]), "a"),
	]
	index = 2
	while index < len(form):
		keyword = form[index]
		if index + 1 >= len(form):
			raise ValueError("TIDE action declaration has a keyword without a value.")
		result.append(str(keyword).lower() if isinstance(keyword, str) else keyword)
		value = form[index + 1]
		if str(keyword).lower() == ":parameters" and isinstance(value, list):
			parameter_form = _transform_typed_form(
				[":parameters", *value],
				name_kind="v",
			)
			result.append(parameter_form[1:])
		else:
			result.append(_transform_tide_expression(value, symbols))
		index += 2
	return result


def _transform_tide_expression(
	expression: _PDDLSExpression,
	symbols: _TideSymbolTable,
	*,
	temporal_context: bool = False,
) -> _PDDLSExpression:
	if isinstance(expression, str):
		name = expression.lower()
		if name.startswith("?"):
			return _encode_tide_variable(name)
		if name in symbols.objects:
			return _encode_tide_symbol(name, "o")
		if name in symbols.types:
			return _encode_tide_type(name)
		return name
	if not expression:
		return []
	head_raw = expression[0]
	if not isinstance(head_raw, str):
		return [
			_transform_tide_expression(
				item,
				symbols,
				temporal_context=temporal_context,
			)
			for item in expression
		]
	head = head_raw.lower()
	if temporal_context and _is_tide_temporal_operator(expression):
		encoded_head = head
	elif head in symbols.predicates:
		encoded_head = _encode_tide_symbol(head, "p_")
	elif head in symbols.functions and head != "total-cost":
		encoded_head = _encode_tide_symbol(head, "f")
	else:
		encoded_head = head
	if head in {"forall", "exists"} and len(expression) >= 3:
		variables = expression[1]
		if not isinstance(variables, list):
			raise ValueError(f"TIDE {head} expression has malformed parameters.")
		parameter_form = _transform_typed_form(
			[":parameters", *variables],
			name_kind="v",
		)
		return [
			encoded_head,
			parameter_form[1:],
			*(
				_transform_tide_expression(
					item,
					symbols,
					temporal_context=temporal_context,
				)
				for item in expression[2:]
			),
		]
	return [
		encoded_head,
		*(
			_transform_tide_expression(
				item,
				symbols,
				temporal_context=temporal_context,
			)
			for item in expression[1:]
		),
	]


def _is_tide_temporal_operator(expression: Sequence[_PDDLSExpression]) -> bool:
	"""Recognize an operator node by syntax, not by a potentially colliding name."""

	if not expression or not isinstance(expression[0], str):
		return False
	head = expression[0].lower()
	operands = expression[1:]
	if head in {"next", "eventually", "always", "not"}:
		return len(operands) == 1 and isinstance(operands[0], list)
	if head in {"until", "release"}:
		return len(operands) == 2 and all(isinstance(operand, list) for operand in operands)
	if head in {"and", "or"}:
		return bool(operands) and all(isinstance(operand, list) for operand in operands)
	return head in {"true", "false"} and not operands


def _encode_tide_symbol(symbol: str, kind: str) -> str:
	name = str(symbol).lower()
	return f"{_TIDE_SYMBOL_PREFIX}{kind}{name.encode('utf-8').hex()}"


def _encode_tide_variable(symbol: str) -> str:
	name = str(symbol).lower().removeprefix("?")
	return f"?{_encode_tide_symbol(name, 'v')}"


def _encode_tide_type(symbol: str) -> str:
	name = str(symbol).lower()
	return name if name in {"object", "number"} else _encode_tide_symbol(name, "t")


def _decode_tide_plan_action(action: str) -> str:
	match = re.fullmatch(r"\(\s*([^\s()]+)(?P<args>(?:\s+[^\s()]+)*)\s*\)", action)
	if match is None:
		raise ValueError(f"Malformed normalized TIDE plan action: {action!r}.")
	tokens = [match.group(1), *match.group("args").split()]
	return "(" + " ".join(_decode_tide_symbol(token) for token in tokens) + ")"


def _decode_tide_symbol(symbol: str) -> str:
	value = str(symbol).lower()
	for kind in ("a", "o"):
		prefix = f"{_TIDE_SYMBOL_PREFIX}{kind}"
		if not value.startswith(prefix):
			continue
		encoded = value[len(prefix) :]
		if not encoded or not re.fullmatch(r"[0-9a-f]+", encoded) or len(encoded) % 2:
			raise ValueError(f"Malformed normalized TIDE symbol: {symbol!r}.")
		try:
			return bytes.fromhex(encoded).decode("utf-8")
		except UnicodeDecodeError as error:
			raise ValueError(f"Malformed normalized TIDE symbol: {symbol!r}.") from error
	return value


def _render_pddl_document(document: list[_PDDLSExpression]) -> str:
	if len(document) < 2:
		return _render_pddl_expression(document) + "\n"
	lines = [f"(define {_render_pddl_expression(document[1])}"]
	lines.extend(f" {_render_pddl_expression(form)}" for form in document[2:])
	lines.append(")")
	return "\n".join(lines) + "\n"


def _render_pddl_expression(expression: _PDDLSExpression) -> str:
	if isinstance(expression, str):
		return expression
	return "(" + " ".join(_render_pddl_expression(item) for item in expression) + ")"


def parse_tide_statistics(statistics_text: str) -> dict[str, float]:
	"""Parse the official TIDE single-problem statistics file."""

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
