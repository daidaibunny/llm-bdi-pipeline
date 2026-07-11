# Research Pipeline Decisions

This document is the maintained pre-paper decision record for the research
pipeline. It records the current architecture, evidence/compiler boundaries,
benchmark scope, certificate requirements, supported fragments, and explicit
limitations. It is not the paper narrative and MUST be updated whenever an
implementation change alters a research-facing claim. The normative design for
parametric natural-language LTLf input and temporal evaluation is maintained in
[`input_design.md`](input_design.md).

## Canonical Terminology

**MOOSE evidence** is the readable first-order decision-list artifact emitted by
`policy --dump-policy`. For example, one evidence rule may associate the
singleton goal `at(package0,location2)` with the fixed primitive sequence
`load-truck; drive-truck; unload-truck` under a regressed state condition. MOOSE
is the current Evidence Module provider; it is not the compiler and does not
generate AgentSpeak(L) query wrappers.

A **macro** is a finite, fixed sequence of primitive PDDL actions in one
evidence rule or action-only plan template. It is not a new PDDL action and is
not a recursive module. For example, `load-truck; drive-truck; unload-truck` is
a macro, whereas `!clear(Y); !on(X,Y)` is a recursive subgoal decomposition.

The **Validated Policy-Lifting Compiler** consumes provider-neutral evidence
and the PDDL action schemas. It validates action sequences, generates required
schema-closure candidates, checks binding and progress conditions, selects a
compact candidate set, and renders the maintained atomic AgentSpeak(L) library.
MOOSE and the compiler are upstream and downstream components rather than
alternative planners.

**Clingo** is the Answer Set Programming solver used for constrained branch
selection. It does not plan in a PDDL state space and does not execute actions.
The compiler presents candidate branches, evidence-coverage obligations,
internal-module closure requirements, incompatibility constraints, and a
lexicographic cost objective; Clingo returns an optimal selected subset within
that certified candidate space.

A **certificate** is a machine-recheckable witness that justifies one compiler
claim. It must contain enough structured information for an independent checker
to replay the relevant PDDL schema reasoning; a prose metadata label is not a
certificate. The current certificate families are binding, schema
executability, target achievement, evidence coverage, internal-module closure,
well-founded recursive progress, resource-capacity restoration, and
target-preserving DFA guard serialization. Optimality is claimed only after all
hard certificate obligations hold and only within the generated candidate
space.

The **Temporal Query Compiler** is the third production component. It consumes
a validated lifted LTLf/DFA artifact and appends query-local `trans` wrappers
that call the atomic library. The **Temporal Goal Validation Module** is a
separate evaluation component. It validates a predicted lifted LTLf against the
sealed gold temporal semantics, replays hidden source witnesses, and checks
generated execution traces with both PDDL action semantics and DFA acceptance.

This repository no longer builds a universal generalized planner and no longer
routes domains by prior-paper taxonomy labels. The current strategy is to use
an Evidence Module to import external generalized-planning artifacts, normalize
them into provider-neutral singleton-goal evidence, then compile the accepted
evidence into one maintained domain-level AgentSpeak(L) library per domain.
MOOSE is the current Evidence Module provider for positive singleton PDDL
predicate goals; it is not the name of the framework module.

## Compiler Contract

The architecture separates four modules.

1. The Evidence Module imports provider artifacts and emits a
   `PolicyEvidenceProgram`. A `PolicyEvidenceProgram` is the common evidence
   intermediate representation: it records a provider name, a source artifact,
   and singleton-goal policy rules. For example, the MOOSE adapter parses a
   `policy --dump-policy` first-order decision-list rule whose singleton goal is
   `at(package0, location2)` and whose macro sequence loads a package, flies it,
   unloads it, drives it by truck, and unloads it at the destination.
2. The Validated Policy-Lifting Compiler consumes the evidence program plus the
   PDDL domain schema. A PDDL domain schema is the action-schema file, for
   example a `drive-truck` action with typed parameters, preconditions, add
   effects, and delete effects. The compiler checks that evidence actions replay
   through those schemas, lifts object names to variables, adds required
   PDDL-schema closure modules, selects a compact branch set, and renders
   AgentSpeak(L) plans such as `+!at(X,Y)`.
3. The Temporal Query Compiler consumes validated lifted LTLf/DFA query
   artifacts and appends query-local wrapper plans that call the atomic library.
4. The Temporal Goal Validation Module validates the model payload, proves or
   refutes gold/predicted DFA language equivalence, checks the hidden source
   witness, and consumes the committed trace produced by the separate Jason
   runtime. It validates that trace independently with PDDL replay, VAL, and
   gold-DFA acceptance.

## Temporal Goal Validation Contract

One benchmark record is
`B_i = <D, P_i, q_i, T_i, theta_i, pi_i>`. Here `D` is the PDDL domain,
`P_i` supplies the initial state and objects, `q_i` is the public controlled
natural-language query, `T_i` is the sealed gold lifted LTLf, `theta_i` is the
hidden variable-to-object assignment, and `pi_i` is a short legal witness
trace. The original achievement goal in `P_i` is provenance only and is not a
temporal success criterion.

The validation module uses four independent gates:

1. **Prediction contract validation** checks the exact eight-key model payload,
   LTLf syntax and operator fragment, atom-table closure, catalogue vocabulary,
   arity, subtype-compatible parameters, domain constants, and bounded integer
   numeric equalities. It never repairs a response. A model-correctable failure
   receives one stable `TranslationErrorCode`; an infrastructure failure is
   recorded separately.
