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

## Experimental Comparison Contract

The framework is not evaluated as though it were one more per-instance PDDL
planner. MOOSE is one instantiated Evidence Module provider; the proposed
components are the Validated Policy-Lifting Compiler and Temporal Query
Compiler. Baselines and ablations therefore match one module boundary at a time.

### Primary Atomic Comparison

All atomic variants consume the same serialized `PolicyEvidenceProgram`, PDDL
domain, train/test split, and evidence hash.

| Method | Native behavior |
| --- | --- |
| Evidence Adapter | Validate each evidence macro by symbolic PDDL execution and render the surviving lifted macro plans. Do not add schema closure, internal subgoal modules, or branch optimization. |
| Action Closure | Add every certificate-valid action-only PDDL producer candidate required by producible-fluent closure. Do not add subgoal-decomposed candidates. |
| Maximal Certified | Generate the full certified candidate universe and use Clingo to retain a largest jointly compatible program under the same closure, ranking, and resource constraints as the full method. This is not an unchecked union of individually certified branches. |
| Full Compiler | Minimize branch, context, and body cost over the same candidate universe and hard certificate constraints used by Maximal Certified. |

Evidence Adapter is deliberately a strong baseline rather than an unchecked text translator.
It preserves all provider macros that meet the same schema validation used by
the full method. Maximal Certified versus Full Compiler changes only the
optimization objective, so differences in output size and Jason matching cost
can be attributed to compact selection. The machine-readable variant values are
`validated_evidence_adapter`, `action_only_closure`,
`maximal_certified_program`, and `full`; manuscript tables use the short names
above. A certificate-family
ablation removes the affected candidate family and records resulting rejections
or coverage loss; it must not bypass the certificate and emit unsafe code.

### Primary Temporal Comparison

All temporal variants consume the same atomic-library hash, validated lifted
LTLf JSON, binding, real MONA-derived DFA, and Jason PDDL environment.

| Method | Native behavior |
| --- | --- |
| Unprotected DFA | Use the real DFA and primitive-step monitor, but serialize each transition guard in a deterministic canonical order without completion-effect threat ordering or preserving branch portfolios. |
| Certified Flat | Use complete effect summaries, threat-safe order, and per-occurrence preservation portfolios, but compile literals as flat sibling plans. |
| Certified Balanced | Compile the identical certified literal order and branch choices into the balanced binary repair tree. |
| Completion Monitor | Retain the Certified Balanced controller and choices but advance the DFA only when an atomic module returns, for the dedicated intermediate-state semantic challenge set. |

Unprotected DFA and Completion Monitor are evaluation modes, never production
fallbacks. The historical
sequence-only PDDL-goal wrapper may be retained only as a weak evaluation
reference in isolated artifacts; production temporal append always follows the
real DFA transition path. Signed-negative and bounded-numeric capability
ablations retain the DFA and remove only their certified establishment strategy.

### External References and Fairness

Raw MOOSE execution distinguishes evidence quality from compiler and
AgentSpeak execution. LAMA for classical instances, ENHSP MRP+HJ for numeric
instances, and a direct LTLf compilation with a fixed classical planner are
external task-level references. Their outputs and cost structures differ from a
reusable AgentSpeak library, so they are reported separately from compiler and
controller ablations. Plan4Past supplies the experimental design precedent of fixing the
downstream planner while comparing temporal compilations; its pure-past input
is not treated as directly interchangeable with our future LTLf input without a
separately proved language-equivalent translation.

Five fixed MOOSE seeds are run independently with one internal MOOSE worker.
Evidence is never unioned and a best seed is never selected. Every paired
compiler comparison records the exact evidence hash; every paired temporal
comparison records the atomic-library, input, binding, and DFA hashes. Report
each seed, mean and sample standard deviation, paired coverage differences,
PAR-2 for timeouts, and plan length only on jointly solved instances. Keep
evidence synthesis, domain compilation, query append, execution, and validation
times separate. Published values obtained under other hardware, splits, or
formula sets are related-work context and are not copied into result tables.

