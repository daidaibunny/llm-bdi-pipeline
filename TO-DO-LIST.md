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
- [x] Add strict PDDL syntax validation plus conservative compilable-fragment rejection
  for domain-level ASL synthesis.
- [x] Add generated-AgentSpeak validation and compound context rendering for PDDL/DFA
  literal formulas.
- [x] Add a learner-sketches policy-to-ASL pipeline and CLI path that compiles only
  explicitly bound DLPlan feature rules.
- [x] Add Layer C ambiguity filtering so contradictory lifted goal-order evidence is
  not compiled as a hard composer rule.
- [x] Add guarded backend audit commands and compile smoke output for existing
  learner-sketches Blocksworld policies.
- [x] Extend selection beyond capability coverage with bounded transition-progress
  validation over enumerated training transition systems.
