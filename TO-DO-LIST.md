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
| Atomic ASL library generation | Needs five-seed full rerun | Run all 16 entries for fixed seeds 0--4 with one internal MOOSE worker. Seed processes may run concurrently in isolated output roots; never merge evidence or select a best seed. |
| Jason plus VAL validation | Needs five-seed full rerun | Validate each seed's ASL independently. Run seed repetitions sequentially with six per-test workers, then report every seed plus mean and sample standard deviation by domain. |
| Numeric domains | Supported bounded fragment | Positive integer equalities, constant deltas, bounded prerequisite preparation, mixed Boolean/numeric preservation, Jason execution, VAL, and DFA trace validation are implemented. Keep arbitrary arithmetic and unrestricted numeric planning outside the claim. |
| Temporal Input generation | Complete and frozen | The complete 1,228-row natural-language manifest and 475-row deduplicated worklist are sealed in the tracked TEG source archives. |
| Temporal Goal Validation | Complete and publicly versioned for translation and witness scope | The tracked release at `paper_artifacts/temporal_goal_benchmark/v1` independently reproduces 475/475 exact DFA-language equivalence and 1,228/1,228 hidden-witness acceptance. Its README, CC BY 4.0 notice, citation metadata, portable source archives, integrity verifier, and versioned public Release form the dataset publication boundary. |
| Temporal execution validation | Complete on pinned revision | `teg-paper-clean-e28bcea4` obtains 1,228/1,228 Jason, neutral-goal VAL, gold-DFA, and predicted-DFA successes across all 16 domains and five formula profiles. The run records commit `e28bcea4`, no tracked changes, every atomic-library input hash, 12 workers, 1,800-second Jason/VAL limits, and a 64-MiB Java stack. |
| AAAI paper package | Theoretical framework, source-verified citation audit, supplement, and all-yes claim-scoped checklist complete; paired results pending | The manuscript presents GP2PL as a certificate-carrying representation-compilation framework and AgentSpeak(L)/Jason as its evaluated realization. External definitions, prior methods, software, benchmark provenance, prompt programming, and natural-language specification claims carry sentence-local primary citations; GP2PL claims use internal propositions, tables, appendices, and released artifacts. The standalone technical supplement contains formal assumptions, complete proofs, a theory-to-code map, the paper-facing frozen natural-language-to-LTLf prompt, the novel-data appendix, source provenance, parameters, environment, distributions, and Checklist evidence. The checklist now records complete authored-code and novel-data publication; its statistical `yes` means the paper makes no untested inferential comparison. The anonymous PDF keeps the named public repository disabled. The registered five-seed compiler, temporal-ablation, and external-reference matrices still must complete before comparative or significance claims are inserted. |
| Atomic experiment harness | Native paired runner complete | Evidence Only, Action Closure, Maximal Certified, and Full GP2PL consume byte-identical model/readable-policy evidence per seed; incomplete artifacts and matrices are rejected. Run the registered five-seed matrix before filling result cells. |
| Temporal experiment harness | Native paired runner complete | Unprotected DFA, Certified Flat, Certified Balanced, and Completion Monitor consume the same-run seed-0 Full GP2PL libraries, fixed benchmark, sample set, and DFA matrix. Run the registered matrix before filling result cells. |
| External references | Portable runtime fixes complete; full matrices pending | Raw MOOSE, LAMA, ENHSP MRP+HJ, and FOND4LTLf plus LAMA use pinned native tools, common resource guards, concise per-case logs, and independent validation. Setup now rejects a macOS Java launcher without a JDK, passes the pinned MONA executable into internal DFA validation, pins VAL, and serializes the non-reentrant MOOSE-hosted LAMA runtime across processes. Rerun the registered full matrices from new output roots before filling paper cells. |
| Rejection and metamorphic matrix | Complete on clean revision | All 13 registered certificate rejection and symbol-invariance cases pass on clean commit `46c5af1e`. The portable summary is released under `paper_artifacts/gp2pl_evaluation/v1`; rerun only when a certificate implementation changes. |
| Main empirical figure | Generator complete; final data pending | `scripts/generate_aaai_figures.py` renders the two-figure paper's empirical Figure 2 from one complete `paired_results.json`. It rejects dirty, incomplete, or unpaired matrices and writes no release PDF until the registered five-seed atomic and four-variant temporal matrix is complete. |

## Certified Generic Fixes

- External-reference setup now probes a working Java runtime and MONA binary,
  verifies the exact MOOSE artifact digest, and checks out pinned VAL source.
  Direct temporal validation receives the selected MONA executable explicitly;
  it no longer depends on the parent shell's `PATH`. MOOSE-hosted Raw MOOSE and
  LAMA calls share one host-wide lock because the exact nested Apptainer runtime
  uses global loop devices and a shared `/work/out` directory. Scientific
  planner failures remain resumable results, while infrastructure failures are
  retried by `--resume`.

