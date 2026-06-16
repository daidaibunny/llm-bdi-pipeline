"""
Domain-agnostic lifted ASL synthesis from PDDL action schemas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping, Sequence

from plan_library.models import (
	AgentSpeakBodyStep,
	AgentSpeakPlan,
	AgentSpeakTrigger,
	PlanLibrary,
)
from utils.pddl_parser import PDDLFact, PDDLParser, PDDLPredicate

from .clingo_backend import ClingoRequiredRuleGroup, ClingoSketchRuleSelector
from .models import LiftedCall, LiftedPlanRule, SketchSynthesisReport
from .pddl_support import assert_compilable_pddl_files
from .pddl_expression import LiftedLiteral, parameter_variables, parse_pddl_literals
from .transition_system import (
	State,
	TrainingTransitionEvidence,
	collect_training_transition_evidence,
	fact_atom,
	reachable_states_for_problem,
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
	candidate_rules, recursion_audit = filter_rules_by_recursion_descent(
		candidate_rules,
		ranking_states=recursion_ranking_states_from_problem_files(
			domain=domain,
			problem_files=training_problem_files,
		),
	)
	required_capabilities = _required_capabilities(
		predicates=domain.predicates,
		candidate_rules=candidate_rules,
		training_goal_facts=training_goal_facts,
	)
	selection = ClingoSketchRuleSelector().select(
		candidate_rules=candidate_rules,
		required_capabilities=required_capabilities,
		required_rule_groups=transition_progress_required_rule_groups(
			candidate_rules,
			transition_evidence,
		)
		+ composer_state_coverage_required_rule_groups(
			candidate_rules,
			domain=domain,
			problem_files=training_problem_files,
		),
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
			"recursion_descent_audit": recursion_audit,
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
	rules.extend(_causal_interference_ordering_rules(actions))
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


def filter_rules_by_recursion_descent(
	rules: Sequence[LiftedPlanRule],
	*,
	ranking_states: Sequence[State] = (),
) -> tuple[tuple[LiftedPlanRule, ...], Mapping[str, object]]:
	"""Reject recursive atomic rules without a structural progress certificate.

	The current lifted module language has no numeric ranking field. The
	domain-agnostic certificate we can prove from the rule structure is therefore
	limited but useful: before a rule recurses to its own head, it must call a
	different positive subgoal whose corresponding fact is explicitly missing in
	the rule context. This is exactly the prepare-rule shape generated from PDDL
	action preconditions: `not pre(...) <- !pre(...); !target(...)`.
	"""

	audit = recursion_descent_audit(rules, ranking_states=ranking_states)
	rejected_names = {
		str(certificate["rule_name"])
		for certificate in tuple(audit["certificates"])
		if not bool(certificate["accepted"])
	}
	filtered = tuple(
		rule for rule in tuple(rules or ()) if rule.name not in rejected_names
	)
	return filtered, audit


def recursion_descent_audit(
	rules: Sequence[LiftedPlanRule],
	*,
	ranking_states: Sequence[State] = (),
) -> Mapping[str, object]:
	"""Return structural recursion-descent certificates for lifted rules."""

	certificates = tuple(
		_recursive_rule_certificate(rule, ranking_states=ranking_states)
		for rule in tuple(rules or ())
		if _recursive_body_indices(rule)
	)
	accepted = tuple(
		certificate for certificate in certificates if bool(certificate["accepted"])
	)
	rejected = tuple(
		certificate for certificate in certificates if not bool(certificate["accepted"])
	)
	return {
		"contract": "missing_positive_precondition_before_same_goal_recursion",
		"ranking_contract": (
			"same_predicate_recursion_must_follow_bounded_acyclic_relation"
		),
		"recursive_rule_count": len(certificates),
		"accepted_recursive_rule_count": len(accepted),
		"rejected_recursive_rule_count": len(rejected),
		"certificates": certificates,
		"violations": tuple(
			f"{certificate['rule_name']}: {certificate['reason']}"
			for certificate in rejected
		),
	}


def recursion_ranking_states_from_problem_files(
	*,
	domain: object,
	problem_files: Sequence[str | Path],
	max_reachable_states: int = 20000,
) -> tuple[State, ...]:
	"""Collect bounded reachable states used as recursion-ranking evidence."""

	states: list[State] = []
	for problem_file in tuple(problem_files or ()):
		problem = PDDLParser.parse_problem(problem_file)
		states.extend(
			sorted(
				reachable_states_for_problem(
					domain,
					problem,
					max_states=max_reachable_states,
				),
				key=lambda item: tuple(sorted(item)),
			),
		)
	return tuple(dict.fromkeys(states))


def _recursive_rule_certificate(
	rule: LiftedPlanRule,
	*,
	ranking_states: Sequence[State],
) -> dict[str, object]:
	recursive_indices = _recursive_body_indices(rule)
	first_recursive_index = recursive_indices[0]
	first_recursive_call = rule.body[first_recursive_index]
	prefix_subgoals = tuple(
		step
		for step in rule.body[:first_recursive_index]
		if step.kind == "subgoal" and step.symbol != rule.head.symbol
	)
	context_missing_atoms = {
		_strip_negation(context)
		for context in tuple(rule.context or ())
		if _is_negated_atom(context)
	}
	for subgoal in prefix_subgoals:
		subgoal_atom = _call(subgoal.symbol, subgoal.arguments)
		if subgoal_atom not in context_missing_atoms:
			continue
		return {
			"rule_name": rule.name,
			"head": _call(rule.head.symbol, rule.head.arguments),
			"accepted": True,
			"descent_subgoal": subgoal_atom,
			"missing_context": f"not {subgoal_atom}",
			"recursive_call_index": first_recursive_index,
			"reason": "missing positive precondition is pursued before recursion",
		}
	if prefix_subgoals:
		return {
			"rule_name": rule.name,
			"head": _call(rule.head.symbol, rule.head.arguments),
			"accepted": False,
			"descent_subgoal": None,
			"missing_context": None,
			"recursive_call_index": first_recursive_index,
			"reason": (
				"prefix subgoals are not paired with a missing context literal; "
				"requires an explicit ranking feature before recursive compilation"
			),
		}
	if first_recursive_call.symbol == rule.head.symbol and (
		tuple(first_recursive_call.arguments or ()) != tuple(rule.head.arguments or ())
	):
		ranking_certificate = _bounded_acyclic_relation_certificate(
			rule,
			first_recursive_call,
			ranking_states=ranking_states,
			recursive_call_index=first_recursive_index,
		)
		if ranking_certificate is not None:
			return ranking_certificate
		return {
			"rule_name": rule.name,
			"head": _call(rule.head.symbol, rule.head.arguments),
			"accepted": False,
			"descent_subgoal": None,
			"missing_context": None,
			"recursive_call_index": first_recursive_index,
			"reason": (
				"same-predicate recursion changes arguments and requires an explicit "
				"ranking feature before recursive compilation"
			),
		}
	return {
		"rule_name": rule.name,
		"head": _call(rule.head.symbol, rule.head.arguments),
		"accepted": False,
		"descent_subgoal": None,
		"missing_context": None,
		"recursive_call_index": first_recursive_index,
		"reason": "no missing positive precondition subgoal appears before recursion",
	}


def _bounded_acyclic_relation_certificate(
	rule: LiftedPlanRule,
	recursive_call: LiftedCall,
	*,
	ranking_states: Sequence[State],
	recursive_call_index: int,
) -> dict[str, object] | None:
	changed_pairs = tuple(
		(head_arg, recursive_arg)
		for head_arg, recursive_arg in zip(rule.head.arguments, recursive_call.arguments)
		if head_arg != recursive_arg
	)
	if not changed_pairs or not tuple(ranking_states or ()):
		return None
	context_atoms = tuple(
		_parse_atom(context)
		for context in tuple(rule.context or ())
		if not _is_negated_atom(context)
	)
	for head_arg, recursive_arg in changed_pairs:
		for predicate, arguments in context_atoms:
			if head_arg not in arguments or recursive_arg not in arguments:
				continue
			head_position = arguments.index(head_arg)
			recursive_position = arguments.index(recursive_arg)
			if head_position == recursive_position:
				continue
			if _relation_is_acyclic_in_states(
				predicate=predicate,
				head_position=head_position,
				recursive_position=recursive_position,
				states=ranking_states,
			):
				return {
					"rule_name": rule.name,
					"head": _call(rule.head.symbol, rule.head.arguments),
					"accepted": True,
					"descent_subgoal": _call(recursive_call.symbol, recursive_call.arguments),
					"missing_context": None,
					"recursive_call_index": recursive_call_index,
					"ranking_relation": predicate,
					"ranking_edge": f"{head_arg}->{recursive_arg}",
					"ranking_state_count": len(tuple(ranking_states or ())),
					"reason": "recursive call follows a bounded acyclic context relation",
				}
	return None


def _relation_is_acyclic_in_states(
	*,
	predicate: str,
	head_position: int,
	recursive_position: int,
	states: Sequence[State],
) -> bool:
	observed_edge = False
	for state in tuple(states or ()):
		edges: set[tuple[str, str]] = set()
		for atom in state:
			fact_predicate, fact_arguments = _parse_atom(atom)
			if fact_predicate != predicate:
				continue
			if max(head_position, recursive_position) >= len(fact_arguments):
				continue
			observed_edge = True
			edges.add((fact_arguments[head_position], fact_arguments[recursive_position]))
		if _has_cycle(edges):
			return False
	return observed_edge


def _has_cycle(edges: set[tuple[str, str]]) -> bool:
	graph: dict[str, set[str]] = {}
	for source, target in edges:
		graph.setdefault(source, set()).add(target)
		graph.setdefault(target, set())
	visiting: set[str] = set()
	visited: set[str] = set()

	def _visit(node: str) -> bool:
		if node in visiting:
			return True
		if node in visited:
			return False
		visiting.add(node)
		for successor in graph.get(node, ()):
			if _visit(successor):
				return True
		visiting.remove(node)
		visited.add(node)
		return False

	return any(_visit(node) for node in tuple(graph))


def _recursive_body_indices(rule: LiftedPlanRule) -> tuple[int, ...]:
	if rule.layer != "atomic":
		return ()
	return tuple(
		index
		for index, step in enumerate(tuple(rule.body or ()))
		if step.kind == "subgoal"
		and step.symbol == rule.head.symbol
	)


def _is_negated_atom(context: str) -> bool:
	return str(context or "").strip().lower().startswith("not ")


def _strip_negation(context: str) -> str:
	text = str(context or "").strip()
	return text[4:].strip() if text.lower().startswith("not ") else text


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


def causal_interference_ordering_rules(domain: object) -> tuple[LiftedPlanRule, ...]:
	"""Derive lifted composer ordering rules from schema causal structure.

	A producer goal predicate must be achieved before a consumer goal predicate
	when the producer's achieving action adds a fact that the consumer's achieving
	action requires as a precondition, and the shared link variables are all goal
	arguments. This recovers bottom-up nested orderings from action schemas alone,
	with no training traces and no domain-specific tokens.
	"""

	return _causal_interference_ordering_rules(getattr(domain, "actions", ()) or ())


def _causal_interference_ordering_rules(
	actions: Sequence[object],
) -> tuple[LiftedPlanRule, ...]:
	achievers = _goal_predicate_achievers(actions)
	seen: set[tuple[str, str, tuple[tuple[int, int], ...]]] = set()
	rules: list[LiftedPlanRule] = []
	index = 0
	for consumer_pred, consumer_list in achievers.items():
		for producer_pred, producer_list in achievers.items():
			for consumer in consumer_list:
				for producer in producer_list:
					for link in _producer_consumer_links(producer, consumer):
						key = (producer_pred, consumer_pred, link)
						if key in seen:
							continue
						lifted = _lift_causal_ordering(producer, consumer, link)
						if lifted is None:
							continue
						seen.add(key)
						index += 1
						context, body, capability = lifted
						rules.append(
							_rule(
								f"g_causal_order_{producer_pred}_before_{consumer_pred}_{index}",
								"g",
								(),
								context,
								body,
								layer="composer",
								capabilities=(capability,),
								cost=2,
							),
						)
	for threat_pred, threat_list in achievers.items():
		for threatened_pred, threatened_list in achievers.items():
			for threat in threat_list:
				for threatened in threatened_list:
					for link in _delete_threat_links(threat, threatened):
						key = (f"delete:{threat_pred}", threatened_pred, link)
						if key in seen:
							continue
						lifted = _lift_delete_threat_ordering(threat, threatened, link)
						if lifted is None:
							continue
						seen.add(key)
						index += 1
						context, body, capability = lifted
						rules.append(
							_rule(
								f"g_delete_threat_order_{threat_pred}_before_"
								f"{threatened_pred}_{index}",
								"g",
								(),
								context,
								body,
								layer="composer",
								capabilities=(capability,),
								cost=2,
							),
						)
	return tuple(rules)


def _goal_predicate_achievers(actions: Sequence[object]) -> dict[str, tuple[dict, ...]]:
	achievers: dict[str, list[dict]] = {}
	for action in actions:
		preconditions = tuple(
			literal
			for literal in parse_pddl_literals(str(getattr(action, "preconditions", "")))
			if literal.is_positive
		)
		add_effects = tuple(
			literal
			for literal in parse_pddl_literals(str(getattr(action, "effects", "")))
			if literal.is_positive
		)
		delete_effects = tuple(
			literal
			for literal in parse_pddl_literals(str(getattr(action, "effects", "")))
			if not literal.is_positive
		)
		for add in add_effects:
			if not add.arguments:
				continue
			achievers.setdefault(add.predicate, []).append(
				{
					"action": str(getattr(action, "name")),
					"target": add,
					"preconditions": preconditions,
					"add_effects": add_effects,
					"delete_effects": delete_effects,
				},
			)
	return {predicate: tuple(items) for predicate, items in achievers.items()}


def _producer_consumer_links(
	producer: dict,
	consumer: dict,
) -> tuple[tuple[tuple[int, int], ...], ...]:
	"""Return goal-argument links where a producer add supplies a consumer pre.

	Each link is a tuple of (consumer_target_index, producer_target_index) pairs
	identifying which goal arguments must denote the same object for the
	producer's added fact to be exactly the consumer precondition it enables.
	"""

	producer_positions = _argument_positions(producer["target"].arguments)
	consumer_positions = _argument_positions(consumer["target"].arguments)
	links: list[tuple[tuple[int, int], ...]] = []
	for precondition in consumer["preconditions"]:
		for supplied in producer["add_effects"]:
			if precondition.predicate != supplied.predicate:
				continue
			if len(precondition.arguments) != len(supplied.arguments):
				continue
			if not precondition.arguments:
				continue
			pairs: list[tuple[int, int]] = []
			grounded = True
			for consumer_arg, producer_arg in zip(
				precondition.arguments,
				supplied.arguments,
			):
				consumer_index = consumer_positions.get(consumer_arg)
				producer_index = producer_positions.get(producer_arg)
				if consumer_index is None or producer_index is None:
					grounded = False
					break
				pairs.append((consumer_index, producer_index))
			if not grounded or not pairs:
				continue
			links.append(tuple(pairs))
	return tuple(dict.fromkeys(links))


def _delete_threat_links(
	threat: dict,
	threatened: dict,
) -> tuple[tuple[tuple[int, int], ...], ...]:
	"""Return links where achieving one goal deletes another goal literal."""

	threat_positions = _argument_positions(threat["target"].arguments)
	threatened_positions = _argument_positions(threatened["target"].arguments)
	links: list[tuple[tuple[int, int], ...]] = []
	for deleted in threat["delete_effects"]:
		if deleted.predicate != threatened["target"].predicate:
			continue
		if len(deleted.arguments) != len(threatened["target"].arguments):
			continue
		if not deleted.arguments:
			continue
		pairs: list[tuple[int, int]] = []
		grounded = True
		for deleted_arg, threatened_arg in zip(
			deleted.arguments,
			threatened["target"].arguments,
		):
			threat_index = threat_positions.get(deleted_arg)
			threatened_index = threatened_positions.get(threatened_arg)
			if threat_index is None or threatened_index is None:
				grounded = False
				break
			pairs.append((threat_index, threatened_index))
		if not grounded or not pairs:
			continue
		links.append(tuple(pairs))
	return tuple(dict.fromkeys(links))


def _lift_causal_ordering(
	producer: dict,
	consumer: dict,
	link: tuple[tuple[int, int], ...],
) -> tuple[tuple[str, ...], tuple[LiftedCall, ...], str] | None:
	consumer_arity = len(consumer["target"].arguments)
	producer_arity = len(producer["target"].arguments)
	consumer_to_producer = {
		consumer_index: producer_index for consumer_index, producer_index in link
	}
	if len(consumer_to_producer) != len(link):
		return None
	# Build shared object identities: consumer slots first (so X is the topmost
	# consumer argument and Y the linked block), then producer slots, collapsing
	# linked producer slots onto their consumer identity.
	identities: dict[tuple[str, int], int] = {}
	next_id = 0
	for consumer_index in range(consumer_arity):
		identities[("c", consumer_index)] = next_id
		next_id += 1
	for producer_index in range(producer_arity):
		linked_consumer = next(
			(
				consumer_index
				for consumer_index, mapped in consumer_to_producer.items()
				if mapped == producer_index
			),
			None,
		)
		if linked_consumer is not None:
			identities[("p", producer_index)] = identities[("c", linked_consumer)]
		else:
			identities[("p", producer_index)] = next_id
			next_id += 1
	if next_id <= max(consumer_arity, producer_arity):
		return None
	variable_names = ("X", "Y", "Z", "W", "V", "U", "T", "S")
	if next_id > len(variable_names):
		return None

	def _variable(slot: tuple[str, int]) -> str:
		return variable_names[identities[slot]]

	consumer_args = tuple(_variable(("c", index)) for index in range(consumer_arity))
	producer_args = tuple(_variable(("p", index)) for index in range(producer_arity))
	if consumer_args == producer_args:
		return None
	consumer_pred = consumer["target"].predicate
	producer_pred = producer["target"].predicate
	context = (
		_call(f"goal_{producer_pred}", producer_args),
		_call(f"goal_{consumer_pred}", consumer_args),
		f"not {_call(producer_pred, producer_args)}",
	)
	body = (_subgoal(producer_pred, *producer_args), _subgoal("g"))
	capability = (
		f"causal_order_{producer_pred}_{'_'.join(producer_args)}_before_"
		f"{consumer_pred}_{'_'.join(consumer_args)}"
	)
	return context, body, capability


def _lift_delete_threat_ordering(
	threat: dict,
	threatened: dict,
	link: tuple[tuple[int, int], ...],
) -> tuple[tuple[str, ...], tuple[LiftedCall, ...], str] | None:
	threat_arity = len(threat["target"].arguments)
	threatened_arity = len(threatened["target"].arguments)
	threat_to_threatened = {
		threat_index: threatened_index for threat_index, threatened_index in link
	}
	if len(threat_to_threatened) != len(link):
		return None
	identities: dict[tuple[str, int], int] = {}
	next_id = 0
	for threat_index in range(threat_arity):
		identities[("t", threat_index)] = next_id
		next_id += 1
	for threatened_index in range(threatened_arity):
		linked_threat = next(
			(
				threat_index
				for threat_index, mapped in threat_to_threatened.items()
				if mapped == threatened_index
			),
			None,
		)
		if linked_threat is not None:
			identities[("d", threatened_index)] = identities[("t", linked_threat)]
		else:
			identities[("d", threatened_index)] = next_id
			next_id += 1
	variable_names = ("X", "Y", "Z", "W", "V", "U", "T", "S")
	if next_id > len(variable_names):
		return None

	def _variable(slot: tuple[str, int]) -> str:
		return variable_names[identities[slot]]

	threat_args = tuple(_variable(("t", index)) for index in range(threat_arity))
	threatened_args = tuple(
		_variable(("d", index)) for index in range(threatened_arity)
	)
	threat_pred = threat["target"].predicate
	threatened_pred = threatened["target"].predicate
	context = (
		_call(f"goal_{threat_pred}", threat_args),
		_call(f"goal_{threatened_pred}", threatened_args),
		f"not {_call(threat_pred, threat_args)}",
	)
	body = (_subgoal(threat_pred, *threat_args), _subgoal("g"))
	capability = (
		f"delete_threat_order_{threat_pred}_{'_'.join(threat_args)}_before_"
		f"{threatened_pred}_{'_'.join(threatened_args)}"
	)
	return context, body, capability


def _argument_positions(arguments: Sequence[str]) -> dict[str, int]:
	positions: dict[str, int] = {}
	for index, argument in enumerate(arguments):
		positions.setdefault(argument, index)
	return positions


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
			binding_context = _binding_context_for_precondition(
				precondition,
				head_arguments=head_arguments,
				preconditions=preconditions,
				producible_predicates=producible_predicates,
			)
			if binding_context is not None:
				rules.append(
					_rule(
						f"{effect.predicate}_prepare_{precondition.predicate}_for_{action_name}",
						effect.predicate,
						head_arguments,
						(*binding_context, f"not {_positive_signature(precondition)}"),
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


def _binding_context_for_precondition(
	precondition: LiftedLiteral,
	*,
	head_arguments: tuple[str, ...],
	preconditions: tuple[LiftedLiteral, ...],
	producible_predicates: frozenset[str],
) -> tuple[str, ...] | None:
	if not precondition.is_positive:
		return None
	if precondition.predicate not in producible_predicates:
		return None
	head_variables = set(head_arguments)
	precondition_variables = {_var(argument) for argument in precondition.arguments}
	if precondition_variables.issubset(head_variables):
		return ()

	bound_variables = set(head_variables)
	binding_literals: list[LiftedLiteral] = []
	remaining = [
		literal
		for literal in preconditions
		if literal != precondition and literal.is_positive
	]
	while not precondition_variables.issubset(bound_variables):
		next_literal = None
		for literal in remaining:
			literal_variables = {_var(argument) for argument in literal.arguments}
			if not literal_variables.intersection(bound_variables):
				continue
			if literal_variables.issubset(bound_variables):
				continue
			next_literal = literal
			break
		if next_literal is None:
			return None
		remaining.remove(next_literal)
		binding_literals.append(next_literal)
		bound_variables.update(_var(argument) for argument in next_literal.arguments)
	return tuple(literal.signature() for literal in binding_literals)


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
	for problem_position, problem_file in enumerate(tuple(problem_files or ()), start=1):
		problem = PDDLParser.parse_problem(problem_file)
		facts.extend(problem.goal_facts)
		evidence.append(collect_training_transition_evidence(domain, problem))
	return tuple(facts), tuple(evidence)


def composer_state_coverage_required_rule_groups(
	candidate_rules: Sequence[LiftedPlanRule],
	*,
	domain: object,
	problem_files: Sequence[str | Path],
	max_reachable_states: int = 20000,
) -> tuple[ClingoRequiredRuleGroup, ...]:
	"""Require the selected composer to cover every bounded non-goal state."""

	groups: list[ClingoRequiredRuleGroup] = []
	for problem_position, problem_file in enumerate(tuple(problem_files or ()), start=1):
		problem = PDDLParser.parse_problem(problem_file)
		goal_atoms = tuple(
			fact_atom(fact.predicate, fact.args)
			for fact in problem.goal_facts
			if fact.is_positive
		)
		goal_facts = tuple(
			fact_atom(f"goal_{fact.predicate}", fact.args)
			for fact in problem.goal_facts
			if fact.is_positive
		)
		for index, state in enumerate(
			sorted(
				reachable_states_for_problem(
					domain,
					problem,
					max_states=max_reachable_states,
				),
				key=lambda item: tuple(sorted(item)),
			),
		):
			if all(atom in state for atom in goal_atoms):
				continue
			rule_names = tuple(
				rule.name
				for rule in candidate_rules
				if _composer_rule_is_applicable(
					rule,
					state=state,
					goal_facts=goal_facts,
				)
			)
			if not rule_names:
				raise ValueError(
					"No lifted composer candidate covers bounded reachable state "
					f"{index} in problem {problem.name}.",
				)
			groups.append(
				ClingoRequiredRuleGroup(
					name=f"composer_state_{problem_position}_{problem.name}_{index}",
					rule_names=rule_names,
				),
			)
	return tuple(groups)


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


def transition_progress_required_rule_groups(
	candidate_rules: Sequence[LiftedPlanRule],
	transition_evidence: Sequence[TrainingTransitionEvidence],
) -> tuple[ClingoRequiredRuleGroup, ...]:
	"""Return ASP selector constraints for observed training progress transitions."""

	groups: list[ClingoRequiredRuleGroup] = []
	for evidence in transition_evidence:
		for progression in evidence.goal_progressions:
			rule_names = tuple(
				rule.name
				for rule in candidate_rules
				if _rule_covers_progression(rule, progression)
			)
			if not rule_names:
				raise ValueError(
					"No lifted candidate rule covers bounded transition-progress evidence: "
					f"{evidence.problem_name}: {progression.goal_fact.to_signature()} via "
					f"{progression.action_signature} before step {progression.step_index}.",
				)
			groups.append(
				ClingoRequiredRuleGroup(
					name=(
						f"progress_{evidence.problem_name}_{progression.step_index}_"
						f"{progression.goal_fact.predicate}"
					),
					rule_names=rule_names,
				),
			)
	return tuple(groups)


def _has_selected_progress_rule(
	selected_rules: Sequence[LiftedPlanRule],
	progression,
) -> bool:
	for rule in selected_rules:
		if _rule_covers_progression(rule, progression):
			return True
	return False


def _rule_covers_progression(rule: LiftedPlanRule, progression) -> bool:
	return _rule_covers_action_achievement(
		rule,
		target_fact=progression.goal_fact,
		action_name=progression.action_name,
		action_arguments=progression.action_arguments,
		before_state=frozenset(progression.before_state),
	)


def _rule_covers_action_achievement(
	rule: LiftedPlanRule,
	*,
	target_fact: PDDLFact,
	action_name: str,
	action_arguments: Sequence[str],
	before_state: frozenset[str],
) -> bool:
	"""Return whether a lifted atomic action-rule grounds to one achievement event."""

	if rule.layer != "atomic":
		return False
	if rule.head.symbol != target_fact.predicate:
		return False
	substitution = _substitution_from_head(rule, target_fact)
	if substitution is None:
		return False
	for step in rule.body:
		if step.kind != "action" or step.symbol != action_name:
			continue
		action_substitution = _merge_substitution(
			substitution,
			dict(zip(step.arguments, action_arguments)),
		)
		if action_substitution is None:
			continue
		if all(
			_context_literal_holds(
				literal,
				action_substitution,
				before_state,
			)
			for literal in rule.context
		):
			return True
	return False


def atomic_achievement_justifications(
	selected_rules: Sequence[LiftedPlanRule],
	transition_evidence: Sequence[TrainingTransitionEvidence],
) -> dict[str, tuple]:
	"""Map each selected atomic action-rule to the trace slices that justify it.

	A slice justifies a rule when the rule head grounds to the slice target fact,
	the rule body issues the slice achiever action, and every rule context literal
	holds in the slice before-state. Composer rules and rules with no action body
	are not atomic-module justifications and are omitted from the result.
	"""

	all_slices = tuple(
		slice_
		for evidence in transition_evidence
		for slice_ in getattr(evidence, "atomic_achievements", ()) or ()
	)
	justifications: dict[str, tuple] = {}
	for rule in selected_rules:
		if rule.layer != "atomic":
			continue
		if not any(step.kind == "action" for step in rule.body):
			continue
		supporting = tuple(
			slice_
			for slice_ in all_slices
			if _rule_covers_action_achievement(
				rule,
				target_fact=slice_.target_fact,
				action_name=slice_.action_name,
				action_arguments=slice_.action_arguments,
				before_state=frozenset(slice_.before_state),
			)
		)
		justifications[rule.name] = supporting
	return justifications


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


def _composer_rule_is_applicable(
	rule: LiftedPlanRule,
	*,
	state: State,
	goal_facts: tuple[str, ...],
) -> bool:
	if rule.layer != "composer":
		return False
	if rule.head.symbol != "g" or rule.head.arguments:
		return False
	return bool(
		_context_substitutions(
			contexts=rule.context,
			state=state,
			goal_facts=goal_facts,
		),
	)


def _context_substitutions(
	*,
	contexts: Sequence[str],
	state: State,
	goal_facts: tuple[str, ...],
) -> tuple[dict[str, str], ...]:
	substitutions: tuple[dict[str, str], ...] = ({},)
	for context in contexts:
		next_substitutions: list[dict[str, str]] = []
		for candidate in substitutions:
			next_substitutions.extend(
				_context_literal_substitutions(
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


def _context_literal_substitutions(
	*,
	context: str,
	substitution: dict[str, str],
	state: State,
	goal_facts: tuple[str, ...],
) -> tuple[dict[str, str], ...]:
	text = str(context or "").strip()
	if not text or text.lower() == "true":
		return (dict(substitution),)
	if "!=" in text:
		left, right = text.split("!=", 1)
		return (
			(dict(substitution),)
			if _ground_term(left, substitution) != _ground_term(right, substitution)
			else ()
		)
	if "\\==" in text:
		left, right = text.split("\\==", 1)
		return (
			(dict(substitution),)
			if _ground_term(left, substitution) != _ground_term(right, substitution)
			else ()
		)
	if "==" in text:
		left, right = text.split("==", 1)
		return (
			(dict(substitution),)
			if _ground_term(left, substitution) == _ground_term(right, substitution)
			else ()
		)
	if text.lower().startswith("not "):
		atom = text[4:].strip()
		if _contains_unbound_variables(atom, substitution):
			return ()
		return (
			(dict(substitution),)
			if _ground_context_atom(atom, substitution) not in state
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
	fact_atom_value: str,
	substitution: dict[str, str],
) -> dict[str, str] | None:
	pattern_predicate, pattern_arguments = _parse_atom(pattern_atom)
	fact_predicate, fact_arguments = _parse_atom(fact_atom_value)
	if pattern_predicate != fact_predicate:
		return None
	if len(pattern_arguments) != len(fact_arguments):
		return None
	merged = dict(substitution)
	for pattern, value in zip(pattern_arguments, fact_arguments):
		if _is_variable(pattern):
			if pattern in merged and merged[pattern] != value:
				return None
			merged[pattern] = value
		elif pattern != value:
			return None
	return merged


def _parse_atom(atom: str) -> tuple[str, tuple[str, ...]]:
	text = str(atom or "").strip()
	if "(" not in text:
		return text, ()
	if not text.endswith(")"):
		return text, ()
	predicate, raw_arguments = text.split("(", 1)
	return (
		predicate.strip(),
		tuple(
			argument.strip()
			for argument in raw_arguments[:-1].split(",")
			if argument.strip()
		),
	)


def _contains_unbound_variables(atom: str, substitution: dict[str, str]) -> bool:
	_, arguments = _parse_atom(atom)
	return any(_is_variable(argument) and argument not in substitution for argument in arguments)


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


def _is_variable(token: str) -> bool:
	text = str(token or "").strip()
	return bool(text) and text[0].isupper()


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
