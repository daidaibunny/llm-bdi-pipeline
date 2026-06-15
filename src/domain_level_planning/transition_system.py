"""
Domain-agnostic STRIPS transition evidence for lifted-library synthesis.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import product
from typing import Iterable, Sequence

from utils.pddl_parser import PDDLAction, PDDLDomain, PDDLFact, PDDLProblem

from .pddl_expression import LiftedLiteral, parse_pddl_literals


State = frozenset[str]


@dataclass(frozen=True)
class GroundAction:
	"""A grounded STRIPS action instance."""

	name: str
	arguments: tuple[str, ...]
	preconditions: tuple[LiftedLiteral, ...]
	add_effects: tuple[LiftedLiteral, ...]
	delete_effects: tuple[LiftedLiteral, ...]
	substitution: dict[str, str]

	def signature(self) -> str:
		return self.name if not self.arguments else f"{self.name}({', '.join(self.arguments)})"


@dataclass(frozen=True)
class GoalProgressEvidence:
	"""One observed action that makes a training goal fact true."""

	goal_fact: PDDLFact
	action_name: str
	action_arguments: tuple[str, ...]
	action_signature: str
	step_index: int
	before_state: tuple[str, ...]
	after_state: tuple[str, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"goal_fact": _goal_signature(self.goal_fact),
			"action_name": self.action_name,
			"action_arguments": list(self.action_arguments),
			"action_signature": self.action_signature,
			"step_index": self.step_index,
			"before_state": list(self.before_state),
			"after_state": list(self.after_state),
		}


@dataclass(frozen=True)
class TrainingTransitionEvidence:
	"""Small transition-system evidence extracted from one training problem."""

	problem_name: str
	object_count: int
	explored_state_count: int
	explored_transition_count: int
	plan_length: int
	goal_facts: tuple[str, ...]
	goal_orderings: tuple[tuple[PDDLFact, PDDLFact], ...]
	goal_progressions: tuple[GoalProgressEvidence, ...] = ()

	def to_dict(self) -> dict[str, object]:
		return {
			"problem_name": self.problem_name,
			"object_count": self.object_count,
			"explored_state_count": self.explored_state_count,
			"explored_transition_count": self.explored_transition_count,
			"plan_length": self.plan_length,
			"goal_facts": list(self.goal_facts),
			"goal_orderings": [
				(_goal_signature(earlier), _goal_signature(later))
				for earlier, later in self.goal_orderings
			],
			"goal_progressions": [
				progression.to_dict()
				for progression in self.goal_progressions
			],
		}


def collect_training_transition_evidence(
	domain: PDDLDomain,
	problem: PDDLProblem,
	*,
	max_states: int = 20000,
) -> TrainingTransitionEvidence:
	"""Explore a small grounded transition system and extract goal-order evidence."""

	ground_actions = ground_actions_for_problem(domain.actions, problem)
	initial_state = initial_state_from_problem(problem)
	goal_atoms = tuple(
		fact_atom(fact.predicate, fact.args)
		for fact in problem.goal_facts
		if fact.is_positive
	)
	queue = deque([initial_state])
	predecessors: dict[State, tuple[State, GroundAction] | None] = {initial_state: None}
	goal_state: State | None = initial_state if _satisfies(initial_state, goal_atoms) else None
	explored_transition_count = 0

	while queue and goal_state is None:
		state = queue.popleft()
		for action in ground_actions:
			if not is_action_applicable(state, action):
				continue
			next_state = apply_ground_action(state, action)
			explored_transition_count += 1
			if next_state in predecessors:
				continue
			predecessors[next_state] = (state, action)
			if len(predecessors) > max_states:
				raise ValueError(
					f"Training transition-system exploration exceeded {max_states} states "
					f"for problem {problem.name}."
				)
			if satisfies_atoms(next_state, goal_atoms):
				goal_state = next_state
				break
			queue.append(next_state)

	if goal_state is None:
		raise ValueError(f"No training plan found in bounded transition system: {problem.name}")

	plan = _reconstruct_plan(goal_state, predecessors)
	goal_orderings = _goal_orderings_from_plan(
		initial_state=initial_state,
		plan=plan,
		goal_facts=tuple(fact for fact in problem.goal_facts if fact.is_positive),
	)
	goal_progressions = _goal_progressions_from_plan(
		initial_state=initial_state,
		plan=plan,
		goal_facts=tuple(fact for fact in problem.goal_facts if fact.is_positive),
	)
	return TrainingTransitionEvidence(
		problem_name=problem.name,
		object_count=len(problem.objects),
		explored_state_count=len(predecessors),
		explored_transition_count=explored_transition_count,
		plan_length=len(plan),
		goal_facts=tuple(_goal_signature(fact) for fact in problem.goal_facts),
		goal_orderings=goal_orderings,
		goal_progressions=goal_progressions,
	)


def initial_state_from_problem(problem: PDDLProblem) -> State:
	"""Return the positive initial facts of a parsed PDDL problem."""

	return frozenset(
		fact_atom(fact.predicate, fact.args)
		for fact in problem.init_facts
		if fact.is_positive
	)


def ground_actions_for_problem(
	actions: Sequence[PDDLAction],
	problem: PDDLProblem,
) -> tuple[GroundAction, ...]:
	"""Ground action schemas against a parsed PDDL problem."""

	return tuple(_iter_ground_actions(actions, problem))


def is_action_applicable(state: State, action: GroundAction) -> bool:
	"""Return whether a grounded action is applicable in a STRIPS state."""

	return _is_applicable(state, action)


def apply_ground_action(state: State, action: GroundAction) -> State:
	"""Apply a grounded action to a STRIPS state."""

	return _apply_action(state, action)


def reachable_states_for_problem(
	domain: PDDLDomain,
	problem: PDDLProblem,
	*,
	max_states: int = 20000,
) -> frozenset[State]:
	"""Enumerate the bounded reachable STRIPS states for one grounded problem."""

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
					f"Reachable-state exploration exceeded {max_states} states "
					f"for problem {problem.name}."
				)
			queue.append(next_state)
	return frozenset(visited)


def satisfies_atoms(state: State, atoms: tuple[str, ...]) -> bool:
	"""Return whether all atoms hold in a STRIPS state."""

	return _satisfies(state, atoms)


def fact_atom(predicate: str, arguments: Iterable[str]) -> str:
	"""Render a predicate and arguments into the project fact signature."""

	return _atom(predicate, arguments)


def _iter_ground_actions(
	actions: Sequence[PDDLAction],
	problem: PDDLProblem,
) -> Iterable[GroundAction]:
	for action in actions:
		parameters = tuple(_parameter_name_type(parameter) for parameter in action.parameters)
		object_domains = tuple(_objects_for_type(problem, type_name) for _, type_name in parameters)
		for objects in product(*object_domains):
			substitution = {
				name: object_name
				for (name, _), object_name in zip(parameters, objects)
			}
			preconditions = tuple(
				_ground_literal(literal, substitution)
				for literal in parse_pddl_literals(action.preconditions)
			)
			effects = tuple(
				_ground_literal(literal, substitution)
				for literal in parse_pddl_literals(action.effects)
			)
			yield GroundAction(
				name=action.name,
				arguments=tuple(objects),
				preconditions=preconditions,
				add_effects=tuple(literal for literal in effects if literal.is_positive),
				delete_effects=tuple(literal for literal in effects if not literal.is_positive),
				substitution=substitution,
			)


def _objects_for_type(problem: PDDLProblem, type_name: str) -> tuple[str, ...]:
	if type_name in {"", "object"}:
		return tuple(problem.objects)
	typed_objects = tuple(
		object_name
		for object_name in problem.objects
		if problem.object_types.get(object_name, "object") == type_name
	)
	return typed_objects or tuple(problem.objects)


def _parameter_name_type(parameter: str) -> tuple[str, str]:
	text = str(parameter or "").strip()
	if " - " not in text:
		return text, "object"
	name, type_name = text.split(" - ", 1)
	return name.strip(), type_name.strip()


def _ground_literal(
	literal: LiftedLiteral,
	substitution: dict[str, str],
) -> LiftedLiteral:
	return LiftedLiteral(
		predicate=literal.predicate,
		arguments=tuple(substitution.get(argument, argument) for argument in literal.arguments),
		is_positive=literal.is_positive,
	)


def _is_applicable(state: State, action: GroundAction) -> bool:
	for precondition in action.preconditions:
		atom = _atom(precondition.predicate, precondition.arguments)
		if precondition.is_positive and atom not in state:
			return False
		if not precondition.is_positive and atom in state:
			return False
	return True


def _apply_action(state: State, action: GroundAction) -> State:
	next_state = set(state)
	for effect in action.delete_effects:
		next_state.discard(_atom(effect.predicate, effect.arguments))
	for effect in action.add_effects:
		next_state.add(_atom(effect.predicate, effect.arguments))
	return frozenset(next_state)


def _satisfies(state: State, goal_atoms: tuple[str, ...]) -> bool:
	return all(atom in state for atom in goal_atoms)


def _reconstruct_plan(
	goal_state: State,
	predecessors: dict[State, tuple[State, GroundAction] | None],
) -> tuple[GroundAction, ...]:
	actions: list[GroundAction] = []
	cursor = goal_state
	while predecessors[cursor] is not None:
		previous, action = predecessors[cursor]  # type: ignore[misc]
		actions.append(action)
		cursor = previous
	actions.reverse()
	return tuple(actions)


def _goal_orderings_from_plan(
	*,
	initial_state: State,
	plan: tuple[GroundAction, ...],
	goal_facts: tuple[PDDLFact, ...],
) -> tuple[tuple[PDDLFact, PDDLFact], ...]:
	achievement_step: dict[str, int] = {}
	for fact in goal_facts:
		atom = _atom(fact.predicate, fact.args)
		if atom in initial_state:
			achievement_step[atom] = 0

	state = initial_state
	for step_index, action in enumerate(plan, start=1):
		next_state = _apply_action(state, action)
		for fact in goal_facts:
			atom = _atom(fact.predicate, fact.args)
			if atom not in state and atom in next_state:
				achievement_step[atom] = step_index
		state = next_state

	orderings: list[tuple[PDDLFact, PDDLFact]] = []
	for earlier in goal_facts:
		earlier_step = achievement_step.get(_atom(earlier.predicate, earlier.args))
		if earlier_step is None:
			continue
		for later in goal_facts:
			if earlier == later:
				continue
			later_step = achievement_step.get(_atom(later.predicate, later.args))
			if later_step is None:
				continue
			if earlier_step < later_step:
				orderings.append((earlier, later))
	return tuple(orderings)


def _goal_progressions_from_plan(
	*,
	initial_state: State,
	plan: tuple[GroundAction, ...],
	goal_facts: tuple[PDDLFact, ...],
) -> tuple[GoalProgressEvidence, ...]:
	progressions: dict[str, GoalProgressEvidence] = {}
	state = initial_state
	for step_index, action in enumerate(plan, start=1):
		next_state = _apply_action(state, action)
		for fact in goal_facts:
			atom = _atom(fact.predicate, fact.args)
			if atom not in state and atom in next_state:
				progressions[atom] = GoalProgressEvidence(
					goal_fact=fact,
					action_name=action.name,
					action_arguments=action.arguments,
					action_signature=action.signature(),
					step_index=step_index,
					before_state=tuple(sorted(state)),
					after_state=tuple(sorted(next_state)),
				)
		state = next_state
	return tuple(progressions[atom] for atom in sorted(progressions))


def _atom(predicate: str, arguments: Iterable[str]) -> str:
	args = tuple(arguments)
	return predicate if not args else f"{predicate}({', '.join(args)})"


def _goal_signature(fact: PDDLFact) -> str:
	atom = (
		f"goal_{fact.predicate}"
		if not fact.args
		else f"goal_{fact.predicate}({', '.join(fact.args)})"
	)
	return atom if fact.is_positive else f"not {atom}"
