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
| A11 | Maintain exactly one appendable domain ASL library per domain. | Implemented and regression-tested | `append_temporal_goal_to_library` now preserves `temporal_goal_append_history` and rejects duplicate temporal goal names with `duplicate_temporal_goal`. CLI regression test appends two queries sequentially by feeding the first output `plan_library.json` into the second append and verifies both top-level goals remain in the same ASL library. |
| A12 | Replace raw MOOSE macro dump with compact recursive atomic modules when claiming final domain-level ASL quality. | Open with quality gate | The current MOOSE Blocks snapshot is lifted but not compact: it compiles the raw MOOSE decision list into 72 `+!on(...)` macro rules. `audit_moose_atomic_library_quality` now marks direct MOOSE outputs as compact singleton macro, compact recursive module, or raw non-compact macro policy in artifact metadata. This prevents overclaiming, but the final compact recursive library still needs a validated policy/module backend or a principled compression layer. |

## Current Evidence Snapshot

| Check | Result |
| --- | --- |
| Full Python test suite | `111 passed, 2 warnings` with `PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q`. |
| Ruff check | `uv run ruff check ...` passes on the current touched source, scripts, and tests. `ruff==0.15.20` is installed in the dev dependency group. |
| Final artifact validation | `checks=26` with `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_final_paper_data.py --output-dir tmp/paper-final-latest --validate-only`. |
| Atomic selector tests | Included in full suite; selector only chooses MOOSE as implemented atomic ASL compiler and refuses unverified fallback compilers. |
| Temporal appender tests | Included in full suite; validates lifted atom restoration, singleton transition guards, negative waiting guards, and negative progress rejection. |
| Lifted LTLf schema tests | Included in full suite; validates lifted atom/binding JSON handoff. |
| Logger tests | `2 passed` with `uv run pytest tests/evaluation/test_execution_logger.py`. |
| DFA adapter/controller/appender tests | `30 passed` with `PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q tests/domain_level_planning/test_dfa_goal_adapter.py tests/domain_level_planning/test_dfa_controller.py tests/domain_level_planning/test_temporal_goal_appender.py tests/domain_level_planning/test_moose_policy_adapter.py`. |
| MOOSE readable policy adapter tests | Included in DFA/MOOSE focused suite; verifies readable-policy parsing, ASL compilation, CLI materialization, and quality metadata. |
| MOOSE readable artifact smoke | `uv run python scripts/gp_backend_audit.py moose-readable-summary --policy-file .external/moose/exact-runs/ferry-seed0.model.readable --domain-name ferry` reports `rules=5`, `modules=5`, `asl_plans=5`. |
| MOOSE atomic ASL artifact smoke | `uv run python scripts/gp_backend_audit.py moose-readable-compile-asl --policy-file .external/moose/exact-runs/ferry-seed0.model.readable --domain-name ferry --output-dir tmp/moose-atomic/ferry-library` writes a domain-level atomic `plan_library.json` and `plan_library.asl`. |
| MOOSE Blocks atomic-plus-temporal end-to-end smoke | Guarded MOOSE Blocks probe first4 training under `16GiB/900s` learned `72` singleton rules and compiled `72` raw MOOSE atomic ASL plans. Appending the first two probe instances as LTLf tower goals produced one maintained context-driven temporal library with `83` plans and no `teg_state` or `dfa_state` beliefs. Snapshots are under `snapshots/moose_blocks_e2e/`. A first20 interactive attempt reached `6/20` before manual interruption; no memory guard violation occurred. This is a pipeline smoke, not final compact recursive Blocksworld library quality. |
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

uv run python src/main.py compile-moose-atomic-library \
  --policy-file .external/moose/exact-runs/ferry-seed0.model.readable \
  --domain-name ferry \
  --output-root tmp/moose-atomic/ferry-library-main

uv run python src/main.py append-lifted-temporal-goal \
  --domain-file src/domains/blocks/domain.pddl \
  --plan-library-file artifacts/domain_libraries/blocks/plan_library.json \
  --ltlf-goal-json artifacts/input/blocksworld_lifted_ltlf.json \
  --query-id query_1 \
  --output-root artifacts/domain_libraries/blocks
```

Historical restoration references are no longer part of the active task list.
Current temporal input is the validated lifted LTLf JSON interface in
`src/domain_level_planning/lifted_ltlf_goal_schema.py`.
