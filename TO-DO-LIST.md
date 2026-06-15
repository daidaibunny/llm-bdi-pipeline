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
- [x] Add a bounded lifted-ASL executor and verify that one domain-level
  Blocksworld library learned from `p01` solves `p01` through `p20` without
  runtime full-trace planning.
- [x] Add paper-style bounded library validation over all reachable states in
  small training transition systems, including termination, high-level decision
  acyclicity, and goal-state fixed-point checks.
- [x] Add explicit learned-policy audit reports for paper-backend sketch
  artifacts, separating parseability, DLPlan feature binding, executable effect
  binding, and ASL readiness.

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
| R11 | Held-out and counterexample hooks exist. | Validation reports expose structured `LibraryCounterexample` records; refinement can add failed held-out problems into the next synthesis round. | Done |
| R12 | Resource safety for external learners. | Audit commands print guarded learner invocations by default and never run unbounded experiments in tests. | Done |
| R13 | Blocksworld first-20 domain-level validation. | One lifted library synthesized from `p01` solves `p01`-`p20` through the bounded ASL executor; generated ASL contains no `achieve_*`, `transition_*`, or `dfa_state` names. | Done |
| R14 | Paper-style bounded validation. | Synthesis reports include all-reachable-state validation for training transition systems, high-level decision acyclicity, and goal-state fixed-point checks. | Done |
| R15 | Paper backend artifact audit. | External learner-sketches policies are parsed and reported with feature/rule counts, binding coverage, unsupported features, executable effect count, and ASL readiness. | Done |
| R16 | Bootstrap and paper-grade synthesis profiles are separated. | `bootstrap` permits schema fallback; `paper` requires external learned policy rules to bind, bounded validation to pass, and rejects silent rule drops. | Done |
| R17 | Execution semantics are explicit. | The executor can run planner-style backtracking validation or deterministic first-applicable ASL execution for held-out refinement. | Done |
| R18 | learner-sketches can be invoked as a guarded synthesis backend. | The unified pipeline can run a pinned learner-sketches backend, discover `sketch_minimized_<width>.txt`, audit/bind it, and use it to satisfy `paper` profile without a manually supplied policy file. | Done |
| R19 | Recoverable learner-sketches role-count features bind without guessing. | `n_count(r_primitive(P,0,1))` is compiled to lifted predicate subgoal/action-effect candidates; object-specific distance features remain rejected. | Done |
| R20 | Bounded transition progress constrains ASP selection. | Observed goal-progress transitions are converted into required rule groups before Clingo selection, with post-selection validation retained as a defensive check. | Done |
| R21 | Counterexamples constrain synthesis without polluting base training data. | Failed held-out problems can be passed as counterexample problem files; their transition evidence becomes separate selector constraints and report fields. | Done |
| R22 | Bounded sketch-style state coverage constrains ASP selection. | Every bounded reachable non-goal training or counterexample state must be covered by at least one applicable lifted `+!g` composer candidate before Clingo can select a library. | Done |
| R23 | Nullary DLPlan boolean features bind conservatively. | `b_nullary(P)` features compile to PDDL predicate contexts and positive subgoal effects, while negative effects require explicit PDDL delete-action candidates. | Done |

Remaining research hardening after the first unified architecture:

- [x] Add a guarded automatic learner-sketches training adapter to the unified
  synthesis pipeline.
- [x] Move bounded transition-progress checks directly into ASP constraints instead of
  selecting first and validating after selection.
- [x] Promote learner-sketches-style bounded-width ASP constraints from post-hoc
  validation into the main synthesis objective.
- [x] Add an automatic counterexample-guided refinement loop for held-out failures.
- [x] Promote counterexample constraints into the ASP objective instead of adding
  whole failed problems only.
- [x] Expand DLPlan feature binding coverage to recover plain primitive role-count
  features used in learner-sketches Blocksworld policies.
- [x] Expand DLPlan feature binding coverage beyond currently recoverable predicate,
  role-count, and goal-aligned role patterns with nullary boolean feature support.
- [x] Audit current learner-sketches Blocksworld DLPlan expressions. All
  recoverable patterns in the existing artifacts are covered; object-specific
  `n_concept_distance(c_one_of(...),...)` and vocabulary mismatches such as
  `arm-empty` versus local `handempty` remain intentionally rejected.
- [ ] Future research: implement a principled lifted treatment for object-specific
  DLPlan distance features or an explicit verified vocabulary-adapter layer,
  without guessing predicate equivalence from names.
