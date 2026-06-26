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
class LayerPaperQualityContract:
	"""Paper-facing contract for one learned layer."""

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
	"""The bounded-class synthesis contract reported with each library."""

	guarantee: str
	paper_core_method: tuple[str, ...]
	implementation_safeguards: tuple[str, ...]
	non_goals: tuple[str, ...]
	supported_pddl_fragment: str
	runtime_planner_policy: str
	layer_b_target: str
	layer_c_target: str
	goal_fact_semantics: str
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
			"layer_b_target": self.layer_b_target,
			"layer_c_target": self.layer_c_target,
			"goal_fact_semantics": self.goal_fact_semantics,
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
		"""Return paper-ready prose derived from the machine-readable contract."""

		hypothesis = self.hypothesis_class
		exclusions = ", ".join(hypothesis.exclusions)
		return (
			(
				"The core method is goal-conditioned modular policy-sketch "
				"synthesis: from a PDDL domain and small training problems, the "
				"system learns a lifted Layer B module library and a lifted Layer C "
				"goal composer, then compiles the selected rules to AgentSpeak(L)."
			),
			(
				"We use a bounded-class guarantee: the system synthesizes and "
				"validates the best library it can find inside this hypothesis "
				"class, and it does not claim universal PDDL generalized-planning "
				"completeness."
			),
			(
				"The representation is domain-level and lifted. State features are "
				f"{_series(hypothesis.feature_language['state_features'])}; goal "
				f"features are {_series(hypothesis.feature_language['goal_features'])}. "
				f"{self.goal_fact_semantics}."
			),
			(
				"Layer B learns atomic predicate-goal modules. "
				f"{self.layer_b_target}; bodies may use "
				f"{hypothesis.module_language['body_calls']}."
			),
			(
				"Layer C learns the conjunctive-goal composer. "
				f"{self.layer_c_target}; rules have the shape "
				f"{hypothesis.composer_language['rule_shape']} and use ordering "
				f"evidence from {_series(hypothesis.composer_language['ordering_evidence'])}. "
				f"At runtime, {hypothesis.composer_language['runtime_gate']}."
			),
			(
				"Synthesis is offline and evidence-driven. The selector enforces "
				f"{_series(hypothesis.progress_language['selection_constraints'])}, "
				f"and validation is scoped to "
				f"{hypothesis.progress_language['validation_scope']}."
			),
			(
				"Correctness is claimed only for "
				f"{hypothesis.correctness_language['claim_scope']}, with success "
				f"defined as {hypothesis.correctness_language['success_condition']}. "
				f"{self.runtime_planner_policy}; runtime full-trace planning is not "
				"the library executor."
			),
			(
				"The current exclusions are: "
				f"{exclusions}. Unsupported cases, including negative or disjunctive "
				"achievement goals, must be rejected with diagnostics before ASL "
				"compilation unless a separate semantics is added."
			),
			(
				"The current Layer B and Layer C claims are intentionally bounded: "
				"proof reports justify selected modules and composer rules, but we "
				"do not claim complete held-out tower benchmark scaling or full arbitrary-domain "
				"module learning."
			),
		)


def _series(items: object) -> str:
	if isinstance(items, str):
		return items
	values = tuple(str(item) for item in tuple(items or ()))
	if not values:
		return ""
	if len(values) == 1:
		return values[0]
	return ", ".join(values[:-1]) + f", and {values[-1]}"


