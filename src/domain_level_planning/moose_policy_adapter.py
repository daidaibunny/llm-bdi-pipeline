"""
Adapter for MOOSE readable policy artifacts.

MOOSE stores trained policies as Python pickle files, but its official
interface exposes a stable text form via `policy <model> --dump-policy`. This
module consumes that readable decision-list form instead of importing MOOSE
runtime classes into the main package.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary
from utils.pddl_parser import PDDLDomain
from utils.pddl_parser import PDDLParser

from .atomic_module_synthesis import synthesize_atomic_minimal_literal_module_library
from .atomic_module_synthesis import PDDLLiteralSchema
from .atomic_module_synthesis import _ParsedAction
from .atomic_module_synthesis import _parameter_type
from .pddl_types import OBJ_TP_PREDICATE
from .pddl_types import type_closure
from .policy_program import LearnedPolicyRule
from .policy_program import LiftedPolicyProgram
from .policy_program import PolicyModule


@dataclass(frozen=True)
class MooseAtom:
	"""One lifted atom or action call in a MOOSE readable policy rule."""

	predicate: str
	arguments: tuple[str, ...]

	def to_call(self, variable_map: dict[str, str]) -> str:
		return _call(self.predicate, tuple(variable_map.get(arg, arg) for arg in self.arguments))


@dataclass(frozen=True)
class MooseReadableRule:
	"""One MOOSE first-order decision-list rule parsed from readable text."""

	precedence: str
	variables: tuple[str, ...]
	state_conditions: tuple[MooseAtom, ...]
	goal_conditions: tuple[MooseAtom, ...]
	actions: tuple[MooseAtom, ...]
	source_rule: str

	@property
	def is_singleton_goal_rule(self) -> bool:
		return len(self.goal_conditions) == 1

	def variable_map(self) -> dict[str, str]:
		return {variable: _agentspeak_variable(variable) for variable in self.variables}


@dataclass(frozen=True)
class MooseAtomicLibraryQualityReport:
	"""Structural quality report for direct MOOSE-to-ASL atomic libraries."""

	plan_count: int
	goal_symbol_count: int
	goal_symbols: tuple[str, ...]
	max_plans_per_goal_symbol: int
	max_body_step_count: int
	primitive_action_step_count: int
	subgoal_step_count: int
	singleton_macro_library_ready: bool
	compact_recursive_module_ready: bool
	faithful_decision_list_ready: bool
	artifact_classification: str
	warnings: tuple[str, ...] = ()

	def to_dict(self) -> dict[str, object]:
		return {
			"plan_count": self.plan_count,
			"goal_symbol_count": self.goal_symbol_count,
			"goal_symbols": list(self.goal_symbols),
			"max_plans_per_goal_symbol": self.max_plans_per_goal_symbol,
			"max_body_step_count": self.max_body_step_count,
			"primitive_action_step_count": self.primitive_action_step_count,
			"subgoal_step_count": self.subgoal_step_count,
			"singleton_macro_library_ready": self.singleton_macro_library_ready,
			"compact_recursive_module_ready": self.compact_recursive_module_ready,
			"faithful_decision_list_ready": self.faithful_decision_list_ready,
			"artifact_classification": self.artifact_classification,
			"warnings": list(self.warnings),
		}


@dataclass(frozen=True)
class MooseMacroEvidenceReducerReport:
	"""Audit record for validated MOOSE macro evidence preserved in ASL."""

	raw_singleton_macro_count: int
	validated_macro_count: int
	invalid_macro_count: int
	deduplicated_macro_count: int
	merged_plan_count: int
	validation_basis: tuple[str, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"raw_singleton_macro_count": self.raw_singleton_macro_count,
			"validated_macro_count": self.validated_macro_count,
			"invalid_macro_count": self.invalid_macro_count,
			"deduplicated_macro_count": self.deduplicated_macro_count,
			"merged_plan_count": self.merged_plan_count,
			"validation_basis": list(self.validation_basis),
		}


@dataclass(frozen=True)
class _MooseMacroEvidencePlans:
	plans: tuple[AgentSpeakPlan, ...]
	report: MooseMacroEvidenceReducerReport


def parse_moose_readable_policy(text: str) -> tuple[MooseReadableRule, ...]:
	"""Parse MOOSE `--dump-policy` output into structured lifted rules."""

	blocks = tuple(
		block.strip()
		for block in re.split(r"\n\s*\n", str(text or "").strip())
		if block.strip()
	)
	rules: list[MooseReadableRule] = []
	for index, block in enumerate(blocks, start=1):
		rule = _parse_optional_rule_block(block, index=index)
		if rule is not None:
			rules.append(rule)
	return tuple(rules)


def load_moose_readable_policy(path: str | Path) -> tuple[MooseReadableRule, ...]:
	"""Load a MOOSE readable policy file from disk."""

	return parse_moose_readable_policy(Path(path).read_text(encoding="utf-8"))


def policy_program_from_moose_readable_policy(
	text: str,
	*,
	domain_name: str,
	source_name: str,
	policy_file: str | Path | None = None,
) -> LiftedPolicyProgram:
	"""Convert MOOSE readable policy text into the policy-first IR."""

	rules = parse_moose_readable_policy(text)
	learned_rules: list[LearnedPolicyRule] = []
	modules: list[PolicyModule] = []
	for index, rule in enumerate(rules, start=1):
		if not rule.is_singleton_goal_rule:
			continue
		variable_map = rule.variable_map()
		goal = rule.goal_conditions[0]
		name = f"moose_{_safe_name(source_name)}_rule_{index}"
		learned_rules.append(
			LearnedPolicyRule(
				name=name,
				conditions=tuple(
					(condition.to_call(variable_map), "holds")
					for condition in rule.state_conditions
				)
				+ ((goal.to_call(variable_map), "goal"),),
				effects=tuple(
					(f"primitive_action:{action.to_call(variable_map)}", "call")
					for action in rule.actions
				),
				source_rule=rule.source_rule,
			),
		)
		modules.append(
			PolicyModule(
				name=f"module_{_safe_name(goal.predicate)}",
				parameters=tuple(variable_map.get(arg, arg) for arg in goal.arguments),
				rule_names=(name,),
				goal_symbol=goal.predicate,
			),
		)
	return LiftedPolicyProgram(
		domain_name=domain_name,
		backend_name="moose",
		source_name=source_name,
		representation="moose_first_order_decision_list",
		features=(),
		rules=tuple(learned_rules),
		modules=tuple(modules),
		progress_certificate={
			"termination_basis": "moose_learned_precedence_order",
			"raw_rule_count": len(rules),
			"singleton_goal_rule_count": len(learned_rules),
		},
		provenance={
			"paper_basis": "MOOSE goal-regression generalized planner",
			"policy_file": str(policy_file) if policy_file is not None else None,
			"source_backend": "moose",
			"artifact_format": "policy --dump-policy readable text",
		},
		is_learned_policy=True,
	)


def compile_moose_readable_policy_to_asl_library(
	text: str,
	*,
	domain_name: str,
	source_name: str,
	policy_file: str | Path | None = None,
) -> PlanLibrary:
	"""Compile singleton-goal MOOSE readable policy rules into ASL plans."""

	rules = parse_moose_readable_policy(text)
	plans: list[AgentSpeakPlan] = []
	for index, rule in enumerate(rules, start=1):
		if not rule.is_singleton_goal_rule:
			continue
		variable_map = rule.variable_map()
		goal = rule.goal_conditions[0]
		plans.append(
			AgentSpeakPlan(
				plan_name=f"moose_{_safe_name(source_name)}_rule_{index}",
				trigger=AgentSpeakTrigger(
					event_type="achievement_goal",
					symbol=goal.predicate,
					arguments=tuple(variable_map.get(arg, arg) for arg in goal.arguments),
				),
				context=tuple(
					condition.to_call(variable_map)
					for condition in rule.state_conditions
				),
				body=tuple(
					AgentSpeakBodyStep(
						"action",
						action.predicate,
						tuple(variable_map.get(arg, arg) for arg in action.arguments),
					)
					for action in rule.actions
				),
				binding_certificate=(
					{
						"artifact_family": "moose_goal_regression_policy",
						"source_backend": "moose",
						"source_name": source_name,
						"policy_file": str(policy_file) if policy_file is not None else None,
						"precedence": rule.precedence,
					},
				),
			),
		)
	quality_report = audit_moose_atomic_library_quality(
		plans=tuple(plans),
	)
	return PlanLibrary(
		domain_name=domain_name,
		plans=tuple(plans),
		metadata={
			"generation_mode": "faithful_moose_decision_list_asl_library",
			"atomic_template_backend": "moose",
			"source_name": source_name,
			"policy_file": str(policy_file) if policy_file is not None else None,
			"raw_rule_count": len(rules),
			"compiled_singleton_rule_count": len(plans),
			"library_quality": quality_report.to_dict(),
			"artifact_contract": (
				"faithful ASL rendering of MOOSE first-order decision-list "
				"singleton-goal rules; rule order, state context, goal trigger, "
				"and macro action sequence are preserved"
			),
		},
	)


def compile_moose_readable_policy_to_minimal_module_asl_library(
	text: str,
	*,
	domain_file: str | Path,
	domain_name: str,
	source_name: str,
	policy_file: str | Path | None = None,
) -> PlanLibrary:
	"""Compress MOOSE singleton evidence into compact recursive atomic modules."""

	rules = parse_moose_readable_policy(text)
	seed_predicates = tuple(
		dict.fromkeys(
			rule.goal_conditions[0].predicate
			for rule in rules
			if rule.is_singleton_goal_rule
		),
	)
	library = synthesize_atomic_minimal_literal_module_library(
		domain_file=domain_file,
		seed_predicates=seed_predicates,
		source_backend="moose_schema_minimal_modules",
		source_name=source_name,
		policy_file=policy_file,
	)
	macro_evidence = _compile_validated_moose_macro_evidence_plans(
		rules=rules,
		domain_file=domain_file,
		source_name=source_name,
		policy_file=policy_file,
	)
	merged_plans = _ensure_unique_plan_names(
		_deduplicate_agent_plans((*library.plans, *macro_evidence.plans)),
	)
	macro_quality_report = audit_moose_atomic_library_quality(plans=macro_evidence.plans)
	library_quality = _post_moose_reducer_library_quality(
		plans=merged_plans,
		macro_evidence_plan_count=len(macro_evidence.plans),
	)
	return PlanLibrary(
		domain_name=domain_name or library.domain_name,
		plans=merged_plans,
		initial_beliefs=library.initial_beliefs,
		metadata={
			**dict(library.metadata),
			"source_raw_rule_count": len(rules),
			"source_seed_predicates": list(seed_predicates),
			"moose_macro_evidence_reducer": {
				**macro_evidence.report.to_dict(),
				"merged_plan_count": len(merged_plans),
			},
			"library_quality": library_quality,
			"moose_macro_library_quality": macro_quality_report.to_dict(),
		},
	)


def _compile_validated_moose_macro_evidence_plans(
	*,
	rules: Sequence[MooseReadableRule],
	domain_file: str | Path,
	source_name: str,
	policy_file: str | Path | None,
) -> _MooseMacroEvidencePlans:
	domain = PDDLParser.parse_domain(domain_file)
	actions_by_name = {
		action.name: action
		for action in (_ParsedAction.from_pddl(action) for action in domain.actions)
	}
	predicate_types = _predicate_parameter_types(domain)
	raw_singleton_rules = tuple(rule for rule in rules if rule.is_singleton_goal_rule)
	plans: list[AgentSpeakPlan] = []
	invalid_count = 0
	for index, rule in enumerate(raw_singleton_rules, start=1):
		plan = _validated_moose_macro_rule_plan(
			rule=rule,
			rule_index=index,
			actions_by_name=actions_by_name,
			predicate_types=predicate_types,
			type_tokens=domain.types,
			source_name=source_name,
			policy_file=policy_file,
		)
		if plan is None:
			invalid_count += 1
			continue
		plans.append(plan)
	deduplicated = _deduplicate_agent_plans(tuple(plans))
	return _MooseMacroEvidencePlans(
		plans=_ensure_unique_plan_names(deduplicated),
		report=MooseMacroEvidenceReducerReport(
			raw_singleton_macro_count=len(raw_singleton_rules),
			validated_macro_count=len(plans),
			invalid_macro_count=invalid_count,
			deduplicated_macro_count=len(deduplicated),
			merged_plan_count=len(deduplicated),
			validation_basis=(
				"MOOSE readable singleton goal rule supplies state context, goal, and macro action sequence",
				"PDDL action schemas validate every primitive action arity and symbolic precondition/effect transition",
				"PDDL predicate and action parameter types compile to reserved obj_tp/2 context guards",
				"Goal variables are alpha-normalized to X,Y,... and non-goal witnesses to fresh lifted variables",
			),
		),
	)


def _post_moose_reducer_library_quality(
	*,
	plans: Sequence[AgentSpeakPlan],
	macro_evidence_plan_count: int,
) -> dict[str, object]:
	plan_tuple = tuple(plans or ())
	subgoal_step_count = sum(
		1
		for plan in plan_tuple
		for step in tuple(plan.body or ())
		if step.kind == "subgoal"
	)
	primitive_action_step_count = sum(
		1
		for plan in plan_tuple
		for step in tuple(plan.body or ())
		if step.kind == "action"
	)
	if macro_evidence_plan_count and subgoal_step_count:
		classification = "moose_evidence_augmented_compact_recursive_atomic_module_library"
	elif macro_evidence_plan_count:
		classification = "validated_moose_macro_evidence_atomic_library"
	elif subgoal_step_count:
		classification = "compact_recursive_atomic_module_library"
	else:
		classification = "compact_lifted_singleton_macro_library"
	return {
		"artifact_classification": classification,
		"plan_count": len(plan_tuple),
		"primitive_action_step_count": primitive_action_step_count,
		"subgoal_step_count": subgoal_step_count,
		"moose_macro_evidence_plan_count": macro_evidence_plan_count,
		"compact_recursive_module_ready": subgoal_step_count > 0,
		"validated_macro_evidence_ready": macro_evidence_plan_count > 0,
	}


def _validated_moose_macro_rule_plan(
	*,
	rule: MooseReadableRule,
	rule_index: int,
	actions_by_name: Mapping[str, _ParsedAction],
	predicate_types: Mapping[str, tuple[str, ...]],
	type_tokens: Sequence[str],
	source_name: str,
	policy_file: str | Path | None,
) -> AgentSpeakPlan | None:
	if not rule.is_singleton_goal_rule or not rule.actions:
		return None
	goal = rule.goal_conditions[0]
	variable_map = _canonical_rule_variable_map(rule)
	type_contexts = _obj_tp_contexts_for_rule(
		rule=rule,
		actions_by_name=actions_by_name,
		predicate_types=predicate_types,
		type_tokens=type_tokens,
		variable_map=variable_map,
	)
	if type_contexts is None:
		return None
	if not _moose_macro_rule_is_symbolically_executable(
		rule=rule,
		actions_by_name=actions_by_name,
	):
		return None
	return AgentSpeakPlan(
		plan_name=f"moose_reduced_{_safe_name(source_name)}_rule_{rule_index}",
		trigger=AgentSpeakTrigger(
			event_type="achievement_goal",
			symbol=goal.predicate,
			arguments=tuple(variable_map.get(argument, argument) for argument in goal.arguments),
		),
		context=_deduplicate_strings(
			tuple(condition.to_call(variable_map) for condition in rule.state_conditions)
			+ type_contexts,
		),
		body=tuple(
			AgentSpeakBodyStep(
				"action",
				action.predicate,
				tuple(variable_map.get(argument, argument) for argument in action.arguments),
			)
			for action in rule.actions
		),
		binding_certificate=(
			{
				"artifact_family": "validated_moose_macro_evidence",
				"source_backend": "moose",
				"source_name": source_name,
				"policy_file": str(policy_file) if policy_file is not None else None,
				"precedence": rule.precedence,
				"validation": "pddl_schema_symbolic_execution",
			},
		),
	)


def _canonical_rule_variable_map(rule: MooseReadableRule) -> dict[str, str]:
	names = ("X", "Y", "Z", "A", "B", "C", "D")
	mapping: dict[str, str] = {}
	next_index = 0
	for argument in rule.goal_conditions[0].arguments if rule.goal_conditions else ():
		if argument in mapping:
			continue
		mapping[argument] = names[next_index] if next_index < len(names) else f"V{next_index}"
		next_index += 1
	for variable in rule.variables:
		if variable in mapping:
			continue
		mapping[variable] = names[next_index] if next_index < len(names) else f"V{next_index}"
		next_index += 1
	return mapping


def _moose_macro_rule_is_symbolically_executable(
	*,
	rule: MooseReadableRule,
	actions_by_name: Mapping[str, _ParsedAction],
) -> bool:
	state = {_atom_key(condition): True for condition in rule.state_conditions}
	for action_call in rule.actions:
		action = actions_by_name.get(action_call.predicate)
		if action is None or len(action.parameters) != len(action_call.arguments):
			return False
		binding = {
			parameter: argument
			for parameter, argument in zip(action.parameters, action_call.arguments)
		}
		for precondition in action.preconditions:
			mapped = _map_schema_literal(precondition, binding)
			current = state.get(_atom_key(mapped))
			if precondition.is_positive and current is not True:
				return False
			if not precondition.is_positive and current is True:
				return False
		for delete_effect in action.delete_effects:
			state[_atom_key(_map_schema_literal(delete_effect, binding))] = False
		for add_effect in action.add_effects:
			state[_atom_key(_map_schema_literal(add_effect, binding))] = True
	return all(state.get(_atom_key(goal)) is True for goal in rule.goal_conditions)


def _map_schema_literal(
	literal: PDDLLiteralSchema,
	binding: Mapping[str, str],
) -> MooseAtom:
	return MooseAtom(
		predicate=literal.predicate,
		arguments=tuple(binding.get(argument, argument) for argument in literal.arguments),
	)


def _obj_tp_contexts_for_rule(
	*,
	rule: MooseReadableRule,
	actions_by_name: Mapping[str, _ParsedAction],
	predicate_types: Mapping[str, tuple[str, ...]],
	type_tokens: Sequence[str],
	variable_map: Mapping[str, str],
) -> tuple[str, ...] | None:
	types_by_argument: dict[str, set[str]] = {}
	for atom in (*rule.state_conditions, *rule.goal_conditions):
		for argument, type_name in zip(atom.arguments, predicate_types.get(atom.predicate, ())):
			_add_required_type(types_by_argument, argument, type_name)
	for action_call in rule.actions:
		action = actions_by_name.get(action_call.predicate)
		if action is None or len(action.parameters) != len(action_call.arguments):
			return None
		for parameter, argument in zip(action.parameters, action_call.arguments):
			_add_required_type(
				types_by_argument,
				argument,
				action.parameter_types.get(parameter, "object"),
			)
	contexts: list[str] = []
	for argument, required_types in sorted(types_by_argument.items()):
		most_specific = _most_specific_compatible_types(required_types, type_tokens)
		if most_specific is None:
			return None
		for type_name in most_specific:
			if type_name == "object":
				continue
			contexts.append(
				f"{OBJ_TP_PREDICATE}({variable_map.get(argument, argument)}, {type_name})",
			)
	return _deduplicate_strings(tuple(contexts))


def _add_required_type(
	types_by_argument: dict[str, set[str]],
	argument: str,
	type_name: str,
) -> None:
	canonical = _canonical_type_name(type_name)
	if canonical == "object":
		return
	types_by_argument.setdefault(argument, set()).add(canonical)


def _predicate_parameter_types(domain: PDDLDomain) -> dict[str, tuple[str, ...]]:
	return {
		predicate.name: tuple(_parameter_type(parameter) for parameter in predicate.parameters)
		for predicate in domain.predicates
	}


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
	return tuple(
		dict.fromkeys(
			type_name
			for type_name in non_object
			if not any(
				type_name != other
				and _is_subtype(other, type_name, type_tokens)
				for other in non_object
			)
		),
	)


def _types_are_compatible(left: str, right: str, type_tokens: Sequence[str]) -> bool:
	if left == "object" or right == "object":
		return True
	return _is_subtype(left, right, type_tokens) or _is_subtype(right, left, type_tokens)


def _is_subtype(child: str, parent: str, type_tokens: Sequence[str]) -> bool:
	return _canonical_type_name(parent) in type_closure(_canonical_type_name(child), type_tokens)


def _canonical_type_name(type_name: str) -> str:
	return str(type_name or "").strip().lower() or "object"


def _atom_key(atom: MooseAtom) -> tuple[str, tuple[str, ...]]:
	return (atom.predicate, atom.arguments)


def _deduplicate_agent_plans(plans: Sequence[AgentSpeakPlan]) -> tuple[AgentSpeakPlan, ...]:
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
	name_counts: dict[str, int] = {}
	unique: list[AgentSpeakPlan] = []
	for plan in plans:
		seen_count = name_counts.get(plan.plan_name, 0)
		name_counts[plan.plan_name] = seen_count + 1
		if seen_count == 0:
			unique.append(plan)
			continue
		unique.append(
			AgentSpeakPlan(
				plan_name=f"{plan.plan_name}_{seen_count + 1}",
				trigger=plan.trigger,
				context=plan.context,
				body=plan.body,
				source_instruction_ids=plan.source_instruction_ids,
				binding_certificate=plan.binding_certificate,
			),
		)
	return tuple(unique)


def _deduplicate_strings(items: Sequence[str]) -> tuple[str, ...]:
	return tuple(dict.fromkeys(item for item in items if item))


def audit_moose_atomic_library_quality(
	*,
	plans: Sequence[AgentSpeakPlan],
	max_compact_plan_count: int = 10,
	max_macro_body_steps: int = 8,
) -> MooseAtomicLibraryQualityReport:
	"""Classify MOOSE output without mistaking decision-list macros for recursion."""

	plan_tuple = tuple(plans or ())
	plans_by_goal: dict[str, int] = {}
	primitive_action_step_count = 0
	subgoal_step_count = 0
	max_body_step_count = 0
	for plan in plan_tuple:
		plans_by_goal[plan.trigger.symbol] = plans_by_goal.get(plan.trigger.symbol, 0) + 1
		body = tuple(plan.body or ())
		max_body_step_count = max(max_body_step_count, len(body))
		primitive_action_step_count += sum(1 for step in body if step.kind == "action")
		subgoal_step_count += sum(1 for step in body if step.kind == "subgoal")
	goal_symbols = tuple(sorted(plans_by_goal))
	max_plans_per_goal_symbol = max(plans_by_goal.values(), default=0)
	singleton_macro_library_ready = (
		len(plan_tuple) <= max_compact_plan_count
		and max_body_step_count <= max_macro_body_steps
	)
	compact_recursive_module_ready = (
		singleton_macro_library_ready
		and subgoal_step_count > 0
	)
	faithful_decision_list_ready = bool(plan_tuple) and primitive_action_step_count > 0
	if compact_recursive_module_ready:
		artifact_classification = "compact_recursive_atomic_module_library"
	elif singleton_macro_library_ready:
		artifact_classification = "compact_lifted_singleton_macro_library"
	elif faithful_decision_list_ready:
		artifact_classification = "faithful_moose_decision_list_asl_library"
	else:
		artifact_classification = "empty_or_unbound_moose_atomic_library"
	warnings: list[str] = []
	if subgoal_step_count == 0 and plan_tuple:
		warnings.append(
			"Direct MOOSE output contains primitive macro actions but no recursive "
			"atomic subgoal calls; claim faithful decision-list compilation rather "
			"than compact recursive module synthesis."
		)
	if len(plan_tuple) > max_compact_plan_count:
		warnings.append(
			"Plan count exceeds the compact-library threshold; this is acceptable "
			"for faithful MOOSE decision-list compilation, but it is not a compact "
			"recursive module artifact."
		)
	if max_body_step_count > max_macro_body_steps:
		warnings.append(
			"At least one plan body exceeds the compact macro threshold; inspect "
			"whether raw trace replay leaked into the library."
		)
	return MooseAtomicLibraryQualityReport(
		plan_count=len(plan_tuple),
		goal_symbol_count=len(goal_symbols),
		goal_symbols=goal_symbols,
		max_plans_per_goal_symbol=max_plans_per_goal_symbol,
		max_body_step_count=max_body_step_count,
		primitive_action_step_count=primitive_action_step_count,
		subgoal_step_count=subgoal_step_count,
		singleton_macro_library_ready=singleton_macro_library_ready,
		compact_recursive_module_ready=compact_recursive_module_ready,
		faithful_decision_list_ready=faithful_decision_list_ready,
		artifact_classification=artifact_classification,
		warnings=tuple(warnings),
	)


def _parse_optional_rule_block(block: str, *, index: int) -> MooseReadableRule | None:
	lines = tuple(line.rstrip() for line in block.splitlines() if line.strip())
	fields: dict[str, str] = {}
	for line in lines:
		if ":" not in line:
			continue
		key, value = line.split(":", 1)
		fields[key.strip()] = value.strip()
	required = ("precedence", "vars", "s_cond", "g_cond", "actions")
	missing = tuple(key for key in required if key not in fields)
	if len(missing) == len(required):
		return None
	if missing:
		raise ValueError(
			f"MOOSE readable policy rule {index} is missing fields: {', '.join(missing)}",
		)
	return MooseReadableRule(
		precedence=fields["precedence"],
		variables=tuple(item for item in fields["vars"].split() if item),
		state_conditions=_parse_atoms(fields["s_cond"]),
		goal_conditions=_parse_atoms(fields["g_cond"]),
		actions=_parse_atoms(fields["actions"]),
		source_rule="\n".join(lines),
	)


def _parse_atoms(text: str) -> tuple[MooseAtom, ...]:
	atoms: list[MooseAtom] = []
	for raw_atom in re.findall(r"\(([^()]*)\)", str(text or "")):
		parts = tuple(part for part in raw_atom.split() if part)
		if not parts:
			continue
		atoms.append(MooseAtom(predicate=parts[0], arguments=parts[1:]))
	return tuple(atoms)


def _agentspeak_variable(variable: str) -> str:
	text = str(variable or "").strip()
	if not text:
		return "V"
	return text[:1].upper() + text[1:]


def _call(predicate: str, arguments: Sequence[str]) -> str:
	args = tuple(arguments or ())
	return str(predicate) if not args else f"{predicate}({', '.join(args)})"


def _safe_name(value: str) -> str:
	text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip()).strip("_")
	if not text:
		return "policy"
	if text[0].isdigit():
		return f"p_{text}"
	return text
