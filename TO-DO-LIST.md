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
| A1 | Replace class-based backend routing on the main path with atomic template backend selection. | Implemented first pass | `src/domain_level_planning/atomic_backend_selector.py` selects from training goal templates, not benchmark class ids. `run_domain_level_experiment` now reports `atomic_template_backend_decision`; registry rows use `goal_property_group_id` only for evaluation coverage. |
| A2 | Use MOOSE as the first positive singleton-goal backend candidate. | Implemented first pass | Selector chooses MOOSE first when present. `src/domain_level_planning/moose_policy_adapter.py` parses official `policy --dump-policy` readable artifacts into `LiftedPolicyProgram` and lifted ASL atomic plans. `scripts/gp_backend_audit.py moose-atomic-command` prints a guarded train+dump command. Next: run selected-domain MOOSE smoke jobs when we decide the exact runtime budget. |
| A3 | Do not claim negative literal template support without evidence. | Implemented at selector boundary | Negative goal facts return `negative_literal_template_not_supported`. Next: audit whether any backend can safely learn negative literal modules. |
| A4 | Add singleton-literal DFA validation for the Input handoff. | Implemented first pass | `validate_singleton_literal_dfa` rejects conjunctive/disjunctive guards, undeclared predicates, wrong arities, unsupported negative literals, malformed transition records, and allows accepting `true` self-loops. Next: wire logger events around LTLf-to-DFA execution failures. |
| A5 | Append query-specific temporal goals to a domain ASL library. | In progress | `append_temporal_goal_to_library` appends `+!g_query` plans for positive progress literals. `append_lifted_temporal_goal_case_to_library` connects lifted LTLf cases to a DFA builder. It records `requires_external_dfa_state=true`. |
| A6 | Restore/refactor historical logger into the new pipeline. | Implemented first pass | `src/execution_logging/execution_logger.py` restores structured JSON, human log, and payload externalization without HTN/HDDL imports. Tests: `tests/evaluation/test_execution_logger.py`. |
| A7 | Restore/refactor historical LTLf JSON schema and prompts only as Input interface references. | In progress | `src/domain_level_planning/lifted_ltlf_goal_schema.py` parses lifted LTLf JSON with atoms and bindings. LLM prompts remain external Input responsibility. |
| A8 | Remove stale 12-family routing language from current path, tests, registry, and paper text. | In progress | `scripts/materialize_achievement_benchmarks.py`, `src/benchmark_registry/achievement_goals`, `paper_artifacts/domain_support_taxonomy.json`, and focused tests now use six selected domains and goal-property groups. Next: decide whether to delete or quarantine old Layer B/C synthesis internals. |
| A9 | Materialize the six selected domains with deterministic splits. | Implemented | `uv run python scripts/materialize_achievement_benchmarks.py` rebuilt `src/domains` with `ferry`, `miconic`, `gripper`, `logistics`, `blocks`, and `8puzzle-1tile`; each uses `floor(2/3 * N)` train and remaining test. |
| A10 | Preserve current PDDL-only and no synthetic achievement-name constraints. | In progress | New code emits no `achieve_*`, `transition_*`, or `dfa_state` names. It does append `g_query` names by design. |

## Current Evidence Snapshot

| Check | Result |
| --- | --- |
| Atomic selector tests | `3 passed` with `uv run pytest tests/domain_level_planning/test_atomic_backend_selector.py`. |
| Temporal appender tests | `4 passed` with `uv run pytest tests/domain_level_planning/test_temporal_goal_appender.py`. |
| Lifted LTLf schema tests | `2 passed` with `uv run pytest tests/domain_level_planning/test_lifted_ltlf_goal_schema.py`. |
| Logger tests | `2 passed` with `uv run pytest tests/evaluation/test_execution_logger.py`. |
| MOOSE readable policy adapter tests | `3 passed` with `uv run pytest tests/domain_level_planning/test_moose_policy_adapter.py`. |
| MOOSE readable artifact smoke | `uv run python scripts/gp_backend_audit.py moose-readable-summary --policy-file .external/moose/exact-runs/ferry-seed0.model.readable --domain-name ferry` reports `rules=5`, `modules=5`, `asl_plans=5`. |
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
```

Historical assets to inspect while restoring temporal/logging support:

```bash
git show f6a5d00:src/execution_logging/execution_logger.py
git show f6a5d00:src/execution_logging/artifacts.py
git show f6a5d00:src/temporal_specification/ltlf_dataset_generation.py
git show f6a5d00:src/evaluation/goal_grounding/prompts.py
git show fcc9011:src/evaluation/temporal_compilation/ltlf_to_dfa.py
git show fcc9011:src/evaluation/temporal_compilation/dfa_builder.py
```
