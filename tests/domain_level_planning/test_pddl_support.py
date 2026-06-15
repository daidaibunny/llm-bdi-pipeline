from __future__ import annotations

from pathlib import Path

import pytest

from domain_level_planning import build_goal_conditioned_library_from_pddl
from domain_level_planning.pddl_support import assert_compilable_pddl_files


def test_compilable_pddl_support_accepts_strips_domain_and_problem(tmp_path: Path) -> None:
	domain_file, problem_file = _write_minimal_strips_domain_and_problem(tmp_path)

	assert_compilable_pddl_files(domain_file=domain_file, problem_files=(problem_file,))


def test_compilable_pddl_support_rejects_conditional_effects(tmp_path: Path) -> None:
	domain_file, problem_file = _write_minimal_strips_domain_and_problem(
		tmp_path,
		requirements=":strips :conditional-effects",
		effect="(and (when (ready ?x) (done ?x)))",
	)

	with pytest.raises(ValueError, match="conditional-effects"):
		assert_compilable_pddl_files(domain_file=domain_file, problem_files=(problem_file,))


def test_schema_synthesis_rejects_disjunctive_problem_goals(tmp_path: Path) -> None:
	domain_file, problem_file = _write_minimal_strips_domain_and_problem(
		tmp_path,
		goal="(or (done a) (ready a))",
	)

	with pytest.raises(ValueError, match="Unsupported PDDL expression operator 'or'"):
		build_goal_conditioned_library_from_pddl(
			domain_file=domain_file,
			training_problem_files=(problem_file,),
		)


def _write_minimal_strips_domain_and_problem(
	tmp_path: Path,
	*,
	requirements: str = ":strips :typing",
	effect: str = "(done ?x)",
	goal: str = "(and (done a))",
) -> tuple[Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		f"""
		(define (domain generic)
		 (:requirements {requirements})
		 (:types item)
		 (:predicates
		  (ready ?x - item)
		  (done ?x - item)
		 )
		 (:action finish
		  :parameters (?x - item)
		  :precondition (ready ?x)
		  :effect {effect}
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		f"""
		(define (problem p1)
		 (:domain generic)
		 (:objects a - item)
		 (:init (ready a))
		 (:goal {goal})
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file
