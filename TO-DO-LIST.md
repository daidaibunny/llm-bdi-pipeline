# To Do List

This is the active progress tracker for the domain-level lifted AgentSpeak(L)
library research line. Historical HTN/HDDL migration, branch cleanup, and the
long T1-T140 implementation log have been compacted. Keep this file focused on
current decisions, open gaps, and next implementation tasks.

## Current Research Target

Achievement goals are the current scope. Temporal extended goals remain the
final target, but the DFA layer should sit above a credible achievement-goal
library instead of generating query-specific ASL libraries.

Target pipeline:

```text
PDDL domain + training/counterexample problems
→ goal-conditioned modular policy-sketch synthesis
→ feature binding
→ Layer B atomic goal modules
→ Layer C goal dependency composer
→ lifted AgentSpeak(L) domain-level plan library
→ held-out validation
→ counterexample-guided refinement
→ future DFA controller for temporal extended goals
```

Paper core method:

```text
goal-conditioned modular policy sketches
+ lifted Layer B atomic modules
+ lifted Layer C goal composer
+ ASP-style selector
+ ASL compiler
```

Implementation safeguards, not the paper core:

- Fast Downward or other planners as offline trace-evidence providers.
- Trace-supported macro candidates.
- Bounded validation, no-hardcoding audits, and diagnostic reports.
- Counterexample failure classification unless it is used by the declared
  learning algorithm.

## Current Implemented Baseline

| Area | Current state |
| --- | --- |
| PDDL-only direction | HTN/HDDL paths are no longer the active architecture. Current benchmarks and synthesis path are PDDL-based. |
| DFA role | DFA is preserved as the future temporal-goal controller. It should call the domain-level achievement-goal library, not replace it. |
| Domain-level ASL synthesis | Unified synthesis exists: schema candidates, external sketch candidates, Clingo selection, bounded validation, counterexample inputs, ASL compilation, and report generation. |
| Layer B | Atomic modules are generated from PDDL add effects, trace evidence, repair evidence, and external sketch candidates. Reports include trace justification, strategy groups, strategy portfolios, recursion-descent audits, and selected/output manifests. |
| Layer C | Composer rules are generated from schema causal support, delete-threat interactions, trace ordering, state coverage, and counterexample ordering. Reports include a goal-agenda graph with support edges, delete-threat edges, selected support acyclicity, binding-context depth, and runtime-ready agenda metadata. |
| ASL contract | Generated plans are lifted, use PDDL predicate goal heads or `+!g`, use PDDL primitive actions/subgoals only, enforce variable-binding safety, and treat context literals as order-independent conjunction with negation-as-absence over state, goal descriptors, and derived ready-context facts. |
| Paper-profile gates | Strict profile rejects missing external learned policies, uncompiled learned rules, unselected external sketches, unjustified schema action modules, bounded-validation failures, and cyclic selected Layer C support agendas. |
| AAMAS method draft | A tracked AAMAS-2026 LaTeX paper skeleton now exists under `latex_code/aamas_method_paper/`. It fixes the formal method framing for positive conjunctive achievement goals: goal-conditioned representation, Layer B/C paper contracts, runtime ready agenda gates, hypothesis class, candidate generation, answer-set selection, compiler semantics, bounded guarantee, evaluation protocol, and explicit exclusions. |
| Experiments | Generic PDDL experiment runner, Blocksworld first-20 runner, Labworkflow dependency runner, and completed-report comparison CLI exist. |
| Resource safety | External learner commands must use `scripts/resource_guard.py`; keep memory at or below 16 GiB unless explicitly approved. |
| No hardcoding | Tests scan production domain-level code for domain-specific special cases and generated synthetic/grounded names. |
| External policy adapters | External learned policies may use an explicit source-local predicate vocabulary JSON adapter. Adapter targets are validated against the active PDDL domain; undeclared mappings are rejected instead of guessed. |
| Feature binding | Action-effect candidates now include both add and delete effects, promote unique candidates per qualitative operator, add type guards from PDDL action parameters, and promote trace-supported macros only for type-ambiguous effect predicates. Ambiguous candidates remain unpromoted instead of guessed. |
| Expanded matrix safety | Matrix rows now support an entry-level `timeout_seconds`, and experiment evaluation supports per-problem `evaluation_timeout_seconds` so one hard held-out problem becomes a structured failure instead of hanging the whole matrix. |
| Goal consistency diagnostics | Executor now performs a schema-level goal mutex precheck before `!g` execution. Symmetric add/delete evidence from PDDL action schemas turns contradictory positive achievement goals into immediate `goal_mutex` diagnostics instead of recursive ASL loops or per-problem timeouts. |

