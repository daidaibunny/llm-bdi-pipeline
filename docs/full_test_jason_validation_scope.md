# Full-Test Jason Validation Scope

`scripts/run_full_test_jason_validation.py` is a diagnostic runner, not the full
natural-language to LTLf to DFA input pipeline.

Current full-test behavior:

1. Read each test `problem.pddl`.
2. Interpret the positive conjunctive PDDL goal as one diagnostic DFA-style
   transition guard.
3. Compute conservative may-delete summaries from the final selected atomic
   module call graph to a finite, alpha-normalized relational fixed point, with
   PDDL type constraints participating in unification.
4. Serialize the guard only when those summaries are complete and the induced
   delete-threat graph has a certified order or supported preservation proof.
5. Compile that order into a balanced query-local transition repair tree.
6. Run Jason against the generated atomic AgentSpeak(L) library plus that
   wrapper.
7. Export every successful primitive action as a complete PDDL plan trace.
8. For paper-quality runs, validate that exported trace with VAL or an IPC-style
   plan verifier.

The wrapper shape is a declarative `trans` controller whose ordered literals are
organized as a balanced repair tree:

```asl
miconic_test_61.

+!g_miconic_test_61 : miconic_test_61 <-
	!g_miconic_test_61_trans_1.

+!g_miconic_test_61_trans_1 : miconic_test_61 <-
	!g_miconic_test_61_trans_1_repair_1_2;
	!g_miconic_test_61_trans_1_done.

+!g_miconic_test_61_trans_1_repair_1_2 : miconic_test_61 <-
	!g_miconic_test_61_trans_1_repair_1_1;
	!g_miconic_test_61_trans_1_repair_2_2.

+!g_miconic_test_61_trans_1_repair_1_1 :
	miconic_test_61 & not served(p1) <-
	!served(p1).

+!g_miconic_test_61_trans_1_done :
	miconic_test_61 & served(p1) & served(p2) <-
	true.

+!g_miconic_test_61_trans_1_done : miconic_test_61 <-
	!g_miconic_test_61_trans_1.
```

This runner validates:

```text
PDDL test conjunction -> certified guard order -> balanced trans repair tree -> Jason execution
-> exported PDDL plan trace -> VAL/IPC plan verification
```

It does not validate:

```text
natural language -> lifted LTLf JSON -> LTLf2DFA -> validated DFA -> ASL append
```

Jason is not doing classical planning in this setup. It dispatches the selected
atomic modules and rechecks the complete transition guard after one tree pass.
If achieving
`G2` may delete `G1`, the serializer places `G2` before `G1`. This ordering is
derived from PDDL effects and the selected ASL call graph, not predicate names,
argument positions, or PDDL file order. If the universal graph is cyclic, the
runner may copy a certified preservation-safe subset of complete action-only
atomic branches under a query-local helper and call that helper. The copied
trigger enforces the branch proof at execution time; the runner does not merely
assume that Jason will choose a safe branch from the original module. If neither
this selection nor a supported ranking certificate exists, the diagnostic query
is rejected instead of silently replaying an unproved order.

The effect fixed point keeps query arguments as anchors and alpha-normalizes
internal variables, so parameter-changing recursive calls are explored without
a benchmark-specific recursion depth. PDDL sibling types remain disjoint during
threat unification. For example, a module delete effect over `at(Truck,L)` does
not threaten a conjunctive goal over `at(Package,L)`, while a delete over a
compatible truck subtype still does. Repeated lifted variables in one guard
share both their binding and accumulated type requirements.

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

## Registered Experiment Modes

The production path remains the validated policy-lifting compiler plus the real
DFA, preservation-certified balanced controller, primitive-step monitor, Jason,
and VAL. Experimental modes are explicit, isolated output variants; none may be
selected as a silent fallback.

Atomic experiment modes share one normalized evidence artifact. Evidence
Adapter renders only PDDL-validated evidence macros. Action Closure adds
certified PDDL producers but no internal subgoals. Maximal Certified selects a
largest jointly compatible program from the full certified candidate universe.
Full Compiler minimizes over that exact universe and the same hard constraints.
This sequence
separates evidence quality, schema closure, lifted decomposition, and selection.

