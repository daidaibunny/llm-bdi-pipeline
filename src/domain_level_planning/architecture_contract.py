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
class HypothesisClassContract:
	"""Machine-readable bounded hypothesis class for paper claims."""

	name: str
	feature_language: dict[str, object]
	module_language: dict[str, object]
	composer_language: dict[str, object]
	progress_language: dict[str, object]
	correctness_language: dict[str, object]
	exclusions: tuple[str, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"name": self.name,
			"feature_language": dict(self.feature_language),
			"module_language": dict(self.module_language),
			"composer_language": dict(self.composer_language),
			"progress_language": dict(self.progress_language),
			"correctness_language": dict(self.correctness_language),
			"exclusions": list(self.exclusions),
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
	hypothesis_class: HypothesisClassContract
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
			"hypothesis_class": self.hypothesis_class.to_dict(),
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
			"learn lifted atomic predicate-goal modules whose heads are declared "
			"PDDL achievement predicates and whose bodies contain declared PDDL "
			"primitive actions or declared PDDL predicate subgoals with matching "
			"schema arities"
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
		hypothesis_class=bounded_hypothesis_class_contract(),
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
			ArchitectureDecision(
				id="D7",
				decision="Reject object-specific DLPlan features unless principled lifting exists.",
				status="accepted",
				rationale=(
					"Guessing bindings for object-specific features would break the "
					"domain-level lifted-library claim."
				),
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
					"descent audits are reported; repair diagnostics from "
					"counterexample precondition failures are included in the "
					"Layer B evidence matrix; selected and output rules are reported "
					"with lifted provenance manifests."
				),
				required_improvement=(
					"Add a multi-strategy module learner that generalizes from these "
					"evidence sources, including repair diagnostics, and rejects "
					"unsafe alternatives."
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
					"counterexample failure classification exist; primitive-precondition "
					"repair evidence is lifted into Layer B constraints and consumed "
					"as selector hard groups when matching prepare rules exist. "
					"Atomic-progress refinement constraints are consumed as selector "
					"hard groups when matching atomic action rules exist. "
					"Goal-bound primitive-precondition failures can synthesize new "
					"safe Layer B prepare candidates when read-only goal facts bind "
					"all extra variables; undeclared or wrong-arity repair failing "
					"actions are rejected before binding. Explicit counterexample goal-ordering "
					"constraints synthesize Layer C composer candidates and selector "
					"hard groups, with rejected binding diagnostics when the lifted "
					"ordering or repair evidence is not executable or references "
					"undeclared predicates or wrong predicate arities; wrong-arity "
					"atomic-progress diagnostics identify the offending predicates. "
					"Negative precondition repairs are rejected explicitly instead "
					"of being misread as positive achievement modules. Selected and "
					"output composer rules are reported with lifted provenance manifests."
				),
				required_improvement=(
					"Learn richer final-goal causal structures and make failure "
					"classifications generate new composer/module candidates beyond "
					"the current explicit goal-ordering and goal-bound primitive-"
					"precondition repair subsets."
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
				current_state=(
					"Recoverable lifted patterns bind; object-specific, distance, "
					"and vocabulary-mismatch patterns are rejected with distinct "
					"rejection diagnostics."
				),
				required_improvement=(
					"Expand only principled lifted bindings, especially for "
					"object-specific or distance features, and report every rejection."
				),
				status="partially_done",
			),
			ArchitectureGap(
				id="G6",
				layer="external backends",
				gap="Paper-code reuse is an audit pipeline, not yet the full learner.",
				current_state=(
					"learner-sketches policies can be parsed, audited, bound, and used "
					"when safe; h-policy-learner and d2l are pinned and reported in the "
					"backend audit matrix but remain audit-only until verified adapters "
					"exist."
				),
				required_improvement=(
					"Implement verified policy-to-ASL adapters for non-learner-sketches "
					"backends before allowing them to drive Layer B or Layer C synthesis."
				),
				status="partially_done",
			),
			ArchitectureGap(
				id="G7",
				layer="ASL compiler",
				gap="Compiler subset needs a full paper-level semantics contract.",
				current_state=(
					"Generated heads, contexts, primitive actions, and subgoal calls are "
					"schema-checked; deterministic first-applicable execution and the "
					"currently supported ASL subset are reported with the library."
				),
				required_improvement=(
					"Define primitive-action precondition handling in the paper method "
					"section and extend the contract whenever more AgentSpeak constructs "
					"are intentionally supported."
				),
				status="partially_done",
			),
			ArchitectureGap(
				id="G8",
				layer="validation",
				gap="Current validation is bounded and smoke-test oriented.",
				current_state=(
					"Bounded all-reachable-state checks, first-applicable execution, "
					"one IPC-style first-20 benchmark runner, and one non-matching "
					"synthetic goal-dependency benchmark runner exist; experiment "
					"reports include coverage, generated ASL, generated-output audit, "
					"library size and runtime metrics, including synthesis and "
					"evaluation runtime metrics."
				),
				required_improvement=(
					"Add broader experiment protocol with more domains, ablations, "
					"baselines, held-out scaling, and deeper failure analysis."
				),
				status="partially_done",
			),
			ArchitectureGap(
				id="G9",
				layer="counterexample refinement",
				gap="Refinement hooks exist but are not a full learning loop.",
				current_state=(
					"Held-out failures are classified into lifted Layer B or Layer C "
					"records; primitive repair, atomic-progress, explicit goal-ordering, "
					"wrong-arity, undeclared-symbol, and negative precondition repairs "
					"produce machine-readable matched or rejected diagnostics."
				),
				required_improvement=(
					"Connect more failure classes to generated candidate rules and "
					"synthesize missing candidates outside the current explicit "
					"goal-ordering and goal-bound repair subsets."
				),
				status="partially_done",
			),
			ArchitectureGap(
				id="G10",
				layer="PDDL scope",
				gap="Supported PDDL fragment must stay explicit and machine-readable.",
				current_state=(
					"STRIPS-style positive conjunctive achievement goals serialize "
					"cleanly; unsupported requirements, unsupported expression operators, "
					"negative goals, numeric fragments, and action-cost fragments are "
					"rejected with structured reasons and machine-readable diagnostics "
					"before compilation proceeds."
				),
				required_improvement=(
					"Keep the report aligned with future fragment expansions, especially "
					"negative goals, disjunctive goals, derived predicates, conditional "
					"effects, quantifiers, or numeric fluents."
				),
				status="done_current_fragment",
			),
			ArchitectureGap(
				id="G11",
				layer="no-hardcoding",
				gap="No-hardcoding audit must remain enforced as implementation grows.",
				current_state=(
					"Tests scan domain-level production code and generated libraries for "
					"synthetic names, grounded terms, mutable goal descriptors, "
					"undeclared symbols, wrong arities, selected/output rule manifest "
					"leakage, and known domain-specific tokens."
				),
				required_improvement=(
					"Keep extending these checks whenever new modules or generated "
					"artifacts are added so domain-specific production branches cannot "
					"silently enter the library path."
				),
				status="partially_done",
			),
			ArchitectureGap(
				id="G12",
				layer="TEG",
				gap="DFA-to-library interface is not yet fully integrated.",
				current_state=(
					"Positive conjunctive DFA guards can be translated into "
					"schema-validated goal facts and PDDL predicate subgoal calls; "
					"a runtime controller can select DFA progress transitions and "
					"execute them through the same domain-level lifted ASL library; "
					"a temporal artifact pipeline persists the domain-level ASL "
					"library separately from query-specific DFA metadata and "
					"progress requests; the runtime controller can execute repeated "
					"progress steps until an accepting DFA state; "
					"the artifact pipeline records structured accepted/rejected DFA "
					"guard diagnostics; the supported ASL subset and execution "
					"semantics are reported with each domain-level contract."
				),
				required_improvement=(
					"Define unsupported negative/disjunctive guard semantics and "
					"run broader temporal-goal evaluation beyond smoke tests."
				),
				status="partially_done",
			),
		),
	)


