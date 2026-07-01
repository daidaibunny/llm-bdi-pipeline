# Generalized Planner Routing Taxonomy

This document records the project pivot agreed on 2026-07-01:
the project does not implement a universal generalized planner. It acts as a
caller, router, and AgentSpeak(L) compiler for existing generalized-planning
backends. The research contribution is the backend-selection criterion for a
selected planning family, the normalization of backend output, and the
compilation of the resulting generalized policy into lifted AgentSpeak(L) plan
libraries.

## Classification Unit and Terminology

The unit of analysis in this document is not a bare PDDL domain. It is a
planning family:

```text
planning family = (PDDL domain, goal family, instance distribution)
```

Papers report results by domain name, for example Ferry or Blocks, because
benchmarks are organized by domain directories. However, the assumptions used by
generalized planners are about the problem family induced by a domain and a
goal distribution. The same domain can induce different goal-interaction
structures. For example, Blocks with goal `clear(a)` differs from Blocks with
tower-construction goals such as `on(a,b) & on(b,c)`. Therefore, this document
uses domain names as shorthand for the selected domain-goal family, not as a
claim that the bare domain has a fixed generalized-planning type.

Current terminology:

- Atomic goal item: one ground PDDL fluent required by the problem goal, such
  as `at(ball1,room_b)`, `served(passenger3)`, `clear(a)`, or `on(a,b)`.
  These are state predicates, not actions, trace steps, or synthetic subgoals.
- Positive conjunctive achievement goal: a finite conjunction
  `G = g1 & g2 & ... & gn`, where each `gi` is an atomic goal item. The
  conjunction is over required final-state fluents.
- Goal family: the schema-level pattern that generates those atomic goal items
  across instances, for example "all balls are at the destination room",
  "all passengers are served", or "a tower relation over blocks is achieved".
- Goal interaction: a relation between two atomic goal items caused by PDDL
  action preconditions, add effects, delete effects, mutex facts, resources, or
  structural support relations.
- Ordering constraint: a partial order over atomic goal achievements or module
  calls. For example, with `on(a,b) & on(b,c)`, a Blocks tower family can require
  achieving `on(b,c)` before `on(a,b)` because `on(b,c)` provides structural
  support for the upper relation.
- Routing criterion: the router should use the planning-family structure
  together with backend output compatibility. It does not decide from the PDDL
  domain name alone.

MOOSE illustrates this distinction. Its theoretical assumptions, such as goal
independence and serialisable goal independence, concern how the atomic goal
items in a conjunctive goal can be regressed and achieved. Its experiments are
reported by domain because the benchmark families are stored by domain. In this
document, a MOOSE-routed Ferry family means the Ferry domain with the Ferry goal
family used by the MOOSE benchmark, not every possible Ferry problem.

## Scope

Current scope is positive conjunctive achievement goals. Temporal extended goals
remain a later layer: a DFA controller will decide which achievement condition is
needed next, and the routed domain-level library will realize that condition.

The target artifact remains:

```text
PDDL domain + goal-family training instances
-> routed generalized-planning backend
-> backend-specific generalized plan or policy
-> normalized LiftedPolicyProgram
-> conservative feature/action/subgoal binding
-> lifted AgentSpeak(L) domain-level plan library
```

The router does not claim completeness for arbitrary PDDL. It makes an explicit
backend choice based on the planning-family class and reports when no trusted
backend applies.

## Meaning of "State of the Art"

Generalized planning does not have one universal state-of-the-art solver.
Existing approaches differ by output language and planning-family assumptions:

- Goal-regression decision-list policies target planning families whose atomic
  goal items are goal-separable or serialisable.
- Feature-definable general policies target families that admit a compact
  qualitative feature policy.
- Bounded-width sketches target families with a reusable subgoal decomposition
  whose generated subproblems have bounded width.
- Hierarchical width-reduction policies target families where a sketch can be
  refined into nested lower-width policies or zero-width executable rules.
- Lifted decision-list policy search targets families where a direct lifted
  action-selection policy can guide planning.
- Planning-program synthesis targets families whose solution can be represented
  as a bounded program with loops, jumps, pointers, or registers.
- Neural relational generalized policies provide learned relational baselines
  or feature-discovery signals; they are not deterministic ASL compiler sources
  unless distilled into symbolic rules.

