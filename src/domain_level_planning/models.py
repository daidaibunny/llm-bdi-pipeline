"""
Lifted modular-sketch models used before AgentSpeak(L) compilation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class LiftedCall:
	"""A lifted primitive action or achievement-goal call."""

	kind: str
	symbol: str
	arguments: Tuple[str, ...] = ()


@dataclass(frozen=True)
class LiftedPlanRule:
	"""A goal-conditioned modular sketch rule before ASL compilation."""

	name: str
	head: LiftedCall
	context: Tuple[str, ...]
	body: Tuple[LiftedCall, ...] = ()
	layer: str = "atomic"
	rationale: str = ""
	capabilities: Tuple[str, ...] = ()
	cost: int = 1


@dataclass(frozen=True)
class SketchSynthesisReport:
	"""Summary of the bounded-class synthesis contract for one library."""

	theoretical_contract: str
	solver_family: str
	runtime_full_trace_planner: bool
	uses_read_only_goal_facts: bool
	supported_domain_class: str
	learned_layers: Tuple[str, ...]
	optimizer: str
	selected_rule_count: int
	candidate_rule_count: int

	def to_dict(self) -> dict[str, Any]:
		return {
			"theoretical_contract": self.theoretical_contract,
			"solver_family": self.solver_family,
			"runtime_full_trace_planner": self.runtime_full_trace_planner,
			"uses_read_only_goal_facts": self.uses_read_only_goal_facts,
			"supported_domain_class": self.supported_domain_class,
			"learned_layers": list(self.learned_layers),
			"optimizer": self.optimizer,
			"selected_rule_count": self.selected_rule_count,
			"candidate_rule_count": self.candidate_rule_count,
		}
