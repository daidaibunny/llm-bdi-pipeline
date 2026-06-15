"""
Counterexample-guided refinement for domain-level lifted ASL synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .library_executor import evaluate_library_on_problem
from .library_synthesis import ExternalSketchPolicySource
from .library_synthesis import UnifiedSynthesisResult
from .library_synthesis import synthesize_domain_level_asl_library
from .library_verifier import LibraryCounterexample
from .transition_system import fact_atom
from .transition_system import initial_state_from_problem
from utils.pddl_parser import PDDLParser


@dataclass(frozen=True)
class HeldoutProblemEvaluation:
	"""Execution result for one held-out problem under one synthesized library."""

	problem_file: str
	problem_name: str
	solved: bool
	step_count: int
	failure_reason: str | None = None
	counterexample: LibraryCounterexample | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"problem_file": self.problem_file,
			"problem_name": self.problem_name,
			"solved": self.solved,
			"step_count": self.step_count,
			"failure_reason": self.failure_reason,
			"counterexample": (
				self.counterexample.to_dict()
				if self.counterexample is not None
				else None
			),
		}


@dataclass(frozen=True)
class RefinementRoundReport:
	"""One counterexample-guided synthesis attempt."""

	round_index: int
	training_problem_files: tuple[str, ...]
	heldout_evaluations: tuple[HeldoutProblemEvaluation, ...]
	added_counterexample_problem_files: tuple[str, ...]
	synthesis_report: dict[str, object]

	def to_dict(self) -> dict[str, object]:
		return {
			"round_index": self.round_index,
			"training_problem_files": list(self.training_problem_files),
			"heldout_evaluations": [
				evaluation.to_dict()
				for evaluation in self.heldout_evaluations
			],
			"added_counterexample_problem_files": list(
				self.added_counterexample_problem_files,
			),
			"synthesis_report": dict(self.synthesis_report),
		}


@dataclass(frozen=True)
class CounterexampleGuidedSynthesisResult:
	"""Final library plus the refinement trace that produced it."""

	final_result: UnifiedSynthesisResult
	rounds: tuple[RefinementRoundReport, ...]
	converged: bool

	def to_dict(self) -> dict[str, object]:
		return {
			"converged": self.converged,
			"rounds": [round_report.to_dict() for round_report in self.rounds],
			"final_report": dict(self.final_result.report),
		}


def synthesize_with_counterexample_refinement(
	*,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path] = (),
	heldout_problem_files: Sequence[str | Path] = (),
	external_sketch_policies: Sequence[ExternalSketchPolicySource] = (),
	synthesis_profile: str = "bootstrap",
	max_refinement_rounds: int = 1,
	max_execution_steps: int = 2000,
	max_depth: int = 200,
) -> CounterexampleGuidedSynthesisResult:
	"""Refine a lifted library by adding failed held-out problems to training."""

	if max_refinement_rounds < 0:
		raise ValueError("max_refinement_rounds must be non-negative.")
	current_training = _unique_paths(training_problem_files)
	heldout_files = _unique_paths(heldout_problem_files)
	rounds: list[RefinementRoundReport] = []
	final_result: UnifiedSynthesisResult | None = None
	converged = False

	for round_index in range(max_refinement_rounds + 1):
		result = synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=current_training,
			external_sketch_policies=external_sketch_policies,
			synthesis_profile=synthesis_profile,
		)
		final_result = result
		heldout_evaluations = _evaluate_heldout_problems(
			plan_result=result,
			domain_file=domain_file,
			heldout_problem_files=heldout_files,
			max_execution_steps=max_execution_steps,
			max_depth=max_depth,
		)
		failed_files = tuple(
			evaluation.problem_file
			for evaluation in heldout_evaluations
			if not evaluation.solved
		)
		added_files = tuple(
			file_path
			for file_path in failed_files
			if file_path not in current_training
		)
		rounds.append(
			RefinementRoundReport(
				round_index=round_index,
				training_problem_files=current_training,
				heldout_evaluations=heldout_evaluations,
				added_counterexample_problem_files=added_files,
				synthesis_report=dict(result.report),
			),
		)
		if not failed_files:
			converged = True
			break
		if round_index >= max_refinement_rounds or not added_files:
			break
		current_training = _unique_paths((*current_training, *added_files))

	if final_result is None:
		raise RuntimeError("Counterexample-guided synthesis produced no result.")
	return CounterexampleGuidedSynthesisResult(
		final_result=final_result,
		rounds=tuple(rounds),
		converged=converged,
	)


def _evaluate_heldout_problems(
	*,
	plan_result: UnifiedSynthesisResult,
	domain_file: str | Path,
	heldout_problem_files: tuple[str, ...],
	max_execution_steps: int,
	max_depth: int,
) -> tuple[HeldoutProblemEvaluation, ...]:
	return tuple(
		_evaluate_heldout_problem(
			plan_result=plan_result,
			domain_file=domain_file,
			problem_file=problem_file,
			max_execution_steps=max_execution_steps,
			max_depth=max_depth,
		)
		for problem_file in heldout_problem_files
	)


def _evaluate_heldout_problem(
	*,
	plan_result: UnifiedSynthesisResult,
	domain_file: str | Path,
	problem_file: str | Path,
	max_execution_steps: int,
	max_depth: int,
) -> HeldoutProblemEvaluation:
	problem = PDDLParser.parse_problem(problem_file)
	execution = evaluate_library_on_problem(
		plan_library=plan_result.plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
		max_steps=max_execution_steps,
		max_depth=max_depth,
		backtrack_on_body_failure=False,
	)
	return HeldoutProblemEvaluation(
		problem_file=str(Path(problem_file).expanduser().resolve()),
		problem_name=problem.name,
		solved=execution.solved,
		step_count=len(execution.steps),
		failure_reason=execution.failure_reason,
		counterexample=(
			None
			if execution.solved
			else _counterexample_from_heldout_failure(
				problem=problem,
				failure_reason=execution.failure_reason or "held-out execution failed",
				steps=execution.steps,
				final_state=execution.final_state,
			)
		),
	)


def _counterexample_from_heldout_failure(
	*,
	problem,
	failure_reason: str,
	steps: tuple[str, ...],
	final_state: frozenset[str],
) -> LibraryCounterexample:
	goal_facts = tuple(
		fact_atom(f"goal_{fact.predicate}", fact.args)
		for fact in problem.goal_facts
		if fact.is_positive
	)
	goal_atoms = tuple(
		fact_atom(fact.predicate, fact.args)
		for fact in problem.goal_facts
		if fact.is_positive
	)
	return LibraryCounterexample(
		problem_name=problem.name,
		state_index=0,
		failure_reason=failure_reason,
		state=tuple(sorted(initial_state_from_problem(problem))),
		goal_facts=goal_facts,
		goal_atoms=goal_atoms,
		was_goal_state=False,
		steps=steps,
		final_state=tuple(sorted(final_state)),
	)


def _unique_paths(paths: Sequence[str | Path]) -> tuple[str, ...]:
	return tuple(
		dict.fromkeys(
			str(Path(path).expanduser().resolve())
			for path in tuple(paths or ())
		),
	)