2. **DFA language equivalence** first alpha-normalizes gold and predicted atom
   tables by their PDDL semantic identity, for example
   `(predicate,on,(X,Y),null)`, then invokes real LTLf2DFA/MONA on both
   formulas. It explores the reachable product automaton over the complete
   joint Boolean alphabet. If one DFA accepts and the other rejects, the
   shortest discovered valuation sequence is persisted as a counterexample
   certificate. Equality is semantic, not textual: `F(a & b)` and `F(b & a)`
   pass when their atom tables denote the same PDDL atoms.
3. **Hidden witness validation** grounds the accepted prediction with
   `theta_i`, replays every primitive action in `pi_i` from the initial state,
   checks the sealed state fingerprints, and requires both gold and predicted
   DFAs to accept the resulting non-empty finite state trace. This is a data and
   grounding consistency check; it does not replace language equivalence,
   because an incorrectly weak formula may also hold on one witness.
4. **Execution-trace validation** replays the Jason-exported primitive action
   trace under the parsed PDDL action schemas. VAL receives a generated copy of
   `P_i` in which only the original goal is replaced by the true empty
   conjunction `(:goal (and))`, so VAL checks action legality without imposing
   the unrelated achievement goal. The replayed state sequence must then be
   accepted by the sealed gold DFA and the predicted DFA. End-to-end success
   requires PDDL replay, VAL, gold acceptance, and prediction acceptance.

The batch input is the 475-row `translation_predictions.jsonl`. Its results are
expanded through the sealed worklist membership to all 1,228 problem rows. The
validator writes separate translation-level and problem-level JSONL reports,
an aggregate summary, optional execution-level evidence, and one validated
append dataset per domain. A translation enters an append dataset only after
payload validation, exact DFA equivalence, and hidden-witness acceptance.

The exact DFA product is bounded by a declared maximum Boolean alphabet size,
not by a domain or predicate name. Benchmark version 1 uses at most three
temporal atoms per query. Exceeding the configured bound, MONA timeout, missing
VAL, malformed sealed audit data, and PDDL replay disagreement fail closed as
infrastructure or benchmark-consistency outcomes; they are never relabelled as
model semantic errors.

The compiler contract also includes a bounded integer numeric-resource fragment.
A numeric resource is a declared PDDL function with an integer value in the
state, for example `(capacity ?vehicle)` or `(pogo_sticks_to_make)`. A numeric
resource context is rendered as a mutable AgentSpeak belief plus comparison,
for example `capacity(V,N) & N > 0`. A numeric resource goal is rendered with
the target value as the final achievement-goal argument, for example
`+!pogo_sticks_to_make(0)`. Numeric macro evidence is accepted only when the
PDDL schema validates the primitive action sequence and the macro has a unit
monotone numeric effect toward the target, for example
`craft_wooden_pogo; !pogo_sticks_to_make(0)` after a `decrease` effect on
`pogo_sticks_to_make`.

The compiler does not use a domain-name switch and does not assign a whole
domain to a compiler class. The structural labels are plan-template-level
labels. A plan template is one AgentSpeak(L) plan branch, for example one
`+!at(X,Y) : ... <- ...` branch. A single domain library usually contains
several plan-template kinds at the same time.

| Plan-template kind | Meaning | Example |
| --- | --- | --- |
| `already_true_plan_template` | The requested fluent is already true, so the plan body is empty except for rendered `true`. | `+!clear(X) : clear(X) <- true.` |
| `action_only_plan_template` | The body contains only primitive PDDL actions. This includes fixed backend macro evidence, where a macro is a fixed action sequence, not a new PDDL action. | Logistics `+!at(P,L)` may execute `load_truck; drive_truck; unload_truck`. Blocks `+!clear(X)` may execute `unstack(Y,X); put_down(Y)`. |
| `subgoal_decomposed_plan_template` | The body contains at least one internal AgentSpeak achievement subgoal such as `!clear(Y)`. | Blocks `+!on(X,Y)` may call `!clear(Y); !on(X,Y)` when `Y` is not clear. |
| `numeric_already_true_plan_template` | A bounded integer numeric-resource achievement is already at the requested target value. This kind is chosen from the numeric certificate, not from the empty body alone. | `+!pogo_sticks_to_make(0) : pogo_sticks_to_make(N) & N == 0 <- true.` |
| `numeric_resource_progress_plan_template` | A bounded integer numeric-resource achievement executes a validated unit-progress macro and recursively asks for the same target value. | `+!pogo_sticks_to_make(0) : pogo_sticks_to_make(N) & N > 0 <- craft_wooden_pogo; !pogo_sticks_to_make(0).` |

The metadata reports a library profile such as `mixed_atomic_template_library`
when several plan-template kinds appear in one domain library. This profile is
diagnostic only; it is not a domain taxonomy and is not used for routing.

## MOOSE Evidence and Compiler Responsibilities

The MOOSE module and the compiler module have different responsibilities. The
MOOSE module is the external evidence provider: it trains on singleton-goal
PDDL problems and emits a readable first-order decision list through
`policy --dump-policy`. A readable policy rule contains a lifted-looking state
condition, one singleton goal condition, and a primitive action macro. For
example, a Depots rule may say that under state facts such as
`at(crate0, depot0)`, `at(hoist0, depot0)`, and `clear(pallet0)`, the singleton
goal `on(crate0, pallet0)` can be achieved by a macro ending in
`drop(hoist0, crate0, pallet0, depot0)`.

