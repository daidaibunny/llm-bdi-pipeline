"""Natural-language to LTLf goal-specification generation.

This is the goal-specification layer described in BDI.md (sections 2, 3, 5, 6).
For any supported domain and any goal, a SOTA language model converts a single
natural-language instruction into one LTLf formula whose atoms are PDDL fluents
(predicates), never action or event names.

LTLf is the single goal-specification surface:

- A temporal extended goal (TEG) uses temporal operators, e.g.
  ``F(on(b4, b2) & X(F(on(b1, b4))))``.
- A plain achievement goal degenerates to a pure conjunction with no temporal
  operators, e.g. ``on(b4, b2) & on(b3, b1)``.

The generator is domain-generic: it derives every legal atom from the parsed PDDL
domain, so adding a new supported domain requires no code change here.
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional, Sequence

from language_model import (
	create_openai_compatible_client,
	create_openai_compatible_json_completion,
)
from temporal_specification.models import TemporalSpecificationRecord
from temporal_specification.validation import (
	validate_predicate_grounded_temporal_specification,
)
from utils.config import Config, get_config

_RETRYABLE_ERROR_CLASS_NAMES = {
	"timeouterror",
	"apitimeouterror",
	"apiconnectionerror",
	"readtimeout",
	"connecttimeout",
	"pooltimeout",
	"readerror",
	"connecterror",
	"remoteprotocolerror",
	"networkerror",
}
_MAX_TRANSPORT_RETRIES = 3


class NLToLTLfEmptyResponseError(RuntimeError):
	"""The provider returned no usable completion text."""


class NLToLTLfMalformedResponseError(ValueError):
	"""The model returned text, but it was not valid NL-to-LTLf JSON."""


class NLToLTLfGenerator:
	"""Convert one natural-language query into one predicate-grounded LTLf formula."""

	def __init__(
		self,
		*,
		model: Optional[str] = None,
		api_key: Optional[str] = None,
		base_url: Optional[str] = None,
		timeout: Optional[float] = None,
		max_tokens: Optional[int] = None,
		config: Optional[Config] = None,
		client: Any | None = None,
	) -> None:
		active_config = config or get_config()
		self.model = str(model or active_config.ltlf_generation_model)
		self.request_timeout = float(timeout or active_config.ltlf_generation_timeout)
		self.response_max_tokens = int(max_tokens or active_config.ltlf_generation_max_tokens)
		if client is not None:
			self.client = client
		else:
			resolved_api_key = api_key or active_config.ltlf_generation_api_key
			if not resolved_api_key:
				raise ValueError(
					"NL-to-LTLf generation requires an API key. Set LTLF_GENERATION_API_KEY "
					"or LANGUAGE_MODEL_API_KEY, or pass an explicit client.",
				)
			self.client = create_openai_compatible_client(
				api_key=resolved_api_key,
				base_url=base_url or active_config.ltlf_generation_base_url,
				timeout=self.request_timeout,
			)

	def generate(
		self,
		*,
		domain: Any,
		instruction: str,
		instruction_id: str | None = None,
		problem_file: str | None = None,
	) -> TemporalSpecificationRecord:
		"""Generate and validate one predicate-grounded LTLf temporal specification."""

		source_text = str(instruction or "").strip()
		if not source_text:
			raise ValueError("NL-to-LTLf generation requires a non-empty instruction.")

		messages = [
			{"role": "system", "content": build_system_prompt(domain)},
			{"role": "user", "content": f"Goal: {source_text}"},
		]
		payload = self._request_json(messages)
		ltlf_formula = str(payload.get("ltlf_formula") or "").strip()
		if not ltlf_formula:
			raise NLToLTLfMalformedResponseError(
				"NL-to-LTLf response did not include a non-empty 'ltlf_formula'.",
			)
		diagnostics = tuple(
			str(item).strip()
			for item in (payload.get("diagnostics") or ())
			if str(item).strip()
		)
		record = TemporalSpecificationRecord(
			instruction_id=str(instruction_id or "").strip() or "query",
			source_text=source_text,
			ltlf_formula=ltlf_formula,
			referenced_events=(),
			diagnostics=diagnostics,
			problem_file=problem_file,
		)
		return validate_predicate_grounded_temporal_specification(record, domain=domain)

	def _request_json(self, messages: Sequence[dict[str, str]]) -> dict[str, Any]:
		attempt = 0
		last_error: Exception | None = None
		while attempt <= _MAX_TRANSPORT_RETRIES:
			attempt += 1
			try:
				response = create_openai_compatible_json_completion(
					self.client,
					model=self.model,
					messages=messages,
					timeout=self.request_timeout,
					max_tokens=self.response_max_tokens,
					stream=False,
					reasoning_effort="high",
				)
				response_text = self._extract_response_text(response)
				return self._parse_json_blob(response_text)
			except Exception as exc:  # noqa: BLE001 - retried transport boundary
				last_error = exc
				if attempt <= _MAX_TRANSPORT_RETRIES and self._is_retryable(exc):
					time.sleep(min(2.0 * attempt, 5.0))
					continue
				raise
		assert last_error is not None
		raise last_error

	@staticmethod
	def _is_retryable(exc: Exception) -> bool:
		return type(exc).__name__.strip().lower() in _RETRYABLE_ERROR_CLASS_NAMES

	@staticmethod
	def _extract_response_text(response: object) -> str:
		choices = getattr(response, "choices", None) or ()
		if not choices:
			raise NLToLTLfEmptyResponseError("LLM response did not include any choices.")
		message = getattr(choices[0], "message", None)
		if message is None:
			raise NLToLTLfEmptyResponseError(
				"LLM response choice did not include a message payload.",
			)
		content = getattr(message, "content", None)
		if isinstance(content, str) and content.strip():
			return content
		dumped = message.model_dump() if hasattr(message, "model_dump") else None
		if isinstance(dumped, dict):
			for key in ("content", "text", "output_text"):
				value = dumped.get(key)
				if isinstance(value, str) and value.strip():
					return value
		raise NLToLTLfEmptyResponseError(
			"LLM response did not contain any textual completion content.",
		)

	@staticmethod
	def _parse_json_blob(response_text: str) -> dict[str, Any]:
		cleaned = str(response_text or "").strip()
		if cleaned.startswith("```"):
			cleaned = cleaned.strip("`")
			if cleaned.lower().startswith("json"):
				cleaned = cleaned[4:]
			cleaned = cleaned.strip()
		try:
			payload = json.loads(cleaned)
		except json.JSONDecodeError:
			start = cleaned.find("{")
			end = cleaned.rfind("}")
			if start == -1 or end <= start:
				raise NLToLTLfMalformedResponseError(
					"NL-to-LTLf response was not valid JSON.",
				)
			payload = json.loads(cleaned[start : end + 1])
		if not isinstance(payload, dict):
			raise NLToLTLfMalformedResponseError(
				"NL-to-LTLf response must be one JSON object.",
			)
		return payload


def build_system_prompt(domain: Any) -> str:
	"""Build the domain-aware NL-to-LTLf system prompt from a parsed PDDL domain."""

	domain_name = str(getattr(domain, "name", "") or "domain").strip() or "domain"
	types = [str(item).strip() for item in (getattr(domain, "types", ()) or ()) if str(item).strip()]
	predicate_lines = []
	for predicate in getattr(domain, "predicates", ()) or ():
		name = str(getattr(predicate, "name", "") or "").strip()
		if not name:
			continue
		parameters = list(getattr(predicate, "parameters", ()) or ())
		signature = f"{name}({', '.join(str(p) for p in parameters)})" if parameters else f"{name}()"
		predicate_lines.append(f"  - {signature}")
	action_names = sorted(
		str(getattr(action, "name", "") or "").strip()
		for action in (getattr(domain, "actions", ()) or ())
		if str(getattr(action, "name", "") or "").strip()
	)

	lines = [
		"You are an expert in Linear Temporal Logic on Finite Traces (LTLf) and typed "
		"symbolic planning.",
		"Convert one natural-language goal into exactly one LTLf formula for the "
		f"planning domain '{domain_name}'.",
		"",
		f"Object types: {', '.join(types) if types else '(untyped)'}",
		"",
		"The ONLY legal atoms are these domain predicates (use the predicate name with "
		"concrete object arguments):",
		*predicate_lines,
		"",
		"ATOM RULES (critical):",
		"- Atoms MUST be domain predicates (fluents) describing a desired state, e.g. "
		"on(b4, b2).",
		"- NEVER use action or operator names as atoms. The following are actions and are "
		f"FORBIDDEN as atoms: {', '.join(action_names) if action_names else '(none declared)'}.",
		"- If the instruction names an action-like task (e.g. 'put b4 on b2'), translate it "
		"to the predicate that becomes true as a result (e.g. on(b4, b2)).",
		"- Preserve object identifiers exactly as written. Use only the provided predicates.",
		"",
		"LTLf SYNTAX:",
		"- Atomic predicate: predicate(arg1, arg2, ...)",
		"- Negation: !   Conjunction: &   Disjunction: |   Implication: ->",
		"- Unary temporal operators: X (next), F (eventually), G (always)",
		"- Binary temporal operators: U (until), R (release)",
		"- Group with parentheses; precedence is !, then temporal, then &, then |, then ->.",
		"",
		"ACHIEVEMENT vs TEMPORAL (critical):",
		"- If the goal states only WHICH facts must hold, with no ordering or temporal "
		"relation, return a PURE CONJUNCTION with NO temporal operators, e.g. "
		"on(b4, b2) & on(b3, b1).",
		"- Only introduce F / X / G / U / R when the instruction expresses a genuine "
		"temporal relation (first/then/before/after/until/always/eventually).",
		"- For an ordered sequence 'achieve A, then B, then C', use nested eventualities, "
		"e.g. F(A & X(F(B & X(F(C))))).",
		"",
		"OUTPUT CONTRACT:",
		"- Return JSON only. No markdown, no prose, no comments.",
		'- Return exactly one JSON object: {"ltlf_formula": "<formula>", "atoms": ["<atom>", ...]}.',
		"- ltlf_formula is a single LTLf string using only the predicates above as atoms.",
		"- atoms lists every distinct predicate instance used in ltlf_formula.",
		"",
		"EXAMPLES (schematic - replace with the current domain's predicates):",
		'- "put a on b, then b on c" -> '
		'{"ltlf_formula": "F(on(a, b) & X(F(on(b, c))))", "atoms": ["on(a, b)", "on(b, c)"]}',
		'- "make a on b and c on d (any order)" -> '
		'{"ltlf_formula": "on(a, b) & on(c, d)", "atoms": ["on(a, b)", "on(c, d)"]}',
	]
	return "\n".join(lines)
