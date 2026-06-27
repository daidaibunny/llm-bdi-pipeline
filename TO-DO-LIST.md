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

policy: blocks_4_on_2, paper-profile satisfiable-large diagnostic
split: `src/domains/blocksworld/satisfiable-large/p01.pddl`-`p10.pddl`
object counts: 50, 60, 70, 80, 90, 100, 110, 120, 130, 140
goal shape: full `on(...)` tower from all-table initial states; no
  `clear(...)` or `ontable(...)` goals, so the split tests bottom-up tower
  dependency without final-goal mutexes.
latest report directory: `tmp/domain-level-experiment-matrix/blocksworld-satisfiable-large/`
bootstrap train1 result: 10/10, step count min=98, max=278, mean=188.0
paper external `blocks_4_on_2` result: 10/10, paper_profile_ready=true,
  step count min=98, max=278, mean=188.0

policy: blocks_4_on_2, paper-profile satisfiable-mixed-large diagnostic
split: `src/domains/blocksworld/satisfiable-mixed-large/p01.pddl`-`p10.pddl`
object counts: 20, 30, 40, 50, 60, 70, 80, 90, 100, 110
goal shape: multiple final towers with mixed `ontable(...)` root goals and
  `on(...)` tower-link goals; initial states contain nontrivial towers rather
  than all blocks on the table.
latest report directory: `tmp/domain-level-experiment-matrix/blocksworld-satisfiable-mixed-large/`
bootstrap train1 result: 10/10, paper_profile_ready=false as expected for
  schema-only bootstrap, plan_count=40.
paper external `blocks_4_on_2` result: 10/10, paper_profile_ready=true,
  selected external sketch=1, selected goal agenda acyclic=true, plan_count=41,
  runtime planner=none.
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
| D7 | External paper code should be reused when verified. | Accepted | learner-sketches, h-policy-learner, and d2l can drive synthesis only through verified policy dialect adapters, conservative feature binding, rule-level safety checks, and Clingo selection. Unknown backend names remain rejected. |
| D8 | Separate paper core method from implementation safeguards. | Accepted | Trace macros, Fast Downward fallback, bounded validators, and audits can support engineering rigor, but they must not become the main contribution narrative. |
| D9 | Use read-only `ready_<predicate>` contexts for runtime goal-agenda gating. | Accepted | `ready_` facts are derived from selected Layer C support edges plus current state and goal descriptors. They may appear only in ASL contexts, never as plan heads, body subgoals, actions, or initial beliefs. |
| D10 | State Layer B/C paper claims as bounded layer contracts. | Accepted | Each learned layer reports target artifact, admissible evidence, selector obligations, compiler/runtime semantics, required proof reports, and not-claimed boundaries so the paper cannot overclaim current implementation strength. |

## Open Gaps

