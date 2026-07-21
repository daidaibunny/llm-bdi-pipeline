# To Do List

This tracker reflects the current atomic-template library plus temporal-goal
append architecture. Completed historical milestones have been removed.

## Current Target

The repository does not implement a universal generalized planner and does not
route whole domains by prior paper taxonomy classes. The current path is:

```text
PDDL domain + train split
-> external generalized-planning evidence
-> atomic minimal literal module synthesis
-> one maintained domain-level BDI plan library
-> AgentSpeak(L)/Jason realization used in the current implementation

validated lifted LTLf JSON
-> LTLf-to-DFA
-> conjunction/negation guard-transition validation
-> append +!g_query wrapper to the same domain library
```

Each selected domain has one maintained library under
`artifacts/domain_libraries/<domain>/`.

## Selected Benchmark Scope

The groups are evaluation coverage, not backend-routing classes. A benchmark
entry may be a planning-family entry rather than a unique PDDL dynamics file.

| Group | Domains | Split policy |
| --- | --- | --- |
| ESHO classical domains | `barman`, `ferry`, `gripper`, `logistics`, `miconic`, `rovers`, `satellite`, `transport` | MOOSE official `training/` as train and `testing/` as test. |
| Numeric fluent domains | `numeric-ferry`, `numeric-miconic`, `numeric-minecraft`, `numeric-transport` | MOOSE official `training/` as train and `testing/` as test; execution uses the declared bounded-integer fragment. |
| Feature-definable serialized-width domains | `blocksworld-clear`, `blocksworld-on`, `blocksworld-tower`, `depots` | `blocksworld-clear/on` use KR 2025 learner-policies no-constants train/test folders; `blocksworld-tower` uses `floor(1/4 * instance_count)` train; `depots` uses `floor(1/2 * instance_count)` train because the D2L source has only 22 instances. |

`8puzzle-1tile` is outside the selected benchmark scope because the current
compiler does not yet provide a graph-search or permutation-progress
certificate.

## Active Work

