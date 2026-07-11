from __future__ import annotations

from pathlib import Path

import pytest

from domain_level_planning.temporal_goal_appender import append_temporal_goal_to_library
from domain_level_planning.temporal_goal_appender import append_lifted_temporal_goal_case_to_library
from domain_level_planning.temporal_goal_appender import validate_guard_transition_dfa
from domain_level_planning.lifted_ltlf_goal_schema import LTLfAtomSpec
from domain_level_planning.lifted_ltlf_goal_schema import LiftedLTLfGoalCase
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary


def test_validate_guard_transition_dfa_accepts_conjunction_and_negation() -> None:
	diagnostic = validate_guard_transition_dfa(
		{
			"initial_state": "q0",
			"accepting_states": ["q1"],
			"guarded_transitions": [
				{
					"source_state": "q0",
					"target_state": "q1",
					"raw_label": "a(X) & not b(Y)",
				},
			],
		},
		declared_arities={"a": 1, "b": 1},
	)

	assert diagnostic.valid is True
	assert diagnostic.errors == ()


def test_validate_guard_transition_dfa_reports_domain_errors() -> None:
	diagnostic = validate_guard_transition_dfa(
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
	]
	assert diagnostic.errors[0]["predicate"] == "missing"
	assert diagnostic.errors[1]["expected_arity"] == 1
	assert diagnostic.errors[1]["actual_arity"] == 2


def test_validate_guard_transition_dfa_accepts_numeric_resource_function() -> None:
	diagnostic = validate_guard_transition_dfa(
		{
			"initial_state": "q0",
			"accepting_states": ["q1"],
			"guarded_transitions": [
				{
					"source_state": "q0",
					"target_state": "q1",
					"raw_label": "pogo_sticks_to_make(0)",
				},
			],
		},
		declared_arities={"pogo_sticks_to_make": 1},
	)

	assert diagnostic.valid is True
	assert diagnostic.errors == ()


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
		"g_query_1_trans_sequence",
		"g_query_1_trans_1_repair_tree",
		"g_query_1_trans_1_repair_1_1_satisfied",
		"g_query_1_trans_1_repair_1_1_achieve",
		"g_query_1_trans_1_done_success",
		"g_query_1_trans_1_done_replay",
		"g_query_1_trans_2_repair_tree",
		"g_query_1_trans_2_repair_1_1_satisfied",
		"g_query_1_trans_2_repair_1_1_achieve",
		"g_query_1_trans_2_done_success",
		"g_query_1_trans_2_done_replay",
	]
	assert updated.plans[1].trigger.symbol == "g_query_1"
	assert updated.plans[1].context == ("query_1",)
	assert updated.plans[1].body == (
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_1", ()),
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_2", ()),
	)
	assert updated.plans[2].context == ("query_1", "obj_tp(X, item)")
	assert updated.plans[2].body == (
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_1_repair_1_1", ()),
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_1_done", ()),
	)
	assert updated.plans[3].context == (
		"query_1",
		"obj_tp(X, item)",
		"done(X)",
	)
	assert updated.plans[3].body == ()
	assert updated.plans[4].context == (
		"query_1",
		"obj_tp(X, item)",
		"not done(X)",
	)
	assert updated.plans[4].body == (
		AgentSpeakBodyStep("subgoal", "done", ("X",)),
	)
	assert updated.initial_beliefs == ("query_1",)
	assert updated.metadata["temporal_goal_append"]["goal_name"] == "g_query_1"
	assert updated.metadata["temporal_goal_append"]["wrapper_mode"] == (
		"dfa_guard_transition_replay"
	)
	assert updated.metadata["temporal_goal_append"]["progress_transition_count"] == 2
	assert updated.metadata["temporal_goal_append"]["negative_guard_count"] == 0
	assert updated.metadata["temporal_goal_append"]["negative_guard_policy"] == (
		"completion_context_with_conditional_may_add_preservation"
	)
	assert updated.metadata["temporal_goal_append"]["negative_achievement_supported"] is False
	assert updated.metadata["temporal_goal_append"]["transition_controller_strategy"] == (
		"balanced_transition_repair_tree"
	)
	assert (
		updated.metadata["temporal_goal_append"]["query_entry_proposition"]
		== "query_1"
	)
	assert [
		diagnostic["request"]["achievement_subgoals"][0]["symbol"]
		for diagnostic in updated.metadata["temporal_goal_append"]["progress_request_diagnostics"]
	] == ["done", "ready"]
	assert [
		record["goal_name"]
		for record in updated.metadata["temporal_goal_append_history"]
	] == ["g_query_1"]


