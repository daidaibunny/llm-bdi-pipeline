from __future__ import annotations

from domain_level_planning.library_contract import audit_domain_level_library_contract
from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary


def test_domain_level_library_contract_accepts_lifted_predicate_modules() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="g_satisfy_goal_done",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("goal_done(X)", "not done(X)"),
				body=(
					AgentSpeakBodyStep("subgoal", "done", ("X",)),
					AgentSpeakBodyStep("subgoal", "g"),
				),
			),
			AgentSpeakPlan(
				plan_name="done_via_finish",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
				context=("ready(X)",),
				body=(AgentSpeakBodyStep("action", "finish", ("X",)),),
			),
		),
	)

	report = audit_domain_level_library_contract(plan_library)

	assert report.passed is True
	assert all(report.checked_layers.values())
	assert report.violations == ()
	serialized = report.to_dict()
	assert serialized["supported_asl_subset"]["plan_heads"] == (
		"PDDL predicate achievement goals or zero-argument +!g only"
	)
	assert serialized["supported_asl_subset"]["body_steps"] == (
		"PDDL primitive action calls and PDDL predicate subgoal calls only"
	)
	assert serialized["supported_asl_subset"]["contexts"] == (
		"implicit conjunction of atom, not atom, equality, or inequality "
		"context literals only"
	)
	assert serialized["execution_semantics"] == {
		"plan_selection": "deterministic_first_applicable_asl_order",
		"context_semantics": (
			"order-independent implicit conjunction over supported context literals; "
			"positive context atoms bind variables before negated context atoms are checked"
		),
		"negation_semantics": (
			"negation-as-absence over the current state, goal descriptor set, "
			"or derived ready-context set"
		),
		"goal_state_semantics": "fixed point: +!g has no applicable unsatisfied-goal plan",
		"primitive_action_semantics": "PDDL STRIPS simulator applies declared actions",
		"primitive_precondition_semantics": (
			"primitive action preconditions are checked at execution time; "
			"violations produce primitive-precondition counterexamples"
		),
	}
	assert serialized["goal_descriptor_usage"] == {
		"context_descriptors": [
			{
				"descriptor": "goal_done(X)",
				"pddl_predicate": "done",
				"arguments": ["X"],
				"plan_name": "g_satisfy_goal_done",
				"negated": False,
			},
		],
		"mutable_locations": [],
		"read_only": True,
	}


def test_domain_level_library_contract_accepts_declared_pddl_symbols() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="g_satisfy_goal_done",
				trigger=AgentSpeakTrigger("achievement_goal", "g"),
				context=("goal_done(X)", "ready_done(X)", "not done(X)"),
				body=(
					AgentSpeakBodyStep("subgoal", "done", ("X",)),
					AgentSpeakBodyStep("subgoal", "g"),
				),
			),
			AgentSpeakPlan(
				plan_name="done_via_finish",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
				context=("ready(X)",),
				body=(AgentSpeakBodyStep("action", "finish", ("X",)),),
			),
		),
	)

	report = audit_domain_level_library_contract(
		plan_library,
		declared_predicates=("ready", "done"),
		declared_actions=("finish",),
	)

	assert report.passed is True
	assert report.checked_layers["declared_pddl_symbols"] is True
	assert report.violations == ()


def test_domain_level_library_contract_rejects_mutable_ready_contexts() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		initial_beliefs=("ready_done(X)",),
		plans=(
			AgentSpeakPlan(
				plan_name="bad_ready_head",
				trigger=AgentSpeakTrigger("achievement_goal", "ready_done", ("X",)),
				context=(),
				body=(AgentSpeakBodyStep("subgoal", "ready_done", ("X",)),),
			),
		),
	)

	report = audit_domain_level_library_contract(
		plan_library,
		declared_predicates=("done",),
	)

	assert report.passed is False
	assert report.checked_layers["goal_descriptors_read_only"] is False
	assert any("ready context" in violation for violation in report.violations)


def test_domain_level_library_contract_respects_declared_ready_prefix_predicates() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="ready_done_via_prepare",
				trigger=AgentSpeakTrigger("achievement_goal", "ready_done", ("X",)),
				context=("ready_done(X)",),
				body=(AgentSpeakBodyStep("action", "prepare", ("X",)),),
			),
		),
	)

	report = audit_domain_level_library_contract(
		plan_library,
		declared_predicates=("ready_done",),
		declared_actions=("prepare",),
	)

	assert report.passed is True
	assert report.checked_layers["goal_descriptors_read_only"] is True
	assert report.checked_layers["declared_pddl_symbols"] is True


def test_domain_level_library_contract_accepts_lifted_equality_contexts() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="done_when_distinct",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("X", "Y")),
				context=("ready(X)", "not =(X, Y)"),
				body=(AgentSpeakBodyStep("action", "finish", ("X", "Y")),),
			),
		),
	)

	report = audit_domain_level_library_contract(
		plan_library,
		declared_predicates={"ready": 1, "done": 2},
		declared_actions={"finish": 2},
	)

	assert report.passed is True
	assert report.checked_layers["context_subset"] is True
	assert report.checked_layers["declared_pddl_symbols"] is True
	assert report.violations == ()


