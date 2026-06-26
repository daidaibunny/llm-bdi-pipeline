from __future__ import annotations

from pathlib import Path

from domain_level_planning import (
	build_goal_conditioned_library_from_pddl,
	goal_facts_from_problem,
)
from domain_level_planning.library_executor import evaluate_library_on_problem
from domain_level_planning.schema_synthesis import _goal_ordering_rules_from_evidence
from domain_level_planning.schema_synthesis import _candidate_rules_from_domain
from domain_level_planning.schema_synthesis import _training_evidence as _collect_training_evidence
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
	assert "+!g : goal_at(P, L) & ready_at(P, L) & not at(P, L) <-" in asl
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


def test_atomic_achievement_trace_macros_cover_intermediate_predicates(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "relay-domain.pddl"
	problem_file = tmp_path / "relay-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain relay-mini)
		 (:requirements :strips :typing)
		 (:types item place - object)
		 (:predicates
		  (pos ?x - item ?p - place)
		  (link ?from ?to - place)
		  (target ?p - place)
		  (done ?x - item)
		 )
		 (:action move
		  :parameters (?x - item ?from ?to - place)
		  :precondition (and (pos ?x ?from) (link ?from ?to))
		  :effect (and (not (pos ?x ?from)) (pos ?x ?to))
		 )
		 (:action finish
		  :parameters (?x - item ?p - place)
		  :precondition (and (pos ?x ?p) (target ?p))
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem relay-p1)
		 (:domain relay-mini)
		 (:objects box - item a b c - place)
		 (:init (pos box a) (link a b) (link b c) (target c))
		 (:goal (and (done box)))
		)
		""",
		encoding="utf-8",
	)

	plan_library = build_goal_conditioned_library_from_pddl(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
	)
	asl = render_plan_library_asl(plan_library)
	domain = PDDLParser.parse_domain(domain_file)
	_, transition_evidence = _collect_training_evidence(
		domain=domain,
		problem_files=(problem_file,),
	)
	candidate_rules = _candidate_rules_from_domain(
		domain.predicates,
		domain.actions,
		transition_evidence=transition_evidence,
	)

	assert "trace_macro" not in asl
	assert any(
		rule.name.startswith("pos_trace_macro_atomic")
		for rule in candidate_rules
	)


def test_schema_synthesizer_learns_route_progress_for_cyclic_movement(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain route-mini)
		 (:requirements :strips :typing)
		 (:types item place - object)
		 (:predicates
		  (at ?x - item ?p - place)
		  (road ?from - place ?to - place)
		 )
		 (:action move
		  :parameters (?x - item ?from - place ?to - place)
		  :precondition (and (at ?x ?from) (road ?from ?to))
		  :effect (and (not (at ?x ?from)) (at ?x ?to))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem route-p1)
		 (:domain route-mini)
		 (:objects box - item a b c - place)
		 (:init
		  (at box a)
		  (road a b)
		  (road b a)
		  (road b c)
		 )
		 (:goal (and (at box c)))
		)
		""",
		encoding="utf-8",
	)

	plan_library = build_goal_conditioned_library_from_pddl(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
	)
	asl = render_plan_library_asl(plan_library)
	result = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
		max_steps=20,
		max_depth=20,
	)

	assert "route_step_at_move(X, From, Next, To)" in asl
	assert "\tmove(X, From, Next);" in asl
	assert "\t!at(X, To)." in asl
	assert result.solved is True
	assert result.steps == ("move(box, a, b)", "move(box, b, c)")


