# To Do List

This tracker reflects the 2026-07-03 pivot. Keep it focused on the current
atomic-template library plus temporal-goal append architecture.

## Current Target

We do not build a universal generalized planner and do not route domains by
prior paper taxonomy classes. The project now has two layers:

```text
PDDL domain + train split
-> atomic predicate/literal template backend
-> domain-level lifted AgentSpeak(L) atomic library

validated lifted LTLf JSON
-> LTLf-to-DFA
-> singleton-literal DFA validator
-> append +!g_query temporal wrapper to the same domain library
```

There is one maintained ASL library per domain. New user queries append new
top-level goals to that domain library.

## Selected Six-Domain Scope

The domain groups are for evaluation coverage only, not for backend routing.

| Group | Domains | Current rationale |
| --- | --- | --- |
| Singleton regression-friendly classical goals | `ferry`, `miconic` | MOOSE paper domains; strong fit for singleton-goal regression templates. |
| Multi-object classical achievement goals | `gripper`, `logistics` | Tests whether atomic templates compose over many objects without grounding. |
| Structural or temporalized achievement goals | `blocks`, `8puzzle-1tile` | Tests Blocks-style goal interaction and compact rearrangement families. |

Numeric MOOSE domains remain out of scope until numeric fluents have a safe ASL
literal semantics.

## Active Requirements

