from __future__ import annotations

from pathlib import Path

from domain_level_planning import (
	build_blocksworld_goal_conditioned_library,
	goal_facts_from_problem,
)
from plan_library.rendering import render_plan_library_asl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "domain.pddl"
BLOCKS_P01 = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "problems" / "p01.pddl"


def test_blocksworld_synthesizer_builds_lifted_atomic_modules() -> None:
	plan_library = build_blocksworld_goal_conditioned_library(domain_file=BLOCKS_DOMAIN)
	asl = render_plan_library_asl(plan_library)

	assert plan_library.domain_name == "BLOCKS"
	assert plan_library.initial_beliefs == ()
	assert plan_library.metadata["generation_mode"] == "goal_conditioned_modular_sketch"
	assert "+!clear(X)" in asl
	assert "+!on(X, Y)" in asl
	assert "+!ontable(X)" in asl
	assert "!clear(Y);" in asl
	assert "stack(X, Y)" in asl
	assert "unstack(Y, X)" in asl
	assert "!achieve_" not in asl
	assert "!transition_" not in asl
	assert "dfa_state" not in asl


def test_blocksworld_composer_prioritizes_bottom_up_goal_dependency() -> None:
	plan_library = build_blocksworld_goal_conditioned_library(domain_file=BLOCKS_DOMAIN)
	asl = render_plan_library_asl(plan_library)

	bottom_up_index = asl.index("+!g : goal_on(Y, Z) & goal_on(X, Y) & not on(Y, Z) <-")
	generic_on_index = asl.index("+!g : goal_on(X, Y) & not on(X, Y) <-")

	assert bottom_up_index < generic_on_index
	assert "\t!on(Y, Z);" in asl
	assert "\t!g." in asl
	assert "!goal_on" not in asl


def test_goal_facts_from_problem_are_read_only_problem_inputs() -> None:
	goal_facts = goal_facts_from_problem(BLOCKS_P01)

	assert goal_facts == (
		"goal_on(b4, b2)",
		"goal_on(b1, b4)",
		"goal_on(b3, b1)",
	)


def test_generated_library_is_domain_level_not_query_or_object_specific() -> None:
	plan_library = build_blocksworld_goal_conditioned_library(
		domain_file=BLOCKS_DOMAIN,
		training_problem_files=(BLOCKS_P01,),
	)
	asl = render_plan_library_asl(plan_library)

	for object_name in ("b1", "b2", "b3", "b4", "b5"):
		assert f"+!on({object_name}" not in asl
		assert f"+!clear({object_name}" not in asl
	assert "goal_on(b4, b2)." not in asl
	assert plan_library.metadata["training_problem_count"] == 1
	assert plan_library.metadata["training_goal_facts"] == (
		"goal_on(b4, b2)",
		"goal_on(b1, b4)",
		"goal_on(b3, b1)",
	)
	assert "compose_unsatisfied_goal_on" in plan_library.metadata["required_capabilities"]
	transition_systems = plan_library.metadata["transition_systems"]
	assert len(transition_systems) == 1
	assert transition_systems[0]["problem_name"] == "p01"
	assert transition_systems[0]["reachable_state_count"] > 0
	assert transition_systems[0]["transition_count"] > 0


def test_synthesis_report_exposes_bounded_class_contract_without_runtime_planner() -> None:
	plan_library = build_blocksworld_goal_conditioned_library(domain_file=BLOCKS_DOMAIN)
	report = plan_library.metadata["synthesis_report"]

	assert report["theoretical_contract"] == "bounded_class_guarantee"
	assert report["solver_family"] == "clingo_goal_conditioned_modular_policy_sketch"
	assert report["runtime_full_trace_planner"] is False
	assert report["uses_read_only_goal_facts"] is True
	assert report["selected_rule_count"] == report["candidate_rule_count"]
	assert plan_library.metadata["selection_cost"] == report["selected_rule_count"]


def test_unsupported_training_goal_fails_instead_of_silent_fallback(tmp_path: Path) -> None:
	problem_file = tmp_path / "unsupported-goal.pddl"
	problem_file.write_text(
		"""
		(define (problem unsupported-goal)
		 (:domain BLOCKS)
		 (:objects b1 - block)
		 (:init (handempty) (ontable b1) (clear b1))
		 (:goal (and (not (clear b1))))
		)
		""",
		encoding="utf-8",
	)

	try:
		build_blocksworld_goal_conditioned_library(
			domain_file=BLOCKS_DOMAIN,
			training_problem_files=(problem_file,),
		)
	except ValueError as exc:
		assert "positive achievement goals only" in str(exc)
	else:
		raise AssertionError("Expected unsupported negative goal to fail.")
