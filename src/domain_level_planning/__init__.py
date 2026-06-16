"""
Domain-level lifted plan-library synthesis.

The public entry points in this package build goal-conditioned, reusable
AgentSpeak(L) libraries. They are intentionally separate from the query-specific
DFA pipeline.
"""

from __future__ import annotations

from .clingo_backend import (
	ClingoRequiredRuleGroup,
	ClingoSelectionResult,
	ClingoSketchRuleSelector,
)
from .architecture_contract import (
	ArchitectureContract,
	ArchitectureDecision,
	ArchitectureGap,
	HypothesisClassContract,
	architecture_gap_summary,
	bounded_hypothesis_class_contract,
	domain_level_architecture_contract,
)
from .gp_backends import (
	BackendManifest,
	GPBackendRunner,
	LearnerSketchesRunConfig,
	LearnerSketchesRunResult,
	SketchCondition,
	SketchEffect,
	SketchFeature,
	SketchPolicy,
	SketchRule,
	backend_audit_matrix,
	discover_learner_sketches_policy_file,
	discover_backend_manifest,
	parse_dlplan_policy,
	run_learner_sketches,
)
from .feature_binding import (
	ActionEffectBindingCandidate,
	FeatureBindingReport,
	bind_goal_aligned_action_effect_candidates,
	bind_recoverable_dlplan_features,
	bind_unique_action_effect_candidates,
)
from .dfa_adapter import (
	DFAAchievementRequest,
	adapt_dfa_guard_to_achievement_request,
	adapt_dfa_guarded_transition_to_achievement_request,
)
from .experiments import run_domain_level_experiment
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
from .library_contract import (
	DomainLevelLibraryContractReport,
	audit_domain_level_library_contract,
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
	RefinementConstraint,
	RefinementRoundReport,
	classify_heldout_failure_for_refinement,
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
	"ArchitectureContract",
	"ArchitectureDecision",
	"ArchitectureGap",
	"HypothesisClassContract",
	"ClingoRequiredRuleGroup",
	"ClingoSelectionResult",
	"ClingoSketchRuleSelector",
	"ActionEffectBindingCandidate",
	"DFAAchievementRequest",
	"FeatureBindingReport",
	"BackendManifest",
	"ExternalSketchPolicySource",
	"GPBackendRunner",
	"LearnerSketchesRunConfig",
	"LearnerSketchesRunResult",
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
	"DomainLevelLibraryContractReport",
	"BoundedLibraryValidationReport",
	"BoundedProblemValidation",
	"LibraryCounterexample",
	"PDDLSupportReport",
	"CounterexampleGuidedSynthesisResult",
	"HeldoutProblemEvaluation",
	"RefinementConstraint",
	"RefinementRoundReport",
	"build_goal_conditioned_library_from_pddl",
	"build_schema_only_goal_conditioned_library_from_pddl",
	"bind_goal_aligned_action_effect_candidates",
	"bind_recoverable_dlplan_features",
	"bind_unique_action_effect_candidates",
	"compile_bound_sketch_to_asl_library",
	"compile_learner_sketch_policy_to_asl",
	"classify_heldout_failure_for_refinement",
	"backend_audit_matrix",
	"discover_learner_sketches_policy_file",
	"discover_backend_manifest",
	"goal_facts_from_problem",
	"assert_compilable_pddl_files",
	"audit_learned_policy_for_asl_binding",
	"audit_domain_level_library_contract",
	"architecture_gap_summary",
	"bounded_hypothesis_class_contract",
	"domain_level_architecture_contract",
	"adapt_dfa_guard_to_achievement_request",
	"adapt_dfa_guarded_transition_to_achievement_request",
	"inspect_pddl_support",
	"parse_dlplan_policy",
	"run_learner_sketches",
	"run_domain_level_experiment",
	"synthesize_domain_level_asl_library",
	"synthesize_with_counterexample_refinement",
	"validate_library_on_bounded_transition_systems",
]
