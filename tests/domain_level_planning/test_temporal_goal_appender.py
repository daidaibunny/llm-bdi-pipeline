from __future__ import annotations

from pathlib import Path

import pytest

from domain_level_planning.temporal_goal_appender import append_temporal_goal_to_library
from domain_level_planning.temporal_goal_appender import append_lifted_temporal_goal_case_to_library
from domain_level_planning.temporal_goal_appender import dfa_semantic_fingerprint
from domain_level_planning.temporal_goal_appender import DFALiteral
from domain_level_planning.temporal_goal_appender import TemporalCompilerVariant
from domain_level_planning.temporal_goal_appender import _ground_action_only_plan
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


def test_dfa_semantic_fingerprint_ignores_runtime_timing() -> None:
	first_payload = {
		"formula": "F(a0)",
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{"source_state": "q0", "target_state": "q1", "raw_label": "done(X)"},
		],
		"timing_profile": {"convert_seconds": 0.1, "total_seconds": 0.2},
	}
	second_payload = {
		**first_payload,
		"timing_profile": {"convert_seconds": 4.0, "total_seconds": 5.0},
	}

	assert dfa_semantic_fingerprint(first_payload) == dfa_semantic_fingerprint(
		second_payload,
	)


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
		"g_query_1_monitor_accepting",
		"g_query_1_trans_1_monitor_dispatch",
		"g_query_1_trans_2_monitor_dispatch",
		"g_query_1_trans_1_repair_tree",
		"g_query_1_trans_1_repair_1_1_satisfied",
		"g_query_1_trans_1_repair_1_1_achieve",
		"g_query_1_trans_1_done_success",
		"g_query_1_trans_1_done_replay",
		"g_query_1_trans_2_repair_tree",
		"g_query_1_trans_2_repair_1_1_satisfied",
		"g_query_1_trans_2_done_success",
		"g_query_1_trans_2_done_replay",
	]
	assert updated.plans[1].trigger.symbol == "g_query_1"
	assert updated.plans[1].context == (
		"query_1",
		"g_query_1_monitor_accepting",
	)
	assert updated.plans[2].context == (
		"query_1",
		"g_query_1_monitor_state_q0",
	)
	assert updated.plans[2].body == (
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_1", ()),
		AgentSpeakBodyStep("subgoal", "g_query_1", ()),
	)
	assert updated.plans[4].context == ("query_1", "obj_tp(X, item)")
	assert updated.plans[4].body == (
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_1_repair_1_1", ()),
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_1_done", ()),
	)
	assert updated.plans[5].context == (
		"query_1",
		"obj_tp(X, item)",
		"done(X)",
	)
	assert updated.plans[5].body == ()
	assert updated.plans[6].context == (
		"query_1",
		"obj_tp(X, item)",
		"not done(X)",
	)
	assert updated.plans[6].body == (
		AgentSpeakBodyStep("subgoal", "done", ("X",)),
	)
	assert updated.initial_beliefs == ("query_1",)
	assert updated.metadata["temporal_goal_append"]["goal_name"] == "g_query_1"
	assert updated.metadata["temporal_goal_append"]["wrapper_mode"] == (
		"runtime_monitored_dfa_product"
	)
	assert updated.metadata["temporal_goal_append"]["progress_transition_count"] == 2
	assert updated.metadata["temporal_goal_append"]["negative_guard_count"] == 0
	assert updated.metadata["temporal_goal_append"]["negative_guard_policy"] == (
		"completion_context_with_conditional_may_add_preservation"
	)
	assert updated.metadata["temporal_goal_append"]["negative_atomic_module_supported"] is False
	assert (
		updated.metadata["temporal_goal_append"]
		["negative_guard_establishment_supported"]
		is True
	)
	assert updated.metadata["temporal_goal_append"]["transition_controller_strategy"] == (
		"monitored_balanced_repair_tree"
	)
	assert updated.metadata["temporal_goal_append"]["runtime_monitor_required"] is True
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