| ID | Requirement | Status | Evidence / Next Step |
| --- | --- | --- | --- |
| A1 | Replace class-based backend routing and old in-repo generalized-planning synthesis on the main path with atomic template backend selection. | Implemented | `src/domain_level_planning/atomic_backend_selector.py` selects from training goal templates, not benchmark class ids. Old schema synthesis, conjunctive-goal ordering/refinement, experiment matrix runner, Fast Downward transition planning, and language-model Input helpers have been removed from public code. Registry rows use goal-property groups only for evaluation coverage. |
| A2 | Use MOOSE as the first positive singleton-goal backend candidate. | Implemented for artifact path | Selector chooses MOOSE first when present. `src/domain_level_planning/moose_policy_adapter.py` parses official `policy --dump-policy` readable artifacts into `LiftedPolicyProgram` and lifted ASL atomic plans. `scripts/gp_backend_audit.py moose-atomic-command` prints a guarded train+dump command, and `moose-readable-compile-asl` materializes `plan_library.json`, `plan_library.asl`, and metadata from the readable artifact. Next: run selected-domain MOOSE smoke jobs only under an explicit runtime budget. |
| A3 | Do not claim negative literal template support without evidence. | Implemented at selector and progress-boundary | Negative training goal items return `negative_literal_template_not_supported`. Negative DFA waiting guards are allowed as automaton structure; negative progress literals still fail unless a backend later supplies a validated negative atomic template. |
| A4 | Add singleton-literal DFA validation for the Input handoff. | Implemented with restored request diagnostics | `validate_singleton_literal_dfa` rejects conjunctive/disjunctive guards, undeclared predicates, wrong arities, malformed transition records, and optionally unsupported negative literals. `src/domain_level_planning/dfa_adapter.py` restores the last-generation guard-to-achievement-request diagnostics for Input/validator feedback. Temporal appending allows negative waiting guards but rejects negative progress literals. Next: wire logger events around LTLf-to-DFA execution failures. |
| A5 | Append query-specific temporal goals to a domain ASL library. | Implemented as context-driven prefix wrapper | `append_temporal_goal_to_library` appends `+!g_query` plans for positive progress literals. The wrapper follows the historical context-driven style: already satisfied DFA prefix literals identify the current progress context, the next positive transition literal is called as an atomic PDDL subgoal, and the wrapper recurses to the same query goal. Accepting plans terminate when the full accepted prefix context holds. Append metadata records DFA progress request diagnostics, while the ASL body still calls atomic PDDL predicate subgoals directly rather than `goal_*` descriptors. |
| A6 | Restore/refactor historical logger into the new pipeline. | Implemented first pass | `src/execution_logging/execution_logger.py` restores structured JSON, human log, and payload externalization without HTN/HDDL imports. Tests: `tests/evaluation/test_execution_logger.py`. |
| A7 | Restore/refactor historical LTLf JSON schema and prompts only as Input interface references. | Implemented at handoff boundary | `src/domain_level_planning/lifted_ltlf_goal_schema.py` parses lifted LTLf JSON with atoms and bindings. Historical prompt generation stays outside this repository because the Input component is owned separately. |
| A8 | Remove stale 12-family routing language and old self-synthesis implementation from current path, tests, registry, and paper text. | Implemented | `scripts/materialize_achievement_benchmarks.py`, `src/benchmark_registry/achievement_goals`, `paper_artifacts/domain_support_taxonomy.json`, focused tests, and backend consumption roles now use six selected domains and goal-property groups. Historical schema-derived synthesis, sketch-to-`+!g` compilation, planner-trace transition modules, and old Layer C execution paths are no longer retained in `src`. The only restored DFA-era code is the guard adapter/controller diagnostic interface, which maps DFA guards to atomic achievement requests and does not generate low-level plans. |
| A9 | Materialize the six selected domains with deterministic splits. | Implemented | `uv run python scripts/materialize_achievement_benchmarks.py` rebuilt `src/domains` with `ferry`, `miconic`, `gripper`, `logistics`, `blocks`, and `8puzzle-1tile`; each uses `floor(2/3 * N)` train and remaining test. |
| A10 | Preserve current PDDL-only and no synthetic achievement-name constraints. | Implemented for generated current artifacts | New atomic and temporal append code emits no `achieve_*`, `transition_*`, or `dfa_state` names. It appends `g_query` names by design as query-specific top-level temporal wrappers. |
| A11 | Maintain exactly one appendable domain ASL library per domain. | Implemented and regression-tested | The main CLI now resolves every maintained library to `artifacts/domain_libraries/<domain>/plan_library.{json,asl}` by default. `--library-root` can relocate the root for tests, but the domain subdirectory is canonical. `--output-root` is deprecated and must equal the canonical domain directory if provided. Append rejects non-canonical `--plan-library-file` paths, preserves `temporal_goal_append_history`, and rejects duplicate temporal goal names with `duplicate_temporal_goal`. Regression tests cover sequential append into the same file plus rejection of non-canonical output/input paths. |
| A12 | Replace raw MOOSE macro dump with compact recursive atomic minimal literal modules when claiming final domain-level ASL quality. | Implemented with Clingo branch selection and type-aware binding guards | `src/domain_level_planning/atomic_module_synthesis.py` uses MOOSE singleton predicates as seed-goal evidence, then synthesizes compact recursive modules from PDDL action schemas for every predicate that appears in a positive action effect. Static predicates are detected schema-theoretically by absence from add/delete effects and remain context-only. The synthesizer performs schema-level STRIPS feasibility checks, typed action-argument compatibility, typed functional fluent conflict pruning, and type-aware binding observability checks before candidate generation. Final branch selection is Clingo/ASP-backed obligation coverage with lexicographic minimization over selected branch count, context literal count, and body step count. PDDL typing is internal only; final ASL must not emit `type_*` fluents. Because final ASL has no synthetic type guards, branches that narrow a visible variable from a broad predicate type to an unobservable subtype are rejected. This fixes Logistics-style bad bindings such as treating a package variable as a truck, but it also means Logistics currently keeps only safe `already_true` modules unless a future mechanism exposes package/truck/airplane roles through PDDL fluents or a safe type semantics. |
| A13 | Keep the temporal append path compatible with the new compact atomic library. | Implemented six-domain smoke | For `ferry`, `miconic`, `gripper`, `logistics`, `blocks`, and `8puzzle-1tile`, the pipeline compiled one MOOSE-trained readable policy into the canonical `artifacts/domain_libraries/<domain>/plan_library.asl`, then appended one LTLf query wrapper into the same file. Audit: `tmp/domain_canonical_smoke_subset/final_asl_audit.json`. The wrapper remains query-specific and calls atomic PDDL predicate subgoals directly. |
| A14 | Restore Jason support as a real PDDL environment validation gate for current ASL libraries. | Implemented with indexed/static-belief runtime | `src/evaluation/jason_runtime/runner.py` restores the historical Jason marker protocol and real Java `Environment` execution, refactored to the current PDDL-only architecture. It resolves Jason from Maven Central, materializes `agentspeak_generated.asl`, `jason_runner.mas2j`, `JasonPipelineEnvironment.java`, and `JasonPipelineIndexedBeliefBase.java`, checks PDDL action preconditions/effects against the complete world state, and exposes `src/main.py validate-jason-plan-library`. The runtime now splits PDDL seed facts schema-theoretically: dynamic action-effect predicates are Jason percepts, while static predicates are loaded as indexed read-only beliefs. This aligns validation with MOOSE's database-style rule instantiation and avoids Jason percept/matching blowups on dense static facts. |