The project should route across these tracks rather than force every domain into
one representation.

## Backend Matrix

| Backend track | Representative paper and citation | Output form | Paper domain evidence | Best routing target | Local status |
| --- | --- | --- | --- | --- | --- |
| Goal regression via MOOSE | Chen, Hofmann, Klassen, and McIlraith, "Satisficing and Optimal Generalised Planning via Goal Regression", AAAI 2026. Code: <https://github.com/DillonZChen/moose>. Dataset: <https://github.com/DillonZChen/moose-dataset>. | First-order condition-to-action decision lists, executable as policy or used for search pruning. | Paper explicitly studies ESHO classical domains `barman`, `ferry`, `gripper`, `logistics`, `miconic`, `rovers`, `satellite`, `transport`, and numeric `numeric-ferry`, `numeric-miconic`, `numeric-minecraft`, `numeric-transport`. It also defines goal-independence style assumptions such as true goal independence, serialisable goal independence, and optimal goal independence. | Planning families whose conjunctive goals can be decomposed into singleton atomic goal items and regressed independently or in a serialisable order. | `.external/moose` pinned at `ce1e99b`; `.external/moose-dataset` pinned at `e009705`. Ferry reproduction already succeeded locally. |
| Learning general policies from examples | Bonet, Drexler, and Geffner, "Learning General Policies from Examples", KR 2025. Code: <https://github.com/bonetblai/learner-policies-from-examples>. | DLPlan feature policies with structural termination certificates. | Paper evaluates 34 domains and divides them into C1-C5. C1-C4 are 20 solved domains: `Blocks4ops-clear`, `Delivery-1pkg`, `Gripper`, `Reward`, `Visitall`, `Childsnack`, `Spanner-1nut`, `Logistics-1truck`, `Barman-1cocktail-1shot`, `Blocks4ops-on`, `Spanner`, `Delivery`, `Ferry`, `Miconic`, `8puzzle-1tile-fixed`, `8puzzle-1tile`, `Blocks4ops`, `Sokoban-1stone-7x7`, `Logistics-1pkg`, `Zenotravel-1plane`. C5 failed domains include `Rovers`, `Depot`, `Satellite`, `Driverlog`, full `Logistics`, and others due to missing feature expressivity or timeout. | Route for planning families where a terminating DLPlan feature policy is learned and verified. The paper's C1-C5 classes provide a failure taxonomy. | `.external/gp-backends/learner-policies-from-examples` pinned at `9991926`; local execution must use Docker because bundled planner libraries are Linux ELF. |
| D2L generalized policy learner | Frances, Bonet, and Geffner, "Learning General Policies from Small Examples Without Supervision", AAAI 2021. Code: <https://github.com/rleap-project/d2l>. | Feature-selected qualitative general policies learned by MaxSAT. | Paper domains include `Qclear`, `Qon`, `Qgrip`, `Qrew`, `Qdeliv`, `Qvisit`, `Qspan`, `Qmicon`, and `Qbw`. The paper explicitly handles Blocksworld variants, Spanner dead ends, Visitall distance features, Miconic, Delivery, and Gripper. | Planning families where a compact policy over DLPlan-style features captures the required goal-interaction structure. Strong reference for Blocks and other goal-dependent structural policies. | `.external/gp-backends/d2l` pinned at `0620e16`; Docker path exists. Treat as backend or baseline after parser/binding adapter verification. |
| Learned policy sketches | Drexler, Seipp, and Geffner, "Learning Sketches for Decomposing Planning Problems into Subproblems of Bounded Width", ICAPS 2022 extended version. Code: <https://github.com/bonetblai/learner-sketches>. Data DOI in paper: <https://doi.org/10.5281/zenodo.6381592>. | Sketch rules `C -> E` over qualitative features; execution requires SIWR/IW search to fill each subproblem. | Paper reports learning over nine domains: `Blocks-clear`, `Blocks-on`, `Childsnack`, `Delivery`, `Gripper`, `Miconic`, `Reward`, `Spanner`, `Visitall`. Testing tables use 30 instances per domain and show width-bounded SIWR behavior. | Planning families with bounded sketch width and reusable subgoal structure, especially where direct one-step policy is too restrictive but subproblems are low width. | `.external/gp-backends/learner-sketches` pinned at `7a7ea6a`. Parser exists. ASL compilation must preserve that sketches are subgoal controllers, not primitive action policies. |
| Hierarchical policy learning / Vanir | Drexler, Seipp, and Geffner, "Learning Hierarchical Policies by Iteratively Reducing the Width of Sketch Rules", KR 2023. Software entry: <https://ml.rwth-aachen.de/software/>. IPC 2023 report describes Vanir as a width-based hierarchical-policy learner. | Hierarchical sketches/policies obtained by repeatedly reducing sketch width until executable zero-width rules are reached. | The local h-policy repository contains learners for `delivery`, `blocks_4_on`, `blocks_4_clear`, `miconic`, `gripper`, `visitall`, `spanner`, and `reward`. The IPC 2023 learning-track report evaluates Vanir as a domain-knowledge generator for a subset of IPC learning-track domains. | Route for families where the learned artifact is hierarchical and can be parsed as module calls. Promotion requires artifact parsing, feature binding, and held-out validation. | `.external/gp-backends/h-policy-learner` pinned at `03e3455`. Currently audit-only; promotion requires `sketch_str.txt` artifacts to pass parser, feature binding, and held-out validation. |
| Handcrafted and learned subgoal-structure sketches | Drexler, Seipp, and Geffner, "Expressing and Exploiting the Common Subgoal Structure of Classical Planning Domains Using Sketches", JAIR 2024; Bonet and Geffner, "General Policies, Subgoal Structure, and Planning Width", JAIR 2024. | Sketches and serializations of bounded width. | JAIR sketch paper studies seven IPC-style domains: `Floortile`, `TPP`, `Barman`, `Grid`, `Childsnack`, `Driverlog`, `Schedule`, plus IPC and Autoscale tests. The JAIR width paper gives the formal basis for bounded width, serialized width, and sketches. | Theory and benchmark guidance for selecting domains that should go to a sketch backend. | Literature only. Use to justify routing classes and to define fallback when learner-sketches cannot produce a safe executable policy. |
| PG3 policy-guided generalized policy search | Yang, Silver, Curtis, Lozano-Perez, and Kaelbling, "PG3: Policy-Guided Planning for Generalized Policy Generation", IJCAI 2022. Code: <https://github.com/ryangpeixu/pg3>. | Goal-conditioned lifted decision-list policies. | Paper evaluates six PDDL domains: `Delivery`, `Gripper`, `Miconic`, `Ferry`, `Spanner`, and `Forest`. Table results show PG3 solving all six in the reported evaluation. | Route for planning families where a direct lifted decision-list action policy is the accepted backend artifact. | Downloaded and pinned in `.external/gp-backends/pg3` at `61496456c89ebccc66ba83679ba0e363232f6ac0`. Audit-only until a lifted decision-list to `LiftedPolicyProgram` adapter exists. |
| Planning-program synthesis: BFGP, PGP(v), lifted helpful actions | Segovia-Aguas, Jimenez, and Jonsson, "Generalized Planning as Heuristic Search", 2021; Segovia-Aguas et al., "Computing Programs for Generalized Planning as Heuristic Search", 2022; Lei, Lipovetzky, and Ehinger, "Novelty and Lifted Helpful Actions in Generalized Planning", 2023; Gomez and Segovia-Aguas, "Parallel Strategies for Best-First Generalized Planning", 2024. | Planning programs with loops, jumps, pointers, and RAM-like operations. | Reported domains include STRIPS program-synthesis benchmarks such as `Corridor`, `Gripper`, `Lock`, `Ontable`, `Spanner`, `Visitall`, and numeric/program domains such as `Fibo`, `Find`, `Reverse`, `Select`, `Sorting`, and `Triangular Sum`. Lei et al. describe PGP guided by landmark heuristics as the then state of the art and improve it with novelty and lifted helpful actions. | Route for loop, pointer, register, or indexable program families. ASL use requires a planning-program-to-ASL adapter. | Downloaded and pinned: `best-first-generalized-planning`, `bfgp-pp`, `pgp-landmarks`, and `up-bfgp`. Audit/baseline-only until a planning-program-to-ASL adapter exists. |
| Policy reuse and modular policies | Bonet, Drexler, and Geffner, "On Policy Reuse: An Expressive Language for Representing and Executing General Policies that Call Other Policies", ICAPS 2024. Data DOI in paper: <https://doi.org/10.5281/zenodo.10814690>. | Module language where policies/sketches call other policies/sketches with parameters, memory states, and indexical features. | Paper examples focus on reusable modules such as Blocksworld `on(X,Y)`, `tower(O,X)`, and `blocks(O)`. It is representation work, not a full learner. | Best theoretical match to ASL module calls, especially for Blocksworld tower construction. Use as compiler target inspiration, not as a standalone learner route. | Literature only. Should inform `LiftedPolicyProgram -> ASL` compiler design. |
| Relational graph-neural general policies | Stahlberg, Bonet, and Geffner, "Learning General Optimal Policies with Graph Neural Networks: Expressive Power, Transparency, and Limits", KR 2022. Code: <https://github.com/simon-stahlberg/mimir-rgnn>. Follow-up work includes "Learning More Expressive General Policies for Classical Planning Domains", AAAI 2025. | Neural relational value or policy functions over PDDL states, sometimes analyzed or distilled into symbolic structure. | KR 2022 studies tractable generalized-planning domains and focuses on expressive limits of relational graph neural networks. The AAAI 2025 follow-up reports R-GNN[t] and Edge Transformer experiments on domains such as `Blocks`, `Grid`, `Gripper`, `Logistics`, `Miconic`, `Rovers`, `Vacuum`, and `Visitall`. | Neural baseline and feature-discovery reference. ASL compilation requires symbolic certification or distillation. | Downloaded and pinned in `.external/gp-backends/mimir-rgnn` at `ea3089713c18ab1d7faf1a7f5ecddb4f5acdcbab`. Audit-only. |
| State-centric learned transition models | Gupta, Pallagani, Aydin, and Srivastava, "On Sample-Efficient Generalized Planning via Learned Transition Models", ICAPS 2026. Code: <https://github.com/ai4society/state-centric-gen-planning>. | Learned transition models that roll out symbolic state trajectories and decode valid successors. | Repository reports domains such as Blocks and provides Fast Downward, VAL, Pyperplan, and WLPlan based data-generation and evaluation scripts. | Neural baseline for planning-family generalization through learned transition dynamics. It is not a direct ASL compiler backend. | Downloaded and pinned in `.external/gp-backends/state-centric-gen-planning` at `03a61f587ea5a2745192225a1d0be19ca045a774`. Audit-only. |
| IPC learning-track domain-knowledge systems | IPC 2023 learning track systems such as HUZAR and Vanir, reported in "The 2023 International Planning Competition". | Learned domain knowledge for classical planners; output is not always a standalone generalized plan. | The IPC report compares systems on many planning domains. Vanir targets polynomial domains; HUZAR won the learning track overall. | Comparator for learned planner-domain knowledge. ASL use requires emitted knowledge with a parseable symbolic policy form. | Downloaded and pinned `ipc-learning-huzar` and `ipc-learning-pgp-baseline`. Audit/baseline-only. |
| LLM-generated generalized planning programs | Silver et al., "Generalized Planning in PDDL Domains with Pretrained Large Language Models", AAAI 2024. | Python programs synthesized from PDDL and example tasks. | Paper evaluates seven domains: `Delivery`, `Forest`, `Gripper`, `Miconic`, `Ferry`, `Spanner`, and `Heavy`. GPT-4 solves Delivery, Forest, Gripper, Ferry, and Heavy in the reported setting, but not Miconic and Spanner; PG3 remains the symbolic comparator. | Baseline for code-generation approaches. It is not a deterministic GP backend for ASL compilation. | Downloaded and pinned in `.external/gp-backends/llm-genplan` at `a2b8baa7153d5a8f2df51fbc72c51def80ddc169`. Audit-only. |

