from __future__ import annotations

from pathlib import Path

from domain_level_planning.atomic_backend_selector import AtomicGoalTemplate
from domain_level_planning.atomic_backend_selector import select_atomic_template_backend


def test_atomic_backend_selector_derives_templates_without_domain_class(
	tmp_path: Path,
) -> None:
	domain_file = _write_domain(tmp_path)
	problem_file = _write_problem(tmp_path, "(done item1)")
	backend_root = tmp_path / "backends"
	_moose_backend(backend_root)

	decision = select_atomic_template_backend(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		backend_root=backend_root,
	)

	assert decision.selected_backend == "moose"
	assert decision.selection_basis == "atomic_singleton_goal_regression"
	assert decision.required_goal_templates == (
		AtomicGoalTemplate(predicate="done", arity=1, polarity="positive"),
	)
	assert decision.input_goal_item_count == 1
	assert decision.rejected_backends == ()


def test_atomic_backend_selector_rejects_negative_goals_without_claiming_support(
	tmp_path: Path,
) -> None:
	domain_file = _write_domain(tmp_path)
	problem_file = _write_problem(tmp_path, "(not (done item1))")
	backend_root = tmp_path / "backends"
	_moose_backend(backend_root)

	decision = select_atomic_template_backend(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		backend_root=backend_root,
	)

	assert decision.selected_backend is None
	assert decision.blocking_gap == "negative_literal_template_not_supported"
	assert decision.required_goal_templates == (
		AtomicGoalTemplate(predicate="done", arity=1, polarity="negative"),
	)


def test_atomic_backend_selector_does_not_fall_back_to_unverified_compiler(
	tmp_path: Path,
) -> None:
	domain_file = _write_domain(tmp_path)
	problem_file = _write_problem(tmp_path, "(done item1)")
	backend_root = tmp_path / "backends"
	_kr_backend(backend_root)

	decision = select_atomic_template_backend(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		backend_root=backend_root,
	)

	assert decision.selected_backend is None
	assert decision.blocking_gap == "no_atomic_template_backend_available"
	assert decision.rejected_backends == (
		{"backend": "moose", "reason": "missing_backend"},
		{
			"backend": "learner-policies-from-examples",
			"reason": "no_verified_atomic_literal_asl_compiler_for_this_backend",
		},
		{"backend": "d2l", "reason": "missing_backend"},
		{"backend": "learner-sketches", "reason": "missing_backend"},
		{"backend": "h-policy-learner", "reason": "missing_backend"},
	)


def _moose_backend(root: Path) -> None:
	moose = root / "moose"
	(moose / ".git").mkdir(parents=True)
	(moose / ".git" / "HEAD").write_text("ce1e99b\n", encoding="utf-8")


def _kr_backend(root: Path) -> None:
	backend = root / "learner-policies-from-examples"
	(backend / ".git").mkdir(parents=True)
	(backend / ".git" / "HEAD").write_text(
		"9991926f7655c4b6c8dc2f0404123639e42056f2\n",
		encoding="utf-8",
	)


def _write_domain(tmp_path: Path) -> Path:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain tiny)
		 (:requirements :strips :typing)
		 (:types item)
		 (:predicates (ready ?x - item) (done ?x - item))
		 (:action finish
		  :parameters (?x - item)
		  :precondition (ready ?x)
		  :effect (and (not (ready ?x)) (done ?x))
		 )
		)
		""",
		encoding="utf-8",
	)
	return domain_file


def _write_problem(tmp_path: Path, goal: str) -> Path:
	problem_file = tmp_path / f"problem-{abs(hash(goal))}.pddl"
	problem_file.write_text(
		f"""
		(define (problem tiny-problem)
		 (:domain tiny)
		 (:objects item1 - item)
		 (:init (ready item1))
		 (:goal {goal})
		)
		""",
		encoding="utf-8",
	)
	return problem_file