Latest known Blocksworld smoke result:

```text
script: uv run python scripts/run_blocksworld_first20_experiment.py \
  --train-count 1 --eval-count 20
coverage: 20/20
profile: bootstrap_schema_only
runtime planner: none
paper-profile ready: false, because no external learned sketch policy is selected
plan count: 40 after generic PDDL type guards
```

Latest learner-sketches Blocksworld audit:

```text
policy: blocks_4_on_1, existing official learner-sketches artifact
adapter: explicit predicate_map {"on-table": "ontable", "arm-empty": "handempty"}
bootstrap+external coverage: 20/20
external audit: 2/2 features bound, 3/3 learned rules compiled
strict paper profile: fails bounded validation when aggregate feature rules are
  forced into executable ASL
blocker class: external sketch is qualitative aggregate feature progress; it
  still needs principled variable/effect binding before it is a safe runtime
  composer
policy: blocks_4_on_2
external audit: 1/1 features bound, 1/1 learned rules compiled
strict paper profile: ready=true, coverage=20/20, selected/output external
  sketch candidate count=1, bounded validation passed
policy: blocks_4_on_1
strict paper profile with diagnostics: coverage=20/20 and bounded validation
  passed after rejecting rule 1 as no_goal_progress_evidence; ready=false only
  because the full external policy contains that unsafe aggregate rule
policy: blocks_4_on_2, paper-profile all30 diagnostic
coverage: 20/30 on `p01`-`p30`
paper profile: ready=true, blocking_failure_count=0, selected external sketch=1
plan library: 41 lifted plans, 152 ASL lines, no runtime full-trace planner
latest goal-mutex rerun: `tmp/domain-level-experiment-matrix/blocksworld-paper-external-on2-all30-goal-mutex.json`
diagnosis: `p21`-`p30` all fail before execution with `goal_mutex`; for example
  `p21` contains both `clear(b2)` and `on(b17,b2)`. Fast Downward translator
  independently reports `Goal violates a mutex` for `p21`. These are not
  Layer C execution-policy failures; the all30 local split contains
  unsatisfiable held-out goals after `p20`. We need a satisfiable larger
  Blocksworld split before claiming or rejecting larger-tower Layer C scaling.
```

## Stable Decisions

| ID | Decision | Status | Notes |
| --- | --- | --- | --- |
| D1 | Use a bounded-class guarantee, not universal arbitrary-PDDL completeness. | Accepted | The paper must state the supported hypothesis class clearly. |
| D2 | Main method family is goal-conditioned modular policy sketches. | Accepted | This combines serialized-width sketches, reusable modules, goal facts, and ASL compilation. |
| D3 | Keep read-only `goal_<predicate>` descriptors. | Accepted | A domain-level library needs instance/query goals without grounding the library itself. |
| D4 | Classical planners are synthesis/evidence/counterexample tools only. | Accepted | Runtime full-trace planning is not the target contribution. |
| D5 | Current scope is positive conjunctive achievement goals. | Accepted | Negative/disjunctive goals need a separate semantics design. |
| D6 | Reject object-specific or distance DLPlan features unless principled lifting exists. | Accepted | Guessing those bindings would undermine the lifted-library claim. |
| D7 | External paper code should be reused when verified. | Accepted | learner-sketches is the only backend currently allowed to drive synthesis; h-policy-learner and d2l remain audit-only. |
| D8 | Separate paper core method from implementation safeguards. | Accepted | Trace macros, Fast Downward fallback, bounded validators, and audits can support engineering rigor, but they must not become the main contribution narrative. |
| D9 | Use read-only `ready_<predicate>` contexts for runtime goal-agenda gating. | Accepted | `ready_` facts are derived from selected Layer C support edges plus current state and goal descriptors. They may appear only in ASL contexts, never as plan heads, body subgoals, actions, or initial beliefs. |
| D10 | State Layer B/C paper claims as bounded layer contracts. | Accepted | Each learned layer reports target artifact, admissible evidence, selector obligations, compiler/runtime semantics, required proof reports, and not-claimed boundaries so the paper cannot overclaim current implementation strength. |

