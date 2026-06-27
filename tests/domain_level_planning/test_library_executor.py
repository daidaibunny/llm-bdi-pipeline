from __future__ import annotations

from pathlib import Path

from domain_level_planning.library_executor import _context_substitutions
from domain_level_planning.library_executor import evaluate_library_on_problem
from domain_level_planning.library_verifier import (
	validate_library_on_bounded_transition_systems,
)
from domain_level_planning.library_synthesis import synthesize_domain_level_asl_library
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary
from plan_library.rendering import render_plan_library_asl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_ROOT = PROJECT_ROOT / "src" / "domains" / "blocksworld"
BLOCKS_DOMAIN = BLOCKS_ROOT / "domain.pddl"
BLOCKS_PROBLEMS = tuple(sorted((BLOCKS_ROOT / "problems").glob("p*.pddl")))


def test_lifted_blocksworld_library_from_one_training_problem_solves_first_20() -> None:
	result = synthesize_domain_level_asl_library(
		domain_file=BLOCKS_DOMAIN,
		training_problem_files=(BLOCKS_PROBLEMS[0],),
	)
	plan_library = result.plan_library
	asl = render_plan_library_asl(plan_library)

	assert len(plan_library.plans) >= 40
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl
	causal_plan = "+!g : goal_on(Y, Z) & goal_on(X, Y) & not on(Y, Z) <-"
	binding_causal_plan = (
		"+!g : goal_on(Y, Z) & goal_clear(X) & on(Y, X) & not on(Y, Z) <-"
	)
	generic_plan = "+!g : goal_on(X, Y) & ready_on(X, Y) & not on(X, Y) <-"
	assert causal_plan in asl
	assert binding_causal_plan in asl
	assert asl.index(causal_plan) < asl.index(generic_plan)
	layer_c = result.report["evidence_matrix"]["layer_c_goal_composer"]
	assert layer_c["causal_interference_selected_count"] >= 1
	assert layer_c["delete_threat_ordering_selected_count"] >= 1

	results = tuple(
		evaluate_library_on_problem(
			plan_library=plan_library,
			domain_file=BLOCKS_DOMAIN,
			problem_file=problem_file,
			max_steps=10000,
			max_depth=1000,
		)
		for problem_file in BLOCKS_PROBLEMS[:20]
	)

	assert [result.problem_name for result in results] == [
		f"p{index:02d}"
		for index in range(1, 21)
	]
	assert all(result.solved for result in results), [
		(result.problem_name, result.failure_reason)
		for result in results
		if not result.solved
	]
	assert [len(result.steps) for result in results] == [
		12,
		30,
		24,
		32,
		64,
		66,
		44,
		88,
		76,
		74,
		94,
		90,
		90,
		128,
		102,
		116,
		122,
		126,
		120,
		172,
	]

	bounded_validation = result.report["bounded_validation"]
	assert bounded_validation["passed"] is True
	assert bounded_validation["execution_semantics"] == "deterministic_first_applicable_asl"
	assert bounded_validation["checked_problem_count"] == 1
	assert bounded_validation["checked_state_count"] > 1
	assert bounded_validation["failure_count"] == 0


def test_bounded_verifier_checks_all_reachable_states_for_small_domain(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_tiny_switch_domain(tmp_path)
	plan_library = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
	).plan_library

	report = validate_library_on_bounded_transition_systems(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_files=(problem_file,),
		max_reachable_states=10,
		max_execution_steps=10,
		max_depth=10,
	)

	assert report.passed is True
	assert report.checked_problem_count == 1
	assert report.checked_state_count == 2
	assert report.problem_reports[0].goal_state_count == 1
	assert report.problem_reports[0].max_execution_steps == 1