The rejection suite is part of the evaluation rather than an implementation
unit test only. It covers unbound variables, incomplete closure, non-decreasing
recursion, unreleased resource debt, cyclic or incomplete completion threats,
forbidden negative-guard `MayAdd`, and numeric overshoot. Metamorphic tests apply
predicate/action/object renaming, compatible parameter permutation, and
irrelevant-fluent injection. These are the empirical checks behind the
domain-independent and fail-closed claims.

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

### Canonical TEG Benchmark Artifact

The repository tracks the frozen release at
`paper_artifacts/temporal_goal_benchmark/v1`. Its single canonical
`benchmark.json` contains 16 domain partitions and 1,228 problem-level cases.
A problem-level case is one tuple `(D, P_i, q_i, T_hat_i, theta_i)`: `D` is the
PDDL domain, `P_i` is the held-out initial state, `q_i` is the controlled query,
`T_hat_i` is the model-predicted lifted LTLf that passed exact language
equivalence, and `theta_i` is the sealed typed binding used for this problem.
The hidden oracle `T_i`, witness actions, and witness states are not copied into
the released case.

The bundle reports two evaluation units without conflating them. The 475
unique translation inputs are the macro unit for model translation accuracy.
The 1,228 expanded problem bindings are the micro unit for witness replay and
grounding consistency. Expansion through `member_sample_ids` does not create
additional model calls. The tracked result is 475/475 exact DFA-language
equivalence and 1,228/1,228 hidden-witness acceptance.

The 16 files under `domains/` are derived operational views, not separate
benchmarks. They exist because the temporal appender consumes one domain at a
time and every domain maintains one AgentSpeak library. The aggregate bundle
records each view's SHA-256, and the release manifest records the aggregate
bundle SHA-256. Consistently renaming PDDL symbols changes only corresponding
case symbols; benchmark generation contains no domain-name, action-name, or
fluent-name dispatch rule.

Execution evaluation remains a separate stage. A case is not an end-to-end
success until query append, Jason execution, primitive PDDL replay, independent
VAL under the neutral goal, gold-DFA acceptance, and predicted-DFA acceptance
all pass. The frozen version-1 release records execution as `not_attempted`.
Future execution failures are reported by domain and formula profile and do not
retroactively change the translation or witness metrics.

Each problem-level execution is one externally bound invocation. Before DFA
guard atoms enter the query-local AgentSpeak wrapper, the compiler substitutes
the case binding `theta_i`, for example `on(X,Y)` under `{X:b1,Y:b4}` becomes
the wrapper subgoal `!on(b1,b4)`. The atomic domain module remains lifted as
`+!on(X,Y)`; only the query wrapper is grounded. The runner rejects any mismatch
between the released binding and the sealed construction-audit assignment.

The paper execution entry point is
`scripts/run_temporal_goal_benchmark_execution.sh`. It consumes a complete
timestamped atomic-library batch without retraining MOOSE, compiles every case
independently, and records query compilation, Jason, PDDL replay, neutral-goal
VAL, gold-DFA, and predicted-DFA outcomes separately. Unsupported DFA structure
and missing certificates are structured compiler rejections rather than Jason
failures. Results are aggregated by domain and formula profile, while every
case retains its DFA payload, Jason artifacts, committed trace, validator
artifacts, and exact source revision.

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

Predicate closure does not disappear when backend evidence contains only a
numeric goal. Every declared predicate occurring in a positive PDDL add effect
is a producible fluent and enters the same schema candidate generation and
Clingo selection. Predicates with no add effect remain static context. This
ensures, for example, that a numeric resource policy can coexist with lifted
`+!position(X)` and `+!air_cell(X)` modules derived from their schemas without
recognizing those names. The compiler metadata already labels each omitted
producible fluent as a coverage gap; the implementation therefore treats such
an omission as an invalid incomplete library rather than a permitted numeric
special case.

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