| Item | Status | Next step |
| --- | --- | --- |
| Full 16-domain benchmark materialization | Updated | Keep `scripts/materialize_achievement_benchmarks.py` as the single source of truth and rerun it after source-policy changes. |
| Atomic ASL library generation | Complete and compiler frozen | The independent Full GP2PL libraries for seeds 0--4 use the same declared benchmark and protocol; evidence is neither merged nor selected by best seed. |
| Jason plus VAL validation | Complete for the five-seed Full GP2PL method | The five complete 1,228-case runs obtain 1,224, 1,219, 1,187, 1,205, and 1,224 successes: 98.68% mean with 1.29 percentage-point sample standard deviation. All 6,059 successful traces pass original-goal VAL; no case times out or exits nonzero. The compact record is `paper_artifacts/gp2pl_evaluation/v1/five_seed_full_compiler_summary.json`. |
| Numeric domains | Supported bounded fragment | Positive integer equalities, constant deltas, bounded prerequisite preparation, mixed Boolean/numeric preservation, Jason execution, VAL, and DFA trace validation are implemented. Keep arbitrary arithmetic and unrestricted numeric planning outside the claim. |
| Temporal Input generation | Complete and frozen | The complete 1,228-row natural-language manifest and 475-row deduplicated worklist are sealed in the tracked TEG source archives. |
| Temporal Goal Validation | Complete and publicly versioned for translation and witness scope | The tracked release at `paper_artifacts/temporal_goal_benchmark/v1` independently reproduces 475/475 exact DFA-language equivalence and 1,228/1,228 hidden-witness acceptance. Its README, CC BY 4.0 notice, citation metadata, portable source archives, integrity verifier, and versioned public Release form the dataset publication boundary. |
| Temporal execution validation | Complete | The fixed outcome record obtains 1,228/1,228 Jason, neutral-goal VAL, gold-DFA, and predicted-DFA successes across all 16 domains and five formula profiles under 12 workers, 1,800-second Jason/VAL limits, and a 64-MiB Java stack. |
| AAAI paper package | Official AAAI-27 format and evidence-complete main-paper structure in progress | The manuscript uses the official `aaai2027.sty` and `aaai2027.bst` files without legacy font overrides. Its abstract and introduction follow a problem--gap--method--guarantee--result cadence, introduce Blocks World before symbolic notation, and defer certificate inventories to the method. Evaluation prose reports scientific aggregates, seed variation, failure concentration, causal interpretation, and claim boundaries; worker and resource details remain in the Technical Supplement, while source hashes and run identifiers are omitted from all public results. Notation separates the certified atomic module core `M_D`, per-query plan set `Q_q`, and sole maintained library version `L_D^[k]`, with append update `L_D^[k+1] = L_D^[k] union Q_q`. Figure 1 is the first-page representation bridge. Figure 2 combines the two compiler-stage overview with a concrete DFA-guided tower-query chain in its right panel. Figure 3 is the sole local Blocks World case and shows the selected atomic core executing recursively on an unseen stack. Main-paper results use compact local tables rather than an empirical dashboard figure. Per-profile, per-domain, per-seed, runtime, and cross-scope detail remains in the Technical Supplement. |
| Evaluation result order | Complete | The main paper presents paired component ablations first, full-system atomic and temporal results second, and external planning references last. Small tables appear beside the claim they support: paired atomic, paired temporal, five-seed robustness, fixed-core temporal validity, and the identical-scope Raw MOOSE evidence versus Full GP2PL contrast. A pre-conclusion float barrier keeps these tables ahead of the final section and references. |
| Manuscript prose and captions | Submission-quality audit complete; page-budget editing deferred | The abstract, introduction, foundations, related work, method, evaluation, merged Conclusion and Future Work, and technical proof/reporting text now use one conditional claim boundary. Atomic inference aggregates five seeded outcomes within held-out case identifiers before an exact sign test; temporal contrasts report discordant counts and domain/input concentration without a case-level p-value. The results state the 10.42-point atomic and 9.36-point temporal effects, the fivefold offline compile-cost tradeoff, the Balanced controller-size/fan-out tradeoff, the 720/740 versus 117/740 same-scope added-domain contrast, and the concentration of 113/115 temporal gains in four numeric domains plus two gains in Transport. Captions define denominators, validation criteria, aggregation, units, PAR-2, and scope. Three short limitation sentences retain the evidence-provider, candidate-grammar, temporal-distribution, fixed-core, and incomplete-strategy boundaries; the final generator-onboarding paragraph remains the future-work direction. The current PDFs compile cleanly; shortening to the conference page budget remains a separate final editorial pass. |
| Future-domain onboarding | Manuscript contract recorded | A pinned parameterized PDDL problem generator may create finite training instances for a compatible generalized-planning provider. Generator provenance, validation against the domain, and a content-disjoint sealed test split are mandatory. This is evidence-acquisition scalability, not an expansion of GP2PL's supported semantics or certificates. |
| Atomic experiment harness | Complete, frozen, and inserted | The paired matrix covers 24,560 outcomes. Evidence Only, Direct Producers, Maximum Feasible, and Full GP2PL obtain 5,420, 5,419, 6,059, and 6,059 valid executions of 6,140; Full preserves Maximum Feasible coverage with 34 fewer mean branches. |
| Temporal experiment harness | Complete, frozen, and inserted | The three reported variants consume the same seed-0 Full GP2PL libraries and the same benchmark, bindings, and DFAs. Unprotected, Module-Return, and Balanced obtain 1,113, 1,212, and 1,228 valid traces of 1,228; transition-repair fan-out is 3, 2, and 2. |
| External references | Complete, repaired, frozen, and scope-separated in the manuscript | The original twelve MOOSE domains use the explicitly labelled five-model coverage reported in arXiv `2511.11095v1`, Table 4; no published runtime is compared locally. The five four-domain Raw MOOSE runs obtain 26, 23, 23, 25, and 20 VAL-valid plans of 148. On the identical 740 added-domain seed--case evaluations, the main paper reports Raw MOOSE evidence at 117/740 and Full GP2PL at 720/740. The complete repaired matrix obtains 591/868 for LAMA and 253/360 for MRP+HJ; the direct temporal matrix supports 492/1,228 inputs and validates 298, with 736 explicit unsupported cases. All 2,456 external records remain frozen in `paper_artifacts/gp2pl_evaluation/v1/external_reference_results.json`; their complete multi-scope table is retained in the Technical Supplement and is not ranked across scopes. |
| Rejection and metamorphic matrix | Complete | All 13 registered certificate rejection and symbol-invariance cases pass. The outcome-only summary is released under `paper_artifacts/gp2pl_evaluation/v1`; rerun only when a certificate implementation changes. |
| Empirical diagnostic plot | Frozen but supplementary only | `scripts/generate_aaai_figures.py --ablation-results` still reproduces the former three-panel dashboard from all paired outcomes, but the main paper no longer uses it as Figure 3. Exact compact tables communicate the heterogeneous endpoint results more directly. The plot remains a reproducibility diagnostic for the Technical Supplement or artifact, while the generated paired tables use bold for tied best results and blue bold for the selected configuration; disjoint external scopes remain unranked. |