def test_executor_can_disable_planner_style_body_failure_backtracking(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_two_action_domain(tmp_path)
	plan_library = PlanLibrary(
		domain_name="two-action",
		plans=(
			AgentSpeakPlan(
				plan_name="bad_first",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("goal_done", "ready"),
				body=(AgentSpeakBodyStep("action", "wrong"),),
			),
			AgentSpeakPlan(
				plan_name="good_second",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("goal_done", "ready"),
				body=(AgentSpeakBodyStep("action", "finish"),),
			),
		),
	)

	with_backtracking = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
		backtrack_on_body_failure=True,
	)
	without_backtracking = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
		backtrack_on_body_failure=False,
	)

	assert with_backtracking.solved is True
	assert with_backtracking.steps == ("finish",)
	assert without_backtracking.solved is False
	assert "preconditions" in str(without_backtracking.failure_reason).lower()
	assert "wrong" in str(without_backtracking.failure_reason)


def test_executor_treats_context_literals_as_order_independent_conjunction(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_single_object_done_domain(tmp_path)
	plan_library = PlanLibrary(
		domain_name="single-object-done",
		plans=(
			AgentSpeakPlan(
				plan_name="g_satisfy_done_with_negation_first",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("not done(X)", "goal_done(X)", "ready(X)"),
				body=(AgentSpeakBodyStep("action", "finish", ("X",)),),
			),
		),
	)

	execution = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
	)

	assert execution.solved is True
	assert execution.steps == ("finish(a)",)


def test_context_substitutions_are_deterministic_for_unordered_state_facts() -> None:
	substitutions = _context_substitutions(
		contexts=("choice(X)",),
		substitution={},
		state=frozenset(("choice(b)", "choice(a)")),
		goal_facts=(),
		derived_context_facts=(),
	)

	assert tuple(substitution["X"] for substitution in substitutions) == ("a", "b")


def test_executor_evaluates_lifted_inequality_contexts_and_preconditions(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_distinct_pair_domain(tmp_path)
	plan_library = PlanLibrary(
		domain_name="distinct-pair",
		plans=(
			AgentSpeakPlan(
				plan_name="g_satisfy_distinct_done",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("goal_done(X, Y)", "not done(X, Y)"),
				body=(
					AgentSpeakBodyStep("subgoal", "done", ("X", "Y")),
					AgentSpeakBodyStep("subgoal", "g"),
				),
			),
			AgentSpeakPlan(
				plan_name="done_when_distinct",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("X", "Y")),
				context=("ready(X)", "ready(Y)", "not =(X, Y)"),
				body=(AgentSpeakBodyStep("action", "finish", ("X", "Y")),),
			),
		),
	)

	execution = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
	)

	assert execution.solved is True
	assert execution.steps == ("finish(a, b)",)


def test_executor_derives_ready_goal_contexts_from_selected_agenda_edges(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_two_object_ordered_done_domain(tmp_path)
	plan_library = PlanLibrary(
		domain_name="ordered-done",
		plans=(
			AgentSpeakPlan(
				plan_name="g_satisfy_goal_done",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("goal_done(X)", "ready_done(X)", "not done(X)"),
				body=(
					AgentSpeakBodyStep("subgoal", "done", ("X",)),
					AgentSpeakBodyStep("subgoal", "g"),
				),
			),
			AgentSpeakPlan(
				plan_name="done_already_true",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
				context=("done(X)",),
				body=(),
			),
			AgentSpeakPlan(
				plan_name="done_via_finish",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
				context=("ready(X)",),
				body=(AgentSpeakBodyStep("action", "finish", ("X",)),),
			),
		),
		metadata={
			"runtime_goal_agenda": {
				"read_only_ready_contexts": True,
				"support_edges": (
					{
						"category": "support",
						"selected": True,
						"earlier": "done(A)",
						"later": "done(B)",
						"binding_contexts": ("precedes(A, B)",),
					},
				),
			},
		},
	)

	execution = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
	)

	assert execution.solved is True
	assert execution.steps == ("finish(a)", "finish(b)")


def test_executor_reports_schema_goal_mutex_before_running_library(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_exclusive_slot_domain(tmp_path)
	plan_library = PlanLibrary(
		domain_name="exclusive-slot",
		plans=(),
	)

	execution = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
	)

	assert execution.solved is False
	assert execution.steps == ()
	assert execution.failure_reason is not None
	assert "goal mutex" in execution.failure_reason
	assert "placed(a, s)" in execution.failure_reason
	assert "free(s)" in execution.failure_reason


