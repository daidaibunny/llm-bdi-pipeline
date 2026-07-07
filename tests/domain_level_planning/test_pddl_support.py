from __future__ import annotations

from pathlib import Path

import pytest

from domain_level_planning.pddl_support import assert_compilable_pddl_files
from domain_level_planning.pddl_support import inspect_pddl_support


def test_compilable_pddl_support_accepts_strips_domain_and_problem(tmp_path: Path) -> None:
	domain_file, problem_file = _write_minimal_strips_domain_and_problem(tmp_path)

	assert_compilable_pddl_files(domain_file=domain_file, problem_files=(problem_file,))


def test_pddl_support_report_serializes_supported_fragment(tmp_path: Path) -> None:
	domain_file, problem_file = _write_minimal_strips_domain_and_problem(tmp_path)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["domain_file"] == str(domain_file)
	assert serialized["problem_files"] == [str(problem_file)]
	assert serialized["requirements"] == [":strips", ":typing"]
	assert serialized["supported_requirements"] == [":strips", ":typing"]
	assert serialized["unsupported_requirements"] == []
	assert serialized["unsupported_blocks"] == []
	assert serialized["unsupported_expression_operators"] == []
	assert serialized["unsupported_reasons"] == []
	assert serialized["is_compilable"] is True
	assert ":strips" in serialized["supported_requirement_set"]
	assert ":conditional-effects" in serialized["known_unsupported_requirement_set"]
	assert any(
		"positive conjunctive predicate achievement goals" in assumption
		for assumption in serialized["fragment_assumptions"]
	)


def test_pddl_support_report_accepts_metric_only_action_costs(tmp_path: Path) -> None:
	domain_file, problem_file = _write_action_costs_domain_and_problem(tmp_path)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["is_compilable"] is True
	assert serialized["unsupported_requirements"] == []
	assert serialized["unsupported_blocks"] == []
	assert serialized["unsupported_expression_operators"] == []
	assert serialized["unsupported_reasons"] == []
	assert ":action-costs" in serialized["supported_requirement_set"]