The batch runner defaults to 43200 seconds for MOOSE training and 1800 seconds
for MOOSE test-time planning. The paper protocol now executes five independent
synthesis repetitions with fixed seeds `0, 1, 2, 3, 4`. Each repetition trains
on the complete selected train split and has exactly one internal MOOSE worker.
This single-worker restriction is a reproducibility choice, not a MOOSE method
parameter: the current MOOSE implementation seeds one process-global random
generator and calls goal-permutation sampling from problem threads, so changing
thread scheduling can change which problem receives each random draw.

The five seed repetitions may run concurrently as isolated operating-system
processes because they share only read-only PDDL/backend inputs and use separate
model, policy, library, and log roots. A same-seed Logistics `p03` smoke test
produced the same 27-rule canonical policy hash in two concurrent isolated
processes with one internal worker; seeds 0 and 1 produced different canonical
policies on the same instance. This smoke test motivates process isolation but
is not treated as a proof over all domains. Every completed repetition therefore
records raw and canonical policy hashes so same-seed reproducibility remains
auditable.

Each seed policy is compiled and evaluated independently. Policies, rules, and
ASL branches are never concatenated across seeds, and the evaluation never
selects the best seed. Jason/VAL repetitions run sequentially across seeds to
avoid cross-seed resource contention changing timeout outcomes; each repetition
uses six per-test Jason workers by default. Reports retain every seed result and
summarize coverage with the mean and sample standard deviation across completed
repetitions. Concurrent synthesis timings are throughput measurements; runtime
claims against another system require a separately controlled non-contented
timing run.

The repository-wide external-process guard remains 16 GiB; this is a declared
reproduction deviation from the paper's 32-GB synthesis ceiling.
`num_workers`, outer seed-process parallelism, full-split flags such as
`num_training = -1`, policy-dump and ASL append timeouts, Jason timeout, and VAL
timeout are pipeline or hardware settings, not MOOSE method parameters.

The compiler's schema-derived candidate language is explicit but no longer has
an arbitrary primitive-action depth bound. It contains direct producers,
finite backward STRIPS regressions over acyclic producible-precondition
dependencies, and optional causal resource-mode discharge paths. Backward
regression replaces an open requirement by the selected action's preconditions
and rejects a step when its delete effects contradict another open requirement.
An action's still-unbound parameters are first unified with compatible open
positive requirements; only parameters that remain unbound receive fresh
variables. Search terminates by forbidding a repeated alpha-normalized
requirement/producer step and retaining only the shortest body for an equivalent
requirement and completion-effect contract. This search is enabled only when
the producer-precondition predicate graph reachable from the target is acyclic.
Cyclic targets rely on validated provider macros and separately certified
recursive modules rather than an unrestricted instance-level planner.

Removing this acyclic gate is not an accepted fallback. Alpha-normalized cycle
blocking makes the signature space finite but can still enumerate a
combinatorial number of lifted requirement sets. A real Logistics probe exceeded
600 seconds under that experimental configuration, whereas the retained
acyclic compiler completed in seconds. Cyclic producer dependencies therefore
require an evidence-guided mode-path or a separately proved lexicographic
progress certificate before they enter the supported compiler fragment.

Resource-mode discharge separately searches a finite symbolic mode graph and
forbids repeated alpha-normalized resource modes. Consequently, a schema
candidate may contain more than five actions, but every accepted path is finite
and symbolically replayed. A validated Evidence Module macro is also never
truncated. Clingo optimality remains only within this generated certified
candidate language. These are structural scope restrictions, not domain-name
rules and not MOOSE parameters.

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

Deleting one obstruction is not sufficient by itself. Clingo jointly selects
the cross-predicate preparation graph and relation-preserving action branches.
Cross-predicate preparation edges must form a directed acyclic graph. Each
selected edge receives natural-number caller and callee ranks with
`caller_rank > callee_rank`, while its local negative precondition guard falls
from unsatisfied to satisfied before the original target is retried.
Same-predicate recursion is exempt from this predicate-rank rule only when it
has the separate relational decrease certificate above.

