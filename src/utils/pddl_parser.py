"""
PDDL parser for the benchmark subset used by this project.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class PDDLPredicate:
	"""Predicate schema declared by a PDDL domain."""

	name: str
	parameters: List[str]


@dataclass(frozen=True)
class PDDLAction:
	"""Primitive action schema declared by a PDDL domain."""

	name: str
	parameters: List[str]
	preconditions: str
	effects: str


@dataclass(frozen=True)
class PDDLFact:
	"""Ground fact in a PDDL problem."""

	predicate: str
	args: List[str]
	is_positive: bool = True

	def to_signature(self) -> str:
		atom = self.predicate if not self.args else f"{self.predicate}({', '.join(self.args)})"
		return atom if self.is_positive else f"not {atom}"


@dataclass(frozen=True)
class PDDLDomain:
	"""Parsed PDDL domain."""

	name: str
	requirements: List[str]
	types: List[str]
	predicates: List[PDDLPredicate]
	actions: List[PDDLAction]


@dataclass(frozen=True)
class PDDLProblem:
	"""Parsed PDDL problem."""

	name: str
	domain_name: str
	objects: List[str]
	object_types: Dict[str, str]
	init_facts: List[PDDLFact]
	goal_facts: List[PDDLFact]


class PDDLParser:
	"""Parse the IPC PDDL fragment used by the benchmark data."""

	@staticmethod
	def parse_domain(file_path: str | Path) -> PDDLDomain:
		content = _strip_comments(Path(file_path).read_text(encoding="utf-8"))
		domain_name_match = re.search(r"\(define\s+\(domain\s+([^\s)]+)\)", content, re.IGNORECASE)
		domain_name = _canonical_symbol(
			domain_name_match.group(1) if domain_name_match else "unknown",
		)
		return PDDLDomain(
			name=domain_name,
			requirements=_extract_simple_list_block(content, "requirements"),
			types=_extract_simple_list_block(content, "types"),
			predicates=_extract_predicates(content),
			actions=_extract_actions(content),
		)

	@staticmethod
	def parse_problem(file_path: str | Path) -> PDDLProblem:
		content = _strip_comments(Path(file_path).read_text(encoding="utf-8"))
		problem_name_match = re.search(r"\(define\s+\(problem\s+([^\s)]+)\)", content, re.IGNORECASE)
		domain_name_match = re.search(r"\(:domain\s+([^\s)]+)\)", content, re.IGNORECASE)
		objects, object_types = _extract_problem_objects(content)
		return PDDLProblem(
			name=_canonical_symbol(
				problem_name_match.group(1)
				if problem_name_match
				else "unknown_problem",
			),
			domain_name=_canonical_symbol(
				domain_name_match.group(1)
				if domain_name_match
				else "unknown_domain",
			),
			objects=objects,
			object_types=object_types,
			init_facts=_extract_problem_facts(content, "init"),
			goal_facts=_extract_problem_goal_facts(content),
		)


def _strip_comments(content: str) -> str:
	return re.sub(r";.*$", "", content, flags=re.MULTILINE)


def _canonical_symbol(symbol: str) -> str:
	return str(symbol).lower()


def _extract_simple_list_block(content: str, block_name: str) -> List[str]:
	start = _find_block_start(content, block_name)
	if start == -1:
		return []
	end = _find_matching_paren(content, start)
	inner = content[start + len(f"(:{block_name}") : end].strip()
	return [_canonical_symbol(token) for token in re.split(r"\s+", inner) if token]


def _extract_predicates(content: str) -> List[PDDLPredicate]:
	start = _find_block_start(content, "predicates")
	if start == -1:
		return []
	end = _find_matching_paren(content, start)
	inner = content[start + len("(:predicates") : end]
	predicates: List[PDDLPredicate] = []
	for expression in _top_level_expressions(inner):
		tokens = expression.strip("() \n\t").split()
		if not tokens:
			continue
		name = _canonical_symbol(tokens[0])
		parameters = _group_typed_parameters(tokens[1:])
		predicates.append(PDDLPredicate(name=name, parameters=parameters))
	return predicates


def _extract_actions(content: str) -> List[PDDLAction]:
	actions: List[PDDLAction] = []
	cursor = 0
	while True:
		start = _find_block_start(content, "action", cursor)
		if start == -1:
			break
		end = _find_matching_paren(content, start)
		block = content[start:end + 1]
		header_match = re.match(r"\(:action\s+([^\s)]+)", block, re.IGNORECASE)
		if header_match is None:
			cursor = end + 1
			continue
		actions.append(
			PDDLAction(
				name=_canonical_symbol(header_match.group(1)),
				parameters=_extract_action_parameters(block),
				preconditions=_extract_keyword_expression(block, "precondition"),
				effects=_extract_keyword_expression(block, "effect"),
			),
		)
		cursor = end + 1
	return actions


def _extract_action_parameters(block: str) -> List[str]:
	match = re.search(r":parameters\s*\(", block, re.IGNORECASE)
	if match is None:
		return []
	start = match.end() - 1
	end = _find_matching_paren(block, start)
	tokens = block[start + 1 : end].split()
	return _group_typed_parameters(tokens)


def _extract_keyword_expression(block: str, keyword: str) -> str:
	match = re.search(rf":{keyword}\s*", block, re.IGNORECASE)
	if match is None:
		return ""
	cursor = match.end()
	while cursor < len(block) and block[cursor].isspace():
		cursor += 1
	if cursor >= len(block):
		return ""
	if block[cursor] != "(":
		start = cursor
		while cursor < len(block) and not block[cursor].isspace():
			cursor += 1
		return block[start:cursor].strip()
	end = _find_matching_paren(block, cursor)
	return block[cursor:end + 1].strip()


def _extract_problem_objects(content: str) -> tuple[List[str], Dict[str, str]]:
	start = _find_block_start(content, "objects")
	if start == -1:
		return [], {}
	end = _find_matching_paren(content, start)
	tokens = content[start + len("(:objects") : end].split()
	objects: List[str] = []
	object_types: Dict[str, str] = {}
	pending: List[str] = []
	index = 0
	while index < len(tokens):
		token = tokens[index]
		if token == "-" and index + 1 < len(tokens):
			type_name = _canonical_symbol(tokens[index + 1])
			for name in pending:
				object_name = _canonical_symbol(name)
				objects.append(object_name)
				object_types[object_name] = type_name
			pending = []
			index += 2
			continue
		pending.append(token)
		index += 1
	for name in pending:
		object_name = _canonical_symbol(name)
		objects.append(object_name)
		object_types[object_name] = "object"
	return objects, object_types


def _extract_problem_facts(content: str, block_name: str) -> List[PDDLFact]:
	start = _find_block_start(content, block_name)
	if start == -1:
		return []
	end = _find_matching_paren(content, start)
	inner = content[start + len(f"(:{block_name}") : end]
	return _parse_fact_expressions(_top_level_expressions(inner))


def _extract_problem_goal_facts(content: str) -> List[PDDLFact]:
	start = _find_block_start(content, "goal")
	if start == -1:
		return []
	end = _find_matching_paren(content, start)
	inner = content[start + len("(:goal") : end].strip()
	if inner.lower().startswith("(and"):
		inner_end = _find_matching_paren(inner, 0)
		inner = inner[len("(and") : inner_end]
		return _parse_fact_expressions(_top_level_expressions(inner))
	return _parse_fact_expressions([inner])


def _parse_fact_expressions(expressions: List[str]) -> List[PDDLFact]:
	facts: List[PDDLFact] = []
	for expression in expressions:
		text = expression.strip()
		if not text or not text.startswith("("):
			continue
		if text.lower().startswith("(not"):
			inner_start = text.find("(", 1)
			inner_end = _find_matching_paren(text, inner_start)
			parsed = _parse_positive_fact(text[inner_start:inner_end + 1])
			if parsed is not None:
				facts.append(PDDLFact(parsed.predicate, parsed.args, is_positive=False))
			continue
		parsed = _parse_positive_fact(text)
		if parsed is not None:
			facts.append(parsed)
	return facts


def _parse_positive_fact(expression: str) -> PDDLFact | None:
	tokens = expression.strip("() \n\t").split()
	if not tokens or tokens[0] == "=":
		return None
	return PDDLFact(
		predicate=_canonical_symbol(tokens[0]),
		args=[_canonical_symbol(token) for token in tokens[1:]],
		is_positive=True,
	)


def _top_level_expressions(text: str) -> List[str]:
	expressions: List[str] = []
	start = None
	depth = 0
	for index, character in enumerate(text):
		if character == "(":
			if depth == 0:
				start = index
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0 and start is not None:
				expressions.append(text[start:index + 1])
				start = None
	return expressions


def _group_typed_parameters(tokens: List[str]) -> List[str]:
	parameters: List[str] = []
	pending: List[str] = []
	index = 0
	while index < len(tokens):
		token = _canonical_symbol(tokens[index])
		if token == "-" and index + 1 < len(tokens):
			type_name = _canonical_symbol(tokens[index + 1])
			for name in pending:
				parameters.append(f"{name} - {type_name}")
			pending = []
			index += 2
			continue
		pending.append(token)
		index += 1
	parameters.extend(pending)
	return parameters


def _find_block_start(content: str, block_name: str, start: int = 0) -> int:
	match = re.search(rf"\(:{re.escape(block_name)}(?:\s|\))", content[start:], re.IGNORECASE)
	return -1 if match is None else start + match.start()


def _find_matching_paren(text: str, start: int) -> int:
	depth = 0
	for index in range(start, len(text)):
		if text[index] == "(":
			depth += 1
		elif text[index] == ")":
			depth -= 1
			if depth == 0:
				return index
	raise ValueError(f"Unmatched parenthesis at index {start}.")
