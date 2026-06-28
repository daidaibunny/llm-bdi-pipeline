"""
Validation helpers for temporal specifications and LTLf event extraction.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from utils.symbol_normalizer import SymbolNormalizer

from .models import ReferencedEvent, TemporalSpecificationRecord
from .pddl_mapping import EVENT_TO_FLUENT_BY_DOMAIN


_FORMULA_OPERATOR_SEQUENCE_PATTERN = re.compile(r"^(?:WX|[FGXURW])+$")
_TASK_EVENT_SUFFIX_PATTERN = re.compile(
	r"^(?P<base>[a-z_][a-z0-9_]*?)__(?:e|event)(?P<index>[1-9][0-9]*)$",
)
_RESERVED_FORMULA_TOKENS = {
	"true",
	"false",
	"F",
	"G",
	"X",
	"WX",
	"U",
	"R",
	"last",
}


def extract_formula_atoms_in_order(ltlf_formula: str) -> Tuple[str, ...]:
	"""Extract task-event atoms from one LTLf formula in source order."""

	ordered_atoms: List[str] = []
	invalid_tokens: set[str] = set()
	text = str(ltlf_formula or "")
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
		if token in _RESERVED_FORMULA_TOKENS or _FORMULA_OPERATOR_SEQUENCE_PATTERN.fullmatch(token):
			continue
		if index < len(text) and text[index] == "(":
			if token in _RESERVED_FORMULA_TOKENS or _FORMULA_OPERATOR_SEQUENCE_PATTERN.fullmatch(token):
				index += 1
				continue
			depth = 1
			index += 1
			while index < len(text) and depth > 0:
				if text[index] == "(":
					depth += 1
				elif text[index] == ")":
					depth -= 1
				index += 1
			token = text[start:index]
		if token.startswith("subgoal_") or token.startswith("query_step_"):
			invalid_tokens.add(token)
			continue
		ordered_atoms.append(token)
	if invalid_tokens:
		raise ValueError(
			"LTLf formula may not use placeholder atoms such as subgoal_* or query_step_*. "
			"Found: " + ", ".join(sorted(invalid_tokens)),
		)
	return tuple(ordered_atoms)


def parse_task_event_predicate_name(raw_predicate_name: str) -> Tuple[str, str, bool]:
	"""Split an event predicate into exact name, base task name, and suffix flag."""

	predicate_name = str(raw_predicate_name or "").strip()
	match = _TASK_EVENT_SUFFIX_PATTERN.fullmatch(predicate_name)
	if match is None:
		return predicate_name, predicate_name, False
	return predicate_name, str(match.group("base") or "").strip(), True


def referenced_events_from_formula(ltlf_formula: str) -> Tuple[ReferencedEvent, ...]:
	"""Build referenced-event records directly from the atoms in an LTLf formula."""

	normalizer = SymbolNormalizer()
	events: List[ReferencedEvent] = []
	for atom_expression in extract_formula_atoms_in_order(ltlf_formula):
		predicate_name, arguments = normalizer.parse_predicate_string(atom_expression)
		exact_event_name, _base_event_name, _ = parse_task_event_predicate_name(predicate_name)
		events.append(
			ReferencedEvent(
				event=exact_event_name,
				arguments=tuple(str(argument).strip() for argument in arguments if str(argument).strip()),
			),
		)
	return tuple(events)


def build_domain_event_name_map(domain: Any) -> Dict[str, str]:
	"""Build a raw-name lookup for PDDL events and mapped temporal fluents."""

	name_map: Dict[str, str] = {}
	for action in getattr(domain, "actions", ()) or ():
		action_name = str(getattr(action, "name", "") or "").strip()
		if action_name:
			name_map[action_name] = action_name
	for predicate in getattr(domain, "predicates", ()) or ():
		predicate_name = str(getattr(predicate, "name", "") or "").strip()
		if predicate_name:
			name_map[predicate_name] = predicate_name
	predicate_names = set(name_map)
	for mapping in EVENT_TO_FLUENT_BY_DOMAIN.values():
		for event_name, fluent_name in mapping.items():
			if fluent_name in predicate_names:
				name_map[event_name] = fluent_name
	return name_map


def validate_temporal_specification_record(
	record: TemporalSpecificationRecord,
	*,
	domain: Any,
) -> TemporalSpecificationRecord:
	"""Validate event references and enrich a temporal specification with extracted events."""

	if not record.instruction_id:
		raise ValueError("Temporal specification requires a non-empty instruction_id.")
	if not record.source_text:
		raise ValueError(f'Temporal specification "{record.instruction_id}" requires source_text.')
	if not record.ltlf_formula:
		raise ValueError(f'Temporal specification "{record.instruction_id}" requires ltlf_formula.')

	name_map = build_domain_event_name_map(domain)
	diagnostics: List[str] = [
		str(message).strip()
		for message in record.diagnostics
		if str(message).strip()
	]
	referenced_events = list(record.referenced_events or referenced_events_from_formula(record.ltlf_formula))
	if not referenced_events:
		raise ValueError(
			f'Temporal specification "{record.instruction_id}" does not reference any task events.',
		)

	validated_events: List[ReferencedEvent] = []
	for event in referenced_events:
		event_name = str(event.event or "").strip()
		if not event_name:
			continue
		_exact_name, base_event_name, has_explicit_suffix = parse_task_event_predicate_name(event_name)
		if base_event_name not in name_map:
			raise ValueError(
				f'Temporal specification "{record.instruction_id}" references unknown event '
				f'"{base_event_name}".',
			)
		if has_explicit_suffix:
			diagnostics.append(f"Repeated event identity preserved for {event_name}.")
		validated_events.append(
			ReferencedEvent(
				event=event_name,
				arguments=tuple(str(argument).strip() for argument in event.arguments if str(argument).strip()),
			),
		)

	return TemporalSpecificationRecord(
		instruction_id=record.instruction_id,
		source_text=record.source_text,
		ltlf_formula=record.ltlf_formula,
		referenced_events=tuple(validated_events),
		diagnostics=tuple(dict.fromkeys(diagnostics)),
		problem_file=record.problem_file,
	)


def build_domain_predicate_arity_map(domain: Any) -> Dict[str, int]:
	"""Map each declared PDDL predicate name to its declared arity."""

	arity_map: Dict[str, int] = {}
	for predicate in getattr(domain, "predicates", ()) or ():
		predicate_name = str(getattr(predicate, "name", "") or "").strip()
		if predicate_name:
			arity_map[predicate_name] = len(getattr(predicate, "parameters", ()) or ())
	return arity_map


def build_domain_action_name_set(domain: Any) -> set[str]:
	"""Collect declared PDDL action names for fluent-vs-action atom rejection."""

	action_names: set[str] = set()
	for action in getattr(domain, "actions", ()) or ():
		action_name = str(getattr(action, "name", "") or "").strip()
		if action_name:
			action_names.add(action_name)
	return action_names


def validate_predicate_grounded_temporal_specification(
	record: TemporalSpecificationRecord,
	*,
	domain: Any,
) -> TemporalSpecificationRecord:
	"""Validate that every LTLf atom is a declared PDDL fluent, not an action.

	This is the goal-specification contract from BDI.md: the domain-level ASL
	library implements predicate achievement goals (``!on(X, Y)``), so generated
	LTLf atoms must be domain predicates such as ``on(b4, b2)``, never action or
	event names such as ``do_put_on(b4, b2)``.
	"""

	if not record.instruction_id:
		raise ValueError("Temporal specification requires a non-empty instruction_id.")
	if not record.source_text:
		raise ValueError(f'Temporal specification "{record.instruction_id}" requires source_text.')
	if not record.ltlf_formula:
		raise ValueError(f'Temporal specification "{record.instruction_id}" requires ltlf_formula.')

	predicate_arity_map = build_domain_predicate_arity_map(domain)
	action_names = build_domain_action_name_set(domain)
	referenced_events = referenced_events_from_formula(record.ltlf_formula)
	if not referenced_events:
		raise ValueError(
			f'Temporal specification "{record.instruction_id}" does not reference any predicate atoms.',
		)

	validated_events: List[ReferencedEvent] = []
	for event in referenced_events:
		predicate_name = str(event.event or "").strip()
		if not predicate_name:
			continue
		if predicate_name in action_names and predicate_name not in predicate_arity_map:
			raise ValueError(
				f'Temporal specification "{record.instruction_id}" uses action name '
				f'"{predicate_name}" as an LTLf atom. Atoms must be PDDL fluents '
				f"(predicates), not actions.",
			)
		if predicate_name not in predicate_arity_map:
			raise ValueError(
				f'Temporal specification "{record.instruction_id}" references unknown '
				f'predicate "{predicate_name}".',
			)
		expected_arity = predicate_arity_map[predicate_name]
		if len(event.arguments) != expected_arity:
			raise ValueError(
				f'Temporal specification "{record.instruction_id}" atom "{predicate_name}" '
				f"uses {len(event.arguments)} arguments but predicate arity is {expected_arity}.",
			)
		validated_events.append(event)

	diagnostics = tuple(
		dict.fromkeys(
			str(message).strip()
			for message in record.diagnostics
			if str(message).strip()
		),
	)
	return TemporalSpecificationRecord(
		instruction_id=record.instruction_id,
		source_text=record.source_text,
		ltlf_formula=record.ltlf_formula,
		referenced_events=tuple(validated_events),
		diagnostics=diagnostics,
		problem_file=record.problem_file,
	)


def normalise_temporal_specification_payloads(
	payloads: Sequence[Dict[str, Any]],
	*,
	domain: Any,
) -> Tuple[TemporalSpecificationRecord, ...]:
	"""Convert raw payloads into validated temporal-specification records."""

	return tuple(
		validate_temporal_specification_record(
			TemporalSpecificationRecord.from_dict(payload),
			domain=domain,
		)
		for payload in payloads
	)
