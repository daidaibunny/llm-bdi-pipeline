"""
Compile generated context literals into small PDDL problem variants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from utils.pddl_parser import PDDLFact, PDDLParser


def write_goal_problem_variant(
	*,
	base_problem_file: str | Path,
	goal_literals: Iterable[str],
	output_file: str | Path,
) -> Path:
	"""Write a PDDL problem that reuses the base init state with a new goal."""

	base_problem = PDDLParser.parse_problem(base_problem_file)
	output_path = Path(output_file).expanduser().resolve()
	output_path.parent.mkdir(parents=True, exist_ok=True)
	goal_facts = tuple(_context_literal_to_fact(literal) for literal in goal_literals)
	output_path.write_text(
		_render_problem(
			problem_name=f"{base_problem.name}_transition_goal",
			domain_name=base_problem.domain_name,
			objects=tuple(base_problem.objects),
			object_types=base_problem.object_types,
			init_facts=tuple(base_problem.init_facts),
			goal_facts=goal_facts,
		),
		encoding="utf-8",
	)
	return output_path


def _context_literal_to_fact(literal: str) -> PDDLFact:
	text = str(literal or "").strip()
	is_positive = True
	if text.lower().startswith("not "):
		is_positive = False
		text = text[4:].strip()
	elif text.startswith("!"):
		is_positive = False
		text = text[1:].strip()
	if "(" not in text:
		return PDDLFact(predicate=text, args=[], is_positive=is_positive)
	if not text.endswith(")"):
		raise ValueError(f"Unsupported context literal for PDDL goal: {literal!r}")
	predicate, raw_args = text.split("(", 1)
	args = tuple(argument.strip() for argument in raw_args[:-1].split(",") if argument.strip())
	return PDDLFact(predicate=predicate.strip(), args=list(args), is_positive=is_positive)


def _render_problem(
	*,
	problem_name: str,
	domain_name: str,
	objects: Tuple[str, ...],
	object_types: dict[str, str],
	init_facts: Tuple[PDDLFact, ...],
	goal_facts: Tuple[PDDLFact, ...],
) -> str:
	lines = [
		f"(define (problem {problem_name})",
		f" (:domain {domain_name})",
		" (:objects",
	]
	lines.extend(_render_typed_objects(objects=objects, object_types=object_types))
	lines.extend(
		[
			" )",
			" (:init",
		],
	)
	for fact in init_facts:
		if fact.is_positive:
			lines.append(f"  {_render_fact(fact)}")
	lines.extend(
		[
			" )",
			" (:goal",
			"  (and",
		],
	)
	if goal_facts:
		for fact in goal_facts:
			lines.append(f"   {_render_fact(fact)}")
	else:
		lines.append("   (and)")
	lines.extend(
		[
			"  )",
			" )",
			")",
			"",
		],
	)
	return "\n".join(lines)


def _render_typed_objects(*, objects: Tuple[str, ...], object_types: dict[str, str]) -> list[str]:
	grouped: dict[str, list[str]] = {}
	for object_name in objects:
		grouped.setdefault(object_types.get(object_name, "object"), []).append(object_name)
	return [
		f"  {' '.join(names)} - {type_name}"
		for type_name, names in grouped.items()
		if names
	]


def _render_fact(fact: PDDLFact) -> str:
	atom = (
		f"({fact.predicate})"
		if not fact.args
		else f"({fact.predicate} {' '.join(fact.args)})"
	)
	return atom if fact.is_positive else f"(not {atom})"
