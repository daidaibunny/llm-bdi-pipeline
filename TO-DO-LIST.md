# To Do List

This file is the active progress tracker for the domain-level lifted
AgentSpeak(L) library research line. Historical branch cleanup and completed
PDDL/DFA migration tasks have been compacted; future work should update this
file before claiming a milestone is complete.

## Current Research Target

Achievement goals are the current scope. Temporal extended goals remain the
final target, but the DFA layer should sit above a credible achievement-goal
library instead of generating query-specific ASL libraries.

Target pipeline:

```text
PDDL domain + training problems
→ external generalized-planning learner / traces / sketches
→ feature binding
→ Layer B atomic goal modules
→ Layer C goal dependency composer
→ lifted AgentSpeak(L) domain-level plan library
→ held-out validation
→ counterexample-guided refinement
```

## Compact Completed Summary

| Area | Current status |
| --- | --- |
| HTN/HDDL removal | Completed; current benchmark direction is PDDL-only. |
| DFA high-level restoration | Completed; DFA remains the future TEG controller, not the final low-level library generator. |
| Domain-level synthesis skeleton | Implemented with schema candidates, external sketch candidates, Clingo selection, bounded validation, and counterexample inputs. |
| External backend audit | Implemented for pinned learner-sketches, h-policy-learner, d2l, and MOOSE reproduction notes. |
| Resource safety | External learner commands are guarded by default; keep memory at or below 16 GiB unless explicitly approved. |
| No synthetic ASL names | Tests cover no `achieve_*`, `transition_*`, or `dfa_state` in generated domain-level ASL. |
| No production Blocksworld hardcoding | Tests scan `src/domain_level_planning` for Blocksworld-only special cases. |

## Decisions To Confirm Or Keep Stable

| ID | Decision | Current stance | Why it matters | Status |
| --- | --- | --- | --- | --- |
| D1 | Theoretical guarantee | Use bounded-class guarantee, not universal PDDL completeness. | Universal generalized planning from arbitrary PDDL is not a credible claim; the paper must define the expressible class. | Accepted; needs formal write-up. |
| D2 | Main method family | Use goal-conditioned modular policy sketches, informed by serialized width and policy reuse. | This aligns subgoal decomposition with ASL modules better than flat policies or MOOSE-style singleton regression. | Accepted; implementation still incomplete. |
| D3 | Goal representation | Keep read-only `goal_<predicate>` facts as problem/DFA goal descriptors. | A domain-level library must know the current instance goal without becoming query-specific. | Accepted; semantics need stronger tests and write-up. |
| D4 | Fast Downward role | Use classical planners only for synthesis evidence, traces, counterexamples, and validation. | Runtime full-trace planning would collapse the contribution into a planner wrapper. | Accepted. |
| D5 | TEG integration | Keep DFA as an upper-layer controller over the achievement-goal library. | The achievement-goal library should stay domain-level while DFA remains query-specific. | Accepted; later integration pending. |
| D6 | Negative and disjunctive goals | Do not silently support them until semantics are designed. | Current Layer B/C assumes positive conjunctive achievement goals. | Open design decision. |
| D7 | Object-specific DLPlan features | Reject them unless a principled lifting method is implemented. | Guessing object-specific bindings would break lifted domain-level claims. | Accepted; future method pending. |

## Current Gaps

