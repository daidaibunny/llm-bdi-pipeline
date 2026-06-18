"""
Reproducible domain-level lifted-library experiment reporting.
"""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Sequence

from plan_library.rendering import render_plan_library_asl
from utils.pddl_parser import PDDLParser

from .library_contract import audit_domain_level_library_contract
from .library_executor import evaluate_library_on_problem
from .library_synthesis import ExternalSketchPolicySource
from .library_synthesis import synthesize_domain_level_asl_library
from .refinement import synthesize_with_counterexample_refinement


def run_domain_level_experiment(
	*,
	experiment_name: str,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path],
	evaluation_problem_files: Sequence[str | Path],
	counterexample_problem_files: Sequence[str | Path] = (),
	external_sketch_policies: Sequence[ExternalSketchPolicySource] = (),
	synthesis_profile: str = "bootstrap",
	max_execution_steps: int = 10000,
	max_depth: int = 1000,
	use_counterexample_refinement: bool = False,
	max_refinement_rounds: int = 1,
	ablation_label: str | None = None,
	baselines: Sequence[dict[str, object]] = (),
) -> dict[str, object]:
	"""Run one reproducible domain-level library experiment."""

	synthesis_started = perf_counter()
	if use_counterexample_refinement:
		refined = synthesize_with_counterexample_refinement(
			domain_file=domain_file,
			training_problem_files=training_problem_files,
			heldout_problem_files=evaluation_problem_files,
			counterexample_problem_files=counterexample_problem_files,
			external_sketch_policies=external_sketch_policies,
			synthesis_profile=synthesis_profile,
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
		)
		for problem_file in tuple(evaluation_problem_files or ())
	)
	evaluation_duration = perf_counter() - evaluation_started
	evaluation_results = tuple(item[0] for item in evaluation_with_runtime)
	evaluation_runtimes = tuple(item[1] for item in evaluation_with_runtime)
	contract = audit_domain_level_library_contract(
		plan_library,
		declared_predicates=domain.predicates,
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
		"experiment_protocol": _experiment_protocol(
			synthesis_profile=synthesis_profile,
			external_sketch_policies=external_sketch_policies,
			use_counterexample_refinement=use_counterexample_refinement,
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
	ablation_label: str | None,
	baselines: Sequence[dict[str, object]] = (),
) -> dict[str, object]:
	ablation = _ablation_record(
		label=ablation_label,
		synthesis_profile=synthesis_profile,
		external_sketch_policies=external_sketch_policies,
		use_counterexample_refinement=use_counterexample_refinement,
	)
	return {
		"scope": "bounded_domain_level_lifted_asl_evaluation",
		"training_source": "provided_pddl_training_problems",
		"evaluation_source": "provided_pddl_evaluation_problems",
		"synthesis_profile": str(synthesis_profile or "bootstrap"),
		"external_policy_count": len(tuple(external_sketch_policies or ())),
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
		records.append(
			{
				"label": str(item.get("label") or ""),
				"solver_family": str(item.get("solver_family") or "external_baseline"),
				"solved_count": int(item.get("solved_count") or 0),
				"failed_count": int(item.get("failed_count") or 0),
				"coverage_ratio": float(item.get("coverage_ratio") or 0.0),
				"runtime_planner": str(item.get("runtime_planner") or "offline_baseline_only"),
			},
		)
	return records


def _ablation_record(
	*,
	label: str | None,
	synthesis_profile: str,
	external_sketch_policies: Sequence[ExternalSketchPolicySource],
	use_counterexample_refinement: bool,
) -> dict[str, object] | None:
	text = str(label or "").strip()
	if not text:
		return None
	return {
		"label": text,
		"synthesis_profile": str(synthesis_profile or "bootstrap"),
		"external_policy_count": len(tuple(external_sketch_policies or ())),
		"counterexample_refinement": bool(use_counterexample_refinement),
		"runtime_planner": "none",
	}


def _learning_audit(synthesis_report: dict[str, object]) -> dict[str, object]:
	"""Expose compact learner evidence summaries in experiment reports."""

	matrix = dict(synthesis_report.get("evidence_matrix") or {})
	layer_b = dict(matrix.get("layer_b_atomic_modules") or {})
	layer_c = dict(matrix.get("layer_c_goal_composer") or {})
	strategy_groups = tuple(layer_b.get("atomic_action_strategy_groups") or ())
	strategy_candidates = tuple(
		candidate
		for group in strategy_groups
		for candidate in tuple(dict(group).get("candidates") or ())
	)
	composer_candidates = tuple(layer_c.get("composer_candidate_evidence") or ())
	return {
		"layer_b_atomic_modules": {
			"atomic_action_strategy_group_count": len(strategy_groups),
			"atomic_action_strategy_candidate_count": len(strategy_candidates),
			"selected_atomic_action_strategy_candidate_count": sum(
				1 for candidate in strategy_candidates if bool(candidate.get("selected"))
			),
			"rejected_atomic_action_strategy_candidate_count": sum(
				1 for candidate in strategy_candidates if not bool(candidate.get("selected"))
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
			"composer_candidate_verdict_counts": _count_by_key(
				composer_candidates,
				"verdict",
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

	rows = tuple(_comparison_row(report) for report in tuple(reports or ()))
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
		"rows": list(rows),
	}


def _comparison_row(report: dict[str, object]) -> dict[str, object]:
	protocol = dict(report.get("experiment_protocol") or {})
	coverage = dict(report.get("coverage") or {})
	plan_library = dict(report.get("plan_library") or {})
	paper_quality = dict(report.get("paper_quality_summary") or {})
	ablation = _primary_ablation(protocol, report)
	return {
		"label": str(ablation.get("label") or report.get("experiment_name") or ""),
		"experiment_name": str(report.get("experiment_name") or ""),
		"synthesis_profile": str(protocol.get("synthesis_profile") or "bootstrap"),
		"external_policy_count": int(protocol.get("external_policy_count") or 0),
		"counterexample_refinement": bool(
			ablation.get("counterexample_refinement", False),
		),
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
	}


def _baseline_comparison_row(
	report: dict[str, object],
	baseline: object,
) -> dict[str, object]:
	item = dict(baseline or {})
	library_coverage = float(
		dict(report.get("coverage") or {}).get("coverage_ratio") or 0.0,
	)
	baseline_coverage = float(item.get("coverage_ratio") or 0.0)
	return {
		"report_label": str(report.get("experiment_name") or ""),
		"label": str(item.get("label") or ""),
		"solver_family": str(item.get("solver_family") or "external_baseline"),
		"solved_count": int(item.get("solved_count") or 0),
		"failed_count": int(item.get("failed_count") or 0),
		"coverage_ratio": baseline_coverage,
		"library_coverage_ratio": library_coverage,
		"coverage_delta_vs_library": baseline_coverage - library_coverage,
	}


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


def _count_by_key(items, key: str) -> dict[str, int]:
	counts: dict[str, int] = {}
	for item in tuple(items or ()):
		value = str(dict(item).get(key) or "unknown")
		counts[value] = counts.get(value, 0) + 1
	return dict(sorted(counts.items()))


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
	for item in failed:
		reason = str(item.get("failure_reason") or "unknown")
		reason_counts[reason] = reason_counts.get(reason, 0) + 1
	step_counts = tuple(int(item.get("step_count") or 0) for item in evaluation_results)
	return {
		"failed_problem_count": len(failed),
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
) -> tuple[dict[str, object], dict[str, object]]:
	started = perf_counter()
	result = _evaluate_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
		max_execution_steps=max_execution_steps,
		max_depth=max_depth,
	)
	return result, {
		"problem_name": result["problem_name"],
		"problem_file": result["problem_file"],
		"duration_seconds": perf_counter() - started,
	}


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