Relation threats are evaluated over this selected preparation graph, not the
larger raw candidate graph. A branch such
as `unstack; stack`, which exchanges one `on` atom for another, cannot coexist
with recursion certified by the global `count(on)`. For an anchored cone,
the compiler composes final PDDL effects and permits a relation add only when
the branch trigger maps the same anchor argument and its guards prove that the
new anchor differs from the protected anchor. The query compiler independently
rechecks the same selected preparation edges and anchored effect condition from
the final library rather than trusting metadata alone.
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

The compiler accepts a finite cleanup path only when the PDDL schema certifies
all of the following facts:

- each cleanup edge deletes the current producer-created debt mode without
  immediately re-adding it, and the terminal edge restores the consumed free
  mode; for example `drop(H,C,B,P)` deletes `lifting(H,C)` and restores
  `available(H)`;
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

Multi-step discharge is supported when every intermediate mode carries the same
schema-derived capacity key and occupant roles, no normalized mode repeats,
every action is symbolically executable, and the final state preserves the
atomic target. The compiler also records the complete release-action path, not
only its final action. It does not yet synthesize a query-local restricted
portfolio for an overloaded producer predicate whose safe and unsafe branches
are distinguished only by untyped static roles. In the untyped Depots PDDL,
for example, `at/2` is produced by both `drive` and `drop`; schema syntax alone
does not prove that `truck(B)` and `crate(B)` are disjoint. If a recursive
resource preparation requires only the `drive` portfolio while `drop` would
increase a protected support cone, the compiler rejects that closure instead
of assuming role disjointness or recognizing either predicate name.

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
internal-module closure, enforces an acyclic cross-predicate preparation graph,
and rejects selected relation producers reachable from a ranking root unless
their final effects preserve the certified anchored cone.

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

After selection, already-true branches are rendered first. A producer macro
with a target-preserving causal resource-discharge certificate precedes a
shorter producer that would leave the resource occupied. A preparation branch
derived from that discharge path also precedes the outstanding-debt producer;
ordinary complete action-only macros still precede ordinary recursive repair
branches. This ordering changes neither branch contexts nor effects: an
inapplicable discharge branch is skipped by normal AgentSpeak context matching.

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
must first be satisfiable; then Clingo first maximizes relational recursive
capabilities with strict well-founded certificates, next maximizes compatible
acyclic precondition-discharge capabilities, and finally minimizes branch
count, context count, and body cost. The first priority reflects unbounded
structural generalization rather than a domain name or predicate name.
Optimality is claimed only within the generated certified candidate space, not
over all possible AgentSpeak programs.

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

The current implementation supports finite acyclic protected resource-mode
discharge when every step is certified directly by PDDL preconditions and
effects. It is not complete for all parking cases. If a release path requires
an overloaded untyped producer to be restricted to one context-dependent
branch portfolio, or if every available cleanup path would delete the protected
target without a representable non-unification guard, the compiler rejects the
branch rather than patching the domain by name.

### Certified Existential Preparation Projection

A producer action can require several dynamic preconditions that cannot all be
true at the same location or process stage. Requiring every sibling
precondition in the context of every preparation branch can therefore create a
deadlock. The compiler now projects an unrelated dynamic sibling out of one
preparation context only under all of these schema-derived conditions:

- the producer-precondition dependency graph is acyclic and traverses a
  schema-inferred single-valued fluent, such as one object's current location;
- every projected sibling has exactly one PDDL producer schema;
- the static preconditions of that producer remain in the context as
  feasibility witnesses;
- nested producer variables are alpha-renamed away from all outer variables;
- the branch recursively rechecks the original atomic target before its
  primitive producer can execute.

For example, an image producer may require both `calibrated(C,R)` and
`at(R,IW)`. Calibration itself may require visiting another waypoint. The
calibration repair branch may omit the current dynamic `at(R,IW)` requirement,
but it retains static facts establishing that `C` is on board `R`, supports the
requested mode, has a calibration target, and that suitable waypoints are
visible. After calibration, `!have_image(...)` is called again, so the final
primitive image action still requires the full original producer context.

