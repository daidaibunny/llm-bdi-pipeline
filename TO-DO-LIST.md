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
| G1 | Theory | Bounded-class guarantee is not formal enough for a paper. | Reports now expose a machine-readable architecture contract with guarantee, non-goals, accepted/open decisions, and open gaps. | Define the full feature language, module language, composer language, progress, correctness, and validation scope in the paper method section. | A method section and machine-readable contract state assumptions and non-goals without ambiguity. | Partially done. |
| G2 | Layer B | Atomic module learning is still mostly schema/sketch candidate selection. | PDDL add-effect rules, precondition subgoal preparation, external sketch candidates, bounded progress constraints, and now domain-agnostic trace slicing with last-achiever marking and trace-justification of selected atomic rules exist. | Add anti-unification, multi-strategy module learning, and recursion descent checks on top of the trace slices. | From training traces and schemas, the system can justify each selected `+!P(...)` module and reject unsafe alternatives. | Partially done. |
| G3 | Layer C | Goal dependency composer is the largest research gap. | Shared-object ordering evidence and bounded state-coverage constraints exist. | Learn lifted ordering/composer rules from traces, delete/precondition interference, final-goal causal structure, and failed executions. | Strong goal-dependency domains such as Blocksworld produce bottom-up composer rules without domain hardcoding. | Open. |
| G4 | Goal facts | `goal_<predicate>` semantics need stricter contract. | Goal facts are read-only inputs, appear only in contexts, and renderer validation rejects them in initial beliefs, plan heads, body calls, actions, or belief updates. | Define negative-goal representation before supporting it. | Tests prove goal facts are descriptors only and never compiled as primitive actions or mutable subgoals. | Partially done. |
| G5 | Feature binding | DLPlan binding remains conservative. | Recoverable predicate, role-count, goal-aligned, role-intersection, and nullary features bind; object-specific and vocabulary-mismatch features are rejected. | Expand principled lifted bindings and produce accepted/rejected diagnostics for every backend rule. | Every external rule has a compiled or rejected reason with no silent fallback. | Partially done. |
| G6 | External backends | Paper-code reuse is an audit pipeline, not yet the full learner. | learner-sketches policies can be parsed, audited, bound, used when safe, and summarized in a synthesis evidence matrix by source and layer. | Compare backends systematically and identify which backend evidence should drive Layer B versus Layer C. | A backend matrix records input, output, reusable evidence, failure modes, and resource profile. | Partially done. |
| G7 | ASL compiler | Compiler subset needs a stronger semantics contract. | Generated contexts/actions/subgoals are rendered and validated in tests. | Define supported ASL subset, plan ordering semantics, negation semantics, recursion termination policy, and primitive-action precondition handling. | Invalid contexts or unsupported semantics fail before output; deterministic execution is documented by report. | In progress. |
| G8 | Validation | Current validation is bounded and smoke-test oriented. | Bounded all-reachable-state checks and first-applicable execution exist. | Add full experiment protocol: train/test splits, larger held-out instances, ablations, baselines, library size, runtime, and failure analysis. | Blocksworld and at least one non-Blocksworld domain have reproducible experiment tables. | Open. |
| G9 | Counterexample refinement | Refinement hooks exist but are not a full learning loop. | Counterexample problem files add transition-progress and state-coverage constraints. | Classify execution failures and convert each failure type into lifted module/order constraints. | A failed held-out problem can automatically refine the library and improve validation coverage. | Partially done. |
| G10 | PDDL scope | Supported PDDL fragment needs to be explicit. | STRIPS-style syntax validation rejects many unsupported requirements. | Decide exact support for negative goals, equality, typed objects, derived predicates, conditional effects, quantifiers, and numeric fluents. | `PDDLSupportReport` and paper text agree on supported and rejected fragments. | In progress. |
| G11 | No-hardcoding | Audit should remain enforced as implementation grows. | A test scans domain-level production code for Blocksworld-only tokens. | Extend checks to generated libraries and new modules whenever they are added. | CI fails on Blocksworld-specific production branches or synthetic plan names. | In progress. |
| G12 | TEG readiness | DFA-to-library interface is not yet implemented. | DFA high-level generation exists separately; achievement-goal library is domain-level. | Translate DFA guards into goal requests over the domain-level library without query-specific ASL generation. | A DFA transition guard can call the same lifted library used for ordinary achievement goals. | Later. |

## Implementation Tasks

| ID | Task | Gap addressed | Acceptance check | Status |
| --- | --- | --- | --- | --- |
| T1 | Add machine-readable architecture contract and gap report to synthesis output. | G1, G4, G7, G10 | `UnifiedSynthesisResult.report` exposes guarantee, decisions, support boundaries, and open gaps. | Done |
| T2 | Add tests for the architecture contract report. | G1 | Tests assert bounded-class scope, `goal_*` decision, Layer B/C gap visibility, and no universal-PDDL claim. | Done |
| T3 | Strengthen goal-fact descriptor tests. | G4 | Tests assert goal facts remain problem/DFA descriptors and are rejected as initial beliefs, plan heads, body calls, primitive actions, or belief updates. | Done |
| T4 | Extend no-hardcoding and synthetic-name audit when new modules are added. | G11 | Tests cover source and rendered output for forbidden synthetic names. | Pending. |
| T5 | Add backend evidence matrix to reports. | G6 | Report separates schema, external sketch, trace evidence, and counterexample evidence by layer. | Done |
| T6 | Implement trace slicing and last-achiever evidence extraction for Layer B. | G2 | Training trace evidence can explain selected atomic rules beyond raw add-effect schema candidates. | Done |
| T7 | Implement lifted anti-unification for repeated atomic-goal examples. | G2 | Repeated grounded examples produce one lifted module candidate with support count. | Pending. |
| T8 | Add recursion descent/ranking checks for recursive modules. | G2, G7 | Recursive module candidates must expose a decreasing feature or be rejected. | Pending. |
| T9 | Implement causal-interference ordering candidates for Layer C. | G3 | Delete/precondition interactions generate candidate composer ordering constraints. | Pending. |
| T10 | Convert held-out execution failures into lifted refinement constraints. | G3, G9 | Failure classifier creates new required rule groups or candidate rules without polluting base training data. | Pending. |
| T11 | Build reproducible Blocksworld first-20 experiment report from the current library path. | G8 | Train/test split, generated ASL, coverage, failures, and no-hardcoding checks are reproducible with one command. | Pending. |
| T12 | Add at least one non-Blocksworld goal-dependency experiment. | G8, G11 | Demonstrates the approach is not tuned to Blocksworld. | Pending. |
| T13 | Define and test the DFA guard to achievement-goal request adapter. | G12 | DFA guard conjunctions call `!P(...)` subgoals through the domain-level library. | Later. |

## Current Completion Rule

Before claiming a gap is complete:

1. Add or update tests that fail before the change.
2. Implement the smallest domain-agnostic change that satisfies the test.
3. Run the relevant test suite.
4. Update this file with the new status and evidence.
5. Commit and push the milestone.
