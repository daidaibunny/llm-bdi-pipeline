from __future__ import annotations

from pathlib import Path

from domain_level_planning.transition_system import (
	AtomicAchievementEvidence,
	atomic_achievements_from_plan,
	collect_training_transition_evidence,
)
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