def test_temporal_compiler_variants_share_inputs_and_isolate_mechanisms(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "independent-domain.pddl"
	domain_file.write_text(
		"""
(define (domain independent)
 (:requirements :strips)
 (:predicates (seed) (left) (right))
 (:action make-left :parameters () :precondition (seed) :effect (left))
 (:action make-right :parameters () :precondition (seed) :effect (right))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="independent",
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
			{"source_state": "q0", "target_state": "q1", "raw_label": "right & left"},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	outputs = {
		variant: append_temporal_goal_to_library(
			plan_library=library,
			goal_name=f"g_{variant.value}",
			dfa_payload=dfa_payload,
			domain_file=domain_file,
			compiler_variant=variant,
		)
		for variant in TemporalCompilerVariant
	}

	contracts = {
		variant: output.metadata["temporal_goal_append"]["experiment_contract"]
		for variant, output in outputs.items()
	}
	assert {contract["dfa_fingerprint"] for contract in contracts.values()} == {
		contracts[TemporalCompilerVariant.CERTIFIED_BALANCED]["dfa_fingerprint"],
	}
	assert {contract["atomic_library_fingerprint"] for contract in contracts.values()} == {
		contracts[TemporalCompilerVariant.CERTIFIED_BALANCED][
			"atomic_library_fingerprint"
		],
	}
	assert {
		contract["compiler_variant"] for contract in contracts.values()
	} == {variant.value for variant in TemporalCompilerVariant}
	assert len(
		{contract["controller_fingerprint"] for contract in contracts.values()},
	) == len(TemporalCompilerVariant)

	unprotected = outputs[TemporalCompilerVariant.DFA_AWARE_UNPROTECTED]
	assert any(plan.plan_name.endswith("_repair_1") for plan in unprotected.plans)
	assert not any("repair_1_2_dispatch" in plan.plan_name for plan in unprotected.plans)
	unprotected_repair = next(
		plan for plan in unprotected.plans if plan.plan_name.endswith("_repair_1")
	)
	assert unprotected_repair.binding_certificate[0]["serialization_certificate"][
		"certificate_kind"
	] == "evaluation_only_canonical_unprotected_serialization"

	certified_flat = outputs[TemporalCompilerVariant.CERTIFIED_FLAT]
	assert any(plan.plan_name.endswith("_repair_1") for plan in certified_flat.plans)
	assert not any("repair_1_2_dispatch" in plan.plan_name for plan in certified_flat.plans)

	certified_linear = outputs[TemporalCompilerVariant.CERTIFIED_LINEAR]
	assert any(
		plan.plan_name.endswith("_repair_linear") for plan in certified_linear.plans
	)
	assert not any(
		"repair_1_2_dispatch" in plan.plan_name for plan in certified_linear.plans
	)
	linear_entry = next(
		plan
		for plan in certified_linear.plans
		if plan.plan_name.endswith("_repair_linear")
	)
	assert [step.symbol for step in linear_entry.body] == [
		f"g_certified_linear_trans_1_repair_{index}_{index}"
		for index in range(1, 3)
	] + ["g_certified_linear_trans_1_done"]

	balanced = outputs[TemporalCompilerVariant.CERTIFIED_BALANCED]
	assert any("repair_1_2_dispatch" in plan.plan_name for plan in balanced.plans)
	completion = outputs[TemporalCompilerVariant.COMPLETION_BOUNDARY_MONITOR]
	completion_achievements = tuple(
		plan
		for plan in completion.plans
		if plan.binding_certificate
		and plan.binding_certificate[-1].get("wrapper_role")
		== "transition_repair_tree_leaf_achievement"
	)
	assert completion_achievements
	assert all(
		plan.body[-1]
		== AgentSpeakBodyStep("action", "temporal_monitor_checkpoint", ())
		for plan in completion_achievements
	)
	assert completion.metadata["temporal_goal_append"][
		"monitor_observation_boundary"
	] == "atomic_module_completion"


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

	assert updated.plans[3].body == (
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_1", ()),
		AgentSpeakBodyStep("subgoal", "g_query_1", ()),
	)
	assert updated.plans[4].body == (
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_2", ()),
		AgentSpeakBodyStep("subgoal", "g_query_1", ()),
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
		"not g_query_1_monitor_state_q0",
	)
	assert first_done.binding_certificate[0]["completion_condition"] == (
		"source_state_exit"
	)
	second_done = next(
		plan for plan in updated.plans if plan.plan_name == "g_query_1_trans_2_done_success"
	)
	assert second_done.context == (
		"query_1",
		"obj_tp(Y, item)",
		"not g_query_1_monitor_state_q1",
	)
	second_leaf = next(
		plan
		for plan in updated.plans
		if plan.plan_name == "g_query_1_trans_2_repair_2_2_achieve"
	)
	assert second_leaf.context == (
		"query_1",
		"obj_tp(Y, item)",
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
		"negative_guard_establishment_checked": False,
		"negative_guard_establishable": True,
		"negative_guard_establishers": {},
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
	assert "g_query_1_trans_1_selected_completed" in repair_subgoals


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

	assert transition.context == (
		"query_1",
		"not g_query_1_monitor_state_q0",
	)
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
		"negative_guard_establishment_checked": True,
		"negative_guard_establishable": False,
		"negative_guard_establishers": {},
	}


def test_append_temporal_goal_observes_negative_numeric_equality_fail_closed(
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

	updated = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	numeric_leaf = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("literal_atom") == "fuel(0)"
	)
	assert numeric_leaf.context[-1] == "not fuel(0)"
	assert numeric_leaf.body == ()
	assert (
		numeric_leaf.binding_certificate[0]["serialization_certificate"]
		["observation_only_negative_literals"]
		== ["fuel(0)"]
	)


def test_numeric_conjunction_orders_effect_producer_before_numeric_observer(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "numeric-observer-domain.pddl"
	domain_file.write_text(
		"""
(define (domain numeric-observer)
 (:requirements :strips :fluents)
 (:predicates (ready ?x) (loaded ?x))
 (:functions (level))
 (:action load
  :parameters (?x)
  :precondition (and (ready ?x) (= (level) 1))
  :effect (and (loaded ?x) (decrease (level) 1)))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="numeric-observer",
		plans=(
			AgentSpeakPlan(
				"loaded_already_true",
				AgentSpeakTrigger("achievement_goal", "loaded", ("X",)),
				("loaded(X)",),
				(),
			),
			AgentSpeakPlan(
				"loaded_via_load",
				AgentSpeakTrigger("achievement_goal", "loaded", ("X",)),
				("ready(X)", "level(N)", "N == 1"),
				(AgentSpeakBodyStep("action", "load", ("X",)),),
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
				"raw_label": "level(0) & loaded(item)",
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
	leaves = tuple(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("wrapper_role")
		in {
			"transition_repair_tree_leaf_satisfied",
			"transition_repair_tree_leaf_achievement",
		}
	)
	loaded_leaf = next(
		plan
		for plan in leaves
		if plan.binding_certificate[0].get("literal_atom") == "loaded(item)"
		and plan.binding_certificate[0].get("wrapper_role")
		== "transition_repair_tree_leaf_achievement"
	)
	numeric_leaves = tuple(
		plan
		for plan in leaves
		if plan.binding_certificate[0].get("literal_atom") == "level(0)"
	)

	assert loaded_leaf.binding_certificate[0]["literal_index"] == 1
	assert all(plan.binding_certificate[0]["literal_index"] == 2 for plan in numeric_leaves)
	assert any(not plan.body for plan in numeric_leaves)
	assert any(
		plan.body and plan.body[0].kind == "subgoal"
		for plan in numeric_leaves
	)
	serialization = loaded_leaf.binding_certificate[0]["serialization_certificate"]
	assert serialization["certificate_kind"] == "mixed_boolean_numeric_effect_order"
	assert serialization["threat_edges"] == [[1, 0]]


def test_numeric_singleton_uses_schema_certified_unit_progress_action(
	tmp_path: Path,
) -> None:
	domain_file = _write_numeric_resource_domain(tmp_path)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "pogo_sticks_to_make(0)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=PlanLibrary(domain_name="numeric-resource", plans=()),
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	progress_plan = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[-1].get("wrapper_role")
		== "query_local_mixed_numeric_safe_branch"
	)

	assert progress_plan.context == (
		"pogo_sticks_to_make(N)",
		"N > 0",
	)
	assert progress_plan.body == (
		AgentSpeakBodyStep("action", "craft_wooden_pogo", ()),
	)
	assert progress_plan.binding_certificate[0]["certificate_kind"] == (
		"unit_monotone_numeric_progress"
	)


def test_numeric_action_side_effect_establishes_observation_only_boolean_sibling(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "numeric-side-effect-domain.pddl"
	domain_file.write_text(
		"""
(define (domain numeric-side-effect)
 (:requirements :strips :fluents)
 (:predicates (ready ?x) (opened ?x))
 (:functions (count))
 (:action open-and-count
  :parameters (?x)
  :precondition (ready ?x)
  :effect (and (opened ?x) (increase (count) 1)))
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
				"raw_label": "opened(item) & count(1)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=PlanLibrary(domain_name="numeric-side-effect", plans=()),
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	numeric_leaf = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("literal_atom") == "count(1)"
		and plan.body
	)
	serialization = numeric_leaf.binding_certificate[0]["serialization_certificate"]

	assert numeric_leaf.binding_certificate[0]["literal_index"] == 1
	assert serialization["side_effect_establishment_edges"] == [[1, 0]]
	assert serialization["ordered_literal_indexes"] == [1, 0]


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
		if plan.plan_name == "g_query_1_trans_1_repair_2_2_achieve"
	)
	certificate = next(
		plan
		for plan in query_plans
		if plan.plan_name == "g_query_1_trans_1_repair_tree"
	).binding_certificate[0]["serialization_certificate"]

	assert "deliver-safely" in query_actions
	assert "deliver-damaged" not in query_actions
	assert repair.body[0].symbol == "g_query_1_trans_1_selected_delivered"
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
		if plan.plan_name.endswith("_monitor_accepting")
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
		"g_query_1_monitor_accepting",
		"g_query_1_trans_1_monitor_dispatch",
		"g_query_1_trans_1_repair_tree",
		"g_query_1_trans_1_repair_1_1_satisfied",
		"g_query_1_trans_1_done_success",
		"g_query_1_trans_1_done_replay",
	]
	assert updated.plans[1].context == (
		"query_1",
		"g_query_1_monitor_state_q0",
	)
	assert updated.plans[1].body == (
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_1", ()),
		AgentSpeakBodyStep("subgoal", "g_query_1", ()),
	)


def test_append_temporal_goal_compiles_branching_dfa_with_runtime_monitor(
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

	updated = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	entry_plans = tuple(plan for plan in updated.plans if plan.trigger.symbol == "g_query_1")
	assert any(
		"g_query_1_monitor_accepting" in plan.context and not plan.body
		for plan in entry_plans
	)
	assert {
		context
		for plan in entry_plans
		for context in plan.context
		if context.startswith("g_query_1_monitor_state_")
	} == {
		"g_query_1_monitor_state_q0",
		"g_query_1_monitor_state_q1",
		"g_query_1_monitor_state_q2",
	}
	assert updated.metadata["temporal_goal_append"]["wrapper_mode"] == (
		"runtime_monitored_dfa_product"
	)


def test_until_progress_edges_merge_to_their_common_achievement_objective(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "until-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain until-fragment)
		 (:requirements :strips)
		 (:predicates (safe) (complete))
		 (:action complete-now
		  :parameters ()
		  :precondition (safe)
		  :effect (and (complete) (not (safe)))
		 )
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="until-fragment",
		plans=(
			AgentSpeakPlan(
				"complete_via_action",
				AgentSpeakTrigger("achievement_goal", "complete", ()),
				("safe",),
				(AgentSpeakBodyStep("action", "complete-now", ()),),
			),
		),
	)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{
				"source_state": "q0",
				"target_state": "q0",
				"raw_label": "safe & not complete",
			},
			{
				"source_state": "q0",
				"target_state": "dead",
				"raw_label": "not safe & not complete",
			},
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "safe & complete",
			},
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "not safe & complete",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
			{"source_state": "dead", "target_state": "dead", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	repair_leaves = tuple(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("wrapper_role")
		== "transition_repair_tree_leaf_achievement"
	)
	assert len(repair_leaves) == 1
	assert repair_leaves[0].body[0].kind == "subgoal"
	assert repair_leaves[0].body[0].symbol.endswith("_source_safe_complete")
	assert any(
		plan.trigger.symbol == repair_leaves[0].body[0].symbol
		and plan.body == (AgentSpeakBodyStep("action", "complete-now", ()),)
		and plan.binding_certificate[-1].get("certificate_kind")
		== "primitive_prefix_source_invariant_preservation"
		for plan in updated.plans
	)
	assert repair_leaves[0].context[-1] == "not complete"
	assert all("safe" not in plan.context for plan in repair_leaves)


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
		"g_query_1_monitor_accepting",
		"g_query_1_trans_1_monitor_dispatch",
		"g_query_1_trans_1_done",
	]
	assert updated.plans[2].context == (
		"query_1",
		"obj_tp(X, item)",
		"not g_query_1_monitor_state_q0",
	)
	assert updated.plans[2].body == ()


def test_append_temporal_goal_establishes_negative_only_progress_from_pddl_delete(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "deactivation-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain deactivation)
		 (:requirements :strips :typing)
		 (:types item - object)
		 (:predicates (active ?x - item))
		 (:action deactivate
		  :parameters (?x - item)
		  :precondition (active ?x)
		  :effect (not (active ?x))
		 )
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(domain_name="deactivation", plans=())
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "not active(X)",
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
	negative_leaf = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("literal_polarity") == "negative"
		and plan.binding_certificate[0].get("wrapper_role")
		== "transition_repair_tree_leaf_achievement"
	)
	establisher = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[-1].get("certificate_kind")
		== "pddl_single_action_must_delete"
	)

	assert negative_leaf.context[-1] == "active(X)"
	assert negative_leaf.body == (
		AgentSpeakBodyStep("subgoal", establisher.trigger.symbol, ("X",)),
	)
	assert establisher.context == ("obj_tp(X, item)", "active(X)")
	assert establisher.body == (AgentSpeakBodyStep("action", "deactivate", ("X",)),)


def test_append_temporal_goal_establishes_negative_guard_via_positive_side_effect(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "acquisition-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain acquisition)
		 (:requirements :strips :typing)
		 (:types actor item - object)
		 (:predicates
		  (ready ?actor - actor ?item - item)
		  (available ?actor - actor)
		  (holding ?actor - actor ?item - item)
		 )
		 (:action acquire
		  :parameters (?actor - actor ?item - item)
		  :precondition (and (ready ?actor ?item) (available ?actor))
		  :effect (and (holding ?actor ?item) (not (available ?actor)))
		 )
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="acquisition",
		plans=(
			AgentSpeakPlan(
				"holding_already_true",
				AgentSpeakTrigger("achievement_goal", "holding", ("X", "Y")),
				("holding(X, Y)",),
				(),
			),
			AgentSpeakPlan(
				"holding_via_acquire",
				AgentSpeakTrigger("achievement_goal", "holding", ("X", "Y")),
				("ready(X, Y)", "available(X)"),
				(AgentSpeakBodyStep("action", "acquire", ("X", "Y")),),
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
				"raw_label": "holding(agent, item) & not available(agent)",
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
	negative_leaf = next(
		plan
		for plan in query_plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("literal_polarity") == "negative"
		and plan.binding_certificate[0].get("wrapper_role")
		== "transition_repair_tree_leaf_achievement"
	)
	establishment_plan = next(
		plan
		for plan in query_plans
		if plan.binding_certificate
		and plan.binding_certificate[-1].get("wrapper_role")
		== "query_local_negative_guard_establishment_branch"
	)

	assert negative_leaf.context[-1] == "available(agent)"
	assert negative_leaf.body[0].symbol == establishment_plan.trigger.symbol
	assert establishment_plan.context == (
		"ready(agent, item)",
		"available(agent)",
	)
	assert establishment_plan.body == (
		AgentSpeakBodyStep("action", "acquire", ("agent", "item")),
	)
	serialization = next(
		plan.binding_certificate[0]["serialization_certificate"]
		for plan in query_plans
		if plan.plan_name == "g_query_1_trans_1_repair_tree"
	)
	assert serialization["negative_guard_establishment_checked"] is True
	assert serialization["negative_guard_establishable"] is True


def test_accepting_complete_guard_establisher_precedes_partial_negative_fallback(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "typed-transfer-domain.pddl"
	domain_file.write_text(
		"""
(define (domain typed-transfer)
 (:requirements :strips :typing)
 (:types
  movable - object
  carrier - movable
  site - object
  parcel - movable
  cart jet - carrier)
 (:predicates
  (placed ?x - movable ?s - site)
  (inside ?p - parcel ?c - carrier))
 (:action stow_cart
  :parameters (?p - parcel ?c - cart ?s - site)
  :precondition (and (placed ?p ?s) (placed ?c ?s))
  :effect (and (inside ?p ?c) (not (placed ?p ?s))))
 (:action stow_jet
  :parameters (?p - parcel ?j - jet ?s - site)
  :precondition (and (placed ?p ?s) (placed ?j ?s))
  :effect (and (inside ?p ?j) (not (placed ?p ?s))))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="typed-transfer",
		plans=(
			AgentSpeakPlan(
				"inside_already_true",
				AgentSpeakTrigger("achievement_goal", "inside", ("X", "Y")),
				("inside(X, Y)",),
				(),
			),
			AgentSpeakPlan(
				"inside_via_cart",
				AgentSpeakTrigger("achievement_goal", "inside", ("X", "Y")),
				(
					"obj_tp(X, parcel)",
					"obj_tp(Y, cart)",
					"placed(X, Z)",
					"obj_tp(Z, site)",
					"placed(Y, Z)",
				),
				(AgentSpeakBodyStep("action", "stow_cart", ("X", "Y", "Z")),),
			),
			AgentSpeakPlan(
				"inside_via_jet",
				AgentSpeakTrigger("achievement_goal", "inside", ("X", "Y")),
				(
					"obj_tp(X, parcel)",
					"obj_tp(Y, jet)",
					"placed(X, Z)",
					"obj_tp(Z, site)",
					"placed(Y, Z)",
				),
				(AgentSpeakBodyStep("action", "stow_jet", ("X", "Y", "Z")),),
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
				"raw_label": "inside(pkg, jet0) & not placed(pkg, hub)",
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
	negative_leaf = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("literal_polarity") == "negative"
		and plan.binding_certificate[0].get("wrapper_role")
		== "transition_repair_tree_leaf_achievement"
	)
	helper_symbol = negative_leaf.body[0].symbol
	helper_plans = tuple(
		plan for plan in updated.plans if plan.trigger.symbol == helper_symbol
	)
	certificate_kinds = tuple(
		plan.binding_certificate[-1].get("certificate_kind")
		for plan in helper_plans
	)

	assert "pddl_single_action_whole_guard" in certificate_kinds
	assert "pddl_single_action_must_delete" in certificate_kinds
	assert max(
		index
		for index, kind in enumerate(certificate_kinds)
		if kind == "pddl_single_action_whole_guard"
	) < min(
		index
		for index, kind in enumerate(certificate_kinds)
		if kind == "pddl_single_action_must_delete"
	)
	assert any(
		plan.body
		== (AgentSpeakBodyStep("action", "stow_jet", ("pkg", "jet0", "hub")),)
		for plan in helper_plans
	)
	serialization = next(
		plan.binding_certificate[0]["serialization_certificate"]
		for plan in updated.plans
		if plan.plan_name == "g_query_1_trans_1_repair_tree"
	)
	assert serialization["accepting_whole_guard_dominance_checked"] is True
	assert serialization["whole_guard_dominating_branch_count"] >= 1
	assert serialization["whole_guard_dominance_scope"] == "accepting_target_only"
	assert serialization["negative_guard_establishment_strategy"] == (
		"complete_guard_first_with_partial_deleter_fallback"
	)

	nonterminal = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_2",
		dfa_payload={
			"initial_state": "q0",
			"accepting_states": ["q2"],
			"guarded_transitions": [
				{
					"source_state": "q0",
					"target_state": "q1",
					"raw_label": "inside(pkg, jet0) & not placed(pkg, hub)",
				},
				{
					"source_state": "q1",
					"target_state": "q2",
					"raw_label": "inside(pkg, jet0)",
				},
				{"source_state": "q2", "target_state": "q2", "raw_label": "true"},
			],
		},
		domain_file=domain_file,
	)
	nonterminal_negative_leaf = next(
		plan
		for plan in nonterminal.plans
		if plan.plan_name.startswith("g_query_2_trans_1")
		and plan.binding_certificate
		and plan.binding_certificate[0].get("literal_polarity") == "negative"
		and plan.binding_certificate[0].get("wrapper_role")
		== "transition_repair_tree_leaf_achievement"
	)
	nonterminal_helper_plans = tuple(
		plan
		for plan in nonterminal.plans
		if plan.trigger.symbol == nonterminal_negative_leaf.body[0].symbol
	)
	assert nonterminal_helper_plans
	assert all(
		plan.binding_certificate[-1].get("certificate_kind")
		== "pddl_single_action_must_delete"
		for plan in nonterminal_helper_plans
	)
	nonterminal_serialization = next(
		plan.binding_certificate[0]["serialization_certificate"]
		for plan in nonterminal.plans
		if plan.plan_name == "g_query_2_trans_1_repair_tree"
	)
	assert "accepting_whole_guard_dominance_checked" not in nonterminal_serialization


def test_single_action_whole_guard_certificate_needs_no_atomic_seed_module(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "conversion-domain.pddl"
	domain_file.write_text(
		"""
(define (domain conversion)
 (:requirements :strips :typing)
 (:types item - object)
 (:predicates (located ?x - item) (raw ?x - item) (processed ?x - item))
 (:action convert
  :parameters (?x - item)
  :precondition (and (located ?x) (raw ?x))
  :effect (and (processed ?x) (not (raw ?x))))
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
				"raw_label": "processed(item) & not raw(item)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=PlanLibrary(domain_name="conversion", plans=()),
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	helper = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[-1].get("certificate_kind")
		== "pddl_single_action_whole_guard"
	)
	positive_leaf = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("literal_atom") == "processed(item)"
		and plan.binding_certificate[0].get("wrapper_role")
		== "transition_repair_tree_leaf_achievement"
	)
	negative_leaf = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("literal_atom") == "raw(item)"
		and plan.binding_certificate[0].get("wrapper_role")
		== "transition_repair_tree_leaf_satisfied"
	)

	assert helper.context == (
		"obj_tp(item, item)",
		"located(item)",
		"raw(item)",
	)
	assert helper.body == (AgentSpeakBodyStep("action", "convert", ("item",)),)
	assert positive_leaf.body == (
		AgentSpeakBodyStep("subgoal", helper.trigger.symbol, ("item",)),
	)
	assert positive_leaf.binding_certificate[0]["literal_index"] == 1
	assert negative_leaf.binding_certificate[0]["literal_index"] == 2


def test_whole_guard_action_is_reachable_from_every_positive_literal(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "joint-effect-domain.pddl"
	domain_file.write_text(
		"""
(define (domain joint-effect)
 (:requirements :strips :typing)
 (:types item - object)
 (:predicates
  (enabled ?x - item ?y - item)
  (ready ?x - item ?y - item)
  (done ?y - item))
 (:action complete
  :parameters (?x - item ?y - item)
  :precondition (enabled ?x ?y)
  :effect (and (ready ?x ?y) (done ?y)))
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
				"raw_label": "ready(X,Y) & done(Y)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=PlanLibrary(domain_name="joint-effect", plans=()),
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	helper = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[-1].get("certificate_kind")
		== "pddl_single_action_whole_guard"
	)
	achievement_leaves = {
		plan.binding_certificate[0]["literal_atom"]: plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("wrapper_role")
		== "transition_repair_tree_leaf_achievement"
	}

	assert set(achievement_leaves) == {"ready(X, Y)", "done(Y)"}
	assert all(
		plan.body
		== (AgentSpeakBodyStep("subgoal", helper.trigger.symbol, ("X", "Y")),)
		for plan in achievement_leaves.values()
	)
	assert helper.trigger.arguments == ("X", "Y")


def test_negative_establisher_binds_deleter_destination_from_positive_sibling(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "functional-location-domain.pddl"
	domain_file.write_text(
		"""
(define (domain functional-location)
 (:requirements :strips :typing)
 (:types location - object)
 (:predicates (at ?x - location))
 (:action relocate
  :parameters (?from - location ?to - location)
  :precondition (at ?from)
  :effect (and (not (at ?from)) (at ?to)))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="functional-location",
		plans=(
			AgentSpeakPlan(
				"at_via_relocate",
				AgentSpeakTrigger("achievement_goal", "at", ("X",)),
				("at(Y)", "Y \\== X"),
				(AgentSpeakBodyStep("action", "relocate", ("Y", "X")),),
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
				"raw_label": "at(destination) & not at(origin)",
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
	establisher = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[-1].get("certificate_kind")
		== "pddl_single_action_must_delete"
	)
	negative_leaf = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("literal_atom") == "at(origin)"
		and plan.binding_certificate[0].get("wrapper_role")
		== "transition_repair_tree_leaf_achievement"
	)

	assert establisher.context == (
		"obj_tp(origin, location)",
		"obj_tp(destination, location)",
		"at(origin)",
	)
	assert establisher.body == (
		AgentSpeakBodyStep("action", "relocate", ("origin", "destination")),
	)
	assert negative_leaf.body == (
		AgentSpeakBodyStep("subgoal", establisher.trigger.symbol, ()),
	)


def test_single_action_whole_guard_certifies_boolean_and_numeric_effects(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "mixed-effect-domain.pddl"
	domain_file.write_text(
		"""
(define (domain mixed-effect)
 (:requirements :strips :typing :fluents)
 (:types item - object)
 (:predicates (ready ?x - item) (loaded ?x - item))
 (:functions (capacity))
 (:action load-one
  :parameters (?x - item)
  :precondition (and (ready ?x) (> (capacity) 0))
  :effect (and (loaded ?x) (decrease (capacity) 1)))
 (:action unload-one
  :parameters (?x - item)
  :precondition (loaded ?x)
  :effect (and (not (loaded ?x)) (increase (capacity) 1)))
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
				"raw_label": "loaded(item) & capacity(3)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	library = PlanLibrary(
		domain_name="mixed-effect",
		plans=(
			AgentSpeakPlan(
				"loaded_via_load",
				AgentSpeakTrigger("achievement_goal", "loaded", ("X",)),
				("ready(X)", "capacity(N)", "N > 0"),
				(AgentSpeakBodyStep("action", "load-one", ("X",)),),
			),
		),
	)
	updated = append_temporal_goal_to_library(
		plan_library=library,
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	helper = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[-1].get("certificate_kind")
		== "pddl_single_action_whole_guard"
	)
	serialization = helper.binding_certificate[-1]

	assert helper.context == (
		"obj_tp(item, item)",
		"ready(item)",
		"capacity(N)",
		"N > 0",
		"capacity(4)",
	)
	assert helper.body == (AgentSpeakBodyStep("action", "load-one", ("item",)),)
	assert serialization["numeric_guard_literals"] == ["capacity(3)"]
	assert serialization["numeric_predecessor_contexts"] == ["capacity(4)"]


def test_grounded_whole_guard_actions_keep_pddl_subtype_contexts(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "typed-carrier-domain.pddl"
	domain_file.write_text(
		"""
(define (domain typed-carrier)
 (:requirements :strips :typing)
 (:types vehicle package location - object
         truck airplane - vehicle)
 (:predicates (at ?x - object ?l - location)
              (in ?p - package ?v - vehicle))
 (:action load-truck
  :parameters (?p - package ?v - truck ?l - location)
  :precondition (and (at ?p ?l) (at ?v ?l))
  :effect (and (not (at ?p ?l)) (in ?p ?v)))
 (:action load-airplane
  :parameters (?p - package ?v - airplane ?l - location)
  :precondition (and (at ?p ?l) (at ?v ?l))
  :effect (and (not (at ?p ?l)) (in ?p ?v)))
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
				"raw_label": "in(parcel, plane) & not at(parcel, hub)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=PlanLibrary(domain_name="typed-carrier", plans=()),
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	helpers = tuple(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[-1].get("certificate_kind")
		== "pddl_single_action_whole_guard"
	)
	contexts_by_action = {
		plan.body[0].symbol: plan.context
		for plan in helpers
	}

	assert "obj_tp(plane, truck)" in contexts_by_action["load-truck"]
	assert "obj_tp(plane, airplane)" in contexts_by_action["load-airplane"]
	assert "obj_tp(parcel, package)" in contexts_by_action["load-truck"]
	assert "obj_tp(hub, location)" in contexts_by_action["load-truck"]


def test_numeric_repair_precedes_negative_observation_when_final_action_establishes_both(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "numeric-carrier-domain.pddl"
	domain_file.write_text(
		"""
(define (domain numeric-carrier)
 (:requirements :strips :typing :fluents)
 (:types vehicle package location - object)
 (:predicates (at ?x - object ?l - location))
 (:functions (capacity ?v - vehicle))
 (:action drive
  :parameters (?v - vehicle ?from - location ?to - location)
  :precondition (at ?v ?from)
  :effect (and (not (at ?v ?from)) (at ?v ?to)))
 (:action pick-up
  :parameters (?v - vehicle ?l - location ?p - package)
  :precondition (and (at ?v ?l) (at ?p ?l) (> (capacity ?v) 0))
  :effect (and (not (at ?p ?l)) (decrease (capacity ?v) 1)))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="numeric-carrier",
		plans=(
			AgentSpeakPlan(
				"at_via_drive",
				AgentSpeakTrigger("achievement_goal", "at", ("X", "Y")),
				("at(X, A)", "A \\== Y"),
				(AgentSpeakBodyStep("action", "drive", ("X", "A", "Y")),),
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
				"raw_label": "capacity(carrier, 3) & not at(parcel, hub)",
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
	root = next(
		plan for plan in updated.plans if plan.plan_name == "g_query_1_trans_1_repair_tree"
	)
	serialization = root.binding_certificate[0]["serialization_certificate"]
	leaves = tuple(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("wrapper_role")
		in {
			"transition_repair_tree_leaf_satisfied",
			"transition_repair_tree_leaf_achievement",
		}
	)

	assert serialization["repair_positive_before_negative"] is True
	assert any(
		plan.binding_certificate[0].get("literal_atom") == "capacity(carrier, 3)"
		and plan.binding_certificate[0].get("literal_index") == 1
		for plan in leaves
	)
	assert any(
		plan.binding_certificate[0].get("literal_atom") == "at(parcel, hub)"
		and plan.binding_certificate[0].get("literal_index") == 2
		for plan in leaves
	)
	assert any(
		certificate.get("negative_guard_established_by_final_action") is True
		for plan in updated.plans
		for certificate in plan.binding_certificate
	)


def test_numeric_progress_alpha_renames_action_precondition_value_variables(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "numeric-production-domain.pddl"
	domain_file.write_text(
		"""
(define (domain numeric-production)
 (:requirements :strips :fluents)
 (:predicates (ready))
 (:functions (raw_count) (product_count))
	(:action harvest
	 :parameters ()
	 :precondition (ready)
	 :effect (increase (raw_count) 1))
 (:action produce
  :parameters ()
  :precondition (and (ready) (>= (raw_count) 1))
  :effect (and (decrease (raw_count) 1) (increase (product_count) 4)))
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
				"raw_label": "product_count(4)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=PlanLibrary(domain_name="numeric-production", plans=()),
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	progress = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("wrapper_role")
		== "query_local_numeric_progress_branch"
	)

	assert "product_count(N)" in progress.context
	assert "N == 0" in progress.context
	assert "raw_count(M)" in progress.context
	assert "M >= 1" in progress.context
	preparation = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("certificate_kind")
		== "lexicographic_numeric_requirement_preparation"
	)
	assert preparation.context[:4] == (
		"product_count(N)",
		"N == 0",
		"raw_count(N0)",
		"N0 < 1",
	)
	assert preparation.body[0] == AgentSpeakBodyStep("action", "harvest", ())
	assert preparation.body[1].kind == "subgoal"
	assert preparation.body[1].symbol.endswith("_repair_product_count_1")
	assert preparation.body[1].arguments == ("4",)


def test_numeric_until_separates_repeatable_preserving_and_exact_terminal_steps(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "numeric-loading-domain.pddl"
	domain_file.write_text(
		"""
(define (domain numeric-loading)
 (:requirements :strips :typing :fluents)
 (:types item location - object)
 (:predicates (at ?x - item ?l - location) (carrier-at ?l - location))
 (:functions (capacity))
 (:action load
  :parameters (?x - item ?l - location)
  :precondition (and (at ?x ?l) (carrier-at ?l) (>= (capacity) 1))
  :effect (and (not (at ?x ?l)) (decrease (capacity) 1)))
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
				"target_state": "q0",
				"raw_label": "at(protected, hub) & not capacity(2)",
			},
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "at(protected, hub) & capacity(2)",
			},
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "not at(protected, hub) & capacity(2)",
			},
			{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
		],
	}

	updated = append_temporal_goal_to_library(
		plan_library=PlanLibrary(domain_name="numeric-loading", plans=()),
		goal_name="g_query_1",
		dfa_payload=dfa_payload,
		domain_file=domain_file,
	)
	repeatable = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("certificate_kind")
		== "repeatable_source_invariant_preserving_numeric_progress"
	)
	terminal = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("source_invariant_violation_only_at_target")
		is True
	)
	base = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("certificate_kind")
		== "observed_numeric_target_base_case"
	)

	assert any("\\== protected" in item for item in repeatable.context)
	assert "capacity(N)" in terminal.context
	assert "N == 3" in terminal.context
	assert base.context == ("capacity(2)",)
	assert base.body == ()


def test_ground_action_only_plan_alpha_renames_outer_reserved_variables() -> None:
	plan = AgentSpeakPlan(
		"at_via_navigate",
		AgentSpeakTrigger("achievement_goal", "at", ("X", "Y")),
		("at(X, Z)", "Y \\== Z"),
		(AgentSpeakBodyStep("action", "navigate", ("X", "Z", "Y")),),
	)

	context, body = _ground_action_only_plan(
		plan,
		goal=DFALiteral("at", ("rover1", "waypoint1")),
		reserved_variables=("Z",),
	)

	assert context == ("at(rover1, Z0)", "waypoint1 \\== Z0")
	assert body == (
		AgentSpeakBodyStep("action", "navigate", ("rover1", "Z0", "waypoint1")),
	)


def test_until_repair_selects_only_primitive_prefix_source_invariant_safe_branches(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "until-carrier-domain.pddl"
	domain_file.write_text(
		"""
(define (domain until-carrier)
 (:requirements :strips :typing)
 (:types package vehicle location - object)
 (:predicates
  (at ?p - package ?l - location)
  (staged ?p - package)
  (in ?p - package ?v - vehicle))
 (:action unsafe-stage
  :parameters (?p - package ?l - location)
  :precondition (at ?p ?l)
  :effect (and (not (at ?p ?l)) (staged ?p)))
 (:action finish-stage
  :parameters (?p - package ?v - vehicle)
  :precondition (staged ?p)
  :effect (in ?p ?v))
 (:action safe-load
  :parameters (?p - package ?v - vehicle ?l - location)
  :precondition (at ?p ?l)
  :effect (and (not (at ?p ?l)) (in ?p ?v)))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="until-carrier",
		plans=(
			AgentSpeakPlan(
				"in_via_unsafe_staging",
				AgentSpeakTrigger("achievement_goal", "in", ("X", "Y")),
				("at(X, L)",),
				(
					AgentSpeakBodyStep("action", "unsafe-stage", ("X", "L")),
					AgentSpeakBodyStep("action", "finish-stage", ("X", "Y")),
				),
			),
			AgentSpeakPlan(
				"in_via_safe_load",
				AgentSpeakTrigger("achievement_goal", "in", ("X", "Y")),
				("at(X, L)",),
				(AgentSpeakBodyStep("action", "safe-load", ("X", "Y", "L")),),
			),
		),
	)
	dfa_payload = {
		"initial_state": "q0",
		"accepting_states": ["q1"],
		"guarded_transitions": [
			{
				"source_state": "q0",
				"target_state": "q0",
				"raw_label": "at(parcel, origin) & not in(parcel, carrier)",
			},
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "at(parcel, origin) & in(parcel, carrier)",
			},
			{
				"source_state": "q0",
				"target_state": "q1",
				"raw_label": "not at(parcel, origin) & in(parcel, carrier)",
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
	source_safe_aliases = tuple(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[-1].get("certificate_kind")
		== "primitive_prefix_source_invariant_preservation"
	)
	achievement_leaf = next(
		plan
		for plan in updated.plans
		if plan.binding_certificate
		and plan.binding_certificate[0].get("wrapper_role")
		== "transition_repair_tree_leaf_achievement"
	)

	assert [plan.body[0].symbol for plan in source_safe_aliases] == ["safe-load"]
	assert source_safe_aliases[0].binding_certificate[-1]["source_invariants"] == [
		"at(parcel, origin)",
	]
	assert achievement_leaf.body == (
		AgentSpeakBodyStep("subgoal", source_safe_aliases[0].trigger.symbol, ("parcel", "carrier")),
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
	assert updated.plans[0].plan_name == "g_query_1_monitor_accepting"
	assert updated.metadata["temporal_goal_append"]["goal_name"] == "g_query_1"


def test_append_lifted_temporal_goal_restores_proposition_labels_from_atoms(
	tmp_path: Path,
) -> None:
	domain_file = _write_blocks_domain(tmp_path)
	library = PlanLibrary(
		domain_name="blocks",
		plans=(
			AgentSpeakPlan(
				"on_via_action",
				AgentSpeakTrigger("achievement_goal", "on", ("X", "Y")),
				("clear(Y)",),
				(AgentSpeakBodyStep("action", "place", ("X", "Y")),),
			),
		),
	)
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
	accepting = next(
		plan for plan in updated.plans if plan.plan_name == "g_query_1_monitor_accepting"
	)
	assert accepting.context == (
		"query_1",
		"g_query_1_monitor_accepting",
	)
	dispatch = next(
		plan for plan in updated.plans if plan.plan_name.endswith("_monitor_dispatch")
	)
	assert dispatch.body == (
		AgentSpeakBodyStep("subgoal", "g_query_1_trans_1", ()),
		AgentSpeakBodyStep("subgoal", "g_query_1", ()),
	)
	assert (
		updated.metadata["temporal_goal_append"]["progress_request_diagnostics"][0]
		["request"]["achievement_subgoals"]
		== [{"kind": "subgoal", "symbol": "on", "arguments": ["X", "Y"]}]
	)


def test_append_lifted_temporal_goal_applies_external_invocation_bindings(
	tmp_path: Path,
) -> None:
	domain_file = _write_blocks_domain(tmp_path)
	library = PlanLibrary(
		domain_name="blocks",
		plans=(
			AgentSpeakPlan(
				"on_via_action",
				AgentSpeakTrigger("achievement_goal", "on", ("X", "Y")),
				("clear(Y)",),
				(AgentSpeakBodyStep("action", "place", ("X", "Y")),),
			),
		),
	)
	case = LiftedLTLfGoalCase(
		query_id="query_1",
		goal_name="g_query_1",
		problem_file="p01.pddl",
		source_text="Eventually put X on Y.",
		ltlf_formula="F(a0)",
		atoms=(LTLfAtomSpec("a0", "on", ("X", "Y")),),
		bindings={"X": "b1", "Y": "b4"},
	)

	updated, dfa_payload = append_lifted_temporal_goal_case_to_library(
		plan_library=library,
		goal_case=case,
		domain_file=domain_file,
		dfa_builder=_FakeEncodedDFABuilder(),
	)

	assert dfa_payload["guarded_transitions"][0]["raw_label"] == "on(b1, b4)"
	achieve_plan = next(
		plan
		for plan in updated.plans
		if plan.plan_name == "g_query_1_trans_1_repair_1_1_achieve"
	)
	assert achieve_plan.body == (
		AgentSpeakBodyStep("subgoal", "on", ("b1", "b4")),
	)
	assert dfa_payload["lifted_atom_binding"]["invocation_bindings"] == {
		"X": "b1",
		"Y": "b4",
	}


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
	assert updated.plans[0].context == (
		"numeric_minecraft_test_1",
		"g_numeric_minecraft_test_1_monitor_accepting",
	)
	dispatch = next(
		plan for plan in updated.plans if plan.plan_name.endswith("_monitor_dispatch")
	)
	assert dispatch.body == (
		AgentSpeakBodyStep("subgoal", "g_numeric_minecraft_test_1_trans_1", ()),
		AgentSpeakBodyStep("subgoal", "g_numeric_minecraft_test_1", ()),
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
