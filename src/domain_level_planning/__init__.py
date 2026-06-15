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
	bind_goal_aligned_action_effect_candidates,
	bind_recoverable_dlplan_features,
	bind_unique_action_effect_candidates,
)
from .models import (
	LiftedCall,
	LiftedPlanRule,
	SketchSynthesisReport,
)
from .paper_backend_audit import (
	PaperPolicyAuditReport,
	audit_learned_policy_for_asl_binding,
)
from .library_synthesis import (
	ExternalSketchPolicySource,
	UnifiedSynthesisResult,
	synthesize_domain_level_asl_library,
)
from .library_verifier import (
	BoundedLibraryValidationReport,
	BoundedProblemValidation,
	LibraryCounterexample,
	validate_library_on_bounded_transition_systems,
)
from .pddl_support import (
	PDDLSupportReport,
	assert_compilable_pddl_files,
	inspect_pddl_support,
)
from .refinement import (
	CounterexampleGuidedSynthesisResult,
	HeldoutProblemEvaluation,
	RefinementRoundReport,
	synthesize_with_counterexample_refinement,
)
from .schema_synthesis import (
	build_goal_conditioned_library_from_pddl,
	build_schema_only_goal_conditioned_library_from_pddl,
	goal_facts_from_problem,
)
from .sketch_pipeline import (
	SketchPipelineResult,
	compile_learner_sketch_policy_to_asl,
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
	"ExternalSketchPolicySource",
	"GPBackendRunner",
	"SketchCondition",
	"SketchCompilationTarget",
	"SketchEffect",
	"SketchFeature",
	"SketchFeatureBinding",
	"SketchPolicy",
	"SketchPipelineResult",
	"SketchRule",
	"SketchSynthesisReport",
	"PaperPolicyAuditReport",
	"UnifiedSynthesisResult",
	"BoundedLibraryValidationReport",
	"BoundedProblemValidation",
	"LibraryCounterexample",
	"PDDLSupportReport",
	"CounterexampleGuidedSynthesisResult",
	"HeldoutProblemEvaluation",
	"RefinementRoundReport",
	"build_goal_conditioned_library_from_pddl",
	"build_schema_only_goal_conditioned_library_from_pddl",
	"bind_goal_aligned_action_effect_candidates",
	"bind_recoverable_dlplan_features",
	"bind_unique_action_effect_candidates",
	"compile_bound_sketch_to_asl_library",
	"compile_learner_sketch_policy_to_asl",
	"discover_backend_manifest",
	"goal_facts_from_problem",
	"assert_compilable_pddl_files",
	"audit_learned_policy_for_asl_binding",
	"inspect_pddl_support",
	"parse_dlplan_policy",
	"synthesize_domain_level_asl_library",
	"synthesize_with_counterexample_refinement",
	"validate_library_on_bounded_transition_systems",
]
