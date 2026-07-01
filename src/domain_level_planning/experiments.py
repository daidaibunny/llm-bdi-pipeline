"""
Reproducible domain-level lifted-library experiment reporting.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
from pathlib import Path
import re
import signal
from time import perf_counter
from typing import Iterator, Sequence

from plan_library.rendering import render_plan_library_asl
from utils.pddl_parser import PDDLParser

from .library_contract import audit_domain_level_library_contract
from .library_executor import evaluate_library_on_problem
from .library_synthesis import ExternalSketchPolicySource
from .library_synthesis import synthesize_domain_level_asl_library
from .pddl_types import declared_type_names, type_guard_symbol
from .refinement import synthesize_with_counterexample_refinement
from .gp_router import GPRouteDecision
from .gp_router import route_generalized_planner


def run_domain_level_experiment(
	*,
	experiment_name: str,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path],
	evaluation_problem_files: Sequence[str | Path],
	domain_id: str | None = None,
	benchmark_class_id: str | None = None,
	counterexample_problem_files: Sequence[str | Path] = (),
	external_sketch_policies: Sequence[ExternalSketchPolicySource] = (),
	synthesis_profile: str = "bootstrap",
	max_execution_steps: int = 10000,
	max_depth: int = 1000,
	evaluation_timeout_seconds: float | None = None,
	disabled_synthesis_mechanisms: Sequence[str] = (),
	use_synthesis_planner_traces: bool = False,
	synthesis_planner_executable: str | Path | None = None,
	synthesis_planner_timeout_seconds: int = 60,
	use_counterexample_refinement: bool = False,
	max_refinement_rounds: int = 1,
	ablation_label: str | None = None,
	baselines: Sequence[dict[str, object]] = (),
	fail_on_paper_profile_failure: bool = True,
) -> dict[str, object]:
	"""Run one reproducible domain-level library experiment."""

	route_decision = _route_decision(
		domain_file=domain_file,
		domain_id=domain_id,
		benchmark_class_id=benchmark_class_id,
	)
	synthesis_started = perf_counter()
	if use_counterexample_refinement:
		refined = synthesize_with_counterexample_refinement(
			domain_file=domain_file,
			training_problem_files=training_problem_files,
			heldout_problem_files=evaluation_problem_files,
			counterexample_problem_files=counterexample_problem_files,
			external_sketch_policies=external_sketch_policies,
			synthesis_profile=synthesis_profile,
			disabled_synthesis_mechanisms=disabled_synthesis_mechanisms,
			use_synthesis_planner_traces=use_synthesis_planner_traces,
			synthesis_planner_executable=synthesis_planner_executable,
			synthesis_planner_timeout_seconds=synthesis_planner_timeout_seconds,
			max_refinement_rounds=max_refinement_rounds,
			max_execution_steps=max_execution_steps,
			max_depth=max_depth,
		)
		result = refined.final_result
		refinement_trace = refined.to_dict()
	else:
		result = synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=training_problem_files,
			counterexample_problem_files=counterexample_problem_files,
			external_sketch_policies=external_sketch_policies,
			synthesis_profile=synthesis_profile,
			disabled_synthesis_mechanisms=disabled_synthesis_mechanisms,
			use_synthesis_planner_traces=use_synthesis_planner_traces,
			synthesis_planner_executable=synthesis_planner_executable,
			synthesis_planner_timeout_seconds=synthesis_planner_timeout_seconds,
			fail_on_paper_profile_failure=fail_on_paper_profile_failure,
		)
		refinement_trace = None
	synthesis_duration = perf_counter() - synthesis_started
	plan_library = result.plan_library
	asl = render_plan_library_asl(plan_library)
	domain = PDDLParser.parse_domain(domain_file)
	evaluation_started = perf_counter()
	evaluation_with_runtime = tuple(
		_evaluate_problem_with_runtime(
			plan_library=plan_library,
			domain_file=domain_file,
			problem_file=problem_file,
			max_execution_steps=max_execution_steps,
			max_depth=max_depth,
			timeout_seconds=evaluation_timeout_seconds,
		)
		for problem_file in tuple(evaluation_problem_files or ())
	)
	evaluation_duration = perf_counter() - evaluation_started
	evaluation_results = tuple(item[0] for item in evaluation_with_runtime)
	evaluation_runtimes = tuple(item[1] for item in evaluation_with_runtime)
	contract = audit_domain_level_library_contract(
		plan_library,
		declared_predicates=_declared_predicate_arities_with_type_guards(domain),
		declared_actions=domain.actions,
	)
	contract_dict = contract.to_dict()
	generated_output_audit = _generated_output_audit(contract_dict)
	solved_count = sum(1 for item in evaluation_results if bool(item["solved"]))
	failed = tuple(item for item in evaluation_results if not bool(item["solved"]))
	return {
		"experiment_name": experiment_name,
		"domain_file": _resolved(domain_file),
		"generation_mode": result.report["generation_mode"],
		"gp_route_decision": (
			route_decision.to_dict()
			if route_decision is not None
			else None
		),
		"experiment_protocol": _experiment_protocol(
			synthesis_profile=synthesis_profile,
			external_sketch_policies=external_sketch_policies,
			use_counterexample_refinement=use_counterexample_refinement,
			use_synthesis_planner_traces=use_synthesis_planner_traces,
			disabled_synthesis_mechanisms=disabled_synthesis_mechanisms,
			ablation_label=ablation_label,
			baselines=baselines,
		),
		"paper_quality_summary": _paper_quality_summary(result.report),
		"train_problem_count": len(tuple(training_problem_files or ())),
		"training_problem_files": [
			_resolved(path) for path in tuple(training_problem_files or ())
		],
		"counterexample_problem_count": len(tuple(counterexample_problem_files or ())),
		"counterexample_problem_files": [
			_resolved(path) for path in tuple(counterexample_problem_files or ())
		],
		"evaluation_problem_count": len(evaluation_results),
		"evaluation_problem_files": [
			_resolved(path) for path in tuple(evaluation_problem_files or ())
		],
		"coverage": {
			"solved_count": solved_count,
			"failed_count": len(failed),
			"coverage_ratio": (
				solved_count / len(evaluation_results)
				if evaluation_results
				else 0.0
			),
			"failed_problem_names": [
				str(item["problem_name"]) for item in failed
			],
		},
		"failure_analysis": _failure_analysis(evaluation_results),
		"evaluation_results": list(evaluation_results),
		"plan_library": {
			"domain_name": plan_library.domain_name,
			"plan_count": len(tuple(plan_library.plans or ())),
			"initial_belief_count": len(tuple(plan_library.initial_beliefs or ())),
			"primitive_action_call_count": _body_step_count(
				plan_library,
				{"action", "primitive_action"},
			),
			"subgoal_call_count": _body_step_count(plan_library, {"subgoal"}),
			"asl_line_count": len([line for line in asl.splitlines() if line.strip()]),
		},
		"runtime_seconds": {
			"synthesis": synthesis_duration,
			"evaluation_total": evaluation_duration,
			"evaluation_by_problem": list(evaluation_runtimes),
		},
		"domain_level_contract": contract_dict,
		"generated_output_audit": generated_output_audit,
		"pddl_to_asl_symbol_map": result.report.get("pddl_to_asl_symbol_map"),
		"validation_scope": _validation_scope(
			bounded_validation=result.report.get("bounded_validation"),
			evaluation_results=evaluation_results,
		),
		"no_synthetic_names": (
			"achieve_" not in asl
			and "transition_" not in asl
			and "dfa_state" not in asl
		),
		"bounded_validation": result.report.get("bounded_validation"),
		"synthesis_report": dict(result.report),
		"learning_audit": _learning_audit(result.report),
		"refinement_analysis": _refinement_analysis(refinement_trace),
		"refinement_trace": refinement_trace,
		"asl": asl,
	}


def _route_decision(
	*,
	domain_file: str | Path,
	domain_id: str | None,
	benchmark_class_id: str | None,
) -> GPRouteDecision | None:
	if not benchmark_class_id:
		return None
	return route_generalized_planner(
		domain_id=domain_id or Path(domain_file).stem,
		benchmark_class_id=benchmark_class_id,
		allow_baseline_schema_lift=True,
	)


def _paper_quality_summary(synthesis_report: dict[str, object]) -> dict[str, object]:
	profile = str(synthesis_report.get("synthesis_profile") or "bootstrap")
	failures = tuple(str(item) for item in synthesis_report.get("paper_profile_failures") or ())
	external_policy_count = int(synthesis_report.get("external_policy_count") or 0)
	selected_sources = dict(synthesis_report.get("selected_candidate_sources") or {})
	output_sources = dict(synthesis_report.get("output_candidate_sources") or {})
	selected_external_rule_names = _external_sketch_rule_names(
		synthesis_report.get("selected_rule_manifest"),
	)
	output_external_rule_names = _external_sketch_rule_names(
		synthesis_report.get("output_rule_manifest"),
	)
	return {
		"synthesis_profile": profile,
		"paper_profile_ready": bool(synthesis_report.get("paper_profile_ready")),
		"schema_only_bootstrap": _is_schema_only_bootstrap(
			synthesis_report=synthesis_report,
			profile=profile,
			external_policy_count=external_policy_count,
		),
		"external_policy_count": external_policy_count,
		"selected_external_sketch_candidate_count": int(
			selected_sources.get("external_sketch") or 0,
		),
		"output_external_sketch_candidate_count": int(
			output_sources.get("external_sketch") or 0,
		),
		"selected_external_sketch_rule_names": selected_external_rule_names,
		"output_external_sketch_rule_names": output_external_rule_names,
		"external_policy_required_for_paper_profile": any(
			"external learned sketch policy" in failure
			for failure in failures
		),
		"blocking_failure_count": len(failures),
		"blocking_failures": list(failures),
	}


def _declared_predicate_arities_with_type_guards(domain: object) -> dict[str, int]:
	arities = {
		str(getattr(predicate, "name")): len(tuple(getattr(predicate, "parameters", ()) or ()))
		for predicate in tuple(getattr(domain, "predicates", ()) or ())
	}
	for type_name in declared_type_names(tuple(getattr(domain, "types", ()) or ())):
		arities.setdefault(type_guard_symbol(type_name), 1)
	return arities


def _external_sketch_rule_names(raw_manifest: object) -> list[str]:
	"""Return selected/output learned-sketch rule names from a synthesis manifest."""

	names: list[str] = []
	for raw_item in tuple(raw_manifest or ()):
		if not isinstance(raw_item, dict):
			continue
		if raw_item.get("source") != "external_sketch":
			continue
		name = str(raw_item.get("name") or "").strip()
		if name:
			names.append(name)
	return names


def _is_schema_only_bootstrap(
	*,
	synthesis_report: dict[str, object],
	profile: str,
	external_policy_count: int,
) -> bool:
	if profile != "bootstrap" or external_policy_count != 0:
		return False
	refinement_counts = (
		"counterexample_problem_count",
		"repair_synthesized_candidate_count",
		"explicit_goal_ordering_candidate_count",
		"state_coverage_synthesized_candidate_count",
	)
	return all(int(synthesis_report.get(key) or 0) == 0 for key in refinement_counts)


def _experiment_protocol(
	*,
	synthesis_profile: str,
	external_sketch_policies: Sequence[ExternalSketchPolicySource],
	use_counterexample_refinement: bool,
	use_synthesis_planner_traces: bool,
	disabled_synthesis_mechanisms: Sequence[str],
	ablation_label: str | None,
	baselines: Sequence[dict[str, object]] = (),
) -> dict[str, object]:
	mechanism_status = _ablation_mechanism_status(
		synthesis_profile=synthesis_profile,
		external_policy_count=len(tuple(external_sketch_policies or ())),
		use_counterexample_refinement=use_counterexample_refinement,
		use_synthesis_planner_traces=use_synthesis_planner_traces,
		disabled_synthesis_mechanisms=disabled_synthesis_mechanisms,
	)
	ablation = _ablation_record(
		label=ablation_label,
		synthesis_profile=synthesis_profile,
		external_sketch_policies=external_sketch_policies,
		use_counterexample_refinement=use_counterexample_refinement,
		use_synthesis_planner_traces=use_synthesis_planner_traces,
		disabled_synthesis_mechanisms=disabled_synthesis_mechanisms,
		mechanism_status=mechanism_status,
	)
	return {
		"scope": "bounded_domain_level_lifted_asl_evaluation",
		"training_source": "provided_pddl_training_problems",
		"evaluation_source": "provided_pddl_evaluation_problems",
		"synthesis_profile": str(synthesis_profile or "bootstrap"),
		"external_policy_count": len(tuple(external_sketch_policies or ())),
		"disabled_synthesis_mechanisms": list(
			tuple(disabled_synthesis_mechanisms or ()),
		),
		"mechanism_status": mechanism_status,
		"runtime_planner": "none",
		"baselines": _baseline_records(baselines),
		"ablations": [] if ablation is None else [ablation],
		"limitations": [
			"coverage is measured only over the listed evaluation PDDL problems",
			"no IPC-wide baseline table is implied by this smoke protocol",
		],
	}


def _baseline_records(
	baselines: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
	records: list[dict[str, object]] = []
	for baseline in tuple(baselines or ()):
		item = dict(baseline or {})
		normalized = {
			"label": str(item.get("label") or ""),
			"domain_name": str(item.get("domain_name") or ""),
			"solver_family": str(item.get("solver_family") or "external_baseline"),
			"solved_count": int(item.get("solved_count") or 0),
			"failed_count": int(item.get("failed_count") or 0),
			"coverage_ratio": float(item.get("coverage_ratio") or 0.0),
			"runtime_planner": str(item.get("runtime_planner") or "offline_baseline_only"),
			"notes": str(item.get("notes") or ""),
		}
		for optional_field in (
			"comparison_scope",
			"domain_level_artifact",
			"evidence_source",
			"coverage_semantics",
			"validation",
		):
			if optional_field in item:
				normalized[optional_field] = item[optional_field]
		records.append(normalized)
	return records


def _ablation_record(
	*,
	label: str | None,
	synthesis_profile: str,
	external_sketch_policies: Sequence[ExternalSketchPolicySource],
	use_counterexample_refinement: bool,
	use_synthesis_planner_traces: bool,
	disabled_synthesis_mechanisms: Sequence[str],
	mechanism_status: dict[str, str],
) -> dict[str, object] | None:
	text = str(label or "").strip()
	if not text:
		return None
	enabled = _mechanisms_by_status(mechanism_status, "enabled")
	disabled = _mechanisms_by_status(mechanism_status, "disabled")
	return {
		"label": text,
		"synthesis_profile": str(synthesis_profile or "bootstrap"),
		"external_policy_count": len(tuple(external_sketch_policies or ())),
		"counterexample_refinement": bool(use_counterexample_refinement),
		"use_synthesis_planner_traces": bool(use_synthesis_planner_traces),
		"disabled_synthesis_mechanisms": list(
			tuple(disabled_synthesis_mechanisms or ()),
		),
		"runtime_planner": "none",
		"mechanism_status": dict(mechanism_status),
		"enabled_mechanisms": list(enabled),
		"disabled_mechanisms": list(disabled),
	}


def _ablation_mechanism_status(
	*,
	synthesis_profile: str,
	external_policy_count: int,
	use_counterexample_refinement: bool,
	use_synthesis_planner_traces: bool,
	disabled_synthesis_mechanisms: Sequence[str],
) -> dict[str, str]:
	"""Return the mechanism switches actually used by one experiment row."""

	return {
		"external_sketch_evidence": (
			"enabled" if external_policy_count > 0 else "disabled"
		),
		"counterexample_refinement": (
			"enabled" if use_counterexample_refinement else "disabled"
		),
		"offline_synthesis_planner_traces": (
			"enabled" if use_synthesis_planner_traces else "disabled"
		),
		"layer_c_ordering": (
			"disabled"
			if "layer_c_ordering" in set(disabled_synthesis_mechanisms or ())
			else "enabled"
		),
		"paper_profile_gate": (
			"enabled" if str(synthesis_profile or "bootstrap") == "paper" else "disabled"
		),
	}


def _mechanisms_by_status(
	mechanism_status: dict[str, str],
	status: str,
) -> tuple[str, ...]:
	order = (
		"external_sketch_evidence",
		"counterexample_refinement",
		"offline_synthesis_planner_traces",
		"layer_c_ordering",
		"paper_profile_gate",
	)
	return tuple(
		name
		for name in order
		if str(mechanism_status.get(name) or "") == status
	)


def _learning_audit(synthesis_report: dict[str, object]) -> dict[str, object]:
	"""Expose compact learner evidence summaries in experiment reports."""

	matrix = dict(synthesis_report.get("evidence_matrix") or {})
	layer_b = dict(matrix.get("layer_b_atomic_modules") or {})
	layer_c = dict(matrix.get("layer_c_goal_composer") or {})
	strategy_groups = tuple(layer_b.get("atomic_action_strategy_groups") or ())
	atomic_module_proofs = tuple(layer_b.get("atomic_module_proofs") or ())
	strategy_portfolio = dict(layer_b.get("atomic_strategy_portfolio") or {})
	strategy_candidates = tuple(
		candidate
		for group in strategy_groups
		for candidate in tuple(dict(group).get("candidates") or ())
	)
	composer_rule_proofs = tuple(layer_c.get("composer_rule_proofs") or ())
	composer_candidates = tuple(layer_c.get("composer_candidate_evidence") or ())
	return {
		"layer_b_atomic_modules": {
			"atomic_module_proof_count": len(atomic_module_proofs),
			"justified_atomic_module_proof_count": sum(
				1
				for proof in atomic_module_proofs
				if dict(proof).get("proof_status") == "justified"
			),
			"unjustified_atomic_module_proof_count": sum(
				1
				for proof in atomic_module_proofs
				if dict(proof).get("proof_status") != "justified"
			),
			"atomic_action_strategy_group_count": len(strategy_groups),
			"atomic_action_strategy_candidate_count": len(strategy_candidates),
			"selected_atomic_action_strategy_candidate_count": sum(
				1 for candidate in strategy_candidates if bool(candidate.get("selected"))
			),
			"rejected_atomic_action_strategy_candidate_count": sum(
				1 for candidate in strategy_candidates if not bool(candidate.get("selected"))
			),
			"atomic_strategy_portfolio_group_count": int(
				strategy_portfolio.get("group_count") or 0,
			),
			"atomic_strategy_portfolio_multi_strategy_group_count": int(
				strategy_portfolio.get("multi_strategy_group_count") or 0,
			),
			"atomic_strategy_portfolio_trace_backed_selected_group_count": int(
				strategy_portfolio.get("trace_backed_selected_group_count") or 0,
			),
			"atomic_strategy_portfolio_unjustified_selected_group_count": int(
				strategy_portfolio.get("unsafe_or_unjustified_selected_group_count") or 0,
			),
			"atomic_strategy_portfolio_dominated_rejected_candidate_count": int(
				strategy_portfolio.get("dominated_rejected_candidate_count") or 0,
			),
			"atomic_action_strategy_verdict_counts": _count_by_key(
				strategy_candidates,
				"verdict",
			),
			"atomic_action_strategy_rejection_counts": _count_by_key(
				(
					candidate
					for candidate in strategy_candidates
					if candidate.get("rejection_reason") is not None
				),
				"rejection_reason",
			),
		},
		"layer_c_goal_composer": {
			"composer_rule_proof_count": len(composer_rule_proofs),
			"justified_composer_rule_proof_count": sum(
				1
				for proof in composer_rule_proofs
				if dict(proof).get("proof_status") == "justified"
			),
			"unjustified_composer_rule_proof_count": sum(
				1
				for proof in composer_rule_proofs
				if dict(proof).get("proof_status") != "justified"
			),
			"composer_candidate_count": len(composer_candidates),
			"selected_composer_candidate_count": sum(
				1 for candidate in composer_candidates if bool(candidate.get("selected"))
			),
			"rejected_composer_candidate_count": sum(
				1 for candidate in composer_candidates if not bool(candidate.get("selected"))
			),
			"causal_interference_candidate_count": int(
				layer_c.get("causal_interference_candidate_count") or 0,
			),
			"causal_interference_selected_count": int(
				layer_c.get("causal_interference_selected_count") or 0,
			),
			"delete_threat_ordering_candidate_count": int(
				layer_c.get("delete_threat_ordering_candidate_count") or 0,
			),
			"delete_threat_ordering_selected_count": int(
				layer_c.get("delete_threat_ordering_selected_count") or 0,
			),
			"trace_ordering_candidate_count": int(
				layer_c.get("trace_ordering_candidate_count") or 0,
			),
			"trace_ordering_selected_count": int(
				layer_c.get("trace_ordering_selected_count") or 0,
			),
			"goal_agenda_edge_count": int(
				dict(layer_c.get("goal_agenda") or {}).get("edge_count") or 0,
			),
			"goal_agenda_support_edge_count": int(
				dict(layer_c.get("goal_agenda") or {}).get("support_edge_count") or 0,
			),
			"goal_agenda_delete_threat_edge_count": int(
				dict(layer_c.get("goal_agenda") or {}).get("delete_threat_edge_count")
				or 0,
			),
			"selected_goal_agenda_support_edge_count": int(
				dict(layer_c.get("goal_agenda") or {}).get(
					"selected_support_edge_count",
				)
				or 0,
			),
			"selected_goal_agenda_acyclic": bool(
				dict(layer_c.get("goal_agenda") or {}).get(
					"selected_support_agenda_acyclic",
					True,
				),
			),
			"composer_candidate_verdict_counts": _count_by_key(
				composer_candidates,
				"verdict",
			),
			"composer_ordering_kind_counts": _count_by_key(
				(
					candidate
					for candidate in composer_candidates
					if candidate.get("ordering_kind") is not None
				),
				"ordering_kind",
			),
			"max_schema_binding_ordering_candidate_depth": (
				_max_schema_binding_ordering_depth(composer_candidates)
			),
			"max_schema_binding_ordering_selected_depth": (
				_max_schema_binding_ordering_depth(composer_candidates, selected_only=True)
			),
			"max_schema_binding_ordering_depth": (
				_max_schema_binding_ordering_depth(composer_candidates, selected_only=True)
			),
			"composer_candidate_rejection_counts": _count_by_key(
				(
					candidate
					for candidate in composer_candidates
					if candidate.get("rejection_reason") is not None
				),
				"rejection_reason",
			),
		},
	}


def compare_domain_level_experiment_reports(
	reports: Sequence[dict[str, object]],
) -> dict[str, object]:
	"""Build a compact comparison table from already-run experiment reports."""

	rows = _comparison_rows_with_deltas(
		tuple(_comparison_row(report) for report in tuple(reports or ())),
	)
	baselines = tuple(
		_baseline_comparison_row(report, baseline)
		for report in tuple(reports or ())
		for baseline in tuple(
			dict(report.get("experiment_protocol") or {}).get("baselines") or (),
		)
	)
	return {
		"report_count": len(rows),
		"baseline_count": len(baselines),
		"best_by_coverage": _best_by_coverage(rows),
		"best_baseline_by_coverage": _best_baseline_by_coverage(baselines),
		"best_baseline_delta_vs_library": _best_baseline_delta_vs_library(baselines),
		"baselines": list(baselines),
		"paper_table_rows": _paper_table_rows(rows=rows, baselines=baselines),
		"rows": list(rows),
	}


def _comparison_row(report: dict[str, object]) -> dict[str, object]:
	protocol = dict(report.get("experiment_protocol") or {})
	coverage = dict(report.get("coverage") or {})
	plan_library = dict(report.get("plan_library") or {})
	paper_quality = dict(report.get("paper_quality_summary") or {})
	learning_audit = dict(report.get("learning_audit") or {})
	layer_b = dict(learning_audit.get("layer_b_atomic_modules") or {})
	layer_c = dict(learning_audit.get("layer_c_goal_composer") or {})
	runtime = dict(report.get("runtime_seconds") or {})
	failure = dict(report.get("failure_analysis") or {})
	ablation = _primary_ablation(protocol, report)
	evaluation_problem_count = int(report.get("evaluation_problem_count") or 0)
	return {
		"label": str(ablation.get("label") or report.get("experiment_name") or ""),
		"experiment_name": str(report.get("experiment_name") or ""),
		"domain_name": str(plan_library.get("domain_name") or ""),
		"synthesis_profile": str(protocol.get("synthesis_profile") or "bootstrap"),
		"external_policy_count": int(protocol.get("external_policy_count") or 0),
		"counterexample_refinement": bool(
			ablation.get("counterexample_refinement", False),
		),
		"use_synthesis_planner_traces": bool(
			ablation.get("use_synthesis_planner_traces", False),
		),
		"mechanism_status": dict(ablation.get("mechanism_status") or {}),
		"enabled_mechanisms": list(ablation.get("enabled_mechanisms") or ()),
		"disabled_mechanisms": list(ablation.get("disabled_mechanisms") or ()),
		"runtime_planner": str(protocol.get("runtime_planner") or "none"),
		"evaluation_problem_count": evaluation_problem_count,
		"solved_count": int(coverage.get("solved_count") or 0),
		"failed_count": int(coverage.get("failed_count") or 0),
		"coverage_ratio": float(coverage.get("coverage_ratio") or 0.0),
		"paper_profile_ready": bool(paper_quality.get("paper_profile_ready")),
		"schema_only_bootstrap": bool(paper_quality.get("schema_only_bootstrap")),
		"selected_external_sketch_candidate_count": int(
			paper_quality.get("selected_external_sketch_candidate_count") or 0,
		),
		"output_external_sketch_candidate_count": int(
			paper_quality.get("output_external_sketch_candidate_count") or 0,
		),
		"paper_blocking_failure_count": int(
			paper_quality.get("blocking_failure_count") or 0,
		),
		"plan_count": int(plan_library.get("plan_count") or 0),
		"primitive_action_call_count": int(
			plan_library.get("primitive_action_call_count") or 0,
		),
		"subgoal_call_count": int(plan_library.get("subgoal_call_count") or 0),
		"asl_line_count": int(plan_library.get("asl_line_count") or 0),
		"synthesis_runtime_seconds": float(runtime.get("synthesis") or 0.0),
		"evaluation_runtime_seconds": float(runtime.get("evaluation_total") or 0.0),
		"selected_atomic_action_strategy_candidate_count": int(
			layer_b.get("selected_atomic_action_strategy_candidate_count") or 0,
		),
		"selected_composer_candidate_count": int(
			layer_c.get("selected_composer_candidate_count") or 0,
		),
		"selected_goal_agenda_acyclic": bool(
			layer_c.get("selected_goal_agenda_acyclic", True),
		),
		"failure_reason_counts": dict(failure.get("failure_reason_counts") or {}),
	}


def _comparison_rows_with_deltas(
	rows: Sequence[dict[str, object]],
) -> tuple[dict[str, object], ...]:
	if not rows:
		return ()
	best = max(float(row.get("coverage_ratio") or 0.0) for row in rows)
	return tuple(
		{
			**dict(row),
			"coverage_delta_vs_best_library": (
				float(row.get("coverage_ratio") or 0.0) - best
			),
		}
		for row in rows
	)


def _baseline_comparison_row(
	report: dict[str, object],
	baseline: object,
) -> dict[str, object]:
	item = dict(baseline or {})
	library_coverage = float(
		dict(report.get("coverage") or {}).get("coverage_ratio") or 0.0,
	)
	baseline_coverage = float(item.get("coverage_ratio") or 0.0)
	solved_count = int(item.get("solved_count") or 0)
	failed_count = int(item.get("failed_count") or 0)
	return {
		"report_label": str(report.get("experiment_name") or ""),
		"label": str(item.get("label") or ""),
		"domain_name": str(
			item.get("domain_name")
			or dict(report.get("plan_library") or {}).get("domain_name")
			or "",
		),
		"solver_family": str(item.get("solver_family") or "external_baseline"),
		"solved_count": solved_count,
		"failed_count": failed_count,
		"evaluation_problem_count": solved_count + failed_count,
		"coverage_ratio": baseline_coverage,
		"library_coverage_ratio": library_coverage,
		"coverage_delta_vs_library": baseline_coverage - library_coverage,
		"runtime_planner": str(item.get("runtime_planner") or "offline_baseline_only"),
		"notes": str(item.get("notes") or ""),
		"comparison_scope": str(item.get("comparison_scope") or "coverage_baseline"),
		"domain_level_artifact": bool(item.get("domain_level_artifact", False)),
		"evidence_source": str(item.get("evidence_source") or ""),
		"coverage_semantics": str(item.get("coverage_semantics") or "executed"),
		"validation": item.get("validation"),
	}


def _paper_table_rows(
	*,
	rows: Sequence[dict[str, object]],
	baselines: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
	table_rows: list[dict[str, object]] = []
	for row in tuple(rows or ()):
		label = str(row.get("label") or "")
		table_rows.append(
			{
				"row_type": "library",
				"label": label,
				"macro_id": label,
				"domain_name": str(row.get("domain_name") or ""),
				"solved": _solved_text(row),
				"coverage_percent": _coverage_percent(row),
				"plan_count": int(row.get("plan_count") or 0),
				"runtime_planner": str(row.get("runtime_planner") or "none"),
				"mechanism_summary": _mechanism_summary(row),
				"paper_profile_ready": bool(row.get("paper_profile_ready")),
				"coverage_delta_vs_best_library": float(
					row.get("coverage_delta_vs_best_library") or 0.0,
				),
				"notes": _library_paper_note(row),
			},
		)
	for baseline in tuple(baselines or ()):
		label = str(baseline.get("label") or "")
		report_label = str(baseline.get("report_label") or "")
		table_rows.append(
			{
				"row_type": "baseline",
				"label": label,
				"macro_id": _baseline_macro_id(
					report_label=report_label,
					label=label,
				),
				"report_label": report_label,
				"domain_name": str(baseline.get("domain_name") or ""),
				"solver_family": str(baseline.get("solver_family") or ""),
				"solved": _solved_text(baseline),
				"coverage_percent": _coverage_percent(baseline),
				"plan_count": None,
				"runtime_planner": str(
					baseline.get("runtime_planner") or "offline_baseline_only",
				),
				"mechanism_summary": "baseline",
				"paper_profile_ready": None,
				"coverage_delta_vs_library": float(
					baseline.get("coverage_delta_vs_library") or 0.0,
				),
				"notes": _baseline_paper_note(baseline),
			},
		)
	return table_rows


def _baseline_macro_id(*, report_label: str, label: str) -> str:
	"""Return a stable result-macro key for a baseline row.

	Baseline labels intentionally repeat across experiment splits; for example,
	the per-problem planner baseline is named the same way for every split row.
	LaTeX result macros need the report label as part of the key so the generated
	file is importable without command redefinitions.
	"""

	if report_label and label:
		return f"{report_label}_{label}"
	return label or report_label or "baseline"


def _solved_text(row: dict[str, object]) -> str:
	solved = int(row.get("solved_count") or 0)
	total = int(row.get("evaluation_problem_count") or 0)
	if total <= 0:
		total = solved + int(row.get("failed_count") or 0)
	return f"{solved}/{total}"


def _coverage_percent(row: dict[str, object]) -> float:
	return round(100.0 * float(row.get("coverage_ratio") or 0.0), 1)


def _library_paper_note(row: dict[str, object]) -> str:
	if not bool(row.get("selected_goal_agenda_acyclic", True)):
		return "selected Layer C agenda is cyclic"
	failures = dict(row.get("failure_reason_counts") or {})
	if failures:
		return "; ".join(f"{key}: {value}" for key, value in sorted(failures.items()))
	if bool(row.get("schema_only_bootstrap")):
		return "schema-only bootstrap"
	if int(row.get("selected_external_sketch_candidate_count") or 0) > 0:
		return "selected external sketch evidence"
	return ""


def _baseline_paper_note(row: dict[str, object]) -> str:
	parts = []
	scope = str(row.get("comparison_scope") or "").strip()
	semantics = str(row.get("coverage_semantics") or "").strip()
	if scope and scope != "coverage_baseline":
		parts.append(scope)
	if semantics and semantics != "executed":
		parts.append(semantics)
	if bool(row.get("domain_level_artifact")):
		parts.append("domain-level")
	notes = str(row.get("notes") or "").strip()
	if notes:
		parts.append(notes)
	return "; ".join(parts)


def _mechanism_summary(row: dict[str, object]) -> str:
	enabled = tuple(str(item) for item in tuple(row.get("enabled_mechanisms") or ()))
	disabled = tuple(str(item) for item in tuple(row.get("disabled_mechanisms") or ()))
	if enabled:
		return "enabled: " + ", ".join(enabled)
	if disabled:
		return "disabled: " + ", ".join(disabled)
	return ""


def _primary_ablation(
	protocol: dict[str, object],
	report: dict[str, object],
) -> dict[str, object]:
	ablations = tuple(protocol.get("ablations") or ())
	if ablations:
		return dict(ablations[0])
	return {
		"label": report.get("experiment_name") or "",
		"counterexample_refinement": False,
		"use_synthesis_planner_traces": False,
		"mechanism_status": dict(protocol.get("mechanism_status") or {}),
		"enabled_mechanisms": _mechanisms_by_status(
			dict(protocol.get("mechanism_status") or {}),
			"enabled",
		),
		"disabled_mechanisms": _mechanisms_by_status(
			dict(protocol.get("mechanism_status") or {}),
			"disabled",
		),
	}


def _best_by_coverage(rows: Sequence[dict[str, object]]) -> str | None:
	if not rows:
		return None
	best = max(
		tuple(rows),
		key=lambda row: (
			float(row.get("coverage_ratio") or 0.0),
			int(row.get("solved_count") or 0),
			-int(row.get("failed_count") or 0),
		),
	)
	return str(best.get("label") or "")


def _best_baseline_by_coverage(rows: Sequence[dict[str, object]]) -> str | None:
	if not rows:
		return None
	best = _best_baseline_row(rows)
	return str(best.get("label") or "")


def _best_baseline_delta_vs_library(
	rows: Sequence[dict[str, object]],
) -> float | None:
	if not rows:
		return None
	best = _best_baseline_row(rows)
	return float(best.get("coverage_delta_vs_library") or 0.0)


def _best_baseline_row(rows: Sequence[dict[str, object]]) -> dict[str, object]:
	return max(
		tuple(rows),
		key=lambda row: (
			float(row.get("coverage_ratio") or 0.0),
			int(row.get("solved_count") or 0),
			-int(row.get("failed_count") or 0),
		),
	)


def format_comparison_latex_macros(comparison: dict[str, object]) -> str:
	"""Render stable LaTeX result macros from a comparison dictionary."""

	lines = [
		"% Auto-generated by scripts/compare_domain_level_experiments.py.",
		"% Re-run the comparison script after changing experiment reports.",
	]
	seen_prefixes: set[str] = set()
	for row in tuple(comparison.get("paper_table_rows") or ()):
		item = dict(row)
		prefix = _latex_macro_prefix(str(item.get("macro_id") or item.get("label") or "row"))
		if prefix in seen_prefixes:
			raise ValueError(
				"Duplicate LaTeX result macro prefix generated for row "
				f"{item.get('label')!r}: {prefix}",
			)
		seen_prefixes.add(prefix)
		lines.extend(
			[
				f"\\newcommand{{\\Result{prefix}Type}}{{{item.get('row_type', '')}}}",
				f"\\newcommand{{\\Result{prefix}Solved}}{{{item.get('solved', '')}}}",
				(
					f"\\newcommand{{\\Result{prefix}CoveragePercent}}"
					f"{{{float(item.get('coverage_percent') or 0.0):.1f}\\%}}"
				),
				f"\\newcommand{{\\Result{prefix}RuntimePlanner}}{{{item.get('runtime_planner', '')}}}",
				f"\\newcommand{{\\Result{prefix}Mechanisms}}{{{_latex_escape(str(item.get('mechanism_summary') or ''))}}}",
				f"\\newcommand{{\\Result{prefix}PlanCount}}{{{_latex_plan_count(item)}}}",
				f"\\newcommand{{\\Result{prefix}Notes}}{{{_latex_escape(str(item.get('notes') or ''))}}}",
			],
		)
	return "\n".join(lines) + "\n"


def _latex_macro_prefix(label: str) -> str:
	parts = tuple(part for part in re.split(r"[^A-Za-z0-9]+", label) if part)
	prefix = "".join(_latex_macro_part(part) for part in parts)
	if not prefix or prefix[0].isdigit():
		prefix = f"Row{prefix}"
	if len(prefix) > 40:
		digest = _latex_digest_suffix(label)
		prefix = f"{prefix[:24]}Hash{digest}"
	return prefix


def _latex_macro_part(part: str) -> str:
	"""Convert a label token into letters accepted in a LaTeX command name."""

	converted = "".join(_latex_digit_word(character) for character in part)
	return converted[:1].upper() + converted[1:] if converted else ""


def _latex_digest_suffix(label: str) -> str:
	"""Return a short all-letter digest accepted inside a LaTeX command name."""

	alphabet = "abcdefghijklmnop"
	hex_digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:8]
	return "".join(alphabet[int(character, 16)] for character in hex_digest)


def _latex_digit_word(character: str) -> str:
	digit_words = {
		"0": "Zero",
		"1": "One",
		"2": "Two",
		"3": "Three",
		"4": "Four",
		"5": "Five",
		"6": "Six",
		"7": "Seven",
		"8": "Eight",
		"9": "Nine",
	}
	return digit_words.get(character, character)


def _latex_plan_count(row: dict[str, object]) -> str:
	value = row.get("plan_count")
	return "--" if value is None else str(value)


def _latex_escape(value: str) -> str:
	return (
		value.replace("\\", "\\textbackslash{}")
		.replace("&", "\\&")
		.replace("%", "\\%")
		.replace("$", "\\$")
		.replace("#", "\\#")
		.replace("_", "-")
		.replace("{", "\\{")
		.replace("}", "\\}")
	)


def _count_by_key(items, key: str) -> dict[str, int]:
	counts: dict[str, int] = {}
	for item in tuple(items or ()):
		value = str(dict(item).get(key) or "unknown")
		counts[value] = counts.get(value, 0) + 1
	return dict(sorted(counts.items()))


def _max_schema_binding_ordering_depth(
	composer_candidates,
	*,
	selected_only: bool = False,
) -> int:
	return max(
		(
			int(dict(candidate).get("ordering_binding_depth") or 0)
			for candidate in tuple(composer_candidates or ())
			if dict(candidate).get("ordering_kind")
			== "schema_causal_precondition_binding_support"
			and (not selected_only or bool(dict(candidate).get("selected")))
		),
		default=0,
	)


def _body_step_count(plan_library, kinds: set[str]) -> int:
	return sum(
		1
		for plan in tuple(plan_library.plans or ())
		for step in tuple(plan.body or ())
		if step.kind in kinds
	)


def _validation_scope(
	*,
	bounded_validation: object,
	evaluation_results: Sequence[dict[str, object]],
) -> dict[str, object]:
	validation = dict(bounded_validation or {})
	return {
		"bounded_validation_problem_count": int(
			validation.get("checked_problem_count") or 0,
		),
		"bounded_validation_source": "training_and_counterexample_problem_files",
		"bounded_validation_problem_names": [
			str(item.get("problem_name") or "")
			for item in tuple(validation.get("problem_reports") or ())
			if isinstance(item, dict)
		],
		"evaluation_problem_count": len(tuple(evaluation_results or ())),
		"evaluation_source": "evaluation_problem_files",
		"coverage_is_heldout_runtime_execution": True,
	}


def _failure_analysis(evaluation_results: Sequence[dict[str, object]]) -> dict[str, object]:
	failed = tuple(item for item in evaluation_results if not bool(item["solved"]))
	reason_counts: dict[str, int] = {}
	kind_counts: dict[str, int] = {}
	for item in failed:
		reason = str(item.get("failure_reason") or "unknown")
		reason_counts[reason] = reason_counts.get(reason, 0) + 1
		kind = _failure_kind(reason)
		kind_counts[kind] = kind_counts.get(kind, 0) + 1
	step_counts = tuple(int(item.get("step_count") or 0) for item in evaluation_results)
	return {
		"failed_problem_count": len(failed),
		"failure_kind_counts": dict(sorted(kind_counts.items())),
		"failure_reason_counts": dict(sorted(reason_counts.items())),
		"failed_problems": [
			{
				"problem_name": str(item["problem_name"]),
				"problem_file": str(item["problem_file"]),
				"failure_reason": item.get("failure_reason"),
				"step_count": int(item.get("step_count") or 0),
			}
			for item in failed
		],
		"step_count_summary": _numeric_summary(step_counts),
	}


def _failure_kind(reason: str) -> str:
	text = str(reason or "").lower()
	if "goal mutex" in text:
		return "goal_mutex"
	if "timeout" in text:
		return "timeout"
	if "recursive loop" in text:
		return "recursive_loop"
	if "step limit" in text:
		return "step_limit"
	if "no applicable plan" in text:
		return "no_applicable_plan"
	if "missing goals" in text:
		return "missing_goals"
	if "preconditions are not satisfied" in text:
		return "primitive_precondition_failure"
	return "unknown"


def _refinement_analysis(refinement_trace: dict[str, object] | None) -> dict[str, object]:
	if refinement_trace is None:
		return {
			"enabled": False,
			"converged": None,
			"round_count": 0,
			"constraint_count": 0,
			"constraints_by_type": {},
			"constraints_by_failure_kind": {},
			"constraints_by_target_layer": {},
			"first_round_failed_heldout_count": 0,
			"final_round_failed_heldout_count": 0,
		}
	summary = dict(refinement_trace.get("refinement_summary") or {})
	rounds = tuple(refinement_trace.get("rounds") or ())
	return {
		"enabled": True,
		"converged": bool(refinement_trace.get("converged")),
		"round_count": int(summary.get("round_count") or len(rounds)),
		"constraint_count": int(summary.get("constraint_count") or 0),
		"constraints_by_type": dict(summary.get("constraints_by_type") or {}),
		"constraints_by_failure_kind": dict(
			summary.get("constraints_by_failure_kind") or {},
		),
		"constraints_by_target_layer": dict(
			summary.get("constraints_by_target_layer") or {},
		),
		"first_round_failed_heldout_count": _round_failed_heldout_count(
			rounds[0] if rounds else None,
		),
		"final_round_failed_heldout_count": _round_failed_heldout_count(
			rounds[-1] if rounds else None,
		),
	}


def _round_failed_heldout_count(round_report: object | None) -> int:
	if not isinstance(round_report, dict):
		return 0
	return sum(
		1
		for evaluation in tuple(round_report.get("heldout_evaluations") or ())
		if not bool(dict(evaluation).get("solved"))
	)


def _numeric_summary(values: Sequence[int]) -> dict[str, float | int | None]:
	if not values:
		return {
			"min": None,
			"max": None,
			"mean": None,
		}
	return {
		"min": min(values),
		"max": max(values),
		"mean": sum(values) / len(values),
	}


def _evaluate_problem_with_runtime(
	*,
	plan_library,
	domain_file: str | Path,
	problem_file: str | Path,
	max_execution_steps: int,
	max_depth: int,
	timeout_seconds: float | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
	started = perf_counter()
	timed_out = False
	try:
		with _evaluation_timeout(problem_file, timeout_seconds=timeout_seconds):
			result = _evaluate_problem(
				plan_library=plan_library,
				domain_file=domain_file,
				problem_file=problem_file,
				max_execution_steps=max_execution_steps,
				max_depth=max_depth,
			)
	except TimeoutError as error:
		timed_out = True
		problem = PDDLParser.parse_problem(problem_file)
		result = {
			"problem_file": _resolved(problem_file),
			"problem_name": problem.name,
			"solved": False,
			"step_count": 0,
			"steps": [],
			"failure_reason": str(error),
		}
	return result, {
		"problem_name": result["problem_name"],
		"problem_file": result["problem_file"],
		"duration_seconds": perf_counter() - started,
		"timed_out": timed_out,
	}


@contextmanager
def _evaluation_timeout(
	problem_file: str | Path,
	*,
	timeout_seconds: float | None,
) -> Iterator[None]:
	if timeout_seconds is None:
		yield
		return
	timeout = float(timeout_seconds)
	if timeout <= 0:
		yield
		return
	problem = PDDLParser.parse_problem(problem_file)
	previous_handler = signal.getsignal(signal.SIGALRM)
	previous_timer = signal.getitimer(signal.ITIMER_REAL)
	started = perf_counter()

	def handle_timeout(_signum: int, _frame: object) -> None:
		raise TimeoutError(
			"evaluation timeout exceeded "
			f"timeout_seconds={timeout:g} for problem {problem.name}",
		)

	signal.signal(signal.SIGALRM, handle_timeout)
	signal.setitimer(signal.ITIMER_REAL, timeout)
	try:
		yield
	finally:
		signal.signal(signal.SIGALRM, previous_handler)
		_restore_timer(previous_timer, elapsed=perf_counter() - started)


def _restore_timer(previous_timer: tuple[float, float], *, elapsed: float) -> None:
	previous_delay, previous_interval = previous_timer
	if previous_delay <= 0:
		signal.setitimer(signal.ITIMER_REAL, 0.0)
		return
	signal.setitimer(
		signal.ITIMER_REAL,
		max(0.000001, previous_delay - elapsed),
		previous_interval,
	)


def _generated_output_audit(contract: dict[str, object]) -> dict[str, object]:
	checked_layers = dict(contract.get("checked_layers") or {})
	violations = tuple(str(item) for item in contract.get("violations") or ())
	return {
		"passed": bool(contract.get("passed")),
		"no_synthetic_names": bool(checked_layers.get("no_synthetic_names")),
		"no_grounded_plan_terms": bool(
			checked_layers.get("lifted_plan_heads")
			and checked_layers.get("lifted_body_calls")
			and checked_layers.get("lifted_contexts")
		),
		"no_initial_beliefs": bool(checked_layers.get("no_initial_beliefs")),
		"goal_descriptors_read_only": bool(
			checked_layers.get("goal_descriptors_read_only"),
		),
		"supported_asl_subset": bool(
			checked_layers.get("plan_head_subset")
			and checked_layers.get("body_step_subset")
			and checked_layers.get("context_subset")
		),
		"declared_pddl_symbols": bool(
			checked_layers.get("declared_pddl_symbols", True),
		),
		"checked_layers": checked_layers,
		"violation_count": len(violations),
		"violations": list(violations),
	}


def _evaluate_problem(
	*,
	plan_library,
	domain_file: str | Path,
	problem_file: str | Path,
	max_execution_steps: int,
	max_depth: int,
) -> dict[str, object]:
	execution = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
		max_steps=max_execution_steps,
		max_depth=max_depth,
	)
	return {
		"problem_file": _resolved(problem_file),
		"problem_name": execution.problem_name,
		"solved": execution.solved,
		"step_count": len(execution.steps),
		"steps": list(execution.steps),
		"failure_reason": execution.failure_reason,
	}


def _resolved(path: str | Path) -> str:
	return str(Path(path).expanduser().resolve())