## Open Gaps

| ID | Layer | Current gap | What good looks like | Priority |
| --- | --- | --- | --- | --- |
| G1 | Theory | Bounded-class guarantee now has a formal AAMAS method draft, but still needs to be integrated with final evaluation claims and related-work positioning. | Final paper prose must stay aligned with the implementation reports and must not overclaim unsupported PDDL fragments, incomplete Layer C cases, or future temporal-goal support. | High |
| G2 | Layer B | Atomic modules still rely on schema/trace heuristics plus reports, not a full learned multi-strategy module learner. | The learner can justify each selected atomic module from traces, external sketches, or repairs, and can reject unsafe alternatives beyond simple cost/coverage rules. | High |
| G3 | Layer C | Goal dependency handling is much stronger, but still not a complete learned composer. Generic `ready_<predicate>` gates now prevent generic `+!g` plans from ignoring selected support-agenda predecessors. The former Blocksworld all30 loop/timeout failure has been reclassified: `p21`-`p30` contain schema-level goal mutexes, so they are not valid evidence of larger-tower Layer C failure. | Goal-agenda and composer synthesis handle goal-dependent domains robustly, with acyclic support agendas, explainable delete-threat diagnostics, counterexample-driven new composer candidates, and scalable execution on a satisfiable larger held-out Blocksworld split. | High |
| G4 | External learners | learner-sketches Blocksworld `blocks_4_on_2` now passes strict paper-profile synthesis and 20/20 Blocksworld first-20 evaluation using an existing official policy artifact. Wider learner-sketches policies may still include unsafe aggregate rules that are rejected precisely. | A guarded learner-sketches run produces a policy artifact that is parsed, bound, selected, validated, and included in a paper-profile experiment. | High |
| G5 | Feature binding | Safe DLPlan bindings now support explicit vocabulary adapters, add/delete action-effect candidates, producer-precondition variable bridges, and rule-level no-goal-progress rejection. Remaining gap is broader lifted binding for richer DLPlan expressions such as object-specific/distance features. | Every external feature either compiles to PDDL literals/actions/subgoals or has a precise rejection reason; additional principled lifted bindings are added only when justified. | Medium |
| G6 | Validation | Current validation is smoke/bounded, not yet a broad paper experiment suite. | Multiple IPC-style domains, train/test scaling, ablations, external baselines, failure analysis, and reproducible tables. | High |
| G7 | Counterexample refinement | Refinement loop exists, but not every failure class generates new executable candidates. | Held-out failures improve coverage through generated Layer B/Layer C candidates whenever the failure is inside the supported class; unsupported cases are reported precisely. | Medium |
| G8 | Temporal extended goals | DFA-to-library interface exists for positive conjunctive guards, but broader TEG evaluation is pending. | Query-specific DFA controller calls the same domain-level library and reports guard diagnostics without generating query-specific ASL libraries. | Medium |
| G9 | Paper comparison | MOOSE and other generalized-planning systems have been studied, but current ASL pipeline lacks final comparative tables. | Completed baseline metadata and/or reproduced baseline runs are compared against the lifted ASL library under a clear protocol. | Medium |
| G10 | Training scalability | Done for the current safe fragment: when bounded transition-system exploration fails, synthesis can use a validated offline planner trace as evidence while preserving `runtime_full_trace_planner=false`. | Broaden this evidence path to more external learner artifacts and keep reports precise when no provider or invalid trace is available. | High |
| G11 | Transport-style cyclic-route modules | Still open. Generic schema rules solve direct and bounded-acyclic movement, and unsafe trace replay is now kept as candidate evidence instead of automatic output. Transport and Marsrover expose the remaining gap: same-predicate movement over cyclic route graphs lacks a learned ranking/feature, so `at(...)` recursion is correctly rejected rather than guessed. | Layer B learns type-safe multi-strategy movement/logistics modules with a verifiable cyclic-route progress measure, and Layer C composes package/vehicle/location goals without recursive loops or unsatisfied load preconditions. | High |

