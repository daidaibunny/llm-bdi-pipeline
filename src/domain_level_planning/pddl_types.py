"""
PDDL type helpers for lifted domain-level planning.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence


def parameter_name(parameter: str) -> str:
	text = str(parameter or "").strip()
	if " - " in text:
		text = text.split(" - ", 1)[0].strip()
	return text


def parameter_type(parameter: str) -> str:
	text = str(parameter or "").strip()
	if " - " not in text:
		return "object"
	return text.split(" - ", 1)[1].strip() or "object"


def type_guard_symbol(type_name: str) -> str:
	return f"type_{str(type_name or '').strip()}"


def declared_type_names(type_tokens: Sequence[str]) -> tuple[str, ...]:
	parent_map = type_parent_map(type_tokens)
	return tuple(
		name
		for name in dict.fromkeys((*parent_map.keys(), *parent_map.values()))
		if name and name != "object"
	)


def type_parent_map(type_tokens: Sequence[str]) -> dict[str, str]:
	parent_by_type: dict[str, str] = {}
	pending: list[str] = []
	tokens = tuple(str(token).strip() for token in tuple(type_tokens or ()) if str(token).strip())
	index = 0
	while index < len(tokens):
		token = tokens[index]
		if token == "-" and index + 1 < len(tokens):
			parent = tokens[index + 1]
			for type_name in pending:
				parent_by_type[type_name] = parent
			pending = []
			index += 2
			continue
		pending.append(token)
		index += 1
	for type_name in pending:
		parent_by_type.setdefault(type_name, "object")
	return parent_by_type


def type_closure(type_name: str, type_tokens: Sequence[str]) -> tuple[str, ...]:
	parent_by_type = type_parent_map(type_tokens)
	return _type_closure_from_parent_map(type_name, parent_by_type)


def object_type_atoms(problem: object, type_tokens: Sequence[str]) -> tuple[str, ...]:
	parent_by_type = type_parent_map(type_tokens)
	object_types = dict(getattr(problem, "object_types", {}) or {})
	atoms: list[str] = []
	for object_name in tuple(getattr(problem, "objects", ()) or ()):
		for type_name in _type_closure_from_parent_map(
			object_types.get(object_name, "object"),
			parent_by_type,
		):
			if type_name == "object":
				continue
			atoms.append(_call(type_guard_symbol(type_name), (str(object_name),)))
	return tuple(dict.fromkeys(atoms))


def object_belongs_to_type(
	object_name: str,
	*,
	object_types: Mapping[str, str],
	requested_type: str,
	type_tokens: Sequence[str],
) -> bool:
	normalized_type = str(requested_type or "").strip() or "object"
	if normalized_type == "object":
		return True
	closure = _type_closure_from_parent_map(
		object_types.get(object_name, "object"),
		type_parent_map(type_tokens),
	)
	return normalized_type in closure


def _type_closure_from_parent_map(
	type_name: str,
	parent_by_type: Mapping[str, str],
) -> tuple[str, ...]:
	closure: list[str] = []
	current = str(type_name or "").strip() or "object"
	seen: set[str] = set()
	while current and current not in seen:
		seen.add(current)
		closure.append(current)
		if current == "object":
			break
		current = parent_by_type.get(current, "object")
	if "object" not in closure:
		closure.append("object")
	return tuple(closure)


def _call(symbol: str, arguments: Iterable[str]) -> str:
	args = tuple(arguments)
	return symbol if not args else f"{symbol}({', '.join(args)})"
