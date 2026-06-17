"""
Audit learned generalized-planning policies before ASL synthesis.

The goal is to separate a paper backend's learned sketch from the additional
binding work required to turn that sketch into executable lifted AgentSpeak(L).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from utils.pddl_parser import PDDLDomain

from .feature_binding import bind_goal_aligned_action_effect_candidates
from .feature_binding import bind_recoverable_dlplan_features
from .feature_binding import bind_unique_action_effect_candidates
from .feature_binding import FeatureBindingDiagnostic
from .feature_binding import FeatureBindingReport
from .gp_backends import SketchPolicy
from .gp_backends import parse_dlplan_policy


@dataclass(frozen=True)
class PaperPolicyAuditReport:
	"""Binding-readiness report for one learned paper-backend policy."""

	source_name: str
	policy_file: str
	feature_count: int
	rule_count: int
	bound_feature_count: int
	unsupported_features: Mapping[str, str]
	action_effect_candidate_count: int
	executable_effect_count: int
	ready_for_executable_asl: bool
	feature_binding_diagnostics: tuple[FeatureBindingDiagnostic, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"source_name": self.source_name,
			"policy_file": self.policy_file,
			"feature_count": self.feature_count,
			"rule_count": self.rule_count,
			"bound_feature_count": self.bound_feature_count,
			"unsupported_features": dict(self.unsupported_features),
			"action_effect_candidate_count": self.action_effect_candidate_count,
			"executable_effect_count": self.executable_effect_count,
			"ready_for_executable_asl": self.ready_for_executable_asl,
			"feature_binding_diagnostics": tuple(
				diagnostic.to_dict()
				for diagnostic in self.feature_binding_diagnostics
			),
		}


def audit_learned_policy_for_asl_binding(
	*,
	source_name: str,
	policy_file: str | Path,
	domain: PDDLDomain,
) -> tuple[PaperPolicyAuditReport, SketchPolicy, FeatureBindingReport]:
	"""Parse and bind one learned DLPlan policy artifact."""

	path = Path(policy_file)
	policy = parse_dlplan_policy(path.read_text(encoding="utf-8"))
	binding_report = bind_goal_aligned_action_effect_candidates(
		policy=policy,
		report=bind_unique_action_effect_candidates(
			bind_recoverable_dlplan_features(policy=policy, domain=domain),
		),
	)
	executable_effect_count = sum(
		len(binding.effect_body)
		for binding in binding_report.bindings.values()
	)
	action_candidate_count = sum(
		len(candidates)
		for candidates in binding_report.action_effect_candidates.values()
	)
	report = PaperPolicyAuditReport(
		source_name=source_name,
		policy_file=str(path),
		feature_count=len(policy.features),
		rule_count=len(policy.parsed_rules),
		bound_feature_count=len(binding_report.bindings),
		unsupported_features=binding_report.unsupported_features,
		action_effect_candidate_count=action_candidate_count,
		executable_effect_count=executable_effect_count,
		ready_for_executable_asl=_policy_rules_are_executable(
			policy=policy,
			bindings=binding_report.bindings,
		),
		feature_binding_diagnostics=tuple(
			binding_report.feature_diagnostics[feature_id]
			for feature_id in policy.features
		),
	)
	return report, policy, binding_report


def _policy_rules_are_executable(
	*,
	policy: SketchPolicy,
	bindings: Mapping[str, object],
) -> bool:
	rules = tuple(policy.parsed_rules or ())
	if not rules:
		return False
	for rule in rules:
		body_step_count = 0
		for condition in rule.conditions:
			binding = bindings.get(condition.feature_id)
			if binding is None or condition.operator not in binding.condition_contexts:
				return False
		for effect in rule.effects:
			binding = bindings.get(effect.feature_id)
			if binding is None or effect.operator not in binding.effect_body:
				return False
			body_step_count += len(binding.effect_body[effect.operator])
		if body_step_count == 0:
			return False
	return True