## Certified Generic Fixes

- External-reference setup now probes a working Java runtime and MONA binary,
  verifies the exact MOOSE artifact digest, and checks out pinned VAL source.
  Direct temporal validation receives the selected MONA executable explicitly;
  it no longer depends on the parent shell's `PATH`. Setup extracts the pinned
  MOOSE image into a hash-checked Apptainer sandbox, so concurrent Raw MOOSE and
  LAMA calls need neither host loop devices nor a shared `/work/out` directory.
  Each call mounts a private output directory. FOND4LTLf redirects pinned
  `ltlf2dfa` 1.0.2's fixed `automa.mona` path into a per-case workspace.
  Scientific planner failures remain resumable results, while infrastructure
  failures are retried by `--resume`. An audited merge may replace only the
  complete primary summary's exact infrastructure-failure set using a
  one-worker serial retry with unchanged inputs, tools, limits, and per-case
  provenance; hardware-equivalent runtimes remain eligible for PAR-2.
  FOND4LTLf normalization removes a
  declaration-only `:action-costs` flag when no numeric syntax exists, so
  Boolean Barman cases are not misclassified as numeric PDDL.

- Full-test validation freezes every selected domain and problem into a hashed,
  run-local PDDL input snapshot before starting Jason workers. A transiently
  absent or changing materialized source is retried for up to 15 minutes;
  workers never reread the mutable benchmark tree after the snapshot. An
  unexpected per-case infrastructure exception is persisted without aborting
  sibling cases. Internal resume bookkeeping reuses only matching-input
  successes, and the outer five-seed script reuses a MOOSE batch only when its
  complete command, settings, domain set, successful return code, and expected
  atomic ASL files match exactly. Pre-registry validated-policy-lifting manifests
  may omit the compiler variant only when adding the historical `full` default to
  both settings and command makes the invocation otherwise identical; registered
  non-default variants remain fail-closed.

- Temporal append now always calls the real `ltlf2dfa`/MONA converter. The
  removed ordered-sequence fast path can no longer bypass DFA construction.
  Every distance-reducing DFA edge produces a query-local `trans` controller.
  Its certified literal order is compiled into a balanced binary
  transition-repair tree with
  maximum trigger fan-out two, maximum plan-body length two, and logarithmic
  nesting depth. A direct linear realization would preserve the same order but
  make one plan body and its intention continuation grow with guard size. One full repair
  pass completes before `done` tests the current monitor state. A post-exit
  suffix contains only observations or already certified, prefix-preserving
  repairs; every primitive action remains DFA-observed, so rejection fails
  closed and a macro that crosses several DFA edges is not replayed against an
  obsolete intermediate target.