## Non-TEG Priority Queue

This queue excludes temporal extended goal work. Work from top to bottom so the
paper claim gets cleaner before adding harder learning machinery.

| Order | Scope | Why this order | Completion target | Status |
| --- | --- | --- | --- | --- |
| P1 | Paper/evaluation skeleton | Low risk and fixes the claim boundary before new code. | AAMAS draft has related work, backend positioning, experiment matrix, baseline protocol, ablation protocol, and failure-analysis protocol. | Done. |
| P2 | External backend decision | Mostly already implemented; needs a paper-facing fixed role. | learner-sketches is the only synthesis-consumed backend; h-policy-learner and d2l are baseline/audit-only until verified adapters exist. | Done. |
| P3 | Blocksworld expanded paper-profile run | Most direct positive evidence. | Strict paper-profile learner-sketches run on a fixed larger train/test split, not only first20 smoke. | Revised: all30 diagnostic row is not a valid larger satisfiable split because `p21`-`p30` contain goal mutexes. Latest run is 20/30, paper_profile_ready=true, blocking_failure_count=0, plan_count=41, and `failure_kind_counts={"goal_mutex": 10}`. Need a satisfiable larger split for true scaling evidence. |
| P4 | Baseline and ablation table generation | Needed for paper evaluation, independent of new learning power. | Comparison table includes classical planner, learner-sketches, MOOSE metadata, ASL library, and no-sketch/no-composer/no-refinement/no-trace ablations. | Done for infrastructure: comparison rows now include library/baseline paper-table rows, coverage deltas, runtime planner flags, selected Layer B/C evidence counts, failure summaries, and optional LaTeX result macros via `scripts/compare_domain_level_experiments.py --latex-macros-output`. Final numeric table rows still depend on the final experiment set and baseline JSON inputs. |
| P5 | Layer B evidence tightening | Turns current heuristic-looking modules into defensible learned modules. | Every selected atomic module has a compact proof object: source evidence, covered transitions, rejected alternatives, and selector reason. | Done: `atomic_module_proofs` now records selected atomic rule source, verdict, proof status, selector reason, trace-support transitions, strategy-group obligations, and rejected alternatives. Experiment `learning_audit` exposes proof counts and unjustified counts. |
| P6 | Layer C composer tightening | Main goal-dependency method gap. | Every selected composer rule has ordering evidence and failures can generate executable candidate rules when inside the supported class. | Done for current supported class: `composer_rule_proofs` now records selected composer source, verdict, proof status, selector reason, ordering kind, ordered goals, agenda edge, binding contexts, and rejected alternatives. Existing counterexample goal-ordering refinement remains executable and tested. |
| P7 | Feature-binding expansion | Only after core paper claim is stable. | Add principled bindings only for features with verified lifted semantics; otherwise keep structured rejection. | Done for current paper scope: external backend reports now include a machine-readable `feature_binding_contract` and per-policy `feature_binding_summary` with bound feature kinds, unsupported rejection reason counts, and a check that every unsupported feature has a reason. No unprincipled object-specific/distance binding was added. |
| P8 | Cyclic-route ranking/reachability | Hardest and may become limitation instead of core contribution. | Generic ranking/reachability feature solves Transport/Marsrover-style `at(...)` recursion without trace replay, or the paper explicitly excludes it. | Done by explicit bounded-claim exclusion: the architecture contract now excludes cyclic same-predicate route recursion without a ranking or reachability certificate. Transport/Marsrover remain diagnostic limitations, not positive claim domains, until a paper-backed ranking/reachability backend is implemented. |

## Immediate Next Tasks

