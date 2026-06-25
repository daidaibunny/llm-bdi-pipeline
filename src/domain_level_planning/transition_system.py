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
from .pddl_types import object_belongs_to_type, object_type_atoms


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
class AtomicAchievementEvidence:
	"""One trace slice where an action makes a (possibly non-goal) fact true.

	Layer B atomic-module learning generalizes from these slices rather than from
	final goal facts alone. Each slice records the achieving action, the grounded
	preconditions that enabled it in the before-state, and whether this is the
	last time the fact transitions from false to true in the plan.
	"""

	target_fact: PDDLFact
	action_name: str
	action_arguments: tuple[str, ...]
	action_signature: str
	step_index: int
	enabling_preconditions: tuple[LiftedLiteral, ...]
	before_state: tuple[str, ...]
	after_state: tuple[str, ...]
	is_last_achiever: bool = False

	def to_dict(self) -> dict[str, object]:
		return {
			"target_fact": _fact_signature(self.target_fact),
			"action_name": self.action_name,
			"action_arguments": list(self.action_arguments),
			"action_signature": self.action_signature,
			"step_index": self.step_index,
			"is_last_achiever": self.is_last_achiever,
			"enabling_preconditions": [
				_atom(literal.predicate, literal.arguments)
				for literal in self.enabling_preconditions
			],
			"before_state": list(self.before_state),
			"after_state": list(self.after_state),
		}