The compiler module is the post-MOOSE, pre-AgentSpeak component. It consumes
the readable policy as evidence, checks it against the PDDL domain schema, adds
internal atomic modules required by PDDL precondition/effect closure, places
both evidence macros and schema-derived branches in one certified candidate
space, runs one Clingo/ASP selection, and renders the final AgentSpeak(L)
library. A
PDDL domain schema is the declared predicate and action model, for example
Depots `drop(?hoist, ?crate, ?surface, ?place)` with preconditions such as
`lifting(?hoist, ?crate)`, `clear(?surface)`, `at(?hoist, ?place)`, and
`at(?surface, ?place)`, and an add effect `on(?crate, ?surface)`.

MOOSE is the only implemented and experimentally evaluated Evidence Module
provider. `PolicyEvidenceProgram` is an extension interface: another provider
may be added later if its adapter emits the same normalized singleton-goal
rules and passes the same PDDL certificates. This interface does not imply that
another provider has already been reproduced or has MOOSE-equivalent results.

### MOOSE Parameter Provenance

MOOSE-native settings and our compiler settings are reported separately. The
MOOSE paper provides the following settings:

- `num_permutations = 3` is the default effort parameter in Algorithm 1. It is
  the maximum number of goal orderings sampled per training problem.
- `goal_max_size = 1` is our artifact flag that enforces the paper algorithm's
  singleton-goal step, where each relaxed subproblem has goal `{g_k}`. It is
  not a compactness threshold for the final ASL library.
- Generalized-plan synthesis receives 12 hours and 32 GB and is repeated five
  times in the paper.
- Test-time planning receives 1800 seconds and 8 GB. Up to five trained MOOSE
  models correspond to the five synthesis repetitions.

The batch runner now defaults to 43200 seconds for MOOSE training and 1800
seconds for MOOSE test-time planning, and records `random_seed` so five runs can
be aggregated. The repository-wide external-process guard remains 16 GiB; this
is a declared reproduction deviation from the paper's 32-GB synthesis ceiling.
`num_workers`, full-split flags such as `num_training = -1`, policy-dump and ASL
append timeouts, Jason timeout, and VAL timeout are pipeline or hardware
settings, not MOOSE method parameters.

The compiler's schema-derived candidate language is also explicit. It contains:

1. one direct target producer;
2. one support producer followed by the target producer;
3. one support producer, one bridge producer, and the target producer;
4. one prefix producer before the support/bridge/target sequence; and
5. optionally, one PDDL-certified resource-release action after any sequence.

Thus a schema-derived candidate has at most five primitive actions. A validated
Evidence Module macro may be longer and is not truncated by this bound. Clingo
optimality is only within this finite generated candidate language. This is a
method scope restriction, not a domain-name rule and not a MOOSE parameter.

The compiler therefore does not simply rename objects from training instances
into variables. It may add an internal module when the target action's
precondition names a producible fluent. A producible fluent is a predicate that
appears in some positive add effect, for example Depots `lifting(H,C)` or
Blocks `clear(X)`. A static context predicate is a predicate that never appears
in positive add/delete effects, for example Logistics `in-city(L,C)`; it can
bind context but must not become a `+!in_city(...)` achievement module.

### Range-Safe Precondition Lifting

Range-safe precondition lifting is the current general fix for producer actions
whose useful preconditions contain variables not present in the requested goal
head. Range-safe means every non-head variable is bound by positive context
facts before the compiler turns the precondition into an internal subgoal.

Before this fix, the compiler could emit the direct producer branch below, but
it would usually not emit the repair branch for the missing `lifting(Z,X)`
precondition because `Z` is not an argument of the head goal `on(X,Y)`:

```asl
+!on(X, Y) :
	clear(Y) & crate(X) & surface(Y) & at(Y, A) & place(A) &
	at(Z, A) & hoist(Z) & lifting(Z, X) <-
	drop(Z, X, Y, A).
```

This branch is correct only when the hoist is already lifting the target crate.
If `lifting(Z,X)` is false, Jason cannot use this branch and the library may
fall back to a much longer MOOSE macro or fail to repair the missing condition.

After the fix, the same PDDL schema also justifies a prepare branch:

```asl
+!on(X, Y) :
	clear(Y) & crate(X) & surface(Y) & at(Y, A) & place(A) &
	at(Z, A) & hoist(Z) & not lifting(Z, X) <-
	!lifting(Z, X);
	!on(X, Y).
```

The important part is the binding proof for `Z`: `at(Z,A) & hoist(Z)` binds
the hoist variable, while `at(Y,A) & place(A)` connects the hoist's place to
the target surface. The rule is not Depots-specific; it is generated from the
producer action's positive preconditions and add effect. The same mechanism
applies to any domain where a producer action needs an extra witness object,
provided that witness is range-restricted by positive context.

The fix is intentionally conservative. The compiler still refuses to turn an
extra-variable relation into an achievement subgoal if the extra variables can
only be introduced by a negative literal, by a static relation with no dynamic
anchor, or by an unrelated context fact. This avoids unsafe plans such as
asking Jason to achieve a relation over an unbound object.

### Well-Founded Relational Progress

A same-predicate recursive preparation branch is admitted only when the
compiler can construct a non-negative feature from a fixed structural grammar.
A ranking feature is compile-time metadata, not a new ASL fluent. The first
feature is a global relational count. For example, for `+!clear(X)` the schema
can induce `count(on)`, meaning the
number of currently true atoms of the dynamic predicate used as the obstruction
relation. The generated `unstack; put-down` sequence deletes one `on` atom and
does not add any `on` atom, so the feature strictly decreases and is bounded
below by zero.

