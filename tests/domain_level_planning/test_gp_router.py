from __future__ import annotations

from pathlib import Path

from domain_level_planning.atomic_backend_selector import select_atomic_template_backend


def test_atomic_backend_selection_does_not_depend_on_legacy_class_labels(
	tmp_path: Path,
) -> None:
	"""Regression guard for the 2026-07-03 architecture pivot."""

	root = tmp_path / "backends"
	moose = root / "moose"
	moose.mkdir(parents=True)
	(moose / ".git").mkdir()

	domain_file, problem_file = _write_singleton_goal_case(tmp_path)
	decision = select_atomic_template_backend(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		backend_root=root,
	)

	assert decision.selected_backend == "moose"
	assert decision.selection_basis == "atomic_singleton_goal_regression"
	assert decision.required_goal_templates[0].predicate == "done"
	assert decision.required_goal_templates[0].arity == 1


def test_atomic_backend_selection_reports_negative_literal_gap(tmp_path: Path) -> None:
	root = tmp_path / "backends"
	(root / "moose" / ".git").mkdir(parents=True)
	domain_file, problem_file = _write_negative_goal_case(tmp_path)

	decision = select_atomic_template_backend(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		backend_root=root,
	)

	assert decision.selected_backend is None
	assert decision.blocking_gap == "negative_literal_template_not_supported"


def _write_singleton_goal_case(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain singleton-template-mini)
		 (:requirements :strips)
		 (:predicates (done ?x))
		 (:action finish
		  :parameters (?x)
		  :precondition (and)
		  :effect (done ?x))
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem singleton-template-p1)
		 (:domain singleton-template-mini)
		 (:objects a)
		 (:init)
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_negative_goal_case(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "negative-domain.pddl"
	problem_file = tmp_path / "negative-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain negative-template-mini)
		 (:requirements :strips)
		 (:predicates (done ?x))
		 (:action clear
		  :parameters (?x)
		  :precondition (done ?x)
		  :effect (not (done ?x)))
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem negative-template-p1)
		 (:domain negative-template-mini)
		 (:objects a)
		 (:init (done a))
		 (:goal (and (not (done a))))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file
