# AAAI Paper Narrative Outline

This document is the normative narrative and result-integration plan for the
AAAI manuscript under `latex_code/aamas_method_paper/`. It must remain aligned
with the implementation-facing decisions in
[`research_pipeline_decisions.md`](research_pipeline_decisions.md) and the
temporal-input contract in [`input_design.md`](input_design.md). Whenever a
better paper organization is adopted, update this file in the same commit as
the manuscript.

## Canonical Title and Thesis

The preferred title is:

> **From Generalized Planning to BDI Execution: Certified AgentSpeak Plan
> Libraries for Temporally Extended Goals**

The title names the source representation, the deployment target, and the
temporal scope without claiming that the system synthesizes an entire
Belief--Desire--Intention (BDI) agent. The output is an AgentSpeak(L) plan
library that a BDI interpreter such as Jason can execute.

The paper has one thesis:

> Generalized-planning evidence can be compiled into a reusable, executable BDI
> plan library, and supported temporally extended goals can be composed over
> that library, provided that every accepted atomic branch and temporal
> transition carries the required schema-derived certificates.

A certificate is a compile-time, machine-checkable obligation. For example, a
binding certificate proves that every variable in `stack(X,Y)` is supplied by
the trigger or positive context; a completion-effect certificate proves which
PDDL literals may be added or deleted when `!on(X,Y)` successfully returns.
The compiler is fail-closed: it emits code only when its obligations are
proved, and otherwise returns a structured rejection.

## AAAI Narrative Alignment

The narrative follows three accepted AAAI generalized-planning papers rather
than treating the manuscript as a software-module report.

