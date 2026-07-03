# External Generalized-Planning Backend Strategy

This document records the current architecture after the 2026-07-03 pivot. The
repository no longer tries to implement a universal generalized planner and no
longer routes whole domains by a prior-paper taxonomy class.

## Current Products

The framework has two products.

1. A domain-level lifted atomic AgentSpeak(L) library.
2. Query-specific lifted temporal wrappers appended to that same domain library.

The atomic library is generated from a PDDL domain and its train split by
consuming an external generalized-planning backend artifact. The temporal
wrapper is generated from a validated lifted LTLf JSON object compiled to a
deterministic finite automaton.

```text
PDDL domain + train split
-> atomic goal-template extraction
-> external generalized-planning backend artifact
-> LiftedPolicyProgram
-> atomic AgentSpeak(L) compiler
-> domain-level lifted atomic library

lifted LTLf JSON
-> LTLf-to-DFA
-> singleton-literal transition validation
-> append +!g_query wrapper plans
```

There is exactly one maintained AgentSpeak(L) library per domain. New user
queries append new top-level goals such as `g_query_17`; they do not create a
separate query-specific atomic library.

## Backend Policy

Backends are selected by whether their artifact can support the required atomic
predicate or literal templates, not by assigning a domain to a static class.

MOOSE is the first implemented backend path for positive singleton predicate
templates because its method learns lifted goal-regression rules over singleton
goal conditions. The current compiler consumes MOOSE readable policies produced
by `policy <model> --dump-policy`.

Other generalized-planning backends are pinned and audited as candidates:

- KR 2025 learner-policies-from-examples
- D2L
- learner-sketches
- h-policy-learner
- PG3 and planning-program systems as comparison or future adapters

A non-MOOSE backend counts as an atomic-library backend only after it passes:

```text
parse -> LiftedPolicyProgram -> verified atomic binding -> ASL compilation -> held-out validation
```

Until then, it remains audit-only or candidate-only.

## Temporal Wrapper Contract

The Input component is external. This repository consumes its lifted LTLf JSON
artifact and does not call a language model unless explicitly requested.

Every relevant DFA transition guard must be a singleton literal over declared
PDDL vocabulary. Compound guards, undeclared predicates, wrong arities, and
negative progress literals are rejected with diagnostics. Negative waiting
guards and accepting `true` self-loops may remain DFA structure.

For a positive transition literal such as `on(X,Y)`, the appended wrapper has
this shape:

```asl
+!g_query : not on(X,Y) <-
	!on(X,Y);
	!g_query.
```

The wrapper calls an existing atomic module. General temporal correctness still
requires an external DFA or reward-machine state whenever world-state contexts
alone do not identify the current automaton state.

## Selected Six-Domain Scope

The six domains are evaluation coverage, not backend-routing classes.

| Evaluation group | Domains | Purpose |
| --- | --- | --- |
| Singleton regression-friendly classical goals | `ferry`, `miconic` | Check MOOSE-style singleton positive predicate templates. |
| Multi-object classical achievement goals | `gripper`, `logistics` | Check reusable atomic templates over many objects. |
| Structural or temporalized achievement goals | `blocks`, `8puzzle-1tile` | Check interaction-heavy goals through atomic modules plus temporal wrappers. |

Each selected domain is materialized under `src/domains/<domain>/` with:

```text
domain.pddl
train/*.pddl
test/*.pddl
source.json
```

The split is deterministic:

```text
train = floor(2/3 * instance_count)
test = remaining instances
```

The registry under `src/benchmark_registry/achievement_goals` records these
domains and their atomic-backend artifact gates. It must not contain old
planner-trace synthesis fields.

## Current Implementation Status

Implemented:

- atomic template extraction from training problem goals;
- MOOSE readable-policy to `LiftedPolicyProgram`;
- MOOSE readable-policy to lifted atomic AgentSpeak(L);
- lifted LTLf JSON parsing with atom and binding metadata;
- LTLf-to-DFA integration through the restored temporal compilation code;
- singleton-literal DFA validation;
- query-specific `+!g_query` append;
- structured execution logging for temporal append runs;
- final artifact package generation without experiment-matrix planner traces.

Removed from the active code path:

- in-repository Clingo or schema-level generalized-planning synthesis;
- Layer C / conjunctive-goal composer code;
- planner-trace transition planning and Fast Downward runtime modules;
- old `goal_<predicate>` read-only descriptor semantics;
- old natural-language model transport code;
- old query-specific DFA high-level plan-library generation.

## Reproducibility Commands

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q

PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_final_paper_data.py \
  --output-dir tmp/paper-final-latest

PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_final_paper_data.py \
  --output-dir tmp/paper-final-latest \
  --validate-only
```

Backend audit commands:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/gp_backend_audit.py status
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/gp_backend_audit.py usage
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/gp_backend_audit.py capability
```
