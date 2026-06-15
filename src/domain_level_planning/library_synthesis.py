"""
Unified domain-level synthesis from PDDL, training evidence, and paper policies.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep, AgentSpeakPlan, AgentSpeakTrigger, PlanLibrary
from utils.pddl_parser import PDDLParser

from .architecture_contract import architecture_gap_summary
from .architecture_contract import domain_level_architecture_contract
from .clingo_backend import ClingoSketchRuleSelector
from .gp_backends import BackendManifest, LearnerSketchesRunConfig, LearnerSketchesRunResult
from .gp_backends import run_learner_sketches
from .library_verifier import BoundedLibraryValidationReport
from .library_verifier import validate_library_on_bounded_transition_systems
from .models import LiftedCall, LiftedPlanRule
from .paper_backend_audit import PaperPolicyAuditReport
from .paper_backend_audit import audit_learned_policy_for_asl_binding
from .pddl_support import assert_compilable_pddl_files
from .schema_synthesis import _candidate_rules_from_domain
from .schema_synthesis import _required_capabilities
from .schema_synthesis import _training_evidence
from .schema_synthesis import _validate_selected_rules_against_transition_progress
from .schema_synthesis import composer_state_coverage_required_rule_groups
from .schema_synthesis import transition_progress_required_rule_groups


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


def synthesize_domain_level_asl_library(
	*,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path] = (),
	counterexample_problem_files: Sequence[str | Path] = (),
	external_sketch_policies: Sequence[ExternalSketchPolicySource] = (),
	learner_sketches_backend: BackendManifest | None = None,
	learner_sketches_runs: Sequence[LearnerSketchesRunConfig] = (),
	synthesis_profile: str = "bootstrap",
) -> UnifiedSynthesisResult:
	"""Synthesize one lifted domain-level ASL library through the unified path."""

	profile = _normalize_synthesis_profile(synthesis_profile)
	training_problem_files = tuple(training_problem_files or ())
	counterexample_problem_files = tuple(counterexample_problem_files or ())
	assert_compilable_pddl_files(
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
	candidate_rules = _deduplicate_rules(schema_candidates + external_candidates)
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
		required_rule_groups=(*progress_rule_groups, *state_coverage_rule_groups),
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
		"auto_learner_sketches_run_count": len(tuple(learner_sketches_runs or ())),
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
		"candidate_count": len(candidate_rules),
		"selected_rule_count": len(selection.rules),
		"output_rule_count": len(output_rules),
		"selector_progress_constraint_count": len(progress_rule_groups),
		"selector_training_progress_constraint_count": len(training_progress_rule_groups),
		"selector_counterexample_progress_constraint_count": len(
			counterexample_progress_rule_groups,
		),
		"selector_state_coverage_constraint_count": len(state_coverage_rule_groups),
		"selector_training_state_coverage_constraint_count": len(
			training_state_coverage_rule_groups,
		),
		"selector_counterexample_state_coverage_constraint_count": len(
			counterexample_state_coverage_rule_groups,
		),
		"rejected_external_feature_count": len(rejected_features),
		"candidate_sources": _candidate_source_counts(candidate_rules),
		"selected_candidate_sources": _candidate_source_counts(selection.rules),
		"output_candidate_sources": _candidate_source_counts(output_rules),
		"selection_cost": selection.cost,
		"paper_policy_audits": tuple(
			audit.to_dict()
			for audit in paper_policy_audits
		),
		"external_rule_binding_reports": tuple(
			report.to_dict()
			for report in external_rule_reports
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


def _body_step_to_lifted_call(step: AgentSpeakBodyStep) -> LiftedCall:
	kind = "action" if step.kind in {"action", "primitive_action"} else step.kind
	return LiftedCall(kind, step.symbol, step.arguments)


def _deduplicate_rules(rules: Sequence[LiftedPlanRule]) -> tuple[LiftedPlanRule, ...]:
	seen: set[tuple[object, ...]] = set()
	deduplicated: list[LiftedPlanRule] = []
	for rule in rules:
		key = (
			rule.head,
			rule.context,
			rule.body,
			rule.layer,
		)
		if key in seen:
			continue
		seen.add(key)
		deduplicated.append(rule)
	return tuple(deduplicated)


def _candidate_source_counts(rules: Sequence[LiftedPlanRule]) -> dict[str, int]:
	counts: dict[str, int] = {}
	for rule in rules:
		source = (
			"external_sketch"
			if rule.rationale.startswith("external_policy:")
			else "schema"
		)
		counts[source] = counts.get(source, 0) + 1
	return counts


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
