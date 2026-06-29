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
from .goal_mutex import GoalMutexDiagnostic, schema_goal_mutexes
from .transition_system import problem_with_domain_constants


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
	problem_with_constants = problem_with_domain_constants(problem, simulator.domain)
	initial_state = frozenset(
		(
			*(
				fact_to_signature(fact)
				for fact in problem_with_constants.init_facts
				if fact.is_positive
			),
			*object_type_atoms(problem_with_constants, simulator.domain.types),
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
	goal_mutexes = schema_goal_mutexes(
		domain=simulator.domain,
		goal_atoms=tuple(_state_atom_from_goal_fact(fact) for fact in goal_facts),
	)
	if goal_mutexes:
		return LibraryExecutionResult(
			problem_name=problem_name,
			solved=False,
			steps=(),
			final_state=frozenset(initial_state),
			state_trace=(frozenset(initial_state),),
			decision_trace=(),
			failure_reason=_goal_mutex_failure_reason(goal_mutexes),
		)
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
	candidate_plans = _candidate_plans(plan_library, symbol, arguments)
	derived_goal_facts = _goal_facts_for_derived_contexts(
		goal_facts=goal_facts,
		symbol=symbol,
		arguments=arguments,
	)
	derived_context_facts = (
		_derived_context_facts(
			plan_library=plan_library,
			state=state,
			goal_facts=derived_goal_facts,
		)
		if _plans_need_derived_context_facts(candidate_plans, derived_goal_facts)
		else ()
	)
	for plan in candidate_plans:
		substitution = _match_arguments(plan.trigger.arguments, arguments)
		if substitution is None:
			continue
		for context_substitution in _context_substitutions(
			contexts=plan.context,
			substitution=substitution,
			state=state,
			goal_facts=goal_facts,
			derived_context_facts=derived_context_facts,
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


def _goal_facts_for_derived_contexts(
	*,
	goal_facts: tuple[str, ...],
	symbol: str,
	arguments: tuple[str, ...],
) -> tuple[str, ...]:
	if symbol == "g" or not tuple(arguments or ()):
		return goal_facts
	current_subgoal = _goal_fact(symbol, arguments)
	if current_subgoal in goal_facts:
		return goal_facts
	return (*goal_facts, current_subgoal)


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


def _plans_need_derived_context_facts(
	plans: Sequence[AgentSpeakPlan],
	goal_facts: tuple[str, ...],
) -> bool:
	return any(
		_context_needs_derived_context_facts(context, goal_facts)
		for plan in tuple(plans or ())
		for context in tuple(plan.context or ())
	)


def _context_needs_derived_context_facts(
	context: str,
	goal_facts: tuple[str, ...],
) -> bool:
	text = str(context or "").strip()
	if text.lower().startswith("not "):
		text = text[4:].strip()
	symbol, _arguments = _parse_atom(text)
	return _is_ready_context_for_goal_symbol(
		symbol,
		goal_facts,
	) or symbol.startswith("route_step_")


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
	derived_context_facts: tuple[str, ...],
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
					derived_context_facts=derived_context_facts,
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
					derived_context_facts=derived_context_facts,
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
	derived_context_facts: tuple[str, ...],
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
		facts = _context_fact_source(
			atom,
			state=state,
			goal_facts=goal_facts,
			derived_context_facts=derived_context_facts,
		)
		return (
			(dict(substitution),)
			if _ground_atom(atom, substitution) not in facts
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
	facts = _context_fact_source(
		text,
		state=state,
		goal_facts=goal_facts,
		derived_context_facts=derived_context_facts,
	)
	return tuple(
		merged
		for fact in facts
		if (merged := _match_atom(text, fact, substitution)) is not None
	)


def _context_fact_source(
	context_atom: str,
	*,
	state: frozenset[str],
	goal_facts: tuple[str, ...],
	derived_context_facts: tuple[str, ...],
) -> tuple[str, ...] | frozenset[str]:
	symbol, _arguments = _parse_atom(context_atom)
	if symbol.startswith("goal_"):
		return goal_facts
	if _is_ready_context_for_goal_symbol(symbol, goal_facts):
		return derived_context_facts
	if symbol in _derived_context_symbols(derived_context_facts):
		return derived_context_facts
	return tuple(sorted(state))


def _derived_context_facts(
	*,
	plan_library: PlanLibrary,
	state: frozenset[str],
	goal_facts: tuple[str, ...],
) -> tuple[str, ...]:
	ready_facts = {
		_ready_fact_from_goal_fact(goal_fact)
		for goal_fact in tuple(goal_facts or ())
	}
	agenda = dict(plan_library.metadata.get("runtime_goal_agenda") or {})
	support_edges = tuple(agenda.get("support_edges") or ())
	route_facts = _route_step_context_facts(
		plan_library=plan_library,
		state=state,
		goal_facts=goal_facts,
	)
	if not support_edges:
		return tuple(sorted((*ready_facts, *route_facts)))
	blocked = {
		_ready_fact_from_goal_fact(goal_fact)
		for goal_fact in tuple(goal_facts or ())
		if _goal_blocked_by_support_agenda(
			goal_fact=goal_fact,
			goal_facts=goal_facts,
			state=state,
			support_edges=support_edges,
		)
	}
	return tuple(sorted((ready_facts - blocked).union(route_facts)))


def _derived_context_symbols(derived_context_facts: Sequence[str]) -> frozenset[str]:
	return frozenset(
		_parse_atom(fact)[0]
		for fact in tuple(derived_context_facts or ())
	)


def _route_step_context_facts(
	*,
	plan_library: PlanLibrary,
	state: frozenset[str],
	goal_facts: tuple[str, ...],
) -> frozenset[str]:
	facts: set[str] = set()
	for feature in tuple(plan_library.metadata.get("runtime_route_features") or ()):
		if not isinstance(feature, Mapping):
			continue
		facts.update(
			_route_step_context_facts_for_feature(
				feature=feature,
				state=state,
				goal_facts=goal_facts,
			),
		)
	return frozenset(facts)


def _route_step_context_facts_for_feature(
	*,
	feature: Mapping[str, object],
	state: frozenset[str],
	goal_facts: tuple[str, ...],
) -> tuple[str, ...]:
	symbol = str(feature.get("symbol") or "").strip()
	target_predicate = str(feature.get("target_predicate") or "").strip()
	if not symbol or not target_predicate:
		return ()
	head_arguments = tuple(str(item) for item in tuple(feature.get("head_arguments") or ()))
	context_arguments = tuple(
		str(item) for item in tuple(feature.get("context_arguments") or ())
	)
	edge_contexts = tuple(str(item) for item in tuple(feature.get("edge_contexts") or ()))
	source_variable = str(feature.get("source_variable") or "").strip()
	next_variable = str(feature.get("next_variable") or "").strip()
	target_variable = str(feature.get("target_variable") or "").strip()
	changed_position = int(feature.get("changed_position") or 0)
	if (
		not head_arguments
		or not context_arguments
		or not edge_contexts
		or not source_variable
		or not next_variable
		or not target_variable
		or changed_position >= len(head_arguments)
	):
		return ()
	head_pattern = _call(target_predicate, head_arguments)
	source_arguments = list(head_arguments)
	source_arguments[changed_position] = source_variable
	source_pattern = _call(target_predicate, source_arguments)
	route_facts: list[str] = []
	for goal_fact in tuple(goal_facts or ()):
		goal_atom = _state_atom_from_goal_fact(goal_fact)
		goal_substitution = _match_atom(head_pattern, goal_atom, {})
		if goal_substitution is None:
			continue
		target = goal_substitution.get(target_variable)
		if target is None:
			continue
		edge_substitutions = _binding_context_substitutions(
			contexts=edge_contexts,
			substitution=goal_substitution,
			state=state,
		)
		edges = {
			(substitution[source_variable], substitution[next_variable])
			for substitution in edge_substitutions
			if source_variable in substitution and next_variable in substitution
		}
		distances = _shortest_distances_to_target(edges, target)
		current_substitutions = _binding_context_substitutions(
			contexts=(source_pattern,),
			substitution=goal_substitution,
			state=state,
		)
		for current in current_substitutions:
			source = current.get(source_variable)
			if source is None or source not in distances:
				continue
			for edge_source, edge_next in sorted(edges):
				if edge_source != source:
					continue
				if distances.get(edge_next, len(edges) + 1) >= distances[source]:
					continue
				merged = dict(current)
				merged[next_variable] = edge_next
				if _contains_unbound_variables(
					_call(symbol, context_arguments),
					merged,
				):
					continue
				route_facts.append(_call(symbol, tuple(merged[arg] for arg in context_arguments)))
	return tuple(dict.fromkeys(route_facts))


def _shortest_distances_to_target(
	edges: set[tuple[str, str]],
	target: str,
) -> dict[str, int]:
	reverse_graph: dict[str, set[str]] = {}
	for source, next_node in edges:
		reverse_graph.setdefault(next_node, set()).add(source)
	distances = {target: 0}
	frontier = [target]
	while frontier:
		node = frontier.pop(0)
		for predecessor in sorted(reverse_graph.get(node, ())):
			if predecessor in distances:
				continue
			distances[predecessor] = distances[node] + 1
			frontier.append(predecessor)
	return distances


def _goal_blocked_by_support_agenda(
	*,
	goal_fact: str,
	goal_facts: tuple[str, ...],
	state: frozenset[str],
	support_edges: Sequence[Mapping[str, object]],
) -> bool:
	later_goal_atom = _state_atom_from_goal_fact(goal_fact)
	for edge in tuple(support_edges or ()):
		if not bool(edge.get("selected", True)) or edge.get("category") != "support":
			continue
		later_pattern = str(edge.get("later") or "").strip()
		earlier_pattern = str(edge.get("earlier") or "").strip()
		if not later_pattern or not earlier_pattern:
			continue
		later_substitution = _match_atom(later_pattern, later_goal_atom, {})
		if later_substitution is None:
			continue
		for candidate in _binding_context_substitutions(
			contexts=tuple(str(item) for item in tuple(edge.get("binding_contexts") or ())),
			substitution=later_substitution,
			state=state,
		):
			if _has_unsatisfied_predecessor_goal(
				earlier_pattern=earlier_pattern,
				later_pattern=later_pattern,
				substitution=candidate,
				goal_facts=goal_facts,
				state=state,
			):
				return True
	return False


def _binding_context_substitutions(
	*,
	contexts: Sequence[str],
	substitution: Mapping[str, str],
	state: frozenset[str],
) -> tuple[dict[str, str], ...]:
	substitutions = (dict(substitution),)
	for context in tuple(contexts or ()):
		next_substitutions: list[dict[str, str]] = []
		for candidate in substitutions:
			next_substitutions.extend(
				_satisfying_state_context_substitutions(
					context=context,
					substitution=candidate,
					state=state,
				),
			)
		substitutions = tuple(next_substitutions)
		if not substitutions:
			return ()
	return substitutions


def _satisfying_state_context_substitutions(
	*,
	context: str,
	substitution: Mapping[str, str],
	state: frozenset[str],
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
	return tuple(
		merged
		for fact in sorted(state)
		if (merged := _match_atom(text, fact, substitution)) is not None
	)


def _has_unsatisfied_predecessor_goal(
	*,
	earlier_pattern: str,
	later_pattern: str,
	substitution: Mapping[str, str],
	goal_facts: tuple[str, ...],
	state: frozenset[str],
) -> bool:
	for earlier_goal_fact in tuple(goal_facts or ()):
		earlier_goal_atom = _state_atom_from_goal_fact(earlier_goal_fact)
		merged = _match_atom(earlier_pattern, earlier_goal_atom, substitution)
		if merged is None:
			continue
		ground_earlier = _ground_atom(earlier_pattern, merged)
		ground_later = _ground_atom(later_pattern, merged)
		if ground_earlier == ground_later:
			continue
		if ground_earlier not in state:
			return True
	return False


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


def _ready_fact_from_goal_fact(goal_fact: str) -> str:
	state_atom = _state_atom_from_goal_fact(goal_fact)
	predicate, arguments = _parse_atom(state_atom)
	return _call(f"ready_{predicate}", arguments)


def _is_ready_context_for_goal_symbol(symbol: str, goal_facts: tuple[str, ...]) -> bool:
	text = str(symbol or "").strip()
	if not text.startswith("ready_"):
		return False
	return text in {
		_parse_atom(_ready_fact_from_goal_fact(goal_fact))[0]
		for goal_fact in tuple(goal_facts or ())
	}


def _all_goal_facts_satisfied(state: frozenset[str], goal_facts: tuple[str, ...]) -> bool:
	return all(_state_atom_from_goal_fact(goal_fact) in state for goal_fact in goal_facts)


def _state_atom_from_goal_fact(goal_fact: str) -> str:
	text = str(goal_fact or "").strip()
	if text.startswith("goal_"):
		return text[len("goal_") :]
	return text


def _goal_mutex_failure_reason(
	diagnostics: Sequence[GoalMutexDiagnostic],
) -> str:
	first = tuple(diagnostics or ())[0]
	return (
		"goal mutex detected: "
		f"{first.first_goal} conflicts with {first.second_goal}; "
		"schema evidence: "
		f"{first.first_producer_action} adds {first.first_goal} and deletes "
		f"{first.first_add_deletes_second}, "
		f"{first.second_producer_action} adds {first.second_goal} and deletes "
		f"{first.second_add_deletes_first}"
	)


def _call(symbol: str, arguments: Iterable[str]) -> str:
	args = tuple(arguments)
	return symbol if not args else f"{symbol}({', '.join(args)})"


def _is_variable(token: str) -> bool:
	text = str(token or "").strip()
	return bool(text) and text[0].isupper()