Temporal experiment modes share one DFA and atomic-library hash. The
DFA-aware-unprotected mode uses canonical within-edge order without threat or
preservation reasoning. Certified Flat uses the full selected order and branch
portfolios but retains flat sibling controller plans. Certified Balanced changes
only the controller indexing structure. Completion Monitor
changes only when the real DFA is observed and is restricted to a semantic
challenge suite with intermediate-state obligations.

Each variant writes its strategy identifier, source revision, evidence/library/
query/DFA hashes, settings, per-instance result records, and aggregate summary.
Paper tables are generated from these summaries. A variant is paired only when
all controlled hashes match. Raw MOOSE, LAMA/ENHSP, and direct temporal planning
are external references and therefore use a separate report rather than being
mixed into the compiler ablation matrix.

The paper-facing names are `Evidence Adapter`, `Action Closure`, `Maximal
Certified`, `Full Compiler`, `Unprotected DFA`, `Certified Flat`, `Certified
Balanced`, and `Completion Monitor`. Stable snake-case identifiers remain in
JSON and command-line arguments only. Tables use short descriptive headings,
not numbered labels or compressed oracle initials.

## Temporal Wrapper Policy

The canonical appender uses the real `ltlf2dfa`/MONA automaton and emits one
query-local `trans` helper for every progress transition on the unique accepting
path. A query entry proposition is a zero-arity belief that enables one query;
for example, `miconic_test_61.` enables `+!g_miconic_test_61`.

A singleton positive guard has identity serialization: its single leaf calls
one atomic subgoal and the done helper rechecks the guard. A conjunctive guard
is first serialized by the selected modules' delete-effect certificate, then
compiled into a balanced binary tree over that fixed order. Every leaf checks
one literal and calls its atomic module only when missing. The final done helper
checks all positive literals and negative context guards together; if an atomic
module invalidated an earlier literal, it replays the same transition. Negative
literals are context checks, never negative achievement subgoals. The old
linear body, one-sibling-plan-per-literal replay, and monotonic step-helper paths
are not selected.

Negative contexts are now certified before wrapper generation. The atomic call
graph contributes conditional completion-level `MayAdd` as well as `MayDelete`
effects. If a feasible positive repair branch may add an atom required absent by
the same DFA guard, the appender either copies only action-only branches that
achieve the positive literal while preserving every positive sibling and
negative guard, or rejects the transition with
`negative_guard_not_preserved`. When a positive action-only branch has an exact
PDDL net `MustDelete` for a currently present forbidden atom and preserves all
positive siblings, the appender copies it under a query-local establishment
helper. A signed negative leaf calls only that helper. The certificate stores
the forbidden atoms and both preserving and establishing branch names. A negative-only edge is only an immediate
context check; it does not create a negative achievement module. Mixed numeric
conjunctions remain outside the certificate.

The balanced tree is a data-structure optimization over one DFA transition,
not another planner. With `N` positive literals, the old sibling layout gave
the same trigger `N` repair plans. Re-entering that trigger after each repair
could inspect `N` candidates up to `N` times, giving quadratic controller work.
The tree gives an internal trigger one dispatch plan and a repairable leaf two
mutually exclusive plans: already satisfied or repair. One pass visits `N`
signed leaves, maximum trigger fan-out is two, and nesting depth is logarithmic. The
complete conjunction is checked once at the end of a pass. The generated ASL
contains more query-local helper plans, but it does not change the certified
literal order, primitive action sequence chosen by an atomic module, or DFA
transition boundaries.

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

## Validated Policy Lifting And ASL Compilation

This repository does not modify MOOSE's goal regression learner and should not
claim to replace the generalized planner. The implemented architecture uses an
Evidence Module followed by a validated policy-lifting compiler. The Evidence
Module imports backend artifacts such as MOOSE singleton-goal policy evidence
and normalizes them into a `PolicyEvidenceProgram`. The compiler checks that
evidence against the PDDL schema, lifts grounded-looking rule variables into
domain-level AgentSpeak(L) variables, and writes one maintained ASL library for
the domain.

