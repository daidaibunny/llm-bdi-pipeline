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
| Goal-separable and serialisable achievement classes | `gripper`, `miconic`, `logistics` |
| Bounded-width sketchable subgoal-structure classes | `barman`, `childsnack`, `visitall` |
| Feature-definable goal-dependent construction classes | `blocks`, `depots` |

Total selected IPC domains: 8. Instance counts are domain-specific:
`gripper` 20, `miconic` 150, `logistics` 84, `barman` 20,
`childsnack` 20, `visitall` 20, `blocks` 102, and `depots` 22.

## Active Requirements

| ID | Requirement | Status | Evidence / Next Step |
| --- | --- | --- | --- |
| R1 | Materialize all selected domains from the unified source. | Implemented | `scripts/materialize_achievement_benchmarks.py`; complete IPC snapshots under `src/domains`. |
| R2 | Remove obsolete formal benchmark domains and generated-variant references. | Implemented | Generated-only formal domains are no longer in `src/domains`, the achievement registry, or current paper taxonomy rows. Deleted the unreferenced old external vocabulary adapter and the Blocks-only experiment wrapper in favor of the generic registry/script path. |
| R3 | Keep mechanism tests independent of formal benchmark data. | Implemented | Resource-dependency tests now write temporary PDDL fixtures under `tmp_path`. |
| R4 | Update registry, taxonomy, manifest, and AAMAS text to the 8-domain complete IPC corpus. | Implemented | `src/benchmark_registry/achievement_goals`, `paper_artifacts/domain_support_taxonomy.json`, `paper_artifacts/final_paper_manifest.json`, and `latex_code/aamas_method_paper/sections/method.tex` / `evaluation.tex`. |
| R5 | Use full IPC splits without bounded-state explosion in synthesis setup. | Implemented | Main and expanded-smoke registry rows now enable synthesis-time Fast Downward trace fallback with `runtime_full_trace_planner=false`. `run_final_paper_data.py --config-only` renders 8 main rows with `use_synthesis_planner_traces=true`. |
| R6 | Support IPC parser constructs exposed by the 8-domain corpus. | Implemented | Added generic support for PDDL predicates whose names start with `not`, forward-referenced typed parent declarations during Tarski validation, and domain `:constants`. All 8 selected domains pass lightweight parser/support sweep. |
| R7 | Remove obsolete generated-result dependencies from the paper draft. | Implemented, validating | AAMAS result macro files are cleared until final regenerated results exist. |
| R8 | Run tests and final config validation. | Implemented | Targeted regressions pass. `run_final_paper_data.py --config-only` renders the new registry configs. `--validate-only` still requires a regenerated `tmp/paper-final-latest/comparison.json`, which is outside this data migration. |
| R9 | Commit and push the benchmark infrastructure cleanup. | Implemented | Full pytest, config render, representative smoke, commit, and push are complete for this milestone. |

## Current Evidence Snapshot

Latest lightweight checks:

| Check | Result |
| --- | --- |
| 8-domain parser/support sweep | All selected domains compile under the supported PDDL fragment for the first training problem. |
| Final config render | 8 main experiments generated; each uses offline synthesis planner traces and the project Fast Downward executable. |
| Representative trace smoke | `gripper` 1/1, `blocks` 0/1 due held-out execution timeout, `childsnack` 0/1 due missing `served` strategy; all three rows now synthesize a library without matrix failure. |

Interpretation:

- The latest fixes close infrastructure-level PDDL and benchmark-profile blockers.
- Remaining failures are now learning/execution coverage gaps: stronger Layer B
  modules for resource-production domains such as Childsnack, and stronger
  Layer C/execution scaling for larger held-out Blocks instances.

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