- Producible-target expansion now runs even when backend evidence contains only a
  numeric goal. Every PDDL positive add-effect predicate is treated as a
  producible fluent, while static predicates remain context-only. This removes
  the Numeric Minecraft coverage gap for `position/1` and `air_cell/1` without
  recognizing their names.
- Positive integer numeric equalities may use schema-certified constant-delta
  repairs: unit effects require strict monotone progress, non-unit effects
  require the exact predecessor value, and a mixed Boolean/numeric threat cycle
  may use one primitive action only when its complete net effect establishes the
  entire guard.
- Validated MOOSE macros and action-schema-derived branches now enter one Clingo
  generated certified candidate set. Evidence coverage, nonrecursive
  schema-achievement coverage, internal-call closure, compatible recursive
  capabilities, branch count, context count, and body cost are decided in one
  solve; MOOSE macros are no longer appended after schema selection.
- Query goal ordering no longer infers semantics from predicate argument
  positions. Delete threats come only from conservative summaries of the final
  selected atomic module call graph. Summaries use a PDDL-typed relational fixed
  point over alpha-normalized subgoal-call shapes, so recursive parameter changes
  are included without a domain-specific depth bound. Incomplete summaries and
  cyclic threat graphs are rejected; parser order is not a fallback.
- Negative DFA guards now require conditional completion-level `MayAdd`
  preservation and effect-certified establishment. A signed negative leaf may
  call only a query-local action-only branch whose PDDL net effect has an exact
  `MustDelete`, achieves a positive sibling, and preserves every other guard.
  Direct deleters bind otherwise-free parameters through compatible positive
  sibling add effects before range restriction.
  All 23 Barman same-state negation cases pass Jason, replay, VAL, and both DFAs
  with one action each. Negative-only edges remain context checks.
- MOOSE evidence variables are no longer made pairwise distinct by default.
  Inequality guards are emitted only when PDDL symbolic execution proves that
  aliasing would violate an action precondition or a prior delete effect.
- Atomic compilation and temporal append now enforce the supported PDDL
  fragment before synthesis. LTLf formulas with unbalanced parentheses are
  rejected rather than repaired, and VAL success requires an explicit known
  success marker instead of exit code zero alone.
- PDDL constants and schema variables now have distinct symbolic identities.
  Threat ordering therefore remains sound even when an object is literally
  named `x`, `y`, or another schema-variable-like token.
- Compiler-generated resource-release sequences require a causal keyed-capacity
  invariant, a finite non-repeating path from acquired mode back to free mode,
  target preservation, and exact alias guards. Every intermediate transition is
  symbolically replayed. Structurally symmetric same-arity modes are rejected
  when their free/debt orientation cannot be inferred.
- Schema-derived macro generation is no longer truncated after five actions.
  It performs finite backward STRIPS regression over an acyclic
  producer-precondition graph, unifies producer preconditions with compatible
  open requirements before introducing fresh variables, forbids repeated
  alpha-normalized requirement/producer roles, retains the shortest body for an
  equivalent completion contract, and symbolically replays every result. Cyclic
  targets do not trigger an unrestricted instance-level planner.
- Same-predicate recursion requires a non-negative relational-count feature
  with a strict delete and no selected reachable branch that can increase the
  feature. Anchored relation cones permit an add only when the trigger preserves
  the same anchor and an action-schema-derived guard proves that the new anchor differs.
- Cross-predicate preparation candidates are optional Clingo capabilities. The
  selected dependency edges must form a directed acyclic graph and are sealed
  with caller/callee ranks satisfying `caller_rank > callee_rank`. Relation
  threats are checked over this selected graph rather than over unused raw
  candidates; the query compiler independently rechecks the final certificates.
