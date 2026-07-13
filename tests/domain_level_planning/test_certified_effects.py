from __future__ import annotations

from pathlib import Path

import domain_level_planning.certified_effects as certified_effects
import pytest

from domain_level_planning.atomic_module_synthesis import (
	synthesize_atomic_minimal_literal_module_library,
)
from domain_level_planning.certified_effects import threat_safe_positive_literal_order
from domain_level_planning.certified_effects import (
	preservation_safe_action_only_plan_selection,
)
from domain_level_planning.certified_effects import preservation_safe_plan_selection
from domain_level_planning.certified_effects import query_local_preservation_alias_plans
from domain_level_planning.certified_effects import negative_guard_establishment_alias_plans
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary
from utils.pddl_parser import PDDLParser


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_threat_certificate_rejects_sibling_type_false_unification(
	tmp_path: Path,
) -> None:
	domain_file = _write_typed_transport_fragment(tmp_path / "domain.pddl")
	library = _typed_transport_library()

	order, certificate = threat_safe_positive_literal_order(
		(
			("at", ("parcel1", "origin")),
			("delivered", ("parcel2",)),
		),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
		object_types={
			"parcel1": "package",
			"parcel2": "package",
			"origin": "location",
		},
	)

	assert order == (0, 1)
	assert certificate.threat_edges == ()


def test_threat_certificate_preserves_compatible_subtype_unification(
	tmp_path: Path,
) -> None:
	domain_file = _write_typed_transport_fragment(tmp_path / "domain.pddl")
	library = _typed_transport_library()

	order, certificate = threat_safe_positive_literal_order(
		(
			("at", ("vehicle1", "origin")),
			("delivered", ("parcel1",)),
		),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
		object_types={
			"vehicle1": "truck",
			"parcel1": "package",
			"origin": "location",
		},
	)

	assert order == (1, 0)
	assert certificate.threat_edges == ((1, 0),)


def test_threat_certificate_shares_lifted_variable_types_across_guard_literals(
	tmp_path: Path,
) -> None:
	domain_file = _write_typed_transport_fragment(tmp_path / "domain.pddl")

	order, certificate = threat_safe_positive_literal_order(
		(
			("at", ("X", "origin")),
			("delivered", ("X",)),
		),
		plan_library=_typed_transport_library(),
		domain=PDDLParser.parse_domain(domain_file),
		object_types={"origin": "location"},
	)

	assert order == (0, 1)
	assert certificate.threat_edges == ()