def test_append_temporal_goal_compiles_one_helper_per_conjunctive_transition(
	tmp_path: Path,
) -> None:
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
			AgentSpeakPlan(
				plan_name="ready_via_reset",
				trigger=AgentSpeakTrigger("achievement_goal", "ready", ("X",)),
				context=("done(X)",),
				body=(AgentSpeakBodyStep("action", "reset", ("X",)),),
			),
		),
	)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q2"],
		"guarded_transitions": [
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "done(X) & ready(Y)",
			},
			{
				"source_state": "q1",
				"target_state": "q2",
				"raw_label": "done(Y) & not ready(Y)",
			},
			{"source_state": "q2", "target_state": "q2", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)

	assert updated.plans[2].body == (
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_1", ()),
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_2", ()),
	)
	first_tree_entry = next(
		plan for plan in updated.plans if plan.plan_name == "g_query_1_trans_1_repair_tree"
	)
	assert first_tree_entry.context == (
		"query_1",
		"obj_tp(X, item)",
		"obj_tp(Y, item)",
	)
	first_done = next(
		plan for plan in updated.plans if plan.plan_name == "g_query_1_trans_1_done_success"
	)
	assert first_done.context == (
		"query_1",
		"obj_tp(X, item)",
		"obj_tp(Y, item)",
		"done(X)",
		"ready(Y)",
	)
	second_done = next(
		plan for plan in updated.plans if plan.plan_name == "g_query_1_trans_2_done_success"
	)
	assert second_done.context == (
		"query_1",
		"obj_tp(Y, item)",
		"done(Y)",
		"not ready(Y)",
	)
	second_leaf = next(
		plan
		for plan in updated.plans
		if plan.plan_name == "g_query_1_trans_2_repair_1_1_achieve"
	)
	assert second_leaf.context == (
		"query_1",
		"obj_tp(Y, item)",
		"not ready(Y)",
		"not done(Y)",
	)
	assert all(
		diagnostic["supported"] is True
		for diagnostic in updated.metadata["temporal_goal_append"][
			"progress_request_diagnostics"
		]
	)
	certificate = first_tree_entry.binding_certificate[0]["serialization_certificate"]
	assert certificate == {
		"certificate_kind": "atomic_module_effect_serialization",
		"effect_summary_method": "pddl_typed_conditional_relational_fixed_point",
		"shared_query_variable_types_checked": True,
		"ordered_literal_indexes": [0, 1],
		"threat_edges": [[0, 1]],
		"module_summaries_complete": True,
		"conditional_effects_checked": True,
		"functional_invariant_count": 0,
		"observation_boundary": "atomic_module_completion",
		"serialization_strategy": "universal_acyclic_threat_order",
		"ranking_relation": None,
		"ranking_relation_anchor_position": None,
		"ranking_assumptions": [],
		"negative_guard_count": 0,
		"negative_guard_literals": [],
		"negative_guard_preservation_checked": False,
		"negative_guard_preserved": True,
		"negative_guard_threats": [],
	}


