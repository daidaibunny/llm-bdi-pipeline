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

## Selected Benchmark Scope

The six selected domains are evaluation coverage groups, not backend-routing
classes.

| Group | Domains | Shared property |
| --- | --- | --- |
| Singleton regression-friendly classical goals | `ferry`, `miconic` | Test singleton positive predicate goals where MOOSE-style goal regression should provide direct policy evidence. |
| Multi-object classical achievement goals | `gripper`, `logistics` | Test repeated lifted atomic goals over many objects without allowing the final library to become instance-specific. |
| Support-dependent construction goals | `blocks`, `depots` | Test goals whose literals depend on support, clearing, lifting, or stacking relations, requiring schema-augmented internal atomic modules. |

The formal local corpus lives under `src/domains/<domain>/` with
`domain.pddl`, `train/*.pddl`, `test/*.pddl`, and `source.json`.

The current split policy is:

| Domains | Split policy |
| --- | --- |
| `ferry`, `miconic`, `gripper`, `logistics` | MOOSE official artifact split: source `training/` is train, source `testing/` is test. |
| `blocks`, `depots` | `floor(1/4 * instance_count)` train, remaining instances as test. |

## Domain Evidence Notes

The following notes describe which goal structures each benchmark stresses.
They are not compiler-outcome assignments.

| Domain | Evidence note |
| --- | --- |
| `ferry` | Car-location goals such as `at(C,L)` exercise lifted ferry-loading and sailing actions. The resulting library can contain already-true, action-only, and preparation templates. |
| `miconic` | Passenger service goals such as `served(P)` exercise boarding, lift movement, and departure actions; static floor-order predicates such as `above(F1,F2)` remain context only. |
| `gripper` | Ball-location goals such as `at(B,R)` exercise repeated lifted object movement over balls and grippers. |
| `logistics` | Package-location goals exercise long intermodal action-only macros such as loading into an airplane, flying, unloading, loading into a truck, driving, and unloading. |
| `blocks` | Support construction goals such as `on(X,Y)` exercise schema-derived internal modules such as `clear(X)`, `holding(X)`, `handempty`, and `ontable(X)`. |
| `depots` | Crate support goals such as `on(C,P)` combine transport and stacking, exercising internal modules over `clear`, `lifting`, `available`, `at`, and `in`. |

## Unsupported Boundary

`8puzzle-1tile` is not in the formal benchmark scope. The current compiler can
handle validated singleton macro evidence and support-dependent schema closure,
but `8puzzle-1tile` requires graph-search and permutation-progress reasoning:
placing one tile depends on moving the blank through a grid while preserving
solvability constraints. That structure needs a graph-search controller,
planning-program artifact, or a separate progress certificate before it can be
compiled into a compact AgentSpeak(L) atomic library. Until then, the correct
result is `unsupported_by_current_compiler`, not a domain-specific patch.
