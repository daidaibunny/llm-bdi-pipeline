# Generalized Planner Routing Taxonomy
This document is the project reference for the current achievement-goal
planning line. It replaces the earlier attempt to build one universal
generalized planner inside this repository.

The project now treats existing generalized-planning systems as backends. Our
role is to select a backend for a planning family, run it under a reproducible
interface, parse its generalized artifact, bind that artifact to declared PDDL
vocabulary, and compile the accepted artifact into a lifted AgentSpeak(L)
domain-level plan library.

## Current Scope

The current scope is positive conjunctive achievement goals. Temporal extended
goals are a later layer. An LTLf formula can later be compiled into a
deterministic finite automaton that chooses which achievement condition to
realize next, but that automaton is query-specific and must sit above the
domain-level achievement-goal library.

The current target pipeline is:

```text
PDDL domain + routed training instances
-> generalized-planning backend
-> backend artifact
-> LiftedPolicyProgram
-> conservative binding to PDDL vocabulary
-> lifted AgentSpeak(L) domain-level plan library
-> held-out validation without runtime full-trace planning
```

If no backend emits an artifact that passes parsing, binding, compilation, and
held-out validation, the router must report the planning family as unsupported
or diagnostic-only. It must not silently fall back to a problem-specific
classical plan at runtime.

## Classification Unit

The unit of classification is a planning family, not a bare domain name:

```text
planning family = (PDDL domain, goal family, instance distribution)
```

This follows how generalized-planning papers define their evaluation settings.
A PDDL domain gives actions and predicates, but the learnability of a reusable
policy also depends on the goal schema and on the training and testing instance
distribution. For example, Blocks with a single `clear(a)` goal and Blocks with
a tower goal such as `on(a,b) & on(b,c)` have the same PDDL action schemas but
different generalized-planning structure.

## Core Terms

| Term | Definition in this project |
| --- | --- |
| PDDL | Planning Domain Definition Language. It provides the formal action schemas, predicates, types, problem objects, initial state, and final-state goal formula. |
| LTLf | Linear Temporal Logic over finite traces. It is outside the current achievement-goal layer and will later be compiled into a deterministic finite automaton controller. |
| AgentSpeak(L), or ASL | The target behavior language for the final lifted plan library. A plan head should be a declared predicate achievement goal such as `+!on(X,Y)`, not a generated name such as `+!achieve_on_X_Y`. |
| Generalized planner | A system that learns or synthesizes one reusable policy, sketch, or program from multiple planning instances, rather than solving each instance with a separate trace. |
| Backend | One external generalized-planning implementation, such as MOOSE, learner-sketches, D2L, or KR 2025 learner-policies-from-examples. |
| Backend artifact | The output produced by a backend: a decision-list policy, a DLPlan feature policy, a sketch, a hierarchical sketch, or a planning program. |
| LiftedPolicyProgram | The internal normalized representation that stores a backend artifact before AgentSpeak(L) compilation. It is lifted: variables stand for objects, and object-specific training names must not appear as library heads. |
| Atomic goal item | One ground PDDL state fluent required by a problem goal, for example `at(ball1,room_b)`, `served(passenger3)`, or `on(a,b)`. It is not an action and not an invented subgoal. |
| Positive conjunctive achievement goal | A final-state goal of the form `g1 & ... & gn`, where each `gi` is an atomic goal item and there are no temporal operators, disjunctions, or numeric objectives in the current layer. |
| Goal family | The schema-level pattern that generates goal items across instances, such as "all packages reach destination locations" or "the target block support relation is achieved". |
| Goal interaction | A dependency between atomic goal items caused by action preconditions, add effects, delete effects, mutual exclusion, shared resources, movement topology, or structural support. |
| Ordering constraint | A partial order over achieving atomic goal items or over calling their lifted modules. In Blocks, `on(b,c)` may have to be achieved before `on(a,b)` because the lower relation must support the upper relation. |
| DLPlan | A description-logic planning feature language used by several generalized-planning systems to describe lifted state and goal properties. |
| Feature | A lifted, symbolic state descriptor used by a backend, often from DLPlan or related description-logic languages. Examples include counts, reachability-like concepts, or goal-aware equality between current and target relations. |
| Feature binding | The checked mapping from backend features, actions, and calls to declared PDDL predicates, primitive actions, predicate achievement goals, read-only goal descriptors, or read-only router agenda gates. Unsupported features remain rejected. |
| Sketch | A generalized-planning rule of the form `condition -> qualitative effect`. A sketch does not necessarily say the exact primitive action; it states which abstract feature or subgoal should make progress. |
| Program | A generalized plan represented with control flow such as loops, jumps, registers, or pointers. Program artifacts are useful baselines until a program-to-AgentSpeak(L) adapter exists. |
| Runtime full-trace planner | A classical planner called during execution to solve a new problem from scratch. This is disallowed for the final domain-level library claim. Classical planners may still be used offline for backend learning, baselines, and validation. |
| Held-out validation | Testing the compiled library on instances not used to obtain the backend artifact. |
| KR 2025 C5 failure group | The set of domains reported by the KR 2025 learner-policies-from-examples paper as failing because no discriminating features are found within the configured feature-generation resources. |
| Boundary family | A relevant family that we discuss but do not include in the formal main corpus because the current router lacks a trusted backend path or safe compiler binding. |

