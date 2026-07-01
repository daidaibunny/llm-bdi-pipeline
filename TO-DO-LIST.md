# To Do List

This is the active progress tracker for the domain-level lifted AgentSpeak(L)
library research line. Keep it focused on current decisions, open gaps, and
verification evidence.

## Current Research Target

Current scope: positive conjunctive achievement goals. Temporal extended goals
remain a future overlay where an LTLf-to-DFA controller calls the achievement
goal library.

Current strategic pivot, confirmed on 2026-07-01: do not build a universal
generalized planner. The project should route domains to existing
state-of-the-art generalized-planning backends, normalize their generalized
policy or sketch outputs, and compile those outputs into lifted AgentSpeak(L).

Target pipeline:

```text
PDDL domain + training/counterexample problems
→ routed external generalized-planning backend
→ LiftedPolicyProgram
→ feature binding
→ Layer B atomic goal modules
→ Layer C goal dependency composer
→ lifted AgentSpeak(L) domain-level plan library
→ held-out validation
→ counterexample-guided refinement
→ future DFA controller for temporal extended goals
```

## Current Benchmark Decision

The previous implementation milestone materialized an 8-domain IPC corpus from
one independent source. That corpus remains useful as infrastructure evidence,
but it is no longer the final paper taxonomy after the 2026-07-01 research
pivot.

Current materialized source:

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

New paper direction: use paper-quality official or reputable benchmark sources
matched to the selected generalized-planning backend. Prefer official IPC PDDL
when the exact domain variant exists there. Use the original paper repository
when a backend paper defines a restricted or synthetic generalized-planning
variant that is not an IPC domain.

## Selected Routing Domain Classes

| Class | Domains |
| --- | --- |
| Goal-regression and serialisable-goal domains | `ferry`, `gripper`, `miconic`, `logistics` |
| Bounded-width sketchable subgoal-structure domains | `delivery`, `spanner`, `visitall`, `childsnack`, `barman` |
| Feature-definable structural and goal-dependent domains | `blocks`, `8puzzle-1tile`, `sokoban-1stone` |

Total selected routing domains: 12. `depots` is demoted to a boundary or
failure-analysis domain because the KR 2025 learner reports Depot in its C5
failure group.

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
| R10 | Make prior paper-code reuse the main Layer B/C route rather than hand-built schema heuristics. | In progress | Added policy-first `LiftedPolicyProgram` IR and KR 2025 `learner-policies-from-examples` backend adapter. Existing schema synthesis remains a baseline adapter, not the main method. |
| R11 | Stabilize KR 2025 backend execution without native macOS planner failures. | Implemented | `docker/learning-general-policies/Dockerfile` builds an Ubuntu 22.04 linux/amd64 image with Boost.Python 1.82.0, Python 3.10, `pymimir==0.9.62`, and `dlplan==0.3.29`; BFWS dynamic libraries resolve inside Docker. Actual KR runs should use `learning-general-policies-docker-*` commands. |
| R12 | Validate a non-degenerate KR learner run that emits a policy artifact. | Open | Environment smoke now reaches feature generation and solver construction. One-problem Blocks smoke is too small and fails inside KR policy construction; next use a paper-style small training subset directory rather than `--max_num_instances` over a large folder. |
| R13 | Replace the old domain taxonomy with a backend-routing taxonomy based on prior GP tracks. | Implemented as design document | `docs/gp_backend_routing_taxonomy.md` now records track-specific backend choices for MOOSE, KR 2025, D2L, learner-sketches, h-policy/Vanir, PG3, planning-program backends, policy reuse, graph-neural policies, IPC learning-track systems, and LLM GP baselines. |
| R14 | Materialize the new routing benchmark set. | Open | Add or reclassify `ferry`, `delivery`, `spanner`, `8puzzle-1tile`, and `sokoban-1stone`; demote `depots` to boundary unless a routed backend solves it. |
| R15 | Implement route-specific backend adapters instead of extending the hand-built GP learner. | Open | First targets: MOOSE policy parser for Class A, h-policy/learner-sketches parser for Class B, and KR/D2L policy parser for Class C. All routes must normalize into `LiftedPolicyProgram` before ASL compilation. |
| R16 | Add backend-probe and acceptance gates. | Open | A backend route is accepted only if it emits a generalized artifact and the artifact passes parser, feature-binding, ASL compilation, and held-out validation gates under resource guards. |

## Current Evidence Snapshot

Latest lightweight checks:

| Check | Result |
| --- | --- |
| 8-domain parser/support sweep | All selected domains compile under the supported PDDL fragment for the first training problem. |
| Final config render | 8 main experiments generated; each uses offline synthesis planner traces and the project Fast Downward executable. |
| Representative trace smoke | `gripper` 1/1, `blocks` 0/1 due held-out execution timeout, `childsnack` 0/1 due missing `served` strategy; all three rows now synthesize a library without matrix failure. |
| KR 2025 Docker environment smoke | Docker image builds; `dlplan 0.3.29` exposes `set_generate_til_c_role`; `libbfws.so` resolves Boost.Python 1.82.0 and Python 3.10. |

Interpretation:

- The latest fixes close infrastructure-level PDDL and benchmark-profile blockers.
- Remaining failures are now learning/execution coverage gaps: stronger Layer B
  modules for resource-production domains such as Childsnack, and stronger
  Layer C/execution scaling for larger held-out Blocks instances.
- The architecture is being pulled back toward paper-code reuse: KR 2025 is the
  current policy-first backend candidate; schema-derived rules are baseline
  evidence, not the final claimed learning method.

## Commands

Core checks:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_final_paper_data.py --output-dir tmp/paper-final-latest --config-only
uv run python scripts/gp_backend_audit.py learning-general-policies-docker-build-command
uv run python scripts/gp_backend_audit.py learning-general-policies-docker-command --experiment blocks_4_clear_0 --timeout-seconds 120 --max-num-instances 1
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