## Paper-Code Capability Confirmation

The confirmation below distinguishes source-code completeness from full local
paper-result reproduction. A backend marked source-complete has the official or
trusted paper code, the declared entrypoints, and the expected benchmark or
experiment structure. It does not mean that the full paper table has been
re-run locally under the original resource limits. That full reproduction is a
separate experiment task.

Machine-readable status is exposed by:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/gp_backend_audit.py capability
```

| Backend or paper line | Capability confirmation | What is confirmed | Remaining reproduction or routing gap |
| --- | --- | --- | --- |
| MOOSE | `confirmed_exact_reproduction_ready` | Official repo, local image, dataset, VAL integration, and prior Ferry reproduction are present. | Full synthesis under the original 32GB and 12h budget is not re-run by the lightweight audit. |
| learner-sketches | `confirmed_paper_source_complete` | Official source, learning entrypoint, benchmark folders, and learning/testing scripts are present. | Full ICAPS tables are not re-run; ASL compilation must preserve sketch subproblem semantics. |
| h-policy-learner / Vanir-style hierarchy | `confirmed_paper_source_complete` | Official source, hierarchy-learning scripts, testing scripts, and reported benchmark folders are present. | Exact cluster-scale experiments are not re-run; generated hierarchy artifacts still need verified ASL binding. |
| D2L | `confirmed_source_complete_needs_paper_environment` | Official source, Dockerfile, experiment runner, and paper experiment names are present. | Full AAAI table reproduction depends on the original planner and MaxSAT stack. |
| learner-policies-from-examples | `confirmed_source_complete_needs_paper_environment` | Official KR source, final-paper commit note, learning entrypoint, and benchmark folders are present. | Linux planner libraries require Docker; full KR matrix is not part of the lightweight audit. |
| PG3 | `confirmed_paper_source_complete` | Official source, main Python entrypoint, run script, and README reproduction guidance are present. | Full training budget is not re-run; decision-list policy to ASL adapter is not implemented. |
| best-first-generalized-planning | `confirmed_paper_source_complete` | Official source, generators, synthesis command, validator, and ICAPS experiment script are present. | C++ build and full experiments are not re-run; planning-program to ASL adapter is missing. |
| BFGP++ | `confirmed_paper_source_complete` | Official source, compile script, synthesis, validation, and repair modes are present. | Structured program to ASL adapter is missing. |
| PGP-landmarks | `confirmed_paper_source_complete` | Official source, landmark-guided PGP entrypoints, paper scripts, generators, and validator are present. | SoCS experiment script is not re-run; planning-program to ASL adapter is missing. |
| SLTP | `confirmed_source_complete_needs_paper_environment` | Official source, sampling, feature generation, learning pipeline, and Docker usage are documented. | Legacy FS/OpenWBO dependencies are required; no direct ASL compiler route. |
| UP-BFGP | `confirmed_library_or_interface_only` | Official interface source for BFGP++ inside Unified Planning is present. | It is not a standalone generalized-planning paper artifact. |
| Policy reuse and modular policies | Reference-only | This is a representation paper for modular policies and policy calls. | No standalone learner backend is used; it informs the ASL compiler target language. |
| JAIR sketch / width theory | Reference-only | This line provides accepted theory and benchmark framing for sketch width and subgoal structure. | No separate runnable backend beyond learner-sketches / h-policy is claimed. |
| mimir-rgnn | `confirmed_library_or_interface_only` | Official R-GNN planning library and PDDL integration are present. | Full experiment pipeline/checkpoints are not bundled as a direct symbolic GP backend; no ASL distillation. |
| state-centric transition models | `confirmed_source_complete_needs_paper_environment` | Official implementation, data generation, training, inference, and aggregation entrypoints are present. | Checkpoints are external release artifacts; output is a neural transition model, not lifted ASL. |
| IPC HUZAR | `confirmed_competition_artifact_only` | IPC learning-track repository, Apptainer recipes, symbolic planner, and graph-neural components are present. | Emits planner domain knowledge, not a standalone generalized policy. |
| IPC PGP baseline | `confirmed_competition_artifact_only` | IPC baseline repository and learn/plan Apptainer flow are present. | It is a competition flow; planning-program to ASL adapter is missing. |
| LLM-GenPlan | `confirmed_paper_source_complete` | Official source, CI, cached-log reproduction script, and cached chat-log directory are present. | Full cached reproduction is long-running; Python program output is not directly ASL. |

## Paper Planning-Family Classifications Worth Reusing

We should reuse prior classifications rather than invent informal labels.

### MOOSE classes

MOOSE reports experiments by benchmark domain, but its goal-independence
assumptions explain when goal regression works for a planning family:

- True goal independence.
- Serialisable goal independence.
- Optimal goal independence.
- ESHO benchmark families, using the paper's term for families where satisficing
  plans are available but optimality remains computationally demanding.

Routing implication: try MOOSE when the selected goal family is
goal-regression decomposable: the atomic goal items can be solved as singleton
goals in an independent or serialisable order. Do not route MOOSE to
Sussman-anomaly-style goal families such as unrestricted Blocksworld tower
construction.

### KR 2025 policy-learning classes

KR 2025 gives an empirical classification:

- C1: one call to the learner, first plan sufficient, no extra transitions.
- C2: first plan sufficient, but extra good or bad transitions are needed.
- C3: one plan sufficient, but not the first considered plan.
- C4: requires second wrapper strategy over more than one example path.
- C5: no general policy found, due to feature-pool edge failures or timeout.

Routing implication: KR 2025 can be used either as a policy backend or as a
diagnostic backend. If a planning family falls into C5 in the paper, support
requires a new feature language, a different backend, or a documented
out-of-scope decision.

### Sketch and width classes

The sketch literature uses:

- Problem width.
- Satisficing width.
- Serialized width.
- Sketch width.
- Terminating or acyclic sketches.

Routing implication: if a planning family is known to have a compact
bounded-width sketch, route to learner-sketches or a sketch executor. The output
is a subgoal decomposition; execution requires low-width search or a subgoal
executor.

### Feature-definable policy classes

D2L and KR 2025 use DLPlan-style concepts, roles, counts, distances, and goal
predicates. They apply when the required abstraction is expressible by a finite
set of lifted qualitative features generated by the backend.

Routing implication: route planning families such as Blocks, Visitall, Spanner,
Delivery, and restricted Logistics to D2L or KR 2025 when their goal-interaction
structure is feature-definable.

### Planning-program classes

BFGP and PGP operate over planning programs with loops, jumps, and pointers.
These are suitable for fixed-goal algorithmic tasks, object-indexed loops, and
numeric/list-style benchmarks.

Routing implication: keep as a separate future route. It is not the primary
route for domain-level ASL predicate-goal libraries because its output language
does not match AgentSpeak(L) predicate-goal module syntax such as `+!on(X,Y)` or
`+!clear(X)`.

## Proposed Project Planning-Family Routing Classes

The following classes are route-oriented, not claims about universal domain
complexity. Each class refers to a selected domain-goal family, not to every
possible problem over a bare PDDL domain. Each class has a primary backend and
fallback backends.

### Class A: Goal-regression-decomposable domain-goal families

Property:

- Positive conjunctive goals decompose into singleton atomic goal items.
- There exists an independent or serialisable order in which singleton goal
  regressions remain valid for the selected family.
- The route may use a fixed, learned, or regression-derived order over atomic
  goal items.
- This aligns with MOOSE true/serialisable/optimal goal independence.

Primary backend:

- MOOSE.

Fallbacks:

- PG3 for domains in the PG3 paper.
- KR 2025 if MOOSE fails but a feature policy exists.

Recommended project domains:

| Domain | Source | Reason |
| --- | --- | --- |
| `ferry` | MOOSE dataset or IPC/PDDL source | Selected family: cars-at-destinations goals. MOOSE paper and local reproduction provide direct backend evidence. |
| `gripper` | IPC 1998 via `potassco/pddl-instances` | Selected family: balls-at-destination-room goals. Appears in MOOSE, PG3, D2L, learner-sketches, KR 2025. |
| `miconic` | IPC 2000 elevator simple typed via `potassco/pddl-instances` | Selected family: passenger-served goals. Appears in MOOSE, PG3, D2L, learner-sketches, KR 2025. |
| `logistics` | IPC 2000 logistics typed via `potassco/pddl-instances` | Selected family: packages-at-destinations goals. MOOSE studies full Logistics; KR 2025 solves restricted variants and marks full Logistics as C5. |

### Class B: Bounded-width sketchable subgoal-structure families

Property:

- A compact sketch can decompose the selected goal family into subproblems of
  bounded width.
- The backend may need SIWR/IW to fill holes.
- The learned artifact may be a sketch rather than a direct one-step policy.

Primary backend:

- learner-sketches.

Fallbacks:

- KR 2025 when a direct structurally terminating policy is found.
- D2L for domains from the AAAI 2021 feature-policy experiments.

Recommended project domains:

| Domain | Source | Reason |
| --- | --- | --- |
| `delivery` | learner-sketches/D2L/PG3 benchmark source or AI-Planning generator | Selected family: package-delivery goals. Central example in sketch and feature-policy theory; also in PG3. |
| `spanner` | IPC 2011 or learner-sketches/D2L source | Selected family: nut-tightening goals under tool/resource constraints. Appears in D2L, learner-sketches, PG3, KR 2025. |
| `visitall` | IPC 2011 via `potassco/pddl-instances` | Selected family: all-cells-visited goals. Appears in D2L, learner-sketches, KR 2025, BFGP/PGP. |
| `childsnack` | IPC 2014 via `potassco/pddl-instances` | Selected family: children-served goals. Sketch literature proves a width-1 sketch; KR 2025 learns a policy but has weaker large-instance coverage. |
| `barman` | IPC 2011 via `potassco/pddl-instances` | Selected family: drink-preparation goals. JAIR sketch work gives a Barman sketch; KR 2025 solves restricted variants and reports failure on broader variants. |

### Class C: Feature-definable structural and goal-dependent families

Property:

- At least one atomic goal item supports, threatens, or orders another atomic
  goal item in the selected family.
- A compact policy exists only with goal-aware features, indexical concepts,
  distance/count features, or reusable modules.
- This is where Blocks-style goal dependency belongs.

Primary backends:

- KR 2025 learning-general-policies-from-examples.
- D2L for smaller feature-definable policies.

Compiler guidance:

- Use policy-reuse / modular-policy work as the ASL target model. Its modules
  such as `on(X,Y)`, `tower(O,X)`, and `blocks(O)` are close to lifted ASL
  plans.

Recommended project domains:

| Domain | Source | Reason |
| --- | --- | --- |
| `blocks` | IPC 2000 typed Blocks via `potassco/pddl-instances`; Blocks variants also in D2L and KR 2025 | Selected family: clear/on/tower-construction goals. D2L handles `Qclear`, `Qon`, and `Qbw`; KR 2025 solves `Blocks4ops-clear`, `Blocks4ops-on`, and `Blocks4ops`. |
| `8puzzle-1tile` | KR 2025 benchmark source | Selected family: tile-position goals. KR 2025 solves both fixed and non-fixed variants; the family tests structural rearrangement. |
| `sokoban-1stone` | KR 2025 benchmark source and Sokoban IPC variants | Selected family: one-stone-at-target goals. KR 2025 solves `Sokoban-1stone-7x7` but with high cost and overfitting risk. |

Domains to demote from primary support:

| Domain | Reason |
| --- | --- |
| `depots` | KR 2025 reports `Depot` in C5 with feature-pool edge failure. It is a boundary/failure-analysis family unless a backend or feature language supports it. |
| `rovers`, `satellite`, full `transport` | MOOSE studies these, but KR 2025 C5 and our previous route/reachability issues suggest they require richer route, instrument, resource, or transitive-closure reasoning. Treat as boundary domains. |
| full `logistics` | MOOSE supports it, but KR 2025 reports full `Logistics` in C5 while solving restricted variants. Keep it in Class A as a MOOSE route, but mark it as a cross-backend boundary. |

## Recommended Formal Benchmark Set

For the next paper-quality routing evaluation, use 12 primary domains:

| Class | Domains | Primary route |
| --- | --- | --- |
| Class A: goal-regression-decomposable domain-goal families | `ferry`, `gripper`, `miconic`, `logistics` | MOOSE |
| Class B: bounded-width sketchable subgoal-structure families | `delivery`, `spanner`, `visitall`, `childsnack`, `barman` | learner-sketches, then KR 2025/D2L fallback |
| Class C: feature-definable structural and goal-dependent families | `blocks`, `8puzzle-1tile`, `sokoban-1stone` | KR 2025, then D2L fallback |

This set is the formal routing corpus. It is selected for backend-routing
evidence and ASL compilability, not for the earlier hand-built Layer B/C
architecture.

Keep `depots`, `rovers`, `satellite`, `transport`, `driverlog`, and full
`zenotravel` as boundary domains.

## Download and Provenance Plan

Use official IPC or reputable paper repositories. Do not mix ad hoc generated
problems into formal benchmarks unless the generator is the official paper or
IPC generator.

| Source | URL | Local commit/status | Use |
| --- | --- | --- | --- |
| `potassco/pddl-instances` | <https://github.com/potassco/pddl-instances> | `cf19edf7c53d1540ddbb396c642595e0926ee552` | Primary IPC source for `gripper`, `miconic`, `logistics`, `blocks`, `barman`, `childsnack`, `visitall`, and IPC variants such as `spanner` or `sokoban` when available. |
| `AI-Planning/classical-domains` | <https://github.com/AI-Planning/classical-domains> | `4bd0b42d89ea02bd38af6f93cf20a0ab0cbda9d9` | Secondary official-style PDDL source for domains missing from `potassco/pddl-instances`. |
| `AI-Planning/pddl-generators` | <https://github.com/AI-Planning/pddl-generators> | `d5c22c9ab21ecaf90db82daf2a0537973c661009` | Reputable generator source for generated families such as Delivery or Spanner when paper benchmarks use generators. |
| `aibasel/downward-benchmarks` | <https://github.com/aibasel/downward-benchmarks> | `8302319bb3800daae88aef76d86b581a2e7988ab` | Fast Downward benchmark source used by several planning papers. |
| MOOSE dataset | <https://github.com/DillonZChen/moose-dataset> | `e00970516154e9042b783a4613a1ed7286c9beee` | Exact MOOSE paper benchmark source for Class A reproduction. |
| learner-sketches benchmarks | <https://github.com/bonetblai/learner-sketches> | `7a7ea6a6356035afa16ed958b53d8edc86994e0a` | Paper benchmark/source for learned sketches. |
| D2L benchmarks | <https://github.com/rleap-project/d2l> | `0620e169c894d79b3c84f435dba1462996f7c270` | AAAI 2021 feature-policy benchmark definitions. |
| KR 2025 benchmarks | <https://github.com/bonetblai/learner-policies-from-examples> | `9991926f7655c4b6c8dc2f0404123639e42056f2` | Source for KR 2025 C1-C5 benchmark taxonomy and structural-policy domains. |

## Router Design

The router is evidence-driven and conservative.

1. Read domain metadata from the benchmark registry. Initially, use explicit
   planning-family annotations rather than pretending that static PDDL analysis
   of a bare domain can perfectly infer the selected generalized planner.
2. Run a bounded backend probe on a small training subset under memory and
   time limits.
3. Accept a backend only if it emits a generalized artifact and the artifact
   passes our parser, feature-binding, and held-out validation gates.
4. Normalize accepted backend output into `LiftedPolicyProgram`.
5. Compile only bound predicates, primitive actions, and predicate subgoal calls
   into ASL. Do not invent `achieve_*`, `transition_*`, or hidden synthetic
   subgoals.
6. If all routes fail, mark the domain unsupported and report the backend
   failure reasons.

Suggested route order:

```text
Class A:
	MOOSE -> PG3 if available -> KR 2025