## Why Backend Routing Is Necessary

No known generalized planner is state-of-the-art for every PDDL planning
family. Existing systems use different hypothesis languages and therefore have
different strengths.

| Generalized-planning line | Typical artifact | Planning-family property it targets |
| --- | --- | --- |
| MOOSE goal regression | First-order condition-to-action decision list | Goal items are independent or serialisable under singleton-goal regression. |
| Policy sketches | Feature rules `C -> E` | A compact sketch decomposes the family into bounded-width subproblems. |
| Hierarchical policy learning | Nested sketches or policies | Sketch rules can be refined into lower-width or executable subpolicies. |
| DLPlan feature-policy learning | Terminating qualitative feature policy | A finite lifted feature pool separates preferred transitions from rejected transitions. |
| Lifted decision-list search | Goal-conditioned action policy | A direct lifted policy can choose actions for held-out instances. |
| Planning-program synthesis | Algorithmic program with control flow | The solution is naturally represented by loops, registers, and program counters. |
| Neural relational policy learning | Learned relational policy or value model | Useful as a baseline or feature-discovery signal, but not directly compilable to symbolic AgentSpeak(L) without certification. |

The router therefore chooses a backend from planning-family evidence and from
the artifact's ability to pass compiler gates. It must not classify a case only
by a folder name such as `blocks` or `logistics`.

## Selected Corpus

The formal achievement-goal corpus currently contains 12 selected planning
families. Each family has a local snapshot under `src/domains/<family>/` with:

```text
domain.pddl
train/*.pddl
test/*.pddl
source.json
```

The split is deterministic: `floor(2/3 * instance_count)` training instances
and the remaining instances as held-out goal-specification instances.

| Class | Selected families | Primary route |
| --- | --- | --- |
| Goal-regression-decomposable families | `ferry`, `gripper`, `miconic`, `logistics` | MOOSE first; PG3 or KR 2025 only if the MOOSE artifact cannot pass compiler gates. |
| Bounded-width sketchable subgoal-structure families | `delivery`, `spanner`, `visitall`, `childsnack`, `barman` | learner-sketches first; h-policy/Vanir, KR 2025, or D2L as fallbacks. |
| Feature-definable structural goal-dependency families | `blocks`, `8puzzle-1tile`, `sokoban-1stone` | KR 2025 learner-policies-from-examples first; D2L as feature-policy reference and fallback. |

These are the only selected main-corpus families for the achievement-goal
layer. `depots` is not selected; it is a boundary family because KR 2025 reports
Depot in its C5 failure group.

The materialized local split is:

| Class | Family | Instances | Train | Test | Source |
| --- | --- | ---: | ---: | ---: | --- |
| A | `ferry` | 110 | 73 | 37 | `DillonZChen/moose-dataset` |
| A | `gripper` | 20 | 13 | 7 | `potassco/pddl-instances` |
| A | `miconic` | 150 | 100 | 50 | `potassco/pddl-instances` |
| A | `logistics` | 84 | 56 | 28 | `potassco/pddl-instances` |
| B | `delivery` | 30 | 20 | 10 | `bonetblai/learner-sketches` |
| B | `spanner` | 30 | 20 | 10 | `bonetblai/learner-sketches` |
| B | `visitall` | 20 | 13 | 7 | `potassco/pddl-instances` |
| B | `childsnack` | 20 | 13 | 7 | `potassco/pddl-instances` |
| B | `barman` | 20 | 13 | 7 | `potassco/pddl-instances` |
| C | `blocks` | 102 | 68 | 34 | `potassco/pddl-instances` |
| C | `8puzzle-1tile` | 20 | 13 | 7 | `bonetblai/learner-policies-from-examples` |
| C | `sokoban-1stone` | 10 | 6 | 4 | `bonetblai/learner-policies-from-examples` |