## Current Evidence Snapshot

| Check | Result |
| --- | --- |
| Focused Python suites | `37 passed` with `PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/evaluation/test_jason_runtime.py tests/test_full_test_jason_validation_script.py tests/domain_level_planning/test_temporal_goal_appender.py tests/plan_library/test_validation.py -q`. |
| Ruff check | `uv run ruff check ...` passes on the current touched source, scripts, and tests. `ruff==0.15.20` is installed in the dev dependency group. |
| Final artifact validation | `checks=26` with `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_final_paper_data.py --output-dir tmp/paper-final-latest --validate-only`. |
| Atomic selector tests | Included in full suite; selector only chooses MOOSE as implemented atomic ASL compiler and refuses unverified fallback compilers. |
| Type-aware atomic binding smoke | `tmp/post-moose-recursive-atomic-type-aware-20260705-022159/domain_libraries` contains regenerated atomic-only libraries. Logistics now emits only safe `+!at` and `+!in` already-true modules, avoiding invalid `load_truck(X,X,...)`, `drive_truck(X,...)`, and `fly_airplane(X,...)` branches under the no-`type_*` final ASL contract. |
| Temporal appender tests | Included in full suite; validates lifted atom restoration, singleton transition guards, negative waiting guards, and negative progress rejection. |
| Lifted LTLf schema tests | Included in full suite; validates lifted atom/binding JSON handoff. |
| Logger tests | `2 passed` with `uv run pytest tests/evaluation/test_execution_logger.py`. |
| DFA adapter/controller/appender tests | `30 passed` with `PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q tests/domain_level_planning/test_dfa_goal_adapter.py tests/domain_level_planning/test_dfa_controller.py tests/domain_level_planning/test_temporal_goal_appender.py tests/domain_level_planning/test_moose_policy_adapter.py`. |
| MOOSE readable policy adapter tests | Included in DFA/MOOSE focused suite; verifies readable-policy parsing, ASL compilation, CLI materialization, and quality metadata. |
| MOOSE readable artifact smoke | `uv run python scripts/gp_backend_audit.py moose-readable-summary --policy-file .external/moose/exact-runs/ferry-seed0.model.readable --domain-name ferry` reports `rules=5`, `modules=5`, `asl_plans=5`. |
| MOOSE atomic ASL artifact smoke | `uv run python scripts/gp_backend_audit.py moose-readable-compile-asl --policy-file .external/moose/exact-runs/ferry-seed0.model.readable --domain-name ferry --output-dir tmp/moose-atomic/ferry-library` writes a domain-level atomic `plan_library.json` and `plan_library.asl`. |
| MOOSE Blocks raw atomic-plus-temporal smoke | Guarded MOOSE Blocks probe first4 training under `16GiB/900s` learned `72` singleton rules and compiled `72` raw MOOSE atomic ASL plans. Appending the first two probe instances as LTLf tower goals produced one maintained context-driven temporal library with `83` plans and no `teg_state` or `dfa_state` beliefs. Snapshots are under `snapshots/moose_blocks_e2e/`. This remains backend evidence, not final compact library quality. |
| Post-MOOSE Blocks recursive module smoke | `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/gp_backend_audit.py moose-readable-compile-asl --policy-file tmp/moose-blocks-e2e/blocks-probe-first4.model.readable --domain-file src/domains/blocks/domain.pddl --domain-name blocks --post-moose-recursive --output-dir snapshots/moose_blocks_minimal_modules` writes compact lifted recursive modules over all producible Blocks fluents seeded from MOOSE singleton evidence. Current Blocks unit smoke emits 23 plans covering `on`, `clear`, `holding`, `handempty`, and `ontable`; this replaces the older 8-plan partial-coverage snapshot. |
| Compact Blocks atomic-plus-temporal smoke | The snapshot in `snapshots/moose_blocks_minimal_modules_appended/` demonstrates the ASL shape. The maintained-library path is now canonicalized by `src/main.py`; use `artifacts/domain_libraries/blocks/plan_library.asl` for the active per-domain library. |
| Canonical single-ASL smoke | `src/main.py compile-moose-atomic-library ... --library-root tmp/canonical-domain-library-smoke` followed by `src/main.py append-lifted-temporal-goal ... --library-root tmp/canonical-domain-library-smoke` returned the same `tmp/canonical-domain-library-smoke/blocks/plan_library.asl`; `find` found exactly one ASL file under that library root. |
| Six-domain canonical ASL smoke | Existing MOOSE readable policies under `tmp/domain_canonical_smoke_subset/` compile and append successfully for all selected domains. Final totals: `ferry 13`, `miconic 15`, `gripper 14`, `logistics 20`, `blocks 19`, and `8puzzle-1tile 10` plans including two query-wrapper plans each. Atomic audit found `0` grounded atomic arguments, `0` role coverage gaps, and no synthetic names in all six libraries. |
| Real Jason execution smoke | `uv run python src/main.py validate-jason-plan-library ...` now runs generated ASL in Jason with a real PDDL action environment and an indexed/static-belief belief base. Targeted p2 probes that previously timed out now pass: Miconic `p2_01` succeeds in `6.79s` with `400` actions; Gripper `p2_02` succeeds in `102.18s` with the default linear wrapper and `25999` actions. The optional compact completion wrapper also passes Gripper `p2_02` in `111.92s`. Full six-domain validation still needs to be rerun after this runtime fix. |
| MOOSE paper audit | Local paper text confirms MOOSE decomposes training problems into singleton goal conditions and applies goal regression, making it suitable for atomic positive predicate templates. |