If projection dependencies are cyclic, or a projected obligation has several
producer schemas, the candidate keeps the former full connected context. At
selection time, cross-predicate preparation branches are optional recursive
capabilities rather than mandatory evidence obligations. Clingo chooses an
acyclic subset and seals each selected branch with its caller/callee dependency
ranks. A cyclic subset is rejected; it is not retained as an unordered strongly
connected component. This is a fail-closed compositional rule, not arbitrary
schema planning.

### Certified DFA Guard Serialization

Every distance-reducing DFA progress edge is compiled into one query-local
`trans` helper guarded by the current runtime monitor state. A singleton
positive guard calls its atomic module once and
rechecks the guard, which is action-equivalent to the former linear call while
adding declarative completion checking. For a conjunctive guard, the compiler
computes conservative conditional may-add and may-delete summaries over the
final selected atomic module call graph. Every effect retains its branch's
positive, negative, equality, and disequality context. Effects are composed to
successful atomic-module completion, so a primitive add later deleted or a
delete later restored is represented by its completion polarity. The summary is a finite relational
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
universal summary, the compiler may derive a candidate support-depth order:
every positive goal uses one binary relation with a compiler-generated
relational decrease certificate, the requested relation graph is functional and
acyclic, and supports can be ordered before dependants. That order is not by
itself an execution certificate. Every selected branch must also preserve all
earlier ranked achievements. A recursive repair is admitted only when it
discharges one explicit negative context obligation, its preparation module has
a complete summary, and its recursive self-call is rewritten to the enforced
query-local alias. This rule records the explicit paper assumption that the
relation is acyclic in every reachable execution state. It is a structural
assumption over PDDL effects and selected modules, not a domain or
predicate-name switch.

The enforced portfolio is selected per ordered literal occurrence, not once per
predicate symbol. A literal occurrence is one concrete position in the guard;
for example, `on(middle,lower)` and `on(upper,middle)` are two occurrences of
`on/2`. They have different protected prefixes after support-depth ordering, so
the compiler independently certifies which `+!on/2` branches preserve the
goals established before each position. Equivalent occurrence portfolios are
shared under one helper only after their selected branch-name sets coincide.
This prevents a branch unsafe for a late occurrence from globally removing a
recursive branch that is safe and necessary at an earlier occurrence. Plan
contexts such as `not clear(X)` and `not holding(X)` are alternative
applicability cases; the compiler does not incorrectly require one preparation
module to preserve every alternative context simultaneously. Persisted
certificates therefore record selected branch names by literal index and report
recursive closure only when at least one selected branch actually contains an
internal achievement call.

If the ranked portfolio cannot be certified, the compiler may instead enforce a
query-local preservation-safe action-only selection. An action-only branch is a selected
atomic plan whose body is a finite sequence of primitive PDDL actions and has no
internal achievement call. The compiler symbolically executes the whole branch,
keeps only branches whose conditional net deletes cannot unify with any sibling
goal and whose net adds cannot unify with any negative guard, copies those branches under a query-local helper trigger, and makes every
transition repair call the helper. Merely proving that a safe branch exists is
not enough: copying the branch is what prevents Jason from selecting an unsafe
sibling from the original atomic trigger. Ground object names are alpha-normalized
to typed equality-pattern representatives during this check, while domain
constants and shared query variables remain fixed. This is a proof-cost
optimization and does not merge objects that may be equal in execution. The
filter retains every certified safe action-only branch; it does not claim a new
minimum-branch optimization. If no non-empty safe branch remains, the cycle is
still rejected. Mixed Boolean/numeric guards use exact action-only net Boolean
effects and constant-integer numeric deltas. If repairing one literal changes a
sibling numeric fluent, the compiler adds the corresponding ordering threat.
Query-local helpers are indexed by complete literal atoms, so equal predicate
names with different arguments or values cannot overwrite one another. A
literal without a complete preserving action-only branch remains
observation-only and cannot fall back to an uncertified atomic trigger.
For example, `in(package,vehicle) & capacity(vehicle)=2` may call a certified
pickup branch first and observe the resulting capacity equality second. This is
a cross-literal preservation certificate, not a completeness claim for
arbitrary numeric planning.
For a positive numeric equality, the query compiler may additionally derive a
one-action progress branch directly from a PDDL numeric effect. A unit delta is
admitted only under a strict directional guard, such as `N>0` before a
decrement toward zero, so each replay is monotone. A non-unit delta is admitted
only at the exact predecessor value `target-delta`, which prevents overshoot.
If the action has an unsatisfied producible predicate precondition or a
constant-bounded numeric precondition, the query compiler may add a certified
preparation branch. Predicate preparation strictly reduces the number of
missing positive producer preconditions. Numeric preparation strictly reduces
the prerequisite deficit, leaves the target numeric fluent unchanged, and
preserves the producer's other preconditions. The resulting ranking is
lexicographic and is persisted in the branch certificate; no fluent or action
name is recognized.

