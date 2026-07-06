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

The compiler does not use a domain-name switch. It assigns an evidence outcome
from the shape of the MOOSE policy plus the PDDL schema:

| Compiler outcome | Meaning | Example |
| --- | --- | --- |
| `validated_lifted_policy_rule_library` | MOOSE already gives complete singleton macro evidence, and the macro replays symbolically through PDDL action schemas. | Logistics `+!at(P,L)` can preserve a lifted load-fly-unload-drive-unload macro after type-safe binding. |
| `validated_policy_lifting_with_schema_augmented_recursive_modules` | MOOSE provides seed singleton evidence, but PDDL add-effect/precondition closure requires internal producible fluent modules. | Blocks `+!on(X,Y)` may call `!clear(Y)` before stacking; Depots `+!on(C,P)` may need `!lifting(H,C)` or `!clear(P)`. |
| `unsupported_by_current_compiler` | The available evidence cannot be compiled into a compact, progress-safe atomic library under the current contract. | `8puzzle-1tile` needs graph reachability and permutation-progress reasoning over the blank square. |

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

## Domain Outcomes

| Domain | Compiler outcome | Assignment reason |
| --- | --- | --- |
| `ferry` | `validated_lifted_policy_rule_library` | Singleton car-location goals such as `at(C,L)` are directly supported by MOOSE macro evidence over loading, sailing, and debarking actions. |
| `miconic` | `validated_lifted_policy_rule_library` | Passenger service goals such as `served(P)` compile from validated boarding, movement, and departure branches; static floor-order predicates remain context only. |
| `gripper` | `validated_lifted_policy_rule_library` | Ball-location goals such as `at(B,R)` compile to lifted producer macros over `pick`, `move`, and `drop`. |
| `logistics` | `validated_lifted_policy_rule_library` | Package-location goals require long macros, but those macros are complete MOOSE evidence and are type-safe after `obj_tp/2` binding. |
| `blocks` | `validated_policy_lifting_with_schema_augmented_recursive_modules` | Support construction goals such as `on(X,Y)` require internal producible fluents such as `clear`, `holding`, `handempty`, and `ontable`. |
| `depots` | `validated_policy_lifting_with_schema_augmented_recursive_modules` | Crate support goals such as `on(C,P)` combine stacking and transport, requiring internal modules over `clear`, `lifting`, `available`, `at`, and `in`. |

## Unsupported Boundary

`8puzzle-1tile` is not in the formal benchmark scope. The current compiler can
handle validated singleton macro evidence and support-dependent schema closure,
but `8puzzle-1tile` requires graph-search and permutation-progress reasoning:
placing one tile depends on moving the blank through a grid while preserving
solvability constraints. That structure needs a graph-search controller,
planning-program artifact, or a separate progress certificate before it can be
compiled into a compact AgentSpeak(L) atomic library. Until then, the correct
result is `unsupported_by_current_compiler`, not a domain-specific patch.
