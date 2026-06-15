"""
End-to-end adapter from external sketch policies to generated AgentSpeak(L).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from plan_library.models import PlanLibrary
from utils.pddl_parser import PDDLParser

from .feature_binding import (
	FeatureBindingReport,
	bind_goal_aligned_action_effect_candidates,
	bind_recoverable_dlplan_features,
	bind_unique_action_effect_candidates,
)
from .gp_backends import parse_dlplan_policy
from .pddl_support import assert_compilable_pddl_files
from .sketch_asl_compiler import SketchCompilationTarget, compile_bound_sketch_to_asl_library


@dataclass(frozen=True)
class SketchPipelineResult:
	"""Compiled sketch plus binding diagnostics."""

	plan_library: PlanLibrary
	binding_report: FeatureBindingReport
	unsupported_features: Mapping[str, str]


def compile_learner_sketch_policy_to_asl(
	*,
	domain_file: str | Path,
	policy_file: str | Path,
	domain_name: str | None = None,
	target: SketchCompilationTarget | None = None,
	require_full_binding: bool = True,
) -> SketchPipelineResult:
	"""Compile one learner-sketches policy file into a conservative ASL library."""

	assert_compilable_pddl_files(domain_file=domain_file)
	domain = PDDLParser.parse_domain(domain_file)
	policy = parse_dlplan_policy(Path(policy_file).read_text(encoding="utf-8"))
	report = bind_goal_aligned_action_effect_candidates(
		policy=policy,
		report=bind_unique_action_effect_candidates(
			bind_recoverable_dlplan_features(policy=policy, domain=domain),
		),
	)
	if require_full_binding and report.unsupported_features:
		raise ValueError(
			"Cannot compile sketch policy with unsupported DLPlan features: "
			+ ", ".join(
				f"{feature_id}={expression}"
				for feature_id, expression in report.unsupported_features.items()
			),
		)
	plan_library = compile_bound_sketch_to_asl_library(
		domain_name=domain_name or domain.name,
		policy=policy,
		feature_bindings=report.bindings,
		target=target,
	)
	return SketchPipelineResult(
		plan_library=plan_library,
		binding_report=report,
		unsupported_features=report.unsupported_features,
	)