## Routing Classes

### Class A: Goal-Regression-Decomposable Families

Definition:

- the goal is a positive conjunction of atomic goal items;
- singleton goal items can be regressed through action schemas;
- solving one item does not require a global construction policy over the whole
  goal structure;
- when order matters, a valid serial order exists within the family and can be
  represented by the backend artifact.

Theoretical basis:

- MOOSE true goal independence, serialisable goal independence, and optimal
  goal independence;
- executable lifted-policy baselines such as PG3.

Selected families:

| Family | Goal-family shorthand | Selection rationale |
| --- | --- | --- |
| `ferry` | cars reach destination locations | Direct MOOSE benchmark family. The local MOOSE reproduction already validates the Ferry results with VAL. |
| `gripper` | balls reach the destination room | Standard generalized-planning family used by MOOSE, PG3, D2L, learner-sketches, and KR 2025. |
| `miconic` | passengers are served | Standard elevator achievement family across generalized-planning papers. |
| `logistics` | packages reach destinations | Included as a stress family because MOOSE studies full Logistics, while KR 2025 reports restricted success and full-family difficulty. |

### Class B: Bounded-Width Sketchable Subgoal-Structure Families

Definition:

- the goal is a positive conjunction of atomic goal items;
- a compact sketch can decompose the family into subproblems;
- after applying the sketch, the subproblems have bounded width or bounded
  effective width;
- the backend artifact may specify abstract progress rather than a primitive
  action at every step.

Theoretical basis:

- learned policy sketches;
- sketch width and subgoal-structure theory;
- hierarchical width-reduction policies.

Selected families:

| Family | Goal-family shorthand | Selection rationale |
| --- | --- | --- |
| `delivery` | packages are delivered | Central benchmark in sketch, D2L, PG3, and KR 2025 lines. |
| `spanner` | nuts are tightened under tool constraints | Appears in D2L, learner-sketches, PG3, KR 2025, and planning-program work. |
| `visitall` | all required cells or locations are visited | Standard width, sketch, and feature-policy family. |
| `childsnack` | children are served | Used in sketch work and KR 2025; tests decomposition under resource and compatibility constraints. |
| `barman` | requested drink contents are achieved | Used by MOOSE and sketch/subgoal-structure work; stresses resources and ordered preparation subgoals. |

### Class C: Feature-Definable Structural Goal-Dependency Families

Definition:

- the goal is a positive conjunction of atomic goal items;
- at least one goal item supports, threatens, or orders another goal item;
- arbitrary order over goal items is unsound for the family;
- a compact policy requires goal-aware lifted features, indexical concepts,
  counts, distances, or reusable modules.

Theoretical basis:

- D2L feature-definable policies for Blocksworld variants and full
  Blocksworld;
- KR 2025 feature-policy classes and failure taxonomy;
- policy-reuse work as the closest representation model for callable
  AgentSpeak(L)-style modules.

Selected families:

| Family | Goal-family shorthand | Selection rationale |
| --- | --- | --- |
| `blocks` | clear, on, and tower construction goals | Canonical structural goal-dependency family. Prior work studies `Qclear`, `Qon`, and full Blocksworld as related goal families, but this corpus counts `blocks` once. |
| `8puzzle-1tile` | one tile reaches its target position | KR 2025 solves fixed and non-fixed one-tile variants; tests structural rearrangement with compact features. |
| `sokoban-1stone` | one stone reaches its target cell | KR 2025 solves one-stone variants; tests feature-definable push-to-target structure. |

## Boundary Families

Boundary families are not part of the selected main corpus until a backend
artifact passes parsing, binding, AgentSpeak(L) compilation, and held-out
validation.

