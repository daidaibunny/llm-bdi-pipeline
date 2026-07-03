"""
Synthesize compact recursive atomic literal modules from PDDL schemas.

The synthesizer uses external generalized-planning artifacts as evidence for
which atomic predicates matter, then compresses flat primitive macro evidence
into reusable predicate modules using PDDL action precondition/effect structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary
from utils.pddl_parser import PDDLAction
from utils.pddl_parser import PDDLDomain
from utils.pddl_parser import PDDLParser


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
	branch_count_by_predicate: Mapping[str, int]
	producer_actions_by_predicate: Mapping[str, tuple[str, ...]]
	recursive_predicates: tuple[str, ...]
	pruned_candidate_count: int
	theoretical_basis: tuple[str, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"seed_predicates": list(self.seed_predicates),
			"module_predicates": list(self.module_predicates),
			"plan_count": self.plan_count,
			"branch_count_by_predicate": dict(self.branch_count_by_predicate),
			"producer_actions_by_predicate": {
				predicate: list(actions)
				for predicate, actions in self.producer_actions_by_predicate.items()
			},
			"recursive_predicates": list(self.recursive_predicates),
			"pruned_candidate_count": self.pruned_candidate_count,
			"theoretical_basis": list(self.theoretical_basis),
		}


def synthesize_atomic_minimal_literal_module_library(
	*,
	domain_file: str | Path,
	seed_predicates: Sequence[str],
	source_backend: str,
	source_name: str,
	policy_file: str | Path | None = None,
) -> PlanLibrary:
	"""Build compact recursive atomic modules for seed PDDL predicates."""

	domain = PDDLParser.parse_domain(domain_file)
	declared_predicates = {predicate.name for predicate in domain.predicates}
	seeds = tuple(
		dict.fromkeys(
			predicate
			for predicate in (str(item).strip() for item in seed_predicates)
			if predicate and predicate in declared_predicates
		),
	)
	if not seeds:
		raise ValueError("No declared seed predicates were provided for atomic module synthesis.")
	parsed_actions = tuple(_ParsedAction.from_pddl(action) for action in domain.actions)
	module_predicates = _module_predicate_closure(
		seeds=seeds,
		actions=parsed_actions,
		declared_predicates=declared_predicates,
	)
	raw_plans = _candidate_module_plans(
		domain=domain,
		actions=parsed_actions,
		module_predicates=module_predicates,
		source_backend=source_backend,
		source_name=source_name,
		policy_file=policy_file,
	)
	plans = _prune_subsumed_sibling_branches(raw_plans)
	report = _module_synthesis_report(
		plans=plans,
		raw_plan_count=len(raw_plans),
		seeds=seeds,
		module_predicates=module_predicates,
		actions=parsed_actions,
	)
	return PlanLibrary(
		domain_name=domain.name,
		plans=plans,
		initial_beliefs=(),
		metadata={
			"generation_mode": "atomic_minimal_literal_module_library",
			"atomic_template_backend": source_backend,
			"source_name": source_name,
			"policy_file": str(policy_file) if policy_file is not None else None,
			"library_quality": {
				"artifact_classification": "compact_recursive_atomic_module_library",
				"compact_recursive_module_ready": True,
				"plan_count": len(plans),
				"subgoal_step_count": sum(
					1
					for plan in plans
					for step in plan.body
					if step.kind == "subgoal"
				),
			},
			"atomic_module_synthesis": report.to_dict(),
		},
	)


@dataclass(frozen=True)
class _ParsedAction:
	name: str
	parameters: tuple[str, ...]
	preconditions: tuple[PDDLLiteralSchema, ...]
	add_effects: tuple[PDDLLiteralSchema, ...]
	delete_effects: tuple[PDDLLiteralSchema, ...]

	@classmethod
	def from_pddl(cls, action: PDDLAction) -> "_ParsedAction":
		effects = _parse_pddl_literals(action.effects)
		return cls(
			name=action.name,
			parameters=tuple(_parameter_name(parameter) for parameter in action.parameters),
			preconditions=tuple(_parse_pddl_literals(action.preconditions)),
			add_effects=tuple(literal for literal in effects if literal.is_positive),
			delete_effects=tuple(literal for literal in effects if not literal.is_positive),
		)


def _module_predicate_closure(
	*,
	seeds: Sequence[str],
	actions: Sequence[_ParsedAction],
	declared_predicates: set[str],
) -> tuple[str, ...]:
	module_predicates = set(seeds)
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
			target_predicate=predicate.name,
			module_predicates=module_set,
		):
			plans.extend(
				_sequence_module_plans(
					sequence=sequence,
					module_predicates=module_set,
					recursive_module_predicates=recursive_module_predicates,
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
	body_actions: tuple[_ActionCall, ...]
	producer_action_names: tuple[str, ...]


def _producer_action_sequences(
	*,
	actions: Sequence[_ParsedAction],
	target_predicate: str,
	module_predicates: set[str],
) -> tuple[_ProducerSequence, ...]:
	sequences: list[_ProducerSequence] = []
	for final_action, effect in _producer_effects(actions, target_predicate):
		head_arguments, variable_map = _head_variable_map(effect)
		variable_map = _complete_variable_map(final_action.parameters, variable_map)
		mapped_effect = effect.mapped(variable_map)
		transient_preconditions = _transient_preconditions(
			action=final_action,
			variable_map=variable_map,
			module_predicates=module_predicates,
		)
		if _has_arbitrary_extra_target_relation(
			action=final_action,
			target_effect=mapped_effect,
			variable_map=variable_map,
			target_arguments=head_arguments,
		):
			continue
		if not transient_preconditions:
			sequence = _finalize_sequence(
				actions=actions,
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
			)
			if sequence is not None:
				sequences.append(sequence)
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
					avoid_variables=set(head_arguments) - set(support_map.values()),
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
				context_literals = tuple(
					precondition.mapped(support_map)
					for precondition in support_action.preconditions
				) + tuple(
					precondition.mapped(variable_map)
					for precondition in final_action.preconditions
					if not _same_literal(precondition.mapped(variable_map), transient)
				)
				sequence = _finalize_sequence(
					actions=actions,
					target_effect=mapped_effect,
					target_arguments=head_arguments,
					context_literals=context_literals,
					body_actions=(
						_action_call(support_action, support_map),
						_action_call(final_action, variable_map),
					),
					producer_action_names=(support_action.name, final_action.name),
				)
				if sequence is not None:
					sequences.append(sequence)
	return tuple(_deduplicate_sequences(sequences))


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
	module_predicates: set[str],
) -> tuple[PDDLLiteralSchema, ...]:
	deleted = tuple(effect.mapped(variable_map) for effect in action.delete_effects)
	return tuple(
		mapped
		for precondition in action.preconditions
		for mapped in (precondition.mapped(variable_map),)
		if mapped.is_positive
		and mapped.arguments
		and mapped.predicate not in module_predicates
		and any(_same_literal(mapped, deleted_literal) for deleted_literal in deleted)
	)


def _finalize_sequence(
	*,
	actions: Sequence[_ParsedAction],
	target_effect: PDDLLiteralSchema,
	target_arguments: tuple[str, ...],
	context_literals: Sequence[PDDLLiteralSchema],
	body_actions: Sequence[_ActionCall],
	producer_action_names: tuple[str, ...],
) -> _ProducerSequence | None:
	if any(_same_literal(target_effect, literal) for literal in context_literals):
		return None
	sequence_body = tuple(body_actions)
	cleanup_actions = _cleanup_action_calls(
		actions=actions,
		target_effect=target_effect,
		target_arguments=target_arguments,
		body_actions=sequence_body,
	)
	if cleanup_actions:
		sequence_body += cleanup_actions
		producer_action_names += tuple(action.action.name for action in cleanup_actions)
	return _ProducerSequence(
		target_predicate=target_effect.predicate,
		target_arguments=target_arguments,
		context_literals=_deduplicate_literals(tuple(context_literals)),
		body_actions=sequence_body,
		producer_action_names=producer_action_names,
	)


def _cleanup_action_calls(
	*,
	actions: Sequence[_ParsedAction],
	target_effect: PDDLLiteralSchema,
	target_arguments: tuple[str, ...],
	body_actions: tuple[_ActionCall, ...],
) -> tuple[_ActionCall, ...]:
	if not body_actions:
		return ()
	last_call = body_actions[-1]
	last_map = {
		parameter: argument
		for parameter, argument in zip(last_call.action.parameters, last_call.arguments)
	}
	available = tuple(effect.mapped(last_map) for effect in last_call.action.add_effects)
	deleted = tuple(effect.mapped(last_map) for effect in last_call.action.delete_effects)
	for cleanup_action in actions:
		if cleanup_action.name == last_call.action.name:
			continue
		cleanup_map = _cleanup_variable_map(
			cleanup_action=cleanup_action,
			available_literals=available,
		)
		if cleanup_map is None:
			continue
		mapped_preconditions = tuple(
			precondition.mapped(cleanup_map)
			for precondition in cleanup_action.preconditions
		)
		if any(not literal.is_positive for literal in mapped_preconditions):
			continue
		if not all(
			any(_same_literal(literal, available_literal) for available_literal in available)
			for literal in mapped_preconditions
		):
			continue
		mapped_adds = tuple(effect.mapped(cleanup_map) for effect in cleanup_action.add_effects)
		mapped_deletes = tuple(
			effect.mapped(cleanup_map)
			for effect in cleanup_action.delete_effects
		)
		if any(_same_literal(target_effect, deleted_literal) for deleted_literal in mapped_deletes):
			continue
		if not any(
			any(_same_literal(add_literal, deleted_literal) for deleted_literal in deleted)
			for add_literal in mapped_adds
		):
			continue
		if _has_arbitrary_extra_target_relation(
			action=cleanup_action,
			target_effect=target_effect,
			variable_map=cleanup_map,
			target_arguments=target_arguments,
		):
			continue
		return (_action_call(cleanup_action, cleanup_map),)
	return ()


def _cleanup_variable_map(
	*,
	cleanup_action: _ParsedAction,
	available_literals: Sequence[PDDLLiteralSchema],
) -> dict[str, str] | None:
	for precondition in cleanup_action.preconditions:
		if not precondition.is_positive:
			continue
		for available in available_literals:
			if precondition.predicate != available.predicate:
				continue
			if len(precondition.arguments) != len(available.arguments):
				continue
			variable_map = {
				raw_argument: mapped_argument
				for raw_argument, mapped_argument in zip(
					precondition.arguments,
					available.arguments,
				)
			}
			return _complete_variable_map(cleanup_action.parameters, variable_map)
	return None


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
			return True
	return False


def _is_public_positive_precondition(
	*,
	literal: PDDLLiteralSchema,
	sequence: _ProducerSequence,
	module_predicates: set[str],
	recursive_module_predicates: set[str],
) -> bool:
	return (
		literal.is_positive
		and literal.predicate in module_predicates
		and literal.predicate in recursive_module_predicates
		and not _same_signature(
			literal.predicate,
			literal.arguments,
			sequence.target_predicate,
			sequence.target_arguments,
		)
	)


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
	for literal in sequence.context_literals:
		if not _is_public_positive_precondition(
			literal=literal,
			sequence=sequence,
			module_predicates=module_predicates,
			recursive_module_predicates=recursive_module_predicates,
		):
			continue
		plans.append(
			_prepare_precondition_plan(
				sequence=sequence,
				precondition=literal,
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
		context=tuple(_deduplicate(literal.to_context() for literal in sequence.context_literals)),
		body=tuple(
			AgentSpeakBodyStep("action", call.action.name, call.arguments)
			for call in sequence.body_actions
		),
		binding_certificate=(
			{
				"artifact_family": "atomic_minimal_literal_module",
				"rule_kind": "producer_action_sequence",
				"producer_actions": list(sequence.producer_action_names),
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
	source_backend: str,
	source_name: str,
	policy_file: str | Path | None,
) -> AgentSpeakPlan:
	binding_contexts = tuple(
		literal.to_context()
		for literal in sequence.context_literals
		if literal.is_positive
		and literal.predicate != precondition.predicate
		and _shares_extra_variable(
			literal=literal,
			precondition=precondition,
			head_arguments=sequence.target_arguments,
		)
	)
	context = tuple(_deduplicate(binding_contexts + (f"not {precondition.to_call()}",)))
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
				"source_backend": source_backend,
				"source_name": source_name,
				"policy_file": str(policy_file) if policy_file is not None else None,
			},
		),
	)


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


def _prune_subsumed_sibling_branches(
	plans: Sequence[AgentSpeakPlan],
) -> tuple[AgentSpeakPlan, ...]:
	kept: list[AgentSpeakPlan] = []
	for plan in tuple(plans):
		if _is_subsumed_by_existing(plan, kept):
			continue
		kept = [
			existing
			for existing in kept
			if not _plan_subsumes(plan, existing)
		]
		kept.append(plan)
	return tuple(kept)


def _is_subsumed_by_existing(plan: AgentSpeakPlan, existing_plans: Sequence[AgentSpeakPlan]) -> bool:
	return any(_plan_subsumes(existing, plan) for existing in existing_plans)


def _plan_subsumes(candidate: AgentSpeakPlan, other: AgentSpeakPlan) -> bool:
	if candidate.trigger.symbol != other.trigger.symbol:
		return False
	if len(candidate.trigger.arguments) != len(other.trigger.arguments):
		return False
	if not candidate.body or not other.body:
		return False
	if candidate.body[-1].kind != "action" or other.body[-1].kind != "action":
		return False
	if (
		candidate.body[-1].symbol != other.body[-1].symbol
		or candidate.body[-1].arguments != other.body[-1].arguments
	):
		return False
	candidate_context = set(candidate.context)
	other_context = set(other.context)
	candidate_subgoals = {
		(step.symbol, step.arguments)
		for step in candidate.body[:-1]
		if step.kind == "subgoal"
	}
	other_subgoals = {
		(step.symbol, step.arguments)
		for step in other.body[:-1]
		if step.kind == "subgoal"
	}
	return candidate_context <= other_context and candidate_subgoals <= other_subgoals


def _module_synthesis_report(
	*,
	plans: Sequence[AgentSpeakPlan],
	raw_plan_count: int,
	seeds: Sequence[str],
	module_predicates: Sequence[str],
	actions: Sequence[_ParsedAction],
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
		branch_count_by_predicate=branch_counts,
		producer_actions_by_predicate=producers,
		recursive_predicates=tuple(sorted(recursive_predicates)),
		pruned_candidate_count=max(0, raw_plan_count - len(tuple(plans))),
		theoretical_basis=(
			"MOOSE singleton-goal regression supplies lifted target-predicate evidence",
			"PDDL action schemas supply primitive producer/precondition structure",
			"policy-reuse style predicate modules allow subgoal calls between atomic literals",
			"minimal sibling branches are selected by schema subsumption over contexts and subgoals",
		),
	)


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
	if operator in {"or", "forall", "exists", "when", "imply"}:
		return ()
	return (
		PDDLLiteralSchema(
			predicate=operator,
			arguments=tuple(_parameter_name(str(argument)) for argument in expression[1:]),
			is_positive=True,
		),
	)


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
