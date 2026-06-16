"""
Machine-readable architecture contract for domain-level library synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ArchitectureDecision:
	"""A stable design decision that constrains synthesis claims."""

	id: str
	decision: str
	status: str
	rationale: str

	def to_dict(self) -> dict[str, str]:
		return {
			"id": self.id,
			"decision": self.decision,
			"status": self.status,
			"rationale": self.rationale,
		}


@dataclass(frozen=True)
class ArchitectureGap:
	"""A known gap between current implementation and the paper-quality target."""

	id: str
	layer: str
	gap: str
	current_state: str
	required_improvement: str
	status: str

	def to_dict(self) -> dict[str, str]:
		return {
			"id": self.id,
			"layer": self.layer,
			"gap": self.gap,
			"current_state": self.current_state,
			"required_improvement": self.required_improvement,
			"status": self.status,
		}


@dataclass(frozen=True)
class ArchitectureContract:
	"""The bounded-class synthesis contract reported with each library."""

	guarantee: str
	non_goals: tuple[str, ...]
	supported_pddl_fragment: str
	runtime_planner_policy: str
	layer_b_target: str
	layer_c_target: str
	goal_fact_semantics: str
	decisions: tuple[ArchitectureDecision, ...]
	gaps: tuple[ArchitectureGap, ...]

	def to_dict(self) -> dict[str, Any]:
		return {
			"guarantee": self.guarantee,
			"non_goals": list(self.non_goals),
			"supported_pddl_fragment": self.supported_pddl_fragment,
			"runtime_planner_policy": self.runtime_planner_policy,
			"layer_b_target": self.layer_b_target,
			"layer_c_target": self.layer_c_target,
			"goal_fact_semantics": self.goal_fact_semantics,
			"decisions": [decision.to_dict() for decision in self.decisions],
			"gaps": [gap.to_dict() for gap in self.gaps],
		}


def domain_level_architecture_contract() -> ArchitectureContract:
	"""Return the current research contract for lifted ASL synthesis."""

	return ArchitectureContract(
		guarantee=(
			"bounded-class guarantee: synthesize and validate the best library found "
			"inside the current goal-conditioned modular sketch hypothesis class; "
			"do not claim universal PDDL generalized-planning completeness"
		),
		non_goals=(
			"universal completeness for arbitrary PDDL domains",
			"runtime full-trace planning for each new problem",
			"query-specific or problem-specific ASL libraries as the main artifact",
			"synthetic achievement names such as achieve_*, transition_*, or dfa_state",
			"guessing vocabulary equivalence for external learner artifacts",
		),
		supported_pddl_fragment=(
			"classical STRIPS-style achievement goals over the project-supported "
			"PDDL subset; unsupported requirements must fail before compilation"
		),
		runtime_planner_policy=(
			"classical planners may provide synthesis evidence, traces, "
			"counterexamples, and validation, but not final runtime full traces"
		),
		layer_b_target=(
			"learn lifted atomic predicate-goal modules whose heads are PDDL "
			"achievement goals and whose bodies contain PDDL primitive actions or "
			"other PDDL predicate subgoals"
		),
		layer_c_target=(
			"learn lifted goal-conditioned composer rules that choose which atomic "
			"goal module to call next for conjunctive goals with dependencies"
		),
		goal_fact_semantics=(
			"goal_<predicate> atoms are read-only goal descriptors derived from "
			"PDDL goals or future DFA requests; they are not primitive actions, "
			"mutable beliefs, or synthetic achievement goals"
		),
		decisions=(
			ArchitectureDecision(
				id="D1",
				decision="Use bounded-class guarantee instead of universal PDDL completeness.",
				status="accepted",
				rationale="Arbitrary-domain generalized planning is too strong a claim.",
			),
			ArchitectureDecision(
				id="D2",
				decision="Use goal-conditioned modular policy sketches as the main method family.",
				status="accepted",
				rationale="They align subgoal decomposition with reusable ASL modules.",
			),
			ArchitectureDecision(
				id="D3",
				decision="Keep read-only goal_<predicate> descriptors.",
				status="accepted",
				rationale="A domain-level library needs the current problem goal as input.",
			),
			ArchitectureDecision(
				id="D4",
				decision="Use planners only for synthesis evidence and validation.",
				status="accepted",
				rationale="Runtime full-trace planning would erase the plan-library contribution.",
			),
			ArchitectureDecision(
				id="D5",
				decision="Keep DFA as the future TEG controller above the AG library.",
				status="accepted",
				rationale="Temporal goals are query-specific; the achievement library is domain-level.",
			),
			ArchitectureDecision(
				id="D6",
				decision="Do not silently support negative or disjunctive goals.",
				status="open",
				rationale="Current Layer B/C semantics are positive conjunctive achievement-goal based.",
			),
		),
		gaps=(
			ArchitectureGap(
				id="G1",
				layer="theory",
				gap="The bounded-class contract needs a formal paper definition.",
				current_state="Reports expose the contract as implementation metadata.",
				required_improvement="Define feature, module, composer, progress, and correctness languages.",
				status="in_progress",
			),
			ArchitectureGap(
				id="G2",
				layer="Layer B",
				gap="Atomic module learning still lacks a full multi-strategy module learner.",
				current_state=(
					"Schema, sketch, bounded progress candidates, trace slicing, "
					"last achievers, anti-unified support patterns, and recursion "
					"descent audits are reported."
				),
				required_improvement=(
					"Add a multi-strategy module learner that generalizes from these "
					"evidence sources and rejects unsafe alternatives."
				),
				status="partially_done",
			),
			ArchitectureGap(
				id="G3",
				layer="Layer C",
				gap="Goal dependency composition remains the main research gap.",
				current_state=(
					"Shared-object trace order evidence, schema causal-interference "
					"ordering candidates, bounded state-coverage constraints, and "
					"counterexample failure classification exist."
				),
				required_improvement=(
					"Learn richer final-goal causal structures and broader "
					"counterexample failure types as reusable composer rules."
				),
				status="partially_done",
			),
			ArchitectureGap(
				id="G4",
				layer="goal representation",
				gap="Goal-fact semantics need stronger validation and documentation.",
				current_state="goal_<predicate> facts are used as read-only descriptors.",
				required_improvement="Prove they are not emitted as mutable beliefs or primitive actions.",
				status="partially_done",
			),
			ArchitectureGap(
				id="G5",
				layer="feature binding",
				gap="DLPlan feature binding is intentionally conservative.",
				current_state="Recoverable lifted patterns bind; object-specific patterns are rejected.",
				required_improvement="Expand only principled lifted bindings and report every rejection.",
				status="partially_done",
			),
			ArchitectureGap(
				id="G6",
				layer="validation",
				gap="Bounded validation is not yet a full experiment protocol.",
				current_state="Training and counterexample problems receive bounded first-applicable validation.",
				required_improvement="Add train/test splits, held-out scaling, ablations, baselines, and failure analysis.",
				status="open",
			),
			ArchitectureGap(
				id="G7",
				layer="TEG",
				gap="DFA guard requests are not yet connected to the domain-level library.",
				current_state=(
					"Positive conjunctive DFA guards can be translated into "
					"goal facts and PDDL predicate subgoal calls; the supported "
					"ASL subset and execution semantics are reported with each "
					"domain-level contract."
				),
				required_improvement=(
					"Integrate the adapter into the runtime DFA controller and "
					"define unsupported negative/disjunctive guard semantics."
				),
				status="partially_done",
			),
		),
	)


def architecture_gap_summary(gaps: Iterable[ArchitectureGap]) -> dict[str, int]:
	"""Count architecture gaps by status for reports and tests."""

	counts: dict[str, int] = {}
	for gap in gaps:
		counts[gap.status] = counts.get(gap.status, 0) + 1
	return counts