| ID | Layer | Current gap | What good looks like | Priority |
| --- | --- | --- | --- | --- |
| G1 | Theory | Done for the current achievement-goal fragment: bounded-class guarantee now has a machine-readable contract plus formal AAMAS method draft covering feature, module, composer, progress, compiler, and bounded-correctness languages. | Final paper prose must stay aligned with the implementation reports and must not overclaim unsupported PDDL fragments, incomplete Layer C cases, or future temporal-goal support. | High |
| G2 | Layer B | Done for the declared bounded hypothesis class: selected atomic modules now carry proof records, selector reasons, declared-symbol checks, variable-binding checks, trace/sketch/repair evidence, rejected alternatives, and recursion-safety audits when recursion appears. | Future improvements may broaden the hypothesis class, but universal arbitrary-domain module learning is explicitly outside the paper claim. | Done |
| G3 | Layer C | Done for the declared bounded hypothesis class: selected composer rules must satisfy bounded state coverage when evidence exists, acyclic support-agenda checks, runtime `ready_<predicate>` gates, ordering/provenance proof records, and counterexample/state-coverage binding diagnostics. Larger satisfiable Blocksworld splits solve 10/10 under the paper external profile; the old all30 tail is a goal-mutex diagnostic, not a composer loop. | Future work may add richer final-goal causal structures, but universal arbitrary-domain goal-order learning is explicitly outside the paper claim. | Done |
| G4 | External learners | learner-sketches, h-policy-learner, and d2l now have synthesis-consumable verified adapters for safe policy dialects. h-policy hierarchical `sketch_str.txt` artifacts reuse the DLPlan policy path, including safe filtered goal-role features. d2l text policies convert only the recoverable lifted subset into internal sketch rules; unsupported D2L features remain rejected with D2L-specific diagnostics. | Broaden backend-specific feature dialect support only with principled lifted bindings and keep unsafe artifacts rejected. | Done |
| G5 | Feature binding | Safe DLPlan bindings now support explicit vocabulary adapters, add/delete action-effect candidates, producer-precondition variable bridges, and rule-level no-goal-progress rejection. Remaining gap is broader lifted binding for richer DLPlan expressions such as object-specific/distance features. | Every external feature either compiles to PDDL literals/actions/subgoals or has a precise rejection reason; additional principled lifted bindings are added only when justified. | Medium |
| G6 | Validation | Done for the current paper package. The final-data protocol produces main, ablation, limitation, baseline, comparison, and LaTeX macro outputs. Main Blocksworld strict paper-profile rows solve first20, satisfiable-large, and satisfiable-mixed-large with runtime planner `none`; Labworkflow supplies the Layer C/counterexample-refinement stress because current Blocksworld no-Layer-C probes still solve 100% and therefore do not isolate that mechanism. `scripts/run_final_paper_data.py --validate-only` now checks the final package, matrix summaries, baseline rows, strict-profile rows, coverage-drop ablations, runtime-planner labels, and generated result macros. | Future validation can broaden the domain set or add a harder Blocksworld Layer C stress split, but the current final paper tables must describe this boundary honestly. | Done |
| G7 | Counterexample refinement | Refinement loop exists, but not every failure class generates new executable candidates. | Held-out failures improve coverage through generated Layer B/Layer C candidates whenever the failure is inside the supported class; unsupported cases are reported precisely. | Medium |
| G8 | Temporal extended goals | DFA-to-library interface exists for positive conjunctive guards, but broader TEG evaluation is pending. | Query-specific DFA controller calls the same domain-level library and reports guard diagnostics without generating query-specific ASL libraries. | Medium |
| G9 | Paper comparison | Done for the current final package. Baseline records include Fast Downward per-problem trace baselines, raw learner-sketches artifact audits, and MOOSE status-CSV probes, each marked with `comparison_scope`, `domain_level_artifact`, `coverage_semantics`, and `runtime_planner`. LaTeX result macros now use unique, digit-free command names so repeated baseline labels across splits cannot collide. | Future comparison work can add stronger executable h-policy/d2l rows, but the current paper no longer lacks baseline tables or result-import plumbing. | Done |
| G10 | Training scalability | Done for the current safe fragment: when bounded transition-system exploration fails, synthesis can use a validated offline planner trace as evidence while preserving `runtime_full_trace_planner=false`. Marsrover now uses this path as a fixed-resource trace-evidence fragment rather than failing at transition-system explosion. | Future work can broaden this evidence path to more external learner artifacts and keep reports precise when no provider or invalid trace is available. | Done |
| G11 | Resource/route modules | Boundary for the current paper: typed-overloaded logistics and Marsrover-style producer-resource fragments are supported from problem initial states. Layer B now learns generic route-step shortest-path descent for single-effect movement schemas, causal-chain modules for typed-overloaded effects, producer-backed hidden-resource prepare rules, disconnected final-action location binding, and saturated static filters after hidden variables are bound. Transport train3 first10 and Marsrover trace-evidence first10 both solve 10/10 from problem initial states with no runtime full-trace planner. Bounded all-reachable-state validation still reports mid-state counterexamples, so this is not claimed as a complete arbitrary reachable-state logistics policy. | Report Transport/Marsrover as boundary rows unless a future method strengthens reachable-mid-state repair/counterexample refinement. | Boundary |

## Non-TEG Priority Queue

This queue excludes temporal extended goal work. Work from top to bottom so the
paper claim gets cleaner before adding harder learning machinery.