def domain_level_architecture_contract() -> ArchitectureContract:
	"""Return the current research contract for lifted ASL synthesis."""

	return ArchitectureContract(
		guarantee=(
			"bounded-class guarantee: synthesize and validate the best library found "
			"inside the current goal-conditioned modular sketch hypothesis class; "
			"do not claim universal PDDL generalized-planning completeness"
		),
		paper_core_method=(
			"goal-conditioned modular policy-sketch synthesis",
			"Layer B lifted atomic predicate-goal modules",
			"Layer C lifted conjunctive-goal composer",
			"ASP-style selector over declared PDDL predicates, primitive actions, "
			"subgoal calls, and read-only goal descriptors",
			"AgentSpeak(L) compiler for the selected lifted rules",
		),
		implementation_safeguards=(
			"offline planner traces may be used only as validated synthesis evidence",
			"trace-supported macro rules are candidates, not the core method or "
			"unchecked replay output",
			"bounded validation, counterexample diagnostics, and no-hardcoding audits "
			"guard the implementation claim",
			"Fast Downward integration is a trace-evidence fallback and evaluation aid, "
			"not the runtime library executor",
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
			"goal module to call next for conjunctive goals with dependencies, "
			"and expose selected support-agenda edges as runtime ready gates"
		),
		goal_fact_semantics=(
			"goal_<predicate> atoms are read-only goal descriptors derived from "
			"PDDL goals or future DFA requests; they are not primitive actions, "
			"mutable beliefs, or synthetic achievement goals. ready_<predicate> "
			"atoms are read-only contexts derived at runtime from selected "
			"Layer C support-agenda edges, current state facts, and goal descriptors; "
			"they are not plan heads, body subgoals, primitive actions, or initial beliefs"
		),
		paper_layer_contracts=paper_layer_quality_contracts(),
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
				ArchitectureDecision(
					id="D8",
					decision=(
						"Allow cyclic same-predicate route recursion only when guarded "
						"by a verified route-step shortest-path descent feature."
					),
					status="accepted",
					rationale=(
						"Static graph distance gives a domain-agnostic progress "
						"certificate for single-effect movement schemas without "
						"falling back to trace replay."
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
					"with lifted provenance manifests; selected atomic rules now "
					"receive per-rule evidence verdicts such as trace-justified, "
					"schema-no-action-body, external-policy-bound, or "
					"counterexample-repair-synthesized; trace-supported primitive "
					"action strategies receive lower selector cost, and context-compatible "
					"primitive action alternatives are selected through strategy groups "
					"instead of requiring every action schema; those strategy groups "
					"now report selected and rejected candidate strategies with trace "
					"support, verdicts, costs, and rejection reasons; paper-profile "
					"exclusion removes unsupported schema action capabilities before selection."
				),
				required_improvement=(
					"Add a multi-strategy module learner that generalizes from these "
					"evidence sources, including repair diagnostics and candidate "
					"comparison reports, and rejects unsafe alternatives beyond the "
					"current evidence-weighted selector."
				),
				status="partially_done",
			),
			ArchitectureGap(
				id="G3",
				layer="Layer C",
				gap="Goal dependency composition remains the main research gap.",
				current_state=(
					"Shared-object trace order evidence, schema causal-interference "
					"ordering candidates for precondition-support and delete-threat "
					"relations, bounded state-coverage constraints, and "
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
					"atomic-progress diagnostics identify the offending predicates, "
					"report which PDDL actions can produce the declared target predicates, "
					"and distinguish declared-but-unproducible targets from selector "
					"mismatches; invalid or negative lifted atomic-progress goals are "
					"rejected before they can bind selector groups. "
					"Negative precondition repairs are rejected explicitly instead "
					"of being misread as positive achievement modules. Missing-module "
					"failures that name a concrete failed atomic subgoal are refined "
					"into precise atomic-progress constraints for that subgoal; top-level "
					"missing-composer failures are classified as Layer C state-coverage "
					"refinements; recursive-loop and step-limit failures are reported "
					"as non-generative termination diagnostics. Selected and "
					"output composer rules are reported with lifted provenance manifests "
					"and per-rule composer evidence verdicts; all composer candidates "
					"now report selected/rejected status, costs, verdicts, and "
					"rejection reasons. Schema-derived causal and delete-threat "
					"ordering capabilities are selector requirements and deterministic "
					"ASL output prioritizes them before generic goal dispatch, so "
					"bottom-up composer rules can be emitted from PDDL schema structure "
					"without training traces or domain-specific code; schema causal "
					"ordering also supports bounded positive-precondition binding "
					"closures for hidden producer goal arguments when the producer "
					"and consumer goal predicates differ, and composer evidence reports "
					"those binding contexts and binding depth separately from direct causal orderings. Composer evidence "
					"now records ordering kind and ordered-goal patterns for trace, "
					"schema causal-precondition, schema delete-threat, and counterexample "
					"ordering candidates."
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
				current_state=(
					"goal_<predicate> facts are used as read-only descriptors; the "
					"library contract rejects them as initial beliefs, plan heads, "
					"body calls, actions, or belief updates, and now reports every "
					"context descriptor with its mapped PDDL predicate and read-only status."
				),
				required_improvement="Define negative-goal representation before supporting it.",
				status="partially_done",
			),
			ArchitectureGap(
				id="G5",
				layer="feature binding",
				gap="DLPlan feature binding is intentionally conservative.",
				current_state=(
					"Recoverable lifted patterns bind; object-specific, distance, "
					"and vocabulary-mismatch patterns are rejected with distinct "
					"rejection diagnostics; concept, forward/reverse role, nullary, "
					"and goal-aligned concept/role intersection DLPlan features must "
					"match PDDL predicate arities before binding; feature diagnostics "
					"now include action-candidate details for ambiguous primitive "
					"effect bindings instead of only reporting candidate counts."
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
					"when safe, including policies that use forward or reverse binary "
					"role DLPlan features; h-policy-learner and d2l are pinned and "
					"reported in the backend audit matrix but remain audit-only until "
					"verified adapters exist; external policy sources pass through a synthesis-consumption "
					"gate before parsing, so audit-only or unknown backends are rejected "
					"with machine-readable blocking gaps; each synthesis run reports an "
					"external backend consumption summary for accepted/rejected sources, "
					"ready policies, compiled rules, rejected rules, candidates, and "
					"feature rejection reasons; uncompiled learned rules report "
					"per-missing-rule-binding diagnostics and unbound-body-variable "
					"diagnostics, and strict paper-profile failures include compact "
					"feature:operator binding reasons plus unbound body variables; "
					"paper policy audit readiness requires every parsed learned rule "
					"to have bound conditions, bound effects, variable-binding-safe "
					"body calls, and a non-empty executable body; external learned sketch candidates "
					"must be selected by the Clingo synthesis step before they appear "
					"in output ASL."
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
					"currently supported ASL subset are reported with the library; "
					"context execution is order-independent over implicit conjunctions, "
					"with positive literals binding variables before negated literals; "
					"primitive actions are applied by the PDDL STRIPS simulator and "
					"precondition violations become primitive-precondition counterexamples; "
					"variable-binding safety rejects body action or subgoal arguments not "
					"bound by the plan head or positive context literals; "
					"PDDL-to-ASL symbol mapping records sanitized primitive action "
					"functors so rendered ASL can be traced back to original PDDL schemas."
				),
				required_improvement=(
					"Mirror primitive-action precondition handling in the paper method "
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
					"one IPC-style first-20 benchmark runner, one non-matching "
					"synthetic goal-dependency benchmark runner, a generic PDDL split "
					"experiment runner, and a report-comparison CLI exist; experiment "
					"reports include coverage, generated ASL, generated-output audit, "
					"library size and runtime metrics, including synthesis and "
					"evaluation runtime metrics, compact Layer B and Layer C learning "
					"audit summaries, including schema causal and delete-threat ordering "
					"candidate/selected counts plus trace-ordering candidate/selected "
					"counts and composer ordering-kind counts, optional explicit ablation metadata, "
					"optional already-completed external baseline metadata without running "
					"hidden planners, a pure already-run report comparison table helper "
					"and CLI "
					"with baseline rows, best-baseline summaries, and coverage deltas "
					"against the ASL library, validated generic-runner ingestion of "
					"completed baseline JSON metadata, a validation-scope summary that separates "
					"synthesis-time bounded validation from evaluation coverage, plus "
					"top-level refinement analysis for convergence and constraint-type counts."
				),
				required_improvement=(
					"Add broader experiment protocol with more domains, actual ablations "
					"and externally comparable baseline tables, held-out scaling, and "
					"deeper failure analysis."
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
					"produce machine-readable matched or rejected diagnostics; missing-module "
					"failures are narrowed to the named failed atomic subgoal when the "
					"failure text identifies one, while `!g` failures are treated as "
					"composer state-coverage failures; recursive-loop and nontermination "
					"failures are separated from progress and ordering refinements; "
					"rejected atomic-progress diagnostics now include producer actions "
					"from PDDL add effects for declared target predicates, so wrong-arity "
					"and declared-but-unproducible failures are distinguishable; "
					"invalid or negative lifted atomic-progress goals are rejected "
					"as non-generative input errors before selector binding; "
					"the refinement loop can continue on newly classified lifted constraints "
					"even when the failed problem file was already present in the counterexample "
					"set; "
					"explicit counterexample state-coverage failures can synthesize or "
					"merge conservative goal-dispatch composer candidates and bind them "
					"as selector hard groups; unified synthesis reports expose termination "
					"diagnostic counts, diagnostic group types, explicit non-generative "
					"markers, and non-generative reasons."
				),
				required_improvement=(
					"Connect more failure classes to generated candidate rules and "
					"synthesize missing candidates outside the current explicit "
					"goal-ordering, state-coverage, and goal-bound repair subsets."
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
					"PDDL predicate symbols outside the current AgentSpeak atom "
					"identifier subset, negative goals, numeric fragments, and "
					"action-cost fragments are rejected with structured reasons and "
					"machine-readable diagnostics before compilation proceeds; "
					"action-symbol collisions after AgentSpeak sanitization are also "
					"rejected before ASL generation."
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
					"leakage, goal-descriptor usage summaries, learning-audit summaries, "
					"and known domain-specific tokens."
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
					"guard diagnostics with distinct negative, false, and disjunctive "
					"rejection reasons, and raw disjunctions are rejected before "
					"event-to-PDDL mapping can partially accept one branch; the "
					"supported ASL subset and execution "
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


def paper_layer_quality_contracts() -> tuple[LayerPaperQualityContract, ...]:
	"""Return final-paper contracts for Layer B and Layer C claims."""

	return (
		LayerPaperQualityContract(
			layer="Layer B",
			target_artifact="lifted atomic predicate-goal module set",
			core_claim=(
				"select reusable predicate-goal modules whose heads are declared "
				"PDDL predicates and whose bodies are executable ASL calls over "
				"declared primitive actions or predicate subgoals"
			),
			admissible_evidence=(
				"PDDL action-effect schemas",
				"validated bounded transition evidence",
				"offline planner traces used only as synthesis evidence",
				"external policy-sketch bindings",
				"counterexample repair and atomic-progress constraints",
			),
			selector_obligations=(
				"cover observed atomic goal-progress transitions",
				"select at least one context-compatible primitive strategy when required",
				"reject undeclared, wrong-arity, unbound-variable, or unsafe recursive rules",
				"prefer trace/sketch/repair justified rules over unjustified schema-only rules",
			),
			compiler_output=(
				"ASL plans headed by +!P(Args), with bodies containing only declared "
				"PDDL primitive actions or declared predicate subgoal calls"
			),
			runtime_semantics=(
				"atomic modules execute through deterministic first-applicable ASL "
				"selection and STRIPS-style primitive action simulation"
			),
			required_reports=(
				"atomic_module_proofs",
				"atomic_action_strategy_group_reports",
				"selected_rule_manifest",
				"rule_manifest_audit",
			),
				not_claimed=(
					"full arbitrary-domain module learning",
					"unchecked trace replay as a lifted module",
					"arbitrary multi-resource logistics policies beyond verified "
					"route movement and typed-overloaded causal-chain delivery modules",
				),
		),
		LayerPaperQualityContract(
			layer="Layer C",
			target_artifact="lifted conjunctive-goal composer plus runtime support agenda",
			core_claim=(
				"select goal-conditioned +!g rules that decide the next atomic "
				"predicate goal for positive conjunctive achievement goals"
			),
			admissible_evidence=(
				"PDDL causal precondition support",
				"PDDL delete-threat interactions",
				"last-achievement trace ordering",
				"bounded state-coverage constraints",
				"counterexample goal-ordering and state-coverage constraints",
			),
			selector_obligations=(
				"cover bounded reachable non-goal states when bounded evidence exists",
				"keep selected support-agenda edges acyclic",
				"prioritize selected ordering rules before generic goal dispatch",
				"reject undeclared or wrong-arity composer refinements before ASL generation",
			),
			compiler_output=(
				"ASL +!g plans whose contexts mention state predicates, read-only "
				"goal descriptors, and read-only ready contexts"
			),
			runtime_semantics=(
				"ready_<predicate> derived contexts gate generic +!g dispatch using "
				"selected support-agenda edges, current state facts, and goal descriptors"
			),
			required_reports=(
				"composer_rule_proofs",
				"goal_agenda",
				"runtime_goal_agenda",
				"output_composer_rule_evidence",
			),
			not_claimed=(
				"complete held-out tower benchmark scaling",
				"universal goal-order learning for arbitrary PDDL domains",
				"permanent protection of all achieved facts",
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
					"safe lifted DLPlan feature bindings, including forward/reverse binary roles",
				),
			"goal_features": (
				"read-only goal_<predicate> descriptors",
				"read-only ready_<predicate> derived contexts for runtime agenda gating",
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
				"subgoal calls with matching schema arities; every body variable "
				"must be bound by the plan head or positive context literals"
			),
				"recursion": (
					"same-predicate recursion requires a missing-precondition or "
					"bounded acyclic-relation descent certificate; single-effect "
					"movement recursion may instead use a route_step shortest-path "
					"distance-decrease context; same-predicate delegation across "
					"typed argument partitions is allowed with an explicit type certificate"
				),
				"causal_chain_modules": (
					"typed-overloaded effect predicates may use schema causal-chain "
					"action modules when a producer action supplies a target-action "
					"precondition, shared static preconditions bridge resource variables, "
					"and resource predicates are not emitted as independent causal-chain goals"
				),
		},
		composer_language={
			"rule_shape": (
				"goal-conditioned +!g rules selecting one atomic module under a "
				"runtime support agenda"
			),
			"ordering_evidence": (
				"trace orderings",
				"schema causal interference",
				"counterexample goal ordering",
			),
			"runtime_gate": (
				"selected support-agenda edges derive ready_<predicate> contexts "
				"that block generic dispatch until predecessor goals are satisfied"
			),
			"resource_priority": (
				"typed-overloaded target actions may add current-resource priority "
				"composer rules so an already-held target object is delivered before "
				"another goal consumes the same carrier resource"
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
				"arbitrary multi-resource logistics/resource agendas beyond the "
				"typed-overloaded carrier/resource causal-chain fragment",
				"runtime full-trace planning as the plan-library executor",
			),
	)


def architecture_gap_summary(gaps: Iterable[ArchitectureGap]) -> dict[str, int]:
	"""Count architecture gaps by status for reports and tests."""

	counts: dict[str, int] = {}
	for gap in gaps:
		counts[gap.status] = counts.get(gap.status, 0) + 1
	return counts
