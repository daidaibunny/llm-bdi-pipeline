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
from .library_synthesis import synthesize_domain_level_asl_library
from .refinement import synthesize_with_counterexample_refinement


def run_domain_level_experiment(
	*,
	experiment_name: str,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path],
	evaluation_problem_files: Sequence[str | Path],
	counterexample_problem_files: Sequence[str | Path] = (),
	max_execution_steps: int = 10000,
	max_depth: int = 1000,
	use_counterexample_refinement: bool = False,
	max_refinement_rounds: int = 1,
) -> dict[str, object]:
	"""Run one reproducible domain-level library experiment."""

	synthesis_started = perf_counter()
	if use_counterexample_refinement:
		refined = synthesize_with_counterexample_refinement(
			domain_file=domain_file,
			training_problem_files=training_problem_files,
			heldout_problem_files=evaluation_problem_files,
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
		"no_synthetic_names": (
			"achieve_" not in asl
			and "transition_" not in asl
			and "dfa_state" not in asl
		),
		"bounded_validation": result.report.get("bounded_validation"),
		"synthesis_report": dict(result.report),
		"refinement_trace": refinement_trace,
		"asl": asl,
	}


def _body_step_count(plan_library, kinds: set[str]) -> int:
	return sum(
		1
		for plan in tuple(plan_library.plans or ())
		for step in tuple(plan.body or ())
		if step.kind in kinds
	)


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
			checked_layers.get("body_step_subset")
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
