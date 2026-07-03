# Generalized Planning Backend Strategy

This document is the project reference for the current architecture after the
2026-07-03 pivot.

## Core Decision

We are no longer trying to build one universal generalized planner, and we are
no longer routing a domain to a backend by assigning the domain to a paper
taxonomy class.

The new architecture has two separate products:

1. A domain-level atomic literal plan library.
2. Query-specific temporal goal wrappers appended to that domain library.

The atomic library is learned from a PDDL domain and its training split using
existing generalized-planning backends. The temporal wrapper is generated from a
validated lifted LTLf JSON specification compiled to a deterministic finite
automaton.

## Target Pipeline

```text
PDDL domain + train split
-> atomic goal template extraction
-> SOTA generalized-planning backend
-> lifted atomic predicate/literal templates
-> domain-level AgentSpeak(L) atomic library

Natural-language input
-> external Input module
-> lifted LTLf JSON
-> LTLf-to-DFA
-> singleton-literal DFA validation
-> append +!g_query wrapper plans to the domain library
```

There is exactly one maintained AgentSpeak(L) library per domain. Each new user
query appends one new top-level goal name, for example `g_query_17`, to the same
domain library. The appended plans may call only existing atomic predicate
modules such as `!on(X,Y)` or primitive PDDL actions already present in the
atomic library.

## Atomic Template Generation

An atomic goal template is a lifted predicate or literal family that appears as
a target in training problems or in a validated temporal transition. Examples:

```text
on(?x, ?y)
clear(?x)
at(?package, ?location)
served(?passenger)
not blocked(?cell)
```

The first backend candidate is MOOSE because its paper method explicitly
decomposes training problems into singleton goal conditions and applies goal
regression to learn lifted rules. This makes it a strong fit for atomic
predicate/literal templates.

MOOSE is not the final answer for multi-literal interacting goals. Its own
theory is based on true, serialisable, or optimal goal independence. Blocks-style
conjunctive tower goals are the canonical counterexample: `on(X,Y)` can be
reasonable as a singleton template, while `on(X,Y) & on(Y,Z)` requires temporal
or structural ordering.

Backend priority for atomic template generation is:

1. MOOSE for positive singleton predicate goals.
2. KR 2025 learner-policies-from-examples when a feature-policy artifact is a
   better match or when MOOSE cannot emit a usable artifact.
3. D2L, learner-sketches, and h-policy-learner as audited fallback or comparison
   backends when their artifacts pass parser, binding, and compilation gates.

Negative literal templates are not claimed as supported until a backend artifact
shows a validated way to produce them. The implementation must reject them with
a precise diagnostic rather than emitting invented synthetic subgoals.

## Temporal Query Append Layer

The Input component is owned by another project member. Our contract starts from
its final artifact:

```text
lifted LTLf JSON -> LTLf formula string -> DFA payload
```

The DFA payload must satisfy the singleton-literal transition contract before it
can append ASL plans. Each transition guard must be one literal, not a
conjunction, disjunction, implication, or arbitrary Boolean formula. Negative
waiting guards such as `not done` are valid DFA structure and are not compiled
into atomic subgoals unless they are progress transitions. Accepting self-loops
labelled `true` are also allowed as implementation plumbing.

For a positive literal transition `on(X,Y)`, the appended ASL shape is:

```asl
+!g_query : not on(X,Y) <-
	!on(X,Y);
	!g_query.
```

This wrapper does not replace the DFA. For general temporal goals, a DFA or
reward-machine state must still be maintained by the temporal controller. A pure
ASL context-only encoding is sound only for monotonic or non-ambiguous sequences
where the current world state uniquely determines the next temporal step.

## Six-Domain Evaluation Scope

The six-domain scope is a benchmark design, not a backend-routing taxonomy. It
is chosen to cover different goal-property regimes while keeping the paper
focused.