| Order | Scope | Why this order | Completion target | Status |
| --- | --- | --- | --- | --- |
| P1 | Paper/evaluation skeleton | Low risk and fixes the claim boundary before new code. | AAMAS draft has related work, backend positioning, experiment matrix, baseline protocol, ablation protocol, and failure-analysis protocol. | Done. |
| P2 | External backend decision | Implemented. | learner-sketches, h-policy-learner, and d2l are synthesis-consumable only through verified adapters; unknown backends are rejected. | Done. |
| P3 | Blocksworld expanded paper-profile run | Most direct positive evidence. | Strict paper-profile learner-sketches run on fixed larger train/test splits, not only first20 smoke. | Done for two satisfiable larger splits: `satisfiable-large` covers 50-140 block full towers, and `satisfiable-mixed-large` covers 20-110 block nontrivial initial towers with multiple final towers and mixed `ontable`/`on` goals. Paper external `blocks_4_on_2` solves both 10/10 with `paper_profile_ready=true`. The old all30 row remains only a goal-mutex diagnostic. |
| P4 | Baseline and ablation table generation | Needed for paper evaluation, independent of new learning power. | Comparison table includes classical planner, learner-sketches, MOOSE metadata, ASL library, and no-sketch/no-composer/no-refinement/no-trace ablations. | Done for infrastructure and first real synthesis toggle: comparison rows now include library/baseline paper-table rows, coverage deltas, runtime planner flags, selected Layer B/C evidence counts, failure summaries, machine-readable ablation mechanism status, and optional LaTeX result macros via `scripts/compare_domain_level_experiments.py --latex-macros-output`. `disabled_synthesis_mechanisms=["layer_c_ordering"]` filters Layer C ordering candidates and reports removed rules. Final numeric table rows still depend on the final experiment set and baseline JSON inputs. |
| P5 | Layer B evidence tightening | Turns current heuristic-looking modules into defensible learned modules. | Every selected atomic module has a compact proof object: source evidence, covered transitions, rejected alternatives, and selector reason. | Done: `atomic_module_proofs` now records selected atomic rule source, verdict, proof status, selector reason, trace-support transitions, strategy-group obligations, and rejected alternatives. Experiment `learning_audit` exposes proof counts and unjustified counts. |
| P6 | Layer C composer tightening | Main goal-dependency method gap. | Every selected composer rule has ordering evidence and failures can generate executable candidate rules when inside the supported class. | Done for current supported class: `composer_rule_proofs` now records selected composer source, verdict, proof status, selector reason, ordering kind, ordered goals, agenda edge, binding contexts, and rejected alternatives. Existing counterexample goal-ordering refinement remains executable and tested. |
| P7 | Feature-binding expansion | Only after core paper claim is stable. | Add principled bindings only for features with verified lifted semantics; otherwise keep structured rejection. | Done for current paper scope: external backend reports now include a machine-readable `feature_binding_contract` and per-policy `feature_binding_summary` with bound feature kinds, unsupported rejection reason counts, and a check that every unsupported feature has a reason. No unprincipled object-specific/distance binding was added. |
| P8 | Cyclic-route ranking/reachability and typed carrier/resource delivery | Hardest non-Blocksworld improvement. | Generic route progress solves single-effect movement recursion, and typed-overloaded causal-chain modules solve carrier/package delivery without trace replay or capacity subgoal pollution. | Done for the current fragment: schema synthesis infers `route_step_*` contexts from PDDL movement schemas, executor derives route progress for the current atomic subgoal target, recursion audit accepts route-step descent and typed partition delegation, causal-chain modules use shared static preconditions to bridge resource variables, and current-resource priority handles already-held target objects in a generic mid-state test. Transport train3 first10 solves 10/10 from initial states; arbitrary reachable mid-state logistics coverage remains open. |

## Final Paper Data Plan

The final data package is the acceptance target for the current paper package.
It is acceptable only when it produces a reproducible result directory, a
comparison JSON with non-empty baseline rows, LaTeX result macros, and a clear
split between main claims, ablations, baselines, and limitation diagnostics.
The package must also pass:

```bash
uv run python scripts/run_final_paper_data.py \
  --output-dir tmp/paper-final-latest --validate-only
```

### Final Claim Boundary

