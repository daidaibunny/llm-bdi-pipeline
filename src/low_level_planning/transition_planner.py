"""
Build low-level planning certificates for DFA progress transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

from plan_library.models import AgentSpeakBodyStep
from plan_library.rendering import sanitize_identifier

from .fast_downward import FastDownwardPlanner, FastDownwardPlannerConfig
from .strips_state import STRIPSStateSimulator, signatures_to_facts


@dataclass(frozen=True)
class TransitionPlanningRequest:
	"""Input for one transition-level low-level planning attempt."""

	plan_name: str
	domain_file: str
	problem_file: str
	target_context: Tuple[str, ...]
	source_context: Tuple[str, ...]
	cumulative_context: Tuple[str, ...]
	work_dir: str


@dataclass(frozen=True)
class TransitionPlanningResult:
	"""ASL body fragment and certificate for one transition-level plan."""

	body_steps: Tuple[AgentSpeakBodyStep, ...]
	certificate: Dict[str, Any]
	post_state: Tuple[str, ...] = ()
	warnings: Tuple[str, ...] = ()


class FastDownwardTransitionPlanner:
	"""Use Fast Downward to support transition-level ASL subgoals."""

	def __init__(
		self,
		*,
		config: FastDownwardPlannerConfig | None = None,
		render_primitive_actions: bool = True,
	) -> None:
		self._planner = FastDownwardPlanner(config)
		self._render_primitive_actions = render_primitive_actions
		self._simulators: dict[str, STRIPSStateSimulator] = {}
		self._states_by_context: dict[tuple[str, str, Tuple[str, ...]], frozenset[str]] = {}

	def plan_transition(self, request: TransitionPlanningRequest) -> TransitionPlanningResult:
		"""Return low-level body steps and a Fast Downward certificate."""

		task_name = sanitize_identifier(request.plan_name)
		simulator = self._simulator_for(request.domain_file)
		source_context_key = tuple(request.source_context)
		state_key = (request.domain_file, request.problem_file, source_context_key)
		if state_key not in self._states_by_context:
			if source_context_key:
				return TransitionPlanningResult(
					body_steps=(),
					certificate={
						"low_level_planner": "fast_downward",
						"target_context": list(request.target_context),
						"source_context": list(request.source_context),
						"cumulative_context": list(request.cumulative_context),
						"error": "Missing canonical source state for transition context.",
					},
					warnings=("Missing canonical source state for transition context.",),
				)
			self._states_by_context[state_key] = simulator.initial_state_from_problem(
				request.problem_file,
			)
		source_state = self._states_by_context[state_key]
		result = self._planner.solve_transition_goal(
			domain_file=request.domain_file,
			base_problem_file=request.problem_file,
			goal_literals=request.target_context,
			work_dir=Path(request.work_dir),
			task_name=task_name,
			initial_facts=signatures_to_facts(source_state),
		)
		post_state: frozenset[str] = source_state
		if result.success:
			try:
				post_state = simulator.apply_plan(state=source_state, actions=result.actions)
			except ValueError as exc:
				return TransitionPlanningResult(
					body_steps=(),
					certificate={
						"low_level_planner": "fast_downward",
						"target_context": list(request.target_context),
						"source_context": list(request.source_context),
						"cumulative_context": list(request.cumulative_context),
						"result": result.to_dict(),
						"error": str(exc),
					},
					warnings=(str(exc),),
				)
			self._states_by_context[
				(request.domain_file, request.problem_file, tuple(request.cumulative_context))
			] = post_state
		if self._render_primitive_actions and result.success:
			body_steps = tuple(
				AgentSpeakBodyStep("action", action.name, action.arguments)
				for action in result.actions
			)
		else:
			body_steps = ()
		warnings = (result.error,) if result.error else ()
		return TransitionPlanningResult(
			body_steps=body_steps,
			certificate={
				"low_level_planner": "fast_downward",
				"target_context": list(request.target_context),
				"source_context": list(request.source_context),
				"cumulative_context": list(request.cumulative_context),
				"result": result.to_dict(),
			},
			post_state=tuple(sorted(post_state)),
			warnings=tuple(warning for warning in warnings if warning),
		)

	def _simulator_for(self, domain_file: str) -> STRIPSStateSimulator:
		if domain_file not in self._simulators:
			self._simulators[domain_file] = STRIPSStateSimulator(domain_file)
		return self._simulators[domain_file]