| ID | Layer | Gap | Current implementation | Required improvement | Acceptance check | Status |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | Theory | Bounded-class guarantee needs final paper prose, but the implementation contract is now explicit. | Reports expose a machine-readable architecture contract with guarantee, non-goals, accepted/open decisions, open gaps, and a bounded hypothesis-class contract covering feature language, module language, composer language, progress language, correctness scope, validation scope, and exclusions. | Convert the machine-readable hypothesis class into the paper method section and keep it aligned with future implementation changes. | A method section and machine-readable contract state assumptions and non-goals without ambiguity. | Partially done. |
| G2 | Layer B | Atomic module learning still lacks a full multi-strategy module learner. | PDDL add-effect rules, precondition subgoal preparation, external sketch candidates, bounded progress constraints, trace slicing, last-achiever marking, trace-justification of selected atomic rules, lifted anti-unified support patterns, recursive-module descent audits, and repair-constraint binding diagnostics now exist and are reported in the architecture contract/evidence matrix. | Add a multi-strategy module learner on top of the trace slices, anti-unified patterns, recursion certificates, and repair diagnostics, and use it to reject unsafe alternatives. | From training traces and schemas, the system can justify each selected `+!P(...)` module and reject unsafe alternatives. | Partially done. |
| G3 | Layer C | Goal dependency composer remains the largest research gap. | Shared-object trace ordering evidence, schema causal-interference ordering candidates, bounded state-coverage constraints, counterexample failure classification, primitive-precondition repair evidence, and evidence-matrix counts now exist and are reported in the architecture contract; primitive-precondition repair constraints are consumed as selector hard groups when matching prepare rules exist; goal-bound primitive-precondition failures can synthesize safe Layer B prepare candidates when read-only goal facts bind all extra variables; explicit counterexample goal-ordering constraints synthesize Layer C composer candidates and selector hard groups. | Extend ordering learning with richer final-goal causal structure and make failure classifications generate new composer/module candidates beyond the current explicit goal-ordering and goal-bound primitive-precondition repair subsets. | Strong goal-dependency domains such as Blocksworld produce bottom-up composer rules without domain hardcoding. | Partially done. |
| G4 | Goal facts | `goal_<predicate>` semantics need stricter contract. | Goal facts are read-only inputs, appear only in contexts, and renderer validation rejects them in initial beliefs, plan heads, body calls, actions, or belief updates. | Define negative-goal representation before supporting it. | Tests prove goal facts are descriptors only and never compiled as primitive actions or mutable subgoals. | Partially done. |
| G5 | Feature binding | DLPlan binding remains conservative. | Recoverable predicate, role-count, goal-aligned, role-intersection, and nullary features bind; object-specific and vocabulary-mismatch features are rejected; every backend feature now has machine-readable accepted/rejected diagnostics with binding kind, operators, action-candidate count, promoted effects, and rejection reason. | Expand principled lifted bindings beyond the current safe DLPlan fragment, especially object-specific or distance features. | Every external feature and rule has a compiled or rejected reason with no silent fallback. | Partially done. |
| G6 | External backends | Paper-code reuse is an audit pipeline, not yet the full learner. | learner-sketches policies can be parsed, audited, bound, used when safe, and summarized in a synthesis evidence matrix by source and layer; `backend_audit_matrix()` now records each pinned backend's paper role, input artifacts, output artifacts, reusable evidence, failure modes, pin status, and resource profile, and unified synthesis reports include that matrix. | Compare backends systematically and identify which backend evidence should drive Layer B versus Layer C. | A backend matrix records input, output, reusable evidence, failure modes, and resource profile. | Partially done. |
| G7 | ASL compiler | Compiler subset needs a full paper-level semantics contract. | Generated contexts/actions/subgoals are rendered and validated in tests; recursive atomic candidates need a structural descent certificate before compilation; the domain-level contract now reports the currently executable ASL subset: lifted predicate heads or `+!g`, atom/`not atom` context literals interpreted as implicit conjunction, and action/subgoal-only bodies under deterministic first-applicable execution. | Extend the contract if the compiler supports more Jason/AgentSpeak constructs, and define primitive-action precondition handling in the paper method section. | Unsupported context expressions or unsupported body step kinds fail before output; deterministic execution and the supported body/context/head subset are documented by report. | Partially done. |
| G8 | Validation | Current validation is bounded and smoke-test oriented. | Bounded all-reachable-state checks, first-applicable execution, Blocksworld first-20, and non-Blocksworld Labworkflow goal-dependency experiment runners exist. | Add broader experiment protocol: more IPC-style domains, ablations, baselines, library size, runtime, and failure analysis. | Blocksworld and at least one non-Blocksworld domain have reproducible experiment tables. | Partially done. |
| G9 | Counterexample refinement | Refinement hooks exist but are not a full learning loop. | Counterexample problem files add transition-progress and state-coverage constraints; held-out failures are classified into lifted Layer B/Layer C refinement records; primitive precondition failures now report failing primitive action, lifted missing goals, and lifted missing preconditions; primitive repair constraints are fed into later synthesis rounds and become selector hard groups when existing prepare candidates match; goal-bound unmatched repairs synthesize new conservative Layer B prepare candidates; explicit goal-ordering constraints synthesize Layer C composer candidates; unsafe unmatched repair constraints are reported as rejected binding diagnostics with available capabilities and rejection reason instead of guessed or silently ignored; refinement traces include a machine-readable summary of convergence, held-out failures, added counterexamples, repair constraints, and constraints grouped by failure kind, target layer, and constraint type. | Connect more failure classes to generated candidate rules, and synthesize missing candidates when no existing rule matches a failure classification outside the current explicit goal-ordering and goal-bound repair subsets. | A failed held-out problem can automatically refine the library and improve validation coverage, with report summaries showing what changed. | Partially done. |
| G10 | PDDL scope | Supported PDDL fragment must stay explicit and machine-readable. | `PDDLSupportReport` now serializes domain/problem files, declared requirements, supported and unsupported requirements, unsupported blocks, unsupported expression operators, fragment assumptions, and compile status; unified synthesis reports and library metadata include this audit before compilation proceeds. | Keep the report aligned with future fragment expansions, especially if negative goals, disjunctive goals, derived predicates, conditional effects, quantifiers, or numeric fluents are ever intentionally supported. | Tests prove supported STRIPS inputs serialize cleanly, action-cost/numeric fragments are rejected with structured reasons, negative goals are rejected as outside the current positive-conjunctive achievement-goal fragment, and synthesis reports include the same PDDL audit. | Done for current fragment. |
| G11 | No-hardcoding | Audit should remain enforced as implementation grows. | Tests scan domain-level production code for domain-specific tokens and generated libraries; Blocksworld and Labworkflow experiments use the same generic runner; experiment reports now include a structured generated-output audit for synthetic names, grounded terms, initial beliefs, goal descriptor misuse, and supported ASL subset compliance. | Keep extending these checks whenever new modules or generated artifacts are added. | CI fails on domain-specific production branches or synthetic/non-lifted generated plan libraries, and experiment reports expose the same audit evidence. | Partially done. |
| G12 | TEG readiness | DFA-to-library interface is not yet fully integrated. | Positive conjunctive DFA guards can be adapted into read-only `goal_<predicate>` facts and PDDL predicate subgoal calls for the domain-level library; the ASL subset and execution semantics used by this library are now reported in the architecture contract. | Integrate the adapter into the runtime DFA controller and define negative/disjunctive guard semantics. | A DFA transition guard can call the same lifted library used for ordinary achievement goals. | Partially done. |

