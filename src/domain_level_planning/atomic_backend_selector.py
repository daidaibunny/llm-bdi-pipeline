"""
Backend selection for lifted atomic literal template generation.

This module replaces the old planning-family router on the main path. The new
question is not "which class does this domain belong to?", but "which external
generalized-planning backend can produce reusable templates for the atomic goal
items seen in this training split?".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from utils.pddl_parser import PDDLFact
from utils.pddl_parser import PDDLParser

from .gp_backends import DEFAULT_BACKEND_ROOT
from .gp_backends import PINNED_BACKENDS
from .gp_backends import backend_consumption_role
from .gp_backends import discover_backend_manifest


PROJECT_EXTERNAL_ROOT = Path(__file__).resolve().parents[2] / ".external"


@dataclass(frozen=True)
class AtomicGoalTemplate:
	"""Predicate-level target that an atomic lifted template must handle."""

	predicate: str
	arity: int
	polarity: str = "positive"

	def to_dict(self) -> dict[str, object]:
		return {
			"predicate": self.predicate,
			"arity": self.arity,
			"polarity": self.polarity,
		}


@dataclass(frozen=True)
class AtomicTemplateBackendDecision:
	"""Backend decision for atomic predicate/literal plan-template learning."""

	domain_name: str
	selected_backend: str | None
	selection_basis: str
	required_goal_templates: tuple[AtomicGoalTemplate, ...]
	input_goal_item_count: int
	candidate_backends: tuple[str, ...]
	rejected_backends: tuple[dict[str, str], ...]
	blocking_gap: str | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"domain_name": self.domain_name,
			"selected_backend": self.selected_backend,
			"selection_basis": self.selection_basis,
			"required_goal_templates": [
				template.to_dict() for template in self.required_goal_templates
			],
			"input_goal_item_count": self.input_goal_item_count,
			"candidate_backends": list(self.candidate_backends),
			"rejected_backends": [dict(item) for item in self.rejected_backends],
			"blocking_gap": self.blocking_gap,
		}


ATOMIC_TEMPLATE_BACKENDS: tuple[str, ...] = (
	"moose",
	"learner-policies-from-examples",
	"d2l",
	"learner-sketches",
	"h-policy-learner",
)


def select_atomic_template_backend(
	*,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path],
	backend_root: str | Path | None = None,
) -> AtomicTemplateBackendDecision:
	"""Select an external backend for atomic literal plan-template generation."""

	domain = PDDLParser.parse_domain(domain_file)
	goal_facts = _training_goal_facts(training_problem_files)
	templates = _goal_templates(goal_facts)
	if any(template.polarity == "negative" for template in templates):
		return AtomicTemplateBackendDecision(
			domain_name=domain.name,
			selected_backend=None,
			selection_basis="atomic_singleton_goal_regression",
			required_goal_templates=templates,
			input_goal_item_count=len(goal_facts),
			candidate_backends=ATOMIC_TEMPLATE_BACKENDS,
			rejected_backends=(),
			blocking_gap="negative_literal_template_not_supported",
		)

	root = Path(backend_root) if backend_root is not None else DEFAULT_BACKEND_ROOT
	rejected: list[dict[str, str]] = []
	for backend_name in ATOMIC_TEMPLATE_BACKENDS:
		rejection = _backend_rejection_reason(backend_name, root=root)
		if rejection is None:
			return AtomicTemplateBackendDecision(
				domain_name=domain.name,
				selected_backend=backend_name,
				selection_basis=_selection_basis(backend_name),
				required_goal_templates=templates,
				input_goal_item_count=len(goal_facts),
				candidate_backends=ATOMIC_TEMPLATE_BACKENDS,
				rejected_backends=tuple(rejected),
				blocking_gap=None,
			)
		rejected.append({"backend": backend_name, "reason": rejection})

	return AtomicTemplateBackendDecision(
		domain_name=domain.name,
		selected_backend=None,
		selection_basis="atomic_singleton_goal_regression",
		required_goal_templates=templates,
		input_goal_item_count=len(goal_facts),
		candidate_backends=ATOMIC_TEMPLATE_BACKENDS,
		rejected_backends=tuple(rejected),
		blocking_gap="no_atomic_template_backend_available",
	)


def _training_goal_facts(problem_files: Sequence[str | Path]) -> tuple[PDDLFact, ...]:
	facts: list[PDDLFact] = []
	for problem_file in tuple(problem_files or ()):
		problem = PDDLParser.parse_problem(problem_file)
		facts.extend(tuple(problem.goal_facts or ()))
	return tuple(facts)


def _goal_templates(goal_facts: Sequence[PDDLFact]) -> tuple[AtomicGoalTemplate, ...]:
	seen: set[tuple[str, int, str]] = set()
	templates: list[AtomicGoalTemplate] = []
	for fact in tuple(goal_facts or ()):
		key = (
			str(fact.predicate).strip(),
			len(tuple(fact.args or ())),
			"positive" if fact.is_positive else "negative",
		)
		if not key[0] or key in seen:
			continue
		seen.add(key)
		templates.append(
			AtomicGoalTemplate(
				predicate=key[0],
				arity=key[1],
				polarity=key[2],
			),
		)
	return tuple(sorted(templates, key=lambda item: (item.predicate, item.arity, item.polarity)))


def _selection_basis(backend_name: str) -> str:
	if backend_name == "moose":
		return "atomic_singleton_goal_regression"
	if backend_name == "learner-policies-from-examples":
		return "atomic_feature_policy_from_examples"
	if backend_name == "d2l":
		return "atomic_description_logic_policy"
	if backend_name == "learner-sketches":
		return "atomic_policy_sketch"
	if backend_name == "h-policy-learner":
		return "atomic_hierarchical_policy"
	return "atomic_generalized_planning_backend"


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
	if not bool(role.get("consumed_by_atomic_library")):
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
