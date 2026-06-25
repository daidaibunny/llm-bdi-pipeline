from __future__ import annotations

from pathlib import Path

from domain_level_planning.transition_system import (
	AtomicAchievementEvidence,
	apply_ground_action,
	anti_unify_atomic_achievements,
	anti_unify_training_atomic_achievements,
	atomic_achievements_from_plan,
	collect_training_transition_evidence,
	collect_training_transition_evidence_from_plan,
	ground_actions_for_problem,
	is_action_applicable,
)
from low_level_planning.models import LowLevelAction
from utils.pddl_parser import PDDLParser


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "domain.pddl"
BLOCKS_P01 = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "problems" / "p01.pddl"


def test_training_evidence_slices_non_goal_atomic_achievements() -> None:
	domain = PDDLParser.parse_domain(BLOCKS_DOMAIN)
	problem = PDDLParser.parse_problem(BLOCKS_P01)

	evidence = collect_training_transition_evidence(domain, problem)

	achieved_predicates = {
		slice_.target_fact.predicate
		for slice_ in evidence.atomic_achievements
	}
	# Layer B must observe intermediate, non-goal predicates, not only on(...).
	assert "holding" in achieved_predicates
	assert "clear" in achieved_predicates
	# Every slice records the achiever action and the step that produced it.
	for slice_ in evidence.atomic_achievements:
		assert slice_.action_name
		assert slice_.step_index >= 1
		target_atom = (
			slice_.target_fact.predicate
			if not slice_.target_fact.args
			else f"{slice_.target_fact.predicate}({', '.join(slice_.target_fact.args)})"
		)
		assert target_atom in slice_.after_state
		assert target_atom not in slice_.before_state


def test_atomic_achievement_records_enabling_preconditions() -> None:
	domain = PDDLParser.parse_domain(BLOCKS_DOMAIN)
	problem = PDDLParser.parse_problem(BLOCKS_P01)

	evidence = collect_training_transition_evidence(domain, problem)

	on_slices = [
		slice_
		for slice_ in evidence.atomic_achievements
		if slice_.target_fact.predicate == "on"
	]
	assert on_slices
	# on(?x,?y) is achieved by stack, whose preconditions are holding(?x) & clear(?y).
	stack_slice = next(
		slice_ for slice_ in on_slices if slice_.action_name == "stack"
	)
	enabling_predicates = {
		literal.predicate for literal in stack_slice.enabling_preconditions
	}
	assert enabling_predicates == {"holding", "clear"}
	# Enabling preconditions must actually hold in the before-state of the slice.
	for literal in stack_slice.enabling_preconditions:
		atom = f"{literal.predicate}({', '.join(literal.arguments)})"
		assert atom in stack_slice.before_state


def test_last_achiever_marks_only_final_false_to_true_transition() -> None:
	# A handcrafted plan that achieves clear(a) twice: only the second counts.
	from domain_level_planning.transition_system import GroundAction
	from domain_level_planning.pddl_expression import LiftedLiteral

	def lit(predicate: str, *args: str, positive: bool = True) -> LiftedLiteral:
		return LiftedLiteral(predicate=predicate, arguments=tuple(args), is_positive=positive)

	put_down_first = GroundAction(
		name="put-down",
		arguments=("a",),
		preconditions=(lit("holding", "a"),),
		add_effects=(lit("clear", "a"), lit("ontable", "a")),
		delete_effects=(lit("holding", "a"),),
		substitution={"x": "a"},
	)
	pick_up = GroundAction(
		name="pick-up",
		arguments=("a",),
		preconditions=(lit("clear", "a"), lit("ontable", "a")),
		add_effects=(lit("holding", "a"),),
		delete_effects=(lit("clear", "a"), lit("ontable", "a")),
		substitution={"x": "a"},
	)
	put_down_second = GroundAction(
		name="put-down",
		arguments=("a",),
		preconditions=(lit("holding", "a"),),
		add_effects=(lit("clear", "a"), lit("ontable", "a")),
		delete_effects=(lit("holding", "a"),),
		substitution={"x": "a"},
	)

	achievements = atomic_achievements_from_plan(
		initial_state=frozenset({"holding(a)"}),
		plan=(put_down_first, pick_up, put_down_second),
	)

	clear_slices = [s for s in achievements if s.target_fact.predicate == "clear"]
	# clear(a) is achieved at step 1 and again at step 3.
	assert [s.step_index for s in clear_slices] == [1, 3]
	assert [s.is_last_achiever for s in clear_slices] == [False, True]


def test_atomic_achievement_evidence_is_serializable() -> None:
	domain = PDDLParser.parse_domain(BLOCKS_DOMAIN)
	problem = PDDLParser.parse_problem(BLOCKS_P01)

	evidence = collect_training_transition_evidence(domain, problem)
	payload = evidence.to_dict()

	assert "atomic_achievements" in payload
	assert isinstance(payload["atomic_achievements"], list)
	assert payload["atomic_achievements"]
	first = payload["atomic_achievements"][0]
	assert set(first) >= {
		"target_fact",
		"action_name",
		"action_arguments",
		"step_index",
		"is_last_achiever",
		"enabling_preconditions",
	}
	assert isinstance(
		AtomicAchievementEvidence.__dataclass_fields__["is_last_achiever"].default,
		bool,
	)


