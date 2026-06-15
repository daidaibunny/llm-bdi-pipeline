"""
Bind conservative DLPlan feature patterns to lifted ASL contexts and calls.

This module does not try to interpret arbitrary Description Logic features.
It only binds patterns whose PDDL meaning is syntactically recoverable from the
feature expression. Unsupported features are reported instead of guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from plan_library.models import AgentSpeakBodyStep
from utils.pddl_parser import PDDLAction, PDDLDomain

from .gp_backends import SketchPolicy
from .gp_backends import SketchEffect, SketchRule
from .pddl_expression import parse_pddl_literals, parameter_variables
from .sketch_asl_compiler import SketchFeatureBinding


@dataclass(frozen=True)
class FeatureBindingReport:
	"""Result of a conservative feature-binding pass."""

	bindings: Mapping[str, SketchFeatureBinding]
	unsupported_features: Mapping[str, str]
	action_effect_candidates: Mapping[str, tuple["ActionEffectBindingCandidate", ...]]


@dataclass(frozen=True)
class ActionEffectBindingCandidate:
	"""One action-schema candidate that can realize a feature-value change."""

	feature_id: str
	operator: str
	effect_predicate: str
	add_effects: tuple[tuple[str, tuple[str, ...]], ...]
	action_name: str
	context: tuple[str, ...]
	body: tuple[AgentSpeakBodyStep, ...]


@dataclass(frozen=True)
class _GoalAlignedFeature:
	predicate: str
	arity: int


def bind_recoverable_dlplan_features(
	*,
	policy: SketchPolicy,
	domain: PDDLDomain,
) -> FeatureBindingReport:
	"""Bind DLPlan features whose predicate-level meaning is recoverable."""

	predicate_arities = {
		predicate.name: len(predicate.parameters)
		for predicate in domain.predicates
	}
	bindings: dict[str, SketchFeatureBinding] = {}
	unsupported: dict[str, str] = {}
	action_candidates: dict[str, tuple[ActionEffectBindingCandidate, ...]] = {}
	for feature_id, expression in policy.features.items():
		binding = _bind_feature_expression(expression, predicate_arities)
		if binding is None:
			unsupported[feature_id] = expression
			continue
		bindings[feature_id] = binding
		predicate = _primitive_count_predicate(expression)
		if predicate is not None:
			candidates = _action_effect_candidates(
				feature_id=feature_id,
				predicate=predicate,
				actions=tuple(domain.actions),
			)
			if candidates:
				action_candidates[feature_id] = candidates
	return FeatureBindingReport(
		bindings=bindings,
		unsupported_features=unsupported,
		action_effect_candidates=action_candidates,
	)


def bind_unique_action_effect_candidates(
	report: FeatureBindingReport,
) -> FeatureBindingReport:
	"""Promote unambiguous action-effect candidates into executable bindings."""

	bindings = dict(report.bindings)
	for feature_id, candidates in report.action_effect_candidates.items():
		if len(candidates) != 1:
			continue
		candidate = candidates[0]
		binding = bindings.get(feature_id)
		if binding is None:
			continue
		effect_contexts = dict(binding.effect_contexts or {})
		effect_body = dict(binding.effect_body)
		effect_contexts[candidate.operator] = candidate.context
		effect_body[candidate.operator] = candidate.body
		bindings[feature_id] = SketchFeatureBinding(
			condition_contexts=binding.condition_contexts,
			effect_contexts=effect_contexts,
			effect_body=effect_body,
		)
	return FeatureBindingReport(
		bindings=bindings,
		unsupported_features=report.unsupported_features,
		action_effect_candidates=report.action_effect_candidates,
	)


def bind_goal_aligned_action_effect_candidates(
	*,
	policy: SketchPolicy,
	report: FeatureBindingReport,
) -> FeatureBindingReport:
	"""Promote action candidates using goal-aligned feature effects as evidence."""

	goal_aligned_features = {
		feature_id: feature
		for feature_id, expression in policy.features.items()
		if (feature := _goal_aligned_feature(expression)) is not None
	}
	bindings = dict(report.bindings)
	for rule in policy.parsed_rules:
		progress_effects = _progress_effects(rule, goal_aligned_features)
		if not progress_effects:
			progress_effects = tuple(
				_ProgressEffect(
					predicate=feature.predicate,
					arguments=_arguments_for_arity(feature.arity),
				)
				for feature in goal_aligned_features.values()
			)
		if not progress_effects:
			continue
		for effect in rule.effects:
			candidates = report.action_effect_candidates.get(effect.feature_id, ())
			if not candidates:
				continue
			matching = tuple(
				_remap_candidate_to_progress_effect(candidate, progress_effect)
				for candidate in candidates
				for progress_effect in progress_effects
				if candidate.operator == effect.operator
				and _candidate_adds_predicate(candidate, progress_effect.predicate)
			)
			if len(matching) != 1:
				continue
			bindings[effect.feature_id] = _merge_action_candidate(
				bindings[effect.feature_id],
				matching[0],
			)
	return FeatureBindingReport(
		bindings=bindings,
		unsupported_features=report.unsupported_features,
		action_effect_candidates=report.action_effect_candidates,
	)


def _bind_feature_expression(
	expression: str,
	predicate_arities: Mapping[str, int],
) -> SketchFeatureBinding | None:
	text = _normalize_expression(expression)
	nullary = re.fullmatch(r"b_nullary\(([^(),]+)\)", text)
	if nullary:
		predicate = nullary.group(1)
		if predicate_arities.get(predicate) != 0:
			return None
		return SketchFeatureBinding(
			condition_contexts={
				"c_b_pos": (predicate,),
				"c_b_neg": (f"not {predicate}",),
			},
			effect_body={},
		)

	primitive_concept = re.fullmatch(r"n_count\(c_primitive\(([^(),]+),0\)\)", text)
	if primitive_concept:
		predicate = primitive_concept.group(1)
		return _predicate_count_binding(predicate, predicate_arities, goal_aligned=False)

	primitive_role = re.fullmatch(r"n_count\(r_primitive\(([^(),]+),0,1\)\)", text)
	if primitive_role:
		predicate = primitive_role.group(1)
		return _predicate_count_binding(predicate, predicate_arities, goal_aligned=False)

	goal_concept = re.fullmatch(
		r"n_count\(c_equal\(c_primitive\(([^(),]+),0\),c_primitive\(\1_g,0\)\)\)",
		text,
	)
	if goal_concept:
		predicate = goal_concept.group(1)
		return _predicate_count_binding(predicate, predicate_arities, goal_aligned=True)

	goal_role = re.fullmatch(
		r"n_count\(c_equal\(r_primitive\(([^(),]+),0,1\),r_primitive\(\1_g,0,1\)\)\)",
		text,
	)
	if goal_role:
		predicate = goal_role.group(1)
		return _predicate_count_binding(predicate, predicate_arities, goal_aligned=True)

	goal_role_intersection = re.fullmatch(
		r"n_count\(r_and\(r_primitive\(([^(),]+),0,1\),r_primitive\(\1_g,0,1\)\)\)",
		text,
	)
	if goal_role_intersection:
		predicate = goal_role_intersection.group(1)
		return _predicate_count_binding(predicate, predicate_arities, goal_aligned=True)

	return None


def _predicate_count_binding(
	predicate: str,
	predicate_arities: Mapping[str, int],
	*,
	goal_aligned: bool,
) -> SketchFeatureBinding | None:
	arity = predicate_arities.get(predicate)
	if arity is None:
		return None
	arguments = _arguments_for_arity(arity)
	atom = _call(predicate, arguments)
	goal_atom = _call(f"goal_{predicate}", arguments)
	condition_contexts: dict[str, tuple[str, ...]] = {
		"c_n_gt": (),
		"c_n_eq": (),
	}
	effect_contexts: dict[str, tuple[str, ...]] = {}
	effect_body: dict[str, tuple[AgentSpeakBodyStep, ...]] = {}
	if goal_aligned:
		effect_contexts["e_n_inc"] = (goal_atom, f"not {atom}")
		effect_body["e_n_inc"] = (
			AgentSpeakBodyStep("subgoal", predicate, arguments),
		)
	else:
		effect_contexts["e_n_inc"] = (f"not {atom}",)
		effect_body["e_n_inc"] = (
			AgentSpeakBodyStep("subgoal", predicate, arguments),
		)
	effect_contexts["e_n_bot"] = ()
	effect_body["e_n_bot"] = ()
	return SketchFeatureBinding(
		condition_contexts=condition_contexts,
		effect_contexts=effect_contexts,
		effect_body=effect_body,
	)


def _action_effect_candidates(
	*,
	feature_id: str,
	predicate: str,
	actions: tuple[PDDLAction, ...],
) -> tuple[ActionEffectBindingCandidate, ...]:
	candidates: list[ActionEffectBindingCandidate] = []
	for action in actions:
		action_arguments = parameter_variables(action.parameters)
		preconditions = tuple(
			literal.signature()
			for literal in parse_pddl_literals(action.preconditions)
		)
		effects = parse_pddl_literals(action.effects)
		add_effects = tuple(
			(
				effect.predicate,
				tuple(_var(argument) for argument in effect.arguments),
			)
			for effect in effects
			if effect.is_positive
		)
		for effect in effects:
			if effect.predicate != predicate:
				continue
			if effect.is_positive:
				continue
			candidates.append(
				ActionEffectBindingCandidate(
					feature_id=feature_id,
					operator="e_n_dec",
					effect_predicate=effect.predicate,
					add_effects=add_effects,
					action_name=action.name,
					context=preconditions,
					body=(AgentSpeakBodyStep("primitive_action", action.name, action_arguments),),
				),
			)
	return tuple(candidates)


def _merge_action_candidate(
	binding: SketchFeatureBinding,
	candidate: ActionEffectBindingCandidate,
) -> SketchFeatureBinding:
	effect_contexts = dict(binding.effect_contexts or {})
	effect_body = dict(binding.effect_body)
	effect_contexts[candidate.operator] = candidate.context
	effect_body[candidate.operator] = candidate.body
	return SketchFeatureBinding(
		condition_contexts=binding.condition_contexts,
		effect_contexts=effect_contexts,
		effect_body=effect_body,
	)


@dataclass(frozen=True)
class _ProgressEffect:
	predicate: str
	arguments: tuple[str, ...]


def _progress_effects(
	rule: SketchRule,
	goal_aligned_features: Mapping[str, _GoalAlignedFeature],
) -> tuple[_ProgressEffect, ...]:
	effects: list[_ProgressEffect] = []
	for effect in rule.effects:
		if effect.operator != "e_n_inc":
			continue
		feature = goal_aligned_features.get(effect.feature_id)
		if feature is not None:
			effects.append(
				_ProgressEffect(
					predicate=feature.predicate,
					arguments=_arguments_for_arity(feature.arity),
				),
			)
	return tuple(effects)


def _candidate_adds_predicate(
	candidate: ActionEffectBindingCandidate,
	predicate: str,
) -> bool:
	return any(add_predicate == predicate for add_predicate, _ in candidate.add_effects)


def _remap_candidate_to_progress_effect(
	candidate: ActionEffectBindingCandidate,
	progress_effect: _ProgressEffect,
) -> ActionEffectBindingCandidate:
	for add_predicate, add_arguments in candidate.add_effects:
		if add_predicate != progress_effect.predicate:
			continue
		if len(add_arguments) != len(progress_effect.arguments):
			continue
		substitution = dict(zip(add_arguments, progress_effect.arguments))
		progress_context = (
			_call(f"goal_{progress_effect.predicate}", progress_effect.arguments),
			f"not {_call(progress_effect.predicate, progress_effect.arguments)}",
		)
		return ActionEffectBindingCandidate(
			feature_id=candidate.feature_id,
			operator=candidate.operator,
			effect_predicate=candidate.effect_predicate,
			add_effects=candidate.add_effects,
			action_name=candidate.action_name,
			context=tuple(
				dict.fromkeys(
					(
						*progress_context,
						*(
							_rewrite_variables(item, substitution)
							for item in candidate.context
						),
					),
				),
			),
			body=tuple(_rewrite_body_step(step, substitution) for step in candidate.body),
		)
	return candidate


def _goal_aligned_feature(expression: str) -> _GoalAlignedFeature | None:
	text = _normalize_expression(expression)
	concept = re.fullmatch(
		r"n_count\(c_equal\(c_primitive\(([^(),]+),0\),c_primitive\(\1_g,0\)\)\)",
		text,
	)
	if concept:
		return _GoalAlignedFeature(predicate=concept.group(1), arity=1)
	role = re.fullmatch(
		r"n_count\(c_equal\(r_primitive\(([^(),]+),0,1\),r_primitive\(\1_g,0,1\)\)\)",
		text,
	)
	if role:
		return _GoalAlignedFeature(predicate=role.group(1), arity=2)
	role_intersection = re.fullmatch(
		r"n_count\(r_and\(r_primitive\(([^(),]+),0,1\),r_primitive\(\1_g,0,1\)\)\)",
		text,
	)
	if role_intersection:
		return _GoalAlignedFeature(predicate=role_intersection.group(1), arity=2)
	return None


def _rewrite_body_step(
	step: AgentSpeakBodyStep,
	substitution: Mapping[str, str],
) -> AgentSpeakBodyStep:
	return AgentSpeakBodyStep(
		step.kind,
		step.symbol,
		tuple(substitution.get(argument, argument) for argument in step.arguments),
	)


def _rewrite_variables(text: str, substitution: Mapping[str, str]) -> str:
	result = str(text)
	for source, target in sorted(substitution.items(), key=lambda item: len(item[0]), reverse=True):
		result = re.sub(rf"\b{re.escape(source)}\b", target, result)
	return result


def _primitive_count_predicate(expression: str) -> str | None:
	text = _normalize_expression(expression)
	match = re.fullmatch(r"n_count\(c_primitive\(([^(),]+),0\)\)", text)
	if not match:
		match = re.fullmatch(r"n_count\(r_primitive\(([^(),]+),0,1\)\)", text)
	return match.group(1) if match else None


def _arguments_for_arity(arity: int) -> tuple[str, ...]:
	return tuple(parameter_variables(tuple(f"?x{index}" for index in range(arity))))


def _var(parameter: str) -> str:
	return parameter_variables((parameter,))[0]


def _call(predicate: str, arguments: tuple[str, ...]) -> str:
	return predicate if not arguments else f"{predicate}({', '.join(arguments)})"


def _normalize_expression(expression: str) -> str:
	return re.sub(r"\s+", "", expression.strip())
