from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from temporal_specification import (
	NLToLTLfGenerator,
	NLToLTLfMalformedResponseError,
	TemporalSpecificationRecord,
	build_system_prompt,
	validate_predicate_grounded_temporal_specification,
)
from utils.pddl_parser import PDDLParser

BLOCKSWORLD_DOMAIN = SRC_ROOT / "domains" / "blocksworld" / "domain.pddl"


class _FakeMessage:
	def __init__(self, content: str) -> None:
		self.content = content


class _FakeChoice:
	def __init__(self, content: str) -> None:
		self.message = _FakeMessage(content)
		self.finish_reason = "stop"


class _FakeResponse:
	def __init__(self, content: str) -> None:
		self.choices = [_FakeChoice(content)]


class _FakeCompletions:
	def __init__(self, content: str) -> None:
		self._content = content
		self.calls: list[dict] = []

	def create(self, **kwargs):
		self.calls.append(kwargs)
		return _FakeResponse(self._content)


class _FakeChat:
	def __init__(self, content: str) -> None:
		self.completions = _FakeCompletions(content)


class _FakeClient:
	def __init__(self, content: str) -> None:
		self.chat = _FakeChat(content)


@pytest.fixture(scope="module")
def domain():
	return PDDLParser.parse_domain(BLOCKSWORLD_DOMAIN)


def test_system_prompt_lists_predicates_and_forbids_actions(domain) -> None:
	prompt = build_system_prompt(domain)
	assert "on(" in prompt
	assert "FORBIDDEN as atoms" in prompt
	# blocksworld action names must be named as forbidden atoms
	assert "stack" in prompt
	assert "PURE CONJUNCTION" in prompt


def test_generator_returns_validated_fluent_record(domain) -> None:
	content = json.dumps(
		{
			"ltlf_formula": "F(on(b4, b2) & X(F(on(b1, b4))))",
			"atoms": ["on(b4, b2)", "on(b1, b4)"],
		},
	)
	generator = NLToLTLfGenerator(client=_FakeClient(content), model="fake/model")
	record = generator.generate(
		domain=domain,
		instruction="Put b4 on b2, then b1 on b4.",
		instruction_id="query_1",
		problem_file="p01.pddl",
	)
	assert record.ltlf_formula == "F(on(b4, b2) & X(F(on(b1, b4))))"
	assert record.problem_file == "p01.pddl"
	assert tuple(event.event for event in record.referenced_events) == ("on", "on")
	# the request passed JSON response_format through the transport
	assert generator.client.chat.completions.calls[0]["response_format"] == {"type": "json_object"}


def test_generator_degenerate_conjunction(domain) -> None:
	content = json.dumps({"ltlf_formula": "on(b4, b2) & on(b3, b1)", "atoms": []})
	generator = NLToLTLfGenerator(client=_FakeClient(content))
	record = generator.generate(domain=domain, instruction="Make b4 on b2 and b3 on b1.")
	assert "F(" not in record.ltlf_formula
	assert record.ltlf_formula == "on(b4, b2) & on(b3, b1)"


def test_generator_rejects_action_atoms(domain) -> None:
	content = json.dumps({"ltlf_formula": "F(stack(b4, b2))", "atoms": ["stack(b4, b2)"]})
	generator = NLToLTLfGenerator(client=_FakeClient(content))
	with pytest.raises(ValueError):
		generator.generate(domain=domain, instruction="Stack b4 on b2.")


def test_generator_rejects_malformed_json(domain) -> None:
	generator = NLToLTLfGenerator(client=_FakeClient("not json at all"))
	with pytest.raises(NLToLTLfMalformedResponseError):
		generator.generate(domain=domain, instruction="anything")


def test_validation_rejects_wrong_arity(domain) -> None:
	record = TemporalSpecificationRecord("q", "x", "on(b4)", ())
	with pytest.raises(ValueError):
		validate_predicate_grounded_temporal_specification(record, domain=domain)


def test_validation_rejects_unknown_predicate(domain) -> None:
	record = TemporalSpecificationRecord("q", "x", "floating(b4, b2)", ())
	with pytest.raises(ValueError):
		validate_predicate_grounded_temporal_specification(record, domain=domain)