def test_executor_reports_blocksworld_goal_mutex_before_recursive_loop() -> None:
	plan_library = PlanLibrary(
		domain_name="blocks-empty",
		plans=(),
	)

	execution = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=BLOCKS_DOMAIN,
		problem_file=BLOCKS_PROBLEMS[20],
		max_steps=10000,
		max_depth=1000,
	)

	assert execution.problem_name == "p21"
	assert execution.solved is False
	assert execution.steps == ()
	assert execution.failure_reason is not None
	assert "goal mutex" in execution.failure_reason
	assert "clear(b2)" in execution.failure_reason
	assert "on(b17, b2)" in execution.failure_reason


def _write_tiny_switch_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain tiny-switch)
		 (:requirements :strips)
		 (:predicates (ready) (done))
		 (:action finish
		  :parameters ()
		  :precondition (ready)
		  :effect (and (not (ready)) (done))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem tiny-p1)
		 (:domain tiny-switch)
		 (:objects)
		 (:init (ready))
		 (:goal (and (done)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_exclusive_slot_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "exclusive-slot-domain.pddl"
	problem_file = tmp_path / "exclusive-slot-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain exclusive-slot)
		 (:requirements :strips)
		 (:predicates
		  (carrying ?x)
		  (placed ?x ?slot)
		  (free ?slot)
		 )
		 (:action place
		  :parameters (?x ?slot)
		  :precondition (and (carrying ?x) (free ?slot))
		  :effect (and (placed ?x ?slot) (not (free ?slot)) (not (carrying ?x)))
		 )
		 (:action remove
		  :parameters (?x ?slot)
		  :precondition (placed ?x ?slot)
		  :effect (and (carrying ?x) (free ?slot) (not (placed ?x ?slot)))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem exclusive-slot-p1)
		 (:domain exclusive-slot)
		 (:objects a s)
		 (:init (carrying a) (free s))
		 (:goal (and (placed a s) (free s)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_two_object_ordered_done_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "ordered-done-domain.pddl"
	problem_file = tmp_path / "ordered-done-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain ordered-done)
		 (:requirements :strips)
		 (:predicates (ready ?x) (done ?x) (precedes ?x ?y))
		 (:action finish
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem ordered-done-p1)
		 (:domain ordered-done)
		 (:objects a b)
		 (:init (ready a) (ready b) (precedes a b))
		 (:goal (and (done b) (done a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_distinct_pair_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "distinct-pair-domain.pddl"
	problem_file = tmp_path / "distinct-pair-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain distinct-pair)
		 (:requirements :strips :equality :negative-preconditions)
		 (:predicates
		  (ready ?x)
		  (done ?x ?y)
		 )
		 (:action finish
		  :parameters (?x ?y)
		  :precondition (and (ready ?x) (ready ?y) (not (= ?x ?y)))
		  :effect (done ?x ?y)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem distinct-pair-p1)
		 (:domain distinct-pair)
		 (:objects a b)
		 (:init (ready a) (ready b))
		 (:goal (and (done a b)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_single_object_done_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "single-object-domain.pddl"
	problem_file = tmp_path / "single-object-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain single-object-done)
		 (:requirements :strips)
		 (:predicates (ready ?x) (done ?x))
		 (:action finish
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem single-object-p1)
		 (:domain single-object-done)
		 (:objects a)
		 (:init (ready a))
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_two_action_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain two-action)
		 (:requirements :strips)
		 (:predicates (ready) (wrong-ready) (done))
		 (:action wrong
		  :parameters ()
		  :precondition (wrong-ready)
		  :effect (done)
		 )
		 (:action finish
		  :parameters ()
		  :precondition (ready)
		  :effect (done)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem two-action-p1)
		 (:domain two-action)
		 (:objects)
		 (:init (ready))
		 (:goal (and (done)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file
