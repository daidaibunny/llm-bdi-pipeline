"""
Domain-agnostic lifted ASL synthesis from PDDL action schemas.
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
from utils.pddl_parser import PDDLFact, PDDLParser, PDDLPredicate

from .clingo_backend import ClingoSketchRuleSelector
from .models import LiftedCall, LiftedPlanRule, SketchSynthesisReport
from .pddl_expression import LiftedLiteral, parameter_variables, parse_pddl_literals


def build_goal_conditioned_library_from_pddl(
	*,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path] = (),
) -> PlanLibrary:
	"""Build a lifted goal-conditioned library for any STRIPS-style PDDL domain."""

	domain = PDDLParser.parse_domain(domain_file)
	training_goal_facts = _training_goal_facts(training_problem_files)
	candidate_rules = _candidate_rules_from_domain(domain.predicates, domain.actions)
	required_capabilities = _required_capabilities(
		predicates=domain.predicates,
		candidate_rules=candidate_rules,
		training_goal_facts=training_goal_facts,
	)
	selection = ClingoSketchRuleSelector().select(
		candidate_rules=candidate_rules,
		required_capabilities=required_capabilities,
	)
	report = SketchSynthesisReport(
		theoretical_contract="bounded_class_guarantee",
		solver_family="clingo_goal_conditioned_schema_synthesis",
		runtime_full_trace_planner=False,
		uses_read_only_goal_facts=True,
		supported_domain_class="strips_action_schema_add_effect_modules",
		learned_layers=("layer_b_atomic_goal_modules", "layer_c_goal_composer"),
		optimizer="asp_minimize_rule_cost_subject_to_schema_capability_coverage",
		selected_rule_count=len(selection.rules),
		candidate_rule_count=len(candidate_rules),
	)
	return PlanLibrary(
		domain_name=domain.name,
		plans=tuple(_compile_rule_to_plan(rule) for rule in selection.rules),
		initial_beliefs=(),
		metadata={
			"generation_mode": "goal_conditioned_schema_synthesis",
			"training_problem_count": len(tuple(training_problem_files or ())),
			"training_goal_facts": tuple(
				_goal_fact_signature(fact)
				for fact in training_goal_facts
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


def _candidate_rules_from_domain(
	predicates: Sequence[PDDLPredicate],
	actions: Sequence[object],
) -> tuple[LiftedPlanRule, ...]:
	rules: list[LiftedPlanRule] = []
	for predicate in predicates:
		rules.extend(_composer_rules(predicate))
		rules.append(_already_true_rule(predicate))
	for action in actions:
		rules.extend(_action_effect_rules(action))
	return tuple(rules)


def _composer_rules(predicate: PDDLPredicate) -> tuple[LiftedPlanRule, ...]:
	arguments = parameter_variables(predicate.parameters)
	goal_context = _call(f"goal_{predicate.name}", arguments)
	state_context = _call(predicate.name, arguments)
	return (
		_rule(
			f"g_satisfy_goal_{predicate.name}",
			"g",
			(),
			(goal_context, f"not {state_context}"),
			(_subgoal(predicate.name, *arguments), _subgoal("g")),
			layer="composer",
			capabilities=(f"compose_goal_{predicate.name}",),
		),
	)


def _already_true_rule(predicate: PDDLPredicate) -> LiftedPlanRule:
	arguments = parameter_variables(predicate.parameters)
	return _rule(
		f"{predicate.name}_already_true",
		predicate.name,
		arguments,
		(_call(predicate.name, arguments),),
		(),
		capabilities=(f"module_{predicate.name}_already_true",),
	)


def _action_effect_rules(action: object) -> tuple[LiftedPlanRule, ...]:
	action_name = str(getattr(action, "name"))
	action_arguments = parameter_variables(getattr(action, "parameters"))
	preconditions = parse_pddl_literals(str(getattr(action, "preconditions", "")))
	add_effects = tuple(
		effect
		for effect in parse_pddl_literals(str(getattr(action, "effects", "")))
		if effect.is_positive
	)
	rules: list[LiftedPlanRule] = []
	for effect in add_effects:
		head_arguments = tuple(_var(argument) for argument in effect.arguments)
		context = tuple(literal.signature() for literal in preconditions)
		rules.append(
			_rule(
				f"{effect.predicate}_via_{action_name}",
				effect.predicate,
				head_arguments,
				context,
				(_action(action_name, *action_arguments),),
				capabilities=(f"module_{effect.predicate}_action_{action_name}",),
			),
		)
	return tuple(rules)


def _required_capabilities(
	*,
	predicates: Sequence[PDDLPredicate],
	candidate_rules: Sequence[LiftedPlanRule],
	training_goal_facts: Iterable[PDDLFact],
) -> tuple[str, ...]:
	predicate_names = {predicate.name for predicate in predicates}
	required: list[str] = []
	for predicate in predicates:
		required.append(f"compose_goal_{predicate.name}")
		required.append(f"module_{predicate.name}_already_true")
	for rule in candidate_rules:
		if rule.layer == "atomic" and rule.body:
			required.extend(rule.capabilities)
	for fact in training_goal_facts:
		if not fact.is_positive:
			raise ValueError(
				"Goal-conditioned schema synthesis currently supports positive "
				f"achievement goals only; unsupported goal fact: {fact.to_signature()}."
			)
		if fact.predicate not in predicate_names:
			raise ValueError(f"Goal predicate is not declared in the PDDL domain: {fact.predicate}")
		required.append(f"compose_goal_{fact.predicate}")
		required.append(f"module_{fact.predicate}_already_true")
	return tuple(dict.fromkeys(required))


def _training_goal_facts(problem_files: Sequence[str | Path]) -> tuple[PDDLFact, ...]:
	facts: list[PDDLFact] = []
	for problem_file in tuple(problem_files or ()):
		problem = PDDLParser.parse_problem(problem_file)
		facts.extend(problem.goal_facts)
	return tuple(facts)


def _rule(
	name: str,
	head_symbol: str,
	head_arguments: Iterable[str],
	context: Iterable[str],
	body: Iterable[LiftedCall],
	*,
	layer: str = "atomic",
	capabilities: Iterable[str] = (),
	cost: int = 1,
) -> LiftedPlanRule:
	return LiftedPlanRule(
		name=name,
		head=LiftedCall("subgoal", head_symbol, tuple(head_arguments)),
		context=tuple(context),
		body=tuple(body),
		layer=layer,
		capabilities=tuple(capabilities),
		cost=cost,
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
				"synthesis_family": "goal_conditioned_schema_synthesis",
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


def _call(predicate: str, arguments: Iterable[str]) -> str:
	args = tuple(arguments)
	return predicate if not args else f"{predicate}({', '.join(args)})"


def _var(parameter: str) -> str:
	text = str(parameter or "").strip().lstrip("?")
	if not text:
		return "X"
	return f"{text[0].upper()}{text[1:]}"