A MOOSE readable policy is the `policy --dump-policy` first-order decision-list
artifact. For example, one readable rule may have goal condition
`at(package0, location2)` and action sequence `load-airplane(package0,
airplane0, location0); fly-airplane(airplane0, location0, location1);
unload-airplane(package0, airplane0, location1); load-truck(package0, truck0,
location1); drive-truck(truck0, location1, location2, city0);
unload-truck(package0, truck0, location2)`. The compiler does not trust this
sequence merely because the domain is named `logistics`; it preserves the
branch only if every primitive action is symbolically executable from the rule's
state condition under the PDDL action schemas.

The current compiler path is:

```text
MOOSE readable singleton policy
-> Evidence Module adapter
-> PolicyEvidenceProgram
-> validated policy-rule lifting
-> PDDL schema parsing
-> producible fluent closure
-> candidate atomic branch generation
-> schema feasibility and safety filters
-> Clingo/ASP branch selection
-> AgentSpeak(L) rendering
```

Validated policy-rule lifting means parsing each singleton MOOSE rule's state
condition, goal condition, and macro action sequence, then replaying the macro
over a symbolic state using the PDDL action schemas. For example, the Logistics
intermodal macro above is kept only if `load-airplane` has its required
`at(package0, location0)` and `at(airplane0, location0)` preconditions in the
symbolic state, and if the subsequent `fly-airplane`, `unload-airplane`,
`load-truck`, `drive-truck`, and `unload-truck` steps make the target
`at(package0, location2)` true. During this step, `package0`, `airplane0`,
`truck0`, and locations are alpha-normalized to variables such as `X`, `Z`,
`D`, and `Y`; PDDL typing is compiled to reserved `obj_tp/2` context guards.

Seed predicate extraction is still used after lifting. It collects the PDDL
predicate symbols that MOOSE actually learned as singleton targets. For example,
if MOOSE learned singleton rules for `served(p1)` and `served(p2)`, the seed
predicate is `served`. This seed set is not treated as the whole library; it is
the starting evidence for schema closure.

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
not check for particular domain names or particular action names.

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
validated policy lifting plus schema-augmented branch selection; it is not MOOSE
goal regression.

AgentSpeak(L) rendering is the final formatting step. It emits PDDL predicate
achievement heads such as `+!served(X)`, PDDL primitive actions such as
`depart(Y,X)`, PDDL predicate subgoals such as `!lift_at(Y)`, allowed query
wrappers such as `+!g_query_1`, and reserved `obj_tp/2` contexts. It must not
emit synthetic achievements such as `achieve_*`, `transition_*`, `dfa_state`, or
domain-specific `type_*` guards.

There is no Logistics-specific compiler branch and no Blocks-specific compiler
branch. The same implementation is used for every selected domain. The
structural labels are plan-template-level labels, not domain labels. A plan
template is one AgentSpeak(L) plan branch, for example one
`+!at(X,Y) : ... <- ...` branch. A single domain library usually contains
several template kinds at the same time:

- `already_true_plan_template`: the requested fluent is already true, so the
  plan body is empty except for rendered `true`. For example:

```asl
+!clear(X) : clear(X) <-
	true.
```

- `action_only_plan_template`: the body contains only primitive PDDL actions. A
  macro is one fixed primitive-action sequence; it is not a new PDDL action and
  not a hidden planner call. For example, a Logistics macro for `+!at(X,Y)` may
  execute `load_truck(X,Z,A); drive_truck(Z,A,Y,B); unload_truck(X,Z,Y)`. A
  Blocks action-only template for `+!clear(X)` may execute `unstack(Y,X);
  put_down(Y)`.
- `subgoal_decomposed_plan_template`: the body contains at least one internal
  AgentSpeak achievement subgoal. For example:

```asl
+!on(X, Y) : not clear(Y) & obj_tp(X, block) & obj_tp(Y, block) <-
	!clear(Y);
	!on(X, Y).
```

- `numeric_already_true_plan_template`: a bounded integer numeric-resource
  achievement is already at the requested target value. For example:

```asl
+!pogo_sticks_to_make(0) : pogo_sticks_to_make(N) & N == 0 <-
	true.
```

