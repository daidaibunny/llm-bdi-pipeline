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
-> singleton-literal DFA validation
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
| Jason plus VAL validation | Needs full rerun | Run parser-order full-test validation after the new ASL batch completes. Report per-domain Jason and VAL success, timeout, and failure categories. |
| Numeric domains | Experimental | Keep numeric support marked experimental until numeric fluents have a complete executable semantics and full validation evidence. |
| Temporal Input integration | External dependency | Consume provided lifted LTLf JSON only; do not regenerate language-model prompts in this repository unless explicitly requested. |

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
