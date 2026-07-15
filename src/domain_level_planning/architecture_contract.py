"""
Machine-readable architecture contract for the current plan-library framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ArchitectureDecision:
	"""A stable design decision that constrains paper claims."""

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
	"""A known gap between current implementation and the target artifact."""

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
	"""Machine-readable bounded claim for the current framework."""

	name: str
	feature_language: dict[str, object]
	module_language: dict[str, object]
	temporal_wrapper_language: dict[str, object]
	progress_language: dict[str, object]
	correctness_language: dict[str, object]
	exclusions: tuple[str, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"name": self.name,
			"feature_language": dict(self.feature_language),
			"module_language": dict(self.module_language),
			"temporal_wrapper_language": dict(self.temporal_wrapper_language),
			"progress_language": dict(self.progress_language),
			"correctness_language": dict(self.correctness_language),
			"exclusions": list(self.exclusions),
		}


@dataclass(frozen=True)
class LayerPaperQualityContract:
	"""Paper-facing contract for one current framework layer."""

	layer: str
	target_artifact: str
	core_claim: str
	admissible_evidence: tuple[str, ...]
	selector_obligations: tuple[str, ...]
	compiler_output: str
	runtime_semantics: str
	required_reports: tuple[str, ...]
	not_claimed: tuple[str, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"layer": self.layer,
			"target_artifact": self.target_artifact,
			"core_claim": self.core_claim,
			"admissible_evidence": list(self.admissible_evidence),
			"selector_obligations": list(self.selector_obligations),
			"compiler_output": self.compiler_output,
			"runtime_semantics": self.runtime_semantics,
			"required_reports": list(self.required_reports),
			"not_claimed": list(self.not_claimed),
		}


@dataclass(frozen=True)
class ArchitectureContract:
	"""The current paper claim reported with generated artifacts."""

	guarantee: str
	paper_core_method: tuple[str, ...]
	implementation_safeguards: tuple[str, ...]
	non_goals: tuple[str, ...]
	supported_pddl_fragment: str
	runtime_planner_policy: str
	atomic_template_target: str
	temporal_append_target: str
	temporal_descriptor_semantics: str
	paper_layer_contracts: tuple[LayerPaperQualityContract, ...]
	hypothesis_class: HypothesisClassContract
	decisions: tuple[ArchitectureDecision, ...]
	gaps: tuple[ArchitectureGap, ...]

	def to_dict(self) -> dict[str, Any]:
		return {
			"guarantee": self.guarantee,
			"paper_core_method": list(self.paper_core_method),
			"implementation_safeguards": list(self.implementation_safeguards),
			"non_goals": list(self.non_goals),
			"supported_pddl_fragment": self.supported_pddl_fragment,
			"runtime_planner_policy": self.runtime_planner_policy,
			"atomic_template_target": self.atomic_template_target,
			"temporal_append_target": self.temporal_append_target,
			"temporal_descriptor_semantics": self.temporal_descriptor_semantics,
			"paper_layer_contracts": [
				contract.to_dict()
				for contract in self.paper_layer_contracts
			],
			"paper_method_summary": list(self.paper_method_summary()),
			"hypothesis_class": self.hypothesis_class.to_dict(),
			"decisions": [decision.to_dict() for decision in self.decisions],
			"gaps": [gap.to_dict() for gap in self.gaps],
		}

	def paper_method_summary(self) -> tuple[str, ...]:
		"""Return paper-ready prose derived from the contract."""

		hypothesis = self.hypothesis_class
		return (
			(
				"The core method is atomic-template import plus temporal-goal "
				"append: the system extracts singleton predicate or literal "
				"targets from a PDDL training split, consumes a verified external "
				"generalized-planning artifact, normalizes it as a "
				"LiftedPolicyProgram, and compiles lifted atomic AgentSpeak(L) "
				"plans."
			),
			(
				"The framework does not route whole domains by prior paper classes "
				"and does not claim a new universal generalized planner. Backend "
				"choice is driven by the required atomic templates and by artifact "
				"parser, binding, compiler, and validation gates."
			),
			(
				"MOOSE is the first candidate for positive singleton predicate "
				"templates because its learned readable policies are goal-regression "
				"rules over singleton goal conditions."
			),
			(
				"The temporal layer consumes lifted LTLf JSON, compiles it to a "
				"DFA, validates conjunctive guard transitions, and appends one "
				"query-local transition helper per progress edge plus "
				"query-specific +!g_query wrappers to the same domain library."
			),
			(
				"Negative transition literals remain AgentSpeak context constraints "
				"and never become negative achievement subgoals."
			),
			(
				f"The current bounded claim is {hypothesis.correctness_language['claim_scope']}; "
				f"excluded cases are {_series(hypothesis.exclusions)}."
			),
		)


def domain_level_architecture_contract() -> ArchitectureContract:
	"""Return the current research contract for lifted ASL artifacts."""

	return ArchitectureContract(
		guarantee=(
			"bounded atomic-template guarantee: import or learn lifted singleton "
			"predicate/literal plan templates from verified external generalized-"
			"planning artifacts, append conjunction-and-negation DFA transition wrappers, "
			"and do not claim universal PDDL generalized-planning completeness"
		),
		paper_core_method=(
			"atomic goal-template extraction",
			"verified external generalized-planning artifact consumption",
			"LiftedPolicyProgram normalizer",
			"AgentSpeak(L) compiler for lifted atomic plans",
			"lifted LTLf-to-DFA temporal goal append",
			"conjunctive guard-transition DFA validator",
		),
		implementation_safeguards=(
			"old in-repository GP synthesis and conjunctive-goal ordering code is not part of the current method",
			"external learners must run under resource guards",
			"backend artifacts must pass parser, binding, compiler, and validation gates",
			"negative guard literals remain context-only and never become subgoals",
			"DFA wrapper progress is encoded through one validated helper per progress edge",
		),
		non_goals=(
			"universal completeness for arbitrary PDDL domains",
			"routing a whole domain by a paper taxonomy class",
			"runtime full-trace planning for each new problem",
			"query-specific or problem-specific atomic libraries as the main artifact",
			"synthetic achievement names such as achieve_*, transition_*, or dfa_state",
			"reimplementing the external natural-language Input component",
		),
		supported_pddl_fragment=(
			"classical PDDL predicate and literal goals whose required atomic "
			"templates are accepted by a verified backend artifact"
		),
		runtime_planner_policy=(
			"classical planners may support external backend training or validation, "
			"but the generated library is not a runtime full-trace planner"
		),
		atomic_template_target=(
			"lifted +!P(Args) atomic modules compiled from "
			"verified external singleton-goal artifacts"
		),
		temporal_append_target=(
			"query-specific +!g_query wrappers from "
			"conjunctive DFA progress transitions with context-only negation"
		),
		temporal_descriptor_semantics=(
			"lifted LTLf atoms and DFA metadata are external Input artifacts, not "
			"mutable beliefs, primitive actions, or synthetic achievement goals. "
			"The current ASL output may contain query-specific g_query wrappers "
			"whose contexts are validated DFA prefix/progress literals, but not "
			"legacy unscoped dfa_state beliefs."
		),
		paper_layer_contracts=paper_layer_quality_contracts(),
		hypothesis_class=bounded_hypothesis_class_contract(),
		decisions=(
			ArchitectureDecision(
				id="D1",
				decision="Do not build a universal generalized planner in this repository.",
				status="accepted",
				rationale="The project should call verified SOTA GP backends, not invent a broad GP algorithm.",
			),
			ArchitectureDecision(
				id="D2",
				decision="Select backends by atomic template needs, not by domain taxonomy.",
				status="accepted",
				rationale="The same domain can provide different goal items; backend suitability is artifact-level.",
			),
			ArchitectureDecision(
				id="D3",
				decision="Use MOOSE first for positive singleton predicate templates.",
				status="accepted",
				rationale="MOOSE explicitly learns goal-regression rules from singleton goal conditions.",
			),
			ArchitectureDecision(
				id="D4",
				decision="Keep lifted LTLf/DFA as the temporal layer above the atomic library.",
				status="accepted",
				rationale="Temporal extended goals are query-specific while the atomic library remains domain-level.",
			),
			ArchitectureDecision(
				id="D5",
				decision="Compile negative transition literals as context constraints only.",
				status="accepted",
				rationale="Negation constrains transition eligibility; negative achievement still requires a separate backend contract.",
			),
		),
		gaps=(
			ArchitectureGap(
				id="G1",
				layer="atomic template backend",
				gap="The final paper matrix must be regenerated from one clean pinned revision.",
				current_state=(
					"Timestamped MOOSE train/dump batches and full Jason plus VAL "
					"validation are implemented, and each validation summary records "
					"its source revision and working-tree state."
				),
				required_improvement=(
					"Regenerate every reported domain result from a clean commit using "
					"the declared MOOSE, Jason, and VAL resource budgets."
				),
				status="open",
			),
			ArchitectureGap(
				id="G2",
				layer="temporal append",
				gap="DFA wrapper execution requires a controller when ASL context cannot infer DFA state.",
				current_state=(
					"The appender validates conjunction-and-negation DFA transitions, "
					"keeps negative literals context-only, and "
					"records when external DFA state is required."
				),
				required_improvement=(
					"Define the external DFA state runtime controller protocol in "
					"experiments whenever state inference from ASL contexts alone is "
					"ambiguous."
				),
				status="bounded_current_path",
			),
			ArchitectureGap(
				id="G3",
				layer="Input handoff",
				gap="Natural-language prompt generation is external to this repository.",
				current_state=(
					"The repository consumes lifted LTLf JSON with atoms and bindings, "
					"but it does not call the language model or implement retry prompts."
				),
				required_improvement=(
					"Coordinate the JSON schema and validator diagnostics with the "
					"separate Input component."
				),
				status="external_dependency",
			),
		),
	)


def paper_layer_quality_contracts() -> tuple[LayerPaperQualityContract, ...]:
	"""Return paper-facing contracts for the current two-layer framework."""

	return (
		LayerPaperQualityContract(
			layer="Atomic Template Layer",
			target_artifact="domain-level lifted atomic AgentSpeak(L) library",
			core_claim=(
				"compile verified singleton predicate/literal generalized-planning "
				"artifacts into reusable +!P(Args) ASL plans"
			),
			admissible_evidence=(
				"Evidence Module policy evidence programs",
				"MOOSE readable policy artifacts after adapter normalization",
				"other backend artifacts after adapter, parser, and binding gates",
				"PDDL domain predicate and action declarations",
				"held-out validation without runtime full-trace planning",
			),
			selector_obligations=(
				"derive required atomic templates from the train split",
				"use the Evidence Module backend that can emit validated singleton evidence",
				"reject unsupported negative templates",
				"reject undeclared predicates, wrong arities, and grounded plan heads",
			),
			compiler_output=(
				"ASL plans headed by declared PDDL predicate achievement goals with "
				"primitive PDDL action bodies"
			),
			runtime_semantics=(
				"the domain library executes atomic predicate goals without asking a "
				"classical planner for a complete trace at runtime"
			),
			required_reports=(
				"atomic_backend_decision",
				"policy_program_summary",
				"plan_library.json",
				"plan_library.asl",
			),
			not_claimed=(
				"universal arbitrary-domain generalized planning",
				"interacting conjunctive-goal solving by MOOSE directly",
				"negative literal achievement without a validated backend",
			),
		),
		LayerPaperQualityContract(
			layer="Temporal Goal Append Layer",
			target_artifact="query-specific +!g_query wrappers over the domain library",
			core_claim=(
				"compile lifted LTLf goals to DFA metadata and append wrapper plans "
				"when the unique accepting progress path uses conjunction and negation"
			),
			admissible_evidence=(
				"lifted LTLf JSON from the external Input component",
				"ltlf2dfa DFA payloads",
				"conjunctive guard-transition DFA validator diagnostics",
				"PDDL predicate arity checks",
			),
			selector_obligations=(
				"compile every progress edge into exactly one query-local transition helper",
				"accept conjunctive positive achievement literals",
				"allow negative waiting guards as DFA structure",
				"keep negative progress literals as context constraints",
				"record whether external DFA state is required",
			),
			compiler_output=(
				"ASL +!g_query entry plans that call one +!g_query_trans_i helper "
				"per DFA progress edge; each helper rechecks and repairs its guard"
			),
			runtime_semantics=(
				"an external DFA or reward-machine controller owns temporal state "
				"whenever world-state contexts alone do not identify the current "
				"DFA state"
			),
			required_reports=(
				"dfa_payload",
				"guard_transition_dfa_diagnostic",
				"temporal_append_metadata",
				"updated plan_library.asl",
			),
			not_claimed=(
				"pure context-only ASL correctness for every DFA",
				"arbitrary Boolean DFA guard compilation",
				"language-model prompt generation inside this repository",
			),
		),
	)


def bounded_hypothesis_class_contract() -> HypothesisClassContract:
	"""Return the exact bounded hypothesis class claimed now."""

	return HypothesisClassContract(
		name="atomic_template_with_guard_transition_temporal_append",
		feature_language={
			"state_features": (
				"PDDL predicate literals over lifted variables",
				"negative literals used as DFA waiting guards",
			),
			"goal_features": (
				"positive singleton predicate templates",
				"query-specific lifted LTLf goal names",
			),
			"external_features": (
				"verified MOOSE readable singleton-goal rules",
				"fallback backend artifacts only after parser and binding gates",
			),
		},
		module_language={
			"heads": "declared PDDL predicate achievement goals and query-specific +!g_query",
			"contexts": "PDDL state literals and validated conjunction-and-negation DFA guards",
			"body_calls": "declared PDDL primitive actions or declared PDDL predicate subgoals",
			"recursion": (
				"atomic modules require progress certificates; query transitions use "
				"balanced binary transition-repair trees and one source-state completion test"
			),
		},
		temporal_wrapper_language={
			"rule_shape": (
				"one +!g_query entry plus one balanced binary transition-repair tree per "
				"certified DFA progress transition"
			),
			"ordering_evidence": (
				"DFA source-state dispatch over certified distance-reducing transitions",
				"PDDL-typed conditional module-completion summaries within one signed guard",
			),
			"runtime_gate": (
				"source-state completion test after one complete transition-repair pass; "
				"ambiguous branching DFA state remains unsupported"
			),
			"goal_dependency_scope": "temporal ordering expressed by lifted LTLf and DFA",
		},
		progress_language={
			"selection_constraints": (
				"backend artifact parser success",
				"declared predicate and arity checks",
				"conjunctive guard-transition DFA validation",
			),
			"validation_scope": "selected PDDL train/test splits and supplied lifted LTLf cases",
			"termination_checks": (
				"DFA progress transitions follow the certified accepting path",
				"recursive atomic modules require a well-founded ranking certificate",
				"negative progress literals remain context-only",
			),
		},
		correctness_language={
			"claim_scope": "verified atomic libraries plus conjunction-and-negation DFA transition wrappers",
			"success_condition": "atomic subgoals are delegated to domain-level lifted ASL plans",
			"runtime_planning": "no full-trace planner call during library execution",
			"evidence": (
				"MOOSE readable compile report",
				"plan_library.asl",
				"DFA validation diagnostics",
				"unit and CLI tests",
			),
		},
		exclusions=(
			"arbitrary PDDL domains",
			"disjunctive or branching DFA progress structures without an external controller",
			"negative achievement subgoals without a validated backend",
			"numeric goals outside bounded integer resource equality",
			"runtime full-trace planning as the library executor",
		),
	)


def architecture_gap_summary(gaps: Iterable[ArchitectureGap]) -> dict[str, int]:
	"""Count architecture gaps by status for reports and tests."""

	counts: dict[str, int] = {}
	for gap in gaps:
		counts[gap.status] = counts.get(gap.status, 0) + 1
	return counts


def _series(items: Iterable[object]) -> str:
	values = tuple(str(item) for item in tuple(items or ()))
	if not values:
		return ""
	if len(values) == 1:
		return values[0]
	return ", ".join(values[:-1]) + f", and {values[-1]}"