- `numeric_resource_progress_plan_template`: a bounded integer numeric-resource
  achievement executes a validated unit-progress macro and recursively asks for
  the same target value. For example:

```asl
+!pogo_sticks_to_make(0) : pogo_sticks_to_make(N) & N > 0 <-
	craft_wooden_pogo;
	!pogo_sticks_to_make(0).
```

The metadata therefore reports a generic `artifact_classification` of
`atomic_template_library`, plus `library_profile` and
`plan_template_kind_counts`. A `mixed_atomic_template_library` means the domain
library contains multiple plan-template kinds. This is a diagnostic profile of
the ASL file, not a taxonomy of the domain and not a routing decision.

Numeric resource functions are legal singleton LTLf/DFA progress atoms in the
temporal append contract by adding the target value as the final argument. For
example, the PDDL function `(pogo_sticks_to_make)` is represented in a DFA
transition as `pogo_sticks_to_make(0)` and compiles to the subgoal
`!pogo_sticks_to_make(0)`. Direct PDDL test-goal wrappers are only an
evaluation bridge for benchmark smoke runs where the input is a PDDL problem
file. The final user-query path remains validated lifted LTLf JSON,
LTLf-to-DFA, conjunctive/negative/numeric guard validation, then AgentSpeak(L)
append with a query-local primitive-step DFA monitor.

`unsupported_by_current_compiler` remains a boundary diagnosis, not a domain
class. A graph-search-style domain such as `8puzzle-1tile` is an example when
the available evidence does not yield a compact progress-safe atomic module.
Moving a target tile depends on blank-position reachability and permutation
constraints; the current compiler has no graph-search controller or ranking
certificate for that structure. The correct behavior is to report the
limitation, not to add a domain-name patch.

### Internal Subgoal Coverage

An internal subgoal such as `!clear(Y)` is emitted only when the compiler can
also emit plans for the target predicate `clear`. The input to this check is the
Evidence Module's `PolicyEvidenceProgram` plus the PDDL domain schema. For the
current MOOSE backend, that evidence program is produced from a MOOSE readable
singleton policy. The output is a closed set of atomic modules before
AgentSpeak(L) rendering.

The closure rule is domain-general:

1. Start from evidence seed predicates. If the Evidence Module imports a
   singleton rule for `on(X,Y)`, then `on` is a seed predicate.
2. Add every predicate that appears in a positive PDDL action effect. Such a
   predicate is a producible fluent, meaning an action can make it true. In
   Blocks, `put-down` adds `clear(X)`, `handempty`, and `ontable(X)`; `unstack`
   adds `holding(X)` and `clear(Y)`.
3. For every module predicate, generate an already-true template and producer
   templates from actions whose add effects produce that predicate.
4. Generate a prepare-subgoal template only when the missing precondition is
   itself a producible module predicate with a valid producer. Static predicates
   such as Miconic `above(F1,F2)` remain context only and do not become
   `+!above(...)` goals.

For Blocks, this process generates `clear` without any Blocks-name branch:

```asl
+!clear(X) : clear(X) <-
	true.

+!clear(X) : holding(X) & obj_tp(X, block) <-
	put_down(X).

+!clear(X) : on(Y, X) & clear(Y) & handempty & obj_tp(X, block) & obj_tp(Y, block) <-
	unstack(Y, X);
	put_down(Y).
```

These templates come from the PDDL schema: `put-down(?x)` has add effect
`clear(?x)`, and `unstack(?x,?y)` has add effect `clear(?y)`. To make
`clear(X)` with `unstack`, the compiler aligns PDDL parameter `?y` with ASL
variable `X`, producing the context `on(Y,X) & clear(Y) & handempty`.

Same-predicate recursive templates require a progress certificate. A progress
certificate is a schema-level well-founded ranking proof, not merely a witness
that one action deletes one fact. In Blocks:

```asl
+!clear(X) : on(Y, X) & not clear(Y) & obj_tp(X, block) & obj_tp(Y, block) <-
	!clear(Y);
	!clear(X).
```

The compile-time certificate is:

