# Generalized-Planning Backend Strategy

This repository no longer builds a universal generalized planner and no longer
routes domains by prior-paper taxonomy labels. The current strategy is to use
an Evidence Module to import external generalized-planning artifacts, normalize
them into backend-agnostic singleton-goal evidence, then compile the accepted
evidence into one maintained domain-level AgentSpeak(L) library per domain.
MOOSE is the current Evidence Module provider for positive singleton PDDL
predicate goals; it is not the name of the framework module.

## Compiler Contract

The architecture separates four modules.

1. The Evidence Module imports backend artifacts and emits a
   `PolicyEvidenceProgram`. A `PolicyEvidenceProgram` is the common evidence
   intermediate representation: it records a backend name, a source artifact,
   and singleton-goal policy rules. For example, the MOOSE adapter parses a
   `policy --dump-policy` first-order decision-list rule whose singleton goal is
   `at(package0, location2)` and whose macro sequence loads a package, flies it,
   unloads it, drives it by truck, and unloads it at the destination.
2. The Validated Policy-Lifting Compiler consumes the evidence program plus the
   PDDL domain schema. A PDDL domain schema is the action-schema file, for
   example a `drive-truck` action with typed parameters, preconditions, add
   effects, and delete effects. The compiler checks that evidence actions replay
   through those schemas, lifts object names to variables, adds required
   PDDL-schema closure modules, selects a compact branch set, and renders
   AgentSpeak(L) plans such as `+!at(X,Y)`.
3. The Temporal Query Compiler consumes validated lifted LTLf/DFA query
   artifacts and appends query-local wrapper plans that call the atomic library.
4. The Execution Validation Module runs the generated ASL in Jason, writes a
   committed PDDL action trace only after Jason success, and validates that trace
   with VAL or an equivalent verifier.

The compiler contract also includes a bounded integer numeric-resource fragment.
A numeric resource is a declared PDDL function with an integer value in the
state, for example `(capacity ?vehicle)` or `(pogo_sticks_to_make)`. A numeric
resource context is rendered as a mutable AgentSpeak belief plus comparison,
for example `capacity(V,N) & N > 0`. A numeric resource goal is rendered with
the target value as the final achievement-goal argument, for example
`+!pogo_sticks_to_make(0)`. Numeric macro evidence is accepted only when the
PDDL schema validates the primitive action sequence and the macro has a unit
monotone numeric effect toward the target, for example
`craft_wooden_pogo; !pogo_sticks_to_make(0)` after a `decrease` effect on
`pogo_sticks_to_make`.

The compiler does not use a domain-name switch and does not assign a whole
domain to a compiler class. The structural labels are plan-template-level
labels. A plan template is one AgentSpeak(L) plan branch, for example one
`+!at(X,Y) : ... <- ...` branch. A single domain library usually contains
several plan-template kinds at the same time.

| Plan-template kind | Meaning | Example |
| --- | --- | --- |
| `already_true_plan_template` | The requested fluent is already true, so the plan body is empty except for rendered `true`. | `+!clear(X) : clear(X) <- true.` |
| `action_only_plan_template` | The body contains only primitive PDDL actions. This includes fixed backend macro evidence, where a macro is a fixed action sequence, not a new PDDL action. | Logistics `+!at(P,L)` may execute `load_truck; drive_truck; unload_truck`. Blocks `+!clear(X)` may execute `unstack(Y,X); put_down(Y)`. |
| `subgoal_decomposed_plan_template` | The body contains at least one internal AgentSpeak achievement subgoal such as `!clear(Y)`. | Blocks `+!on(X,Y)` may call `!clear(Y); !on(X,Y)` when `Y` is not clear. |
| `numeric_already_true_plan_template` | A bounded integer numeric-resource achievement is already at the requested target value. This kind is chosen from the numeric certificate, not from the empty body alone. | `+!pogo_sticks_to_make(0) : pogo_sticks_to_make(N) & N == 0 <- true.` |
| `numeric_resource_progress_plan_template` | A bounded integer numeric-resource achievement executes a validated unit-progress macro and recursively asks for the same target value. | `+!pogo_sticks_to_make(0) : pogo_sticks_to_make(N) & N > 0 <- craft_wooden_pogo; !pogo_sticks_to_make(0).` |

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
MOOSE is a source of evidence and benchmark provenance, not the taxonomy itself
and not the name of the compiler module.

| Group | Domains | Shared property |
| --- | --- | --- |
| ESHO classical domains | `barman`, `ferry`, `gripper`, `logistics`, `miconic`, `rovers`, `satellite`, `transport` | Classical PDDL domains in the easy-to-solve, hard-to-optimise benchmark family used by MOOSE following the Helmert-style complexity view. These domains are suitable for testing whether singleton-goal regression evidence can be lifted into reusable atomic AgentSpeak(L) modules. |
| Numeric fluent domains | `numeric-ferry`, `numeric-miconic`, `numeric-minecraft`, `numeric-transport` | PDDL domains whose state, action applicability, or goals include numeric functions, numeric conditions, or numeric effects. They are included for benchmark coverage and for the bounded integer numeric-resource compiler fragment. |
| Feature-definable serialized-width domains | `blocksworld-clear`, `blocksworld-on`, `blocksworld-tower`, `depots` | Relational planning-family entries whose compact reusable behavior is normally expressed through lifted features and serialized subgoal structure: a feature-defined policy or sketch selects progress-making subgoals whose induced subproblems have small width. This group tests whether the compiler can add justified internal atomic modules from PDDL schemas rather than merely replay fixed singleton macros. |