def test_atomic_achievement_anti_unification_groups_repeated_grounded_examples() -> None:
	domain = PDDLParser.parse_domain(BLOCKS_DOMAIN)
	problem = PDDLParser.parse_problem(BLOCKS_P01)

	evidence = collect_training_transition_evidence(domain, problem)
	patterns = anti_unify_atomic_achievements(evidence.atomic_achievements)

	on_stack = [
		pattern
		for pattern in patterns
		if pattern.target_predicate == "on" and pattern.action_name == "stack"
	]
	assert len(on_stack) == 1
	pattern = on_stack[0]
	assert pattern.target_arguments == ("X", "Y")
	assert pattern.action_arguments == ("X", "Y")
	assert pattern.enabling_preconditions == ("clear(Y)", "holding(X)")
	assert pattern.support_count >= 1
	assert pattern.last_achiever_support_count >= 1
	assert pattern.example_signatures
	assert pattern.to_dict()["support_count"] == pattern.support_count


def test_training_atomic_anti_unification_merges_across_evidence_objects() -> None:
	domain = PDDLParser.parse_domain(BLOCKS_DOMAIN)
	problem = PDDLParser.parse_problem(BLOCKS_P01)

	evidence = collect_training_transition_evidence(domain, problem)
	patterns = anti_unify_training_atomic_achievements((evidence, evidence))

	on_stack = next(
		pattern
		for pattern in patterns
		if pattern.target_predicate == "on" and pattern.action_name == "stack"
	)
	assert on_stack.support_count >= 2


def test_training_evidence_can_be_built_from_offline_planner_trace() -> None:
	domain = PDDLParser.parse_domain(BLOCKS_DOMAIN)
	problem = PDDLParser.parse_problem(BLOCKS_P01)
	bounded = collect_training_transition_evidence(domain, problem)
	trace_actions = tuple(
		LowLevelAction(action.name, action.arguments)
		for action in bounded.plan_actions
	)

	evidence = collect_training_transition_evidence_from_plan(
		domain,
		problem,
		trace_actions,
		evidence_source="offline_planner_trace",
	)

	assert evidence.evidence_source == "offline_planner_trace"
	assert evidence.explored_state_count == 0
	assert evidence.explored_transition_count == len(trace_actions)
	assert evidence.plan_length == bounded.plan_length
	assert evidence.plan_actions == bounded.plan_actions
	assert evidence.goal_progressions
	assert evidence.atomic_achievements
	assert evidence.to_dict()["evidence_source"] == "offline_planner_trace"


def test_transition_system_evaluates_equality_preconditions_and_ignores_numeric_effects(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_distinct_metric_domain(tmp_path)
	domain = PDDLParser.parse_domain(domain_file)
	problem = PDDLParser.parse_problem(problem_file)
	actions = ground_actions_for_problem(domain.actions, problem)

	distinct_action = next(
		action for action in actions if action.signature() == "finish(a, b)"
	)
	same_action = next(
		action for action in actions if action.signature() == "finish(a, a)"
	)
	state = frozenset({"ready(a)", "ready(b)"})

	assert is_action_applicable(state, distinct_action) is True
	assert is_action_applicable(state, same_action) is False
	assert apply_ground_action(state, distinct_action) == frozenset(
		{"ready(a)", "ready(b)", "done(a, b)"},
	)


def test_transition_system_matches_pddl_types_case_insensitively(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_mixed_case_type_domain(tmp_path)
	domain = PDDLParser.parse_domain(domain_file)
	problem = PDDLParser.parse_problem(problem_file)

	actions = ground_actions_for_problem(domain.actions, problem, domain_types=domain.types)

	assert any(
		action.signature() == "calibrate(camera0, target0)"
		for action in actions
	)


def _write_distinct_metric_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "distinct-metric-domain.pddl"
	problem_file = tmp_path / "distinct-metric-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain distinct-metric)
		 (:requirements :strips :equality :negative-preconditions :action-costs)
		 (:predicates
		  (ready ?x)
		  (done ?x ?y)
		 )
		 (:functions (total-cost))
		 (:action finish
		  :parameters (?x ?y)
		  :precondition (and (ready ?x) (ready ?y) (not (= ?x ?y)))
		  :effect (and (done ?x ?y) (increase (total-cost) 1))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem distinct-metric-p1)
		 (:domain distinct-metric)
		 (:objects a b)
		 (:init (ready a) (ready b) (= (total-cost) 0))
		 (:goal (and (done a b)))
		 (:metric minimize (total-cost))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_mixed_case_type_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "mixed-case-domain.pddl"
	problem_file = tmp_path / "mixed-case-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain mixed-case-types)
		 (:requirements :strips :typing)
		 (:types camera objective)
		 (:predicates (ready ?c - camera ?o - objective) (done ?c - camera ?o - objective))
		 (:action calibrate
		  :parameters (?c - camera ?o - objective)
		  :precondition (ready ?c ?o)
		  :effect (done ?c ?o)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem mixed-case-p1)
		 (:domain mixed-case-types)
		 (:objects camera0 - Camera target0 - Objective)
		 (:init (ready camera0 target0))
		 (:goal (and (done camera0 target0)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file
