from __future__ import annotations

from pathlib import Path

from utils.pddl_parser import PDDLParser


def test_parse_pddl_domain_and_problem(tmp_path: Path) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain transport)
		 (:requirements :strips :typing)
		 (:types location locatable vehicle package - object)
		 (:predicates
		  (at ?x - locatable ?l - location)
		  (in ?p - package ?v - vehicle)
		 )
		 (:action drive
		  :parameters (?v - vehicle ?from ?to - location)
		  :precondition (at ?v ?from)
		  :effect (and (not (at ?v ?from)) (at ?v ?to))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file = tmp_path / "problem.pddl"
	problem_file.write_text(
		"""
		(define (problem p1)
		 (:domain transport)
		 (:objects city-loc-0 city-loc-1 - location truck-0 - vehicle package-0 - package)
		 (:init (at truck-0 city-loc-1) (at package-0 city-loc-0))
		 (:goal (and (at package-0 city-loc-1) (not (in package-0 truck-0))))
		)
		""",
		encoding="utf-8",
	)

	domain = PDDLParser.parse_domain(domain_file)
	problem = PDDLParser.parse_problem(problem_file)

	assert domain.name == "transport"
	assert [predicate.name for predicate in domain.predicates] == ["at", "in"]
	assert [action.name for action in domain.actions] == ["drive"]
	assert problem.domain_name == "transport"
	assert problem.object_types["package-0"] == "package"
	assert [fact.to_signature() for fact in problem.goal_facts] == [
		"at(package-0, city-loc-1)",
		"not in(package-0, truck-0)",
	]


def test_parse_problem_accepts_predicates_whose_names_start_with_not(
	tmp_path: Path,
) -> None:
	problem_file = tmp_path / "problem.pddl"
	problem_file.write_text(
		"""
		(define (problem p1)
		 (:domain generic)
		 (:objects a)
		 (:init (notready a) (notexist a) (ready a))
		 (:goal (and (done a)))
		)
		""",
		encoding="utf-8",
	)

	problem = PDDLParser.parse_problem(problem_file)

	assert [fact.to_signature() for fact in problem.init_facts] == [
		"notready(a)",
		"notexist(a)",
		"ready(a)",
	]


def test_parse_domain_constants_with_types(tmp_path: Path) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain constants)
		 (:requirements :strips :typing)
		 (:types place item)
		 (:constants kitchen table1 - place box1 - item)
		 (:predicates (at ?x - item ?p - place))
		)
		""",
		encoding="utf-8",
	)

	domain = PDDLParser.parse_domain(domain_file)

	assert domain.constants == ["kitchen", "table1", "box1"]
	assert domain.constant_types == {
		"kitchen": "place",
		"table1": "place",
		"box1": "item",
	}


def test_parse_bounded_integer_numeric_resource_fragment(tmp_path: Path) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain numeric-transport)
		 (:requirements :strips :typing :numeric-fluents)
		 (:types vehicle package location)
		 (:predicates
		  (at ?x ?l - location)
		  (in ?p - package ?v - vehicle)
		 )
		 (:functions
		  (capacity ?v - vehicle)
		 )
		 (:action pick-up
		  :parameters (?v - vehicle ?p - package ?l - location)
		  :precondition (and (at ?v ?l) (at ?p ?l) (>= (capacity ?v) 1))
		  :effect (and (not (at ?p ?l)) (in ?p ?v) (decrease (capacity ?v) 1))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file = tmp_path / "problem.pddl"
	problem_file.write_text(
		"""
		(define (problem p1)
		 (:domain numeric-transport)
		 (:objects truck1 - vehicle package1 - package depot1 - location)
		 (:init (= (capacity truck1) 2) (at truck1 depot1) (at package1 depot1))
		 (:goal (and (in package1 truck1) (= (capacity truck1) 1)))
		)
		""",
		encoding="utf-8",
	)

	domain = PDDLParser.parse_domain(domain_file)
	problem = PDDLParser.parse_problem(problem_file)

	assert [function.name for function in domain.functions] == ["capacity"]
	assert domain.actions[0].numeric_preconditions[0].comparator == ">="
	assert domain.actions[0].numeric_preconditions[0].left.to_signature() == "capacity(?v)"
	assert domain.actions[0].numeric_preconditions[0].right.to_signature() == "1"
	assert domain.actions[0].numeric_effects[0].operator == "decrease"
	assert domain.actions[0].numeric_effects[0].fluent.to_signature() == "capacity(?v)"
	assert domain.actions[0].numeric_effects[0].amount.to_signature() == "1"
	assert problem.numeric_init[0].fluent.to_signature() == "capacity(truck1)"
	assert problem.numeric_init[0].value == 2
	assert [fact.to_signature() for fact in problem.goal_facts] == ["in(package1, truck1)"]
	assert problem.numeric_goal_conditions[0].to_signature() == "capacity(truck1) = 1"
