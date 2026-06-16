"""
Reproducible domain-level lifted-library experiment reporting.
"""

from __future__ import annotations

from pathlib import Path
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
	plan_library = result.plan_library
	asl = render_plan_library_asl(plan_library)
	domain = PDDLParser.parse_domain(domain_file)
	evaluation_results = tuple(
		_evaluate_problem(
			plan_library=plan_library,
			domain_file=domain_file,
			problem_file=problem_file,
			max_execution_steps=max_execution_steps,
			max_depth=max_depth,
		)
		for problem_file in tuple(evaluation_problem_files or ())
	)
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
		"evaluation_results": list(evaluation_results),
		"plan_library": {
			"domain_name": plan_library.domain_name,
			"plan_count": len(tuple(plan_library.plans or ())),
			"initial_belief_count": len(tuple(plan_library.initial_beliefs or ())),
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
