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

The formal achievement-goal corpus is the 12-family generalized-planner routing
taxonomy. It supersedes the earlier IPC-only corpus as the single selected
benchmark framework.

Current pinned materialization sources:

```text
potassco/pddl-instances
DillonZChen/moose-dataset
bonetblai/learner-sketches
bonetblai/learner-policies-from-examples
```

Tracked layout:

```text
src/domains/<domain>/domain.pddl
src/domains/<domain>/train/*.pddl
src/domains/<domain>/test/*.pddl
src/domains/<domain>/source.json
```

Each selected domain contains all selected source instances for its planning
family. The `train` split size is `floor(2/3 * instance_count)`; the remaining
instances form the held-out goal-specification `test` split.

## Selected Routing Planning-Family Classes

| Class | Domain shorthand |
| --- | --- |
| Goal-regression-decomposable domain-goal families | `ferry`, `gripper`, `miconic`, `logistics` |
| Bounded-width sketchable subgoal-structure families | `delivery`, `spanner`, `visitall`, `childsnack`, `barman` |
| Feature-definable structural and goal-dependent families | `blocks`, `8puzzle-1tile`, `sokoban-1stone` |

Total selected routing families: 12. Domain names are shorthand for selected
domain-goal families, not claims that a bare PDDL domain has one fixed
generalized-planning type. `depots` is demoted to a boundary or failure-analysis
family because the KR 2025 learner reports Depot in its C5 failure group.

## Active Requirements

| ID | Requirement | Status | Evidence / Next Step |
| --- | --- | --- | --- |
| R1 | Materialize all selected domains from the pinned reputable benchmark sources. | Implemented | `scripts/materialize_achievement_benchmarks.py`; 12 selected snapshots under `src/domains`: `ferry`, `gripper`, `miconic`, `logistics`, `delivery`, `spanner`, `visitall`, `childsnack`, `barman`, `blocks`, `8puzzle-1tile`, and `sokoban-1stone`. |
| R2 | Remove obsolete formal benchmark domains and generated-variant references. | Implemented | Generated-only formal domains are no longer in `src/domains`, the achievement registry, or current paper taxonomy rows. Deleted the unreferenced old external vocabulary adapter and the Blocks-only experiment wrapper in favor of the generic registry/script path. |
| R3 | Keep mechanism tests independent of formal benchmark data. | Implemented | Resource-dependency tests now write temporary PDDL fixtures under `tmp_path`. |
| R4 | Update registry, taxonomy, manifest, and AAMAS text to the 12-family routing corpus. | Implemented | `src/benchmark_registry/achievement_goals`, `paper_artifacts/domain_support_taxonomy.json`, `paper_artifacts/final_paper_manifest.json`, and `latex_code/aamas_method_paper/sections/method.tex` / `evaluation.tex`. |
| R5 | Use deterministic train/test splits without bounded-state explosion in synthesis setup. | Implemented | Main and expanded-smoke registry rows enable synthesis-time Fast Downward trace fallback with `runtime_full_trace_planner=false`. Config rendering produces one main row per selected routing family. |
| R6 | Support PDDL parser constructs exposed by the selected corpus. | Implemented | Added generic support for PDDL predicates whose names start with `not`, forward-referenced typed parent declarations during Tarski validation, and domain `:constants`. Keep this row current as newly materialized paper-source domains are parsed. |
| R7 | Remove obsolete generated-result dependencies from the paper manuscript. | Implemented, validating | AAMAS result macro files are cleared until final regenerated results exist. |
| R8 | Run tests and final config validation. | Implemented | Targeted regressions pass. `run_final_paper_data.py --config-only` renders the new registry configs. `--validate-only` still requires a regenerated `tmp/paper-final-latest/comparison.json`, which is outside this data migration. |
| R9 | Commit and push the benchmark infrastructure cleanup. | Implemented | Full pytest, config render, representative smoke, commit, and push are complete for this milestone. |
| R10 | Make prior paper-code reuse the main Layer B/C route rather than hand-built schema heuristics. | Implemented as router boundary | Added policy-first `LiftedPolicyProgram` IR, KR 2025 `learner-policies-from-examples` backend adapter, and `gp_router.py`. Existing schema synthesis is now exposed only as `baseline_schema_lift` fallback route metadata, not the main method. |
| R11 | Stabilize KR 2025 backend execution without native macOS planner failures. | Implemented | `docker/learning-general-policies/Dockerfile` builds an Ubuntu 22.04 linux/amd64 image with Boost.Python 1.82.0, Python 3.10, `pymimir==0.9.62`, and `dlplan==0.3.29`; BFWS dynamic libraries resolve inside Docker. Actual KR runs should use `learning-general-policies-docker-*` commands. |
| R12 | Validate a non-degenerate KR learner run that emits a policy artifact. | Open | Environment smoke now reaches feature generation and solver construction. One-problem Blocks smoke is too small and fails inside KR policy construction; next use a paper-style small training subset directory rather than `--max_num_instances` over a large folder. |
| R13 | Replace the old domain taxonomy with a backend-routing planning-family taxonomy based on prior GP tracks. | Implemented as design document | `docs/gp_backend_routing_taxonomy.md` now defines the classification unit as `(PDDL domain, goal family, instance distribution)` and records track-specific backend choices for MOOSE, KR 2025, D2L, learner-sketches, h-policy/Vanir, PG3, planning-program backends, policy reuse, graph-neural policies, IPC learning-track systems, and LLM GP baselines. |
| R14 | Materialize the new routing benchmark set. | Implemented | `ferry`, `delivery`, `spanner`, `8puzzle-1tile`, and `sokoban-1stone` are now tracked under `src/domains`; `depots` is removed from the formal selected corpus and remains a boundary case only. |
| R15 | Implement route-specific backend adapters instead of extending the hand-built GP learner. | In progress | Router and route metadata are implemented. Next targets: MOOSE policy parser for Class A, h-policy/learner-sketches parser for Class B, and KR/D2L policy parser for Class C. All routes must normalize into `LiftedPolicyProgram` before ASL compilation. |
| R16 | Add backend-probe and acceptance gates. | In progress | Router now rejects unavailable or unsupported backend routes and marks schema synthesis as baseline fallback only. Still needed: artifact-level acceptance gates for emitted backend policies/sketches/programs. |
| R17 | Physically remove old GP-main-path code references after routing migration. | Implemented, monitoring | Registry, manifest, taxonomy, tests, and paper text now target the 12-family routing taxonomy. Continue checking that no stale formal-support wording is reintroduced; `depots` may appear only as boundary/failure-analysis context. |
| R18 | Download, pin, and document how to invoke all relevant generalized-planning codebases. | Implemented | Unified audit now covers MOOSE plus the pinned `.external/gp-backends` inventory: learner-sketches, h-policy-learner, d2l, learner-policies-from-examples, PG3, mimir-rgnn, best-first-generalized-planning, BFGP++, PGP-landmarks, SLTP, UP-BFGP, LLM-GenPlan, state-centric generalized planning, IPC HUZAR, and IPC PGP baseline. `gp_backend_audit.py install` can restore the code inventory, `status` verifies pins, `usage` prints runnable entrypoints, and `capability` reports whether each backend is paper-source-complete, environment-dependent, interface-only, or competition-artifact-only. |