```text
certificate_kind = well_founded_relational_count_decrease
ranking_feature_kind = global_dynamic_atom_count
relation_predicate = on
relation_arguments = Y, X
strictly_decreasing_actions = [unstack]
non_increasing_actions = [put-down]
lower_bound = 0
```

This means the number of dynamic `on` atoms is a non-negative feature. The
producer sequence deletes at least one such atom and adds none. The compiler
also follows the selected module call graph and tells Clingo that this recursion
cannot coexist with any candidate branch that may add `on`; for example,
`unstack; stack` is incompatible because it exchanges one `on` fact for
another. The compiler does not inspect domain, predicate, or action names.

The fixed ranking grammar also contains
`anchored_acyclic_relation_cone_count`. This feature counts relation atoms in
the obstruction cone rooted at a query argument. It permits a cleanup sequence
to delete `relation(Z,X)` and add `relation(Z,B)` without decreasing the global
relation count only when generated inequality guards prove `B != X`. The local
candidate is not enough by itself: Clingo follows the selected module call graph
and excludes it if any reachable selected branch can increase the same anchored
cone without a compatible certificate. Depots currently generates such a local
candidate but fails this whole-library compatibility check, so the compiler
correctly omits the recursive branch rather than claiming unsupported progress.

For producer schemas with several staged dynamic preconditions, the compiler
uses `existential_precondition_context_projection` only when the preparation
dependency graph is acyclic and traverses a schema-inferred single-valued
fluent. An omitted sibling must have exactly one producer
schema, and that schema's static preconditions remain as feasibility witnesses.
Nested producer variables are alpha-renamed against the outer producer
variables. The repair body then calls the original target again, so the final
primitive producer cannot run until its complete context has been re-established.
If the dependency graph is cyclic or producer-ambiguous, the full connected
context is retained. This prevents a domain-specific Rovers-style workaround:
the same rule applies to any staged producer chain derived from PDDL schemas.

At the DFA transition layer, a cyclic threat graph may use
`query_local_support_ranked_recursive_closure` only when all positive goals use the
same certified binary relation and the requested support graph is functional
and acyclic. The child/support argument orientation comes from the recursive
certificate. The resulting order is only a candidate: every selected branch
must preserve earlier ranked achievements, and every recursive branch must
discharge one explicit missing context through a preparation module with a
complete effect summary. Self-recursion is rewritten to a query-local alias so
Jason cannot escape to an uncertified sibling branch. The persisted certificate
explicitly assumes that the binary relation remains acyclic in every reachable
state. If noninterference cannot be proved, compilation fails closed despite an
acyclic requested support graph. Effects are observed at successful atomic-module
completion for branch ordering, while the query-local DFA monitor observes the
initial valuation and every successful primitive PDDL action. This supports the
declared `F`, `X`, strong-`U`, conjunction, and literal-negation fragment but
does not make action-strategy synthesis complete for arbitrary PDDL-times-LTLf
products.

A second certified cyclic case uses
`query_local_preservation_safe_action_only_branches`. The runner symbolically
executes each selected finite primitive macro to module completion, filters out
every branch whose conditional net delete can threaten a sibling goal, and
copies all remaining branches under a query-local trigger. For example, if one
generic achievement module contains both a producer macro and a resource-reuse
macro that may delete another requested achievement, only the producer macro is
callable through the query-local helper. Problem-object names are reduced to
typed equality-pattern representatives so hundreds of structurally identical
goal pairs share one proof; PDDL domain constants and lifted variable identity
are preserved. This rule contains no benchmark, predicate, or action-name
switch. It fails closed when no non-empty safe action-only branch exists. In
particular, the current Tower and Depots libraries do not receive recursive
query aliases when their recursive preparation footprints cannot prove sibling
preservation; acyclicity alone is intentionally insufficient.

## Current Benchmark Scope And Library Profiles

The component between backend artifacts and ASL rendering is called the
validated policy-lifting compiler. It runs after the Evidence Module has
normalized a backend artifact into a `PolicyEvidenceProgram`; for example, the
MOOSE adapter normalizes a `policy --dump-policy` first-order decision-list rule
whose goal condition is `at(package0, location2)` and whose body is a macro
sequence of PDDL actions. The compiler runs before rendering the final
AgentSpeak(L) file; an AgentSpeak(L) file is the executable library containing
plans such as `+!at(X,Y) : ... <- ...`.

