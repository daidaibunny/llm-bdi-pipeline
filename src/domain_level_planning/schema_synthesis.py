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
from .pddl_support import assert_compilable_pddl_files
from .pddl_expression import LiftedLiteral, parameter_variables, parse_pddl_literals
from .transition_system import (
	TrainingTransitionEvidence,
	collect_training_transition_evidence,
)


def build_goal_conditioned_library_from_pddl(
	*,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path] = (),
) -> PlanLibrary:
	"""Build a lifted goal-conditioned library for any STRIPS-style PDDL domain."""

	from .library_synthesis import synthesize_domain_level_asl_library

	return synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=training_problem_files,
	).plan_library


def build_schema_only_goal_conditioned_library_from_pddl(
	*,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path] = (),
) -> PlanLibrary:
	"""Build a lifted goal-conditioned library from schema/evidence candidates only."""

	assert_compilable_pddl_files(
		domain_file=domain_file,
		problem_files=tuple(training_problem_files or ()),
	)
	domain = PDDLParser.parse_domain(domain_file)
	training_goal_facts, transition_evidence = _training_evidence(
		domain=domain,
		problem_files=training_problem_files,
	)
	candidate_rules = _candidate_rules_from_domain(
		domain.predicates,
		domain.actions,
		transition_evidence=transition_evidence,
	)
	required_capabilities = _required_capabilities(
		predicates=domain.predicates,
		candidate_rules=candidate_rules,
		training_goal_facts=training_goal_facts,
	)
	selection = ClingoSketchRuleSelector().select(
		candidate_rules=candidate_rules,
		required_capabilities=required_capabilities,
	)
	_validate_selected_rules_against_transition_progress(
		selection.rules,
		transition_evidence,
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
			"transition_systems": tuple(
				evidence.to_dict()
				for evidence in transition_evidence
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
	*,
	transition_evidence: Sequence[TrainingTransitionEvidence] = (),
) -> tuple[LiftedPlanRule, ...]:
	rules: list[LiftedPlanRule] = []
	producible_predicates = _producible_predicates(actions)
	rules.extend(_goal_ordering_rules_from_evidence(transition_evidence))
	for predicate in predicates:
		rules.extend(_composer_rules(predicate))
		rules.append(_already_true_rule(predicate))
	for action in actions:
		rules.extend(
			_action_effect_rules(
				action,
				producible_predicates=producible_predicates,
			),
		)
	return tuple(rules)


def _goal_ordering_rules_from_evidence(
	transition_evidence: Sequence[TrainingTransitionEvidence],
) -> tuple[LiftedPlanRule, ...]:
	rules: list[LiftedPlanRule] = []
	candidates: dict[
		tuple[tuple[str, tuple[str, ...]], tuple[str, tuple[str, ...]]],
		tuple[PDDLFact, PDDLFact, tuple[str, ...], tuple[LiftedCall, ...], str],
	] = {}
	support_counts: dict[
		tuple[tuple[str, tuple[str, ...]], tuple[str, tuple[str, ...]]],
		int,
	] = {}
	rule_index = 0
	for evidence in transition_evidence:
		for earlier, later in evidence.goal_orderings:
			lifted = _lift_goal_ordering(earlier, later)
			if lifted is None:
				continue
			context, body, pattern = lifted
			key = _goal_ordering_direction_key(earlier, later)
			support_counts[key] = support_counts.get(key, 0) + 1
			candidates.setdefault(key, (earlier, later, context, body, pattern))
	for key, (earlier, later, context, body, pattern) in candidates.items():
		reverse_key = _goal_ordering_direction_key(later, earlier)
		if support_counts[key] <= support_counts.get(reverse_key, 0):
			continue
		rule_index += 1
		rules.append(
			_rule(
				f"g_order_{earlier.predicate}_before_{later.predicate}_{rule_index}",
				"g",
				(),
				context,
				body,
				layer="composer",
				capabilities=(_goal_ordering_capability(key),),
				cost=2,
			),
		)
	return tuple(rules)


def _goal_ordering_direction_key(
	earlier: PDDLFact,
	later: PDDLFact,
) -> tuple[tuple[str, tuple[str, ...]], tuple[str, tuple[str, ...]]]:
	object_variables: dict[str, str] = {}

	def _canonical_arguments(arguments: Iterable[str]) -> tuple[str, ...]:
		canonical: list[str] = []
		for object_name in arguments:
			if object_name not in object_variables:
				object_variables[object_name] = f"V{len(object_variables)}"
			canonical.append(object_variables[object_name])
		return tuple(canonical)

	return (
		(earlier.predicate, _canonical_arguments(earlier.args)),
		(later.predicate, _canonical_arguments(later.args)),
	)


def _goal_ordering_capability(
	key: tuple[tuple[str, tuple[str, ...]], tuple[str, tuple[str, ...]]],
) -> str:
	earlier, later = key
	return (
		f"order_{earlier[0]}_{'_'.join(earlier[1])}_before_"
		f"{later[0]}_{'_'.join(later[1])}"
	)


def _lift_goal_ordering(
	earlier: PDDLFact,
	later: PDDLFact,
) -> tuple[tuple[str, ...], tuple[LiftedCall, ...], str] | None:
	if not earlier.is_positive or not later.is_positive:
		return None
	if not set(earlier.args).intersection(set(later.args)):
		return None
	object_variables: dict[str, str] = {}
	variable_names = ("X", "Y", "Z", "W", "V", "U", "T", "S")

	def _variables(objects: Iterable[str]) -> tuple[str, ...]:
		variables: list[str] = []
		for object_name in objects:
			if object_name not in object_variables:
				index = len(object_variables)
				object_variables[object_name] = (
					variable_names[index]
					if index < len(variable_names)
					else f"X{index + 1}"
				)
			variables.append(object_variables[object_name])
		return tuple(variables)

	later_arguments = _variables(later.args)
	earlier_arguments = _variables(earlier.args)
	context = (
		_call(f"goal_{earlier.predicate}", earlier_arguments),
		_call(f"goal_{later.predicate}", later_arguments),
		f"not {_call(earlier.predicate, earlier_arguments)}",
	)
	body = (_subgoal(earlier.predicate, *earlier_arguments), _subgoal("g"))
	pattern = "|".join(
		object_variables[object_name]
		for object_name in tuple(later.args) + tuple(earlier.args)
	)
	return context, body, pattern


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


def _action_effect_rules(
	action: object,
	*,
	producible_predicates: frozenset[str],
) -> tuple[LiftedPlanRule, ...]:
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
		head_call = _subgoal(effect.predicate, *head_arguments)
		for precondition in preconditions:
			if _can_prepare_precondition(
				precondition,
				head_arguments=head_arguments,
				producible_predicates=producible_predicates,
			):
				rules.append(
					_rule(
						f"{effect.predicate}_prepare_{precondition.predicate}_for_{action_name}",
						effect.predicate,
						head_arguments,
						(f"not {_positive_signature(precondition)}",),
						(
							_subgoal(
								precondition.predicate,
								*tuple(_var(argument) for argument in precondition.arguments),
							),
							head_call,
						),
						capabilities=(
							f"module_{effect.predicate}_prepare_"
							f"{precondition.predicate}_for_{action_name}"
						,),
						cost=2,
					),
				)
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


def _producible_predicates(actions: Sequence[object]) -> frozenset[str]:
	predicates: set[str] = set()
	for action in actions:
		for effect in parse_pddl_literals(str(getattr(action, "effects", ""))):
			if effect.is_positive:
				predicates.add(effect.predicate)
	return frozenset(predicates)


def _can_prepare_precondition(
	precondition: LiftedLiteral,
	*,
	head_arguments: tuple[str, ...],
	producible_predicates: frozenset[str],
) -> bool:
	if not precondition.is_positive:
		return False
	if precondition.predicate not in producible_predicates:
		return False
	precondition_variables = {_var(argument) for argument in precondition.arguments}
	return precondition_variables.issubset(set(head_arguments))


def _positive_signature(literal: LiftedLiteral) -> str:
	return _call(literal.predicate, tuple(_var(argument) for argument in literal.arguments))


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
		if rule.layer == "composer" and any(
			capability.startswith("order_")
			for capability in rule.capabilities
		):
			required.extend(rule.capabilities)
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


def _training_evidence(
	*,
	domain: object,
	problem_files: Sequence[str | Path],
) -> tuple[tuple[PDDLFact, ...], tuple[TrainingTransitionEvidence, ...]]:
	facts: list[PDDLFact] = []
	evidence: list[TrainingTransitionEvidence] = []
	for problem_file in tuple(problem_files or ()):
		problem = PDDLParser.parse_problem(problem_file)
		facts.extend(problem.goal_facts)
		evidence.append(collect_training_transition_evidence(domain, problem))
	return tuple(facts), tuple(evidence)


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


def _validate_selected_rules_against_transition_progress(
	selected_rules: Sequence[LiftedPlanRule],
	transition_evidence: Sequence[TrainingTransitionEvidence],
) -> None:
	failures: list[str] = []
	for evidence in transition_evidence:
		for progression in evidence.goal_progressions:
			if _has_selected_progress_rule(selected_rules, progression):
				continue
			failures.append(
				(
					f"{evidence.problem_name}: no selected lifted rule grounds to "
					f"{progression.goal_fact.to_signature()} via "
					f"{progression.action_signature} with context true before step "
					f"{progression.step_index}"
				),
			)
	if failures:
		raise ValueError(
			"Selected lifted library fails bounded transition-progress validation: "
			+ "; ".join(failures),
		)


def _has_selected_progress_rule(
	selected_rules: Sequence[LiftedPlanRule],
	progression,
) -> bool:
	for rule in selected_rules:
		if rule.layer != "atomic":
			continue
		if rule.head.symbol != progression.goal_fact.predicate:
			continue
		substitution = _substitution_from_head(rule, progression.goal_fact)
		if substitution is None:
			continue
		for step in rule.body:
			if step.kind != "action" or step.symbol != progression.action_name:
				continue
			action_substitution = _merge_substitution(
				substitution,
				dict(zip(step.arguments, progression.action_arguments)),
			)
			if action_substitution is None:
				continue
			if all(
				_context_literal_holds(
					literal,
					action_substitution,
					frozenset(progression.before_state),
				)
				for literal in rule.context
			):
				return True
	return False


def _substitution_from_head(
	rule: LiftedPlanRule,
	goal_fact: PDDLFact,
) -> dict[str, str] | None:
	if len(rule.head.arguments) != len(goal_fact.args):
		return None
	return _merge_substitution({}, dict(zip(rule.head.arguments, goal_fact.args)))


def _merge_substitution(
	base: dict[str, str],
	additions: dict[str, str],
) -> dict[str, str] | None:
	merged = dict(base)
	for variable, value in additions.items():
		if variable in merged and merged[variable] != value:
			return None
		merged[variable] = value
	return merged


def _context_literal_holds(
	literal: str,
	substitution: dict[str, str],
	state: frozenset[str],
) -> bool:
	text = str(literal or "").strip()
	if not text or text.lower() == "true":
		return True
	if "!=" in text:
		left, right = text.split("!=", 1)
		return _ground_term(left, substitution) != _ground_term(right, substitution)
	if "\\==" in text:
		left, right = text.split("\\==", 1)
		return _ground_term(left, substitution) != _ground_term(right, substitution)
	if "==" in text:
		left, right = text.split("==", 1)
		return _ground_term(left, substitution) == _ground_term(right, substitution)
	if text.lower().startswith("not "):
		return _ground_context_atom(text[4:].strip(), substitution) not in state
	return _ground_context_atom(text, substitution) in state


def _ground_context_atom(atom: str, substitution: dict[str, str]) -> str:
	text = str(atom or "").strip()
	if "(" not in text:
		return _ground_term(text, substitution)
	if not text.endswith(")"):
		return text
	predicate, raw_arguments = text.split("(", 1)
	arguments = tuple(
		_ground_term(argument, substitution)
		for argument in raw_arguments[:-1].split(",")
		if argument.strip()
	)
	return _call(predicate.strip(), arguments)


def _ground_term(term: str, substitution: dict[str, str]) -> str:
	text = str(term or "").strip()
	return substitution.get(text, text)


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