The second feature is an anchored acyclic relation-cone count. It applies when
a sequence removes `relation(Z,X)` and may add `relation(Z,B)`: the global count
does not fall, but the obstruction cone rooted at `X` falls when schema-derived
guards prove `B != X`. This candidate certificate carries the explicit
assumption that the relation is acyclic in all reachable states. It is selected
only if the complete reachable module closure preserves the same anchored cone.

Concretely, if one transition requires `supports(a,b)` and `supports(b,c)`, the
support-depth order builds `supports(b,c)` first and then `supports(a,b)`. The
assumption excludes any reachable cycle such as `supports(a,b) & supports(b,a)`:
with a cycle there is no finite bottom support from which recursive progress can
be ranked. The predicate name is irrelevant; the same test passes after
renaming the relation and every action in the PDDL domain.

Deleting one obstruction is not sufficient by itself. The compiler follows the
selected module call graph and adds Clingo incompatibility constraints against
any candidate branch that may increase the chosen feature. Thus a branch such
as `unstack; stack`, which exchanges one `on` atom for another, cannot coexist
with recursion certified by the global `count(on)`. For an anchored cone,
relation-adding branches require their own compatible preservation proof.
Navigation recursion such as moving
between two rooms deletes and re-adds one location fluent, so no strict count
decrease is available and that recursion is not selected. Predicate names and
argument positions are not consulted; the feature and action effects come from
the PDDL schema.

### Causal Resource-Capacity Certificate

Protected resource release is the compiler rule for a producer action that
achieves the requested atomic literal but leaves behind a temporary resource
debt. A resource debt is a fluent produced by the action that represents an
object being held, lifted, carried, boarded, or otherwise tied to a resource.
For example, in Depots the action `lift(H,C,S,P)` can achieve `clear(S)`, but
it also creates `lifting(H,C)` and deletes `available(H)`. If the library stops
there, later goals may fail because the hoist is still occupied.

The compiler now accepts a one-step cleanup action only when the PDDL schema
certifies all of the following facts:

- the cleanup action deletes the producer-created debt, for example
  `drop(H,C,B,P)` deletes `lifting(H,C)`;
- the producer consumes a key-only free mode and creates a key-plus-occupant
  debt mode, while the cleanup performs the inverse transition. For example,
  `available(H)` supplies key `H`, while `lifting(H,C)` adds occupant `C`;
- the debt predicate is not merely a same-predicate property moved by the
  producer, so `clear(Y)` created by `unstack(X,Y)` is not treated as a held
  resource;
- every extra cleanup variable is range-restricted by positive context facts,
  for example a parking surface `B` must satisfy `surface(B)`, `at(B,P)`, and
  `clear(B)`;
- if the cleanup action could delete the protected target, the compiler emits a
  Jason non-unification guard such as `B \== S`.

Before this rule, a generated `+!clear(S)` branch in Depots could stop after
lifting the obstructing crate:

```asl
+!clear(S) :
	surface(S) & on(C, S) & clear(C) & at(C, P) &
	at(H, P) & available(H) <-
	lift(H, C, S, P).
```

This branch achieves `clear(S)`, but it leaves `lifting(H,C)` true and
`available(H)` false. After the rule, the compiler can emit a certified cleanup
branch:

```asl
+!clear(S) :
	surface(S) & on(C, S) & clear(C) & at(C, P) &
	at(H, P) & available(H) &
	surface(B) & at(B, P) & clear(B) & B \== S <-
	lift(H, C, S, P);
	drop(H, C, B, P).
```

This is still not a domain-name patch. The same rule would also accept a
Blocks-style `unstack; put-down` cleanup, because `unstack(B,S)` creates
`holding(B)` and deletes `handempty`, while `put-down(B)` deletes
`holding(B)` and restores zero-arity `handempty`. The rule rejects the reverse
shape, such as turning `available(H)` back into `lifting(H,C)`, because that is
resource acquisition rather than resource release.

The key-plus-occupant condition is not treated as an arity shortcut. It is used
together with the paired precondition/add/delete effects to orient an otherwise
symmetric transition. If two same-shaped predicates can be swapped without
changing the schema, the compiler cannot know which mode denotes availability;
it rejects that cleanup unless provider evidence or a future explicit resource
contract supplies the missing orientation.

The current implementation is intentionally one-step. If a domain needs
multi-step parking, such as releasing a resource only after moving a truck or
finding a buffer through several actions, that remains a future compiler
extension rather than an implicit hardcoded repair.

### Joint Certified Candidate Selection

Validated MOOSE macros and schema-derived modules are no longer selected in
separate phases. A validated MOOSE macro
is a readable-policy action sequence that replays through the PDDL action
schemas, for example a complete Logistics package-delivery macro
`load-truck; drive-truck; unload-truck`. A recursive repair branch is a branch
whose body calls internal subgoals, for example `!lifting(Z,X); !on(X,Y)`.

