"""Exact adapters for the finite, sequential plan language used in the audit."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import operator
from time import monotonic

from lark import Lark, UnexpectedInput

from evaluation.execution_coverage import (
	AnalysisLimit, Call, GroundBranch, Step, UnsupportedModel,
)
from plan_library.models import PlanLibrary
from temporal_input.nl_benchmark import (
	GroundAction, GroundAtom, GroundState, NumericKey, _all_object_types, _apply_action,
	_binding_satisfies, _build_catalog, _initial_state, _object_has_type,
	_parse_s_expression,
)
from utils.pddl_parser import PDDLParser


_CONTEXT = Lark(r"""
?start: "not" atom -> negative
      | atom -> positive
      | TERM OP TERM -> comparison
atom: TERM ["(" [TERM ("," TERM)*] ")"]
TERM: /[a-zA-Z_][a-zA-Z0-9_-]*/ | /-?[0-9]+/
OP: "\\==" | "!=" | "==" | ">=" | "<=" | ">" | "<"
%import common.WS
%ignore WS
""", parser="lalr", maybe_placeholders=False)


@dataclass(frozen=True)
class Guard:
	kind: str
	symbol: str
	arguments: tuple[str, ...]


@lru_cache(maxsize=16_384)
def parse_guard(text: str) -> Guard:
	try:
		tree = _CONTEXT.parse(text)
	except UnexpectedInput as exc:
		raise UnsupportedModel(f"Unsupported context: {text}") from exc
	if tree.data == "comparison":
		return Guard("comparison", str(tree.children[1]),
			(str(tree.children[0]), str(tree.children[2])))
	atom = tree.children[0]
	return Guard(str(tree.data), str(atom.children[0]),
		tuple(str(item) for item in atom.children[1:]))


def _variable(term: str) -> bool:
	return bool(term) and (term[0].isupper() or term.startswith("_"))


def _ground(term: str, binding: dict[str, str]) -> str:
	if _variable(term):
		if term not in binding:
			raise UnsupportedModel(f"Unbound variable: {term}")
		return binding[term]
	return term


def _unify(pattern: tuple[str, ...], values: tuple[str, ...],
		binding: dict[str, str]) -> dict[str, str] | None:
	if len(pattern) != len(values):
		return None
	result = dict(binding)
	for term, value in zip(pattern, values):
		if _variable(term) and term not in result:
			result[term] = value
		elif _ground(term, result) != value:
			return None
	return result


class PDDLExecutionModel:
	"""Interpret structured plans from raw contexts and domain action schemas.

	Compiler metadata and certificates are deliberately not used. Enumeration is
	complete or raises AnalysisLimit; no binding or numeric value is clipped.
	"""

	def __init__(self, domain_file: Path, problem_file: Path, library: PlanLibrary,
			*, max_seconds: float = 30.0, max_join_attempts: int = 1_000_000):
		self.catalog = _build_catalog(domain_file)
		for action in self.catalog.domain.actions:
			self._check_expression(_parse_s_expression(action.preconditions), effect=False)
			self._check_expression(_parse_s_expression(action.effects), effect=True)
		self.problem = PDDLParser.parse_problem(problem_file)
		if self.problem.domain_name != self.catalog.domain.name:
			raise UnsupportedModel("Problem and domain names differ")
		self.initial = _initial_state(self.problem)
		self.library = library
		self.objects = _all_object_types(self.catalog.domain, self.problem)
		self.actions = {schema.name: schema for schema in self.catalog.actions}
		self.plans = {}
		for plan in library.plans:
			self.plans.setdefault(plan.trigger.symbol, []).append(plan)
		self.types = tuple(sorted({"object", *self.catalog.type_parents,
			*self.catalog.type_parents.values(), *self.objects.values()}))
		self.type_rows = tuple((obj, kind) for obj in sorted(self.objects)
			for kind in self.types if self.has_type(obj, kind))
		self.reset_budget(max_seconds, max_join_attempts)

	def _check_expression(self, node: object, *, effect: bool) -> None:
		if not isinstance(node, list) or not node:
			raise UnsupportedModel(f"Malformed PDDL expression: {node}")
		head = node[0]
		if head == "and":
			for child in node[1:]:
				self._check_expression(child, effect=effect)
			return
		if head == "not" and len(node) == 2:
			child = node[1]
			if not isinstance(child, list) or child[0] not in self.catalog.predicate_types:
				raise UnsupportedModel("Only predicate negation is supported in actions")
			self._check_expression(child, effect=effect)
			return
		if head in self.catalog.predicate_types:
			if len(node) != len(self.catalog.predicate_types[head]) + 1:
				raise UnsupportedModel(f"Wrong predicate arity: {node}")
			if any(not isinstance(term, str) for term in node[1:]):
				raise UnsupportedModel(f"Nested predicate term: {node}")
			return
		allowed = {"increase", "decrease"} if effect else {"=", ">", ">=", "<", "<="}
		if head not in allowed or len(node) != 3:
			raise UnsupportedModel(f"Unsupported PDDL connective: {node}")
		for expression in node[1:]:
			if isinstance(expression, list):
				if not expression or expression[0] not in self.catalog.function_types:
					raise UnsupportedModel(f"Unsupported numeric expression: {expression}")
				if len(expression) != len(self.catalog.function_types[expression[0]]) + 1:
					raise UnsupportedModel(f"Wrong function arity: {expression}")
				if any(not isinstance(term, str) for term in expression):
					raise UnsupportedModel("Nested numeric terms are unsupported")
			else:
				try:
					int(expression)
				except (ValueError, TypeError) as exc:
					raise UnsupportedModel("Object equality or non-integer arithmetic") from exc
		if effect and (not isinstance(node[1], list) or not isinstance(node[2], str)):
			raise UnsupportedModel("Numeric effects must have constant integer deltas")

	def reset_budget(self, seconds: float, join_attempts: int = 1_000_000) -> None:
		self.deadline = monotonic() + seconds
		self.max_join_attempts = join_attempts
		self.join_attempts = 0

	def _check_budget(self) -> None:
		self.join_attempts += 1
		if self.join_attempts > self.max_join_attempts:
			raise AnalysisLimit("binding_join_limit")
		if monotonic() >= self.deadline:
			raise AnalysisLimit("binding_time_limit")

	def has_type(self, obj: str, kind: str) -> bool:
		return obj in self.objects and _object_has_type(
			self.objects[obj], kind, self.catalog.type_parents)

	def _rows(self, guard: Guard, state: GroundState) -> tuple[tuple[str, ...], ...]:
		if guard.symbol == "obj_tp":
			if len(guard.arguments) != 2:
				raise UnsupportedModel("Wrong obj_tp arity")
			return self.type_rows
		if guard.symbol in self.catalog.function_types:
			if len(guard.arguments) != len(self.catalog.function_types[guard.symbol]) + 1:
				raise UnsupportedModel(f"Wrong numeric belief arity: {guard.symbol}")
			return tuple(key.arguments + (str(value),) for key, value in state.numeric_values
				if key.function == guard.symbol)
		types = self.catalog.predicate_types.get(guard.symbol)
		if types is None or len(types) != len(guard.arguments):
			raise UnsupportedModel(f"Unknown predicate or wrong arity: {guard.symbol}")
		return tuple(atom.arguments for atom in sorted(state.facts)
			if atom.predicate == guard.symbol)

	def branches(self, goal: Call, state: GroundState) -> tuple[GroundBranch, ...]:
		result = []
		for plan in self.plans.get(goal.symbol, ()):
			binding = _unify(plan.trigger.arguments, goal.arguments, {})
			if binding is None:
				continue
			guards = tuple(parse_guard(item) for item in plan.context if item != "true")
			positives = sorted((guard for guard in guards if guard.kind == "positive"),
				key=lambda guard: len(self._rows(guard, state)))
			bindings = [binding]
			for guard in positives:
				joined = []
				for current in bindings:
					for row in self._rows(guard, state):
						self._check_budget()
						match = _unify(guard.arguments, row, current)
						if match is not None:
							joined.append(match)
				bindings = joined
			for current in bindings:
				self._check_budget()
				if any(tuple(_ground(term, current) for term in guard.arguments)
						in self._rows(guard, state) for guard in guards
						if guard.kind == "negative"):
					continue
				if not all(_compare(guard, current) for guard in guards
						if guard.kind == "comparison"):
					continue
				body = tuple(Step(step.kind, Call(step.symbol,
					tuple(_ground(term, current) for term in step.arguments)))
					for step in plan.body)
				result.append(GroundBranch(plan.plan_name, goal, body,
					tuple(sorted(current.items()))))
		return tuple(dict.fromkeys(result))

	def applicable(self, branch: GroundBranch, state: GroundState) -> bool:
		"""Check a supplied binding without enumerating unrelated alternatives."""
		binding = dict(branch.binding)
		for plan in self.plans.get(branch.goal.symbol, ()):
			if plan.plan_name != branch.name:
				continue
			if tuple(_ground(term, binding) for term in plan.trigger.arguments) != (
					branch.goal.arguments):
				continue
			guards = [parse_guard(text) for text in plan.context if text != "true"]
			valid = True
			for guard in guards:
				if guard.kind == "comparison":
					valid = valid and _compare(guard, binding)
				else:
					present = tuple(_ground(term, binding) for term in guard.arguments) in (
						self._rows(guard, state))
					valid = valid and (present == (guard.kind == "positive"))
			body = tuple(Step(step.kind, Call(step.symbol,
				tuple(_ground(term, binding) for term in step.arguments))) for step in plan.body)
			if valid and body == branch.body:
				return True
		return False

	def execute(self, action: Call, state: GroundState) -> GroundState | None:
		schema = self.actions.get(action.symbol)
		if schema is None or len(schema.parameters) != len(action.arguments):
			raise UnsupportedModel(f"Unknown action or wrong arity: {action}")
		binding = dict(zip(schema.parameters, action.arguments))
		if not all(self.has_type(value, schema.parameter_types[name])
				for name, value in binding.items()):
			return None
		reads = [expr for condition in schema.numeric_preconditions
			for expr in (condition.left, condition.right) if expr.kind == "fluent"]
		keys = [NumericKey(expr.value, tuple(binding.get(x, x) for x in expr.args))
			for expr in reads]
		keys.extend(NumericKey(effect.fluent.function,
			tuple(binding.get(x, x) for x in effect.fluent.args))
			for effect in schema.numeric_effects)
		if any(key not in state.numeric for key in keys):
			raise UnsupportedModel("An action reads or updates an undefined numeric fluent")
		if not _binding_satisfies(schema, binding, state):
			return None
		return _apply_action(self.catalog, state,
			GroundAction(action.symbol, action.arguments, tuple(binding.items())))

	def satisfied(self, goal: Call, state: GroundState) -> bool:
		if goal.symbol in self.catalog.function_types:
			if len(goal.arguments) != len(self.catalog.function_types[goal.symbol]) + 1:
				raise UnsupportedModel(f"Wrong numeric target arity: {goal}")
			key = NumericKey(goal.symbol, goal.arguments[:-1])
			if key not in state.numeric:
				raise UnsupportedModel(f"Undefined numeric target: {key}")
			try:
				return state.numeric[key] == int(goal.arguments[-1])
			except ValueError as exc:
				raise UnsupportedModel("Non-integer target") from exc
		if goal.symbol not in self.catalog.predicate_types:
			raise UnsupportedModel(f"No return contract for goal: {goal.symbol}")
		return GroundAtom(goal.symbol, goal.arguments) in state.facts


def _compare(guard: Guard, binding: dict[str, str]) -> bool:
	left, right = (_ground(term, binding) for term in guard.arguments)
	if guard.symbol == "==":
		return left == right
	if guard.symbol in ("!=", "\\=="):
		return left != right
	operations = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le}
	try:
		return operations[guard.symbol](int(left), int(right))
	except (ValueError, KeyError) as exc:
		raise UnsupportedModel(f"Non-integer comparison: {guard}") from exc
