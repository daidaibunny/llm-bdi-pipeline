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
from .models import LowLevelPlanResult


@dataclass(frozen=True)
class TransitionPlanningRequest:
	"""Input for one transition-level low-level planning attempt."""

	plan_name: str
	domain_file: str
	problem_file: str
	target_context: Tuple[str, ...]
	cumulative_context: Tuple[str, ...]
	work_dir: str


@dataclass(frozen=True)
class TransitionPlanningResult:
	"""ASL body fragment and certificate for one transition-level plan."""

	body_steps: Tuple[AgentSpeakBodyStep, ...]
	certificate: Dict[str, Any]
	warnings: Tuple[str, ...] = ()


class FastDownwardTransitionPlanner:
	"""Use Fast Downward to support transition-level ASL subgoals."""

	def __init__(
		self,
		*,
		config: FastDownwardPlannerConfig | None = None,
		render_primitive_actions: bool = False,
	) -> None:
		self._planner = FastDownwardPlanner(config)
		self._render_primitive_actions = render_primitive_actions

	def plan_transition(self, request: TransitionPlanningRequest) -> TransitionPlanningResult:
		"""Return low-level body steps and a Fast Downward certificate."""

		task_name = sanitize_identifier(request.plan_name)
		result = self._planner.solve_transition_goal(
			domain_file=request.domain_file,
			base_problem_file=request.problem_file,
			goal_literals=request.cumulative_context or request.target_context,
			work_dir=Path(request.work_dir),
			task_name=task_name,
		)
		if self._render_primitive_actions and result.success:
			body_steps = tuple(
				AgentSpeakBodyStep("action", action.name, action.arguments)
				for action in result.actions
			)
		else:
			body_steps = (
				AgentSpeakBodyStep("subgoal", f"achieve_{task_name}"),
			)
		warnings = (result.error,) if result.error else ()
		return TransitionPlanningResult(
			body_steps=body_steps,
			certificate={
				"low_level_planner": "fast_downward",
				"target_context": list(request.target_context),
				"cumulative_context": list(request.cumulative_context),
				"result": result.to_dict(),
			},
			warnings=tuple(warning for warning in warnings if warning),
		)
