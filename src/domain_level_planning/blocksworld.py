"""
Goal-conditioned modular sketches for the standard four-operator Blocksworld.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from plan_library.models import (
	AgentSpeakBodyStep,
	AgentSpeakPlan,
	AgentSpeakTrigger,
	PlanLibrary,
)
from utils.pddl_parser import PDDLDomain, PDDLFact, PDDLParser

from .blocksworld_transition_system import (
	TransitionSystemSummary,
	enumerate_blocksworld_transition_system,
)
from .clingo_backend import ClingoSketchRuleSelector
from .models import LiftedCall, LiftedPlanRule, SketchSynthesisReport


BLOCKSWORLD_PREDICATES = frozenset({"on", "ontable", "clear", "handempty", "holding"})
BLOCKSWORLD_ACTIONS = frozenset({"pick-up", "put-down", "stack", "unstack"})


def build_blocksworld_goal_conditioned_library(
	*,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path] = (),
) -> PlanLibrary:
	"""Build a lifted ASL library for standard four-operator Blocksworld."""

	domain = PDDLParser.parse_domain(domain_file)
	_validate_supported_blocksworld_domain(domain)
	training_goal_facts, transition_summaries = _training_evidence(training_problem_files)
	required_capabilities = _required_blocksworld_capabilities(
		training_goal_facts=training_goal_facts,
	)
	candidate_rules = _blocksworld_modular_sketch_rules()
	selection = ClingoSketchRuleSelector().select(
		candidate_rules=candidate_rules,
		required_capabilities=required_capabilities,
	)
	rules = selection.rules
	report = SketchSynthesisReport(
		theoretical_contract="bounded_class_guarantee",
		solver_family="clingo_goal_conditioned_modular_policy_sketch",
		runtime_full_trace_planner=False,
		uses_read_only_goal_facts=True,
		supported_domain_class="standard_four_operator_blocksworld",
		learned_layers=("layer_b_atomic_goal_modules", "layer_c_goal_dependency_composer"),
		optimizer=(
			"asp_minimize_rule_cost_subject_to_layer_b_and_layer_c_capability_coverage"
		),
		selected_rule_count=len(rules),
		candidate_rule_count=len(candidate_rules),
	)
	return PlanLibrary(
		domain_name=domain.name,
		plans=tuple(_compile_rule_to_plan(rule) for rule in rules),
		initial_beliefs=(),
		metadata={
			"generation_mode": "goal_conditioned_modular_sketch",
			"training_problem_count": len(tuple(training_problem_files or ())),
			"training_goal_facts": tuple(
				_goal_fact_signature(fact)
				for fact in training_goal_facts
			),
			"transition_systems": tuple(
				summary.to_dict()
				for summary in transition_summaries
			),
			"required_capabilities": tuple(required_capabilities),
			"selected_rule_names": list(selection.selected_rule_names),
			"selection_cost": selection.cost,
			"synthesis_report": report.to_dict(),
		},
	)


def goal_facts_from_problem(problem_file: str | Path) -> tuple[str, ...]:
	"""Return read-only `goal_<predicate>` facts from a PDDL problem goal."""

	problem = PDDLParser.parse_problem(problem_file)
	return tuple(_goal_fact_signature(fact) for fact in problem.goal_facts)


def _blocksworld_modular_sketch_rules() -> tuple[LiftedPlanRule, ...]:
	return (
		# Layer C: goal dependency composer.
		_rule(
			"g_bottom_up_on_dependency",
			"g",
			(),
			("goal_on(Y, Z)", "goal_on(X, Y)", "not on(Y, Z)"),
			(_subgoal("on", "Y", "Z"), _subgoal("g")),
			layer="composer",
			rationale="Serialize tower goals bottom-up before placing X on Y.",
			capabilities=("compose_on_bottom_up_dependency",),
		),
		_rule(
			"g_prepare_goal_base",
			"g",
			(),
			("goal_on(X, Y)", "goal_ontable(Y)", "not ontable(Y)"),
			(_subgoal("ontable", "Y"), _subgoal("g")),
			layer="composer",
			rationale="Place a required tower base on the table before upper goals.",
			capabilities=("compose_required_table_base",),
		),
		_rule(
			"g_satisfy_goal_on",
			"g",
			(),
			("goal_on(X, Y)", "not on(X, Y)"),
			(_subgoal("on", "X", "Y"), _subgoal("g")),
			layer="composer",
			rationale="Call the atomic on-module for unsatisfied target on facts.",
			capabilities=("compose_unsatisfied_goal_on",),
		),
		_rule(
			"g_satisfy_goal_ontable",
			"g",
			(),
			("goal_ontable(X)", "not ontable(X)"),
			(_subgoal("ontable", "X"), _subgoal("g")),
			layer="composer",
			rationale="Call the atomic ontable-module for unsatisfied target table facts.",
			capabilities=("compose_unsatisfied_goal_ontable",),
		),
		_rule(
			"g_satisfy_goal_clear",
			"g",
			(),
			("goal_clear(X)", "not clear(X)"),
			(_subgoal("clear", "X"), _subgoal("g")),
			layer="composer",
			rationale="Call the atomic clear-module for unsatisfied target clear facts.",
			capabilities=("compose_unsatisfied_goal_clear",),
		),
		_rule(
			"g_satisfy_goal_holding",
			"g",
			(),
			("goal_holding(X)", "not holding(X)"),
			(_subgoal("holding", "X"), _subgoal("g")),
			layer="composer",
			rationale="Call the atomic holding-module for unsatisfied target holding facts.",
			capabilities=("compose_unsatisfied_goal_holding",),
		),
		_rule(
			"g_satisfy_goal_handempty",
			"g",
			(),
			("goal_handempty", "not handempty"),
			(_subgoal("handempty"), _subgoal("g")),
			layer="composer",
			rationale="Call the atomic handempty-module for unsatisfied target handempty facts.",
			capabilities=("compose_unsatisfied_goal_handempty",),
		),
		_rule(
			"g_done",
			"g",
			(),
			("true",),
			(),
			layer="composer",
			rationale="Terminal fallback when no unsatisfied goal rule is applicable.",
			capabilities=("compose_terminal_goal",),
		),
		# Layer B: atomic clear(X).
		_rule(
			"clear_already_true",
			"clear",
			("X",),
			("clear(X)",),
			(),
			capabilities=("clear_already_true",),
		),
		_rule(
			"clear_top_block_first",
			"clear",
			("X",),
			("on(Y, X)", "not clear(Y)"),
			(_subgoal("clear", "Y"), _subgoal("clear", "X")),
			capabilities=("clear_recursively_clear_top_block",),
		),
		_rule(
			"clear_by_unstacking_top_block",
			"clear",
			("X",),
			("on(Y, X)", "clear(Y)", "handempty"),
			(_action("unstack", "Y", "X"), _action("put-down", "Y"), _subgoal("clear", "X")),
			capabilities=("clear_unstack_top_block",),
		),
		_rule(
			"clear_release_held_block",
			"clear",
			("X",),
			("holding(Y)",),
			(_action("put-down", "Y"), _subgoal("clear", "X")),
			capabilities=("clear_release_held_block",),
		),
		# Layer B: atomic on(X,Y).
		_rule(
			"on_already_true",
			"on",
			("X", "Y"),
			("on(X, Y)",),
			(),
			capabilities=("on_already_true",),
		),
		_rule(
			"on_clear_moving_block",
			"on",
			("X", "Y"),
			("not on(X, Y)", "not clear(X)"),
			(_subgoal("clear", "X"), _subgoal("on", "X", "Y")),
			capabilities=("on_clear_moving_block",),
		),
		_rule(
			"on_clear_support_block",
			"on",
			("X", "Y"),
			("not on(X, Y)", "clear(X)", "not clear(Y)"),
			(_subgoal("clear", "Y"), _subgoal("on", "X", "Y")),
			capabilities=("on_clear_support_block",),
		),
		_rule(
			"on_stack_held_block",
			"on",
			("X", "Y"),
			("not on(X, Y)", "holding(X)", "clear(Y)"),
			(_action("stack", "X", "Y"),),
			capabilities=("on_stack_held_block",),
		),
		_rule(
			"on_pick_up_from_table",
			"on",
			("X", "Y"),
			("not on(X, Y)", "clear(X)", "clear(Y)", "handempty", "ontable(X)"),
			(_action("pick-up", "X"), _action("stack", "X", "Y")),
			capabilities=("on_pick_up_from_table",),
		),
		_rule(
			"on_move_from_another_block",
			"on",
			("X", "Y"),
			("not on(X, Y)", "clear(X)", "clear(Y)", "handempty", "on(X, Z)"),
			(_action("unstack", "X", "Z"), _action("stack", "X", "Y")),
			capabilities=("on_move_from_another_block",),
		),
		_rule(
			"on_release_irrelevant_held_block",
			"on",
			("X", "Y"),
			("not on(X, Y)", "holding(Z)", "Z != X"),
			(_action("put-down", "Z"), _subgoal("on", "X", "Y")),
			capabilities=("on_release_irrelevant_held_block",),
		),
		# Layer B: atomic ontable(X).
		_rule(
			"ontable_already_true",
			"ontable",
			("X",),
			("ontable(X)",),
			(),
			capabilities=("ontable_already_true",),
		),
		_rule(
			"ontable_clear_first",
			"ontable",
			("X",),
			("not ontable(X)", "not clear(X)"),
			(_subgoal("clear", "X"), _subgoal("ontable", "X")),
			capabilities=("ontable_clear_first",),
		),
		_rule(
			"ontable_put_down_held_block",
			"ontable",
			("X",),
			("holding(X)",),
			(_action("put-down", "X"),),
			capabilities=("ontable_put_down_held_block",),
		),
		_rule(
			"ontable_unstack_to_table",
			"ontable",
			("X",),
			("not ontable(X)", "on(X, Y)", "clear(X)", "handempty"),
			(_action("unstack", "X", "Y"), _action("put-down", "X")),
			capabilities=("ontable_unstack_to_table",),
		),
		_rule(
			"ontable_release_irrelevant_held_block",
			"ontable",
			("X",),
			("not ontable(X)", "holding(Y)", "Y != X"),
			(_action("put-down", "Y"), _subgoal("ontable", "X")),
			capabilities=("ontable_release_irrelevant_held_block",),
		),
		# Layer B: support modules for preconditions.
		_rule(
			"holding_already_true",
			"holding",
			("X",),
			("holding(X)",),
			(),
			capabilities=("holding_already_true",),
		),
		_rule(
			"holding_clear_first",
			"holding",
			("X",),
			("not holding(X)", "not clear(X)"),
			(_subgoal("clear", "X"), _subgoal("holding", "X")),
			capabilities=("holding_clear_first",),
		),
		_rule(
			"holding_release_other_block",
			"holding",
			("X",),
			("not holding(X)", "holding(Y)", "Y != X"),
			(_action("put-down", "Y"), _subgoal("holding", "X")),
			capabilities=("holding_release_other_block",),
		),
		_rule(
			"holding_pick_up_from_table",
			"holding",
			("X",),
			("not holding(X)", "clear(X)", "ontable(X)", "handempty"),
			(_action("pick-up", "X"),),
			capabilities=("holding_pick_up_from_table",),
		),
		_rule(
			"holding_unstack_from_support",
			"holding",
			("X",),
			("not holding(X)", "clear(X)", "on(X, Y)", "handempty"),
			(_action("unstack", "X", "Y"),),
			capabilities=("holding_unstack_from_support",),
		),
		_rule(
			"handempty_already_true",
			"handempty",
			(),
			("handempty",),
			(),
			capabilities=("handempty_already_true",),
		),
		_rule(
			"handempty_put_down_held_block",
			"handempty",
			(),
			("holding(X)",),
			(_action("put-down", "X"),),
			capabilities=("handempty_put_down_held_block",),
		),
	)


def _rule(
	name: str,
	head_symbol: str,
	head_arguments: Iterable[str],
	context: Iterable[str],
	body: Iterable[LiftedCall],
	*,
	layer: str = "atomic",
	rationale: str = "",
	capabilities: Iterable[str] = (),
	cost: int = 1,
) -> LiftedPlanRule:
	return LiftedPlanRule(
		name=name,
		head=LiftedCall("subgoal", head_symbol, tuple(head_arguments)),
		context=tuple(context),
		body=tuple(body),
		layer=layer,
		rationale=rationale,
		capabilities=tuple(capabilities),
		cost=cost,
	)


def _required_blocksworld_capabilities(
	*,
	training_goal_facts: Iterable[PDDLFact] = (),
) -> tuple[str, ...]:
	required = [
		"compose_on_bottom_up_dependency",
		"compose_required_table_base",
		"compose_unsatisfied_goal_on",
		"compose_unsatisfied_goal_ontable",
		"compose_unsatisfied_goal_clear",
		"compose_unsatisfied_goal_holding",
		"compose_unsatisfied_goal_handempty",
		"compose_terminal_goal",
		"clear_already_true",
		"clear_recursively_clear_top_block",
		"clear_unstack_top_block",
		"clear_release_held_block",
		"on_already_true",
		"on_clear_moving_block",
		"on_clear_support_block",
		"on_stack_held_block",
		"on_pick_up_from_table",
		"on_move_from_another_block",
		"on_release_irrelevant_held_block",
		"ontable_already_true",
		"ontable_clear_first",
		"ontable_put_down_held_block",
		"ontable_unstack_to_table",
		"ontable_release_irrelevant_held_block",
		"holding_already_true",
		"holding_clear_first",
		"holding_release_other_block",
		"holding_pick_up_from_table",
		"holding_unstack_from_support",
		"handempty_already_true",
		"handempty_put_down_held_block",
	]
	for fact in training_goal_facts:
		required.extend(_capabilities_for_goal_fact(fact))
	return tuple(dict.fromkeys(required))


def _training_evidence(
	problem_files: Sequence[str | Path],
) -> tuple[tuple[PDDLFact, ...], tuple[TransitionSystemSummary, ...]]:
	facts: list[PDDLFact] = []
	transition_summaries: list[TransitionSystemSummary] = []
	for problem_file in tuple(problem_files or ()):
		problem = PDDLParser.parse_problem(problem_file)
		transition_summaries.append(enumerate_blocksworld_transition_system(problem))
		facts.extend(problem.goal_facts)
		for fact in problem.goal_facts:
			_capabilities_for_goal_fact(fact)
	return tuple(facts), tuple(transition_summaries)


def _capabilities_for_goal_fact(fact: PDDLFact) -> tuple[str, ...]:
	if not fact.is_positive:
		raise ValueError(
			"Goal-conditioned Blocksworld synthesis currently supports positive "
			f"achievement goals only; unsupported goal fact: {fact.to_signature()}."
		)
	if fact.predicate == "on":
		return ("compose_unsatisfied_goal_on", "on_already_true")
	if fact.predicate == "ontable":
		return ("compose_unsatisfied_goal_ontable", "ontable_already_true")
	if fact.predicate == "clear":
		return ("compose_unsatisfied_goal_clear", "clear_already_true")
	if fact.predicate == "holding":
		return ("compose_unsatisfied_goal_holding", "holding_already_true")
	if fact.predicate == "handempty":
		return ("compose_unsatisfied_goal_handempty", "handempty_already_true")
	raise ValueError(
		"Goal-conditioned Blocksworld synthesis cannot cover unsupported goal "
		f"predicate: {fact.predicate}."
	)


def _action(symbol: str, *arguments: str) -> LiftedCall:
	return LiftedCall("action", symbol, tuple(arguments))


def _subgoal(symbol: str, *arguments: str) -> LiftedCall:
	return LiftedCall("subgoal", symbol, tuple(arguments))


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
				"rationale": rule.rationale,
				"synthesis_family": "goal_conditioned_modular_policy_sketch",
			},
		),
	)


def _goal_fact_signature(fact: PDDLFact) -> str:
	atom = (
		f"goal_{fact.predicate}"
		if not fact.args
		else f"goal_{fact.predicate}({', '.join(fact.args)})"
	)
	return atom if fact.is_positive else f"not {atom}"


def _validate_supported_blocksworld_domain(domain: PDDLDomain) -> None:
	predicates = {predicate.name for predicate in domain.predicates}
	actions = {action.name for action in domain.actions}
	missing_predicates = sorted(BLOCKSWORLD_PREDICATES - predicates)
	missing_actions = sorted(BLOCKSWORLD_ACTIONS - actions)
	if missing_predicates or missing_actions:
		raise ValueError(
			"The goal-conditioned Blocksworld synthesizer supports only the "
			"standard four-operator Blocksworld schema. "
			f"Missing predicates={missing_predicates}; missing actions={missing_actions}."
		)
