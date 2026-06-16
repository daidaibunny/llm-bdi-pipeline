"""
Counterexample-guided refinement for domain-level lifted ASL synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
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
class RefinementConstraint:
	"""Lifted counterexample constraint proposed from one held-out failure."""

	failure_kind: str
	target_layer: str
	constraint_type: str
	problem_file: str
	problem_name: str
	failure_reason: str
	ground_missing_goals: tuple[str, ...] = ()
	ground_satisfied_goals: tuple[str, ...] = ()
	lifted_orderings: tuple[tuple[str, str], ...] = ()
	required_rule_group_types: tuple[str, ...] = ()

	def to_dict(self) -> dict[str, object]:
		return {
			"failure_kind": self.failure_kind,
			"target_layer": self.target_layer,
			"constraint_type": self.constraint_type,
			"problem_file": self.problem_file,
			"problem_name": self.problem_name,
			"failure_reason": self.failure_reason,
			"ground_missing_goals": list(self.ground_missing_goals),
			"ground_satisfied_goals": list(self.ground_satisfied_goals),
			"lifted_orderings": [
				list(ordering) for ordering in self.lifted_orderings
			],
			"required_rule_group_types": list(self.required_rule_group_types),
		}


@dataclass(frozen=True)
class HeldoutProblemEvaluation:
	"""Execution result for one held-out problem under one synthesized library."""

	problem_file: str
	problem_name: str
	solved: bool
	step_count: int
	failure_reason: str | None = None
	counterexample: LibraryCounterexample | None = None
	refinement_constraints: tuple[RefinementConstraint, ...] = ()

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
			"refinement_constraints": [
				constraint.to_dict()
				for constraint in self.refinement_constraints
			],
		}


@dataclass(frozen=True)
class RefinementRoundReport:
	"""One counterexample-guided synthesis attempt."""

	round_index: int
	training_problem_files: tuple[str, ...]
	counterexample_problem_files: tuple[str, ...]
	heldout_evaluations: tuple[HeldoutProblemEvaluation, ...]
	added_counterexample_problem_files: tuple[str, ...]
	refinement_constraints: tuple[RefinementConstraint, ...]
	synthesis_report: dict[str, object]

	def to_dict(self) -> dict[str, object]:
		return {
			"round_index": self.round_index,
			"training_problem_files": list(self.training_problem_files),
			"counterexample_problem_files": list(self.counterexample_problem_files),
			"heldout_evaluations": [
				evaluation.to_dict()
				for evaluation in self.heldout_evaluations
			],
			"added_counterexample_problem_files": list(
				self.added_counterexample_problem_files,
			),
			"refinement_constraints": [
				constraint.to_dict()
				for constraint in self.refinement_constraints
			],
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
	counterexample_constraints = ()
	heldout_files = _unique_paths(heldout_problem_files)
	rounds: list[RefinementRoundReport] = []
	final_result: UnifiedSynthesisResult | None = None
	converged = False

	for round_index in range(max_refinement_rounds + 1):
		result = synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=current_training,
			counterexample_problem_files=counterexample_constraints,
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
		round_constraints = tuple(
			constraint
			for evaluation in heldout_evaluations
			for constraint in evaluation.refinement_constraints
		)
		rounds.append(
			RefinementRoundReport(
				round_index=round_index,
				training_problem_files=current_training,
				counterexample_problem_files=counterexample_constraints,
				heldout_evaluations=heldout_evaluations,
				added_counterexample_problem_files=added_files,
				refinement_constraints=round_constraints,
				synthesis_report=dict(result.report),
			),
		)
		if not failed_files:
			converged = True
			break
		if round_index >= max_refinement_rounds or not added_files:
			break
		counterexample_constraints = _unique_paths(
			(*counterexample_constraints, *added_files),
		)

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
	counterexample = (
		None
		if execution.solved
		else _counterexample_from_heldout_failure(
			problem=problem,
			failure_reason=execution.failure_reason or "held-out execution failed",
			steps=execution.steps,
			final_state=execution.final_state,
		)
	)
	return HeldoutProblemEvaluation(
		problem_file=str(Path(problem_file).expanduser().resolve()),
		problem_name=problem.name,
		solved=execution.solved,
		step_count=len(execution.steps),
		failure_reason=execution.failure_reason,
		counterexample=counterexample,
		refinement_constraints=(
			()
			if counterexample is None
			else classify_heldout_failure_for_refinement(
				problem_file=problem_file,
				problem=problem,
				counterexample=counterexample,
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


def classify_heldout_failure_for_refinement(
	*,
	problem_file: str | Path,
	problem,
	counterexample: LibraryCounterexample,
) -> tuple[RefinementConstraint, ...]:
	"""Classify a failed held-out execution into lifted refinement constraints."""

	missing_goals = tuple(
		atom for atom in counterexample.goal_atoms if atom not in counterexample.final_state
	)
	satisfied_goals = tuple(
		atom for atom in counterexample.goal_atoms if atom in counterexample.final_state
	)
	if missing_goals and satisfied_goals and tuple(counterexample.steps):
		orderings = _lift_goal_orderings_from_failure(
			earlier_atoms=missing_goals,
			later_atoms=satisfied_goals,
		)
		if orderings:
			return (
				RefinementConstraint(
					failure_kind="goal_ordering_failure",
					target_layer="layer_c_goal_composer",
					constraint_type="counterexample_goal_ordering",
					problem_file=str(Path(problem_file).expanduser().resolve()),
					problem_name=problem.name,
					failure_reason=counterexample.failure_reason,
					ground_missing_goals=missing_goals,
					ground_satisfied_goals=satisfied_goals,
					lifted_orderings=orderings,
					required_rule_group_types=(
						"counterexample_transition_progress",
						"counterexample_state_coverage",
						"counterexample_goal_ordering",
					),
				),
			)
	if missing_goals:
		return (
			RefinementConstraint(
				failure_kind=_failure_kind(counterexample.failure_reason),
				target_layer="layer_b_atomic_modules",
				constraint_type="counterexample_atomic_progress",
				problem_file=str(Path(problem_file).expanduser().resolve()),
				problem_name=problem.name,
				failure_reason=counterexample.failure_reason,
				ground_missing_goals=missing_goals,
				ground_satisfied_goals=satisfied_goals,
				required_rule_group_types=("counterexample_transition_progress",),
			),
		)
	return (
		RefinementConstraint(
			failure_kind=_failure_kind(counterexample.failure_reason),
			target_layer="execution_semantics",
			constraint_type="counterexample_execution_trace",
			problem_file=str(Path(problem_file).expanduser().resolve()),
			problem_name=problem.name,
			failure_reason=counterexample.failure_reason,
			ground_missing_goals=missing_goals,
			ground_satisfied_goals=satisfied_goals,
			required_rule_group_types=("counterexample_state_coverage",),
		),
	)


def _lift_goal_orderings_from_failure(
	*,
	earlier_atoms: Sequence[str],
	later_atoms: Sequence[str],
) -> tuple[tuple[str, str], ...]:
	orderings: list[tuple[str, str]] = []
	for earlier in tuple(earlier_atoms or ()):
		for later in tuple(later_atoms or ()):
			lifted = _lift_goal_pair(earlier, later)
			if lifted is not None:
				orderings.append(lifted)
	return tuple(dict.fromkeys(orderings))


def _lift_goal_pair(earlier_atom: str, later_atom: str) -> tuple[str, str] | None:
	earlier_predicate, earlier_args = _parse_atom(earlier_atom)
	later_predicate, later_args = _parse_atom(later_atom)
	if not set(earlier_args).intersection(later_args):
		return None
	object_variables: dict[str, str] = {}
	variable_names = ("X", "Y", "Z", "W", "V", "U", "T", "S")

	def _variables(arguments: Sequence[str]) -> tuple[str, ...]:
		variables: list[str] = []
		for argument in arguments:
			if argument not in object_variables:
				index = len(object_variables)
				object_variables[argument] = (
					variable_names[index]
					if index < len(variable_names)
					else f"X{index + 1}"
				)
			variables.append(object_variables[argument])
		return tuple(variables)

	later_variables = _variables(later_args)
	earlier_variables = _variables(earlier_args)
	return (
		fact_atom(f"goal_{earlier_predicate}", earlier_variables),
		fact_atom(f"goal_{later_predicate}", later_variables),
	)


def _failure_kind(failure_reason: str) -> str:
	text = str(failure_reason or "").lower()
	if "no applicable plan" in text:
		return "missing_module_or_context"
	if "preconditions" in text:
		return "primitive_precondition_failure"
	if "recursive loop" in text:
		return "recursive_loop"
	if "step limit" in text:
		return "nontermination"
	return "execution_failure"


def _parse_atom(atom: str) -> tuple[str, tuple[str, ...]]:
	text = str(atom or "").strip()
	if "(" not in text:
		return text, ()
	match = re.fullmatch(r"\s*([^()\s]+)\((.*)\)\s*", text)
	if match is None:
		return text, ()
	return (
		match.group(1).strip(),
		tuple(part.strip() for part in match.group(2).split(",") if part.strip()),
	)


def _unique_paths(paths: Sequence[str | Path]) -> tuple[str, ...]:
	return tuple(
		dict.fromkeys(
			str(Path(path).expanduser().resolve())
			for path in tuple(paths or ())
		),
	)
