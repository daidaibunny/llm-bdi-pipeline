# Generalized-Planning Backend Strategy

This repository no longer builds a universal generalized planner and no longer
routes domains by prior-paper taxonomy labels. The current strategy is to use
MOOSE as the external generalized-planning evidence backend for positive
singleton PDDL predicate goals, then compile the accepted evidence into one
maintained domain-level AgentSpeak(L) library per domain.

## Compiler Contract

The post-MOOSE, pre-AgentSpeak component is the validated policy-lifting
compiler. A MOOSE readable policy is the `policy --dump-policy` first-order
decision-list artifact; for example, a rule may say that when the singleton goal
is `at(package0, location2)`, a macro sequence of PDDL actions can load a
package, fly it, unload it, drive it by truck, and unload it at the destination.
A PDDL domain is the action-schema file, for example a `drive-truck` action with
typed parameters, preconditions, add effects, and delete effects. The compiler
checks that the readable policy's actions replay through those schemas, lifts
object names to variables, adds required PDDL-schema closure modules, selects a
compact branch set, and renders AgentSpeak(L) plans such as `+!at(X,Y)`.

The compiler does not use a domain-name switch and does not assign a whole
domain to a compiler class. The structural labels are plan-template-level
labels. A plan template is one AgentSpeak(L) plan branch, for example one
`+!at(X,Y) : ... <- ...` branch. A single domain library usually contains
several plan-template kinds at the same time.

| Plan-template kind | Meaning | Example |
| --- | --- | --- |
| `already_true_plan_template` | The requested fluent is already true, so the plan body is empty except for rendered `true`. | `+!clear(X) : clear(X) <- true.` |
| `action_only_plan_template` | The body contains only primitive PDDL actions. This includes fixed MOOSE macro evidence, where a macro is a fixed action sequence, not a new PDDL action. | Logistics `+!at(P,L)` may execute `load_truck; drive_truck; unload_truck`. Blocks `+!clear(X)` may execute `unstack(Y,X); put_down(Y)`. |
| `subgoal_decomposed_plan_template` | The body contains at least one internal AgentSpeak achievement subgoal such as `!clear(Y)`. | Blocks `+!on(X,Y)` may call `!clear(Y); !on(X,Y)` when `Y` is not clear. |

The metadata reports a library profile such as `mixed_atomic_template_library`
when several plan-template kinds appear in one domain library. This profile is
diagnostic only; it is not a domain taxonomy and is not used for routing.

## Benchmark Scope

The MOOSE paper evaluates eight classical ESHO domains for synthesis cost:
`barman`, `ferry`, `gripper`, `logistics`, `miconic`, `rovers`, `satellite`,
and `transport`. It then adds four numeric domains for instantiation-cost and
solution-quality experiments: `numeric-ferry`, `numeric-miconic`,
`numeric-minecraft`, and `numeric-transport`. The official companion source is
`DillonZChen/moose-dataset` at commit
`e00970516154e9042b783a4613a1ed7286c9beee`; in that source, those twelve
domains have both non-empty `training/` and non-empty `testing/` directories.

We therefore materialize every MOOSE direct train/test domain, including the
numeric domains, plus the project-added feature-definable serialized-width
benchmarks needed for the internal-module part of the plan-library claim. The
taxonomy below uses literature-level properties rather than task-story labels.
MOOSE is a source of evidence and benchmark provenance, not the taxonomy itself.

| Group | Domains | Shared property |
| --- | --- | --- |
| ESHO classical domains | `barman`, `ferry`, `gripper`, `logistics`, `miconic`, `rovers`, `satellite`, `transport` | Classical PDDL domains in the easy-to-solve, hard-to-optimise benchmark family used by MOOSE following the Helmert-style complexity view. These domains are suitable for testing whether singleton-goal regression evidence can be lifted into reusable atomic AgentSpeak(L) modules. |
| Numeric fluent domains | `numeric-ferry`, `numeric-miconic`, `numeric-minecraft`, `numeric-transport` | PDDL domains whose state, action applicability, or goals include numeric functions, numeric conditions, or numeric effects. They are included for benchmark coverage and for a staged numeric compiler extension, but the current main compiler contract remains predicate-level until numeric fluent semantics are implemented end to end. |
| Feature-definable serialized-width domains | `blocks`, `depots` | Relational domains whose compact reusable behavior is normally expressed through lifted features and serialized subgoal structure: a feature-defined policy or sketch selects progress-making subgoals whose induced subproblems have small width. This group tests whether the compiler can add justified internal atomic modules from PDDL schemas rather than merely replay fixed singleton macros. |

