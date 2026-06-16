from __future__ import annotations

from pathlib import Path

import pytest

from domain_level_planning import build_goal_conditioned_library_from_pddl
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


def test_pddl_support_report_serializes_rejected_action_costs(tmp_path: Path) -> None:
	domain_file, problem_file = _write_action_costs_domain_and_problem(tmp_path)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["is_compilable"] is False
	assert serialized["unsupported_requirements"] == [":action-costs"]
	assert any(block.endswith("domain.pddl::functions") for block in serialized["unsupported_blocks"])
	assert any(block.endswith("problem.pddl::metric") for block in serialized["unsupported_blocks"])
	assert "increase" in serialized["unsupported_expression_operators"]
	assert {
		"kind": "unsupported_requirement",
		"location": str(domain_file),
		"symbol": ":action-costs",
		"message": "requirement :action-costs has no compiler support",
	} in serialized["unsupported_diagnostics"]
	assert any(
		diagnostic["kind"] == "unsupported_block"
		and diagnostic["symbol"] == ":functions"
		for diagnostic in serialized["unsupported_diagnostics"]
	)
	assert any(
		diagnostic["kind"] == "unsupported_expression_operator"
		and diagnostic["symbol"] == "increase"
		for diagnostic in serialized["unsupported_diagnostics"]
	)
	assert any(":action-costs" in reason for reason in serialized["unsupported_reasons"])
	assert any(":functions" in reason for reason in serialized["unsupported_reasons"])
	assert any(":metric" in reason for reason in serialized["unsupported_reasons"])


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
			"kind": "unsupported_goal_fragment",
			"location": str(problem_file),
			"symbol": ":goal",
			"message": (
				f"{problem_file}: problem goals must be positive achievement goals only "
				"inside a conjunction of predicate atoms"
			),
		},
	]
	assert any(
		"positive achievement goals only" in reason
		for reason in serialized["unsupported_reasons"]
	)


def test_pddl_support_rejects_predicates_outside_current_asl_identifier_subset(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_hyphenated_symbol_domain_and_problem(tmp_path)

	report = inspect_pddl_support(domain_file=domain_file, problem_files=(problem_file,))
	serialized = report.to_dict()

	assert serialized["is_compilable"] is False
	assert {
		"kind": "unsupported_asl_symbol",
		"location": f"{domain_file}:predicate",
		"symbol": "needs-ready",
		"message": (
			f"{domain_file}: PDDL predicate 'needs-ready' is outside the current "
			"AgentSpeak identifier subset"
		),
	} in serialized["unsupported_diagnostics"]
	assert not any(
		diagnostic["kind"] == "unsupported_asl_symbol"
		and diagnostic["location"] == f"{domain_file}:action"
		for diagnostic in serialized["unsupported_diagnostics"]
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
