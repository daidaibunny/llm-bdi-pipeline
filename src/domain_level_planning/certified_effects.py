"""Conservative effect certificates for selected atomic AgentSpeak modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakPlan
from plan_library.models import PlanLibrary
from utils.pddl_parser import PDDLDomain

from .atomic_module_synthesis import _ParsedAction


@dataclass(frozen=True)
class EffectTerm:
	"""A constant or a scoped lifted variable in an effect summary."""

	symbol: str
	variable_scope: str | None = None

	@property
	def is_variable(self) -> bool:
		return self.variable_scope is not None


@dataclass(frozen=True)
class EffectAtom:
	predicate: str
	arguments: tuple[EffectTerm, ...]


@dataclass(frozen=True)
class AtomicModuleEffectSummary:
	"""May-delete summary for every selected branch of one atomic module call."""

	delete_atoms: tuple[EffectAtom, ...]
	complete: bool


@dataclass(frozen=True)
class TransitionSerializationCertificate:
	"""Proof record for one conjunctive DFA guard serialization."""

	ordered_indexes: tuple[int, ...]
	threat_edges: tuple[tuple[int, int], ...]
	module_summaries_complete: bool

	def to_dict(self) -> dict[str, object]:
		return {
			"certificate_kind": "atomic_module_delete_effect_serialization",
			"ordered_literal_indexes": list(self.ordered_indexes),
			"threat_edges": [list(edge) for edge in self.threat_edges],
			"module_summaries_complete": self.module_summaries_complete,
		}


def threat_safe_positive_literal_order(
	literals: Sequence[tuple[str, tuple[str, ...]]],
	*,
	plan_library: PlanLibrary,
	domain: PDDLDomain,
) -> tuple[tuple[int, ...], TransitionSerializationCertificate]:
	"""Return a certified order; reject incomplete or cyclic conjunctive effects."""

	literal_tuple = tuple(literals or ())
	if len(literal_tuple) <= 1:
		indexes = tuple(range(len(literal_tuple)))
		return indexes, TransitionSerializationCertificate(indexes, (), True)
	actions = tuple(_ParsedAction.from_pddl(action) for action in domain.actions)
	plans_by_predicate = _plans_by_predicate(plan_library.plans)
	actions_by_name = {action.name: action for action in actions}
	goal_atoms = tuple(
		EffectAtom(
			predicate=predicate,
			arguments=tuple(_query_term(argument, index) for argument in arguments),
		)
		for index, (predicate, arguments) in enumerate(literal_tuple)
	)
	edges: set[tuple[int, int]] = set()
	for achiever_index, goal_atom in enumerate(goal_atoms):
		summary = _module_delete_summary(
			goal=goal_atom,
			plans_by_predicate=plans_by_predicate,
			actions_by_name=actions_by_name,
			visiting=frozenset(),
		)
		if not summary.complete:
			raise ValueError(
				"uncertified_conjunctive_transition: selected atomic module effect "
				f"summary is incomplete for {literal_tuple[achiever_index][0]}.",
			)
		for protected_index, protected_atom in enumerate(goal_atoms):
			if achiever_index == protected_index:
				continue
			if any(_atoms_unify(deleted, protected_atom) for deleted in summary.delete_atoms):
				edges.add((achiever_index, protected_index))
	ordered_indexes = _stable_topological_order(len(literal_tuple), edges)
	if ordered_indexes is None:
		raise ValueError(
			"cyclic_conjunctive_transition_not_certified: selected atomic modules "
			"have a cyclic delete-threat graph and no transition ranking certificate.",
		)
	certificate = TransitionSerializationCertificate(
		ordered_indexes=ordered_indexes,
		threat_edges=tuple(sorted(edges)),
		module_summaries_complete=True,
	)
	return ordered_indexes, certificate


def _plans_by_predicate(
	plans: Sequence[AgentSpeakPlan],
) -> dict[str, tuple[AgentSpeakPlan, ...]]:
	return {
		predicate: tuple(plan for plan in plans if plan.trigger.symbol == predicate)
		for predicate in sorted({plan.trigger.symbol for plan in plans})
	}


def _module_delete_summary(
	*,
	goal: EffectAtom,
	plans_by_predicate: Mapping[str, Sequence[AgentSpeakPlan]],
	actions_by_name: Mapping[str, _ParsedAction],
	visiting: frozenset[str],
) -> AtomicModuleEffectSummary:
	key = goal.predicate
	if key in visiting:
		return AtomicModuleEffectSummary((), True)
	plans = tuple(plans_by_predicate.get(goal.predicate, ()))
	if not plans:
		return AtomicModuleEffectSummary((), False)
	delete_atoms: list[EffectAtom] = []
	complete = True
	for plan_index, plan in enumerate(plans):
		if len(plan.trigger.arguments) != len(goal.arguments):
			complete = False
			continue
		binding = dict(zip(plan.trigger.arguments, goal.arguments))
		local_scope = f"{goal.predicate}:{plan_index}:{len(visiting)}"
		for step in plan.body:
			step_arguments = tuple(
				_bound_term(argument, binding=binding, scope=local_scope)
				for argument in step.arguments
			)
			if step.kind == "action":
				action = actions_by_name.get(step.symbol)
				if action is None or len(action.parameters) != len(step_arguments):
					complete = False
					continue
				action_binding = dict(zip(action.parameters, step_arguments))
				for effect in action.delete_effects:
					delete_atoms.append(
						EffectAtom(
							predicate=effect.predicate,
							arguments=tuple(
								action_binding.get(
									argument,
									EffectTerm(argument, variable_scope=local_scope),
								)
								for argument in effect.arguments
							),
						),
					)
			elif step.kind == "subgoal":
				nested = _module_delete_summary(
					goal=EffectAtom(step.symbol, step_arguments),
					plans_by_predicate=plans_by_predicate,
					actions_by_name=actions_by_name,
					visiting=visiting | {key},
				)
				delete_atoms.extend(nested.delete_atoms)
				complete = complete and nested.complete
			else:
				complete = False
	return AtomicModuleEffectSummary(
		delete_atoms=tuple(dict.fromkeys(delete_atoms)),
		complete=complete,
	)


def _query_term(argument: str, literal_index: int) -> EffectTerm:
	text = str(argument)
	if text and text[0].isupper():
		return EffectTerm(text, variable_scope=f"query:{literal_index}")
	return EffectTerm(text)


def _bound_term(
	argument: str,
	*,
	binding: Mapping[str, EffectTerm],
	scope: str,
) -> EffectTerm:
	if argument in binding:
		return binding[argument]
	if str(argument) and str(argument)[0].isupper():
		return EffectTerm(str(argument), variable_scope=scope)
	return EffectTerm(str(argument))


def _atoms_unify(left: EffectAtom, right: EffectAtom) -> bool:
	if left.predicate != right.predicate or len(left.arguments) != len(right.arguments):
		return False
	bindings: dict[tuple[str, str], EffectTerm] = {}
	return all(
		_terms_unify(left_term, right_term, bindings)
		for left_term, right_term in zip(left.arguments, right.arguments)
	)


def _terms_unify(
	left: EffectTerm,
	right: EffectTerm,
	bindings: dict[tuple[str, str], EffectTerm],
) -> bool:
	if not left.is_variable and not right.is_variable:
		return left.symbol == right.symbol
	if left.is_variable:
		key = (str(left.variable_scope), left.symbol)
		bound = bindings.get(key)
		if bound is not None:
			return _terms_unify(bound, right, bindings)
		bindings[key] = right
		return True
	key = (str(right.variable_scope), right.symbol)
	bound = bindings.get(key)
	if bound is not None:
		return _terms_unify(left, bound, bindings)
	bindings[key] = left
	return True


def _stable_topological_order(
	item_count: int,
	edges: set[tuple[int, int]],
) -> tuple[int, ...] | None:
	successors = {index: set() for index in range(item_count)}
	indegree = {index: 0 for index in range(item_count)}
	for source, target in edges:
		if target in successors[source]:
			continue
		successors[source].add(target)
		indegree[target] += 1
	ready = [index for index in range(item_count) if indegree[index] == 0]
	ordered: list[int] = []
	while ready:
		current = ready.pop(0)
		ordered.append(current)
		for target in sorted(successors[current]):
			indegree[target] -= 1
			if indegree[target] == 0:
				ready.append(target)
				ready.sort()
	if len(ordered) != item_count:
		return None
	return tuple(ordered)
