# Full-Test Jason Validation Scope

`scripts/run_full_test_jason_validation.py` is a diagnostic runner, not the full
natural-language to LTLf to DFA input pipeline.

Current full-test behavior:

1. Read each test `problem.pddl`.
2. Extract only positive facts from the PDDL `:goal`.
3. Preserve the parser/file order of those facts.
4. Emit one query wrapper plan whose body calls those atomic goals in sequence.
5. Run Jason against the generated atomic AgentSpeak(L) library plus that
   wrapper.
6. Export every successful primitive action as a complete PDDL plan trace.
7. For paper-quality runs, validate that exported trace with VAL or an IPC-style
   plan verifier.

The wrapper shape is:

```asl
miconic_test_61.

+!g_miconic_test_61 : miconic_test_61 <-
	!served(p1);
	!served(p2);
	!served(p3).
```

This runner validates:

```text
PDDL test goal facts -> ordered singleton goal body -> Jason execution
-> exported PDDL plan trace -> VAL/IPC plan verification
```

It does not validate:

```text
natural language -> lifted LTLf JSON -> LTLf2DFA -> validated DFA -> ASL append
```

Jason is not doing classical planning in this setup. Jason receives the top-level
goal event such as `!g_miconic_test_61`, matches the first applicable ASL plan,
and executes the body. The planning work is split across two other components:
the atomic library provides plans for goals such as `!served(P)` or `!at(C,L)`,
and the upstream input layer chooses the temporal order when it creates an LTLf
formula. In this diagnostic runner, the order is just the PDDL parser order.

## Validation Semantics And Budget

The Jason Java environment is an execution environment, not the final plan
validator. It checks PDDL preconditions and effects online while Jason runs, but
the paper-quality success criterion is stricter: Jason must finish, export a
complete PDDL plan trace in `jason_plan.plan`, and that trace must be accepted
by VAL or an IPC-style verifier against the same domain and problem file.

The exported trace uses PDDL action names and object names, not Jason-safe
identifiers. For example, an ASL action functor `pick_up(b1)` is written as the
PDDL plan line `(pick-up b1)` when the source PDDL action is `pick-up`. The
artifact `pddl_symbol_map.tsv` maps Jason-safe symbols back to original PDDL
symbols when sanitization was needed.

The full-test runner now defaults to `1800` seconds for each Jason validation
case and `1800` seconds for each VAL/IPC verification call. This follows the
MOOSE paper's planning/instantiation comparison budget, not its separate
generalised-plan synthesis budget. Debug runs may pass `--no-require-plan-verifier`,
but those results are not paper-quality validation results.

## Temporal Wrapper Policy

The current ASL append policy for linear temporal goals is a single-body
compression with an explicit query entry proposition. A query entry proposition
is a zero-arity belief that enables one appended query wrapper; for example,
`miconic_test_61.` enables `+!g_miconic_test_61`. If the validated DFA has
exactly one positive singleton-literal progress path from the initial state to
an accepting state, the appender writes one plan body containing those progress
literals as subgoals. It does not write `tg_state(...)` beliefs.

The old query-local `tg_state(goal,state)` monitor was removed from the current
maintained output contract because it made large test batches much longer and
forced Jason to do extra context matching before every progress step. For a
linear goal such as "serve p1, then p2, then p3", the direct body above is
semantically sufficient for this diagnostic path. The explicit entry
proposition keeps many appended query wrappers maintainable in one ASL file.

Branching or state-dependent DFA goals are not silently compiled to `tg_state`
plans. They now fail with `nonlinear_temporal_goal_not_supported`. Those goals
need an external DFA or reward-machine controller because a single ASL body is
not equivalent to a branching automaton.

## Atomic Goal Repairs

