"""
PDDL syntax validation and conservative compilable-fragment checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from plan_library.rendering import sanitize_identifier
from tarski.io import PDDLReader
from utils.pddl_parser import PDDLParser
from utils.pddl_parser import PDDLNumericExpression


SUPPORTED_REQUIREMENTS = frozenset(
	{
		":strips",
		":typing",
		":negative-preconditions",
		":equality",
		":action-costs",
		":numeric-fluents",
		":fluents",
	}
)

UNSUPPORTED_REQUIREMENTS = frozenset(
	{
		":adl",
		":conditional-effects",
		":derived-predicates",
		":durative-actions",
		":preferences",
		":quantified-preconditions",
		":universal-preconditions",
		":existential-preconditions",
	}
)

UNSUPPORTED_DOMAIN_BLOCKS = frozenset(
	{
		":derived",
		":durative-action",
		":constraints",
	}
)

UNSUPPORTED_EXPRESSION_OPERATORS = frozenset(
	{
		"or",
		"forall",
		"exists",
		"when",
		"imply",
		"preference",
		"assign",
		"scale-up",
		"scale-down",
		"+",
		"-",
		"*",
		"/",
	}
)

SUPPORTED_FRAGMENT_ASSUMPTIONS = (
	"classical finite-domain PDDL files parsed before lifted ASL synthesis",
	"positive conjunctive predicate achievement goals only",
	"primitive action schemas with predicate preconditions and predicate effects",
	"bounded integer numeric resource fluents may appear in action preconditions and effects",
	"numeric effects are limited to constant integer increase/decrease updates",
	"PDDL predicate and action symbols may be sanitized for AgentSpeak rendering",
	"sanitized predicate and action functors must remain unique",
	"metric-only action-costs functions are distinguished from logical numeric resources",
	"typing, equality, and negative preconditions are accepted only inside the project parser subset",
	(
		"derived predicates, conditional effects, quantifiers, preferences, durative "
		"actions, arbitrary arithmetic expressions, and numeric goals remain unsupported"
	),
)


@dataclass(frozen=True)
class PDDLUnsupportedDiagnostic:
	"""One structured reason why a PDDL file is outside the supported fragment."""

	kind: str
	location: str
	symbol: str
	message: str

	def to_dict(self) -> dict[str, str]:
		return {
			"kind": self.kind,
			"location": self.location,
			"symbol": self.symbol,
			"message": self.message,
		}


@dataclass(frozen=True)
class PDDLSupportReport:
	"""Supported-fragment result for one PDDL domain/problem set."""

	domain_file: Path
	problem_files: tuple[Path, ...]
	requirements: tuple[str, ...]
	supported_requirements: tuple[str, ...]
	unsupported_requirements: tuple[str, ...]
	unsupported_blocks: tuple[str, ...]
	unsupported_expression_operators: tuple[str, ...]
	unsupported_reasons: tuple[str, ...]
	unsupported_diagnostics: tuple[PDDLUnsupportedDiagnostic, ...] = ()
	numeric_functions: tuple[str, ...] = ()
	logical_numeric_functions: tuple[str, ...] = ()
	metric_only_numeric_functions: tuple[str, ...] = ()

	@property
	def is_compilable(self) -> bool:
		return not self.unsupported_reasons

	def to_dict(self) -> dict[str, object]:
		"""Return a machine-readable fragment audit for reports and papers."""

		return {
			"domain_file": str(self.domain_file),
			"problem_files": [str(path) for path in self.problem_files],
			"requirements": list(self.requirements),
			"supported_requirements": list(self.supported_requirements),
			"unsupported_requirements": list(self.unsupported_requirements),
			"unsupported_blocks": list(self.unsupported_blocks),
			"unsupported_expression_operators": list(self.unsupported_expression_operators),
			"unsupported_reasons": list(self.unsupported_reasons),
			"unsupported_diagnostics": [
				diagnostic.to_dict()
				for diagnostic in self.unsupported_diagnostics
			],
			"numeric_functions": list(self.numeric_functions),
			"logical_numeric_functions": list(self.logical_numeric_functions),
			"metric_only_numeric_functions": list(self.metric_only_numeric_functions),
			"is_compilable": self.is_compilable,
			"supported_requirement_set": sorted(SUPPORTED_REQUIREMENTS),
			"known_unsupported_requirement_set": sorted(UNSUPPORTED_REQUIREMENTS),
			"known_unsupported_domain_blocks": sorted(UNSUPPORTED_DOMAIN_BLOCKS),
			"fragment_assumptions": list(SUPPORTED_FRAGMENT_ASSUMPTIONS),
		}


def assert_compilable_pddl_files(
	*,
	domain_file: str | Path,
	problem_files: Sequence[str | Path] = (),
) -> PDDLSupportReport:
	"""Validate PDDL syntax and reject fragments this library cannot compile."""

	report = inspect_pddl_support(
		domain_file=domain_file,
		problem_files=problem_files,
	)
	if report.unsupported_reasons:
		raise ValueError(
			"Unsupported PDDL for lifted ASL synthesis: "
			+ "; ".join(report.unsupported_reasons),
		)
	return report


def inspect_pddl_support(
	*,
	domain_file: str | Path,
	problem_files: Sequence[str | Path] = (),
) -> PDDLSupportReport:
	"""Return syntax and supported-fragment information for PDDL inputs."""

	domain_path = Path(domain_file)
	problem_paths = tuple(Path(path) for path in problem_files)
	_validate_with_tarski(domain_path, problem_paths)
	domain_text = _strip_comments(domain_path.read_text(encoding="utf-8"))
	problem_texts = tuple(
		_strip_comments(path.read_text(encoding="utf-8"))
		for path in problem_paths
	)
	requirements = tuple(_requirements(domain_text))
	parsed_domain = PDDLParser.parse_domain(domain_path)
	parsed_problems = tuple(PDDLParser.parse_problem(path) for path in problem_paths)
	numeric_profile = _numeric_profile(parsed_domain, parsed_problems)
	reasons: list[str] = []
	diagnostics: list[PDDLUnsupportedDiagnostic] = []
	unsupported_requirements: list[str] = []
	unsupported_blocks: list[str] = []
	unsupported_operators: list[str] = []

	for requirement in requirements:
		if requirement in UNSUPPORTED_REQUIREMENTS:
			unsupported_requirements.append(requirement)
			message = f"requirement {requirement} is not supported"
			reasons.append(message)
			diagnostics.append(
				PDDLUnsupportedDiagnostic(
					kind="unsupported_requirement",
					location=str(domain_path),
					symbol=requirement,
					message=message,
				),
			)
		elif requirement not in SUPPORTED_REQUIREMENTS:
			unsupported_requirements.append(requirement)
			message = f"requirement {requirement} has no compiler support"
			reasons.append(message)
			diagnostics.append(
				PDDLUnsupportedDiagnostic(
					kind="unsupported_requirement",
					location=str(domain_path),
					symbol=requirement,
					message=message,
				),
			)

	for file_label, text in (
		(str(domain_path), domain_text),
		*((str(path), text) for path, text in zip(problem_paths, problem_texts)),
	):
		for block in sorted(UNSUPPORTED_DOMAIN_BLOCKS):
			if _contains_pddl_block(text, block):
				location = f"{file_label}:{block}"
				message = f"{file_label}: block {block} is not supported"
				unsupported_blocks.append(location)
				reasons.append(message)
				diagnostics.append(
					PDDLUnsupportedDiagnostic(
						kind="unsupported_block",
						location=file_label,
						symbol=block,
						message=message,
					),
				)
		for operator in _unsupported_expression_operators(text):
			message = f"{file_label}: Unsupported PDDL expression operator {operator!r}"
			unsupported_operators.append(operator)
			reasons.append(message)
			diagnostics.append(
				PDDLUnsupportedDiagnostic(
					kind="unsupported_expression_operator",
					location=file_label,
					symbol=operator,
					message=message,
				),
			)
	for problem_path, problem_text in zip(problem_paths, problem_texts):
		for diagnostic in _unsupported_goal_diagnostics(problem_path, problem_text):
			reasons.append(diagnostic.message)
			diagnostics.append(diagnostic)
	for diagnostic in _unsupported_numeric_diagnostics(
		domain_path=domain_path,
		problem_paths=problem_paths,
		domain=parsed_domain,
		problems=parsed_problems,
	):
		reasons.append(diagnostic.message)
		diagnostics.append(diagnostic)
	for diagnostic in _unsupported_asl_symbol_collision_diagnostics(
		domain_path,
		domain_text,
	):
		reasons.append(diagnostic.message)
		diagnostics.append(diagnostic)

	return PDDLSupportReport(
		domain_file=domain_path,
		problem_files=problem_paths,
		requirements=requirements,
		supported_requirements=tuple(
			requirement
			for requirement in requirements
			if requirement in SUPPORTED_REQUIREMENTS
		),
		unsupported_requirements=tuple(dict.fromkeys(unsupported_requirements)),
		unsupported_blocks=tuple(dict.fromkeys(unsupported_blocks)),
		unsupported_expression_operators=tuple(dict.fromkeys(unsupported_operators)),
		unsupported_reasons=tuple(dict.fromkeys(reasons)),
		unsupported_diagnostics=tuple(_deduplicate_diagnostics(diagnostics)),
		numeric_functions=numeric_profile["numeric_functions"],
		logical_numeric_functions=numeric_profile["logical_numeric_functions"],
		metric_only_numeric_functions=numeric_profile["metric_only_numeric_functions"],
	)


def _validate_with_tarski(domain_file: Path, problem_files: tuple[Path, ...]) -> None:
	try:
		raw_domain_text = _strip_comments(domain_file.read_text(encoding="utf-8"))
		if _contains_numeric_pddl(raw_domain_text):
			PDDLParser.parse_domain(domain_file)
			for problem_file in problem_files:
				PDDLParser.parse_problem(problem_file)
			return
		domain_text = _normalize_domain_for_tarski(
			raw_domain_text,
		)
		if problem_files:
			for problem_file in problem_files:
				reader = PDDLReader(raise_on_error=True)
				reader.parse_domain_string(domain_text)
				reader.parse_instance_string(
					_normalize_definition_name_for_tarski(
						_strip_comments(problem_file.read_text(encoding="utf-8")),
						kind="problem",
					),
				)
		else:
			reader = PDDLReader(raise_on_error=True)
			reader.parse_domain_string(domain_text)
	except Exception as error:
		raise ValueError(f"PDDL syntax validation failed: {error}") from error


def _contains_numeric_pddl(domain_text: str) -> bool:
	requirements = set(_requirements(domain_text))
	return (
		":numeric-fluents" in requirements
		or ":fluents" in requirements
		or _keyword_block(domain_text, "functions") is not None
	)


def _normalize_domain_for_tarski(text: str) -> str:
	"""Normalize IPC syntax variants that are valid PDDL but strict Tarski rejects."""

	return _normalize_type_declaration_order_for_tarski(
		_normalize_definition_name_for_tarski(text, kind="domain"),
	)


def _normalize_definition_name_for_tarski(text: str, *, kind: str) -> str:
	"""Allow IPC files whose domain/problem names start with digits."""

	def _replace(match: re.Match[str]) -> str:
		name = match.group("name")
		if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", name):
			return match.group(0)
		safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", name)
		if not re.match(r"[A-Za-z_]", safe_name):
			safe_name = f"p_{safe_name}"
		return f"(define ({kind} {safe_name})"

	return re.sub(
		rf"\(define\s+\({kind}\s+(?P<name>[^\s)]+)\)",
		_replace,
		text,
		count=1,
		flags=re.IGNORECASE,
	)


def _normalize_type_declaration_order_for_tarski(text: str) -> str:
	"""Declare parent types before child types for strict Tarski validation.

	Some IPC domains use a compact typed list where a type is referenced as a
	parent before that parent appears later in the same `:types` block. PDDL
	allows this declaration style, but Tarski validates the block sequentially.
	The rewrite is used only for syntax validation; the repository snapshot and
	project parser keep the original PDDL text.
	"""

	block = _keyword_block(text, "types")
	if block is None:
		return text
	tokens = block[len("(:types") : -1].split()
	groups = _type_declaration_groups(tokens)
	if not groups:
		return text
	parent_by_type = {
		child: parent
		for children, parent in groups
		for child in children
		if child != "object"
	}
	children_by_parent: dict[str, list[str]] = {}
	for children, parent in groups:
		bucket = children_by_parent.setdefault(parent, [])
		for child in children:
			if child == "object" or child in bucket:
				continue
			bucket.append(child)
	ordered_parents = sorted(
		children_by_parent,
		key=lambda parent: (_type_depth(parent, parent_by_type), parent),
	)
	parts: list[str] = []
	for parent in ordered_parents:
		children = children_by_parent[parent]
		if not children:
			continue
		parts.append(f"{' '.join(children)} - {parent}")
	normalized_block = f"(:types {' '.join(parts)})"
	return text.replace(block, normalized_block, 1)


def _type_declaration_groups(tokens: Sequence[str]) -> tuple[tuple[tuple[str, ...], str], ...]:
	groups: list[tuple[tuple[str, ...], str]] = []
	pending: list[str] = []
	index = 0
	while index < len(tokens):
		token = tokens[index].lower()
		if token == "-" and index + 1 < len(tokens):
			parent = tokens[index + 1].lower()
			if pending:
				groups.append((tuple(dict.fromkeys(pending)), parent))
			pending = []
			index += 2
			continue
		pending.append(token)
		index += 1
	if pending:
		groups.append((tuple(dict.fromkeys(pending)), "object"))
	return tuple(groups)


def _type_depth(type_name: str, parent_by_type: Mapping[str, str]) -> int:
	if type_name == "object":
		return 0
	depth = 1
	current = type_name
	seen: set[str] = set()
	while current in parent_by_type and current not in seen:
		seen.add(current)
		current = parent_by_type[current]
		if current == "object":
			return depth
		depth += 1
	return depth


def _requirements(domain_text: str) -> tuple[str, ...]:
	match = re.search(
		r"\(:requirements(?P<body>[^)]*)\)",
		domain_text,
		flags=re.IGNORECASE,
	)
	if match is None:
		return ()
	return tuple(
		token.lower()
		for token in re.split(r"\s+", match.group("body").strip())
		if token
	)


def _contains_pddl_block(text: str, block: str) -> bool:
	return re.search(rf"\({re.escape(block)}(?:\s|\))", text, flags=re.IGNORECASE) is not None


def _unsupported_goal_reasons(problem_path: Path, problem_text: str) -> tuple[str, ...]:
	return tuple(
		diagnostic.message
		for diagnostic in _unsupported_goal_diagnostics(problem_path, problem_text)
	)


def _unsupported_goal_diagnostics(
	problem_path: Path,
	problem_text: str,
) -> tuple[PDDLUnsupportedDiagnostic, ...]:
	goal_expression = _keyword_expression(problem_text, "goal")
	if goal_expression is None:
		return ()
	parsed = _parse_form(goal_expression)
	if _is_positive_conjunctive_goal(parsed):
		return ()
	kind, symbol, fragment_label = _unsupported_goal_fragment(parsed)
	message = (
		f"{problem_path}: {fragment_label} problem goals are not supported; "
		"supported goals are positive achievement goals only: predicate atoms "
		"optionally inside an and conjunction"
	)
	return (
		PDDLUnsupportedDiagnostic(
			kind=kind,
			location=str(problem_path),
			symbol=symbol,
			message=message,
		),
	)


def _numeric_profile(domain: object, problems: Sequence[object]) -> dict[str, tuple[str, ...]]:
	declared = tuple(
		sanitize_identifier(getattr(function, "name", ""))
		for function in tuple(getattr(domain, "functions", ()) or ())
	)
	condition_functions: set[str] = set()
	effect_functions: set[str] = set()
	goal_functions: set[str] = set()
	for action in tuple(getattr(domain, "actions", ()) or ()):
		for condition in tuple(getattr(action, "numeric_preconditions", ()) or ()):
			condition_functions.update(_numeric_condition_functions(condition))
		for effect in tuple(getattr(action, "numeric_effects", ()) or ()):
			effect_functions.add(sanitize_identifier(effect.fluent.function))
			effect_functions.update(_numeric_expression_functions(effect.amount))
	for problem in tuple(problems or ()):
		for condition in tuple(getattr(problem, "numeric_goal_conditions", ()) or ()):
			goal_functions.update(_numeric_condition_functions(condition))
	logical = condition_functions | effect_functions | goal_functions
	metric_only = {
		function
		for function in declared
		if function == "total_cost" and function not in condition_functions and function not in goal_functions
	}
	return {
		"numeric_functions": tuple(sorted(dict.fromkeys(declared))),
		"logical_numeric_functions": tuple(sorted(logical - metric_only)),
		"metric_only_numeric_functions": tuple(sorted(metric_only)),
	}


def _unsupported_numeric_diagnostics(
	*,
	domain_path: Path,
	problem_paths: Sequence[Path],
	domain: object,
	problems: Sequence[object],
) -> tuple[PDDLUnsupportedDiagnostic, ...]:
	diagnostics: list[PDDLUnsupportedDiagnostic] = []
	for action in tuple(getattr(domain, "actions", ()) or ()):
		for effect in tuple(getattr(action, "numeric_effects", ()) or ()):
			if _is_integer_constant_expression(effect.amount):
				continue
			message = (
				f"{domain_path}: action {action.name!r} numeric effects must "
				"increase or decrease by integer constants in the supported "
				"bounded resource fragment"
			)
			diagnostics.append(
				PDDLUnsupportedDiagnostic(
					kind="unsupported_numeric_effect_amount",
					location=f"{domain_path}:action:{action.name}",
					symbol=effect.operator,
					message=message,
				),
			)
	for problem_path, problem in zip(problem_paths, problems):
		for assignment in tuple(getattr(problem, "numeric_init", ()) or ()):
			if isinstance(assignment.value, int):
				continue
			message = (
				f"{problem_path}: numeric initial values must be finite integers "
				"in the supported bounded resource fragment"
			)
			diagnostics.append(
				PDDLUnsupportedDiagnostic(
					kind="unsupported_numeric_init_value",
					location=str(problem_path),
					symbol=assignment.fluent.function,
					message=message,
				),
			)
		if tuple(getattr(problem, "numeric_goal_conditions", ()) or ()):
			message = (
				f"{problem_path}: numeric problem goals are not supported by current "
				"atomic ASL synthesis; supported numeric fluents may appear in action "
				"preconditions and effects for bounded integer resource accounting"
			)
			diagnostics.append(
				PDDLUnsupportedDiagnostic(
					kind="unsupported_numeric_goal",
					location=str(problem_path),
					symbol="=",
					message=message,
				),
			)
	return tuple(diagnostics)


def _numeric_condition_functions(condition: object) -> set[str]:
	return (
		_numeric_expression_functions(getattr(condition, "left", None))
		| _numeric_expression_functions(getattr(condition, "right", None))
	)


def _numeric_expression_functions(expression: object) -> set[str]:
	if not isinstance(expression, PDDLNumericExpression):
		return set()
	if expression.kind != "fluent":
		return set()
	return {sanitize_identifier(expression.value)}


def _is_integer_constant_expression(expression: object) -> bool:
	return (
		isinstance(expression, PDDLNumericExpression)
		and expression.kind == "constant"
		and re.fullmatch(r"[+-]?\d+", expression.value) is not None
	)


def _unsupported_asl_symbol_collision_diagnostics(
	domain_path: Path,
	domain_text: str,
) -> tuple[PDDLUnsupportedDiagnostic, ...]:
	diagnostics: list[PDDLUnsupportedDiagnostic] = []
	for kind, symbols in (
		("predicate", _declared_predicate_names(domain_text)),
		("action", _declared_action_names(domain_text)),
	):
		by_asl_symbol: dict[str, list[str]] = {}
		for symbol in symbols:
			by_asl_symbol.setdefault(sanitize_identifier(symbol), []).append(symbol)
		for asl_symbol, pddl_symbols in sorted(by_asl_symbol.items()):
			unique_symbols = tuple(dict.fromkeys(pddl_symbols))
			if len(unique_symbols) < 2:
				continue
			quoted_symbols = ", ".join(repr(symbol) for symbol in unique_symbols)
			message = (
				f"{domain_path}: PDDL {kind} symbols ({quoted_symbols}) collapse "
				f"to the same AgentSpeak functor {asl_symbol!r}"
			)
			diagnostics.append(
				PDDLUnsupportedDiagnostic(
					kind="unsupported_asl_symbol_collision",
					location=f"{domain_path}:{kind}",
					symbol=asl_symbol,
					message=message,
				),
			)
	return tuple(diagnostics)


def _declared_predicate_names(domain_text: str) -> tuple[str, ...]:
	predicate_block = _keyword_block(domain_text, "predicates")
	if predicate_block is None:
		return ()
	return tuple(
		dict.fromkeys(
			match.group(1)
			for match in re.finditer(
				r"\(([A-Za-z_][A-Za-z0-9_-]*)\b",
				predicate_block,
			)
			if match.group(1).lower() != "and"
		),
	)


def _declared_action_names(domain_text: str) -> tuple[str, ...]:
	return tuple(
		dict.fromkeys(
			match.group(1)
			for match in re.finditer(
				r"\(:action\s+([A-Za-z_][A-Za-z0-9_-]*)\b",
				domain_text,
				flags=re.IGNORECASE,
			)
		),
	)


def _keyword_block(text: str, keyword: str) -> str | None:
	match = re.search(rf"\(:{re.escape(keyword)}(?:\s|\))", text, flags=re.IGNORECASE)
	if match is None:
		return None
	start = match.start()
	depth = 0
	for index in range(start, len(text)):
		if text[index] == "(":
			depth += 1
		elif text[index] == ")":
			depth -= 1
			if depth == 0:
				return text[start : index + 1]
	return None


def _deduplicate_diagnostics(
	diagnostics: Iterable[PDDLUnsupportedDiagnostic],
) -> tuple[PDDLUnsupportedDiagnostic, ...]:
	seen: set[tuple[str, str, str, str]] = set()
	deduplicated: list[PDDLUnsupportedDiagnostic] = []
	for diagnostic in diagnostics:
		key = (
			diagnostic.kind,
			diagnostic.location,
			diagnostic.symbol,
			diagnostic.message,
		)
		if key in seen:
			continue
		seen.add(key)
		deduplicated.append(diagnostic)
	return tuple(deduplicated)


def _keyword_expression(text: str, keyword: str) -> str | None:
	match = re.search(rf":{re.escape(keyword)}\s*", text, flags=re.IGNORECASE)
	if match is None:
		return None
	cursor = match.end()
	while cursor < len(text) and text[cursor].isspace():
		cursor += 1
	if cursor >= len(text) or text[cursor] != "(":
		return None
	depth = 0
	for index in range(cursor, len(text)):
		if text[index] == "(":
			depth += 1
		elif text[index] == ")":
			depth -= 1
			if depth == 0:
				return text[cursor:index + 1]
	return None


def _is_positive_conjunctive_goal(expression: object) -> bool:
	if not isinstance(expression, tuple) or not expression:
		return False
	head = str(expression[0]).lower()
	if head == "and":
		return all(_is_positive_goal_atom(child) for child in expression[1:])
	return _is_positive_goal_atom(expression)


def _is_positive_goal_atom(expression: object) -> bool:
	if not isinstance(expression, tuple) or not expression:
		return False
	head = str(expression[0]).lower()
	if head in UNSUPPORTED_EXPRESSION_OPERATORS or head in {"not", "="}:
		return False
	return all(not isinstance(argument, tuple) for argument in expression[1:])


def _unsupported_goal_fragment(expression: object) -> tuple[str, str, str]:
	if _contains_operator(expression, "not"):
		return ("unsupported_negative_goal", "not", "negative")
	if _contains_operator(expression, "or"):
		return ("unsupported_disjunctive_goal", "or", "disjunctive")
	if _contains_operator(expression, "="):
		return ("unsupported_goal_equality", "=", "equality")
	for operator in sorted(UNSUPPORTED_EXPRESSION_OPERATORS):
		if _contains_operator(expression, operator):
			return ("unsupported_goal_operator", operator, f"{operator!r}")
	return ("unsupported_goal_fragment", ":goal", "non-conjunctive")


def _contains_operator(expression: object, operator: str) -> bool:
	if not isinstance(expression, tuple) or not expression:
		return False
	if str(expression[0]).lower() == operator:
		return True
	return any(_contains_operator(child, operator) for child in expression[1:])


def _unsupported_expression_operators(text: str) -> tuple[str, ...]:
	operators: list[str] = []
	for expression in _top_level_forms(text):
		_collect_unsupported_operators(_parse_form(expression), operators)
	return tuple(dict.fromkeys(operators))


def _collect_unsupported_operators(expression: object, operators: list[str]) -> None:
	if not isinstance(expression, tuple) or not expression:
		return
	head = str(expression[0]).lower()
	if _is_supported_numeric_effect_expression(expression):
		return
	if head in UNSUPPORTED_EXPRESSION_OPERATORS:
		operators.append(head)
	for child in expression[1:]:
		_collect_unsupported_operators(child, operators)


def _is_supported_numeric_effect_expression(expression: object) -> bool:
	return (
		isinstance(expression, tuple)
		and len(expression) >= 3
		and str(expression[0]).lower() == "increase"
		and isinstance(expression[1], tuple)
		and bool(expression[1])
	)


def _top_level_forms(text: str) -> tuple[str, ...]:
	forms: list[str] = []
	start = None
	depth = 0
	in_string = False
	escaped = False
	for index, character in enumerate(text):
		if escaped:
			escaped = False
			continue
		if character == "\\" and in_string:
			escaped = True
			continue
		if character == '"':
			in_string = not in_string
			continue
		if in_string:
			continue
		if character == "(":
			if depth == 0:
				start = index
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0 and start is not None:
				forms.append(text[start:index + 1])
				start = None
	return tuple(forms)


def _parse_form(text: str) -> object:
	tokens = _tokens(text)
	if not tokens:
		return ()
	expression, cursor = _parse_tokens(tokens, 0)
	if cursor != len(tokens):
		return ()
	return expression


def _tokens(text: str) -> tuple[str, ...]:
	buffer: list[str] = []
	token: list[str] = []
	for character in text:
		if character in "()":
			if token:
				buffer.append("".join(token))
				token = []
			buffer.append(character)
		elif character.isspace():
			if token:
				buffer.append("".join(token))
				token = []
		else:
			token.append(character)
	if token:
		buffer.append("".join(token))
	return tuple(buffer)


def _parse_tokens(tokens: tuple[str, ...], cursor: int) -> tuple[object, int]:
	if cursor >= len(tokens):
		return (), cursor
	if tokens[cursor] != "(":
		return tokens[cursor], cursor + 1
	cursor += 1
	items: list[object] = []
	while cursor < len(tokens) and tokens[cursor] != ")":
		item, cursor = _parse_tokens(tokens, cursor)
		items.append(item)
	if cursor >= len(tokens):
		return tuple(items), cursor
	return tuple(items), cursor + 1


def _strip_comments(content: str) -> str:
	return re.sub(r";.*$", "", content, flags=re.MULTILINE)
