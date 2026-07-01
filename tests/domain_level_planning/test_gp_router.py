from __future__ import annotations

from pathlib import Path

from domain_level_planning.gp_router import GPRouteDecision
from domain_level_planning.gp_router import route_generalized_planner


def test_router_prefers_external_policy_backend_for_serialisable_class(
	tmp_path: Path,
) -> None:
	root = tmp_path / "backends"
	moose = root / "moose"
	moose.mkdir(parents=True)
	(moose / ".git").mkdir()
	(moose / ".git" / "HEAD").write_text("ce1e99b\n", encoding="utf-8")

	decision = route_generalized_planner(
		domain_id="ferry",
		benchmark_class_id="goal_regression_serialisable_goal_domains",
		backend_root=root,
		allow_baseline_schema_lift=True,
	)

	assert decision == GPRouteDecision(
		domain_id="ferry",
		benchmark_class_id="goal_regression_serialisable_goal_domains",
		selected_backend="moose",
		selected_route="goal_regression_policy",
		route_kind="external_gp_backend",
		candidate_backends=("moose", "pg3", "learner-policies-from-examples"),
		rejected_backends=(),
		is_baseline=False,
		blocking_gap=None,
	)


def test_router_falls_back_to_schema_lift_only_as_baseline(
	tmp_path: Path,
) -> None:
	decision = route_generalized_planner(
		domain_id="blocks",
		benchmark_class_id="feature_definable_structural_goal_dependent_domains",
		backend_root=tmp_path,
		allow_baseline_schema_lift=True,
	)

	assert decision.selected_backend == "baseline_schema_lift"
	assert decision.selected_route == "schema_lift_baseline"
	assert decision.route_kind == "baseline_adapter"
	assert decision.is_baseline is True
	assert decision.blocking_gap == "no_trusted_external_gp_backend_available"
	assert decision.candidate_backends == (
		"learner-policies-from-examples",
		"d2l",
		"h-policy-learner",
	)
	assert decision.rejected_backends == (
		{
			"backend": "learner-policies-from-examples",
			"reason": "missing_backend",
		},
		{
			"backend": "d2l",
			"reason": "missing_backend",
		},
		{
			"backend": "h-policy-learner",
			"reason": "missing_backend",
		},
	)


def test_router_rejects_unknown_class_without_silent_schema_path(
	tmp_path: Path,
) -> None:
	decision = route_generalized_planner(
		domain_id="unknown",
		benchmark_class_id="unknown_class",
		backend_root=tmp_path,
		allow_baseline_schema_lift=False,
	)

	assert decision.selected_backend is None
	assert decision.selected_route == "unsupported"
	assert decision.route_kind == "unsupported"
	assert decision.is_baseline is False
	assert decision.candidate_backends == ()
	assert decision.blocking_gap == "no_route_for_benchmark_class"
