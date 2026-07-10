from __future__ import annotations

import pytest

from domain_level_planning.dfa_adapter import (
	adapt_dfa_guard_to_achievement_request,
	adapt_dfa_guarded_transition_to_achievement_request,
	inspect_dfa_guard_to_achievement_request,
)
from plan_library.models import AgentSpeakBodyStep
from utils.pddl_parser import PDDLParser


BLOCKS_DOMAIN = "src/domains/blocksworld-tower/domain.pddl"


def test_dfa_guard_conjunction_becomes_goal_facts_and_subgoal_calls() -> None:
	request = adapt_dfa_guard_to_achievement_request(
		"on(b1,b2) & clear(b1)",
		domain_key="blocksworld",
		declared_predicates=PDDLParser.parse_domain(BLOCKS_DOMAIN).predicates,
	)

	assert request.state_literals == ("on(b1, b2)", "clear(b1)")
	assert request.goal_facts == ("goal_on(b1, b2)", "goal_clear(b1)")
	assert request.body_steps == (
		AgentSpeakBodyStep("subgoal", "on", ("b1", "b2")),
		AgentSpeakBodyStep("subgoal", "clear", ("b1",)),
	)
	assert request.to_dict()["achievement_subgoals"] == [
		{"kind": "subgoal", "symbol": "on", "arguments": ["b1", "b2"]},
		{"kind": "subgoal", "symbol": "clear", "arguments": ["b1"]},
	]


def test_dfa_guard_adapter_reports_transition_metadata() -> None:
	request = adapt_dfa_guarded_transition_to_achievement_request(
		{
			"source_state": "q0",
			"target_state": "q1",
			"raw_label": "on(b1,b2)",
		},
		domain_key="blocksworld",
		declared_predicates=PDDLParser.parse_domain(BLOCKS_DOMAIN).predicates,
	)

	assert request.source_state == "q0"
	assert request.target_state == "q1"
	assert request.raw_guard == "on(b1,b2)"
	assert request.goal_facts == ("goal_on(b1, b2)",)
	assert request.body_steps == (
		AgentSpeakBodyStep("subgoal", "on", ("b1", "b2")),
	)


def test_dfa_guard_adapter_keeps_negative_literals_as_context_only() -> None:
	request = adapt_dfa_guard_to_achievement_request(
		"clear(b1) & not on(b1,b2)",
		domain_key="blocksworld",
		domain_file=BLOCKS_DOMAIN,
	)

	assert request.state_literals == ("clear(b1)", "not on(b1, b2)")
	assert request.negative_context_literals == ("not on(b1, b2)",)
	assert request.goal_facts == ("goal_clear(b1)",)
	assert request.body_steps == (AgentSpeakBodyStep("subgoal", "clear", ("b1",)),)


def test_dfa_guard_adapter_rejects_false_guard() -> None:
	with pytest.raises(ValueError, match="conjunction-and-negation"):
		adapt_dfa_guard_to_achievement_request(
			"false",
			domain_key="blocksworld",
		)


def test_dfa_guard_adapter_ignores_true_guard() -> None:
	request = adapt_dfa_guard_to_achievement_request(
		"true",
		domain_key="blocksworld",
		declared_predicates=PDDLParser.parse_domain(BLOCKS_DOMAIN).predicates,
	)

	assert request.state_literals == ()
	assert request.goal_facts == ()
	assert request.body_steps == ()


def test_dfa_guard_adapter_accepts_domain_file_for_schema_validation() -> None:
	request = adapt_dfa_guard_to_achievement_request(
		"on(b1,b2) & handempty",
		domain_key="blocksworld",
		domain_file=BLOCKS_DOMAIN,
	)

	assert request.goal_facts == ("goal_on(b1, b2)", "goal_handempty")
	assert request.body_steps == (
		AgentSpeakBodyStep("subgoal", "on", ("b1", "b2")),
		AgentSpeakBodyStep("subgoal", "handempty", ()),
	)


def test_dfa_guard_adapter_rejects_legacy_event_mapping_names() -> None:
	diagnostic = inspect_dfa_guard_to_achievement_request(
		"do_put_on_b1_b2",
		domain_key="blocksworld",
		domain_file=BLOCKS_DOMAIN,
	)

	assert diagnostic.supported is False
	assert diagnostic.rejection_reason == "undeclared_pddl_predicate"
	assert diagnostic.state_literals == ("do_put_on_b1_b2",)


def test_dfa_guard_adapter_rejects_undeclared_pddl_predicates() -> None:
	with pytest.raises(ValueError, match="undeclared PDDL predicate 'unknown'"):
		adapt_dfa_guard_to_achievement_request(
			"unknown(b1)",
			domain_key="blocksworld",
			domain_file=BLOCKS_DOMAIN,
		)


def test_dfa_guard_adapter_rejects_wrong_pddl_predicate_arity() -> None:
	with pytest.raises(ValueError, match="PDDL predicate on/2 with wrong arity 1"):
		adapt_dfa_guard_to_achievement_request(
			"on(b1)",
			domain_key="blocksworld",
			domain_file=BLOCKS_DOMAIN,
		)


def test_dfa_guard_adapter_reports_structured_negative_context_diagnostics() -> None:
	diagnostic = inspect_dfa_guard_to_achievement_request(
		"not on(b1,b2)",
		domain_key="blocksworld",
		domain_file=BLOCKS_DOMAIN,
	)

	assert diagnostic.supported is True
	assert diagnostic.rejection_reason is None
	assert diagnostic.raw_guard == "not on(b1,b2)"
	assert diagnostic.state_literals == ("not on(b1, b2)",)
	assert diagnostic.request is not None
	assert diagnostic.request.negative_context_literals == ("not on(b1, b2)",)
	assert diagnostic.request.body_steps == ()
	assert diagnostic.to_dict() == {
		"raw_guard": "not on(b1,b2)",
		"supported": True,
		"rejection_reason": None,
		"message": None,
		"state_literals": ["not on(b1, b2)"],
		"request": {
			"raw_guard": "not on(b1,b2)",
			"source_state": None,
			"target_state": None,
			"state_literals": ["not on(b1, b2)"],
			"negative_context_literals": ["not on(b1, b2)"],
			"guard_constraints": ["not on(b1, b2)"],
			"goal_facts": [],
			"achievement_subgoals": [],
		},
	}


def test_dfa_guard_adapter_distinguishes_disjunction_and_false_rejections() -> None:
	disjunction = inspect_dfa_guard_to_achievement_request(
		"on(b1,b2) | clear(b1)",
		domain_key="blocksworld",
		domain_file=BLOCKS_DOMAIN,
	)
	false_guard = inspect_dfa_guard_to_achievement_request(
		"false",
		domain_key="blocksworld",
		domain_file=BLOCKS_DOMAIN,
	)

	assert disjunction.supported is False
	assert disjunction.rejection_reason == "unsupported_disjunctive_guard"
	assert false_guard.supported is False
	assert false_guard.rejection_reason == "unsupported_false_guard"