| Claim class | Included in main claim? | Required evidence | Excluded or limitation evidence |
| --- | --- | --- | --- |
| Positive conjunctive achievement goals | Yes | Held-out execution of the compiled lifted ASL library. Runtime full-trace planner must be `none`. | Negative, disjunctive, quantified, and temporal goals stay outside the main experiment unless a tested semantics is added. |
| Domain-level lifted library | Yes | No grounded plan heads, no synthetic `achieve_*`, `transition_*`, or `dfa_state` names, no object-specific training replay. | Per-problem planner traces may be baseline or synthesis evidence only. |
| Goal dependency | Yes | At least one Blocksworld or equivalent split where Layer C evidence is necessary or where the no-Layer-C ablation has a meaningful failure/deterioration. | A split where no-Layer-C also solves 100% is not enough to support the Layer C contribution. |
| External paper-code reuse | Yes | learner-sketches policy selected by the strict paper profile; h-policy-learner and d2l reported through verified adapter compatibility or explicit safe rejection. | Unsupported external feature dialects are diagnostics, not silent fallbacks. |
| Broader PDDL applicability | Secondary | Transport/Satellite style rows may support engineering breadth only when their fragment limits are explicit. | Marsrover-scale state explosion is a limitation unless trace-evidence or external-backend synthesis succeeds under fixed resources. |
| Temporal extended goals | No for current paper | DFA role may be described as future upper controller. | No TEG coverage table is required for this achievement-goal paper. |

### Required Final Tables

| Table | Purpose | Minimum rows | Acceptance criteria |
| --- | --- | --- | --- |
| Main results | Show the proposed lifted ASL library works as a domain-level artifact. | Blocksworld strict paper profile first20; Blocksworld satisfiable-large; Blocksworld satisfiable-mixed-large; Labworkflow refinement; optional Transport/Satellite secondary rows. | Main Blocksworld rows must be `paper_profile_ready=true`, coverage 100%, runtime planner `none`, selected external sketch count greater than 0 where labeled external. |
| Baselines | Show how the method compares with existing planning/generalized-planning tools. | Classical planner per-problem trace baseline; raw learner-sketches policy baseline; MOOSE where assumptions apply; optional h-policy/d2l audit baseline. | `comparison.json` must have `baseline_count > 0`; each baseline record must state whether it is domain-level, per-problem, or audit-only. |
| Ablations | Show each mechanism matters. | No external sketch; no Layer C ordering; no counterexample refinement; no offline synthesis trace evidence. | At least one ablation must produce a meaningful coverage drop or blocking diagnostic for the mechanism it removes. If a row remains 100%, the paper must explain why that split does not stress that mechanism. |
| Goal-dependency stress | Specifically justify Layer C. | A hard Blocksworld dependency split or equivalent conjunctive-goal dependency domain, plus the no-Layer-C row on the same split. | Full method succeeds; no-Layer-C fails, times out, or reports missing/unsafe composer evidence. |
| Failure analysis | Make limitations paper-useful instead of vague. | Marsrover scalability diagnostic; Transport reachable-mid-state diagnostic; unsupported feature-binding diagnostics. | Every failure row must have a precise reason, not just failed coverage. Diagnostic failures must not be mixed into the main success-count claim. |
| Reproducibility | Let the final numbers be regenerated. | Commit hash, command lines, train/eval split files, resource limits, timeout settings, backend pins, and generated LaTeX macros. | A single documented command sequence regenerates the result directory and `latex_code/aamas_method_paper/generated/results.tex`. |

### Final Experiment Protocol

| Phase | Output directory | Required command or artifact | Notes |
| --- | --- | --- | --- |
| 1. Backend audit | `tmp/paper-final/backend-audit/` | `uv run python scripts/gp_backend_audit.py status` and learner-sketches summary commands. | Confirms pinned backends before result generation. External learners must keep memory guards at or below 16 GiB. |
| 2. Library matrix | `tmp/paper-final/main-matrix/` | A fixed JSON config, not the development preset name, should run final library rows. | No unresolved failed rows in the main matrix. Marsrover belongs in a separate limitation matrix unless repaired. |
| 3. Baseline generation | `tmp/paper-final/baselines/` | Generate completed baseline JSON records for classical planner, raw learner-sketches, and MOOSE/audit baselines. | Baselines are compared as baselines, not used as runtime execution for the proposed library. |
| 4. Ablation matrix | `tmp/paper-final/ablation-matrix/` | Same splits as main rows, one mechanism disabled per row. | The Layer C ablation must include a split that actually stresses goal dependency. |
| 5. Limitation matrix | `tmp/paper-final/limitation-matrix/` | Expected diagnostic rows for unsupported fragments and scalability boundaries. | These rows support honest scope, not the main positive coverage claim. |
| 6. Comparison and macros | `tmp/paper-final/comparison.json` and `latex_code/aamas_method_paper/generated/results.tex` | `uv run python scripts/compare_domain_level_experiments.py ... --latex-macros-output ...` | The paper must import generated macros instead of manually transcribing final values. |
| 7. Verification | root test output, final-package validation, and LaTeX build output | `uv run pytest -q`; `uv run python scripts/run_final_paper_data.py --output-dir tmp/paper-final-latest --validate-only`; `cd latex_code/aamas_method_paper && latexmk -pdf -outdir=build main.tex` | Final data is not accepted if tests fail, final package validation fails, or the paper does not compile. |