For an Until source state, literals common to all waiting self-loop cubes are
source invariants. The current action-strategy fragment requires one positive
progress literal for such a state. Every selected action-only macro is checked
at each primitive prefix: a positive invariant cannot be deleted and a negative
invariant cannot be added before the progress literal is established. The final
establishing action may consume a source invariant because strong Until
requires the left operand only at earlier positions. For a multi-step numeric
target, repeatable steps instead carry schema-derived non-unification guards,
for example `Other \== Protected`, while a step that must consume the protected
object is restricted to the exact predecessor value. A query-local numeric base
case observes the target equality and terminates recursive preparation.

All query-local composition uses capture-avoiding substitution. Atomic-plan
local variables are alpha-renamed away from both query variables and variables
owned by an outer producer before contexts and bodies are combined. This
prevents accidental constraints such as `Y \== Y` or one symbol being required
to denote both a store and a waypoint.
If independently summarized branches induce a conservative cycle, one
primitive action may replace that serialization only when symbolic execution
proves that its complete net effect establishes every Boolean and numeric
literal in the guard. This is a whole-guard certificate, not a domain-specific
numeric operator or an unrestricted arithmetic planner.
It never falls back to parser order or a monotonic step-helper path. Negative
guard literals remain context checks and are never converted into negative
achievement subgoals.

Negative predicates now carry fail-closed preservation and establishment
certificates. For a guard
such as `delivered(P) & not damaged(P)`, every feasible conditional `MayAdd`
effect of the selected `!delivered(P)` module is type-unified with
`damaged(P)`. A branch that may add the forbidden atom cannot enter the
unfiltered transition. The compiler either enforces a query-local action-only
selection containing only goal-achieving branches that preserve positive
siblings and negative guards, or raises `negative_guard_not_preserved` before
ASL rendering. The certificate records the concrete negative literals,
preservation status, selected branch names, and the
`atomic_module_completion` observation boundary. Predicate/action renaming and
PDDL sibling types do not alter this rule.

When a forbidden atom is present, the appender may repair its absence through
either a positive sibling's finite action-only branch or a directly matched
single PDDL action. Both cases require an exact net `MustDelete`, preservation
of every positive sibling, and no completion `MayAdd` for any forbidden atom.
Extra action parameters must be range-restricted by positive PDDL preconditions
or `obj_tp/2`. Free deleter parameters are first unified with compatible
positive-sibling add effects. Thus a relocation action whose delete binds the
origin and whose add binds the requested destination can establish
`at(destination) & not at(origin)` without leaving the destination variable
unconstrained. For example, an arbitrary action that adds `holding(H,C)` and
deletes `available(H)` certifies `holding(h,c) & not available(h)`; a
negative-only `not active(x)` may use a generic `deactivate(x)` schema for the
same reason. No predicate or action name is recognized by the algorithm. If no
establisher exists, the signed negative leaf succeeds only when the atom is
already absent rather than inventing a negative subgoal.