| Family | Boundary reason |
| --- | --- |
| `depots` | KR 2025 reports Depot in C5 with feature-pool edge failure. It combines route, resource, and stacking structure beyond the current trusted route. |
| `rovers`, `satellite`, `transport` | These require richer route, instrument, resource, or transitive-closure reasoning. MOOSE also removes path-finding components from some route domains. |
| Numeric MOOSE families | Current scope is predicate achievement goals, not numeric fluents or optimization. |
| Fibonacci, Sorting, and related program-synthesis families | Useful for BFGP and Progressive Generalized Planning baselines, but their program outputs do not yet map cleanly to predicate-goal AgentSpeak(L) modules. |
| Grid, Floortile, Schedule, and Traveling Purchaser Problem | Important benchmarks for some sketch or planning-program papers, but not selected in the current 12-family corpus. |

## Backend Inventory

The local machine-readable capability audit is:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/gp_backend_audit.py capability
```

| Backend line | Local status | Current role |
| --- | --- | --- |
| MOOSE | `confirmed_exact_reproduction_ready` | Primary Class A route and reproduction baseline. |
| learner-sketches | `confirmed_paper_source_complete` | Primary Class B route candidate. |
| h-policy-learner / Vanir | `confirmed_paper_source_complete` | Class B fallback candidate once hierarchy artifacts are parsed and bound. |
| D2L | `confirmed_source_complete_needs_paper_environment` | Class C feature-policy reference and fallback. |
| KR 2025 learner-policies-from-examples | `confirmed_source_complete_needs_paper_environment` | Primary Class C route candidate. |
| PG3 | `confirmed_paper_source_complete` | Class A/B fallback after a decision-list-to-AgentSpeak(L) adapter exists. |
| BFGP, BFGP++, Progressive Generalized Planning, and UP-BFGP | paper source or interface confirmed | Program-synthesis baselines until a program-to-AgentSpeak(L) adapter exists. |
| SLTP | `confirmed_source_complete_needs_paper_environment` | Feature-learning reference and possible baseline; not a current compiler source. |
| mimir-rgnn and state-centric transition models | library or environment dependent | Neural baselines or feature-discovery references, not deterministic compiler sources. |
| IPC learning-track HUZAR and Progressive Generalized Planning baseline | `confirmed_competition_artifact_only` | Comparator systems for learned domain knowledge, not direct AgentSpeak(L) generation routes. |
| LLM-GenPlan | `confirmed_paper_source_complete` | Code-generation baseline; not a trusted deterministic generalized-planner backend for this compiler path. |

## Acceptance Gates

A backend is accepted for a planning family only if every gate passes:

1. Backend availability: the pinned implementation exists locally and can run
   under the declared resource guard.
2. Artifact emission: the backend emits a generalized artifact, not only
   independent per-problem traces.
3. Parser support: the artifact dialect is parsed into `LiftedPolicyProgram`
   without guessing unsupported syntax.
4. Vocabulary binding: every predicate, action, feature, and subgoal binds to
   declared PDDL vocabulary or to a documented read-only descriptor.
5. AgentSpeak(L) compilability: the compiled library contains lifted plans,
   declared PDDL primitive actions, declared predicate subgoals, and no
   synthetic achievement names such as `achieve_*`, `transition_*`, or
   `dfa_state`.
6. Held-out validation: the compiled library validates on held-out instances
   without runtime full-trace planning.

If any gate fails, the router records the failure reason and tries the next
declared route. The older schema-derived synthesis path is allowed only as a
diagnostic or baseline fallback, not as the main research method.

## Source and Provenance

Formal benchmark data is materialized from pinned, reputable generalized-
planning or planning benchmark sources.

| Source | Commit | Selected local families |
| --- | --- | --- |
| `potassco/pddl-instances` | `cf19edf7c53d1540ddbb396c642595e0926ee552` | `gripper`, `miconic`, `logistics`, `visitall`, `childsnack`, `barman`, `blocks` |
| `DillonZChen/moose-dataset` | `e00970516154e9042b783a4613a1ed7286c9beee` | `ferry` |
| `bonetblai/learner-sketches` | `7a7ea6a6356035afa16ed958b53d8edc86994e0a` | `delivery`, `spanner` |
| `bonetblai/learner-policies-from-examples` | `9991926f7655c4b6c8dc2f0404123639e42056f2` | `8puzzle-1tile`, `sokoban-1stone` |

Regenerate the tracked local snapshots with:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/materialize_achievement_benchmarks.py
```

The materializer verifies source commits and writes:

```text
src/domains/<family>/domain.pddl
src/domains/<family>/train/*.pddl
src/domains/<family>/test/*.pddl
src/domains/<family>/source.json
src/benchmark_registry/achievement_goals/**/benchmark.json
```

## Router Execution Policy

The benchmark registry is the single source of truth for selected family
membership, source paths, split sizes, and route metadata. The router must not
infer classification from the PDDL domain name alone.

Declared route order:

```text
Class A:
	MOOSE -> PG3 -> KR 2025

Class B:
	learner-sketches -> h-policy/Vanir -> KR 2025 -> D2L

Class C:
	KR 2025 -> D2L

Boundary/program families:
	BFGP or Progressive Generalized Planning only after a program-to-ASL adapter
	exists
```

The router always prefers a verified backend artifact over any hand-built or
schema-derived fallback.

## Citation List

- Chen, D. Z., Hofmann, T., Klassen, T. Q., and McIlraith, S. A. 2026.
  Satisficing and Optimal Generalised Planning via Goal Regression. AAAI 2026.
  Code: <https://github.com/DillonZChen/moose>.
- Bonet, B., Drexler, D., and Geffner, H. 2025. Learning General Policies from
  Examples. KR 2025. Code:
  <https://github.com/bonetblai/learner-policies-from-examples>.
- Frances, G., Bonet, B., and Geffner, H. 2021. Learning General Policies from
  Small Examples Without Supervision. AAAI 2021. Code:
  <https://github.com/rleap-project/d2l>.
- Drexler, D., Seipp, J., and Geffner, H. 2022. Learning Sketches for
  Decomposing Planning Problems into Subproblems of Bounded Width. ICAPS 2022.
  Code: <https://github.com/bonetblai/learner-sketches>.
- Drexler, D., Seipp, J., and Geffner, H. 2023. Learning Hierarchical Policies
  by Iteratively Reducing the Width of Sketch Rules. KR 2023. Software:
  <https://ml.rwth-aachen.de/software/>.
- Drexler, D., Seipp, J., and Geffner, H. 2024. Expressing and Exploiting the
  Common Subgoal Structure of Classical Planning Domains Using Sketches. JAIR
  2024.
- Bonet, B., and Geffner, H. 2024. General Policies, Subgoal Structure, and
  Planning Width. JAIR 80:475-516.
- Yang, R., Silver, T., Curtis, A., Lozano-Perez, T., and Kaelbling, L. P.
  2022. PG3: Policy-Guided Planning for Generalized Policy Generation. IJCAI
  2022. Code: <https://github.com/ryangpeixu/pg3>.
- Segovia-Aguas, J., Jimenez, S., and Jonsson, A. 2021. Generalized Planning as
  Heuristic Search.
- Segovia-Aguas, J., Jimenez, S., and Jonsson, A. 2022. Computing Programs for
  Generalized Planning as Heuristic Search.
- Lei, C., Lipovetzky, N., and Ehinger, K. A. 2023. Novelty and Lifted Helpful
  Actions in Generalized Planning.
- Gomez, A. F.-A., and Segovia-Aguas, J. 2024. Parallel Strategies for
  Best-First Generalized Planning.
- Bonet, B., Drexler, D., and Geffner, H. 2024. On Policy Reuse: An Expressive
  Language for Representing and Executing General Policies that Call Other
  Policies. ICAPS 2024.
- Stahlberg, S., Bonet, B., and Geffner, H. 2022. Learning General Optimal
  Policies with Graph Neural Networks: Expressive Power, Transparency, and
  Limits. KR 2022. Code: <https://github.com/simon-stahlberg/mimir-rgnn>.
- Stahlberg, S., Bonet, B., and Geffner, H. 2025. Learning More Expressive
  General Policies for Classical Planning Domains. AAAI 2025.
- Gupta, N., Pallagani, V., Aydin, J. A., and Srivastava, B. 2026. On
  Sample-Efficient Generalized Planning via Learned Transition Models. ICAPS
  2026. Code:
  <https://github.com/ai4society/state-centric-gen-planning>.
- Taitler, A., Alford, R., Espasa, J., et al. 2024. The 2023 International
  Planning Competition. AI Magazine.
- Silver, T., Yang, R., Curtis, A., Lozano-Perez, T., and Kaelbling, L. P.
  2024. Generalized Planning in PDDL Domains with Pretrained Large Language
  Models. AAAI 2024.