| ID | Task | Gap | Acceptance check | Status |
| --- | --- | --- | --- | --- |
| N1 | Run a guarded learner-sketches Blocksworld policy experiment and try a strict paper-profile synthesis run. | G4, G6 | Report shows whether external policy is parsed, bound, selected, and whether bounded validation passes. Memory guard must be at or below 16 GiB. | Done for existing official artifacts: `blocks_4_on_2` strict paper-profile ready=true, coverage=20/20, bounded validation passed. Fresh guarded learner rerun remains optional for reproducibility, not for architecture blocking. |
| N2 | If N1 fails, classify the blocker precisely: vocabulary mismatch, unsupported DLPlan feature, unbound body variables, empty learned rule body, or unselected external candidate. | G4, G5 | Paper-profile failure message and `paper_policy_audits` identify the exact blocker without silent fallback. | Done for current audit: vocabulary mismatch fixed by explicit adapter; unsafe aggregate-only rules now fail with `no_goal_progress_evidence`; richer unsupported DLPlan features remain explicit rejections. |
| N3 | Implement a principled variable/effect bridge for external aggregate sketches. | G4, G5 | External auxiliary effects are compiled only when schema support links their variables to target goal parameters; unsafe aggregate rules are rejected with precise diagnostics instead of becoming runtime composer plans. | Done for current core: producer-precondition bridge is domain-agnostic, paper-profile keeps recursive prepare closures, and unsafe aggregate rules are rejected. Remaining work belongs to broader feature-language expansion. |
| N4 | Improve Layer B candidate learning where selected modules are schema-only or unjustified in paper profile. | G2 | Add failing tests from a generic PDDL domain; selected atomic modules become trace/external/repair justified or explicitly rejected. | Done for current paper-profile path: Blocksworld `blocks_4_on_2` reports 9/9 selected atomic action strategies as trace_justified and 0 unjustified selected groups; generic prepare-closure and unsafe aggregate-rule tests cover the regression. |
| N5 | Improve Layer C counterexample candidate generation beyond explicit ordering/state coverage. | G3, G7 | A held-out goal-dependency failure generates a new executable composer/module candidate and improves held-out coverage. | Done for current supported class: `test_top_level_failure_after_progress_keeps_goal_ordering_signal` preserves ordering plus state-coverage signals, and the Labworkflow refinement experiment shows held-out `p02` failing in round 0, generating `counterexample_goal_ordering`, then succeeding in round 1 with an executable `+!g` ordering composer. Broader failure-class synthesis remains G7/G9 future work. |
| N6 | Build a broader experiment matrix. | G6, G9 | At least Blocksworld plus one non-Blocksworld domain report coverage, library size, runtime, learning audit, paper-profile readiness, and baseline comparison rows. | Done for current minimum matrix: `tmp/domain-level-experiment-matrix/blocksworld-paper-on2.json` gives Blocksworld first-20 coverage 20/20, plan_count=38, paper_profile_ready=true, selected external sketch=1; `tmp/domain-level-experiment-matrix/labworkflow-refinement.json` gives non-Blocksworld coverage 2/2, plan_count=11, counterexample goal-ordering refinement converged; `tmp/domain-level-experiment-matrix/comparison.json` records comparison rows. Larger paper suite and external baselines remain G6/G9 future work. |
| N7 | Write the paper-method theory section from the machine-readable architecture contract. | G1 | Prose matches implementation reports and states bounded-class assumptions without overclaiming. | Done for implementation source of truth: `architecture_contract` now emits `paper_method_summary` paragraphs derived from the bounded-class, feature, module, composer, progress, correctness, runtime-planner, and exclusion fields; tests assert the summary covers the required theory terms without creating a separate stale documentation file. |
| N8 | Define negative/disjunctive goal and DFA guard semantics. | G5, G8 | Unsupported cases either remain rejected with precise diagnostics or get a tested semantics and ASL compilation path. | Done for current scope by explicit rejection: PDDL problem goals now distinguish `unsupported_negative_goal` and `unsupported_disjunctive_goal`; DFA guards already report `unsupported_negative_guard`, `unsupported_disjunctive_guard`, and `unsupported_false_guard`; tests cover both achievement-goal and temporal guard paths. Future support still requires a separate semantics design before compilation. |
| N9 | Keep no-hardcoding and generated-output audits current after every synthesis change. | G2, G3, G8 | `uv run pytest tests/domain_level_planning/test_no_domain_hardcoding.py -q` and relevant generated-output tests pass. | Ongoing, latest pass: no-hardcoding audit passed and full suite passed with `260 passed, 2 warnings` after N17 changes. |
| N10 | Build a paper-grade experiment matrix runner. | G6, G9 | A single command runs configured domain/profile entries, writes per-entry reports, writes comparison rows, preserves diagnostic failures, and does not call runtime full-trace planners or unguarded external learners. | Done for current infrastructure: `scripts/run_domain_level_experiment_matrix.py` consumes JSON configs or the `paper-diagnostic-smoke` preset, writes `matrix-summary.json`, per-experiment reports, and `comparison.json`; tests cover success plus diagnostic failure rows and fail-fast behavior. Latest preset run produced 5/5 succeeded rows: Blocksworld bootstrap 20/20, Blocksworld paper external 20/20, Labworkflow refinement 2/2, Transport diagnostic 1/1, and Satellite diagnostic 1/1. |
| N11 | Fix generic typed/action-cost/equality PDDL support without domain hardcoding. | G2, G5, G6 | Equality contexts execute correctly, metric-only action costs are ignored as cost updates, hyphenated symbols render safely, typed action rules cannot bind objects of the wrong PDDL type, and the diagnostic matrix reaches 5/5 succeeded rows. | Done: added generic equality support in contract/executor/transition simulation/rendering; accepted metric-only `:action-costs`, `:functions`, `:metric`, and `increase` effects while preserving collision checks; added PDDL type guard facts and action-parameter type contexts; fixed Clingo rule-id collisions for hyphenated or duplicate rule names; added trace-supported macros for type-ambiguous effect predicates only. Evidence: `uv run pytest -q` -> `249 passed, 2 warnings`; `paper-diagnostic-smoke` matrix -> `succeeded=5 failed=0`; no-hardcoding test passed. |
| N12 | Expand the matrix across all local PDDL domains and make long rows diagnostic-safe. | G6, G10, G11 | `paper-expanded-smoke` covers Blocksworld, Labworkflow, Transport, Satellite, and Marsrover; per-entry and per-problem timeouts prevent runaway rows; failures identify the next generic Layer B/C gaps. | Updated diagnostic scope: bounded failures now can fall back to synthesis planner traces when configured. Latest focused smoke results after trace-macro safety tightening: Transport train3 first10 = 0/10 because cyclic `at(...)` recursion is rejected without a ranking feature; Marsrover train3 first5 with Fast Downward synthesis traces = 0/5 but synthesis succeeds with `synthesis_planner_trace_evidence_count=1`, proving G10 while exposing G11. |
| N13 | Design and implement a principled cyclic-route progress feature for same-predicate movement modules. | G2, G11 | A generic PDDL domain with cyclic route facts learns a lifted `P(entity, target)` module that reaches the target without trace replay, recursive loops, or runtime full-trace planning. Transport and Marsrover improve through the same generic mechanism. | Deferred beyond current paper claim. The current method explicitly rejects cyclic same-predicate route recursion unless a ranking or reachability certificate exists; future work can implement a paper-backed route-composition or ranking-feature backend. |
| N14 | Rewrite the method plan around the simplified core contribution before adding more functionality. | G1, G2, G3 | The architecture contract and tests distinguish paper core method from implementation safeguards; the next implementation task can be justified by the core method, not by ad hoc failure patching. | Done for the paper-method draft: `latex_code/aamas_method_paper/main.tex` and `sections/method.tex` define the AAMAS-formatted formal algorithm, bounded-class guarantee, candidate language, selector, compiler semantics, evaluation protocol, and exclusions. Verified with `latexmk -pdf main.tex`. |
| N15 | Expand the method draft into a full evaluation-ready paper skeleton. | G1, G6, G9 | Add related work, experiment table shells, ablation protocol, final claim checklist, and result-import macros without changing the fixed core algorithm. | Done for infrastructure: related-work positioning, non-temporal evaluation matrix, baseline protocol, ablation protocol, failure-analysis protocol, optional `generated/results.tex` import, and comparison-to-LaTeX macro generation are implemented. Final macro values remain tied to final experiment outputs, not hard-coded into the paper. |
| N16 | Add runtime `ready_<predicate>` agenda gates for generic `+!g` composer plans. | G3, G6 | Generic composer contexts include `ready_P(...)`; selected support agenda edges are saved in plan-library metadata; executor derives ready facts from current state plus goal descriptors; contract rejects mutable `ready_` use; Blocksworld first20 remains 20/20 and all30 failure mode is remeasured. | Done for plumbing: schema synthesis emits `goal_P(...) & ready_P(...) & not P(...)`; `runtime_goal_agenda` records selected support edges; executor evaluates derived ready contexts domain-generically using `earlier`, `later`, and `binding_contexts`; contract treats `ready_` as read-only derived context while respecting declared PDDL predicates such as `ready_a`. Evidence: `uv run pytest -q` -> `260 passed, 2 warnings`. The old all30 loop/timeout diagnosis is superseded by N18 goal-mutex diagnostics. |
| N17 | Pull Layer B and Layer C architecture back to final-paper quality. | G1, G2, G3 | Architecture report and AAMAS method text expose the exact bounded Layer B/C claims: artifact, admissible evidence, selector obligations, compiler/runtime semantics, required proof reports, and explicit not-claimed boundaries. | Done for contract alignment: `architecture_contract` now emits `paper_layer_contracts` for Layer B and Layer C; Layer C contract includes `ready_<predicate>` runtime support agenda semantics and explicitly does not claim complete held-out tower benchmark scaling; Layer B contract separates admissible evidence and proof reports from full arbitrary-domain module learning. AAMAS method text now describes ready facts, Layer B proof boundaries, Layer C runtime agenda gates, and the all30 limitation. Evidence: architecture contract test passed; no-hardcoding audit passed; `latexmk -pdf main.tex` passed; `uv run pytest -q` -> `260 passed, 2 warnings`. |
| N18 | Diagnose and repair the Blocksworld all30 `p21` loop/timeout failure mode. | G3, G6 | Reproduce `p21`, explain the exact root cause, add a generic fix, and verify first20/no-hardcoding do not regress. | Done: `p21` was reproduced as `recursive loop on !g` after 236 actions, but the final missing goals revealed a contradictory goal set (`clear(b2)` with `on(b17,b2)`). Added domain-agnostic schema-level goal mutex diagnostics from symmetric PDDL add/delete effects. `p21` now fails in 0 steps with `goal mutex detected`; `p22`-`p30` are also classified as `goal_mutex`. Evidence: targeted executor tests passed, Blocksworld first20 still passed, no-hardcoding passed, all30 report has `failure_kind_counts={"goal_mutex": 10}`. |

