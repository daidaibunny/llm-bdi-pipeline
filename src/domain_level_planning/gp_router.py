"""
Conservative router for generalized-planning backends.

This module is the code-level boundary for the current research pivot: the main
route should be an external generalized-planning backend whose artifact is later
normalized into a LiftedPolicyProgram. The older schema-derived synthesizer is
kept only as an explicit baseline adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .gp_backends import DEFAULT_BACKEND_ROOT
from .gp_backends import PINNED_BACKENDS
from .gp_backends import backend_consumption_role
from .gp_backends import discover_backend_manifest


@dataclass(frozen=True)
class GPBackendRoute:
	"""One backend option for a benchmark class."""

	backend_name: str
	route_name: str


@dataclass(frozen=True)
class GPRouteDecision:
	"""Machine-readable decision made before generalized-policy synthesis."""

	domain_id: str
	benchmark_class_id: str
	selected_backend: str | None
	selected_route: str
	route_kind: str
	candidate_backends: tuple[str, ...]
	rejected_backends: tuple[dict[str, str], ...]
	is_baseline: bool
	blocking_gap: str | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"domain_id": self.domain_id,
			"benchmark_class_id": self.benchmark_class_id,
			"selected_backend": self.selected_backend,
			"selected_route": self.selected_route,
			"route_kind": self.route_kind,
			"candidate_backends": list(self.candidate_backends),
			"rejected_backends": [dict(item) for item in self.rejected_backends],
			"is_baseline": self.is_baseline,
			"blocking_gap": self.blocking_gap,
		}


ROUTING_CLASSES: Mapping[str, tuple[GPBackendRoute, ...]] = {
	"goal_regression_serialisable_goal_domains": (
		GPBackendRoute("moose", "goal_regression_policy"),
		GPBackendRoute("pg3", "lifted_decision_list_policy"),
		GPBackendRoute("learner-policies-from-examples", "feature_policy"),
	),
	"bounded_width_sketchable_subgoal_structure_domains": (
		GPBackendRoute("learner-sketches", "bounded_width_sketch"),
		GPBackendRoute("h-policy-learner", "hierarchical_width_policy"),
		GPBackendRoute("learner-policies-from-examples", "feature_policy"),
		GPBackendRoute("d2l", "description_logic_policy"),
	),
	"feature_definable_structural_goal_dependent_domains": (
		GPBackendRoute("learner-policies-from-examples", "feature_policy"),
		GPBackendRoute("d2l", "description_logic_policy"),
		GPBackendRoute("h-policy-learner", "hierarchical_width_policy"),
	),
}

LEGACY_CLASS_ALIASES: Mapping[str, str] = {
	"goal_separable_serialisable_achievement_classes": (
		"goal_regression_serialisable_goal_domains"
	),
	"bounded_width_sketchable_subgoal_structure_classes": (
		"bounded_width_sketchable_subgoal_structure_domains"
	),
	"feature_definable_goal_dependent_construction_classes": (
		"feature_definable_structural_goal_dependent_domains"
	),
}

def route_generalized_planner(
	*,
	domain_id: str,
	benchmark_class_id: str,
	backend_root: str | Path | None = None,
	allow_baseline_schema_lift: bool = False,
) -> GPRouteDecision:
	"""Select the first trusted generalized-planning backend for a domain class."""

	normalized_class = _normalize_class_id(benchmark_class_id)
	routes = tuple(ROUTING_CLASSES.get(normalized_class, ()))
	if not routes:
		return GPRouteDecision(
			domain_id=domain_id,
			benchmark_class_id=benchmark_class_id,
			selected_backend=None,
			selected_route="unsupported",
			route_kind="unsupported",
			candidate_backends=(),
			rejected_backends=(),
			is_baseline=False,
			blocking_gap="no_route_for_benchmark_class",
		)

	root = Path(backend_root) if backend_root is not None else DEFAULT_BACKEND_ROOT
	rejected: list[dict[str, str]] = []
	for route in routes:
		rejection = _backend_rejection_reason(route.backend_name, root=root)
		if rejection is None:
			return GPRouteDecision(
				domain_id=domain_id,
				benchmark_class_id=normalized_class,
				selected_backend=route.backend_name,
				selected_route=route.route_name,
				route_kind="external_gp_backend",
				candidate_backends=tuple(item.backend_name for item in routes),
				rejected_backends=tuple(rejected),
				is_baseline=False,
				blocking_gap=None,
			)
		rejected.append({"backend": route.backend_name, "reason": rejection})

	if allow_baseline_schema_lift:
		return GPRouteDecision(
			domain_id=domain_id,
			benchmark_class_id=normalized_class,
			selected_backend="baseline_schema_lift",
			selected_route="schema_lift_baseline",
			route_kind="baseline_adapter",
			candidate_backends=tuple(item.backend_name for item in routes),
			rejected_backends=tuple(rejected),
			is_baseline=True,
			blocking_gap="no_trusted_external_gp_backend_available",
		)
	return GPRouteDecision(
		domain_id=domain_id,
		benchmark_class_id=normalized_class,
		selected_backend=None,
		selected_route="unsupported",
		route_kind="unsupported",
		candidate_backends=tuple(item.backend_name for item in routes),
		rejected_backends=tuple(rejected),
		is_baseline=False,
		blocking_gap="no_trusted_external_gp_backend_available",
	)


def _normalize_class_id(benchmark_class_id: str) -> str:
	return LEGACY_CLASS_ALIASES.get(benchmark_class_id, benchmark_class_id)


def _backend_rejection_reason(backend_name: str, *, root: Path) -> str | None:
	if backend_name == "moose":
		return None if _moose_backend_present(root) else "missing_backend"
	backend_def = _pinned_backend_definition(backend_name)
	if backend_def is None:
		return "backend_not_pinned_or_not_installed"
	manifest = discover_backend_manifest(
		root=root,
		name=backend_name,
		url=str(backend_def["url"]),
		commit=str(backend_def["commit"]),
	)
	if not manifest.present:
		return "missing_backend"
	role = backend_consumption_role(backend_name)
	if not bool(role.get("consumed_by_synthesis")):
		return str(role.get("blocking_gap") or "backend_not_consumable")
	return None


def _pinned_backend_definition(backend_name: str) -> Mapping[str, object] | None:
	for backend in PINNED_BACKENDS:
		if str(backend["name"]) == backend_name:
			return backend
	return None


def _moose_backend_present(root: Path) -> bool:
	candidates = [root / "moose", root.parent / "moose"]
	if root.expanduser().resolve() == DEFAULT_BACKEND_ROOT.expanduser().resolve():
		candidates.append(PROJECT_EXTERNAL_ROOT / "moose")
	return any(
		(candidate / ".git").exists() or candidate.exists()
		for candidate in candidates
	)


PROJECT_EXTERNAL_ROOT = Path(__file__).resolve().parents[2] / ".external"