@dataclass(frozen=True)
class LiftedAtomicAchievementPattern:
	"""Anti-unified Layer B evidence shared by grounded achievement slices."""

	target_predicate: str
	target_arguments: tuple[str, ...]
	action_name: str
	action_arguments: tuple[str, ...]
	enabling_preconditions: tuple[str, ...]
	support_count: int
	last_achiever_support_count: int
	example_signatures: tuple[str, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"target_predicate": self.target_predicate,
			"target_arguments": list(self.target_arguments),
			"action_name": self.action_name,
			"action_arguments": list(self.action_arguments),
			"enabling_preconditions": list(self.enabling_preconditions),
			"support_count": self.support_count,
			"last_achiever_support_count": self.last_achiever_support_count,
			"example_signatures": list(self.example_signatures),
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
	atomic_achievements: tuple[AtomicAchievementEvidence, ...] = ()
	initial_state: tuple[str, ...] = ()
	plan_actions: tuple[GroundAction, ...] = ()
	evidence_source: str = "bounded_transition_system"

	def to_dict(self) -> dict[str, object]:
		return {
			"problem_name": self.problem_name,
			"evidence_source": self.evidence_source,
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
			"atomic_achievements": [
				slice_.to_dict()
				for slice_ in self.atomic_achievements
			],
			"initial_state": list(self.initial_state),
			"plan_actions": [
				action.signature()
				for action in self.plan_actions
			],
		}


def collect_training_transition_evidence(
	domain: PDDLDomain,
	problem: PDDLProblem,
	*,
	max_states: int = 20000,
) -> TrainingTransitionEvidence:
	"""Explore a small grounded transition system and extract goal-order evidence."""

	ground_actions = ground_actions_for_problem(
		domain.actions,
		problem,
		domain_types=domain.types,
	)
	initial_state = initial_state_from_problem(problem, domain_types=domain.types)
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
	atomic_achievements = atomic_achievements_from_plan(
		initial_state=initial_state,
		plan=plan,
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
		atomic_achievements=atomic_achievements,
		initial_state=tuple(sorted(initial_state)),
		plan_actions=plan,
	)


def collect_training_transition_evidence_from_plan(
	domain: PDDLDomain,
	problem: PDDLProblem,
	plan_actions: Sequence[object],
	*,
	evidence_source: str = "offline_planner_trace",
) -> TrainingTransitionEvidence:
	"""Extract training evidence from an externally supplied grounded plan trace.

	The plan is used only as offline synthesis evidence. Every action is checked
	against the grounded PDDL schemas and simulated from the problem initial
	state, so stale or invalid planner output cannot silently justify ASL rules.
	"""

	ground_actions = ground_actions_for_problem(
		domain.actions,
		problem,
		domain_types=domain.types,
	)
	ground_action_by_signature = {
		action.signature(): action for action in ground_actions
	}
	plan = tuple(
		_ground_plan_action(
			raw_action,
			ground_action_by_signature=ground_action_by_signature,
		)
		for raw_action in tuple(plan_actions or ())
	)
	if not plan:
		raise ValueError(
			f"Offline planner trace for problem {problem.name} contains no actions.",
		)
	initial_state = initial_state_from_problem(problem, domain_types=domain.types)
	state = initial_state
	for step_index, action in enumerate(plan, start=1):
		if not is_action_applicable(state, action):
			raise ValueError(
				"Offline planner trace action is not applicable for problem "
				f"{problem.name} at step {step_index}: {action.signature()}",
			)
		state = apply_ground_action(state, action)
	goal_atoms = tuple(
		fact_atom(fact.predicate, fact.args)
		for fact in problem.goal_facts
		if fact.is_positive
	)
	if not satisfies_atoms(state, goal_atoms):
		raise ValueError(
			f"Offline planner trace does not satisfy training goals for {problem.name}.",
		)
	goal_facts = tuple(fact for fact in problem.goal_facts if fact.is_positive)
	return TrainingTransitionEvidence(
		problem_name=problem.name,
		object_count=len(problem.objects),
		explored_state_count=0,
		explored_transition_count=len(plan),
		plan_length=len(plan),
		goal_facts=tuple(_goal_signature(fact) for fact in problem.goal_facts),
		goal_orderings=_goal_orderings_from_plan(
			initial_state=initial_state,
			plan=plan,
			goal_facts=goal_facts,
		),
		goal_progressions=_goal_progressions_from_plan(
			initial_state=initial_state,
			plan=plan,
			goal_facts=goal_facts,
		),
		atomic_achievements=atomic_achievements_from_plan(
			initial_state=initial_state,
			plan=plan,
		),
		initial_state=tuple(sorted(initial_state)),
		plan_actions=plan,
		evidence_source=evidence_source,
	)


def initial_state_from_problem(
	problem: PDDLProblem,
	*,
	domain_types: Sequence[str] = (),
) -> State:
	"""Return the positive initial facts of a parsed PDDL problem."""

	return frozenset(
		(
			*(
				fact_atom(fact.predicate, fact.args)
				for fact in problem.init_facts
				if fact.is_positive
			),
			*object_type_atoms(problem, domain_types),
		),
	)


def ground_actions_for_problem(
	actions: Sequence[PDDLAction],
	problem: PDDLProblem,
	*,
	domain_types: Sequence[str] = (),
) -> tuple[GroundAction, ...]:
	"""Ground action schemas against a parsed PDDL problem."""

	return tuple(_iter_ground_actions(actions, problem, domain_types=domain_types))


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

	ground_actions = ground_actions_for_problem(
		domain.actions,
		problem,
		domain_types=domain.types,
	)
	initial_state = initial_state_from_problem(problem, domain_types=domain.types)
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
	*,
	domain_types: Sequence[str] = (),
) -> Iterable[GroundAction]:
	for action in actions:
		parameters = tuple(_parameter_name_type(parameter) for parameter in action.parameters)
		object_domains = tuple(
			_objects_for_type(problem, type_name, domain_types=domain_types)
			for _, type_name in parameters
		)
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


