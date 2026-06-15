"""
Compile externally learned policy sketches into lifted AgentSpeak(L) skeletons.

External sketch learners output qualitative feature progress rules. A separate
binding layer must say how each feature condition/effect corresponds to PDDL
state literals, read-only goal facts, primitive actions, or predicate subgoals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from plan_library.models import (
	AgentSpeakBodyStep,
	AgentSpeakPlan,
	AgentSpeakTrigger,
	PlanLibrary,
)

from .gp_backends import SketchPolicy


@dataclass(frozen=True)
class SketchFeatureBinding:
	"""ASL-level interpretation of one learned sketch feature."""

	condition_contexts: Mapping[str, tuple[str, ...]]
	effect_body: Mapping[str, tuple[AgentSpeakBodyStep, ...]]
	effect_contexts: Mapping[str, tuple[str, ...]] | None = None


@dataclass(frozen=True)
class SketchCompilationTarget:
	"""AgentSpeak trigger and recursive call used for one sketch compilation."""

	symbol: str = "g"
	arguments: tuple[str, ...] = ()
	recurse: bool = True


def compile_bound_sketch_to_asl_library(
	*,
	domain_name: str,
	policy: SketchPolicy,
	feature_bindings: Mapping[str, SketchFeatureBinding],
	target: SketchCompilationTarget | None = None,
	top_level_goal: str | None = None,
) -> PlanLibrary:
	"""Compile a bound qualitative sketch into a lifted AgentSpeak(L) library.

	The compiler is intentionally conservative: every feature condition and
	effect must have an explicit binding. This prevents abstract DLPlan feature
	progress from being silently turned into synthetic `achieve_*` plans.
	"""

	compilation_target = _compilation_target(target, top_level_goal)
	plans: list[AgentSpeakPlan] = []
	for rule_index, rule in enumerate(policy.parsed_rules, start=1):
		context: list[str] = []
		body: list[AgentSpeakBodyStep] = []
		for condition in rule.conditions:
			context.extend(
				_lookup_condition_context(
					feature_bindings,
					condition.feature_id,
					condition.operator,
				),
			)
		for effect in rule.effects:
			context.extend(
				_lookup_effect_context(
					feature_bindings,
					effect.feature_id,
					effect.operator,
				),
			)
			body.extend(
				_lookup_effect_body(
					feature_bindings,
					effect.feature_id,
					effect.operator,
				),
			)
		if rule.effects and not body:
			raise ValueError(
				f"Sketch rule {rule_index} does not provide an executable ASL body "
				f"after feature binding: {rule.raw}",
			)
		if compilation_target.recurse:
			body.append(
				AgentSpeakBodyStep(
					"subgoal",
					compilation_target.symbol,
					compilation_target.arguments,
				),
			)
		plans.append(
			AgentSpeakPlan(
				plan_name=f"sketch_rule_{rule_index}",
				trigger=AgentSpeakTrigger(
					event_type="achievement_goal",
					symbol=compilation_target.symbol,
					arguments=compilation_target.arguments,
				),
				context=tuple(dict.fromkeys(context)),
				body=tuple(body),
				binding_certificate=(
					{
						"synthesis_family": "external_policy_sketch_binding",
						"source_rule": rule.raw,
					},
				),
			),
		)
	return PlanLibrary(
		domain_name=domain_name,
		plans=tuple(plans),
		metadata={
			"generation_mode": "bound_external_policy_sketch",
			"feature_count": len(policy.features),
			"rule_count": len(policy.parsed_rules),
			"target": {
				"symbol": compilation_target.symbol,
				"arguments": list(compilation_target.arguments),
				"recurse": compilation_target.recurse,
			},
			"requires_feature_bindings": True,
		},
	)


def _compilation_target(
	target: SketchCompilationTarget | None,
	top_level_goal: str | None,
) -> SketchCompilationTarget:
	if target is not None and top_level_goal is not None:
		raise ValueError("Pass either target or top_level_goal, not both.")
	if target is not None:
		return target
	if top_level_goal is not None:
		return SketchCompilationTarget(symbol=top_level_goal)
	return SketchCompilationTarget()


def _lookup_condition_context(
	feature_bindings: Mapping[str, SketchFeatureBinding],
	feature_id: str,
	operator: str,
) -> Sequence[str]:
	binding = _feature_binding(feature_bindings, feature_id)
	try:
		return binding.condition_contexts[operator]
	except KeyError as error:
		raise ValueError(
			f"No ASL context binding for condition operator {operator!r} "
			f"on sketch feature {feature_id!r}.",
		) from error


def _lookup_effect_body(
	feature_bindings: Mapping[str, SketchFeatureBinding],
	feature_id: str,
	operator: str,
) -> Sequence[AgentSpeakBodyStep]:
	binding = _feature_binding(feature_bindings, feature_id)
	try:
		return binding.effect_body[operator]
	except KeyError as error:
		raise ValueError(
			f"No ASL body binding for effect operator {operator!r} "
			f"on sketch feature {feature_id!r}.",
		) from error


def _lookup_effect_context(
	feature_bindings: Mapping[str, SketchFeatureBinding],
	feature_id: str,
	operator: str,
) -> Sequence[str]:
	binding = _feature_binding(feature_bindings, feature_id)
	if binding.effect_contexts is None:
		return ()
	return binding.effect_contexts.get(operator, ())


def _feature_binding(
	feature_bindings: Mapping[str, SketchFeatureBinding],
	feature_id: str,
) -> SketchFeatureBinding:
	try:
		return feature_bindings[feature_id]
	except KeyError as error:
		raise ValueError(f"No ASL binding for sketch feature {feature_id!r}.") from error