- Acyclic producer-precondition dependencies that traverse a schema-inferred
  single-valued fluent may use context-minimizing precondition repair: unrelated
  dynamic siblings are deferred, unique-producer static
  feasibility witnesses are retained, nested variables are alpha-renamed, and
  the complete producer context is rechecked before execution. Cyclic or
  producer-ambiguous dependencies retain the full connected context.
- Acyclic support-depth serialization is admitted only through a query-local,
  occurrence-specific preservation portfolio whose recursive preparation
  summaries preserve earlier ranked achievements. Acyclic requested relations
  without this branch-level
  noninterference certificate remain unsupported.
- Query-local preservation portfolios are selected per ordered literal
  occurrence. Repeated uses of one predicate receive distinct aliases when
  their protected prefixes require different branch sets; identical portfolios
  are shared. Certificate metadata reports recursive closure only when a
  recursive branch was actually selected. A real `blocksworld-tower`
  `instance-26` probe changed from zero-action failure to a 34-action trace that
  VAL accepts; this is probe evidence, not a full-domain result.
- Every positive DFA progress transition uses the same balanced `trans` repair
  tree. Singleton guards use identity serialization; conjunctions use certified
  threat ordering before tree construction. The old linear, sibling-replay,
  and monotonic step-helper paths are no longer selected.
- The implementation contains no domain-name routing for these rules. Synthetic
  regression domains cover constant/variable identity, alias-safe cleanup,
  persistent goals, and interfering goals.

Current compiler acceptance gate (2026-07-13): full `ruff check .` passes;
`pytest -q` reports 418 passed with only two third-party Lark deprecation
warnings; real `ltlf2dfa`/MONA builds the expected three-state, five-transition
automaton for `F(a & X(F(b)))`; and the typed threat certificate processes the
48,500-literal Gripper `p2_30` goal in about 11 seconds with one cached module
summary and zero threat edges. Representative real MOOSE readable-policy
wrappers accept Numeric Minecraft, Blocksworld Clear, Gripper, Satellite,
Rovers, and Logistics. Unsupported cyclic or ambiguous closures are rejected
rather than falling back to an uncertified order.

Diagnostic staged-precondition run (2026-07-12): the current compiler produced
Jason- and VAL-valid traces for all 90 Rovers test instances, including the two
previous regressions `p0_14` and `p0_19`. This run started from a working tree
  with tracked changes, so it is implementation evidence only. Source-state
  bookkeeping remains local and is excluded from public result records.

Fixed TEG execution result (2026-07-13): 1,228/1,228 successful executions over
all 16 domains. Every counted case has an explicit
Jason success marker, a complete primitive PDDL action trace accepted by
neutral-goal VAL, and acceptance by both gold and predicted DFAs. The five
profile totals are 273 ordered-two, 272 ordered-three, 275 strong-Until, 137
same-state conjunction, and 271 same-state-with-negation successes. The run is
published in the outcome-only evaluation release.

Temporal semantic conformance (2026-07-13): a separate versioned suite now
checks the declared finite-trace operators against both a direct recursive
semantics evaluator and real MONA-derived DFAs. It also covers initial-state
predicate and numeric-equality acceptance as zero-action singleton-state
traces. VAL 1.4 cannot parse an empty plan, so these cases record vacuous PDDL
replay legality and VAL not applicable; the non-empty 1,228-case matrix remains
unchanged. Clean commit `67b82843` passes 14/14 formula-semantics cases and 2/2
zero-action integration cases. The pinned record is
`paper_artifacts/temporal_semantic_conformance/v1/release_validation.json`.

Previously recorded focused validation evidence. Rerun these probes after the
current threat-ordering and temporal-append changes before using them as paper
results:

| Probe | Result |
| --- | --- |
| `blocksworld-tower` instances 49 and 51 | `2/2` Jason plus VAL valid; both previously timed out. |
| `rovers` official test split | `90/90` Jason plus VAL valid; restores the earlier `p0_14` and `p0_20` regressions. |
| `gripper` `p1_30` | VAL valid, 3.365 seconds and 3,999 actions. |
| `gripper` `p2_12` | VAL valid, 38.175 seconds and 85,999 actions with the balanced binary transition-repair tree; the same delta-indexed runtime took 288.508 seconds with sibling replay. |
| `blocksworld-tower` `instance-26` | Final compiler probe is Jason plus VAL valid with 34 primitive actions. |
| `depots` full test split | `7/11` Jason plus VAL valid. `p12`, `p15`, `p20`, and `p22` fail without a committed trace; every successful trace passes VAL. |
| `logistics` `p1_19` | The acyclic compiler finishes in seconds and executes a 38-action diagnostic prefix, but no complete Jason trace is committed. The cyclic location/transport dependency remains unsupported. |

The remaining Depots gap must not be patched with domain-specific parking or
transport rules. The current candidate-construction grammar now supports
arbitrary-length finite acyclic regression and multi-step resource-mode discharge. The remaining
case needs a query-local nested precondition-repair branch set when one untyped
predicate has several producers with different preservation contracts. Such a
branch set must be selected from certified branch effects, or justified by a separately
validated static role invariant; the compiler must not infer role disjointness
from predicate names.

An experimental removal of the acyclic producer-dependency gate made the real
Logistics compiler exceed its 600-second probe budget. That search was not
retained: alpha-normalized cycle blocking guarantees finiteness of signatures
but does not prevent combinatorial enumeration. A future cyclic extension needs
an evidence-guided mode-path or lexicographic progress certificate, not an
unrestricted schema search.

## Commands

Regenerate the selected benchmark corpus:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/materialize_achievement_benchmarks.py
```

Run the full benchmark ASL batch with the current default domain list:

```bash
PYTHONDONTWRITEBYTECODE=1 \
RUN_ID=pddl-five-seed-$(date +%Y%m%d-%H%M%S) \
MOOSE_SEEDS="0 1 2 3 4" \
MOOSE_WORKERS=1 \
MOOSE_SEED_PARALLELISM=5 \
JASON_WORKERS=6 \
TRAIN_TIMEOUT_SECONDS=43200 \
JASON_TIMEOUT_SECONDS=1800 \
VAL_TIMEOUT_SECONDS=1800 \
JASON_JAVA_STACK_SIZE=64m \
bash scripts/run_parser_order_full_val_batch.sh
```

Run focused checks after benchmark, compiler, or paper-scope edits:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run ruff check \
  scripts/materialize_achievement_benchmarks.py \
  scripts/run_moose_faithful_e2e.py \
  tests/test_moose_faithful_e2e_script.py \
  tests/test_main_temporal_artifact_cli.py \
  tests/domain_level_planning/test_no_domain_hardcoding.py \
  tests/domain_level_planning/test_atomic_module_synthesis.py \
  tests/domain_level_planning/test_evidence_module.py \
  tests/domain_level_planning/test_dfa_goal_adapter.py

PYTHONDONTWRITEBYTECODE=1 uv run pytest -q \
  tests/test_moose_faithful_e2e_script.py \
  tests/test_main_temporal_artifact_cli.py \
  tests/domain_level_planning/test_no_domain_hardcoding.py \
  tests/domain_level_planning/test_atomic_module_synthesis.py \
  tests/domain_level_planning/test_evidence_module.py \
  tests/domain_level_planning/test_dfa_goal_adapter.py
```

Validate frozen lifted LTLf predictions and optionally matching execution
traces named `<sample_id>.plan`:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python \
  scripts/validate_temporal_goal_predictions.py \
  --handoff-root artifacts/temporal_nl_handoffs/temporal-nl-v1-20260711-final \
  --benchmark-root artifacts/temporal_nl_benchmarks/temporal-nl-v1-20260711-final \
  --predictions-file artifacts/temporal_predictions/translation_predictions.jsonl \
  --output-dir artifacts/temporal_goal_validation/<run-id>
```
