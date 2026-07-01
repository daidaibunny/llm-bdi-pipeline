# Generalized Planner Routing Taxonomy

This document records the project pivot agreed on 2026-07-01:
we should not invent a universal generalized planner. The project should become a
caller, router, and AgentSpeak(L) compiler for existing state-of-the-art
generalized-planning backends. The research contribution should be in choosing the
right generalized planner for the right domain class, normalizing its output, and
compiling the resulting domain-level generalized policy into lifted AgentSpeak(L)
plan libraries.

## Scope

Current scope is positive conjunctive achievement goals. Temporal extended goals
remain a later layer: a DFA controller will decide which achievement condition is
needed next, and the routed domain-level library will realize that condition.

The target artifact remains:

```text
PDDL domain + training instances
-> routed generalized-planning backend
-> backend-specific generalized plan or policy
-> normalized LiftedPolicyProgram
-> conservative feature/action/subgoal binding
-> lifted AgentSpeak(L) domain-level plan library
```

The router should not claim completeness for arbitrary PDDL. It should make an
explicit backend choice based on the domain class and report when no trusted
backend applies.

## Meaning of "State of the Art"

Generalized planning does not have one universal state-of-the-art solver. The
strongest work is split by output language and domain assumptions:

- Goal-regression decision-list policies: strong for goal-separable or
  serialisable domains.
- Feature-definable general policies: strong when a compact qualitative feature
  policy exists.
- Bounded-width sketches: strong when the domain has reusable subgoal structure
  and SIWR can fill the low-width subproblems.
- Hierarchical width-reduction policies: strong when a sketch can be refined
  into nested lower-width policies or zero-width executable rules.
- Lifted decision-list policy search: strong when direct action-selection
  policies can guide planning.
- Planning-program synthesis: strong when the solution is naturally a loop or
  pointer/index program, but its output is less directly aligned with ASL.
- Neural relational generalized policies: useful as a strong learning baseline
  or feature-discovery reference, but less suitable as a deterministic ASL
  compiler source unless the neural policy is distilled into symbolic rules.

The project should route across these tracks rather than force every domain into
one representation.

## Backend Matrix

