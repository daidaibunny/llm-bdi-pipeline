from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from domain_level_planning.library_executor import evaluate_library_on_problem
from domain_level_planning.library_verifier import LibraryCounterexample
from domain_level_planning.refinement import HeldoutProblemEvaluation
from domain_level_planning.refinement import RefinementConstraint
from domain_level_planning.refinement import classify_heldout_failure_for_refinement
from domain_level_planning.refinement import synthesize_with_counterexample_refinement
from plan_library.rendering import render_plan_library_asl
from utils.pddl_parser import PDDLParser


def test_counterexample_refinement_learns_goal_ordering_without_problem_reexploration(
	tmp_path: Path,
) -> None:
	domain_file, single_goal_problem, dependent_problem = _write_ordering_domain(tmp_path)

	refined = synthesize_with_counterexample_refinement(
		domain_file=domain_file,
		training_problem_files=(single_goal_problem,),
		heldout_problem_files=(dependent_problem,),
		max_refinement_rounds=1,
		max_execution_steps=20,
		max_depth=20,
	)

	assert refined.converged is True
	assert len(refined.rounds) == 2
	summary = refined.to_dict()["refinement_summary"]
	assert summary["converged"] is True
	assert summary["round_count"] == 2
	assert summary["failed_heldout_evaluation_count"] == 1
	assert summary["solved_heldout_evaluation_count"] == 1
	assert summary["added_counterexample_problem_count"] == 0
	assert summary["constraint_only_refinement_round_count"] == 1
	assert summary["constraint_count"] == 1
	assert summary["generative_constraint_count"] == 1
	assert summary["diagnostic_constraint_count"] == 0
	assert summary["constraints_by_failure_kind"] == {"goal_ordering_failure": 1}
	assert summary["constraints_by_target_layer"] == {"layer_c_goal_composer": 1}
	assert summary["constraints_by_type"] == {"counterexample_goal_ordering": 1}
	assert summary["final_counterexample_problem_count"] == 0
	assert refined.rounds[0].heldout_evaluations[0].solved is False
	assert refined.rounds[0].heldout_evaluations[0].counterexample is not None
	constraint = refined.rounds[0].heldout_evaluations[0].refinement_constraints[0]
	assert constraint.failure_kind == "goal_ordering_failure"
	assert constraint.target_layer == "layer_c_goal_composer"
	assert constraint.constraint_type == "counterexample_goal_ordering"
	assert constraint.lifted_orderings == (
		("goal_z_base(Y)", "goal_a_top(X, Y)"),
	)
	assert constraint.required_rule_group_types == (
		"counterexample_transition_progress",
		"counterexample_state_coverage",
		"counterexample_goal_ordering",
	)
	assert refined.rounds[0].refinement_constraints == (constraint,)
	assert (
		refined.rounds[0].to_dict()["refinement_constraints"][0]["failure_kind"]
		== "goal_ordering_failure"
	)
	assert refined.rounds[0].added_counterexample_problem_files == ()
	assert refined.rounds[1].heldout_evaluations[0].solved is True
	assert str(dependent_problem.resolve()) not in refined.rounds[1].training_problem_files
	assert refined.rounds[1].counterexample_problem_files == ()
	assert (
		refined.rounds[1].synthesis_report[
			"selector_counterexample_goal_ordering_constraint_count"
		]
		> 0
	)
	assert (
		refined.rounds[1].synthesis_report["selected_candidate_sources"][
			"counterexample_goal_ordering"
		]
		== 1
	)

	asl = render_plan_library_asl(refined.final_result.plan_library)
	assert "+!g : goal_z_base(Y) & goal_a_top(X, Y) & not z_base(Y) <-" in asl
	assert "\t!z_base(Y);" in asl
	assert "!achieve_" not in asl
	assert "!transition_" not in asl
	assert "dfa_state" not in asl

	execution = evaluate_library_on_problem(
		plan_library=refined.final_result.plan_library,
		domain_file=domain_file,
		problem_file=dependent_problem,
		max_steps=20,
		max_depth=20,
	)
	assert execution.solved is True
	assert execution.steps == ("make_base(b)", "make_top(a, b)")