The important repairs are in the atomic minimal literal module synthesis stage.
An atomic goal is a single PDDL fluent used as an AgentSpeak achievement goal,
for example `!at(Car, Location)`, `!served(Person)`, or `!on(Block, Support)`.
The output must use PDDL fluents, PDDL actions, allowed `g_*` query wrapper
names, and the reserved static sort metadata predicate `obj_tp(Object, Type)`.
Internal type checks may be used while compiling, but final ASL must not contain
domain-specific non-PDDL guards such as `type_block(X)`. `obj_tp/2` is allowed
only in plan contexts and is generated from PDDL `:types` and problem
`:objects`; it is not an achievement goal, not a primitive action, and not part
of exported PDDL action traces.

Static context safety means predicates that are never produced by any action are
used only as context, not as achievement goals. For example, Miconic `above(F1,
F2)` is a static ordering relation. The compiler may use it in a context such as
`lift_at(Y) & above(X,Y)`, but it must not generate `+!above(X,Y)`.

Producer macro ordering means a complete executable action sequence that
achieves the requested fluent is placed before recursive preparation branches.
This matters because Jason tries plans in file order.

Old Gripper failure shape:

```asl
+!at_robby(X) : room(Y) & not at_robby(Y) <-
	!at_robby(Y);
	!at_robby(X).
```

That branch can oscillate between rooms because it asks Jason to achieve another
same-predicate navigation goal without a progress measure.

Current Gripper producer-first shape:

```asl
+!at(X, Y) : at(X, A) & at_robby(A) & free(Z) & ball(X) & room(A) & gripper(Z) & room(Y) <-
	pick(X, A, Z);
	move(A, Y);
	drop(X, Y, Z).
```

This is better because the branch is directly executable when the ball, robot,
and gripper are bound. It performs the full producer macro before any more
general preparation branch can be considered.

Recursive progress certification means same-predicate recursive branches are
allowed only when the PDDL action schema gives a local reason that recursion
moves toward executability. A progress certificate is a schema-level witness,
for example an action in the body deletes or changes a dynamic relation that was
blocking the target fluent. Without that certificate, a branch like `!at_robby(Y);
!at_robby(X)` can loop.

Old Miconic dangerous shape:

```asl
+!lift_at(X) : above(Y, X) & not lift_at(Y) <-
	!lift_at(Y);
	!lift_at(X).
```

The variable `Y` is introduced by the dense static relation `above(Y,X)`, so
Jason can spend a long time matching candidates and can chase arbitrary floors.

Current Miconic movement shape:

```asl
+!lift_at(X) : lift_at(Y) & above(X, Y) <-
	down(Y, X).

+!lift_at(X) : lift_at(Y) & above(Y, X) <-
	up(Y, X).
```

This binds the current lift location first with `lift_at(Y)`, then uses
`above/2` only to choose the correct movement action. It removes unbound
same-predicate recursion for elevator movement.

The Clingo selector is the solver-backed branch selector used after candidate
generation. A branch selector is the component that chooses which candidate ASL
branches survive into the final library. In this project, Clingo must preserve
required branch kinds such as already-true branches, direct producer branches,
and certified recursive preparation branches, while minimizing branch count,
context count, and body cost within the generated candidate space.

## Post-MOOSE To ASL Synthesis

This repository does not modify MOOSE's goal regression learner. A MOOSE
readable policy is the `policy --dump-policy` first-order decision-list artifact,
for example a singleton goal rule whose target is `at(ball1, roomb)` and whose
macro action sequence is `pick(ball1, rooma, right); move(rooma, roomb);
drop(ball1, roomb, right)`. In the compact path, the MOOSE readable policy is
used only as evidence for which singleton goal predicates should seed the ASL
library.

The post-MOOSE synthesis path is:

```text
MOOSE readable singleton policy
-> seed predicate extraction
-> PDDL schema parsing
-> producible fluent closure
-> candidate atomic branch generation
-> schema feasibility and safety filters
-> Clingo/ASP branch selection
-> AgentSpeak(L) rendering
```

Seed predicate extraction means collecting the PDDL predicate symbols that MOOSE
actually learned as singleton targets. For example, if MOOSE learned singleton
rules for `served(p1)` and `served(p2)`, the seed predicate is `served`. This
step is in `compile_moose_readable_policy_to_minimal_module_asl_library`.

