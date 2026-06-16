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
				),
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
	assert any("Synthetic name" in violation for violation in report.violations)
	assert any("grounded argument" in violation for violation in report.violations)
	assert any("goal descriptor" in violation for violation in report.violations)
