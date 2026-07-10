"""
Synthesize compact recursive atomic literal modules from PDDL schemas.

The synthesizer uses external generalized-planning artifacts as evidence for
which atomic predicates matter, then compresses flat primitive macro evidence
into reusable predicate modules using PDDL action precondition/effect structure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from typing import Mapping, Sequence

import clingo

from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary
from utils.pddl_parser import PDDLAction
from utils.pddl_parser import PDDLDomain
from utils.pddl_parser import PDDLNumericCondition
from utils.pddl_parser import PDDLNumericEffect
from utils.pddl_parser import PDDLNumericExpression
from utils.pddl_parser import PDDLParser

from .pddl_types import OBJ_TP_PREDICATE
from .pddl_support import assert_compilable_pddl_files
from .pddl_types import type_closure


@dataclass(frozen=True)
class PDDLLiteralSchema:
	"""One lifted predicate literal from an action schema."""

	predicate: str
	arguments: tuple[str, ...]
	is_positive: bool = True

	def mapped(self, variable_map: Mapping[str, str]) -> "PDDLLiteralSchema":
		return PDDLLiteralSchema(
			predicate=self.predicate,
			arguments=tuple(variable_map.get(argument, _var(argument)) for argument in self.arguments),
			is_positive=self.is_positive,
		)

	def to_call(self) -> str:
		if not self.arguments:
			return self.predicate
		return f"{self.predicate}({', '.join(self.arguments)})"

	def to_context(self) -> str:
		call = self.to_call()
		return call if self.is_positive else f"not {call}"


@dataclass(frozen=True)
class AtomicModuleSynthesisReport:
	"""Summary of the compact atomic module library synthesis run."""

	seed_predicates: tuple[str, ...]
	module_predicates: tuple[str, ...]
	plan_count: int
	raw_candidate_count: int
	branch_count_by_predicate: Mapping[str, int]
	producer_actions_by_predicate: Mapping[str, tuple[str, ...]]
	recursive_predicates: tuple[str, ...]
	pruned_candidate_count: int
	selector_backend: str
	selector_objective: tuple[str, ...]
	selector_optimization_cost: tuple[int, ...]
	selector_obligation_count: int
	selected_branch_ids: tuple[str, ...]
	selection_scope: str
	candidate_source_counts: Mapping[str, int]
	evidence_obligation_count: int
	selector_coverage_basis: tuple[str, ...]
	rejected_uncertified_candidate_count: int
	ranking_incompatibility_count: int
	recursive_capability_obligation_count: int
	selected_recursive_capability_count: int
	predicate_roles: tuple[Mapping[str, object], ...]
	branch_certification_rules: tuple[str, ...]
	theoretical_basis: tuple[str, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"seed_predicates": list(self.seed_predicates),
			"module_predicates": list(self.module_predicates),
			"plan_count": self.plan_count,
			"raw_candidate_count": self.raw_candidate_count,
			"branch_count_by_predicate": dict(self.branch_count_by_predicate),
			"producer_actions_by_predicate": {
				predicate: list(actions)
				for predicate, actions in self.producer_actions_by_predicate.items()
			},
			"recursive_predicates": list(self.recursive_predicates),
			"pruned_candidate_count": self.pruned_candidate_count,
			"selector_backend": self.selector_backend,
			"selector_objective": list(self.selector_objective),
			"selector_optimization_cost": list(self.selector_optimization_cost),
			"selector_obligation_count": self.selector_obligation_count,
			"selected_branch_ids": list(self.selected_branch_ids),
			"selection_scope": self.selection_scope,
			"candidate_source_counts": dict(self.candidate_source_counts),
			"evidence_obligation_count": self.evidence_obligation_count,
			"selector_coverage_basis": list(self.selector_coverage_basis),
			"rejected_uncertified_candidate_count": (
				self.rejected_uncertified_candidate_count
			),
			"ranking_incompatibility_count": self.ranking_incompatibility_count,
			"recursive_capability_obligation_count": (
				self.recursive_capability_obligation_count
			),
			"selected_recursive_capability_count": (
				self.selected_recursive_capability_count
			),
			"predicate_roles": [dict(item) for item in self.predicate_roles],
			"branch_certification_rules": list(self.branch_certification_rules),
			"theoretical_basis": list(self.theoretical_basis),
		}


@dataclass(frozen=True)
class _SelectedModulePlans:
	"""Selected candidate branches plus solver metadata."""

	plans: tuple[AgentSpeakPlan, ...]
	report: "_ClingoBranchSelectorReport"


@dataclass(frozen=True)
class _ClingoBranchSelectorReport:
	"""Evidence that candidate branch selection was solved by Clingo/ASP."""

	backend: str
	raw_candidate_count: int
	selected_candidate_count: int
	obligation_count: int
	optimization_cost: tuple[int, ...]
	selected_branch_ids: tuple[str, ...]
	objective: tuple[str, ...]
	selection_scope: str
	candidate_source_counts: Mapping[str, int]
	evidence_obligation_count: int
	coverage_basis: tuple[str, ...]
	ranking_incompatibility_count: int
	recursive_capability_obligation_count: int
	selected_recursive_capability_count: int


@dataclass(frozen=True)
class _BranchEffectContract:
	"""Schema-derived final-state contract for one primitive-action branch."""

	must_add: frozenset[tuple[str, tuple[str, ...]]]
	may_delete: frozenset[tuple[str, tuple[str, ...]]]
	numeric_delta: tuple[tuple[str, tuple[str, ...], int], ...]
	resource_release: tuple[object, ...]
	complete: bool


def synthesize_atomic_minimal_literal_module_library(
	*,
	domain_file: str | Path,
	seed_predicates: Sequence[str],
	source_backend: str,
	source_name: str,
	policy_file: str | Path | None = None,
	validated_evidence_candidates: Sequence[AgentSpeakPlan] = (),
) -> PlanLibrary:
	"""Build compact recursive atomic modules for seed PDDL predicates."""

	pddl_support = assert_compilable_pddl_files(domain_file=domain_file)
	domain = PDDLParser.parse_domain(domain_file)
	declared_predicates = {predicate.name for predicate in domain.predicates}
	seeds = tuple(
		dict.fromkeys(
			predicate
			for predicate in (str(item).strip() for item in seed_predicates)
			if predicate and predicate in declared_predicates
		),
	)
	evidence_candidates = tuple(validated_evidence_candidates or ())
	if not seeds and not evidence_candidates:
		raise ValueError(
			"No declared seed predicates or validated evidence candidates were "
			"provided for atomic module synthesis.",
		)
	parsed_actions = tuple(_ParsedAction.from_pddl(action) for action in domain.actions)
	module_predicates = (
		_module_predicate_closure(
			seeds=seeds,
			actions=parsed_actions,
			declared_predicates=declared_predicates,
		)
		if seeds
		else ()
	)
	schema_candidates = _candidate_module_plans(
		domain=domain,
		actions=parsed_actions,
		seed_predicates=seeds,
		module_predicates=module_predicates,
		source_backend=source_backend,
		source_name=source_name,
		policy_file=policy_file,
	)
	raw_plans = tuple(
		_deduplicate_plans((*schema_candidates, *evidence_candidates)),
	)
	selection = _select_branches_with_clingo(
		raw_plans,
		schema_candidates=schema_candidates,
		evidence_obligations=evidence_candidates,
		actions=parsed_actions,
	)
	plans = _ensure_unique_plan_names(selection.plans)
	subgoal_step_count = sum(
		1
		for plan in plans
		for step in plan.body
		if step.kind == "subgoal"
	)
	primitive_action_step_count = sum(
		1
		for plan in plans
		for step in plan.body
		if step.kind == "action"
	)
	report = _module_synthesis_report(
		plans=plans,
		raw_plan_count=len(raw_plans),
		selection_report=selection.report,
		seeds=seeds,
		module_predicates=module_predicates,
		actions=parsed_actions,
		rejected_uncertified_candidate_count=0,
	)
	return PlanLibrary(
		domain_name=domain.name,
		plans=plans,
		initial_beliefs=(),
		metadata={
			"pddl_support": pddl_support.to_dict(),
			"generation_mode": "atomic_minimal_literal_module_library",
			"atomic_template_backend": source_backend,
			"source_name": source_name,
			"policy_file": str(policy_file) if policy_file is not None else None,
			"library_quality": {
				"artifact_classification": (
					"atomic_template_library"
					if plans
					else "empty_or_unbound_atomic_template_library"
				),
				"artifact_classification_basis": (
					"generic artifact label; structural categories are "
					"plan-template-level, not domain-level"
				),
				"library_profile": _library_template_profile(
					_plan_template_kind_counts(plans),
				),
				"plan_template_kind_counts": _plan_template_kind_counts(plans),
				"plan_template_classification_basis": (
					"per plan template: empty body is already-true, bodies with "
					"only primitive actions are action-only, bodies containing "
					"achievement subgoals are subgoal-decomposed"
				),
				"compact_recursive_module_ready": subgoal_step_count > 0,
				"plan_count": len(plans),
				"primitive_action_step_count": primitive_action_step_count,
				"subgoal_step_count": subgoal_step_count,
			},
			"atomic_module_synthesis": report.to_dict(),
		},
	)


def _plan_template_kind_counts(plans: Sequence[AgentSpeakPlan]) -> dict[str, int]:
	counts: dict[str, int] = {}
	for plan in tuple(plans or ()):
		kind = _plan_template_kind(plan)
		counts[kind] = counts.get(kind, 0) + 1
	return dict(sorted(counts.items()))


def _plan_template_kind(plan: AgentSpeakPlan) -> str:
	body = tuple(plan.body or ())
	if not body:
		return "already_true_plan_template"
	if any(step.kind == "subgoal" for step in body):
		return "subgoal_decomposed_plan_template"
	if all(step.kind == "action" for step in body):
		return "action_only_plan_template"
	return "mixed_body_plan_template"


def _library_template_profile(kind_counts: Mapping[str, int]) -> str:
	kinds = {kind for kind, count in dict(kind_counts).items() if count > 0}
	if not kinds:
		return "empty_atomic_template_library"
	if len(kinds) > 1:
		return "mixed_atomic_template_library"
	kind = next(iter(kinds))
	if kind == "already_true_plan_template":
		return "already_true_only_atomic_template_library"
	if kind == "action_only_plan_template":
		return "action_only_atomic_template_library"
	if kind == "subgoal_decomposed_plan_template":
		return "subgoal_decomposed_atomic_template_library"
	return "mixed_body_atomic_template_library"


@dataclass(frozen=True)
class _ParsedAction:
	name: str
	parameters: tuple[str, ...]
	parameter_types: Mapping[str, str]
	preconditions: tuple[PDDLLiteralSchema, ...]
	add_effects: tuple[PDDLLiteralSchema, ...]
	delete_effects: tuple[PDDLLiteralSchema, ...]
	numeric_preconditions: tuple[PDDLNumericCondition, ...] = ()
	numeric_effects: tuple[PDDLNumericEffect, ...] = ()

	@classmethod
	def from_pddl(cls, action: PDDLAction) -> "_ParsedAction":
		effects = _parse_pddl_literals(action.effects)
		return cls(
			name=action.name,
			parameters=tuple(_parameter_name(parameter) for parameter in action.parameters),
			parameter_types={
				_parameter_name(parameter): _parameter_type(parameter)
				for parameter in action.parameters
			},
			preconditions=tuple(_parse_pddl_literals(action.preconditions)),
			add_effects=tuple(literal for literal in effects if literal.is_positive),
			delete_effects=tuple(literal for literal in effects if not literal.is_positive),
			numeric_preconditions=tuple(
				getattr(action, "numeric_preconditions", ()) or (),
			),
			numeric_effects=tuple(
				getattr(action, "numeric_effects", ()) or (),
			),
		)


def _module_predicate_closure(
	*,
	seeds: Sequence[str],
	actions: Sequence[_ParsedAction],
	declared_predicates: set[str],
) -> tuple[str, ...]:
	module_predicates = set(seeds)
	module_predicates.update(
		effect.predicate
		for action in actions
		for effect in action.add_effects
		if effect.predicate in declared_predicates
	)
	changed = True
	while changed:
		changed = False
		for target_predicate in tuple(sorted(module_predicates)):
			for action, effect in _producer_effects(actions, target_predicate):
				_, variable_map = _head_variable_map(effect)
				variable_map = _complete_variable_map(action.parameters, variable_map)
				for predicate in _recursive_support_predicates(
					action=action,
					variable_map=variable_map,
					actions=actions,
					declared_predicates=declared_predicates,
				):
					if predicate != target_predicate and predicate not in module_predicates:
						module_predicates.add(predicate)
						changed = True
	return tuple(sorted(module_predicates))


def _candidate_module_plans(
	*,
	domain: PDDLDomain,
	actions: Sequence[_ParsedAction],
	seed_predicates: Sequence[str],
	module_predicates: Sequence[str],
	source_backend: str,
	source_name: str,
	policy_file: str | Path | None,
) -> tuple[AgentSpeakPlan, ...]:
	module_set = set(module_predicates)
	plans: list[AgentSpeakPlan] = []
	recursive_module_predicates = {
		predicate
		for predicate in module_set
		if _predicate_requires_recursive_module(predicate, actions)
	}
	for predicate in domain.predicates:
		if predicate.name not in module_set:
			continue
		head_arguments = tuple(_head_variable(index) for index, _ in enumerate(predicate.parameters))
		plans.append(
			AgentSpeakPlan(
				plan_name=f"{predicate.name}_already_true",
				trigger=AgentSpeakTrigger("achievement_goal", predicate.name, head_arguments),
				context=(_call(predicate.name, head_arguments),),
				body=(),
				binding_certificate=(
					{
						"artifact_family": "atomic_minimal_literal_module",
						"rule_kind": "already_true",
						"source_backend": source_backend,
						"source_name": source_name,
					},
				),
			),
		)
		for sequence in _producer_action_sequences(
			actions=actions,
			type_tokens=domain.types,
			seed_predicates=set(seed_predicates),
			target_predicate=predicate.name,
			module_predicates=module_set,
			recursive_module_predicates=recursive_module_predicates,
		):
			plans.extend(
				_sequence_module_plans(
					sequence=sequence,
					module_predicates=module_set,
					recursive_module_predicates=recursive_module_predicates,
					actions=actions,
					source_backend=source_backend,
					source_name=source_name,
					policy_file=policy_file,
				),
			)
	return tuple(_deduplicate_plans(plans))


@dataclass(frozen=True)
class _ActionCall:
	action: _ParsedAction
	arguments: tuple[str, ...]


@dataclass(frozen=True)
class _ProducerSequence:
	target_predicate: str
	target_arguments: tuple[str, ...]
	context_literals: tuple[PDDLLiteralSchema, ...]
	numeric_contexts: tuple[str, ...]
	guard_contexts: tuple[str, ...]
	type_contexts: tuple[str, ...]
	body_actions: tuple[_ActionCall, ...]
	producer_action_names: tuple[str, ...]
	resource_release_certificates: tuple[Mapping[str, object], ...] = ()


@dataclass(frozen=True)
class _CleanupExtension:
	context_literals: tuple[PDDLLiteralSchema, ...]
	guard_contexts: tuple[str, ...]
	body_actions: tuple[_ActionCall, ...]
	producer_action_names: tuple[str, ...]
	resource_release_certificates: tuple[Mapping[str, object], ...]


@dataclass(frozen=True)
class _FunctionalPredicateGroup:
	predicate: str
	key_positions: tuple[int, ...]
	value_positions: tuple[int, ...]
	key_types: tuple[str, ...]


@dataclass(frozen=True)
class _RecursiveProgressCertificate:
	"""Well-founded schema proof for one same-predicate recursive branch."""

	relation_predicate: str
	relation_arguments: tuple[str, ...]
	strictly_decreasing_actions: tuple[str, ...]
	non_increasing_actions: tuple[str, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"certificate_kind": "well_founded_relational_count_decrease",
			"ranking_feature_kind": "global_dynamic_atom_count",
			"relation_predicate": self.relation_predicate,
			"relation_arguments": list(self.relation_arguments),
			"strictly_decreasing_actions": list(self.strictly_decreasing_actions),
			"non_increasing_actions": list(self.non_increasing_actions),
			"lower_bound": 0,
		}


def _producer_action_sequences(
	*,
	actions: Sequence[_ParsedAction],
	type_tokens: Sequence[str],
	seed_predicates: set[str],
	target_predicate: str,
	module_predicates: set[str],
	recursive_module_predicates: set[str],
) -> tuple[_ProducerSequence, ...]:
	sequences: list[_ProducerSequence] = []
	functional_groups = _functional_predicate_groups(actions, type_tokens)
	dynamic_predicates = _dynamic_predicates(actions)
	for final_action, effect in _producer_effects(actions, target_predicate):
		head_arguments, variable_map = _head_variable_map(effect)
		variable_map = _complete_variable_map(final_action.parameters, variable_map)
		mapped_effect = effect.mapped(variable_map)
		transient_preconditions = _transient_preconditions(
			action=final_action,
			variable_map=variable_map,
			target_predicate=target_predicate,
			seed_predicates=seed_predicates,
			module_predicates=module_predicates,
			recursive_module_predicates=recursive_module_predicates,
		)
		if _has_arbitrary_extra_target_relation(
			action=final_action,
			target_effect=mapped_effect,
			variable_map=variable_map,
			target_arguments=head_arguments,
		):
			continue
		sequences.extend(_finalize_sequences(
			actions=actions,
			type_tokens=type_tokens,
			functional_groups=functional_groups,
			dynamic_predicates=dynamic_predicates,
			target_effect=mapped_effect,
			target_arguments=head_arguments,
			context_literals=tuple(
				precondition.mapped(variable_map)
				for precondition in final_action.preconditions
			),
			body_actions=(
				_action_call(final_action, variable_map),
			),
			producer_action_names=(final_action.name,),
		))
		for transient in transient_preconditions:
			for support_action, support_effect in _producer_effects(actions, transient.predicate):
				support_map = {
					raw_argument: mapped_argument
					for raw_argument, mapped_argument in zip(
						support_effect.arguments,
						transient.arguments,
					)
				}
				support_map = _complete_variable_map(
					support_action.parameters,
					support_map,
					avoid_variables=set(variable_map.values()) - set(support_map.values()),
				)
				support_effect_mapped = support_effect.mapped(support_map)
				if not _same_literal(support_effect_mapped, transient):
					continue
				if _has_arbitrary_extra_target_relation(
					action=support_action,
					target_effect=support_effect_mapped,
					variable_map=support_map,
					target_arguments=head_arguments,
				):
					continue
				base_context_literals = tuple(
					precondition.mapped(support_map)
					for precondition in support_action.preconditions
				) + tuple(
					precondition.mapped(variable_map)
					for precondition in final_action.preconditions
					if not _same_literal(precondition.mapped(variable_map), transient)
				)
				base_body_actions = (
					_action_call(support_action, support_map),
					_action_call(final_action, variable_map),
				)
				sequences.extend(_finalize_sequences(
					actions=actions,
					type_tokens=type_tokens,
					functional_groups=functional_groups,
					dynamic_predicates=dynamic_predicates,
					target_effect=mapped_effect,
					target_arguments=head_arguments,
					context_literals=base_context_literals,
					body_actions=base_body_actions,
					producer_action_names=(support_action.name, final_action.name),
				))
				for bridge in _bridge_action_sequences(
					actions=actions,
					type_tokens=type_tokens,
					support_action=support_action,
					support_map=support_map,
					final_action=final_action,
					final_map=variable_map,
					transient=transient,
					target_predicate=target_predicate,
					target_arguments=head_arguments,
					module_predicates=module_predicates,
				):
					sequences.extend(_finalize_sequences(
						actions=actions,
						type_tokens=type_tokens,
						functional_groups=functional_groups,
						dynamic_predicates=dynamic_predicates,
						target_effect=mapped_effect,
						target_arguments=head_arguments,
						context_literals=bridge.context_literals,
						body_actions=bridge.body_actions,
						producer_action_names=bridge.producer_action_names,
					))
	return tuple(_deduplicate_sequences(sequences))


@dataclass(frozen=True)
class _BridgeCandidate:
	context_literals: tuple[PDDLLiteralSchema, ...]
	body_actions: tuple[_ActionCall, ...]
	producer_action_names: tuple[str, ...]


def _bridge_action_sequences(
	*,
	actions: Sequence[_ParsedAction],
	type_tokens: Sequence[str],
	support_action: _ParsedAction,
	support_map: Mapping[str, str],
	final_action: _ParsedAction,
	final_map: Mapping[str, str],
	transient: PDDLLiteralSchema,
	target_predicate: str,
	target_arguments: Sequence[str],
	module_predicates: set[str],
) -> tuple[_BridgeCandidate, ...]:
	support_contexts = tuple(
		precondition.mapped(support_map)
		for precondition in support_action.preconditions
	)
	support_adds = tuple(effect.mapped(support_map) for effect in support_action.add_effects)
	available_after_support = support_contexts + support_adds
	final_preconditions = tuple(
		precondition.mapped(final_map)
		for precondition in final_action.preconditions
		if not _same_literal(precondition.mapped(final_map), transient)
	)
	missing_final_preconditions = tuple(
		literal
		for literal in final_preconditions
		if literal.is_positive
		and not _literal_in(literal, available_after_support)
	)
	candidates: list[_BridgeCandidate] = []
	for missing in missing_final_preconditions:
		if _should_delegate_missing_bridge_precondition(
			missing=missing,
			target_predicate=target_predicate,
			target_arguments=target_arguments,
			module_predicates=module_predicates,
		):
			continue
		for bridge_action, bridge_effect in _producer_effects(actions, missing.predicate):
			if bridge_action.name in {support_action.name, final_action.name}:
				continue
			bridge_map = {
				raw_argument: mapped_argument
				for raw_argument, mapped_argument in zip(
					bridge_effect.arguments,
					missing.arguments,
				)
			}
			bridge_map = _complete_variable_map(
				bridge_action.parameters,
				bridge_map,
				avoid_variables=set(final_map.values()) - set(bridge_map.values()),
			)
			if not _same_literal(bridge_effect.mapped(bridge_map), missing):
				continue
			bridge_preconditions = tuple(
				precondition.mapped(bridge_map)
				for precondition in bridge_action.preconditions
			)
			if not any(_literal_in(precondition, available_after_support) for precondition in bridge_preconditions):
				continue
			bridge_adds = tuple(effect.mapped(bridge_map) for effect in bridge_action.add_effects)
			context_literals = tuple(
				literal
				for literal in support_contexts + bridge_preconditions + final_preconditions
				if not _literal_in(literal, support_adds)
				and not _literal_in(literal, bridge_adds)
			)
			body_actions = (
				_action_call(support_action, support_map),
				_action_call(bridge_action, bridge_map),
				_action_call(final_action, final_map),
			)
			if not _action_calls_have_compatible_types(body_actions, type_tokens):
				continue
			base_candidate = _BridgeCandidate(
				context_literals=_deduplicate_literals(context_literals),
				body_actions=body_actions,
				producer_action_names=(
					support_action.name,
					bridge_action.name,
					final_action.name,
				),
			)
			candidates.append(base_candidate)
			candidates.extend(
				_prefix_bridge_action_sequences(
					actions=actions,
					type_tokens=type_tokens,
					base_candidate=base_candidate,
				),
			)
	return tuple(candidates)


def _prefix_bridge_action_sequences(
	*,
	actions: Sequence[_ParsedAction],
	type_tokens: Sequence[str],
	base_candidate: _BridgeCandidate,
) -> tuple[_BridgeCandidate, ...]:
	"""Add one producer before a bridge sequence when it establishes support context."""

	if not base_candidate.body_actions:
		return ()
	candidates: list[_BridgeCandidate] = []
	for context_literal in tuple(base_candidate.context_literals or ()):
		if not context_literal.is_positive:
			continue
		for prefix_action, prefix_effect in _producer_effects(actions, context_literal.predicate):
			prefix_map = {
				raw_argument: mapped_argument
				for raw_argument, mapped_argument in zip(
					prefix_effect.arguments,
					context_literal.arguments,
				)
			}
			prefix_map = _complete_variable_map(
				prefix_action.parameters,
				prefix_map,
				avoid_variables=_body_action_variables(base_candidate.body_actions)
				- set(prefix_map.values()),
			)
			prefix_effect_mapped = prefix_effect.mapped(prefix_map)
			if not _same_literal(prefix_effect_mapped, context_literal):
				continue
			prefix_adds = tuple(effect.mapped(prefix_map) for effect in prefix_action.add_effects)
			prefix_contexts = tuple(
				precondition.mapped(prefix_map)
				for precondition in prefix_action.preconditions
			)
			body_actions = (
				_action_call(prefix_action, prefix_map),
				*base_candidate.body_actions,
			)
			if not _action_calls_have_compatible_types(body_actions, type_tokens):
				continue
			context_literals = tuple(
				literal
				for literal in prefix_contexts + base_candidate.context_literals
				if not _literal_in(literal, prefix_adds)
			)
			candidates.append(
				_BridgeCandidate(
					context_literals=_deduplicate_literals(context_literals),
					body_actions=body_actions,
					producer_action_names=(
						prefix_action.name,
						*base_candidate.producer_action_names,
					),
				),
			)
	return tuple(candidates)


def _body_action_variables(body_actions: Sequence[_ActionCall]) -> set[str]:
	return {
		argument
		for call in tuple(body_actions or ())
		for argument in tuple(call.arguments or ())
	}


def _should_delegate_missing_bridge_precondition(
	*,
	missing: PDDLLiteralSchema,
	target_predicate: str,
	target_arguments: Sequence[str],
	module_predicates: set[str],
) -> bool:
	"""Prefer an atomic module when a bridge prepares non-head internal state."""

	if missing.predicate not in module_predicates:
		return False
	if missing.predicate == target_predicate:
		return False
	return not set(missing.arguments) <= set(target_arguments)


def _recursive_support_predicates(
	*,
	action: _ParsedAction,
	variable_map: Mapping[str, str],
	actions: Sequence[_ParsedAction],
	declared_predicates: set[str],
) -> tuple[str, ...]:
	predicates: set[str] = set()
	for precondition in action.preconditions:
		mapped = precondition.mapped(variable_map)
		if not mapped.is_positive or mapped.predicate not in declared_predicates:
			continue
		if _predicate_requires_recursive_module(mapped.predicate, actions):
			predicates.add(mapped.predicate)
		for producer, effect in _producer_effects(actions, mapped.predicate):
			support_map = {
				raw_argument: mapped_argument
				for raw_argument, mapped_argument in zip(effect.arguments, mapped.arguments)
			}
			support_map = _complete_variable_map(producer.parameters, support_map)
			for producer_precondition in producer.preconditions:
				nested = producer_precondition.mapped(support_map)
				if (
					nested.is_positive
					and nested.predicate in declared_predicates
					and _predicate_requires_recursive_module(nested.predicate, actions)
				):
					predicates.add(nested.predicate)
	return tuple(sorted(predicates))


def _predicate_requires_recursive_module(
	predicate: str,
	actions: Sequence[_ParsedAction],
) -> bool:
	for action, effect in _producer_effects(actions, predicate):
		head_arguments, variable_map = _head_variable_map(effect)
		variable_map = _complete_variable_map(action.parameters, variable_map)
		target = effect.mapped(variable_map)
		for precondition in action.preconditions:
			mapped = precondition.mapped(variable_map)
			if (
				mapped.is_positive
				and mapped.predicate == predicate
				and not _same_literal(mapped, target)
				and set(mapped.arguments) != set(head_arguments)
			):
				return True
	return False


def _transient_preconditions(
	*,
	action: _ParsedAction,
	variable_map: Mapping[str, str],
	target_predicate: str,
	seed_predicates: set[str],
	module_predicates: set[str],
	recursive_module_predicates: set[str],
) -> tuple[PDDLLiteralSchema, ...]:
	deleted = tuple(effect.mapped(variable_map) for effect in action.delete_effects)
	return tuple(
		mapped
		for precondition in action.preconditions
		for mapped in (precondition.mapped(variable_map),)
		if mapped.is_positive
		and mapped.arguments
		and _should_compose_transient_precondition(
			mapped,
			target_predicate=target_predicate,
			seed_predicates=seed_predicates,
			module_predicates=module_predicates,
			recursive_module_predicates=recursive_module_predicates,
		)
		and any(_same_atom(mapped, deleted_literal) for deleted_literal in deleted)
	)


def _should_compose_transient_precondition(
	literal: PDDLLiteralSchema,
	*,
	target_predicate: str,
	seed_predicates: set[str],
	module_predicates: set[str],
	recursive_module_predicates: set[str],
) -> bool:
	if literal.predicate not in module_predicates:
		return True
	return (
		target_predicate in seed_predicates
		and literal.predicate != target_predicate
		and literal.predicate not in recursive_module_predicates
	)


def _finalize_sequences(
	*,
	actions: Sequence[_ParsedAction],
	type_tokens: Sequence[str],
	functional_groups: Sequence[_FunctionalPredicateGroup],
	dynamic_predicates: set[str],
	target_effect: PDDLLiteralSchema,
	target_arguments: tuple[str, ...],
	context_literals: Sequence[PDDLLiteralSchema],
	body_actions: Sequence[_ActionCall],
	producer_action_names: tuple[str, ...],
) -> tuple[_ProducerSequence, ...]:
	if any(_same_literal(target_effect, literal) for literal in context_literals):
		return ()
	base_body = tuple(body_actions)
	base_contexts = tuple(context_literals)
	if not _action_calls_have_compatible_types(base_body, type_tokens):
		return ()
	cleanup_extensions = _cleanup_action_calls(
		actions=actions,
		type_tokens=type_tokens,
		target_effect=target_effect,
		target_arguments=target_arguments,
		context_literals=base_contexts,
		body_actions=base_body,
	)
	variants: tuple[_CleanupExtension | None, ...] = cleanup_extensions or (None,)
	sequences: list[_ProducerSequence] = []
	for cleanup_extension in variants:
		sequence_body = base_body
		sequence_contexts = base_contexts
		sequence_action_names = producer_action_names
		guard_contexts: tuple[str, ...] = ()
		resource_release_certificates: tuple[Mapping[str, object], ...] = ()
		if cleanup_extension is not None:
			sequence_body += cleanup_extension.body_actions
			sequence_contexts += cleanup_extension.context_literals
			guard_contexts = cleanup_extension.guard_contexts
			resource_release_certificates = cleanup_extension.resource_release_certificates
			sequence_action_names += cleanup_extension.producer_action_names
		if not _action_calls_have_compatible_types(sequence_body, type_tokens):
			continue
		type_contexts = _obj_tp_contexts_for_action_calls(sequence_body, type_tokens)
		if type_contexts is None:
			continue
		numeric_contexts = _numeric_contexts_for_action_calls(sequence_body)
		deduplicated_contexts = _deduplicate_literals(sequence_contexts)
		range_restricted_contexts = _range_restricted_context_literals(
			context_literals=deduplicated_contexts,
			head_arguments=target_arguments,
			dynamic_predicates=dynamic_predicates,
		)
		if range_restricted_contexts is None:
			continue
		has_functional_conflict = _has_functional_context_conflict(
			context_literals=range_restricted_contexts,
			body_actions=sequence_body,
			type_tokens=type_tokens,
			functional_groups=functional_groups,
		)
		if has_functional_conflict and not resource_release_certificates:
			continue
		if resource_release_certificates:
			execution_guards = _symbolic_sequence_execution_guards(
				target_effect=target_effect,
				context_literals=range_restricted_contexts,
				body_actions=sequence_body,
			)
			if execution_guards is None:
				continue
			guard_contexts = _deduplicate((*guard_contexts, *execution_guards))
			resource_release_certificates = tuple(
				{
					**dict(certificate),
					"sequence_alias_guards": list(execution_guards),
				}
				for certificate in resource_release_certificates
			)
		elif not _symbolic_sequence_is_executable(
			target_effect=target_effect,
			context_literals=range_restricted_contexts,
			body_actions=sequence_body,
		):
			continue
		sequences.append(
			_ProducerSequence(
				target_predicate=target_effect.predicate,
				target_arguments=target_arguments,
				context_literals=range_restricted_contexts,
				numeric_contexts=numeric_contexts,
				guard_contexts=guard_contexts,
				type_contexts=type_contexts,
				body_actions=sequence_body,
				producer_action_names=sequence_action_names,
				resource_release_certificates=resource_release_certificates,
			),
		)
	return tuple(_deduplicate_sequences(sequences))


def _cleanup_action_calls(
	*,
	actions: Sequence[_ParsedAction],
	type_tokens: Sequence[str],
	target_effect: PDDLLiteralSchema,
	target_arguments: tuple[str, ...],
	context_literals: tuple[PDDLLiteralSchema, ...],
	body_actions: tuple[_ActionCall, ...],
) -> tuple[_CleanupExtension, ...]:
	if not body_actions:
		return ()
	last_call = body_actions[-1]
	last_map = {
		parameter: argument
		for parameter, argument in zip(last_call.action.parameters, last_call.arguments)
	}
	available = tuple(effect.mapped(last_map) for effect in last_call.action.add_effects)
	deleted = tuple(effect.mapped(last_map) for effect in last_call.action.delete_effects)
	true_before_cleanup = _positive_state_after_action_calls(
		context_literals=context_literals,
		body_actions=body_actions,
	)
	extensions: list[_CleanupExtension] = []
	for cleanup_action in actions:
		if cleanup_action.name == last_call.action.name:
			continue
		for cleanup_map, released_literal in _cleanup_variable_maps(
			cleanup_action=cleanup_action,
			available_literals=available,
			true_before_cleanup=true_before_cleanup,
			target_effect=target_effect,
			target_arguments=target_arguments,
		):
			mapped_preconditions = tuple(
				precondition.mapped(cleanup_map)
				for precondition in cleanup_action.preconditions
			)
			if any(not literal.is_positive for literal in mapped_preconditions):
				continue
			mapped_adds = tuple(
				effect.mapped(cleanup_map)
				for effect in cleanup_action.add_effects
			)
			mapped_deletes = tuple(
				effect.mapped(cleanup_map)
				for effect in cleanup_action.delete_effects
			)
			if not any(
				_same_atom(released_literal, deleted_literal)
				for deleted_literal in mapped_deletes
			):
				continue
			if any(released_literal.predicate == deleted_literal.predicate for deleted_literal in deleted):
				continue
			if not any(
				any(_same_atom(add_literal, deleted_literal) for deleted_literal in deleted)
				for add_literal in mapped_adds
			):
				continue
			restored_literals = tuple(
				add_literal
				for add_literal in mapped_adds
				if any(_same_atom(add_literal, deleted_literal) for deleted_literal in deleted)
			)
			if not restored_literals:
				continue
			capacity_invariant = _causal_resource_capacity_invariant(
				resource_debt_literal=released_literal,
				restored_literals=restored_literals,
				producer_preconditions=tuple(
					precondition.mapped(last_map)
					for precondition in last_call.action.preconditions
				),
			)
			if capacity_invariant is None:
				continue
			guard_contexts = _target_preservation_guards(
				target_effect=target_effect,
				mapped_deletes=mapped_deletes,
			)
			if guard_contexts is None:
				continue
			if _has_arbitrary_extra_target_relation(
				action=cleanup_action,
				target_effect=target_effect,
				variable_map=cleanup_map,
				target_arguments=target_arguments,
			):
				continue
			cleanup_call = _action_call(cleanup_action, cleanup_map)
			if not _action_calls_have_compatible_types((*body_actions, cleanup_call), type_tokens):
				continue
			extra_contexts = tuple(
				literal
				for literal in mapped_preconditions
				if not any(
					_same_literal(literal, state_literal)
					for state_literal in true_before_cleanup
				)
			)
			resource_certificate = {
				"certificate_kind": "causal_resource_capacity_invariant_discharge",
				"producer_action": last_call.action.name,
				"release_action": cleanup_action.name,
				"resource_debt_literal": released_literal.to_call(),
				"restored_literals": [
					add_literal.to_call()
					for add_literal in restored_literals
				],
				"target_preserved": True,
				**capacity_invariant,
				"target_preservation_guards": list(guard_contexts),
			}
			extensions.append(
				_CleanupExtension(
					context_literals=_deduplicate_literals(extra_contexts),
					guard_contexts=guard_contexts,
					body_actions=(cleanup_call,),
					producer_action_names=(cleanup_action.name,),
					resource_release_certificates=(resource_certificate,),
				),
			)
	return _deduplicate_cleanup_extensions(extensions)


def _causal_resource_capacity_invariant(
	*,
	resource_debt_literal: PDDLLiteralSchema,
	restored_literals: Sequence[PDDLLiteralSchema],
	producer_preconditions: Sequence[PDDLLiteralSchema],
) -> Mapping[str, object] | None:
	"""Infer a free-key/occupied-key transition; reject structurally symmetric modes."""

	debt_arguments = set(resource_debt_literal.arguments)
	for restored in restored_literals:
		key_arguments = set(restored.arguments)
		occupancy_arguments = debt_arguments - key_arguments
		if not key_arguments < debt_arguments or not occupancy_arguments:
			continue
		if not any(_same_atom(restored, item) for item in producer_preconditions):
			continue
		return {
			"resource_invariant_kind": "keyed_single_capacity_occupancy_transition",
			"capacity_key_arguments": sorted(key_arguments),
			"occupancy_arguments": sorted(occupancy_arguments),
			"orientation_basis": (
				"producer consumes the key-only free mode and creates the "
				"key-plus-occupant debt mode; cleanup performs the inverse transition"
			),
		}
	return None


def _deduplicate_cleanup_extensions(
	extensions: Sequence[_CleanupExtension],
) -> tuple[_CleanupExtension, ...]:
	seen: set[tuple[object, ...]] = set()
	deduplicated: list[_CleanupExtension] = []
	for extension in extensions:
		key = (
			tuple(literal.to_context() for literal in extension.context_literals),
			extension.guard_contexts,
			tuple(
				(call.action.name, call.arguments)
				for call in extension.body_actions
			),
		)
		if key in seen:
			continue
		seen.add(key)
		deduplicated.append(extension)
	return tuple(deduplicated)


def _positive_state_after_action_calls(
	*,
	context_literals: Sequence[PDDLLiteralSchema],
	body_actions: Sequence[_ActionCall],
) -> tuple[PDDLLiteralSchema, ...]:
	state: dict[tuple[str, tuple[str, ...]], PDDLLiteralSchema | None] = {}
	for literal in context_literals:
		state[_atom_key(literal)] = literal if literal.is_positive else None
	for call in body_actions:
		variable_map = {
			parameter: argument
			for parameter, argument in zip(call.action.parameters, call.arguments)
		}
		for effect in call.action.delete_effects:
			state[_atom_key(effect.mapped(variable_map))] = None
		for effect in call.action.add_effects:
			mapped = effect.mapped(variable_map)
			state[_atom_key(mapped)] = mapped
	return tuple(literal for literal in state.values() if literal is not None)


def _cleanup_variable_maps(
	*,
	cleanup_action: _ParsedAction,
	available_literals: Sequence[PDDLLiteralSchema],
	true_before_cleanup: Sequence[PDDLLiteralSchema],
	target_effect: PDDLLiteralSchema,
	target_arguments: Sequence[str],
) -> tuple[tuple[dict[str, str], PDDLLiteralSchema], ...]:
	candidates: list[tuple[dict[str, str], PDDLLiteralSchema]] = []
	protected_assignments = _protected_delete_assignments(
		cleanup_action=cleanup_action,
		target_effect=target_effect,
	)
	for precondition in cleanup_action.preconditions:
		if not precondition.is_positive:
			continue
		for available in available_literals:
			variable_map = _literal_schema_variable_map(
				pattern=precondition,
				literal=available,
				parameters=cleanup_action.parameters,
				protected_assignments=protected_assignments,
			)
			if variable_map is None:
				continue
			partial_maps = _bind_cleanup_maps_from_state(
				cleanup_action=cleanup_action,
				variable_map=variable_map,
				true_before_cleanup=true_before_cleanup,
				protected_assignments=protected_assignments,
			)
			for partial_map in partial_maps:
				completed_map = _complete_cleanup_variable_map(
					parameters=cleanup_action.parameters,
					variable_map=partial_map,
					protected_assignments=protected_assignments,
					target_arguments=target_arguments,
				)
				candidates.append((completed_map, available))
	return _deduplicate_cleanup_variable_maps(candidates)


def _literal_schema_variable_map(
	*,
	pattern: PDDLLiteralSchema,
	literal: PDDLLiteralSchema,
	parameters: Sequence[str],
	protected_assignments: Mapping[str, set[str]],
) -> dict[str, str] | None:
	if pattern.predicate != literal.predicate or len(pattern.arguments) != len(literal.arguments):
		return None
	parameter_names = set(parameters)
	variable_map: dict[str, str] = {}
	for raw_argument, mapped_argument in zip(pattern.arguments, literal.arguments):
		if raw_argument not in parameter_names:
			if raw_argument != mapped_argument:
				return None
			continue
		if _cleanup_assignment_is_protected(
			parameter=raw_argument,
			candidate=mapped_argument,
			protected_assignments=protected_assignments,
		):
			return None
		variable_map[raw_argument] = mapped_argument
	return variable_map


def _bind_cleanup_maps_from_state(
	*,
	cleanup_action: _ParsedAction,
	variable_map: Mapping[str, str],
	true_before_cleanup: Sequence[PDDLLiteralSchema],
	protected_assignments: Mapping[str, set[str]],
) -> tuple[dict[str, str], ...]:
	"""Enumerate every positive-state join while retaining unbound alternatives."""

	bound_maps: list[dict[str, str]] = [dict(variable_map)]
	seen = {_cleanup_variable_map_key(variable_map)}
	index = 0
	while index < len(bound_maps):
		bound = bound_maps[index]
		index += 1
		for precondition in cleanup_action.preconditions:
			if not precondition.is_positive:
				continue
			for state_literal in _cleanup_state_binding_order(true_before_cleanup, bound):
				extended = _extend_cleanup_map_from_literal(
					pattern=precondition,
					literal=state_literal,
					parameters=cleanup_action.parameters,
					variable_map=bound,
					protected_assignments=protected_assignments,
				)
				if extended is None or extended == bound:
					continue
				key = _cleanup_variable_map_key(extended)
				if key in seen:
					continue
				seen.add(key)
				bound_maps.append(extended)
	return tuple(bound_maps)


def _deduplicate_cleanup_variable_maps(
	candidates: Sequence[tuple[dict[str, str], PDDLLiteralSchema]],
) -> tuple[tuple[dict[str, str], PDDLLiteralSchema], ...]:
	seen: set[tuple[tuple[str, str], ...]] = set()
	deduplicated: list[tuple[dict[str, str], PDDLLiteralSchema]] = []
	for variable_map, available in candidates:
		key = _cleanup_variable_map_key(variable_map)
		if key in seen:
			continue
		seen.add(key)
		deduplicated.append((variable_map, available))
	return tuple(deduplicated)


def _cleanup_variable_map_key(
	variable_map: Mapping[str, str],
) -> tuple[tuple[str, str], ...]:
	return tuple(sorted(variable_map.items()))


def _cleanup_state_binding_order(
	literals: Sequence[PDDLLiteralSchema],
	variable_map: Mapping[str, str],
) -> tuple[PDDLLiteralSchema, ...]:
	bound_values = set(variable_map.values())
	return tuple(
		sorted(
			literals,
			key=lambda literal: (
				-sum(1 for argument in literal.arguments if argument in bound_values),
				len(literal.arguments),
				literal.predicate,
				literal.arguments,
			),
		),
	)


def _extend_cleanup_map_from_literal(
	*,
	pattern: PDDLLiteralSchema,
	literal: PDDLLiteralSchema,
	parameters: Sequence[str],
	variable_map: Mapping[str, str],
	protected_assignments: Mapping[str, set[str]],
) -> dict[str, str] | None:
	if pattern.predicate != literal.predicate or len(pattern.arguments) != len(literal.arguments):
		return None
	parameter_names = set(parameters)
	extended = dict(variable_map)
	for raw_argument, mapped_argument in zip(pattern.arguments, literal.arguments):
		if raw_argument not in parameter_names:
			if raw_argument != mapped_argument:
				return None
			continue
		current = extended.get(raw_argument)
		if current is not None:
			if current != mapped_argument:
				return None
			continue
		if raw_argument in protected_assignments:
			return None
		if _cleanup_assignment_is_protected(
			parameter=raw_argument,
			candidate=mapped_argument,
			protected_assignments=protected_assignments,
		):
			return None
		extended[raw_argument] = mapped_argument
	return extended


def _complete_cleanup_variable_map(
	*,
	parameters: Sequence[str],
	variable_map: Mapping[str, str],
	protected_assignments: Mapping[str, set[str]],
	target_arguments: Sequence[str],
) -> dict[str, str]:
	completed = dict(variable_map)
	used_variables = set(completed.values())
	for parameter in parameters:
		if parameter in completed:
			continue
		avoid_variables = set(target_arguments)
		if protected_assignments.get(parameter):
			avoid_variables.update(protected_assignments[parameter])
		next_index = 0
		while (
			_head_variable(next_index) in used_variables
			or _head_variable(next_index) in avoid_variables
		):
			next_index += 1
		completed[parameter] = _head_variable(next_index)
		used_variables.add(completed[parameter])
	return completed


def _protected_delete_assignments(
	*,
	cleanup_action: _ParsedAction,
	target_effect: PDDLLiteralSchema,
) -> dict[str, set[str]]:
	protected: dict[str, set[str]] = {}
	for delete_effect in cleanup_action.delete_effects:
		if (
			delete_effect.predicate != target_effect.predicate
			or len(delete_effect.arguments) != len(target_effect.arguments)
		):
			continue
		for raw_argument, target_argument in zip(delete_effect.arguments, target_effect.arguments):
			if raw_argument == target_argument:
				continue
			protected.setdefault(raw_argument, set()).add(target_argument)
	return protected


def _cleanup_assignment_is_protected(
	*,
	parameter: str,
	candidate: str,
	protected_assignments: Mapping[str, set[str]],
) -> bool:
	return candidate in protected_assignments.get(parameter, set())


def _target_preservation_guards(
	*,
	target_effect: PDDLLiteralSchema,
	mapped_deletes: Sequence[PDDLLiteralSchema],
) -> tuple[str, ...] | None:
	guards: list[str] = []
	for deleted in mapped_deletes:
		if deleted.predicate != target_effect.predicate:
			continue
		if len(deleted.arguments) != len(target_effect.arguments):
			continue
		if tuple(deleted.arguments) == tuple(target_effect.arguments):
			return None
		guard = _non_unification_guard(deleted.arguments, target_effect.arguments)
		if guard is None:
			return None
		if guard:
			guards.append(guard)
	return _deduplicate(tuple(guards))


def _non_unification_guard(
	left_arguments: Sequence[str],
	right_arguments: Sequence[str],
) -> str | None:
	for left, right in zip(left_arguments, right_arguments):
		if left == right:
			continue
		if not (_is_agentspeak_variable(left) or _is_agentspeak_variable(right)):
			return ""
		return _inequality_guard_text(left, right)
	return None


def _inequality_guard_text(left: str, right: str) -> str:
	left_is_variable = _is_agentspeak_variable(left)
	right_is_variable = _is_agentspeak_variable(right)
	if right_is_variable and not left_is_variable:
		left, right = right, left
	elif left_is_variable == right_is_variable and right < left:
		left, right = right, left
	return f"{left} \\== {right}"


def _numeric_contexts_for_action_calls(
	body_actions: Sequence[_ActionCall],
) -> tuple[str, ...]:
	contexts: list[str] = []
	used_variables = {
		argument
		for call in tuple(body_actions or ())
		for argument in tuple(call.arguments or ())
		if _is_agentspeak_variable(argument)
	}
	for call in tuple(body_actions or ()):
		variable_map = {
			parameter: argument
			for parameter, argument in zip(call.action.parameters, call.arguments)
		}
		for condition in call.action.numeric_preconditions:
			contexts.extend(
				_numeric_condition_contexts(
					condition=condition,
					variable_map=variable_map,
					used_variables=used_variables,
				),
			)
	return _deduplicate(tuple(contexts))


def _numeric_condition_contexts(
	*,
	condition: PDDLNumericCondition,
	variable_map: Mapping[str, str],
	used_variables: set[str],
) -> tuple[str, ...]:
	fluent_contexts: list[str] = []
	value_variables_by_fluent: dict[tuple[str, tuple[str, ...]], str] = {}

	def render_term(expression: PDDLNumericExpression) -> str:
		if expression.kind == "constant":
			return str(expression.value)
		arguments = tuple(
			_map_numeric_argument(argument, variable_map)
			for argument in tuple(expression.args or ())
		)
		key = (str(expression.value), arguments)
		value_variable = value_variables_by_fluent.get(key)
		if value_variable is None:
			value_variable = _fresh_numeric_value_variable(used_variables)
			used_variables.add(value_variable)
			value_variables_by_fluent[key] = value_variable
			fluent_contexts.append(
				_numeric_fluent_context(
					function=str(expression.value),
					arguments=arguments,
					value_variable=value_variable,
				),
			)
		return value_variable

	left = render_term(condition.left)
	right = render_term(condition.right)
	return tuple(fluent_contexts + [f"{left} {condition.comparator} {right}"])


def _map_numeric_argument(argument: str, variable_map: Mapping[str, str]) -> str:
	text = str(argument or "").strip()
	name = _parameter_name(text)
	if name in variable_map:
		return variable_map[name]
	if text.startswith("?"):
		return _var(name)
	return name


def _numeric_fluent_context(
	*,
	function: str,
	arguments: Sequence[str],
	value_variable: str,
) -> str:
	return _call(str(function), (*tuple(arguments or ()), value_variable))


def _fresh_numeric_value_variable(used_variables: set[str]) -> str:
	for candidate in ("N", "M", "K", "Q", "R"):
		if candidate not in used_variables:
			return candidate
	index = 0
	while f"N{index}" in used_variables:
		index += 1
	return f"N{index}"


def _literal_in(
	literal: PDDLLiteralSchema,
	candidates: Sequence[PDDLLiteralSchema],
) -> bool:
	return any(_same_literal(literal, candidate) for candidate in candidates)


def _dynamic_predicates(actions: Sequence[_ParsedAction]) -> set[str]:
	return {
		literal.predicate
		for action in actions
		for literal in (*action.add_effects, *action.delete_effects)
	}


def _range_restricted_context_literals(
	*,
	context_literals: Sequence[PDDLLiteralSchema],
	head_arguments: Sequence[str],
	dynamic_predicates: set[str],
) -> tuple[PDDLLiteralSchema, ...] | None:
	"""Keep only context literals whose variables are safely range-restricted."""

	bound_variables = set(head_arguments)
	selected: list[PDDLLiteralSchema] = []
	remaining = list(context_literals)
	changed = True
	while changed:
		changed = False
		for literal in tuple(remaining):
			literal_variables = set(literal.arguments)
			if not literal.is_positive:
				continue
			if literal.predicate not in dynamic_predicates and not (
				literal_variables <= bound_variables or literal_variables & bound_variables
			):
				continue
			selected.append(literal)
			remaining.remove(literal)
			bound_variables.update(literal_variables)
			changed = True
	for literal in tuple(remaining):
		literal_variables = set(literal.arguments)
		if literal_variables - bound_variables:
			if not literal.is_positive:
				return None
			continue
		selected.append(literal)
	return _deduplicate_literals(tuple(selected))


def _action_calls_have_compatible_types(
	body_actions: Sequence[_ActionCall],
	type_tokens: Sequence[str],
) -> bool:
	return _obj_tp_contexts_for_action_calls(body_actions, type_tokens) is not None


def _obj_tp_contexts_for_action_calls(
	body_actions: Sequence[_ActionCall],
	type_tokens: Sequence[str],
) -> tuple[str, ...] | None:
	types_by_argument = _argument_required_types(body_actions)
	contexts: list[str] = []
	for argument, type_names in sorted(types_by_argument.items()):
		most_specific = _most_specific_compatible_types(type_names, type_tokens)
		if most_specific is None:
			return None
		for type_name in most_specific:
			if type_name == "object":
				continue
			contexts.append(f"{OBJ_TP_PREDICATE}({argument}, {type_name})")
	return tuple(dict.fromkeys(contexts))


def _filter_obj_tp_contexts(
	contexts: Sequence[str],
	variables: set[str],
) -> tuple[str, ...]:
	return tuple(
		context
		for context in tuple(contexts or ())
		if (_obj_tp_context_variable(context) in variables)
	)


def _obj_tp_context_variable(context: str) -> str | None:
	text = str(context or "").strip()
	prefix = f"{OBJ_TP_PREDICATE}("
	if not text.startswith(prefix) or not text.endswith(")"):
		return None
	arguments = tuple(argument.strip() for argument in text[len(prefix) : -1].split(","))
	if len(arguments) != 2:
		return None
	return arguments[0]


def _most_specific_compatible_types(
	type_names: set[str],
	type_tokens: Sequence[str],
) -> tuple[str, ...] | None:
	normalized = tuple(dict.fromkeys(_canonical_type_name(item) for item in type_names))
	non_object = tuple(type_name for type_name in normalized if type_name != "object")
	if not non_object:
		return ()
	for left in non_object:
		for right in non_object:
			if left == right:
				continue
			if not _types_are_compatible(left, right, type_tokens):
				return None
	most_specific = tuple(
		type_name
		for type_name in non_object
		if not any(
			type_name != other
			and _is_subtype(other, type_name, type_tokens)
			for other in non_object
		)
	)
	return tuple(dict.fromkeys(most_specific))


def _types_are_compatible(left: str, right: str, type_tokens: Sequence[str]) -> bool:
	if left == "object" or right == "object":
		return True
	return _is_subtype(left, right, type_tokens) or _is_subtype(right, left, type_tokens)


def _is_subtype(child: str, parent: str, type_tokens: Sequence[str]) -> bool:
	return _canonical_type_name(parent) in type_closure(_canonical_type_name(child), type_tokens)


def _canonical_type_name(type_name: str) -> str:
	return str(type_name or "").strip().lower() or "object"


def _symbolic_sequence_is_executable(
	*,
	target_effect: PDDLLiteralSchema,
	context_literals: Sequence[PDDLLiteralSchema],
	body_actions: Sequence[_ActionCall],
) -> bool:
	state: dict[tuple[str, tuple[str, ...]], bool] = {}
	for literal in context_literals:
		key = _atom_key(literal)
		value = literal.is_positive
		if key in state and state[key] != value:
			return False
		state[key] = value
	for call in body_actions:
		variable_map = {
			parameter: argument
			for parameter, argument in zip(call.action.parameters, call.arguments)
		}
		for precondition in call.action.preconditions:
			mapped = precondition.mapped(variable_map)
			current_value = state.get(_atom_key(mapped))
			if mapped.is_positive and current_value is not True:
				return False
			if not mapped.is_positive and current_value is not False:
				return False
		for effect in call.action.delete_effects:
			state[_atom_key(effect.mapped(variable_map))] = False
		for effect in call.action.add_effects:
			state[_atom_key(effect.mapped(variable_map))] = True
	return state.get(_atom_key(target_effect)) is True


def _symbolic_sequence_execution_guards(
	*,
	target_effect: PDDLLiteralSchema,
	context_literals: Sequence[PDDLLiteralSchema],
	body_actions: Sequence[_ActionCall],
) -> tuple[str, ...] | None:
	"""Certify every context-permitted aliasing of a symbolic action sequence."""

	state: dict[tuple[str, tuple[str, ...]], bool] = {}
	guards: list[str] = []
	for literal in context_literals:
		key = _atom_key(literal)
		value = literal.is_positive
		if key in state and state[key] != value:
			return None
		conflict_guards = _symbolic_alias_conflict_guards(
			state=state,
			literal=literal,
			expected_value=value,
		)
		if conflict_guards is None:
			return None
		guards.extend(conflict_guards)
		state[key] = value
	for call in body_actions:
		variable_map = {
			parameter: argument
			for parameter, argument in zip(call.action.parameters, call.arguments)
		}
		for precondition in call.action.preconditions:
			mapped = precondition.mapped(variable_map)
			current_value = state.get(_atom_key(mapped))
			expected_value = mapped.is_positive
			if current_value is not expected_value:
				return None
			conflict_guards = _symbolic_alias_conflict_guards(
				state=state,
				literal=mapped,
				expected_value=expected_value,
			)
			if conflict_guards is None:
				return None
			guards.extend(conflict_guards)
		for effect in call.action.delete_effects:
			state[_atom_key(effect.mapped(variable_map))] = False
		for effect in call.action.add_effects:
			state[_atom_key(effect.mapped(variable_map))] = True
	if state.get(_atom_key(target_effect)) is not True:
		return None
	target_guards = _symbolic_alias_conflict_guards(
		state=state,
		literal=target_effect,
		expected_value=True,
	)
	if target_guards is None:
		return None
	guards.extend(target_guards)
	return _deduplicate(tuple(guards))


def _symbolic_alias_conflict_guards(
	*,
	state: Mapping[tuple[str, tuple[str, ...]], bool],
	literal: PDDLLiteralSchema,
	expected_value: bool,
) -> tuple[str, ...] | None:
	guards: list[str] = []
	for (predicate, arguments), value in state.items():
		if value is expected_value:
			continue
		if predicate != literal.predicate or len(arguments) != len(literal.arguments):
			continue
		guard = _exact_non_unification_guard(literal.arguments, arguments)
		if guard is None:
			return None
		if guard:
			guards.append(guard)
	return _deduplicate(tuple(guards))


def _exact_non_unification_guard(
	left_arguments: Sequence[str],
	right_arguments: Sequence[str],
) -> str | None:
	"""Return an exact conjunctive guard, or None when disjunction is required."""

	differences: list[tuple[str, str]] = []
	for left, right in zip(left_arguments, right_arguments):
		if left == right:
			continue
		if not (_is_agentspeak_variable(left) or _is_agentspeak_variable(right)):
			return ""
		differences.append((left, right))
	if len(differences) != 1:
		return None
	return _inequality_guard_text(*differences[0])


def _atom_key(literal: PDDLLiteralSchema) -> tuple[str, tuple[str, ...]]:
	return (literal.predicate, literal.arguments)


def _functional_predicate_groups(
	actions: Sequence[_ParsedAction],
	type_tokens: Sequence[str],
) -> tuple[_FunctionalPredicateGroup, ...]:
	candidates: list[_FunctionalPredicateGroup] = []
	for action in actions:
		for add_effect in action.add_effects:
			for delete_effect in action.delete_effects:
				if add_effect.predicate != delete_effect.predicate:
					continue
				if len(add_effect.arguments) != len(delete_effect.arguments):
					continue
				value_positions = tuple(
					index
					for index, (add_arg, delete_arg) in enumerate(
						zip(add_effect.arguments, delete_effect.arguments),
					)
					if add_arg != delete_arg
				)
				if not value_positions:
					continue
				key_positions = tuple(
					index
					for index in range(len(add_effect.arguments))
					if index not in value_positions
				)
				key_types = tuple(
					_literal_argument_type(action, add_effect.arguments[index])
					for index in key_positions
				)
				candidate = _FunctionalPredicateGroup(
					predicate=add_effect.predicate,
					key_positions=key_positions,
					value_positions=value_positions,
					key_types=key_types,
				)
				if candidate not in candidates:
					candidates.append(candidate)
	return tuple(
		candidate
		for candidate in candidates
		if _functional_group_is_not_invalidated(candidate, actions, type_tokens)
	)


def _functional_group_is_not_invalidated(
	group: _FunctionalPredicateGroup,
	actions: Sequence[_ParsedAction],
	type_tokens: Sequence[str],
) -> bool:
	for action in actions:
		for add_effect in action.add_effects:
			if add_effect.predicate != group.predicate:
				continue
			if not _effect_key_types_compatible(group, action, add_effect, type_tokens):
				continue
			if not any(
				delete_effect.predicate == group.predicate
				and len(delete_effect.arguments) == len(add_effect.arguments)
				and all(
					delete_effect.arguments[position] == add_effect.arguments[position]
					for position in group.key_positions
				)
				and any(
					delete_effect.arguments[position] != add_effect.arguments[position]
					for position in group.value_positions
				)
				for delete_effect in action.delete_effects
			):
				return False
	return True


def _effect_key_types_compatible(
	group: _FunctionalPredicateGroup,
	action: _ParsedAction,
	effect: PDDLLiteralSchema,
	type_tokens: Sequence[str],
) -> bool:
	return all(
		_types_are_compatible(
			group_type,
			_literal_argument_type(action, effect.arguments[position]),
			type_tokens,
		)
		for group_type, position in zip(group.key_types, group.key_positions)
	)


def _literal_argument_type(action: _ParsedAction, argument: str) -> str:
	return _canonical_type_name(action.parameter_types.get(argument, "object"))


def _has_functional_context_conflict(
	*,
	context_literals: Sequence[PDDLLiteralSchema],
	body_actions: Sequence[_ActionCall],
	type_tokens: Sequence[str],
	functional_groups: Sequence[_FunctionalPredicateGroup],
) -> bool:
	argument_types = _argument_required_types(body_actions)
	positive_contexts = tuple(literal for literal in context_literals if literal.is_positive)
	for group in functional_groups:
		relevant = tuple(
			literal
			for literal in positive_contexts
			if literal.predicate == group.predicate
			and _literal_matches_group_key_types(
				literal=literal,
				group=group,
				argument_types=argument_types,
				type_tokens=type_tokens,
			)
		)
		for index, left in enumerate(relevant):
			for right in relevant[index + 1:]:
				if _functional_context_literals_conflict(left, right, group):
					return True
	return False


def _argument_required_types(body_actions: Sequence[_ActionCall]) -> dict[str, set[str]]:
	types_by_argument: dict[str, set[str]] = {}
	for call in body_actions:
		for parameter, argument in zip(call.action.parameters, call.arguments):
			argument_type = call.action.parameter_types.get(parameter, "object")
			if argument_type and argument_type != "object":
				types_by_argument.setdefault(argument, set()).add(argument_type)
	return types_by_argument


def _literal_matches_group_key_types(
	*,
	literal: PDDLLiteralSchema,
	group: _FunctionalPredicateGroup,
	argument_types: Mapping[str, set[str]],
	type_tokens: Sequence[str],
) -> bool:
	for group_type, position in zip(group.key_types, group.key_positions):
		argument = literal.arguments[position]
		required_types = argument_types.get(argument)
		if not required_types:
			continue
		if not any(
			_types_are_compatible(group_type, required_type, type_tokens)
			for required_type in required_types
		):
			return False
	return True


def _functional_context_literals_conflict(
	left: PDDLLiteralSchema,
	right: PDDLLiteralSchema,
	group: _FunctionalPredicateGroup,
) -> bool:
	left_key = tuple(left.arguments[position] for position in group.key_positions)
	right_key = tuple(right.arguments[position] for position in group.key_positions)
	if left_key != right_key:
		return False
	left_value = tuple(left.arguments[position] for position in group.value_positions)
	right_value = tuple(right.arguments[position] for position in group.value_positions)
	return left_value != right_value


def _has_arbitrary_extra_target_relation(
	*,
	action: _ParsedAction,
	target_effect: PDDLLiteralSchema,
	variable_map: Mapping[str, str],
	target_arguments: Sequence[str],
) -> bool:
	target_argument_set = set(target_arguments)
	preconditions = tuple(precondition.mapped(variable_map) for precondition in action.preconditions)
	for effect in action.add_effects:
		mapped = effect.mapped(variable_map)
		if _same_literal(mapped, target_effect):
			continue
		effect_arguments = set(mapped.arguments)
		if not effect_arguments & target_argument_set:
			continue
		if not effect_arguments - target_argument_set:
			continue
		if not any(_same_literal(mapped, precondition) for precondition in preconditions):
			extra_arguments = effect_arguments - target_argument_set
			if not _variables_are_bound_by_positive_precondition_chain(
				variables=extra_arguments,
				preconditions=preconditions,
				initial_bound_variables=target_argument_set,
			):
				return True
	return False


def _variables_are_bound_by_positive_precondition_chain(
	*,
	variables: set[str],
	preconditions: Sequence[PDDLLiteralSchema],
	initial_bound_variables: set[str],
) -> bool:
	"""Return whether variables are range-restricted by positive preconditions."""

	bound_variables = set(initial_bound_variables)
	remaining = [literal for literal in preconditions if literal.is_positive]
	changed = True
	while changed:
		changed = False
		for literal in tuple(remaining):
			literal_variables = set(literal.arguments)
			if not (literal_variables & bound_variables):
				continue
			bound_variables.update(literal_variables)
			remaining.remove(literal)
			changed = True
	return variables <= bound_variables


def _is_public_positive_precondition(
	*,
	literal: PDDLLiteralSchema,
	sequence: _ProducerSequence,
	module_predicates: set[str],
	recursive_module_predicates: set[str],
	actions: Sequence[_ParsedAction],
) -> bool:
	return (
		literal.is_positive
		and literal.predicate in module_predicates
		and not _same_signature(
			literal.predicate,
			literal.arguments,
			sequence.target_predicate,
			sequence.target_arguments,
		)
		and _candidate_subgoal_has_progress_potential(
			literal=literal,
			sequence=sequence,
			recursive_module_predicates=recursive_module_predicates,
		)
		and _can_use_precondition_as_subgoal(
			target_predicate=sequence.target_predicate,
			target_arguments=sequence.target_arguments,
			precondition=literal,
			actions=actions,
		)
		and _precondition_has_range_safe_prepare_context(
			sequence=sequence,
			precondition=literal,
		)
		and not _is_unbound_extra_variable_relation_binding(
			literal=literal,
			sequence=sequence,
		)
	)


def _is_unbound_extra_variable_relation_binding(
	*,
	literal: PDDLLiteralSchema,
	sequence: _ProducerSequence,
) -> bool:
	"""Return whether a relation literal should bind context, not become a goal."""

	extra_variables = set(literal.arguments) - set(sequence.target_arguments)
	return bool(extra_variables) and _prepare_precondition_binding_literals(
		sequence=sequence,
		precondition=literal,
	) is None


def _precondition_has_range_safe_prepare_context(
	*,
	sequence: _ProducerSequence,
	precondition: PDDLLiteralSchema,
) -> bool:
	return _prepare_precondition_binding_literals(
		sequence=sequence,
		precondition=precondition,
	) is not None


def _prepare_precondition_binding_literals(
	*,
	sequence: _ProducerSequence,
	precondition: PDDLLiteralSchema,
) -> tuple[PDDLLiteralSchema, ...] | None:
	"""Return positive contexts that bind a prepared precondition safely."""

	head_variables = set(sequence.target_arguments)
	extra_variables = set(precondition.arguments) - head_variables
	positive_contexts = tuple(
		literal
		for literal in sequence.context_literals
		if literal.is_positive and not _same_literal(literal, precondition)
	)
	if not extra_variables:
		return tuple(
			literal
			for literal in positive_contexts
			if _shares_extra_variable(
				literal=literal,
				precondition=precondition,
				head_arguments=sequence.target_arguments,
			)
		)

	selected: list[PDDLLiteralSchema] = []
	remaining = list(positive_contexts)
	bound_variables = set(precondition.arguments) | head_variables
	changed = True
	while changed:
		changed = False
		for literal in tuple(remaining):
			literal_variables = set(literal.arguments)
			if not (literal_variables & bound_variables):
				continue
			selected.append(literal)
			remaining.remove(literal)
			bound_variables.update(literal_variables)
			changed = True
	if not extra_variables <= {
		argument
		for literal in selected
		for argument in literal.arguments
	} | head_variables:
		return None
	return _deduplicate_literals(tuple(selected))


def _candidate_subgoal_has_progress_potential(
	*,
	literal: PDDLLiteralSchema,
	sequence: _ProducerSequence,
	recursive_module_predicates: set[str],
) -> bool:
	"""Return whether a missing precondition can safely become a subgoal branch."""

	if literal.predicate in recursive_module_predicates:
		return True
	return any(
		call.action.name not in sequence.producer_action_names
		and any(effect.predicate == literal.predicate for effect in call.action.add_effects)
		for call in sequence.body_actions
	) or literal.predicate != sequence.target_predicate


def _shares_extra_variable(
	*,
	literal: PDDLLiteralSchema,
	precondition: PDDLLiteralSchema,
	head_arguments: Sequence[str],
) -> bool:
	extra_variables = set(precondition.arguments) - set(head_arguments)
	return bool(extra_variables and extra_variables & set(literal.arguments))


def _action_call(
	action: _ParsedAction,
	variable_map: Mapping[str, str],
) -> _ActionCall:
	return _ActionCall(
		action=action,
		arguments=tuple(variable_map.get(parameter, _var(parameter)) for parameter in action.parameters),
	)


def _sequence_module_plans(
	*,
	sequence: _ProducerSequence,
	module_predicates: set[str],
	recursive_module_predicates: set[str],
	actions: Sequence[_ParsedAction],
	source_backend: str,
	source_name: str,
	policy_file: str | Path | None,
) -> tuple[AgentSpeakPlan, ...]:
	plans = [
		_final_action_sequence_plan(
			sequence=sequence,
			source_backend=source_backend,
			source_name=source_name,
			policy_file=policy_file,
		),
	]
	if not sequence.target_arguments:
		return tuple(plans)
	for literal in sequence.context_literals:
		if not _is_public_positive_precondition(
			literal=literal,
			sequence=sequence,
			module_predicates=module_predicates,
			recursive_module_predicates=recursive_module_predicates,
			actions=actions,
		):
			continue
		progress_certificate = _recursive_progress_certificate(
			sequence=sequence,
			precondition=literal,
			actions=actions,
		)
		if _requires_recursive_progress_certificate(
			sequence=sequence,
			precondition=literal,
		) and progress_certificate is None:
			continue
		plans.append(
			_prepare_precondition_plan(
				sequence=sequence,
				precondition=literal,
				progress_certificate=progress_certificate,
				source_backend=source_backend,
				source_name=source_name,
				policy_file=policy_file,
			),
		)
	return tuple(plans)


def _final_action_sequence_plan(
	*,
	sequence: _ProducerSequence,
	source_backend: str,
	source_name: str,
	policy_file: str | Path | None,
) -> AgentSpeakPlan:
	return AgentSpeakPlan(
		plan_name=(
			f"{sequence.target_predicate}_via_"
			f"{'_then_'.join(sequence.producer_action_names)}"
		),
		trigger=AgentSpeakTrigger(
			event_type="achievement_goal",
			symbol=sequence.target_predicate,
			arguments=sequence.target_arguments,
		),
		context=tuple(
			_order_contexts_for_matching(
				tuple(literal.to_context() for literal in sequence.context_literals)
				+ sequence.numeric_contexts
				+ sequence.guard_contexts,
				sequence.type_contexts,
				initial_bound_variables=sequence.target_arguments,
			),
		),
		body=tuple(
			AgentSpeakBodyStep("action", call.action.name, call.arguments)
			for call in sequence.body_actions
		),
		binding_certificate=(
			{
				"artifact_family": "atomic_minimal_literal_module",
				"rule_kind": "producer_action_sequence",
				"producer_actions": list(sequence.producer_action_names),
				"numeric_contexts": list(sequence.numeric_contexts),
				"guard_contexts": list(sequence.guard_contexts),
				"resource_release_certificates": [
					dict(certificate)
					for certificate in sequence.resource_release_certificates
				],
				"source_backend": source_backend,
				"source_name": source_name,
				"policy_file": str(policy_file) if policy_file is not None else None,
			},
		),
	)


def _prepare_precondition_plan(
	*,
	sequence: _ProducerSequence,
	precondition: PDDLLiteralSchema,
	progress_certificate: _RecursiveProgressCertificate | None,
	source_backend: str,
	source_name: str,
	policy_file: str | Path | None,
) -> AgentSpeakPlan:
	binding_literals = (
		_prepare_precondition_binding_literals(
			sequence=sequence,
			precondition=precondition,
		)
		or ()
	)
	binding_contexts = tuple(literal.to_context() for literal in binding_literals)
	body_variables = set(sequence.target_arguments) | set(precondition.arguments)
	for literal in binding_literals:
		body_variables.update(literal.arguments)
	context = tuple(
		_order_contexts_for_matching(
			binding_contexts + (f"not {precondition.to_call()}",),
			_filter_obj_tp_contexts(sequence.type_contexts, body_variables),
			initial_bound_variables=sequence.target_arguments,
		),
	)
	return AgentSpeakPlan(
		plan_name=(
			f"{sequence.target_predicate}_prepare_{precondition.predicate}_"
			f"{'_'.join(precondition.arguments)}"
		),
		trigger=AgentSpeakTrigger(
			event_type="achievement_goal",
			symbol=sequence.target_predicate,
			arguments=sequence.target_arguments,
		),
		context=context,
		body=(
			AgentSpeakBodyStep("subgoal", precondition.predicate, precondition.arguments),
			AgentSpeakBodyStep(
				"subgoal",
				sequence.target_predicate,
				sequence.target_arguments,
			),
		),
		binding_certificate=(
			{
				"artifact_family": "atomic_minimal_literal_module",
				"rule_kind": "prepare_public_precondition",
				"prepared_predicate": precondition.predicate,
				"recursive_progress_certificate": (
					progress_certificate.to_dict()
					if progress_certificate is not None
					else None
				),
				"source_backend": source_backend,
				"source_name": source_name,
				"policy_file": str(policy_file) if policy_file is not None else None,
			},
		),
	)


def _requires_recursive_progress_certificate(
	*,
	sequence: _ProducerSequence,
	precondition: PDDLLiteralSchema,
) -> bool:
	return (
		sequence.target_predicate == precondition.predicate
		and tuple(sequence.target_arguments) != tuple(precondition.arguments)
	)


def _recursive_progress_certificate(
	*,
	sequence: _ProducerSequence,
	precondition: PDDLLiteralSchema,
	actions: Sequence[_ParsedAction],
) -> _RecursiveProgressCertificate | None:
	if not _requires_recursive_progress_certificate(
		sequence=sequence,
		precondition=precondition,
	):
		return None
	head_variables = set(sequence.target_arguments)
	recursive_variables = set(precondition.arguments) - head_variables
	if not recursive_variables:
		return None
	for context_literal in sequence.context_literals:
		if not context_literal.is_positive:
			continue
		context_variables = set(context_literal.arguments)
		if not recursive_variables <= context_variables:
			continue
		if not head_variables & context_variables:
			continue
		strictly_decreasing: list[str] = []
		non_increasing: list[str] = []
		for call in sequence.body_actions:
			variable_map = {
				parameter: argument
				for parameter, argument in zip(call.action.parameters, call.arguments)
			}
			mapped_adds = tuple(
				add_effect.mapped(variable_map)
				for add_effect in call.action.add_effects
			)
			if any(add.predicate == context_literal.predicate for add in mapped_adds):
				break
			mapped_deletes = tuple(
				delete_effect.mapped(variable_map)
				for delete_effect in call.action.delete_effects
			)
			if any(_same_atom(deleted, context_literal) for deleted in mapped_deletes):
				strictly_decreasing.append(call.action.name)
			else:
				non_increasing.append(call.action.name)
		else:
			if strictly_decreasing:
				return _RecursiveProgressCertificate(
					relation_predicate=context_literal.predicate,
					relation_arguments=context_literal.arguments,
					strictly_decreasing_actions=tuple(strictly_decreasing),
					non_increasing_actions=tuple(non_increasing),
				)
	return None


def _recursive_progress_certificate_from_plan(
	plan: AgentSpeakPlan,
) -> _RecursiveProgressCertificate | None:
	for record in tuple(plan.binding_certificate or ()):
		payload = record.get("recursive_progress_certificate")
		if not isinstance(payload, Mapping):
			continue
		if payload.get("certificate_kind") != "well_founded_relational_count_decrease":
			continue
		return _RecursiveProgressCertificate(
			relation_predicate=str(payload["relation_predicate"]),
			relation_arguments=tuple(str(item) for item in payload["relation_arguments"]),
			strictly_decreasing_actions=tuple(
				str(item) for item in payload["strictly_decreasing_actions"]
			),
			non_increasing_actions=tuple(
				str(item) for item in payload["non_increasing_actions"]
			),
		)
	return None


def _select_branches_with_clingo(
	plans: Sequence[AgentSpeakPlan],
	*,
	schema_candidates: Sequence[AgentSpeakPlan] = (),
	evidence_obligations: Sequence[AgentSpeakPlan] = (),
	actions: Sequence[_ParsedAction] = (),
) -> _SelectedModulePlans:
	"""Select a minimum branch set that covers all generated branch evidence."""

	raw_plans = tuple(plans)
	if not raw_plans:
		raise ValueError("No candidate branches were generated for Clingo selection.")
	if not schema_candidates and not evidence_obligations:
		schema_candidates = raw_plans
	branch_ids = tuple(f"b{index}" for index, _ in enumerate(raw_plans))
	obligation_groups = _certified_branch_obligation_groups(
		raw_plans=raw_plans,
		schema_candidates=schema_candidates,
		evidence_obligations=evidence_obligations,
		actions=actions,
	)
	recursive_capability_groups = _recursive_capability_obligation_groups(
		raw_plans=raw_plans,
		schema_candidates=schema_candidates,
	)
	coverage_pairs = tuple(
		(selected_index, obligation_index)
		for obligation_index, candidate_indexes in enumerate(obligation_groups)
		for selected_index in candidate_indexes
	)
	if not coverage_pairs:
		raise ValueError("Clingo branch selector received no candidate coverage facts.")
	program = _clingo_selector_program(
		plans=raw_plans,
		branch_ids=branch_ids,
		obligation_ids=tuple(f"o{index}" for index in range(len(obligation_groups))),
		coverage_pairs=coverage_pairs,
		recursive_capability_groups=recursive_capability_groups,
		ranking_incompatibility_pairs=_recursive_rank_incompatibility_pairs(
			raw_plans,
			actions=actions,
		),
	)
	control = clingo.Control(["--warn=none"])
	control.add("base", [], program)
	control.ground([("base", [])])
	model_symbols: tuple[clingo.Symbol, ...] = ()
	optimization_cost: tuple[int, ...] = ()

	def _capture_model(model: clingo.Model) -> None:
		nonlocal model_symbols, optimization_cost
		model_symbols = tuple(model.symbols(shown=True))
		optimization_cost = tuple(int(item) for item in model.cost)

	result = control.solve(on_model=_capture_model)
	if not result.satisfiable:
		raise RuntimeError("Clingo branch selector could not satisfy coverage obligations.")
	selected_ids = tuple(
		str(symbol.arguments[0])
		for symbol in model_symbols
		if symbol.name == "selected" and len(symbol.arguments) == 1
	)
	if not selected_ids:
		raise RuntimeError("Clingo branch selector returned an empty selected branch set.")
	selected_index_by_id = {branch_id: index for index, branch_id in enumerate(branch_ids)}
	selected_indexes = tuple(
		sorted(selected_index_by_id[branch_id] for branch_id in selected_ids)
	)
	selected_branch_ids = tuple(branch_ids[index] for index in selected_indexes)
	selected_index_set = set(selected_indexes)
	selected_recursive_capability_count = sum(
		1
		for group in recursive_capability_groups
		if any(index in selected_index_set for index in group)
	)
	selected_plans = tuple(
		sorted(
			(raw_plans[index] for index in selected_indexes),
			key=_runtime_plan_priority,
		),
	)
	return _SelectedModulePlans(
		plans=selected_plans,
		report=_ClingoBranchSelectorReport(
			backend="clingo_asp_minimize",
			raw_candidate_count=len(raw_plans),
			selected_candidate_count=len(selected_indexes),
			obligation_count=len(obligation_groups),
			optimization_cost=optimization_cost,
			selected_branch_ids=selected_branch_ids,
			objective=(
				"maximize compatible well-founded recursive capabilities",
				"minimize selected branch count",
				"then minimize selected context literal count",
				"then minimize selected body step count",
			),
			selection_scope=(
				"joint_schema_and_validated_evidence_candidates"
				if evidence_obligations
				else "schema_candidates"
			),
			candidate_source_counts={
				"schema": len(tuple(schema_candidates or ())),
				"validated_evidence": len(tuple(evidence_obligations or ())),
				"joint_unique": len(raw_plans),
			},
			evidence_obligation_count=len(tuple(evidence_obligations or ())),
			coverage_basis=(
				"alpha-equivalent trigger, context, and body",
				"or identical primitive/subgoal body under a context subset implication",
				(
					"or a weaker-context primitive producer whose schema-derived positive "
					"postconditions refine the obligation without additional deletes and "
					"with an identical numeric transformation and independently certified "
					"resource release"
				),
				"recursive body-prefix similarity is not accepted as semantic coverage",
			),
			ranking_incompatibility_count=len(
				_recursive_rank_incompatibility_pairs(raw_plans, actions=actions),
			),
			recursive_capability_obligation_count=len(recursive_capability_groups),
			selected_recursive_capability_count=selected_recursive_capability_count,
		),
	)


def _runtime_plan_priority(plan: AgentSpeakPlan) -> tuple[str, int, int, str]:
	"""Order selected branches so executable producers run before preparation loops."""

	rule_kind = _plan_rule_kind(plan)
	priority_by_kind = {
		"already_true": 0,
		"producer_action_sequence": 1,
		"prepare_public_precondition": 2,
	}
	return (
		plan.trigger.symbol,
		priority_by_kind.get(rule_kind, 9),
		len(plan.body),
		plan.plan_name,
	)


def _plan_rule_kind(plan: AgentSpeakPlan) -> str:
	for certificate in plan.binding_certificate:
		rule_kind = str(certificate.get("rule_kind") or "").strip()
		if rule_kind:
			return rule_kind
	return ""


def _clingo_selector_program(
	*,
	plans: Sequence[AgentSpeakPlan],
	branch_ids: Sequence[str],
	obligation_ids: Sequence[str],
	coverage_pairs: Sequence[tuple[int, int]],
	recursive_capability_groups: Sequence[Sequence[int]],
	ranking_incompatibility_pairs: Sequence[tuple[int, int]],
) -> str:
	lines: list[str] = [
		"{ selected(Branch) } :- branch(Branch).",
		":- selected(Branch), not certified(Branch).",
		"provided(Predicate) :- selected(Branch), provides(Branch, Predicate).",
		":- selected(Branch), calls(Branch, Predicate), not provided(Predicate).",
		":- selected(Left), selected(Right), incompatible(Left, Right).",
		"covered(Obligation) :- selected(Branch), covers(Branch, Obligation).",
		"recursive_covered(Capability) :- selected(Branch), "
		"recursive_candidate(Capability, Branch).",
		":- obligation(Obligation), not covered(Obligation).",
		"#maximize { 1@4,Capability : recursive_covered(Capability) }.",
		"#minimize { 1@3,Branch : selected(Branch) }.",
		"#minimize { Cost@2,Branch : selected(Branch), context_cost(Branch, Cost) }.",
		"#minimize { Cost@1,Branch : selected(Branch), body_cost(Branch, Cost) }.",
		"#show selected/1.",
	]
	for index, plan in enumerate(plans):
		branch_id = branch_ids[index]
		lines.extend(
			(
				f"branch({branch_id}).",
				f"certified({branch_id}).",
				f"context_cost({branch_id}, {len(plan.context)}).",
				f"body_cost({branch_id}, {len(plan.body)}).",
			),
		)
	for obligation_id in obligation_ids:
		lines.append(f"obligation({obligation_id}).")
	for capability_index, candidate_indexes in enumerate(recursive_capability_groups):
		for candidate_index in candidate_indexes:
			lines.append(
				f"recursive_candidate(r{capability_index}, {branch_ids[candidate_index]}).",
			)
	predicate_ids = {
		predicate: f"p{index}"
		for index, predicate in enumerate(
			sorted({plan.trigger.symbol for plan in plans}),
		)
	}
	for index, plan in enumerate(plans):
		branch_id = branch_ids[index]
		lines.append(f"provides({branch_id}, {predicate_ids[plan.trigger.symbol]}).")
		for predicate in sorted(
			{
				step.symbol
				for step in plan.body
				if step.kind == "subgoal" and step.symbol in predicate_ids
			},
		):
			lines.append(f"calls({branch_id}, {predicate_ids[predicate]}).")
	for selected_index, obligation_index in coverage_pairs:
		lines.append(
			f"covers({branch_ids[selected_index]}, {obligation_ids[obligation_index]}).",
		)
	for left_index, right_index in ranking_incompatibility_pairs:
		lines.append(
			f"incompatible({branch_ids[left_index]}, {branch_ids[right_index]}).",
		)
	return "\n".join(lines)


def _certified_branch_obligation_groups(
	*,
	raw_plans: Sequence[AgentSpeakPlan],
	schema_candidates: Sequence[AgentSpeakPlan],
	evidence_obligations: Sequence[AgentSpeakPlan],
	actions: Sequence[_ParsedAction],
) -> tuple[tuple[int, ...], ...]:
	"""Build structural schema obligations plus semantic evidence obligations."""

	raw_tuple = tuple(raw_plans or ())
	actions_by_name = {action.name: action for action in tuple(actions or ())}
	groups: list[tuple[int, ...]] = []
	for obligation in tuple(schema_candidates or ()):
		if _recursive_progress_certificate_from_plan(obligation) is not None:
			continue
		candidate_indexes = tuple(
			index
			for index, candidate in enumerate(raw_tuple)
			if _candidate_branch_covers_evidence(candidate, obligation)
			or _candidate_achieves_schema_obligation(
				candidate,
				obligation,
				actions_by_name=actions_by_name,
			)
			or _certified_resource_release_alternative(candidate, obligation)
		)
		if candidate_indexes:
			groups.append(candidate_indexes)
	for evidence in tuple(evidence_obligations or ()):
		candidate_indexes = tuple(
			index
			for index, candidate in enumerate(raw_tuple)
			if _candidate_branch_covers_evidence(candidate, evidence)
		)
		if not candidate_indexes:
			raise ValueError(
				"A validated evidence obligation has no schema-certified candidate coverage.",
			)
		groups.append(candidate_indexes)
	return tuple(dict.fromkeys(groups))


def _recursive_capability_obligation_groups(
	*,
	raw_plans: Sequence[AgentSpeakPlan],
	schema_candidates: Sequence[AgentSpeakPlan],
) -> tuple[tuple[int, ...], ...]:
	raw_tuple = tuple(raw_plans or ())
	groups = []
	for obligation in tuple(schema_candidates or ()):
		if _recursive_progress_certificate_from_plan(obligation) is None:
			continue
		candidate_indexes = tuple(
			index
			for index, candidate in enumerate(raw_tuple)
			if _candidate_branch_covers_evidence(candidate, obligation)
		)
		if candidate_indexes:
			groups.append(candidate_indexes)
	return tuple(dict.fromkeys(groups))


def _candidate_achieves_schema_obligation(
	candidate: AgentSpeakPlan,
	obligation: AgentSpeakPlan,
	*,
	actions_by_name: Mapping[str, _ParsedAction],
) -> bool:
	"""Check positive-achievement refinement under complete PDDL effect contracts."""

	if _plan_rule_kind(candidate) != "producer_action_sequence":
		return False
	if _plan_rule_kind(obligation) != "producer_action_sequence":
		return False
	if candidate.trigger.symbol != obligation.trigger.symbol:
		return False
	if candidate.trigger.arguments != obligation.trigger.arguments:
		return False
	if not set(candidate.context) <= set(obligation.context):
		return False
	candidate_contract = _branch_effect_contract(
		candidate,
		actions_by_name=actions_by_name,
	)
	obligation_contract = _branch_effect_contract(
		obligation,
		actions_by_name=actions_by_name,
	)
	if not candidate_contract.complete or not obligation_contract.complete:
		return False
	return (
		obligation_contract.must_add <= candidate_contract.must_add
		and candidate_contract.may_delete <= obligation_contract.may_delete
		and candidate_contract.numeric_delta == obligation_contract.numeric_delta
	)


def _branch_effect_contract(
	plan: AgentSpeakPlan,
	*,
	actions_by_name: Mapping[str, _ParsedAction],
) -> _BranchEffectContract:
	"""Compose net Boolean and numeric effects for an action-only plan body."""

	must_add: set[tuple[str, tuple[str, ...]]] = set()
	may_delete: set[tuple[str, tuple[str, ...]]] = set()
	numeric_delta: dict[tuple[str, tuple[str, ...]], int] = {}
	for step in tuple(plan.body or ()):
		if step.kind != "action":
			return _BranchEffectContract(
				frozenset(),
				frozenset(),
				(),
				(),
				False,
			)
		action = actions_by_name.get(step.symbol)
		if action is None or len(action.parameters) != len(step.arguments):
			return _BranchEffectContract(
				frozenset(),
				frozenset(),
				(),
				(),
				False,
			)
		binding = {
			parameter: argument
			for parameter, argument in zip(action.parameters, step.arguments)
		}
		for effect in action.delete_effects:
			atom = (
				effect.predicate,
				tuple(binding.get(argument, argument) for argument in effect.arguments),
			)
			must_add.discard(atom)
			may_delete.add(atom)
		for effect in action.add_effects:
			atom = (
				effect.predicate,
				tuple(binding.get(argument, argument) for argument in effect.arguments),
			)
			may_delete.discard(atom)
			must_add.add(atom)
		for effect in action.numeric_effects:
			if effect.operator not in {"increase", "decrease"}:
				return _BranchEffectContract(frozenset(), frozenset(), (), (), False)
			if effect.amount.kind != "constant" or not re.fullmatch(
				r"[+-]?\d+",
				str(effect.amount.value),
			):
				return _BranchEffectContract(frozenset(), frozenset(), (), (), False)
			fluent = (
				str(effect.fluent.function).strip().lower(),
				tuple(
					binding.get(argument, argument)
					for argument in tuple(effect.fluent.args or ())
				),
			)
			amount = int(str(effect.amount.value))
			if effect.operator == "decrease":
				amount = -amount
			numeric_delta[fluent] = numeric_delta.get(fluent, 0) + amount
	target_atom = (
		plan.trigger.symbol,
		tuple(plan.trigger.arguments),
	)
	resource_release = _resource_release_contract(plan)
	resource_certificates = tuple(
		_first_binding_certificate(plan).get("resource_release_certificates") or ()
	)
	if resource_certificates and not resource_release:
		return _BranchEffectContract(frozenset(), frozenset(), (), (), False)
	return _BranchEffectContract(
		must_add=frozenset((target_atom,)) if target_atom in must_add else frozenset(),
		may_delete=frozenset(may_delete),
		numeric_delta=tuple(
			sorted(
				(function, arguments, delta)
				for (function, arguments), delta in numeric_delta.items()
				if delta != 0
			),
		),
		resource_release=resource_release,
		complete=True,
	)


def _first_binding_certificate(plan: AgentSpeakPlan) -> Mapping[str, object]:
	return next(
		(record for record in tuple(plan.binding_certificate or ()) if isinstance(record, Mapping)),
		{},
	)


def _certified_resource_release_alternative(
	candidate: AgentSpeakPlan,
	obligation: AgentSpeakPlan,
) -> bool:
	if candidate.trigger.symbol != obligation.trigger.symbol:
		return False
	if len(candidate.trigger.arguments) != len(obligation.trigger.arguments):
		return False
	if not set(candidate.context) <= set(obligation.context):
		return False
	return _resource_release_contract(candidate) == _resource_release_contract(obligation) != ()


def _resource_release_contract(plan: AgentSpeakPlan) -> tuple[object, ...]:
	certificate = _first_binding_certificate(plan)
	resource_certificates = tuple(certificate.get("resource_release_certificates") or ())
	if not resource_certificates:
		return ()
	canonical_argument = _canonical_plan_argument_replacer(plan)

	def canonical_text(value: object) -> str:
		return _replace_context_variables(str(value or ""), canonical_argument)

	contracts = []
	for resource in resource_certificates:
		if resource.get("certificate_kind") != (
			"causal_resource_capacity_invariant_discharge"
		):
			return ()
		contracts.append(
			(
				str(resource.get("certificate_kind") or ""),
				str(resource.get("producer_action") or ""),
				str(resource.get("release_action") or ""),
				canonical_text(resource.get("resource_debt_literal")),
				tuple(
					sorted(
						canonical_text(item)
						for item in tuple(resource.get("restored_literals") or ())
					),
				),
				str(resource.get("resource_invariant_kind") or ""),
				tuple(
					canonical_argument(str(item))
					for item in tuple(resource.get("capacity_key_arguments") or ())
				),
				tuple(
					canonical_argument(str(item))
					for item in tuple(resource.get("occupancy_arguments") or ())
				),
				bool(resource.get("target_preserved")),
				tuple(
					sorted(
						canonical_text(item)
						for item in tuple(resource.get("target_preservation_guards") or ())
					),
				),
				tuple(
					sorted(
						canonical_text(item)
						for item in tuple(resource.get("sequence_alias_guards") or ())
					),
				),
			)
		)
	return tuple(contracts)


def _canonical_plan_argument_replacer(plan: AgentSpeakPlan) -> Callable[[str], str]:
	"""Return one alpha-renaming shared by a plan body and its certificates."""

	variable_map = {
		argument: f"H{index}"
		for index, argument in enumerate(tuple(plan.trigger.arguments or ()))
		if _is_agentspeak_variable(argument)
	}
	next_local_index = 0

	def replace(argument: str) -> str:
		nonlocal next_local_index
		if not _is_agentspeak_variable(argument):
			return argument
		if argument not in variable_map:
			variable_map[argument] = f"V{next_local_index}"
			next_local_index += 1
		return variable_map[argument]

	for context in sorted(tuple(plan.context or ())):
		_replace_context_variables(context, replace)
	for step in tuple(plan.body or ()):
		for argument in tuple(step.arguments or ()):
			replace(argument)
	return replace


def _call_predicate(call: str) -> str:
	return str(call or "").partition("(")[0].strip()


def _recursive_rank_incompatibility_pairs(
	plans: Sequence[AgentSpeakPlan],
	*,
	actions: Sequence[_ParsedAction],
) -> tuple[tuple[int, int], ...]:
	plan_tuple = tuple(plans or ())
	actions_by_name = {action.name: action for action in actions}
	call_graph: dict[str, set[str]] = {}
	for plan in plan_tuple:
		call_graph.setdefault(plan.trigger.symbol, set()).update(
			step.symbol for step in plan.body if step.kind == "subgoal"
		)
	pairs: set[tuple[int, int]] = set()
	for recursive_index, recursive_plan in enumerate(plan_tuple):
		certificate = _recursive_progress_certificate_from_plan(recursive_plan)
		if certificate is None:
			continue
		reachable_modules = _reachable_module_predicates(
			{step.symbol for step in recursive_plan.body if step.kind == "subgoal"},
			call_graph=call_graph,
		)
		for candidate_index, candidate in enumerate(plan_tuple):
			if candidate.trigger.symbol not in reachable_modules:
				continue
			if _plan_directly_adds_predicate(
				candidate,
				predicate=certificate.relation_predicate,
				actions_by_name=actions_by_name,
			):
				pairs.add((recursive_index, candidate_index))
	return tuple(sorted(pairs))


def _reachable_module_predicates(
	initial: set[str],
	*,
	call_graph: Mapping[str, set[str]],
) -> set[str]:
	reachable = set(initial)
	frontier = list(initial)
	while frontier:
		predicate = frontier.pop()
		for called in call_graph.get(predicate, set()):
			if called in reachable:
				continue
			reachable.add(called)
			frontier.append(called)
	return reachable


def _plan_directly_adds_predicate(
	plan: AgentSpeakPlan,
	*,
	predicate: str,
	actions_by_name: Mapping[str, _ParsedAction],
) -> bool:
	for step in plan.body:
		if step.kind != "action":
			continue
		action = actions_by_name.get(step.symbol)
		if action is None:
			return True
		if any(effect.predicate == predicate for effect in action.add_effects):
			return True
	return False


def _candidate_branch_covers_evidence(
	candidate: AgentSpeakPlan,
	evidence: AgentSpeakPlan,
) -> bool:
	if candidate.trigger.symbol != evidence.trigger.symbol:
		return False
	if len(candidate.trigger.arguments) != len(evidence.trigger.arguments):
		return False
	if _canonical_branch_signature(candidate) == _canonical_branch_signature(evidence):
		return True
	if not set(candidate.context) <= set(evidence.context):
		return False
	if _same_body(candidate.body, evidence.body):
		return True
	return False


def _canonical_branch_signature(
	plan: AgentSpeakPlan,
) -> tuple[str, int, tuple[str, ...], tuple[tuple[str, str, tuple[str, ...]], ...]]:
	"""Canonicalize local variable names while preserving trigger argument positions."""

	variable_map = {
		argument: f"H{index}"
		for index, argument in enumerate(tuple(plan.trigger.arguments or ()))
	}
	next_local_index = 0

	def canonical_argument(argument: str) -> str:
		nonlocal next_local_index
		if not _is_agentspeak_variable(argument):
			return argument
		if argument not in variable_map:
			variable_map[argument] = f"V{next_local_index}"
			next_local_index += 1
		return variable_map[argument]

	def canonical_context(context: str) -> str:
		return _replace_context_variables(context, canonical_argument)

	return (
		plan.trigger.symbol,
		len(tuple(plan.trigger.arguments or ())),
		tuple(sorted(canonical_context(context) for context in tuple(plan.context or ()))),
		tuple(
			(
				step.kind,
				step.symbol,
				tuple(canonical_argument(argument) for argument in tuple(step.arguments or ())),
			)
			for step in tuple(plan.body or ())
		),
	)


def _replace_context_variables(
	context: str,
	replace_argument: Callable[[str], str],
) -> str:
	tokens = re.split(r"(\b[A-Z][A-Za-z0-9_]*\b)", str(context or ""))
	return "".join(
		replace_argument(token) if _is_agentspeak_variable(token) else token
		for token in tokens
	)


def _same_body(
	left: Sequence[AgentSpeakBodyStep],
	right: Sequence[AgentSpeakBodyStep],
) -> bool:
	return tuple(_body_step_key(step) for step in left) == tuple(
		_body_step_key(step) for step in right
	)


def _body_step_key(step: AgentSpeakBodyStep) -> tuple[str, str, tuple[str, ...]]:
	return (step.kind, step.symbol, tuple(step.arguments))


def _producer_effects(
	actions: Sequence[_ParsedAction],
	predicate: str,
) -> tuple[tuple[_ParsedAction, PDDLLiteralSchema], ...]:
	return tuple(
		(action, effect)
		for action in actions
		for effect in action.add_effects
		if effect.predicate == predicate
	)


def _can_use_precondition_as_subgoal(
	*,
	target_predicate: str,
	target_arguments: Sequence[str],
	precondition: PDDLLiteralSchema,
	actions: Sequence[_ParsedAction],
) -> bool:
	if not precondition.is_positive:
		return False
	if _same_signature(precondition.predicate, precondition.arguments, target_predicate, target_arguments):
		return False
	if not actions:
		return True
	producers = _producer_effects(actions, precondition.predicate)
	if not producers:
		return False
	circular_producers = 0
	for producer, effect in producers:
		effect_map = {
			raw_argument: mapped_argument
			for raw_argument, mapped_argument in zip(effect.arguments, precondition.arguments)
		}
		for producer_precondition in producer.preconditions:
			mapped_arguments = tuple(
				effect_map.get(argument, _var(argument))
				for argument in producer_precondition.arguments
			)
			if _same_signature(
				producer_precondition.predicate,
				mapped_arguments,
				target_predicate,
				target_arguments,
			):
				circular_producers += 1
				break
	return circular_producers < len(producers)


def _module_synthesis_report(
	*,
	plans: Sequence[AgentSpeakPlan],
	raw_plan_count: int,
	selection_report: _ClingoBranchSelectorReport,
	seeds: Sequence[str],
	module_predicates: Sequence[str],
	actions: Sequence[_ParsedAction],
	rejected_uncertified_candidate_count: int,
) -> AtomicModuleSynthesisReport:
	branch_counts: dict[str, int] = {}
	recursive_predicates: set[str] = set()
	for plan in plans:
		branch_counts[plan.trigger.symbol] = branch_counts.get(plan.trigger.symbol, 0) + 1
		if any(step.kind == "subgoal" and step.symbol == plan.trigger.symbol for step in plan.body):
			recursive_predicates.add(plan.trigger.symbol)
	producers = {
		predicate: tuple(action.name for action, _ in _producer_effects(actions, predicate))
		for predicate in module_predicates
	}
	return AtomicModuleSynthesisReport(
		seed_predicates=tuple(seeds),
		module_predicates=tuple(module_predicates),
		plan_count=len(tuple(plans)),
		raw_candidate_count=raw_plan_count,
		branch_count_by_predicate=branch_counts,
		producer_actions_by_predicate=producers,
		recursive_predicates=tuple(sorted(recursive_predicates)),
		pruned_candidate_count=max(0, raw_plan_count - len(tuple(plans))),
		selector_backend=selection_report.backend,
		selector_objective=selection_report.objective,
		selector_optimization_cost=selection_report.optimization_cost,
		selector_obligation_count=selection_report.obligation_count,
		selected_branch_ids=selection_report.selected_branch_ids,
		selection_scope=selection_report.selection_scope,
		candidate_source_counts=selection_report.candidate_source_counts,
		evidence_obligation_count=selection_report.evidence_obligation_count,
		selector_coverage_basis=selection_report.coverage_basis,
		rejected_uncertified_candidate_count=rejected_uncertified_candidate_count,
		ranking_incompatibility_count=selection_report.ranking_incompatibility_count,
		recursive_capability_obligation_count=(
			selection_report.recursive_capability_obligation_count
		),
		selected_recursive_capability_count=(
			selection_report.selected_recursive_capability_count
		),
		predicate_roles=_predicate_role_report(
			plans=plans,
			module_predicates=module_predicates,
			actions=actions,
		),
		branch_certification_rules=(
			"static context literals must be range-restricted by head variables or "
			"previous positive dynamic literals",
			"negative context literals must be range-restricted and cannot bind new variables",
			(
				"extra-variable prepared preconditions require a positive context "
				"closure that binds every non-head variable before the negative guard"
			),
			"same-predicate recursive prepare branches require a non-negative "
			"relational-count ranking feature that strictly decreases and is never increased",
			(
				"resource-release cleanup branches require a schema certificate "
				"that deletes a producer-created resource debt, restores a literal "
				"deleted by the producer, preserves the protected target, and records "
				"all exact alias guards needed by later action preconditions"
			),
		),
		theoretical_basis=(
			"MOOSE singleton-goal regression supplies lifted target-predicate evidence",
			"PDDL action schemas supply primitive producer/precondition structure",
			"policy-reuse style predicate modules allow subgoal calls between atomic literals",
			"PDDL typing is used internally to reject unobservable subtype role bindings",
			"range-restricted static and negative contexts prevent unbounded "
			"Jason unification over inertial relations",
			"range-safe extra-variable preconditions may be lifted into internal "
			"atomic subgoal calls instead of staying as long primitive macros",
			"same-predicate recursive branches require a schema-level well-founded "
			"relational-count progress certificate",
			"resource-release cleanup branches are accepted only when PDDL effects "
			"prove resource debt discharge plus target preservation",
			"Clingo/ASP selects a minimum branch set that covers all generated branch evidence",
		),
	)


def _predicate_role_report(
	*,
	plans: Sequence[AgentSpeakPlan],
	module_predicates: Sequence[str],
	actions: Sequence[_ParsedAction],
) -> tuple[Mapping[str, object], ...]:
	module_set = set(module_predicates)
	emitted = {plan.trigger.symbol for plan in plans}
	declared = tuple(
		dict.fromkeys(
			literal.predicate
			for action in actions
			for literal in (*action.preconditions, *action.add_effects, *action.delete_effects)
		),
	)
	report: list[Mapping[str, object]] = []
	for predicate in sorted(declared):
		producers = tuple(
			action.name
			for action, _ in _producer_effects(actions, predicate)
		)
		deleters = tuple(
			action.name
			for action in actions
			if any(effect.predicate == predicate for effect in action.delete_effects)
		)
		consumers = tuple(
			action.name
			for action in actions
			if any(precondition.predicate == predicate for precondition in action.preconditions)
		)
		if producers:
			role = "producible_fluent"
			expected_module = True
		elif deleters:
			role = "deleted_only_fluent"
			expected_module = False
		else:
			role = "static_context"
			expected_module = False
		report.append(
			{
				"predicate": predicate,
				"role": role,
				"producers": list(dict.fromkeys(producers)),
				"deleters": list(dict.fromkeys(deleters)),
				"consumers": list(dict.fromkeys(consumers)),
				"selected_for_module_generation": predicate in module_set,
				"emitted_module": predicate in emitted,
				"expected_module": expected_module,
				"coverage_status": (
					"ok"
					if (predicate in emitted) == expected_module
					else "gap"
				),
			},
		)
	return tuple(report)


def _head_variable_map(effect: PDDLLiteralSchema) -> tuple[tuple[str, ...], dict[str, str]]:
	head_arguments = tuple(_head_variable(index) for index, _ in enumerate(effect.arguments))
	variable_map = {
		raw_argument: head_argument
		for raw_argument, head_argument in zip(effect.arguments, head_arguments)
	}
	next_index = len(head_arguments)
	for argument in effect.arguments:
		if argument not in variable_map:
			variable_map[argument] = _head_variable(next_index)
			next_index += 1
	return head_arguments, variable_map


def _complete_variable_map(
	parameters: Sequence[str],
	variable_map: Mapping[str, str],
	*,
	avoid_variables: set[str] | None = None,
) -> dict[str, str]:
	completed = dict(variable_map)
	used_variables = set(completed.values()) | set(avoid_variables or set())
	next_index = 0
	for parameter in parameters:
		name = _parameter_name(parameter)
		if name in completed:
			continue
		while _head_variable(next_index) in used_variables:
			next_index += 1
		completed[name] = _head_variable(next_index)
		used_variables.add(completed[name])
	return completed


def _parse_pddl_literals(expression: str) -> tuple[PDDLLiteralSchema, ...]:
	parsed = _parse_sexpr(expression)
	if parsed is None:
		return ()
	return tuple(_literal_schemas_from_sexpr(parsed))


def _literal_schemas_from_sexpr(expression: object) -> tuple[PDDLLiteralSchema, ...]:
	if not isinstance(expression, list) or not expression:
		return ()
	operator = str(expression[0]).lower()
	if operator == "and":
		return tuple(
			literal
			for child in expression[1:]
			for literal in _literal_schemas_from_sexpr(child)
		)
	if operator == "not" and len(expression) == 2:
		return tuple(
			PDDLLiteralSchema(
				predicate=literal.predicate,
				arguments=literal.arguments,
				is_positive=False,
			)
			for literal in _literal_schemas_from_sexpr(expression[1])
		)
	if _is_numeric_pddl_expression(expression):
		return ()
	if operator in {"or", "forall", "exists", "when", "imply"}:
		return ()
	return (
		PDDLLiteralSchema(
			predicate=operator,
			arguments=tuple(_parameter_name(str(argument)) for argument in expression[1:]),
			is_positive=True,
		),
	)


def _is_numeric_pddl_expression(expression: Sequence[object]) -> bool:
	if not expression:
		return False
	operator = str(expression[0]).lower()
	if operator in {
		">",
		">=",
		"<",
		"<=",
		"increase",
		"decrease",
		"assign",
		"scale-up",
		"scale-down",
	}:
		return True
	if operator != "=" or len(expression) != 3:
		return False
	return any(
		isinstance(argument, list) or _is_numeric_constant_token(argument)
		for argument in expression[1:]
	)


def _is_numeric_constant_token(value: object) -> bool:
	return re.fullmatch(r"[+-]?\d+(?:\.\d+)?", str(value or "").strip()) is not None


def _parse_sexpr(expression: str) -> object | None:
	tokens = _sexpr_tokens(expression)
	if not tokens:
		return None
	parsed, next_index = _parse_sexpr_tokens(tokens, 0)
	if next_index != len(tokens):
		raise ValueError(f"Invalid PDDL expression with trailing tokens: {expression!r}")
	return parsed


def _parse_sexpr_tokens(tokens: Sequence[str], index: int) -> tuple[object, int]:
	if index >= len(tokens):
		raise ValueError("Unexpected end of PDDL expression.")
	token = tokens[index]
	if token != "(":
		return token.lower(), index + 1
	items: list[object] = []
	index += 1
	while index < len(tokens) and tokens[index] != ")":
		item, index = _parse_sexpr_tokens(tokens, index)
		items.append(item)
	if index >= len(tokens):
		raise ValueError("Unmatched parenthesis in PDDL expression.")
	return items, index + 1


def _sexpr_tokens(expression: str) -> tuple[str, ...]:
	return tuple(
		token
		for token in (
			str(expression or "")
			.replace("(", " ( ")
			.replace(")", " ) ")
			.split()
		)
		if token
	)


def _parameter_name(parameter: str) -> str:
	text = str(parameter or "").strip().lower()
	if " - " in text:
		text = text.split(" - ", 1)[0].strip()
	return text


def _parameter_type(parameter: str) -> str:
	text = str(parameter or "").strip().lower()
	if " - " not in text:
		return "object"
	return text.split(" - ", 1)[1].strip() or "object"


def _var(parameter: str) -> str:
	text = _parameter_name(parameter).lstrip("?")
	if not text:
		return "X"
	return text[:1].upper() + text[1:]


def _head_variable(index: int) -> str:
	names = ("X", "Y", "Z", "A", "B", "C", "D")
	if index < len(names):
		return names[index]
	return f"V{index}"


def _call(predicate: str, arguments: Sequence[str]) -> str:
	args = tuple(arguments or ())
	return predicate if not args else f"{predicate}({', '.join(args)})"


def _same_literal(left: PDDLLiteralSchema, right: PDDLLiteralSchema) -> bool:
	return left.is_positive == right.is_positive and _same_atom(left, right)


def _same_atom(left: PDDLLiteralSchema, right: PDDLLiteralSchema) -> bool:
	return _same_signature(left.predicate, left.arguments, right.predicate, right.arguments)


def _same_signature(
	left_predicate: str,
	left_arguments: Sequence[str],
	right_predicate: str,
	right_arguments: Sequence[str],
) -> bool:
	return left_predicate == right_predicate and tuple(left_arguments) == tuple(right_arguments)


def _deduplicate(items: Sequence[str]) -> tuple[str, ...]:
	return tuple(dict.fromkeys(item for item in items if item))


def _order_contexts_for_matching(
	relational_contexts: Sequence[str],
	type_contexts: Sequence[str],
	initial_bound_variables: Sequence[str] = (),
) -> tuple[str, ...]:
	"""Order conjunctive contexts so Jason can use bound-argument indexes early."""

	remaining = list(_deduplicate(tuple(relational_contexts or ()) + tuple(type_contexts or ())))
	ordered: list[str] = []
	bound_variables = {
		variable
		for variable in tuple(initial_bound_variables or ())
		if _is_agentspeak_variable(variable)
	}
	while remaining:
		best_index = min(
			range(len(remaining)),
			key=lambda index: _context_matching_key(remaining[index], bound_variables),
		)
		context = remaining.pop(best_index)
		ordered.append(context)
		parsed = _parse_context_literal_for_matching(context)
		if parsed is None or parsed["negative"] or parsed["kind"] != "atom":
			continue
		bound_variables.update(
			argument
			for argument in parsed["arguments"]
			if _is_agentspeak_variable(argument)
		)
	return tuple(ordered)


def _context_matching_key(
	context: str,
	bound_variables: set[str],
) -> tuple[int, int, int, int, str]:
	parsed = _parse_context_literal_for_matching(context)
	if parsed is None:
		return (9, 0, 0, 0, context)
	arguments = tuple(parsed["arguments"])
	variables = tuple(argument for argument in arguments if _is_agentspeak_variable(argument))
	unbound_variables = tuple(variable for variable in variables if variable not in bound_variables)
	bound_count = len(variables) - len(unbound_variables)
	all_variables_bound = not unbound_variables
	is_obj_tp = parsed["predicate"] == OBJ_TP_PREDICATE
	is_comparison = parsed["kind"] == "comparison"
	is_negative = bool(parsed["negative"])
	if is_obj_tp and all_variables_bound and not is_negative:
		group = 0
	elif is_comparison and all_variables_bound:
		group = 1
	elif all_variables_bound and not is_negative:
		group = 2
	elif all_variables_bound:
		group = 3
	elif not is_comparison and not is_obj_tp and not is_negative and bound_count:
		group = 4
	elif is_obj_tp and not is_negative and bound_count:
		group = 5
	elif not is_comparison and not is_obj_tp and not is_negative:
		group = 6
	elif is_obj_tp and not is_negative:
		group = 7
	else:
		group = 8
	return (group, len(unbound_variables), -bound_count, len(arguments), context)


def _parse_context_literal_for_matching(context: str) -> dict[str, object] | None:
	text = str(context or "").strip()
	negative = False
	if text.startswith("not "):
		negative = True
		text = text[4:].strip()
	if not text:
		return None
	comparison = _parse_context_comparison_for_matching(text)
	if comparison is not None:
		left, right = comparison
		return {
			"kind": "comparison",
			"negative": negative,
			"predicate": "",
			"arguments": (left, right),
		}
	if "(" not in text:
		if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", text):
			return None
		return {"kind": "atom", "negative": negative, "predicate": text, "arguments": ()}
	match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*)\((.*)\)", text)
	if match is None:
		return None
	arguments_text = match.group(2).strip()
	arguments = tuple(
		argument.strip()
		for argument in arguments_text.split(",")
		if argument.strip()
	)
	return {
		"kind": "atom",
		"negative": negative,
		"predicate": match.group(1),
		"arguments": arguments,
	}


def _parse_context_comparison_for_matching(text: str) -> tuple[str, str] | None:
	match = re.fullmatch(
		r"\s*(?P<left>[A-Za-z_][A-Za-z0-9_-]*|[+-]?\d+(?:\.\d+)?)\s*"
		r"(?P<operator>\\==|!=|==|>=|<=|>|<)\s*"
		r"(?P<right>[A-Za-z_][A-Za-z0-9_-]*|[+-]?\d+(?:\.\d+)?)\s*",
		text,
	)
	if match is None:
		return None
	return match.group("left"), match.group("right")


def _is_agentspeak_variable(token: str) -> bool:
	return bool(re.fullmatch(r"[A-Z][A-Za-z0-9_]*", str(token or "").strip()))


def _deduplicate_literals(
	items: Sequence[PDDLLiteralSchema],
) -> tuple[PDDLLiteralSchema, ...]:
	seen: set[tuple[object, ...]] = set()
	unique: list[PDDLLiteralSchema] = []
	for literal in items:
		key = (literal.predicate, literal.arguments, literal.is_positive)
		if key in seen:
			continue
		seen.add(key)
		unique.append(literal)
	return tuple(unique)


def _deduplicate_sequences(
	sequences: Sequence[_ProducerSequence],
) -> tuple[_ProducerSequence, ...]:
	seen: set[tuple[object, ...]] = set()
	unique: list[_ProducerSequence] = []
	for sequence in sequences:
		key = (
			sequence.target_predicate,
			sequence.target_arguments,
			tuple(
				(literal.predicate, literal.arguments, literal.is_positive)
				for literal in sequence.context_literals
			),
			sequence.numeric_contexts,
			sequence.guard_contexts,
			tuple((call.action.name, call.arguments) for call in sequence.body_actions),
		)
		if key in seen:
			continue
		seen.add(key)
		unique.append(sequence)
	return tuple(unique)


def _deduplicate_plans(plans: Sequence[AgentSpeakPlan]) -> tuple[AgentSpeakPlan, ...]:
	seen: set[tuple[object, ...]] = set()
	unique: list[AgentSpeakPlan] = []
	for plan in plans:
		key = (
			plan.trigger.symbol,
			plan.trigger.arguments,
			plan.context,
			tuple((step.kind, step.symbol, step.arguments) for step in plan.body),
		)
		if key in seen:
			continue
		seen.add(key)
		unique.append(plan)
	return tuple(unique)


def _ensure_unique_plan_names(plans: Sequence[AgentSpeakPlan]) -> tuple[AgentSpeakPlan, ...]:
	"""Keep ASL plan labels unique without changing selected branch semantics."""

	name_counts: dict[str, int] = {}
	renamed: list[AgentSpeakPlan] = []
	for plan in tuple(plans or ()):
		base_name = plan.plan_name
		seen_count = name_counts.get(base_name, 0)
		name_counts[base_name] = seen_count + 1
		if seen_count == 0:
			renamed.append(plan)
			continue
		renamed.append(
			AgentSpeakPlan(
				plan_name=f"{base_name}_{seen_count + 1}",
				trigger=plan.trigger,
				context=plan.context,
				body=plan.body,
				source_instruction_ids=plan.source_instruction_ids,
				binding_certificate=plan.binding_certificate,
			),
		)
	return tuple(renamed)