PDDL schema parsing means reading the domain's lifted predicate and action
schemas, not the grounded training instances. For example, in Miconic the
schema says `depart(?f, ?p)` requires `lift_at(?f)`, `destin(?p, ?f)`, and
`boarded(?p)`, and adds `served(?p)`.

Producible fluent closure means adding every dynamic predicate that appears in a
positive action effect as a possible atomic module, plus recursively needed
support predicates. For example, even if MOOSE only seeds `served`, the closure
adds `lift_at` and `boarded` because they are producible fluents needed by the
PDDL schemas. Static predicates, such as Miconic `above/2` or Logistics
`in_city/2`, remain context predicates and do not become `+!above(...)` or
`+!in_city(...)` achievement goals.

Candidate atomic branch generation means creating possible ASL plans for each
module predicate from action preconditions and effects. For example,
`depart(?f, ?p)` generates a direct candidate:

```asl
+!served(X) : lift_at(Y) & destin(X, Y) & boarded(X) <-
	depart(Y, X).
```

It also generates preparation candidates when a required producible fluent is
missing. For example, if `lift_at(Y)` is not true, `served(X)` may delegate to
the `lift_at` module:

```asl
+!served(X) : destin(X, Y) & not lift_at(Y) <-
	!lift_at(Y);
	!served(X).
```

Schema feasibility and safety filters remove candidates that are not safe under
the current ASL execution contract. These filters are domain-general; they do
not check for domain names such as `miconic` or action names such as `up`.

- Static context range restriction: a static relation can be used only after its
  variables are connected to the goal head or to earlier positive context
  literals. For example, `lift_at(Y) & above(X,Y)` is safe because `Y` is first
  bound by the dynamic fluent `lift_at(Y)`, but `above(Y,X) & not lift_at(Y)` is
  rejected because the dense static relation introduces `Y` before a dynamic
  binding.
- Recursive progress certification: a same-predicate recursive branch is allowed
  only when a body action deletes or changes a dynamic obstruction relation. For
  example, Blocks `clear(X)` can recursively clear a block above `X` because
  `unstack(Y,X)` deletes `on(Y,X)`.
- Bridge precondition delegation: if a bridge action only prepares a missing
  producible fluent over variables outside the target goal head, and that fluent
  already has its own module, the outer module delegates instead of inlining the
  bridge. For example, `served(X)` has head variable `X`; `lift_at(Y)` introduces
  non-head variable `Y`; since `lift_at` has its own module, `served(X)` calls
  `!lift_at(Y)` instead of inlining `board; up/down; depart`. In contrast,
  Gripper `at(X,Y)` keeps branches involving `at_robby(Y)` because `Y` is part
  of the target head.
- Type-compatible binding: PDDL action parameter types are checked during
  branch construction. The final ASL uses the reserved static context
  `obj_tp(Variable, Type)`, for example `obj_tp(X, package)` and
  `obj_tp(Z, truck)`, instead of domain-specific guards such as `type_truck(Z)`.
  This allows Logistics to keep `load_truck(X,Z,A); drive_truck(...);
  unload_truck(...)` while rejecting bindings that would treat the package `X`
  as the truck `Z`.

The Clingo/ASP branch selector receives the candidate branches and solves a
coverage/minimization problem. A coverage obligation is a candidate branch that
must be represented either by itself or by another branch with no stronger
context and an equivalent or recursively covering body. The selector minimizes
selected branch count, then context literal count, then body step count. This is
post-MOOSE reduction; it is not MOOSE goal regression.

AgentSpeak(L) rendering is the final formatting step. It emits PDDL predicate
achievement heads such as `+!served(X)`, PDDL primitive actions such as
`depart(Y,X)`, PDDL predicate subgoals such as `!lift_at(Y)`, allowed query
wrappers such as `+!g_query_1`, and reserved `obj_tp/2` contexts. It must not
emit synthetic achievements such as `achieve_*`, `transition_*`, `dfa_state`, or
domain-specific `type_*` guards.

## Jason Runtime Optimization

