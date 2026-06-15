"""
PDDL syntax validation and conservative compilable-fragment checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from tarski.io import PDDLReader


SUPPORTED_REQUIREMENTS = frozenset(
	{
		":strips",
		":typing",
		":negative-preconditions",
		":equality",
	}
)

UNSUPPORTED_REQUIREMENTS = frozenset(
	{
		":adl",
		":conditional-effects",
		":derived-predicates",
		":durative-actions",
		":fluents",
		":numeric-fluents",
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
		":functions",
		":constraints",
	}
)


@dataclass(frozen=True)
class PDDLSupportReport:
	"""Supported-fragment result for one PDDL domain/problem set."""

	domain_file: Path
	problem_files: tuple[Path, ...]
	requirements: tuple[str, ...]
	supported_requirements: tuple[str, ...]
	unsupported_reasons: tuple[str, ...]

	@property
	def is_compilable(self) -> bool:
		return not self.unsupported_reasons


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
	reasons: list[str] = []

	for requirement in requirements:
		if requirement in UNSUPPORTED_REQUIREMENTS:
			reasons.append(f"requirement {requirement} is not supported")
		elif requirement not in SUPPORTED_REQUIREMENTS:
			reasons.append(f"requirement {requirement} has no compiler support")

	for block in sorted(UNSUPPORTED_DOMAIN_BLOCKS):
		if re.search(rf"\({re.escape(block)}(?:\s|\))", domain_text, flags=re.IGNORECASE):
			reasons.append(f"domain block {block} is not supported")

	for file_label, text in (
		(str(domain_path), domain_text),
		*((str(path), text) for path, text in zip(problem_paths, problem_texts)),
	):
		for operator in _unsupported_expression_operators(text):
			reasons.append(
				f"{file_label}: Unsupported PDDL expression operator {operator!r}",
			)

	return PDDLSupportReport(
		domain_file=domain_path,
		problem_files=problem_paths,
		requirements=requirements,
		supported_requirements=tuple(
			requirement
			for requirement in requirements
			if requirement in SUPPORTED_REQUIREMENTS
		),
		unsupported_reasons=tuple(dict.fromkeys(reasons)),
	)


def _validate_with_tarski(domain_file: Path, problem_files: tuple[Path, ...]) -> None:
	try:
		domain_text = _normalize_definition_name_for_tarski(
			_strip_comments(domain_file.read_text(encoding="utf-8")),
			kind="domain",
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


def _unsupported_expression_operators(text: str) -> tuple[str, ...]:
	operators: list[str] = []
	for expression in _top_level_forms(text):
		_collect_unsupported_operators(_parse_form(expression), operators)
	return tuple(dict.fromkeys(operators))


def _collect_unsupported_operators(expression: object, operators: list[str]) -> None:
	if not isinstance(expression, tuple) or not expression:
		return
	head = str(expression[0]).lower()
	if head in {"or", "forall", "exists", "when", "imply", "preference"}:
		operators.append(head)
	for child in expression[1:]:
		_collect_unsupported_operators(child, operators)


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
