"""
Adapt DFA transition guards into domain-level achievement-goal requests.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep
from utils.pddl_parser import PDDLParser


@dataclass(frozen=True)
class DFAAchievementRequest:
	"""Achievement-goal request issued by a DFA transition guard."""

	raw_guard: str
	state_literals: tuple[str, ...]
	goal_facts: tuple[str, ...]
	body_steps: tuple[AgentSpeakBodyStep, ...]
	source_state: str | None = None
	target_state: str | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"raw_guard": self.raw_guard,
			"source_state": self.source_state,
			"target_state": self.target_state,
			"state_literals": list(self.state_literals),
			"goal_facts": list(self.goal_facts),
			"achievement_subgoals": [
				step.to_dict() for step in self.body_steps
			],
		}


@dataclass(frozen=True)
class DFAGuardAdaptationDiagnostic:
	"""Structured support diagnostic for one DFA guard adaptation attempt."""

	raw_guard: str
	supported: bool
	state_literals: tuple[str, ...]
	request: DFAAchievementRequest | None = None
	rejection_reason: str | None = None
	message: str | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"raw_guard": self.raw_guard,
			"supported": self.supported,
			"rejection_reason": self.rejection_reason,
			"message": self.message,
			"state_literals": list(self.state_literals),
			"request": self.request.to_dict() if self.request is not None else None,
		}


def adapt_dfa_guarded_transition_to_achievement_request(
	transition: Mapping[str, object],
	*,
	domain_key: str,
	domain_file: str | Path | None = None,
	declared_predicates: Sequence[object] | Mapping[str, int | None] = (),
) -> DFAAchievementRequest:
	"""Adapt one DFA guarded transition into achievement-goal requests."""

	request = adapt_dfa_guard_to_achievement_request(
		str(transition.get("raw_label") or "true"),
		domain_key=domain_key,
		domain_file=domain_file,
		declared_predicates=declared_predicates,
	)
	return DFAAchievementRequest(
		raw_guard=request.raw_guard,
		state_literals=request.state_literals,
		goal_facts=request.goal_facts,
		body_steps=request.body_steps,
		source_state=_optional_text(transition.get("source_state")),
		target_state=_optional_text(transition.get("target_state")),
	)


def adapt_dfa_guard_to_achievement_request(
	raw_guard: str,
	*,
	domain_key: str,
	domain_file: str | Path | None = None,
	declared_predicates: Sequence[object] | Mapping[str, int | None] = (),
) -> DFAAchievementRequest:
	"""Translate a positive conjunctive DFA guard into achievement requests.

	The current ASL append contract requires singleton-literal progress guards,
	but this adapter deliberately accepts positive conjunctions for diagnostics
	and offline controller validation. Negative, false, or disjunctive guards are
	rejected instead of being compiled into query-specific low-level plans.
	"""

	_ = domain_key
	diagnostic = inspect_dfa_guard_to_achievement_request(
		raw_guard,
		domain_key=domain_key,
		domain_file=domain_file,
		declared_predicates=declared_predicates,
	)
	if diagnostic.request is None:
		raise ValueError(diagnostic.message or "DFA guard adaptation failed.")
	return diagnostic.request


def inspect_dfa_guard_to_achievement_request(
	raw_guard: str,
	*,
	domain_key: str,
	domain_file: str | Path | None = None,
	declared_predicates: Sequence[object] | Mapping[str, int | None] = (),
) -> DFAGuardAdaptationDiagnostic:
	"""Return a structured diagnostic for adapting one DFA guard."""

	_ = domain_key
	normalized_guard = str(raw_guard or "").strip() or "true"
	raw_rejection_reason = _unsupported_raw_guard_reason(normalized_guard)
	if raw_rejection_reason is not None:
		message = (
			"DFA guard adapter currently supports positive conjunctive "
			f"achievement requests only; received {raw_guard!r}."
		)
		return DFAGuardAdaptationDiagnostic(
			raw_guard=normalized_guard,
			supported=False,
			state_literals=(),
			rejection_reason=raw_rejection_reason,
			message=message,
		)
	state_literals = _pddl_context_literals_from_guard(normalized_guard)
	if any(_is_unsupported_literal(literal) for literal in state_literals):
		message = (
			"DFA guard adapter currently supports positive conjunctive "
			f"achievement requests only; received {raw_guard!r}."
		)
		return DFAGuardAdaptationDiagnostic(
			raw_guard=normalized_guard,
			supported=False,
			state_literals=state_literals,
			rejection_reason=_unsupported_literal_reason(state_literals),
			message=message,
		)
	try:
		parsed_atoms = tuple(_parse_atom(literal) for literal in state_literals)
		_validate_guard_atoms(
			parsed_atoms,
			declared_predicates=_predicate_arities(
				domain_file=domain_file,
				declared_predicates=declared_predicates,
			),
		)
	except ValueError as error:
		return DFAGuardAdaptationDiagnostic(
			raw_guard=normalized_guard,
			supported=False,
			state_literals=state_literals,
			rejection_reason=_schema_rejection_reason(str(error)),
			message=str(error),
		)
	request = DFAAchievementRequest(
		raw_guard=normalized_guard,
		state_literals=state_literals,
		goal_facts=tuple(
			_call(f"goal_{predicate}", arguments)
			for predicate, arguments in parsed_atoms
		),
		body_steps=tuple(
			AgentSpeakBodyStep("subgoal", predicate, arguments)
			for predicate, arguments in parsed_atoms
		),
	)
	return DFAGuardAdaptationDiagnostic(
		raw_guard=normalized_guard,
		supported=True,
		state_literals=state_literals,
		request=request,
	)


def _is_unsupported_literal(literal: str) -> bool:
	text = str(literal or "").strip()
	return (
		not text
		or text.lower() == "false"
		or text.lower().startswith("not ")
		or "|" in text
	)


def _unsupported_raw_guard_reason(raw_guard: str) -> str | None:
	text = str(raw_guard or "").strip().lower()
	if text == "false":
		return "unsupported_false_guard"
	if "|" in str(raw_guard or "") or " or " in f" {str(raw_guard or '').lower()} ":
		return "unsupported_disjunctive_guard"
	return None


def _pddl_context_literals_from_guard(raw_guard: str) -> tuple[str, ...]:
	text = str(raw_guard or "").strip()
	if not text or text.lower() == "true":
		return ()
	return tuple(
		literal
		for literal in (
			_normalise_literal_text(part)
			for part in _split_top_level_conjunction(text)
		)
		if literal and literal != "true"
	)


def _split_top_level_conjunction(raw_guard: str) -> tuple[str, ...]:
	parts: list[str] = []
	start = 0
	depth = 0
	for index, character in enumerate(str(raw_guard or "")):
		if character == "(":
			depth += 1
		elif character == ")":
			depth = max(0, depth - 1)
		elif character == "&" and depth == 0:
			parts.append(raw_guard[start:index].strip())
			start = index + 1
	parts.append(str(raw_guard or "")[start:].strip())
	return tuple(part for part in parts if part)


def _normalise_literal_text(raw_literal: str) -> str:
	text = _strip_balanced_parentheses(str(raw_literal or "").strip())
	polarity = ""
	for prefix in ("not ", "!", "~"):
		if text.lower().startswith(prefix):
			polarity = "not "
			text = text[len(prefix) :].strip()
			break
	text = _strip_balanced_parentheses(text)
	if not text or text.lower() in {"true", "false"}:
		return f"{polarity}{text.lower()}".strip()
	predicate, arguments = _parse_atom(text)
	normalised_atom = _call(predicate, arguments)
	return f"{polarity}{normalised_atom}" if polarity else normalised_atom


def _strip_balanced_parentheses(text: str) -> str:
	current = str(text or "").strip()
	while current.startswith("(") and current.endswith(")") and _outer_parentheses_wrap(current):
		current = current[1:-1].strip()
	return current


def _outer_parentheses_wrap(text: str) -> bool:
	depth = 0
	for index, character in enumerate(text):
		if character == "(":
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0 and index != len(text) - 1:
				return False
			if depth < 0:
				return False
	return depth == 0


def _unsupported_literal_reason(literals: Sequence[str]) -> str:
	if any(str(literal or "").strip().lower() == "false" for literal in literals):
		return "unsupported_false_guard"
	if any("|" in str(literal or "") for literal in literals):
		return "unsupported_disjunctive_guard"
	if any(str(literal or "").strip().lower().startswith("not ") for literal in literals):
		return "unsupported_negative_guard"
	return "unsupported_guard_literal"


def _parse_atom(atom: str) -> tuple[str, tuple[str, ...]]:
	text = str(atom or "").strip()
	if "(" not in text:
		return text, ()
	if not text.endswith(")"):
		raise ValueError(f"Invalid DFA guard atom for achievement request: {atom!r}.")
	predicate, raw_arguments = text.split("(", 1)
	return (
		predicate.strip(),
		tuple(
			argument.strip()
			for argument in raw_arguments[:-1].split(",")
			if argument.strip()
		),
	)


def _validate_guard_atoms(
	parsed_atoms: Sequence[tuple[str, tuple[str, ...]]],
	*,
	declared_predicates: Mapping[str, int | None],
) -> None:
	if not declared_predicates:
		return
	for predicate, arguments in parsed_atoms:
		if predicate not in declared_predicates:
			raise ValueError(
				f"DFA guard references undeclared PDDL predicate {predicate!r}.",
			)
		declared_arity = declared_predicates[predicate]
		if declared_arity is not None and declared_arity != len(arguments):
			raise ValueError(
				(
					"DFA guard references PDDL predicate "
					f"{predicate}/{declared_arity} with wrong arity {len(arguments)}."
				),
			)


def _predicate_arities(
	*,
	domain_file: str | Path | None,
	declared_predicates: Sequence[object] | Mapping[str, int | None],
) -> Mapping[str, int | None]:
	arities: dict[str, int | None] = {}
	if domain_file is not None:
		arities.update(_declared_arities(PDDLParser.parse_domain(domain_file).predicates))
	arities.update(_declared_arities(declared_predicates))
	return arities


def _declared_arities(
	symbols: Sequence[object] | Mapping[str, int | None],
) -> dict[str, int | None]:
	if isinstance(symbols, Mapping):
		return {str(name): arity for name, arity in symbols.items()}
	arities: dict[str, int | None] = {}
	for symbol in tuple(symbols or ()):
		name = getattr(symbol, "name", None)
		if name is not None:
			parameters = getattr(symbol, "parameters", None)
			arities[str(name)] = None if parameters is None else len(tuple(parameters))
			continue
		arities[str(symbol)] = None
	return arities


def _call(predicate: str, arguments: Sequence[str]) -> str:
	args = tuple(arguments)
	return predicate if not args else f"{predicate}({', '.join(args)})"


def _optional_text(value: object) -> str | None:
	text = str(value or "").strip()
	return text or None


def _schema_rejection_reason(message: str) -> str:
	if "undeclared PDDL predicate" in message:
		return "undeclared_pddl_predicate"
	if "wrong arity" in message:
		return "wrong_pddl_predicate_arity"
	if "Invalid DFA guard atom" in message:
		return "invalid_guard_atom"
	return "unsupported_guard_schema"
