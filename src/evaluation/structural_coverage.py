"""Exact Boolean context counts, kept distinct from stateful execution coverage."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from graphlib import CycleError, TopologicalSorter
from typing import Literal, Mapping

from dd.autoref import BDD

from evaluation.coverage_model import PDDLExecutionModel, _compare, _ground, parse_guard
from evaluation.execution_coverage import UnsupportedModel


@dataclass(frozen=True)
class BooleanContext:
	"""One fully ground conjunction over unconstrained Boolean world atoms."""

	positive: frozenset[str] = frozenset()
	negative: frozenset[str] = frozenset()
	eligible: bool = True


def ground_boolean_context(context: tuple[str, ...], binding: dict[str, str],
		model: PDDLExecutionModel) -> BooleanContext:
	"""Project a supplied full binding, not the truth values of its test state.

	Type membership is fixed metadata; PDDL predicates remain Boolean variables,
	including predicates static in the transition model. Integer-valued functions
	are not independent Boolean propositions and require a separate state measure.
	"""
	if model.catalog.function_types:
		raise UndefinedCoverage("Numeric world-state measure requires an explicit specification")
	positive, negative = set(), set()
	eligible = True
	for text in context:
		if text == "true":
			continue
		guard = parse_guard(text)
		args = tuple(_ground(term, binding) for term in guard.arguments)
		if guard.kind == "comparison":
			eligible = eligible and _compare(guard, binding)
		elif guard.symbol == "obj_tp":
			if len(args) != 2:
				raise UnsupportedModel("Wrong obj_tp arity")
			eligible = eligible and (model.has_type(*args) == (guard.kind == "positive"))
		elif guard.symbol in model.catalog.function_types:
			raise UndefinedCoverage("Numeric world-state measure is not defined by Boolean counting")
		else:
			types = model.catalog.predicate_types.get(guard.symbol)
			if types is None or len(args) != len(types):
				raise UnsupportedModel(f"Unknown Boolean atom: {text}")
			if not all(model.has_type(obj, kind) for obj, kind in zip(args, types)):
				raise UnsupportedModel(f"Ill-typed ground atom: {text}")
			atom = f"{guard.symbol}({','.join(args)})"
			(positive if guard.kind == "positive" else negative).add(atom)
	return BooleanContext(frozenset(positive), frozenset(negative), eligible)


@dataclass(frozen=True)
class ContextCounts:
	basic: tuple[Fraction, ...]
	union: Fraction
	overlap: Fraction

	@property
	def raw_sum(self) -> Fraction:
		return sum(self.basic, Fraction())


def count_contexts(contexts: tuple[BooleanContext, ...], *,
		max_bdd_nodes: int = 100_000) -> ContextCounts:
	"""Count under the uniform Boolean state space, without enumerating worlds.

	Atoms absent from every context cancel from numerator and denominator.
	``overlap`` is the measure of states satisfying at least two contexts,
	not the sum of pairwise overlaps, which would overcount triple intersections.
	"""
	if max_bdd_nodes < 1:
		raise ValueError("BDD budget must be positive")
	atoms = sorted({atom for c in contexts for atom in c.positive | c.negative})
	variables = {atom: f"v{index}" for index, atom in enumerate(atoms)}
	bdd = BDD()
	if variables:
		bdd.declare(*variables.values())
	denominator = 1 << len(atoms)
	seen, overlap = bdd.false, bdd.false
	basic = []
	for context in contexts:
		node = bdd.true if context.eligible else bdd.false
		for atom in sorted(context.positive):
			node &= bdd.var(variables[atom])
		for atom in sorted(context.negative):
			node &= ~bdd.var(variables[atom])
		basic.append(Fraction(bdd.count(node, nvars=len(atoms)), denominator))
		overlap |= seen & node
		seen |= node
		if len(bdd) > max_bdd_nodes:
			raise OverflowError("BDD node budget exhausted; exact count unavailable")
	return ContextCounts(tuple(basic),
		Fraction(bdd.count(seen, nvars=len(atoms)), denominator),
		Fraction(bdd.count(overlap, nvars=len(atoms)), denominator))


@dataclass(frozen=True)
class StructuralPlan:
	"""A fully ground plan; primitive actions have no structural child score."""

	context: BooleanContext
	subgoals: tuple[str, ...] = ()


class UndefinedCoverage(ValueError):
	"""The supplied equations do not specify a unique admissible metric."""


def extended_coverage(graph: Mapping[str, tuple[StructuralPlan, ...]], root: str,
		*, overlap: Literal["literal_sum", "partition_max"]) -> Fraction:
	"""Evaluate finite acyclic structural equations with an explicit overlap rule.

	The literal sum is the uploaded manuscript's equation, with no clamping at one.
	Partition-max is a distinct, explicitly requested correction. Neither is
	a stateful execution probability or a proof of plan correctness.
	"""
	if overlap not in ("literal_sum", "partition_max"):
		raise ValueError("An explicit supported overlap rule is required")
	dependencies = {}
	pending = [root]
	while pending:
		goal = pending.pop()
		if goal in dependencies:
			continue
		children = {child for plan in graph.get(goal, ()) for child in plan.subgoals}
		dependencies[goal] = children
		pending.extend(children)
	try:
		order = tuple(TopologicalSorter(dependencies).static_order())
	except CycleError as exc:
		raise UndefinedCoverage("Recursive coverage requires a fixed-point convention") from exc
	values = {}
	for goal in order:
		plans = graph.get(goal, ())
		weights = []
		for plan in plans:
			weight = Fraction(1)
			for subgoal in plan.subgoals:
				weight *= values[subgoal]
			weights.append(weight)
		if overlap == "literal_sum":
			basics = count_contexts(tuple(plan.context for plan in plans)).basic
			values[goal] = sum((basic * weight for basic, weight in zip(basics, weights)),
				Fraction())
		else:
			seen: list[BooleanContext] = []
			previous, value = Fraction(), Fraction()
			for weight in sorted(set(weights), reverse=True):
				seen.extend(plan.context for plan, w in zip(plans, weights) if w == weight)
				covered = count_contexts(tuple(seen)).union
				value += weight * (covered - previous)
				previous = covered
			values[goal] = value
	return values[root]
