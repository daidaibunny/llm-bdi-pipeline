"""Conservative effect certificates for selected atomic AgentSpeak modules."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakPlan
from plan_library.models import PlanLibrary
from utils.pddl_parser import PDDLDomain

from .atomic_module_synthesis import _ParsedAction
from .pddl_types import parameter_type
from .pddl_types import type_closure


@dataclass(frozen=True)
class EffectTerm:
	"""A constant or a scoped lifted variable in an effect summary."""

	symbol: str
	variable_scope: str | None = None
	required_types: frozenset[str] = frozenset()

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
			"effect_summary_method": "pddl_typed_relational_fixed_point",
			"shared_query_variable_types_checked": True,
			"ordered_literal_indexes": list(self.ordered_indexes),
			"threat_edges": [list(edge) for edge in self.threat_edges],
			"module_summaries_complete": self.module_summaries_complete,
		}


def threat_safe_positive_literal_order(
	literals: Sequence[tuple[str, tuple[str, ...]]],
	*,
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	object_types: Mapping[str, str] | None = None,
) -> tuple[tuple[int, ...], TransitionSerializationCertificate]:
	"""Return a certified order; reject incomplete or cyclic conjunctive effects."""

	literal_tuple = tuple(literals or ())
	if len(literal_tuple) <= 1:
		indexes = tuple(range(len(literal_tuple)))
		return indexes, TransitionSerializationCertificate(indexes, (), True)
	actions = tuple(_ParsedAction.from_pddl(action) for action in domain.actions)
	plans_by_predicate = _plans_by_predicate(plan_library.plans)
	actions_by_name = {action.name: action for action in actions}
	predicate_types = {
		predicate.name: tuple(parameter_type(parameter) for parameter in predicate.parameters)
		for predicate in domain.predicates
	}
	known_object_types = {**dict(domain.constant_types), **dict(object_types or {})}
	query_variable_types = _query_variable_type_requirements(
		literal_tuple,
		predicate_types=predicate_types,
		type_tokens=domain.types,
	)
	goal_atoms = tuple(
		EffectAtom(
			predicate=predicate,
			arguments=tuple(
				_query_term(
					argument,
					required_type=tuple(predicate_types.get(predicate, ()))[position]
					if position < len(tuple(predicate_types.get(predicate, ())))
					else "object",
					known_object_types=known_object_types,
					query_variable_types=query_variable_types,
					type_tokens=domain.types,
				)
				for position, argument in enumerate(arguments)
			),
		)
		for predicate, arguments in literal_tuple
	)
	goal_indexes_by_predicate, goal_indexes_by_constant, goal_indexes_by_variable = (
		_index_goal_atoms(goal_atoms)
	)
	summary_cache: dict[
		tuple[str, tuple[tuple[str, ...], ...]],
		tuple[EffectAtom, AtomicModuleEffectSummary],
	] = {}
	edges: set[tuple[int, int]] = set()
	for achiever_index, goal_atom in enumerate(goal_atoms):
		summary = _cached_module_delete_summary(
			goal_atom,
			cache=summary_cache,
			plans_by_predicate=plans_by_predicate,
			actions_by_name=actions_by_name,
			predicate_types=predicate_types,
			type_tokens=domain.types,
		)
		if not summary.complete:
			raise ValueError(
				"uncertified_conjunctive_transition: selected atomic module effect "
				f"summary is incomplete for {literal_tuple[achiever_index][0]}.",
			)
		for deleted in summary.delete_atoms:
			for protected_index in _indexed_goal_candidates(
				deleted,
				goal_indexes_by_predicate=goal_indexes_by_predicate,
				goal_indexes_by_constant=goal_indexes_by_constant,
				goal_indexes_by_variable=goal_indexes_by_variable,
			):
				if achiever_index == protected_index:
					continue
				if _atoms_unify(
					deleted,
					goal_atoms[protected_index],
					type_tokens=domain.types,
				):
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


def _cached_module_delete_summary(
	goal: EffectAtom,
	*,
	cache: dict[
		tuple[str, tuple[tuple[str, ...], ...]],
		tuple[EffectAtom, AtomicModuleEffectSummary],
	],
	plans_by_predicate: Mapping[str, Sequence[AgentSpeakPlan]],
	actions_by_name: Mapping[str, _ParsedAction],
	predicate_types: Mapping[str, Sequence[str]],
	type_tokens: Sequence[str],
) -> AtomicModuleEffectSummary:
	type_shape = tuple(tuple(sorted(argument.required_types)) for argument in goal.arguments)
	cache_key = (goal.predicate, type_shape)
	cached = cache.get(cache_key)
	if cached is None:
		generic_goal = EffectAtom(
			goal.predicate,
			tuple(
				EffectTerm(
					f"H{index}",
					variable_scope="query",
					required_types=argument.required_types,
				)
				for index, argument in enumerate(goal.arguments)
			),
		)
		cached = (
			generic_goal,
			_module_delete_summary(
				goal=generic_goal,
				plans_by_predicate=plans_by_predicate,
				actions_by_name=actions_by_name,
				predicate_types=predicate_types,
				type_tokens=type_tokens,
			),
		)
		cache[cache_key] = cached
	generic_goal, generic_summary = cached
	head_binding = {
		generic_argument.symbol: actual_argument
		for generic_argument, actual_argument in zip(generic_goal.arguments, goal.arguments)
	}
	return AtomicModuleEffectSummary(
		delete_atoms=tuple(
			_instantiate_query_anchors(atom, head_binding=head_binding)
			for atom in generic_summary.delete_atoms
		),
		complete=generic_summary.complete,
	)


def _instantiate_query_anchors(
	atom: EffectAtom,
	*,
	head_binding: Mapping[str, EffectTerm],
) -> EffectAtom:
	return EffectAtom(
		atom.predicate,
		tuple(
			head_binding.get(argument.symbol, argument)
			if argument.variable_scope == "query"
			else argument
			for argument in atom.arguments
		),
	)


def _index_goal_atoms(
	goal_atoms: Sequence[EffectAtom],
) -> tuple[
	dict[str, set[int]],
	dict[tuple[str, int, str], set[int]],
	dict[tuple[str, int], set[int]],
]:
	by_predicate: dict[str, set[int]] = {}
	by_constant: dict[tuple[str, int, str], set[int]] = {}
	by_variable: dict[tuple[str, int], set[int]] = {}
	for index, atom in enumerate(goal_atoms):
		by_predicate.setdefault(atom.predicate, set()).add(index)
		for position, argument in enumerate(atom.arguments):
			if argument.is_variable:
				by_variable.setdefault((atom.predicate, position), set()).add(index)
			else:
				by_constant.setdefault(
					(atom.predicate, position, argument.symbol),
					set(),
				).add(index)
	return by_predicate, by_constant, by_variable


def _indexed_goal_candidates(
	delete_atom: EffectAtom,
	*,
	goal_indexes_by_predicate: Mapping[str, set[int]],
	goal_indexes_by_constant: Mapping[tuple[str, int, str], set[int]],
	goal_indexes_by_variable: Mapping[tuple[str, int], set[int]],
) -> set[int]:
	candidates = set(goal_indexes_by_predicate.get(delete_atom.predicate, set()))
	for position, argument in enumerate(delete_atom.arguments):
		if argument.is_variable:
			continue
		compatible_at_position = set(
			goal_indexes_by_constant.get(
				(delete_atom.predicate, position, argument.symbol),
				set(),
			),
		)
		compatible_at_position.update(
			goal_indexes_by_variable.get((delete_atom.predicate, position), set()),
		)
		candidates.intersection_update(compatible_at_position)
		if not candidates:
			break
	return candidates


def _module_delete_summary(
	*,
	goal: EffectAtom,
	plans_by_predicate: Mapping[str, Sequence[AgentSpeakPlan]],
	actions_by_name: Mapping[str, _ParsedAction],
	predicate_types: Mapping[str, Sequence[str]],
	type_tokens: Sequence[str],
) -> AtomicModuleEffectSummary:
	pending = [_canonicalize_effect_atom(goal, namespace="module-call")]
	seen: set[EffectAtom] = set()
	delete_atoms: list[EffectAtom] = []
	complete = True
	while pending:
		current_goal = pending.pop()
		if current_goal in seen:
			continue
		seen.add(current_goal)
		plans = tuple(plans_by_predicate.get(current_goal.predicate, ()))
		if not plans:
			complete = False
			continue
		matched_plan = False
		for plan_index, plan in enumerate(plans):
			binding = _bind_plan_trigger(plan, current_goal)
			if binding is None:
				continue
			matched_plan = True
			local_scope = (
				f"{current_goal.predicate}:{len(seen)}:{plan_index}"
			)
			for step in plan.body:
				if step.kind == "action":
					action = actions_by_name.get(step.symbol)
					if action is None or len(action.parameters) != len(step.arguments):
						complete = False
						continue
					step_arguments = tuple(
						_bound_term(
							argument,
							binding=binding,
							scope=local_scope,
							required_type=action.parameter_types.get(parameter, "object"),
							type_tokens=type_tokens,
						)
						for parameter, argument in zip(action.parameters, step.arguments)
					)
					action_binding = dict(zip(action.parameters, step_arguments))
					for effect in action.delete_effects:
						delete_atoms.append(
							_canonicalize_effect_atom(
								EffectAtom(
									predicate=effect.predicate,
									arguments=tuple(
										action_binding.get(
											argument,
											EffectTerm(
												argument,
												variable_scope=local_scope,
											),
										)
										for argument in effect.arguments
									),
								),
								namespace="delete-effect",
							),
						)
				elif step.kind == "subgoal":
					subgoal_types = tuple(predicate_types.get(step.symbol, ()))
					step_arguments = tuple(
						_bound_term(
							argument,
							binding=binding,
							scope=local_scope,
							required_type=(
								subgoal_types[position]
								if position < len(subgoal_types)
								else "object"
							),
							type_tokens=type_tokens,
						)
						for position, argument in enumerate(step.arguments)
					)
					pending.append(
						_canonicalize_effect_atom(
							EffectAtom(step.symbol, step_arguments),
							namespace="module-call",
						),
					)
				else:
					complete = False
		if not matched_plan:
			complete = False
	return AtomicModuleEffectSummary(
		delete_atoms=tuple(dict.fromkeys(delete_atoms)),
		complete=complete,
	)


def _bind_plan_trigger(
	plan: AgentSpeakPlan,
	goal: EffectAtom,
) -> dict[str, EffectTerm] | None:
	trigger_arguments = tuple(plan.trigger.arguments)
	if len(trigger_arguments) != len(goal.arguments):
		return None
	binding: dict[str, EffectTerm] = {}
	for trigger_argument, goal_argument in zip(trigger_arguments, goal.arguments):
		if _is_agentspeak_variable(trigger_argument):
			previous = binding.get(trigger_argument)
			if previous is not None and previous != goal_argument:
				return None
			binding[trigger_argument] = goal_argument
			continue
		if not goal_argument.is_variable and trigger_argument != goal_argument.symbol:
			return None
	return binding


def _is_agentspeak_variable(argument: str) -> bool:
	text = str(argument or "")
	return bool(text) and (text[0].isupper() or text[0] == "_")


def _canonicalize_effect_atom(atom: EffectAtom, *, namespace: str) -> EffectAtom:
	variable_map: dict[tuple[str, str], EffectTerm] = {}
	arguments: list[EffectTerm] = []
	for argument in atom.arguments:
		if not argument.is_variable or argument.variable_scope == "query":
			arguments.append(argument)
			continue
		key = (str(argument.variable_scope), argument.symbol)
		variable_map.setdefault(
			key,
			EffectTerm(
				f"V{len(variable_map)}",
				variable_scope=namespace,
				required_types=argument.required_types,
			),
		)
		arguments.append(variable_map[key])
	return EffectAtom(atom.predicate, tuple(arguments))


def _query_term(
	argument: str,
	*,
	required_type: str,
	known_object_types: Mapping[str, str],
	query_variable_types: Mapping[str, frozenset[str]],
	type_tokens: Sequence[str],
) -> EffectTerm:
	text = str(argument)
	if text and text[0].isupper():
		return EffectTerm(
			text,
			variable_scope="query",
			required_types=query_variable_types.get(
				text,
				frozenset((required_type or "object",)),
			),
		)
	required_types = frozenset(
		(str(known_object_types.get(text) or "object"), required_type or "object"),
	)
	if not _required_types_are_consistent(required_types, type_tokens):
		raise ValueError(
			"ill_typed_conjunctive_transition: ground query object "
			f"{text!r} is incompatible with required type {required_type!r}.",
		)
	return EffectTerm(text, required_types=required_types)


def _query_variable_type_requirements(
	literals: Sequence[tuple[str, tuple[str, ...]]],
	*,
	predicate_types: Mapping[str, Sequence[str]],
	type_tokens: Sequence[str],
) -> dict[str, frozenset[str]]:
	required_by_variable: dict[str, set[str]] = {}
	for predicate, arguments in literals:
		signature = tuple(predicate_types.get(predicate, ()))
		for position, argument in enumerate(arguments):
			text = str(argument)
			if not text or not text[0].isupper():
				continue
			required_by_variable.setdefault(text, set()).add(
				signature[position] if position < len(signature) else "object",
			)
	result = {
		variable: frozenset(required_types)
		for variable, required_types in required_by_variable.items()
	}
	for variable, required_types in result.items():
		if not _required_types_are_consistent(required_types, type_tokens):
			raise ValueError(
				"ill_typed_conjunctive_transition: shared query variable "
				f"{variable!r} has incompatible PDDL type requirements "
				f"{sorted(required_types)!r}.",
			)
	return result


def _bound_term(
	argument: str,
	*,
	binding: Mapping[str, EffectTerm],
	scope: str,
	required_type: str,
	type_tokens: Sequence[str],
) -> EffectTerm:
	if argument in binding:
		bound = binding[argument]
		merged_types = frozenset((*bound.required_types, required_type))
		if not _required_types_are_consistent(merged_types, type_tokens):
			return EffectTerm(
				bound.symbol,
				variable_scope=bound.variable_scope,
				required_types=frozenset(("__inconsistent_type__",)),
			)
		return EffectTerm(
			bound.symbol,
			variable_scope=bound.variable_scope,
			required_types=merged_types,
		)
	if str(argument) and str(argument)[0].isupper():
		return EffectTerm(
			str(argument),
			variable_scope=scope,
			required_types=frozenset((required_type,)),
		)
	return EffectTerm(str(argument), required_types=frozenset((required_type,)))


def _atoms_unify(
	left: EffectAtom,
	right: EffectAtom,
	*,
	type_tokens: Sequence[str],
) -> bool:
	if left.predicate != right.predicate or len(left.arguments) != len(right.arguments):
		return False
	bindings: dict[tuple[str, str], EffectTerm] = {}
	return all(
		_terms_unify(left_term, right_term, bindings, type_tokens=type_tokens)
		for left_term, right_term in zip(left.arguments, right.arguments)
	)


def _terms_unify(
	left: EffectTerm,
	right: EffectTerm,
	bindings: dict[tuple[str, str], EffectTerm],
	*,
	type_tokens: Sequence[str],
) -> bool:
	if not _terms_have_compatible_types(left, right, type_tokens):
		return False
	if not left.is_variable and not right.is_variable:
		return left.symbol == right.symbol
	if left.is_variable:
		key = (str(left.variable_scope), left.symbol)
		bound = bindings.get(key)
		if bound is not None:
			return _terms_unify(bound, right, bindings, type_tokens=type_tokens)
		bindings[key] = right
		return True
	key = (str(right.variable_scope), right.symbol)
	bound = bindings.get(key)
	if bound is not None:
		return _terms_unify(left, bound, bindings, type_tokens=type_tokens)
	bindings[key] = left
	return True


def _terms_have_compatible_types(
	left: EffectTerm,
	right: EffectTerm,
	type_tokens: Sequence[str],
) -> bool:
	if "__inconsistent_type__" in left.required_types | right.required_types:
		return False
	return _required_types_are_consistent(
		left.required_types | right.required_types,
		type_tokens,
	)


def _required_types_are_consistent(
	required_types: frozenset[str],
	type_tokens: Sequence[str],
) -> bool:
	non_object = tuple(type_name for type_name in required_types if type_name != "object")
	return all(
		left == right
		or left in type_closure(right, type_tokens)
		or right in type_closure(left, type_tokens)
		for left in non_object
		for right in non_object
	)


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
	heapq.heapify(ready)
	ordered: list[int] = []
	while ready:
		current = heapq.heappop(ready)
		ordered.append(current)
		for target in sorted(successors[current]):
			indegree[target] -= 1
			if indegree[target] == 0:
				heapq.heappush(ready, target)
	if len(ordered) != item_count:
		return None
	return tuple(ordered)