Here a benchmark entry may be a planning-family entry rather than a unique PDDL
dynamics file. `blocksworld-clear` and `blocksworld-on` share Blocksworld-style
dynamics but differ in the lifted singleton goal family: the former is the
`QClear` family with goals such as `clear(X)`, and the latter is the `QOn`
family with goals such as `on(X,Y)`. `blocksworld-tower` is the classical typed
Blocksworld arrangement family, where multiple support literals interact and
must be serialized. This naming follows prior general-policy and planning-width
work on `QClear`, `QOn`, and full Blocksworld; it is not an implementation
route or a duplicate-counting trick.

The formal local corpus lives under `src/domains/<domain>/` with
`domain.pddl`, `train/*.pddl`, `test/*.pddl`, and `source.json`.

The current split policy is:

| Domains | Split policy |
| --- | --- |
| All twelve MOOSE direct train/test domains | MOOSE official companion split: source `training/` as train and source `testing/` as test. |
| `blocksworld-clear`, `blocksworld-on` | KR 2025 learner-policies no-constants split: source `learning/benchmarks/tractable/<family>/training/easy` as train and source `testing/benchmarks/<family>` as test. |
| `blocksworld-tower`, `depots` | Project feature-definable serialized-width split: `floor(1/4 * instance_count)` train and remaining instances as test. |

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
| `blocksworld-clear` | Feature-definable serialized-width domains | KR 2025 `QClear` family. Atomic `clear(X)` goals exercise recursive obstruction removal and internal modules such as `holding(X)`, `handempty`, and `ontable(X)`. |
| `blocksworld-on` | Feature-definable serialized-width domains | KR 2025 `QOn` family. Atomic `on(X,Y)` goals exercise support preparation through `clear(X)`, `clear(Y)`, `holding(X)`, `handempty`, and `ontable(X)`. |
| `blocksworld-tower` | Feature-definable serialized-width domains | Classical typed Blocksworld arrangement family. Multi-literal tower goals stress serialized support-dependent construction over the same atomic modules. |
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

## Numeric Support

Numeric fluent support is an explicit compiler extension, not a silent
translation of numeric PDDL into classical predicates. A numeric fluent is a
PDDL function whose value is part of the state, for example `(ferry-capacity)`
or `(capacity ?vehicle)`. A numeric condition is a comparison over such values,
for example `(> (capacity ?vehicle) 0)`. A numeric effect is an update such as
`(decrease (capacity ?vehicle) 1)` or `(increase (ferry-capacity) 1)`.

The implemented fragment is bounded integer-resource PDDL:

- numeric functions have finite integer values in the problem initial state;
- numeric preconditions use simple comparisons against constants or another
  parsed numeric term;
- numeric effects use `increase` and `decrease` by constant amounts;
- numeric problem goals may use equality between one declared numeric fluent and
  one integer target value;
- numeric fluents are used as action applicability and resource accounting, not
  as recursive ranking proofs for graph-search-style goals;
- generated action traces are still validated by a PDDL validator that supports
  numeric fluents.

Under this fragment, AgentSpeak(L) plans use numeric beliefs as executable
state, for example `capacity(v1,2)`, and primitive action execution updates
those beliefs according to the PDDL numeric effect. The final ASL library uses
declared PDDL function names directly. For example, the numeric goal
`(= (pogo_sticks_to_make) 0)` is represented as:

```asl
+!pogo_sticks_to_make(0) : pogo_sticks_to_make(N) & N == 0 <-
	true.

+!pogo_sticks_to_make(0) : pogo_sticks_to_make(N) & N > 0 & position(crafting_table) <-
	craft_wooden_pogo;
	!pogo_sticks_to_make(0).
```

The first plan is the already-true branch: if the numeric belief already equals
the target, no primitive action is needed. The second plan is the monotone
resource branch: it is emitted only when validated Evidence Module macro
evidence and the PDDL schema show that the primitive action decreases the
target resource by one. In the current experiments, that evidence comes from
the MOOSE readable-policy provider.

The implemented pipeline now:

1. distinguishes metric-only action costs from logical numeric resources in the
   PDDL support audit;
2. parses functions, numeric initial assignments, numeric preconditions,
   numeric effects, and numeric equality goals into typed internal structures;
3. seeds numeric fluents as mutable Jason beliefs and applies numeric
   `increase`/`decrease` effects during primitive action execution;
4. renders numeric contexts such as `capacity(V,N) & N > 0`;
5. validates Evidence Module numeric macro evidence against predicate and
   numeric schema conditions before rendering ASL;
6. accepts numeric resource functions as singleton LTLf/DFA progress atoms by
   adding the target value as the final argument. For example, the PDDL function
   `(pogo_sticks_to_make)` is legal in a DFA transition as
   `pogo_sticks_to_make(0)`, which appends the subgoal
   `!pogo_sticks_to_make(0)`;
7. relies on VAL or an equivalent numeric-capable validator for final action
   trace justification.

The deployed query path remains the temporal path:
validated lifted LTLf JSON, then LTLf-to-DFA, then singleton-literal DFA
validation, then AgentSpeak(L) append. Direct PDDL test-goal wrappers are only
an evaluation bridge for benchmark smoke runs where the input is a PDDL problem
file rather than a user query artifact. Those bridge plans are marked with
`evaluation_pddl_goal_wrapper_bridge` metadata and must not be described as the
final natural-language query interface.

Unsupported numeric cases include arbitrary arithmetic expressions, real-valued
updates, optimization metrics as achievement goals, non-equality numeric goals,
and numeric goals that require a recursive ranking proof not present in the
validated evidence.

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