| Backend track | Representative paper and citation | Output form | Paper domain evidence | Best routing target | Local status |
| --- | --- | --- | --- | --- | --- |
| Goal regression via MOOSE | Chen, Hofmann, Klassen, and McIlraith, "Satisficing and Optimal Generalised Planning via Goal Regression", AAAI 2026. Code: <https://github.com/DillonZChen/moose>. Dataset: <https://github.com/DillonZChen/moose-dataset>. | First-order condition-to-action decision lists, executable as policy or used for search pruning. | Paper explicitly studies ESHO classical domains `barman`, `ferry`, `gripper`, `logistics`, `miconic`, `rovers`, `satellite`, `transport`, and numeric `numeric-ferry`, `numeric-miconic`, `numeric-minecraft`, `numeric-transport`. It also defines goal-independence style assumptions such as true goal independence, serialisable goal independence, and optimal goal independence. | Domains whose conjunctive goals can be decomposed into singleton goals without severe interaction, or whose goal order can be serialised by regression. | `.external/moose` pinned at `ce1e99b`; `.external/moose-dataset` pinned at `e009705`. Ferry reproduction already succeeded locally. |
| Learning general policies from examples | Bonet, Drexler, and Geffner, "Learning General Policies from Examples", KR 2025. Code: <https://github.com/bonetblai/learner-policies-from-examples>. | DLPlan feature policies with structural termination certificates. | Paper evaluates 34 domains and divides them into C1-C5. C1-C4 are 20 solved domains: `Blocks4ops-clear`, `Delivery-1pkg`, `Gripper`, `Reward`, `Visitall`, `Childsnack`, `Spanner-1nut`, `Logistics-1truck`, `Barman-1cocktail-1shot`, `Blocks4ops-on`, `Spanner`, `Delivery`, `Ferry`, `Miconic`, `8puzzle-1tile-fixed`, `8puzzle-1tile`, `Blocks4ops`, `Sokoban-1stone-7x7`, `Logistics-1pkg`, `Zenotravel-1plane`. C5 failed domains include `Rovers`, `Depot`, `Satellite`, `Driverlog`, full `Logistics`, and others due to missing feature expressivity or timeout. | Primary candidate for feature-definable terminating policies, especially when we need an honest failure reason. Good route for Blocks variants, Delivery, Visitall, Spanner, Ferry, Miconic, restricted Logistics, and restricted Barman. | `.external/gp-backends/learner-policies-from-examples` pinned at `9991926`; local execution must use Docker because bundled planner libraries are Linux ELF. |
| D2L generalized policy learner | Frances, Bonet, and Geffner, "Learning General Policies from Small Examples Without Supervision", AAAI 2021. Code: <https://github.com/rleap-project/d2l>. | Feature-selected qualitative general policies learned by MaxSAT. | Paper domains include `Qclear`, `Qon`, `Qgrip`, `Qrew`, `Qdeliv`, `Qvisit`, `Qspan`, `Qmicon`, and `Qbw`. The paper explicitly handles Blocksworld variants, Spanner dead ends, Visitall distance features, Miconic, Delivery, and Gripper. | Feature-definable domains where a compact policy over DLPlan-style features exists. Strong reference for Blocks and other goal-dependent structural policies. | `.external/gp-backends/d2l` pinned at `0620e16`; Docker path exists. Treat as backend or baseline after parser/binding adapter verification. |
| Learned policy sketches | Drexler, Seipp, and Geffner, "Learning Sketches for Decomposing Planning Problems into Subproblems of Bounded Width", ICAPS 2022 extended version. Code: <https://github.com/bonetblai/learner-sketches>. Data DOI in paper: <https://doi.org/10.5281/zenodo.6381592>. | Sketch rules `C -> E` over qualitative features; execution requires SIWR/IW search to fill each subproblem. | Paper reports learning over nine domains: `Blocks-clear`, `Blocks-on`, `Childsnack`, `Delivery`, `Gripper`, `Miconic`, `Reward`, `Spanner`, `Visitall`. Testing tables use 30 instances per domain and show width-bounded SIWR behavior. | Domains with bounded sketch width and reusable subgoal structure, especially where direct one-step policy is too restrictive but subproblems are low width. | `.external/gp-backends/learner-sketches` pinned at `7a7ea6a`. Parser exists. ASL compilation must preserve that sketches are subgoal controllers, not primitive action policies. |
| Hierarchical policy learning / Vanir | Drexler, Seipp, and Geffner, "Learning Hierarchical Policies by Iteratively Reducing the Width of Sketch Rules", KR 2023. Software entry: <https://ml.rwth-aachen.de/software/>. IPC 2023 report describes Vanir as a width-based hierarchical-policy learner. | Hierarchical sketches/policies obtained by repeatedly reducing sketch width until executable zero-width rules are reached. | The local h-policy repository contains learners for `delivery`, `blocks_4_on`, `blocks_4_clear`, `miconic`, `gripper`, `visitall`, `spanner`, and `reward`. The IPC 2023 learning-track report says Vanir produced fewer domain-knowledge files than some competitors but with high quality, including best quality in `Ferry`, `Rovers`, and `Satellite`. | Strong candidate for ASL because hierarchy and policy calls are closer to BDI modules than flat sketches. Best as a route for bounded-width or modular domains after the backend artifact parser is verified. | `.external/gp-backends/h-policy-learner` pinned at `03e3455`. Currently audit-only; should be promoted only after `sketch_str.txt` artifacts pass parser, feature binding, and held-out validation. |
| Handcrafted and learned subgoal-structure sketches | Drexler, Seipp, and Geffner, "Expressing and Exploiting the Common Subgoal Structure of Classical Planning Domains Using Sketches", JAIR 2024; Bonet and Geffner, "General Policies, Subgoal Structure, and Planning Width", JAIR 2024. | Sketches and serializations of bounded width. | JAIR sketch paper studies seven IPC-style domains: `Floortile`, `TPP`, `Barman`, `Grid`, `Childsnack`, `Driverlog`, `Schedule`, plus IPC and Autoscale tests. The JAIR width paper gives the formal basis for bounded width, serialized width, and sketches. | Theory and benchmark guidance for selecting domains that should go to a sketch backend. | Literature only. Use to justify routing classes and to define fallback when learner-sketches cannot produce a safe executable policy. |
| PG3 policy-guided generalized policy search | Yang, Silver, Curtis, Lozano-Perez, and Kaelbling, "PG3: Policy-Guided Planning for Generalized Policy Generation", IJCAI 2022. Code: <https://github.com/ryangpeixu/pg3>. | Goal-conditioned lifted decision-list policies. | Paper evaluates six PDDL domains: `Delivery`, `Gripper`, `Miconic`, `Ferry`, `Spanner`, and `Forest`. Table results show PG3 solving all six in the reported evaluation. | Candidate router for domains where a direct lifted decision-list action policy is expected and where planner-guided policy search is useful. | No local backend currently pinned. Need code audit before using as a production route. |
| Planning-program synthesis: BFGP, PGP(v), lifted helpful actions | Segovia-Aguas, Jimenez, and Jonsson, "Generalized Planning as Heuristic Search", 2021; Segovia-Aguas et al., "Computing Programs for Generalized Planning as Heuristic Search", 2022; Lei, Lipovetzky, and Ehinger, "Novelty and Lifted Helpful Actions in Generalized Planning", 2023; Gomez and Segovia-Aguas, "Parallel Strategies for Best-First Generalized Planning", 2024. | Planning programs with loops, jumps, pointers, and RAM-like operations. | Reported domains include STRIPS program-synthesis benchmarks such as `Corridor`, `Gripper`, `Lock`, `Ontable`, `Spanner`, `Visitall`, and numeric/program domains such as `Fibo`, `Find`, `Reverse`, `Select`, `Sorting`, and `Triangular Sum`. Lei et al. describe PGP guided by landmark heuristics as the then state of the art and improve it with novelty and lifted helpful actions. | Loop-heavy or pointer/indexable tasks where a program is natural. Not the first ASL route because translating RAM-like programs into predicate-goal ASL modules is nontrivial. | Literature only. Useful as related work and possible future route for loop/program domains. |
| Policy reuse and modular policies | Bonet, Drexler, and Geffner, "On Policy Reuse: An Expressive Language for Representing and Executing General Policies that Call Other Policies", ICAPS 2024. Data DOI in paper: <https://doi.org/10.5281/zenodo.10814690>. | Module language where policies/sketches call other policies/sketches with parameters, memory states, and indexical features. | Paper examples focus on reusable modules such as Blocksworld `on(X,Y)`, `tower(O,X)`, and `blocks(O)`. It is representation work, not a full learner. | Best theoretical match to ASL module calls, especially for Blocksworld tower construction. Use as compiler target inspiration, not as a standalone learner route. | Literature only. Should inform `LiftedPolicyProgram -> ASL` compiler design. |
| Relational graph-neural general policies | Stahlberg, Bonet, and Geffner, "Learning General Optimal Policies with Graph Neural Networks: Expressive Power, Transparency, and Limits", KR 2022. Code: <https://github.com/simon-stahlberg/mimir-rgnn>. Follow-up work includes "Learning More Expressive General Policies for Classical Planning Domains", AAAI 2025. | Neural relational value or policy functions over PDDL states, sometimes analyzed or distilled into symbolic structure. | KR 2022 studies tractable generalized-planning domains and focuses on expressive limits of relational graph neural networks. The AAAI 2025 follow-up reports R-GNN[t] and Edge Transformer experiments on domains such as `Blocks`, `Grid`, `Gripper`, `Logistics`, `Miconic`, `Rovers`, `Vacuum`, and `Visitall`. | Strong learning baseline and possible feature-discovery route. It should not be a primary ASL compiler backend until the neural policy can be certified or distilled into symbolic action/subgoal rules. | No local backend pinned. Keep as related work or optional experimental baseline. |
| IPC learning-track domain-knowledge systems | IPC 2023 learning track systems such as HUZAR and Vanir, reported in "The 2023 International Planning Competition". | Learned domain knowledge for classical planners, not necessarily standalone generalized plans. | The IPC report compares systems on many planning domains. Vanir specifically targets polynomial domains and generated high-quality knowledge on a smaller set; HUZAR won the learning track overall. | Useful comparator for "learned domain knowledge improves planning"; not a direct route to lifted ASL unless the emitted knowledge has a parseable symbolic policy form. | No adapter. Use as context when discussing why our routing problem is broader than a single GP solver. |
| LLM-generated generalized planning programs | Silver et al., "Generalized Planning in PDDL Domains with Pretrained Large Language Models", AAAI 2024. | Python programs synthesized from PDDL and example tasks. | Paper evaluates seven domains: `Delivery`, `Forest`, `Gripper`, `Miconic`, `Ferry`, `Spanner`, and `Heavy`. GPT-4 is strong on Delivery, Forest, Gripper, Ferry, Heavy, weak on Miconic and Spanner; PG3 remains a strong baseline. | Baseline or auxiliary heuristic, not a default paper-quality route. It is not a stable, deterministic GP backend. | Literature only. Do not make it a primary route unless the paper explicitly studies LLM-assisted routing. |

