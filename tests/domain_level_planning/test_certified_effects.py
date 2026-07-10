from __future__ import annotations

from pathlib import Path

import domain_level_planning.certified_effects as certified_effects
import pytest

from domain_level_planning.atomic_module_synthesis import (
	synthesize_atomic_minimal_literal_module_library,
)
from domain_level_planning.certified_effects import threat_safe_positive_literal_order
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
	original_summary = certified_effects._module_delete_summary
	original_unify = certified_effects._atoms_unify
	counts = {"summary": 0, "unify": 0}

	def counted_summary(*args, **kwargs):
		counts["summary"] += 1
		return original_summary(*args, **kwargs)

	def counted_unify(*args, **kwargs):
		counts["unify"] += 1
		return original_unify(*args, **kwargs)

	monkeypatch.setattr(certified_effects, "_module_delete_summary", counted_summary)
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
	assert certificate.ranking_assumptions == (
		"the certified binary relation is acyclic in every reachable execution state",
		"atomic modules are observed only at successful module completion",
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
