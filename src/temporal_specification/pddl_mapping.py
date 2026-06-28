"""
Map stored temporal events onto PDDL fluents.
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

from utils.symbol_normalizer import SymbolNormalizer


EVENT_TO_FLUENT_BY_DOMAIN: Dict[str, Dict[str, str]] = {
	"blocksworld": {
		"do_put_on": "on",
		"do_move": "on",
		"do_on_table": "on-table",
		"do_clear": "clear",
	},
	"blocks": {
		"do_put_on": "on",
		"do_move": "on",
		"do_on_table": "on-table",
		"do_clear": "clear",
	},
	"marsrover": {
		"get_soil_data": "communicated_soil_data",
		"get_rock_data": "communicated_rock_data",
		"get_image_data": "communicated_image_data",
	},
	"rover": {
		"get_soil_data": "communicated_soil_data",
		"get_rock_data": "communicated_rock_data",
		"get_image_data": "communicated_image_data",
	},
	"satellite": {
		"do_observation": "have_image",
	},
	"satellite2": {
		"do_observation": "have_image",
	},
	"transport": {
		"deliver": "at",
	},
}


def event_to_fluent_name(event_name: str, *, domain_key: str | None = None) -> str:
	"""Return the PDDL fluent predicate that represents one stored temporal event."""

	name = str(event_name or "").strip()
	if not name:
		return ""
	domain_map = EVENT_TO_FLUENT_BY_DOMAIN.get(str(domain_key or "").strip().lower(), {})
	if name in domain_map:
		return domain_map[name]
	for mapping in EVENT_TO_FLUENT_BY_DOMAIN.values():
		if name in mapping:
			return mapping[name]
	return name


def map_event_atom_to_pddl_fluent(
	atom: str,
	*,
	domain_key: str | None = None,
) -> str:
	"""Map a stored LTLf atom, possibly flattened, to a PDDL fluent atom."""

	text = str(atom or "").strip()
	if not text:
		return ""
	is_negative = False
	for prefix in ("not ", "~", "!"):
		if text.lower().startswith(prefix):
			is_negative = True
			text = text[len(prefix) :].strip()
			break

	event_name, arguments = _parse_event_atom(text, domain_key=domain_key)
	fluent_name = event_to_fluent_name(event_name, domain_key=domain_key)
	if arguments:
		fluent_atom = f"{fluent_name}({', '.join(arguments)})"
	else:
		fluent_atom = fluent_name
	return f"not {fluent_atom}" if is_negative else fluent_atom


def map_event_expression_to_pddl_context(
	expression: str,
	*,
	domain_key: str | None = None,
) -> Tuple[str, ...]:
	"""Map an and/not DFA guard expression into AgentSpeak context literals."""

	text = str(expression or "").strip()
	if not text or text.lower() == "true":
		return ()
	if text.lower() == "false":
		return ("false",)
	context_literals = []
	for raw_part in re.split(r"\s*&\s*", text):
		part = raw_part.strip()
		if not part:
			continue
		while part.startswith("(") and part.endswith(")") and _balanced_inner(part):
			part = part[1:-1].strip()
		context_literals.append(
			map_event_atom_to_pddl_fluent(part, domain_key=domain_key),
		)
	return tuple(literal for literal in context_literals if literal)


def _parse_event_atom(atom: str, *, domain_key: str | None) -> Tuple[str, Tuple[str, ...]]:
	normalizer = SymbolNormalizer()
	predicate_name, arguments = normalizer.parse_predicate_string(atom)
	if arguments:
		return predicate_name, tuple(arguments)

	restored = normalizer.restore_symbol_hyphens(atom)
	domain_map = EVENT_TO_FLUENT_BY_DOMAIN.get(str(domain_key or "").strip().lower(), {})
	known_event_names = tuple(
		sorted(
			set(domain_map) | {name for mapping in EVENT_TO_FLUENT_BY_DOMAIN.values() for name in mapping},
			key=len,
			reverse=True,
		),
	)
	for event_name in known_event_names:
		prefix = f"{event_name}_"
		if restored == event_name:
			return event_name, ()
		if restored.startswith(prefix):
			return event_name, tuple(part for part in restored[len(prefix) :].split("_") if part)
	return restored, ()


def _balanced_inner(text: str) -> bool:
	depth = 0
	for index, character in enumerate(text):
		if character == "(":
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0 and index != len(text) - 1:
				return False
	return depth == 0