def test_append_temporal_goal_rejects_cyclic_conjunctive_threats(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "cyclic-domain.pddl"
	domain_file.write_text(
		"""
(define (domain cyclic)
 (:requirements :strips)
 (:predicates (left) (right) (seed))
 (:action make-left
  :parameters ()
  :precondition (seed)
  :effect (and (left) (not (right))))
 (:action make-right
  :parameters ()
  :precondition (seed)
  :effect (and (right) (not (left))))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="cyclic",
		plans=(
			AgentSpeakPlan(
				"left_via_make_left",
				AgentSpeakTrigger("achievement_goal", "left", ()),
				("seed",),
				(AgentSpeakBodyStep("action", "make-left", ()),),
			),
			AgentSpeakPlan(
				"right_via_make_right",
				AgentSpeakTrigger("achievement_goal", "right", ()),
				("seed",),
				(AgentSpeakBodyStep("action", "make-right", ()),),
			),
		),
	)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "left & right"},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	with pytest.raises(ValueError, match="cyclic_conjunctive_transition_not_certified"):
		append_temporal_goal_to_library(
			plan_library=library,
			goal_name="g_query_1",
			dfa_payload=dfa_payload,
				domain_file=domain_file,
			)


def test_append_temporal_goal_enforces_preservation_safe_query_local_branches(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "selection-domain.pddl"
	domain_file.write_text(
		"""
(define (domain selection)
 (:requirements :strips)
 (:predicates (completed ?x) (ready ?x))
 (:action finish-safely
  :parameters (?x)
  :precondition (ready ?x)
  :effect (completed ?x))
 (:action finish-by-reusing
  :parameters (?x ?other)
  :precondition (and (ready ?x) (completed ?other))
  :effect (and (completed ?x) (not (completed ?other))))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="selection",
		plans=(
			AgentSpeakPlan(
				"completed_already_true",
				AgentSpeakTrigger("achievement_goal", "completed", ("X",)),
				("completed(X)",),
				(),
			),
			AgentSpeakPlan(
				"completed_safe",
				AgentSpeakTrigger("achievement_goal", "completed", ("X",)),
				("ready(X)",),
				(AgentSpeakBodyStep("action", "finish-safely", ("X",)),),
			),
			AgentSpeakPlan(
				"completed_unsafe",
				AgentSpeakTrigger("achievement_goal", "completed", ("X",)),
				("ready(X)", "completed(Y)"),
				(AgentSpeakBodyStep("action", "finish-by-reusing", ("X", "Y")),),
			),
		),
	)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "completed(first) & completed(second)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	query_plans = tuple(plan for plan in updated.plans if plan.plan_name.startswith("g_query_1"))
	query_bodies = tuple(
		step.symbol for plan in query_plans for step in plan.body if step.kind == "action"
	)
	repair_subgoals = tuple(
		step.symbol
		for plan in query_plans
		if "_repair_" in plan.plan_name
		for step in plan.body
		if step.kind == "subgoal"
	)

	assert "finish-safely" in query_bodies
	assert "finish-by-reusing" not in query_bodies
	assert "g_query_1_trans_1_achieve_completed" in repair_subgoals


def test_append_temporal_goal_rejects_uncertified_negative_guard_preservation(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "negative-unsafe-domain.pddl"
	domain_file.write_text(
		"""
(define (domain negative-unsafe)
 (:requirements :strips)
 (:predicates (ready ?x) (delivered ?x) (damaged ?x))
 (:action deliver-damaged
  :parameters (?x)
  :precondition (ready ?x)
  :effect (and (delivered ?x) (damaged ?x)))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="negative-unsafe",
		plans=(
			AgentSpeakPlan(
				"delivered_via_damaged",
				AgentSpeakTrigger("achievement_goal", "delivered", ("X",)),
				("ready(X)",),
				(AgentSpeakBodyStep("action", "deliver-damaged", ("X",)),),
			),
		),
	)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "delivered(item) & not damaged(item)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	with pytest.raises(ValueError, match="negative_guard_not_preserved"):
		append_temporal_goal_to_library(
			plan_library=library,
			goal_name="g_query_1",
			dfa_payload=dfa_payload,
			domain_file=domain_file,
		)


def test_append_temporal_goal_compiles_negative_only_transition_as_context(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "negative-only-domain.pddl"
	domain_file.write_text(
		"""
(define (domain negative-only)
 (:requirements :strips)
 (:predicates (blocked ?x))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "not blocked(item)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=PlanLibrary(domain_name="negative-only", plans=()),
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	transition = next(
		plan for plan in updated.plans if plan.plan_name == "g_query_1_trans_1_done"
	)
	certificate = transition.binding_certificate[0]["serialization_certificate"]

	assert transition.context == ("query_1", "not blocked(item)")
	assert transition.body == ()
	assert certificate == {
		"certificate_kind": "negative_context_only_transition",
		"ordered_literal_indexes": [],
		"threat_edges": [],
		"module_summaries_complete": True,
		"negative_guard_count": 1,
		"negative_guard_literals": ["blocked(item)"],
		"negative_guard_preservation_checked": True,
		"negative_guard_preserved": True,
		"negative_guard_threats": [],
	}


def test_append_temporal_goal_rejects_uncertified_numeric_negative_conjunction(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "numeric-negative-domain.pddl"
	domain_file.write_text(
		"""
(define (domain numeric-negative)
 (:requirements :strips :fluents)
 (:predicates (ready) (done))
 (:functions (fuel))
 (:action finish
  :parameters ()
  :precondition (ready)
  :effect (done))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="numeric-negative",
		plans=(
			AgentSpeakPlan(
				"done_via_finish",
				AgentSpeakTrigger("achievement_goal", "done", ()),
				("ready",),
				(AgentSpeakBodyStep("action", "finish", ()),),
			),
		),
	)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "done & not fuel(0)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	with pytest.raises(ValueError, match="uncertified_numeric_conjunctive_transition"):
		append_temporal_goal_to_library(
			plan_library=library,
			goal_name="g_query_1",
			dfa_payload=dfa_payload,
			domain_file=domain_file,
		)


def test_append_temporal_goal_enforces_negative_preserving_query_local_branches(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "negative-selection-domain.pddl"
	domain_file.write_text(
		"""
(define (domain negative-selection)
 (:requirements :strips)
 (:predicates (ready ?x) (delivered ?x) (damaged ?x))
 (:action deliver-safely
  :parameters (?x)
  :precondition (ready ?x)
  :effect (delivered ?x))
 (:action deliver-damaged
  :parameters (?x)
  :precondition (ready ?x)
  :effect (and (delivered ?x) (damaged ?x)))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="negative-selection",
		plans=(
			AgentSpeakPlan(
				"delivered_already_true",
				AgentSpeakTrigger("achievement_goal", "delivered", ("X",)),
				("delivered(X)",),
				(),
			),
			AgentSpeakPlan(
				"delivered_safe",
				AgentSpeakTrigger("achievement_goal", "delivered", ("X",)),
				("ready(X)",),
				(AgentSpeakBodyStep("action", "deliver-safely", ("X",)),),
			),
			AgentSpeakPlan(
				"delivered_unsafe",
				AgentSpeakTrigger("achievement_goal", "delivered", ("X",)),
				("ready(X)",),
				(AgentSpeakBodyStep("action", "deliver-damaged", ("X",)),),
			),
		),
	)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "delivered(item) & not damaged(item)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	query_plans = tuple(
		plan for plan in updated.plans if plan.plan_name.startswith("g_query_1")
	)
	query_actions = tuple(
		step.symbol
		for plan in query_plans
		for step in plan.body
		if step.kind == "action"
	)
	repair = next(
		plan
		for plan in query_plans
		if plan.plan_name == "g_query_1_trans_1_repair_1_1_achieve"
	)
	certificate = next(
		plan
		for plan in query_plans
		if plan.plan_name == "g_query_1_trans_1_repair_tree"
	).binding_certificate[0]["serialization_certificate"]

	assert "deliver-safely" in query_actions
	assert "deliver-damaged" not in query_actions
	assert repair.body[0].symbol == "g_query_1_trans_1_achieve_delivered"
	assert certificate["negative_guard_preservation_checked"] is True
	assert certificate["negative_guard_preserved"] is True
	assert certificate["negative_guard_count"] == 1
	assert certificate["negative_guard_literals"] == ["damaged(item)"]
	assert updated.metadata["temporal_goal_append"]["negative_guard_count"] == 1
	assert certificate["serialization_strategy"] == (
		"query_local_preservation_safe_action_only_branches"
	)


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

	assert [
		plan.trigger.symbol
		for plan in after_second.plans
		if plan.plan_name.endswith("_trans_sequence")
	] == ["g_query_1", "g_query_2"]
	trigger_counts = {
		plan.trigger.symbol: sum(
			candidate.trigger.symbol == plan.trigger.symbol
			for candidate in after_second.plans
		)
		for plan in after_second.plans
	}
	assert max(trigger_counts.values()) == 2
	assert [
		record["goal_name"]
		for record in after_second.metadata["temporal_goal_append_history"]
	] == ["g_query_1", "g_query_2"]
	assert after_second.initial_beliefs == ("query_1", "query_2")


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
		"g_query_1_trans_sequence",
		"g_query_1_trans_1_repair_tree",
		"g_query_1_trans_1_repair_1_1_satisfied",
		"g_query_1_trans_1_repair_1_1_achieve",
		"g_query_1_trans_1_done_success",
		"g_query_1_trans_1_done_replay",
	]
	assert updated.plans[0].context == ("query_1",)
	assert updated.plans[0].body == (
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_1", ()),
	)


def test_append_temporal_goal_rejects_branching_dfa_without_external_controller(
	tmp_path: Path,
) -> None:
	domain_file = _write_branching_domain(tmp_path)
	library = PlanLibrary(domain_name="branching", plans=())
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q3"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "a"},
			{"source_state": "q0", "target_state": "q2", "raw_label": "b"},
			{"source_state": "q1", "target_state": "q3", "raw_label": "c"},
			{"source_state": "q2", "target_state": "q3", "raw_label": "d"},
			{"source_state": "q3", "target_state": "q3", "raw_label": "true"},
		],
	}

	with pytest.raises(ValueError, match="nonlinear_temporal_goal_not_supported"):
		append_temporal_goal_to_library(
			plan_library=library,
			goal_name="g_query_1",
			dfa_payload=dfa_payload,
			domain_file=domain_file,
		)


def test_append_temporal_goal_keeps_negative_progress_literal_as_context(tmp_path: Path) -> None:
	domain_file = _write_domain(tmp_path)
	library = PlanLibrary(domain_name="tiny", plans=())
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "not done(X)"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)

	assert [plan.plan_name for plan in updated.plans] == [
		"g_query_1_trans_sequence",
		"g_query_1_trans_1_done",
	]
	assert updated.plans[1].context == (
		"query_1",
		"obj_tp(X, item)",
		"not done(X)",
	)
	assert updated.plans[1].body == ()


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
	assert updated.plans[0].plan_name == "g_query_1_trans_sequence"
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
	assert updated.plans[0].context == ("query_1",)
	assert updated.plans[0].body == (
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_1", ()),
	)
	assert (
		updated.metadata["temporal_goal_append"]["progress_request_diagnostics"][0]
		["request"]["achievement_subgoals"]
		== [{"kind": "subgoal", "symbol": "on", "arguments": ["X", "Y"]}]
	)


def test_append_lifted_temporal_goal_accepts_numeric_resource_function_atom(
	tmp_path: Path,
) -> None:
	domain_file = _write_numeric_resource_domain(tmp_path)
	library = PlanLibrary(domain_name="numeric-minecraft", plans=())
	case = LiftedLTLfGoalCase(
		query_id="query_1",
		goal_name="g_numeric_minecraft_test_1",
		problem_file="p01.pddl",
		source_text="Craft until no pogo sticks remain to make.",
		ltlf_formula="F(pogo_done)",
		atoms=(
			LTLfAtomSpec("pogo_done", "pogo_sticks_to_make", ("0",)),
		),
		bindings={},
	)

	updated, dfa_payload = append_lifted_temporal_goal_case_to_library(
		plan_library=library,
		goal_case=case,
		domain_file=domain_file,
		dfa_builder=_FakeNumericEncodedDFABuilder(),
	)

	assert dfa_payload["guarded_transitions"][0]["raw_label"] == "pogo_sticks_to_make(0)"
	assert updated.plans[0].context == ("numeric_minecraft_test_1",)
	assert updated.plans[0].body == (
		AgentSpeakBodyStep("subgoal", "g_numeric_minecraft_test_1_trans_1", ()),
	)
	assert (
		updated.metadata["temporal_goal_append"]["progress_request_diagnostics"][0]
		["request"]["achievement_subgoals"]
		== [{"kind": "subgoal", "symbol": "pogo_sticks_to_make", "arguments": ["0"]}]
	)


def test_append_temporal_goal_rejects_wrong_numeric_resource_function_arity(
	tmp_path: Path,
) -> None:
	domain_file = _write_numeric_resource_domain(tmp_path)
	library = PlanLibrary(domain_name="numeric-minecraft", plans=())
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "pogo_sticks_to_make"},
		],
	}

	with pytest.raises(ValueError, match="wrong_arity"):
		append_temporal_goal_to_library(
			plan_library=library,
			goal_name="g_numeric_minecraft_test_1",
			dfa_payload=dfa_payload,
			domain_file=domain_file,
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
			 (:action reset
			  :parameters (?x - item)
			  :precondition (done ?x)
			  :effect (ready ?x)
			 )
		)
		""",
		encoding="utf-8",
	)
	return domain_file


def _write_numeric_resource_domain(tmp_path: Path) -> Path:
	domain_file = tmp_path / "numeric-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain numeric-minecraft)
		 (:requirements :strips :typing :numeric-fluents)
		 (:functions (pogo_sticks_to_make))
		 (:action craft_wooden_pogo
		  :parameters ()
		  :precondition (> (pogo_sticks_to_make) 0)
		  :effect (decrease (pogo_sticks_to_make) 1)
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


def _write_branching_domain(tmp_path: Path) -> Path:
	domain_file = tmp_path / "branching-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain branching)
		 (:requirements :strips)
		 (:predicates (a) (b) (c) (d))
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


class _FakeNumericEncodedDFABuilder:
	def build(self, formula: str):
		return {
			"original_formula": formula,
			"initial_state": "q0",
			"accepting_states": ["q1"],
			"guarded_transitions": [
				{"source_state": "q0", "target_state": "q1", "raw_label": "pogo_done"},
				{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
			],
		}