def bounded_hypothesis_class_contract() -> HypothesisClassContract:
	"""Return the exact bounded hypothesis class claimed by the implementation."""

	return HypothesisClassContract(
		name="goal_conditioned_modular_sketch_asl",
		feature_language={
			"state_features": (
				"PDDL predicates over lifted variables",
				"negation-as-absence context literals",
				"safe lifted DLPlan feature bindings only",
			),
			"goal_features": (
				"read-only goal_<predicate> descriptors",
				"positive conjunctive achievement goals",
			),
			"external_features": (
				"accepted DLPlan features with explicit ASL bindings",
				"rejected object-specific, distance, or vocabulary-mismatched features",
			),
		},
		module_language={
			"heads": "declared PDDL predicate achievement goals and zero-argument +!g",
			"contexts": "implicit conjunction of supported state and goal literals",
			"body_calls": (
				"declared PDDL primitive action calls and declared PDDL predicate "
				"subgoal calls with matching schema arities"
			),
			"recursion": (
				"same-predicate recursion requires a missing-precondition or "
				"bounded acyclic-relation descent certificate"
			),
		},
		composer_language={
			"rule_shape": "goal-conditioned +!g rules selecting one atomic module",
			"ordering_evidence": (
				"trace orderings",
				"schema causal interference",
				"counterexample goal ordering",
			),
			"goal_dependency_scope": "positive conjunctive achievement goals",
		},
		progress_language={
			"selection_constraints": (
				"capability coverage",
				"transition-progress required groups",
				"bounded state-coverage required groups",
			),
			"validation_scope": "bounded reachable states from training and counterexample problems",
			"termination_checks": (
				"recursion descent audit",
				"bounded execution step limit",
				"acyclic high-level decision trace validation",
			),
		},
		correctness_language={
			"claim_scope": "bounded training/counterexample/held-out transition systems",
			"success_condition": "all positive goal atoms satisfied at fixed point",
			"runtime_planning": "no full-trace planner call during library execution",
			"evidence": (
				"synthesis report",
				"architecture contract",
				"domain-level contract",
				"bounded validation report",
				"experiment report",
			),
		},
		exclusions=(
			"arbitrary PDDL domains",
			"negative or disjunctive achievement goals",
			"numeric fluents and action costs",
			"derived predicates and conditional effects",
			"runtime full-trace planning as the plan-library executor",
		),
	)


def architecture_gap_summary(gaps: Iterable[ArchitectureGap]) -> dict[str, int]:
	"""Count architecture gaps by status for reports and tests."""

	counts: dict[str, int] = {}
	for gap in gaps:
		counts[gap.status] = counts.get(gap.status, 0) + 1
	return counts