A negative-only edge succeeds when the atom is absent and may call only the
single-action `MustDelete` helper described above when it is present. No
`!not_p(...)` achievement is synthesized, and no waiting for exogenous deletion
is implied. Temporary addition followed by deletion before atomic-module return
is permitted by the completion summary. Negated numeric equality is checked by
the runtime monitor; without a certified numeric change-away branch it remains
observation-only rather than being rejected as malformed LTLf.

After certification fixes an order `L1, ..., Ln`, the appender prepends signed
negative obligations and compiles the result into a balanced transition repair
tree. A transition repair tree is
query-local AgentSpeak control structure: an internal helper for range `[i,j]`
calls the two midpoint ranges. A positive leaf checks or achieves `Li`; a
negative leaf checks `not N` and, when available, calls only its certified
`MustDelete(N)` helper. The root then calls a separate done helper. The done
helper re-enters the same transition only while the exact runtime monitor still
reports its source state. Once the monitor leaves that source state, the helper
returns and the top-level dispatcher follows the actual DFA state. This matters
when one atomic macro contains several primitive actions and crosses several
DFA edges before returning: requiring the immediately adjacent target state
would incorrectly replay a transition that has already completed. Guard truth
is still exact because only the runtime DFA can cause source-state exit; a
rejecting successor has no accepting shortcut and fails at top-level dispatch.
Thus balancing changes how Jason dispatches a certified serialization, not
which serialization or temporal semantics is used.

This replaces the old one-sibling-plan-per-literal representation. For `N`
positive literals, that representation gave one trigger `N` repair candidates
and could repeat that candidate scan after each repair, yielding quadratic
controller matching. The balanced tree has `O(N)` query-local nodes, maximum
trigger fan-out two, `O(N)` visits per pass, and `O(log N)` nesting depth. The
exact runtime monitor is consulted through the source-state completion belief
after each pass. The compiler records
`transition_controller_strategy=monitored_balanced_repair_tree` so experiments
cannot silently mix the two encodings. Tree helper names are not PDDL fluents,
atomic modules, or exported actions.

For a singleton transition, the tree has one leaf: if the literal is absent it
calls the same atomic module once, and the done helper checks whether the exact
monitor left the source state. It is therefore primitive-action equivalent to
the previous singleton wrapper when the module crosses one edge, while also
remaining correct when one macro crosses multiple edges.
For several DFA progress transitions, one independently generated tree is used
per distance-reducing edge; the current runtime monitor state selects applicable
dispatch plans. The tree does not provide action batching, make an uncertified
threat cycle safe, or make action-strategy synthesis complete.

The execution environment advances the real deterministic finite automaton
after the initial valuation and after every successful primitive PDDL action.
It updates query-local monitor-state and accepting beliefs used by the top-level
AgentSpeak controller. These beliefs are controller interface state, not domain
fluents and not exported actions. Same-source/same-target MONA valuation cubes
are grouped by their common achievement objective, while the monitor still
evaluates every original cube. Consequently a strong-until formula detects an
intermediate violation even when an atomic macro later restores the fluent.
This gives exact trace observation for the declared `F`, `X`, `U`, conjunction,
and literal-negation fragment. It does not prove that the generated action
strategy solves every satisfiable PDDL-times-LTLf product; missing certified
progress actions remain execution failure or timeout outcomes.

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
validated lifted LTLf JSON, then LTLf-to-DFA, then conjunctive/negative/numeric
guard validation, then AgentSpeak(L) append with a query-local primitive-step
DFA monitor. Direct PDDL test-goal wrappers are only an evaluation bridge for
benchmark smoke runs where the input is a PDDL problem file rather than a user
query artifact. Those bridge plans are marked with
`evaluation_pddl_goal_wrapper_bridge` metadata and must not be described as the
final natural-language query interface.

Unsupported numeric cases include arbitrary arithmetic expressions, real-valued
updates, optimization metrics as achievement goals, non-equality numeric goals,
and numeric goals that require a recursive ranking proof not present in the
validated evidence.