def _objects_for_type(
	problem: PDDLProblem,
	type_name: str,
	*,
	domain_types: Sequence[str] = (),
) -> tuple[str, ...]:
	if type_name in {"", "object"}:
		return tuple(problem.objects)
	typed_objects = tuple(
		object_name
		for object_name in problem.objects
		if object_belongs_to_type(
			object_name,
			object_types=problem.object_types,
			requested_type=type_name,
			type_tokens=domain_types,
		)
	)
	if typed_objects or domain_types:
		return typed_objects
	return tuple(problem.objects)


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
		if precondition.predicate == "=":
			holds = _equality_holds(precondition.arguments)
			if precondition.is_positive and not holds:
				return False
			if not precondition.is_positive and holds:
				return False
			continue
		atom = _atom(precondition.predicate, precondition.arguments)
		if precondition.is_positive and atom not in state:
			return False
		if not precondition.is_positive and atom in state:
			return False
	return True


def _apply_action(state: State, action: GroundAction) -> State:
	next_state = set(state)
	for effect in action.delete_effects:
		if effect.predicate == "=":
			continue
		next_state.discard(_atom(effect.predicate, effect.arguments))
	for effect in action.add_effects:
		if effect.predicate == "=":
			continue
		next_state.add(_atom(effect.predicate, effect.arguments))
	return frozenset(next_state)


def _equality_holds(arguments: tuple[str, ...]) -> bool:
	if len(arguments) != 2:
		return False
	left, right = arguments
	return left == right


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


def _ground_plan_action(
	raw_action: object,
	*,
	ground_action_by_signature: dict[str, GroundAction],
) -> GroundAction:
	name = str(getattr(raw_action, "name", "")).strip()
	arguments = tuple(str(argument) for argument in getattr(raw_action, "arguments", ()) or ())
	signature = _atom(name, arguments)
	if signature in ground_action_by_signature:
		return ground_action_by_signature[signature]
	if not arguments and name in ground_action_by_signature:
		return ground_action_by_signature[name]
	raise ValueError(f"Unknown grounded planner action: {signature}")


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


def atomic_achievements_from_plan(
	*,
	initial_state: State,
	plan: tuple[GroundAction, ...],
) -> tuple[AtomicAchievementEvidence, ...]:
	"""Slice a plan into per-action atomic achievement evidence.

	Every action add-effect that transitions a fact from false to true becomes a
	slice, including intermediate non-goal facts. The last false-to-true
	transition of each fact across the whole plan is flagged as the last achiever.
	"""

	slices: list[AtomicAchievementEvidence] = []
	state = initial_state
	for step_index, action in enumerate(plan, start=1):
		next_state = _apply_action(state, action)
		enabling = tuple(
			precondition
			for precondition in action.preconditions
			if precondition.is_positive
			and _atom(precondition.predicate, precondition.arguments) in state
		)
		for effect in action.add_effects:
			atom = _atom(effect.predicate, effect.arguments)
			if atom in state or atom not in next_state:
				continue
			slices.append(
				AtomicAchievementEvidence(
					target_fact=PDDLFact(
						predicate=effect.predicate,
						args=list(effect.arguments),
						is_positive=True,
					),
					action_name=action.name,
					action_arguments=action.arguments,
					action_signature=action.signature(),
					step_index=step_index,
					enabling_preconditions=enabling,
					before_state=tuple(sorted(state)),
					after_state=tuple(sorted(next_state)),
				),
			)
		state = next_state
	return _mark_last_achievers(slices)


def anti_unify_atomic_achievements(
	slices: Sequence[AtomicAchievementEvidence],
) -> tuple[LiftedAtomicAchievementPattern, ...]:
	"""Anti-unify grounded atomic achievement slices into lifted support patterns."""

	grouped: dict[tuple[object, ...], list[AtomicAchievementEvidence]] = {}
	for slice_ in tuple(slices or ()):
		pattern = _anti_unified_slice_pattern(slice_)
		grouped.setdefault(pattern, []).append(slice_)
	patterns: list[LiftedAtomicAchievementPattern] = []
	for pattern, support in grouped.items():
		(
			target_predicate,
			target_arguments,
			action_name,
			action_arguments,
			enabling_preconditions,
		) = pattern
		examples = tuple(
			(
				f"{_fact_signature(slice_.target_fact)} via "
				f"{slice_.action_signature}@{slice_.step_index}"
			)
			for slice_ in support
		)
		patterns.append(
			LiftedAtomicAchievementPattern(
				target_predicate=str(target_predicate),
				target_arguments=tuple(target_arguments),
				action_name=str(action_name),
				action_arguments=tuple(action_arguments),
				enabling_preconditions=tuple(enabling_preconditions),
				support_count=len(support),
				last_achiever_support_count=sum(
					1 for slice_ in support if slice_.is_last_achiever
				),
				example_signatures=examples,
			),
		)
	return tuple(
		sorted(
			patterns,
			key=lambda item: (
				item.target_predicate,
				item.action_name,
				item.target_arguments,
				item.action_arguments,
				item.enabling_preconditions,
			),
		),
	)


