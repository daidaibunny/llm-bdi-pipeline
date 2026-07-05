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
The output must use only PDDL fluents and PDDL actions plus allowed `g_*` query
wrapper names. Internal type checks may be used while compiling, but final ASL
must not contain non-PDDL guards such as `type_block(X)`.

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

## Remaining Bottleneck

The single-body wrapper reduces wrapper overhead, but it does not solve every
Jason runtime bottleneck. Miconic p2 instances contain very dense static
`above/2` facts, so Jason context matching can still be expensive inside atomic
plans. That is an atomic library/runtime indexing problem, not an LTLf wrapper
problem. The correct next performance direction is to keep static predicates
range-restricted and to move closer to MOOSE-style indexed policy execution for
large static relations.
