from __future__ import annotations

from pathlib import Path

from domain_level_planning import (
	build_goal_conditioned_library_from_pddl,
	goal_facts_from_problem,
)
from domain_level_planning.schema_synthesis import _goal_ordering_rules_from_evidence
from domain_level_planning.schema_synthesis import _validate_selected_rules_against_transition_progress
from domain_level_planning.models import LiftedCall, LiftedPlanRule
from domain_level_planning.transition_system import TrainingTransitionEvidence
from domain_level_planning.transition_system import GoalProgressEvidence
from plan_library.rendering import render_plan_library_asl
from utils.pddl_parser import PDDLFact


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "domain.pddl"
BLOCKS_P01 = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "problems" / "p01.pddl"


def test_schema_synthesizer_builds_lifted_modules_from_any_pddl_domain() -> None:
	domain_file, problem_file = _write_logistics_domain_and_problem()

	plan_library = build_goal_conditioned_library_from_pddl(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
	)
	asl = render_plan_library_asl(plan_library)

	assert plan_library.domain_name == "logistics-mini"
	assert plan_library.initial_beliefs == ()
	assert plan_library.metadata["generation_mode"] == "unified_goal_conditioned_modular_synthesis"
	assert "+!g : goal_at(P, L) & not at(P, L) <-" in asl
	assert "\t!at(P, L);" in asl
	assert "+!at(P, L) : at(P, L) <-" in asl
	assert "+!at(P, To) : not at(P, From) <-" not in asl
	assert "+!at(P, To) : at(P, From) & road(From, To) <-" in asl
	assert "\tdrive(P, From, To)." in asl
	assert "goal_at(pkg1, depot)." not in asl
	assert "plan=g_done" not in asl
	assert "!achieve_" not in asl
	assert "!transition_" not in asl
	assert "dfa_state" not in asl


def test_schema_synthesizer_also_handles_blocksworld_without_domain_specific_code() -> None:
	plan_library = build_goal_conditioned_library_from_pddl(
		domain_file=BLOCKS_DOMAIN,
		training_problem_files=(BLOCKS_P01,),
	)
	asl = render_plan_library_asl(plan_library)

	assert "+!g : goal_on(X, Y) & not on(X, Y) <-" in asl
	assert "+!on(X, Y) : on(X, Y) <-" in asl
	assert "+!on(X, Y) : not holding(X) <-" in asl
	assert "\t!holding(X);" in asl
	assert "+!on(X, Y) : holding(X) & clear(Y) <-" in asl
	assert "\tstack(X, Y)." in asl
	assert "goal_on(b4, b2)." not in asl
	assert "+!g : goal_on(Y, Z) & goal_on(X, Y) & not on(Y, Z) <-" in asl
	assert "+!g : goal_on(Z, W) & goal_on(X, Y) & not on(Z, W) <-" not in asl
	transition_systems = plan_library.metadata["transition_systems"]
	assert transition_systems[0]["goal_facts"] == [
		"goal_on(b4, b2)",
		"goal_on(b1, b4)",
		"goal_on(b3, b1)",
	]
	assert transition_systems[0]["goal_orderings"] == [
		("goal_on(b4, b2)", "goal_on(b1, b4)"),
		("goal_on(b4, b2)", "goal_on(b3, b1)"),
		("goal_on(b1, b4)", "goal_on(b3, b1)"),
	]


def test_goal_facts_from_problem_are_read_only_problem_inputs() -> None:
	goal_facts = goal_facts_from_problem(BLOCKS_P01)

	assert goal_facts == (
		"goal_on(b4, b2)",
		"goal_on(b1, b4)",
		"goal_on(b3, b1)",
	)


def test_synthesis_report_exposes_clingo_schema_contract() -> None:
	domain_file, _ = _write_logistics_domain_and_problem()
	plan_library = build_goal_conditioned_library_from_pddl(domain_file=domain_file)
	report = plan_library.metadata["unified_synthesis_report"]

	assert report["theoretical_contract"] == "bounded_class_guarantee"
	assert report["generation_mode"] == "unified_goal_conditioned_modular_synthesis"
	assert report["external_policy_count"] == 0
	assert report["selected_rule_count"] > 0
	assert report["candidate_count"] >= report["selected_rule_count"]


