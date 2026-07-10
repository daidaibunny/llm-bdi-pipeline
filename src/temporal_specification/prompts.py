"""Final prompt contract for controlled English to lifted LTLf translation.

The public natural-language manifest supplies already-declared lifted parameters.
The model translates temporal meaning only: it neither chooses variables nor
grounds them to objects. Formulae use propositional atom identifiers so the
LTLf2DFA/MONA input remains independent of PDDL punctuation and variable case.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields, replace
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class PromptConfig:
	"""Detachable components retained for full/baseline/ablation evaluation."""

	normal_form: bool = True
	few_shot: bool = True
	variable_rules: bool = True
	operator_whitelist: bool = True
	error_guidance: bool = True

	@property
	def name(self) -> str:
		disabled = [item.name for item in fields(self) if not getattr(self, item.name)]
		if not disabled:
			return "full"
		if len(disabled) == len(fields(self)):
			return "baseline"
		if len(disabled) == 1:
			return f"no_{disabled[0]}"
		return "custom_" + "-".join(sorted(disabled))

	@classmethod
	def from_name(cls, name: str) -> PromptConfig:
		"""Parse one stable prompt-variant name."""

		text = str(name or "").strip().lower()
		if text in {"", "full"}:
			return FULL_PROMPT_CONFIG
		if text == "baseline":
			return BASELINE_PROMPT_CONFIG
		if text.startswith("no_"):
			return ablation_config(text[3:])
		raise ValueError(
			f"unknown prompt config {name!r}; expected full, baseline, or "
			f"no_<component> for one of {PROMPT_COMPONENTS}",
		)


PROMPT_COMPONENTS = tuple(item.name for item in fields(PromptConfig))
FULL_PROMPT_CONFIG = PromptConfig()
BASELINE_PROMPT_CONFIG = PromptConfig(
	**{component: False for component in PROMPT_COMPONENTS},
)


def ablation_config(component: str) -> PromptConfig:
	"""Return the full prompt with exactly one component disabled."""

	key = str(component or "").strip().lower()
	if key not in PROMPT_COMPONENTS:
		raise ValueError(
			f"unknown prompt component {component!r}; expected one of "
			f"{PROMPT_COMPONENTS}",
		)
	return replace(FULL_PROMPT_CONFIG, **{key: False})


def build_lifted_ltlf_system_prompt(
	catalog: Mapping[str, Any],
	config: PromptConfig = FULL_PROMPT_CONFIG,
) -> str:
	"""Build the final NL-to-lifted-LTLf system prompt from a public catalogue."""

	domain = _required_text(catalog, "domain")
	predicate_lines = _predicate_lines(catalog.get("predicates"))
	function_lines = _function_lines(catalog.get("numeric_functions"))
	constant_lines = _constant_lines(catalog.get("constants"))
	type_lines = _type_lines(catalog.get("type_parents"))
	lines = [
		"You translate one controlled natural-language temporal goal into lifted "
		"Linear Temporal Logic on finite traces (LTLf).",
		f"Planning domain: {domain}",
		"Your only task is semantic translation. Do not plan or execute actions. "
		"Do not ground lifted parameters or choose problem objects.",
		"",
		"PUBLIC PDDL CATALOGUE",
		"Predicates:",
		*(predicate_lines or ["  - (none)"]),
		"Numeric functions:",
		*(function_lines or ["  - (none)"]),
		"Domain constants:",
		*(constant_lines or ["  - (none)"]),
		"Type hierarchy (child <: parent):",
		*(type_lines or ["  - (none declared)"]),
		"",
		"ATOM TABLE CONTRACT",
		"- The LTLf formula uses only propositional symbols a0, a1, a2, ... .",
		"- Define every symbol exactly once in atoms, in first-formula-occurrence "
		"order, and define no unused atom.",
		"- A predicate atom has keys symbol, kind, predicate, and args.",
		"- A numeric equality atom has keys symbol, kind, function, args, and value; "
		"value must be an integer explicitly requested by the query.",
		"- Use only predicates, numeric functions, constants, parameter names, and "
		"arities from this prompt and the user message.",
	]

	if config.variable_rules:
		lines += [
			"",
			"LIFTED PARAMETER CONTRACT",
			"- Copy declared_parameters and constraints byte-for-byte in meaning and "
			"preserve each parameter's exact case-sensitive name.",
			"- Every non-constant atom argument must be one declared parameter. Do not "
			"invent, omit, rename, merge, or ground parameters.",
			"- Check each argument against the declared PDDL type, including subtype "
			"membership from the catalogue.",
			"- External constraints describe legal later assignments. They are copied "
			"as metadata and are not LTLf propositions.",
		]

	if config.operator_whitelist:
		lines += [
			"",
			"BENCHMARK-V1 OPERATOR CONTRACT",
			"- Allowed operators are exactly F, X, U, &, and !.",
			"- F means eventually on the finite trace; X means the immediate next "
			"state; U is strong until and requires its right operand eventually.",
			"- Parentheses must make grouping explicit.",
			"- Forbidden: disjunction |, global G, release R, weak-next WX, implication, "
			"equivalence, quantifiers, and every unlisted operator.",
		]

	if config.normal_form:
		lines += [
			"",
			"BENCHMARK-V1 TEMPORAL STRUCTURES",
			"Translate the query's wording, not any hidden profile label:",
			"- Same-state conjunction: F(a0 & a1).",
			"- Same-state positive and negative condition: F(a0 & !a1).",
			"- Strictly ordered two milestones: F(a0 & X(F(a1))).",
			"- Strictly ordered three milestones: "
			"F(a0 & X(F(a1 & X(F(a2))))).",
			"- Persistence through the first state where a milestone occurs: a0 U a1.",
			"'Strictly later' always requires at least one next-state step; do not "
			"weaken it to F(a0 & F(a1)).",
		]

	if config.few_shot:
		lines += [
			"",
			"SCHEMATIC EXAMPLES",
			"- 'At some state, both the first and second stated conditions' -> "
			"F(a0 & a1).",
			"- 'The first stated condition, then strictly later the second' -> "
			"F(a0 & X(F(a1))).",
			"- 'The first stated condition continues until the second' -> a0 U a1.",
			"The atom table, not these structural examples, supplies the current "
			"domain's exact PDDL symbols.",
		]

	lines += [
		"",
		"OUTPUT CONTRACT",
		"Return JSON only, with exactly these eight top-level keys:",
		"schema_version, sample_id, temporal_logic, ltlf_formula, atoms, "
		"declared_parameters, constraints, status.",
		"Use schema_version 1, temporal_logic LTLf, and status supported.",
		"Predicate atom entry shape:",
		'{"symbol": "a0", "kind": "predicate", '
		'"predicate": "<one listed predicate name>", '
		'"args": ["<declared parameter or domain constant>"]}',
		"Numeric atom entry shape:",
		'{"symbol": "a0", "kind": "numeric_equality", '
		'"function": "<one listed numeric function name>", '
		'"args": ["<declared parameter or domain constant>"], "value": 1}',
		"Copy sample_id, declared_parameters, and constraints exactly from the user "
		"message; choose only ltlf_formula and its atoms table.",
		"Do not add prose, markdown, confidence scores, explanations, object names, "
		"or extra keys.",
	]

	if config.error_guidance:
		lines += [
			"",
			"RETRY CONTRACT",
			"A later user message may provide the previous formula plus one "
			"model-correctable schema, syntax, vocabulary, arity, type, parameter, "
			"operator, atom-table, or semantic error. Correct only that translation "
			"and return the same eight-key JSON schema. Infrastructure failures are "
			"never translation instructions.",
		]

	return "\n".join(lines)


def build_lifted_ltlf_user_prompt(sample: Mapping[str, Any]) -> str:
	"""Build one leak-free user message from a public natural-language row."""

	status = _required_text(sample, "status")
	if status != "constructed_temporal_query":
		raise ValueError(
			"NL-to-LTLf prompts require status constructed_temporal_query; "
			f"received {status!r}",
		)
	parameter_semantics = _required_text(sample, "parameter_semantics")
	if parameter_semantics != "externally_bound":
		raise ValueError(
			"parameter_semantics must be externally_bound for lifted translation",
		)
	payload = {
		"sample_id": _required_text(sample, "sample_id"),
		"source_text": _required_text(sample, "source_text"),
		"declared_parameters": _json_sequence(sample, "declared_parameters"),
		"constraints": _json_sequence(sample, "constraints"),
		"parameter_semantics": parameter_semantics,
	}
	return "\n".join(
		[
			"Translate this public benchmark row. The source text is the sole source "
			"of temporal structure; metadata omitted here must not be inferred.",
			json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
			"Return the required eight-key JSON object now.",
		]
	)


def build_retry_user_message(feedback: Mapping[str, Any]) -> str:
	"""Render model-correctable validation feedback as one retry message."""

	required = {
		"previous_ltlf",
		"error_type",
		"error_detail",
		"hint",
		"attempt",
	}
	missing = required.difference(feedback)
	if missing:
		raise ValueError(f"retry feedback is missing keys: {sorted(missing)}")
	payload = {key: feedback[key] for key in sorted(required)}
	return "\n".join(
		[
			"The previous translation failed a model-correctable validation check:",
			json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
			"Apply the stated correction while preserving the source query, declared "
			"parameters, and constraints. Return the same eight-key JSON schema only.",
		]
	)


def _required_text(payload: Mapping[str, Any], key: str) -> str:
	value = str(payload.get(key) or "").strip()
	if not value:
		raise ValueError(f"{key} must be a non-empty string")
	return value


def _json_sequence(payload: Mapping[str, Any], key: str) -> list[Any]:
	value = payload.get(key)
	if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
		raise ValueError(f"{key} must be a JSON array")
	return list(value)


def _predicate_lines(raw: Any) -> list[str]:
	return _signature_lines(raw, symbol_key="name")


def _function_lines(raw: Any) -> list[str]:
	return _signature_lines(raw, symbol_key="name")


def _signature_lines(raw: Any, *, symbol_key: str) -> list[str]:
	if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
		return []
	lines: list[str] = []
	for item in raw:
		if not isinstance(item, Mapping):
			continue
		name = str(item.get(symbol_key) or "").strip()
		argument_types = item.get("argument_types")
		if not name or not isinstance(argument_types, Sequence):
			continue
		arguments = ", ".join(str(value).strip() for value in argument_types)
		lines.append(f"  - {name}({arguments})" if arguments else f"  - {name}")
	return lines


def _constant_lines(raw: Any) -> list[str]:
	if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
		return []
	lines: list[str] = []
	for item in raw:
		if isinstance(item, Mapping):
			name = str(item.get("name") or "").strip()
			pddl_type = str(item.get("pddl_type") or "object").strip()
			if name:
				lines.append(f"  - {name} : {pddl_type}")
		elif str(item).strip():
			lines.append(f"  - {str(item).strip()} : object")
	return lines


def _type_lines(raw: Any) -> list[str]:
	if not isinstance(raw, Mapping):
		return []
	return [
		f"  - {str(child).strip()} <: {str(parent).strip()}"
		for child, parent in sorted(raw.items())
		if str(child).strip() and str(parent).strip()
	]