def test_schema_synthesizer_keeps_duplicate_precondition_prepare_strategies(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain pickup-mini)
		 (:requirements :strips :typing)
		 (:types vehicle package location - object)
		 (:predicates
		  (at ?x - object ?l - location)
		  (in ?p - package ?v - vehicle)
		  (road ?from - location ?to - location)
		 )
		 (:action drive
		  :parameters (?v - vehicle ?from ?to - location)
		  :precondition (and (at ?v ?from) (road ?from ?to))
		  :effect (and (not (at ?v ?from)) (at ?v ?to))
		 )
		 (:action pick-up
		  :parameters (?v - vehicle ?l - location ?p - package)
		  :precondition (and (at ?v ?l) (at ?p ?l))
		  :effect (in ?p ?v)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem pickup-p1)
		 (:domain pickup-mini)
		 (:objects truck - vehicle pkg - package a b - location)
		 (:init (at truck a) (at pkg b) (road a b))
		 (:goal (and (in pkg truck)))
		)
		""",
		encoding="utf-8",
	)

	plan_library = build_goal_conditioned_library_from_pddl(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
	)
	asl = render_plan_library_asl(plan_library)
	result = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
		max_steps=20,
		max_depth=20,
	)

	assert "not at(V, L)" in asl
	assert "\t!at(V, L);" in asl
	assert "not at(P, L)" in asl
	assert "\t!at(P, L);" in asl
	assert result.solved is True
	assert result.steps == ("drive(truck, a, b)", "pick-up(truck, b, pkg)")


def test_schema_synthesizer_learns_typed_carrier_delivery_chain(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain carrier-delivery-mini)
		 (:requirements :strips :typing)
		 (:types locatable place - object carrier package - locatable)
		 (:predicates
		  (at ?x - locatable ?l - place)
		  (loaded ?p - package ?c - carrier)
		  (road ?from - place ?to - place)
		 )
		 (:action move
		  :parameters (?c - carrier ?from - place ?to - place)
		  :precondition (and (at ?c ?from) (road ?from ?to))
		  :effect (and (not (at ?c ?from)) (at ?c ?to))
		 )
		 (:action load
		  :parameters (?c - carrier ?p - package ?from - place)
		  :precondition (and (at ?c ?from) (at ?p ?from))
		  :effect (and (not (at ?p ?from)) (loaded ?p ?c))
		 )
		 (:action unload
		  :parameters (?c - carrier ?p - package ?to - place)
		  :precondition (and (at ?c ?to) (loaded ?p ?c))
		  :effect (and (not (loaded ?p ?c)) (at ?p ?to))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem carrier-delivery-p1)
		 (:domain carrier-delivery-mini)
		 (:objects truck - carrier parcel - package a b c d - place)
		 (:init
		  (at truck a)
		  (at parcel b)
		  (road a b)
		  (road b d)
		  (road d b)
		  (road d c)
		 )
		 (:goal (and (at parcel c)))
		)
		""",
		encoding="utf-8",
	)

	plan_library = build_goal_conditioned_library_from_pddl(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
	)
	asl = render_plan_library_asl(plan_library)
	result = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
		max_steps=30,
		max_depth=30,
	)

	assert "+!at(P, To) : type_carrier(C)" in asl
	assert "\t!loaded(P, C);" in asl
	assert "\t!at(C, To);" in asl
	assert "\tunload(C, P, To)." in asl
	assert result.solved is True
	assert result.steps == (
		"move(truck, a, b)",
		"load(truck, parcel, b)",
		"move(truck, b, d)",
		"move(truck, d, c)",
		"unload(truck, parcel, c)",
	)