### Data Acceptance Checklist

- `comparison.json` has `baseline_count > 0`.
- Every main method row reports `runtime_planner = "none"`.
- Every strict paper-profile main row reports `paper_profile_ready = true`.
- Every generated ASL library passes no-synthetic-name and no-grounded-plan-head audits.
- Every selected Layer B and Layer C rule has proof/provenance metadata.
- Layer C is tested on at least one split where disabling it is informative.
- All baseline records state whether they are per-problem planners, generalized-policy systems, or audit-only external artifacts.
- Marsrover is reported as a fixed-resource synthesis-trace fragment, and bounded exploration without trace evidence is described only as a scalability diagnostic.
- Final result macros are generated from JSON reports, not handwritten.
- `scripts/run_final_paper_data.py --validate-only` succeeds on the final package.
- The final paper text only claims the supported bounded class and does not claim arbitrary-domain generalized planning completeness.

## Immediate Next Tasks

| ID | Task | Gap | Acceptance check | Status |
| --- | --- | --- | --- | --- |
| N1 | Run a guarded learner-sketches Blocksworld policy experiment and try a strict paper-profile synthesis run. | G4, G6 | Report shows whether external policy is parsed, bound, selected, and whether bounded validation passes. Memory guard must be at or below 16 GiB. | Done for existing official artifacts: `blocks_4_on_2` strict paper-profile ready=true, coverage=20/20, bounded validation passed. Fresh guarded learner rerun remains optional for reproducibility, not for architecture blocking. |
| N2 | If N1 fails, classify the blocker precisely: vocabulary mismatch, unsupported DLPlan feature, unbound body variables, empty learned rule body, or unselected external candidate. | G4, G5 | Paper-profile failure message and `paper_policy_audits` identify the exact blocker without silent fallback. | Done for current audit: vocabulary mismatch fixed by explicit adapter; unsafe aggregate-only rules now fail with `no_goal_progress_evidence`; richer unsupported DLPlan features remain explicit rejections. |
| N3 | Implement a principled variable/effect bridge for external aggregate sketches. | G4, G5 | External auxiliary effects are compiled only when schema support links their variables to target goal parameters; unsafe aggregate rules are rejected with precise diagnostics instead of becoming runtime composer plans. | Done for current core: producer-precondition bridge is domain-agnostic, paper-profile keeps recursive prepare closures, and unsafe aggregate rules are rejected. Remaining work belongs to broader feature-language expansion. |
| N4 | Improve Layer B candidate learning where selected modules are schema-only or unjustified in paper profile. | G2 | Add failing tests from a generic PDDL domain; selected atomic modules become trace/external/repair justified or explicitly rejected. | Done for current paper-profile path: Blocksworld `blocks_4_on_2` reports 9/9 selected atomic action strategies as trace_justified and 0 unjustified selected groups; generic prepare-closure and unsafe aggregate-rule tests cover the regression. |
| N5 | Improve Layer C counterexample candidate generation beyond explicit ordering/state coverage. | G3, G7 | A held-out goal-dependency failure generates a new executable composer/module candidate and improves held-out coverage. | Done for current supported class: `test_top_level_failure_after_progress_keeps_goal_ordering_signal` preserves ordering plus state-coverage signals, and the Labworkflow refinement experiment shows held-out `p02` failing in round 0, generating `counterexample_goal_ordering`, then succeeding in round 1 with an executable `+!g` ordering composer. Broader failure-class synthesis remains G7/G9 future work. |
| N6 | Build a broader experiment matrix. | G6, G9 | At least Blocksworld plus one non-Blocksworld domain report coverage, library size, runtime, learning audit, paper-profile readiness, and baseline comparison rows. | Done for the current paper-expanded matrix infrastructure. Latest final/probe evidence: Blocksworld paper-profile first20 20/20, satisfiable-large 10/10, satisfiable-mixed-large 10/10; Labworkflow 2/2; Satellite first10 10/10; Transport train3 first10 10/10 with plan_count 28 after current-resource priority; Marsrover trace-evidence train1 first10 10/10 after generic hidden-resource and final-location binding repairs. Experiment and comparison reports include mechanism status for ablation rows. External baselines remain G9 future work. |
| N7 | Write the paper-method theory section from the machine-readable architecture contract. | G1 | Prose matches implementation reports and states bounded-class assumptions without overclaiming. | Done for implementation source of truth: `architecture_contract` now emits `paper_method_summary` paragraphs derived from the bounded-class, feature, module, composer, progress, correctness, runtime-planner, and exclusion fields; tests assert the summary covers the required theory terms without creating a separate stale documentation file. |
| N8 | Define negative/disjunctive goal and DFA guard semantics. | G5, G8 | Unsupported cases either remain rejected with precise diagnostics or get a tested semantics and ASL compilation path. | Done for current scope by explicit rejection: PDDL problem goals now distinguish `unsupported_negative_goal` and `unsupported_disjunctive_goal`; DFA guards already report `unsupported_negative_guard`, `unsupported_disjunctive_guard`, and `unsupported_false_guard`; tests cover both achievement-goal and temporal guard paths. Future support still requires a separate semantics design before compilation. |
| N9 | Keep no-hardcoding and generated-output audits current after every synthesis change. | G2, G3, G8 | `uv run pytest tests/domain_level_planning/test_no_domain_hardcoding.py -q` and relevant generated-output tests pass. | Ongoing, latest pass: no-hardcoding audit is covered by the full suite, and `uv run pytest -q` passed with `278 passed, 2 warnings` after verified h-policy/d2l backend adapters and bounded Layer B/C contract closure. |
| N10 | Build a paper-grade experiment matrix runner. | G6, G9 | A single command runs configured domain/profile entries, writes per-entry reports, writes comparison rows, preserves diagnostic failures, and does not call runtime full-trace planners or unguarded external learners. | Done for current infrastructure: `scripts/run_domain_level_experiment_matrix.py` consumes JSON configs or built-in presets, writes `matrix-summary.json`, per-experiment reports, and `comparison.json`; tests cover success plus diagnostic failure rows and fail-fast behavior. Latest `paper-expanded-smoke` run produced 12 succeeded rows and 1 diagnostic failed row after adding the no-Layer-C-ordering ablation row. |
| N11 | Fix generic typed/action-cost/equality PDDL support without domain hardcoding. | G2, G5, G6 | Equality contexts execute correctly, metric-only action costs are ignored as cost updates, hyphenated symbols render safely, typed action rules cannot bind objects of the wrong PDDL type, and the diagnostic matrix reaches 5/5 succeeded rows. | Done: added generic equality support in contract/executor/transition simulation/rendering; accepted metric-only `:action-costs`, `:functions`, `:metric`, and `increase` effects while preserving collision checks; added PDDL type guard facts and action-parameter type contexts; fixed Clingo rule-id collisions for hyphenated or duplicate rule names; added trace-supported macros for type-ambiguous effect predicates only. Evidence: `uv run pytest -q` -> `249 passed, 2 warnings`; `paper-diagnostic-smoke` matrix -> `succeeded=5 failed=0`; no-hardcoding test passed. |
| N12 | Expand the matrix across all local PDDL domains and make long rows diagnostic-safe. | G6, G10, G11 | `paper-expanded-smoke` covers Blocksworld, Labworkflow, Transport, Satellite, and Marsrover; per-entry and per-problem timeouts prevent runaway rows; failures identify the next generic Layer B/C gaps. | Done for the refreshed diagnostic suite. The previous Marsrover bounded-exploration failure is now repaired through synthesis-time planner traces plus generic Layer B binding fixes: `tmp/probe-marsrover-trace-route-like-supported/marsrover-trace-train1-first10-timeout15.json` reports 10/10 with runtime planner `none` under a 15-second per-problem evaluation budget. |
| N13 | Design and implement a principled cyclic-route progress feature for same-predicate movement modules. | G2, G11 | A generic PDDL domain with cyclic route facts learns a lifted `P(entity, target)` module that reaches the target without trace replay, recursive loops, or runtime full-trace planning. | Done and extended: `test_schema_synthesizer_learns_route_progress_for_cyclic_movement` covers top-level cyclic movement, while `test_schema_synthesizer_learns_typed_carrier_delivery_chain` covers cyclic route progress inside a generated delivery subgoal. Route features are metadata-backed read-only contexts, not plan heads or body subgoals. |
| N20 | Add typed-overloaded causal-chain modules for carrier/resource delivery. | G2, G11 | Generic PDDL domains with a carrier/package `at(...)` overload and optional capacity resource solve delivery goals without runtime full-trace planning, without `capacity` causal-chain pollution, and without Blocksworld regression. | Done: schema synthesis now generates causal-chain modules only for typed-overloaded effect predicates, bridges resource variables through shared static preconditions, rejects resource causal-chain output for non-training target predicates, adds current-resource priority composer rules for already-held target objects, and executor derives route progress for current atomic subgoal targets. Evidence: resource-delivery and generic mid-state tests pass; Blocksworld first20 regression passes; focused Transport train3 first10 solves 10/10 with `at` causal-chain, current-resource priority, and no `cap_causal_chain`. |
| N14 | Rewrite the method plan around the simplified core contribution before adding more functionality. | G1, G2, G3 | The architecture contract and tests distinguish paper core method from implementation safeguards; the next implementation task can be justified by the core method, not by ad hoc failure patching. | Done for the paper-method draft: `latex_code/aamas_method_paper/main.tex` and `sections/method.tex` define the AAMAS-formatted formal algorithm, bounded-class guarantee, candidate language, selector, compiler semantics, evaluation protocol, and exclusions. Verified with `latexmk -pdf main.tex`. |
| N15 | Expand the method draft into a full evaluation-ready paper skeleton. | G1, G6, G9 | Add related work, experiment tables, ablation interpretation, final claim checklist, and result-import macros without changing the fixed core algorithm. | Done for the current paper package: `sections/evaluation.tex` now imports generated result macros into main-result, ablation, baseline, boundary, and reproducibility text. It states that Labworkflow is the current Layer C/refinement stress row and that Blocksworld no-Layer-C is not used as mechanism-necessity evidence because it remains 100% on current splits. |
| N16 | Add runtime `ready_<predicate>` agenda gates for generic `+!g` composer plans. | G3, G6 | Generic composer contexts include `ready_P(...)`; selected support agenda edges are saved in plan-library metadata; executor derives ready facts from current state plus goal descriptors; contract rejects mutable `ready_` use; Blocksworld first20 remains 20/20 and all30 failure mode is remeasured. | Done for plumbing: schema synthesis emits `goal_P(...) & ready_P(...) & not P(...)`; `runtime_goal_agenda` records selected support edges; executor evaluates derived ready contexts domain-generically using `earlier`, `later`, and `binding_contexts`; contract treats `ready_` as read-only derived context while respecting declared PDDL predicates such as `ready_a`. Evidence: `uv run pytest -q` -> `260 passed, 2 warnings`. The old all30 loop/timeout diagnosis is superseded by N18 goal-mutex diagnostics. |
| N17 | Pull Layer B and Layer C architecture back to final-paper quality. | G1, G2, G3 | Architecture report and AAMAS method text expose the exact bounded Layer B/C claims: artifact, admissible evidence, selector obligations, compiler/runtime semantics, required proof reports, and explicit not-claimed boundaries. | Done for contract alignment: `architecture_contract` now marks Layer B and Layer C complete for the declared bounded hypothesis class and keeps universal arbitrary-domain generalized planning as a non-goal. Layer C contract includes `ready_<predicate>` runtime support agenda semantics; Layer B contract requires proof records, selector reasons, and safety audits. Evidence: focused architecture tests passed after the contract update. |
| N18 | Diagnose and repair the Blocksworld all30 `p21` loop/timeout failure mode. | G3, G6 | Reproduce `p21`, explain the exact root cause, add a generic fix, and verify first20/no-hardcoding do not regress. | Done: `p21` was reproduced as `recursive loop on !g` after 236 actions, but the final missing goals revealed a contradictory goal set (`clear(b2)` with `on(b17,b2)`). Added domain-agnostic schema-level goal mutex diagnostics from symmetric PDDL add/delete effects. `p21` now fails in 0 steps with `goal mutex detected`; `p22`-`p30` are also classified as `goal_mutex`. Evidence: targeted executor tests passed, Blocksworld first20 still passed, no-hardcoding passed, all30 report has `failure_kind_counts={"goal_mutex": 10}`. |
| N19 | Create and evaluate satisfiable larger Blocksworld held-out splits. | G3, G6 | Add reproducible splits, verify they have no schema goal mutexes, wire them into the expanded matrix, and run paper-profile evaluation. | Done: `scripts/generate_blocksworld_satisfiable_split.py` generates deterministic full-tower and mixed multi-tower problems. `src/domains/blocksworld/satisfiable-large` tracks the 50-140 block full-tower split; `src/domains/blocksworld/satisfiable-mixed-large` tracks the 20-110 block mixed split with nontrivial initial towers, multiple final towers, and mixed `ontable`/`on` goals. Reports in `tmp/domain-level-experiment-matrix/blocksworld-satisfiable-large/` and `tmp/domain-level-experiment-matrix/blocksworld-satisfiable-mixed-large/` show bootstrap 10/10 and paper external 10/10 for both splits; paper external rows are `paper_profile_ready=true` with no runtime full-trace planner. |
| N21 | Build the final paper data package. | G6, G9 | Produce `tmp/paper-final/` with backend audit logs, main library reports, baseline JSON rows, ablation reports, limitation diagnostics, `comparison.json`, and generated LaTeX result macros. | Done for the current final-data protocol. Tooling: `scripts/run_final_paper_data.py` writes fixed main/ablation/limitation configs, runs backend audits, generates baselines, runs matrices, writes `comparison.json`, and emits `latex_code/aamas_method_paper/generated/results.tex`. Result macro generation now includes split-specific baseline macro identifiers, rejects duplicate macro prefixes, and converts digits to words so generated commands are valid LaTeX control sequences. The validator `uv run python scripts/run_final_paper_data.py --output-dir tmp/paper-final-latest --validate-only` passed with 26 checks. Latest regenerated package reports 10 library rows, 10 baseline rows, 20 paper-table rows, and no duplicate result macros. |
| N22 | Add or select a goal-dependency stress split for Layer C ablation. | G3, G6 | On the same split, the full method succeeds and the no-Layer-C variant either fails, times out, or emits a clear missing-composer/unsafe-composer diagnostic. | Done via Labworkflow goal-dependency stress. Full counterexample-refinement row solves `2/2`; both `no_layer_c_no_refinement_labworkflow` and `no_counterexample_refinement_labworkflow` solve `1/2` with the precise failure `no applicable plan for !reagent_logged(r1)`. This is the final Layer C/counterexample stress evidence; Blocksworld no-Layer-C remains 100% on current splits and should be described as not stressing that mechanism. |
| N23 | Generate final baseline records. | G9 | Completed baseline JSON contains at least classical per-problem planner, raw learner-sketches policy, and MOOSE or audit-only generalized-planning baseline rows with coverage and scope labels. | Done. `scripts/generate_domain_level_baselines.py` generates Fast Downward per-problem baselines validated by local STRIPS simulation, raw learner-sketches artifact-audit baselines, and MOOSE status-CSV baselines. Final baseline records preserve `comparison_scope`, `domain_level_artifact`, `coverage_semantics`, and `evidence_source`, so per-problem planner baselines are not confused with domain-level libraries. Latest final package has 10 baseline rows. |
| N24 | Decide Marsrover final treatment. | G6, G10 | Either repair Marsrover synthesis under fixed resource limits using validated trace/external evidence, or move it to a limitation-only matrix with the state-explosion diagnosis. | Repaired inside the current bounded fragment using synthesis-time trace evidence and generic Layer B fixes, not Marsrover hardcoding. Evidence: train1/eval first10 solves 10/10 under a 15-second per-problem evaluation budget, with generated lifted library runtime and no full-trace runtime planner. Keep it as a secondary trace-evidence fragment rather than a strict paper-profile main claim; bounded exploration without trace evidence remains a scalability diagnostic. |

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
uv run python scripts/run_final_paper_data.py \
  --output-dir tmp/paper-final-latest --validate-only
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
