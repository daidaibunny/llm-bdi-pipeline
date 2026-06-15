"""
Domain-level lifted plan-library synthesis.

The public entry points in this package build goal-conditioned, reusable
AgentSpeak(L) libraries. They are intentionally separate from the query-specific
DFA pipeline.
"""

from __future__ import annotations

from .clingo_backend import ClingoSelectionResult, ClingoSketchRuleSelector
from .gp_backends import (
	BackendManifest,
	GPBackendRunner,
	SketchCondition,
	SketchEffect,
	SketchFeature,
	SketchPolicy,
	SketchRule,
	discover_backend_manifest,
	parse_dlplan_policy,
)
from .feature_binding import (
	ActionEffectBindingCandidate,
	FeatureBindingReport,
	bind_recoverable_dlplan_features,
	bind_unique_action_effect_candidates,
)
from .models import (
	LiftedCall,
	LiftedPlanRule,
	SketchSynthesisReport,
)
from .schema_synthesis import (
	build_goal_conditioned_library_from_pddl,
	goal_facts_from_problem,
)
from .sketch_asl_compiler import (
	SketchCompilationTarget,
	SketchFeatureBinding,
	compile_bound_sketch_to_asl_library,
)

__all__ = [
	"LiftedCall",
	"LiftedPlanRule",
	"ClingoSelectionResult",
	"ClingoSketchRuleSelector",
	"ActionEffectBindingCandidate",
	"FeatureBindingReport",
	"BackendManifest",
	"GPBackendRunner",
	"SketchCondition",
	"SketchCompilationTarget",
	"SketchEffect",
	"SketchFeature",
	"SketchFeatureBinding",
	"SketchPolicy",
	"SketchRule",
	"SketchSynthesisReport",
	"build_goal_conditioned_library_from_pddl",
	"bind_recoverable_dlplan_features",
	"bind_unique_action_effect_candidates",
	"compile_bound_sketch_to_asl_library",
	"discover_backend_manifest",
	"goal_facts_from_problem",
	"parse_dlplan_policy",
]