Class B:
	learner-sketches -> h-policy/Vanir -> KR 2025 -> D2L

Class C:
	KR 2025 -> D2L -> policy-reuse compiler patterns if a module policy is supplied

Boundary/program domains:
	BFGP/PGP(v) only after a planning-program-to-ASL adapter exists
```

## Implications for the Current Repository

1. The previous hand-built generalized planner is a baseline, not the main
   method.
2. The formal achievement-goal corpus is the 12-domain-goal-family routing
   taxonomy above.
3. `depots` remains boundary/failure-analysis unless a backend actually solves
   it and the result passes ASL compilation plus held-out validation.
4. The main implementation work is backend adapters and ASL compilers:
   MOOSE policy -> `LiftedPolicyProgram`, KR/D2L DLPlan policy ->
   `LiftedPolicyProgram`, learner-sketches sketch -> `LiftedPolicyProgram`
   with explicit subproblem semantics, then ASL.
5. h-policy/Vanir is the next backend-adapter target because its hierarchical
   policy output has explicit policy calls. It requires artifact parsing and
   validation before becoming a claimed route.

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
  2026. Code: <https://github.com/ai4society/state-centric-gen-planning>.
- Taitler, A., Alford, R., Espasa, J., et al. 2024. The 2023 International
  Planning Competition. AI Magazine.
- Silver, T., Yang, R., Curtis, A., Lozano-Perez, T., and Kaelbling, L. P.
  2024. Generalized Planning in PDDL Domains with Pretrained Large Language
  Models. AAAI 2024.