def test_schema_synthesizer_uses_resource_bridge_without_resource_causal_chain(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	midstate_problem_file = tmp_path / "midstate-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain resource-delivery-mini)
		 (:requirements :strips :typing)
		 (:types locatable place capacity - object carrier package - locatable)
		 (:predicates
		  (at ?x - locatable ?l - place)
		  (loaded ?p - package ?c - carrier)
		  (road ?from - place ?to - place)
		  (cap ?c - carrier ?s - capacity)
		  (pred ?low - capacity ?high - capacity)
		 )
		 (:action move
		  :parameters (?c - carrier ?from - place ?to - place)
		  :precondition (and (at ?c ?from) (road ?from ?to))
		  :effect (and (not (at ?c ?from)) (at ?c ?to))
		 )
		 (:action load
		  :parameters (?c - carrier ?p - package ?from - place ?low ?high - capacity)
		  :precondition (and
		   (at ?c ?from)
		   (at ?p ?from)
		   (pred ?low ?high)
		   (cap ?c ?high)
		  )
		  :effect (and
		   (not (at ?p ?from))
		   (loaded ?p ?c)
		   (cap ?c ?low)
		   (not (cap ?c ?high))
		  )
		 )
		 (:action unload
		  :parameters (?c - carrier ?p - package ?to - place ?low ?high - capacity)
		  :precondition (and
		   (at ?c ?to)
		   (loaded ?p ?c)
		   (pred ?low ?high)
		   (cap ?c ?low)
		  )
		  :effect (and
		   (not (loaded ?p ?c))
		   (at ?p ?to)
		   (cap ?c ?high)
		   (not (cap ?c ?low))
		  )
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem resource-delivery-p1)
		 (:domain resource-delivery-mini)
		 (:objects truck - carrier parcel - package a b c d - place low high - capacity)
		 (:init
		  (at truck a)
		  (at parcel b)
		  (cap truck high)
		  (pred low high)
		  (road a b)
		  (road b d)
		  (road d b)
		  (road d c)
		 )
		 (:goal (and (at parcel c)))
		)
		""",
		encoding="utf-8",
	)
	midstate_problem_file.write_text(
		"""
		(define (problem resource-delivery-midstate)
		 (:domain resource-delivery-mini)
		 (:objects
		  truck - carrier
		  parcel waiting - package
		  a b c d - place
		  low high - capacity
		 )
		 (:init
		  (at truck b)
		  (at waiting b)
		  (loaded parcel truck)
		  (cap truck low)
		  (pred low high)
		  (road b d)
		  (road d b)
		  (road b c)
		 )
		 (:goal (and
		  (at waiting c)
		  (at parcel d)
		 ))
		)
		""",
		encoding="utf-8",
	)

	plan_library = build_goal_conditioned_library_from_pddl(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
	)
	asl = render_plan_library_asl(plan_library)
	result = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=problem_file,
		max_steps=40,
		max_depth=40,
	)
	midstate_result = evaluate_library_on_problem(
		plan_library=plan_library,
		domain_file=domain_file,
		problem_file=midstate_problem_file,
		max_steps=40,
		max_depth=40,
	)

	assert "at_causal_chain" in asl
	assert "g_current_resource_at_via_loaded" in asl
	assert "cap_causal_chain" not in asl
	at_chain = asl.split("plan=at_causal_chain", 1)[1].split("\n\n", 1)[0]
	assert "\t!cap(" not in at_chain
	assert result.solved is True
	assert result.steps == (
		"move(truck, a, b)",
		"load(truck, parcel, b, low, high)",
		"move(truck, b, d)",
		"move(truck, d, c)",
		"unload(truck, parcel, c, low, high)",
	)
	assert midstate_result.solved is True
	assert midstate_result.steps == (
		"move(truck, b, d)",
		"unload(truck, parcel, d, low, high)",
		"move(truck, d, b)",
		"load(truck, waiting, b, low, high)",
		"move(truck, b, c)",
		"unload(truck, waiting, c, low, high)",
	)


def test_schema_synthesizer_rejects_action_rules_with_unbound_parameters(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "unbound-action-domain.pddl"
	problem_file = tmp_path / "unbound-action-problem.pddl"
	domain_file.write_text(
		"""
		(define (domain unbound-action-mini)
		 (:requirements :strips)
		 (:predicates
		  (ready ?x)
		  (done ?x)
		 )
		 (:action choose
		  :parameters (?x ?y)
		  :precondition (ready ?x)
		  :effect (done ?x)
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem unbound-action-p1)
		 (:domain unbound-action-mini)
		 (:objects a b)
		 (:init (ready a))
		 (:goal (and (done a)))
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
		message = str(exc)
		assert "No lifted candidate rule covers bounded transition-progress evidence" in message
		assert "done(a)" in message
	else:
		raise AssertionError("Expected unbound action-parameter rule to be rejected.")


def test_schema_synthesizer_also_handles_blocksworld_without_domain_specific_code() -> None:
	plan_library = build_goal_conditioned_library_from_pddl(
		domain_file=BLOCKS_DOMAIN,
		training_problem_files=(BLOCKS_P01,),
	)
	asl = render_plan_library_asl(plan_library)

	assert "+!g : goal_on(X, Y) & ready_on(X, Y) & not on(X, Y) <-" in asl
	assert "+!on(X, Y) : on(X, Y) <-" in asl
	assert "+!on(X, Y) : type_block(X) & type_block(Y) & not holding(X) <-" in asl
	assert "\t!holding(X);" in asl
	assert (
		"+!on(X, Y) : type_block(X) & type_block(Y) & holding(X) & clear(Y) <-"
		in asl
	)
	assert "\tstack(X, Y)." in asl
	assert "goal_on(b4, b2)." not in asl
	assert "+!g : goal_on(Y, Z) & goal_on(X, Y) & not on(Y, Z) <-" in asl
	assert "+!g : goal_on(Z, W) & goal_on(X, Y) & not on(Z, W) <-" not in asl
	runtime_agenda = plan_library.metadata["runtime_goal_agenda"]
	assert runtime_agenda["read_only_ready_contexts"] is True
	assert runtime_agenda["support_edge_count"] >= 1
	assert all(edge["category"] == "support" for edge in runtime_agenda["support_edges"])
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
	assert report["runtime_goal_agenda"]["read_only_ready_contexts"] is True
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
	generic_plan = "+!g : goal_on(X, Y) & ready_on(X, Y) & not on(X, Y) <-"
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


def test_causal_interference_uses_multi_hop_binding_preconditions_for_hidden_goal_argument(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "multi-hop-causal-domain.pddl"
	domain_file.write_text(
		"""
		(define (domain multi-hop-causal-mini)
		 (:requirements :strips)
		 (:predicates
		  (assigned ?task ?station)
		  (station_tool ?station ?tool)
		  (prepared ?tool)
		  (done ?task)
		 )
		 (:action prepare
		  :parameters (?tool)
		  :precondition ()
		  :effect (prepared ?tool)
		 )
		 (:action finish
		  :parameters (?task ?station ?tool)
		  :precondition (and
		   (assigned ?task ?station)
		   (station_tool ?station ?tool)
		   (prepared ?tool)
		  )
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
			"goal_prepared(Z)",
			"goal_done(X)",
			"assigned(X, Y)",
			"station_tool(Y, Z)",
			"not prepared(Z)",
		)
	)
	assert len(indirect_rules) == 1
	rule = indirect_rules[0]
	assert rule.body == (
		LiftedCall("subgoal", "prepared", ("Z",)),
		LiftedCall("subgoal", "g", ()),
	)
	assert any(
		capability.startswith(
			"causal_order_prepared_Z_before_done_X_via_assigned_station_tool",
		)
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


def test_recursion_descent_prefers_ranking_for_prefixed_argument_changing_recursion() -> None:
	rule = LiftedPlanRule(
		name="pos_prepare_ready_then_recurse",
		head=LiftedCall("subgoal", "pos", ("P", "To")),
		context=("link(From, To)", "not ready(P)"),
		body=(
			LiftedCall("subgoal", "ready", ("P",)),
			LiftedCall("subgoal", "pos", ("P", "From")),
			LiftedCall("subgoal", "pos", ("P", "To")),
		),
		layer="atomic",
	)
	ranking_states = (
		frozenset({"link(a, b)", "link(b, c)"}),
	)

	filtered, audit = filter_rules_by_recursion_descent(
		(rule,),
		ranking_states=ranking_states,
	)

	assert filtered == (rule,)
	assert audit["accepted_recursive_rule_count"] == 1
	certificate = audit["certificates"][0]
	assert certificate["accepted"] is True
	assert certificate["ranking_relation"] == "link"
	assert certificate["ranking_edge"] == "To->From"


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
