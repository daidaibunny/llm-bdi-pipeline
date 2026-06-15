"""
Bounded paper-style validation for lifted AgentSpeak(L) libraries.

The checks are inspired by generalized-planning sketch validation: validate over
all reachable states of small training instances, require termination, reject
cycles in high-level decision traces, and ensure goal states are fixed points.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from plan_library.models import PlanLibrary
from utils.pddl_parser import PDDLDomain, PDDLParser, PDDLProblem

from .library_executor import execute_library_from_state
from .transition_system import State
from .transition_system import apply_ground_action
from .transition_system import fact_atom
from .transition_system import ground_actions_for_problem
from .transition_system import initial_state_from_problem
from .transition_system import is_action_applicable
from .transition_system import satisfies_atoms


@dataclass(frozen=True)
class BoundedProblemValidation:
	"""Validation outcome for one bounded PDDL problem transition system."""

	problem_name: str
	passed: bool
	reachable_state_count: int
	checked_state_count: int
	goal_state_count: int
	max_execution_steps: int
	failures: tuple[str, ...] = ()

	def to_dict(self) -> dict[str, object]:
		return {
			"problem_name": self.problem_name,
			"passed": self.passed,
			"reachable_state_count": self.reachable_state_count,
			"checked_state_count": self.checked_state_count,
			"goal_state_count": self.goal_state_count,
			"max_execution_steps": self.max_execution_steps,
			"failures": list(self.failures),
		}


@dataclass(frozen=True)
class BoundedLibraryValidationReport:
	"""Paper-style bounded validation report for one lifted library."""

	passed: bool
	problem_reports: tuple[BoundedProblemValidation, ...]
	checked_problem_count: int
	checked_state_count: int
	failure_count: int

	def to_dict(self) -> dict[str, object]:
		return {
			"passed": self.passed,
			"checked_problem_count": self.checked_problem_count,
			"checked_state_count": self.checked_state_count,
			"failure_count": self.failure_count,
			"problem_reports": [
				report.to_dict()
				for report in self.problem_reports
			],
		}


def validate_library_on_bounded_transition_systems(
	*,
	plan_library: PlanLibrary,
	domain_file: str | Path,
	problem_files: Sequence[str | Path],
	max_reachable_states: int = 20000,
	max_execution_steps: int = 5000,
	max_depth: int = 500,
) -> BoundedLibraryValidationReport:
	"""Validate one library from every reachable state in bounded problems."""

	domain = PDDLParser.parse_domain(domain_file)
	problem_reports = tuple(
		_validate_problem(
			plan_library=plan_library,
			domain=domain,
			domain_file=domain_file,
			problem=PDDLParser.parse_problem(problem_file),
			max_reachable_states=max_reachable_states,
			max_execution_steps=max_execution_steps,
			max_depth=max_depth,
		)
		for problem_file in tuple(problem_files or ())
	)
	failure_count = sum(len(report.failures) for report in problem_reports)
	return BoundedLibraryValidationReport(
		passed=all(report.passed for report in problem_reports),
		problem_reports=problem_reports,
		checked_problem_count=len(problem_reports),
		checked_state_count=sum(report.checked_state_count for report in problem_reports),
		failure_count=failure_count,
	)


def _validate_problem(
	*,
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	domain_file: str | Path,
	problem: PDDLProblem,
	max_reachable_states: int,
	max_execution_steps: int,
	max_depth: int,
) -> BoundedProblemValidation:
	reachable_states = _reachable_states(
		domain=domain,
		problem=problem,
		max_states=max_reachable_states,
	)
	goal_atoms = _goal_atoms(problem)
	goal_facts = _goal_facts(problem)
	failures: list[str] = []
	max_steps_seen = 0
	goal_state_count = 0
	for index, state in enumerate(sorted(reachable_states, key=_state_sort_key)):
		is_goal_state = _satisfies_goal(state, goal_atoms)
		if is_goal_state:
			goal_state_count += 1
		result = execute_library_from_state(
			plan_library=plan_library,
			domain_file=domain_file,
			problem_name=f"{problem.name}:state-{index}",
			initial_state=state,
			goal_facts=goal_facts,
			goal_atoms=goal_atoms,
			max_steps=max_execution_steps,
			max_depth=max_depth,
		)
		max_steps_seen = max(max_steps_seen, len(result.steps))
		failures.extend(
			_execution_failures(
				state_index=index,
				was_goal_state=is_goal_state,
				result=result,
			),
		)
	return BoundedProblemValidation(
		problem_name=problem.name,
		passed=not failures,
		reachable_state_count=len(reachable_states),
		checked_state_count=len(reachable_states),
		goal_state_count=goal_state_count,
		max_execution_steps=max_steps_seen,
		failures=tuple(failures),
	)


def _reachable_states(
	*,
	domain: PDDLDomain,
	problem: PDDLProblem,
	max_states: int,
) -> frozenset[State]:
	ground_actions = ground_actions_for_problem(domain.actions, problem)
	initial_state = initial_state_from_problem(problem)
	queue = deque([initial_state])
	visited: set[State] = {initial_state}
	while queue:
		state = queue.popleft()
		for action in ground_actions:
			if not is_action_applicable(state, action):
				continue
			next_state = apply_ground_action(state, action)
			if next_state in visited:
				continue
			visited.add(next_state)
			if len(visited) > max_states:
				raise ValueError(
					f"Bounded library validation exceeded {max_states} reachable states "
					f"for problem {problem.name}."
				)
			queue.append(next_state)
	return frozenset(visited)


def _execution_failures(
	*,
	state_index: int,
	was_goal_state: bool,
	result,
) -> tuple[str, ...]:
	failures: list[str] = []
	if not result.solved:
		failures.append(
			f"state {state_index}: execution failed: {result.failure_reason}",
		)
	if _has_cycle(result.decision_trace):
		failures.append(f"state {state_index}: high-level decision trace contains a repeated state")
	if was_goal_state and result.steps:
		failures.append(f"state {state_index}: goal state is not a fixed point")
	return tuple(failures)


def _has_cycle(state_trace: Iterable[frozenset[str]]) -> bool:
	seen: set[frozenset[str]] = set()
	for state in state_trace:
		if state in seen:
			return True
		seen.add(state)
	return False


def _goal_atoms(problem: PDDLProblem) -> tuple[str, ...]:
	return tuple(
		fact_atom(fact.predicate, fact.args)
		for fact in problem.goal_facts
		if fact.is_positive
	)


def _goal_facts(problem: PDDLProblem) -> tuple[str, ...]:
	return tuple(
		fact_atom(f"goal_{fact.predicate}", fact.args)
		for fact in problem.goal_facts
		if fact.is_positive
	)


def _satisfies_goal(state: State, goal_atoms: tuple[str, ...]) -> bool:
	return satisfies_atoms(state, goal_atoms)


def _state_sort_key(state: frozenset[str]) -> tuple[str, ...]:
	return tuple(sorted(state))
