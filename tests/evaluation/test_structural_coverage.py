from fractions import Fraction
import pytest


def test_exact_context_counting_distinguishes_sum_union_and_overlap():
	from evaluation.structural_coverage import BooleanContext, count_contexts
	result = count_contexts((BooleanContext(frozenset({"p"})),
		BooleanContext(frozenset({"q"}))))
	assert result.basic == (Fraction(1, 2), Fraction(1, 2))
	assert result.raw_sum == 1
	assert result.union == Fraction(3, 4)
	assert result.overlap == Fraction(1, 4)


def test_ground_context_can_depend_on_aliasing_and_never_assumes_independence():
	from evaluation.structural_coverage import BooleanContext, count_contexts
	aliased = BooleanContext(frozenset({"p(a)"}), frozenset({"p(a)"}))
	distinct = BooleanContext(frozenset({"p(a)"}), frozenset({"p(b)"}))
	result = count_contexts((aliased, distinct))
	assert result.basic == (0, Fraction(1, 4))
	assert result.union == Fraction(1, 4)
	duplicate = count_contexts((BooleanContext(), BooleanContext(), BooleanContext()))
	assert duplicate.raw_sum == 3
	assert duplicate.union == duplicate.overlap == 1


def test_literal_extended_equations_are_exact_but_do_not_fix_overlap():
	from evaluation.structural_coverage import (
		BooleanContext, StructuralPlan, extended_coverage,
	)
	graph = {
		"g": (StructuralPlan(BooleanContext(), ("h",)),),
		"h": (StructuralPlan(BooleanContext(frozenset({"p"}))),
			StructuralPlan(BooleanContext(frozenset({"q"})))),
	}
	assert extended_coverage(graph, "g", overlap="literal_sum") == 1
	assert extended_coverage(graph, "g", overlap="partition_max") == Fraction(3, 4)


def test_cycles_have_no_silent_truncation_or_assumed_fixed_point():
	from evaluation.structural_coverage import (
		BooleanContext, StructuralPlan, UndefinedCoverage, extended_coverage,
	)
	graph = {"g": (StructuralPlan(BooleanContext(), ("g",)),)}
	for mode in ("literal_sum", "partition_max"):
		with pytest.raises(UndefinedCoverage, match="fixed-point"):
			extended_coverage(graph, "g", overlap=mode)


def test_waters_2014_figure_one_is_nineteen_over_thirty_two():
	from evaluation.structural_coverage import BooleanContext as C
	from evaluation.structural_coverage import StructuralPlan as P, extended_coverage
	graph = {
		"G1": (P(C(frozenset({"A"})), ("G2", "G3")),
			P(C(negative=frozenset({"A"})), ("G4",))),
		"G2": (P(C(frozenset({"B"}))),),
		# The two disjunctive leaf contexts expand to cubes with identical weight.
		"G3": tuple(P(C(frozenset({x}))) for x in ("C", "D", "D", "E")),
		"G4": (P(C(frozenset({"D", "E"}))),
			P(C(frozenset({"D"}), frozenset({"E"}))),
			P(C(frozenset({"E"}), frozenset({"D"})))),
	}
	assert extended_coverage(graph, "G1", overlap="partition_max") == Fraction(19, 32)


def test_grounding_keeps_types_fixed_but_counts_world_atoms_symbolically(tmp_path):
	from evaluation.coverage_model import PDDLExecutionModel
	from evaluation.structural_coverage import ground_boolean_context, count_contexts
	from plan_library.models import PlanLibrary
	domain = tmp_path / "domain.pddl"
	problem = tmp_path / "problem.pddl"
	domain.write_text("""(define (domain test) (:requirements :strips :typing)
	 (:types item - object) (:predicates (p ?x - item)))""")
	problem.write_text("""(define (problem p) (:domain test)
	 (:objects a b - item) (:init (p a)) (:goal (p b)))""")
	model = PDDLExecutionModel(domain, problem, PlanLibrary.from_dict({"plans": []}))
	context = ("p(X)", "not p(Y)", "obj_tp(X, item)")
	x = ground_boolean_context(context, {"X": "a", "Y": "b"}, model)
	y = ground_boolean_context(context, {"X": "a", "Y": "a"}, model)
	assert count_contexts((x, y)).basic == (Fraction(1, 4), 0)


def test_numeric_domain_does_not_receive_an_invented_uniform_boolean_measure(tmp_path):
	from evaluation.coverage_model import PDDLExecutionModel
	from evaluation.structural_coverage import UndefinedCoverage, ground_boolean_context
	from plan_library.models import PlanLibrary
	domain = tmp_path / "domain.pddl"
	problem = tmp_path / "problem.pddl"
	domain.write_text("""(define (domain counter) (:requirements :strips :fluents)
	 (:predicates (p)) (:functions (count)))""")
	problem.write_text("""(define (problem p) (:domain counter)
	 (:objects) (:init (p) (= (count) 2)) (:goal (p)))""")
	model = PDDLExecutionModel(domain, problem, PlanLibrary.from_dict({"plans": []}))
	with pytest.raises(UndefinedCoverage, match="Numeric"):
		ground_boolean_context(("p",), {}, model)