The benchmark groups describe evaluation coverage, not compiler outcomes. ESHO
classical domains are the easy-to-solve, hard-to-optimise classical benchmark
family used by MOOSE. Numeric fluent domains are PDDL domains whose state,
action applicability, or goals use numeric functions, numeric comparisons, or
numeric effects. Feature-definable serialized-width domains are relational
domains where prior general-policy and sketch work describes compact behavior
with lifted features and serialized subgoals whose induced subproblems have
small width.

| Domain | Benchmark property group | Evidence note |
| --- | --- | --- |
| `barman` | ESHO classical domains | Beverage goals such as `contains(Shot,Cocktail)` exercise cleaning, filling, pouring, shaking, and container state. |
| `ferry` | ESHO classical domains | Atomic car-location fluents such as `at(C,L)` exercise ferry loading, sailing, and debarking actions. |
| `gripper` | ESHO classical domains | Repeated `at(B,R)` literals over many balls exercise lifted object transport with `pick`, `move`, and `drop`. |
| `logistics` | ESHO classical domains | Package-location literals exercise long intermodal macros while `obj_tp/2` keeps package, truck, airplane, city, and location roles type safe. |
| `miconic` | ESHO classical domains | Passenger service goals such as `served(P)` exercise boarding, lift movement, and departure; static floor order such as `above(F1,F2)` remains context only. |
| `rovers` | ESHO classical domains | Communication goals such as `communicated_soil_data(W)` exercise sampling, imaging, and data transmission. |
| `satellite` | ESHO classical domains | Pointing and image goals such as `have_image(D,M)` exercise instrument power, calibration, turning, and imaging. |
| `transport` | ESHO classical domains | Package-location goals such as `at(P,L)` exercise capacity-aware loading, driving, and dropping. |
| `numeric-ferry` | Numeric fluent domains | Numeric ferry variant exercises bounded integer state, schema-certified equality progress, and temporal trace monitoring. |
| `numeric-miconic` | Numeric fluent domains | Numeric miconic variant exercises bounded integer state, schema-certified equality progress, and temporal trace monitoring. |
| `numeric-minecraft` | Numeric fluent domains | Numeric resource-production goals such as reducing `pogo_sticks_to_make` to zero exercise non-predicate goal semantics. |
| `numeric-transport` | Numeric fluent domains | Numeric transport variant exercises mixed Boolean/numeric guards and bounded numeric prerequisite preparation. |
| `blocksworld-clear` | Feature-definable serialized-width domains | KR 2025 `QClear` family. Atomic `clear(X)` goals exercise recursive obstruction removal and internal modules such as `holding(X)`, `handempty`, and `ontable(X)`. |
| `blocksworld-on` | Feature-definable serialized-width domains | KR 2025 `QOn` family. Atomic `on(X,Y)` goals exercise support preparation through `clear(X)`, `clear(Y)`, `holding(X)`, `handempty`, and `ontable(X)`. |
| `blocksworld-tower` | Feature-definable serialized-width domains | Classical typed Blocksworld arrangement family. Multi-literal tower goals stress serialized support-dependent construction over the same atomic modules. |
| `depots` | Feature-definable serialized-width domains | Crate-location and crate-support literals exercise internal modules over `clear`, `lifting`, `available`, `at`, and `in`. |

`8puzzle-1tile` is no longer a selected benchmark domain. It remains a boundary
case for the current compiler because the atomic goal "put one tile at its
target square" is not just a local producer or support-clearing pattern. It
requires reasoning about blank reachability and permutation progress over a
graph. Supporting it would require a graph-search or planning-program style
controller with a proof of progress, which is outside the current
Evidence-Module-to-ASL compiler contract.