def anti_unify_training_atomic_achievements(
	evidence_items: Sequence[TrainingTransitionEvidence],
) -> tuple[LiftedAtomicAchievementPattern, ...]:
	"""Anti-unify atomic achievement slices across training evidence objects."""

	return anti_unify_atomic_achievements(
		tuple(
			slice_
			for evidence in tuple(evidence_items or ())
			for slice_ in tuple(getattr(evidence, "atomic_achievements", ()) or ())
		),
	)


def _mark_last_achievers(
	slices: Sequence[AtomicAchievementEvidence],
) -> tuple[AtomicAchievementEvidence, ...]:
	last_step_by_atom: dict[str, int] = {}
	for slice_ in slices:
		atom = _atom(slice_.target_fact.predicate, slice_.target_fact.args)
		last_step_by_atom[atom] = max(last_step_by_atom.get(atom, 0), slice_.step_index)
	marked: list[AtomicAchievementEvidence] = []
	for slice_ in slices:
		atom = _atom(slice_.target_fact.predicate, slice_.target_fact.args)
		marked.append(
			AtomicAchievementEvidence(
				target_fact=slice_.target_fact,
				action_name=slice_.action_name,
				action_arguments=slice_.action_arguments,
				action_signature=slice_.action_signature,
				step_index=slice_.step_index,
				enabling_preconditions=slice_.enabling_preconditions,
				before_state=slice_.before_state,
				after_state=slice_.after_state,
				is_last_achiever=slice_.step_index == last_step_by_atom[atom],
			),
		)
	return tuple(marked)


def _anti_unified_slice_pattern(slice_: AtomicAchievementEvidence) -> tuple[object, ...]:
	object_variables: dict[str, str] = {}

	def _variables(arguments: Iterable[str]) -> tuple[str, ...]:
		return tuple(_variable_for_object(argument, object_variables) for argument in arguments)

	target_arguments = _variables(slice_.target_fact.args)
	action_arguments = _variables(slice_.action_arguments)
	enabling_preconditions = tuple(
		sorted(
			_atom(literal.predicate, _variables(literal.arguments))
			for literal in slice_.enabling_preconditions
		),
	)
	return (
		slice_.target_fact.predicate,
		target_arguments,
		slice_.action_name,
		action_arguments,
		enabling_preconditions,
	)


def _variable_for_object(object_name: str, mapping: dict[str, str]) -> str:
	if object_name not in mapping:
		mapping[object_name] = _variable_name(len(mapping))
	return mapping[object_name]


def _variable_name(index: int) -> str:
	names = ("X", "Y", "Z", "W", "V", "U", "T", "S")
	return names[index] if index < len(names) else f"X{index + 1}"


def _atom(predicate: str, arguments: Iterable[str]) -> str:
	args = tuple(arguments)
	return predicate if not args else f"{predicate}({', '.join(args)})"


def _fact_signature(fact: PDDLFact) -> str:
	return _atom(fact.predicate, fact.args)


def _goal_signature(fact: PDDLFact) -> str:
	atom = (
		f"goal_{fact.predicate}"
		if not fact.args
		else f"goal_{fact.predicate}({', '.join(fact.args)})"
	)
	return atom if fact.is_positive else f"not {atom}"
