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
→ external generalized-planning learner / traces / sketches
→ feature binding
→ Layer B atomic goal modules
→ Layer C goal dependency composer
→ lifted AgentSpeak(L) domain-level plan library
→ held-out validation
→ counterexample-guided refinement
→ future DFA controller for temporal extended goals
```

## Current Implemented Baseline

| Area | Current state |
| --- | --- |
| PDDL-only direction | HTN/HDDL paths are no longer the active architecture. Current benchmarks and synthesis path are PDDL-based. |
| DFA role | DFA is preserved as the future temporal-goal controller. It should call the domain-level achievement-goal library, not replace it. |
| Domain-level ASL synthesis | Unified synthesis exists: schema candidates, external sketch candidates, Clingo selection, bounded validation, counterexample inputs, ASL compilation, and report generation. |
| Layer B | Atomic modules are generated from PDDL add effects, trace evidence, repair evidence, and external sketch candidates. Reports include trace justification, strategy groups, strategy portfolios, recursion-descent audits, and selected/output manifests. |
| Layer C | Composer rules are generated from schema causal support, delete-threat interactions, trace ordering, state coverage, and counterexample ordering. Reports include a goal-agenda graph with support edges, delete-threat edges, selected support acyclicity, and binding-context depth. |
| ASL contract | Generated plans are lifted, use PDDL predicate goal heads or `+!g`, use PDDL primitive actions/subgoals only, enforce variable-binding safety, and treat context literals as order-independent conjunction with negation-as-absence. |
| Paper-profile gates | Strict profile rejects missing external learned policies, uncompiled learned rules, unselected external sketches, unjustified schema action modules, bounded-validation failures, and cyclic selected Layer C support agendas. |
| Experiments | Generic PDDL experiment runner, Blocksworld first-20 runner, Labworkflow dependency runner, and completed-report comparison CLI exist. |
| Resource safety | External learner commands must use `scripts/resource_guard.py`; keep memory at or below 16 GiB unless explicitly approved. |
| No hardcoding | Tests scan production domain-level code for domain-specific special cases and generated synthetic/grounded names. |
| External policy adapters | External learned policies may use an explicit source-local predicate vocabulary JSON adapter. Adapter targets are validated against the active PDDL domain; undeclared mappings are rejected instead of guessed. |
| Feature binding | Action-effect candidates now include both add and delete effects and promote unique candidates per qualitative operator. Ambiguous candidates remain unpromoted instead of guessed. |

Latest known Blocksworld smoke result:

```text
script: uv run python scripts/run_blocksworld_first20_experiment.py \
  --train-count 1 --eval-count 20
coverage: 20/20
profile: bootstrap_schema_only
runtime planner: none
paper-profile ready: false, because no external learned sketch policy is selected
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

## Open Gaps

| ID | Layer | Current gap | What good looks like | Priority |
| --- | --- | --- | --- | --- |
| G1 | Theory | Bounded-class guarantee exists as machine-readable reports, but not yet as final paper prose. | A paper-ready method section defines the feature language, module language, composer language, correctness scope, validation scope, and exclusions. | High |
| G2 | Layer B | Atomic modules still rely on schema/trace heuristics plus reports, not a full learned multi-strategy module learner. | The learner can justify each selected atomic module from traces, external sketches, or repairs, and can reject unsafe alternatives beyond simple cost/coverage rules. | High |
| G3 | Layer C | Goal dependency handling is much stronger, but still not a complete learned composer. | Goal-agenda and composer synthesis handle goal-dependent domains robustly, with acyclic support agendas, explainable delete-threat diagnostics, and counterexample-driven new composer candidates. | High |
| G4 | External learners | learner-sketches Blocksworld `blocks_4_on_2` now passes strict paper-profile synthesis and 20/20 Blocksworld first-20 evaluation using an existing official policy artifact. Wider learner-sketches policies may still include unsafe aggregate rules that are rejected precisely. | A guarded learner-sketches run produces a policy artifact that is parsed, bound, selected, validated, and included in a paper-profile experiment. | High |
| G5 | Feature binding | Safe DLPlan bindings now support explicit vocabulary adapters, add/delete action-effect candidates, producer-precondition variable bridges, and rule-level no-goal-progress rejection. Remaining gap is broader lifted binding for richer DLPlan expressions such as object-specific/distance features. | Every external feature either compiles to PDDL literals/actions/subgoals or has a precise rejection reason; additional principled lifted bindings are added only when justified. | Medium |
| G6 | Validation | Current validation is smoke/bounded, not yet a broad paper experiment suite. | Multiple IPC-style domains, train/test scaling, ablations, external baselines, failure analysis, and reproducible tables. | High |
| G7 | Counterexample refinement | Refinement loop exists, but not every failure class generates new executable candidates. | Held-out failures improve coverage through generated Layer B/Layer C candidates whenever the failure is inside the supported class; unsupported cases are reported precisely. | Medium |
| G8 | Temporal extended goals | DFA-to-library interface exists for positive conjunctive guards, but broader TEG evaluation is pending. | Query-specific DFA controller calls the same domain-level library and reports guard diagnostics without generating query-specific ASL libraries. | Medium |
| G9 | Paper comparison | MOOSE and other generalized-planning systems have been studied, but current ASL pipeline lacks final comparative tables. | Completed baseline metadata and/or reproduced baseline runs are compared against the lifted ASL library under a clear protocol. | Medium |

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
| N9 | Keep no-hardcoding and generated-output audits current after every synthesis change. | G2, G3, G8 | `uv run pytest tests/domain_level_planning/test_no_domain_hardcoding.py -q` and relevant generated-output tests pass. | Ongoing |

## Commands To Use

Core checks:

```bash
uv run pytest -q
uv run pytest tests/domain_level_planning/test_no_domain_hardcoding.py -q
uv run python scripts/run_blocksworld_first20_experiment.py \
  --output tmp/blocksworld-first20-experiment/report.json \
  --train-count 1 --eval-count 20
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
