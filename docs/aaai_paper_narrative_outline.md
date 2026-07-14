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

> **GP2PL: From Generalized Planning Evidence to Certified BDI Plan Libraries
> for Temporally Extended Goals**

**GP2PL** expands to **Generalized Planning to Plan Libraries** and names the
complete framework: evidence normalization, validated policy lifting, temporal
query compilation, and execution validation. It does not rename any one of
those modules in isolation.

The title names the evidence source, the deployment target, the compilation
contribution, and the temporal scope without claiming that the system
synthesizes an entire Belief--Desire--Intention (BDI) agent. The scientific
target is a trigger--context--body BDI plan library. AgentSpeak(L) is the
concrete target-language realization used in this implementation, and Jason is
the evaluated interpreter; neither name defines the upper-level contribution.

The paper has one thesis:

> Generalized-planning evidence can be compiled into a reusable, executable BDI
> plan library, and supported temporally extended goals can be composed over
> that library, provided that every accepted atomic branch and temporal
> transition carries the required schema-derived certificates.

A certificate is a compile-time, machine-checkable obligation. For example, a
binding certificate proves that every variable in `stack(X,Y)` is supplied by
the trigger or positive context; a completion-effect certificate proves which
PDDL literals may be added or deleted when `!on(X,Y)` successfully returns.
The compiler accepts a candidate only when its obligations are proved and
otherwise returns a structured rejection.

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
  make every result answer one clearly stated question. Use descriptive
  paragraph headings rather than combined labels such as `RQ3--RQ5`.