Each MOOSE macro is an evidence obligation in the same Clingo program that
selects direct producers, preparation branches, resource-release branches, and
validated bounded-integer numeric branches. Numeric-only evidence therefore no
longer bypasses Clingo. An evidence obligation is covered only by an
alpha-equivalent branch or an identical body under a weaker conjunctive context.
Separately, one schema-producer obligation may be covered by a weaker-context
primitive producer only when its composed `MustAdd` set contains the required
target, its `MayDelete` set is no larger, and its `NumericDelta` and complete
parameterized `ResourceRelease` contracts are causally compatible. Contract
identity records both action names, but refinement may use a different release
action only when debt, restored literals, capacity/occupancy roles, target
preservation, and alias guards refine the obligation and the composed Boolean
and numeric effects introduce no new harm. Predicate-name
equality and body-prefix similarity are not semantic evidence coverage. In
particular, the current compiler does not yet prove that a short recursive
module is equivalent to an arbitrary long MOOSE macro. Clingo also enforces
internal-module closure and rejects simultaneously selected branches that
invalidate a relational ranking certificate.

```asl
/* broad repair branch tried too early */
+!at(X, Y) : obj_tp(X, ball) & obj_tp(Y, room) & not at_robby(Y) <-
	!at_robby(Y);
	!at(X, Y).

/* complete macro exists but may be tried later */
+!at(X, Y) : at(X, A) & at_robby(A) & free(Z) <-
	pick(X, A, Z);
	move(A, Y);
	drop(X, Y).
```

After selection, already-true branches are rendered first, complete action-only
validated macros are rendered second, mixed bodies are rendered third, and
recursive repair branches are rendered last:

```asl
+!at(X, Y) : at(X, A) & at_robby(A) & free(Z) <-
	pick(X, A, Z);
	move(A, Y);
	drop(X, Y).

+!at(X, Y) : obj_tp(X, ball) & obj_tp(Y, room) & not at_robby(Y) <-
	!at_robby(Y);
	!at(X, Y).
```

The optimization is lexicographic. Hard schema/evidence/closure obligations
must first be satisfiable; then Clingo maximizes compatible well-founded
recursive capabilities and minimizes branch count, context count, and body
cost. Optimality is claimed only within the generated certified candidate
space, not over all possible AgentSpeak programs.

### Current Alignment and Remaining Gap

The current implementation is aligned with the intended post-MOOSE compiler
role in these ways:

- MOOSE remains evidence, not the final library.
- Internal modules such as `clear`, `holding`, `lifting`, `available`, `at`,
  and `in` are generated from PDDL add-effect/precondition closure when they
  are producible fluents.
- Static predicates remain context-only.
- The final ASL uses PDDL fluents and actions plus the reserved `obj_tp/2`
  type metadata; it must not emit `type_*` predicates.
- Clingo/ASP is the branch selector for compactness within the generated
  candidate space.

The current implementation now supports one-step protected resource release
when a cleanup action is certified directly by PDDL preconditions and effects.
It is not yet complete for all possible parking cases. If a domain needs a
multi-step release strategy, or if every available cleanup action would delete
the protected target without a representable non-unification guard, the compiler
should reject the branch rather than patching the domain by name.

### Certified DFA Guard Serialization

Every progress edge on the accepted DFA path is compiled into one query-local
`trans` helper. A singleton positive guard calls its atomic module once and
rechecks the guard, which is action-equivalent to the former linear call while
adding declarative completion checking. For a conjunctive guard, the compiler
computes conservative conditional may-delete summaries over the final selected
atomic module call graph. Every delete retains its branch's positive, negative,
equality, and disequality context. Effects are composed to successful
atomic-module completion, so a primitive delete restored later in the same
macro is not reported as a final delete. The summary is a finite relational
fixed point: root query arguments remain symbolic anchors, newly introduced
module variables are alpha-normalized, and subgoal calls are expanded until no
new predicate/argument shape is reachable. It therefore covers parameter-changing recursion such as
`at(X,Y) -> carry(X,Z) -> at(X,Z)` without a domain-specific depth bound. PDDL
type constraints are part of unification, so deleting `at(Truck,L)` cannot
falsely threaten `at(Package,L)` when `truck` and `package` are disjoint sibling
types. Shared lifted variables retain one binding and the conjunction is
rejected if their declared type requirements are inconsistent. Single-valued
predicate invariants inferred from paired PDDL add/delete schemas also reject a
guard that requests two provably different values for the same key.

If achieving literal `G2` may delete literal `G1`, the certificate requires
`G2` before `G1`. Only literals on the same DFA transition may be reordered;
different transitions retain DFA order. The persisted certificate records the
summary method as `pddl_typed_conditional_relational_fixed_point`, the ordered
literal indexes, all induced threat edges, the functional-invariant count, and
the `atomic_module_completion` observation boundary.

An acyclic threat graph uses universal topological serialization. For a cyclic
universal summary, the compiler first checks the narrow support-depth rule:
every positive goal uses one binary relation with a compiler-generated
relational decrease certificate, the requested relation graph is functional and
acyclic, and supports can be ordered before dependants. The child/support
argument orientation is inferred from the recursive certificate; the compiler
additionally checks that the recursive module closure does not re-add the
relation and that primitive relation producers delete only the same child's
previous relation. This rule records the explicit paper assumption that the
relation is acyclic in every reachable execution state. It is a structural
assumption over a certified relation, not a domain or predicate-name switch.

