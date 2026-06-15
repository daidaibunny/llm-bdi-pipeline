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
	action_name: str
	context: tuple[str, ...]
	body: tuple[AgentSpeakBodyStep, ...]


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
		for effect in parse_pddl_literals(action.effects):
			if effect.predicate != predicate:
				continue
			if effect.is_positive:
				continue
			candidates.append(
				ActionEffectBindingCandidate(
					feature_id=feature_id,
					operator="e_n_dec",
					action_name=action.name,
					context=preconditions,
					body=(AgentSpeakBodyStep("primitive_action", action.name, action_arguments),),
				),
			)
	return tuple(candidates)


def _primitive_count_predicate(expression: str) -> str | None:
	match = re.fullmatch(
		r"n_count\(c_primitive\(([^(),]+),0\)\)",
		_normalize_expression(expression),
	)
	return match.group(1) if match else None


def _arguments_for_arity(arity: int) -> tuple[str, ...]:
	return tuple(parameter_variables(tuple(f"?x{index}" for index in range(arity))))


def _call(predicate: str, arguments: tuple[str, ...]) -> str:
	return predicate if not arguments else f"{predicate}({', '.join(arguments)})"


def _normalize_expression(expression: str) -> str:
	return re.sub(r"\s+", "", expression.strip())
