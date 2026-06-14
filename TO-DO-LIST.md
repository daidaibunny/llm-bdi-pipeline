# To Do List

## Current Refactor

- [x] Create development branch `codex/dfa-pddl-plan-generation`.
- [x] Locate the last git state before DFA/ltlf2dfa runtime deletion.
- [x] Restore DFA compilation and high-level AgentSpeak generation.
- [x] Replace benchmarks with PDDL files while preserving query bindings.
- [x] Remove obsolete generation, parsing, runtime, and test paths.
- [x] Run relevant tests.
- [x] Push a milestone commit.

## Domain-Level Achievement Library

- [x] Add a goal-conditioned modular-sketch representation for lifted ASL libraries.
- [x] Add Clingo-backed rule selection with capability coverage and cost minimization.
- [x] Add a domain-agnostic PDDL action-schema synthesizer for Layer B atomic modules
  and Layer C goal composer.
- [x] Add domain-agnostic small STRIPS transition evidence and shared-object goal
  ordering extraction for Layer C.
- [x] Add tests for arbitrary-domain lifted ASL output, Blocksworld through the generic
  path, read-only goal facts, unsupported goals, and Clingo minimization.
- [ ] Extend the Clingo constraints from capability coverage to full state-transition
  correctness/progress constraints over enumerated training transition systems.
