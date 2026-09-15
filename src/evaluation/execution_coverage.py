"""Independent existential plan analysis; no compiler certificates are trusted."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import monotonic
from typing import Hashable, Protocol


@dataclass(frozen=True, order=True)
class Call:
	"""A ground action or goal; numeric argument values use decimal strings."""

	symbol: str
	arguments: tuple[str, ...] = ()


@dataclass(frozen=True)
class Step:
	kind: str
	call: Call


@dataclass(frozen=True)
class GroundBranch:
	"""One fully bound plan instance whose context holds at the call state."""

	name: str
	goal: Call
	body: tuple[Step, ...]
	binding: tuple[tuple[str, str], ...] = ()


class ExecutionModel(Protocol):
	"""Adapters must enumerate ALL applicable bindings, or raise an error."""

	def branches(self, goal: Call, state: Hashable) -> tuple[GroundBranch, ...]: ...
	def execute(self, action: Call, state: Hashable) -> Hashable | None: ...
	def satisfied(self, goal: Call, state: Hashable) -> bool: ...


class AnalysisLimit(RuntimeError):
	"""A resource bound prevented exhaustive exploration."""


class UnsupportedModel(ValueError):
	"""The adapter cannot give exact semantics for this input."""


@dataclass(frozen=True)
class Proof:
	branch: GroundBranch
	start: Hashable
	end: Hashable
	children: tuple[Call | Proof, ...]


@dataclass
class AnalysisResult:
	coverage: dict[str, int]
	correctness: dict[str, int]
	root_proofs: tuple[Proof | None, ...]
	root_statuses: tuple[str, ...]
	obligations: tuple[tuple[GroundBranch, Hashable, str], ...]
	complete: bool
	reason: str | None = None
	request_count: int = 0
	return_count: int = 0
	configuration_count: int = 0
	root_enumeration_complete: bool = True
	obligation_proofs: tuple[Proof | None, ...] = ()
	saturated: bool = False

	def action_trace(self, root_index: int) -> tuple[Call, ...]:
		"""Flatten a finite derivation without using the Python recursion stack."""
		proof = self.root_proofs[root_index]
		if proof is None:
			raise ValueError("This request has no certified successful derivation")
		pending: list[Call | Proof] = [proof]
		actions: list[Call] = []
		while pending:
			node = pending.pop()
			if isinstance(node, Call):
				actions.append(node)
			else:
				pending.extend(reversed(node.children))
		return tuple(actions)


def _counts(statuses: list[str] | tuple[str, ...]) -> dict[str, int]:
	return {**{key: statuses.count(key) for key in ("pass", "fail", "unknown")},
		"total": len(statuses)}


def validate_proof(model: ExecutionModel, proof: Proof, *,
		materialize_trace: bool = True, max_actions: int = 100_000) -> tuple[Call, ...] | None:
	"""Replay a derivation independently of the saturation worklist."""
	pending = [(proof, False)]
	checked: set[int] = set()
	active: set[int] = set()
	while pending:
		node, ready = pending.pop()
		if id(node) in checked:
			continue
		if not ready:
			if id(node) in active:
				raise ValueError("Circular proof")
			active.add(id(node))
			pending.append((node, True))
			pending.extend((child, False) for child in reversed(node.children)
				if isinstance(child, Proof))
			continue
		applicable = getattr(model, "applicable", None)
		valid = (applicable(node.branch, node.start) if applicable else
			node.branch in model.branches(node.branch.goal, node.start))
		if not valid:
			raise ValueError("Proof uses an inapplicable plan")
		if len(node.children) != len(node.branch.body):
			raise ValueError("Proof omits a body step")
		state = node.start
		for step, child in zip(node.branch.body, node.children):
			if step.kind == "action" and isinstance(child, Call) and step.call == child:
				state = model.execute(child, state)
				if state is None:
					raise ValueError("Proof includes an inapplicable action")
			elif step.kind == "subgoal" and isinstance(child, Proof):
				if child.branch.goal != step.call or child.start != state:
					raise ValueError("Proof has an inconsistent subgoal call")
				state = child.end
			else:
				raise ValueError("Proof substitutes a different body step")
		if state != node.end or not model.satisfied(node.branch.goal, state):
			raise ValueError("Proof has an invalid return state")
		checked.add(id(node))
		active.remove(id(node))
	if not materialize_trace:
		return None
	pending_trace: list[Call | Proof] = [proof]
	actions = []
	while pending_trace:
		node = pending_trace.pop()
		if isinstance(node, Call):
			if len(actions) >= max_actions:
				raise AnalysisLimit("trace_materialization_limit")
			actions.append(node)
		else:
			pending_trace.extend(reversed(node.children))
	return tuple(actions)


def analyze_library(
	model: ExecutionModel,
	requests: tuple[tuple[Call, Hashable], ...],
	*,
	max_configurations: int = 100_000,
	max_seconds: float | None = 30.0,
) -> AnalysisResult:
	"""Saturate finite call-return summaries, without assuming recursive success.

	Only complete saturation proves a negative. A bound leaves every unresolved
	obligation unknown, while finite positive derivations remain valid witnesses.
	"""
	if max_configurations < 1 or (max_seconds is not None and max_seconds <= 0):
		raise ValueError("Analysis budgets must be positive")
	deadline = monotonic() + max_seconds if max_seconds is not None else float("inf")
	type Request = tuple[Call, Hashable]
	type Configuration = tuple[Request, GroundBranch, int, Hashable]
	branches: dict[Request, tuple[GroundBranch, ...]] = {}
	returns: dict[Request, dict[Hashable, Proof]] = {}
	branch_proofs: dict[tuple[Request, GroundBranch], Proof] = {}
	prefixes: dict[Configuration, tuple[Call | Proof, ...]] = {}
	waiters: dict[Request, dict[Configuration, None]] = {}
	queue: deque[Configuration] = deque()

	def schedule(config: Configuration, children: tuple[Call | Proof, ...]) -> None:
		if config not in prefixes:
			if len(prefixes) >= max_configurations:
				raise AnalysisLimit("configuration_limit")
			prefixes[config] = children
			queue.append(config)

	def discover(request: Request) -> None:
		if request in branches:
			return
		goal, start = request
		branches[request] = model.branches(goal, start)
		returns[request] = {}
		waiters[request] = {}
		for branch in branches[request]:
			schedule((request, branch, 0, start), ())

	reason = None
	try:
		for request in requests:
			discover(request)
		while queue:
			if all(returns[request] and all((request, branch) in branch_proofs
					for branch in branches[request]) for request in requests):
				break
			if monotonic() >= deadline:
				raise AnalysisLimit("time_limit")
			config = queue.popleft()
			request, branch, index, state = config
			children = prefixes[config]
			if index == len(branch.body):
				if not model.satisfied(request[0], state):
					continue
				proof = Proof(branch, request[1], state, children)
				branch_proofs.setdefault((request, branch), proof)
				if state not in returns[request]:
					returns[request][state] = proof
					for waiting in waiters[request]:
						parent, parent_branch, position, _ = waiting
						schedule((parent, parent_branch, position + 1, state),
							prefixes[waiting] + (proof,))
				continue
			step = branch.body[index]
			if step.kind == "action":
				end = model.execute(step.call, state)
				if end is not None:
					schedule((request, branch, index + 1, end), children + (step.call,))
			elif step.kind == "subgoal":
				callee = (step.call, state)
				discover(callee)
				waiters[callee][config] = None
				for end, proof in returns[callee].items():
					schedule((request, branch, index + 1, end), children + (proof,))
			else:
				raise UnsupportedModel(f"Unsupported body step: {step.kind}")
	except (AnalysisLimit, UnsupportedModel) as exc:
		reason = str(exc)
	unresolved = "unknown" if reason else "fail"
	proofs = [next(iter(returns.get(request, {}).values()), None) for request in requests]
	statuses = ["pass" if proof else unresolved for proof in proofs]
	obligations = [
		(branch, request[1], "pass" if (request, branch) in branch_proofs else unresolved)
		for request in dict.fromkeys(requests) for branch in branches.get(request, ())
	]
	unique_statuses = list(dict(zip(requests, statuses)).values())
	return AnalysisResult(
		_counts(unique_statuses), _counts([row[2] for row in obligations]),
		tuple(proofs), tuple(statuses), tuple(obligations), reason is None, reason,
		request_count=len(returns), return_count=sum(map(len, returns.values())),
		configuration_count=len(prefixes),
		root_enumeration_complete=all(request in branches for request in requests),
		obligation_proofs=tuple(
			branch_proofs.get((request, branch))
			for request in dict.fromkeys(requests) for branch in branches.get(request, ())
		),
		saturated=not queue and reason is None,
	)
