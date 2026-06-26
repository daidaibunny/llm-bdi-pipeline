"""
Audit learned generalized-planning policies before ASL synthesis.

The goal is to separate a paper backend's learned sketch from the additional
binding work required to turn that sketch into executable lifted AgentSpeak(L).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Mapping

from utils.pddl_parser import PDDLDomain

from .feature_binding import bind_goal_aligned_action_effect_candidates
from .feature_binding import bind_recoverable_dlplan_features
from .feature_binding import bind_unique_action_effect_candidates
from .feature_binding import FeatureBindingDiagnostic
from .feature_binding import FeatureBindingReport
from .feature_binding import goal_aligned_policy_feature_ids
from .gp_backends import SketchPolicy
from .gp_backends import parse_d2l_policy
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
	vocabulary_adapter: Mapping[str, str] = field(default_factory=dict)
	backend_name: str = "learner-sketches"
	policy_dialect: str = "dlplan_policy"
	parse_diagnostics: tuple[Mapping[str, str], ...] = ()

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
			"vocabulary_adapter": dict(self.vocabulary_adapter),
			"backend_name": self.backend_name,
			"policy_dialect": self.policy_dialect,
			"parse_diagnostics": self.parse_diagnostics,
		}


def audit_learned_policy_for_asl_binding(
	*,
	source_name: str,
	policy_file: str | Path,
	domain: PDDLDomain,
	backend_name: str = "learner-sketches",
	vocabulary_map: Mapping[str, str] | None = None,
) -> tuple[PaperPolicyAuditReport, SketchPolicy, FeatureBindingReport]:
	"""Parse and bind one learned DLPlan policy artifact."""

	path = Path(policy_file)
	adapter = _validated_vocabulary_map(
		domain=domain,
		vocabulary_map=dict(vocabulary_map or {}),
	)
	policy_text = _apply_predicate_vocabulary_map(
		path.read_text(encoding="utf-8"),
		adapter,
	)
	policy, policy_dialect, parse_diagnostics = _parse_backend_policy(
		policy_text,
		backend_name=backend_name,
		domain=domain,
	)
	base_report = bind_recoverable_dlplan_features(policy=policy, domain=domain)
	if goal_aligned_policy_feature_ids(policy):
		binding_report = bind_goal_aligned_action_effect_candidates(
			policy=policy,
			report=base_report,
			domain=domain,
		)
	else:
		binding_report = bind_unique_action_effect_candidates(base_report)
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
		vocabulary_adapter=adapter,
		backend_name=backend_name,
		policy_dialect=policy_dialect,
		parse_diagnostics=tuple(
			diagnostic.to_dict()
			for diagnostic in parse_diagnostics
		),
	)
	return report, policy, binding_report


def _parse_backend_policy(
	policy_text: str,
	*,
	backend_name: str,
	domain: PDDLDomain,
) -> tuple[SketchPolicy, str, tuple[object, ...]]:
	normalized = str(backend_name or "").strip()
	if normalized == "d2l" and "(:policy" not in policy_text:
		predicate_arities = {
			predicate.name: len(predicate.parameters)
			for predicate in domain.predicates
		}
		policy, diagnostics = parse_d2l_policy(
			policy_text,
			predicate_arities=predicate_arities,
		)
		return policy, "d2l_text_policy", tuple(diagnostics)
	return parse_dlplan_policy(policy_text), "dlplan_policy", ()


def _validated_vocabulary_map(
	*,
	domain: PDDLDomain,
	vocabulary_map: Mapping[str, str],
) -> Mapping[str, str]:
	"""Validate an explicit external-to-local predicate-name adapter."""

	if not vocabulary_map:
		return {}
	predicate_names = {predicate.name for predicate in domain.predicates}
	adapter: dict[str, str] = {}
	for raw_source, raw_target in vocabulary_map.items():
		source = str(raw_source or "").strip()
		target = str(raw_target or "").strip()
		if not source or not target:
			raise ValueError("Vocabulary adapter entries must use non-empty names.")
		if source.endswith("_g") or target.endswith("_g"):
			raise ValueError(
				"Vocabulary adapter entries must map base predicate names; "
				"goal-suffixed names are derived automatically.",
			)
		if target not in predicate_names:
			raise ValueError(
				f"Vocabulary adapter for source predicate {source!r} does not "
				f"declare target predicate {target!r} in the PDDL domain.",
			)
		adapter[source] = target
	return adapter


def _apply_predicate_vocabulary_map(
	text: str,
	vocabulary_map: Mapping[str, str],
) -> str:
	"""Apply an explicit predicate-name adapter to a DLPlan policy text."""

	rewritten = text
	for source, target in sorted(
		vocabulary_map.items(),
		key=lambda item: len(item[0]),
		reverse=True,
	):
		pattern = re.compile(
			rf"(?<![A-Za-z0-9_-]){re.escape(source)}(?P<suffix>_g)?"
			r"(?![A-Za-z0-9_-])",
		)
		rewritten = pattern.sub(
			lambda match: f"{target}{match.group('suffix') or ''}",
			rewritten,
		)
	return rewritten


def _policy_rules_are_executable(
	*,
	policy: SketchPolicy,
	bindings: Mapping[str, object],
) -> bool:
	rules = tuple(policy.parsed_rules or ())
	if not rules:
		return False
	for rule in rules:
		context: list[str] = []
		body_variables: list[str] = []
		body_step_count = 0
		for condition in rule.conditions:
			binding = bindings.get(condition.feature_id)
			if binding is None or condition.operator not in binding.condition_contexts:
				return False
			context.extend(binding.condition_contexts[condition.operator])
		for effect in rule.effects:
			binding = bindings.get(effect.feature_id)
			if binding is None or effect.operator not in binding.effect_body:
				return False
			context.extend((binding.effect_contexts or {}).get(effect.operator, ()))
			for step in binding.effect_body[effect.operator]:
				body_variables.extend(
					argument
					for argument in tuple(step.arguments or ())
					if _is_lifted_variable(argument)
				)
			body_step_count += len(binding.effect_body[effect.operator])
		if body_step_count == 0:
			return False
		if any(
			variable not in _positive_context_variables(context)
			for variable in tuple(dict.fromkeys(body_variables))
		):
			return False
	return True


def _positive_context_variables(context: list[str]) -> tuple[str, ...]:
	variables: list[str] = []
	for literal in tuple(context or ()):
		text = str(literal or "").strip()
		if text.lower().startswith("not "):
			continue
		for argument in _context_arguments(text):
			if _is_lifted_variable(argument):
				variables.append(argument)
	return tuple(dict.fromkeys(variables))


def _context_arguments(context_literal: str) -> tuple[str, ...]:
	text = str(context_literal or "").strip()
	if "(" not in text or not text.endswith(")"):
		return ()
	_, raw_arguments = text.split("(", 1)
	return tuple(
		argument.strip()
		for argument in raw_arguments[:-1].split(",")
		if argument.strip()
	)


def _is_lifted_variable(argument: str) -> bool:
	text = str(argument or "").strip()
	return bool(text) and bool(re.match(r"^[A-Z]", text))