def test_threat_certificate_closes_parameter_changing_recursive_summary(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "recursive-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain recursive-fragment)
		 (:requirements :strips)
		 (:predicates (linked ?x ?y) (reached ?x) (protected ?x))
		 (:action arrive
		  :parameters (?target)
		  :precondition (protected ?target)
		  :effect (and (reached ?target) (not (protected ?target)))
		 )
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="recursive-fragment",
		plans=(
			AgentSpeakPlan(
				plan_name="reached_via_arrive",
				trigger=AgentSpeakTrigger("achievement_goal", "reached", ("X",)),
				context=("protected(X)",),
				body=(AgentSpeakBodyStep("action", "arrive", ("X",)),),
			),
			AgentSpeakPlan(
				plan_name="reached_prepare_predecessor",
				trigger=AgentSpeakTrigger("achievement_goal", "reached", ("X",)),
				context=("linked(Y, X)", "not reached(Y)"),
				body=(
					AgentSpeakBodyStep("subgoal", "reached", ("Y",)),
					AgentSpeakBodyStep("subgoal", "reached", ("X",)),
				),
			),
			AgentSpeakPlan(
				plan_name="protected_already_true",
				trigger=AgentSpeakTrigger("achievement_goal", "protected", ("X",)),
				context=("protected(X)",),
				body=(),
			),
		),
	)

	order, certificate = threat_safe_positive_literal_order(
		(("protected", ("predecessor",)), ("reached", ("target",))),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert order == (1, 0)
	assert certificate.threat_edges == ((1, 0),)


def test_threat_certificate_reuses_typed_summary_and_indexes_ground_anchors(
	tmp_path: Path,
	monkeypatch,
) -> None:
	domain_file = _write_typed_transport_fragment(tmp_path / "domain.pddl")
	original_summary = certified_effects._module_effect_summary
	original_unify = certified_effects._atoms_unify
	counts = {"summary": 0, "unify": 0}

	def counted_summary(*args, **kwargs):
		counts["summary"] += 1
		return original_summary(*args, **kwargs)

	def counted_unify(*args, **kwargs):
		counts["unify"] += 1
		return original_unify(*args, **kwargs)

	monkeypatch.setattr(certified_effects, "_module_effect_summary", counted_summary)
	monkeypatch.setattr(certified_effects, "_atoms_unify", counted_unify)
	objects = {f"parcel{index}": "package" for index in range(200)}
	objects["destination"] = "location"

	order, certificate = threat_safe_positive_literal_order(
		tuple(("at", (f"parcel{index}", "destination")) for index in range(200)),
		plan_library=_typed_transport_library(),
		domain=PDDLParser.parse_domain(domain_file),
		object_types=objects,
	)

	assert order == tuple(range(200))
	assert certificate.threat_edges == ()
	assert counts == {"summary": 1, "unify": 0}


def test_threat_certificate_uses_negative_branch_context_to_exclude_delete(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "conditional-delete-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain conditional-delete-fragment)
		 (:requirements :strips :negative-preconditions)
		 (:predicates (protected ?x) (done ?x))
		 (:action finish-when-unprotected
		  :parameters (?x)
		  :precondition (not (protected ?x))
		  :effect (and (done ?x) (not (protected ?x)))
		 )
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="conditional-delete-fragment",
		plans=(
			AgentSpeakPlan(
				plan_name="protected_already_true",
				trigger=AgentSpeakTrigger("achievement_goal", "protected", ("X",)),
				context=("protected(X)",),
				body=(),
			),
			AgentSpeakPlan(
				plan_name="done_via_finish_when_unprotected",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
				context=("not protected(X)",),
				body=(
					AgentSpeakBodyStep("action", "finish-when-unprotected", ("X",)),
				),
			),
		),
	)

	order, certificate = threat_safe_positive_literal_order(
		(("protected", ("item",)), ("done", ("item",))),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert order == (0, 1)
	assert certificate.threat_edges == ()
	assert certificate.conditional_effects_checked is True


@pytest.mark.parametrize(
	("goal_predicate", "ready_predicate", "safe_action", "unsafe_action"),
	(
		("completed", "ready", "finish-safely", "finish-by-reusing"),
		("sealed", "prepared", "close-without-touching", "close-by-reusing"),
	),
)
def test_preservation_safe_selection_is_symbol_invariant(
	tmp_path: Path,
	goal_predicate: str,
	ready_predicate: str,
	safe_action: str,
	unsafe_action: str,
) -> None:
	domain_file = tmp_path / f"{goal_predicate}-domain.pddl"
	domain_file.write_text(
		f"""
		(define (domain selection-fragment)
		 (:requirements :strips)
		 (:predicates ({goal_predicate} ?x) ({ready_predicate} ?x))
		 (:action {safe_action}
		  :parameters (?x)
		  :precondition ({ready_predicate} ?x)
		  :effect ({goal_predicate} ?x)
		 )
		 (:action {unsafe_action}
		  :parameters (?x ?other)
		  :precondition (and ({ready_predicate} ?x) ({goal_predicate} ?other))
		  :effect (and ({goal_predicate} ?x) (not ({goal_predicate} ?other)))
		 )
		 (:action preserve-without-achieving
		  :parameters (?x)
		  :precondition ({ready_predicate} ?x)
		  :effect ({ready_predicate} ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="selection-fragment",
		plans=(
			AgentSpeakPlan(
				f"{goal_predicate}_already_true",
				AgentSpeakTrigger("achievement_goal", goal_predicate, ("X",)),
				(f"{goal_predicate}(X)",),
				(),
			),
			AgentSpeakPlan(
				f"{goal_predicate}_safe",
				AgentSpeakTrigger("achievement_goal", goal_predicate, ("X",)),
				(f"{ready_predicate}(X)",),
				(AgentSpeakBodyStep("action", safe_action, ("X",)),),
			),
			AgentSpeakPlan(
				f"{goal_predicate}_unsafe",
				AgentSpeakTrigger("achievement_goal", goal_predicate, ("X",)),
				(f"{ready_predicate}(X)", f"{goal_predicate}(Y)"),
				(AgentSpeakBodyStep("action", unsafe_action, ("X", "Y")),),
			),
			AgentSpeakPlan(
				f"{goal_predicate}_non_achieving",
				AgentSpeakTrigger("achievement_goal", goal_predicate, ("X",)),
				(f"{ready_predicate}(X)",),
				(
					AgentSpeakBodyStep(
						"action",
						"preserve-without-achieving",
						("X",),
					),
				),
			),
		),
	)

	selection = preservation_safe_action_only_plan_selection(
		((goal_predicate, ("first",)), (goal_predicate, ("second",))),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert selection is not None
	assert selection.ordered_indexes == (0, 1)
	assert tuple(plan.plan_name for plan in selection.plans_by_predicate[goal_predicate]) == (
		f"{goal_predicate}_already_true",
		f"{goal_predicate}_safe",
	)
	assert selection.certificate.serialization_strategy == (
		"query_local_preservation_safe_action_only_branches"
	)


@pytest.mark.parametrize(
	("goal_predicate", "forbidden_predicate", "producer_action"),
	(
		("completed", "damaged", "finish-damaged"),
		("sealed", "contaminated", "close-contaminated"),
	),
)
def test_negative_guard_preservation_is_symbol_invariant(
	tmp_path: Path,
	goal_predicate: str,
	forbidden_predicate: str,
	producer_action: str,
) -> None:
	domain_file = tmp_path / f"{goal_predicate}-negative-domain.pddl"
	domain_file.write_text(
		f"""
		(define (domain renamed-negative-fragment)
		 (:requirements :strips)
		 (:predicates (ready ?x) ({goal_predicate} ?x) ({forbidden_predicate} ?x))
		 (:action {producer_action}
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (and ({goal_predicate} ?x) ({forbidden_predicate} ?x))
		 )
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="renamed-negative-fragment",
		plans=(
			AgentSpeakPlan(
				f"{goal_predicate}_unsafe",
				AgentSpeakTrigger("achievement_goal", goal_predicate, ("X",)),
				("ready(X)",),
				(AgentSpeakBodyStep("action", producer_action, ("X",)),),
			),
		),
	)

	with pytest.raises(ValueError, match="negative_guard_not_preserved"):
		threat_safe_positive_literal_order(
			((goal_predicate, ("item",)),),
			negative_literals=((forbidden_predicate, ("item",)),),
			plan_library=library,
			domain=PDDLParser.parse_domain(domain_file),
		)


@pytest.mark.parametrize(
	("goal_predicate", "forbidden_predicate", "producer_action"),
	(
		("holding", "available", "acquire"),
		("sealed", "open", "close"),
	),
)
def test_negative_guard_establishment_is_symbol_invariant(
	tmp_path: Path,
	goal_predicate: str,
	forbidden_predicate: str,
	producer_action: str,
) -> None:
	domain_file = tmp_path / f"{goal_predicate}-establishment-domain.pddl"
	domain_file.write_text(
		f"""
		(define (domain renamed-establishment-fragment)
		 (:requirements :strips)
		 (:predicates
		  (ready ?actor ?item)
		  ({goal_predicate} ?actor ?item)
		  ({forbidden_predicate} ?actor)
		 )
		 (:action {producer_action}
		  :parameters (?actor ?item)
		  :precondition (and (ready ?actor ?item) ({forbidden_predicate} ?actor))
		  :effect (and
		   ({goal_predicate} ?actor ?item)
		   (not ({forbidden_predicate} ?actor))
		  )
		 )
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="renamed-establishment-fragment",
		plans=(
			AgentSpeakPlan(
				f"{goal_predicate}_via_{producer_action}",
				AgentSpeakTrigger(
					"achievement_goal",
					goal_predicate,
					("Actor", "Item"),
				),
				(
					"ready(Actor, Item)",
					f"{forbidden_predicate}(Actor)",
				),
				(
					AgentSpeakBodyStep(
						"action",
						producer_action,
						("Actor", "Item"),
					),
				),
			),
		),
	)

	aliases, helpers, certificate = negative_guard_establishment_alias_plans(
		((goal_predicate, ("agent", "item")),),
		negative_literals=((forbidden_predicate, ("agent",)),),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
		helper_prefix="g_query_trans_1",
	)

	assert len(aliases) == 2
	assert aliases[0].trigger.symbol == helpers[0][0]
	assert aliases[0].trigger.arguments == ()
	assert aliases[0].context == (
		"ready(agent, item)",
		f"{forbidden_predicate}(agent)",
	)
	assert aliases[0].body == (
		AgentSpeakBodyStep("action", producer_action, ("agent", "item")),
	)
	assert {
		plan.binding_certificate[-1]["certificate_kind"] for plan in aliases
	} == {
		"pddl_net_must_delete_with_positive_preservation",
		"pddl_single_action_must_delete",
	}
	assert helpers[0][1] == ()
	assert certificate["negative_guard_establishment_checked"] is True
	assert certificate["negative_guard_establishable"] is True
	assert certificate["negative_guard_establishers"] == {
		f"{forbidden_predicate}(agent)": [plan.plan_name for plan in aliases],
	}


def test_negative_guard_uses_atomic_completion_net_effects(tmp_path: Path) -> None:
	domain_file = tmp_path / "restored-negative-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain restored-negative)
		 (:requirements :strips)
		 (:predicates (ready ?x) (processing ?x) (completed ?x) (exposed ?x))
		 (:action begin
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (and (processing ?x) (exposed ?x))
		 )
		 (:action finish
		  :parameters (?x)
		  :precondition (processing ?x)
		  :effect (and (completed ?x) (not (processing ?x)) (not (exposed ?x)))
		 )
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="restored-negative",
		plans=(
			AgentSpeakPlan(
				"completed_via_begin_finish",
				AgentSpeakTrigger("achievement_goal", "completed", ("X",)),
				("ready(X)",),
				(
					AgentSpeakBodyStep("action", "begin", ("X",)),
					AgentSpeakBodyStep("action", "finish", ("X",)),
				),
			),
		),
	)

	order, certificate = threat_safe_positive_literal_order(
		(("completed", ("item",)),),
		negative_literals=(("exposed", ("item",)),),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert order == (0,)
	assert certificate.negative_guard_preservation_checked is True
	assert certificate.negative_guard_preserved is True
	assert certificate.negative_guard_count == 1


def test_negative_guard_preservation_respects_disjoint_pddl_types(tmp_path: Path) -> None:
	domain_file = tmp_path / "typed-negative-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain typed-negative)
		 (:requirements :strips :typing)
		 (:types locatable location - object package truck - locatable)
		 (:predicates
		  (ready ?item - package)
		  (available ?vehicle - truck)
		  (delivered ?item - package)
		  (marked ?object - locatable)
		 )
		 (:action deliver
		  :parameters (?item - package ?vehicle - truck)
		  :precondition (and (ready ?item) (available ?vehicle))
		  :effect (and (delivered ?item) (marked ?vehicle))
		 )
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="typed-negative",
		plans=(
			AgentSpeakPlan(
				"delivered_via_truck",
				AgentSpeakTrigger("achievement_goal", "delivered", ("X",)),
				("ready(X)", "available(V)"),
				(AgentSpeakBodyStep("action", "deliver", ("X", "V")),),
			),
		),
	)

	order, certificate = threat_safe_positive_literal_order(
		(("delivered", ("parcel",)),),
		negative_literals=(("marked", ("parcel",)),),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
		object_types={"parcel": "package"},
	)

	assert order == (0,)
	assert certificate.negative_guard_preserved is True


def test_preservation_safe_selection_reuses_typed_goal_pair_shapes(
	tmp_path: Path,
	monkeypatch,
) -> None:
	domain_file = tmp_path / "selection-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain selection-fragment)
		 (:requirements :strips)
		 (:predicates (completed ?x) (ready ?x))
		 (:action finish-safely
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (completed ?x)
		 )
		 (:action finish-by-reusing
		  :parameters (?x ?other)
		  :precondition (and (ready ?x) (completed ?other))
		  :effect (and (completed ?x) (not (completed ?other)))
		 )
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="selection-fragment",
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
	original = certified_effects._conditional_delete_can_threaten
	call_count = 0

	def counted(*args, **kwargs):
		nonlocal call_count
		call_count += 1
		return original(*args, **kwargs)

	monkeypatch.setattr(certified_effects, "_conditional_delete_can_threaten", counted)

	selection = preservation_safe_action_only_plan_selection(
		tuple(("completed", (f"item{index}",)) for index in range(200)),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert selection is not None
	assert call_count <= 2


def test_threat_certificate_rejects_functionally_inconsistent_goal_block(
	tmp_path: Path,
) -> None:
	domain_file = _write_typed_transport_fragment(tmp_path / "domain.pddl")

	with pytest.raises(
		ValueError,
		match="functionally_inconsistent_conjunctive_transition",
	):
		threat_safe_positive_literal_order(
			(
				("at", ("parcel1", "origin")),
				("at", ("parcel1", "destination")),
			),
			plan_library=_typed_transport_library(),
			domain=PDDLParser.parse_domain(domain_file),
			object_types={
				"parcel1": "package",
				"origin": "location",
				"destination": "location",
			},
		)


def test_threat_certificate_uses_module_completion_net_effects(tmp_path: Path) -> None:
	domain_file = tmp_path / "restoring-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain restoring-fragment)
		 (:requirements :strips)
		 (:predicates (protected ?x) (held ?x) (done ?x))
		 (:action consume
		  :parameters (?x)
		  :precondition (protected ?x)
		  :effect (and (held ?x) (not (protected ?x)))
		 )
		 (:action restore
		  :parameters (?x)
		  :precondition (held ?x)
		  :effect (and (done ?x) (protected ?x) (not (held ?x)))
		 )
		)
		""",
		encoding="utf-8",
	)
	library = PlanLibrary(
		domain_name="restoring-fragment",
		plans=(
			AgentSpeakPlan(
				"protected_already_true",
				AgentSpeakTrigger("achievement_goal", "protected", ("X",)),
				("protected(X)",),
				(),
			),
			AgentSpeakPlan(
				"done_via_consume_restore",
				AgentSpeakTrigger("achievement_goal", "done", ("X",)),
				("protected(X)",),
				(
					AgentSpeakBodyStep("action", "consume", ("X",)),
					AgentSpeakBodyStep("action", "restore", ("X",)),
				),
			),
		),
	)

	order, certificate = threat_safe_positive_literal_order(
		(("protected", ("item",)), ("done", ("item",))),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert order == (0, 1)
	assert certificate.threat_edges == ()
	assert certificate.observation_boundary == "atomic_module_completion"


def test_threat_certificate_serializes_certified_acyclic_support_relation() -> None:
	domain_file = PROJECT_ROOT / "src" / "domains" / "blocksworld-tower" / "domain.pddl"
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=("on",),
		source_backend="test",
		source_name="support-forest-certificate",
	)

	order, certificate = threat_safe_positive_literal_order(
		(
			("on", ("top", "middle")),
			("on", ("middle", "bottom")),
		),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert order == (1, 0)
	assert certificate.serialization_strategy == (
		"assumption_bounded_support_depth_ranking"
	)
	assert certificate.ranking_relation == "on"
	assert certificate.ranking_relation_anchor_position == 1
	assert certificate.ranking_assumptions == (
		"the certified binary relation is acyclic in every reachable execution state",
		"atomic modules are observed only at successful module completion",
	)


def test_support_depth_certificate_is_invariant_under_vocabulary_renaming(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "renamed-support-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain renamed-support)
		 (:requirements :strips :negative-preconditions)
		 (:predicates (supports ?child ?parent) (free ?item))
		 (:action detach
		  :parameters (?child ?parent)
		  :precondition (and (supports ?child ?parent) (free ?child))
		  :effect (and (free ?parent) (not (supports ?child ?parent)))
		 )
		 (:action attach
		  :parameters (?child ?parent)
		  :precondition (and (free ?child) (free ?parent))
		  :effect (and (supports ?child ?parent) (not (free ?parent)))
		 )
		)
		""",
		encoding="utf-8",
	)
	recursive_certificate = {
		"recursive_progress_certificate": {
			"certificate_kind": "well_founded_relational_count_decrease",
			"ranking_feature_kind": "global_dynamic_atom_count",
			"relation_predicate": "supports",
			"relation_arguments": ["Y", "X"],
			"strictly_decreasing_actions": ["detach"],
			"non_increasing_actions": [],
		},
	}
	library = PlanLibrary(
		domain_name="renamed-support",
		plans=(
			AgentSpeakPlan(
				"free_already_true",
				AgentSpeakTrigger("achievement_goal", "free", ("X",)),
				("free(X)",),
				(),
			),
			AgentSpeakPlan(
				"free_via_detach",
				AgentSpeakTrigger("achievement_goal", "free", ("X",)),
				("supports(Y, X)", "free(Y)"),
				(AgentSpeakBodyStep("action", "detach", ("Y", "X")),),
			),
			AgentSpeakPlan(
				"free_prepare_free",
				AgentSpeakTrigger("achievement_goal", "free", ("X",)),
				("supports(Y, X)", "not free(Y)"),
				(
					AgentSpeakBodyStep("subgoal", "free", ("Y",)),
					AgentSpeakBodyStep("subgoal", "free", ("X",)),
				),
				binding_certificate=(recursive_certificate,),
			),
			AgentSpeakPlan(
				"supports_via_attach",
				AgentSpeakTrigger("achievement_goal", "supports", ("X", "Y")),
				("free(X)", "free(Y)"),
				(AgentSpeakBodyStep("action", "attach", ("X", "Y")),),
			),
			AgentSpeakPlan(
				"supports_prepare_free_child",
				AgentSpeakTrigger("achievement_goal", "supports", ("X", "Y")),
				("not free(X)",),
				(
					AgentSpeakBodyStep("subgoal", "free", ("X",)),
					AgentSpeakBodyStep("subgoal", "supports", ("X", "Y")),
				),
			),
			AgentSpeakPlan(
				"supports_prepare_free_parent",
				AgentSpeakTrigger("achievement_goal", "supports", ("X", "Y")),
				("not free(Y)",),
				(
					AgentSpeakBodyStep("subgoal", "free", ("Y",)),
					AgentSpeakBodyStep("subgoal", "supports", ("X", "Y")),
				),
			),
		),
	)

	order, certificate = threat_safe_positive_literal_order(
		(
			("supports", ("upper", "middle")),
			("supports", ("middle", "lower")),
		),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert order == (1, 0)
	assert certificate.serialization_strategy == (
		"assumption_bounded_support_depth_ranking"
	)
	assert certificate.ranking_relation == "supports"
	assert certificate.ranking_relation_anchor_position == 1


def test_preservation_selection_keeps_certified_recursive_repair_under_noisy_macros(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "recursive-support-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain recursive-support)
		 (:requirements :strips :negative-preconditions)
		 (:predicates (supports ?child ?parent) (free ?item) (held ?item) (ready ?item))
		 (:action detach
		  :parameters (?child ?parent)
		  :precondition (and (supports ?child ?parent) (free ?child))
		  :effect (and (held ?child) (free ?parent) (not (supports ?child ?parent)))
		 )
		 (:action attach
		  :parameters (?child ?parent)
		  :precondition (and (held ?child) (ready ?parent))
		  :effect (and (supports ?child ?parent) (free ?child) (not (held ?child)))
		 )
		 (:action make-ready
		  :parameters (?item)
		  :precondition (free ?item)
		  :effect (ready ?item)
		 )
		)
		""",
		encoding="utf-8",
	)
	recursive_certificate = {
		"recursive_progress_certificate": {
			"certificate_kind": "well_founded_relational_count_decrease",
			"ranking_feature_kind": "global_dynamic_atom_count",
			"relation_predicate": "supports",
			"relation_arguments": ["Y", "X"],
			"strictly_decreasing_actions": ["detach"],
			"non_increasing_actions": [],
		},
	}
	library = PlanLibrary(
		domain_name="recursive-support",
		plans=(
			AgentSpeakPlan(
				"free_already_true",
				AgentSpeakTrigger("achievement_goal", "free", ("X",)),
				("free(X)",),
				(),
			),
			AgentSpeakPlan(
				"free_via_detach",
				AgentSpeakTrigger("achievement_goal", "free", ("X",)),
				("supports(Y, X)", "free(Y)"),
				(AgentSpeakBodyStep("action", "detach", ("Y", "X")),),
			),
			AgentSpeakPlan(
				"free_prepare_free",
				AgentSpeakTrigger("achievement_goal", "free", ("X",)),
				("supports(Y, X)", "not free(Y)"),
				(
					AgentSpeakBodyStep("subgoal", "free", ("Y",)),
					AgentSpeakBodyStep("subgoal", "free", ("X",)),
				),
				binding_certificate=(recursive_certificate,),
			),
			AgentSpeakPlan(
				"ready_already_true",
				AgentSpeakTrigger("achievement_goal", "ready", ("X",)),
				("ready(X)",),
				(),
			),
			AgentSpeakPlan(
				"ready_via_make_ready",
				AgentSpeakTrigger("achievement_goal", "ready", ("X",)),
				("free(X)",),
				(AgentSpeakBodyStep("action", "make-ready", ("X",)),),
			),
			AgentSpeakPlan(
				"supports_already_true",
				AgentSpeakTrigger("achievement_goal", "supports", ("X", "Y")),
				("supports(X, Y)",),
				(),
			),
			AgentSpeakPlan(
				"supports_via_attach",
				AgentSpeakTrigger("achievement_goal", "supports", ("X", "Y")),
				("held(X)", "ready(Y)"),
				(AgentSpeakBodyStep("action", "attach", ("X", "Y")),),
			),
			AgentSpeakPlan(
				"supports_prepare_ready_parent",
				AgentSpeakTrigger("achievement_goal", "supports", ("X", "Y")),
				("not ready(Y)",),
				(
					AgentSpeakBodyStep("subgoal", "ready", ("Y",)),
					AgentSpeakBodyStep("subgoal", "supports", ("X", "Y")),
				),
				binding_certificate=({"rule_kind": "prepare_public_precondition"},),
			),
			# This evidence macro changes another support edge. It must not globally
			# invalidate a safe recursive branch portfolio for the query.
			AgentSpeakPlan(
				"supports_noisy_evidence_macro",
				AgentSpeakTrigger("achievement_goal", "supports", ("X", "Y")),
				("supports(Y, Z)", "free(Y)", "free(X)"),
				(
					AgentSpeakBodyStep("action", "detach", ("Y", "Z")),
					AgentSpeakBodyStep("action", "attach", ("X", "Y")),
				),
			),
		),
	)

	selection = preservation_safe_plan_selection(
		(
			("supports", ("upper", "middle")),
			("supports", ("middle", "lower")),
		),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert selection is not None
	assert selection.ordered_indexes == (1, 0)
	assert selection.certificate.serialization_strategy == (
		"query_local_support_ranked_recursive_closure"
	)
	selected_names = {
		plan.plan_name
		for plans in selection.plans_by_predicate.values()
		for plan in plans
	}
	assert "supports_prepare_ready_parent" in selected_names
	assert "supports_noisy_evidence_macro" not in selected_names

	aliases, helper_by_predicate = query_local_preservation_alias_plans(
		selection,
		helper_prefix="g_query_trans_1",
	)
	helper = helper_by_predicate["supports"]
	recursive_alias = next(
		plan for plan in aliases if plan.plan_name.endswith("supports_prepare_ready_parent")
	)
	assert recursive_alias.body[-1].symbol == helper


def test_preservation_certificate_reports_action_only_when_no_recursive_branch_selected() -> None:
	domain_file = PROJECT_ROOT / "src" / "domains" / "blocksworld-tower" / "domain.pddl"
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=("on",),
		source_backend="test",
		source_name="truthful-recursive-certificate",
	)

	selection = preservation_safe_plan_selection(
		(
			("on", ("top", "middle")),
			("on", ("middle", "bottom")),
		),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert selection is not None
	selected_plans = tuple(
		plan
		for plans in selection.plans_by_literal_index.values()
		for plan in plans
	)
	assert selected_plans
	if not any(any(step.kind == "subgoal" for step in plan.body) for plan in selected_plans):
		assert selection.certificate.serialization_strategy == (
			"query_local_preservation_safe_action_only_branches"
		)


def test_preservation_selection_is_occurrence_scoped_for_repeated_predicate_goals() -> None:
	domain_file = PROJECT_ROOT / "src" / "domains" / "blocksworld-tower" / "domain.pddl"
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=("on",),
		source_backend="test",
		source_name="occurrence-scoped-preservation",
	)

	selection = preservation_safe_plan_selection(
		(
			("on", ("upper", "middle")),
			("on", ("middle", "lower")),
		),
		plan_library=library,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert selection is not None
	assert selection.ordered_indexes == (1, 0)
	assert set(selection.plans_by_literal_index) == {0, 1}
	first_occurrence = selection.plans_by_literal_index[1]
	assert any(plan.plan_name == "on_prepare_clear_X" for plan in first_occurrence)

	aliases, helper_by_literal = query_local_preservation_alias_plans(
		selection,
		helper_prefix="g_query_trans_1",
	)
	assert helper_by_literal["on(middle, lower)"] != helper_by_literal["on(upper, middle)"]
	assert any(
		plan.trigger.symbol == helper_by_literal["on(middle, lower)"]
		and plan.plan_name.endswith("on_prepare_clear_X")
		for plan in aliases
	)


def _write_typed_transport_fragment(path: Path) -> Path:
	path.write_text(
		"""
		(define (domain typed-transport-fragment)
		 (:requirements :strips :typing)
		 (:types
		  locatable location - object
		  package truck - locatable
		 )
		 (:predicates
		  (at ?item - locatable ?place - location)
		  (delivered ?item - package)
		 )
		 (:action relocate-package
		  :parameters (?item - package ?from - location ?to - location)
		  :precondition (at ?item ?from)
		  :effect (and (at ?item ?to) (not (at ?item ?from)))
		 )
		 (:action deliver
		  :parameters
		   (?item - package ?vehicle - truck ?from - location)
		  :precondition (and (at ?item ?from) (at ?vehicle ?from))
		  :effect (and (delivered ?item) (not (at ?vehicle ?from)))
		 )
		)
		""",
		encoding="utf-8",
	)
	return path


def _typed_transport_library() -> PlanLibrary:
	return PlanLibrary(
		domain_name="typed-transport-fragment",
		plans=(
			AgentSpeakPlan(
				plan_name="at_via_relocate_package",
				trigger=AgentSpeakTrigger("achievement_goal", "at", ("X", "Y")),
				context=("at(X, A)",),
				body=(
					AgentSpeakBodyStep("action", "relocate-package", ("X", "A", "Y")),
				),
			),
			AgentSpeakPlan(
				plan_name="delivered_via_deliver",
				trigger=AgentSpeakTrigger("achievement_goal", "delivered", ("X",)),
				context=("at(X, A)", "at(Y, A)"),
				body=(
					AgentSpeakBodyStep("action", "deliver", ("X", "Y", "A")),
				),
			),
		),
	)