For paper writing, the domain grouping should therefore be evaluation analysis,
not a backend-routing rule. A precise statement is: this work compiles validated
singleton-goal policy evidence from an external generalized planner into a
domain-level AgentSpeak(L) atomic library; when the PDDL schema exposes
additional producible fluents required for closure, the compiler may add
schema-augmented recursive atomic modules subject to safety and progress
certificates. This is a compiler claim, not a claim that MOOSE directly solves
interacting conjunctive or temporal goals.

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

### Large Conjunction Controller Scalability

The July 2026 Gripper p2 cases isolate two different costs. The atomic module
still moves one ball with a validated `pick; move; drop` macro, so a problem
with 21,500 destination literals legitimately produces 85,999 primitive
actions. That action cost is separate from the cost of dispatching the query
controller.

The former sibling replay controller generated one plan with trigger `+!trans`
for every missing literal. With `N` literals, Jason could inspect `N` sibling
plans each time `!trans` was replayed. The done plan also contained all `N`
literals and was considered at the same trigger. This made controller matching
approximately quadratic even when every atomic module was correct.

The balanced transition repair tree replaces that fan-out:

```asl
+!g_gripper_test_72_trans_1 : gripper_test_72 <-
	!g_gripper_test_72_trans_1_repair_1_21500;
	!g_gripper_test_72_trans_1_done.

+!g_gripper_test_72_trans_1_repair_1_21500 : gripper_test_72 <-
	!g_gripper_test_72_trans_1_repair_1_10750;
	!g_gripper_test_72_trans_1_repair_10751_21500.

+!g_gripper_test_72_trans_1_repair_1_1 :
	gripper_test_72 & not at(ball1, roomb) <-
	!at(ball1, roomb).
```

This is a balanced binary tree in the ordinary data-structure sense. An
internal range `[i,j]` is split near its midpoint and dispatches to two child
ranges. A leaf represents exactly one ordered guard literal. Balance matters
because the deepest helper chain grows as `log2(N)` rather than `N`; binary
dispatch matters because no trigger has thousands of sibling candidates. One
pass still visits every leaf, so controller work is linear rather than constant.

An isolated `p2_12` comparison used the same atomic library, one Jason worker,
the same 64 MiB Java stack, and the same 85,999-action VAL-valid trace. The
former sibling controller took about 288.5 seconds of Jason execution; the
balanced tree took about 38.2 seconds. For `p2_01`, the corresponding times
were about 12.9 and 3.2 seconds for the same 19,999 actions. The generated
query-local ASL is larger because it explicitly names internal tree nodes:
`p2_12` grew from roughly 107,643 to 279,647 lines. The measured trade-off is
therefore more generated control code for substantially less runtime plan
matching.

The indexed belief base still uses bound variables first. For example, when
checking `at(X,A)` inside `!at(ball123,roomb)`, `ball123` is already bound, so
the runtime uses that argument bucket rather than scanning all `at/2` facts.
The tree complements that optimization by reducing trigger candidate fan-out;
it does not alter belief indexing.

The remaining primitive action count is not solved by this controller. A future
set-level module could batch several homogeneous achievements when a certified
resource-capacity policy exists, but such batching would change action choices
and needs its own progress and preservation proof. It is intentionally not
inferred from a predicate name such as `at` or a domain name such as Gripper.

### Domain-Long ASL Artifact Policy

The full-test script no longer writes the combined domain-long ASL file by
default. The combined file appends every test wrapper for a domain to one
library. For Gripper, 90 full-test wrappers produced an 820,781-line ASL file.
That artifact is useful only for offline inspection of all appended test
wrappers together; it is not required for Jason execution because each test
uses a per-test runtime ASL containing the atomic library plus one query
wrapper.

Before:

```text
domain_libraries/gripper/plan_library.asl
  atomic library
  +!g_gripper_test_1 ...
  +!g_gripper_test_2 ...
  ...
  +!g_gripper_test_90 ...
```

After:

```text
jason/gripper/test_0071_p2_11/plan_library.asl
  atomic library
  +!g_gripper_test_71 ...
```

The best practice for full-test validation is therefore to keep per-test ASL
artifacts and omit domain-long ASL unless the specific debugging question needs
one file containing all wrappers. This reduces large redundant file writes and
keeps inspection focused on the exact ASL Jason executed for one test case.
