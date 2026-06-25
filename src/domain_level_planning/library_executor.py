"""
Bounded executor for generated lifted AgentSpeak(L) achievement libraries.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from low_level_planning.models import LowLevelAction
from low_level_planning.strips_state import STRIPSStateSimulator, fact_to_signature
from plan_library.models import AgentSpeakBodyStep, AgentSpeakPlan, PlanLibrary
from utils.pddl_parser import PDDLParser

from .pddl_types import object_type_atoms


@dataclass(frozen=True)
class LibraryExecutionResult:
	"""Execution outcome for one PDDL problem."""

	problem_name: str
	solved: bool
	steps: tuple[str, ...]
	final_state: frozenset[str]
	state_trace: tuple[frozenset[str], ...] = ()
	decision_trace: tuple[frozenset[str], ...] = ()
	failure_reason: str | None = None


def evaluate_library_on_problem(
	*,
	plan_library: PlanLibrary,
	domain_file: str | Path,
	problem_file: str | Path,
	max_steps: int = 2000,
	max_depth: int = 200,
	backtrack_on_body_failure: bool = False,
) -> LibraryExecutionResult:
	"""Execute a generated library on one problem and check final goals."""

	problem = PDDLParser.parse_problem(problem_file)
	simulator = STRIPSStateSimulator(str(domain_file))
	initial_state = frozenset(
		(
			*(
				fact_to_signature(fact)
				for fact in problem.init_facts
				if fact.is_positive
			),
			*object_type_atoms(problem, simulator.domain.types),
		),
	)
	goal_beliefs = tuple(
		_goal_fact(fact.predicate, fact.args)
		for fact in problem.goal_facts
		if fact.is_positive
	)
	goal_atoms = tuple(
		fact_to_signature(fact)
		for fact in problem.goal_facts
		if fact.is_positive
	)
	return execute_library_from_state(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_name=problem.name,
		initial_state=initial_state,
		goal_facts=goal_beliefs,
		goal_atoms=goal_atoms,
		max_steps=max_steps,
		max_depth=max_depth,
		backtrack_on_body_failure=backtrack_on_body_failure,
	)


def execute_library_from_state(
	*,
	plan_library: PlanLibrary,
	domain_file: str | Path,
	problem_name: str,
	initial_state: frozenset[str],
	goal_facts: tuple[str, ...],
	goal_atoms: tuple[str, ...] | None = None,
	max_steps: int = 2000,
	max_depth: int = 200,
	backtrack_on_body_failure: bool = False,
) -> LibraryExecutionResult:
	"""Execute a generated library from an arbitrary grounded STRIPS state."""

	simulator = STRIPSStateSimulator(str(domain_file))
	state, steps, state_trace, decision_trace, failure = _execute_subgoal(
		plan_library=plan_library,
		simulator=simulator,
		state=frozenset(initial_state),
		goal_facts=goal_facts,
		symbol="g",
		arguments=(),
		steps=(),
		state_trace=(frozenset(initial_state),),
		decision_trace=(),
		max_steps=max_steps,
		max_depth=max_depth,
		backtrack_on_body_failure=backtrack_on_body_failure,
		depth=0,
		active_stack=(),
	)
	if failure is not None:
		return LibraryExecutionResult(
			problem_name=problem_name,
			solved=False,
			steps=steps,
			final_state=state,
			state_trace=state_trace,
			decision_trace=decision_trace,
			failure_reason=failure,
		)
	if goal_atoms is None:
		goal_atoms = tuple(_state_atom_from_goal_fact(fact) for fact in goal_facts)
	missing = tuple(atom for atom in goal_atoms if atom not in state)
	return LibraryExecutionResult(
		problem_name=problem_name,
		solved=not missing,
		steps=steps,
		final_state=state,
		state_trace=state_trace,
		decision_trace=decision_trace,
		failure_reason=None if not missing else f"missing goals: {missing}",
	)


def _execute_subgoal(
	*,
	plan_library: PlanLibrary,
	simulator: STRIPSStateSimulator,
	state: frozenset[str],
	goal_facts: tuple[str, ...],
	symbol: str,
	arguments: tuple[str, ...],
	steps: tuple[str, ...],
	state_trace: tuple[frozenset[str], ...],
	decision_trace: tuple[frozenset[str], ...],
	max_steps: int,
	max_depth: int,
	backtrack_on_body_failure: bool,
	depth: int,
	active_stack: tuple[tuple[str, tuple[str, ...], frozenset[str]], ...],
) -> tuple[
	frozenset[str],
	tuple[str, ...],
	tuple[frozenset[str], ...],
	tuple[frozenset[str], ...],
	str | None,
]:
	current_decision_trace = (
		decision_trace + (state,)
		if symbol == "g"
		else decision_trace
	)
	if symbol == "g" and _all_goal_facts_satisfied(state, goal_facts):
		return state, steps, state_trace, current_decision_trace, None
	if len(steps) >= max_steps:
		return state, steps, state_trace, current_decision_trace, "step limit exceeded"
	if depth > max_depth:
		return state, steps, state_trace, current_decision_trace, "recursion depth exceeded"
	frame = (symbol, arguments, state)
	if frame in active_stack:
		return (
			state,
			steps,
			state_trace,
			current_decision_trace,
			f"recursive loop on !{_call(symbol, arguments)}",
		)
	for plan in _candidate_plans(plan_library, symbol, arguments):
		substitution = _match_arguments(plan.trigger.arguments, arguments)
		if substitution is None:
			continue
		for context_substitution in _context_substitutions(
			contexts=plan.context,
			substitution=substitution,
			state=state,
			goal_facts=goal_facts,
		):
			next_state, next_steps, next_trace, next_decision_trace, failure = _execute_body(
				plan_library=plan_library,
				simulator=simulator,
				state=state,
				goal_facts=goal_facts,
				body=plan.body,
				substitution=context_substitution,
				steps=steps,
				state_trace=state_trace,
				decision_trace=current_decision_trace,
				max_steps=max_steps,
				max_depth=max_depth,
				backtrack_on_body_failure=backtrack_on_body_failure,
				depth=depth,
				active_stack=active_stack + (frame,),
			)
			if failure is None:
				return next_state, next_steps, next_trace, next_decision_trace, None
			if not backtrack_on_body_failure:
				return next_state, next_steps, next_trace, next_decision_trace, failure
	return (
		state,
		steps,
		state_trace,
		current_decision_trace,
		f"no applicable plan for !{_call(symbol, arguments)}",
	)


def _execute_body(
	*,
	plan_library: PlanLibrary,
	simulator: STRIPSStateSimulator,
	state: frozenset[str],
	goal_facts: tuple[str, ...],
	body: Sequence[AgentSpeakBodyStep],
	substitution: Mapping[str, str],
	steps: tuple[str, ...],
	state_trace: tuple[frozenset[str], ...],
	decision_trace: tuple[frozenset[str], ...],
	max_steps: int,
	max_depth: int,
	backtrack_on_body_failure: bool,
	depth: int,
	active_stack: tuple[tuple[str, tuple[str, ...], frozenset[str]], ...],
) -> tuple[
	frozenset[str],
	tuple[str, ...],
	tuple[frozenset[str], ...],
	tuple[frozenset[str], ...],
	str | None,
]:
	current_state = state
	current_steps = steps
	current_trace = state_trace
	current_decision_trace = decision_trace
	for step in body:
		arguments = tuple(_ground_term(argument, substitution) for argument in step.arguments)
		if step.kind == "subgoal":
			(
				current_state,
				current_steps,
				current_trace,
				current_decision_trace,
				failure,
			) = _execute_subgoal(
				plan_library=plan_library,
				simulator=simulator,
				state=current_state,
				goal_facts=goal_facts,
				symbol=step.symbol,
				arguments=arguments,
				steps=current_steps,
				state_trace=current_trace,
				decision_trace=current_decision_trace,
				max_steps=max_steps,
				max_depth=max_depth,
				backtrack_on_body_failure=backtrack_on_body_failure,
				depth=depth + 1,
				active_stack=active_stack,
			)
			if failure is not None:
				return (
					current_state,
					current_steps,
					current_trace,
					current_decision_trace,
					failure,
				)
			continue
		if step.kind in {"action", "primitive_action"}:
			action = LowLevelAction(step.symbol, arguments)
			try:
				current_state = simulator.apply_action(state=current_state, action=action)
			except ValueError as error:
				return (
					current_state,
					current_steps,
					current_trace,
					current_decision_trace,
					str(error),
				)
			current_steps = current_steps + (_call(action.name, action.arguments),)
			current_trace = current_trace + (current_state,)
			if len(current_steps) >= max_steps:
				return (
					current_state,
					current_steps,
					current_trace,
					current_decision_trace,
					"step limit exceeded",
				)
			continue
		return (
			current_state,
			current_steps,
			current_trace,
			current_decision_trace,
			f"unsupported body step kind: {step.kind}",
		)
	return current_state, current_steps, current_trace, current_decision_trace, None


def _candidate_plans(
	plan_library: PlanLibrary,
	symbol: str,
	arguments: tuple[str, ...],
) -> tuple[AgentSpeakPlan, ...]:
	return tuple(
		plan
		for plan in plan_library.plans
		if plan.trigger.symbol == symbol
		and len(plan.trigger.arguments) == len(arguments)
	)


def _match_arguments(
	pattern: Iterable[str],
	arguments: Iterable[str],
) -> dict[str, str] | None:
	substitution: dict[str, str] = {}
	for variable, value in zip(pattern, arguments):
		if _is_variable(variable):
			if variable in substitution and substitution[variable] != value:
				return None
			substitution[variable] = value
		elif variable != value:
			return None
	return substitution


def _context_substitutions(
	*,
	contexts: Sequence[str],
	substitution: Mapping[str, str],
	state: frozenset[str],
	goal_facts: tuple[str, ...],
) -> tuple[dict[str, str], ...]:
	substitutions = (dict(substitution),)
	positive_contexts = tuple(
		context
		for context in tuple(contexts or ())
		if not _is_negated_context_literal(context)
	)
	negative_contexts = tuple(
		context
		for context in tuple(contexts or ())
		if _is_negated_context_literal(context)
	)
	for context in positive_contexts:
		next_substitutions: list[dict[str, str]] = []
		for candidate in substitutions:
			next_substitutions.extend(
				_satisfying_substitutions_for_context(
					context=context,
					substitution=candidate,
					state=state,
					goal_facts=goal_facts,
				),
			)
		substitutions = tuple(next_substitutions)
		if not substitutions:
			return ()
	for context in negative_contexts:
		next_substitutions = []
		for candidate in substitutions:
			next_substitutions.extend(
				_satisfying_substitutions_for_context(
					context=context,
					substitution=candidate,
					state=state,
					goal_facts=goal_facts,
				),
			)
		substitutions = tuple(next_substitutions)
		if not substitutions:
			return ()
	return substitutions


def _is_negated_context_literal(context: str) -> bool:
	return str(context or "").strip().lower().startswith("not ")


def _satisfying_substitutions_for_context(
	*,
	context: str,
	substitution: Mapping[str, str],
	state: frozenset[str],
	goal_facts: tuple[str, ...],
) -> tuple[dict[str, str], ...]:
	text = str(context or "").strip()
	if not text or text.lower() == "true":
		return (dict(substitution),)
	if text.lower().startswith("not "):
		atom = text[4:].strip()
		if _contains_unbound_variables(atom, substitution):
			return ()
		if _is_equality_atom(atom):
			return (
				(dict(substitution),)
				if not _equality_atom_holds(atom, substitution)
				else ()
			)
		return (
			(dict(substitution),)
			if _ground_atom(atom, substitution) not in state
			else ()
		)
	if _is_equality_atom(text):
		if _contains_unbound_variables(text, substitution):
			return ()
		return (
			(dict(substitution),)
			if _equality_atom_holds(text, substitution)
			else ()
		)
	facts = goal_facts if text.startswith("goal_") else tuple(state)
	return tuple(
		merged
		for fact in facts
		if (merged := _match_atom(text, fact, substitution)) is not None
	)


def _match_atom(
	pattern_atom: str,
	fact_atom: str,
	substitution: Mapping[str, str],
) -> dict[str, str] | None:
	pattern_predicate, pattern_arguments = _parse_atom(pattern_atom)
	fact_predicate, fact_arguments = _parse_atom(fact_atom)
	if pattern_predicate != fact_predicate:
		return None
	if len(pattern_arguments) != len(fact_arguments):
		return None
	merged = dict(substitution)
	for pattern, fact in zip(pattern_arguments, fact_arguments):
		if _is_variable(pattern):
			if pattern in merged and merged[pattern] != fact:
				return None
			merged[pattern] = fact
		elif pattern != fact:
			return None
	return merged


def _contains_unbound_variables(atom: str, substitution: Mapping[str, str]) -> bool:
	_, arguments = _parse_atom(atom)
	return any(_is_variable(argument) and argument not in substitution for argument in arguments)


def _ground_atom(atom: str, substitution: Mapping[str, str]) -> str:
	text = str(atom or "").strip()
	if "(" not in text:
		return _ground_term(text, substitution)
	predicate, raw_arguments = text.split("(", 1)
	arguments = tuple(
		_ground_term(argument, substitution)
		for argument in raw_arguments[:-1].split(",")
		if argument.strip()
	)
	return _call(predicate.strip(), arguments)


def _is_equality_atom(atom: str) -> bool:
	predicate, arguments = _parse_atom(atom)
	return predicate == "=" and len(arguments) == 2


def _equality_atom_holds(atom: str, substitution: Mapping[str, str]) -> bool:
	_, arguments = _parse_atom(atom)
	if len(arguments) != 2:
		return False
	left, right = (_ground_term(argument, substitution) for argument in arguments)
	return left == right


def _parse_atom(atom: str) -> tuple[str, tuple[str, ...]]:
	text = str(atom or "").strip()
	if "(" not in text:
		return text, ()
	if not text.endswith(")"):
		return text, ()
	predicate, raw_arguments = text.split("(", 1)
	return (
		predicate.strip(),
		tuple(argument.strip() for argument in raw_arguments[:-1].split(",") if argument.strip()),
	)


def _ground_term(term: str, substitution: Mapping[str, str]) -> str:
	text = str(term or "").strip()
	return substitution.get(text, text)


def _goal_fact(predicate: str, arguments: Iterable[str]) -> str:
	return _call(f"goal_{predicate}", tuple(arguments))


def _all_goal_facts_satisfied(state: frozenset[str], goal_facts: tuple[str, ...]) -> bool:
	return all(_state_atom_from_goal_fact(goal_fact) in state for goal_fact in goal_facts)


def _state_atom_from_goal_fact(goal_fact: str) -> str:
	text = str(goal_fact or "").strip()
	if text.startswith("goal_"):
		return text[len("goal_") :]
	return text


def _call(symbol: str, arguments: Iterable[str]) -> str:
	args = tuple(arguments)
	return symbol if not args else f"{symbol}({', '.join(args)})"


def _is_variable(token: str) -> bool:
	text = str(token or "").strip()
	return bool(text) and text[0].isupper()
