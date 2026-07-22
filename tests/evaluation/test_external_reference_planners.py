from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.external_reference_planners import ExternalReferenceMethod
from evaluation.external_reference_planners import build_enhsp_command
from evaluation.external_reference_planners import build_fond4ltlf_command
from evaluation.external_reference_planners import build_ground_fond4ltlf_formula
from evaluation.external_reference_planners import build_tide_command
from evaluation.external_reference_planners import build_tide_pddl_goal
from evaluation.external_reference_planners import ensure_tide_domain_compatible
from evaluation.external_reference_planners import extract_tide_plan_actions
from evaluation.external_reference_planners import filter_compilation_actions
from evaluation.external_reference_planners import normalize_fond4ltlf_domain
from evaluation.external_reference_planners import parse_tide_statistics
from evaluation.external_reference_planners import reference_methods_for_domain
from evaluation.external_reference_planners import normalize_tide_pddl_task
from evaluation.external_reference_planners import rewrite_pddl_problem_goal


def test_reference_methods_use_short_paper_names() -> None:
	assert ExternalReferenceMethod.RAW_MOOSE.display_name == "Raw MOOSE"
	assert ExternalReferenceMethod.LAMA.display_name == "LAMA"
	assert ExternalReferenceMethod.ENHSP_HMRPHJ.display_name == "MRP+HJ"
	assert ExternalReferenceMethod.FOND4LTLF_LAMA.display_name == "FOND4LTLf + LAMA"
	assert ExternalReferenceMethod.TIDE_LAMA.display_name == "TIDE + LAMA"


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


def test_tide_goal_renderer_preserves_strong_next_and_until() -> None:
	atoms = [
		{"symbol": "a0", "kind": "predicate", "predicate": "clear", "args": ["X"]},
		{"symbol": "a1", "kind": "predicate", "predicate": "on", "args": ["X", "Y"]},
		{"symbol": "a2", "kind": "predicate", "predicate": "on", "args": ["Z", "X"]},
	]

	assert build_tide_pddl_goal(
		ltlf_formula="a0 U F(a1 & X(a2))",
		atoms=atoms,
		bindings={"X": "b2", "Y": "b3", "Z": "b1"},
	) == (
		"(until (clear b2) "
		"(eventually (and (on b2 b3) (next (on b1 b2)))))"
	)


def test_tide_goal_renderer_rejects_numeric_atoms() -> None:
	with pytest.raises(ValueError, match="numeric"):
		build_tide_pddl_goal(
			ltlf_formula="a0",
			atoms=[
				{
					"symbol": "a0",
					"kind": "numeric_equality",
					"function": "fuel",
					"arguments": [],
					"value": 0,
				},
			],
			bindings={},
		)


def test_tide_goal_renderer_rejects_nonliteral_negation() -> None:
	with pytest.raises(ValueError, match="negation on literals only"):
		build_tide_pddl_goal(
			ltlf_formula="!(F(a0))",
			atoms=[
				{
					"symbol": "a0",
					"kind": "predicate",
					"predicate": "ready",
					"arguments": [],
				},
			],
			bindings={},
		)


def test_tide_domain_capability_rejects_resource_numeric_fluents() -> None:
	with pytest.raises(ValueError, match="numeric PDDL"):
		ensure_tide_domain_compatible(
			"""
(define (domain numeric)
 (:requirements :strips :numeric-fluents)
 (:predicates (ready))
 (:functions (fuel))
 (:action consume
  :parameters ()
  :precondition (> (fuel) 0)
  :effect (decrease (fuel) 1)))
""".strip(),
		)


def test_tide_problem_rewrite_replaces_only_goal_block() -> None:
	problem = """
(define (problem p)
 (:domain d)
 (:objects b1 b2)
 (:init (clear b1))
 (:goal (and (clear b2))))
""".strip()

	rewritten = rewrite_pddl_problem_goal(
		problem,
		"(eventually (on b1 b2))",
	)

	assert "(:init (clear b1))" in rewritten
	assert "(:goal (eventually (on b1 b2)))" in rewritten
	assert "(:goal (and (clear b2)))" not in rewritten


def test_tide_command_uses_official_feedback_heuristic_cache_configuration() -> None:
	assert build_tide_command(
		executable="/app/bin/main_single",
		domain_file="/work/domain.pddl",
		problem_file="/work/problem.pddl",
		subproblem_timeout_ms=60_000,
	) == (
		"/app/bin/main_single",
		"/work/domain.pddl",
		"/work/problem.pddl",
		"1",
		"-f",
		"-h",
		"-c",
		"--planner",
		"fd",
		"--search",
		"lama-first",
		"--timeout",
		"60000",
	)


def test_tide_plan_parser_extracts_only_primitive_plan_section() -> None:
	artifact = """
Plan:
(unstack b1 b2)
(put-down b1)

DFA Path:
1 -> 2 -> 3

Product Path:
diagnostic state text
""".strip()

	assert extract_tide_plan_actions(artifact) == (
		"(unstack b1 b2)",
		"(put-down b1)",
	)


