# To Do List

This is the active progress tracker for the domain-level lifted AgentSpeak(L)
library research line. Keep it focused on current decisions, open gaps, and
verification evidence.

## Current Research Target

Current scope: positive conjunctive achievement goals. Temporal extended goals
remain a future overlay where an LTLf-to-DFA controller calls the achievement
goal library.

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

## Current Benchmark Decision

All formal achievement-goal benchmark domains must come from one independent,
paper-quality source, not from learner repositories or implementation-local
fixtures.

Selected source:

```text
potassco/pddl-instances
commit cf19edf7c53d1540ddbb396c642595e0926ee552
```

Tracked layout:

```text
src/domains/<domain>/domain.pddl
src/domains/<domain>/train/*.pddl
src/domains/<domain>/test/*.pddl
src/domains/<domain>/source.json
```

Each selected domain contains all official instances from its selected IPC
directory. The `train` split size is `floor(2/3 * instance_count)`; the
remaining instances form the held-out goal-specification `test` split.

## Selected Domain Classes

| Class | Domains |
| --- | --- |
| Goal-separable and serialisable achievement classes | `gripper`, `miconic` |
| Bounded-width sketchable subgoal-structure classes | `barman`, `childsnack`, `visitall` |
| Feature-definable goal-dependent construction classes | `blocks` |

Total selected IPC domains: 6. Instance counts are domain-specific:
`gripper` 20, `miconic` 150, `barman` 20, `childsnack` 20, `visitall` 20,
and `blocks` 102.

## Active Requirements

| ID | Requirement | Status | Evidence / Next Step |
| --- | --- | --- | --- |
| R1 | Materialize all selected domains from the unified source. | Implemented, validating | `scripts/materialize_achievement_benchmarks.py`; complete IPC snapshots under `src/domains`. |
| R2 | Remove obsolete formal benchmark domains. | Implemented, validating | Generated-only formal domains such as `ferry`, `spanner`, `delivery`, and Blocksworld query variants are no longer in `src/domains`. |
| R3 | Keep mechanism tests independent of formal benchmark data. | Implemented, validating | Resource-dependency tests now write temporary PDDL fixtures under `tmp_path`. |
| R4 | Update registry, taxonomy, manifest, and AAMAS text to the 6-domain complete IPC corpus. | Implemented, validating | `src/benchmark_registry/achievement_goals`, `paper_artifacts/domain_support_taxonomy.json`, `paper_artifacts/final_paper_manifest.json`, and `latex_code/aamas_method_paper/sections/evaluation.tex`. |
| R5 | Remove obsolete generated-result dependencies from the paper draft. | Implemented, validating | AAMAS result macro files are cleared until final regenerated results exist. |
| R6 | Run tests and final config validation. | Implemented | `PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q` passes with 293 tests. `run_final_paper_data.py --config-only` renders the new registry configs. `--validate-only` still requires a regenerated `tmp/paper-final-latest/comparison.json`, which is outside this data migration. |
| R7 | Commit and push the benchmark migration. | Pending | Commit after final git inspection and push `main`. |

## Commands

Core checks:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_final_paper_data.py --output-dir tmp/paper-final-latest --config-only
```

Targeted benchmark checks:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q \
  tests/domain_level_planning/test_final_paper_data_scripts.py::test_domain_support_taxonomy_is_complete_and_manifested \
  tests/domain_level_planning/test_final_paper_data_scripts.py::test_achievement_benchmark_registry_matches_selected_domain_taxonomy \
  tests/domain_level_planning/test_experiment_matrix_script.py::test_paper_expanded_smoke_preset_covers_available_pddl_domains \
  tests/domain_level_planning/test_no_domain_hardcoding.py
```

Regenerate benchmark snapshots only when intentionally refreshing tracked
PDDL data:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/materialize_achievement_benchmarks.py
```