If support-depth does not apply, the compiler may instead enforce a query-local
preservation-safe action-only selection. An action-only branch is a selected
atomic plan whose body is a finite sequence of primitive PDDL actions and has no
internal achievement call. The compiler symbolically executes the whole branch,
keeps only branches whose conditional net deletes cannot unify with any sibling
goal, copies those branches under a query-local helper trigger, and makes every
transition repair call the helper. Merely proving that a safe branch exists is
not enough: copying the branch is what prevents Jason from selecting an unsafe
sibling from the original atomic trigger. Ground object names are alpha-normalized
to typed equality-pattern representatives during this check, while domain
constants and shared query variables remain fixed. This is a proof-cost
optimization and does not merge objects that may be equal in execution. The
filter retains every certified safe action-only branch; it does not claim a new
minimum-branch optimization. If no non-empty safe branch remains, the cycle is
still rejected. Multi-literal numeric guards without numeric effect-preservation
certificates are also rejected.
For example, singleton `fuel(vehicle)=0` can call one certified monotone numeric
module. A transition requiring `at(package,destination) & fuel(vehicle)=3`
needs an additional proof that repairing either conjunct preserves the other;
the current temporal compiler does not yet have this mixed numeric/predicate
preservation certificate and therefore fails closed.
It never falls back to parser order or a monotonic step-helper path. Negative
guard literals remain context checks and are never converted into negative
achievement subgoals.

After certification fixes an order `L1, ..., Ln`, the appender compiles that
order into a balanced transition repair tree. A transition repair tree is
query-local AgentSpeak control structure: an internal helper for range `[i,j]`
calls the two midpoint ranges, while a leaf has two mutually exclusive plans,
one for `Li` already true and one that calls the selected atomic module for
`Li`. The root then calls a separate done helper. The done helper returns only
when the full positive conjunction and all negative guards hold in the same
state; otherwise it re-enters the same transition. Thus balancing changes how
Jason dispatches a certified serialization, not which serialization is used.

This replaces the old one-sibling-plan-per-literal representation. For `N`
positive literals, that representation gave one trigger `N` repair candidates
and could repeat that candidate scan after each repair, yielding quadratic
controller matching. The balanced tree has `O(N)` query-local nodes, maximum
trigger fan-out two, `O(N)` visits per pass, and `O(log N)` nesting depth. The
complete conjunction is checked once per pass. The compiler records
`transition_controller_strategy=balanced_transition_repair_tree` so experiments
cannot silently mix the two encodings. Tree helper names are not PDDL fluents,
atomic modules, or exported actions.

For a singleton transition, the tree has one leaf: if the literal is absent it
calls the same atomic module once, and the done helper rechecks the same guard.
It is therefore primitive-action equivalent to the previous singleton wrapper.
For several DFA progress transitions, one independently generated tree is used
per transition and the DFA path order is unchanged. The tree does not provide
action batching, choose among atomic-module branches, or make an uncertified
threat cycle safe. Those remain separate method obligations.

The completion observation boundary is appropriate for achievement transitions
that are checked after an atomic module returns. It does not justify
safety-sensitive LTLf formulas that must observe every primitive intermediate
action; those require an external DFA controller and primitive-step monitor.
For example, a macro may delete `safe(X)` in its first primitive action and
restore it before the atomic subgoal returns. Completion-level checking can
still certify an eventual achievement after return, but it cannot certify
`G(safe(X))`, because that formula must inspect every intermediate state.

## Benchmark Scope

The MOOSE paper evaluates eight classical ESHO domains for synthesis cost:
`barman`, `ferry`, `gripper`, `logistics`, `miconic`, `rovers`, `satellite`,
and `transport`. It then adds four numeric domains for instantiation-cost and
solution-quality experiments: `numeric-ferry`, `numeric-miconic`,
`numeric-minecraft`, and `numeric-transport`. The official companion source is
`DillonZChen/moose-dataset` at commit
`e00970516154e9042b783a4613a1ed7286c9beee`; in that source, those twelve
domains have both non-empty `training/` and non-empty `testing/` directories.

We therefore materialize every MOOSE direct train/test domain, including the
numeric domains, plus the project-added feature-definable serialized-width
benchmarks needed for the internal-module part of the plan-library claim. The
taxonomy below uses literature-level properties rather than task-story labels.
MOOSE is a source of evidence and benchmark provenance, not the taxonomy itself
and not the name of the compiler module.

| Group | Domains | Shared property |
| --- | --- | --- |
| ESHO classical domains | `barman`, `ferry`, `gripper`, `logistics`, `miconic`, `rovers`, `satellite`, `transport` | Classical PDDL domains in the easy-to-solve, hard-to-optimise benchmark family used by MOOSE following the Helmert-style complexity view. These domains are suitable for testing whether singleton-goal regression evidence can be lifted into reusable atomic AgentSpeak(L) modules. |
| Numeric fluent domains | `numeric-ferry`, `numeric-miconic`, `numeric-minecraft`, `numeric-transport` | PDDL domains whose state, action applicability, or goals include numeric functions, numeric conditions, or numeric effects. They are included for benchmark coverage and for the bounded integer numeric-resource compiler fragment. |
| Feature-definable serialized-width domains | `blocksworld-clear`, `blocksworld-on`, `blocksworld-tower`, `depots` | Relational planning-family entries whose compact reusable behavior is normally expressed through lifted features and serialized subgoal structure: a feature-defined policy or sketch selects progress-making subgoals whose induced subproblems have small width. This group tests whether the compiler can add justified internal atomic modules from PDDL schemas rather than merely replay fixed singleton macros. |