def test_tide_normalization_is_type_ordered_and_delimiter_safe() -> None:
	domain = """
(define (domain arbitrary-domain)
 (:requirements :strips :typing)
 (:types child - parent parent - object)
 (:predicates (arm-empty) (on-table ?x - child))
 (:action put-down
  :parameters (?x - child)
  :precondition (arm-empty)
  :effect (on-table ?x)))
""".strip()
	problem = """
(define (problem arbitrary-problem)
 (:domain arbitrary-domain)
 (:objects room-a - child)
 (:init (arm-empty))
 (:goal (and)))
""".strip()

	normalized = normalize_tide_pddl_task(
		domain_text=domain,
		problem_text=problem,
		temporal_goal="(eventually (on-table room-a))",
	)

	parent = "gp2plt706172656e74"
	child = "gp2plt6368696c64"
	arm_empty = "gp2plp_61726d2d656d707479"
	on_table = "gp2plp_6f6e2d7461626c65"
	room_a = "gp2plo726f6f6d2d61"
	assert f"(:types {parent} - object {child} - {parent})" in normalized.domain_text
	assert f"({arm_empty})" in normalized.domain_text
	assert f"({on_table} ?gp2plv78 - {child})" in normalized.domain_text
	assert f":parameters (?gp2plv78 - {child})" in normalized.domain_text
	assert f"(:objects {room_a} - {child})" in normalized.problem_text
	assert f"(:goal (eventually ({on_table} {room_a})))" in normalized.problem_text
	assert normalized.temporal_goal == f"(eventually ({on_table} {room_a}))"


def test_tide_normalization_distinguishes_temporal_next_from_next_predicate() -> None:
	domain = """
(define (domain operator-collision)
 (:requirements :strips :typing)
 (:types level item)
 (:predicates
  (next ?from - level ?to - level)
  (holding ?item - item))
 (:action advance
  :parameters (?from - level ?to - level ?item - item)
  :precondition (and (next ?from ?to) (holding ?item))
  :effect (holding ?item)))
""".strip()
	problem = """
(define (problem operator-collision-1)
 (:domain operator-collision)
 (:objects l0 l1 - level shaker - item)
 (:init (next l0 l1))
 (:goal (and)))
""".strip()

	normalized = normalize_tide_pddl_task(
		domain_text=domain,
		problem_text=problem,
		temporal_goal="(eventually (next (eventually (holding shaker))))",
	)

	next_predicate = "gp2plp_6e657874"
	assert f"({next_predicate} ?gp2plv66726f6d" in normalized.domain_text
	assert f"({next_predicate} gp2plo6c30 gp2plo6c31)" in normalized.problem_text
	assert "(next (eventually" in normalized.temporal_goal
	assert f"({next_predicate} (eventually" not in normalized.temporal_goal


def test_tide_plan_parser_decodes_normalized_action_and_object_names() -> None:
	artifact = """
Plan:
(gp2pla7075742d646f776e gp2plo726f6f6d2d61)

DFA Path:
1 -> 2
""".strip()

	assert extract_tide_plan_actions(
		artifact,
		decode_normalized_symbols=True,
	) == ("(put-down room-a)",)


def test_tide_normalization_preserves_metric_only_total_cost() -> None:
	normalized = normalize_tide_pddl_task(
		domain_text="""
(define (domain costed)
 (:requirements :strips :action-costs)
 (:predicates (ready))
 (:functions (total-cost) - number)
 (:action prepare
  :parameters ()
  :precondition (and)
  :effect (and (ready) (increase (total-cost) 1))))
""".strip(),
		problem_text="""
(define (problem costed-1)
 (:domain costed)
 (:objects)
 (:init (= (total-cost) 0))
 (:goal (and))
 (:metric minimize (total-cost)))
""".strip(),
		temporal_goal="(eventually (ready))",
	)

	assert "(:functions (total-cost) - number)" in normalized.domain_text
	assert "(increase (total-cost) 1)" in normalized.domain_text
	assert "(:metric minimize (total-cost))" in normalized.problem_text


def test_tide_statistics_parser_preserves_search_diagnostics() -> None:
	statistics = parse_tide_statistics(
		"""
For 1 runs:
Average DFA construction time: 0.25 seconds
First DFA construction time: 0.25 seconds
Average DFA construction time (without first): 0 seconds
Average search time: 1.5 seconds
Average total time: 1.75 seconds
Average number of expanded nodes: 42
Average plan length: 3
Average number of backtracks: 2
""".strip(),
	)

	assert statistics == {
		"average_dfa_seconds": 0.25,
		"average_search_seconds": 1.5,
		"average_total_seconds": 1.75,
		"average_expanded_nodes": 42.0,
		"average_plan_length": 3.0,
		"average_backtracks": 2.0,
	}


def test_tide_adapter_covers_frozen_boolean_temporal_benchmark() -> None:
	project_root = Path(__file__).resolve().parents[2]
	benchmark = json.loads(
		(
			project_root
			/ "paper_artifacts/temporal_goal_benchmark/v1/benchmark.json"
		).read_text(encoding="utf-8"),
	)
	supported = 0
	unsupported_numeric = 0
	for domain_name, domain_record in benchmark["domains"].items():
		domain_text = (
			project_root / "src/domains" / domain_name / "domain.pddl"
		).read_text(encoding="utf-8")
		try:
			ensure_tide_domain_compatible(domain_text)
		except ValueError as error:
			assert "numeric PDDL" in str(error)
			unsupported_numeric += len(domain_record["cases"])
			continue
		for case in domain_record["cases"].values():
			goal = build_tide_pddl_goal(
				ltlf_formula=case["ltlf_formula"],
				atoms=case["atoms"],
				bindings=case["bindings"],
			)
			assert goal.startswith("(") and goal.endswith(")")
			normalized = normalize_tide_pddl_task(
				domain_text=domain_text,
				problem_text=(project_root / case["problem_file"]).read_text(
					encoding="utf-8",
				),
				temporal_goal=goal,
			)
			assert "gp2plp_" in normalized.problem_text
			supported += 1

	assert supported == 868
	assert unsupported_numeric == 360