## Implementation Tasks

| ID | Task | Gap addressed | Acceptance check | Status |
| --- | --- | --- | --- | --- |
| T1 | Add machine-readable architecture contract and gap report to synthesis output. | G1, G4, G7, G10 | `UnifiedSynthesisResult.report` exposes guarantee, decisions, support boundaries, and open gaps. | Done |
| T2 | Add tests for the architecture contract report. | G1 | Tests assert bounded-class scope, `goal_*` decision, Layer B/C gap visibility, and no universal-PDDL claim. | Done |
| T3 | Strengthen goal-fact descriptor tests. | G4 | Tests assert goal facts remain problem/DFA descriptors and are rejected as initial beliefs, plan heads, body calls, primitive actions, or belief updates. | Done |
| T4 | Extend no-hardcoding and synthetic-name audit when new modules are added. | G11 | Tests cover source and generated domain-level libraries for domain-specific logic, synthetic names, grounded output, mutable goal descriptors, and initial beliefs. | Done |
| T5 | Add backend evidence matrix to reports. | G6 | Report separates schema, external sketch, trace evidence, and counterexample evidence by layer. | Done |
| T6 | Implement trace slicing and last-achiever evidence extraction for Layer B. | G2 | Training trace evidence can explain selected atomic rules beyond raw add-effect schema candidates. | Done |
| T7 | Implement lifted anti-unification for repeated atomic-goal examples. | G2 | Repeated grounded examples produce one lifted achievement pattern with support and last-achiever counts in the evidence matrix. | Done |
| T8 | Add recursion descent/ranking checks for recursive modules. | G2, G7 | Recursive module candidates must expose a missing-precondition descent certificate or a bounded acyclic-relation ranking certificate; unsupported recursion is rejected before ASL compilation. | Done |
| T9 | Implement causal-interference ordering candidates for Layer C. | G3 | Delete/precondition interactions generate candidate composer ordering constraints. | Done |
| T10 | Convert held-out execution failures into lifted refinement constraints. | G3, G9 | Failure classifier creates lifted Layer B/Layer C refinement records and counterexample required-rule-group summaries without polluting base training data. | Done |
| T11 | Build reproducible Blocksworld first-20 experiment report from the current library path. | G8 | Train/test split, generated ASL, coverage, failures, and no-hardcoding checks are reproducible with one command. | Done |
| T12 | Add at least one non-Blocksworld goal-dependency experiment. | G8, G11 | Demonstrates the approach is not tuned to Blocksworld. | Done |
| T13 | Define and test the DFA guard to achievement-goal request adapter. | G12 | DFA guard conjunctions call `!P(...)` subgoals through the domain-level library. | Done |
| T14 | Add machine-readable PDDL fragment audit to synthesis reports. | G10 | `PDDLSupportReport.to_dict()` and `UnifiedSynthesisResult.report["pddl_support"]` expose supported/rejected requirements, blocks, operators, positive-goal assumptions, and compile status. | Done |
| T15 | Add machine-readable ASL subset and execution semantics to contract reports. | G7, G12 | `DomainLevelLibraryContractReport.to_dict()` exposes supported heads, contexts, body steps, initial beliefs, deterministic plan selection, context negation semantics, and rejects unsupported body step kinds. | Done |
| T16 | Add structured generated-output audit to experiment reports. | G11 | Domain-level experiment JSON reports expose synthetic-name, grounded-term, initial-belief, goal-descriptor, and ASL-subset audit results derived from the domain-level contract. | Done |
| T17 | Add machine-readable external backend audit matrix. | G6 | `backend_audit_matrix()` and unified synthesis reports expose pinned backend status, paper role, input/output artifacts, reusable evidence, failure modes, and resource guard profile for learner-sketches, h-policy-learner, and d2l. | Done |
| T18 | Add counterexample-refinement summary reports. | G9 | `CounterexampleGuidedSynthesisResult.to_dict()` exposes convergence, round counts, held-out solved/failed counts, added counterexamples, and constraint counts grouped by failure kind, target layer, and type. | Done |
| T19 | Add machine-readable bounded hypothesis-class contract. | G1 | `ArchitectureContract.to_dict()` exposes the bounded feature, module, composer, progress, correctness, validation, and exclusion language used for the current generalized-planning claim. | Done |
| T20 | Add machine-readable feature-binding diagnostics. | G5, G6 | `FeatureBindingReport` and `PaperPolicyAuditReport.to_dict()` expose accepted/rejected diagnostics for each DLPlan feature, including binding kind, operators, action candidates, promoted primitive effects, and rejection reason; unified synthesis reports preserve the diagnostics through `paper_policy_audits`. | Done |
| T21 | Add lifted primitive-precondition repair evidence for held-out failures. | G3, G9 | `classify_heldout_failure_for_refinement(..., domain_file=...)` turns primitive precondition failures into Layer B repair constraints with lifted missing goals, failing primitive action, missing preconditions, and summary repair counts. | Done |
| T22 | Consume primitive-precondition repair constraints during synthesis. | G3, G9 | `synthesize_domain_level_asl_library(..., refinement_constraints=...)` maps `counterexample_atomic_precondition_repair` constraints onto matching lifted prepare-rule selector hard groups and reports the matched rule names and repair constraint counts. | Done |
| T23 | Report unmatched repair constraints without guessing. | G9 | Bootstrap synthesis records unmatched primitive-precondition repair constraints as rejected binding diagnostics; paper profile fails explicitly on unmatched repair evidence instead of silently claiming the failure was consumed. | Done |
| T24 | Add repair evidence to the Layer B evidence matrix. | G2, G9 | `UnifiedSynthesisResult.report["evidence_matrix"]["layer_b_atomic_modules"]` exposes repair constraint counts and matched/rejected repair binding reports beside trace, anti-unification, and recursion evidence. | Done |
| T25 | Keep architecture contract aligned with repair evidence. | G1, G2 | `ArchitectureContract.to_dict()` now states that Layer B evidence includes counterexample repair diagnostics and that the multi-strategy learner must use them. | Done |
| T26 | Classify unmatched repair rejection reasons. | G9 | Rejected primitive-precondition repair reports expose relevant available capabilities and distinguish unproducible precondition predicates from other missing lifted prepare-rule matches. | Done |
| T27 | Cover producible-but-unmatched repair rejection. | G9 | Tests verify primitive-precondition repair diagnostics distinguish producible missing preconditions with no matching lifted prepare rule from truly unproducible predicates. | Done |
| T28 | Synthesize safe goal-bound repair candidates. | G3, G9 | Counterexample primitive-precondition repairs generate a new Layer B prepare candidate only when read-only problem goal facts bind every extra lifted variable; unsafe free-variable repairs remain rejected. | Done |
| T29 | Synthesize explicit goal-ordering composer candidates. | G3, G9 | Counterexample goal-ordering refinements directly generate and select lifted `+!g` composer candidates and selector groups; richer composer invention remains future work. | Done |

## Current Completion Rule

Before claiming a gap is complete:

1. Add or update tests that fail before the change.
2. Implement the smallest domain-agnostic change that satisfies the test.
3. Run the relevant test suite.
4. Update this file with the new status and evidence.
5. Commit and push the milestone.