## Pinned Temporal Execution Evidence

The paper-eligible Temporal Extended Goal execution run is
`teg-paper-clean-e28bcea4`. It executed the complete 1,228-case benchmark from
commit `e28bcea4`, with no tracked source changes, 12 workers, 1,800-second
Jason and VAL limits, and a 64-MiB Java stack. Every atomic AgentSpeak library
input is recorded by SHA-256 hash in the run summary.

All 1,228 cases have an explicit Jason success marker, a complete primitive
PDDL action trace accepted by neutral-goal VAL, and acceptance by both the gold
and predicted finite-trace automata. Each predicted formula is compiled and
executed once; gold-DFA and predicted-DFA acceptance are two semantic checks on
that same replayed state trace, not two independent controller executions. The
domain totals are 720/720 classical,
360/360 bounded-numeric, and 148/148 serialized-width cases. The formula-profile
totals are 273/273 ordered-two, 272/272 ordered-three, 275/275 strong-Until,
137/137 same-state conjunction, and 271/271 same-state-with-negation.

This result establishes complete execution coverage only for the released
benchmark, supplied atomic-library hashes, and declared temporal and numeric
fragments. It does not establish action-strategy completeness for arbitrary
PDDL-times-LTLf products, arbitrary arithmetic planning, or universal
realizability under every type-compatible parameter assignment.

The paper-facing result generator is
`scripts/generate_aaai_result_tables.py`. It validates the benchmark and frozen
prediction hashes, requires a tracked-clean execution revision, requires exact
coverage of all benchmark sample identifiers, and re-hashes every atomic JSON
and ASL input before producing `result_macros.tex`, the per-domain table, the
per-profile table, and `paper_results.json`. For the exact libraries used by
the clean run, it records 1,568 joint certified candidates, 1,527 selected
branches, and 638.4 KiB of ASL. These are hash-locked structural measurements.
The earlier atomic generation batch did not record a clean source revision, so
its synthesis and compiler runtimes are not paper-eligible and must not be
inferred from timestamps or diagnostic logs.

## Temporal Semantic Conformance Suite

The versioned suite at
`paper_artifacts/temporal_semantic_conformance/v1/suite.json` checks the
declared finite-trace semantics independently of the 1,228-case execution
benchmark. Its hand-specified positive and negative traces cover atoms,
literal negation, same-state conjunction, Eventually, strong Next, strong
Until, and numeric-equality observation. Every case must agree among the
expected result, a direct recursive finite-trace evaluator, and the DFA
constructed by the real `ltlf2dfa`/MONA path. This avoids using the same DFA
implementation as both the system under test and its only semantic oracle.

LTLf traces are non-empty state sequences. A zero-action execution is therefore
the singleton trace containing the PDDL initial state, not an empty logical
trace. The suite contains predicate and integer-equality cases that are already
true initially. Both must produce an explicit Jason success marker, an empty
committed PDDL action file, a replay with zero actions and one state, and gold
and predicted DFA acceptance.

VAL 1.4 rejects an empty plan file as a malformed plan and exposes no
zero-action syntax. The validator therefore does not insert a synthetic noop
or label such a case as VAL-accepted. For zero actions, PDDL replay establishes
the initial state and action legality is vacuous; the result records
`legality_certificate=vacuous_zero_action_pddl_replay`,
`val_attempted=false`, and `val_success=null`. Every non-empty execution still
requires independent neutral-goal VAL acceptance. The sealed execution
benchmark contains only state-changing witnesses, so its 1,228 VAL results are
unchanged.

Pinned run `temporal-conformance-paper-67b82843` was produced from clean commit
`67b82843`. All 14 formula-semantics cases agree with their hand-specified
expectations under both independent evaluators, and both zero-action integration
cases pass Jason, singleton-state replay, and both DFA checks. Exact inputs,
tool versions, hashes, and per-case records are stored in
`paper_artifacts/temporal_semantic_conformance/v1/release_validation.json`.

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
