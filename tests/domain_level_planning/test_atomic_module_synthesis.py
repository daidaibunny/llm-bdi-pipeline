from __future__ import annotations

from pathlib import Path

import domain_level_planning.atomic_module_synthesis as atomic_module_synthesis
import pytest

from domain_level_planning.atomic_module_synthesis import (
	PDDLLiteralSchema,
	_ParsedAction,
	_candidate_achieves_schema_obligation,
	_candidate_branch_covers_evidence,
	_resource_release_contract,
	_order_contexts_for_matching,
	_select_branches_with_clingo,
	synthesize_atomic_minimal_literal_module_library,
)
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.rendering import render_plan_library_asl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "blocksworld-tower" / "domain.pddl"


def test_schema_regression_composes_acyclic_chain_without_action_depth_bound(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "long-schema-chain.pddl"
	domain_file.write_text(
		"""
(define (domain long-schema-chain)
 (:requirements :strips :typing)
 (:types item - object)
 (:predicates
  (ready ?x - item)
  (stage1 ?x - item) (stage2 ?x - item) (stage3 ?x - item)
  (stage4 ?x - item) (stage5 ?x - item) (stage6 ?x - item)
  (completed ?x - item))
 (:action advance1
  :parameters (?x - item) :precondition (ready ?x) :effect (stage1 ?x))
 (:action advance2
  :parameters (?x - item) :precondition (stage1 ?x) :effect (stage2 ?x))
 (:action advance3
  :parameters (?x - item) :precondition (stage2 ?x) :effect (stage3 ?x))
 (:action advance4
  :parameters (?x - item) :precondition (stage3 ?x) :effect (stage4 ?x))
 (:action advance5
  :parameters (?x - item) :precondition (stage4 ?x) :effect (stage5 ?x))
 (:action advance6
  :parameters (?x - item) :precondition (stage5 ?x) :effect (stage6 ?x))
 (:action finish
  :parameters (?x - item) :precondition (stage6 ?x) :effect (completed ?x))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	domain = atomic_module_synthesis.PDDLParser.parse_domain(domain_file)
	actions = tuple(
		_ParsedAction.from_pddl(action)
		for action in domain.actions
	)

	sequences = atomic_module_synthesis._producer_action_sequences(
		actions=actions,
		type_tokens=domain.types,
		seed_predicates={"completed"},
		target_predicate="completed",
		module_predicates={
			"ready",
			"stage1",
			"stage2",
			"stage3",
			"stage4",
			"stage5",
			"stage6",
			"completed",
		},
		recursive_module_predicates=set(),
	)

	assert any(
		tuple(call.action.name for call in sequence.body_actions)
		== (
			"advance1",
			"advance2",
			"advance3",
			"advance4",
			"advance5",
			"advance6",
			"finish",
		)
		and tuple(literal.to_context() for literal in sequence.context_literals)
		== ("ready(X)",)
		for sequence in sequences
	)


def test_schema_regression_rejects_cyclic_producer_graph_before_search(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "generic-transfer.pddl"
	domain_file.write_text(
		"""
(define (domain generic-transfer)
 (:requirements :strips :typing)
 (:types item carrier place - object)
 (:predicates
  (item_at ?x - item ?p - place)
  (carrier_at ?c - carrier ?p - place)
  (loaded ?x - item ?c - carrier)
  (completed ?x - item ?p - place))
 (:action relocate
  :parameters (?c - carrier ?from - place ?to - place)
  :precondition (carrier_at ?c ?from)
  :effect (and (not (carrier_at ?c ?from)) (carrier_at ?c ?to)))
 (:action load_item
  :parameters (?x - item ?c - carrier ?p - place)
  :precondition (and (item_at ?x ?p) (carrier_at ?c ?p))
  :effect (and (not (item_at ?x ?p)) (loaded ?x ?c)))
 (:action unload_item
  :parameters (?x - item ?c - carrier ?p - place)
  :precondition (and (loaded ?x ?c) (carrier_at ?c ?p))
  :effect (and (not (loaded ?x ?c)) (item_at ?x ?p)))
 (:action finish
  :parameters (?x - item ?p - place)
  :precondition (item_at ?x ?p)
  :effect (completed ?x ?p))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	domain = atomic_module_synthesis.PDDLParser.parse_domain(domain_file)
	actions = tuple(_ParsedAction.from_pddl(action) for action in domain.actions)

	sequences = atomic_module_synthesis._producer_action_sequences(
		actions=actions,
		type_tokens=domain.types,
		seed_predicates={"completed"},
		target_predicate="completed",
		module_predicates={"item_at", "carrier_at", "loaded", "completed"},
		recursive_module_predicates=set(),
	)

	assert not any(
		tuple(call.action.name for call in sequence.body_actions)
		== ("relocate", "load_item", "relocate", "unload_item", "finish")
		for sequence in sequences
	)
	load_action = next(action for action in actions if action.name == "load_item")
	producer_maps = atomic_module_synthesis._producer_maps_for_regression_requirement(
		action=load_action,
		effect=load_action.add_effects[0],
		requirement=PDDLLiteralSchema("loaded", ("X", "C")),
		state_requirements=(PDDLLiteralSchema("carrier_at", ("C", "Y")),),
		avoid_variables={"X", "C", "Y"},
	)
	assert any(variable_map["?p"] == "Y" for variable_map in producer_maps)


def test_non_seed_producible_module_uses_bounded_support_composition(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "non-seed-support.pddl"
	domain_file.write_text(
		"""
(define (domain non-seed-support)
 (:requirements :strips :typing)
 (:types item - object)
 (:predicates (raw ?x - item) (component ?x - item)
              (intermediate ?x - item) (done ?x - item))
 (:action make-component
  :parameters (?x - item)
  :precondition (raw ?x)
  :effect (component ?x))
 (:action make-intermediate
  :parameters (?x - item)
  :precondition (component ?x)
  :effect (intermediate ?x))
 (:action finish
  :parameters (?x - item)
  :precondition (intermediate ?x)
  :effect (done ?x))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)

	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=("done",),
		source_backend="test",
		source_name="non-seed-support",
	)
	intermediate_macros = tuple(
		plan
		for plan in library.plans
		if plan.trigger.symbol == "intermediate"
		and tuple(step.symbol for step in plan.body)
		== ("make-component", "make-intermediate")
	)

	assert len(intermediate_macros) == 1
	assert intermediate_macros[0].context == (
		"obj_tp(X, item)",
		"raw(X)",
	)


def test_context_order_uses_bound_goal_arguments_before_unbound_buckets() -> None:
	context = _order_contexts_for_matching(
		(
			"at(Z, C)",
			"in-city(C, D)",
			"in-city(A, D)",
			"at(X, A)",
			"in-city(A, B)",
			"in-city(Y, B)",
		),
		(
			"obj_tp(A, location)",
			"obj_tp(B, city)",
			"obj_tp(C, location)",
			"obj_tp(D, city)",
			"obj_tp(X, package)",
			"obj_tp(Y, location)",
			"obj_tp(Z, truck)",
		),
		initial_bound_variables=("X", "Y"),
	)

	assert context[:3] == (
		"obj_tp(X, package)",
		"obj_tp(Y, location)",
		"at(X, A)",
	)
	assert context.index("at(X, A)") < context.index("in-city(A, B)")
	assert context.index("in-city(C, D)") < context.index("at(Z, C)")
	assert context.index("at(Z, C)") < context.index("obj_tp(Z, truck)")


def test_context_order_places_only_bound_inequalities_before_pddl_filters() -> None:
	context = _order_contexts_for_matching(
		(
			"surface(B)",
			"B != X",
			"B != Z",
			"clear(B)",
			"on(Z, X)",
			"at(B, A)",
			"at(Z, A)",
		),
		(
			"obj_tp(X, crate)",
			"obj_tp(B, surface)",
		),
		initial_bound_variables=("X",),
	)

	assert context.index("obj_tp(X, crate)") < context.index("on(Z, X)")
	assert context.index("on(Z, X)") < context.index("B != Z")
	assert context.index("at(B, A)") < context.index("obj_tp(B, surface)")
	assert context.index("obj_tp(B, surface)") < context.index("B != X")
	assert context.index("obj_tp(B, surface)") < context.index("B != Z")
	assert context.index("B != X") < context.index("surface(B)")
	assert context.index("B != Z") < context.index("surface(B)")
	assert context.index("B != X") < context.index("clear(B)")
	assert context.index("B != Z") < context.index("clear(B)")


def test_clingo_selector_removes_context_subsumed_duplicate_branch() -> None:
	weaker_context_branch = AgentSpeakPlan(
		plan_name="deliver_with_weaker_context",
		trigger=AgentSpeakTrigger("achievement_goal", "delivered", ("X",)),
		context=("at(X, Y)",),
		body=(AgentSpeakBodyStep("action", "drop", ("X", "Y")),),
	)
	stronger_context_branch = AgentSpeakPlan(
		plan_name="deliver_with_extra_context",
		trigger=AgentSpeakTrigger("achievement_goal", "delivered", ("X",)),
		context=("at(X, Y)", "clear(Y)"),
		body=(AgentSpeakBodyStep("action", "drop", ("X", "Y")),),
	)
	necessary_recursive_branch = AgentSpeakPlan(
		plan_name="deliver_prepare_at",
		trigger=AgentSpeakTrigger("achievement_goal", "delivered", ("X",)),
		context=("not at(X, Y)",),
		body=(
			AgentSpeakBodyStep("subgoal", "at", ("X", "Y")),
			AgentSpeakBodyStep("subgoal", "delivered", ("X",)),
		),
	)

	selection = _select_branches_with_clingo(
		(
			weaker_context_branch,
			stronger_context_branch,
			necessary_recursive_branch,
		),
	)

	assert selection.plans == (weaker_context_branch, necessary_recursive_branch)
	assert selection.report.backend == "clingo_asp_minimize"
	assert selection.report.raw_candidate_count == 3
	assert selection.report.selected_candidate_count == 2
	assert selection.report.obligation_count == 3


def test_clingo_selector_removes_alpha_equivalent_prepare_branch() -> None:
	first_prepare = AgentSpeakPlan(
		plan_name="at_prepare_at_robby_A",
		trigger=AgentSpeakTrigger("achievement_goal", "at", ("X", "Y")),
		context=("not at_robby(A)", "room(A)"),
		body=(
			AgentSpeakBodyStep("subgoal", "at_robby", ("A",)),
			AgentSpeakBodyStep("subgoal", "at", ("X", "Y")),
		),
	)
	second_prepare = AgentSpeakPlan(
		plan_name="at_prepare_at_robby_B",
		trigger=AgentSpeakTrigger("achievement_goal", "at", ("X", "Y")),
		context=("not at_robby(B)", "room(B)"),
		body=(
			AgentSpeakBodyStep("subgoal", "at_robby", ("B",)),
			AgentSpeakBodyStep("subgoal", "at", ("X", "Y")),
		),
	)

	selection = _select_branches_with_clingo((first_prepare, second_prepare))

	assert len(selection.plans) == 1
	assert selection.plans[0].plan_name in {
		"at_prepare_at_robby_A",
		"at_prepare_at_robby_B",
	}
	assert selection.report.raw_candidate_count == 2
	assert selection.report.selected_candidate_count == 1
	assert selection.report.obligation_count == 1


def test_clingo_selector_does_not_replace_safe_producer_with_extra_delete() -> None:
	dangerous_producer = AgentSpeakPlan(
		plan_name="done_via_short_destructive_action",
		trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
		context=("ready(X)",),
		body=(AgentSpeakBodyStep("action", "finish_destructively", ("X",)),),
		binding_certificate=(
			{"rule_kind": "producer_action_sequence"},
		),
	)
	safe_producer = AgentSpeakPlan(
		plan_name="done_via_two_safe_actions",
		trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
		context=("ready(X)",),
		body=(
			AgentSpeakBodyStep("action", "prepare_safely", ("X",)),
			AgentSpeakBodyStep("action", "finish_safely", ("X",)),
		),
		binding_certificate=(
			{"rule_kind": "producer_action_sequence"},
		),
	)
	actions = (
		_ParsedAction(
			name="finish_destructively",
			parameters=("?x",),
			parameter_types={"?x": "object"},
			preconditions=(),
			add_effects=(PDDLLiteralSchema("done", ("?x",)),),
			delete_effects=(PDDLLiteralSchema("protected", ("?x",), False),),
		),
		_ParsedAction(
			name="prepare_safely",
			parameters=("?x",),
			parameter_types={"?x": "object"},
			preconditions=(),
			add_effects=(PDDLLiteralSchema("staged", ("?x",)),),
			delete_effects=(),
		),
		_ParsedAction(
			name="finish_safely",
			parameters=("?x",),
			parameter_types={"?x": "object"},
			preconditions=(),
			add_effects=(PDDLLiteralSchema("done", ("?x",)),),
			delete_effects=(),
		),
	)

	selection = _select_branches_with_clingo(
		(dangerous_producer, safe_producer),
		actions=actions,
	)

	assert selection.plans == (safe_producer,)


def test_resource_release_contract_preserves_release_action_and_argument_roles() -> None:
	def release_plan(
		*,
		release_action: str,
		capacity_key_arguments: tuple[str, ...],
		occupancy_arguments: tuple[str, ...],
	) -> AgentSpeakPlan:
		return AgentSpeakPlan(
			plan_name=f"done_via_{release_action}",
			trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
			context=("free(R)",),
			body=(AgentSpeakBodyStep("action", release_action, ("R", "X")),),
			binding_certificate=(
				{
					"rule_kind": "producer_action_sequence",
					"resource_release_certificates": [
						{
							"certificate_kind": (
								"causal_resource_capacity_invariant_discharge"
							),
							"producer_action": "acquire",
							"release_action": release_action,
							"resource_debt_literal": "occupied(R, X)",
							"restored_literals": ["free(R)"],
							"resource_invariant_kind": (
								"keyed_single_capacity_occupancy_transition"
							),
							"capacity_key_arguments": list(capacity_key_arguments),
							"occupancy_arguments": list(occupancy_arguments),
							"target_preserved": True,
							"target_preservation_guards": ["R \\== X"],
							"sequence_alias_guards": ["R \\== X"],
						},
					],
				},
			),
		)

	release = release_plan(
		release_action="release",
		capacity_key_arguments=("R",),
		occupancy_arguments=("X",),
	)
	park = release_plan(
		release_action="park",
		capacity_key_arguments=("R",),
		occupancy_arguments=("X",),
	)
	swapped_roles = release_plan(
		release_action="release",
		capacity_key_arguments=("X",),
		occupancy_arguments=("R",),
	)

	assert _resource_release_contract(release) != _resource_release_contract(park)
	assert _resource_release_contract(release) != _resource_release_contract(swapped_roles)


def test_resource_release_search_discharge_can_cross_multiple_causal_modes(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "multi-step-resource.pddl"
	domain_file.write_text(
		"""
(define (domain multi-step-resource)
 (:requirements :strips :typing)
 (:types resource item - object)
 (:predicates
  (free ?r - resource)
  (held ?r - resource ?x - item)
  (staged ?r - resource ?x - item)
  (completed ?x - item))
 (:action produce
  :parameters (?r - resource ?x - item)
  :precondition (free ?r)
  :effect (and (completed ?x) (held ?r ?x) (not (free ?r))))
 (:action transfer
  :parameters (?r - resource ?x - item)
  :precondition (held ?r ?x)
  :effect (and (staged ?r ?x) (not (held ?r ?x))))
 (:action release
  :parameters (?r - resource ?x - item)
  :precondition (staged ?r ?x)
  :effect (and (free ?r) (not (staged ?r ?x))))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	domain = atomic_module_synthesis.PDDLParser.parse_domain(domain_file)
	actions = tuple(_ParsedAction.from_pddl(action) for action in domain.actions)

	sequences = atomic_module_synthesis._producer_action_sequences(
		actions=actions,
		type_tokens=domain.types,
		seed_predicates={"completed"},
		target_predicate="completed",
		module_predicates={"free", "held", "staged", "completed"},
		recursive_module_predicates=set(),
	)
	multi_step = next(
		sequence
		for sequence in sequences
		if tuple(call.action.name for call in sequence.body_actions)
		== ("produce", "transfer", "release")
	)
	certificate = multi_step.resource_release_certificates[0]

	assert certificate["release_actions"] == ["transfer", "release"]
	assert certificate["resource_debt_path"] == ["held(Y, X)", "staged(Y, X)"]
	assert certificate["restored_literals"] == ["free(Y)"]
	assert certificate["target_preserved"] is True


def test_clingo_selects_only_acyclic_cross_predicate_preparation_capabilities() -> None:
	def base_plan(predicate: str) -> AgentSpeakPlan:
		return AgentSpeakPlan(
			plan_name=f"{predicate}_already_true",
			trigger=AgentSpeakTrigger("achievement_goal", predicate, ("X",)),
			context=(f"{predicate}(X)",),
			body=(),
			binding_certificate=(
				{
					"rule_kind": "already_true",
				},
			),
		)

	def prepare_plan(caller: str, callee: str) -> AgentSpeakPlan:
		return AgentSpeakPlan(
			plan_name=f"{caller}_prepare_{callee}",
			trigger=AgentSpeakTrigger("achievement_goal", caller, ("X",)),
			context=(f"not {callee}(X)",),
			body=(
				AgentSpeakBodyStep("subgoal", callee, ("X",)),
				AgentSpeakBodyStep("subgoal", caller, ("X",)),
			),
			binding_certificate=(
				{
					"rule_kind": "prepare_public_precondition",
					"prepared_predicate": callee,
					"recursive_progress_certificate": {
						"certificate_kind": "well_founded_precondition_discharge",
						"ranking_feature_kind": "unsatisfied_precondition_boolean",
						"prepared_predicate": callee,
						"prepared_arguments": ["X"],
					},
				},
			),
		)

	plans = (
		base_plan("alpha"),
		base_plan("beta"),
		prepare_plan("alpha", "beta"),
		prepare_plan("beta", "alpha"),
	)

	selected = _select_branches_with_clingo(
		plans,
		schema_candidates=plans,
	)
	selected_prepare_plans = tuple(
		plan
		for plan in selected.plans
		if plan.binding_certificate[0].get("rule_kind")
		== "prepare_public_precondition"
	)

	assert len(selected_prepare_plans) == 1
	progress = selected_prepare_plans[0].binding_certificate[0][
		"recursive_progress_certificate"
	]
	assert progress["certificate_kind"] == "well_founded_precondition_discharge"
	assert progress["caller_dependency_rank"] > progress["callee_dependency_rank"]
	assert selected.report.preparation_dependency_edge_count == 1
	assert selected.report.preparation_dependency_max_rank == 1


def test_anchored_ranking_allows_only_provably_away_relation_adds(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "renamed-anchored-ranking.pddl"
	domain_file.write_text(
		"""
(define (domain renamed-anchored-ranking)
 (:requirements :strips :negative-preconditions)
 (:predicates (linked ?item ?anchor) (open ?item))
 (:action detach
  :parameters (?item ?anchor)
  :precondition (linked ?item ?anchor)
  :effect (and (open ?anchor) (not (linked ?item ?anchor))))
 (:action attach
  :parameters (?item ?anchor)
  :precondition (open ?anchor)
  :effect (linked ?item ?anchor))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	domain = atomic_module_synthesis.PDDLParser.parse_domain(domain_file)
	actions = tuple(_ParsedAction.from_pddl(action) for action in domain.actions)
	progress = {
		"recursive_progress_certificate": {
			"certificate_kind": "well_founded_relational_count_decrease",
			"ranking_feature_kind": "anchored_acyclic_relation_cone_count",
			"relation_predicate": "linked",
			"relation_arguments": ["Y", "X"],
			"strictly_decreasing_actions": ["detach"],
			"non_increasing_actions": ["attach"],
			"anchor_arguments": ["X"],
		},
	}
	recursive = AgentSpeakPlan(
		"open_prepare_open",
		AgentSpeakTrigger("achievement_goal", "open", ("X",)),
		("linked(Y, X)", "not open(Y)"),
		(
			AgentSpeakBodyStep("subgoal", "open", ("Y",)),
			AgentSpeakBodyStep("subgoal", "open", ("X",)),
		),
		binding_certificate=(progress,),
	)
	safe_relocation = AgentSpeakPlan(
		"open_via_relocate_away",
		AgentSpeakTrigger("achievement_goal", "open", ("X",)),
		("linked(Y, X)", "Z \\== X", "open(Z)"),
		(
			AgentSpeakBodyStep("action", "detach", ("Y", "X")),
			AgentSpeakBodyStep("action", "attach", ("Y", "Z")),
		),
	)
	unsafe_readdition = AgentSpeakPlan(
		"open_via_readd_to_anchor",
		AgentSpeakTrigger("achievement_goal", "open", ("X",)),
		("linked(Y, X)", "open(X)"),
		(
			AgentSpeakBodyStep("action", "detach", ("Y", "X")),
			AgentSpeakBodyStep("action", "attach", ("Y", "X")),
		),
	)

	pairs = set(
		atomic_module_synthesis._recursive_rank_incompatibility_pairs(
			(recursive, safe_relocation, unsafe_readdition),
			actions=actions,
		),
	)

	assert (0, 1) not in pairs
	assert (0, 2) in pairs


def test_certified_resource_release_macro_precedes_shorter_resource_debt_branch() -> None:
	def producer(name: str, actions: tuple[str, ...], *, releases: bool) -> AgentSpeakPlan:
		return AgentSpeakPlan(
			name,
			AgentSpeakTrigger("achievement_goal", "completed", ("X",)),
			("ready(X)",),
			tuple(AgentSpeakBodyStep("action", action, ("X",)) for action in actions),
			binding_certificate=(
				{
					"rule_kind": "producer_action_sequence",
					"resource_release_certificates": (
						[
							{
								"certificate_kind": (
									"causal_resource_capacity_invariant_discharge"
								),
							}
						]
						if releases
						else []
					),
				},
			),
		)

	short_debt = producer("completed_via_acquire", ("acquire",), releases=False)
	long_release = producer(
		"completed_via_acquire_then_release",
		("acquire", "release"),
		releases=True,
	)
	release_preparation = AgentSpeakPlan(
		"completed_prepare_ready_for_release",
		AgentSpeakTrigger("achievement_goal", "completed", ("X",)),
		("not ready(X)",),
		(
			AgentSpeakBodyStep("subgoal", "ready", ("X",)),
			AgentSpeakBodyStep("subgoal", "completed", ("X",)),
		),
		binding_certificate=(
			{
				"rule_kind": "prepare_public_precondition",
				"prepared_predicate": "ready",
				"resource_release_certificates": [
					{
						"certificate_kind": (
							"causal_resource_capacity_invariant_discharge"
						),
						"target_preserved": True,
					},
				],
			},
		),
	)

	ordered = sorted(
		(short_debt, release_preparation, long_release),
		key=lambda plan: atomic_module_synthesis._runtime_plan_priority(plan),
	)

	assert ordered == [long_release, release_preparation, short_debt]


def test_effect_refinement_rejects_different_resource_release_contracts() -> None:
	def producer_plan(
		*,
		name: str,
		release_action: str,
		context: tuple[str, ...],
		occupancy_arguments: tuple[str, ...] = ("X",),
	):
		return AgentSpeakPlan(
			plan_name=name,
			trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
			context=context,
			body=(AgentSpeakBodyStep("action", "finish", ("X",)),),
			binding_certificate=(
				{
					"rule_kind": "producer_action_sequence",
					"resource_release_certificates": [
						{
							"certificate_kind": (
								"causal_resource_capacity_invariant_discharge"
							),
							"producer_action": "acquire",
							"release_action": release_action,
							"resource_debt_literal": "occupied(R, X)",
							"restored_literals": ["free(R)"],
							"resource_invariant_kind": (
								"keyed_single_capacity_occupancy_transition"
							),
							"capacity_key_arguments": ["R"],
							"occupancy_arguments": list(occupancy_arguments),
							"target_preserved": True,
							"target_preservation_guards": [],
							"sequence_alias_guards": [],
						},
					],
				},
			),
		)

	candidate = producer_plan(
		name="candidate_release",
		release_action="release",
		context=("ready(X)",),
	)
	obligation = producer_plan(
		name="obligation_park",
		release_action="park",
		context=("ready(X)", "safe(X)"),
		occupancy_arguments=("R",),
	)
	actions_by_name = {
		"finish": _ParsedAction(
			name="finish",
			parameters=("?x",),
			parameter_types={"?x": "object"},
			preconditions=(PDDLLiteralSchema("ready", ("?x",)),),
			add_effects=(PDDLLiteralSchema("done", ("?x",)),),
			delete_effects=(),
		),
	}

	assert not _candidate_achieves_schema_obligation(
		candidate,
		obligation,
		actions_by_name=actions_by_name,
	)
	assert not _candidate_branch_covers_evidence(candidate, obligation)


def test_blocks_atomic_minimal_literal_modules_are_compact_recursive_and_lifted() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=BLOCKS_DOMAIN,
		seed_predicates=("on",),
		source_backend="moose_schema_minimal_modules",
		source_name="blocks-smoke",
	)
	asl = render_plan_library_asl(library)

	assert {plan.trigger.symbol for plan in library.plans} == {
		"clear",
		"handempty",
		"holding",
		"on",
		"ontable",
	}
	assert not any(
		bool(
			dict(plan.binding_certificate[0].get("context_projection_certificate") or {}).get(
				"dynamic_sibling_projection",
			),
		)
		for plan in library.plans
	)
	assert library.metadata["generation_mode"] == "atomic_minimal_literal_module_library"
	assert library.metadata["library_quality"]["compact_recursive_module_ready"] is True
	assert library.metadata["atomic_module_synthesis"]["module_predicates"] == [
		"clear",
		"handempty",
		"holding",
		"on",
		"ontable",
	]
	selector_report = library.metadata["atomic_module_synthesis"]
	assert len(library.plans) == selector_report["plan_count"]
	assert len(library.plans) <= selector_report["raw_candidate_count"]
	assert selector_report["selector_backend"] == "clingo_asp_minimize"
	assert selector_report["schema_composition_action_bound"] is None
	assert selector_report["schema_composition_grammar"] == [
		"direct producer",
		"finite alpha-normalized acyclic schema regression over producible preconditions",
		"optional acyclic causal resource-mode discharge after any producer sequence",
	]
	assert selector_report["selector_objective"] == [
		"maximize well-founded relational recursive capabilities",
		"maximize compatible well-founded recursive capabilities",
		"minimize selected branch count",
		"then minimize selected context literal count",
		"then minimize selected body step count",
	]
	assert selector_report["branch_certification_rules"] == [
		(
			"static context literals must be range-restricted by head variables or "
			"previous positive dynamic literals"
		),
		"negative context literals must be range-restricted and cannot bind new variables",
		(
			"extra-variable prepared preconditions require a positive context "
			"closure that binds every non-head variable before the negative guard"
		),
		(
			"acyclic preparation dependencies through a schema-inferred functional "
			"fluent may project unrelated dynamic sibling contexts only when every "
			"projected sibling has one producer schema, all "
			"of its static producer preconditions remain as feasibility witnesses, "
			"nested variables are alpha-renamed, and target completion is rechecked"
		),
		(
			"cyclic or producer-ambiguous preparation dependencies retain the full "
			"connected positive context"
		),
		(
			"same-predicate recursive prepare branches require a non-negative "
			"relational-count ranking feature that strictly decreases and is never increased"
		),
		(
			"cross-predicate prepare branches are optional Clingo capabilities; "
			"their selected dependency graph must be acyclic, and each branch "
			"records a strictly decreasing caller/callee dependency rank plus a "
			"successful precondition-discharge recheck"
		),
		(
			"anchored relation-cone rankings may relocate an obstruction only when "
			"schema guards prove the new relation value differs from the protected "
			"anchor; Clingo rejects the capability if any selected reachable module "
			"can increase that relation without the same certificate"
		),
		(
			"resource-release cleanup branches require a schema certificate "
			"that deletes a producer-created resource debt, restores a literal "
			"deleted by the producer, preserves the protected target, and records "
			"all exact alias guards needed by later action preconditions"
		),
	]
	assert selector_report["raw_candidate_count"] >= len(library.plans)
	assert 0 < selector_report["selector_obligation_count"] <= (
		selector_report["raw_candidate_count"]
	)
	assert len(selector_report["selected_branch_ids"]) == len(library.plans)
	role_by_predicate = {
		record["predicate"]: record
		for record in library.metadata["atomic_module_synthesis"]["predicate_roles"]
	}
	assert role_by_predicate["holding"]["role"] == "producible_fluent"
	assert role_by_predicate["holding"]["emitted_module"] is True
	assert role_by_predicate["handempty"]["role"] == "producible_fluent"
	assert role_by_predicate["handempty"]["emitted_module"] is True
	assert role_by_predicate["ontable"]["role"] == "producible_fluent"
	assert role_by_predicate["ontable"]["emitted_module"] is True
	assert all(
		record["coverage_status"] == "ok"
		for record in library.metadata["atomic_module_synthesis"]["predicate_roles"]
	)

	assert "+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not clear(X)" in asl
	assert "\t!clear(X);" in asl
	assert "\t!on(X, Y)." in asl
	assert "+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not clear(Y)" in asl
	assert "\t!clear(Y);" in asl
	assert "+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not holding(X)" in asl
	assert "\t!holding(X);" in asl
	assert "pick_up(X);\n\tunstack" not in asl
	assert library.metadata["pddl_support"]["is_compilable"] is True
	assert (
		"obj_tp(X, block) & obj_tp(Y, block) & X \\== Y & clear(X) & clear(Y) "
		"& ontable(X) & handempty"
	) in asl
	assert (
		"obj_tp(X, block) & obj_tp(Y, block) & X \\== Y & clear(X) & clear(Y) "
		"& handempty & on(X, Z) & obj_tp(Z, block) & Y \\== Z"
	) in asl
	assert "\tunstack(X, Z);" in asl
	assert "\tstack(X, Y)." in asl
	assert "obj_tp(X, block) & handempty & on(Y, X) & obj_tp(Y, block) & clear(Y)" in asl
	assert "\tunstack(Y, X);" in asl
	assert "\tput_down(Y)." in asl
	assert "obj_tp(X, block) & on(Y, X) & obj_tp(Y, block) & not clear(Y)" in asl
	assert "+!holding(X) : holding(X)" in asl
	assert "pick_up(X)." in asl
	assert "unstack(X, Y)." in asl
	assert "+!handempty : handempty" in asl
	assert "put_down(X)." in asl
	assert "+!ontable(X) : ontable(X)" in asl
	assert "+!ontable(X) : obj_tp(X, block) & not holding(X)" in asl

	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl
	assert "teg_state" not in asl
	assert "type_" not in asl
	assert "block0" not in asl
	assert "block1" not in asl
	assert "!on(Y, X)" not in asl
	clear_recursive_plans = [
		plan
		for plan in library.plans
		if plan.trigger.symbol == "clear"
		and any(
			step.kind == "subgoal"
			and step.symbol == "clear"
			and step.arguments != plan.trigger.arguments
			for step in plan.body
		)
	]
	assert len(clear_recursive_plans) == 1
	clear_certificate = clear_recursive_plans[0].binding_certificate[0][
		"recursive_progress_certificate"
	]
	assert clear_certificate == {
		"certificate_kind": "well_founded_relational_count_decrease",
		"ranking_feature_kind": "global_dynamic_atom_count",
		"relation_predicate": "on",
		"relation_arguments": ["Y", "X"],
		"strictly_decreasing_actions": ["unstack"],
		"non_increasing_actions": ["put-down"],
		"lower_bound": 0,
	}


def test_recursive_progress_rejects_delete_add_obstruction_exchange(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
(define (domain exchange)
 (:requirements :strips)
 (:predicates (ready ?x) (link ?x ?y))
 (:action exchange-link
  :parameters (?x ?y)
  :precondition (and (link ?y ?x) (ready ?y))
  :effect (and (ready ?x) (link ?x ?y)
   (not (link ?y ?x)) (not (ready ?y)))
 )
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)

	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=("ready",),
		source_backend="test",
		source_name="exchange",
	)

	assert not any(
		plan.trigger.symbol == "ready"
		and any(step.kind == "subgoal" and step.symbol == "ready" for step in plan.body)
		for plan in library.plans
	)


def test_resource_release_rejects_symmetric_modes_without_capacity_key(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
(define (domain resource-cycle)
 (:requirements :strips)
 (:predicates (available ?r ?x) (debt ?r ?x) (done ?x))
 (:action acquire
  :parameters (?r ?x)
  :precondition (available ?r ?x)
  :effect (and (done ?x) (debt ?r ?x) (not (available ?r ?x)))
 )
 (:action release
  :parameters (?r ?x)
  :precondition (debt ?r ?x)
  :effect (and (available ?r ?x) (not (debt ?r ?x)))
 )
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)

	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=("done",),
		source_backend="test",
		source_name="resource-cycle",
	)
	assert any(
		plan.trigger.symbol == "done"
		and tuple(step.symbol for step in plan.body) == ("acquire",)
		for plan in library.plans
	)
	assert not any(
		plan.trigger.symbol == "done"
		and tuple(step.symbol for step in plan.body) == ("acquire", "release")
		for plan in library.plans
	)


def test_certified_cleanup_does_not_remove_original_producer_candidate(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
(define (domain renamed-resource)
 (:requirements :strips)
 (:predicates
  (idle ?r)
  (engaged ?r ?x)
  (linked ?r ?x)
  (ready ?x)
  (made ?x)
 )
 (:action produce
  :parameters (?r ?x)
  :precondition (and (linked ?r ?x) (idle ?r) (ready ?x))
  :effect (and (made ?x) (engaged ?r ?x) (not (idle ?r)))
 )
 (:action reset
  :parameters (?r ?x)
  :precondition (engaged ?r ?x)
  :effect (and (idle ?r) (not (engaged ?r ?x)))
 )
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)

	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=("made",),
		source_backend="test",
		source_name="renamed-resource",
	)
	action_sequences = {
		tuple(step.symbol for step in plan.body)
		for plan in library.plans
		if plan.trigger.symbol == "made"
		and all(step.kind == "action" for step in plan.body)
	}

	assert ("produce",) in action_sequences
	assert ("produce", "reset") in action_sequences


def test_support_composition_establishes_persistent_precondition_with_alias_guard(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
(define (domain renamed-persistent-support)
 (:requirements :strips)
 (:predicates
  (ready ?x)
  (free ?r)
  (held ?r ?x)
  (made ?x)
 )
 (:action acquire
  :parameters (?r ?x)
  :precondition (and (ready ?x) (free ?r))
  :effect (and (held ?r ?x) (not (free ?r)))
 )
 (:action finish
  :parameters (?r ?x ?spare)
  :precondition (and (held ?r ?x) (free ?spare))
  :effect (made ?x)
 )
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)

	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=("made",),
		source_backend="test",
		source_name="renamed-persistent-support",
	)
	plan = next(
		item
		for item in library.plans
		if item.trigger.symbol == "made"
		and tuple(step.symbol for step in item.body) == ("acquire", "finish")
	)
	acquire_step, finish_step = plan.body
	resource = acquire_step.arguments[0]
	spare = finish_step.arguments[2]

	assert finish_step.arguments[:2] == acquire_step.arguments
	assert any(
		guard in plan.context
		for guard in (f"{resource} \\== {spare}", f"{spare} \\== {resource}")
	)


def test_atomic_module_synthesis_rejects_unsupported_pddl_before_compilation(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "conditional.pddl"
	domain_file.write_text(
		"""
		(define (domain conditional)
		 (:requirements :strips :conditional-effects)
		 (:predicates (ready ?x) (done ?x))
		 (:action finish
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (when (ready ?x) (done ?x))
		 )
		)
		""",
		encoding="utf-8",
	)

	with pytest.raises(ValueError, match="Unsupported PDDL for lifted ASL synthesis"):
		synthesize_atomic_minimal_literal_module_library(
			domain_file=domain_file,
			seed_predicates=("done",),
			source_backend="test",
			source_name="conditional",
		)


def test_ferry_bridge_sequence_keeps_negative_precondition_and_movement_module() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "ferry" / "domain.pddl",
		seed_predicates=("at",),
		source_backend="moose_schema_minimal_modules",
		source_name="ferry-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "+!at(X, Y)" in asl
	assert "board(X, Z);\n\tsail(Z, Y);\n\tdebark(X, Y)." in asl
	assert "not at_ferry(Y)" in asl
	assert "+!at_ferry(X)" in asl
	assert "sail(Y, X)." in asl


def test_numeric_resource_preconditions_compile_to_context_guards(tmp_path: Path) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
(define (domain numeric-transport)
  (:requirements :strips :typing :numeric-fluents)
  (:types vehicle package location)
  (:predicates
    (at ?x ?l - location)
    (in ?p - package ?v - vehicle)
  )
  (:functions
    (capacity ?v - vehicle)
  )
  (:action pick-up
    :parameters (?v - vehicle ?p - package ?l - location)
    :precondition (and (at ?v ?l) (at ?p ?l) (>= (capacity ?v) 1))
    :effect (and
      (not (at ?p ?l))
      (in ?p ?v)
      (decrease (capacity ?v) 1)
    )
  )
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)

	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=("in",),
		source_backend="moose_schema_minimal_modules",
		source_name="numeric-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "capacity(Y, N)" in asl
	assert "N >= 1" in asl
	assert "\tpick_up(Y, X, Z)." in asl
	assert "+!>=" not in asl
	assert ">=(" not in asl
	assert "decrease" not in asl


def test_static_predicates_are_context_only_not_atomic_goal_modules() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "logistics" / "domain.pddl",
		seed_predicates=("at",),
		source_backend="moose_schema_minimal_modules",
		source_name="logistics-smoke",
	)
	asl = render_plan_library_asl(library)
	role_by_predicate = {
		record["predicate"]: record
		for record in library.metadata["atomic_module_synthesis"]["predicate_roles"]
	}

	assert role_by_predicate["in-city"]["role"] == "static_context"
	assert role_by_predicate["in-city"]["emitted_module"] is False
	assert "+!in_city" not in asl
	assert role_by_predicate["in"]["role"] == "producible_fluent"
	assert role_by_predicate["in"]["emitted_module"] is True
	assert "+!in(X, Y)" in asl


def test_depots_drop_is_on_producer_when_extra_variables_are_precondition_bound() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "depots" / "domain.pddl",
		seed_predicates=("on",),
		source_backend="moose_schema_minimal_modules",
		source_name="depots-smoke",
	)
	asl = render_plan_library_asl(library)

	drop_plans = [
		plan
		for plan in library.plans
		if plan.trigger.symbol == "on"
		and plan.body == (AgentSpeakBodyStep("action", "drop", ("Z", "X", "Y", "A")),)
	]

	assert len(drop_plans) == 1
	plan = drop_plans[0]
	assert plan.trigger.arguments == ("X", "Y")
	assert "lifting(Z, X)" in plan.context
	assert "at(Y, A)" in plan.context
	assert "at(Z, A)" in plan.context
	assert "clear(Y)" in plan.context
	assert "\tdrop(Z, X, Y, A)." in asl
	assert "type_" not in asl


def test_depots_lifts_range_safe_extra_variable_precondition_to_subgoal() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "depots" / "domain.pddl",
		seed_predicates=("on",),
		source_backend="moose_schema_minimal_modules",
		source_name="depots-smoke",
	)
	asl = render_plan_library_asl(library)

	prepare_plans = [
		plan
		for plan in library.plans
		if plan.plan_name == "on_prepare_lifting_Z_X"
	]

	assert len(prepare_plans) == 1
	plan = prepare_plans[0]
	assert plan.trigger.symbol == "on"
	assert plan.trigger.arguments == ("X", "Y")
	assert "not lifting(Z, X)" in plan.context
	assert "at(Z, A)" in plan.context
	assert "hoist(Z)" in plan.context
	assert "at(Y, A)" in plan.context
	assert "place(A)" in plan.context
	assert plan.binding_certificate[0]["context_projection_certificate"][
		"dynamic_sibling_projection"
	] is False
	assert plan.body == (
		AgentSpeakBodyStep("subgoal", "lifting", ("Z", "X")),
		AgentSpeakBodyStep("subgoal", "on", ("X", "Y")),
	)
	assert "+!on(X, Y)" in asl
	assert "\t!lifting(Z, X);\n\t!on(X, Y)." in asl
	assert "type_" not in asl


def test_prepare_context_projects_away_unrelated_producer_variables() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "rovers" / "domain.pddl",
		seed_predicates=("communicated_image_data",),
		source_backend="test",
		source_name="projected-preparation-context",
	)
	plan = next(
		item
		for item in library.plans
		if item.plan_name == "have_image_prepare_calibrated_B_X"
	)

	assert "on_board(B, X)" in plan.context
	assert "supports(B, Z)" in plan.context
	assert "not calibrated(B, X)" in plan.context
	assert not any(context.startswith("at(X, ") for context in plan.context)
	assert any(context.startswith("visible_from(Y, ") for context in plan.context)
	assert "calibration_target(B, A)" not in plan.context
	assert plan.body == (
		AgentSpeakBodyStep("subgoal", "calibrated", ("B", "X")),
		AgentSpeakBodyStep("subgoal", "have_image", ("X", "Y", "Z")),
	)
	assert plan.binding_certificate[0]["context_projection_certificate"][
		"dynamic_sibling_projection"
	] is True
	plan_names = [item.plan_name for item in library.plans]
	assert plan_names.index("have_image_prepare_calibrated_B_X") < plan_names.index(
		"have_image_prepare_at_X_A"
	)
	assert plan_names.index(
		"communicated_image_data_prepare_have_image_Z_X_Y"
	) < plan_names.index("communicated_image_data_prepare_at_Z_B")
	communication_repair = next(
		item
		for item in library.plans
		if item.plan_name == "communicated_image_data_prepare_have_image_Z_X_Y"
	)
	assert "equipped_for_imaging(Z)" in communication_repair.context
	assert any(
		context.startswith("on_board(") and context.endswith(", Z)")
		for context in communication_repair.context
	)
	assert any(
		context.startswith("supports(") and context.endswith(", Y)")
		for context in communication_repair.context
	)


def test_prepare_projection_is_invariant_to_domain_vocabulary(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain staged-fabrication)
		 (:requirements :strips :typing)
		 (:types worker tool item site)
		 (:predicates
		  (located ?w - worker ?s - site)
		  (energized ?t - tool ?w - worker)
		  (fabricated ?w - worker ?i - item)
		  (mounted ?t - tool ?w - worker)
		  (charger ?t - tool ?s - site)
		  (compatible ?t - tool ?i - item)
		  (worksite ?i - item ?s - site)
		  (linked ?from - site ?to - site)
		 )
		 (:action travel
		  :parameters (?w - worker ?from - site ?to - site)
		  :precondition (and (located ?w ?from) (linked ?from ?to))
		  :effect (and (located ?w ?to) (not (located ?w ?from)))
		 )
		 (:action energize
		  :parameters (?t - tool ?w - worker ?s - site)
		  :precondition (and (mounted ?t ?w) (charger ?t ?s) (located ?w ?s))
		  :effect (energized ?t ?w)
		 )
		 (:action fabricate
		  :parameters (?w - worker ?i - item ?t - tool ?s - site)
		  :precondition
		   (and (located ?w ?s) (worksite ?i ?s) (energized ?t ?w)
		        (mounted ?t ?w) (compatible ?t ?i))
		  :effect (and (fabricated ?w ?i) (not (energized ?t ?w)))
		 )
		)
		""",
		encoding="utf-8",
	)

	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=("fabricated",),
		source_backend="test",
		source_name="renamed-staged-producer",
	)
	plan = next(
		item
		for item in library.plans
		if item.trigger.symbol == "fabricated"
		and item.binding_certificate[0].get("prepared_predicate") == "energized"
	)

	assert "not energized(Z, X)" in plan.context
	assert "mounted(Z, X)" in plan.context
	assert any(context.startswith("charger(Z, ") for context in plan.context)
	assert not any(context.startswith("located(X, ") for context in plan.context)
	assert plan.binding_certificate[0]["context_projection_certificate"][
		"dynamic_sibling_projection"
	] is True
	assert plan.body == (
		AgentSpeakBodyStep("subgoal", "energized", ("Z", "X")),
		AgentSpeakBodyStep("subgoal", "fabricated", ("X", "Y")),
	)


def test_depots_clear_can_release_hoist_without_deleting_protected_clear() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "depots" / "domain.pddl",
		seed_predicates=("on",),
		source_backend="moose_schema_minimal_modules",
		source_name="depots-smoke",
	)

	release_plans = [
		plan
		for plan in library.plans
		if plan.trigger.symbol == "clear"
		and tuple(step.symbol for step in plan.body) == ("lift", "drop")
	]

	assert len(release_plans) == 1
	plan = release_plans[0]
	lift_step, drop_step = plan.body
	assert lift_step.arguments[2] == "X"
	assert drop_step.arguments[:2] == lift_step.arguments[:2]
	assert drop_step.arguments[3] == lift_step.arguments[3]
	parking_surface = drop_step.arguments[2]
	lifted_object = lift_step.arguments[1]
	assert parking_surface != "X"
	assert parking_surface != lifted_object
	assert f"clear({parking_surface})" in plan.context
	assert f"at({parking_surface}, {drop_step.arguments[3]})" in plan.context
	assert any(
		context in plan.context
		for context in (
			f"{parking_surface} \\== X",
			f"X \\== {parking_surface}",
		)
	)
	assert any(
		context in plan.context
		for context in (
			f"{parking_surface} \\== {lifted_object}",
			f"{lifted_object} \\== {parking_surface}",
		)
	)
	resource_certificates = tuple(
		resource_certificate
		for certificate in plan.binding_certificate
		for resource_certificate in certificate.get("resource_release_certificates", ())
	)
	assert resource_certificates
	assert any(
		guard in resource_certificates[0]["sequence_alias_guards"]
		for guard in (
			f"{parking_surface} \\== {lifted_object}",
			f"{lifted_object} \\== {parking_surface}",
		)
	)


def test_depots_clear_keeps_every_schema_certified_resource_release() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "depots" / "domain.pddl",
		seed_predicates=("on",),
		source_backend="moose_schema_minimal_modules",
		source_name="depots-smoke",
	)

	release_action_sequences = {
		tuple(step.symbol for step in plan.body)
		for plan in library.plans
		if plan.trigger.symbol == "clear"
	}

	assert ("lift", "drop") in release_action_sequences
	assert ("lift", "load") in release_action_sequences
	lift_load_plan = next(
		plan
		for plan in library.plans
		if plan.trigger.symbol == "clear"
		and tuple(step.symbol for step in plan.body) == ("lift", "load")
	)
	lift_step, load_step = lift_load_plan.body
	truck = load_step.arguments[2]
	location = load_step.arguments[3]
	assert truck != lift_step.arguments[0]
	assert f"truck({truck})" in lift_load_plan.context
	assert f"at({truck}, {location})" in lift_load_plan.context


def test_depots_clear_uses_anchored_relation_cone_progress_certificate() -> None:
	domain = atomic_module_synthesis.PDDLParser.parse_domain(
		PROJECT_ROOT / "src" / "domains" / "depots" / "domain.pddl",
	)
	actions = tuple(
		atomic_module_synthesis._ParsedAction.from_pddl(action)
		for action in domain.actions
	)
	module_predicates = atomic_module_synthesis._module_predicate_closure(
		seeds=("on",),
		actions=actions,
		declared_predicates={predicate.name for predicate in domain.predicates},
	)
	candidates = atomic_module_synthesis._candidate_module_plans(
		domain=domain,
		actions=actions,
		seed_predicates=("on",),
		module_predicates=module_predicates,
		source_backend="test",
		source_name="anchored-cone-progress",
		policy_file=None,
	)
	plan = next(
		item
		for item in candidates
		if item.plan_name == "clear_prepare_clear_Z"
		and item.binding_certificate[0]["recursive_progress_certificate"][
			"ranking_feature_kind"
		]
		== "anchored_acyclic_relation_cone_count"
	)
	certificate = plan.binding_certificate[0]["recursive_progress_certificate"]

	assert certificate["certificate_kind"] == (
		"well_founded_relational_count_decrease"
	)
	assert certificate["ranking_feature_kind"] == (
		"anchored_acyclic_relation_cone_count"
	)
	assert certificate["relation_predicate"] == "on"
	assert certificate["relation_arguments"] == ["Z", "X"]
	assert certificate["anchor_arguments"] == ["X"]
	selected_library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "depots" / "domain.pddl",
		seed_predicates=("on",),
		source_backend="test",
		source_name="anchored-cone-progress",
	)
	assert any(
		item.plan_name == "clear_prepare_clear_Z"
		for item in selected_library.plans
	)
	assert (
		selected_library.metadata["atomic_module_synthesis"][
			"selected_recursive_capability_count"
		]
		> 0
	)


def test_depots_lifting_target_is_not_forced_to_release_the_lifted_crate() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "depots" / "domain.pddl",
		seed_predicates=("on",),
		source_backend="moose_schema_minimal_modules",
		source_name="depots-smoke",
	)

	lift_only_plans = [
		plan
		for plan in library.plans
		if plan.trigger.symbol == "lifting"
		and tuple(step.symbol for step in plan.body) == ("lift",)
	]
	released_lifting_target_plans = [
		plan
		for plan in library.plans
		if plan.trigger.symbol == "lifting"
		and tuple(step.symbol for step in plan.body) == ("lift", "drop")
	]

	assert lift_only_plans
	assert released_lifting_target_plans == []


def test_logistics_atomic_modules_compile_pddl_typing_to_obj_tp_guards() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "logistics" / "domain.pddl",
		seed_predicates=("at",),
		source_backend="moose_schema_minimal_modules",
		source_name="logistics-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "type_" not in asl
	assert "type_" not in str(library.metadata["atomic_module_synthesis"])
	assert "obj_tp(X, package)" in asl
	assert "obj_tp(Y, location)" in asl
	assert "obj_tp(Z, truck)" in asl
	assert "obj_tp(Z, airplane)" in asl
	assert "load_truck(X, Z, A);\n\tdrive_truck(Z, A, Y, B);\n\tunload_truck(X, Z, Y)." in asl
	assert (
		"drive_truck(Z, C, A, D);\n\tload_truck(X, Z, A);\n\t"
		"drive_truck(Z, A, Y, B);\n\tunload_truck(X, Z, Y)."
		in asl
	)
	assert (
		"load_airplane(X, Z, A);\n\tfly_airplane(Z, A, Y);\n\tunload_airplane(X, Z, Y)."
		in asl
	)
	assert (
		"fly_airplane(Z, B, A);\n\tload_airplane(X, Z, A);\n\t"
		"fly_airplane(Z, A, Y);\n\tunload_airplane(X, Z, Y)."
		in asl
	)
	assert "load_truck(X, X," not in asl
	assert "load_airplane(X, X," not in asl
	assert "load_airplane(X, Z, A);\n\tunload_airplane(X, Z, Y)." not in asl
	assert "load_truck(X, Z, A);\n\tunload_truck(X, Z, Y)." not in asl


def test_miconic_rejects_simultaneous_lift_location_direct_branch() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "miconic" / "domain.pddl",
		seed_predicates=("served",),
		source_backend="moose_schema_minimal_modules",
		source_name="miconic-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "board(Z, X);\n\tdepart(Y, X)." not in asl
	assert "board(Z, X);\n\tup(Z, Y);\n\tdepart(Y, X)." not in asl
	assert "board(Z, X);\n\tdown(Z, Y);\n\tdepart(Y, X)." not in asl
	assert "obj_tp(X, passenger)" in asl
	assert "obj_tp(Y, floor)" in asl
	assert len({plan.plan_name for plan in library.plans}) == len(library.plans)
	lift_repair_plans = [
		plan
		for plan in library.plans
		if plan.trigger.symbol == "served"
		and plan.body
		== (
			AgentSpeakBodyStep("subgoal", "lift-at", ("Y",)),
			AgentSpeakBodyStep("subgoal", "served", ("X",)),
		)
	]
	assert len(lift_repair_plans) == 1
	lift_repair_context = lift_repair_plans[0].context
	assert "boarded(X)" in lift_repair_context
	assert "destin(X, Y)" in lift_repair_context
	assert "obj_tp(X, passenger)" in lift_repair_context
	assert "obj_tp(Y, floor)" in lift_repair_context
	assert "not lift-at(Y)" in lift_repair_context
	assert "\t!lift_at(Y);\n\t!served(X)." in asl
	assert "+!served(X) : obj_tp(X, passenger) & not boarded(X)" in asl
	assert "\t!boarded(X);\n\t!served(X)." in asl


def test_gripper_rejects_unranked_same_predicate_navigation_recursion() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "gripper" / "domain.pddl",
		seed_predicates=("at",),
		source_backend="moose_schema_minimal_modules",
		source_name="gripper-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "+!at_robby(X) : at_robby(X)" in asl
	assert "+!at_robby(X) : room(X) & at_robby(Y) & X \\== Y & room(Y)" in asl
	assert "move(Y, X)." in asl
	assert "room(Y) & not at_robby(Y)" not in asl
	assert "!at_robby(Y);\n\t!at_robby(X)." not in asl
	at_plan_names = [
		plan.plan_name
		for plan in library.plans
		if plan.trigger.symbol == "at"
	]
	assert at_plan_names.index("at_via_pick_then_move_then_drop") < at_plan_names.index(
		"at_prepare_at-robby_Y",
	)
	assert at_plan_names.index("at_via_pick_then_move_then_drop") < at_plan_names.index(
		"at_prepare_at-robby_A",
	)


def test_miconic_static_above_does_not_bind_unbounded_navigation_context() -> None:
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=PROJECT_ROOT / "src" / "domains" / "miconic" / "domain.pddl",
		seed_predicates=("served",),
		source_backend="moose_schema_minimal_modules",
		source_name="miconic-smoke",
	)
	asl = render_plan_library_asl(library)

	assert "+!lift_at(X) : lift_at(X)" in asl
	assert (
		"+!lift_at(X) : obj_tp(X, floor) & above(Y, X) & obj_tp(Y, floor) "
		"& X \\== Y & lift_at(Y)"
	) in asl
	assert (
		"+!lift_at(X) : obj_tp(X, floor) & above(X, Y) & obj_tp(Y, floor) "
		"& X \\== Y & lift_at(Y)"
	) in asl
	assert "above(Y, X) & not lift_at(Y)" not in asl
	assert "above(X, Y) & not lift_at(Y)" not in asl
