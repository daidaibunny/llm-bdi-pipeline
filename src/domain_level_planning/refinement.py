"""
Counterexample-guided refinement for domain-level lifted ASL synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Sequence

from low_level_planning.models import LowLevelAction
from low_level_planning.strips_state import STRIPSStateSimulator
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
	lifted_missing_goals: tuple[str, ...] = ()
	lifted_satisfied_goals: tuple[str, ...] = ()
	lifted_orderings: tuple[tuple[str, str], ...] = ()
	failing_action: str | None = None
	failing_action_arguments: tuple[str, ...] = ()
	lifted_failing_action: str | None = None
	missing_preconditions: tuple[str, ...] = ()
	lifted_missing_preconditions: tuple[str, ...] = ()
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
			"lifted_missing_goals": list(self.lifted_missing_goals),
			"lifted_satisfied_goals": list(self.lifted_satisfied_goals),
			"lifted_orderings": [
				list(ordering) for ordering in self.lifted_orderings
			],
			"failing_action": self.failing_action,
			"failing_action_arguments": list(self.failing_action_arguments),
			"lifted_failing_action": self.lifted_failing_action,
			"missing_preconditions": list(self.missing_preconditions),
			"lifted_missing_preconditions": list(self.lifted_missing_preconditions),
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
			"refinement_summary": _refinement_summary(
				rounds=self.rounds,
				converged=self.converged,
			),
			"rounds": [round_report.to_dict() for round_report in self.rounds],
			"final_report": dict(self.final_result.report),
		}


def synthesize_with_counterexample_refinement(
	*,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path] = (),
	heldout_problem_files: Sequence[str | Path] = (),
	counterexample_problem_files: Sequence[str | Path] = (),
	external_sketch_policies: Sequence[ExternalSketchPolicySource] = (),
	synthesis_profile: str = "bootstrap",
	disabled_synthesis_mechanisms: Sequence[str] = (),
	use_synthesis_planner_traces: bool = False,
	synthesis_planner_executable: str | Path | None = None,
	synthesis_planner_timeout_seconds: int = 60,
	max_refinement_rounds: int = 1,
	max_execution_steps: int = 2000,
	max_depth: int = 200,
) -> CounterexampleGuidedSynthesisResult:
	"""Refine a lifted library by adding failed held-out problems to training."""

	if max_refinement_rounds < 0:
		raise ValueError("max_refinement_rounds must be non-negative.")
	current_training = _unique_paths(training_problem_files)
	counterexample_constraints = _unique_paths(counterexample_problem_files)
	explicit_refinement_constraints: tuple[RefinementConstraint, ...] = ()
	heldout_files = _unique_paths(heldout_problem_files)
	rounds: list[RefinementRoundReport] = []
	final_result: UnifiedSynthesisResult | None = None
	converged = False

	for round_index in range(max_refinement_rounds + 1):
		result = synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=current_training,
			counterexample_problem_files=counterexample_constraints,
			refinement_constraints=explicit_refinement_constraints,
			disabled_synthesis_mechanisms=disabled_synthesis_mechanisms,
			external_sketch_policies=external_sketch_policies,
			synthesis_profile=synthesis_profile,
			use_synthesis_planner_traces=use_synthesis_planner_traces,
			synthesis_planner_executable=synthesis_planner_executable,
			synthesis_planner_timeout_seconds=synthesis_planner_timeout_seconds,
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
			evaluation.problem_file
			for evaluation in heldout_evaluations
			if not evaluation.solved
			and _requires_counterexample_problem_evidence(evaluation)
			and evaluation.problem_file not in current_training
			and evaluation.problem_file not in counterexample_constraints
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
		new_explicit_constraints = tuple(
			constraint
			for constraint in round_constraints
			if constraint not in explicit_refinement_constraints
		)
		if round_index >= max_refinement_rounds or (
			not added_files and not new_explicit_constraints
		):
			break
		counterexample_constraints = _unique_paths(
			(*counterexample_constraints, *added_files),
		)
		explicit_refinement_constraints = tuple(
			dict.fromkeys((*explicit_refinement_constraints, *new_explicit_constraints)),
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
				domain_file=domain_file,
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
	domain_file: str | Path | None = None,
) -> tuple[RefinementConstraint, ...]:
	"""Classify a failed held-out execution into lifted refinement constraints."""

	all_missing_goals = tuple(
		atom for atom in counterexample.goal_atoms if atom not in counterexample.final_state
	)
	satisfied_goals = tuple(
		atom for atom in counterexample.goal_atoms if atom in counterexample.final_state
	)
	failed_subgoal = _parse_failed_subgoal(counterexample.failure_reason)
	missing_goals = _target_missing_goals_for_failure(
		all_missing_goals=all_missing_goals,
		failed_subgoal=failed_subgoal,
	)
	lifted_missing_goals = _lift_atom_group(missing_goals)
	lifted_satisfied_goals = _lift_atom_group(satisfied_goals)
	termination_constraints = _termination_failure_constraints(
		problem_file=problem_file,
		problem_name=problem.name,
		counterexample=counterexample,
		missing_goals=missing_goals,
		satisfied_goals=satisfied_goals,
		lifted_missing_goals=lifted_missing_goals,
		lifted_satisfied_goals=lifted_satisfied_goals,
		failed_subgoal=failed_subgoal,
	)
	if termination_constraints:
		return termination_constraints
	if missing_goals and _is_top_level_composer_failure(counterexample.failure_reason):
		constraints: list[RefinementConstraint] = []
		if satisfied_goals and tuple(counterexample.steps):
			orderings = _lift_goal_orderings_from_failure(
				earlier_atoms=missing_goals,
				later_atoms=satisfied_goals,
			)
			if orderings:
				constraints.append(
					RefinementConstraint(
						failure_kind="goal_ordering_failure",
						target_layer="layer_c_goal_composer",
						constraint_type="counterexample_goal_ordering",
						problem_file=str(Path(problem_file).expanduser().resolve()),
						problem_name=problem.name,
						failure_reason=counterexample.failure_reason,
						ground_missing_goals=missing_goals,
						ground_satisfied_goals=satisfied_goals,
						lifted_missing_goals=lifted_missing_goals,
						lifted_satisfied_goals=lifted_satisfied_goals,
						lifted_orderings=orderings,
						required_rule_group_types=(
							"counterexample_transition_progress",
							"counterexample_state_coverage",
							"counterexample_goal_ordering",
						),
					),
				)
		constraints.append(
			RefinementConstraint(
				failure_kind="missing_composer_or_context",
				target_layer="layer_c_goal_composer",
				constraint_type="counterexample_state_coverage",
				problem_file=str(Path(problem_file).expanduser().resolve()),
				problem_name=problem.name,
				failure_reason=counterexample.failure_reason,
				ground_missing_goals=missing_goals,
				ground_satisfied_goals=satisfied_goals,
				lifted_missing_goals=lifted_missing_goals,
				lifted_satisfied_goals=lifted_satisfied_goals,
				required_rule_group_types=("counterexample_state_coverage",),
			),
		)
		return tuple(constraints)
	if missing_goals:
		precondition_repair = _primitive_precondition_repair_constraint(
			problem_file=problem_file,
			problem_name=problem.name,
			domain_file=domain_file,
			counterexample=counterexample,
			missing_goals=missing_goals,
			satisfied_goals=satisfied_goals,
			lifted_missing_goals=lifted_missing_goals,
			lifted_satisfied_goals=lifted_satisfied_goals,
		)
		if precondition_repair is not None:
			return (precondition_repair,)
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
					lifted_missing_goals=lifted_missing_goals,
					lifted_satisfied_goals=lifted_satisfied_goals,
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
				lifted_missing_goals=lifted_missing_goals,
				lifted_satisfied_goals=lifted_satisfied_goals,
				required_rule_group_types=(
					("counterexample_atomic_progress",)
					if failed_subgoal is not None
					else ("counterexample_transition_progress",)
				),
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
			lifted_missing_goals=lifted_missing_goals,
			lifted_satisfied_goals=lifted_satisfied_goals,
			required_rule_group_types=("counterexample_state_coverage",),
		),
	)


def _termination_failure_constraints(
	*,
	problem_file: str | Path,
	problem_name: str,
	counterexample: LibraryCounterexample,
	missing_goals: tuple[str, ...],
	satisfied_goals: tuple[str, ...],
	lifted_missing_goals: tuple[str, ...],
	lifted_satisfied_goals: tuple[str, ...],
	failed_subgoal: tuple[str, tuple[str, ...]] | None,
) -> tuple[RefinementConstraint, ...]:
	failure_kind = _failure_kind(counterexample.failure_reason)
	problem_path = str(Path(problem_file).expanduser().resolve())
	if failure_kind == "recursive_loop":
		diagnostic = RefinementConstraint(
			failure_kind=failure_kind,
			target_layer=(
				"layer_c_goal_composer"
				if failed_subgoal is not None and failed_subgoal[0] == "g"
				else "layer_b_atomic_modules"
			),
			constraint_type="counterexample_recursive_loop",
			problem_file=str(Path(problem_file).expanduser().resolve()),
			problem_name=problem_name,
			failure_reason=counterexample.failure_reason,
			ground_missing_goals=missing_goals,
			ground_satisfied_goals=satisfied_goals,
			lifted_missing_goals=lifted_missing_goals,
			lifted_satisfied_goals=lifted_satisfied_goals,
			required_rule_group_types=("counterexample_recursion_descent",),
		)
		companion = _termination_progress_companion_constraint(
			failure_kind=failure_kind,
			problem_file=problem_path,
			problem_name=problem_name,
			failure_reason=counterexample.failure_reason,
			missing_goals=missing_goals,
			satisfied_goals=satisfied_goals,
			lifted_missing_goals=lifted_missing_goals,
			lifted_satisfied_goals=lifted_satisfied_goals,
			failed_subgoal=failed_subgoal,
		)
		return (diagnostic,) if companion is None else (diagnostic, companion)
	if failure_kind == "nontermination":
		diagnostic = RefinementConstraint(
			failure_kind=failure_kind,
			target_layer="execution_semantics",
			constraint_type="counterexample_nontermination",
			problem_file=problem_path,
			problem_name=problem_name,
			failure_reason=counterexample.failure_reason,
			ground_missing_goals=missing_goals,
			ground_satisfied_goals=satisfied_goals,
			lifted_missing_goals=lifted_missing_goals,
			lifted_satisfied_goals=lifted_satisfied_goals,
			required_rule_group_types=("counterexample_nontermination",),
		)
		companion = _termination_progress_companion_constraint(
			failure_kind=failure_kind,
			problem_file=problem_path,
			problem_name=problem_name,
			failure_reason=counterexample.failure_reason,
			missing_goals=missing_goals,
			satisfied_goals=satisfied_goals,
			lifted_missing_goals=lifted_missing_goals,
			lifted_satisfied_goals=lifted_satisfied_goals,
			failed_subgoal=failed_subgoal,
		)
		return (diagnostic,) if companion is None else (diagnostic, companion)
	return ()


def _termination_progress_companion_constraint(
	*,
	failure_kind: str,
	problem_file: str,
	problem_name: str,
	failure_reason: str,
	missing_goals: tuple[str, ...],
	satisfied_goals: tuple[str, ...],
	lifted_missing_goals: tuple[str, ...],
	lifted_satisfied_goals: tuple[str, ...],
	failed_subgoal: tuple[str, tuple[str, ...]] | None,
) -> RefinementConstraint | None:
	if not missing_goals:
		return None
	if failed_subgoal is not None and failed_subgoal[0] != "g":
		return RefinementConstraint(
			failure_kind=f"{failure_kind}_atomic_progress",
			target_layer="layer_b_atomic_modules",
			constraint_type="counterexample_atomic_progress",
			problem_file=problem_file,
			problem_name=problem_name,
			failure_reason=failure_reason,
			ground_missing_goals=missing_goals,
			ground_satisfied_goals=satisfied_goals,
			lifted_missing_goals=lifted_missing_goals,
			lifted_satisfied_goals=lifted_satisfied_goals,
			required_rule_group_types=("counterexample_atomic_progress",),
		)
	return RefinementConstraint(
		failure_kind=f"{failure_kind}_state_coverage",
		target_layer="layer_c_goal_composer",
		constraint_type="counterexample_state_coverage",
		problem_file=problem_file,
		problem_name=problem_name,
		failure_reason=failure_reason,
		ground_missing_goals=missing_goals,
		ground_satisfied_goals=satisfied_goals,
		lifted_missing_goals=lifted_missing_goals,
		lifted_satisfied_goals=lifted_satisfied_goals,
		required_rule_group_types=("counterexample_state_coverage",),
	)


def _primitive_precondition_repair_constraint(
	*,
	problem_file: str | Path,
	problem_name: str,
	domain_file: str | Path | None,
	counterexample: LibraryCounterexample,
	missing_goals: tuple[str, ...],
	satisfied_goals: tuple[str, ...],
	lifted_missing_goals: tuple[str, ...],
	lifted_satisfied_goals: tuple[str, ...],
) -> RefinementConstraint | None:
	if _failure_kind(counterexample.failure_reason) != "primitive_precondition_failure":
		return None
	if domain_file is None:
		return None
	failing_action = _parse_failing_action(counterexample.failure_reason)
	if failing_action is None:
		return None
	simulator = STRIPSStateSimulator(str(domain_file))
	semantics = simulator.ground_action(
		LowLevelAction(failing_action[0], failing_action[1]),
	)
	failure_state = frozenset(counterexample.final_state or counterexample.state)
	missing_preconditions = tuple(
		sorted(
			semantics.positive_preconditions - failure_state,
		),
	)
	violated_negative_preconditions = tuple(
		f"not {atom}"
		for atom in sorted(semantics.negative_preconditions & failure_state)
	)
	unsatisfied_preconditions = (
		*missing_preconditions,
		*violated_negative_preconditions,
	)
	if not unsatisfied_preconditions:
		return None
	object_variables = _object_variable_mapping(
		(
			*missing_goals,
			*satisfied_goals,
			*unsatisfied_preconditions,
		),
	)
	lifted_action = _lift_action_call(
		failing_action[0],
		failing_action[1],
		object_variables,
	)
	return RefinementConstraint(
		failure_kind="primitive_precondition_failure",
		target_layer="layer_b_atomic_modules",
		constraint_type="counterexample_atomic_precondition_repair",
		problem_file=str(Path(problem_file).expanduser().resolve()),
		problem_name=problem_name,
		failure_reason=counterexample.failure_reason,
		ground_missing_goals=missing_goals,
		ground_satisfied_goals=satisfied_goals,
		lifted_missing_goals=_lift_atom_group(missing_goals, object_variables),
		lifted_satisfied_goals=_lift_atom_group(satisfied_goals, object_variables),
		failing_action=failing_action[0],
		failing_action_arguments=failing_action[1],
		lifted_failing_action=lifted_action,
		missing_preconditions=unsatisfied_preconditions,
		lifted_missing_preconditions=_lift_atom_group(
			unsatisfied_preconditions,
			object_variables,
		),
		required_rule_group_types=(
			"counterexample_transition_progress",
			"counterexample_atomic_precondition_repair",
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


def _parse_failing_action(failure_reason: str) -> tuple[str, tuple[str, ...]] | None:
	match = re.search(
		r"for\s+([A-Za-z_][A-Za-z0-9_-]*)\(([^()]*)\)",
		str(failure_reason or ""),
	)
	if match is None:
		return None
	arguments = tuple(
		argument.strip()
		for argument in match.group(2).split(",")
		if argument.strip()
	)
	return match.group(1), arguments


def _parse_failed_subgoal(failure_reason: str) -> tuple[str, tuple[str, ...]] | None:
	match = re.search(
		(
			r"(?:no\s+applicable\s+plan\s+for|recursive\s+loop\s+on)\s+"
			r"!([A-Za-z_][A-Za-z0-9_-]*)\(([^()]*)\)"
		),
		str(failure_reason or ""),
		re.IGNORECASE,
	)
	if match is None:
		match = re.search(
			(
				r"(?:no\s+applicable\s+plan\s+for|recursive\s+loop\s+on)\s+"
				r"!([A-Za-z_][A-Za-z0-9_-]*)\b"
			),
			str(failure_reason or ""),
			re.IGNORECASE,
		)
		if match is None:
			return None
		return match.group(1), ()
	arguments = tuple(
		argument.strip()
		for argument in match.group(2).split(",")
		if argument.strip()
	)
	return match.group(1), arguments


def _target_missing_goals_for_failure(
	*,
	all_missing_goals: tuple[str, ...],
	failed_subgoal: tuple[str, tuple[str, ...]] | None,
) -> tuple[str, ...]:
	if failed_subgoal is None:
		return all_missing_goals
	failed_atom = fact_atom(failed_subgoal[0], failed_subgoal[1])
	return (failed_atom,) if failed_atom in all_missing_goals else all_missing_goals


def _is_top_level_composer_failure(failure_reason: str) -> bool:
	return re.search(
		r"no\s+applicable\s+plan\s+for\s+!g\b",
		str(failure_reason or ""),
		re.IGNORECASE,
	) is not None


def _lift_atom_group(
	atoms: Sequence[str],
	object_variables: dict[str, str] | None = None,
) -> tuple[str, ...]:
	if object_variables is None:
		object_variables = _object_variable_mapping(atoms)
	return tuple(
		_lift_atom(atom, object_variables)
		for atom in tuple(atoms or ())
	)


def _lift_atom(
	atom: str,
	object_variables: dict[str, str],
) -> str:
	text = str(atom or "").strip()
	if text.startswith("not "):
		return f"not {_lift_atom(text[4:].strip(), object_variables)}"
	predicate, arguments = _parse_atom(text)
	return fact_atom(
		predicate,
		tuple(
			object_variables.get(argument, argument)
			for argument in arguments
		),
	)


def _lift_action_call(
	action_name: str,
	arguments: Sequence[str],
	object_variables: dict[str, str],
) -> str:
	return fact_atom(
		action_name,
		tuple(
			object_variables.get(argument, argument)
			for argument in tuple(arguments or ())
		),
	)


def _object_variable_mapping(atoms: Sequence[str]) -> dict[str, str]:
	object_variables: dict[str, str] = {}
	variable_names = ("X", "Y", "Z", "W", "V", "U", "T", "S")
	for atom in tuple(atoms or ()):
		predicate, arguments = _parse_atom(str(atom).removeprefix("not ").strip())
		if not predicate:
			continue
		for argument in arguments:
			if argument in object_variables:
				continue
			index = len(object_variables)
			object_variables[argument] = (
				variable_names[index]
				if index < len(variable_names)
				else f"X{index + 1}"
			)
	return object_variables


def _failure_kind(failure_reason: str) -> str:
	text = str(failure_reason or "").lower()
	if re.search(r"no\s+applicable\s+plan\s+for\s+!g\b", text):
		return "missing_composer_or_context"
	if "no applicable plan" in text:
		return "missing_module_or_context"
	if "preconditions" in text:
		return "primitive_precondition_failure"
	if "recursive loop" in text:
		return "recursive_loop"
	if "step limit" in text:
		return "nontermination"
	return "execution_failure"


def _requires_counterexample_problem_evidence(
	evaluation: HeldoutProblemEvaluation,
) -> bool:
	"""Return whether a failed problem must be re-explored as bounded evidence."""

	constraints = tuple(evaluation.refinement_constraints or ())
	if not constraints:
		return True
	return any(
		constraint.constraint_type != "counterexample_goal_ordering"
		for constraint in constraints
	)


def _refinement_summary(
	*,
	rounds: tuple[RefinementRoundReport, ...],
	converged: bool,
) -> dict[str, object]:
	evaluations = tuple(
		evaluation
		for round_report in tuple(rounds or ())
		for evaluation in round_report.heldout_evaluations
	)
	constraints = tuple(
		constraint
		for round_report in tuple(rounds or ())
		for constraint in round_report.refinement_constraints
	)
	added_counterexamples = tuple(
		path
		for round_report in tuple(rounds or ())
		for path in round_report.added_counterexample_problem_files
	)
	final_counterexamples = (
		tuple(rounds[-1].counterexample_problem_files)
		if rounds
		else ()
	)
	return {
		"converged": converged,
		"round_count": len(tuple(rounds or ())),
		"heldout_evaluation_count": len(evaluations),
		"failed_heldout_evaluation_count": sum(
			1 for evaluation in evaluations if not evaluation.solved
		),
		"solved_heldout_evaluation_count": sum(
			1 for evaluation in evaluations if evaluation.solved
		),
		"added_counterexample_problem_count": len(
			tuple(dict.fromkeys(added_counterexamples)),
		),
		"constraint_only_refinement_round_count": sum(
			1
			for round_report in tuple(rounds or ())
			if round_report.refinement_constraints
			and not round_report.added_counterexample_problem_files
		),
		"final_counterexample_problem_count": len(final_counterexamples),
		"constraint_count": len(constraints),
		"generative_constraint_count": sum(
			1 for constraint in constraints if _is_generative_constraint(constraint)
		),
		"diagnostic_constraint_count": sum(
			1 for constraint in constraints if not _is_generative_constraint(constraint)
		),
		"repair_constraint_count": sum(
			1 for constraint in constraints if "repair" in constraint.constraint_type
		),
		"state_coverage_constraint_count": sum(
			1
			for constraint in constraints
			if constraint.constraint_type == "counterexample_state_coverage"
		),
		"goal_ordering_constraint_count": sum(
			1
			for constraint in constraints
			if constraint.constraint_type == "counterexample_goal_ordering"
		),
		"atomic_progress_constraint_count": sum(
			1
			for constraint in constraints
			if constraint.constraint_type == "counterexample_atomic_progress"
		),
		"recursive_loop_constraint_count": sum(
			1
			for constraint in constraints
			if constraint.constraint_type == "counterexample_recursive_loop"
		),
		"nontermination_constraint_count": sum(
			1
			for constraint in constraints
			if constraint.constraint_type == "counterexample_nontermination"
		),
		"constraints_by_failure_kind": _count_by(
			constraint.failure_kind for constraint in constraints
		),
		"constraints_by_target_layer": _count_by(
			constraint.target_layer for constraint in constraints
		),
		"constraints_by_type": _count_by(
			constraint.constraint_type for constraint in constraints
		),
	}


def _is_generative_constraint(constraint: RefinementConstraint) -> bool:
	return constraint.constraint_type in {
		"counterexample_atomic_precondition_repair",
		"counterexample_atomic_progress",
		"counterexample_goal_ordering",
		"counterexample_state_coverage",
	}


def _count_by(values) -> dict[str, int]:
	counts: dict[str, int] = {}
	for value in values:
		key = str(value)
		counts[key] = counts.get(key, 0) + 1
	return counts


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
