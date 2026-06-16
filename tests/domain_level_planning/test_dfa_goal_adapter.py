from __future__ import annotations

import pytest

from domain_level_planning.dfa_adapter import (
	adapt_dfa_guard_to_achievement_request,
	adapt_dfa_guarded_transition_to_achievement_request,
	inspect_dfa_guard_to_achievement_request,
)
from plan_library.models import AgentSpeakBodyStep
from utils.pddl_parser import PDDLParser


BLOCKS_DOMAIN = "src/domains/blocksworld/domain.pddl"


def test_dfa_guard_conjunction_becomes_goal_facts_and_subgoal_calls() -> None:
	request = adapt_dfa_guard_to_achievement_request(
		"do_put_on_b1_b2 & clear(b1)",
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
			"raw_label": "do_put_on_b1_b2",
		},
		domain_key="blocksworld",
		declared_predicates=PDDLParser.parse_domain(BLOCKS_DOMAIN).predicates,
	)

	assert request.source_state == "q0"
	assert request.target_state == "q1"
	assert request.raw_guard == "do_put_on_b1_b2"
	assert request.goal_facts == ("goal_on(b1, b2)",)
	assert request.body_steps == (
		AgentSpeakBodyStep("subgoal", "on", ("b1", "b2")),
	)


def test_dfa_guard_adapter_rejects_unsupported_negative_or_false_guards() -> None:
	with pytest.raises(ValueError, match="positive conjunctive"):
		adapt_dfa_guard_to_achievement_request(
			"not on(b1,b2)",
			domain_key="blocksworld",
		)

	with pytest.raises(ValueError, match="positive conjunctive"):
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
		"do_put_on_b1_b2 & handempty",
		domain_key="blocksworld",
		domain_file=BLOCKS_DOMAIN,
	)

	assert request.goal_facts == ("goal_on(b1, b2)", "goal_handempty")
	assert request.body_steps == (
		AgentSpeakBodyStep("subgoal", "on", ("b1", "b2")),
		AgentSpeakBodyStep("subgoal", "handempty", ()),
	)


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


def test_dfa_guard_adapter_reports_structured_rejection_diagnostics() -> None:
	diagnostic = inspect_dfa_guard_to_achievement_request(
		"not on(b1,b2)",
		domain_key="blocksworld",
		domain_file=BLOCKS_DOMAIN,
	)

	assert diagnostic.supported is False
	assert diagnostic.rejection_reason == "unsupported_negative_or_disjunctive_guard"
	assert diagnostic.raw_guard == "not on(b1,b2)"
	assert diagnostic.state_literals == ("not on(b1, b2)",)
	assert diagnostic.request is None
	assert diagnostic.to_dict() == {
		"raw_guard": "not on(b1,b2)",
		"supported": False,
		"rejection_reason": "unsupported_negative_or_disjunctive_guard",
		"message": (
			"DFA guard adapter currently supports positive conjunctive "
			"achievement requests only; received 'not on(b1,b2)'."
		),
		"state_literals": ["not on(b1, b2)"],
		"request": None,
	}