The current Jason validation runner keeps the AgentSpeak(L) library semantics
unchanged. The optimization is only about how PDDL facts are loaded into the
Jason runtime and how Jason searches those facts during context matching.

Before this change, every positive initial fact from a test problem was exposed
to Jason as a normal percept or belief. That mixed dynamic state facts, such as
`lift_at(f0)` or `at(ball1,rooma)`, with static context facts, such as
`above(f0,f1)`, `origin(p1,f3)`, `destin(p1,f20)`, `ball(ball1)`, or
`room(rooma)`. Large Miconic and Gripper instances then forced Jason to match
plan contexts against tens of thousands of mostly static facts.

The runner now writes three fact artifacts per validation case:

```text
initial_facts.txt      complete initial world used by the Java environment
initial_percepts.txt   dynamic facts exposed as Jason percepts
static_beliefs.txt     static facts loaded into an indexed read-only belief base
```

Dynamic versus static is detected from the PDDL action schemas, not from domain
names. A predicate is dynamic if it appears in any action add or delete effect.
Otherwise, it is static. For example, if `lift_at` appears in lift movement
effects, `lift_at(f0)` is loaded from `initial_percepts.txt`. If `above` never
appears in any effect, `above(f0,f1)` is loaded from `static_beliefs.txt`.
Reserved `obj_tp/2` facts are also static beliefs. The complete world is still
present in `initial_facts.txt`, so the Java environment continues to check PDDL
action preconditions and effects against the full state.

The generated MAS file now uses `JasonPipelineIndexedBeliefBase`:

```text
agents: agentspeak_generated beliefBaseClass JasonPipelineIndexedBeliefBase;
```

This class extends Jason's default belief base but adds indexes for lookup. It
keeps an exact atom index, such as `destin|p1|f20 -> destin(p1,f20)`, and
argument-position indexes, such as `above arg1 f20 -> above(f0,f20),
above(f1,f20), ...`. When a context literal has a bound argument, Jason can
retrieve a small candidate bucket instead of scanning all beliefs with the same
predicate.

Example Miconic context:

```asl
+!lift_at(X) : lift_at(Y) & above(X, Y) <-
	down(Y, X).
```

Jason first binds `Y` using the dynamic fact `lift_at(Y)`. The indexed belief
base can then resolve `above(X,Y)` using the second-argument bucket for the
current floor, instead of enumerating every `above/2` fact.

The index is kept live as dynamic percepts change. When Jason adds a belief,
the belief is inserted into the exact and argument-position indexes. When Jason
removes a belief, the belief is removed from those indexes incrementally.
Candidates returned from an index are also checked against the underlying
default belief base before use, so stale candidates cannot survive action
effects. Candidate lookup is streamed through a lazy iterator: static candidates
are returned directly, while dynamic candidates are live-checked one by one.
This avoids allocating a merged candidate list for each context match.

The runner also limits successful-action trace output:

```text
-Djason.pipeline.actionTraceLimit=3
-Djason.pipeline.actionTraceInterval=0
```

This keeps large validations from spending time and disk space printing every
primitive action to stdout. It does not truncate the exported PDDL plan trace:
`jason_plan.plan` still contains every successful primitive action and is the
artifact passed to VAL or the configured IPC-style verifier. The real action
count is still reported through `runtime_summary`, so validation records
preserve whether a run executed a short or very long plan.

The complete PDDL plan trace is accumulated in memory during Jason execution
and written to `jason_plan.plan` when `runtime_summary` or MAS shutdown runs.
This keeps the VAL-compatible trace intact while avoiding per-action file I/O.
The trace writer tracks whether the in-memory buffer has changed, so shutdown
does not rewrite the same file after `runtime_summary` has already exported it.

This optimization is domain-general for PDDL action schemas: adding a new
domain does not require a special case for that domain or for predicates such as
`above`, `ball`, or `room`. Remaining slowdowns after this change usually mean
the generated plan actually executes a very long primitive action sequence, as
in large Gripper p2 instances, or that the atomic ASL library itself lacks a
good executable branch.