## Commands To Use

Core checks:

```bash
uv run pytest -q
uv run pytest tests/domain_level_planning/test_no_domain_hardcoding.py -q
uv run python scripts/run_blocksworld_first20_experiment.py \
  --output tmp/blocksworld-first20-experiment/report.json \
  --train-count 1 --eval-count 20
uv run python scripts/run_domain_level_experiment_matrix.py \
  --preset paper-diagnostic-smoke \
  --output-dir tmp/domain-level-experiment-matrix/paper-diagnostic-smoke
uv run python scripts/run_domain_level_experiment_matrix.py \
  --preset paper-expanded-smoke \
  --output-dir tmp/domain-level-experiment-matrix/paper-expanded-smoke
```

External backend audit:

```bash
uv run python scripts/gp_backend_audit.py status
uv run python scripts/gp_backend_audit.py learner-sketches-command --experiment all
uv run python scripts/gp_backend_audit.py learner-sketches-summary --experiment all
```

Do not run external generalized-planning learners without a hard memory guard.

## Completion Rule

Before claiming a gap is complete:

1. Add or update tests that fail before the change.
2. Implement the smallest domain-agnostic change that satisfies the test.
3. Run the relevant test suite.
4. Update this file with the new status and evidence.
5. Commit and push the milestone.