| Group | Domains | Reason |
| --- | --- | --- |
| Singleton regression-friendly classical goals | `ferry`, `miconic` | Both are MOOSE paper domains and are strong tests for singleton goal regression producing compact lifted templates. |
| Multi-object classical achievement goals | `gripper`, `logistics` | Both appear in generalized-planning papers and stress whether atomic templates compose over many objects without query-specific grounding. |
| Structural or temporalized achievement goals | `blocks`, `8puzzle-1tile` | Blocks is the canonical goal-interaction domain; 8puzzle-1tile is a compact rearrangement family from feature-policy work. These domains test whether atomic templates can be reused under a temporal wrapper. |

Numeric MOOSE domains are intentionally not in the current six-domain corpus.
The project target is an AgentSpeak(L) library over PDDL predicates and
literals. Numeric fluents need a separate semantics and compiler contract before
they can be included responsibly.

## Reused Paper Code

Pinned backend code remains under `.external/` and is not vendored into `src/`.

| Backend | Paper role in this project | Local role |
| --- | --- | --- |
| MOOSE | Goal-regression generalized planner over singleton goals. | Primary atomic template backend candidate; readable `--dump-policy` artifacts now parse into `LiftedPolicyProgram` and lifted ASL plans. |
| learner-policies-from-examples | KR 2025 feature-policy learner with structural termination checks. | Fallback and comparison backend, especially for structural domains. |
| D2L | Description-logic feature-policy learner. | Reference backend for Blocks-style atomic policies. |
| learner-sketches | Serialized-width sketch learner. | Fallback and comparison backend for sketch artifacts. |
| h-policy-learner | Hierarchical policy learner. | Fallback and comparison backend for reusable policy modules. |

Every consumed artifact must pass:

```text
parse -> LiftedPolicyProgram -> feature/action binding -> ASL compilation -> held-out validation
```

Artifacts that do not pass these gates remain baseline or diagnostic evidence,
not final library output.

The MOOSE atomic backend path is intentionally artifact-based:

```bash
uv run python scripts/gp_backend_audit.py moose-atomic-command \
  --domain-file src/domains/ferry/domain.pddl \
  --training-dir src/domains/ferry/train \
  --save-file tmp/moose-atomic/ferry.model \
  --timeout-seconds 1800

uv run python scripts/gp_backend_audit.py moose-readable-summary \
  --policy-file tmp/moose-atomic/ferry.model.readable \
  --domain-name ferry

uv run python scripts/gp_backend_audit.py moose-readable-compile-asl \
  --policy-file tmp/moose-atomic/ferry.model.readable \
  --domain-name ferry \
  --output-dir tmp/moose-atomic/ferry-library

uv run python src/main.py compile-moose-atomic-library \
  --policy-file tmp/moose-atomic/ferry.model.readable \
  --domain-name ferry \
  --output-root artifacts/domain_libraries/ferry
```

The first command prints a resource-guarded Docker/Apptainer train-and-dump
command. The second verifies that the dumped readable policy can be parsed into
`LiftedPolicyProgram` and compiled in memory. The third materializes the current
paper artifact shape: `plan_library.json`, `plan_library.asl`, and metadata for
one domain-level atomic library. The fourth exposes the same materialization
through the main framework command-line interface.

After the external Input component produces lifted LTLf JSON, the main temporal
append command is:

```bash
uv run python src/main.py append-lifted-temporal-goal \
  --domain-file src/domains/blocks/domain.pddl \
  --plan-library-file artifacts/domain_libraries/blocks/plan_library.json \
  --ltlf-goal-json artifacts/input/blocksworld_lifted_ltlf.json \
  --query-id query_1 \
  --output-root artifacts/domain_libraries/blocks
```

## Current Implementation Requirements

1. Replace class-based GP routing on the main path with atomic goal-template
   backend selection.
2. Keep MOOSE as the first positive singleton-goal backend, but do not claim
   negative literal support until validated.
3. Restore and refactor the historical LTLf-to-DFA and logger code into the new
   temporal append layer.
4. Keep the registry and generated benchmark data fixed to the six selected
   domains unless the formal paper scope changes.
5. Preserve the deterministic `floor(2/3)` train split and remaining held-out
   split for every selected domain.
6. Add validator diagnostics that can be returned to the external Input module:
   malformed LTLf JSON, unsupported predicate, wrong arity, DFA parser failure,
   non-singleton transition guard, negative progress literal without backend
   support, and LTLf-to-DFA execution failure.
