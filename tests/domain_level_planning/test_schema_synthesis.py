from __future__ import annotations

from pathlib import Path

from domain_level_planning import (
	build_goal_conditioned_library_from_pddl,
	goal_facts_from_problem,
)
from domain_level_planning.schema_synthesis import _goal_ordering_rules_from_evidence
from domain_level_planning.schema_synthesis import _validate_selected_rules_against_transition_progress
from domain_level_planning.schema_synthesis import atomic_achievement_justifications
from domain_level_planning.schema_synthesis import causal_interference_ordering_rules
from domain_level_planning.schema_synthesis import composer_state_coverage_required_rule_groups
from domain_level_planning.schema_synthesis import filter_rules_by_recursion_descent
from domain_level_planning.schema_synthesis import recursion_descent_audit
from domain_level_planning.schema_synthesis import transition_progress_required_rule_groups
from utils.pddl_parser import PDDLParser
from domain_level_planning.models import LiftedCall, LiftedPlanRule
from domain_level_planning.transition_system import TrainingTransitionEvidence
from domain_level_planning.transition_system import GoalProgressEvidence
from plan_library.rendering import render_plan_library_asl
from utils.pddl_parser import PDDLFact


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DOMAIN = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "domain.pddl"
BLOCKS_P01 = PROJECT_ROOT / "src" / "domains" / "blocksworld" / "problems" / "p01.pddl"


def test_schema_synthesizer_builds_lifted_modules_from_any_pddl_domain() -> None:
	domain_file, problem_file = _write_logistics_domain_and_problem()

	plan_library = build_goal_conditioned_library_from_pddl(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
	)
	asl = render_plan_library_asl(plan_library)

	assert plan_library.domain_name == "logistics-mini"
	assert plan_library.initial_beliefs == ()
	assert plan_library.metadata["generation_mode"] == "unified_goal_conditioned_modular_synthesis"
	assert "+!g : goal_at(P, L) & not at(P, L) <-" in asl
	assert "\t!at(P, L);" in asl
	assert "+!at(P, L) : at(P, L) <-" in asl
	assert "+!at(P, To) : not at(P, From) <-" not in asl
	assert "+!at(P, To) : at(P, From) & road(From, To) <-" in asl
	assert "\tdrive(P, From, To)." in asl
	assert "goal_at(pkg1, depot)." not in asl
	assert "plan=g_done" not in asl
	assert "!achieve_" not in asl
	assert "!transition_" not in asl
	assert "dfa_state" not in asl


def test_schema_synthesizer_also_handles_blocksworld_without_domain_specific_code() -> None:
	plan_library = build_goal_conditioned_library_from_pddl(
		domain_file=BLOCKS_DOMAIN,
		training_problem_files=(BLOCKS_P01,),
	)
	asl = render_plan_library_asl(plan_library)

	assert "+!g : goal_on(X, Y) & not on(X, Y) <-" in asl
	assert "+!on(X, Y) : on(X, Y) <-" in asl
	assert "+!on(X, Y) : not holding(X) <-" in asl
	assert "\t!holding(X);" in asl
	assert "+!on(X, Y) : holding(X) & clear(Y) <-" in asl
	assert "\tstack(X, Y)." in asl
	assert "goal_on(b4, b2)." not in asl
	assert "+!g : goal_on(Y, Z) & goal_on(X, Y) & not on(Y, Z) <-" in asl
	assert "+!g : goal_on(Z, W) & goal_on(X, Y) & not on(Z, W) <-" not in asl
	transition_systems = plan_library.metadata["transition_systems"]
	assert transition_systems[0]["goal_facts"] == [
		"goal_on(b4, b2)",
		"goal_on(b1, b4)",
		"goal_on(b3, b1)",
	]
	assert transition_systems[0]["goal_orderings"] == [
		("goal_on(b4, b2)", "goal_on(b1, b4)"),
		("goal_on(b4, b2)", "goal_on(b3, b1)"),
		("goal_on(b1, b4)", "goal_on(b3, b1)"),
	]


def test_goal_facts_from_problem_are_read_only_problem_inputs() -> None:
	goal_facts = goal_facts_from_problem(BLOCKS_P01)

	assert goal_facts == (
		"goal_on(b4, b2)",
		"goal_on(b1, b4)",
		"goal_on(b3, b1)",
	)


def test_synthesis_report_exposes_clingo_schema_contract() -> None:
	domain_file, _ = _write_logistics_domain_and_problem()
	plan_library = build_goal_conditioned_library_from_pddl(domain_file=domain_file)
	report = plan_library.metadata["unified_synthesis_report"]

	assert report["theoretical_contract"] == "bounded_class_guarantee"
	assert report["generation_mode"] == "unified_goal_conditioned_modular_synthesis"
	assert report["external_policy_count"] == 0
	assert report["selected_rule_count"] > 0
	assert report["candidate_count"] >= report["selected_rule_count"]


