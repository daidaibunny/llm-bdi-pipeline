"""
Policy-first intermediate representation for generalized planning backends.

The paper method should learn a lifted policy program before compiling anything
to AgentSpeak(L). This module is the seam between external generalized-planning
learners and the ASL compiler.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .gp_backends import SketchPolicy


@dataclass(frozen=True)
class PolicyFeature:
	"""One abstract state or goal feature selected by a policy learner."""

	identifier: str
	kind: str
	expression: str

	def to_dict(self) -> dict[str, str]:
		return {
			"identifier": self.identifier,
			"kind": self.kind,
			"expression": self.expression,
		}


@dataclass(frozen=True)
class LearnedPolicyRule:
	"""One qualitative policy rule before ASL feature binding."""

	name: str
	conditions: tuple[tuple[str, str], ...]
	effects: tuple[tuple[str, str], ...]
	source_rule: str

	def to_dict(self) -> dict[str, object]:
		return {
			"name": self.name,
			"conditions": [
				{"feature": feature, "operator": operator}
				for feature, operator in self.conditions
			],
			"effects": [
				{"feature": feature, "operator": operator}
				for feature, operator in self.effects
			],
			"source_rule": self.source_rule,
		}


@dataclass(frozen=True)
class PolicyModule:
	"""Named reusable policy region, optionally compiled to ASL plans later."""

	name: str
	parameters: tuple[str, ...]
	rule_names: tuple[str, ...]
	goal_symbol: str | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"name": self.name,
			"parameters": list(self.parameters),
			"rule_names": list(self.rule_names),
			"goal_symbol": self.goal_symbol,
		}


@dataclass(frozen=True)
class LiftedPolicyProgram:
	"""Learned generalized-planning artifact consumed by the ASL compiler."""

	domain_name: str
	backend_name: str
	source_name: str
	representation: str
	features: tuple[PolicyFeature, ...]
	rules: tuple[LearnedPolicyRule, ...]
	modules: tuple[PolicyModule, ...] = ()
	progress_certificate: Mapping[str, object] | None = None
	provenance: Mapping[str, object] | None = None
	is_learned_policy: bool = True

	def to_dict(self) -> dict[str, object]:
		return {
			"domain_name": self.domain_name,
			"backend_name": self.backend_name,
			"source_name": self.source_name,
			"representation": self.representation,
			"is_learned_policy": self.is_learned_policy,
			"features": [feature.to_dict() for feature in self.features],
			"rules": [rule.to_dict() for rule in self.rules],
			"modules": [module.to_dict() for module in self.modules],
			"progress_certificate": dict(self.progress_certificate or {}),
			"provenance": dict(self.provenance or {}),
		}


def policy_program_from_sketch_policy(
	*,
	policy: SketchPolicy,
	domain_name: str,
	source_name: str,
	backend_name: str,
	policy_file: str | Path | None = None,
) -> LiftedPolicyProgram:
	"""Convert a parsed external DLPlan sketch into the policy-first IR."""

	features = tuple(
		PolicyFeature(
			identifier=feature_id,
			kind=_feature_kind(
				feature_id,
				boolean_features=policy.boolean_features,
				numerical_features=policy.numerical_features,
			),
			expression=expression,
		)
		for feature_id, expression in tuple(policy.features.items())
	)
	rules = tuple(
		LearnedPolicyRule(
			name=f"{_safe_name(source_name)}_rule_{index}",
			conditions=tuple(
				(condition.feature_id, condition.operator)
				for condition in tuple(rule.conditions or ())
			),
			effects=tuple(
				(effect.feature_id, effect.operator)
				for effect in tuple(rule.effects or ())
			),
			source_rule=rule.raw,
		)
		for index, rule in enumerate(tuple(policy.parsed_rules or ()), start=1)
	)
	return LiftedPolicyProgram(
		domain_name=domain_name,
		backend_name=backend_name,
		source_name=source_name,
		representation="dlplan_qualitative_policy",
		features=features,
		rules=rules,
		progress_certificate={
			"termination_basis": "external_backend_policy_verification",
			"feature_count": len(features),
			"rule_count": len(rules),
		},
		provenance={
			"paper_basis": _paper_basis_for_backend(backend_name),
			"policy_file": str(policy_file) if policy_file is not None else None,
			"source_backend": backend_name,
		},
	)


def _feature_kind(
	feature_id: str,
	*,
	boolean_features: Mapping[str, str],
	numerical_features: Mapping[str, str],
) -> str:
	if feature_id in boolean_features:
		return "boolean"
	if feature_id in numerical_features:
		return "numerical"
	return "unknown"


def _call(symbol: str, arguments: Sequence[str]) -> str:
	args = tuple(arguments or ())
	if not args:
		return str(symbol)
	return f"{symbol}({', '.join(args)})"


def _paper_basis_for_backend(backend_name: str) -> str:
	if backend_name == "learner-policies-from-examples":
		return (
			"KR 2025 Learning General Policies From Examples; feature-pool "
			"generation, hitting-set-style selection, and structural termination"
		)
	if backend_name == "learner-sketches":
		return "ICAPS 2022 learner-sketches serialized-width policy sketches"
	if backend_name == "h-policy-learner":
		return "hierarchical policy learner / policy reuse generalized planning"
	if backend_name == "d2l":
		return "AAAI 2021 description-logic generalized policy learner"
	return "external generalized-planning backend"


def _safe_name(value: str) -> str:
	return re.sub(r"[^a-zA-Z0-9_]+", "_", str(value or "").strip()).strip("_") or "policy"