def test_goal_ordering_rules_filter_ambiguous_lifted_ordering_evidence() -> None:
	forward = (
		PDDLFact("on", ["b", "c"]),
		PDDLFact("on", ["a", "b"]),
	)
	reverse = (
		PDDLFact("on", ["a", "b"]),
		PDDLFact("on", ["b", "c"]),
	)
	rules = _goal_ordering_rules_from_evidence(
		(
			_training_evidence("forward", (forward,)),
			_training_evidence("reverse", (reverse,)),
		),
	)

	assert rules == ()


def test_transition_progress_validation_rejects_selected_rules_with_wrong_action() -> None:
	evidence = TrainingTransitionEvidence(
		problem_name="p1",
		object_count=1,
		explored_state_count=2,
		explored_transition_count=1,
		plan_length=1,
		goal_facts=("goal_done(a)",),
		goal_orderings=(),
		goal_progressions=(
			GoalProgressEvidence(
				goal_fact=PDDLFact("done", ["a"]),
				action_name="finish",
				action_arguments=("a",),
				action_signature="finish(a)",
				step_index=1,
				before_state=("ready(a)",),
				after_state=("done(a)", "ready(a)"),
			),
		),
	)
	rule = LiftedPlanRule(
		name="done_via_wrong_action",
		head=LiftedCall("subgoal", "done", ("X",)),
		context=("ready(X)",),
		body=(LiftedCall("action", "wait", ("X",)),),
		layer="atomic",
	)

	try:
		_validate_selected_rules_against_transition_progress((rule,), (evidence,))
	except ValueError as exc:
		assert "fails bounded transition-progress validation" in str(exc)
	else:
		raise AssertionError("Expected wrong selected action to fail validation.")


def test_unsupported_negative_training_goal_fails_instead_of_silent_fallback(
	tmp_path: Path,
) -> None:
	domain_file, _ = _write_logistics_domain_and_problem(tmp_path)
	problem_file = tmp_path / "negative-goal.pddl"
	problem_file.write_text(
		"""
		(define (problem negative-goal)
		 (:domain logistics-mini)
		 (:objects pkg1 depot - object)
		 (:init (at pkg1 depot))
		 (:goal (and (not (at pkg1 depot))))
		)
		""",
		encoding="utf-8",
	)

	try:
		build_goal_conditioned_library_from_pddl(
			domain_file=domain_file,
			training_problem_files=(problem_file,),
		)
	except ValueError as exc:
		assert "positive achievement goals only" in str(exc)
	else:
		raise AssertionError("Expected unsupported negative goal to fail.")


def _write_logistics_domain_and_problem(
	tmp_path: Path | None = None,
) -> tuple[Path, Path]:
	root = tmp_path or Path.cwd() / "tmp" / "schema-synthesis-tests"
	root.mkdir(parents=True, exist_ok=True)
	domain_file = root / "domain.pddl"
	problem_file = root / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain logistics-mini)
		 (:requirements :strips :typing)
		 (:types object)
		 (:predicates
		  (at ?p - object ?l - object)
		  (road ?from - object ?to - object)
		 )
		 (:action drive
		  :parameters (?p - object ?from - object ?to - object)
		  :precondition (and (at ?p ?from) (road ?from ?to))
		  :effect (and (not (at ?p ?from)) (at ?p ?to))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem logistics-p1)
		 (:domain logistics-mini)
		 (:objects pkg1 depot hub - object)
		 (:init (at pkg1 hub) (road hub depot))
		 (:goal (and (at pkg1 depot)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _training_evidence(
	name: str,
	orderings: tuple[tuple[PDDLFact, PDDLFact], ...],
) -> TrainingTransitionEvidence:
	return TrainingTransitionEvidence(
		problem_name=name,
		object_count=3,
		explored_state_count=1,
		explored_transition_count=1,
		plan_length=1,
		goal_facts=(),
		goal_orderings=orderings,
	)
