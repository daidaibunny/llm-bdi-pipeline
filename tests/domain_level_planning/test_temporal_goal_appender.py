from __future__ import annotations

from pathlib import Path

import pytest

from domain_level_planning.temporal_goal_appender import append_temporal_goal_to_library
from domain_level_planning.temporal_goal_appender import append_lifted_temporal_goal_case_to_library
from domain_level_planning.temporal_goal_appender import validate_singleton_literal_dfa
from domain_level_planning.lifted_ltlf_goal_schema import LTLfAtomSpec
from domain_level_planning.lifted_ltlf_goal_schema import LiftedLTLfGoalCase
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary


def test_validate_singleton_literal_dfa_rejects_conjunctive_transition() -> None:
	diagnostic = validate_singleton_literal_dfa(
		{
			"initial_state": "q0",
			"accepting_states": ["q1"],
			"guarded_transitions": [
				{"source_state": "q0", "target_state": "q1", "raw_label": "a & b"},
			],
		},
	)

	assert diagnostic.valid is False
	assert diagnostic.errors == (
		{
			"transition_index": 1,
			"source_state": "q0",
			"target_state": "q1",
			"raw_label": "a & b",
			"error_type": "non_singleton_literal_guard",
			"message": "DFA transition guard must contain exactly one literal.",
		},
	)


def test_validate_singleton_literal_dfa_reports_domain_errors() -> None:
	diagnostic = validate_singleton_literal_dfa(
		{
			"initial_state": "q0",
			"accepting_states": ["q1"],
			"guarded_transitions": [
				{"source_state": "q0", "target_state": "q1", "raw_label": "missing(X)"},
				{"source_state": "q0", "target_state": "q1", "raw_label": "done(X,Y)"},
				{"source_state": "q0", "target_state": "q1", "raw_label": "not done(X)"},
			],
		},
		declared_arities={"done": 1},
	)

	assert [error["error_type"] for error in diagnostic.errors] == [
		"unsupported_predicate",
		"wrong_arity",
		"negative_literal_template_not_supported",
	]
	assert diagnostic.errors[0]["predicate"] == "missing"
	assert diagnostic.errors[1]["expected_arity"] == 1
	assert diagnostic.errors[1]["actual_arity"] == 2


def test_append_temporal_goal_adds_query_specific_goal_plans(tmp_path: Path) -> None:
	domain_file = _write_domain(tmp_path)
	library = PlanLibrary(
		domain_name="tiny",
		plans=(
			AgentSpeakPlan(
				plan_name="done_via_finish",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
				context=("ready(X)",),
				body=(AgentSpeakBodyStep("action", "finish", ("X",)),),
			),
		),
	)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q2"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "done(X)"},
			{"source_state": "q1", "target_state": "q2", "raw_label": "ready(Y)"},
			{"source_state": "q2", "target_state": "q2", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)

	assert [plan.plan_name for plan in updated.plans] == [
		"done_via_finish",
		"g_query_1_progress_1",
		"g_query_1_progress_2",
		"g_query_1_accepting",
	]
	assert updated.plans[1].trigger.symbol == "g_query_1"
	assert updated.plans[1].context == ("not done(X)",)
	assert updated.plans[1].body == (
		AgentSpeakBodyStep("subgoal", "done", ("X",)),
		AgentSpeakBodyStep("subgoal", "g_query_1", ()),
	)
	assert updated.plans[2].context == ("not ready(Y)",)
	assert updated.plans[2].body == (
		AgentSpeakBodyStep("subgoal", "ready", ("Y",)),
		AgentSpeakBodyStep("subgoal", "g_query_1", ()),
	)
	assert updated.metadata["temporal_goal_append"]["goal_name"] == "g_query_1"
	assert updated.metadata["temporal_goal_append"]["requires_external_dfa_state"] is True
	assert [
		record["goal_name"]
		for record in updated.metadata["temporal_goal_append_history"]
	] == ["g_query_1"]


def test_append_temporal_goal_preserves_history_across_queries(tmp_path: Path) -> None:
	domain_file = _write_domain(tmp_path)
	library = PlanLibrary(domain_name="tiny", plans=())
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "done(X)"},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	after_first = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	after_second = append_temporal_goal_to_library(
		plan_library=after_first,
		goal_name="g_query_2",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)

	assert [plan.trigger.symbol for plan in after_second.plans] == [
		"g_query_1",
		"g_query_1",
		"g_query_2",
		"g_query_2",
	]
	assert [
		record["goal_name"]
		for record in after_second.metadata["temporal_goal_append_history"]
	] == ["g_query_1", "g_query_2"]


def test_append_temporal_goal_rejects_duplicate_goal_name(tmp_path: Path) -> None:
	domain_file = _write_domain(tmp_path)
	library = PlanLibrary(domain_name="tiny", plans=())
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "done(X)"},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}
	updated = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)

	with pytest.raises(ValueError, match="duplicate_temporal_goal"):
		append_temporal_goal_to_library(
			plan_library=updated,
			goal_name="g_query_1",
			dfa_payload=dfa_payload,
			domain_file=domain_file,
		)