The formal local corpus lives under `src/domains/<domain>/` with
`domain.pddl`, `train/*.pddl`, `test/*.pddl`, and `source.json`.

The current split policy is:

| Domains | Split policy |
| --- | --- |
| All twelve MOOSE direct train/test domains | MOOSE official companion split: source `training/` as train and source `testing/` as test. |
| `blocks`, `depots` | Project feature-definable serialized-width split: `floor(1/4 * instance_count)` train and remaining instances as test. |

## Domain Evidence Notes

The following notes describe which goal structures each benchmark stresses.
They are not compiler-outcome assignments.

| Domain | Group | Evidence note |
| --- | --- | --- |
| `barman` | ESHO classical domains | Beverage goals such as `contains(Shot,Cocktail)` exercise cleaning, filling, pouring, shaking, and container state. |
| `ferry` | ESHO classical domains | Car-location goals such as `at(C,L)` exercise lifted ferry-loading and sailing actions. |
| `gripper` | ESHO classical domains | Ball-location goals such as `at(B,R)` exercise repeated lifted object movement over balls and grippers. |
| `logistics` | ESHO classical domains | Package-location goals exercise long intermodal macros over trucks, airplanes, packages, cities, and locations. |
| `miconic` | ESHO classical domains | Passenger service goals such as `served(P)` exercise boarding, lift movement, and departure; static floor-order predicates such as `above(F1,F2)` remain context only. |
| `rovers` | ESHO classical domains | Communication goals such as `communicated_rock_data(W)` exercise sampling, imaging, calibration, and sending data. |
| `satellite` | ESHO classical domains | Pointing and image goals such as `have_image(D,M)` exercise instrument power, calibration, turning, and imaging. |
| `transport` | ESHO classical domains | Package-location goals such as `at(P,L)` exercise capacity-aware vehicle loading, driving, and dropping. |
| `numeric-ferry` | Numeric fluent domains | Numeric variant of ferry-style car-location goals, included to test numeric evidence import. |
| `numeric-miconic` | Numeric fluent domains | Numeric variant of miconic service goals, included to test numeric evidence import. |
| `numeric-minecraft` | Numeric fluent domains | Numeric resource-production goals such as reducing `pogo_sticks_to_make` to zero exercise non-predicate goal semantics. |
| `numeric-transport` | Numeric fluent domains | Numeric variant of transport package-location goals, included to test numeric evidence import. |
| `blocks` | Feature-definable serialized-width domains | Atomic goals such as `on(X,Y)` and `clear(X)` exercise schema-derived internal modules such as `holding(X)`, `handempty`, and `ontable(X)`. |
| `depots` | Feature-definable serialized-width domains | Crate-location and crate-support literals exercise internal modules over `clear`, `lifting`, `available`, `at`, and `in`. |

## Unsupported Boundary

The official `*-axioms` and `*-disjpres` companion directories are not default
training benchmarks because the companion dataset provides only `testing/`
problems for them. They remain useful as future robustness probes after the base
train/test domains are stable.

`8puzzle-1tile` is not in the formal benchmark scope. The current compiler can
handle validated singleton macro evidence and feature-definable serialized-width
schema closure, but `8puzzle-1tile` requires graph-search and
permutation-progress reasoning:
placing one tile depends on moving the blank through a grid while preserving
solvability constraints. That structure needs a graph-search controller,
planning-program artifact, or a separate progress certificate before it can be
compiled into a compact AgentSpeak(L) atomic library. Until then, the correct
result is `unsupported_by_current_compiler`, not a domain-specific patch.

The same boundary applies to any domain or goal whose reusable atomic module
requires a recursive progress or ranking argument that the compiler cannot
derive from the current evidence. A progress or ranking argument is a
well-founded measure proving that each recursive call moves closer to success;
for example, `clear(X)` in Blocks can use the number of blocks above `X` as a
decreasing measure, while a graph-search puzzle may require reasoning over
blank reachability and permutation distance. Until such a certificate is
generated and validated, those goals remain outside the selected benchmark
claim rather than being patched with domain-specific code.