def test_goal_ordering_rules_filter_ambiguous_lifted_ordering_evidence() -> None:
	forward = (
		PDDLFact("on", ["b", "c"]),
		PDDLFact("on", ["a", "b"]),
	)
	reverse = (
		PDDLFact("on", ["a", "b"]),
		PDDLFact("on", ["b", "c"]),
	)
	rules = _goal_ordering_rules_from_evidence(
		(
			_training_evidence("forward", (forward,)),
			_training_evidence("reverse", (reverse,)),
		),
	)

	assert rules == ()


def test_transition_progress_validation_rejects_selected_rules_with_wrong_action() -> None:
	evidence = TrainingTransitionEvidence(
		problem_name="p1",
		object_count=1,
		explored_state_count=2,
		explored_transition_count=1,
		plan_length=1,
		goal_facts=("goal_done(a)",),
		goal_orderings=(),
		goal_progressions=(
			GoalProgressEvidence(
				goal_fact=PDDLFact("done", ["a"]),
				action_name="finish",
				action_arguments=("a",),
				action_signature="finish(a)",
				step_index=1,
				before_state=("ready(a)",),
				after_state=("done(a)", "ready(a)"),
			),
		),
	)
	rule = LiftedPlanRule(
		name="done_via_wrong_action",
		head=LiftedCall("subgoal", "done", ("X",)),
		context=("ready(X)",),
		body=(LiftedCall("action", "wait", ("X",)),),
		layer="atomic",
	)

	try:
		_validate_selected_rules_against_transition_progress((rule,), (evidence,))
	except ValueError as exc:
		assert "fails bounded transition-progress validation" in str(exc)
	else:
		raise AssertionError("Expected wrong selected action to fail validation.")


def test_transition_progress_evidence_becomes_selector_constraints() -> None:
	evidence = TrainingTransitionEvidence(
		problem_name="p1",
		object_count=1,
		explored_state_count=2,
		explored_transition_count=1,
		plan_length=1,
		goal_facts=("goal_done(a)",),
		goal_orderings=(),
		goal_progressions=(
			GoalProgressEvidence(
				goal_fact=PDDLFact("done", ["a"]),
				action_name="finish",
				action_arguments=("a",),
				action_signature="finish(a)",
				step_index=1,
				before_state=("ready(a)",),
				after_state=("done(a)", "ready(a)"),
			),
		),
	)
	matching_rule = LiftedPlanRule(
		name="done_via_finish",
		head=LiftedCall("subgoal", "done", ("X",)),
		context=("ready(X)",),
		body=(LiftedCall("action", "finish", ("X",)),),
		layer="atomic",
	)
	wrong_rule = LiftedPlanRule(
		name="done_via_wait",
		head=LiftedCall("subgoal", "done", ("X",)),
		context=("ready(X)",),
		body=(LiftedCall("action", "wait", ("X",)),),
		layer="atomic",
	)

	groups = transition_progress_required_rule_groups(
		(wrong_rule, matching_rule),
		(evidence,),
	)

	assert len(groups) == 1
	assert groups[0].rule_names == ("done_via_finish",)


def test_composer_state_coverage_becomes_selector_constraints(tmp_path: Path) -> None:
	domain_file, problem_file = _write_logistics_domain_and_problem(tmp_path)
	domain = PDDLParser.parse_domain(domain_file)
	applicable_rule = LiftedPlanRule(
		name="g_satisfy_at",
		head=LiftedCall("subgoal", "g", ()),
		context=("goal_at(P, L)", "not at(P, L)"),
		body=(LiftedCall("subgoal", "at", ("P", "L")),),
		layer="composer",
		capabilities=("compose_goal_at",),
		cost=5,
	)
	inapplicable_rule = LiftedPlanRule(
		name="g_bad_route",
		head=LiftedCall("subgoal", "g", ()),
		context=("goal_at(P, L)", "blocked(P)"),
		body=(LiftedCall("subgoal", "at", ("P", "L")),),
		layer="composer",
		capabilities=("compose_goal_at",),
		cost=1,
	)

	groups = composer_state_coverage_required_rule_groups(
		(inapplicable_rule, applicable_rule),
		domain=domain,
		problem_files=(problem_file,),
	)

	assert len(groups) == 1
	assert groups[0].rule_names == ("g_satisfy_at",)