## Current Evidence Snapshot

Latest lightweight checks:

| Check | Result |
| --- | --- |
| 12-family data materialization | All selected routing families have `domain.pddl`, `train`, `test`, and `source.json`; split sizes match `floor(2/3 * instance_count)`. |
| Final config render | One main experiment is generated per selected routing family; each uses offline synthesis planner traces and the project Fast Downward executable. |
| Representative trace smoke | `gripper` 1/1, `blocks` 0/1 due held-out execution timeout, `childsnack` 0/1 due missing `served` strategy; all three rows now synthesize a library without matrix failure. |
| KR 2025 Docker environment smoke | Docker image builds; `dlplan 0.3.29` exposes `set_generate_til_c_role`; `libbfws.so` resolves Boost.Python 1.82.0 and Python 3.10. |
| GP backend code inventory | MOOSE plus all 15 pinned `.external/gp-backends` repositories are present at expected commits. Current synthesis-consumable routes are MOOSE, learner-sketches, h-policy-learner, d2l, and learner-policies-from-examples; PG3, planning-program, neural, LLM, and IPC learning-track systems are audit/baseline-only until adapters exist. |
| GP paper-code capability audit | `scripts/gp_backend_audit.py capability` now records the paper-code capability status for every GP line in `docs/gp_backend_routing_taxonomy.md`. The audit distinguishes exact-reproduction-ready, paper-source-complete, source-complete-but-environment-dependent, library/interface-only, and competition-artifact-only backends. |

Interpretation:

- The latest fixes close infrastructure-level PDDL and benchmark-profile blockers.
- Remaining failures are now learning/execution coverage gaps: additional Layer
  B modules for resource-production domains such as Childsnack, and additional
  Layer C/execution scaling for larger held-out Blocks instances.
- The architecture is now explicitly router-first: external GP backends produce
  learned artifacts, those artifacts normalize into `LiftedPolicyProgram`, and
  schema-derived rules are baseline fallback evidence only.

## Commands

Core checks:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_final_paper_data.py --output-dir tmp/paper-final-latest --config-only
uv run python scripts/gp_backend_audit.py learning-general-policies-docker-build-command
uv run python scripts/gp_backend_audit.py learning-general-policies-docker-command --experiment blocks_4_clear_0 --timeout-seconds 120 --max-num-instances 1
uv run python scripts/gp_backend_audit.py status
uv run python scripts/gp_backend_audit.py usage
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