## Numeric Support Track

Numeric fluent support should be added only as an explicit compiler extension,
not by silently treating numeric PDDL as classical predicates. A numeric fluent
is a PDDL function whose value is part of the state, for example
`(ferry-capacity)` or `(capacity ?vehicle)`. A numeric condition is a comparison
over such values, for example `(> (capacity ?vehicle) 0)`. A numeric effect is
an update such as `(decrease (capacity ?vehicle) 1)` or
`(increase (ferry-capacity) 1)`.

The safe first target is a bounded integer-resource fragment:

- numeric functions have finite integer values in the problem initial state;
- numeric preconditions use simple comparisons against constants or another
  parsed numeric term;
- numeric effects use `increase` and `decrease` by constant amounts;
- numeric fluents are used as action applicability and resource accounting, not
  as recursive ranking proofs for graph-search-style goals;
- generated action traces are still validated by a PDDL validator that supports
  numeric fluents.

Under this fragment, AgentSpeak(L) plans may use numeric beliefs as executable
state, for example `capacity(v1, 2)`, and primitive action execution updates
those beliefs according to the PDDL numeric effect. The final ASL library must
therefore include a clear numeric state convention and must not compile
`increase` or `decrease` into unchecked text. A numeric atomic goal such as
`pogo_sticks_to_make == 0` should be represented by an explicit wrapper goal
whose context checks the numeric belief and whose recursive branch is emitted
only when the compiler has a validated producer action or macro that decreases
the relevant value.

The staged implementation order is:

1. Extend the PDDL support audit to distinguish metric-only action costs from
   logical numeric fluents, instead of rejecting all numeric fluent domains
   under one diagnostic.
2. Parse functions, numeric initial assignments, numeric preconditions, numeric
   effects, and numeric goals into typed internal data structures.
3. Extend the Jason runtime bridge so each numeric fluent is seeded as one
   mutable belief and each primitive action applies the corresponding numeric
   update atomically with predicate add/delete effects.
4. Extend ASL rendering with numeric contexts only after the runtime semantics
   are defined, for example `capacity(V,N) & N > 0`.
5. Extend the MOOSE-readable-policy adapter so numeric macro evidence remains
   schema-validated against both predicate and numeric preconditions/effects.
6. Add VAL or an equivalent numeric-capable validator to the batch pipeline and
   require validator success before claiming numeric support.
7. Only after the above works, consider numeric atomic goal synthesis such as
   resource-production goals; recursive numeric modules require an explicit
   decreasing measure and should remain unsupported without one.

## Sources

- Dillon Z. Chen, Till Hofmann, Toryn Q. Klassen, and Sheila A. McIlraith.
  `Satisficing and Optimal Generalised Planning via Goal Regression`, AAAI
  2026. Local verified copy: `.external/moose/moose.pdf`.
- Official MOOSE implementation:
  `https://github.com/DillonZChen/moose`, verified locally at commit
  `ce1e99bc12e9c839c5e8e870aac878fd5d31cf9e`.
- Official MOOSE companion dataset:
  `https://github.com/DillonZChen/moose-dataset`, verified locally at commit
  `e00970516154e9042b783a4613a1ed7286c9beee`.
- B. Bonet and H. Geffner. `General Policies, Subgoal Structure, and Planning
  Width`, JAIR 2024. Local verified copy:
  `paper_artifacts/literature/Bonet2024_General-Policies-Subgoal-Structure-Planning-Width.pdf`.
- D. Drexler, J. Seipp, and H. Geffner. `Learning Sketches for Decomposing
  Planning Problems into Subproblems of Bounded Width`, ICAPS 2022. Local
  verified copy:
  `paper_artifacts/literature/Drexler2022_Learning-Sketches-Bounded-Width.pdf`.
- G. Frances, B. Bonet, and H. Geffner. `Learning General Planning Policies
  from Small Examples Without Supervision`, AAAI 2021. Local verified copy:
  `paper_artifacts/literature/Frances2021_Learning-General-Policies-Small-Examples.pdf`.
