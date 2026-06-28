from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResourceDependencyFixture:
	domain_file: Path
	problems: tuple[Path, ...]


def write_resource_dependency_fixture(
	root: Path,
	*,
	problem_count: int = 6,
) -> ResourceDependencyFixture:
	"""Write a minimal PDDL fixture that forces conjunctive-goal ordering."""

	if problem_count < 2:
		raise ValueError("resource dependency fixture needs at least two problems.")
	root.mkdir(parents=True, exist_ok=True)
	problems_root = root / "problems"
	problems_root.mkdir()
	domain_file = root / "domain.pddl"
	domain_file.write_text(_DOMAIN_TEXT, encoding="utf-8")
	problems = tuple(
		_write_problem(problems_root, index=index)
		for index in range(1, problem_count + 1)
	)
	return ResourceDependencyFixture(domain_file=domain_file, problems=problems)


def _write_problem(problems_root: Path, *, index: int) -> Path:
	problem_file = problems_root / f"p{index:02d}.pddl"
	pair_count = max(1, index - 1)
	samples = tuple(f"s{item}" for item in range(1, pair_count + 1))
	reagents = tuple(f"r{item}" for item in range(1, pair_count + 1))
	if index == 1:
		goal_facts = ("(analysis_done s1 r1)",)
	else:
		goal_facts = tuple(
			fact
			for sample, reagent in zip(samples, reagents)
			for fact in (
				f"(reagent_logged {reagent})",
				f"(analysis_done {sample} {reagent})",
			)
		)
	problem_file.write_text(
		"\n".join(
			(
				f"(define (problem resource-dependency-p{index:02d})",
				" (:domain resource-dependency)",
				" (:objects",
				f"  {' '.join(samples)} - sample",
				f"  {' '.join(reagents)} - reagent",
				" )",
				" (:init",
				*tuple(f"  (sample_available {sample})" for sample in samples),
				*tuple(f"  (reagent_available {reagent})" for reagent in reagents),
				" )",
				" (:goal (and",
				*tuple(f"  {fact}" for fact in goal_facts),
				" ))",
				")",
				"",
			),
		),
		encoding="utf-8",
	)
	return problem_file


_DOMAIN_TEXT = """
(define (domain resource-dependency)
 (:requirements :strips :typing)
 (:types sample reagent - object)
 (:predicates
  (sample_available ?s - sample)
  (reagent_available ?r - reagent)
  (reagent_logged ?r - reagent)
  (analysis_done ?s - sample ?r - reagent)
 )
 (:action log_reagent
  :parameters (?r - reagent)
  :precondition (reagent_available ?r)
  :effect (reagent_logged ?r)
 )
 (:action run_analysis
  :parameters (?s - sample ?r - reagent)
  :precondition (and (sample_available ?s) (reagent_available ?r))
  :effect (and (analysis_done ?s ?r) (not (reagent_available ?r)))
 )
)
""".strip() + "\n"
