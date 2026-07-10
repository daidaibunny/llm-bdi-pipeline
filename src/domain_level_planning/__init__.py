"""
Current domain-level planning exports.

The package exposes only the atomic-template backend path and the lifted
LTLf/DFA temporal append path. Legacy in-repository generalized-planning
synthesis and conjunctive-goal ordering APIs are not part of this package.
"""

from __future__ import annotations

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
from .atomic_module_synthesis import (
	AtomicModuleSynthesisReport,
	synthesize_atomic_minimal_literal_module_library,
)
from .benchmark_registry import (
	AchievementBenchmarkRegistry,
	BenchmarkRecord,
	load_achievement_benchmark_registry,
)
from .dfa_adapter import (
	DFAAchievementRequest,
	DFAGuardAdaptationDiagnostic,
	adapt_dfa_guard_to_achievement_request,
	adapt_dfa_guarded_transition_to_achievement_request,
	inspect_dfa_guard_to_achievement_request,
)
from .dfa_controller import (
	inspect_progress_requests_from_dfa_state,
	progress_requests_from_dfa_state,
	progress_transitions_from_dfa_state,
)
from .evidence_module import (
	AtomicMacroLibraryQualityReport,
	MooseAtomicLibraryQualityReport,
	MooseAtom,
	MooseReadableRule,
	PolicyEvidenceAtom,
	PolicyEvidenceProgram,
	PolicyEvidenceReducerReport,
	PolicyEvidenceRule,
	audit_atomic_macro_library_structure,
	audit_moose_atomic_library_quality,
	compile_policy_evidence_program_to_minimal_module_asl_library,
	compile_moose_readable_policy_to_minimal_module_asl_library,
	compile_moose_readable_policy_to_asl_library,
	evidence_program_from_moose_readable_policy,
	load_moose_readable_policy,
	parse_moose_readable_policy,
	policy_program_from_moose_readable_policy,
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
	discover_backend_manifest,
	discover_learner_sketches_policy_file,
	discover_learning_general_policies_policy_file,
	parse_d2l_policy,
	parse_dlplan_policy,
	run_learning_general_policies,
	run_learner_sketches,
)
from .library_contract import (
	DomainLevelLibraryContractReport,
	audit_domain_level_library_contract,
)
from .lifted_ltlf_goal_schema import (
	LTLfAtomSpec,
	LiftedLTLfGoalCase,
	LiftedLTLfGoalDataset,
	load_lifted_ltlf_goal_dataset,
	parse_lifted_ltlf_goal_dataset,
)
from .policy_program import (
	LearnedPolicyRule,
	LiftedPolicyProgram,
	PolicyFeature,
	PolicyModule,
	policy_program_from_sketch_policy,
)
from .pddl_support import (
	PDDLSupportReport,
	assert_compilable_pddl_files,
	inspect_pddl_support,
)
from .temporal_goal_appender import (
	GuardTransitionDFADiagnostic,
	append_lifted_temporal_goal_case_to_library,
	append_temporal_goal_to_library,
	validate_guard_transition_dfa,
)

__all__ = [
	"AchievementBenchmarkRegistry",
	"ArchitectureContract",
	"ArchitectureDecision",
	"ArchitectureGap",
	"AtomicGoalTemplate",
	"AtomicMacroLibraryQualityReport",
	"AtomicModuleSynthesisReport",
	"AtomicTemplateBackendDecision",
	"BackendManifest",
	"BenchmarkRecord",
	"DFAAchievementRequest",
	"DFAGuardAdaptationDiagnostic",
	"DomainLevelLibraryContractReport",
	"GPBackendRunner",
	"HypothesisClassContract",
	"LTLfAtomSpec",
	"LearnedPolicyRule",
	"LearnerSketchesRunConfig",
	"LearnerSketchesRunResult",
	"LearningGeneralPoliciesRunConfig",
	"LearningGeneralPoliciesRunResult",
	"LiftedLTLfGoalCase",
	"LiftedLTLfGoalDataset",
	"LiftedPolicyProgram",
	"MooseAtom",
	"MooseAtomicLibraryQualityReport",
	"MooseReadableRule",
	"PDDLSupportReport",
	"PolicyFeature",
	"PolicyEvidenceAtom",
	"PolicyEvidenceProgram",
	"PolicyEvidenceReducerReport",
	"PolicyEvidenceRule",
	"PolicyModule",
	"GuardTransitionDFADiagnostic",
	"SketchCondition",
	"SketchEffect",
	"SketchFeature",
	"SketchPolicy",
	"SketchRule",
	"append_lifted_temporal_goal_case_to_library",
	"append_temporal_goal_to_library",
	"adapt_dfa_guard_to_achievement_request",
	"adapt_dfa_guarded_transition_to_achievement_request",
	"architecture_gap_summary",
	"assert_compilable_pddl_files",
	"audit_atomic_macro_library_structure",
	"audit_domain_level_library_contract",
	"audit_moose_atomic_library_quality",
	"backend_audit_matrix",
	"backend_consumption_role",
	"bounded_hypothesis_class_contract",
	"compile_policy_evidence_program_to_minimal_module_asl_library",
	"compile_moose_readable_policy_to_asl_library",
	"compile_moose_readable_policy_to_minimal_module_asl_library",
	"discover_backend_manifest",
	"discover_learner_sketches_policy_file",
	"discover_learning_general_policies_policy_file",
	"domain_level_architecture_contract",
	"evidence_program_from_moose_readable_policy",
	"inspect_dfa_guard_to_achievement_request",
	"inspect_pddl_support",
	"inspect_progress_requests_from_dfa_state",
	"load_achievement_benchmark_registry",
	"load_lifted_ltlf_goal_dataset",
	"load_moose_readable_policy",
	"parse_d2l_policy",
	"parse_dlplan_policy",
	"parse_lifted_ltlf_goal_dataset",
	"parse_moose_readable_policy",
	"policy_program_from_moose_readable_policy",
	"policy_program_from_sketch_policy",
	"progress_requests_from_dfa_state",
	"progress_transitions_from_dfa_state",
	"run_learner_sketches",
	"run_learning_general_policies",
	"select_atomic_template_backend",
	"synthesize_atomic_minimal_literal_module_library",
	"validate_guard_transition_dfa",
]