## Paper Domain Classifications Worth Reusing

We should reuse prior classifications rather than invent informal labels.

### MOOSE classes

MOOSE uses goal-independence assumptions to explain when goal regression works:

- True goal independence.
- Serialisable goal independence.
- Optimal goal independence.
- Easy-to-solve, hard-to-optimise domains.

Routing implication: try MOOSE when the domain looks goal-regression friendly,
especially if goals can be solved as singleton atoms in a stable order. Do not
force MOOSE onto Sussman-anomaly-style domains such as unrestricted
Blocksworld.

### KR 2025 policy-learning classes

KR 2025 gives a useful empirical classification:

- C1: one call to the learner, first plan sufficient, no extra transitions.
- C2: first plan sufficient, but extra good or bad transitions are needed.
- C3: one plan sufficient, but not the first considered plan.
- C4: requires second wrapper strategy over more than one example path.
- C5: no general policy found, due to feature-pool edge failures or timeout.

Routing implication: KR 2025 is valuable because it can both solve and diagnose.
If a domain falls into C5 in the paper, we should not claim support without new
feature expressivity.

### Sketch and width classes

The sketch literature uses:

- Problem width.
- Satisficing width.
- Serialized width.
- Sketch width.
- Terminating or acyclic sketches.

Routing implication: if a domain is known to have a compact bounded-width sketch,
route to learner-sketches or a sketch executor. The output is not necessarily a
primitive-action policy; it is a subgoal decomposition that needs low-width
search or a subgoal executor.