def test_counterexample_refinement_continues_on_new_constraints_without_new_files(
	tmp_path: Path,
	monkeypatch,
) -> None:
	problem_file = tmp_path / "already-training.pddl"
	problem_file.write_text("", encoding="utf-8")
	problem_path = str(problem_file.resolve())
	constraint = RefinementConstraint(
		failure_kind="missing_composer_or_context",
		target_layer="layer_c_goal_composer",
		constraint_type="counterexample_state_coverage",
		problem_file=problem_path,
		problem_name="already-training",
		failure_reason="no applicable plan for !g",
		ground_missing_goals=("done(a)",),
		lifted_missing_goals=("done(X)",),
		required_rule_group_types=("counterexample_state_coverage",),
	)
	synthesis_calls: list[dict[str, object]] = []

	def fake_synthesize(**kwargs):
		synthesis_calls.append(dict(kwargs))
		return SimpleNamespace(report={"round": len(synthesis_calls)})

	def fake_evaluate(**kwargs):
		has_constraints = bool(synthesis_calls[-1]["refinement_constraints"])
		return (
			HeldoutProblemEvaluation(
				problem_file=problem_path,
				problem_name="already-training",
				solved=has_constraints,
				step_count=1 if has_constraints else 0,
				failure_reason=None if has_constraints else "no applicable plan for !g",
				refinement_constraints=() if has_constraints else (constraint,),
			),
		)

	monkeypatch.setattr(
		"domain_level_planning.refinement.synthesize_domain_level_asl_library",
		fake_synthesize,
	)
	monkeypatch.setattr(
		"domain_level_planning.refinement._evaluate_heldout_problems",
		fake_evaluate,
	)

	refined = synthesize_with_counterexample_refinement(
		domain_file=tmp_path / "domain.pddl",
		training_problem_files=(problem_file,),
		heldout_problem_files=(problem_file,),
		counterexample_problem_files=(problem_file,),
		max_refinement_rounds=1,
	)

	assert refined.converged is True
	assert len(refined.rounds) == 2
	assert refined.rounds[0].added_counterexample_problem_files == ()
	assert refined.rounds[0].refinement_constraints
	assert (
		refined.to_dict()["refinement_summary"][
			"constraint_only_refinement_round_count"
		]
		== 1
	)
	assert synthesis_calls[0]["counterexample_problem_files"] == (problem_path,)
	assert synthesis_calls[1]["refinement_constraints"] == (constraint,)
	assert refined.rounds[1].heldout_evaluations[0].solved is True


