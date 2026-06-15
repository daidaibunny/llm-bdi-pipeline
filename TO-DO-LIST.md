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

## Unified Generalized-Planning-To-ASL Architecture Requirements

| ID | Requirement | Acceptance check | Status |
| --- | --- | --- | --- |
| R1 | Single synthesis pipeline from PDDL domain, training problems, and optional external learned policies to one lifted ASL library. | One public API returns a `PlanLibrary` and synthesis report; callers do not manually combine schema and sketch paths. | Done |
| R2 | No domain-specific production logic. | `src/domain_level_planning` contains no action/predicate special cases such as Blocksworld-only rules. Domain names may appear only in tests or audit experiment configs. | Done |
| R3 | Reuse paper-code artifacts as inputs where available. | Pipeline consumes learner-sketches DLPlan policies from `.external/gp-backends` outputs and records them as external candidate sources. | Done |
| R4 | Unified lifted intermediate representation. | External sketch bindings, schema-derived modules, and goal-order evidence all become `LiftedPlanRule` candidates with source metadata before selection. | Done |
| R5 | Layer B atomic goal modules are domain-level and lifted. | Generated module heads are PDDL predicate goals such as `+!P(X,Y)`, never grounded object-specific heads or `achieve_*`. | Done |
| R6 | Layer C composer is goal-conditioned and lifted. | Generated composer rules use read-only `goal_<predicate>` facts and PDDL state predicates; no permanent-protection flags or synthetic transition names. | Done |
| R7 | Selection is constrained by bounded correctness/progress evidence. | Selected rules pass bounded transition-progress validation on enumerated training systems. Failures are explicit. | Done |
| R8 | Unsupported PDDL or DLPlan semantics fail safely. | Conditional effects, numeric fluents, unsupported DLPlan features, and invalid ASL contexts fail with diagnostics instead of silent compilation. | Done |
| R9 | ASL compiler is single-path and validates generated syntax subset. | Unified pipeline output is rendered through `render_plan_library_asl`; invalid generated context/body syntax raises. | Done |
| R10 | External sketch path does not bypass Layer B/C. | Bound sketch rules are converted to candidate module/composer rules or rejected; they are not only compiled as a separate ASL skeleton. | Done |
| R11 | Held-out and counterexample hooks exist. | Pipeline report exposes training evidence, selected sources, rejected candidates, and a place to add failed instances later. | Done |
| R12 | Resource safety for external learners. | Audit commands print guarded learner invocations by default and never run unbounded experiments in tests. | Done |

Remaining research hardening after the first unified architecture:

- [ ] Move bounded transition-progress checks directly into ASP constraints instead of
  selecting first and validating after selection.
- [ ] Add an automatic counterexample-guided refinement loop for held-out failures.
- [ ] Expand DLPlan feature binding coverage beyond currently recoverable predicate
  count and goal-aligned role patterns.
