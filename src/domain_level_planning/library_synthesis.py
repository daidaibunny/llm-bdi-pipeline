"""
Unified domain-level synthesis from PDDL, training evidence, and paper policies.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep, AgentSpeakPlan, AgentSpeakTrigger, PlanLibrary
from utils.pddl_parser import PDDLParser

from .clingo_backend import ClingoSketchRuleSelector
from .feature_binding import bind_goal_aligned_action_effect_candidates
from .feature_binding import bind_recoverable_dlplan_features
from .feature_binding import bind_unique_action_effect_candidates
from .gp_backends import parse_dlplan_policy
from .models import LiftedCall, LiftedPlanRule
from .pddl_support import assert_compilable_pddl_files
from .schema_synthesis import _candidate_rules_from_domain
from .schema_synthesis import _required_capabilities
from .schema_synthesis import _training_evidence
from .schema_synthesis import _validate_selected_rules_against_transition_progress


@dataclass(frozen=True)
class ExternalSketchPolicySource:
	"""One learned policy artifact produced by an external paper-code backend."""

	name: str
	policy_file: str | Path


@dataclass(frozen=True)
class UnifiedSynthesisResult:
	"""Unified synthesis output and diagnostics."""

	plan_library: PlanLibrary
	report: Mapping[str, object]
	rejected_external_features: Mapping[str, str]


def synthesize_domain_level_asl_library(
	*,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path] = (),
	external_sketch_policies: Sequence[ExternalSketchPolicySource] = (),
) -> UnifiedSynthesisResult:
	"""Synthesize one lifted domain-level ASL library through the unified path."""

	assert_compilable_pddl_files(
		domain_file=domain_file,
		problem_files=tuple(training_problem_files or ()),
	)
	domain = PDDLParser.parse_domain(domain_file)
	training_goal_facts, transition_evidence = _training_evidence(
		domain=domain,
		problem_files=training_problem_files,
	)
	schema_candidates = _candidate_rules_from_domain(
		domain.predicates,
		domain.actions,
		transition_evidence=transition_evidence,
	)
	external_candidates, rejected_features = _external_sketch_candidates(
		domain=domain,
		sources=external_sketch_policies,
	)
	candidate_rules = _deduplicate_rules(schema_candidates + external_candidates)
	required_capabilities = _required_capabilities(
		predicates=domain.predicates,
		candidate_rules=candidate_rules,
		training_goal_facts=training_goal_facts,
	)
	selection = ClingoSketchRuleSelector().select(
		candidate_rules=candidate_rules,
		required_capabilities=required_capabilities,
	)
	_validate_selected_rules_against_transition_progress(
		selection.rules,
		transition_evidence,
	)
	output_rules = _deduplicate_rules(selection.rules + external_candidates)
	plan_library = PlanLibrary(
		domain_name=domain.name,
		plans=tuple(_compile_rule_to_plan(rule) for rule in output_rules),
		initial_beliefs=(),
		metadata={
			"generation_mode": "unified_goal_conditioned_modular_synthesis",
			"selected_rule_names": list(selection.selected_rule_names),
			"output_rule_names": [rule.name for rule in output_rules],
			"required_capabilities": tuple(required_capabilities),
			"transition_systems": tuple(
				evidence.to_dict()
				for evidence in transition_evidence
			),
		},
	)
	report = {
		"generation_mode": "unified_goal_conditioned_modular_synthesis",
		"theoretical_contract": "bounded_class_guarantee",
		"external_policy_count": len(tuple(external_sketch_policies or ())),
		"schema_candidate_count": len(schema_candidates),
		"external_candidate_count": len(external_candidates),
		"candidate_count": len(candidate_rules),
		"selected_rule_count": len(selection.rules),
		"output_rule_count": len(output_rules),
		"rejected_external_feature_count": len(rejected_features),
		"candidate_sources": _candidate_source_counts(candidate_rules),
		"selection_cost": selection.cost,
	}
	plan_library.metadata["unified_synthesis_report"] = dict(report)
	return UnifiedSynthesisResult(
		plan_library=plan_library,
		report=report,
		rejected_external_features=rejected_features,
	)


def _external_sketch_candidates(
	*,
	domain,
	sources: Sequence[ExternalSketchPolicySource],
) -> tuple[tuple[LiftedPlanRule, ...], dict[str, str]]:
	candidates: list[LiftedPlanRule] = []
	rejected: dict[str, str] = {}
	for source in sources:
		policy = parse_dlplan_policy(Path(source.policy_file).read_text(encoding="utf-8"))
		binding_report = bind_goal_aligned_action_effect_candidates(
			policy=policy,
			report=bind_unique_action_effect_candidates(
				bind_recoverable_dlplan_features(policy=policy, domain=domain),
			),
		)
		for feature_id, expression in binding_report.unsupported_features.items():
			rejected[f"{source.name}:{feature_id}"] = expression
		candidates.extend(
			_rule
			for _rule in _bound_policy_rules_to_candidates(
				source=source,
				policy=policy,
				bindings=binding_report.bindings,
			)
		)
	return tuple(candidates), rejected


def _bound_policy_rules_to_candidates(
	*,
	source: ExternalSketchPolicySource,
	policy,
	bindings,
) -> tuple[LiftedPlanRule, ...]:
	candidates: list[LiftedPlanRule] = []
	for index, rule in enumerate(policy.parsed_rules, start=1):
		context: list[str] = []
		body: list[LiftedCall] = []
		try:
			for condition in rule.conditions:
				context.extend(
					bindings[condition.feature_id].condition_contexts[condition.operator],
				)
			for effect in rule.effects:
				binding = bindings[effect.feature_id]
				context.extend((binding.effect_contexts or {}).get(effect.operator, ()))
				body.extend(
					_body_step_to_lifted_call(step)
					for step in binding.effect_body[effect.operator]
				)
		except KeyError:
			continue
		if not body:
			continue
		candidates.append(
			LiftedPlanRule(
				name=f"external_{_safe_name(source.name)}_{index}",
				head=LiftedCall("subgoal", "g", ()),
				context=tuple(dict.fromkeys(context)),
				body=tuple(body + [LiftedCall("subgoal", "g", ())]),
				layer="composer",
				rationale=f"external_policy:{source.name}",
				capabilities=(f"external_policy_{_safe_name(source.name)}_{index}",),
				cost=3,
			),
		)
	return tuple(candidates)


def _body_step_to_lifted_call(step: AgentSpeakBodyStep) -> LiftedCall:
	kind = "action" if step.kind in {"action", "primitive_action"} else step.kind
	return LiftedCall(kind, step.symbol, step.arguments)


def _deduplicate_rules(rules: Sequence[LiftedPlanRule]) -> tuple[LiftedPlanRule, ...]:
	seen: set[tuple[object, ...]] = set()
	deduplicated: list[LiftedPlanRule] = []
	for rule in rules:
		key = (
			rule.head,
			rule.context,
			rule.body,
			rule.layer,
		)
		if key in seen:
			continue
		seen.add(key)
		deduplicated.append(rule)
	return tuple(deduplicated)


def _candidate_source_counts(rules: Sequence[LiftedPlanRule]) -> dict[str, int]:
	counts: dict[str, int] = {}
	for rule in rules:
		source = (
			"external_sketch"
			if rule.rationale.startswith("external_policy:")
			else "schema"
		)
		counts[source] = counts.get(source, 0) + 1
	return counts


def _compile_rule_to_plan(rule: LiftedPlanRule) -> AgentSpeakPlan:
	return AgentSpeakPlan(
		plan_name=rule.name,
		trigger=AgentSpeakTrigger(
			event_type="achievement_goal",
			symbol=rule.head.symbol,
			arguments=rule.head.arguments,
		),
		context=rule.context,
		body=tuple(
			AgentSpeakBodyStep(step.kind, step.symbol, step.arguments)
			for step in rule.body
		),
		binding_certificate=(
			{
				"layer": rule.layer,
				"synthesis_family": "unified_goal_conditioned_modular_synthesis",
				"rationale": rule.rationale,
			},
		),
	)


def _safe_name(value: str) -> str:
	return "".join(
		character if character.isalnum() else "_"
		for character in str(value or "").strip().lower()
	).strip("_") or "external"