- Full-test validation freezes every selected domain and problem into a hashed,
  run-local PDDL input snapshot before starting Jason workers. A transiently
  absent or changing materialized source is retried for up to 15 minutes;
  workers never reread the mutable benchmark tree after the snapshot. An
  unexpected per-case infrastructure exception is persisted without aborting
  sibling cases. Repeating the same run identifier reuses only exact-fingerprint
  successes, and the outer five-seed script reuses a MOOSE batch only when its
  complete command, settings, domain set, successful return code, and expected
  atomic ASL files match exactly. Pre-registry validated-policy-lifting manifests
  may omit the compiler variant only when adding the historical `full` default to
  both settings and command makes the invocation otherwise identical; registered
  non-default variants remain fail-closed.

- Temporal append now always calls the real `ltlf2dfa`/MONA converter. The
  removed ordered-sequence fast path can no longer bypass DFA construction.
  Every distance-reducing DFA edge produces a query-local `trans` controller.
  Its certified literal order is compiled into a balanced repair tree with
  maximum trigger fan-out two and logarithmic nesting depth. Completion means
  the primitive-step monitor left the controller's source state, so an atomic
  macro that crosses several DFA edges is not replayed against an obsolete
  intermediate target.
- Atomic schema closure now runs even when backend evidence contains only a
  numeric goal. Every PDDL positive add-effect predicate is treated as a
  producible fluent, while static predicates remain context-only. This removes
  the Numeric Minecraft coverage gap for `position/1` and `air_cell/1` without
  recognizing their names.
- Positive integer numeric equalities may use schema-certified constant-delta
  repairs: unit effects require strict monotone progress, non-unit effects
  require the exact predecessor value, and a mixed Boolean/numeric threat cycle
  may use one primitive action only when its complete net effect establishes the
  entire guard.
- Validated MOOSE macros and PDDL-schema branches now enter one Clingo candidate
  space. Evidence coverage, internal-module closure, compatible recursive
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
  the same anchor and a schema-derived guard proves that the new anchor differs.
- Cross-predicate preparation candidates are optional Clingo capabilities. The
  selected dependency edges must form a directed acyclic graph and are sealed
  with caller/callee ranks satisfying `caller_rank > callee_rank`. Relation
  threats are checked over this selected graph rather than over unused raw
  candidates; the query compiler independently rechecks the final certificates.
- Acyclic producer-precondition dependencies that traverse a schema-inferred
  single-valued fluent may use existential context projection: unrelated
  dynamic siblings are deferred, unique-producer static
  feasibility witnesses are retained, nested variables are alpha-renamed, and
  the complete producer context is rechecked before execution. Cyclic or
  producer-ambiguous dependencies retain the full connected context.
- Candidate support-depth ordering is enforced only through a query-local
  branch portfolio whose recursive preparation summaries preserve earlier
  ranked achievements. Acyclic requested relations without this branch-level
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
with tracked changes, so it is implementation evidence only; regenerate the
final paper matrix from the committed clean revision. The current full-test
runner records the source commit and separates tracked modifications from
untracked files in `summary.json`.

Pinned TEG execution run (2026-07-13): commit `e28bcea4` produced 1,228/1,228
successful executions over all 16 domains. Every counted case has an explicit
Jason success marker, a complete primitive PDDL action trace accepted by
neutral-goal VAL, and acceptance by both gold and predicted DFAs. The five
profile totals are 273 ordered-two, 272 ordered-three, 275 strong-Until, 137
same-state conjunction, and 271 same-state-with-negation successes. The run is
stored at `artifacts/temporal_goal_execution_runs/teg-paper-clean-e28bcea4`.

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
| `gripper` `p2_12` | VAL valid, 38.175 seconds and 85,999 actions with the balanced tree; the same delta-indexed runtime took 288.508 seconds with sibling replay. |
| `blocksworld-tower` `instance-26` | Final compiler probe is Jason plus VAL valid with 34 primitive actions. |
| `depots` full test split | `7/11` Jason plus VAL valid. `p12`, `p15`, `p20`, and `p22` fail without a committed trace; every successful trace passes VAL. |
| `logistics` `p1_19` | The acyclic compiler finishes in seconds and executes a 38-action diagnostic prefix, but no complete Jason trace is committed. The cyclic location/transport dependency remains unsupported. |

The remaining Depots gap must not be patched with domain-specific parking or
transport rules. The current schema language now supports arbitrary-length
finite acyclic regression and multi-step resource-mode discharge. The remaining
case needs a query-local nested branch portfolio when one untyped predicate has
several producers with different preservation contracts. Such a portfolio must
be selected from certified branch effects, or justified by a separately
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
