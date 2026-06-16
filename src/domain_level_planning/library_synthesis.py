"""
Unified domain-level synthesis from PDDL, training evidence, and paper policies.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep, AgentSpeakPlan, AgentSpeakTrigger, PlanLibrary
from utils.pddl_parser import PDDLParser

from .architecture_contract import architecture_gap_summary
from .architecture_contract import domain_level_architecture_contract
from .clingo_backend import ClingoRequiredRuleGroup, ClingoSketchRuleSelector
from .gp_backends import BackendManifest, LearnerSketchesRunConfig, LearnerSketchesRunResult
from .gp_backends import backend_audit_matrix
from .gp_backends import run_learner_sketches
from .library_contract import audit_domain_level_library_contract
from .library_verifier import BoundedLibraryValidationReport
from .library_verifier import validate_library_on_bounded_transition_systems
from .models import LiftedCall, LiftedPlanRule
from .paper_backend_audit import PaperPolicyAuditReport
from .paper_backend_audit import audit_learned_policy_for_asl_binding
from .pddl_expression import parameter_variables, parse_pddl_literals
from .pddl_support import assert_compilable_pddl_files
from .schema_synthesis import _candidate_rules_from_domain
from .schema_synthesis import _required_capabilities
from .schema_synthesis import _training_evidence
from .schema_synthesis import _validate_selected_rules_against_transition_progress
from .schema_synthesis import atomic_achievement_justifications
from .schema_synthesis import composer_state_coverage_required_rule_groups
from .schema_synthesis import filter_rules_by_recursion_descent
from .schema_synthesis import recursion_ranking_states_from_problem_files
from .schema_synthesis import transition_progress_required_rule_groups
from .transition_system import anti_unify_training_atomic_achievements


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


@dataclass(frozen=True)
class ExternalRuleBindingReport:
	"""Compilation diagnostics for one learned paper-policy rule."""

	source_name: str
	rule_index: int
	raw_rule: str
	compiled: bool
	missing_condition_bindings: tuple[str, ...] = ()
	missing_effect_bindings: tuple[str, ...] = ()
	empty_body: bool = False

	def to_dict(self) -> dict[str, object]:
		return {
			"source_name": self.source_name,
			"rule_index": self.rule_index,
			"raw_rule": self.raw_rule,
			"compiled": self.compiled,
			"missing_condition_bindings": list(self.missing_condition_bindings),
			"missing_effect_bindings": list(self.missing_effect_bindings),
			"empty_body": self.empty_body,
		}


@dataclass(frozen=True)
class RepairConstraintBindingReport:
	"""Selector binding diagnostics for one refinement repair constraint."""

	constraint_index: int
	constraint_type: str
	matched: bool
	target_predicates: tuple[str, ...]
	precondition_predicates: tuple[str, ...]
	failing_action: str
	required_capabilities: tuple[str, ...]
	rule_names: tuple[str, ...]
	available_capabilities: tuple[str, ...] = ()
	undeclared_predicates: tuple[str, ...] = ()
	rejection_reason: str | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"constraint_index": self.constraint_index,
			"constraint_type": self.constraint_type,
			"matched": self.matched,
			"target_predicates": self.target_predicates,
			"precondition_predicates": self.precondition_predicates,
			"failing_action": self.failing_action,
			"required_capabilities": self.required_capabilities,
			"available_capabilities": self.available_capabilities,
			"rule_names": self.rule_names,
			"undeclared_predicates": self.undeclared_predicates,
			"rejection_reason": self.rejection_reason,
		}


@dataclass(frozen=True)
class GoalOrderingConstraintBindingReport:
	"""Selector binding diagnostics for one explicit goal-ordering constraint."""

	constraint_index: int
	ordering_index: int
	matched: bool
	earlier_goal: str
	later_goal: str
	required_capability: str | None
	rule_names: tuple[str, ...]
	rejection_reason: str | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"constraint_index": self.constraint_index,
			"ordering_index": self.ordering_index,
			"matched": self.matched,
			"earlier_goal": self.earlier_goal,
			"later_goal": self.later_goal,
			"required_capability": self.required_capability,
			"rule_names": self.rule_names,
			"rejection_reason": self.rejection_reason,
		}


@dataclass(frozen=True)
class AtomicProgressConstraintBindingReport:
	"""Selector binding diagnostics for one atomic-progress refinement constraint."""

	constraint_index: int
	constraint_type: str
	matched: bool
	target_predicates: tuple[str, ...]
	required_capabilities: tuple[str, ...]
	rule_names: tuple[str, ...]
	available_capabilities: tuple[str, ...] = ()
	undeclared_predicates: tuple[str, ...] = ()
	wrong_arity_predicates: tuple[str, ...] = ()
	rejection_reason: str | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"constraint_index": self.constraint_index,
			"constraint_type": self.constraint_type,
			"matched": self.matched,
			"target_predicates": self.target_predicates,
			"required_capabilities": self.required_capabilities,
			"available_capabilities": self.available_capabilities,
			"rule_names": self.rule_names,
			"undeclared_predicates": self.undeclared_predicates,
			"wrong_arity_predicates": self.wrong_arity_predicates,
			"rejection_reason": self.rejection_reason,
		}


def synthesize_domain_level_asl_library(
	*,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path] = (),
	counterexample_problem_files: Sequence[str | Path] = (),
	refinement_constraints: Sequence[object] = (),
	external_sketch_policies: Sequence[ExternalSketchPolicySource] = (),
	learner_sketches_backend: BackendManifest | None = None,
	learner_sketches_runs: Sequence[LearnerSketchesRunConfig] = (),
	synthesis_profile: str = "bootstrap",
) -> UnifiedSynthesisResult:
	"""Synthesize one lifted domain-level ASL library through the unified path."""

	profile = _normalize_synthesis_profile(synthesis_profile)
	training_problem_files = tuple(training_problem_files or ())
	counterexample_problem_files = tuple(counterexample_problem_files or ())
	pddl_support = assert_compilable_pddl_files(
		domain_file=domain_file,
		problem_files=tuple(
			dict.fromkeys((*training_problem_files, *counterexample_problem_files)),
		),
	)
	domain = PDDLParser.parse_domain(domain_file)
	training_goal_facts, transition_evidence = _training_evidence(
		domain=domain,
		problem_files=training_problem_files,
	)
	counterexample_goal_facts, counterexample_transition_evidence = _training_evidence(
		domain=domain,
		problem_files=counterexample_problem_files,
	)
	all_goal_facts = (*training_goal_facts, *counterexample_goal_facts)
	all_transition_evidence = (
		*transition_evidence,
		*counterexample_transition_evidence,
	)
	schema_candidates = _candidate_rules_from_domain(
		domain.predicates,
		domain.actions,
		transition_evidence=all_transition_evidence,
	)
	backend_run_results, learned_sources = _run_requested_learner_sketches(
		backend=learner_sketches_backend,
		run_configs=learner_sketches_runs,
	)
	all_external_sketch_policies = tuple(
		(
			*tuple(external_sketch_policies or ()),
			*learned_sources,
		),
	)
	external_candidates, rejected_features, paper_policy_audits, external_rule_reports = (
		_external_sketch_candidates(
			domain=domain,
			sources=all_external_sketch_policies,
		)
	)
	repair_synthesized_candidates = _repair_synthesized_candidate_rules(
		actions=domain.actions,
		predicates=domain.predicates,
		refinement_constraints=refinement_constraints,
	)
	explicit_goal_ordering_candidates = _explicit_goal_ordering_candidate_rules(
		predicates=domain.predicates,
		refinement_constraints=refinement_constraints,
	)
	raw_candidate_rules = _deduplicate_rules(
		schema_candidates
		+ external_candidates
		+ repair_synthesized_candidates
		+ explicit_goal_ordering_candidates,
	)
	candidate_rules, recursion_descent_audit = filter_rules_by_recursion_descent(
		raw_candidate_rules,
		ranking_states=recursion_ranking_states_from_problem_files(
			domain=domain,
			problem_files=tuple(
				dict.fromkeys((*training_problem_files, *counterexample_problem_files)),
			),
		),
	)
	required_capabilities = _required_capabilities(
		predicates=domain.predicates,
		candidate_rules=candidate_rules,
		training_goal_facts=all_goal_facts,
	)
	if profile == "paper":
		required_capabilities = tuple(
			dict.fromkeys(
				(
					*required_capabilities,
					*_external_rule_capabilities(external_candidates),
				),
			),
		)
	training_progress_rule_groups = transition_progress_required_rule_groups(
		candidate_rules,
		transition_evidence,
	)
	counterexample_progress_rule_groups = transition_progress_required_rule_groups(
		candidate_rules,
		counterexample_transition_evidence,
	)
	training_state_coverage_rule_groups = composer_state_coverage_required_rule_groups(
		candidate_rules,
		domain=domain,
		problem_files=training_problem_files,
	)
	counterexample_state_coverage_rule_groups = composer_state_coverage_required_rule_groups(
		candidate_rules,
		domain=domain,
		problem_files=counterexample_problem_files,
	)
	repair_rule_groups, repair_binding_reports = _repair_required_rule_groups(
		candidate_rules=candidate_rules,
		predicates=domain.predicates,
		actions=domain.actions,
		refinement_constraints=refinement_constraints,
	)
	goal_ordering_rule_groups, goal_ordering_binding_reports = (
		_goal_ordering_required_rule_groups(
			candidate_rules=candidate_rules,
			predicates=domain.predicates,
			refinement_constraints=refinement_constraints,
		)
	)
	atomic_progress_rule_groups, atomic_progress_binding_reports = (
		_atomic_progress_required_rule_groups(
			candidate_rules=candidate_rules,
			predicates=domain.predicates,
			refinement_constraints=refinement_constraints,
		)
	)
	progress_rule_groups = (
		*training_progress_rule_groups,
		*counterexample_progress_rule_groups,
	)
	state_coverage_rule_groups = (
		*training_state_coverage_rule_groups,
		*counterexample_state_coverage_rule_groups,
	)
	selection = ClingoSketchRuleSelector().select(
		candidate_rules=candidate_rules,
		required_capabilities=required_capabilities,
		required_rule_groups=(
			*progress_rule_groups,
			*state_coverage_rule_groups,
			*repair_rule_groups,
			*goal_ordering_rule_groups,
			*atomic_progress_rule_groups,
		),
	)
	_validate_selected_rules_against_transition_progress(
		selection.rules,
		all_transition_evidence,
	)
	output_rules = _order_output_rules(
		_deduplicate_rules(external_candidates + selection.rules),
	)
	plan_library = PlanLibrary(
		domain_name=domain.name,
		plans=tuple(_compile_rule_to_plan(rule) for rule in output_rules),
		initial_beliefs=(),
		metadata={
			"generation_mode": "unified_goal_conditioned_modular_synthesis",
			"pddl_support": pddl_support.to_dict(),
			"selected_rule_names": list(selection.selected_rule_names),
			"output_rule_names": [rule.name for rule in output_rules],
			"required_capabilities": tuple(required_capabilities),
			"transition_systems": tuple(
				evidence.to_dict()
				for evidence in all_transition_evidence
			),
			"training_transition_systems": tuple(
				evidence.to_dict()
				for evidence in transition_evidence
			),
			"counterexample_transition_systems": tuple(
				evidence.to_dict()
				for evidence in counterexample_transition_evidence
			),
		},
	)
	contract_report = audit_domain_level_library_contract(
		plan_library,
		declared_predicates=domain.predicates,
		declared_actions=domain.actions,
	)
	if not contract_report.passed:
		raise ValueError(
			"Generated domain-level library violates the lifted ASL contract: "
			+ "; ".join(contract_report.violations),
		)
	bounded_validation = None
	validation_problem_files = tuple(
		dict.fromkeys((*training_problem_files, *counterexample_problem_files)),
	)
	if validation_problem_files:
		bounded_validation = validate_library_on_bounded_transition_systems(
			plan_library=plan_library,
			domain_file=domain_file,
			problem_files=validation_problem_files,
		)
	paper_profile_failures = _paper_profile_failures(
		training_problem_files=training_problem_files,
		external_sketch_policies=all_external_sketch_policies,
		external_candidates=external_candidates,
		paper_policy_audits=paper_policy_audits,
		external_rule_reports=external_rule_reports,
		repair_binding_reports=repair_binding_reports,
		goal_ordering_binding_reports=goal_ordering_binding_reports,
		atomic_progress_binding_reports=atomic_progress_binding_reports,
		bounded_validation=bounded_validation,
	)
	if profile == "paper" and paper_profile_failures:
		raise ValueError(
			"Paper synthesis profile requirements are not met: "
			+ "; ".join(paper_profile_failures),
		)
	architecture_contract = domain_level_architecture_contract()
	report = {
		"generation_mode": "unified_goal_conditioned_modular_synthesis",
		"synthesis_profile": profile,
		"theoretical_contract": "bounded_class_guarantee",
		"pddl_support": pddl_support.to_dict(),
		"architecture_contract": architecture_contract.to_dict(),
		"architecture_gap_summary": architecture_gap_summary(
			architecture_contract.gaps,
		),
		"paper_quality_checks": (
			"transition_progress",
			"bounded_all_reachable_states",
			"acyclic_high_level_decision_trace",
			"goal_state_fixed_point",
		),
		"domain_level_contract": contract_report.to_dict(),
		"auto_learner_sketches_run_count": len(tuple(learner_sketches_runs or ())),
		"backend_audit_matrix": backend_audit_matrix(),
		"auto_learner_sketches_policy_count": len(learned_sources),
		"auto_learner_sketches_runs": tuple(
			result.to_dict()
			for result in backend_run_results
		),
		"external_policy_count": len(all_external_sketch_policies),
		"manual_external_policy_count": len(tuple(external_sketch_policies or ())),
		"training_problem_count": len(training_problem_files),
		"counterexample_problem_count": len(counterexample_problem_files),
		"schema_candidate_count": len(schema_candidates),
		"external_candidate_count": len(external_candidates),
		"repair_synthesized_candidate_count": len(repair_synthesized_candidates),
		"explicit_goal_ordering_candidate_count": len(
			explicit_goal_ordering_candidates,
		),
		"raw_candidate_count": len(raw_candidate_rules),
		"candidate_count": len(candidate_rules),
		"recursion_descent_audit": recursion_descent_audit,
		"selected_rule_count": len(selection.rules),
		"output_rule_count": len(output_rules),
		"selector_progress_constraint_count": len(progress_rule_groups),
		"selector_training_progress_constraint_count": len(training_progress_rule_groups),
		"selector_counterexample_progress_constraint_count": len(
			counterexample_progress_rule_groups,
		),
		"selector_state_coverage_constraint_count": len(state_coverage_rule_groups),
		"selector_repair_constraint_count": len(repair_rule_groups),
		"selector_atomic_progress_constraint_count": len(atomic_progress_rule_groups),
		"selector_training_state_coverage_constraint_count": len(
			training_state_coverage_rule_groups,
		),
		"selector_counterexample_state_coverage_constraint_count": len(
			counterexample_state_coverage_rule_groups,
		),
		"counterexample_refinement_constraints": _counterexample_refinement_summary(
			counterexample_transition_evidence=counterexample_transition_evidence,
			counterexample_progress_rule_groups=counterexample_progress_rule_groups,
			counterexample_state_coverage_rule_groups=(
				counterexample_state_coverage_rule_groups
			),
			explicit_refinement_constraints=refinement_constraints,
			repair_rule_groups=repair_rule_groups,
			repair_binding_reports=repair_binding_reports,
			goal_ordering_rule_groups=goal_ordering_rule_groups,
			goal_ordering_binding_reports=goal_ordering_binding_reports,
			atomic_progress_rule_groups=atomic_progress_rule_groups,
			atomic_progress_binding_reports=atomic_progress_binding_reports,
		),
		"rejected_external_feature_count": len(rejected_features),
		"candidate_sources": _candidate_source_counts(candidate_rules),
		"selected_candidate_sources": _candidate_source_counts(selection.rules),
		"output_candidate_sources": _candidate_source_counts(output_rules),
		"selection_cost": selection.cost,
		"selected_rule_names": tuple(selection.selected_rule_names),
		"output_rule_names": tuple(rule.name for rule in output_rules),
		"paper_policy_audits": tuple(
			audit.to_dict()
			for audit in paper_policy_audits
		),
		"external_rule_binding_reports": tuple(
			report.to_dict()
			for report in external_rule_reports
		),
		"evidence_matrix": _evidence_matrix(
			schema_candidates=schema_candidates,
			external_candidates=external_candidates,
			repair_synthesized_candidates=repair_synthesized_candidates,
			explicit_goal_ordering_candidates=explicit_goal_ordering_candidates,
			candidate_rules=candidate_rules,
			selected_rules=selection.rules,
			output_rules=output_rules,
			training_transition_evidence=transition_evidence,
			counterexample_transition_evidence=counterexample_transition_evidence,
			training_progress_rule_groups=training_progress_rule_groups,
			counterexample_progress_rule_groups=counterexample_progress_rule_groups,
			training_state_coverage_rule_groups=training_state_coverage_rule_groups,
			counterexample_state_coverage_rule_groups=counterexample_state_coverage_rule_groups,
			paper_policy_audits=paper_policy_audits,
			external_rule_reports=external_rule_reports,
			repair_binding_reports=repair_binding_reports,
			goal_ordering_binding_reports=goal_ordering_binding_reports,
			atomic_progress_binding_reports=atomic_progress_binding_reports,
			recursion_descent_audit=recursion_descent_audit,
		),
		"paper_profile_ready": not paper_profile_failures,
		"paper_profile_failures": tuple(paper_profile_failures),
		"bounded_validation": (
			bounded_validation.to_dict()
			if bounded_validation is not None
			else None
		),
	}
	plan_library.metadata["unified_synthesis_report"] = dict(report)
	return UnifiedSynthesisResult(
		plan_library=plan_library,
		report=report,
		rejected_external_features=rejected_features,
	)


def _normalize_synthesis_profile(profile: str) -> str:
	normalized = str(profile or "bootstrap").strip().lower()
	if normalized not in {"bootstrap", "paper"}:
		raise ValueError(
			"Synthesis profile must be either 'bootstrap' or 'paper'; "
			f"received {profile!r}.",
		)
	return normalized


def _paper_profile_failures(
	*,
	training_problem_files: Sequence[str | Path],
	external_sketch_policies: Sequence[ExternalSketchPolicySource],
	external_candidates: Sequence[LiftedPlanRule],
	paper_policy_audits: Sequence[PaperPolicyAuditReport],
	external_rule_reports: Sequence[ExternalRuleBindingReport],
	repair_binding_reports: Sequence[RepairConstraintBindingReport],
	goal_ordering_binding_reports: Sequence[GoalOrderingConstraintBindingReport],
	atomic_progress_binding_reports: Sequence[AtomicProgressConstraintBindingReport],
	bounded_validation: BoundedLibraryValidationReport | None,
) -> tuple[str, ...]:
	failures: list[str] = []
	if not tuple(training_problem_files or ()):
		failures.append("paper profile requires at least one training problem")
	if not tuple(external_sketch_policies or ()):
		failures.append("paper profile requires at least one external learned sketch policy")
	if not tuple(paper_policy_audits or ()):
		failures.append("paper profile has no parsed external policy audit")
	if not tuple(external_rule_reports or ()):
		failures.append("paper profile has no external learned rule binding reports")
	if not tuple(external_candidates or ()):
		failures.append("paper profile compiled no external learned sketch candidates")
	for audit in tuple(paper_policy_audits or ()):
		if not audit.ready_for_executable_asl:
			failures.append(
				(
					f"external policy {audit.source_name!r} is not ready for executable ASL "
					f"({len(audit.unsupported_features)} unsupported features, "
					f"{audit.executable_effect_count} executable effects)"
				),
			)
	for report in tuple(external_rule_reports or ()):
		if report.compiled:
			continue
		failures.append(
			(
				f"external rule {report.source_name}:{report.rule_index} did not compile "
				f"(missing conditions={report.missing_condition_bindings}, "
				f"missing effects={report.missing_effect_bindings}, "
				f"empty_body={report.empty_body})"
			),
		)
	for report in tuple(repair_binding_reports or ()):
		if report.matched:
			continue
		failures.append(
			(
				"unmatched primitive-precondition repair constraint "
				f"{report.constraint_index} "
				f"(required capabilities={report.required_capabilities})"
			),
		)
	for report in tuple(goal_ordering_binding_reports or ()):
		if report.matched:
			continue
		failures.append(
			(
				"unmatched goal-ordering refinement constraint "
				f"{report.constraint_index}.{report.ordering_index} "
				f"({report.earlier_goal} before {report.later_goal}; "
				f"reason={report.rejection_reason})"
			),
		)
	for report in tuple(atomic_progress_binding_reports or ()):
		if report.matched:
			continue
		failures.append(
			(
				"unmatched atomic-progress refinement constraint "
				f"{report.constraint_index} "
				f"(required capabilities={report.required_capabilities}; "
				f"reason={report.rejection_reason})"
			),
		)
	if bounded_validation is None:
		failures.append("paper profile requires bounded validation over training problems")
	elif not bounded_validation.passed:
		failures.append(
			(
				"bounded validation failed "
				f"({bounded_validation.failure_count} failures across "
				f"{bounded_validation.checked_problem_count} problems)"
			),
		)
	elif bounded_validation.execution_semantics != "deterministic_first_applicable_asl":
		failures.append(
			(
				"paper profile requires deterministic first-applicable ASL validation; "
				f"received {bounded_validation.execution_semantics}"
			),
		)
	return tuple(failures)


def _run_requested_learner_sketches(
	*,
	backend: BackendManifest | None,
	run_configs: Sequence[LearnerSketchesRunConfig],
) -> tuple[tuple[LearnerSketchesRunResult, ...], tuple[ExternalSketchPolicySource, ...]]:
	configs = tuple(run_configs or ())
	if not configs:
		return (), ()
	if backend is None:
		raise ValueError("learner_sketches_backend is required when learner_sketches_runs are provided.")
	results: list[LearnerSketchesRunResult] = []
	sources: list[ExternalSketchPolicySource] = []
	for index, config in enumerate(configs, start=1):
		result = run_learner_sketches(manifest=backend, config=config)
		results.append(result)
		if not result.succeeded or result.policy_file is None:
			raise RuntimeError(
				"learner-sketches did not produce a minimized policy: "
				f"workspace={result.workspace}; returncode={result.returncode}; "
				f"stderr={result.stderr.strip()}",
			)
		sources.append(
			ExternalSketchPolicySource(
				name=f"learner-sketches-{index}-{result.workspace.name}",
				policy_file=result.policy_file,
			),
		)
	return tuple(results), tuple(sources)


def _external_sketch_candidates(
	*,
	domain,
	sources: Sequence[ExternalSketchPolicySource],
) -> tuple[
	tuple[LiftedPlanRule, ...],
	dict[str, str],
	tuple[PaperPolicyAuditReport, ...],
	tuple[ExternalRuleBindingReport, ...],
]:
	candidates: list[LiftedPlanRule] = []
	rejected: dict[str, str] = {}
	audits: list[PaperPolicyAuditReport] = []
	rule_reports: list[ExternalRuleBindingReport] = []
	for source in sources:
		audit, policy, binding_report = audit_learned_policy_for_asl_binding(
			source_name=source.name,
			policy_file=source.policy_file,
			domain=domain,
		)
		audits.append(audit)
		for feature_id, expression in binding_report.unsupported_features.items():
			rejected[f"{source.name}:{feature_id}"] = expression
		source_candidates, source_reports = _bound_policy_rules_to_candidates(
			source=source,
			policy=policy,
			bindings=binding_report.bindings,
		)
		candidates.extend(source_candidates)
		rule_reports.extend(source_reports)
	return tuple(candidates), rejected, tuple(audits), tuple(rule_reports)


def _bound_policy_rules_to_candidates(
	*,
	source: ExternalSketchPolicySource,
	policy,
	bindings,
) -> tuple[tuple[LiftedPlanRule, ...], tuple[ExternalRuleBindingReport, ...]]:
	candidates: list[LiftedPlanRule] = []
	reports: list[ExternalRuleBindingReport] = []
	for index, rule in enumerate(policy.parsed_rules, start=1):
		context: list[str] = []
		body: list[LiftedCall] = []
		missing_conditions: list[str] = []
		missing_effects: list[str] = []
		for condition in rule.conditions:
			binding = bindings.get(condition.feature_id)
			if binding is None or condition.operator not in binding.condition_contexts:
				missing_conditions.append(f"{condition.feature_id}:{condition.operator}")
				continue
			context.extend(binding.condition_contexts[condition.operator])
		for effect in rule.effects:
			binding = bindings.get(effect.feature_id)
			if binding is None or effect.operator not in binding.effect_body:
				missing_effects.append(f"{effect.feature_id}:{effect.operator}")
				continue
			context.extend((binding.effect_contexts or {}).get(effect.operator, ()))
			body.extend(
				_body_step_to_lifted_call(step)
				for step in binding.effect_body[effect.operator]
			)
		compiled = not missing_conditions and not missing_effects and bool(body)
		reports.append(
			ExternalRuleBindingReport(
				source_name=source.name,
				rule_index=index,
				raw_rule=rule.raw,
				compiled=compiled,
				missing_condition_bindings=tuple(missing_conditions),
				missing_effect_bindings=tuple(missing_effects),
				empty_body=not body,
			),
		)
		if not compiled:
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
	return tuple(candidates), tuple(reports)


def _repair_required_rule_groups(
	*,
	candidate_rules: Sequence[LiftedPlanRule],
	predicates: Sequence[object],
	actions: Sequence[object],
	refinement_constraints: Sequence[object],
) -> tuple[tuple[ClingoRequiredRuleGroup, ...], tuple[RepairConstraintBindingReport, ...]]:
	groups: list[ClingoRequiredRuleGroup] = []
	reports: list[RepairConstraintBindingReport] = []
	declared_predicates = _declared_predicate_names(predicates)
	predicate_arities = _declared_predicate_arities(predicates)
	action_arities = _declared_action_arities(actions)
	for index, constraint in enumerate(tuple(refinement_constraints or ()), start=1):
		constraint_type = str(getattr(constraint, "constraint_type", "") or "")
		if constraint_type != "counterexample_atomic_precondition_repair":
			continue
		target_predicates = tuple(
			_atom_predicate(atom)
			for atom in tuple(getattr(constraint, "lifted_missing_goals", ()) or ())
			if _atom_predicate(atom)
		)
		precondition_predicates = tuple(
			_atom_predicate(atom)
			for atom in tuple(getattr(constraint, "lifted_missing_preconditions", ()) or ())
			if _atom_predicate(atom)
		)
		failing_action = str(getattr(constraint, "failing_action", "") or "")
		if failing_action not in action_arities:
			reports.append(
				RepairConstraintBindingReport(
					constraint_index=index,
					constraint_type=constraint_type,
					matched=False,
					target_predicates=target_predicates,
					precondition_predicates=precondition_predicates,
					failing_action=failing_action,
					required_capabilities=(),
					rule_names=(),
					available_capabilities=(),
					rejection_reason="undeclared_repair_failing_action",
				),
			)
			continue
		if not _repair_failing_action_arity_matches(
			constraint=constraint,
			failing_action=failing_action,
			action_arities=action_arities,
		):
			reports.append(
				RepairConstraintBindingReport(
					constraint_index=index,
					constraint_type=constraint_type,
					matched=False,
					target_predicates=target_predicates,
					precondition_predicates=precondition_predicates,
					failing_action=failing_action,
					required_capabilities=(),
					rule_names=(),
					available_capabilities=(),
					rejection_reason="wrong_repair_failing_action_arity",
				),
			)
			continue
		undeclared_predicates = _undeclared_repair_predicates(
			target_predicates=target_predicates,
			precondition_predicates=precondition_predicates,
			declared_predicates=declared_predicates,
		)
		if undeclared_predicates:
			reports.append(
				RepairConstraintBindingReport(
					constraint_index=index,
					constraint_type=constraint_type,
					matched=False,
					target_predicates=target_predicates,
					precondition_predicates=precondition_predicates,
					failing_action=failing_action,
					required_capabilities=(),
					rule_names=(),
					available_capabilities=(),
					undeclared_predicates=undeclared_predicates,
					rejection_reason="undeclared_repair_predicate",
				),
			)
			continue
		target_atoms = tuple(getattr(constraint, "lifted_missing_goals", ()) or ())
		precondition_atoms = tuple(
			getattr(constraint, "lifted_missing_preconditions", ()) or (),
		)
		wrong_arity_predicates = _wrong_arity_lifted_predicates(
			atoms=(*target_atoms, *precondition_atoms),
			predicate_arities=predicate_arities,
		)
		if wrong_arity_predicates:
			reports.append(
				RepairConstraintBindingReport(
					constraint_index=index,
					constraint_type=constraint_type,
					matched=False,
					target_predicates=target_predicates,
					precondition_predicates=precondition_predicates,
					failing_action=failing_action,
					required_capabilities=(),
					rule_names=(),
					available_capabilities=(),
					rejection_reason="wrong_repair_predicate_arity",
				),
			)
			continue
		required_capabilities = tuple(
			f"module_{target}_prepare_{precondition}_for_{failing_action}"
			for target in target_predicates
			for precondition in precondition_predicates
			if target and precondition and failing_action
		)
		rule_names = tuple(
			rule.name
			for rule in tuple(candidate_rules or ())
			if any(
				capability in rule.capabilities
				for capability in required_capabilities
			)
		)
		available_capabilities = _repair_available_capabilities(
			candidate_rules=candidate_rules,
			target_predicates=target_predicates,
			precondition_predicates=precondition_predicates,
			failing_action=failing_action,
		)
		if not rule_names:
			reports.append(
				RepairConstraintBindingReport(
					constraint_index=index,
					constraint_type=constraint_type,
					matched=False,
					target_predicates=target_predicates,
					precondition_predicates=precondition_predicates,
					failing_action=failing_action,
					required_capabilities=required_capabilities,
					rule_names=(),
					available_capabilities=available_capabilities,
					rejection_reason=_repair_rejection_reason(
						precondition_predicates=precondition_predicates,
						available_capabilities=available_capabilities,
					),
				),
			)
			continue
		groups.append(
			ClingoRequiredRuleGroup(
				name=f"repair_{index}_{'_'.join(required_capabilities)}",
				rule_names=rule_names,
			),
		)
		reports.append(
			RepairConstraintBindingReport(
				constraint_index=index,
				constraint_type=constraint_type,
				matched=True,
				target_predicates=target_predicates,
				precondition_predicates=precondition_predicates,
				failing_action=failing_action,
				required_capabilities=required_capabilities,
				rule_names=rule_names,
				available_capabilities=available_capabilities,
				rejection_reason=None,
			),
		)
	return tuple(groups), tuple(reports)


def _repair_synthesized_candidate_rules(
	*,
	actions: Sequence[object],
	predicates: Sequence[object],
	refinement_constraints: Sequence[object],
) -> tuple[LiftedPlanRule, ...]:
	"""Generate safe missing-prepare candidates from lifted repair evidence.

	The synthesis is deliberately conservative: a repair module may introduce
	extra variables only when a read-only goal descriptor binds them in the
	context. This prevents emitting ASL bodies with free variables.
	"""

	rules: list[LiftedPlanRule] = []
	declared_predicates = _declared_predicate_names(predicates)
	predicate_arities = _declared_predicate_arities(predicates)
	action_arities = _declared_action_arities(actions)
	producible_predicates = _positive_effect_predicates(actions)
	for constraint in tuple(refinement_constraints or ()):
		if getattr(constraint, "constraint_type", "") != (
			"counterexample_atomic_precondition_repair"
		):
			continue
		problem_goal_atoms = _repair_constraint_goal_atoms(constraint)
		failing_action = str(getattr(constraint, "failing_action", "") or "")
		action = _action_by_name(actions, failing_action)
		if action is None:
			continue
		if not _repair_failing_action_arity_matches(
			constraint=constraint,
			failing_action=failing_action,
			action_arities=action_arities,
		):
			continue
		action_preconditions = parse_pddl_literals(str(getattr(action, "preconditions", "")))
		for target_atom in tuple(getattr(constraint, "lifted_missing_goals", ()) or ()):
			target_predicate, target_arguments = _parse_lifted_atom(target_atom)
			if not target_predicate:
				continue
			if target_predicate not in declared_predicates:
				continue
			if not _predicate_arity_matches(
				target_predicate,
				target_arguments,
				predicate_arities,
			):
				continue
			for missing_atom in tuple(
				getattr(constraint, "lifted_missing_preconditions", ()) or (),
			):
				precondition_predicate, precondition_arguments = _parse_lifted_atom(
					missing_atom,
				)
				if not precondition_predicate:
					continue
				if precondition_predicate not in declared_predicates:
					continue
				if not _predicate_arity_matches(
					precondition_predicate,
					precondition_arguments,
					predicate_arities,
				):
					continue
				if precondition_predicate not in producible_predicates:
					continue
				matched_precondition = _matching_positive_action_precondition(
					action_preconditions,
					predicate=precondition_predicate,
					arguments=precondition_arguments,
				)
				if matched_precondition is None:
					continue
				context = _repair_candidate_context(
					target_arguments=target_arguments,
					precondition_predicate=precondition_predicate,
					precondition_arguments=precondition_arguments,
					missing_atom=missing_atom,
					problem_goal_atoms=problem_goal_atoms,
				)
				if context is None:
					continue
				rules.append(
					LiftedPlanRule(
						name=(
							f"{target_predicate}_repair_prepare_"
							f"{precondition_predicate}_for_{failing_action}"
						),
						head=LiftedCall("subgoal", target_predicate, target_arguments),
						context=context,
						body=(
							LiftedCall(
								"subgoal",
								precondition_predicate,
								precondition_arguments,
							),
							LiftedCall("subgoal", target_predicate, target_arguments),
						),
						layer="atomic",
						rationale="counterexample_repair",
						capabilities=(
							f"module_{target_predicate}_prepare_"
							f"{precondition_predicate}_for_{failing_action}",
						),
						cost=4,
					),
				)
	return tuple(rules)


def _explicit_goal_ordering_candidate_rules(
	*,
	predicates: Sequence[object],
	refinement_constraints: Sequence[object],
) -> tuple[LiftedPlanRule, ...]:
	"""Compile lifted goal-ordering refinement constraints into composer rules."""

	rules: list[LiftedPlanRule] = []
	index = 0
	declared_predicates = _declared_predicate_names(predicates)
	predicate_arities = _declared_predicate_arities(predicates)
	for constraint in tuple(refinement_constraints or ()):
		if getattr(constraint, "constraint_type", "") != "counterexample_goal_ordering":
			continue
		for earlier_goal, later_goal in tuple(
			getattr(constraint, "lifted_orderings", ()) or (),
		):
			earlier_predicate, earlier_arguments = _parse_goal_descriptor_atom(
				earlier_goal,
			)
			later_predicate, later_arguments = _parse_goal_descriptor_atom(later_goal)
			if not earlier_predicate or not later_predicate:
				continue
			if (
				earlier_predicate not in declared_predicates
				or later_predicate not in declared_predicates
			):
				continue
			if not _predicate_arity_matches(
				earlier_predicate,
				earlier_arguments,
				predicate_arities,
			) or not _predicate_arity_matches(
				later_predicate,
				later_arguments,
				predicate_arities,
			):
				continue
			if not set(earlier_arguments).intersection(later_arguments):
				continue
			index += 1
			rules.append(
				LiftedPlanRule(
					name=(
						f"g_counterexample_order_{earlier_predicate}_before_"
						f"{later_predicate}_{index}"
					),
					head=LiftedCall("subgoal", "g", ()),
					context=(
						_call(f"goal_{earlier_predicate}", earlier_arguments),
						_call(f"goal_{later_predicate}", later_arguments),
						f"not {_call(earlier_predicate, earlier_arguments)}",
					),
					body=(
						LiftedCall("subgoal", earlier_predicate, earlier_arguments),
						LiftedCall("subgoal", "g", ()),
					),
					layer="composer",
					rationale="counterexample_goal_ordering",
					capabilities=(
						_goal_ordering_constraint_capability(
							earlier_predicate=earlier_predicate,
							earlier_arguments=earlier_arguments,
							later_predicate=later_predicate,
							later_arguments=later_arguments,
						),
					),
					cost=1,
				),
			)
	return tuple(rules)


def _goal_ordering_required_rule_groups(
	*,
	candidate_rules: Sequence[LiftedPlanRule],
	predicates: Sequence[object],
	refinement_constraints: Sequence[object],
) -> tuple[tuple[ClingoRequiredRuleGroup, ...], tuple[GoalOrderingConstraintBindingReport, ...]]:
	groups: list[ClingoRequiredRuleGroup] = []
	reports: list[GoalOrderingConstraintBindingReport] = []
	group_index = 0
	declared_predicates = _declared_predicate_names(predicates)
	predicate_arities = _declared_predicate_arities(predicates)
	for constraint_index, constraint in enumerate(
		tuple(refinement_constraints or ()),
		start=1,
	):
		if getattr(constraint, "constraint_type", "") != "counterexample_goal_ordering":
			continue
		for ordering_index, (earlier_goal, later_goal) in enumerate(
			getattr(constraint, "lifted_orderings", ()) or (),
			start=1,
		):
			earlier_predicate, earlier_arguments = _parse_goal_descriptor_atom(
				earlier_goal,
			)
			later_predicate, later_arguments = _parse_goal_descriptor_atom(later_goal)
			if not earlier_predicate or not later_predicate:
				reports.append(
					GoalOrderingConstraintBindingReport(
						constraint_index=constraint_index,
						ordering_index=ordering_index,
						matched=False,
						earlier_goal=str(earlier_goal),
						later_goal=str(later_goal),
						required_capability=None,
						rule_names=(),
						rejection_reason="invalid_goal_descriptor",
					),
				)
				continue
			if (
				earlier_predicate not in declared_predicates
				or later_predicate not in declared_predicates
			):
				reports.append(
					GoalOrderingConstraintBindingReport(
						constraint_index=constraint_index,
						ordering_index=ordering_index,
						matched=False,
						earlier_goal=str(earlier_goal),
						later_goal=str(later_goal),
						required_capability=None,
						rule_names=(),
						rejection_reason="undeclared_goal_ordering_predicate",
					),
				)
				continue
			if not _predicate_arity_matches(
				earlier_predicate,
				earlier_arguments,
				predicate_arities,
			) or not _predicate_arity_matches(
				later_predicate,
				later_arguments,
				predicate_arities,
			):
				reports.append(
					GoalOrderingConstraintBindingReport(
						constraint_index=constraint_index,
						ordering_index=ordering_index,
						matched=False,
						earlier_goal=str(earlier_goal),
						later_goal=str(later_goal),
						required_capability=None,
						rule_names=(),
						rejection_reason="wrong_goal_ordering_predicate_arity",
					),
				)
				continue
			if not set(earlier_arguments).intersection(later_arguments):
				reports.append(
					GoalOrderingConstraintBindingReport(
						constraint_index=constraint_index,
						ordering_index=ordering_index,
						matched=False,
						earlier_goal=str(earlier_goal),
						later_goal=str(later_goal),
						required_capability=None,
						rule_names=(),
						rejection_reason="disconnected_goal_ordering_variables",
					),
				)
				continue
			capability = _goal_ordering_constraint_capability(
				earlier_predicate=earlier_predicate,
				earlier_arguments=earlier_arguments,
				later_predicate=later_predicate,
				later_arguments=later_arguments,
			)
			rule_names = tuple(
				rule.name
				for rule in tuple(candidate_rules or ())
				if capability in rule.capabilities
			)
			if not rule_names:
				reports.append(
					GoalOrderingConstraintBindingReport(
						constraint_index=constraint_index,
						ordering_index=ordering_index,
						matched=False,
						earlier_goal=str(earlier_goal),
						later_goal=str(later_goal),
						required_capability=capability,
						rule_names=(),
						rejection_reason="no_matching_lifted_composer_rule",
					),
				)
				continue
			group_index += 1
			groups.append(
				ClingoRequiredRuleGroup(
					name=f"goal_ordering_{group_index}_{capability}",
					rule_names=rule_names,
				),
			)
			reports.append(
				GoalOrderingConstraintBindingReport(
					constraint_index=constraint_index,
					ordering_index=ordering_index,
					matched=True,
					earlier_goal=str(earlier_goal),
					later_goal=str(later_goal),
					required_capability=capability,
					rule_names=rule_names,
					rejection_reason=None,
				),
			)
	return tuple(groups), tuple(reports)


def _atomic_progress_required_rule_groups(
	*,
	candidate_rules: Sequence[LiftedPlanRule],
	predicates: Sequence[object],
	refinement_constraints: Sequence[object],
) -> tuple[tuple[ClingoRequiredRuleGroup, ...], tuple[AtomicProgressConstraintBindingReport, ...]]:
	groups: list[ClingoRequiredRuleGroup] = []
	reports: list[AtomicProgressConstraintBindingReport] = []
	declared_predicates = _declared_predicate_names(predicates)
	predicate_arities = _declared_predicate_arities(predicates)
	for constraint_index, constraint in enumerate(
		tuple(refinement_constraints or ()),
		start=1,
	):
		constraint_type = str(getattr(constraint, "constraint_type", "") or "")
		if constraint_type != "counterexample_atomic_progress":
			continue
		target_atoms = tuple(getattr(constraint, "lifted_missing_goals", ()) or ())
		target_predicates = tuple(
			_atom_predicate(atom)
			for atom in target_atoms
			if _atom_predicate(atom)
		)
		undeclared_predicates = tuple(
			dict.fromkeys(
				predicate
				for predicate in target_predicates
				if predicate not in declared_predicates
			),
		)
		if undeclared_predicates:
			reports.append(
				AtomicProgressConstraintBindingReport(
					constraint_index=constraint_index,
					constraint_type=constraint_type,
					matched=False,
					target_predicates=target_predicates,
					required_capabilities=(),
					rule_names=(),
					available_capabilities=(),
					undeclared_predicates=undeclared_predicates,
					rejection_reason="undeclared_atomic_progress_predicate",
				),
			)
			continue
		wrong_arity_predicates = _wrong_arity_lifted_predicates(
			atoms=target_atoms,
			predicate_arities=predicate_arities,
		)
		if wrong_arity_predicates:
			reports.append(
				AtomicProgressConstraintBindingReport(
					constraint_index=constraint_index,
					constraint_type=constraint_type,
					matched=False,
					target_predicates=target_predicates,
					required_capabilities=(),
					rule_names=(),
					available_capabilities=(),
					wrong_arity_predicates=wrong_arity_predicates,
					rejection_reason="wrong_atomic_progress_predicate_arity",
				),
			)
			continue
		required_capabilities = tuple(
			f"module_{predicate}_action"
			for predicate in target_predicates
		)
		rule_names = tuple(
			rule.name
			for rule in tuple(candidate_rules or ())
			if rule.layer == "atomic"
			and any(
				capability.startswith(f"module_{predicate}_action_")
				for predicate in target_predicates
				for capability in rule.capabilities
			)
		)
		available_capabilities = tuple(
			dict.fromkeys(
				capability
				for rule in tuple(candidate_rules or ())
				for capability in rule.capabilities
				if any(
					capability.startswith(f"module_{predicate}_")
					for predicate in target_predicates
				)
			),
		)
		if not rule_names:
			reports.append(
				AtomicProgressConstraintBindingReport(
					constraint_index=constraint_index,
					constraint_type=constraint_type,
					matched=False,
					target_predicates=target_predicates,
					required_capabilities=required_capabilities,
					rule_names=(),
					available_capabilities=available_capabilities,
					rejection_reason="no_matching_atomic_progress_rule",
				),
			)
			continue
		groups.append(
			ClingoRequiredRuleGroup(
				name=f"atomic_progress_{constraint_index}_{'_'.join(target_predicates)}",
				rule_names=rule_names,
			),
		)
		reports.append(
			AtomicProgressConstraintBindingReport(
				constraint_index=constraint_index,
				constraint_type=constraint_type,
				matched=True,
				target_predicates=target_predicates,
				required_capabilities=required_capabilities,
				rule_names=rule_names,
				available_capabilities=available_capabilities,
				rejection_reason=None,
			),
		)
	return tuple(groups), tuple(reports)


def _declared_predicate_names(predicates: Sequence[object]) -> frozenset[str]:
	return frozenset(
		str(getattr(predicate, "name", "") or "")
		for predicate in tuple(predicates or ())
		if str(getattr(predicate, "name", "") or "")
	)


def _declared_predicate_arities(predicates: Sequence[object]) -> dict[str, int]:
	return {
		str(getattr(predicate, "name", "") or ""): len(
			tuple(getattr(predicate, "parameters", ()) or ()),
		)
		for predicate in tuple(predicates or ())
		if str(getattr(predicate, "name", "") or "")
	}


def _declared_action_arities(actions: Sequence[object]) -> dict[str, int]:
	return {
		str(getattr(action, "name", "") or ""): len(
			tuple(getattr(action, "parameters", ()) or ()),
		)
		for action in tuple(actions or ())
		if str(getattr(action, "name", "") or "")
	}


def _repair_failing_action_arity_matches(
	*,
	constraint: object,
	failing_action: str,
	action_arities: Mapping[str, int],
) -> bool:
	expected = action_arities.get(failing_action)
	if expected is None:
		return False
	lifted_action = str(getattr(constraint, "lifted_failing_action", "") or "")
	action_name, lifted_arguments = _parse_lifted_atom(lifted_action)
	if action_name:
		if action_name != failing_action:
			return False
		return len(lifted_arguments) == expected
	failing_action_arguments = tuple(
		getattr(constraint, "failing_action_arguments", ()) or (),
	)
	return len(failing_action_arguments) == expected


def _wrong_arity_lifted_predicates(
	*,
	atoms: Sequence[str],
	predicate_arities: Mapping[str, int],
) -> tuple[str, ...]:
	wrong: list[str] = []
	for atom in tuple(atoms or ()):
		predicate, arguments = _parse_lifted_atom(atom)
		if not predicate:
			continue
		if not _predicate_arity_matches(predicate, arguments, predicate_arities):
			wrong.append(predicate)
	return tuple(dict.fromkeys(wrong))


def _predicate_arity_matches(
	predicate: str,
	arguments: tuple[str, ...],
	predicate_arities: Mapping[str, int],
) -> bool:
	expected = predicate_arities.get(predicate)
	return expected is None or expected == len(arguments)


def _undeclared_repair_predicates(
	*,
	target_predicates: tuple[str, ...],
	precondition_predicates: tuple[str, ...],
	declared_predicates: frozenset[str],
) -> tuple[str, ...]:
	return tuple(
		dict.fromkeys(
			predicate
			for predicate in (*target_predicates, *precondition_predicates)
			if predicate and predicate not in declared_predicates
		),
	)


def _repair_available_capabilities(
	*,
	candidate_rules: Sequence[LiftedPlanRule],
	target_predicates: tuple[str, ...],
	precondition_predicates: tuple[str, ...],
	failing_action: str,
) -> tuple[str, ...]:
	relevant_prefixes = tuple(
		dict.fromkeys(
			(
				*(
					f"module_{target}_prepare_"
					for target in target_predicates
				),
				*(
					f"module_{precondition}_action_"
					for precondition in precondition_predicates
				),
				*(
					f"module_{target}_action_{failing_action}"
					for target in target_predicates
					if failing_action
				),
			),
		),
	)
	return tuple(
		dict.fromkeys(
			capability
			for rule in tuple(candidate_rules or ())
			for capability in rule.capabilities
			if any(capability.startswith(prefix) for prefix in relevant_prefixes)
		),
	)


def _action_by_name(actions: Sequence[object], action_name: str) -> object | None:
	for action in tuple(actions or ()):
		if str(getattr(action, "name", "")) == action_name:
			return action
	return None


def _positive_effect_predicates(actions: Sequence[object]) -> frozenset[str]:
	predicates: set[str] = set()
	for action in tuple(actions or ()):
		for effect in parse_pddl_literals(str(getattr(action, "effects", ""))):
			if effect.is_positive:
				predicates.add(effect.predicate)
	return frozenset(predicates)


def _matching_positive_action_precondition(
	preconditions: Sequence[object],
	*,
	predicate: str,
	arguments: tuple[str, ...],
) -> object | None:
	for precondition in tuple(preconditions or ()):
		if not bool(getattr(precondition, "is_positive", False)):
			continue
		if str(getattr(precondition, "predicate", "")) != predicate:
			continue
		precondition_arguments = tuple(
			_parameter_to_variable(argument)
			for argument in tuple(getattr(precondition, "arguments", ()) or ())
		)
		if precondition_arguments == arguments:
			return precondition
	return None


def _repair_candidate_context(
	*,
	target_arguments: tuple[str, ...],
	precondition_predicate: str,
	precondition_arguments: tuple[str, ...],
	missing_atom: str,
	problem_goal_atoms: tuple[str, ...],
) -> tuple[str, ...] | None:
	bound_variables = {
		argument for argument in target_arguments if _is_lifted_variable(argument)
	}
	precondition_variables = {
		argument for argument in precondition_arguments if _is_lifted_variable(argument)
	}
	extra_variables = precondition_variables - bound_variables
	if not extra_variables:
		return (f"not {_call(precondition_predicate, precondition_arguments)}",)
	if missing_atom not in problem_goal_atoms:
		return None
	goal_context = _call(f"goal_{precondition_predicate}", precondition_arguments)
	return (
		goal_context,
		f"not {_call(precondition_predicate, precondition_arguments)}",
	)


def _repair_constraint_goal_atoms(constraint: object) -> tuple[str, ...]:
	problem_file = str(getattr(constraint, "problem_file", "") or "")
	if not problem_file:
		return ()
	try:
		problem = PDDLParser.parse_problem(problem_file)
	except Exception:
		return ()
	lifted_missing_preconditions = tuple(
		getattr(constraint, "lifted_missing_preconditions", ()) or (),
	)
	ground_missing_preconditions = tuple(
		getattr(constraint, "missing_preconditions", ()) or (),
	)
	lifted_by_ground = dict(
		zip(ground_missing_preconditions, lifted_missing_preconditions),
	)
	goal_signatures = {
		_call(fact.predicate, fact.args)
		for fact in tuple(problem.goal_facts or ())
		if fact.is_positive
	}
	return tuple(
		lifted
		for ground, lifted in lifted_by_ground.items()
		if ground in goal_signatures
	)


def _parse_lifted_atom(atom: str) -> tuple[str, tuple[str, ...]]:
	text = str(atom or "").strip()
	if text.startswith("not "):
		return "", ()
	if "(" not in text:
		return text, ()
	if not text.endswith(")"):
		return "", ()
	predicate, raw_arguments = text.split("(", 1)
	return (
		predicate.strip(),
		tuple(
			argument.strip()
			for argument in raw_arguments[:-1].split(",")
			if argument.strip()
		),
	)


def _parse_goal_descriptor_atom(atom: str) -> tuple[str, tuple[str, ...]]:
	predicate, arguments = _parse_lifted_atom(atom)
	if not predicate.startswith("goal_"):
		return "", ()
	return predicate[len("goal_") :], arguments


def _goal_ordering_constraint_capability(
	*,
	earlier_predicate: str,
	earlier_arguments: tuple[str, ...],
	later_predicate: str,
	later_arguments: tuple[str, ...],
) -> str:
	return (
		f"counterexample_order_{earlier_predicate}_{'_'.join(earlier_arguments)}"
		f"_before_{later_predicate}_{'_'.join(later_arguments)}"
	)


def _parameter_to_variable(parameter: str) -> str:
	return parameter_variables((str(parameter),))[0]


def _is_lifted_variable(argument: str) -> bool:
	text = str(argument or "").strip()
	return bool(text) and text[0].isupper()


def _call(predicate: str, arguments: Sequence[str]) -> str:
	return predicate if not arguments else f"{predicate}({', '.join(arguments)})"


def _repair_rejection_reason(
	*,
	precondition_predicates: tuple[str, ...],
	available_capabilities: tuple[str, ...],
) -> str:
	if any(
		not any(
			capability.startswith(f"module_{precondition}_action_")
			for capability in available_capabilities
		)
		for precondition in precondition_predicates
	):
		return "unproducible_precondition_predicate"
	return "no_matching_lifted_prepare_rule"


def _atom_predicate(atom: str) -> str:
	text = str(atom or "").strip()
	if text.startswith("not "):
		text = text[4:].strip()
	if "(" not in text:
		return text
	return text.split("(", 1)[0].strip()


def _body_step_to_lifted_call(step: AgentSpeakBodyStep) -> LiftedCall:
	kind = "action" if step.kind in {"action", "primitive_action"} else step.kind
	return LiftedCall(kind, step.symbol, step.arguments)


def _deduplicate_rules(rules: Sequence[LiftedPlanRule]) -> tuple[LiftedPlanRule, ...]:
	index_by_key: dict[tuple[object, ...], int] = {}
	deduplicated: list[LiftedPlanRule] = []
	for rule in rules:
		key = (rule.head, rule.context, rule.body, rule.layer)
		existing_index = index_by_key.get(key)
		if existing_index is None:
			index_by_key[key] = len(deduplicated)
			deduplicated.append(rule)
			continue
		# Same lifted rule reached from multiple evidence sources (for example a
		# trace-observed ordering and a schema causal-interference ordering): keep
		# one rule but union the capabilities so both evidence tags survive.
		existing = deduplicated[existing_index]
		merged_capabilities = tuple(
			dict.fromkeys((*existing.capabilities, *rule.capabilities)),
		)
		if merged_capabilities != existing.capabilities:
			deduplicated[existing_index] = replace(
				existing,
				capabilities=merged_capabilities,
			)
	return tuple(deduplicated)


def _candidate_source_counts(rules: Sequence[LiftedPlanRule]) -> dict[str, int]:
	counts: dict[str, int] = {}
	for rule in rules:
		source = _candidate_source(rule)
		counts[source] = counts.get(source, 0) + 1
	return counts


def _candidate_source(rule: LiftedPlanRule) -> str:
	if rule.rationale.startswith("external_policy:"):
		return "external_sketch"
	if rule.rationale == "counterexample_repair":
		return "counterexample_repair"
	if rule.rationale == "counterexample_goal_ordering":
		return "counterexample_goal_ordering"
	return "schema"


def _evidence_matrix(
	*,
	schema_candidates: Sequence[LiftedPlanRule],
	external_candidates: Sequence[LiftedPlanRule],
	repair_synthesized_candidates: Sequence[LiftedPlanRule],
	explicit_goal_ordering_candidates: Sequence[LiftedPlanRule],
	candidate_rules: Sequence[LiftedPlanRule],
	selected_rules: Sequence[LiftedPlanRule],
	output_rules: Sequence[LiftedPlanRule],
	training_transition_evidence: Sequence[object],
	counterexample_transition_evidence: Sequence[object],
	training_progress_rule_groups: Sequence[object],
	counterexample_progress_rule_groups: Sequence[object],
	training_state_coverage_rule_groups: Sequence[object],
	counterexample_state_coverage_rule_groups: Sequence[object],
	paper_policy_audits: Sequence[PaperPolicyAuditReport],
	external_rule_reports: Sequence[ExternalRuleBindingReport],
	repair_binding_reports: Sequence[RepairConstraintBindingReport],
	goal_ordering_binding_reports: Sequence[GoalOrderingConstraintBindingReport],
	atomic_progress_binding_reports: Sequence[AtomicProgressConstraintBindingReport],
	recursion_descent_audit: Mapping[str, object],
) -> dict[str, object]:
	"""Summarize which evidence sources support each synthesis layer."""

	training_atomic_patterns = anti_unify_training_atomic_achievements(
		training_transition_evidence,
	)
	counterexample_atomic_patterns = anti_unify_training_atomic_achievements(
		counterexample_transition_evidence,
	)
	all_atomic_patterns = anti_unify_training_atomic_achievements(
		(
			*tuple(training_transition_evidence or ()),
			*tuple(counterexample_transition_evidence or ()),
		),
	)
	repair_reports = tuple(repair_binding_reports or ())
	atomic_progress_reports = tuple(atomic_progress_binding_reports or ())
	goal_ordering_reports = tuple(goal_ordering_binding_reports or ())
	return {
		"layer_b_atomic_modules": {
			"target": "PDDL predicate achievement-goal modules",
			"schema_candidate_count": _layer_count(schema_candidates, "atomic"),
			"external_candidate_count": _layer_count(external_candidates, "atomic"),
			"repair_synthesized_candidate_count": _layer_count(
				repair_synthesized_candidates,
				"atomic",
			),
			"candidate_count": _layer_count(candidate_rules, "atomic"),
			"selected_rule_count": _layer_count(selected_rules, "atomic"),
			"output_rule_count": _layer_count(output_rules, "atomic"),
			"training_transition_progress_constraint_count": len(
				tuple(training_progress_rule_groups or ()),
			),
			"counterexample_transition_progress_constraint_count": len(
				tuple(counterexample_progress_rule_groups or ()),
			),
			"repair_constraint_count": len(repair_reports),
			"atomic_progress_constraint_count": len(atomic_progress_reports),
			"matched_atomic_progress_constraint_count": sum(
				1 for report in atomic_progress_reports if report.matched
			),
			"rejected_atomic_progress_constraint_count": sum(
				1 for report in atomic_progress_reports if not report.matched
			),
			"matched_repair_constraint_count": sum(
				1 for report in repair_reports if report.matched
			),
			"rejected_repair_constraint_count": sum(
				1 for report in repair_reports if not report.matched
			),
			"repair_constraint_binding_reports": tuple(
				report.to_dict()
				for report in repair_reports
			),
			"atomic_progress_constraint_binding_reports": tuple(
				report.to_dict()
				for report in atomic_progress_reports
			),
			"training_goal_progression_count": sum(
				len(getattr(evidence, "goal_progressions", ()) or ())
				for evidence in tuple(training_transition_evidence or ())
			),
			"counterexample_goal_progression_count": sum(
				len(getattr(evidence, "goal_progressions", ()) or ())
				for evidence in tuple(counterexample_transition_evidence or ())
			),
			"training_atomic_achievement_count": sum(
				len(getattr(evidence, "atomic_achievements", ()) or ())
				for evidence in tuple(training_transition_evidence or ())
			),
			"counterexample_atomic_achievement_count": sum(
				len(getattr(evidence, "atomic_achievements", ()) or ())
				for evidence in tuple(counterexample_transition_evidence or ())
			),
			"trace_justified_selected_rule_count": sum(
				1
				for supporting in atomic_achievement_justifications(
					selected_rules,
					(
						*tuple(training_transition_evidence or ()),
						*tuple(counterexample_transition_evidence or ()),
					),
				).values()
				if supporting
			),
			"anti_unified_pattern_count": len(all_atomic_patterns),
			"training_anti_unified_pattern_count": len(training_atomic_patterns),
			"counterexample_anti_unified_pattern_count": len(
				counterexample_atomic_patterns,
			),
			"anti_unified_support_count": sum(
				pattern.support_count for pattern in all_atomic_patterns
			),
			"anti_unified_last_achiever_support_count": sum(
				pattern.last_achiever_support_count
				for pattern in all_atomic_patterns
			),
			"anti_unified_patterns": tuple(
				pattern.to_dict() for pattern in all_atomic_patterns
			),
			"recursion_descent": dict(recursion_descent_audit),
		},
		"layer_c_goal_composer": {
			"target": "goal-conditioned conjunctive-goal composer rules",
			"schema_candidate_count": _layer_count(schema_candidates, "composer"),
			"external_candidate_count": _layer_count(external_candidates, "composer"),
			"explicit_goal_ordering_candidate_count": _layer_count(
				explicit_goal_ordering_candidates,
				"composer",
			),
			"goal_ordering_constraint_count": len(goal_ordering_reports),
			"matched_goal_ordering_constraint_count": sum(
				1 for report in goal_ordering_reports if report.matched
			),
			"rejected_goal_ordering_constraint_count": sum(
				1 for report in goal_ordering_reports if not report.matched
			),
			"goal_ordering_constraint_binding_reports": tuple(
				report.to_dict()
				for report in goal_ordering_reports
			),
			"candidate_count": _layer_count(candidate_rules, "composer"),
			"selected_rule_count": _layer_count(selected_rules, "composer"),
			"output_rule_count": _layer_count(output_rules, "composer"),
			"training_state_coverage_constraint_count": len(
				tuple(training_state_coverage_rule_groups or ()),
			),
			"counterexample_state_coverage_constraint_count": len(
				tuple(counterexample_state_coverage_rule_groups or ()),
			),
			"training_goal_ordering_count": sum(
				len(getattr(evidence, "goal_orderings", ()) or ())
				for evidence in tuple(training_transition_evidence or ())
			),
			"counterexample_goal_ordering_count": sum(
				len(getattr(evidence, "goal_orderings", ()) or ())
				for evidence in tuple(counterexample_transition_evidence or ())
			),
			"causal_interference_candidate_count": _ordering_rule_count(
				candidate_rules,
				"causal_order_",
			),
			"causal_interference_selected_count": _ordering_rule_count(
				selected_rules,
				"causal_order_",
			),
			"trace_ordering_candidate_count": _ordering_rule_count(
				candidate_rules,
				"order_",
			),
		},
		"sources": {
			"schema": {
				"candidate_count": len(tuple(schema_candidates or ())),
				"layer_counts": _layer_counts(schema_candidates),
			},
			"external_sketch": {
				"policy_count": len(tuple(paper_policy_audits or ())),
				"candidate_count": len(tuple(external_candidates or ())),
				"layer_counts": _layer_counts(external_candidates),
				"feature_count": sum(
					audit.feature_count
					for audit in tuple(paper_policy_audits or ())
				),
				"bound_feature_count": sum(
					audit.bound_feature_count
					for audit in tuple(paper_policy_audits or ())
				),
				"unsupported_feature_count": sum(
					len(audit.unsupported_features)
					for audit in tuple(paper_policy_audits or ())
				),
				"raw_rule_count": sum(
					audit.rule_count
					for audit in tuple(paper_policy_audits or ())
				),
				"compiled_rule_count": sum(
					1
					for report in tuple(external_rule_reports or ())
					if report.compiled
				),
				"rejected_rule_count": sum(
					1
					for report in tuple(external_rule_reports or ())
					if not report.compiled
				),
			},
			"counterexample_repair": {
				"candidate_count": len(tuple(repair_synthesized_candidates or ())),
				"layer_counts": _layer_counts(repair_synthesized_candidates),
			},
			"counterexample_goal_ordering": {
				"candidate_count": len(tuple(explicit_goal_ordering_candidates or ())),
				"layer_counts": _layer_counts(explicit_goal_ordering_candidates),
			},
			"training_transition_systems": _transition_evidence_summary(
				training_transition_evidence,
			),
			"counterexample_transition_systems": _transition_evidence_summary(
				counterexample_transition_evidence,
			),
		},
	}


def _layer_count(rules: Sequence[LiftedPlanRule], layer: str) -> int:
	return sum(1 for rule in tuple(rules or ()) if rule.layer == layer)


def _ordering_rule_count(rules: Sequence[LiftedPlanRule], prefix: str) -> int:
	"""Count composer rules whose capability marks a given ordering source.

	The trace-evidence prefix ``order_`` must not also match schema causal rules
	tagged ``causal_order_``; matching is therefore exact on the capability stem.
	"""

	def _matches(capability: str) -> bool:
		if prefix == "order_":
			return capability.startswith("order_") and not capability.startswith(
				"causal_order_",
			)
		return capability.startswith(prefix)

	return sum(
		1
		for rule in tuple(rules or ())
		if any(_matches(capability) for capability in rule.capabilities)
	)


def _layer_counts(rules: Sequence[LiftedPlanRule]) -> dict[str, int]:
	counts: dict[str, int] = {}
	for rule in tuple(rules or ()):
		counts[rule.layer] = counts.get(rule.layer, 0) + 1
	return counts


def _transition_evidence_summary(evidence_items: Sequence[object]) -> dict[str, int]:
	items = tuple(evidence_items or ())
	return {
		"problem_count": len(items),
		"explored_state_count": sum(
			int(getattr(evidence, "explored_state_count", 0) or 0)
			for evidence in items
		),
		"explored_transition_count": sum(
			int(getattr(evidence, "explored_transition_count", 0) or 0)
			for evidence in items
		),
		"plan_length": sum(
			int(getattr(evidence, "plan_length", 0) or 0)
			for evidence in items
		),
		"goal_fact_count": sum(
			len(getattr(evidence, "goal_facts", ()) or ())
			for evidence in items
		),
		"goal_ordering_count": sum(
			len(getattr(evidence, "goal_orderings", ()) or ())
			for evidence in items
		),
		"goal_progression_count": sum(
			len(getattr(evidence, "goal_progressions", ()) or ())
			for evidence in items
		),
		"atomic_achievement_count": sum(
			len(getattr(evidence, "atomic_achievements", ()) or ())
			for evidence in items
		),
	}


def _counterexample_refinement_summary(
	*,
	counterexample_transition_evidence: Sequence[object],
	counterexample_progress_rule_groups: Sequence[object],
	counterexample_state_coverage_rule_groups: Sequence[object],
	explicit_refinement_constraints: Sequence[object],
	repair_rule_groups: Sequence[ClingoRequiredRuleGroup],
	repair_binding_reports: Sequence[RepairConstraintBindingReport],
	goal_ordering_rule_groups: Sequence[ClingoRequiredRuleGroup],
	goal_ordering_binding_reports: Sequence[GoalOrderingConstraintBindingReport],
	atomic_progress_rule_groups: Sequence[ClingoRequiredRuleGroup],
	atomic_progress_binding_reports: Sequence[AtomicProgressConstraintBindingReport],
) -> dict[str, object]:
	"""Summarize hard selector constraints induced by counterexamples."""

	evidence_items = tuple(counterexample_transition_evidence or ())
	progress_groups = tuple(counterexample_progress_rule_groups or ())
	state_groups = tuple(counterexample_state_coverage_rule_groups or ())
	explicit_constraints = tuple(explicit_refinement_constraints or ())
	repair_groups = tuple(repair_rule_groups or ())
	repair_reports = tuple(repair_binding_reports or ())
	goal_ordering_groups = tuple(goal_ordering_rule_groups or ())
	goal_ordering_reports = tuple(goal_ordering_binding_reports or ())
	atomic_progress_groups = tuple(atomic_progress_rule_groups or ())
	atomic_progress_reports = tuple(atomic_progress_binding_reports or ())
	return {
		"problem_count": len(evidence_items),
		"problem_names": tuple(
			str(getattr(evidence, "problem_name", ""))
			for evidence in evidence_items
		),
		"transition_progress_required_group_count": len(progress_groups),
		"state_coverage_required_group_count": len(state_groups),
		"explicit_refinement_constraint_count": len(explicit_constraints),
		"explicit_repair_constraint_count": sum(
			1
			for constraint in explicit_constraints
			if getattr(constraint, "constraint_type", "") == (
				"counterexample_atomic_precondition_repair"
			)
		),
		"repair_required_group_count": len(repair_groups),
		"atomic_progress_required_group_count": len(atomic_progress_groups),
		"atomic_progress_constraint_count": len(atomic_progress_reports),
		"matched_atomic_progress_constraint_count": sum(
			1 for report in atomic_progress_reports if report.matched
		),
		"rejected_atomic_progress_constraint_count": sum(
			1 for report in atomic_progress_reports if not report.matched
		),
		"goal_ordering_required_group_count": len(goal_ordering_groups),
		"goal_ordering_constraint_count": len(goal_ordering_reports),
		"matched_goal_ordering_constraint_count": sum(
			1 for report in goal_ordering_reports if report.matched
		),
		"rejected_goal_ordering_constraint_count": sum(
			1 for report in goal_ordering_reports if not report.matched
		),
		"matched_repair_constraint_count": sum(
			1 for report in repair_reports if report.matched
		),
		"rejected_repair_constraint_count": sum(
			1 for report in repair_reports if not report.matched
		),
		"repair_constraint_binding_reports": tuple(
			report.to_dict()
			for report in repair_reports
		),
		"repair_required_groups": tuple(
			{
				"name": group.name,
				"constraint_type": "counterexample_atomic_precondition_repair",
				"rule_names": group.rule_names,
			}
			for group in repair_groups
		),
		"atomic_progress_required_groups": tuple(
			{
				"name": group.name,
				"constraint_type": "counterexample_atomic_progress",
				"rule_names": group.rule_names,
			}
			for group in atomic_progress_groups
		),
		"atomic_progress_constraint_binding_reports": tuple(
			report.to_dict()
			for report in atomic_progress_reports
		),
		"goal_ordering_required_groups": tuple(
			{
				"name": group.name,
				"constraint_type": "counterexample_goal_ordering",
				"rule_names": group.rule_names,
			}
			for group in goal_ordering_groups
		),
		"goal_ordering_constraint_binding_reports": tuple(
			report.to_dict()
			for report in goal_ordering_reports
		),
		"rejected_goal_ordering_constraints": tuple(
			report.to_dict()
			for report in goal_ordering_reports
			if not report.matched
		),
		"rejected_repair_constraints": tuple(
			report.to_dict()
			for report in repair_reports
			if not report.matched
		),
		"rejected_atomic_progress_constraints": tuple(
			report.to_dict()
			for report in atomic_progress_reports
			if not report.matched
		),
		"required_group_count": (
			len(progress_groups)
			+ len(state_groups)
			+ len(repair_groups)
			+ len(goal_ordering_groups)
			+ len(atomic_progress_groups)
		),
		"required_group_types": tuple(
			group_type
			for group_type, groups in (
				("counterexample_transition_progress", progress_groups),
				("counterexample_state_coverage", state_groups),
				("counterexample_atomic_precondition_repair", repair_groups),
				("counterexample_goal_ordering", goal_ordering_groups),
				("counterexample_atomic_progress", atomic_progress_groups),
			)
			if groups
		),
		"base_training_pollution": False,
	}


def _order_output_rules(rules: Sequence[LiftedPlanRule]) -> tuple[LiftedPlanRule, ...]:
	"""Order plans for deterministic first-applicable AgentSpeak execution."""

	return tuple(sorted(tuple(rules), key=_output_rule_sort_key))


def _output_rule_sort_key(rule: LiftedPlanRule) -> tuple[int, int, int, str]:
	priority = _rule_execution_priority(rule)
	return (
		priority,
		_context_specificity_sort_value(rule, priority),
		len(rule.body),
		rule.name,
	)


def _context_specificity_sort_value(rule: LiftedPlanRule, priority: int) -> int:
	if priority == 4:
		return len(rule.context)
	return -len(rule.context)


def _rule_execution_priority(rule: LiftedPlanRule) -> int:
	if rule.layer == "composer" and any(
		capability.startswith("order_")
		for capability in rule.capabilities
	):
		return 0
	if rule.layer == "composer" and rule.rationale.startswith("external_policy:"):
		return 1
	if rule.layer == "composer":
		return 2
	if not rule.body:
		return 3
	if _is_direct_action_rule(rule):
		return 4
	return 5


def _is_direct_action_rule(rule: LiftedPlanRule) -> bool:
	return bool(rule.body) and all(
		step.kind in {"action", "primitive_action"}
		for step in rule.body
	)


def _external_rule_capabilities(rules: Sequence[LiftedPlanRule]) -> tuple[str, ...]:
	return tuple(
		capability
		for rule in rules
		if rule.rationale.startswith("external_policy:")
		for capability in rule.capabilities
	)


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