## Commands

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q \
  tests/domain_level_planning/test_atomic_backend_selector.py \
  tests/domain_level_planning/test_temporal_goal_appender.py \
  tests/domain_level_planning/test_lifted_ltlf_goal_schema.py \
  tests/evaluation/test_execution_logger.py
```

MOOSE atomic backend helper commands:

```bash
uv run python scripts/gp_backend_audit.py moose-atomic-command \
  --domain-file src/domains/ferry/domain.pddl \
  --training-dir src/domains/ferry/train \
  --save-file tmp/moose-atomic/ferry.model \
  --timeout-seconds 1800

uv run python scripts/gp_backend_audit.py moose-readable-summary \
  --policy-file .external/moose/exact-runs/ferry-seed0.model.readable \
  --domain-name ferry

uv run python scripts/gp_backend_audit.py moose-readable-compile-asl \
  --policy-file .external/moose/exact-runs/ferry-seed0.model.readable \
  --domain-name ferry \
  --output-dir tmp/moose-atomic/ferry-library

uv run python scripts/gp_backend_audit.py moose-readable-compile-asl \
  --policy-file tmp/moose-blocks-e2e/blocks-probe-first4.model.readable \
  --domain-file src/domains/blocks/domain.pddl \
  --domain-name blocks \
  --post-moose-recursive \
  --output-dir snapshots/moose_blocks_minimal_modules

uv run python src/main.py compile-moose-atomic-library \
  --policy-file .external/moose/exact-runs/ferry-seed0.model.readable \
  --domain-name ferry

uv run python src/main.py compile-moose-atomic-library \
  --policy-file tmp/moose-blocks-e2e/blocks-probe-first4.model.readable \
  --domain-file src/domains/blocks/domain.pddl \
  --domain-name blocks \
  --post-moose-recursive

uv run python src/main.py append-lifted-temporal-goal \
  --domain-file src/domains/blocks/domain.pddl \
  --ltlf-goal-json artifacts/input/blocksworld_lifted_ltlf.json \
  --query-id query_1

uv run python src/main.py validate-jason-plan-library \
  --domain-file src/domains/blocks/domain.pddl \
  --problem-file src/domains/blocks/test/instance-69.pddl \
  --goal-name g_blocks_user_goal_1 \
  --timeout-seconds 1800 \
  --require-plan-verifier \
  --plan-verifier-timeout-seconds 1800
```

Historical restoration references are no longer part of the active task list.
Current temporal input is the validated lifted LTLf JSON interface in
`src/domain_level_planning/lifted_ltlf_goal_schema.py`.

Jason full-test validation now exports a complete `jason_plan.plan` PDDL trace
for every successful run and, in the full-test runner, requires VAL or an
IPC-style verifier by default. The `1800` second timeout is the MOOSE paper
planning/instantiation cap; synthesis/train budgets remain separate.
