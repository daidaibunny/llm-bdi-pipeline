"""Conservative effect certificates for selected atomic AgentSpeak modules."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
import re
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary
from utils.pddl_parser import PDDLDomain

from .atomic_module_synthesis import _ParsedAction
from .atomic_module_synthesis import _FunctionalPredicateGroup
from .atomic_module_synthesis import _functional_predicate_groups
from .atomic_module_synthesis import PDDLLiteralSchema
from .pddl_types import OBJ_TP_PREDICATE
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
	"""Conditional completion effects for selected branches of one module call."""

	conditional_delete_effects: tuple["ConditionalDeleteEffect", ...]
	conditional_add_effects: tuple["ConditionalAddEffect", ...]
	complete: bool

	@property
	def delete_atoms(self) -> tuple[EffectAtom, ...]:
		return tuple(effect.delete_atom for effect in self.conditional_delete_effects)

	@property
	def add_atoms(self) -> tuple[EffectAtom, ...]:
		return tuple(effect.add_atom for effect in self.conditional_add_effects)


@dataclass(frozen=True)
class ConditionalDeleteEffect:
	"""One delete effect guarded by the relational context of its plan branch."""

	delete_atom: EffectAtom
	positive_context: tuple[EffectAtom, ...] = ()
	negative_context: tuple[EffectAtom, ...] = ()
	equalities: tuple[tuple[EffectTerm, EffectTerm], ...] = ()
	disequalities: tuple[tuple[EffectTerm, EffectTerm], ...] = ()


@dataclass(frozen=True)
class ConditionalAddEffect:
	"""One add effect guarded by the relational context of its plan branch."""

	add_atom: EffectAtom
	positive_context: tuple[EffectAtom, ...] = ()
	negative_context: tuple[EffectAtom, ...] = ()
	equalities: tuple[tuple[EffectTerm, EffectTerm], ...] = ()
	disequalities: tuple[tuple[EffectTerm, EffectTerm], ...] = ()


@dataclass(frozen=True)
class _BranchCondition:
	positive_context: tuple[EffectAtom, ...] = ()
	negative_context: tuple[EffectAtom, ...] = ()
	equalities: tuple[tuple[EffectTerm, EffectTerm], ...] = ()
	disequalities: tuple[tuple[EffectTerm, EffectTerm], ...] = ()


@dataclass(frozen=True)
class _ActionOnlyPlanEffectSummary:
	"""Exact completion effects and branch condition for one finite primitive macro."""

	conditional_deletes: tuple[ConditionalDeleteEffect, ...]
	add_atoms: tuple[EffectAtom, ...]
	branch_condition: _BranchCondition


@dataclass(frozen=True)
class TransitionSerializationCertificate:
	"""Proof record for one conjunctive DFA guard serialization."""

	ordered_indexes: tuple[int, ...]
	threat_edges: tuple[tuple[int, int], ...]
	module_summaries_complete: bool
	conditional_effects_checked: bool = True
	functional_invariant_count: int = 0
	observation_boundary: str = "atomic_module_completion"
	serialization_strategy: str = "universal_acyclic_threat_order"
	ranking_relation: str | None = None
	ranking_relation_anchor_position: int | None = None
	ranking_assumptions: tuple[str, ...] = ()
	selected_branch_names_by_predicate: tuple[tuple[str, tuple[str, ...]], ...] = ()
	selected_branch_names_by_literal: tuple[
		tuple[int, str, tuple[str, ...]],
		...,
	] = ()
	negative_guard_count: int = 0
	negative_guard_preservation_checked: bool = False
	negative_guard_preserved: bool = True
	negative_guard_threats: tuple[tuple[int, int], ...] = ()

	def to_dict(self) -> dict[str, object]:
		payload: dict[str, object] = {
			"certificate_kind": "atomic_module_effect_serialization",
			"effect_summary_method": "pddl_typed_conditional_relational_fixed_point",
			"shared_query_variable_types_checked": True,
			"ordered_literal_indexes": list(self.ordered_indexes),
			"threat_edges": [list(edge) for edge in self.threat_edges],
			"module_summaries_complete": self.module_summaries_complete,
			"conditional_effects_checked": self.conditional_effects_checked,
			"functional_invariant_count": self.functional_invariant_count,
			"observation_boundary": self.observation_boundary,
			"serialization_strategy": self.serialization_strategy,
			"ranking_relation": self.ranking_relation,
			"ranking_relation_anchor_position": self.ranking_relation_anchor_position,
			"ranking_assumptions": list(self.ranking_assumptions),
			"negative_guard_count": self.negative_guard_count,
			"negative_guard_preservation_checked": (
				self.negative_guard_preservation_checked
			),
			"negative_guard_preserved": self.negative_guard_preserved,
			"negative_guard_threats": [
				list(edge) for edge in self.negative_guard_threats
			],
		}
		if self.selected_branch_names_by_predicate:
			payload["selected_branch_names_by_predicate"] = {
				predicate: list(plan_names)
				for predicate, plan_names in self.selected_branch_names_by_predicate
			}
		if self.selected_branch_names_by_literal:
			payload["selected_branch_names_by_literal"] = [
				{
					"literal_index": literal_index,
					"literal": literal,
					"plan_names": list(plan_names),
				}
				for literal_index, literal, plan_names in self.selected_branch_names_by_literal
			]
		return payload


@dataclass(frozen=True)
class PreservationSafePlanSelection:
	"""Query-local branch portfolio with an enforced preservation certificate."""

	ordered_indexes: tuple[int, ...]
	literals: tuple[tuple[str, tuple[str, ...]], ...]
	plans_by_predicate: Mapping[str, tuple[AgentSpeakPlan, ...]]
	plans_by_literal_index: Mapping[int, tuple[AgentSpeakPlan, ...]]
	certificate: TransitionSerializationCertificate


def query_local_preservation_alias_plans(
	selection: PreservationSafePlanSelection,
	*,
	helper_prefix: str,
) -> tuple[tuple[AgentSpeakPlan, ...], Mapping[str, str]]:
	"""Copy selected branches under query-local triggers that enforce the proof."""

	aliases: list[AgentSpeakPlan] = []
	helper_by_literal: dict[str, str] = {}
	portfolio_keys_by_predicate: dict[str, set[tuple[str, ...]]] = {}
	for literal_index, plans in selection.plans_by_literal_index.items():
		predicate = selection.literals[literal_index][0]
		portfolio_keys_by_predicate.setdefault(predicate, set()).add(
			tuple(plan.plan_name for plan in plans),
		)
	emitted_helpers: set[str] = set()
	for literal_index in selection.ordered_indexes:
		predicate, arguments = selection.literals[literal_index]
		plans = selection.plans_by_literal_index[literal_index]
		is_shared_portfolio = len(portfolio_keys_by_predicate[predicate]) == 1
		helper_symbol = _safe_agentspeak_identifier(
			f"{helper_prefix}_selected_{predicate}"
			if is_shared_portfolio
			else f"{helper_prefix}_selected_{literal_index + 1}_{predicate}",
		)
		literal_text = predicate if not arguments else f"{predicate}({', '.join(arguments)})"
		helper_by_literal[literal_text] = helper_symbol
		helper_by_literal.setdefault(predicate, helper_symbol)
		if helper_symbol in emitted_helpers:
			continue
		emitted_helpers.add(helper_symbol)
		for branch_index, plan in enumerate(plans, start=1):
			rewritten_body = tuple(
				AgentSpeakBodyStep(step.kind, helper_symbol, step.arguments)
				if step.kind == "subgoal"
				and step.symbol == predicate
				and tuple(step.arguments) == tuple(plan.trigger.arguments)
				else step
				for step in plan.body
			)
			aliases.append(
				AgentSpeakPlan(
					plan_name=f"{helper_symbol}_branch_{branch_index}_{plan.plan_name}",
					trigger=AgentSpeakTrigger(
						plan.trigger.event_type,
						helper_symbol,
						plan.trigger.arguments,
					),
					context=plan.context,
					body=rewritten_body,
					source_instruction_ids=plan.source_instruction_ids,
					binding_certificate=(
						*plan.binding_certificate,
						{
							"artifact_family": "temporal_goal_dfa_append",
							"wrapper_role": "query_local_preservation_safe_branch",
							"source_atomic_plan": plan.plan_name,
							"protected_literal_prefix_length": max(
								selection.ordered_indexes.index(index)
								for index in selection.ordered_indexes
								if selection.literals[index][0] == predicate
								and selection.plans_by_literal_index[index] == plans
							),
							"serialization_strategy": (
								selection.certificate.serialization_strategy
							),
						},
					),
				),
				)
	return tuple(aliases), helper_by_literal


def negative_guard_establishment_alias_plans(
	literals: Sequence[tuple[str, tuple[str, ...]]],
	*,
	negative_literals: Sequence[tuple[str, tuple[str, ...]]],
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	helper_prefix: str,
	object_types: Mapping[str, str] | None = None,
) -> tuple[
	tuple[AgentSpeakPlan, ...],
	Mapping[int, tuple[str, tuple[str, ...]]],
	Mapping[str, object],
]:
	"""Select finite branches whose net effects establish forbidden-atom absence."""

	literal_tuple = tuple(literals or ())
	negative_literal_tuple = tuple(negative_literals or ())
	if not negative_literal_tuple:
		return (), {}, {
			"negative_guard_establishment_checked": False,
			"negative_guard_establishable": True,
			"negative_guard_establishers": {},
		}
	actions = tuple(_ParsedAction.from_pddl(action) for action in domain.actions)
	actions_by_name = {action.name: action for action in actions}
	functional_groups = _functional_predicate_groups(actions, domain.types)
	predicate_types = {
		predicate.name: tuple(parameter_type(parameter) for parameter in predicate.parameters)
		for predicate in domain.predicates
	}
	known_object_types = {**dict(domain.constant_types), **dict(object_types or {})}
	query_variable_types = _query_variable_type_requirements(
		(*literal_tuple, *negative_literal_tuple),
		predicate_types=predicate_types,
		type_tokens=domain.types,
	)
	goal_atoms = _query_effect_atoms(
		literal_tuple,
		predicate_types=predicate_types,
		known_object_types=known_object_types,
		query_variable_types=query_variable_types,
		type_tokens=domain.types,
	)
	forbidden_atoms = _query_effect_atoms(
		negative_literal_tuple,
		predicate_types=predicate_types,
		known_object_types=known_object_types,
		query_variable_types=query_variable_types,
		type_tokens=domain.types,
	)
	plans_by_predicate = _plans_by_predicate(plan_library.plans)
	query_arguments = tuple(
		dict.fromkeys(
			argument
			for _predicate, arguments in (*literal_tuple, *negative_literal_tuple)
			for argument in arguments
			if _is_agentspeak_variable(argument)
		)
	)
	aliases: list[AgentSpeakPlan] = []
	helper_by_negative_index: dict[int, tuple[str, tuple[str, ...]]] = {}
	establishers: dict[str, list[str]] = {}
	for negative_index, forbidden in enumerate(forbidden_atoms):
		helper_symbol = _safe_agentspeak_identifier(
			f"{helper_prefix}_establish_not_{forbidden.predicate}_{negative_index + 1}"
		)
		selected_forbidden: list[AgentSpeakPlan] = []
		for positive_index, (goal, literal_signature) in enumerate(
			zip(goal_atoms, literal_tuple)
		):
			for plan_index, plan in enumerate(plans_by_predicate.get(goal.predicate, ())):
				summary = _action_only_plan_effect_summary(
					plan,
					goal=goal,
					plan_index=plan_index,
					actions_by_name=actions_by_name,
					predicate_types=predicate_types,
					type_tokens=domain.types,
				)
				if summary is None or not plan.body:
					continue
				if not _action_only_summary_achieves_goal(
					summary,
					goal=goal,
					body_is_empty=False,
				):
					continue
				if not any(
					_effect_atom_has_same_identity(effect.delete_atom, forbidden)
					for effect in summary.conditional_deletes
				):
					continue
				if _summary_may_add_any_forbidden(
					summary,
					forbidden_atoms=forbidden_atoms,
					type_tokens=domain.types,
				):
					continue
				if _summary_may_delete_positive_sibling(
					summary,
					goal_atoms=goal_atoms,
					achiever_index=positive_index,
					functional_groups=functional_groups,
					type_tokens=domain.types,
				):
					continue
				alias = _ground_establishment_alias(
					plan,
					helper_symbol=helper_symbol,
					helper_arguments=query_arguments,
					target_arguments=literal_signature[1],
					negative_atom=_effect_atom_text(forbidden),
				)
				selected_forbidden.append(alias)
		selected_forbidden.extend(
			_direct_negative_action_establishers(
				actions=actions,
				forbidden=forbidden,
				forbidden_atoms=forbidden_atoms,
				goal_atoms=goal_atoms,
				helper_symbol=helper_symbol,
				helper_arguments=query_arguments,
				type_tokens=domain.types,
			),
		)
		if selected_forbidden:
			helper_by_negative_index[negative_index] = (
				helper_symbol,
				query_arguments,
			)
			aliases.extend(selected_forbidden)
			establishers[_effect_atom_text(forbidden)] = [
				plan.plan_name for plan in selected_forbidden
			]
	return tuple(aliases), helper_by_negative_index, {
		"negative_guard_establishment_checked": True,
		"negative_guard_establishable": (
			len(helper_by_negative_index) == len(forbidden_atoms)
		),
		"negative_guard_establishers": establishers,
	}


def _direct_negative_action_establishers(
	*,
	actions: Sequence[_ParsedAction],
	forbidden: EffectAtom,
	forbidden_atoms: Sequence[EffectAtom],
	goal_atoms: Sequence[EffectAtom],
	helper_symbol: str,
	helper_arguments: tuple[str, ...],
	type_tokens: Sequence[str],
) -> tuple[AgentSpeakPlan, ...]:
	"""Compile one-step PDDL deleters whose net effects preserve the full guard."""

	plans: list[AgentSpeakPlan] = []
	for action_index, action in enumerate(actions, start=1):
		for delete_index, delete_effect in enumerate(action.delete_effects, start=1):
			binding = _bind_delete_schema_to_forbidden(
				action=action,
				delete_effect=delete_effect,
				forbidden=forbidden,
				preferred_add_atoms=goal_atoms,
				type_tokens=type_tokens,
			)
			if binding is None:
				continue
			mapped_deletes = tuple(
				_mapped_action_schema_atom(effect, binding=binding)
				for effect in action.delete_effects
			)
			mapped_adds = tuple(
				_mapped_action_schema_atom(effect, binding=binding)
				for effect in action.add_effects
			)
			if not any(
				_effect_atom_has_same_identity(effect, forbidden)
				for effect in mapped_deletes
			):
				continue
			if any(
				_atoms_unify(effect, guarded, type_tokens=type_tokens)
				for effect in mapped_adds
				for guarded in forbidden_atoms
			):
				continue
			if any(
				_atoms_unify(effect, protected, type_tokens=type_tokens)
				for effect in mapped_deletes
				for protected in goal_atoms
			):
				continue
			context = _direct_negative_action_context(
				action=action,
				binding=binding,
			)
			if context is None:
				continue
			plans.append(
				AgentSpeakPlan(
					plan_name=(
						f"{helper_symbol}_{action.name}_{action_index}_{delete_index}"
					),
					trigger=AgentSpeakTrigger(
						"achievement_goal",
						helper_symbol,
						helper_arguments,
					),
					context=context,
					body=(
						AgentSpeakBodyStep(
							"action",
							action.name,
							tuple(binding[parameter].symbol for parameter in action.parameters),
						),
					),
					binding_certificate=(
						{
							"artifact_family": "temporal_goal_dfa_append",
							"wrapper_role": (
								"query_local_negative_guard_establishment_branch"
							),
							"source_action": action.name,
							"established_negative_atom": _effect_atom_text(forbidden),
							"certificate_kind": "pddl_single_action_must_delete",
							"positive_siblings_preserved": True,
							"negative_siblings_preserved": True,
						},
					),
				),
			)
	return tuple(plans)


def _bind_delete_schema_to_forbidden(
	*,
	action: _ParsedAction,
	delete_effect: PDDLLiteralSchema,
	forbidden: EffectAtom,
	preferred_add_atoms: Sequence[EffectAtom] = (),
	type_tokens: Sequence[str],
) -> dict[str, EffectTerm] | None:
	if (
		delete_effect.predicate != forbidden.predicate
		or len(delete_effect.arguments) != len(forbidden.arguments)
	):
		return None
	binding: dict[str, EffectTerm] = {}
	for schema_argument, forbidden_term in zip(
		delete_effect.arguments,
		forbidden.arguments,
	):
		if schema_argument not in action.parameters:
			if forbidden_term.is_variable or forbidden_term.symbol != schema_argument:
				return None
			continue
		required_type = action.parameter_types.get(schema_argument, "object")
		if not _required_types_are_consistent(
			forbidden_term.required_types | frozenset((required_type,)),
			type_tokens,
		):
			return None
		previous = binding.get(schema_argument)
		if previous is not None and previous != forbidden_term:
			return None
		binding[schema_argument] = forbidden_term
	for preferred in preferred_add_atoms:
		for add_effect in action.add_effects:
			candidate = _extend_action_schema_effect_binding(
				binding,
				action=action,
				schema=add_effect,
				target=preferred,
				type_tokens=type_tokens,
			)
			if candidate is not None:
				binding = candidate
				break
	used_symbols = {term.symbol for term in binding.values()}
	local_index = 0
	local_scope = f"negative-deleter:{action.name}"
	for parameter in action.parameters:
		if parameter in binding:
			continue
		while f"V{local_index}" in used_symbols:
			local_index += 1
		symbol = f"V{local_index}"
		local_index += 1
		used_symbols.add(symbol)
		binding[parameter] = EffectTerm(
			symbol,
			variable_scope=local_scope,
			required_types=frozenset((action.parameter_types.get(parameter, "object"),)),
		)
	return binding


def _extend_action_schema_effect_binding(
	binding: Mapping[str, EffectTerm],
	*,
	action: _ParsedAction,
	schema: PDDLLiteralSchema,
	target: EffectAtom,
	type_tokens: Sequence[str],
) -> dict[str, EffectTerm] | None:
	"""Bind free action parameters from a compatible query guard atom."""

	if schema.predicate != target.predicate or len(schema.arguments) != len(
		target.arguments
	):
		return None
	result = dict(binding)
	for schema_argument, target_term in zip(schema.arguments, target.arguments):
		if schema_argument not in action.parameters:
			if target_term.is_variable or target_term.symbol != schema_argument:
				return None
			continue
		required_type = action.parameter_types.get(schema_argument, "object")
		if not _required_types_are_consistent(
			target_term.required_types | frozenset((required_type,)),
			type_tokens,
		):
			return None
		previous = result.get(schema_argument)
		if previous is not None and previous != target_term:
			return None
		result[schema_argument] = target_term
	return result


def _mapped_action_schema_atom(
	literal: PDDLLiteralSchema,
	*,
	binding: Mapping[str, EffectTerm],
) -> EffectAtom:
	return EffectAtom(
		literal.predicate,
		tuple(
			binding.get(argument, EffectTerm(argument))
			for argument in literal.arguments
		),
	)


def _direct_negative_action_context(
	*,
	action: _ParsedAction,
	binding: Mapping[str, EffectTerm],
) -> tuple[str, ...] | None:
	contexts: list[str] = []
	positive_parameters = {
		argument
		for precondition in action.preconditions
		if precondition.is_positive
		for argument in precondition.arguments
		if argument in action.parameters
	}
	for parameter in action.parameters:
		term = binding[parameter]
		if not term.is_variable or term.variable_scope == "query":
			continue
		required_type = action.parameter_types.get(parameter, "object")
		if required_type == "object" and parameter not in positive_parameters:
			return None
	for parameter in action.parameters:
		term = binding[parameter]
		required_type = action.parameter_types.get(parameter, "object")
		if required_type != "object":
			contexts.append(f"{OBJ_TP_PREDICATE}({term.symbol}, {required_type})")
	for precondition in (
		*(item for item in action.preconditions if item.is_positive),
		*(item for item in action.preconditions if not item.is_positive),
	):
		atom = _mapped_action_schema_atom(precondition, binding=binding)
		call = _effect_atom_text(atom)
		contexts.append(call if precondition.is_positive else f"not {call}")
	return tuple(dict.fromkeys(contexts))


def _summary_may_add_any_forbidden(
	summary: _ActionOnlyPlanEffectSummary,
	*,
	forbidden_atoms: Sequence[EffectAtom],
	type_tokens: Sequence[str],
) -> bool:
	return any(
		_conditional_add_can_violate_negative(
			ConditionalAddEffect(
				add_atom=add_atom,
				positive_context=summary.branch_condition.positive_context,
				negative_context=summary.branch_condition.negative_context,
				equalities=summary.branch_condition.equalities,
				disequalities=summary.branch_condition.disequalities,
			),
			forbidden=forbidden,
			type_tokens=type_tokens,
		)
		for add_atom in summary.add_atoms
		for forbidden in forbidden_atoms
	)


def _summary_may_delete_positive_sibling(
	summary: _ActionOnlyPlanEffectSummary,
	*,
	goal_atoms: Sequence[EffectAtom],
	achiever_index: int,
	functional_groups: Sequence[_FunctionalPredicateGroup],
	type_tokens: Sequence[str],
) -> bool:
	return any(
		_conditional_delete_can_threaten(
			effect,
			protected=protected,
			functional_groups=functional_groups,
			type_tokens=type_tokens,
		)
		for effect in summary.conditional_deletes
		for protected_index, protected in enumerate(goal_atoms)
		if protected_index != achiever_index
	)


def _ground_establishment_alias(
	plan: AgentSpeakPlan,
	*,
	helper_symbol: str,
	helper_arguments: tuple[str, ...],
	target_arguments: tuple[str, ...],
	negative_atom: str,
) -> AgentSpeakPlan:
	substitution = {
		formal: actual
		for formal, actual in zip(plan.trigger.arguments, target_arguments)
		if _is_agentspeak_variable(formal)
	}
	return AgentSpeakPlan(
		plan_name=f"{helper_symbol}_{plan.plan_name}",
		trigger=AgentSpeakTrigger(
			plan.trigger.event_type,
			helper_symbol,
			helper_arguments,
		),
		context=tuple(
			_substitute_agentspeak_identifiers(item, substitution)
			for item in plan.context
		),
		body=tuple(
			AgentSpeakBodyStep(
				step.kind,
				step.symbol,
				tuple(substitution.get(argument, argument) for argument in step.arguments),
			)
			for step in plan.body
		),
		source_instruction_ids=plan.source_instruction_ids,
		binding_certificate=(
			*plan.binding_certificate,
			{
				"artifact_family": "temporal_goal_dfa_append",
				"wrapper_role": "query_local_negative_guard_establishment_branch",
				"source_atomic_plan": plan.plan_name,
				"established_negative_atom": negative_atom,
				"certificate_kind": "pddl_net_must_delete_with_positive_preservation",
			},
		),
	)


def _substitute_agentspeak_identifiers(
	text: str,
	substitution: Mapping[str, str],
) -> str:
	if not substitution:
		return text
	pattern = re.compile(
		r"(?<![A-Za-z0-9_])(" + "|".join(
			re.escape(key) for key in sorted(substitution, key=len, reverse=True)
		) + r")(?![A-Za-z0-9_])"
	)
	return pattern.sub(lambda match: substitution[match.group(1)], text)


def _effect_atom_text(atom: EffectAtom) -> str:
	arguments = ", ".join(argument.symbol for argument in atom.arguments)
	return f"{atom.predicate}({arguments})" if arguments else atom.predicate


def _safe_agentspeak_identifier(value: str) -> str:
	text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "")).strip("_").lower()
	if not text:
		return "query_helper"
	return f"q_{text}" if text[0].isdigit() else text


def threat_safe_positive_literal_order(
	literals: Sequence[tuple[str, tuple[str, ...]]],
	*,
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	object_types: Mapping[str, str] | None = None,
	negative_literals: Sequence[tuple[str, tuple[str, ...]]] = (),
) -> tuple[tuple[int, ...], TransitionSerializationCertificate]:
	"""Return an order that preserves positive siblings and negative guards."""

	literal_tuple = tuple(literals or ())
	negative_literal_tuple = tuple(negative_literals or ())
	if len(literal_tuple) <= 1 and not negative_literal_tuple:
		indexes = tuple(range(len(literal_tuple)))
		return indexes, TransitionSerializationCertificate(indexes, (), True)
	actions = tuple(_ParsedAction.from_pddl(action) for action in domain.actions)
	plans_by_predicate = _plans_by_predicate(plan_library.plans)
	actions_by_name = {action.name: action for action in actions}
	functional_groups = _functional_predicate_groups(actions, domain.types)
	predicate_types = {
		predicate.name: tuple(parameter_type(parameter) for parameter in predicate.parameters)
		for predicate in domain.predicates
	}
	known_object_types = {**dict(domain.constant_types), **dict(object_types or {})}
	query_variable_types = _query_variable_type_requirements(
		(*literal_tuple, *negative_literal_tuple),
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
	negative_guard_atoms = tuple(
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
		for predicate, arguments in negative_literal_tuple
	)
	_assert_functional_goal_consistency(goal_atoms, functional_groups=functional_groups)
	goal_indexes_by_predicate, goal_indexes_by_constant, goal_indexes_by_variable = (
		_index_goal_atoms(goal_atoms)
	)
	summary_cache: dict[
		tuple[str, tuple[tuple[str, ...], ...]],
		tuple[EffectAtom, AtomicModuleEffectSummary],
	] = {}
	edges: set[tuple[int, int]] = set()
	negative_guard_threats: set[tuple[int, int]] = set()
	support_ranking_for_detected_cycle: tuple[tuple[int, ...], str, int] | None = None
	support_ranking_checked = False
	for achiever_index, goal_atom in enumerate(goal_atoms):
		summary = _cached_module_effect_summary(
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
		for conditional_add in summary.conditional_add_effects:
			for negative_index, forbidden in enumerate(negative_guard_atoms):
				if _conditional_add_can_violate_negative(
					conditional_add,
					forbidden=forbidden,
					type_tokens=domain.types,
				):
					negative_guard_threats.add((achiever_index, negative_index))
		for conditional_delete in summary.conditional_delete_effects:
			deleted = conditional_delete.delete_atom
			for protected_index in _indexed_goal_candidates(
				deleted,
				goal_indexes_by_predicate=goal_indexes_by_predicate,
				goal_indexes_by_constant=goal_indexes_by_constant,
				goal_indexes_by_variable=goal_indexes_by_variable,
			):
				if achiever_index == protected_index:
					continue
				if _conditional_delete_can_threaten(
					conditional_delete,
					protected=goal_atoms[protected_index],
					functional_groups=functional_groups,
					type_tokens=domain.types,
				):
					edge = (achiever_index, protected_index)
					edges.add(edge)
					if (protected_index, achiever_index) not in edges:
						continue
					if not support_ranking_checked:
						support_ranking_for_detected_cycle = (
							_assumption_bounded_support_depth_order(
								goal_atoms,
								plan_library=plan_library,
								actions=actions,
							)
						)
						support_ranking_checked = True
					if support_ranking_for_detected_cycle is None:
						raise ValueError(
							"cyclic_conjunctive_transition_not_certified: selected atomic "
							"modules have a cyclic delete-threat graph and no transition "
							"ranking certificate.",
						)
	if negative_guard_threats:
		raised = ", ".join(
			f"positive[{positive_index}]->negative[{negative_index}]"
			for positive_index, negative_index in sorted(negative_guard_threats)
		)
		raise ValueError(
			"negative_guard_not_preserved: selected atomic modules may add a "
			f"forbidden negative-guard atom at module completion ({raised})."
		)
	ordered_indexes = _stable_topological_order(len(literal_tuple), edges)
	serialization_strategy = "universal_acyclic_threat_order"
	ranking_relation: str | None = None
	ranking_relation_anchor_position: int | None = None
	ranking_assumptions: tuple[str, ...] = ()
	if ordered_indexes is None:
		support_ranking = support_ranking_for_detected_cycle
		if not support_ranking_checked:
			support_ranking = _assumption_bounded_support_depth_order(
				goal_atoms,
				plan_library=plan_library,
				actions=actions,
			)
		if support_ranking is not None:
			(
				ordered_indexes,
				ranking_relation,
				ranking_relation_anchor_position,
			) = support_ranking
			serialization_strategy = "assumption_bounded_support_depth_ranking"
			ranking_assumptions = (
				"the certified binary relation is acyclic in every reachable execution state",
				"atomic modules are observed only at successful module completion",
			)
	if ordered_indexes is None:
		raise ValueError(
			"cyclic_conjunctive_transition_not_certified: selected atomic modules "
			"have a cyclic delete-threat graph and no transition ranking certificate.",
		)
	certificate = TransitionSerializationCertificate(
		ordered_indexes=ordered_indexes,
		threat_edges=tuple(sorted(edges)),
		module_summaries_complete=True,
		conditional_effects_checked=True,
		functional_invariant_count=len(functional_groups),
		serialization_strategy=serialization_strategy,
		ranking_relation=ranking_relation,
		ranking_relation_anchor_position=ranking_relation_anchor_position,
		ranking_assumptions=ranking_assumptions,
		negative_guard_count=len(negative_guard_atoms),
		negative_guard_preservation_checked=bool(negative_guard_atoms),
		negative_guard_preserved=True,
		negative_guard_threats=(),
	)
	return ordered_indexes, certificate


def preservation_safe_plan_selection(
	literals: Sequence[tuple[str, tuple[str, ...]]],
	*,
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	object_types: Mapping[str, str] | None = None,
	negative_literals: Sequence[tuple[str, tuple[str, ...]]] = (),
) -> PreservationSafePlanSelection | None:
	"""Select a support-ranked recursive closure, then the finite-macro fallback."""

	actions = tuple(_ParsedAction.from_pddl(action) for action in domain.actions)
	predicate_types = {
		predicate.name: tuple(parameter_type(parameter) for parameter in predicate.parameters)
		for predicate in domain.predicates
	}
	known_object_types = {**dict(domain.constant_types), **dict(object_types or {})}
	query_variable_types = _query_variable_type_requirements(
		(*tuple(literals or ()), *tuple(negative_literals or ())),
		predicate_types=predicate_types,
		type_tokens=domain.types,
	)
	goal_atoms = _query_effect_atoms(
		tuple(literals or ()),
		predicate_types=predicate_types,
		known_object_types=known_object_types,
		query_variable_types=query_variable_types,
		type_tokens=domain.types,
	)
	support_order = _candidate_support_depth_order(
		goal_atoms,
		plan_library=plan_library,
		actions=actions,
	)
	if support_order is not None:
		selection = _preservation_safe_plan_selection(
			literals,
			plan_library=plan_library,
			domain=domain,
			object_types=object_types,
			negative_literals=negative_literals,
			_ordered_indexes=support_order[0],
			_include_guard_discharge_recursion=True,
			_ranking_relation=support_order[1],
			_ranking_anchor_position=support_order[2],
		)
		if selection is not None:
			return selection
	return preservation_safe_action_only_plan_selection(
		literals,
		plan_library=plan_library,
		domain=domain,
		object_types=object_types,
		negative_literals=negative_literals,
	)


def preservation_safe_action_only_plan_selection(
	literals: Sequence[tuple[str, tuple[str, ...]]],
	*,
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	object_types: Mapping[str, str] | None = None,
	negative_literals: Sequence[tuple[str, tuple[str, ...]]] = (),
) -> PreservationSafePlanSelection | None:
	"""Select finite action-only branches preserving every sibling and negative guard.

	The returned plans are safe only when the caller enforces the selection, for
	example by copying them under a query-local AgentSpeak trigger. Returning a
	selection must never be treated as permission to call the original unfiltered
	atomic module.
	"""

	return _preservation_safe_plan_selection(
		literals,
		plan_library=plan_library,
		domain=domain,
		object_types=object_types,
		negative_literals=negative_literals,
	)


def _preservation_safe_plan_selection(
	literals: Sequence[tuple[str, tuple[str, ...]]],
	*,
	plan_library: PlanLibrary,
	domain: PDDLDomain,
	object_types: Mapping[str, str] | None = None,
	negative_literals: Sequence[tuple[str, tuple[str, ...]]] = (),
	_ordered_indexes: Sequence[int] | None = None,
	_include_guard_discharge_recursion: bool = False,
	_ranking_relation: str | None = None,
	_ranking_anchor_position: int | None = None,
) -> PreservationSafePlanSelection | None:
	"""Implement branch-scoped preservation under one explicit serialization order.

	The returned plans are safe only when the caller enforces the selection, for
	example by copying them under a query-local AgentSpeak trigger. Returning a
	selection must never be treated as permission to call the original unfiltered
	atomic module.
	"""

	literal_tuple = tuple(literals or ())
	negative_literal_tuple = tuple(negative_literals or ())
	if len(literal_tuple) <= 1 and not negative_literal_tuple:
		return None
	actions = tuple(_ParsedAction.from_pddl(action) for action in domain.actions)
	actions_by_name = {action.name: action for action in actions}
	functional_groups = _functional_predicate_groups(actions, domain.types)
	predicate_types = {
		predicate.name: tuple(parameter_type(parameter) for parameter in predicate.parameters)
		for predicate in domain.predicates
	}
	known_object_types = {**dict(domain.constant_types), **dict(object_types or {})}
	query_variable_types = _query_variable_type_requirements(
		(*literal_tuple, *negative_literal_tuple),
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
	negative_guard_atoms = tuple(
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
		for predicate, arguments in negative_literal_tuple
	)
	_assert_functional_goal_consistency(goal_atoms, functional_groups=functional_groups)
	ordered_indexes = tuple(
		_ordered_indexes
		if _ordered_indexes is not None
		else range(len(literal_tuple))
	)
	if set(ordered_indexes) != set(range(len(literal_tuple))):
		return None
	order_position = {literal_index: position for position, literal_index in enumerate(ordered_indexes)}
	positive_pair_shapes_by_achiever: dict[
		int,
		set[tuple[EffectAtom, EffectAtom]],
	] = {}
	negative_pair_shapes_by_achiever: dict[
		int,
		set[tuple[EffectAtom, EffectAtom]],
	] = {}
	for achiever_index, achiever in enumerate(goal_atoms):
		for protected_index, protected in enumerate(goal_atoms):
			if achiever_index == protected_index:
				continue
			if _ordered_indexes is not None and (
				order_position[protected_index] >= order_position[achiever_index]
			):
				continue
			positive_pair_shapes_by_achiever.setdefault(achiever_index, set()).add(
				_canonical_goal_pair_shape(
					achiever,
					protected,
					domain_constants=frozenset(domain.constants),
				),
			)
		for forbidden in negative_guard_atoms:
			negative_pair_shapes_by_achiever.setdefault(achiever_index, set()).add(
				_canonical_goal_pair_shape(
					achiever,
					forbidden,
					domain_constants=frozenset(domain.constants),
				),
			)
	plans_by_predicate = _plans_by_predicate(plan_library.plans)
	selected_by_literal_index: dict[int, tuple[AgentSpeakPlan, ...]] = {}
	portfolio_cache: dict[
		tuple[
			str,
			frozenset[tuple[EffectAtom, EffectAtom]],
			frozenset[tuple[EffectAtom, EffectAtom]],
		],
		tuple[AgentSpeakPlan, ...],
	] = {}
	summary_cache: dict[
		tuple[str, tuple[tuple[str, ...], ...]],
		tuple[EffectAtom, AtomicModuleEffectSummary],
	] = {}
	for literal_index in ordered_indexes:
		achiever_atom = goal_atoms[literal_index]
		predicate = achiever_atom.predicate
		positive_pair_shapes = tuple(
			positive_pair_shapes_by_achiever.get(literal_index, ())
		)
		negative_pair_shapes = tuple(
			negative_pair_shapes_by_achiever.get(literal_index, ())
		)
		portfolio_key = (
			predicate,
			frozenset(positive_pair_shapes),
			frozenset(negative_pair_shapes),
		)
		cached_portfolio = portfolio_cache.get(portfolio_key)
		if cached_portfolio is not None:
			selected_by_literal_index[literal_index] = cached_portfolio
			continue
		generic_goal = EffectAtom(
			predicate,
			tuple(
				EffectTerm(
					f"H{index}",
					variable_scope="query",
					required_types=argument.required_types,
				)
				for index, argument in enumerate(achiever_atom.arguments)
			),
		)
		safe_plans: list[AgentSpeakPlan] = []
		for plan_index, plan in enumerate(plans_by_predicate.get(predicate, ())):
			if any(step.kind != "action" for step in plan.body):
				continue
			generic_summary = _action_only_plan_effect_summary(
				plan,
				goal=generic_goal,
				plan_index=plan_index,
				actions_by_name=actions_by_name,
				predicate_types=predicate_types,
				type_tokens=domain.types,
			)
			if generic_summary is None or not _action_only_summary_achieves_goal(
				generic_summary,
				goal=generic_goal,
				body_is_empty=not plan.body,
			):
				continue
			is_safe = True
			for achiever, protected in positive_pair_shapes:
				head_binding = {
					generic_argument.symbol: actual_argument
					for generic_argument, actual_argument in zip(
						generic_goal.arguments,
						achiever.arguments,
					)
				}
				effects = tuple(
					_instantiate_conditional_delete(
						effect,
						head_binding=head_binding,
					)
					for effect in generic_summary.conditional_deletes
				)
				if any(
					_conditional_delete_can_threaten(
						effect,
						protected=protected,
						functional_groups=functional_groups,
						type_tokens=domain.types,
					)
					for effect in effects
				):
					is_safe = False
					break
			if not is_safe:
				continue
			for achiever, forbidden in negative_pair_shapes:
				head_binding = {
					generic_argument.symbol: actual_argument
					for generic_argument, actual_argument in zip(
						generic_goal.arguments,
						achiever.arguments,
					)
				}
				conditional_adds = tuple(
					_instantiate_conditional_add(
						ConditionalAddEffect(
							add_atom=atom,
							positive_context=generic_summary.branch_condition.positive_context,
							negative_context=generic_summary.branch_condition.negative_context,
							equalities=generic_summary.branch_condition.equalities,
							disequalities=generic_summary.branch_condition.disequalities,
						),
						head_binding=head_binding,
					)
					for atom in generic_summary.add_atoms
				)
				if any(
					_conditional_add_can_violate_negative(
						effect,
						forbidden=forbidden,
						type_tokens=domain.types,
					)
					for effect in conditional_adds
				):
					is_safe = False
					break
			if is_safe:
				safe_plans.append(plan)
		if _include_guard_discharge_recursion:
			safe_plans.extend(
				_guard_discharge_recursive_plans(
					plans_by_predicate.get(predicate, ()),
					generic_goal=generic_goal,
					positive_pair_shapes=positive_pair_shapes,
					negative_pair_shapes=negative_pair_shapes,
					plans_by_predicate=plans_by_predicate,
					actions_by_name=actions_by_name,
					predicate_types=predicate_types,
					type_tokens=domain.types,
					functional_groups=functional_groups,
					summary_cache=summary_cache,
				),
			)
		if not safe_plans or not any(
			plan.body and all(step.kind == "action" for step in plan.body)
			for plan in safe_plans
		):
			return None
		selected_by_literal_index[literal_index] = _deduplicate_plans_by_name(safe_plans)
		portfolio_cache[portfolio_key] = selected_by_literal_index[literal_index]
	selected: dict[str, tuple[AgentSpeakPlan, ...]] = {}
	for predicate in dict.fromkeys(literal_tuple[index][0] for index in ordered_indexes):
		portfolios = tuple(
			selected_by_literal_index[index]
			for index in ordered_indexes
			if literal_tuple[index][0] == predicate
		)
		common_names = set(plan.plan_name for plan in portfolios[0])
		for portfolio in portfolios[1:]:
			common_names.intersection_update(plan.plan_name for plan in portfolio)
		selected[predicate] = tuple(
			plan for plan in portfolios[0] if plan.plan_name in common_names
		)
	strategy = "query_local_preservation_safe_action_only_branches"
	ranking_assumptions: tuple[str, ...] = ()
	selected_recursive_plan_count = sum(
		1
		for plans in selected_by_literal_index.values()
		for plan in plans
		if any(step.kind == "subgoal" for step in plan.body)
	)
	if selected_recursive_plan_count:
		strategy = "query_local_support_ranked_recursive_closure"
		ranking_assumptions = (
			"the certified binary relation is acyclic in every reachable execution state",
			"each recursive repair discharges one explicit negative context guard",
			"selected preparation modules preserve all earlier ranked achievements",
		)
	certificate = TransitionSerializationCertificate(
		ordered_indexes=ordered_indexes,
		threat_edges=(),
		module_summaries_complete=True,
		conditional_effects_checked=True,
		functional_invariant_count=len(functional_groups),
		serialization_strategy=strategy,
		ranking_relation=_ranking_relation,
		ranking_relation_anchor_position=_ranking_anchor_position,
		ranking_assumptions=ranking_assumptions,
		selected_branch_names_by_predicate=tuple(
			(predicate, tuple(plan.plan_name for plan in plans))
			for predicate, plans in selected.items()
		),
		selected_branch_names_by_literal=tuple(
			(
				literal_index,
				(
					literal_tuple[literal_index][0]
					if not literal_tuple[literal_index][1]
					else (
						f"{literal_tuple[literal_index][0]}"
						f"({', '.join(literal_tuple[literal_index][1])})"
					)
				),
				tuple(
					plan.plan_name for plan in selected_by_literal_index[literal_index]
				),
			)
			for literal_index in ordered_indexes
		),
		negative_guard_count=len(negative_guard_atoms),
		negative_guard_preservation_checked=bool(negative_guard_atoms),
		negative_guard_preserved=True,
		negative_guard_threats=(),
	)
	return PreservationSafePlanSelection(
		ordered_indexes=ordered_indexes,
		literals=literal_tuple,
		plans_by_predicate=selected,
		plans_by_literal_index=selected_by_literal_index,
		certificate=certificate,
	)


def _canonical_goal_pair_shape(
	achiever: EffectAtom,
	protected: EffectAtom,
	*,
	domain_constants: frozenset[str],
) -> tuple[EffectAtom, EffectAtom]:
	"""Abstract problem-object names while preserving types and equality patterns."""

	term_map: dict[tuple[str, str | None], EffectTerm] = {}
	ground_index = 0
	variable_index = 0

	def canonical_term(term: EffectTerm) -> EffectTerm:
		nonlocal ground_index, variable_index
		if not term.is_variable and term.symbol in domain_constants:
			return term
		key = (term.symbol, term.variable_scope)
		if key in term_map:
			return term_map[key]
		if term.is_variable:
			canonical = EffectTerm(
				f"Q{variable_index}",
				variable_scope="query-pair-shape",
				required_types=term.required_types,
			)
			variable_index += 1
		else:
			canonical = EffectTerm(
				f"__object_{ground_index}",
				required_types=term.required_types,
			)
			ground_index += 1
		term_map[key] = canonical
		return canonical

	def canonical_atom(atom: EffectAtom) -> EffectAtom:
		return EffectAtom(atom.predicate, tuple(canonical_term(term) for term in atom.arguments))

	return canonical_atom(achiever), canonical_atom(protected)


def _deduplicate_plans_by_name(
	plans: Sequence[AgentSpeakPlan],
) -> tuple[AgentSpeakPlan, ...]:
	selected: dict[str, AgentSpeakPlan] = {}
	for plan in tuple(plans or ()):
		selected.setdefault(plan.plan_name, plan)
	return tuple(selected.values())


def _action_only_plan_effect_summary(
	plan: AgentSpeakPlan,
	*,
	goal: EffectAtom,
	plan_index: int,
	actions_by_name: Mapping[str, _ParsedAction],
	predicate_types: Mapping[str, Sequence[str]],
	type_tokens: Sequence[str],
) -> _ActionOnlyPlanEffectSummary | None:
	"""Return exact completion effects for one action-only branch."""

	binding = _bind_plan_trigger(plan, goal)
	if binding is None or any(step.kind != "action" for step in plan.body):
		return None
	local_scope = f"{goal.predicate}:selected:{plan_index}"
	branch_condition = _plan_branch_condition(
		plan,
		binding=binding,
		scope=local_scope,
		predicate_types=predicate_types,
		type_tokens=type_tokens,
	)
	direct_effect_state: dict[EffectAtom, bool] = {}
	for step in plan.body:
		action = actions_by_name.get(step.symbol)
		if action is None or len(action.parameters) != len(step.arguments):
			return None
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
			direct_effect_state[
				_mapped_effect_atom(
					effect,
					action_binding=action_binding,
					scope=local_scope,
				)
			] = False
		for effect in action.add_effects:
			direct_effect_state[
				_mapped_effect_atom(
					effect,
					action_binding=action_binding,
					scope=local_scope,
				)
			] = True
	return _ActionOnlyPlanEffectSummary(
		conditional_deletes=tuple(
			ConditionalDeleteEffect(
				delete_atom=atom,
				positive_context=branch_condition.positive_context,
				negative_context=branch_condition.negative_context,
				equalities=branch_condition.equalities,
				disequalities=branch_condition.disequalities,
			)
			for atom, value in direct_effect_state.items()
			if not value
		),
		add_atoms=tuple(atom for atom, value in direct_effect_state.items() if value),
		branch_condition=branch_condition,
	)


def _action_only_summary_achieves_goal(
	summary: _ActionOnlyPlanEffectSummary,
	*,
	goal: EffectAtom,
	body_is_empty: bool,
) -> bool:
	candidates = (
		summary.branch_condition.positive_context if body_is_empty else summary.add_atoms
	)
	return any(_effect_atom_has_same_identity(candidate, goal) for candidate in candidates)


def _guard_discharge_recursive_plans(
	plans: Sequence[AgentSpeakPlan],
	*,
	generic_goal: EffectAtom,
	positive_pair_shapes: Sequence[tuple[EffectAtom, EffectAtom]],
	negative_pair_shapes: Sequence[tuple[EffectAtom, EffectAtom]],
	plans_by_predicate: Mapping[str, Sequence[AgentSpeakPlan]],
	actions_by_name: Mapping[str, _ParsedAction],
	predicate_types: Mapping[str, Sequence[str]],
	type_tokens: Sequence[str],
	functional_groups: Sequence[_FunctionalPredicateGroup],
	summary_cache: dict[
		tuple[str, tuple[tuple[str, ...], ...]],
		tuple[EffectAtom, AtomicModuleEffectSummary],
	],
) -> tuple[AgentSpeakPlan, ...]:
	"""Return recursive branches justified by one discharged context obligation."""

	patterns: list[tuple[AgentSpeakPlan, EffectAtom, AtomicModuleEffectSummary]] = []
	for plan_index, plan in enumerate(tuple(plans or ())):
		pattern = _guard_discharge_pattern(
			plan,
			generic_goal=generic_goal,
			plan_index=plan_index,
			predicate_types=predicate_types,
			type_tokens=type_tokens,
		)
		if pattern is None:
			continue
		preparation_atom = pattern
		if preparation_atom.predicate == generic_goal.predicate:
			if not _plan_has_relational_progress_certificate(plan):
				continue
		elif _predicate_call_graph_reaches(
			preparation_atom.predicate,
			generic_goal.predicate,
			plans_by_predicate=plans_by_predicate,
		):
			continue
		summary = _cached_module_effect_summary(
			preparation_atom,
			cache=summary_cache,
			plans_by_predicate=plans_by_predicate,
			actions_by_name=actions_by_name,
			predicate_types=predicate_types,
			type_tokens=type_tokens,
		)
		if not summary.complete:
			continue
		patterns.append((plan, preparation_atom, summary))

	selected: list[AgentSpeakPlan] = []
	for plan, _preparation_atom, summary in patterns:
		if not _summary_preserves_goal_pairs(
			summary,
			generic_goal=generic_goal,
			positive_pair_shapes=positive_pair_shapes,
			negative_pair_shapes=negative_pair_shapes,
			functional_groups=functional_groups,
			type_tokens=type_tokens,
		):
			continue
		selected.append(plan)
	return tuple(selected)


def _guard_discharge_pattern(
	plan: AgentSpeakPlan,
	*,
	generic_goal: EffectAtom,
	plan_index: int,
	predicate_types: Mapping[str, Sequence[str]],
	type_tokens: Sequence[str],
) -> EffectAtom | None:
	body = tuple(plan.body or ())
	if len(body) != 2 or any(step.kind != "subgoal" for step in body):
		return None
	preparation, recursive_call = body
	if recursive_call.symbol != plan.trigger.symbol or tuple(
		recursive_call.arguments
	) != tuple(plan.trigger.arguments):
		return None
	binding = _bind_plan_trigger(plan, generic_goal)
	if binding is None:
		return None
	scope = f"{generic_goal.predicate}:recursive-selection:{plan_index}"
	signature = tuple(predicate_types.get(preparation.symbol, ()))
	preparation_atom = EffectAtom(
		preparation.symbol,
		tuple(
			_bound_term(
				argument,
				binding=binding,
				scope=scope,
				required_type=signature[position] if position < len(signature) else "object",
				type_tokens=type_tokens,
			)
			for position, argument in enumerate(preparation.arguments)
		),
	)
	branch_condition = _plan_branch_condition(
		plan,
		binding=binding,
		scope=scope,
		predicate_types=predicate_types,
		type_tokens=type_tokens,
	)
	if not any(
		_effect_atom_has_same_identity(preparation_atom, guarded)
		for guarded in branch_condition.negative_context
	):
		return None
	return preparation_atom


def _plan_has_relational_progress_certificate(plan: AgentSpeakPlan) -> bool:
	return any(
		isinstance(certificate.get("recursive_progress_certificate"), Mapping)
		and certificate["recursive_progress_certificate"].get("certificate_kind")
		== "well_founded_relational_count_decrease"
		for certificate in tuple(plan.binding_certificate or ())
	)


def _predicate_call_graph_reaches(
	source: str,
	target: str,
	*,
	plans_by_predicate: Mapping[str, Sequence[AgentSpeakPlan]],
) -> bool:
	frontier = [source]
	seen: set[str] = set()
	while frontier:
		current = frontier.pop()
		if current in seen:
			continue
		seen.add(current)
		for plan in tuple(plans_by_predicate.get(current, ())):
			for step in plan.body:
				if step.kind != "subgoal":
					continue
				if step.symbol == target:
					return True
				if step.symbol not in seen:
					frontier.append(step.symbol)
	return False


def _summary_preserves_goal_pairs(
	summary: AtomicModuleEffectSummary,
	*,
	generic_goal: EffectAtom,
	positive_pair_shapes: Sequence[tuple[EffectAtom, EffectAtom]],
	negative_pair_shapes: Sequence[tuple[EffectAtom, EffectAtom]],
	functional_groups: Sequence[_FunctionalPredicateGroup],
	type_tokens: Sequence[str],
) -> bool:
	for achiever, protected in positive_pair_shapes:
		head_binding = _generic_head_binding(generic_goal, achiever)
		if any(
			_conditional_delete_can_threaten(
				_instantiate_conditional_delete(effect, head_binding=head_binding),
				protected=protected,
				functional_groups=functional_groups,
				type_tokens=type_tokens,
			)
			for effect in summary.conditional_delete_effects
		):
			return False
	for achiever, forbidden in negative_pair_shapes:
		head_binding = _generic_head_binding(generic_goal, achiever)
		if any(
			_conditional_add_can_violate_negative(
				_instantiate_conditional_add(effect, head_binding=head_binding),
				forbidden=forbidden,
				type_tokens=type_tokens,
			)
			for effect in summary.conditional_add_effects
		):
			return False
	return True


def _generic_head_binding(
	generic_goal: EffectAtom,
	actual_goal: EffectAtom,
) -> dict[str, EffectTerm]:
	return {
		generic_argument.symbol: actual_argument
		for generic_argument, actual_argument in zip(
			generic_goal.arguments,
			actual_goal.arguments,
		)
	}


def _effect_atom_has_same_identity(left: EffectAtom, right: EffectAtom) -> bool:
	return (
		left.predicate == right.predicate
		and len(left.arguments) == len(right.arguments)
		and all(
			(left_term.symbol, left_term.variable_scope)
			== (right_term.symbol, right_term.variable_scope)
			for left_term, right_term in zip(left.arguments, right.arguments)
		)
	)


def _plans_by_predicate(
	plans: Sequence[AgentSpeakPlan],
) -> dict[str, tuple[AgentSpeakPlan, ...]]:
	return {
		predicate: tuple(plan for plan in plans if plan.trigger.symbol == predicate)
		for predicate in sorted({plan.trigger.symbol for plan in plans})
	}


def _cached_module_effect_summary(
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
			_module_effect_summary(
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
		conditional_delete_effects=tuple(
			_instantiate_conditional_delete(effect, head_binding=head_binding)
			for effect in generic_summary.conditional_delete_effects
		),
		conditional_add_effects=tuple(
			_instantiate_conditional_add(effect, head_binding=head_binding)
			for effect in generic_summary.conditional_add_effects
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


def _instantiate_conditional_delete(
	effect: ConditionalDeleteEffect,
	*,
	head_binding: Mapping[str, EffectTerm],
) -> ConditionalDeleteEffect:
	def atom(item: EffectAtom) -> EffectAtom:
		return _instantiate_query_anchors(item, head_binding=head_binding)

	def term(item: EffectTerm) -> EffectTerm:
		if item.variable_scope == "query":
			return head_binding.get(item.symbol, item)
		return item

	return ConditionalDeleteEffect(
		delete_atom=atom(effect.delete_atom),
		positive_context=tuple(atom(item) for item in effect.positive_context),
		negative_context=tuple(atom(item) for item in effect.negative_context),
		equalities=tuple((term(left), term(right)) for left, right in effect.equalities),
		disequalities=tuple(
			(term(left), term(right)) for left, right in effect.disequalities
		),
	)


def _instantiate_conditional_add(
	effect: ConditionalAddEffect,
	*,
	head_binding: Mapping[str, EffectTerm],
) -> ConditionalAddEffect:
	def atom(item: EffectAtom) -> EffectAtom:
		return _instantiate_query_anchors(item, head_binding=head_binding)

	def term(item: EffectTerm) -> EffectTerm:
		if item.variable_scope == "query":
			return head_binding.get(item.symbol, item)
		return item

	return ConditionalAddEffect(
		add_atom=atom(effect.add_atom),
		positive_context=tuple(atom(item) for item in effect.positive_context),
		negative_context=tuple(atom(item) for item in effect.negative_context),
		equalities=tuple((term(left), term(right)) for left, right in effect.equalities),
		disequalities=tuple(
			(term(left), term(right)) for left, right in effect.disequalities
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


def _module_effect_summary(
	*,
	goal: EffectAtom,
	plans_by_predicate: Mapping[str, Sequence[AgentSpeakPlan]],
	actions_by_name: Mapping[str, _ParsedAction],
	predicate_types: Mapping[str, Sequence[str]],
	type_tokens: Sequence[str],
) -> AtomicModuleEffectSummary:
	pending = [_canonicalize_effect_atom(goal, namespace="module-call")]
	seen: set[EffectAtom] = set()
	conditional_deletes: list[ConditionalDeleteEffect] = []
	conditional_adds: list[ConditionalAddEffect] = []
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
			branch_condition = _plan_branch_condition(
				plan,
				binding=binding,
				scope=local_scope,
				predicate_types=predicate_types,
				type_tokens=type_tokens,
			)
			direct_effect_state: dict[EffectAtom, bool] = {}
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
						direct_effect_state[
							_mapped_effect_atom(
								effect,
								action_binding=action_binding,
								scope=local_scope,
							)
						] = False
					for effect in action.add_effects:
						direct_effect_state[
							_mapped_effect_atom(
								effect,
								action_binding=action_binding,
								scope=local_scope,
							)
						] = True
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
					subgoal_atom = EffectAtom(step.symbol, step_arguments)
					pending.append(
						_canonicalize_effect_atom(
							subgoal_atom,
							namespace="module-call",
						),
					)
					direct_effect_state[subgoal_atom] = True
				else:
					complete = False
			for effect_atom, value in direct_effect_state.items():
				if value:
					conditional_adds.append(
						_canonicalize_conditional_add(
							ConditionalAddEffect(
								add_atom=effect_atom,
								positive_context=branch_condition.positive_context,
								negative_context=branch_condition.negative_context,
								equalities=branch_condition.equalities,
								disequalities=branch_condition.disequalities,
							),
							namespace="add-effect",
						),
					)
					continue
				conditional_deletes.append(
					_canonicalize_conditional_delete(
						ConditionalDeleteEffect(
							delete_atom=effect_atom,
							positive_context=branch_condition.positive_context,
							negative_context=branch_condition.negative_context,
							equalities=branch_condition.equalities,
							disequalities=branch_condition.disequalities,
						),
						namespace="delete-effect",
					),
				)
		if not matched_plan:
			complete = False
	return AtomicModuleEffectSummary(
		conditional_delete_effects=tuple(dict.fromkeys(conditional_deletes)),
		conditional_add_effects=tuple(dict.fromkeys(conditional_adds)),
		complete=complete,
	)


def _mapped_effect_atom(
	effect: PDDLLiteralSchema,
	*,
	action_binding: Mapping[str, EffectTerm],
	scope: str,
) -> EffectAtom:
	return EffectAtom(
		predicate=effect.predicate,
		arguments=tuple(
			action_binding.get(
				argument,
				EffectTerm(argument, variable_scope=scope),
			)
			for argument in effect.arguments
		),
	)


def _plan_branch_condition(
	plan: AgentSpeakPlan,
	*,
	binding: Mapping[str, EffectTerm],
	scope: str,
	predicate_types: Mapping[str, Sequence[str]],
	type_tokens: Sequence[str],
) -> _BranchCondition:
	positive: list[EffectAtom] = []
	negative: list[EffectAtom] = []
	equalities: list[tuple[EffectTerm, EffectTerm]] = []
	disequalities: list[tuple[EffectTerm, EffectTerm]] = []
	for raw_context in tuple(plan.context or ()):
		context = str(raw_context or "").strip()
		comparison = re.fullmatch(
			r"(?P<left>[A-Za-z_][A-Za-z0-9_]*|[+-]?\d+)\s*"
			r"(?P<operator>\\==|!=|==)\s*"
			r"(?P<right>[A-Za-z_][A-Za-z0-9_]*|[+-]?\d+)",
			context,
		)
		if comparison is not None:
			pair = (
				_context_term(comparison.group("left"), binding=binding, scope=scope),
				_context_term(comparison.group("right"), binding=binding, scope=scope),
			)
			if comparison.group("operator") == "==":
				equalities.append(pair)
			else:
				disequalities.append(pair)
			continue
		is_negative = context.startswith("not ")
		atom_text = context[4:].strip() if is_negative else context
		match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*)(?:\((.*)\))?", atom_text)
		if match is None:
			continue
		predicate = match.group(1)
		if predicate not in predicate_types:
			continue
		arguments = tuple(
			item.strip()
			for item in str(match.group(2) or "").split(",")
			if item.strip()
		)
		signature = tuple(predicate_types.get(predicate, ()))
		if len(arguments) != len(signature):
			continue
		atom = EffectAtom(
			predicate,
			tuple(
				_bound_term(
					argument,
					binding=binding,
					scope=scope,
					required_type=signature[position],
					type_tokens=type_tokens,
				)
				for position, argument in enumerate(arguments)
			),
		)
		(negative if is_negative else positive).append(atom)
	return _BranchCondition(
		positive_context=tuple(positive),
		negative_context=tuple(negative),
		equalities=tuple(equalities),
		disequalities=tuple(disequalities),
	)


def _context_term(
	argument: str,
	*,
	binding: Mapping[str, EffectTerm],
	scope: str,
) -> EffectTerm:
	if argument in binding:
		return binding[argument]
	if _is_agentspeak_variable(argument):
		return EffectTerm(argument, variable_scope=scope)
	return EffectTerm(argument)


def _canonicalize_conditional_delete(
	effect: ConditionalDeleteEffect,
	*,
	namespace: str,
) -> ConditionalDeleteEffect:
	variable_map: dict[tuple[str, str], EffectTerm] = {}

	def term(argument: EffectTerm) -> EffectTerm:
		if not argument.is_variable or argument.variable_scope == "query":
			return argument
		key = (str(argument.variable_scope), argument.symbol)
		variable_map.setdefault(
			key,
			EffectTerm(
				f"V{len(variable_map)}",
				variable_scope=namespace,
				required_types=argument.required_types,
			),
		)
		return variable_map[key]

	def atom(item: EffectAtom) -> EffectAtom:
		return EffectAtom(item.predicate, tuple(term(argument) for argument in item.arguments))

	return ConditionalDeleteEffect(
		delete_atom=atom(effect.delete_atom),
		positive_context=tuple(atom(item) for item in effect.positive_context),
		negative_context=tuple(atom(item) for item in effect.negative_context),
		equalities=tuple((term(left), term(right)) for left, right in effect.equalities),
		disequalities=tuple(
			(term(left), term(right)) for left, right in effect.disequalities
		),
	)


def _canonicalize_conditional_add(
	effect: ConditionalAddEffect,
	*,
	namespace: str,
) -> ConditionalAddEffect:
	variable_map: dict[tuple[str, str], EffectTerm] = {}

	def term(argument: EffectTerm) -> EffectTerm:
		if not argument.is_variable or argument.variable_scope == "query":
			return argument
		key = (str(argument.variable_scope), argument.symbol)
		variable_map.setdefault(
			key,
			EffectTerm(
				f"V{len(variable_map)}",
				variable_scope=namespace,
				required_types=argument.required_types,
			),
		)
		return variable_map[key]

	def atom(item: EffectAtom) -> EffectAtom:
		return EffectAtom(item.predicate, tuple(term(argument) for argument in item.arguments))

	return ConditionalAddEffect(
		add_atom=atom(effect.add_atom),
		positive_context=tuple(atom(item) for item in effect.positive_context),
		negative_context=tuple(atom(item) for item in effect.negative_context),
		equalities=tuple((term(left), term(right)) for left, right in effect.equalities),
		disequalities=tuple(
			(term(left), term(right)) for left, right in effect.disequalities
		),
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


def _query_effect_atoms(
	literals: Sequence[tuple[str, tuple[str, ...]]],
	*,
	predicate_types: Mapping[str, Sequence[str]],
	known_object_types: Mapping[str, str],
	query_variable_types: Mapping[str, frozenset[str]],
	type_tokens: Sequence[str],
) -> tuple[EffectAtom, ...]:
	return tuple(
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
					type_tokens=type_tokens,
				)
				for position, argument in enumerate(arguments)
			),
		)
		for predicate, arguments in tuple(literals or ())
	)


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


def _assert_functional_goal_consistency(
	goal_atoms: Sequence[EffectAtom],
	*,
	functional_groups: Sequence[_FunctionalPredicateGroup],
) -> None:
	for left_index, left in enumerate(tuple(goal_atoms or ())):
		for right_index in range(left_index + 1, len(tuple(goal_atoms or ()))):
			right = tuple(goal_atoms)[right_index]
			for group in functional_groups:
				if _functional_atoms_are_mutex(left, right, group=group, bindings={}):
					raise ValueError(
						"functionally_inconsistent_conjunctive_transition: positive "
						f"literals at indexes {left_index} and {right_index} violate "
						"a PDDL schema-derived single-valued predicate invariant.",
					)


def _conditional_delete_can_threaten(
	effect: ConditionalDeleteEffect,
	*,
	protected: EffectAtom,
	functional_groups: Sequence[_FunctionalPredicateGroup],
	type_tokens: Sequence[str],
) -> bool:
	bindings = _atom_unification_bindings(
		effect.delete_atom,
		protected,
		type_tokens=type_tokens,
	)
	if bindings is None:
		return False
	if any(
		_atoms_forced_equal(item, protected, bindings=bindings)
		for item in effect.negative_context
	):
		return False
	if any(
		_terms_forced_equal(left, right, bindings=bindings)
		for left, right in effect.disequalities
	):
		return False
	if any(
		_terms_forced_distinct(left, right, bindings=bindings)
		for left, right in effect.equalities
	):
		return False
	for context_atom in effect.positive_context:
		if any(
			_functional_atoms_are_mutex(
				context_atom,
				protected,
				group=group,
				bindings=bindings,
			)
			for group in functional_groups
		):
			return False
	return True


def _conditional_add_can_violate_negative(
	effect: ConditionalAddEffect,
	*,
	forbidden: EffectAtom,
	type_tokens: Sequence[str],
) -> bool:
	"""Return whether a feasible branch may add an atom required to stay absent."""

	bindings = _atom_unification_bindings(
		effect.add_atom,
		forbidden,
		type_tokens=type_tokens,
	)
	if bindings is None:
		return False
	if any(
		_atoms_forced_equal(item, forbidden, bindings=bindings)
		for item in effect.positive_context
	):
		return False
	if any(
		_terms_forced_equal(left, right, bindings=bindings)
		for left, right in effect.disequalities
	):
		return False
	if any(
		_terms_forced_distinct(left, right, bindings=bindings)
		for left, right in effect.equalities
	):
		return False
	return True


def _atom_unification_bindings(
	left: EffectAtom,
	right: EffectAtom,
	*,
	type_tokens: Sequence[str],
) -> dict[tuple[str, str], EffectTerm] | None:
	if left.predicate != right.predicate or len(left.arguments) != len(right.arguments):
		return None
	bindings: dict[tuple[str, str], EffectTerm] = {}
	for left_term, right_term in zip(left.arguments, right.arguments):
		if not _terms_unify(left_term, right_term, bindings, type_tokens=type_tokens):
			return None
	return bindings


def _atoms_forced_equal(
	left: EffectAtom,
	right: EffectAtom,
	*,
	bindings: Mapping[tuple[str, str], EffectTerm],
) -> bool:
	return (
		left.predicate == right.predicate
		and len(left.arguments) == len(right.arguments)
		and all(
			_terms_forced_equal(left_term, right_term, bindings=bindings)
			for left_term, right_term in zip(left.arguments, right.arguments)
		)
	)


def _functional_atoms_are_mutex(
	left: EffectAtom,
	right: EffectAtom,
	*,
	group: _FunctionalPredicateGroup,
	bindings: Mapping[tuple[str, str], EffectTerm],
) -> bool:
	if left.predicate != group.predicate or right.predicate != group.predicate:
		return False
	if not all(
		_terms_forced_equal(
			left.arguments[position],
			right.arguments[position],
			bindings=bindings,
		)
		for position in group.key_positions
	):
		return False
	return any(
		_terms_forced_distinct(
			left.arguments[position],
			right.arguments[position],
			bindings=bindings,
		)
		for position in group.value_positions
	)


def _terms_forced_equal(
	left: EffectTerm,
	right: EffectTerm,
	*,
	bindings: Mapping[tuple[str, str], EffectTerm],
) -> bool:
	resolved_left = _resolve_term(left, bindings=bindings)
	resolved_right = _resolve_term(right, bindings=bindings)
	return resolved_left == resolved_right


def _terms_forced_distinct(
	left: EffectTerm,
	right: EffectTerm,
	*,
	bindings: Mapping[tuple[str, str], EffectTerm],
) -> bool:
	resolved_left = _resolve_term(left, bindings=bindings)
	resolved_right = _resolve_term(right, bindings=bindings)
	return (
		not resolved_left.is_variable
		and not resolved_right.is_variable
		and resolved_left.symbol != resolved_right.symbol
	)


def _resolve_term(
	term: EffectTerm,
	*,
	bindings: Mapping[tuple[str, str], EffectTerm],
) -> EffectTerm:
	current = term
	seen: set[tuple[str, str]] = set()
	while current.is_variable:
		key = (str(current.variable_scope), current.symbol)
		if key in seen or key not in bindings:
			break
		seen.add(key)
		current = bindings[key]
	return current


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


def _assumption_bounded_support_depth_order(
	goal_atoms: Sequence[EffectAtom],
	*,
	plan_library: PlanLibrary,
	actions: Sequence[_ParsedAction],
) -> tuple[tuple[int, ...], str, int] | None:
	"""Serialize one certified binary support relation from supports to dependants."""

	atoms = tuple(goal_atoms or ())
	if not atoms or len({atom.predicate for atom in atoms}) != 1:
		return None
	relation = atoms[0].predicate
	if any(len(atom.arguments) != 2 for atom in atoms):
		return None
	orientation = _certified_support_relation_orientation(
		plan_library,
		relation=relation,
		actions=actions,
	)
	if orientation is None:
		return None
	child_position, anchor_position = orientation
	child_parent_pairs = tuple(
		(atom.arguments[child_position], atom.arguments[anchor_position])
		for atom in atoms
	)
	if not _relation_pairs_form_functional_acyclic_graph(child_parent_pairs):
		return None
	precedence_edges = {
		(support_index, dependant_index)
		for dependant_index, (_, required_support) in enumerate(child_parent_pairs)
		for support_index, (supported_object, _) in enumerate(child_parent_pairs)
		if dependant_index != support_index and required_support == supported_object
	}
	ordered = _stable_topological_order(len(atoms), precedence_edges)
	if ordered is None:
		return None
	return ordered, relation, anchor_position


def _candidate_support_depth_order(
	goal_atoms: Sequence[EffectAtom],
	*,
	plan_library: PlanLibrary,
	actions: Sequence[_ParsedAction],
) -> tuple[tuple[int, ...], str, int] | None:
	"""Return a support order whose branch preservation must be proven separately."""

	atoms = tuple(goal_atoms or ())
	if not atoms or len({atom.predicate for atom in atoms}) != 1:
		return None
	relation = atoms[0].predicate
	if any(len(atom.arguments) != 2 for atom in atoms):
		return None
	orientation = _certified_support_relation_orientation(
		plan_library,
		relation=relation,
		actions=actions,
		require_global_producer_preservation=False,
	)
	if orientation is None:
		return None
	child_position, anchor_position = orientation
	child_parent_pairs = tuple(
		(atom.arguments[child_position], atom.arguments[anchor_position])
		for atom in atoms
	)
	if not _relation_pairs_form_functional_acyclic_graph(child_parent_pairs):
		return None
	precedence_edges = {
		(support_index, dependant_index)
		for dependant_index, (_, required_support) in enumerate(child_parent_pairs)
		for support_index, (supported_object, _) in enumerate(child_parent_pairs)
		if dependant_index != support_index and required_support == supported_object
	}
	ordered = _stable_topological_order(len(atoms), precedence_edges)
	if ordered is None:
		return None
	return ordered, relation, anchor_position


def _certified_support_relation_orientation(
	plan_library: PlanLibrary,
	*,
	relation: str,
	actions: Sequence[_ParsedAction],
	require_global_producer_preservation: bool = True,
) -> tuple[int, int] | None:
	actions_by_name = {action.name: action for action in tuple(actions or ())}
	if not any(
		effect.predicate == relation
		for action in actions
		for effect in action.add_effects
	):
		return None
	for plan in tuple(plan_library.plans or ()):
		for certificate in tuple(plan.binding_certificate or ()):
			progress = certificate.get("recursive_progress_certificate")
			if not isinstance(progress, Mapping):
				continue
			if progress.get("certificate_kind") != (
				"well_founded_relational_count_decrease"
			):
				continue
			if str(progress.get("relation_predicate") or "") != relation:
				continue
			strict_actions = tuple(progress.get("strictly_decreasing_actions") or ())
			if not strict_actions:
				continue
			if not all(
				action_name in actions_by_name
				and any(
					effect.predicate == relation
					for effect in actions_by_name[action_name].delete_effects
				)
				for action_name in strict_actions
			):
				continue
			relation_arguments = tuple(
				str(item) for item in tuple(progress.get("relation_arguments") or ())
			)
			if len(relation_arguments) != 2:
				continue
			trigger_arguments = tuple(plan.trigger.arguments or ())
			anchor_positions = tuple(
				index
				for index, argument in enumerate(relation_arguments)
				if argument in trigger_arguments
			)
			if len(anchor_positions) != 1:
				continue
			anchor_position = anchor_positions[0]
			child_position = 1 - anchor_position
			child_argument = relation_arguments[child_position]
			if not any(
				step.kind == "subgoal"
				and step.symbol == plan.trigger.symbol
				and child_argument in step.arguments
				for step in plan.body
			):
				continue
			if not _recursive_module_closure_preserves_relation(
				plan,
				plan_library=plan_library,
				relation=relation,
				actions_by_name=actions_by_name,
			):
				continue
			if (
				require_global_producer_preservation
				and not _relation_producers_preserve_child_key(
					plan_library,
				relation=relation,
				child_position=child_position,
				actions_by_name=actions_by_name,
				)
			):
				continue
			return child_position, anchor_position
	return None


def _recursive_module_closure_preserves_relation(
	certificate_plan: AgentSpeakPlan,
	*,
	plan_library: PlanLibrary,
	relation: str,
	actions_by_name: Mapping[str, _ParsedAction],
) -> bool:
	call_graph: dict[str, set[str]] = {}
	for plan in tuple(plan_library.plans or ()):
		call_graph.setdefault(plan.trigger.symbol, set()).update(
			step.symbol for step in plan.body if step.kind == "subgoal"
		)
	reachable = {certificate_plan.trigger.symbol}
	frontier = [certificate_plan.trigger.symbol]
	while frontier:
		current = frontier.pop()
		for called in call_graph.get(current, set()):
			if called in reachable:
				continue
			reachable.add(called)
			frontier.append(called)
	for plan in tuple(plan_library.plans or ()):
		if plan.trigger.symbol not in reachable:
			continue
		for step in plan.body:
			if step.kind != "action":
				continue
			action = actions_by_name.get(step.symbol)
			if action is None:
				return False
			if any(effect.predicate == relation for effect in action.add_effects):
				return False
	return True


def _relation_producers_preserve_child_key(
	plan_library: PlanLibrary,
	*,
	relation: str,
	child_position: int,
	actions_by_name: Mapping[str, _ParsedAction],
) -> bool:
	for plan in tuple(plan_library.plans or ()):
		if plan.trigger.symbol != relation:
			continue
		trigger_arguments = tuple(plan.trigger.arguments or ())
		if len(trigger_arguments) != 2:
			return False
		for step in plan.body:
			if step.kind != "action":
				continue
			action = actions_by_name.get(step.symbol)
			if action is None or len(action.parameters) != len(step.arguments):
				return False
			binding = dict(zip(action.parameters, step.arguments))
			for effect in (*action.add_effects, *action.delete_effects):
				if effect.predicate != relation or len(effect.arguments) != 2:
					continue
				mapped_child = binding.get(
					effect.arguments[child_position],
					effect.arguments[child_position],
				)
				if mapped_child != trigger_arguments[child_position]:
					return False
	return True


def _relation_pairs_form_functional_acyclic_graph(
	pairs: Sequence[tuple[EffectTerm, EffectTerm]],
) -> bool:
	parent_by_child: dict[EffectTerm, EffectTerm] = {}
	for child, parent in tuple(pairs or ()):
		if child == parent:
			return False
		previous = parent_by_child.get(child)
		if previous is not None and previous != parent:
			return False
		parent_by_child[child] = parent
	for start in parent_by_child:
		seen: set[EffectTerm] = set()
		current = start
		while current in parent_by_child:
			if current in seen:
				return False
			seen.add(current)
			current = parent_by_child[current]
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