def test_primitive_precondition_failure_refinement_reports_lifted_layer_b_evidence(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_precondition_failure_domain(tmp_path)
	problem = PDDLParser.parse_problem(problem_file)
	counterexample = LibraryCounterexample(
		problem_name=problem.name,
		state_index=0,
		failure_reason="Action preconditions are not satisfied for finish(a).",
		state=("ready(a)",),
		goal_facts=("goal_done(a)",),
		goal_atoms=("done(a)",),
		was_goal_state=False,
		steps=(),
		final_state=("ready(a)",),
	)

	constraints = classify_heldout_failure_for_refinement(
		problem_file=problem_file,
		problem=problem,
		counterexample=counterexample,
		domain_file=domain_file,
	)

	assert len(constraints) == 1
	constraint = constraints[0]
	assert constraint.failure_kind == "primitive_precondition_failure"
	assert constraint.target_layer == "layer_b_atomic_modules"
	assert constraint.constraint_type == "counterexample_atomic_precondition_repair"
	assert constraint.ground_missing_goals == ("done(a)",)
	assert constraint.lifted_missing_goals == ("done(X)",)
	assert constraint.failing_action == "finish"
	assert constraint.failing_action_arguments == ("a",)
	assert constraint.lifted_failing_action == "finish(X)"
	assert constraint.missing_preconditions == ("armed(a)",)
	assert constraint.lifted_missing_preconditions == ("armed(X)",)
	assert constraint.required_rule_group_types == (
		"counterexample_transition_progress",
		"counterexample_atomic_precondition_repair",
	)
	assert constraint.to_dict()["lifted_missing_preconditions"] == ["armed(X)"]
	round_report = _refinement_summary_like((constraint,))
	assert round_report["repair_constraint_count"] == 1
	assert round_report["generative_constraint_count"] == 1
	assert round_report["diagnostic_constraint_count"] == 0
	assert round_report["constraints_by_type"] == {
		"counterexample_atomic_precondition_repair": 1,
	}


def test_primitive_precondition_failure_takes_priority_over_goal_ordering(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_precondition_failure_with_satisfied_goal_domain(
		tmp_path,
	)
	problem = PDDLParser.parse_problem(problem_file)
	counterexample = LibraryCounterexample(
		problem_name=problem.name,
		state_index=0,
		failure_reason="Action preconditions are not satisfied for finish(a).",
		state=("ready(a)",),
		goal_facts=("goal_done(a)", "goal_logged(a)"),
		goal_atoms=("done(a)", "logged(a)"),
		was_goal_state=False,
		steps=("log(a)",),
		final_state=("ready(a)", "logged(a)"),
	)

	constraints = classify_heldout_failure_for_refinement(
		problem_file=problem_file,
		problem=problem,
		counterexample=counterexample,
		domain_file=domain_file,
	)

	assert len(constraints) == 1
	constraint = constraints[0]
	assert constraint.failure_kind == "primitive_precondition_failure"
	assert constraint.target_layer == "layer_b_atomic_modules"
	assert constraint.constraint_type == "counterexample_atomic_precondition_repair"
	assert constraint.ground_missing_goals == ("done(a)",)
	assert constraint.ground_satisfied_goals == ("logged(a)",)
	assert constraint.lifted_missing_goals == ("done(X)",)
	assert constraint.lifted_satisfied_goals == ("logged(X)",)
	assert constraint.missing_preconditions == ("armed(a)",)
	assert constraint.lifted_missing_preconditions == ("armed(X)",)
	assert constraint.lifted_orderings == ()


def test_missing_module_failure_targets_failed_atomic_subgoal_only(
	tmp_path: Path,
) -> None:
	domain_file, _, dependent_problem = _write_ordering_domain(tmp_path)
	problem = PDDLParser.parse_problem(dependent_problem)
	counterexample = LibraryCounterexample(
		problem_name=problem.name,
		state_index=0,
		failure_reason="no applicable plan for !z_base(b)",
		state=("seed(a)", "seed(b)"),
		goal_facts=("goal_z_base(b)", "goal_a_top(a, b)"),
		goal_atoms=("z_base(b)", "a_top(a, b)"),
		was_goal_state=False,
		steps=(),
		final_state=("seed(a)", "seed(b)"),
	)

	constraints = classify_heldout_failure_for_refinement(
		problem_file=dependent_problem,
		problem=problem,
		counterexample=counterexample,
		domain_file=domain_file,
	)

	assert len(constraints) == 1
	constraint = constraints[0]
	assert constraint.failure_kind == "missing_module_or_context"
	assert constraint.target_layer == "layer_b_atomic_modules"
	assert constraint.constraint_type == "counterexample_atomic_progress"
	assert constraint.ground_missing_goals == ("z_base(b)",)
	assert constraint.lifted_missing_goals == ("z_base(X)",)
	assert constraint.required_rule_group_types == ("counterexample_atomic_progress",)


def test_missing_top_level_composer_failure_targets_layer_c_state_coverage(
	tmp_path: Path,
) -> None:
	_, _, dependent_problem = _write_ordering_domain(tmp_path)
	problem = PDDLParser.parse_problem(dependent_problem)
	counterexample = LibraryCounterexample(
		problem_name=problem.name,
		state_index=0,
		failure_reason="no applicable plan for !g",
		state=("seed(a)", "seed(b)"),
		goal_facts=("goal_z_base(b)", "goal_a_top(a, b)"),
		goal_atoms=("z_base(b)", "a_top(a, b)"),
		was_goal_state=False,
		steps=(),
		final_state=("seed(a)", "seed(b)"),
	)

	constraints = classify_heldout_failure_for_refinement(
		problem_file=dependent_problem,
		problem=problem,
		counterexample=counterexample,
	)

	assert len(constraints) == 1
	constraint = constraints[0]
	assert constraint.failure_kind == "missing_composer_or_context"
	assert constraint.target_layer == "layer_c_goal_composer"
	assert constraint.constraint_type == "counterexample_state_coverage"
	assert constraint.ground_missing_goals == ("z_base(b)", "a_top(a, b)")
	assert constraint.lifted_missing_goals == ("z_base(X)", "a_top(Y, X)")
	assert constraint.required_rule_group_types == ("counterexample_state_coverage",)
	round_report = _refinement_summary_like((constraint,))
	assert round_report["state_coverage_constraint_count"] == 1
	assert round_report["constraints_by_target_layer"] == {
		"layer_c_goal_composer": 1,
	}
	assert round_report["constraints_by_type"] == {
		"counterexample_state_coverage": 1,
	}


def test_top_level_failure_after_progress_keeps_goal_ordering_signal(
	tmp_path: Path,
) -> None:
	_, _, dependent_problem = _write_ordering_domain(tmp_path)
	problem = PDDLParser.parse_problem(dependent_problem)
	counterexample = LibraryCounterexample(
		problem_name=problem.name,
		state_index=0,
		failure_reason="no applicable plan for !g",
		state=("seed(a)", "seed(b)"),
		goal_facts=("goal_z_base(b)", "goal_a_top(a, b)"),
		goal_atoms=("z_base(b)", "a_top(a, b)"),
		was_goal_state=False,
		steps=("make_top(a, b)",),
		final_state=("seed(a)", "a_top(a, b)"),
	)

	constraints = classify_heldout_failure_for_refinement(
		problem_file=dependent_problem,
		problem=problem,
		counterexample=counterexample,
	)

	assert tuple(constraint.constraint_type for constraint in constraints) == (
		"counterexample_goal_ordering",
		"counterexample_state_coverage",
	)
	assert constraints[0].failure_kind == "goal_ordering_failure"
	assert constraints[0].target_layer == "layer_c_goal_composer"
	assert constraints[0].lifted_orderings == (
		("goal_z_base(Y)", "goal_a_top(X, Y)"),
	)
	assert constraints[1].failure_kind == "missing_composer_or_context"
	assert constraints[1].target_layer == "layer_c_goal_composer"
	round_report = _refinement_summary_like(constraints)
	assert round_report["goal_ordering_constraint_count"] == 1
	assert round_report["state_coverage_constraint_count"] == 1
	assert round_report["constraints_by_type"] == {
		"counterexample_goal_ordering": 1,
		"counterexample_state_coverage": 1,
	}


def test_recursive_loop_failure_targets_recursive_atomic_module_diagnostics(
	tmp_path: Path,
) -> None:
	_, _, dependent_problem = _write_ordering_domain(tmp_path)
	problem = PDDLParser.parse_problem(dependent_problem)
	counterexample = LibraryCounterexample(
		problem_name=problem.name,
		state_index=0,
		failure_reason="recursive loop on !z_base(b)",
		state=("seed(a)", "seed(b)"),
		goal_facts=("goal_z_base(b)", "goal_a_top(a, b)"),
		goal_atoms=("z_base(b)", "a_top(a, b)"),
		was_goal_state=False,
		steps=(),
		final_state=("seed(a)", "seed(b)"),
	)

	constraints = classify_heldout_failure_for_refinement(
		problem_file=dependent_problem,
		problem=problem,
		counterexample=counterexample,
	)

	assert tuple(constraint.constraint_type for constraint in constraints) == (
		"counterexample_recursive_loop",
		"counterexample_atomic_progress",
	)
	diagnostic, companion = constraints
	assert diagnostic.failure_kind == "recursive_loop"
	assert diagnostic.target_layer == "layer_b_atomic_modules"
	assert diagnostic.ground_missing_goals == ("z_base(b)",)
	assert diagnostic.lifted_missing_goals == ("z_base(X)",)
	assert diagnostic.required_rule_group_types == ("counterexample_recursion_descent",)
	assert companion.failure_kind == "recursive_loop_atomic_progress"
	assert companion.target_layer == "layer_b_atomic_modules"
	assert companion.ground_missing_goals == ("z_base(b)",)
	assert companion.lifted_missing_goals == ("z_base(X)",)
	assert companion.required_rule_group_types == ("counterexample_atomic_progress",)
	round_report = _refinement_summary_like(constraints)
	assert round_report["recursive_loop_constraint_count"] == 1
	assert round_report["atomic_progress_constraint_count"] == 1
	assert round_report["generative_constraint_count"] == 1
	assert round_report["diagnostic_constraint_count"] == 1
	assert round_report["constraints_by_target_layer"] == {
		"layer_b_atomic_modules": 2,
	}


def test_step_limit_failure_reports_nontermination_diagnostics(
	tmp_path: Path,
) -> None:
	_, _, dependent_problem = _write_ordering_domain(tmp_path)
	problem = PDDLParser.parse_problem(dependent_problem)
	counterexample = LibraryCounterexample(
		problem_name=problem.name,
		state_index=0,
		failure_reason="step limit exceeded",
		state=("seed(a)", "seed(b)"),
		goal_facts=("goal_z_base(b)", "goal_a_top(a, b)"),
		goal_atoms=("z_base(b)", "a_top(a, b)"),
		was_goal_state=False,
		steps=("make_base(b)",),
		final_state=("seed(a)", "seed(b)", "z_base(b)"),
	)

	constraints = classify_heldout_failure_for_refinement(
		problem_file=dependent_problem,
		problem=problem,
		counterexample=counterexample,
	)

	assert tuple(constraint.constraint_type for constraint in constraints) == (
		"counterexample_nontermination",
		"counterexample_state_coverage",
	)
	diagnostic, companion = constraints
	assert diagnostic.failure_kind == "nontermination"
	assert diagnostic.target_layer == "execution_semantics"
	assert diagnostic.ground_missing_goals == ("a_top(a, b)",)
	assert diagnostic.lifted_missing_goals == ("a_top(X, Y)",)
	assert diagnostic.required_rule_group_types == ("counterexample_nontermination",)
	assert companion.failure_kind == "nontermination_state_coverage"
	assert companion.target_layer == "layer_c_goal_composer"
	assert companion.ground_missing_goals == ("a_top(a, b)",)
	assert companion.lifted_missing_goals == ("a_top(X, Y)",)
	assert companion.required_rule_group_types == ("counterexample_state_coverage",)
	round_report = _refinement_summary_like(constraints)
	assert round_report["nontermination_constraint_count"] == 1
	assert round_report["state_coverage_constraint_count"] == 1
	assert round_report["generative_constraint_count"] == 1
	assert round_report["diagnostic_constraint_count"] == 1
	assert round_report["constraints_by_type"] == {
		"counterexample_nontermination": 1,
		"counterexample_state_coverage": 1,
	}


def _write_ordering_domain(tmp_path: Path) -> tuple[Path, Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	single_goal_problem = tmp_path / "single-goal.pddl"
	dependent_problem = tmp_path / "dependent-goals.pddl"
	domain_file.write_text(
		"""
		(define (domain ordering-mini)
		 (:requirements :strips :typing)
		 (:types object)
		 (:predicates
		  (seed ?x - object)
		  (a_top ?x - object ?y - object)
		  (z_base ?x - object)
		 )
		 (:action make_base
		  :parameters (?x - object)
		  :precondition (seed ?x)
		  :effect (z_base ?x)
		 )
		 (:action make_top
		  :parameters (?x - object ?y - object)
		  :precondition (and (seed ?x) (seed ?y))
		  :effect (and (a_top ?x ?y) (not (seed ?y)))
		 )
		)
		""",
		encoding="utf-8",
	)
	single_goal_problem.write_text(
		"""
		(define (problem single-goal)
		 (:domain ordering-mini)
		 (:objects a b - object)
		 (:init (seed a) (seed b))
		 (:goal (and (a_top a b)))
		)
		""",
		encoding="utf-8",
	)
	dependent_problem.write_text(
		"""
		(define (problem dependent-goals)
		 (:domain ordering-mini)
		 (:objects a b - object)
		 (:init (seed a) (seed b))
		 (:goal (and (z_base b) (a_top a b)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, single_goal_problem, dependent_problem


def _write_precondition_failure_domain(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "precondition-domain.pddl"
	problem_file = tmp_path / "precondition-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain precondition-mini)
		 (:requirements :strips)
		 (:predicates
		  (ready ?x)
		  (armed ?x)
		  (done ?x)
		 )
		 (:action finish
		  :parameters (?x)
		  :precondition (and (ready ?x) (armed ?x))
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem precondition-p1)
		 (:domain precondition-mini)
		 (:objects a)
		 (:init (ready a))
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_precondition_failure_with_satisfied_goal_domain(
	tmp_path: Path,
) -> tuple[Path, Path]:
	domain_file = tmp_path / "precondition-plus-satisfied-domain.pddl"
	problem_file = tmp_path / "precondition-plus-satisfied-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain precondition-plus-satisfied-mini)
		 (:requirements :strips)
		 (:predicates
		  (ready ?x)
		  (armed ?x)
		  (done ?x)
		  (logged ?x)
		 )
		 (:action log
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (logged ?x)
		 )
		 (:action finish
		  :parameters (?x)
		  :precondition (and (ready ?x) (armed ?x))
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem precondition-plus-satisfied-p1)
		 (:domain precondition-plus-satisfied-mini)
		 (:objects a)
		 (:init (ready a))
		 (:goal (and (done a) (logged a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _refinement_summary_like(constraints):
	from domain_level_planning.refinement import CounterexampleGuidedSynthesisResult
	from domain_level_planning.refinement import RefinementRoundReport

	return CounterexampleGuidedSynthesisResult(
		final_result=SimpleNamespace(report={}),
		rounds=(
			RefinementRoundReport(
				round_index=0,
				training_problem_files=(),
				counterexample_problem_files=(),
				heldout_evaluations=(),
				added_counterexample_problem_files=(),
				refinement_constraints=tuple(constraints),
				synthesis_report={},
			),
		),
		converged=False,
	).to_dict()["refinement_summary"]