Here a benchmark entry may be a planning-family entry rather than a unique PDDL
dynamics file. `blocksworld-clear` and `blocksworld-on` share Blocksworld-style
dynamics but differ in the lifted singleton goal family: the former is the
`QClear` family with goals such as `clear(X)`, and the latter is the `QOn`
family with goals such as `on(X,Y)`. `blocksworld-tower` is the classical typed
Blocksworld arrangement family, where multiple support literals interact and
must be serialized. This naming follows prior general-policy and planning-width
work on `QClear`, `QOn`, and full Blocksworld; it is not an implementation
route or a duplicate-counting trick.

The formal local corpus lives under `src/domains/<domain>/` with
`domain.pddl`, `train/*.pddl`, `test/*.pddl`, and `source.json`.

Materialization also checks referential PDDL validity. Every problem's
`(:domain ...)` declaration is compared with the actual copied `domain.pddl`
declaration and, when an upstream companion artifact retains an obsolete alias,
is normalized to the actual declaration. The number of normalized files is
recorded in `source.json`. This is a syntax-level, symbol-independent corpus
repair applied to every domain; predicates, actions, initial states, goals, and
split membership are unchanged. Validators do not silently accept mismatched
domain references.

The current split policy is:

| Domains | Split policy |
| --- | --- |
| All twelve MOOSE direct train/test domains | MOOSE official companion split: source `training/` as train and source `testing/` as test. |
| `blocksworld-clear`, `blocksworld-on` | KR 2025 learner-policies no-constants split: source `learning/benchmarks/tractable/<family>/training/easy` as train and source `testing/benchmarks/<family>` as test. |
| `blocksworld-tower` | Project feature-definable serialized-width split: `floor(1/4 * instance_count)` train and remaining instances as test. |
| `depots` | Project small-instance feature-definable serialized-width split: `floor(1/2 * instance_count)` train and remaining instances as test. The D2L source has 22 instances, so the larger train side gives MOOSE and the post-MOOSE compiler broader stacking/transport evidence before held-out testing. |

## Domain Evidence Notes

The following notes describe which goal structures each benchmark stresses.
They are not compiler-outcome assignments.

| Domain | Group | Evidence note |
| --- | --- | --- |
| `barman` | ESHO classical domains | Beverage goals such as `contains(Shot,Cocktail)` exercise cleaning, filling, pouring, shaking, and container state. |
| `ferry` | ESHO classical domains | Car-location goals such as `at(C,L)` exercise lifted ferry-loading and sailing actions. |
| `gripper` | ESHO classical domains | Ball-location goals such as `at(B,R)` exercise repeated lifted object movement over balls and grippers. |
| `logistics` | ESHO classical domains | Package-location goals exercise long intermodal macros over trucks, airplanes, packages, cities, and locations. |
| `miconic` | ESHO classical domains | Passenger service goals such as `served(P)` exercise boarding, lift movement, and departure; static floor-order predicates such as `above(F1,F2)` remain context only. |
| `rovers` | ESHO classical domains | Communication goals such as `communicated_rock_data(W)` exercise sampling, imaging, calibration, and sending data. |
| `satellite` | ESHO classical domains | Pointing and image goals such as `have_image(D,M)` exercise instrument power, calibration, turning, and imaging. |
| `transport` | ESHO classical domains | Package-location goals such as `at(P,L)` exercise capacity-aware vehicle loading, driving, and dropping. |
| `numeric-ferry` | Numeric fluent domains | Numeric variant of ferry-style car-location goals, included to test numeric evidence import. |
| `numeric-miconic` | Numeric fluent domains | Numeric variant of miconic service goals, included to test numeric evidence import. |
| `numeric-minecraft` | Numeric fluent domains | Numeric resource-production goals such as reducing `pogo_sticks_to_make` to zero exercise non-predicate goal semantics. |
| `numeric-transport` | Numeric fluent domains | Numeric variant of transport package-location goals, included to test numeric evidence import. |
| `blocksworld-clear` | Feature-definable serialized-width domains | KR 2025 `QClear` family. Atomic `clear(X)` goals exercise recursive obstruction removal and internal modules such as `holding(X)`, `handempty`, and `ontable(X)`. |
| `blocksworld-on` | Feature-definable serialized-width domains | KR 2025 `QOn` family. Atomic `on(X,Y)` goals exercise support preparation through `clear(X)`, `clear(Y)`, `holding(X)`, `handempty`, and `ontable(X)`. |
| `blocksworld-tower` | Feature-definable serialized-width domains | Classical typed Blocksworld arrangement family. Multi-literal tower goals stress serialized support-dependent construction over the same atomic modules. |
| `depots` | Feature-definable serialized-width domains | Crate-location and crate-support literals exercise internal modules over `clear`, `lifting`, `available`, `at`, and `in`. |

## Unsupported Boundary

The official `*-axioms` and `*-disjpres` companion directories are not default
training benchmarks because the companion dataset provides only `testing/`
problems for them. They remain useful as future robustness probes after the base
train/test domains are stable.

`8puzzle-1tile` is not in the formal benchmark scope. The current compiler can
handle validated singleton macro evidence and feature-definable serialized-width
schema closure, but `8puzzle-1tile` requires graph-search and
permutation-progress reasoning:
placing one tile depends on moving the blank through a grid while preserving
solvability constraints. That structure needs a graph-search controller,
planning-program artifact, or a separate progress certificate before it can be
compiled into a compact AgentSpeak(L) atomic library. Until then, the correct
result is `unsupported_by_current_compiler`, not a domain-specific patch.