### Feature-definable policy classes

D2L and KR 2025 use DLPlan-style concepts, roles, counts, distances, and goal
predicates. They are best for domains where the right abstraction can be
expressed by a small set of lifted qualitative features.

Routing implication: route Blocks, Visitall, Spanner, Delivery, restricted
Logistics, and similar domains to D2L or KR 2025 before trying ad hoc schema
synthesis.

### Planning-program classes

BFGP and PGP operate over planning programs with loops, jumps, and pointers.
These are suitable for fixed-goal algorithmic tasks, object-indexed loops, and
numeric/list-style benchmarks.

Routing implication: keep as a separate future route. It is not the primary
route for domain-level ASL predicate-goal libraries because its output language
does not naturally look like `+!on(X,Y)` or `+!clear(X)` modules.

## Proposed Project Routing Classes

The following classes are route-oriented, not claims about universal domain
complexity. Each class has a primary backend and fallback backends.

### Class A: Goal-regression and serialisable-goal domains

Property:

- Positive conjunctive goals decompose into singleton goals with limited harmful
  interactions.
- Goal order can often be random, static, or learned by regression.
- This aligns with MOOSE true/serialisable/optimal goal independence.

Primary backend:

- MOOSE.

Fallbacks:

- PG3 for domains in the PG3 paper.
- KR 2025 if MOOSE fails but a feature policy exists.

Recommended project domains:

| Domain | Source | Reason |
| --- | --- | --- |
| `ferry` | MOOSE dataset or IPC/PDDL source | MOOSE paper and local reproduction are strongest here. |
| `gripper` | IPC 1998 via `potassco/pddl-instances` | Appears in MOOSE, PG3, D2L, learner-sketches, KR 2025. Good cross-backend sanity domain. |
| `miconic` | IPC 2000 elevator simple typed via `potassco/pddl-instances` | Appears in MOOSE, PG3, D2L, learner-sketches, KR 2025. Good serialisable transport domain. |
| `logistics` | IPC 2000 logistics typed via `potassco/pddl-instances` | MOOSE studies full Logistics; KR 2025 solves restricted `Logistics-1pkg` and `Logistics-1truck` but marks full Logistics as C5. Good boundary inside this class. |

### Class B: Bounded-width sketchable subgoal-structure domains

Property:

- A compact sketch can decompose the problem into subproblems of bounded width.
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
| `delivery` | learner-sketches/D2L/PG3 benchmark source or AI-Planning generator | Central example in sketch and feature-policy theory; also in PG3. |
| `spanner` | IPC 2011 or learner-sketches/D2L source | Appears in D2L, learner-sketches, PG3, KR 2025. Includes dead-end/resource structure. |
| `visitall` | IPC 2011 via `potassco/pddl-instances` | Appears in D2L, learner-sketches, KR 2025, BFGP/PGP. Strong feature/sketch benchmark. |
| `childsnack` | IPC 2014 via `potassco/pddl-instances` | Sketch literature proves a width-1 sketch; KR 2025 learns a policy but has weaker large-instance coverage. Good stress test. |
| `barman` | IPC 2011 via `potassco/pddl-instances` | JAIR sketch work gives a Barman sketch; KR 2025 solves restricted Barman variants and fails on a harder Barman variant. Good boundary domain. |

### Class C: Feature-definable structural and goal-dependent domains

Property:

- Goal order matters or the domain has strong structural dependencies.
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
| `blocks` | IPC 2000 typed Blocks via `potassco/pddl-instances`; Blocks variants also in D2L and KR 2025 | Canonical goal-dependent construction domain. D2L handles `Qclear`, `Qon`, and `Qbw`; KR 2025 solves `Blocks4ops-clear`, `Blocks4ops-on`, and `Blocks4ops`. |
| `8puzzle-1tile` | KR 2025 benchmark source | KR 2025 solves both fixed and non-fixed variants; useful structural rearrangement domain. |
| `sokoban-1stone` | KR 2025 benchmark source and Sokoban IPC variants | KR 2025 solves `Sokoban-1stone-7x7` but with high cost and overfitting risk. Good hard structural benchmark. |

Domains to demote from primary support:

| Domain | Reason |
| --- | --- |
| `depots` | KR 2025 reports `Depot` in C5 with feature-pool edge failure. It should be a boundary/failure-analysis domain, not a claimed supported class, unless we add a new backend or new features. |
| `rovers`, `satellite`, full `transport` | MOOSE studies these, but KR 2025 C5 and our previous route/reachability issues suggest they require richer route, instrument, resource, or transitive-closure reasoning. Treat as boundary domains. |
| full `logistics` | MOOSE supports it, but KR 2025 reports full `Logistics` in C5 while solving restricted variants. Keep it in Class A as a MOOSE route, but mark it as a cross-backend boundary. |

## Recommended Formal Benchmark Set

For the next paper-quality routing evaluation, use 12 primary domains:

| Class | Domains | Primary route |
| --- | --- | --- |
| Class A: goal-regression and serialisable-goal | `ferry`, `gripper`, `miconic`, `logistics` | MOOSE |
| Class B: bounded-width sketchable subgoal structure | `delivery`, `spanner`, `visitall`, `childsnack`, `barman` | learner-sketches, then KR 2025/D2L fallback |
| Class C: feature-definable structural and goal-dependent | `blocks`, `8puzzle-1tile`, `sokoban-1stone` | KR 2025, then D2L fallback |

This set is deliberately different from the previous 8-domain taxonomy. The new
set is selected for backend-routing evidence, not for our earlier hand-built
Layer B/C architecture.

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

The router should be evidence-driven and conservative.

1. Read domain metadata from the benchmark registry. Initially, use explicit
   domain-to-class annotations rather than pretending that static PDDL analysis
   can perfectly infer the right generalized planner.
2. Run a cheap backend probe on a small training subset under hard memory and
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

1. The previous hand-built generalized planner should become a baseline, not the
   main method.
2. The current 8-domain taxonomy should be replaced or supplemented by the
   12-domain routing taxonomy above.
3. `depots` should move from "supported feature-definable construction" to
   "boundary/failure-analysis" unless a backend actually solves it.
4. Add `ferry`, `delivery`, `spanner`, `8puzzle-1tile`, and `sokoban-1stone`
   benchmark folders from the reputable sources above.
5. The main implementation work should be backend adapters and ASL compilers:
   MOOSE policy -> `LiftedPolicyProgram`, KR/D2L DLPlan policy ->
   `LiftedPolicyProgram`, learner-sketches sketch -> `LiftedPolicyProgram`
   with explicit subproblem semantics, then ASL.
6. h-policy/Vanir should be treated as the next backend-adapter candidate
   because its hierarchical policy output is more directly compatible with ASL
   modules than flat sketches, but it still requires artifact parsing and
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
- Taitler, A., Alford, R., Espasa, J., et al. 2024. The 2023 International
  Planning Competition. AI Magazine.
- Silver, T., Yang, R., Curtis, A., Lozano-Perez, T., and Kaelbling, L. P.
  2024. Generalized Planning in PDDL Domains with Pretrained Large Language
  Models. AAAI 2024.
