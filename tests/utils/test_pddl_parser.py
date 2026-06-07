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
