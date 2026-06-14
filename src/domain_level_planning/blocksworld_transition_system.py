"""
Explicit transition-system enumeration for standard four-operator Blocksworld.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from utils.pddl_parser import PDDLFact, PDDLProblem


@dataclass(frozen=True)
class GroundAction:
	"""A grounded Blocksworld action."""

	name: str
	arguments: tuple[str, ...]

	def signature(self) -> str:
		return (
			self.name
			if not self.arguments
			else f"{self.name}({', '.join(self.arguments)})"
		)


@dataclass(frozen=True)
class TransitionSystemSummary:
	"""Summary of an enumerated reachable transition system."""

	problem_name: str
	object_count: int
	reachable_state_count: int
	transition_count: int
	goal_facts: tuple[str, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"problem_name": self.problem_name,
			"object_count": self.object_count,
			"reachable_state_count": self.reachable_state_count,
			"transition_count": self.transition_count,
			"goal_facts": list(self.goal_facts),
		}


State = frozenset[str]


def enumerate_blocksworld_transition_system(
	problem: PDDLProblem,
	*,
	max_states: int = 20000,
) -> TransitionSystemSummary:
	"""Enumerate the reachable transition graph for one Blocksworld problem."""

	objects = tuple(problem.objects)
	initial_state = frozenset(
		_atom(fact.predicate, fact.args)
		for fact in problem.init_facts
		if fact.is_positive
	)
	visited: set[State] = {initial_state}
	queue = deque([initial_state])
	transition_count = 0

	while queue:
		state = queue.popleft()
		for action in _applicable_actions(state, objects):
			next_state = _apply_action(state, action)
			transition_count += 1
			if next_state in visited:
				continue
			visited.add(next_state)
			if len(visited) > max_states:
				raise ValueError(
					f"Blocksworld transition-system enumeration exceeded {max_states} "
					f"states for problem {problem.name}."
				)
			queue.append(next_state)

	return TransitionSystemSummary(
		problem_name=problem.name,
		object_count=len(objects),
		reachable_state_count=len(visited),
		transition_count=transition_count,
		goal_facts=tuple(_goal_fact_signature(fact) for fact in problem.goal_facts),
	)


def _applicable_actions(state: State, objects: tuple[str, ...]) -> Iterable[GroundAction]:
	for block in objects:
		if _has(state, "clear", block) and _has(state, "ontable", block) and _has(state, "handempty"):
			yield GroundAction("pick-up", (block,))
		if _has(state, "holding", block):
			yield GroundAction("put-down", (block,))
	for block in objects:
		for support in objects:
			if block == support:
				continue
			if _has(state, "holding", block) and _has(state, "clear", support):
				yield GroundAction("stack", (block, support))
			if (
				_has(state, "on", block, support)
				and _has(state, "clear", block)
				and _has(state, "handempty")
			):
				yield GroundAction("unstack", (block, support))


def _apply_action(state: State, action: GroundAction) -> State:
	next_state = set(state)
	if action.name == "pick-up":
		(block,) = action.arguments
		next_state.difference_update(
			{
				_atom("ontable", (block,)),
				_atom("clear", (block,)),
				_atom("handempty", ()),
			},
		)
		next_state.add(_atom("holding", (block,)))
	elif action.name == "put-down":
		(block,) = action.arguments
		next_state.discard(_atom("holding", (block,)))
		next_state.update(
			{
				_atom("clear", (block,)),
				_atom("handempty", ()),
				_atom("ontable", (block,)),
			},
		)
	elif action.name == "stack":
		block, support = action.arguments
		next_state.difference_update(
			{
				_atom("holding", (block,)),
				_atom("clear", (support,)),
			},
		)
		next_state.update(
			{
				_atom("clear", (block,)),
				_atom("handempty", ()),
				_atom("on", (block, support)),
			},
		)
	elif action.name == "unstack":
		block, support = action.arguments
		next_state.difference_update(
			{
				_atom("clear", (block,)),
				_atom("handempty", ()),
				_atom("on", (block, support)),
			},
		)
		next_state.update(
			{
				_atom("holding", (block,)),
				_atom("clear", (support,)),
			},
		)
	else:
		raise ValueError(f"Unsupported Blocksworld action: {action.signature()}")
	return frozenset(next_state)


def _has(state: State, predicate: str, *arguments: str) -> bool:
	return _atom(predicate, arguments) in state


def _atom(predicate: str, arguments: Iterable[str]) -> str:
	args = tuple(arguments)
	return predicate if not args else f"{predicate}({', '.join(args)})"


def _goal_fact_signature(fact: PDDLFact) -> str:
	atom = (
		f"goal_{fact.predicate}"
		if not fact.args
		else f"goal_{fact.predicate}({', '.join(fact.args)})"
	)
	return atom if fact.is_positive else f"not {atom}"