def test_domain_level_library_contract_rejects_undeclared_pddl_symbols() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="bad_head",
				trigger=AgentSpeakTrigger("achievement_goal", "unknown_head", ("X",)),
				context=("goal_done(X)", "not unknown_context(X)"),
				body=(
					AgentSpeakBodyStep("subgoal", "unknown_subgoal", ("X",)),
					AgentSpeakBodyStep("action", "unknown_action", ("X",)),
				),
			),
		),
	)

	report = audit_domain_level_library_contract(
		plan_library,
		declared_predicates=("done",),
		declared_actions=("finish",),
	)

	assert report.passed is False
	assert report.checked_layers["declared_pddl_symbols"] is False
	assert any("undeclared PDDL predicate" in violation for violation in report.violations)
	assert any("unknown_head" in violation for violation in report.violations)
	assert any("unknown_context" in violation for violation in report.violations)
	assert any("unknown_subgoal" in violation for violation in report.violations)
	assert any("undeclared PDDL action" in violation for violation in report.violations)
	assert any("unknown_action" in violation for violation in report.violations)


def test_domain_level_library_contract_rejects_wrong_pddl_arities() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="bad_arities",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("X", "Y")),
				context=("goal_done(X, Y)", "ready"),
				body=(
					AgentSpeakBodyStep("subgoal", "done", ()),
					AgentSpeakBodyStep("action", "finish", ("X", "Y")),
				),
			),
		),
	)

	report = audit_domain_level_library_contract(
		plan_library,
		declared_predicates={"ready": 1, "done": 1},
		declared_actions={"finish": 1},
	)

	assert report.passed is False
	assert report.checked_layers["declared_pddl_symbols"] is False
	assert any("wrong arity" in violation for violation in report.violations)
	assert any("done/1" in violation for violation in report.violations)
	assert any("ready/1" in violation for violation in report.violations)
	assert any("finish/1" in violation for violation in report.violations)


def test_domain_level_library_contract_rejects_non_achievement_triggers() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="bad_trigger_kind",
				trigger=AgentSpeakTrigger("belief_addition", "done", ("X",)),
				context=("ready(X)",),
				body=(AgentSpeakBodyStep("action", "finish", ("X",)),),
			),
		),
	)

	report = audit_domain_level_library_contract(plan_library)

	assert report.passed is False
	assert report.checked_layers["plan_head_subset"] is False
	assert any("unsupported plan trigger kind" in violation for violation in report.violations)


def test_domain_level_library_contract_rejects_synthetic_or_grounded_output() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		initial_beliefs=("goal_done(a)",),
		plans=(
			AgentSpeakPlan(
				plan_name="achieve_query_transition_1",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("a",)),
				context=("goal_done(a)", "not dfa_state(q0)"),
				body=(
					AgentSpeakBodyStep("subgoal", "goal_done", ("a",)),
					AgentSpeakBodyStep("action", "transition_action", ("a",)),
					AgentSpeakBodyStep("belief_addition", "done", ("a",)),
				),
			),
			AgentSpeakPlan(
				plan_name="bad_context",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
				context=("ready(X) | staged(X)", "X == Y"),
				body=(AgentSpeakBodyStep("action", "finish", ("X",)),),
			),
		),
	)

	report = audit_domain_level_library_contract(plan_library)

	assert report.passed is False
	assert report.checked_layers["no_initial_beliefs"] is False
	assert report.checked_layers["no_synthetic_names"] is False
	assert report.checked_layers["goal_descriptors_read_only"] is False
	assert report.checked_layers["lifted_plan_heads"] is False
	assert report.checked_layers["lifted_body_calls"] is False
	assert report.checked_layers["lifted_contexts"] is False
	assert report.checked_layers["body_step_subset"] is False
	assert report.checked_layers["context_subset"] is False
	assert any("Synthetic name" in violation for violation in report.violations)
	assert any("grounded argument" in violation for violation in report.violations)
	assert any("goal descriptor" in violation for violation in report.violations)
	assert any("unsupported body step kind" in violation for violation in report.violations)
	assert any("unsupported context expression" in violation for violation in report.violations)


def test_domain_level_library_contract_rejects_unbound_body_variables() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="done_via_choose",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
				context=("ready(X)",),
				body=(AgentSpeakBodyStep("action", "choose", ("X", "Y")),),
			),
		),
	)

	report = audit_domain_level_library_contract(plan_library)

	assert report.passed is False
	assert report.checked_layers["variable_binding_safety"] is False
	assert any("unbound variable" in violation for violation in report.violations)
	assert any("Y" in violation for violation in report.violations)


def test_domain_level_library_contract_allows_context_bound_body_variables() -> None:
	plan_library = PlanLibrary(
		domain_name="generic",
		plans=(
			AgentSpeakPlan(
				plan_name="done_via_assigned_tool",
				trigger=AgentSpeakTrigger("achievement_goal", "done", ("X",)),
				context=("assigned(X, Y)", "ready(Y)"),
				body=(AgentSpeakBodyStep("action", "finish", ("X", "Y")),),
			),
		),
	)

	report = audit_domain_level_library_contract(plan_library)

	assert report.passed is True
	assert report.checked_layers["variable_binding_safety"] is True