The same boundary applies to any domain or goal whose reusable atomic module
requires a recursive progress or ranking argument that the compiler cannot
derive from the current evidence. A progress or ranking argument is a
well-founded measure proving that each recursive call moves closer to success;
for example, `clear(X)` in Blocks can use the number of blocks above `X` as a
decreasing measure, while a graph-search puzzle may require reasoning over
blank reachability and permutation distance. Until such a certificate is
generated and validated, those goals remain outside the selected benchmark
claim rather than being patched with domain-specific code.

## Numeric Support

Numeric fluent support is an explicit compiler extension, not a silent
translation of numeric PDDL into classical predicates. A numeric fluent is a
PDDL function whose value is part of the state, for example `(ferry-capacity)`
or `(capacity ?vehicle)`. A numeric condition is a comparison over such values,
for example `(> (capacity ?vehicle) 0)`. A numeric effect is an update such as
`(decrease (capacity ?vehicle) 1)` or `(increase (ferry-capacity) 1)`.

The implemented fragment is bounded integer-resource PDDL:

- numeric functions have finite integer values in the problem initial state;
- numeric preconditions use simple comparisons against constants or another
  parsed numeric term;
- numeric effects use `increase` and `decrease` by constant amounts;
- numeric problem goals may use equality between one declared numeric fluent and
  one integer target value;
- numeric fluents are used as action applicability and resource accounting, not
  as recursive ranking proofs for graph-search-style goals;
- generated action traces are still validated by a PDDL validator that supports
  numeric fluents.

Under this fragment, AgentSpeak(L) plans use numeric beliefs as executable
state, for example `capacity(v1,2)`, and primitive action execution updates
those beliefs according to the PDDL numeric effect. The final ASL library uses
declared PDDL function names directly. For example, the numeric goal
`(= (pogo_sticks_to_make) 0)` is represented as:

```asl
+!pogo_sticks_to_make(0) : pogo_sticks_to_make(N) & N == 0 <-
	true.

+!pogo_sticks_to_make(0) : pogo_sticks_to_make(N) & N > 0 & position(crafting_table) <-
	craft_wooden_pogo;
	!pogo_sticks_to_make(0).
```

The first plan is the already-true branch: if the numeric belief already equals
the target, no primitive action is needed. The second plan is the monotone
resource branch: it is emitted only when validated Evidence Module macro
evidence and the PDDL schema show that the primitive action decreases the
target resource by one. In the current experiments, that evidence comes from
the MOOSE readable-policy provider.

The implemented pipeline now:

1. distinguishes metric-only action costs from logical numeric resources in the
   PDDL support audit;
2. parses functions, numeric initial assignments, numeric preconditions,
   numeric effects, and numeric equality goals into typed internal structures;
3. seeds numeric fluents as mutable Jason beliefs and applies numeric
   `increase`/`decrease` effects during primitive action execution;
4. renders numeric contexts such as `capacity(V,N) & N > 0`;
5. validates Evidence Module numeric macro evidence against predicate and
   numeric schema conditions before rendering ASL;
6. accepts numeric resource functions as singleton LTLf/DFA progress atoms by
   adding the target value as the final argument. For example, the PDDL function
   `(pogo_sticks_to_make)` is legal in a DFA transition as
   `pogo_sticks_to_make(0)`, which appends the subgoal
   `!pogo_sticks_to_make(0)`;
7. relies on VAL or an equivalent numeric-capable validator for final action
   trace justification.

The deployed query path remains the temporal path:
validated lifted LTLf JSON, then LTLf-to-DFA, then singleton-literal DFA
validation, then AgentSpeak(L) append. Direct PDDL test-goal wrappers are only
an evaluation bridge for benchmark smoke runs where the input is a PDDL problem
file rather than a user query artifact. Those bridge plans are marked with
`evaluation_pddl_goal_wrapper_bridge` metadata and must not be described as the
final natural-language query interface.

Unsupported numeric cases include arbitrary arithmetic expressions, real-valued
updates, optimization metrics as achievement goals, non-equality numeric goals,
and numeric goals that require a recursive ranking proof not present in the
validated evidence.

## Sources

- Dillon Z. Chen, Till Hofmann, Toryn Q. Klassen, and Sheila A. McIlraith.
  `Satisficing and Optimal Generalised Planning via Goal Regression`, AAAI
  2026. Local verified copy: `.external/moose/moose.pdf`.
- Official MOOSE implementation:
  `https://github.com/DillonZChen/moose`, verified locally at commit
  `ce1e99bc12e9c839c5e8e870aac878fd5d31cf9e`.
- Official MOOSE companion dataset:
  `https://github.com/DillonZChen/moose-dataset`, verified locally at commit
  `e00970516154e9042b783a4613a1ed7286c9beee`.
- B. Bonet and H. Geffner. `General Policies, Subgoal Structure, and Planning
  Width`, JAIR 2024. Local verified copy:
  `paper_artifacts/literature/Bonet2024_General-Policies-Subgoal-Structure-Planning-Width.pdf`.
- D. Drexler, J. Seipp, and H. Geffner. `Learning Sketches for Decomposing
  Planning Problems into Subproblems of Bounded Width`, ICAPS 2022. Local
  verified copy:
  `paper_artifacts/literature/Drexler2022_Learning-Sketches-Bounded-Width.pdf`.
- G. Frances, B. Bonet, and H. Geffner. `Learning General Planning Policies
  from Small Examples Without Supervision`, AAAI 2021. Local verified copy:
  `paper_artifacts/literature/Frances2021_Learning-General-Policies-Small-Examples.pdf`.
