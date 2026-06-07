"""
Structured low-level planning results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class LowLevelAction:
	"""One grounded primitive action returned by a planner."""

	name: str
	arguments: Tuple[str, ...] = ()

	def to_dict(self) -> Dict[str, Any]:
		return {
			"name": self.name,
			"arguments": list(self.arguments),
		}


@dataclass(frozen=True)
class LowLevelPlanResult:
	"""Planner result for one transition-level PDDL task."""

	success: bool
	actions: Tuple[LowLevelAction, ...] = ()
	planner: str = "fast_downward"
	generated_problem_file: str | None = None
	plan_file: str | None = None
	stdout: str = ""
	stderr: str = ""
	error: str | None = None

	def to_dict(self) -> Dict[str, Any]:
		return {
			"success": self.success,
			"planner": self.planner,
			"actions": [action.to_dict() for action in self.actions],
			"generated_problem_file": self.generated_problem_file,
			"plan_file": self.plan_file,
			"stdout": self.stdout,
			"stderr": self.stderr,
			"error": self.error,
		}