The BDI and temporal bridge must also be positioned against primary work on
[declarative AgentSpeak goal patterns](https://doi.org/10.1145/1160633.1160869),
[BDI plan failure](https://doi.org/10.1145/1329125.1329134),
[BDI goal interference](https://www.ijcai.org/Proceedings/03/Papers/105.pdf),
and
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

Every paragraph must carry one identifiable argumentative role: motivate a
problem, define a concept, state a method, justify a design choice, present
evidence, or delimit a claim. Prefer concrete subjects and causal transitions
over inventories of implementation components. Terms such as `pinned`,
`hash-locked`, `pipeline`, and internal run identifiers belong in the
reproducibility material unless they are indispensable to distinguish two
experimental estimands. The Abstract and Introduction follow the narrative
cadence of accepted AAAI planning papers: problem, limitation of existing
representations, central idea, guarantee, and empirical result.

Apply citations at the sentence or tightly coupled claim cluster they support.
External definitions, prior methods, software behavior, benchmark provenance,
and baseline protocols require a verified primary source. GP2PL definitions,
algorithms, theorems, and measured results instead point to the relevant
internal figure, table, proposition, appendix, or released artifact; do not use
an adjacent prior-work citation to imply that a new GP2PL claim is inherited.
The abstract remains citation-free under the AAAI convention, but every
externally attributable claim must be supported when it first appears in the
main text.

The manuscript presents GP2PL as a theoretical representation-compilation
framework, not as a software architecture report. Its primary objects are a
normalized singleton-goal evidence relation, a finite set of certified lifted
BDI branches, a constrained feasible-library selection problem, conditional
completion summaries, and preservation-safe deterministic finite automaton
guard composition. MOOSE, Clingo, AgentSpeak(L), and Jason instantiate the
evidence, optimization, rendering, and execution interfaces respectively.
Internal class names, path layouts, worker scheduling, hashes, and command-line
flags belong in the technical or code-and-data appendix.

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
2. **Gap:** direct policy-to-BDI-plan translation does not establish binding,
   closure, recursive progress, resource restoration, or safe temporal
   composition.
3. **Method:** jointly certify and select MOOSE evidence macros and PDDL-derived
   atomic modules, realize the selected BDI library in AgentSpeak(L), and compile
   supported LTLf DFA transitions into query-local controllers.
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
5. Present the two-stage architecture and three implemented contributions in a
   continuous paragraph. An itemized contribution list is not forbidden by the
   AAAI template, but prose better matches this paper's short causal argument.
6. End with the supported-fragment boundary rather than universal-planning or
   full-LTLf claims.

### 2. Problem Formulation and Foundations

Define only concepts used by the algorithms:

- a typed STRIPS/PDDL Boolean core, its bounded-integer resource extension, and
  their state-transition semantics;
- a generalized-planning task and readable MOOSE evidence;
- a trigger--context--body BDI plan rule, a lifted module, and library closure;
- AgentSpeak(L) as the concrete rendering used by the implementation and Jason
  as its evaluated interpreter, without claiming portability to unevaluated BDI
  languages;
- an LTLf formula and its deterministic finite automaton (DFA);
- the compilation input `(D, I_train, E, phi)` and output `(L_D, Q_phi)`.

`L_D` is the one maintained domain library. For example, it contains reusable
`+!on(X,Y)` and `+!clear(X)` modules. `Q_phi` is the set of query-local plans,
for example `+!g_query` and `+!g_query_trans_1`, appended for one temporal
query. State the allowed output vocabulary and supported temporal fragment in
this section.

### 3. Related Work and Positioning

Place Related Work after the problem formulation and before the method. AAAI
does not prescribe one location, and MOOSE places it near the end, but this
paper connects three communities whose boundaries should be clear before the
compiler is introduced. Organize the section by representation gap:

1. generalized planning, MOOSE, feature policies, and sketches;
2. policy reuse and solver-backed compact rule selection;
3. procedural BDI plan libraries, AgentSpeak declarative goal patterns, plan
   failure, and definite/possible effect summaries for goal interference;
4. temporally extended BDI goals and LTLf-to-DFA synthesis; and
5. natural-language-to-temporal-logic and planning-constraint translation,
   structured prompt programming, prompt-based semantic-parser robustness, and
   the stricter typed, externally bound validation contract used here.

End with the exact novelty boundary: MOOSE goal regression, Clingo solving,
AgentSpeak semantics, conditional effect summaries for BDI goal interference,
and LTLf-to-DFA translation are prior work. The contribution is their connection
through a certificate-carrying compiler that derives the summaries from
generalized-planning evidence and PDDL schemas, constructs executable domain
modules, and composes query-local controllers.

### 4. GP2PL Domain-Library Compilation

This section covers only the post-evidence domain compiler. Its candidate and
certificate representation is defined at the trigger--context--body BDI
plan-rule level; the implemented final rendering targets AgentSpeak(L).

1. Normalize provider output into a provider-neutral singleton-goal evidence
   program. Do not expose an internal class name in the main narrative.
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
6. Render the selected modules into the one maintained domain library. State
   explicitly that AgentSpeak(L) is the evaluated realization, not the
   definition of the compilation contribution.

Detailed certificate definitions may remain in the main paper when required to
understand a contribution. Long proof steps and secondary implementation cases
belong in supplementary material so that final results fit the seven-page AAAI
technical-content limit.

### 5. DFA-Guided Composition of Temporally Extended Goals

This section covers only query-specific control over the selected domain
library. Open by defining the semantic input boundary rather than prescribing a
surface grammar for users. The evaluated front end receives a source utterance,
the public PDDL symbol catalogue, declared typed parameters, and binding
constraints; it returns the exact eight-key lifted LTLf artifact. Explain its
formula, atom-table, parameter, constraint, metadata, and support-status fields
as one parametric specification. Parameters are externally bound at invocation,
not quantified or exhaustively grounded. The controlled utterances in the
released benchmark define the evaluated distribution rather than a required
user syntax. Keep the frozen prompt and field-by-field schema in the Technical
Supplement and public artifact.

1. Validate the structured artifact fail-closed, meaning rejection rather than
   silent repair. Require the exact schema; exactly one atom-table entry for
   every formula symbol and no unused entry; PDDL catalogue membership; valid
   arities, parameter types, numeric values, and temporal operators. Gold-formula
   equivalence is an evaluation oracle, not a deployment-time input requirement.
2. Construct the deterministic automaton for validated lifted LTLf JSON with
   `ltlf2dfa` and MONA. Do not use an ordered-sequence approximation.
3. Give every DFA edge that strictly reduces graph distance to acceptance one
   transition controller guarded by the current query-local monitor state.
4. Treat a conjunction on one edge as one achievement block whose literals
   must hold in the same observable state.
5. Treat a negative literal such as `not calibrated(C,R)` as a signed context
   obligation, never as `!not_calibrated(C,R)`. A query-local helper may
   establish it only through a certified positive-sibling branch or single PDDL
   action with exact net `MustDelete`, sibling preservation, and no forbidden
   completion `MayAdd`.
6. Build a threat graph from certified completion summaries. An edge
   `G_j -> G_i` means a module for `G_j` may delete `G_i`, so `G_j` must be
   repaired first.
7. For a cyclic threat graph, use only a certified preserving portfolio or a
   supported ranking proof; otherwise reject. Select the preserving portfolio
   per ordered literal occurrence, because two occurrences of one predicate can
   have different protected prefixes. Share query-local aliases only for
   identical certified portfolios, and explain that alternative plan contexts
   are not simultaneous obligations.
8. For mixed Boolean/numeric guards, use complete action-only net Boolean
   effects and constant-integer numeric deltas; index helper selection by the
   full literal atom and leave uncertified literals observation-only. Explain
   strict unit progress, exact non-unit predecessor guards, and the complete
   single-action whole-guard certificate as three bounded strategies rather
   than claiming arbitrary numeric planning. A whole-guard helper must be
   callable from every positive literal it establishes and must carry the
   certificate's complete anchor arguments.
9. For an Until source state, extract common waiting-loop literals as source
   invariants. Require primitive-prefix preservation until the single positive
   progress literal is established. Explain lexicographic predicate/numeric
   precondition preparation, repeatable non-unifying numeric steps, exact
   terminal predecessors, and capture-avoiding composition.
10. Compile the certified order into a balanced binary repair tree. The tree is
   an AgentSpeak indexing structure with trigger fan-out at most two; it does
   not reorder DFA transitions or add planning semantics.
11. Advance the real deterministic finite automaton after the initial valuation
   and every successful primitive PDDL action. Explain that the integrated
   runtime monitor gives the declared formula fragment primitive-step trace
   semantics, while action-strategy synthesis remains incomplete. A transition
   helper returns on source-state exit so an atomic macro may cross several DFA
   edges; the top-level controller always dispatches from the actual monitor
   state.

### 6. Formal Guarantees

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
   initially satisfied or established by their certified repair plans, selected
   modules terminate, and their certified completion effects preserve earlier
   positive and negative obligations, primitive-step monitor advancement leaves
   the source state only through an edge of the constructed DFA whose complete
   cube holds.
4. **Balanced-tree structure:** for `n` signed literals and `e` certified repair
   plans, the generated query-local tree has `2n+e+2` plans, maximum trigger
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

### 7. Experimental Evaluation

The evaluation must match the paper's actual contribution: MOOSE is one
instantiated Evidence Module provider, while the proposed method is the
post-evidence library compiler and temporal query compiler. There is therefore
no single global planner baseline. Present the five questions as separate
descriptive paragraphs rather than numbered or combined RQ labels:

- **Evidence-to-library compilation.** Relative to validated direct adaptation
  of the same normalized evidence, measure how schema-certified lifting and
  internal closure change module coverage and held-out execution.
- **Contributions of candidate generation and selection.** Separate the effects
  of action-only schema closure, recursive/resource/preparation candidates, and
  joint Clingo selection on coverage, size, and runtime.
- **Preservation of temporal guards.** Against a controller with the same real
  DFA, atomic library, monitor, and Jason runtime but no effect-preservation
  reasoning, measure the effect of threat ordering and preserving portfolios on
  VAL- and DFA-valid execution.
- **Controller structure.** Compare flat and balanced repair controllers while
  preserving literal order and branch portfolios; report controller size,
  trigger fan-out, loading cost, and execution time without assigning semantic
  credit to the tree.
- **End-to-end behavior.** Across domains, formula profiles, and evidence seeds,
  report valid traces and reusable-library amortization relative to raw MOOSE
  and per-instance planning references.

The registered atomic comparison is cumulative and paired on one exact
normalized evidence hash:

1. **Evidence Only:** validate provider macros against the PDDL schemas and
   retain them without PDDL closure, internal-module synthesis, or optimization.
2. **Action Closure:** add PDDL producer closure without decomposed
   subgoal candidates.
3. **Maximal Certified:** add progress-, preparation-, and resource-certified
   decomposed candidates, then maximize the jointly compatible branch set under
   all hard certificates.
4. **Full GP2PL:** minimize branch, context, and body cost over exactly the
   same candidate universe and hard constraints as Maximal Certified.

The registered temporal comparison holds the DFA, atomic-library hash, query
binding, and Jason runtime fixed:

For the final combined run, the shared atomic input is not copied from the
long-running evidence batch. It is the seed-0 Full GP2PL output produced by
the atomic stage of the same clean source revision. The evidence batch supplies
only the MOOSE model and readable policy. This prevents libraries compiled at
different repository revisions from entering a paired temporal comparison.

1. **Unprotected DFA:** canonical within-edge serialization, the same
   MONA-derived DFA,
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
feasibility rather than isolating a single subsequent mechanism. Use the 13-case
fail-closed and symbol-invariance matrix to test the individual certificate
families. Likewise, signed-negative and bounded-numeric cases stay in the full
temporal benchmark with explicit support and failure statuses; do not invent
unregistered capability-switch rows. The historical sequence-only controller
may appear only as an evaluation-only weak reference; it must not return as an
operational shortcut.

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
with its underscore encoding are explicit unsupported cases. The exact MOOSE-hosted
LAMA runtime is serialized across processes because its nested Apptainer and shared
work directory are non-reentrant; ENHSP and FOND4LTLf compilation may still use the
declared worker pool. Queue waiting is recorded separately from planner runtime. Published
numbers from different splits or hardware may be cited as prior results but must not be
inserted into paired experiment tables. Plan4Past is a design precedent for
holding the task-level planner fixed while comparing temporal compilations; it
is not directly comparable until any future-LTLf-to-past-LTLf translation has
been proved language-equivalent.

Atomic metrics are producible-predicate coverage, module closure, held-out
Jason+VAL coverage, branch/context/body costs, ASL bytes, and compile time.
Producible-predicate coverage has one paired denominator per seed/domain: all
predicate symbols in positive PDDL action effects. Every method is scored by
the module triggers it actually emits against that same set. Never let Evidence
Only or another reduced variant redefine the denominator through absent
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

The natural-language front end uses one frozen full prompt configuration. The
technical supplement must reproduce a semantically complete paper-facing
template containing the public PDDL catalogue, atom-table contract,
externally-bound parameter contract, allowed operator fragment, normal forms,
schematic examples, exact eight-key JSON output, public user payload, and
model-correctable retry message. State that catalogue/sample placeholders are
deterministic substitutions and that the artifact retains the exact rendered
requests and responses. Prompt compliance is not a semantic oracle: exact
schema/PDDL validation and reachable-product DFA-language equivalence remain
separate gates. Treat this translation protocol as an evaluated input front
end, not as the policy-lifting contribution.

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

## Supplementary and Public Artifact Contract

The standalone source
`latex_code/aamas_method_paper/technical_appendix.tex` is the canonical
technical appendix. It contains the full formal definitions, assumptions,
proofs of every proposition, theory-to-code map, novel-data description,
the frozen natural-language-to-LTLf prompt template, external-data provenance,
final parameter table, development value ranges, hardware/software
specification, distributional statistics, and checklist explanations. The main
paper remains self-contained and includes the essential proof ideas required
to assess the contribution.

Cross-document references in the main paper use explicit textual locations,
such as `Technical Supplement, Sec. 4.2`; they are not bibliography citations.
Keep Sec. 1 for definitions and assumptions, Sec. 2 for complete proofs,
Sec. 4.2 for the frozen prompt, Sec. 4.3 for benchmark provenance, and
Secs. 5.2--5.3 for parameters and reporting. Do not use a vague `the
supplement`, an external web link, or a fragile cross-PDF LaTeX reference. The
main paper must remain self-contained when the supplement is not consulted.

The versioned public evidence is split into:

- `paper_artifacts/temporal_goal_benchmark/v1` for the novel controlled-language
  and parametric LTLf dataset, including its dataset-level README, CC BY 4.0
  notice, citation metadata, portable source archives, and integrity verifier;
- `paper_artifacts/temporal_semantic_conformance/v1` for operator-level semantic
  checks; and
- `paper_artifacts/gp2pl_evaluation/v1` for exact atomic libraries, compact
  execution records, certificate challenges, distributions, and hashes.

GP2PL code uses Apache-2.0 and original GP2PL data uses CC BY 4.0. External PDDL
and MOOSE materials retain upstream rights. Three public benchmark repositories
and MOOSE do not expose an explicit license; they must be fetched at pinned
commits and cannot be represented as GP2PL-licensed source. Checklist code
availability concerns the complete GP2PL-authored source, which is included and
Apache-2.0 licensed. Third-party dependencies are separately cited, pinned, and
retrieved under upstream terms. All novel GP2PL data is publicly released under
CC BY 4.0, including the construction audit that was sealed from the translation
model during inference, so no experimental dataset remains non-public.

AAAI review is double blind and forbids pointers to identifiable web material.
The submission therefore uses an anonymized code-and-data archive and keeps the
named repository link disabled. The camera-ready conditional enables
`https://github.com/daidaibunny/gp2pl`. Never expose that URL in the anonymous
PDF or supplementary review PDF.

Checklist answers may change to `yes` only when the corresponding evidence is
present in the paper, appendix, or submitted archive. The current statistical
answer is `yes` because the paper makes no inferential performance-difference
claim from descriptive fixed-release results. The registered paired five-seed
comparison remains a mandatory gate before adding any future improvement or
significance claim; a repository link or additional prose cannot substitute for
that experiment.

## Final Visual Program

The main paper targets exactly two figures, one algorithm, and no more than
four result tables after the registered matrices are complete. The current
seven-page draft keeps one compact temporal-profile table in the main paper and
moves the fixed per-domain library table, repeated oracle columns, certificate
challenges, and complete distributions to Technical Supplement, Sec.~5.3.
Registered comparison
tables must replace provisional content rather than accumulate beyond the
seven-page technical limit. This follows the visual argument used by closely
related planning papers: MOOSE uses one compact method overview and reserves its
main empirical graphic for cumulative coverage over absolute time, while related
generalized-planning papers place exact per-domain values in dense tables. Our
main Figure 1 therefore explains the complete representation bridge, and main
Figure 2 combines broad paired coverage, an executable coverage-size ablation,
and all-query temporal scaling. The worked policy-lifting and DFA-controller
diagrams remain Supplementary Figures S1 and S2, where they can support the
formal method without consuming two additional main-paper floats.

### Figure Production Handoff Contract

Figure 1 and Supplementary Figures S1--S2 are conceptual method diagrams. Their
labels and examples below come from the implemented architecture and PDDL
schemas, not from estimated experimental measurements. Figure 2 is empirical:
its axes may be laid out in
advance, but every data mark must be generated from pinned JSON artifacts. No
colleague or paper-writing agent may infer missing values from prose, terminal
logs, an earlier run, or another method.

Use one normalized coordinate system for all object specifications below:
`x=0,y=0` is the top-left corner; `x`, `y`, `w`, and `h` are percentages of the
complete slide. Snap objects to the specified coordinates within 0.5 percentage
points. Captions are LaTeX text below the imported graphic and must not be drawn
inside the PowerPoint slide.

Canvas, PowerPoint, Python, and export settings:

- Main Figure 1 uses a 13.333 by 5.000 inch PowerPoint export canvas.
  Supplementary Figures S1 and S2 use a 13.333 by 5.333 inch PowerPoint canvas.
  Main Figure 2 is generated by Matplotlib at exactly 7.0 by 3.0 inches, matching
  the AAAI two-column text width while limiting the plot body to one third of
  the nine-inch text height. Keep a white opaque background.
- Use Arial 17 pt for normal labels, Arial Bold 20 pt for panel headings, and
  Courier New 15 pt for PDDL, AgentSpeak, formulas encoded as text, and artifact
  field names. These become approximately 8--10 pt after scaling to AAAI
  `\textwidth`.
- Use square or 0.06-inch-corner rectangles. Do not use shadows, gradients,
  three-dimensional effects, icons, decorative illustrations, or screenshots.
- Figure 1 and Supplementary Figures S1--S2 share one editable source deck named
  `latex_code/aamas_method_paper/figures/aaai_method_figures_source.pptx`, with
  exactly one figure per slide. Main Figure 2 is produced by the checked-in
  Matplotlib script, not by PowerPoint.
- Main vector files are `fig1_architecture.pdf` and `fig2_evaluation.pdf`.
  Supplementary vector files are `figS1_policy_lifting.pdf` and
  `figS2_dfa_controller.pdf`, all under
  `latex_code/aamas_method_paper/figures/` when delivered.
- Embed fonts in the PDF, crop to the slide boundary, and verify all text at
  `\includegraphics[width=\textwidth]`. Do not rasterize any figure.
- Main Figure 2 uses regular-weight DejaVu Sans throughout: 6.8-pt panel
  headings, 5.8-pt axis labels, and 5.1-pt tick and domain labels. Do not use
  bold text inside the data figure. Hide the top and right spines, retain only
  light-gray major grid lines, and preserve redundant color plus marker or line
  encodings for grayscale printing.

Use this exact color palette. Text is always `#1A1A1A` unless the fill is the
dark Clingo box, in which case text is white.

| Semantic role | Fill | Border |
| --- | --- | --- |
| Input or prior state | `#F2F2F2` | `#4D4D4D` |
| External MOOSE evidence | `#FFF1CC` | `#B26A00` |
| Our compiler operation | `#DDEBF7` | `#0072B2` |
| Certified selected artifact | `#DDF2E9` | `#009E73` |
| Runtime monitor or temporal observation | `#EEE4F2` | `#CC79A7` |
| Fail-closed rejection | `#FBE3D5` | `#D55E00` |
| Feasible but unselected candidate | `#FFFFFF` | `#9E9E9E` |

Connector semantics are global and must not change between figures:

- A 2.25 pt solid `#333333` line with a filled triangular arrowhead means
  artifact, control, or action flow from source to target.
- A 2.25 pt solid `#009E73` line with a filled triangular arrowhead is the
  success-only form of the solid flow: use it only after certification or
  acceptance has succeeded, never for an unproved candidate or replay path.
- A 1.75 pt dashed `#0072B2` line with an open arrowhead means a compile-time
  dependency, subgoal call, effect-summary use, or closure relation. Its label
  must state which of those meanings applies.
- A 1.75 pt dotted `#D55E00` line with a filled arrowhead means fail-closed
  rejection. It always ends at a red rejection box.
- A 1.75 pt dashed `#CC79A7` line with an open arrowhead means that a runtime
  state valuation is observed by the deterministic finite automaton monitor.
- A 1.0 pt solid `#B7B7B7` line without an arrowhead is only a panel boundary,
  container boundary, table-like divider, or plot grid line.
- An orange `#D55E00` solid directed edge labelled `may delete` is reserved for
  a threat-graph ordering relation. It is not a rejection path.

Every connector has exactly one semantic role. Avoid crossing connectors. When
an elbow is necessary, use horizontal and vertical segments with a 0.08-inch
corner radius. An outer container means containment; arrows must not be used to
imply containment.

Use this exact back-to-front layer order in PowerPoint's Selection Pane:

1. opaque white slide background;
2. lane and panel containers;
3. panel dividers and plot grid lines;
4. semantic connectors and arrow labels;
5. operation, artifact, state, and code boxes;
6. certificate badges, state circles, checks, and rejection marks;
7. headings, annotations, and abbreviated-name notes.

Name every shape with its object identifier below, for example `F1-D3` or
`F3-B2`. Name a connector `<source>__to__<target>`, followed by its semantic
role when two connectors share endpoints, for example
`F3-B2__to__F3-B1__may_delete`. Group only a box with its own text, or a state
circle with its own state label. Do not group an arrow with either endpoint;
this preserves editable routing when a label changes.

### Figure 1: End-to-End Architecture

Use a full-width `figure*` near the end of the Introduction. Replace the current
text box; do not retain both. The figure contains three horizontal lane
containers and one shared maintained-library container.

Object placement and exact text:

- `F1-D0`: `x=1,y=3,w=78,h=27`. White outer lane with gray border. No title in
  the border.
- `F1-DL`: `x=2,y=6,w=9,h=21`. Gray title strip containing three centered lines:
  `Reusable`, `domain`, `compilation`.
- `F1-D1`: `x=13,y=9,w=12,h=14`. Gray box: `PDDL domain` on line 1 and
  `+ complete train split` on line 2.
- `F1-D2`: `x=28,y=9,w=12,h=14`. Amber box: `MOOSE readable` on line 1 and
  `singleton policy evidence` on line 2.
- `F1-D3`: `x=43,y=6,w=7,h=20`. Blue box: `Normalize` and `evidence`.
- `F1-D4`: `x=52,y=6,w=8,h=20`. Blue box: `Producible closure` and
  `+ candidates`.
- `F1-D5`: `x=62,y=6,w=8,h=20`. Blue box: `Certify` and `branches`.
- `F1-D6`: `x=72,y=6,w=7,h=20`. Blue box: `Joint Clingo` and `selection`.
- `F1-T0`: `x=1,y=34,w=78,h=29`. White outer lane with gray border.
- `F1-TL`: `x=2,y=38,w=9,h=21`. Gray title strip containing `Query-specific`,
  `temporal`, `compilation`.
- `F1-T1`: `x=13,y=41,w=12,h=14`. Gray box: `Typed, bound` and `LTLf JSON`.
- `F1-T2`: `x=28,y=38,w=9,h=20`. Blue box: `ltlf2dfa` and `+ MONA`.
- `F1-T3`: `x=39,y=38,w=9,h=20`. Blue box: `Signed DFA` and `guards`.
- `F1-T4`: `x=50,y=38,w=10,h=20`. Blue box: `Threat +` on line 1,
  `preservation` on line 2, and `certificate` on line 3.
- `F1-T5`: `x=63,y=38,w=11,h=20`. Blue box: `Balanced repair` and `tree`.
- `F1-L0`: `x=82,y=5,w=15,h=58`. Green outer container. Header at the top:
  `One maintained domain library`.
- `F1-L1`: `x=83.5,y=18,w=12,h=14`. White/green inner box: `Lifted atomic`
  and `modules`.
- `F1-L2`: `x=83.5,y=41,w=12,h=14`. White/green inner box:
  `Appended query-local` and `controllers`.
- Draw a gray horizontal containment divider from `x=83.5,y=36` to
  `x=95.5,y=36`. Do not draw an arrow between `F1-L1` and `F1-L2`.
- `F1-E0`: `x=1,y=70,w=96,h=27`. White outer execution lane.
- `F1-EL`: `x=2,y=75,w=9,h=17`. Gray title strip: `Execution` and
  `validation`.
- `F1-R`: `x=34,y=78,w=16,h=12`. Red box: `Reject` on line 1 and
  `structured diagnostic` on line 2.
- `F1-E1`: `x=56,y=78,w=10,h=12`. Purple box: `Jason`.
- `F1-E2`: `x=69,y=78,w=11,h=12`. Green box: `Committed` on line 1 and
  `PDDL trace` on line 2.
- `F1-E3`: `x=83,y=72,w=12,h=6`. Gray box: `Neutral-goal VAL`.
- `F1-E4`: `x=83,y=81,w=12,h=6`. Purple box: `Gold-DFA acceptance`.
- `F1-E5`: `x=83,y=90,w=12,h=6`. Purple box:
  `Predicted-DFA acceptance`.
- At `x=95.7,y=72,w=1.3,h=24`, draw a right-facing green brace joining
  `F1-E3`, `F1-E4`, and `F1-E5`. Place a green check centred at `(98.2,84)`.
  Place `end-to-end` and `success` on two centred lines at
  `x=96.9,y=91,w=3,h=5` in 11 pt Arial. Nothing may extend beyond `x=100`.

Draw these directed edges in this order:

1. Solid flow: `F1-D1 -> F1-D2 -> F1-D3 -> F1-D4 -> F1-D5 -> F1-D6 -> F1-L1`.
2. Solid flow: `F1-T1 -> F1-T2 -> F1-T3 -> F1-T4 -> F1-T5 -> F1-L2`.
   Label only the last edge `append only; no relearning`.
3. Dotted red rejection: `F1-D5 -> F1-R`, `F1-D6 -> F1-R`, and
   `F1-T4 -> F1-R`. From `F1-D5`, leave through the bottom, move in the lane
   gap at `y=32` to the empty vertical gutter at `x=61`, then descend to
   `y=66`. From `F1-D6`, leave through the right edge into the gutter at
   `x=80.0`, then descend to `y=66`. From `F1-T4`, descend directly to `y=66`.
   Route the three paths independently along the empty `y=66` gutter to
   `x=41.2`, `x=42.0`, and `x=42.8`, then down into the top of `F1-R`. Keep
   0.8 percentage points between paths; do not merge them.
4. Solid green-certified flow from the bottom center of `F1-L0` vertically to
   `y=68`, left to `x=61`, then down into `F1-E1`. Label the horizontal segment
   `execute combined library`.
5. Solid flow `F1-E1 -> F1-E2`. Fan three solid arrows from `F1-E2` to
   `F1-E3`, `F1-E4`, and `F1-E5`. The two DFA arrows must share the same source
   trace and must not look like separate executions.

Do not place `Layer A/B/C`, `tg_state`, a second domain library, or a language
model inside this figure. The external Input component has already produced the
validated LTLf JSON. Draft caption:

> **Figure 1: End-to-end certified compilation and validation.** The reusable
> domain stage compiles singleton-goal evidence and PDDL schemas once into one
> maintained BDI plan library, realized here in AgentSpeak(L). Each temporal
> query contributes only query-local controllers derived from MONA-derived DFA
> transitions. Jason actions are validated independently by VAL and both
> finite-trace automata; uncertified compilation choices are rejected.

### Supplementary Figure S1: From Policy Evidence to a Lifted Atomic Module

Place this full-width figure in the technical supplement beside the complete
candidate-language definition. Use four equal-width panels. This is a method
example, not an experimental result. It uses the repository's Blocks PDDL
vocabulary. PDDL names retain hyphens; rendered AgentSpeak names use underscores.

Panel containers and headings:

- `(a)` is `x=1,y=2,w=23,h=96`, heading `Evidence`.
- `(b)` is `x=26,y=2,w=23,h=96`, heading `PDDL closure`.
- `(c)` is `x=51,y=2,w=24,h=96`, heading `Certification + selection`.
- `(d)` is `x=77,y=2,w=22,h=96`, heading `Executable library`.
- Each panel is white with a gray 1 pt border. Put the bold panel letter at
  `x+1.5,y=4` and the heading centered at `y=5`.

Panel (a) objects:

- `F2-A1`: `x=4,y=17,w=17,h=20`. Gray box with exact text:
  `Training singleton goals`, `on(b1,b2)`, and `on(b3,b1)`.
- `F2-A2`: `x=3,y=49,w=19,h=31`. Amber box headed
  `Normalized MOOSE evidence (schematic)`. Under the heading use Courier New:
  `goal     on(X,Y)`, `context  holding(X), clear(Y)`, and
  `macro    stack(X,Y)`.
- Draw `F2-A1 -> F2-A2` as a solid flow arrow labelled
  `MOOSE goal regression`. Do not depict the training object names inside
  panel (d).

Panel (b) objects use Courier New 14 pt inside blue boxes:

- `F2-B1`: `x=28,y=16,w=19,h=27` with the exact schema excerpt:
  `stack(X,Y)`, `pre: holding(X), clear(Y)`,
  `add: on(X,Y), clear(X), arm-empty`, and
  `del: holding(X), clear(Y)`.
- `F2-B2`: `x=28,y=48,w=19,h=29` with:
  `unstack(X,Y)`, `pre: on(X,Y), clear(X), arm-empty`,
  `add: holding(X), clear(Y)`, and
  `del: on(X,Y), clear(X), arm-empty`.
- `F2-B3`: `x=28,y=82,w=19,h=12`. Green box headed
  `Target-relevant producible closure` with
  `on/2, clear/1, holding/1, arm_empty/0`.
- Draw dashed blue arrows from `F2-B1` and `F2-B2` to `F2-B3`, both labelled
  `add-effect / precondition closure`. Place one small gray note under `F2-B3`:
  `Static predicates remain context only.`

Panel (c) objects:

- Draw a dashed blue container `F2-C0` at `x=52.5,y=15,w=15,h=45`, labelled
  `Certified candidate space` in its top-left corner.
- Inside it stack four candidate cards at `y=22,31,40,49`, each `w=13,h=7`.
  Use amber for `E: validated stack macro`; blue for
  `S1: direct stack producer`; blue for
  `S2: !clear(Y); !on(X,Y)`; and white/gray for
  `S3: longer feasible macro`.
- At `x=68.5,y=17,w=5,h=42`, draw six small certificate badges:
  `Bind`, `Execute`, `Achieve`, `Closure`, `Progress`, and `Resource`.
  A green check means required and proved; gray `n/a` means the candidate does
  not use that feature. Never mark an unproved obligation as `n/a`.
- Draw dashed blue arrows from each candidate card to the badge rail labelled
  `machine-checkable contract`.
- `F2-C1`: `x=57,y=66,w=13,h=13`. Dark blue hexagon with white text:
  `Clingo` and `lexicographic select`.
- Draw solid arrows from every certificate-passing candidate to `F2-C1`.
  Draw no arrow from a certificate-rejected candidate.
- `F2-C2`: `x=54,y=84,w=18,h=8`. Green box:
  `Minimum-cost feasible subset`.
- Draw `F2-C1 -> F2-C2` as a solid green arrow. Put a gray 13 pt note below:
  `Optimal only inside this generated certified space.`

Panel (d) objects:

- `F2-D0`: `x=78.5,y=14,w=19,h=76`. Green outer container headed
  `One domain library`.
- `F2-D1`: `x=80,y=23,w=16,h=49`. White code box containing exactly:

```asl
+!on(X,Y) : on(X,Y) <- true.

+!on(X,Y) : clear(Y) & holding(X) <-
    stack(X,Y).

+!on(X,Y) : not clear(Y) <-
    !clear(Y);
    !on(X,Y).
```

- `F2-D2`: `x=81,y=78,w=14,h=8`. Small green box:
  `+!clear(...) module`.
- Draw a dashed blue subgoal-call arrow from the `!clear(Y)` line in `F2-D1`
  to `F2-D2`. Label it `internal closure`.
- Draw a solid green arrow from `F2-C2` to the left border of `F2-D0`.
- Put a gray footer inside `F2-D0`: `No training objects; no synthetic goals.`

The code is an illustrative certificate-valid selection from the generated
candidate language, not a verbatim claim that every seed selects these exact
three branches. It demonstrates the added internal module and recursive
structure. Draft caption:

> **Supplementary Figure S1: Certified lifting of singleton-goal policy
> evidence.** Provider
> macros and PDDL-derived closure candidates enter the same certified candidate
> space. The selected BDI module, shown in its AgentSpeak(L) realization, is
> lifted, internally closed, and may introduce producible subsidiary goals
> absent from the evidence; compactness is optimal only within the generated
> candidate language.

### Supplementary Figure S2: DFA Transition Compilation and Runtime Monitoring

Place this full-width figure in the technical supplement beside the formal
transition-compilation rules. Use four panels. The decoded MONA example is
`phi = F(on(A,B) & on(B,C) & not holding(A))`. Define the complete progress
guard once as `G`; all subsequent labels refer to that same guard. This is a
semantic method example, not one measured benchmark trace.

Panel containers:

- `(a)` is `x=1,y=2,w=23,h=96`, heading `MONA-derived DFA transition`.
- `(b)` is `x=26,y=2,w=21,h=96`, heading `Signed obligations`.
- `(c)` is `x=49,y=2,w=27,h=96`, heading `Certified repair tree`.
- `(d)` is `x=78,y=2,w=21,h=96`, heading `Primitive-step monitor`.

Panel (a):

- `F3-A1`: `x=3,y=16,w=19,h=17`. Gray formula box with Courier New:
  `G = on(A,B) & on(B,C)` on line 1, `    & not holding(A)` on line 2,
  and `phi = F(G)` on line 3.
- Draw initial state `q0` as a blue single circle centred at `(7,61)`, diameter
  5 percent. Draw accepting state `q1` as a green double circle centred at
  `(19,61)`, diameter 5 percent. A short incoming arrow from the left points to
  `q0`.
- Draw a solid arrow `q0 -> q1` labelled `G`. Draw a loop on `q0` labelled
  `not G` and a loop on `q1` labelled `true`.
- Put `decoded real ltlf2dfa/MONA DFA` in gray 13 pt text at `x=4,y=88`.
  Do not show a hand-authored ordered sequence or a `tg_state` belief.

Panel (b):

- `F3-B0`: `x=28,y=15,w=17,h=10`. Blue box: `Conditional completion` and
  `effect summaries`.
- `F3-B1`: `x=28,y=34,w=17,h=10`. Green box:
  `G1 = on(A,B)  [positive]`.
- `F3-B2`: `x=28,y=55,w=17,h=10`. Green box:
  `G2 = on(B,C)  [positive]`.
- `F3-B3`: `x=28,y=76,w=17,h=12`. Purple box:
  `N1 = not holding(A)` and `observe or exact deleter`.
- Draw dashed blue effect-summary arrows `F3-B0 -> F3-B1`,
  `F3-B0 -> F3-B2`, and `F3-B0 -> F3-B3`.
- Draw one orange directed threat edge from `F3-B2` to `F3-B1`, labelled
  `may delete`. Place a note beside it: `therefore G2 before G1`.
- Do not draw `!not_holding(A)`. The negative card is an absence obligation,
  not an atomic negative achievement goal.

Panel (c):

- At `x=51,y=14,w=23,h=10`, draw a three-cell horizontal order strip:
  `1  on(B,C)`, `2  on(A,B)`, and `3  not holding(A)`.
- Put the heading `Sequential dispatch; not alternatives` directly below the
  strip in gray 13 pt text.
- At `x=52,y=31,w=21,h=7`, draw the wrapper body as
  `trans_1 -> repair_1_3 -> trans_1_done`.
- Tree node `repair_1_3` is centred at `(62,46)`. Its left child
  `repair_1_2` is centred at `(57,61)`; its right child `repair_3_3` is centred
  at `(69,61)`.
- `repair_1_2` has children `repair_1_1` centred at `(53,77)` and
  `repair_2_2` centred at `(61,77)`.
- Use blue rounded rectangles, `w=8,h=7`, for the two internal nodes
  `repair_1_3` and `repair_1_2`. Use green leaf boxes, `w=8,h=10`, for
  `repair_1_1` with subtitle `observe or !on(B,C)` and `repair_2_2` with
  subtitle `observe or !on(A,B)`. Use a purple leaf box, `w=8,h=10`, for
  `repair_3_3` with subtitle `observe not holding(A)`.
- Draw solid control arrows from `repair_1_3` to `repair_1_2` and then to
  `repair_3_3`. Label them `1` and `then 2`. Draw solid control arrows from
  `repair_1_2` to `repair_1_1` and then to `repair_2_2`, also labelled `1` and
  `then 2`. These numbers are sequence positions, not branch alternatives.
- Draw `trans_1_done` as a purple box at `x=65,y=88,w=9,h=7`. A solid dark
  control arrow returns to `repair_1_3`, labelled `monitor still q0: replay`.
  A solid green success arrow leaves panel (c), labelled
  `monitor left q0: return to dispatcher`.
- In a 12 pt gray inset at `x=50,y=95,w=14,h=3`, state:
  `Singleton guard -> one leaf -> same primitive atomic call.` Keep it left of
  `trans_1_done` and do not route the replay arrow through it.

Panel (d):

- Draw a horizontal state timeline from `x=80,y=49` to `x=97,y=49`.
  State circles are `s0`, `s1`, `...`, and `sk`; action arrows between them are
  `a1`, `a2`, `...`, and `ak`. A footer defines
  `ai = one successful primitive PDDL action`.
- Above `s0`, `s1`, and `...`, place purple monitor badges `q0`. Above `sk`,
  place a green double badge `q1 accepting`.
- Draw purple dashed observation arrows from every state circle to its monitor
  badge. Label the first arrow `initial valuation` and the remaining group
  `after every primitive action`.
- Draw one purple dashed observation arrow from the monitor-badge group to the
  right edge of `trans_1_done` in panel (c), labelled `current DFA state guard`.
  Route it through the empty lower gutter so it does not cross the repair tree.
- Draw a solid green arrow from the final `q1 accepting` badge to
  `top-level DFA dispatch` at `x=83,y=76,w=13,h=10`.
- Under the timeline, draw a gray bracket from `s0` through `sk` labelled
  `one committed state trace`. Do not insert a noop before `s0`, and do not
  imply that failed Jason prefixes are committed plans.

All helper names in panel (c) omit the common prefix
`g_query_17_trans_1_` only to remain legible; print this note in gray 12 pt at
`x=65,y=95,w=10,h=3`, to the right of the singleton inset. Draft caption:

> **Supplementary Figure S2: Preservation-safe compilation of one DFA progress
> transition.**
> Conditional module summaries induce a threat order over signed guard
> obligations. A balanced BDI repair tree, rendered here in AgentSpeak(L),
> realizes that fixed order with trigger fan-out at most two, while the DFA
> monitor observes every primitive action. Uncertified cyclic threats or
> negative-literal repairs are rejected rather than serialized heuristically.

### Figure 2: Main Empirical Evidence

Use a full-width `figure*` in Section 7 after the evaluation protocol and metric
definitions, before any result table. This figure is generated from artifacts,
not manually drawn. The checked-in plotting script places every point, interval,
annotation, and curve; PowerPoint must not be used to reconstruct the data marks.

The required generator is `scripts/generate_aaai_figures.py`. It must accept
one `--paired-results` artifact and `--output-file`, apply the gates below before
reading plot values, and exit nonzero without creating a new PDF when a gate
fails. It writes a machine-readable diagnostic and provenance sidecar. The
generator is implemented and tested; the release figure remains unavailable
until the complete registered matrix exists.

Data-release gate:

- All panels read exactly one
  `artifacts/paired_compiler_experiments/<RUN_ID>/paired_results.json`.
  Cross-run stitching with a separate five-seed summary is forbidden.
- Require `success`, `paper_matrix_complete`, `infrastructure_complete`,
  `paired_inputs_verified`, `atomic_pairing.paired`, and
  `temporal_pairing.paired` all true; require a clean pinned source revision,
  seeds 0--4, all 16 domains in every atomic run, all four atomic variants per
  seed, all four temporal variants over the same sample identifiers, six
  execution workers, a 1,800-second limit, and a 64-MiB Jason Java stack.
- If any gate fails, do not render a partial panel and do not fall back to the
  pinned seed-0 temporal run. Persist a machine-readable plotting diagnostic.

Use an asymmetric layout: panel (a) occupies the full left half so 16 domain
labels remain readable; panels (b) and (c) occupy the upper-right and
lower-right quadrants.

- `(a)` spans the full left column and is headed `Paired atomic coverage`.
- `(b)` occupies the upper-right and is headed
  `Atomic coverage-size tradeoff`.
- `(c)` occupies the lower-right and is headed
  `Temporal cumulative coverage`.
- Use Matplotlib's bundled DejaVu Sans font, embedded as TrueType in the PDF.
  Plot backgrounds are white; all plot text uses regular weight; top and right
  spines are omitted; and only light gray major grid lines remain. Use the same
  colorblind-safe palette and redundant marker or line-style encodings as the
  conceptual figure. Stars are not used: in empirical figures they commonly
  imply significance or a privileged best point, neither of which is encoded
  by this experiment.

Panel (a) specification:

- Y-axis order is fixed as: `barman`, `ferry`, `gripper`, `logistics`,
  `miconic`, `rovers`, `satellite`, `transport`, then `numeric-ferry`,
  `numeric-miconic`, `numeric-minecraft`, `numeric-transport`, then
  `blocksworld-clear`, `blocksworld-on`, `blocksworld-tower`, `depots`.
  Draw thin group separators after `transport` and `numeric-transport`.
- X-axis is `Jason + VAL coverage (%)`, fixed from 0 to 100 with ticks at
  0, 25, 50, 75, and 100. Draw a gray dashed reference line at 100.
- Compare only two endpoints under byte-identical per-seed evidence:
  `Evidence Only` and `Full GP2PL`. Evidence Only validates provider macros
  against the PDDL schemas without PDDL-derived closure; Full GP2PL adds closure,
  certificates, and solver-backed selection. This is a compiler contribution
  comparison, not a claim that GP2PL is a faster task planner than MOOSE.
- For every method and domain, plot all five seed coverages as small translucent
  points and plot the mean plus or minus sample standard deviation as a larger
  marker with a horizontal capped interval. Evidence Only is a gray open
  circle; Full GP2PL is a filled blue diamond. A thin gray segment joins the two
  method means for the same domain, making paired gains or losses visible.
- Coverage is `100 * valid_trace_count / test_count` from that domain's original
  held-out PDDL achievement tests. A valid trace requires Jason completion and
  VAL acceptance. Do not pool domains before plotting and do not substitute
  producible-predicate closure for executable held-out coverage.

Panel (b) specification:

- Every plotted point must represent an executable compiler output. Plot all
  four paired atomic variants: `Evidence Only`, `Action Closure`,
  `Maximal Certified`, and `Full GP2PL`. Do not plot the unselected candidate
  pool as though it were an executable baseline.
- For each variant and seed, the x coordinate is the total number of emitted
  AgentSpeak plan branches across the 16 libraries, and the y coordinate is
  `100 * total VAL-valid held-out cases / total held-out cases`. The x-axis uses
  a base-10 logarithmic scale; the y-axis is linear from 0 to 100 percent.
- Plot five translucent seed points per variant and one larger mean point with
  horizontal and vertical sample-standard-deviation bars. Use gray circle,
  amber square, green triangle, and blue diamond in the order above; the
  Evidence Only circle remains open in both atomic panels. Do not draw a Pareto
  frontier or claim dominance unless the measured points establish it.
- Candidate count and percentage branch reduction remain exact table or
  supplementary metrics. This panel answers the stronger question: what
  executable held-out coverage is obtained for the final emitted library size?

Panel (c) specification:

- Use all records in `temporal_runs[*].results` for each of the four hash-paired
  temporal variants. A query enters a curve at its recorded `duration_seconds`
  only when Jason reports success and the execution-validation record confirms
  PDDL replay, attempted and successful VAL validation, gold-DFA acceptance,
  and predicted-DFA acceptance. Failures and timeouts remain in the denominator
  and therefore lower the final curve endpoint.
- `duration_seconds` starts before query-controller compilation and ends after
  execution validation. It is therefore end-to-end query processing time, not
  Jason-only search time. X-axis is `End-to-end query time (s)`, logarithmic
  from 0.1 through the 1,800-second deadline, with only a narrow right margin
  beyond the deadline so its vertical line remains visible. Y-axis is
  `Fraction of all queries solved (%)`, linear from 0 to 100. Draw a vertical
  gray timeout line at 1,800 seconds.
- Draw right-continuous step curves with 1.05 pt strokes:
  `Unprotected DFA` is gray `#7F7F7F`, dotted;
  `Certified Flat` is amber `#E69F00`, dashed;
  `Certified Balanced` is blue `#0072B2`, solid; and
  `Completion Monitor` is purple `#CC79A7`, dash-dot.
- Add one small, method-specific circle, square, diamond, or triangle at each
  common 1, 10, 100, and 1,800 second checkpoint. These marks report the value
  of the same right-continuous curve at shared times; they are not additional
  samples, significance marks, or smoothed estimates.
- Place the legend inside the lower-right only if it covers no curve; otherwise
  place it in one horizontal row above the panel. Do not smooth or interpolate
  the step curves.
- This is a cumulative solved-fraction plot over all queries, not an empirical
  cumulative distribution conditioned on successful queries. The endpoint is
  therefore both a processing-time and coverage statement. This follows the
  absolute-time cumulative-coverage convention used by MOOSE while preserving
  GP2PL's stricter end-to-end success oracle.

Draft caption:

> Figure 2: Paired atomic and temporal evaluation. Panel (a) compares the
> Evidence Only with Full GP2PL on every held-out domain over five
> independently seeded, single-worker MOOSE evidence runs; points are seeds and
> larger markers report mean $\pm$ sample standard deviation. Panel (b) places
> all four executable atomic compiler variants by emitted branches and VAL-valid
> held-out coverage under identical per-seed evidence. Panel (c) reports the
> fraction of all hash-paired temporal queries solved within each end-to-end
> time; failed and timed-out queries remain in the denominator and the vertical
> line marks the 1,800-second limit.

Before delivery, verify Figure 2 totals against the corresponding generated
LaTeX tables. The figure and table must name the same run IDs and input hashes.
No one may copy values from a PDF table back into the plot source.

### Figure Delivery and LaTeX Insertion Contract

The colleague delivers the editable method deck, main Figure 1, and
Supplementary Figures S1--S2. The plotting script delivers main Figure 2. The
release bundle also contains
`latex_code/aamas_method_paper/figures/aaai_figure_manifest.json`, with keys
`schema_version`, `source_revision`, `exported_at`, `assets`, and `fonts`.
Each `assets` entry records `file`, `width_inches`, `height_inches`, and
`data_source`. Figure 1 and Supplementary Figures S1--S2 use
`data_source: "not_empirical"`; Figure 2 records the single paired-result file,
its SHA-256 hash, and the plotting-script revision. The
`fonts` object maps each requested font to the embedded PDF font actually used;
any substitution is a release blocker. The plotting script, not the colleague,
owns Figure 2's numeric data.

Use these exact LaTeX placements and labels after the assets exist:

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{figures/fig1_architecture.pdf}
  \caption{<approved Figure 1 caption from this outline>}
  \label{fig:architecture}
\end{figure*}

\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{figures/fig2_evaluation.pdf}
  \caption{<approved Figure 2 caption from this outline>}
  \label{fig:evaluation-summary}
\end{figure*}
```

The technical supplement inserts `figS1_policy_lifting.pdf` and
`figS2_dfa_controller.pdf` with the approved supplementary captions above. They
must not be renumbered as additional main-paper figures.

The angle-bracket caption placeholders are instructions and must be replaced by
the approved caption text before compilation. Never duplicate a caption inside
the graphic. Inspect every exported PDF at 100 and 200 percent zoom, print one
grayscale proof, and verify that line style and labels preserve every semantic
distinction without color. Run `pdffonts` and require all fonts to report
embedded. The final manuscript must cite each figure before it appears.

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

Use short method names (Evidence Only, Action Closure, Maximal Certified, and
Full GP2PL) and report paired results for every fixed evidence seed:

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
external table in Technical Supplement, Sec.~5.3, and report only the paired
headline comparison in the Evaluation text.

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
the exact seed-specific model-batch manifests and canonical hashes of every
per-domain model/readable-policy pair consumed by the paired compiler runs, one
clean source commit for every derived result summary, the registered resource
protocol, pinned external binaries, and exactly 13 unique successful challenge
nodes. Report a failed contract as an infrastructure failure, never as a method
score.

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
as the fixed seed-0 input table for the temporal evaluation. It must not be
described as the five-seed result; move its detailed per-domain snapshot to
supplementary material when Table 3 is inserted.

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
  one pinned paired-result JSON artifact. PowerPoint is acceptable for main
  Figure 1 and Supplementary Figures S1--S2, but not for manually placing result
  points in main Figure 2.

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
   reports only the fixed seed-0 library structure consumed by the temporal
   run;
2. completed registered atomic and temporal ablation runs, plus the separately
   labelled external references, with result tables inserted only from their
   machine-readable summaries;
3. a rejection/failure analysis tied to stated assumptions;
4. full or supplementary proofs for claims stronger than the current proof
   sketches; and
5. final camera-ready author and artifact metadata. The current compiled draft
   places all technical content, including the Conclusion, within pages 1--7;
   references begin on page 8 and the checklist follows on pages 9--10.

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
| Certified BDI plan-library compilation | 1.8 |
| DFA-guided TEG composition | 1.0 |
| Formal guarantees | 0.5 |
| Experimental evaluation | 1.6 |
| Related work, limitations, conclusion | 0.5 |

When results are inserted, compress detailed certificate prose into tables and
move long proofs to supplementary material before removing definitions or
failure boundaries. The paper source, this outline, and both normative research
design documents must never disagree about architecture, terminology, or
supported capabilities.