- [Bonet, Frances, and Geffner, AAAI-19](https://doi.org/10.1609/aaai.v33i01.33012703)
  moves from a representation problem to formal semantics, a computational
  method, and experiments. Our paper must likewise define the target BDI
  representation before presenting compiler mechanics.
- [Frances, Bonet, and Geffner, AAAI-21](https://doi.org/10.1609/aaai.v35i13.17402)
  introduces generalized policies through a concrete `clear(x)` example, then
  gives the learning formulation, solver, and larger held-out evaluation. Our
  Blocks running example must similarly connect evidence, recursive lifting,
  and temporal composition throughout the paper.
- [Chen et al., MOOSE, AAAI-26](https://doi.org/10.1609/aaai.v40i43.40938)
  separates the synthesis and instantiation stages in an early architecture
  figure, states soundness/completeness conditions separately, and organizes
  experiments by explicit questions. Our paper must separate domain-library
  synthesis from query compilation, place guarantees in their own section, and
  make every result answer a declared research question.

The BDI and temporal bridge must also be positioned against primary work on
[declarative AgentSpeak goal patterns](https://doi.org/10.1145/1160633.1160869),
[BDI plan failure](https://doi.org/10.1145/1329125.1329134), and
[temporally extended agent goals](https://doi.org/10.65109/ttvp5714). These
works supply execution semantics and design precedent; they do not implement
our evidence-to-library compiler.

## One Running Example

Use one small Blocks example in the Introduction, Method, Temporal Composition,
and Evaluation case study.

The evidence-side example begins with a readable MOOSE singleton-goal rule for
`on(X,Y)`, such as a regressed condition that permits `stack(X,Y)`. The compiler
may derive internal producible modules from the PDDL schema closure even when
MOOSE did not observe them as training goals. A representative recursive result
is:

```asl
+!on(X,Y) : holding(X) & clear(Y) <-
	stack(X,Y).

+!on(X,Y) : not clear(Y) <-
	!clear(Y);
	!on(X,Y).
```

The temporal-side example uses a finite-trace goal such as
`F(on(X,Y) & X(F(clear(Z))))`. The first DFA progress transition invokes the
domain module for `on(X,Y)`; a later transition invokes `clear(Z)`. A
conjunctive transition is treated as one state condition, not as an unchecked
sequence of independent calls. The example must explicitly show that atomic
modules stay in the domain library while `g_query` and `g_query_trans_1` are
query-local BDI intentions.

Do not substitute a benchmark-specific rule into the algorithm. The example
illustrates schema-driven behavior; the implementation and claims remain
invariant to predicate and action renaming.

## Final Section Contract

### Scientific Exposition Rule

The main paper explains each mechanism through a research failure mode, a
semantic condition, and the resulting guarantee or rejection boundary. It does
not present process scheduling, output-directory layout, command-line flags, or
internal class names as contributions. Those details belong in the
reproducibility artifact and `docs/research_pipeline_decisions.md`.

Use one symbol-invariant example whenever a certificate would otherwise be
opaque. For resource restoration, an illustrative acquisition deletes
`free(R)` and adds `held(R,O)`; the method must state that names are placeholders
and that the certificate is inferred from shared arguments and PDDL effects. For
a mixed transition such as `at(P,L) and fuel(V)=3`, explain that one symbolic
effect proof must establish both conditions in the same state. Do not replace
these semantics with labels such as `certificate-dependent`.

### Abstract

The abstract follows a five-part structure:

1. **Problem:** generalized planners return reusable policies, while BDI agents
   require executable and maintainable plan libraries.
2. **Gap:** direct policy-to-AgentSpeak translation does not establish binding,
   closure, recursive progress, resource restoration, or safe temporal
   composition.
3. **Method:** jointly certify and select MOOSE evidence macros and PDDL-derived
   atomic modules, then compile supported LTLf DFA transitions into query-local
   controllers.
4. **Guarantee boundary:** state candidate-space optimality and supported-
   fragment soundness, together with fail-closed rejection.
5. **Results:** after the clean final runs, report one atomic-compilation number,
   one Jason+VAL execution number, and one DFA-acceptance or TEG-translation
   number. Do not insert unpinned diagnostic results.

### 1. Introduction

The Introduction establishes the representation bridge rather than listing
software components.

1. Contrast one grounded classical plan, one generalized policy, and one BDI
   plan library.
2. Explain why compilation is not formatting: variables must be safely bound,
   internal calls must be closed, recursion must terminate, and resource use
   must be restored.
3. Explain why a temporally extended goal (TEG), meaning a goal over a finite
   state trace, cannot generally be replaced by an arbitrary sequence of
   achievement calls.
4. Introduce the Blocks running example.
5. Present the two-stage architecture and three implemented contributions.
6. End with the supported-fragment boundary rather than universal-planning or
   full-LTLf claims.

### 2. Problem Formulation and Foundations

Define only concepts used by the algorithms:

- a typed STRIPS/PDDL Boolean core, its bounded-integer resource extension, and
  their state-transition semantics;
- a generalized-planning task and readable MOOSE evidence;
- an AgentSpeak achievement plan, a lifted module, and library closure;
- an LTLf formula and its deterministic finite automaton (DFA);
- the compilation input `(D, I_train, E, phi)` and output `(L_D, Q_phi)`.

`L_D` is the one maintained domain library. For example, it contains reusable
`+!on(X,Y)` and `+!clear(X)` modules. `Q_phi` is the set of query-local plans,
for example `+!g_query` and `+!g_query_trans_1`, appended for one temporal
query. State the allowed output vocabulary and supported temporal fragment in
this section.

### 3. Certified AgentSpeak Plan-Library Synthesis

This section covers only the post-evidence, pre-AgentSpeak domain compiler.

1. Normalize provider output into the provider-neutral
   `PolicyEvidenceProgram` representation.
2. Compute producible-fluent closure from PDDL add effects and positive
   preconditions. Static predicates remain contexts.
3. Generate the finite schema-derived candidate language: direct producers;
   backward STRIPS regression over acyclic producer dependencies; and finite
   causal resource-mode discharge. Regression unifies producer preconditions
   with compatible open requirements before introducing fresh variables.
   Termination comes from
   forbidding repeated alpha-normalized requirement/producer roles and resource
   modes, not from an arbitrary action-depth bound. Validated evidence macros
   are never truncated. Cyclic dependencies require provider evidence or a
   separately certified recursive module; this is not an instance-level planner.
4. Summarize the implemented certificates in one table: binding, symbolic
   executability, achievement, closure, relation-ranked recursive progress,
   finite resource-mode discharge, and Clingo-selected acyclic cross-predicate
   preparation with strictly decreasing dependency ranks.
5. Explain the joint Clingo optimization over evidence and schema candidates.
   The precise claim is global optimality only inside the generated certified
   candidate space.
6. Render the selected modules into the one maintained AgentSpeak domain
   library.

Detailed certificate definitions may remain in the main paper when required to
understand a contribution. Long proof steps and secondary implementation cases
belong in supplementary material so that final results fit the seven-page AAAI
technical-content limit.

### 4. DFA-Guided Composition of Temporally Extended Goals

This section covers only query-specific control over the selected domain
library.

1. Parse validated lifted LTLf JSON with the real `ltlf2dfa` and MONA
   toolchain. Do not use the removed ordered-sequence fast path.
2. Give every DFA edge that strictly reduces graph distance to acceptance one
   transition controller guarded by the current query-local monitor state.
3. Treat a conjunction on one edge as one achievement block whose literals
   must hold in the same observable state.
4. Treat a negative literal such as `not calibrated(C,R)` as a signed context
   obligation, never as `!not_calibrated(C,R)`. A query-local helper may
   establish it only through a certified positive-sibling branch or single PDDL
   action with exact net `MustDelete`, sibling preservation, and no forbidden
   completion `MayAdd`.
5. Build a threat graph from certified completion summaries. An edge
   `G_j -> G_i` means a module for `G_j` may delete `G_i`, so `G_j` must be
   repaired first.
6. For a cyclic threat graph, use only a certified preserving portfolio or a
   supported ranking proof; otherwise reject. Select the preserving portfolio
   per ordered literal occurrence, because two occurrences of one predicate can
   have different protected prefixes. Share query-local aliases only for
   identical certified portfolios, and explain that alternative plan contexts
   are not simultaneous obligations.
7. For mixed Boolean/numeric guards, use complete action-only net Boolean
   effects and constant-integer numeric deltas; index helper selection by the
   full literal atom and leave uncertified literals observation-only. Explain
   strict unit progress, exact non-unit predecessor guards, and the complete
   single-action whole-guard certificate as three bounded strategies rather
   than claiming arbitrary numeric planning. A whole-guard helper must be
   callable from every positive literal it establishes and must carry the
   certificate's complete anchor arguments.
8. For an Until source state, extract common waiting-loop literals as source
   invariants. Require primitive-prefix preservation until the single positive
   progress literal is established. Explain lexicographic predicate/numeric
   precondition preparation, repeatable non-unifying numeric steps, exact
   terminal predecessors, and capture-avoiding composition.
9. Compile the certified order into a balanced binary repair tree. The tree is
   an AgentSpeak indexing structure with trigger fan-out at most two; it does
   not reorder DFA transitions or add planning semantics.
10. Advance the real deterministic finite automaton after the initial valuation
   and every successful primitive PDDL action. Explain that the integrated
   runtime monitor gives the declared formula fragment primitive-step trace
   semantics, while action-strategy synthesis remains incomplete. A transition
   helper returns on source-state exit so an atomic macro may cross several DFA
   edges; the top-level controller always dispatches from the actual monitor
   state.

### 5. Formal Guarantees

Keep guarantees separate from algorithm exposition, following the MOOSE
presentation.

The main paper should contain:

1. **Local atomic-branch soundness:** under its certified context and
   type-consistent grounding, an accepted branch is executable and establishes
   its trigger when it returns, assuming called modules satisfy their own
   contracts.
2. **Certified candidate-space optimality:** Clingo satisfies every encoded
   evidence and closure obligation and returns the lexicographic optimum inside
   the generated candidate space.
3. **Supported-transition composition soundness:** if signed obligations are
   initially satisfied or established by their certified helpers, selected
   modules terminate, and their certified completion effects preserve earlier
   positive and negative obligations, primitive-step monitor advancement leaves
   the source state only through a real DFA edge whose complete cube holds.
4. **Balanced-tree structure:** for `n` signed literals and `e` certified repair
   helpers, the generated query-local tree has `2n+e+2` plans, maximum trigger
   fan-out two, logarithmic nesting depth, linear work per pass, and the same
   certified literal order.
5. **Runtime-monitor trace fidelity:** monitor-state beliefs are the result of
   deterministic DFA transition evaluation after every primitive action, not a
   second planning semantics or a domain fluent.
6. **Initial-state identity case:** zero primitive actions denote the singleton
   trace containing the PDDL initial state. Initial DFA acceptance returns an
   empty committed action trace; it never inserts a noop.

Every theorem must state its assumptions next to the claim. Do not elevate
candidate-generation completeness, arbitrary AgentSpeak optimality, arbitrary
DFA strategy synthesis, or primitive-state safety to a theorem.

### 6. Experimental Evaluation

The evaluation must match the paper's actual contribution: MOOSE is one
instantiated Evidence Module provider, while the proposed method is the
post-evidence library compiler and temporal query compiler. There is therefore
no single global planner baseline. The final evaluation answers five questions:

- **RQ1 Evidence-to-library efficacy:** relative to validated direct adaptation
  of the same normalized evidence, how much do schema-certified lifting and
  internal closure improve module coverage and held-out execution?
- **RQ2 Compiler contribution:** what are the separate effects of action-only
  schema closure, decomposed recursive/resource/preparation candidate
  generation, and joint Clingo selection on coverage, size, and runtime?
- **RQ3 Temporal composition correctness:** relative to a controller using the
  same real DFA, atomic library, monitor, and Jason runtime but no
  effect-preservation reasoning, how much do threat ordering and preserving
  branch portfolios improve VAL- and DFA-valid execution?
- **RQ4 Structural efficiency:** what do joint selection and the balanced repair
  tree change in branch count, controller plans, maximum trigger fan-out,
  compilation/load time, and execution time without changing semantics?
- **RQ5 End-to-end utility:** across domains, formula profiles, and evidence
  seeds, how often does the full system produce Jason+VAL+DFA accepted traces,
  and what reusable-library amortization is observed relative to raw MOOSE and
  per-instance planning references?

The registered atomic comparison is cumulative and paired on one exact
normalized evidence hash:

1. **Evidence Adapter:** schema-check and render provider macros;
   do not perform PDDL closure, internal-module synthesis, or optimization.
2. **Action Closure:** add PDDL producer closure without decomposed
   subgoal candidates.
3. **Maximal Certified:** add progress-, preparation-, and resource-certified
   decomposed candidates, then maximize the jointly compatible branch set under
   all hard certificates.
4. **Full Compiler:** minimize branch, context, and body cost over exactly the
   same candidate universe and hard constraints as Maximal Certified.

The registered temporal comparison holds the DFA, atomic-library hash, query
binding, and Jason runtime fixed:

1. **Unprotected DFA:** canonical within-edge serialization, real DFA,
   and primitive-step monitor, but no threat ordering or preservation portfolio.
2. **Certified Flat:** add complete-effect threat ordering and preserving
   portfolios, retaining flat sibling control.
3. **Certified Balanced:** replace only flat control with the balanced binary
   repair tree.
4. **Completion Monitor:** retain completion-effect certification and balanced
   control, observe the DFA only after an atomic module returns, and omit
   primitive-prefix source-invariant filtering because intermediate primitive
   states are not observable under this ablation. Run it on the complete paired
   benchmark, but attribute observation-boundary effects only on cases with
   intermediate-state obligations.

These four cumulative atomic rows are the complete registered matrix. Do not
claim additional one-certificate-off experiments: retaining an uncertified
branch would be unsound, while removing one candidate family changes closure
feasibility rather than only one downstream mechanism. Use the 13-case
fail-closed and symbol-invariance matrix to test the individual certificate
families. Likewise, signed-negative and bounded-numeric cases stay in the full
temporal benchmark with explicit support and failure statuses; do not invent
unregistered capability-switch rows. The historical sequence-only wrapper may
appear only as an evaluation-only weak reference; it must not return as a
production fast path.

The benchmark section records all 16 domain families and their pinned splits.
The system section records the MOOSE, compiler, Jason, VAL, MONA, memory,
timeout, worker, and seed configuration. The scientific purpose of the five
fixed seeds is to estimate variation caused by MOOSE's randomized goal-order
sampling. One internal MOOSE worker makes training problems consume the seeded
permutation stream sequentially, removing concurrent access to that stream as a
within-run confounder. Every seed is compiled and evaluated independently;
report every result plus the mean and sample standard deviation, never evidence
union or a best-seed result. Concurrent launch is only an artifact-level
throughput choice, and contended wall time is not a method result. Cross-seed
Jason/VAL runs remain sequential while per-test validation is parallel within
one seed.

Keep the two experimental estimands explicit. The five-seed atomic matrix
measures variability of evidence discovery, compilation, and atomic achievement
coverage. The pinned temporal matrix conditions on one exact SHA-256-identified
atomic-library snapshot and measures translation, query-controller execution,
and trace semantics. A recent conditional temporal result does not become
invalid because its library was generated under a different worker protocol,
but it cannot support a cross-seed atomic-robustness claim.

Raw MOOSE, LAMA for classical planning, ENHSP MRP+HJ for numeric planning, and
FOND4LTLf v0.0.4 plus LAMA for its grounded Boolean temporal subset are external
task-level references, not primary compiler baselines. Name these rows directly;
do not replace them with numbered identifiers. All nonempty achievement traces
require original-goal VAL. The direct temporal trace contains only projected
original-domain actions and requires PDDL replay, neutral-goal VAL, gold-DFA
acceptance, and predicted-DFA acceptance. FOND4LTLf compilation and LAMA search
share one 1,800-second, 8-GiB deadline. Numeric inputs and identifiers incompatible
with its underscore encoding are explicit unsupported cases. Published numbers
from different splits or hardware may be cited as prior results but must not be
inserted into paired experiment tables. Plan4Past is a design precedent for
holding the downstream planner fixed while comparing temporal compilations; it
is not directly comparable until any future-LTLf-to-past-LTLf translation has
been proved language-equivalent.

Atomic metrics are producible-predicate coverage, module closure, held-out
Jason+VAL coverage, branch/context/body costs, ASL bytes, and compile time.
Producible-predicate coverage has one paired denominator per seed/domain: all
predicate symbols in positive PDDL action effects. Every method is scored by
the module triggers it actually emits against that same set. Never let Evidence
Adapter or another reduced variant redefine the denominator through absent
closure metadata.
Temporal metrics are compile/rejection status, Jason success, VAL validity,
gold-DFA acceptance, action count, PAR-2 runtime, append time, controller size,
and maximum trigger fan-out. Plan length is compared only on jointly solved
instances. Report paired coverage differences, every seed, mean and sample
standard deviation. A rejection challenge suite and symbol-renaming,
parameter-permutation, object-renaming, and irrelevant-fluent metamorphic tests
are mandatory evidence for fail-closed and domain-independent behavior.

For temporal pairing, define the common DFA fingerprint over the formula, atom
binding, initial state, accepting states, and guarded transition graph. Exclude
conversion timing, artifact paths, and DOT text. Record a separate controller
fingerprint over the variant settings and generated query-local plans so the
paper can demonstrate identical DFA inputs without erasing controller changes.

The final paper must distinguish:

- **Gold semantic oracle:** the hidden structured LTLf formula defines the gold
  DFA used for exact language-equivalence checking and independent acceptance
  of the executed state trace.
- **Predicted TEG execution:** the language model translates controlled natural
  language into lifted LTLf JSON. After exact gold/predicted DFA-language
  equivalence, the predicted formula is compiled into the query controller and
  executed once. The resulting trace is checked by both DFAs.

The pinned version-1 artifact is not two duplicated execution runs. Gold-DFA
and predicted-DFA acceptance are separate semantic oracles over the same trace.
Do not describe this result as an independently executed gold-controller matrix.

Combining these two would make an LTLf translation error indistinguishable from
a compiler or BDI execution error.

Add a separate semantic-conformance paragraph before benchmark results. It must
report agreement among hand-specified expected truth, an independent direct
finite-trace evaluator, and the real MONA-derived DFA for every declared
operator. It must separately report predicate and numeric zero-action
integration. Because VAL 1.4 cannot parse an empty plan, report zero-action
legality as vacuous after successful PDDL initial-state replay and VAL as not
applicable, never as successful. Keep these cases outside the sealed 1,228-row
benchmark totals.

The pinned insertion is run `temporal-conformance-paper-67b82843` from clean
commit `67b82843`: 14/14 direct-semantics-versus-MONA cases and 2/2 zero-action
Jason/PDDL-replay/DFA integration cases pass. Keep its 16 cases separate from
the 1,228 benchmark denominator.

### 7. Related Work and Positioning

Place Related Work after the method and evaluation protocol so that the output
artifact is already clear. Organize it by representation gap:

1. generalized planning, MOOSE, feature policies, and sketches;
2. policy reuse and solver-backed compact rule selection;
3. AgentSpeak plan libraries, declarative goal patterns, and plan failure;
4. temporally extended BDI goals and LTLf-to-DFA synthesis.

End with the exact novelty boundary: MOOSE goal regression, Clingo solving,
AgentSpeak semantics, and LTLf-to-DFA translation are prior work. The
contribution is their fail-closed connection through a certificate-carrying
compiler that emits executable domain modules and query-local controllers.

### 8. Limitations and Conclusion

Limitations must correspond to observed rejection categories and implemented
bounds: MOOSE is the only experimentally instantiated evidence provider;
schema regression is restricted to finite acyclic producer dependencies;
resource discharge requires a finite non-repeating keyed mode path; untyped
overloaded producers that require different nested branch portfolios remain
unsupported; uncertified cycles are rejected; numeric disequality achievement
remains observation-only without a certified change-away branch; and runtime
monitoring does not make action-strategy synthesis complete for arbitrary
PDDL-times-LTLf products.

The Conclusion answers three questions only: what representation gap was
closed, why the output can be executed by a BDI agent, and which temporal goals
are certified. Do not repeat the implementation inventory.

## Final Visual Program

The main paper targets exactly four figures, four tables, and one algorithm.
This follows the visual argument used by closely related planning papers:
MOOSE combines an architecture figure, a full-width worked goal-regression
example, synthesis tables, and cumulative coverage curves; AAAI-24 work on
generalized planning with language models combines a pipeline, a main coverage
table, runtime scaling, ablation, and failure analysis; temporal-planning work
uses automaton diagrams together with coverage/runtime plots. Our figures must
therefore explain the representation bridge and its certificates before they
show aggregate success numbers.

### Figure 1: End-to-End Architecture

Use a full-width `figure*` near the end of the Introduction. Replace the current
text box; do not retain both. Draw three left-to-right horizontal lanes:

1. **Reusable domain compilation.** A gray input box contains the PDDL domain
   and complete train split. An amber box represents MOOSE readable singleton
   policy evidence, for example an `on(X,Y)` rule with a finite action macro.
   Four blue compiler boxes then show evidence normalization, PDDL producible
   closure and candidate generation, certificate checking, and joint Clingo
   selection. The lane ends in one green maintained AgentSpeak domain library.
2. **Query-specific temporal compilation.** A gray box contains typed,
   externally bound parametric LTLf JSON. Blue boxes show real
   `ltlf2dfa`/MONA construction, signed transition-guard extraction,
   threat/preservation certification, and balanced repair-tree compilation.
   A downward append arrow enters the same green domain library; it must be
   labelled “query-local controllers,” not a second library.
3. **Execution and independent validation.** The combined library enters Jason.
   The exported primitive PDDL trace fans out to neutral-goal VAL, gold-DFA
   acceptance, and predicted-DFA acceptance. Red rejection exits leave any
   compiler box when a required certificate cannot be constructed.

Use gray for inputs, amber for external evidence, blue for our compiler, green
for certified artifacts, and red only for fail-closed rejection. Every color
must also have a distinct border/shape so the figure remains meaningful in
grayscale. Draft caption:

> **Figure 1: End-to-end certified compilation and validation.** The reusable
> domain stage compiles singleton-goal evidence and PDDL schemas once into one
> maintained AgentSpeak library. Each temporal query contributes only
> query-local controllers derived from real DFA transitions. Jason actions are
> validated independently by VAL and both finite-trace automata; uncertified
> compilation choices are rejected.

### Figure 2: From Policy Evidence to a Lifted Atomic Module

Use one full-width row with four labelled panels and one consistent Blocks
example. This is a method explanation, not an empirical result.

1. **(a) Evidence.** Show one readable MOOSE rule for singleton `on(X,Y)` with
   its lifted context and finite action macro. Include a small training-instance
   fragment to make clear that the policy is evidence rather than final ASL.
2. **(b) Schema closure.** Show only the relevant PDDL `stack`, `unstack`, and
   producer/precondition effects. Highlight that producible `clear/1` and
   `holding/1` enter closure even when they never appeared as training goals;
   static predicates remain context-only.
3. **(c) Certification and selection.** Represent evidence macros and
   schema-derived candidates entering one candidate set. Attach compact badges
   for binding, symbolic execution, achievement, closure, progress, and resource
   restoration. Show Clingo selecting the minimum-cost feasible subset inside
   this certified space; do not label it globally minimal ASL.
4. **(d) Executable module.** Show three short AgentSpeak branches: already
   true, recursive preparation `!clear(Y); !on(X,Y)`, and direct `stack(X,Y)`.
   Use variables, no training object names, and only PDDL fluents/actions.

Draft caption:

> **Figure 2: Certified lifting of singleton-goal policy evidence.** Provider
> macros and PDDL-derived closure candidates enter the same certified candidate
> space. The selected AgentSpeak module is lifted, internally closed, and may
> introduce producible helper goals absent from the evidence; compactness is
> optimal only within the generated candidate language.

### Figure 3: DFA Transition Compilation and Runtime Monitoring

Use a full-width four-panel figure tied to one conjunctive transition containing
a negative obligation.

1. **(a) Formula and DFA.** Show a typed, bound LTLf example and the real MONA
   deterministic finite automaton. Mark one distance-reducing edge and one
   accepting `true` self-loop.
2. **(b) Signed guard and threat graph.** Expand the selected edge into positive
   achievements and negative absence obligations. Draw a directed threat edge
   `G_j -> G_i` when completing `G_j` may delete `G_i`; annotate that this means
   `G_j` is repaired first. A negative literal must be labelled “observe/exact
   deleter,” never `!not_p`.
3. **(c) Certified order and balanced tree.** Show the topologically certified
   literal order feeding a balanced binary repair tree. Internal nodes dispatch
   contiguous ranges; a leaf either observes its literal or invokes one
   certified atomic module. Add a small singleton inset showing that one DFA
   literal becomes one leaf and therefore has the same primitive-action behavior
   as a direct atomic call.
4. **(d) Primitive-step semantics.** Show each successful PDDL action updating
   the runtime DFA monitor. Source-state exit returns to top-level dispatch;
   `trans_done` replays only while the complete guard is not yet satisfied and
   the monitor remains at the source. End at Jason trace, VAL, and both DFA
   oracles.

Draft caption:

> **Figure 3: Preservation-safe compilation of one DFA progress transition.**
> Conditional module summaries induce a threat order over signed guard
> obligations. A balanced AgentSpeak repair tree realizes that fixed order with
> trigger fan-out at most two, while the real DFA monitor observes every
> primitive action. Uncertified cyclic threats or negative-literal repairs are
> rejected rather than serialized heuristically.

### Figure 4: Main Empirical Evidence

Generate this figure from machine-readable JSON; do not draw empirical points
manually in PowerPoint. Use one full-width row of three panels with a shared
colorblind-safe domain/profile palette:

1. **(a) Atomic test coverage.** Horizontal dot-and-interval plot, one row per
   domain. Plot all five single-worker seed values as faint points and the mean
   with sample-standard-deviation interval as the primary mark. The x-axis is
   Jason+VAL coverage in percent with 100% shown explicitly.
2. **(b) Certified reduction.** Paired dots or a dumbbell for generated
   certified candidates and selected branches per domain. Use a logarithmic
   count axis only if the final range requires it. Annotate the percentage
   reduction; do not compare raw library size across domains as if task counts
   were equal.
3. **(c) Temporal execution cost.** Empirical cumulative distribution of
   per-query runtime, one curve per declared formula profile. Include the
   1,800-second limit and distinguish curves by line style as well as color.
   Since the pinned matrix has complete coverage, this distribution is more
   informative than five identical 100% bars.

Draft caption:

> **Figure 4: Atomic robustness, certified reduction, and temporal execution
> cost.** Panel (a) reports individual values and mean $\pm$ sample standard
> deviation over five independently seeded, single-worker MOOSE runs. Panel (b)
> compares certified candidates before and after joint Clingo selection. Panel
> (c) is the empirical cumulative distribution of wall-clock runtime for the
> pinned bound temporal queries; the vertical line marks the 1,800-second limit.

### Table 1: Supported Fragment and Rejection Boundary

Keep one compact single-column table with columns:

```text
Construct | Accepted strategy | Rejection boundary
```

Rows cover positive predicates, numeric equalities, positive conjunctions,
negative literals, mixed Boolean/numeric guards, disjunction, and primitive-
state safety. This table answers what the method supports; it must not contain
experimental success counts.

### Table 2: Certified Candidate Language

Merge the previous schema-grammar and certificate tables into one full-width
table with columns:

```text
Candidate family | Additional acceptance obligation | Excluded failure
```

Rows cover validated evidence macros, direct producers, acyclic regression,
relational recursion, resource-mode discharge, and cross-module preparation.
The caption states the obligations shared by every branch: typed binding,
symbolic executability, target achievement, and internal closure.

### Atomic Baseline/Ablation Table

Use short method names (Evidence Adapter, Action Closure, Maximal Certified,
and Full Compiler) and report paired results for every fixed evidence seed:

```text
compile/rejection status
producible target coverage
module closure
held-out Jason+VAL coverage
branch/context/body counts
ASL bytes
compiler time
```

Use short descriptive column phrases such as `Method`, `Coverage`, `Branches`,
`Library Size`, and `Time (s)`. Keep stable experiment identifiers in the
machine-readable artifact, not as `C0`/`C1`-style table labels.

### Temporal Baseline/Ablation Table

Use short method names (Unprotected DFA, Certified Flat, Certified Balanced,
and Completion Monitor) on the same query/DFA/library hashes:

```text
controller compiled/rejected
Jason success
VAL validity
gold-DFA acceptance
PAR-2 runtime
action count on jointly solved cases
controller plan count
maximum trigger fan-out
```

Use the method names above directly. Do not replace them with numbered temporal
variants or compressed one-letter oracle headings.

Keep Raw MOOSE, LAMA, MRP+HJ, and FOND4LTLf + LAMA in a separate external
reference table with short columns such as `Method`, `Scope`, `Output`, `Oracle`,
`Coverage`, `PAR-2`, and `Actions`. Do not mix their output representations or
costs into the compiler ablation table. Do not spend main-paper space on an
all-empty external-reference table: keep the registered design in this outline
and insert the table only after the native runners produce a complete hash-locked
matrix. If the final four-table budget is already occupied, place the full
external table in the supplement and report only the paired headline comparison
in the Evaluation text.

Generate all three comparison tables with
`scripts/generate_aaai_comparison_tables.py`. Its mandatory inputs are the
complete paired compiler result, Raw MOOSE summaries explicitly assigned to
seeds 0--4, the native LAMA/MRP+HJ summary, the direct FOND4LTLf summary, and
the challenge summary. The script must fail rather than render a partial table
when a method, seed, case, hash pairing, or clean-source condition is missing.
The final generator must fail closed over the registered corpus rather than
only compare methods with each other. It recomputes immutable identifier-set
digests for all 1,228 achievement cases, all 1,228 temporal cases, the 868
classical LAMA cases, and the 360 numeric MRP+HJ cases; duplicates and shared
omissions are invalid. It additionally requires the five Raw MOOSE runs to use
the exact seed-specific model-batch manifests consumed by the paired compiler
runs, one clean source commit for every downstream summary, the registered
resource protocol, pinned external binaries, and exactly 13 unique successful
challenge nodes. Report a failed contract as an infrastructure failure, never
as a method score.

### TEG Table

### Table 3: Five-Seed Atomic Evaluation

The final main table replaces the current provisional seed-0 domain table when
the registered five-seed matrix is complete. Use one row per domain and grouped
headers:

```text
Domain | Train | Test | Evidence runs/5 | Compiled runs/5 |
Jason+VAL coverage mean +/- sample SD | Certified candidates mean +/- sample SD |
Selected branches mean +/- sample SD | Reduction % | ASL KiB mean +/- sample SD
```

Group classical, numeric, and serialized-width domains with `\midrule`, not
background colors. A dash means not applicable, never zero. Do not pool or pick
the best seed. Draft caption:

> **Table 3: Five-seed atomic-library synthesis and held-out execution.** Each
> repetition trains MOOSE on the complete domain train split with one internal
> worker and a predeclared seed, compiles its evidence independently, and tests
> every atomic benchmark goal in Jason and VAL. Values are mean $\pm$ sample
> standard deviation over seeds 0--4; runs are never pooled or selected post
> hoc.

Until that result exists, `result_domain_table.tex` remains explicitly labelled
as a hash-locked seed-0 conditional-input table. It must not be described as the
five-seed result; move its detailed per-domain snapshot to supplementary
material when Table 3 is inserted.

### Table 4: Temporal Profile Evaluation

Use one full-width table with explicit columns:

```text
Profile | Equivalent translations / total | Bound queries | Controller compiled |
Jason success | VAL success | Gold-DFA accepted | Predicted-DFA accepted |
Median actions | Median seconds
```

Draft caption:

> **Table 4: Translation and execution by temporal profile.** Equivalent
> translations pass exact reachable-product gold/predicted DFA-language
> equivalence. All remaining columns are counts over bound queries except the
> median primitive-action and wall-clock costs.

### Failure and Rejection Reporting

Do not add a fifth main-paper table unless the final five-seed experiment has a
nontrivial rejection distribution that cannot be summarized in Table 3. The
supplementary artifact should always keep translation errors, schema validation
errors, unsupported DFA structure, certificate rejection, Jason failure,
timeout, VAL failure, and DFA-trace rejection as separate statuses. A failed or
timed-out Jason action prefix is diagnostic evidence, not a successful plan.

### AAAI Figure and Table Style Contract

- Cite every figure or table in the body before it appears. Figure captions go
  below figures; table captions remain above the tabular content through the
  template's normal `\caption` placement.
- A caption must define the population/denominator, aggregation over seeds,
  timeout, and every abbreviation needed to read the visual independently. The
  body explains interpretation rather than restating every cell.
- Use `booktabs`, no vertical rules, no colored table cells, and bold only for a
  genuine best comparable result. Use `--` for not applicable and never overload
  zero. Avoid `\tiny`; final table text must remain at least 8 pt.
- Use vector PDF for PowerPoint method figures with embedded fonts. Set the slide
  canvas to the final aspect ratio, use 7--9 pt text at final printed size, and
  export tightly cropped. Raster content, if unavoidable, must be at least
  250 dpi at final size.
- Use a colorblind-safe palette and redundant shape/line encodings. Figure text
  and mathematical symbols must remain readable in grayscale; never convey a
  certificate or failure state by color alone.
- The final empirical figure must be regenerated by a checked-in script from
  pinned JSON artifacts. PowerPoint is acceptable for conceptual Figures 1--3,
  but not for manually placing result points.

## Result-Insertion Contract for the TEG Agent

The agent that receives the final TEG run must:

1. use a clean, pinned Git revision and record all runtime settings;
2. regenerate LaTeX result macros from machine-readable artifacts instead of
   typing aggregate numbers into prose;
3. report predicted-controller execution separately from gold-DFA and
   predicted-DFA trace acceptance; do not count one trace as two executions;
4. require Jason success, VAL validity, and DFA trace acceptance for an
   end-to-end success;
5. add failure categories and representative counterexamples, not only total
   coverage;
6. update the Abstract, Introduction contribution summary, Evaluation,
   Limitations, Conclusion, reproducibility checklist, and this outline in one
   coherent change;
7. preserve the supported-fragment and observation-boundary assumptions even
   if an empirical case happens to pass outside them.
8. retain the zero-action conformance result as a separate semantic boundary;
   do not add a synthetic noop or merge it into the non-empty VAL denominator.
9. generate baseline and ablation values from the checked comparison release;
   do not hand-edit numeric LaTeX cells.

## Submission Readiness

The following result insertions are complete:

1. the pinned predicted-controller execution result from commit `e28bcea4`:
   1,228/1,228 Jason and neutral-goal VAL successes, with the same 1,228 traces
   accepted independently by both gold and predicted DFAs;
2. 475/475 frozen GPT-5.5 predictions satisfying the JSON contract and exact
   gold/predicted DFA-language equivalence;
3. the five profile totals from that run: 273 ordered-two, 272 ordered-three,
   275 strong-Until, 137 same-state conjunction, and 271 same-state with
   negation;
4. a generated 16-domain table for the exact hashed atomic-library inputs:
   1,568 certified candidates, 1,527 selected branches, and 638.4 KiB of ASL;
5. deterministic LaTeX macros and domain/profile tables generated by
   `scripts/generate_aaai_result_tables.py`; and
6. the corresponding quantitative Abstract, Introduction, Evaluation,
   Limitations, and Conclusion text.

The paper is not ready for submission until it additionally contains:

1. the registered five-seed atomic generation and independent Jason/VAL matrix,
   including a clean source revision, every seed result, mean and sample
   standard deviation, and non-contented timing evidence; the current table
   reports only the exact hash-locked seed-0 library structure consumed by the
   clean temporal run;
2. completed registered atomic and temporal ablation runs, plus the separately labelled
   external references, with empty manuscript cells populated only from their
   machine-readable summaries;
3. a rejection/failure analysis tied to stated assumptions; and
4. full or supplementary proofs for claims stronger than the current proof
   sketches; and
5. final camera-ready author and artifact metadata. The current compiled draft
   places all technical content, including the Conclusion, within pages 1--7;
   references begin later on page 7 and the checklist follows on pages 8--9.

The TEG execution matrix exists at
`artifacts/temporal_goal_execution_runs/teg-paper-clean-e28bcea4` and may be
reported. Its exact atomic inputs are hash-locked in the run summary and may be
reported structurally. The manuscript must not present unpinned atomic
generation time or provisional diagnostic runs as final timing evidence.

## Page Budget and Maintenance

AAAI allows seven technical-content pages under the current author-kit rules.
Use the following target allocation:

| Content | Target pages |
| --- | ---: |
| Introduction and architecture | 0.8 |
| Problem formulation and foundations | 0.8 |
| Certified plan-library synthesis | 1.8 |
| DFA-guided TEG composition | 1.0 |
| Formal guarantees | 0.5 |
| Experimental evaluation | 1.6 |
| Related work, limitations, conclusion | 0.5 |

When results are inserted, compress detailed certificate prose into tables and
move long proofs to supplementary material before removing definitions or
failure boundaries. The paper source, this outline, and both normative research
design documents must never disagree about architecture, terminology, or
supported capabilities.