def test_append_temporal_goal_allows_negative_waiting_self_loop(
	tmp_path: Path,
) -> None:
	domain_file = _write_domain(tmp_path)
	library = PlanLibrary(domain_name="tiny", plans=())
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q0", "raw_label": "not done(X)"},
			{"source_state": "q0", "target_state": "q1", "raw_label": "done(X)"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)

	assert [plan.plan_name for plan in updated.plans] == [
		"g_query_1_progress_1",
		"g_query_1_accepting",
	]
	assert updated.plans[0].body == (
		AgentSpeakBodyStep("subgoal", "done", ("X",)),
		AgentSpeakBodyStep("subgoal", "g_query_1", ()),
	)


def test_append_temporal_goal_rejects_negative_progress_literal(tmp_path: Path) -> None:
	domain_file = _write_domain(tmp_path)
	library = PlanLibrary(domain_name="tiny", plans=())
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "not done(X)"},
		],
	}

	with pytest.raises(ValueError, match="negative_literal_template_not_supported"):
		append_temporal_goal_to_library(
			plan_library=library,
			goal_name="g_query_1",
			dfa_payload=dfa_payload,
			domain_file=domain_file,
		)


def test_append_lifted_temporal_goal_case_uses_dfa_builder(tmp_path: Path) -> None:
	domain_file = _write_domain(tmp_path)
	library = PlanLibrary(domain_name="tiny", plans=())
	case = LiftedLTLfGoalCase(
		query_id="query_1",
		goal_name="g_query_1",
		problem_file="p01.pddl",
		source_text="Eventually done X.",
		ltlf_formula="F(done(X))",
		atoms=(),
		bindings={},
	)

	updated, dfa_payload = append_lifted_temporal_goal_case_to_library(
		plan_library=library,
		goal_case=case,
		domain_file=domain_file,
		dfa_builder=_FakeDFABuilder(),
	)

	assert dfa_payload["original_formula"] == "F(done(X))"
	assert updated.plans[0].plan_name == "g_query_1_progress_1"
	assert updated.metadata["temporal_goal_append"]["goal_name"] == "g_query_1"


def test_append_lifted_temporal_goal_restores_proposition_labels_from_atoms(
	tmp_path: Path,
) -> None:
	domain_file = _write_blocks_domain(tmp_path)
	library = PlanLibrary(domain_name="blocks", plans=())
	case = LiftedLTLfGoalCase(
		query_id="query_1",
		goal_name="g_query_1",
		problem_file="p01.pddl",
		source_text="Eventually put X on Y.",
		ltlf_formula="F(on(X,Y))",
		atoms=(
			# Matches the compact proposition shape produced by the LTLf encoder.
			# The ASL append layer must restore it to the PDDL predicate atom.
			LTLfAtomSpec("on_x_y", "on", ("X", "Y")),
		),
		bindings={},
	)

	updated, dfa_payload = append_lifted_temporal_goal_case_to_library(
		plan_library=library,
		goal_case=case,
		domain_file=domain_file,
		dfa_builder=_FakeEncodedDFABuilder(),
	)

	assert dfa_payload["guarded_transitions"][0]["raw_label"] == "on(X, Y)"
	assert dfa_payload["guarded_transitions"][0]["original_raw_label"] == "on_x_y"
	assert updated.plans[0].context == ("not on(X, Y)",)
	assert updated.plans[0].body == (
		AgentSpeakBodyStep("subgoal", "on", ("X", "Y")),
		AgentSpeakBodyStep("subgoal", "g_query_1", ()),
	)


def _write_domain(tmp_path: Path) -> Path:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain tiny)
		 (:requirements :strips :typing)
		 (:types item)
		 (:predicates (ready ?x - item) (done ?x - item))
		 (:action finish
		  :parameters (?x - item)
		  :precondition (ready ?x)
		  :effect (and (not (ready ?x)) (done ?x))
		 )
		)
		""",
		encoding="utf-8",
	)
	return domain_file


def _write_blocks_domain(tmp_path: Path) -> Path:
	domain_file = tmp_path / "blocks-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain blocks)
		 (:requirements :strips :typing)
		 (:types block)
		 (:predicates (on ?x - block ?y - block) (clear ?x - block))
		)
		""",
		encoding="utf-8",
	)
	return domain_file


class _FakeDFABuilder:
	def build(self, formula: str):
		return {
			"original_formula": formula,
			"initial_state": "q0",
			"accepting_states": ["q1"],
			"guarded_transitions": [
				{"source_state": "q0", "target_state": "q1", "raw_label": "done(X)"},
			],
		}


class _FakeEncodedDFABuilder:
	def build(self, formula: str):
		return {
			"original_formula": formula,
			"initial_state": "q0",
			"accepting_states": ["q1"],
			"guarded_transitions": [
				{"source_state": "q0", "target_state": "q1", "raw_label": "on_x_y"},
			],
		}