def test_unsupported_negative_training_goal_fails_instead_of_silent_fallback(
	tmp_path: Path,
) -> None:
	domain_file, _ = _write_logistics_domain_and_problem(tmp_path)
	problem_file = tmp_path / "negative-goal.pddl"
	problem_file.write_text(
		"""
		(define (problem negative-goal)
		 (:domain logistics-mini)
		 (:objects pkg1 depot - object)
		 (:init (at pkg1 depot))
		 (:goal (and (not (at pkg1 depot))))
		)
		""",
		encoding="utf-8",
	)

	try:
		build_goal_conditioned_library_from_pddl(
			domain_file=domain_file,
			training_problem_files=(problem_file,),
		)
	except ValueError as exc:
		assert "positive achievement goals only" in str(exc)
	else:
		raise AssertionError("Expected unsupported negative goal to fail.")


def test_atomic_achievement_justifications_explain_selected_action_rules() -> None:
	domain = PDDLParser.parse_domain(BLOCKS_DOMAIN)
	problem = PDDLParser.parse_problem(BLOCKS_P01)
	from domain_level_planning.transition_system import (
		collect_training_transition_evidence,
	)

	evidence = collect_training_transition_evidence(domain, problem)
	# A schema-derived atomic rule: on(X,Y) is achieved by stack(X,Y).
	on_via_stack = LiftedPlanRule(
		name="on_via_stack",
		head=LiftedCall("subgoal", "on", ("X", "Y")),
		context=("holding(X)", "clear(Y)"),
		body=(LiftedCall("action", "stack", ("X", "Y")),),
		layer="atomic",
	)
	wrong_action = LiftedPlanRule(
		name="on_via_unstack",
		head=LiftedCall("subgoal", "on", ("X", "Y")),
		context=("holding(X)", "clear(Y)"),
		body=(LiftedCall("action", "unstack", ("X", "Y")),),
		layer="atomic",
	)

	justifications = atomic_achievement_justifications(
		(on_via_stack, wrong_action),
		(evidence,),
	)

	# The stack rule is justified by real trace slices; the unstack rule is not.
	assert justifications["on_via_stack"]
	assert justifications["on_via_unstack"] == ()
	# Each supporting slice grounds the rule head to a concrete on(...) fact.
	for slice_ in justifications["on_via_stack"]:
		assert slice_.target_fact.predicate == "on"
		assert slice_.action_name == "stack"


def test_atomic_achievement_justifications_ignore_composer_rules() -> None:
	domain = PDDLParser.parse_domain(BLOCKS_DOMAIN)
	problem = PDDLParser.parse_problem(BLOCKS_P01)
	from domain_level_planning.transition_system import (
		collect_training_transition_evidence,
	)

	evidence = collect_training_transition_evidence(domain, problem)
	composer = LiftedPlanRule(
		name="g_satisfy_goal_on",
		head=LiftedCall("subgoal", "g", ()),
		context=("goal_on(X, Y)", "not on(X, Y)"),
		body=(LiftedCall("subgoal", "on", ("X", "Y")), LiftedCall("subgoal", "g", ())),
		layer="composer",
	)

	justifications = atomic_achievement_justifications((composer,), (evidence,))

	assert justifications == {}


def test_causal_interference_orders_blocksworld_tower_without_traces() -> None:
	domain = PDDLParser.parse_domain(BLOCKS_DOMAIN)

	rules = causal_interference_ordering_rules(domain)

	# Schema-only causal structure must recover the bottom-up tower ordering:
	# on(Y,Z) before on(X,Y), driven by stack(Y,Z) supplying clear(Y) which
	# stack(X,Y) consumes as a precondition. No trace evidence is used.
	tower_rules = [
		rule
		for rule in rules
		if rule.head.symbol == "g"
		and any(call.symbol == "on" for call in rule.body)
		and len(
			[
				context
				for context in rule.context
				if context.strip().startswith("goal_on(")
			],
		)
		== 2
	]
	assert tower_rules
	rule = tower_rules[0]
	assert rule.layer == "composer"
	# Earlier achieved goal is the lower pair on(Y, Z); the rule pursues it first.
	assert ("goal_on", "Y", "Z") == _goal_context_signature(rule.context, "on", 0)
	assert ("goal_on", "X", "Y") == _goal_context_signature(rule.context, "on", 1)
	first_body = rule.body[0]
	assert first_body.symbol == "on"
	assert first_body.arguments == ("Y", "Z")
	# Every candidate exposes a schema causal-interference capability.
	for candidate in rules:
		assert any(
			capability.startswith(("causal_order_", "delete_threat_order_"))
			for capability in candidate.capabilities
		)


