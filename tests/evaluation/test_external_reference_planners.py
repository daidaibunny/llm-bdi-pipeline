from __future__ import annotations

from pathlib import Path

import pytest

from evaluation.external_reference_planners import ExternalReferenceMethod
from evaluation.external_reference_planners import build_enhsp_command
from evaluation.external_reference_planners import build_fond4ltlf_command
from evaluation.external_reference_planners import build_ground_fond4ltlf_formula
from evaluation.external_reference_planners import filter_compilation_actions
from evaluation.external_reference_planners import normalize_fond4ltlf_domain
from evaluation.external_reference_planners import reference_methods_for_domain


def test_reference_methods_use_short_paper_names() -> None:
	assert ExternalReferenceMethod.RAW_MOOSE.display_name == "Raw MOOSE"
	assert ExternalReferenceMethod.LAMA.display_name == "LAMA"
	assert ExternalReferenceMethod.ENHSP_HMRPHJ.display_name == "MRP+HJ"
	assert ExternalReferenceMethod.FOND4LTLF_LAMA.display_name == "FOND4LTLf + LAMA"


def test_reference_methods_follow_domain_features_not_domain_names(tmp_path: Path) -> None:
	classical_domain = tmp_path / "arbitrary-classical.pddl"
	classical_domain.write_text(
		"""
(define (domain renamed)
 (:requirements :strips)
 (:predicates (ready))
 (:action make-ready
  :parameters ()
  :precondition (and)
  :effect (ready)))
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	numeric_domain = tmp_path / "arbitrary-numeric.pddl"
	numeric_domain.write_text(
		"""
(define (domain renamed-numeric)
 (:requirements :strips :numeric-fluents)
 (:predicates (ready))
 (:functions (fuel))
 (:action consume
  :parameters ()
  :precondition (> (fuel) 0)
  :effect (decrease (fuel) 1)))
""".strip()
		+ "\n",
		encoding="utf-8",
	)

	assert reference_methods_for_domain(classical_domain) == (
		ExternalReferenceMethod.RAW_MOOSE,
		ExternalReferenceMethod.LAMA,
	)
	assert reference_methods_for_domain(numeric_domain) == (
		ExternalReferenceMethod.RAW_MOOSE,
		ExternalReferenceMethod.ENHSP_HMRPHJ,
	)


def test_enhsp_command_uses_moose_paper_configuration(tmp_path: Path) -> None:
	command = build_enhsp_command(
		jar_file=tmp_path / "enhsp.jar",
		domain_file=tmp_path / "domain.pddl",
		problem_file=tmp_path / "problem.pddl",
		plan_file=tmp_path / "plan.txt",
	)

	assert command == (
		"java",
		"-jar",
		str(tmp_path / "enhsp.jar"),
		"-o",
		str(tmp_path / "domain.pddl"),
		"-f",
		str(tmp_path / "problem.pddl"),
		"-sp",
		str(tmp_path / "plan.txt"),
		"-planner",
		"sat-hmrphj",
	)


def test_fond4ltlf_command_uses_native_compiler_outputs(tmp_path: Path) -> None:
	command = build_fond4ltlf_command(
		executable=tmp_path / "fond4ltlf",
		domain_file=tmp_path / "domain.pddl",
		problem_file=tmp_path / "problem.pddl",
		formula="F(at_box1_room2)",
		output_domain_file=tmp_path / "compiled-domain.pddl",
		output_problem_file=tmp_path / "compiled-problem.pddl",
	)

	assert command == (
		str(tmp_path / "fond4ltlf"),
		"-d",
		str(tmp_path / "domain.pddl"),
		"-p",
		str(tmp_path / "problem.pddl"),
		"-g",
		"F(at_box1_room2)",
		"-outd",
		str(tmp_path / "compiled-domain.pddl"),
		"-outp",
		str(tmp_path / "compiled-problem.pddl"),
	)


def test_ground_formula_uses_explicit_invocation_binding() -> None:
	case = {
		"ltlf_formula": "F(a0 & X(F(a1)))",
		"bindings": {"X": "box1", "Y": "room2"},
		"atoms": [
			{"symbol": "a0", "kind": "predicate", "predicate": "holding", "args": ["X"]},
			{"symbol": "a1", "kind": "predicate", "predicate": "at", "args": ["X", "Y"]},
		],
	}

	assert build_ground_fond4ltlf_formula(case) == (
		"F(holding_box1 & X(F(at_box1_room2)))"
	)


def test_ground_formula_rejects_numeric_and_ambiguous_symbol_names() -> None:
	with pytest.raises(ValueError, match="numeric"):
		build_ground_fond4ltlf_formula(
			{
				"ltlf_formula": "F(a0)",
				"bindings": {},
				"atoms": [
					{
						"symbol": "a0",
						"kind": "numeric_equality",
						"function": "fuel",
						"args": [],
						"value": 0,
					},
				],
			},
		)
	with pytest.raises(ValueError, match="identifier"):
		build_ground_fond4ltlf_formula(
			{
				"ltlf_formula": "F(a0)",
				"bindings": {"X": "room-1"},
				"atoms": [
					{
						"symbol": "a0",
						"kind": "predicate",
						"predicate": "at",
						"args": ["X"],
					},
				],
			},
		)


def test_fond4ltlf_requirement_normalization_is_semantics_preserving() -> None:
	domain = """
(define (domain d)
 (:requirements :strips :typing :negative-preconditions)
 (:types thing)
 (:predicates (p ?x - thing))
 (:action a
  :parameters (?x - thing)
  :precondition (not (p ?x))
  :effect (p ?x)))
""".strip()

	normalized = normalize_fond4ltlf_domain(domain)

	assert ":negative-preconditions" not in normalized
	assert "(:requirements :strips :typing :adl)" in normalized
	assert ":precondition (not (p ?x))" in normalized


def test_fond4ltlf_requirement_normalization_ignores_comment_text() -> None:
	domain = """
; source path includes (:requirements :fake) but is not PDDL syntax
(define (domain d)
 (:requirements :strips :negative-preconditions)
 (:predicates (p))
 (:action a :parameters () :precondition (not (p)) :effect (p)))
""".strip()

	normalized = normalize_fond4ltlf_domain(domain)

	assert normalized.startswith(
		"; source path includes (:requirements :fake) but is not pddl syntax",
	)
	assert "(:requirements :strips :adl)" in normalized
	assert ":negative-preconditions" not in normalized.splitlines()[2]


def test_fond4ltlf_requirement_normalization_rejects_numeric_pddl() -> None:
	with pytest.raises(ValueError, match="numeric"):
		normalize_fond4ltlf_domain(
			"(define (domain d) (:requirements :strips :numeric-fluents))",
		)


def test_fond4ltlf_normalization_removes_unused_action_cost_declaration() -> None:
	domain = """
(define (domain cost-free)
 (:requirements :action-costs :strips :typing)
 (:types thing)
 (:predicates (ready ?x - thing))
 (:action prepare
  :parameters (?x - thing)
  :precondition (and)
  :effect (ready ?x)))
""".strip()

	normalized = normalize_fond4ltlf_domain(domain)

	assert ":action-costs" not in normalized
	assert "(:requirements :strips :typing)" in normalized
	assert ":effect (ready ?x)" in normalized


def test_compilation_actions_are_removed_without_reordering_domain_actions() -> None:
	compiled_plan = """
(move box1 room1 room2)
(trans-0 box1 room2)
(pick box1 room2)
(trans-1 box1 room2)
"""

	assert filter_compilation_actions(
		compiled_plan,
		original_action_names={"move", "pick"},
	) == (
		"(move box1 room1 room2)",
		"(pick box1 room2)",
	)


def test_compilation_action_filter_fails_on_unknown_actions() -> None:
	with pytest.raises(ValueError, match="unknown action"):
		filter_compilation_actions(
			"(move box1 room1 room2)\n(mystery box1)\n",
			original_action_names={"move"},
		)