def test_pddl_support_accepts_bounded_integer_numeric_resource_fragment(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_numeric_resource_domain_and_problem(tmp_path)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["is_compilable"] is True
	assert serialized["unsupported_requirements"] == []
	assert serialized["unsupported_expression_operators"] == []
	assert serialized["logical_numeric_functions"] == ["capacity"]
	assert serialized["metric_only_numeric_functions"] == []
	assert any(
		"bounded integer numeric resource fluents" in assumption
		for assumption in serialized["fragment_assumptions"]
	)


def test_pddl_support_accepts_bounded_integer_numeric_equality_goal(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_numeric_resource_domain_and_problem(
		tmp_path,
		goal="(= (capacity truck1) 0)",
	)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["is_compilable"] is True
	assert serialized["unsupported_diagnostics"] == []
	assert any(
		"bounded integer numeric equality goals" in assumption
		for assumption in serialized["fragment_assumptions"]
	)


def test_pddl_support_rejects_non_integer_numeric_goal(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_numeric_resource_domain_and_problem(
		tmp_path,
		goal="(= (capacity truck1) 0.5)",
	)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["is_compilable"] is False
	assert {
		"kind": "unsupported_numeric_goal",
		"location": str(problem_file),
		"symbol": "=",
		"message": (
			f"{problem_file}: numeric problem goals must be equality between one "
			"declared numeric fluent and one integer constant in the supported "
			"bounded resource fragment"
		),
	} in serialized["unsupported_diagnostics"]


def test_pddl_support_rejects_non_constant_numeric_effect_amount(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_numeric_resource_domain_and_problem(
		tmp_path,
		effect_amount="(weight package1)",
	)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["is_compilable"] is False
	assert any(
		"numeric effects must increase or decrease by integer constants" in reason
		for reason in serialized["unsupported_reasons"]
	)


def test_pddl_support_rejects_arbitrary_numeric_effect_expression(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_numeric_resource_domain_and_problem(
		tmp_path,
		effect_amount="(+ 1 1)",
	)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["is_compilable"] is False
	assert "+" in serialized["unsupported_expression_operators"]
	assert {
		"kind": "unsupported_expression_operator",
		"location": str(domain_file),
		"symbol": "+",
		"message": f"{domain_file}: Unsupported PDDL expression operator '+'",
	} in serialized["unsupported_diagnostics"]


def test_pddl_support_accepts_forward_referenced_type_parents(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_forward_referenced_type_domain_and_problem(
		tmp_path,
	)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["is_compilable"] is True
	assert serialized["unsupported_reasons"] == []


def test_compilable_pddl_support_rejects_conditional_effects(tmp_path: Path) -> None:
	domain_file, problem_file = _write_minimal_strips_domain_and_problem(
		tmp_path,
		requirements=":strips :conditional-effects",
		effect="(and (when (ready ?x) (done ?x)))",
	)

	with pytest.raises(ValueError, match="conditional-effects"):
		assert_compilable_pddl_files(domain_file=domain_file, problem_files=(problem_file,))


def test_pddl_support_report_rejects_disjunctive_problem_goals(tmp_path: Path) -> None:
	domain_file, problem_file = _write_minimal_strips_domain_and_problem(
		tmp_path,
		goal="(or (done a) (ready a))",
	)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()
	assert serialized["is_compilable"] is False
	assert {
		"kind": "unsupported_disjunctive_goal",
		"location": str(problem_file),
		"symbol": "or",
		"message": (
			f"{problem_file}: disjunctive problem goals are not supported; "
			"supported goals are positive achievement goals only: predicate atoms "
			"optionally inside an and conjunction"
		),
	} in serialized["unsupported_diagnostics"]


def test_pddl_support_report_rejects_negative_problem_goals(tmp_path: Path) -> None:
	domain_file, problem_file = _write_minimal_strips_domain_and_problem(
		tmp_path,
		goal="(and (not (done a)))",
	)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["is_compilable"] is False
	assert serialized["unsupported_diagnostics"] == [
		{
			"kind": "unsupported_negative_goal",
			"location": str(problem_file),
			"symbol": "not",
			"message": (
				f"{problem_file}: negative problem goals are not supported; "
				"supported goals are positive achievement goals only: predicate atoms "
				"optionally inside an and conjunction"
			),
		},
	]
	assert any(
		"negative problem goals are not supported" in reason
		for reason in serialized["unsupported_reasons"]
	)


def test_pddl_support_accepts_hyphenated_symbols_when_rendering_is_unambiguous(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_hyphenated_symbol_domain_and_problem(tmp_path)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["is_compilable"] is True
	assert serialized["unsupported_diagnostics"] == []


def test_pddl_support_rejects_action_symbols_that_collide_after_asl_rendering(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_colliding_action_symbol_domain_and_problem(tmp_path)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["is_compilable"] is False
	assert {
		"kind": "unsupported_asl_symbol_collision",
		"location": f"{domain_file}:action",
		"symbol": "make_done",
		"message": (
			f"{domain_file}: PDDL action symbols ('make-done', 'make_done') "
			"collapse to the same AgentSpeak functor 'make_done'"
		),
	} in serialized["unsupported_diagnostics"]
	assert any(
		"collapse to the same AgentSpeak functor" in reason
		for reason in serialized["unsupported_reasons"]
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


def _write_numeric_resource_domain_and_problem(
	tmp_path: Path,
	*,
	goal: str = "(and (at package1 depot2))",
	effect_amount: str = "1",
) -> tuple[Path, Path]:
	domain_file = tmp_path / "numeric-domain.pddl"
	problem_file = tmp_path / "numeric-problem.pddl"
	domain_file.write_text(
		f"""
		(define (domain numeric-transport)
		 (:requirements :strips :typing :numeric-fluents)
		 (:types location vehicle package)
		 (:predicates
		  (at ?x ?l - location)
		  (in ?p - package ?v - vehicle)
		 )
		 (:functions
		  (capacity ?v - vehicle)
		  (weight ?p - package)
		 )
		 (:action pick-up
		  :parameters (?v - vehicle ?p - package ?l - location)
		  :precondition (and (at ?v ?l) (at ?p ?l) (>= (capacity ?v) 1))
		  :effect (and
		   (not (at ?p ?l))
		   (in ?p ?v)
		   (decrease (capacity ?v) {effect_amount})
		  )
		 )
		 (:action drop
		  :parameters (?v - vehicle ?p - package ?l - location)
		  :precondition (and (at ?v ?l) (in ?p ?v))
		  :effect (and
		   (not (in ?p ?v))
		   (at ?p ?l)
		   (increase (capacity ?v) 1)
		  )
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		f"""
		(define (problem numeric-p1)
		 (:domain numeric-transport)
		 (:objects truck1 - vehicle package1 - package depot1 depot2 - location)
		 (:init
		  (= (capacity truck1) 1)
		  (= (weight package1) 1)
		  (at truck1 depot1)
		  (at package1 depot1)
		 )
		 (:goal {goal})
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_colliding_action_symbol_domain_and_problem(
	tmp_path: Path,
) -> tuple[Path, Path]:
	domain_file = tmp_path / "collision-domain.pddl"
	problem_file = tmp_path / "collision-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain action-collision)
		 (:requirements :strips)
		 (:predicates
		  (ready)
		  (done)
		 )
		 (:action make-done
		  :parameters ()
		  :precondition (ready)
		  :effect (done)
		 )
		 (:action make_done
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
		(define (problem action-collision-p1)
		 (:domain action-collision)
		 (:objects)
		 (:init (ready))
		 (:goal (and (done)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_hyphenated_symbol_domain_and_problem(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "hyphen-domain.pddl"
	problem_file = tmp_path / "hyphen-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain hyphen-symbols)
		 (:requirements :strips)
		 (:predicates
		  (needs-ready ?x)
		  (done ?x)
		 )
		 (:action make-done
		  :parameters (?x)
		  :precondition (needs-ready ?x)
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p1)
		 (:domain hyphen-symbols)
		 (:objects a)
		 (:init (needs-ready a))
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_forward_referenced_type_domain_and_problem(
	tmp_path: Path,
) -> tuple[Path, Path]:
	domain_file = tmp_path / "forward-type-domain.pddl"
	problem_file = tmp_path / "forward-type-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain forward-types)
		 (:requirements :strips :typing)
		 (:types truck airplane - vehicle package vehicle - physobj physobj - object)
		 (:predicates
		  (at ?x - physobj)
		  (loaded ?p - package ?v - vehicle)
		 )
		 (:action load
		  :parameters (?p - package ?v - vehicle)
		  :precondition (at ?p)
		  :effect (loaded ?p ?v)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p1)
		 (:domain forward-types)
		 (:objects p0 - package t0 - truck)
		 (:init (at p0) (at t0))
		 (:goal (and (loaded p0 t0)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_action_costs_domain_and_problem(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain costs)
		 (:requirements :strips :action-costs)
		 (:predicates
		  (ready)
		  (done)
		 )
		 (:functions (total-cost))
		 (:action finish
		  :parameters ()
		  :precondition (ready)
		  :effect (and (done) (increase (total-cost) 1))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem p1)
		 (:domain costs)
		 (:init (ready) (= (total-cost) 0))
		 (:goal (done))
		 (:metric minimize (total-cost))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file
