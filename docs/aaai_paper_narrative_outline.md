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
   than claiming arbitrary numeric planning.
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

The final evaluation answers five questions:

- **RQ1 Atomic coverage:** how often does MOOSE evidence compile into a closed,
  certified lifted AgentSpeak library?
- **RQ2 Compactness and invariance:** how much does joint selection reduce the
  candidate library, and do decisions survive vocabulary renaming, compatible
  parameter permutation, and irrelevant-fluent injection?
- **RQ3 Temporal correctness:** how often do supported DFA guards compile into
  preservation-certified controllers without changing order across DFA edges?
- **RQ4 End-to-end validity:** how often does Jason produce a complete action
  trace that both VAL and the corresponding finite-trace DFA accept?
- **RQ5 Efficiency:** what are synthesis, compilation, query-append, Jason, and
  validation costs, and how do library/controller size affect them?

The benchmark section records all 16 domain families and their pinned splits.
The system section records the MOOSE, compiler, Jason, VAL, MONA, memory,
timeout, worker, and seed configuration. The atomic experiment uses five fixed
independent seeds, one internal MOOSE worker per seed, and isolated policy and
library roots. It must report every seed separately plus the mean and sample
standard deviation; it must not union evidence or select a best seed. Outer
seed-process concurrency is an execution setting, not a MOOSE hyperparameter.
Cross-seed Jason/VAL runs remain sequential while per-test validation is
parallel within one seed. Noisy runtime comparisons require controlled repeated
runs and dispersion rather than timings collected under cross-seed contention.

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

## Required Final Tables and Figures

### Architecture Figure

Show two connected but separate flows:

```text
PDDL + training split -> MOOSE evidence -> certified domain compiler
                                         -> one AgentSpeak domain library

validated lifted LTLf -> real DFA -> certified transition controllers
                                  -> append to the same domain library

domain library + query controllers -> Jason -> PDDL trace -> VAL + DFA oracle
```

### Atomic-Library Table

One row per domain with at least:

```text
train/test counts
MOOSE evidence status
atomic compilation status
evidence candidates
schema candidates
selected branches
library size
Jason successes
VAL successes
median runtime
```

### TEG Table

One row per formula profile or domain/profile group with at least:

```text
query count
JSON-contract valid
DFA-language equivalent to gold
supported-fragment accepted
controller compiled
Jason success
VAL valid
finite-trace DFA accepted
median action count
median runtime
```

### Rejection Table

Keep translation errors, schema validation errors, unsupported DFA structure,
certificate rejection, Jason failure, timeout, VAL failure, and DFA-trace
rejection as separate statuses. A failed or timed-out Jason action prefix is
diagnostic evidence, not a successful plan.

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
2. executable experimental baselines or ablations that isolate the compiler
   and temporal-controller contributions;
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
