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
from .atomic_backend_selector import (
	AtomicGoalTemplate,
	AtomicTemplateBackendDecision,
	select_atomic_template_backend,
)
from .gp_backends import (
	BackendManifest,
	GPBackendRunner,
	LearningGeneralPoliciesRunConfig,
	LearningGeneralPoliciesRunResult,
	LearnerSketchesRunConfig,
	LearnerSketchesRunResult,
	SketchCondition,
	SketchEffect,
	SketchFeature,
	SketchPolicy,
	SketchRule,
	backend_audit_matrix,
	backend_consumption_role,
	discover_learner_sketches_policy_file,
	discover_learning_general_policies_policy_file,
	discover_backend_manifest,
	parse_d2l_policy,
	parse_dlplan_policy,
	run_learning_general_policies,
	run_learner_sketches,
)
from .feature_binding import (
	ActionEffectBindingCandidate,
	FeatureBindingDiagnostic,
	FeatureBindingReport,
	bind_goal_aligned_action_effect_candidates,
	bind_recoverable_dlplan_features,
	bind_unique_action_effect_candidates,
	goal_distance_policy_feature_ids,
)
from .dfa_adapter import (
	DFAAchievementRequest,
	DFAGuardAdaptationDiagnostic,
	adapt_dfa_guard_to_achievement_request,
	adapt_dfa_guarded_transition_to_achievement_request,
	inspect_dfa_guard_to_achievement_request,
)
from .dfa_controller import (
	DFARunExecutionResult,
	DFAProgressExecutionResult,
	execute_dfa_until_accepting,
	execute_dfa_progress_step,
	inspect_progress_requests_from_dfa_state,
	progress_requests_from_dfa_state,
	progress_transitions_from_dfa_state,
)
from .experiments import run_domain_level_experiment
from .models import (
	LiftedCall,
	LiftedPlanRule,
	SketchSynthesisReport,
)
from .moose_policy_adapter import (
	MooseAtom,
	MooseReadableRule,
	compile_moose_readable_policy_to_asl_library,
	load_moose_readable_policy,
	parse_moose_readable_policy,
	policy_program_from_moose_readable_policy,
)
from .paper_backend_audit import (
	PaperPolicyAuditReport,
	audit_learned_policy_for_asl_binding,
)
from .policy_program import (
	LearnedPolicyRule,
	LiftedPolicyProgram,
	PolicyFeature,
	PolicyModule,
	policy_program_from_lifted_rules,
	policy_program_from_sketch_policy,
)
from .library_synthesis import (
	ExternalBackendSourceGateReport,
	ExternalSketchPolicySource,
	UnifiedSynthesisResult,
	synthesize_domain_level_asl_library,
)
from .lifted_ltlf_goal_schema import (
	LTLfAtomSpec,
	LiftedLTLfGoalCase,
	LiftedLTLfGoalDataset,
	load_lifted_ltlf_goal_dataset,
	parse_lifted_ltlf_goal_dataset,
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
from .temporal_goal_pipeline import (
	DomainLevelTemporalArtifact,
	build_domain_level_temporal_artifact,
	persist_domain_level_temporal_artifact,
)
from .temporal_goal_appender import (
	SingletonLiteralDFADiagnostic,
	append_lifted_temporal_goal_case_to_library,
	append_temporal_goal_to_library,
	validate_singleton_literal_dfa,
)

__all__ = [
	"LiftedCall",
	"LiftedPlanRule",
	"ArchitectureContract",
	"ArchitectureDecision",
	"ArchitectureGap",
	"HypothesisClassContract",
	"AtomicGoalTemplate",
	"AtomicTemplateBackendDecision",
	"ClingoRequiredRuleGroup",
	"ClingoSelectionResult",
	"ClingoSketchRuleSelector",
	"ActionEffectBindingCandidate",
	"DFAAchievementRequest",
	"DFAGuardAdaptationDiagnostic",
	"DFAProgressExecutionResult",
	"DFARunExecutionResult",
	"FeatureBindingDiagnostic",
	"FeatureBindingReport",
	"BackendManifest",
	"ExternalSketchPolicySource",
	"GPBackendRunner",
	"LearningGeneralPoliciesRunConfig",
	"LearningGeneralPoliciesRunResult",
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
	"LiftedPolicyProgram",
	"LearnedPolicyRule",
	"MooseAtom",
	"MooseReadableRule",
	"PolicyFeature",
	"PolicyModule",
	"UnifiedSynthesisResult",
	"LTLfAtomSpec",
	"LiftedLTLfGoalCase",
	"LiftedLTLfGoalDataset",
	"DomainLevelLibraryContractReport",
	"DomainLevelTemporalArtifact",
	"SingletonLiteralDFADiagnostic",
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
	"goal_distance_policy_feature_ids",
	"build_domain_level_temporal_artifact",
	"append_lifted_temporal_goal_case_to_library",
	"append_temporal_goal_to_library",
	"validate_singleton_literal_dfa",
	"compile_bound_sketch_to_asl_library",
	"compile_moose_readable_policy_to_asl_library",
	"compile_learner_sketch_policy_to_asl",
	"classify_heldout_failure_for_refinement",
	"backend_audit_matrix",
	"discover_learner_sketches_policy_file",
	"discover_learning_general_policies_policy_file",
	"discover_backend_manifest",
	"goal_facts_from_problem",
	"assert_compilable_pddl_files",
	"audit_learned_policy_for_asl_binding",
	"audit_domain_level_library_contract",
	"architecture_gap_summary",
	"select_atomic_template_backend",
	"bounded_hypothesis_class_contract",
	"domain_level_architecture_contract",
	"adapt_dfa_guard_to_achievement_request",
	"adapt_dfa_guarded_transition_to_achievement_request",
	"inspect_dfa_guard_to_achievement_request",
	"execute_dfa_progress_step",
	"execute_dfa_until_accepting",
	"inspect_progress_requests_from_dfa_state",
	"inspect_pddl_support",
	"parse_dlplan_policy",
	"persist_domain_level_temporal_artifact",
	"policy_program_from_lifted_rules",
	"policy_program_from_sketch_policy",
	"progress_requests_from_dfa_state",
	"progress_transitions_from_dfa_state",
	"run_learning_general_policies",
	"run_learner_sketches",
	"run_domain_level_experiment",
	"synthesize_domain_level_asl_library",
	"load_lifted_ltlf_goal_dataset",
	"load_moose_readable_policy",
	"parse_moose_readable_policy",
	"parse_lifted_ltlf_goal_dataset",
	"policy_program_from_moose_readable_policy",
	"synthesize_with_counterexample_refinement",
	"validate_library_on_bounded_transition_systems",
]
