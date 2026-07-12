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
-> one maintained domain-level AgentSpeak(L) library

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
| Numeric fluent domains | `numeric-ferry`, `numeric-miconic`, `numeric-minecraft`, `numeric-transport` | MOOSE official `training/` as train and `testing/` as test; ASL compilation remains experimental. |
| Feature-definable serialized-width domains | `blocksworld-clear`, `blocksworld-on`, `blocksworld-tower`, `depots` | `blocksworld-clear/on` use KR 2025 learner-policies no-constants train/test folders; `blocksworld-tower` uses `floor(1/4 * instance_count)` train; `depots` uses `floor(1/2 * instance_count)` train because the D2L source has only 22 instances. |

`8puzzle-1tile` is outside the selected benchmark scope because the current
compiler does not yet provide a graph-search or permutation-progress
certificate.

## Active Work

| Item | Status | Next step |
| --- | --- | --- |
| Full 16-domain benchmark materialization | Updated | Keep `scripts/materialize_achievement_benchmarks.py` as the single source of truth and rerun it after source-policy changes. |
| Atomic ASL library generation | Needs full rerun | Run the timestamped MOOSE-to-ASL batch for all 16 selected benchmark entries after this benchmark expansion. |
| Jason plus VAL validation | Needs full rerun | Run full-test DFA-transition validation after the new ASL batch completes. Report per-domain Jason and VAL success, timeout, and failure categories. |
| Numeric domains | Experimental | Keep numeric support marked experimental until numeric fluents have a complete executable semantics and full validation evidence. |
| Temporal Input generation | Ready for model run | The complete 1,228-row natural-language manifest and 475-row deduplicated worklist are frozen. The colleague runs only the 475 Prompt-2 translations and returns canonical `translation_predictions.jsonl`. |
| Temporal Goal Validation | Implemented; pending model artifact | Run `scripts/validate_temporal_goal_predictions.py` after predictions arrive. The batch checks the eight-key contract, exact gold/predicted DFA equivalence, all hidden witnesses, optional Jason traces with neutral-goal VAL, and gold-DFA acceptance. |
| AAAI paper package | Narrative aligned; final matrix pending | Maintain the section responsibilities, claim boundaries, result-insertion contract, and page budget in `docs/aaai_paper_narrative_outline.md`. The manuscript uses the latest available official AAAI-26 author kit and states only implemented claims. Regenerate the final atomic and TEG matrices from one clean pinned revision before submission. |

## Certified Generic Fixes

- Temporal append now always calls the real `ltlf2dfa`/MONA converter. The
  removed ordered-sequence fast path can no longer bypass DFA construction.
  Every progress edge on the unique accepting path produces exactly one
  query-local `trans` controller. Its certified literal order is compiled into
  a balanced repair tree with maximum trigger fan-out two and logarithmic
  nesting depth; singleton guards retain one atomic achievement call, while
  conjunctive guards are checked together after each complete tree pass.
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
  preservation. Unsafe universal modules are replaced only when a query-local
  action-only branch selection both achieves each positive literal and preserves
  all positive siblings and forbidden negative atoms; otherwise compilation
  fails with `negative_guard_not_preserved`. Negative-only edges remain context
  checks and do not invent negative achievement goals.
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
  invariant, inverse acquire/release effects, target preservation, and exact
  alias guards. Structurally symmetric same-arity modes are rejected when their
  free/debt orientation cannot be inferred.
- Same-predicate recursion requires a non-negative relational-count feature
  with a strict delete and no selected branch that can increase the feature.
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
- Every positive DFA progress transition uses the same balanced `trans` repair
  tree. Singleton guards use identity serialization; conjunctions use certified
  threat ordering before tree construction. The old linear, sibling-replay,
  and monotonic step-helper paths are no longer selected.
- The implementation contains no domain-name routing for these rules. Synthetic
  regression domains cover constant/variable identity, alias-safe cleanup,
  persistent goals, and interfering goals.

Current compiler acceptance gate (2026-07-12): full `ruff check .` passes;
`pytest -q` reports 340 passed with only two third-party Lark deprecation
warnings; real `ltlf2dfa`/MONA builds the expected three-state, five-transition
automaton for `F(a & X(F(b)))`; and the typed threat certificate processes the
48,500-literal Gripper `p2_30` goal in about 11 seconds with one cached module
summary and zero threat edges. Representative real MOOSE readable-policy
wrappers accept Numeric Minecraft, Blocksworld Clear, Gripper, Satellite,
Rovers, and Logistics. Depots, Barman, and Blocksworld Tower remain explicit
cyclic-threat rejections rather than falling back to an uncertified order.

Diagnostic staged-precondition run (2026-07-12): the current compiler produced
Jason- and VAL-valid traces for all 90 Rovers test instances, including the two
previous regressions `p0_14` and `p0_19`. This run started from a working tree
with tracked changes, so it is implementation evidence only; regenerate the
final paper matrix from the committed clean revision. The current full-test
runner records the source commit and separates tracked modifications from
untracked files in `summary.json`.

Previously recorded focused validation evidence. Rerun these probes after the
current threat-ordering and temporal-append changes before using them as paper
results:

| Probe | Result |
| --- | --- |
| `blocksworld-tower` instances 49 and 51 | `2/2` Jason plus VAL valid; both previously timed out. |
| `rovers` official test split | `90/90` Jason plus VAL valid; restores the earlier `p0_14` and `p0_20` regressions. |
| `gripper` `p1_30` | VAL valid, 3.365 seconds and 3,999 actions. |
| `gripper` `p2_12` | VAL valid, 38.175 seconds and 85,999 actions with the balanced tree; the same delta-indexed runtime took 288.508 seconds with sibling replay. |
| `depots` `p12` and `p20` | Invalid self-drop removed, but full goals still fail because the evidence/compiler lacks a certified cross-location transport continuation. |

The remaining Depots gap must not be patched with domain-specific parking or
transport rules. A future implementation requires a bounded, evidence-backed
schema-composition certificate; an unrestricted schema-regression planner would
violate the repository scope and could regress already valid atomic modules.

## Commands

Regenerate the selected benchmark corpus:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/materialize_achievement_benchmarks.py
```

Run the full benchmark ASL batch with the current default domain list:

```bash
PYTHONDONTWRITEBYTECODE=1 WORKERS=16 JASON_JAVA_STACK_SIZE=64m \
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