def test_schema_synthesis_selects_schema_causal_ordering_without_traces() -> None:
	plan_library = build_goal_conditioned_library_from_pddl(
		domain_file=BLOCKS_DOMAIN,
		training_problem_files=(),
	)
	asl = render_plan_library_asl(plan_library)
	report = plan_library.metadata["unified_synthesis_report"]

	causal_plan = "+!g : goal_on(Y, Z) & goal_on(X, Y) & not on(Y, Z) <-"
	generic_plan = "+!g : goal_on(X, Y) & not on(X, Y) <-"
	assert causal_plan in asl
	assert asl.index(causal_plan) < asl.index(generic_plan)
	assert (
		report["evidence_matrix"]["layer_c_goal_composer"][
			"causal_interference_selected_count"
		]
		> 0
	)


def test_causal_interference_orders_delete_threat_goals_without_traces(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "delete-threat-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain delete-threat-mini)
		 (:requirements :strips)
		 (:predicates
		  (ready ?x)
		  (a ?x)
		  (b ?x)
		 )
		 (:action make-a
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (and (a ?x) (not (b ?x)))
		 )
		 (:action make-b
		  :parameters (?x)
		  :precondition (ready ?x)
		  :effect (b ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	domain = PDDLParser.parse_domain(domain_file)

	rules = causal_interference_ordering_rules(domain)

	delete_threat_rules = tuple(
		rule
		for rule in rules
		if any(
			capability.startswith("delete_threat_order_a_")
			for capability in rule.capabilities
		)
	)
	assert len(delete_threat_rules) == 1
	rule = delete_threat_rules[0]
	assert rule.context == ("goal_a(X)", "goal_b(X)", "not a(X)")
	assert rule.body == (
		LiftedCall("subgoal", "a", ("X",)),
		LiftedCall("subgoal", "g", ()),
	)


def test_causal_interference_uses_binding_preconditions_for_hidden_goal_argument(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "indirect-causal-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain indirect-causal-mini)
		 (:requirements :strips)
		 (:predicates
		  (assigned ?task ?tool)
		  (prepared ?tool)
		  (done ?task)
		 )
		 (:action prepare
		  :parameters (?tool)
		  :precondition ()
		  :effect (prepared ?tool)
		 )
		 (:action finish
		  :parameters (?task ?tool)
		  :precondition (and (assigned ?task ?tool) (prepared ?tool))
		  :effect (done ?task)
		 )
		)
		""",
		encoding="utf-8",
	)
	domain = PDDLParser.parse_domain(domain_file)

	rules = causal_interference_ordering_rules(domain)

	indirect_rules = tuple(
		rule
		for rule in rules
		if rule.context
		== (
			"goal_prepared(Y)",
			"goal_done(X)",
			"assigned(X, Y)",
			"not prepared(Y)",
		)
	)
	assert len(indirect_rules) == 1
	rule = indirect_rules[0]
	assert rule.body == (
		LiftedCall("subgoal", "prepared", ("Y",)),
		LiftedCall("subgoal", "g", ()),
	)
	assert any(
		capability.startswith("causal_order_prepared_Y_before_done_X")
		for capability in rule.capabilities
	)


def test_causal_interference_orderings_are_empty_without_shared_structure(
	tmp_path: Path,
) -> None:
	domain_file, _ = _write_logistics_domain_and_problem(tmp_path)
	domain = PDDLParser.parse_domain(domain_file)

	rules = causal_interference_ordering_rules(domain)

	# logistics-mini has a single goal predicate with no producer/consumer chain
	# across goal instances, so no causal ordering should be invented.
	assert rules == ()


def test_recursion_descent_audit_accepts_missing_precondition_prepare_rule() -> None:
	rule = LiftedPlanRule(
		name="holding_prepare_ready_for_grab",
		head=LiftedCall("subgoal", "holding", ("X",)),
		context=("not ready(X)",),
		body=(
			LiftedCall("subgoal", "ready", ("X",)),
			LiftedCall("subgoal", "holding", ("X",)),
		),
		layer="atomic",
	)

	audit = recursion_descent_audit((rule,))

	assert audit["recursive_rule_count"] == 1
	assert audit["accepted_recursive_rule_count"] == 1
	assert audit["rejected_recursive_rule_count"] == 0
	certificate = audit["certificates"][0]
	assert certificate["rule_name"] == "holding_prepare_ready_for_grab"
	assert certificate["accepted"] is True
	assert certificate["descent_subgoal"] == "ready(X)"
	assert certificate["missing_context"] == "not ready(X)"


def test_recursion_descent_filter_rejects_self_recursion_without_progress() -> None:
	unsafe = LiftedPlanRule(
		name="done_unsafe_self_loop",
		head=LiftedCall("subgoal", "done", ("X",)),
		context=("not done(X)",),
		body=(LiftedCall("subgoal", "done", ("X",)),),
		layer="atomic",
	)
	safe = LiftedPlanRule(
		name="done_via_finish",
		head=LiftedCall("subgoal", "done", ("X",)),
		context=("ready(X)",),
		body=(LiftedCall("action", "finish", ("X",)),),
		layer="atomic",
	)

	filtered, audit = filter_rules_by_recursion_descent((unsafe, safe))

	assert filtered == (safe,)
	assert audit["recursive_rule_count"] == 1
	assert audit["accepted_recursive_rule_count"] == 0
	assert audit["rejected_recursive_rule_count"] == 1
	assert audit["violations"] == (
		"done_unsafe_self_loop: no missing positive precondition subgoal appears before recursion",
	)


def test_recursion_descent_filter_rejects_recursive_call_without_ranking() -> None:
	rule = LiftedPlanRule(
		name="at_recursive_path_without_ranking",
		head=LiftedCall("subgoal", "at", ("P", "To")),
		context=("road(From, To)", "not at(P, From)"),
		body=(
			LiftedCall("subgoal", "at", ("P", "From")),
			LiftedCall("subgoal", "at", ("P", "To")),
		),
		layer="atomic",
	)

	filtered, audit = filter_rules_by_recursion_descent((rule,))

	assert filtered == ()
	assert audit["rejected_recursive_rule_count"] == 1
	assert audit["certificates"][0]["accepted"] is False
	assert "requires an explicit ranking feature" in audit["certificates"][0]["reason"]


def test_recursion_descent_accepts_argument_changing_recursion_with_acyclic_relation() -> None:
	rule = LiftedPlanRule(
		name="clear_prepare_clear_for_unstack",
		head=LiftedCall("subgoal", "clear", ("Y",)),
		context=("on(X, Y)", "not clear(X)"),
		body=(
			LiftedCall("subgoal", "clear", ("X",)),
			LiftedCall("subgoal", "clear", ("Y",)),
		),
		layer="atomic",
	)
	ranking_states = (
		frozenset({"on(a, b)", "on(b, c)"}),
		frozenset({"on(d, e)"}),
	)

	filtered, audit = filter_rules_by_recursion_descent(
		(rule,),
		ranking_states=ranking_states,
	)

	assert filtered == (rule,)
	assert audit["accepted_recursive_rule_count"] == 1
	certificate = audit["certificates"][0]
	assert certificate["accepted"] is True
	assert certificate["ranking_relation"] == "on"
	assert certificate["ranking_edge"] == "Y->X"
	assert certificate["reason"] == "recursive call follows a bounded acyclic context relation"


def _goal_context_signature(
	context: tuple[str, ...],
	predicate: str,
	occurrence: int,
) -> tuple[str, ...]:
	matches = [
		literal
		for literal in context
		if literal.strip().startswith(f"goal_{predicate}(")
	]
	literal = matches[occurrence].strip()
	name, raw = literal.split("(", 1)
	args = tuple(part.strip() for part in raw[:-1].split(","))
	return (name, *args)


def _write_logistics_domain_and_problem(
	tmp_path: Path | None = None,
) -> tuple[Path, Path]:
	root = tmp_path or Path.cwd() / "tmp" / "schema-synthesis-tests"
	root.mkdir(parents=True, exist_ok=True)
	domain_file = root / "domain.pddl"
	problem_file = root / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain logistics-mini)
		 (:requirements :strips :typing)
		 (:types object)
		 (:predicates
		  (at ?p - object ?l - object)
		  (road ?from - object ?to - object)
		 )
		 (:action drive
		  :parameters (?p - object ?from - object ?to - object)
		  :precondition (and (at ?p ?from) (road ?from ?to))
		  :effect (and (not (at ?p ?from)) (at ?p ?to))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem logistics-p1)
		 (:domain logistics-mini)
		 (:objects pkg1 depot hub - object)
		 (:init (at pkg1 hub) (road hub depot))
		 (:goal (and (at pkg1 depot)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _training_evidence(
	name: str,
	orderings: tuple[tuple[PDDLFact, PDDLFact], ...],
) -> TrainingTransitionEvidence:
	return TrainingTransitionEvidence(
		problem_name=name,
		object_count=3,
		explored_state_count=1,
		explored_transition_count=1,
		plan_length=1,
		goal_facts=(),
		goal_orderings=orderings,
	)
