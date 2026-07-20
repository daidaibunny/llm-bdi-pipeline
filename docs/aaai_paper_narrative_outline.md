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
> transition carries the required action-schema-derived certificates.

A certificate is a compile-time, machine-checkable obligation. For example, a
binding certificate proves that every variable in `stack(X,Y)` is supplied by
the trigger or positive context; a completion-effect certificate proves which
PDDL literals may be added or deleted when `!on(X,Y)` successfully returns.
The compiler accepts a candidate only when its obligations are proved and
otherwise returns a structured rejection.

## Canonical Formal Notation

The manuscript uses one notation for each method object. Do not introduce a
second tuple or reuse one symbol for a different semantic role.

- `D = <P,F,A,T>` is the typed planning domain. A problem instance is
  `I=<D,O_I,s_I^0,G_I>`, where `O_I` is its finite typed object set;
  `I_train` is the finite training instance set. `E_raw` is a raw
  generalized-planning provider artifact; `E_0` is its provider-normalized
  program; and `E = CanonicalLift_D(E_0)` is the typed, alpha-normalized
  singleton-goal evidence program. The lifting step preserves repeated-variable
  sharing and PDDL domain constants; it does not claim the provider's upstream
  inference from ground plans. This avoids reusing `A`, already reserved for
  the PDDL action-schema set.
- `T_D(E) = goalPred(E) union prod(D)` is the Boolean producible target universe;
  `T_D^Z(E)` is the admitted singleton integer-equality target set.
- `G` is the domain-independent candidate-construction grammar. Its typed
  instantiation `Inst_D(G,T_D(E),T_D^Z(E)) = C_D(E)` is the finite
  action-schema-derived branch set. `C_E` is the validated evidence-branch set,
  `C_{D,E} = C_E union C_D(E)` is the generated candidate set, and
  `C^check_{D,E}` is its certified subset. Never call the instantiated set a
  grammar or call the grammar a candidate set.
- `G_D^prod(T)` is the producer--precondition dependency graph reachable from
  target set `T`; it contains an edge `p -> r` when a producer of `p` has a
  positive dynamic precondition with predicate `r`. Schema regression is
  admitted only when this reachable graph is acyclic.
- `b = <g_b,C_b,beta_b,Sigma_b,pi_b>` is one candidate branch. `Sigma_b` is its
  conditional module-completion summary, with `MustAdd`, `MayAdd`, `MayDelete`,
  numeric-delta, and keyed resource-mode projections. `Cert_D(b)` is its
  candidate soundness predicate, and `covers_D(b,e)` is evidence coverage.
- `C_D^nr(E)` is the set of nonrecursive action-schema-derived obligations, and
  `realizes_D(b,c)` is their certified schema-achievement relation.
  `Omega_{D,E}` contains evidence coverage, nonrecursive schema-achievement
  coverage, preparation acyclicity, and recursive-ranking compatibility.
  `Closed_D(R)` means that every internal `!goal` in plan set `R` has a
  type-compatible selected implementation in the same set. `F_{D,E}` is the
  family of subsets of `C^check_{D,E}` that satisfy both `Omega_{D,E}` and
  `Closed_D`. `M_D` is the lexicographic optimum in that family. Optimality is
  never claimed outside the generated certified set.
- `rho_b` is a same-predicate well-founded ranking; `kappa_M` is the selected
  cross-module dependency rank; `G_b^res=(V_b^res,E_b^res)` is a finite abstract
  keyed resource-mode graph whose labelled edges are target-preserving symbolic
  action-schema transitions. These compile-time witnesses do not become agent
  beliefs.
- `tau_q = <iota_q,varphi_q,mu_q,Theta_q,Gamma_q>` is one unbound temporal
  specification: identifier, formula, proposition map, typed parameter
  signature, and binding constraints. `theta_q:Xbar_q->O_I` is the external
  object binding for the invoked instance,
  and `hat(tau)_q = (tau_q,theta_q)` is the bound query.
- `Phi_syn` is the recursive `F`, strong-`X`, strong-`U`, conjunction, and
  literal-negation input grammar; `Phi_bench` is the five-profile evaluation
  family; and `Phi_cert(D,M_D)` is the certificate-accepted subset. Never call
  these three scopes interchangeably "the supported fragment".
- `D_q = <Q_q^dfa,2^AP_q,delta_q,q_q^0,F_q>` is the deterministic finite
  automaton. For the bound query, `val_q` maps a proposition to true exactly
  when its `mu_q` predicate instance holds or its bounded integer equality has
  the requested value after applying `theta_q`. `d_q(z)` is
  the shortest directed distance from state `z` to an accepting state. A guard
  `chi` induces signed obligation
  `O_chi = <P_chi^+,P_chi^->`; `Pi_{chi,i}` is the preservation portfolio for
  occurrence `i`; `prec_chi` is the threat-induced precedence relation;
  `ell_chi` is the certified serialization; and `R_{q_s,chi}` is its
  transition-repair plan set.
- `W_{q_s}` is the set of non-progress self-loop guards and `I_{q_s}` their
  signed intersection invariant; `rho_num` is the lexicographic
  numeric-progress ranking, and `b_chi^joint` a complete joint
  guard-establishment branch. `R_chi[i,j]` is one transition-repair subtree,
  `c_{q_s,chi}` its source-state completion test, and `Pass_{q_s,chi}` one
  complete transition-repair pass.
- `Q_q` is the complete query-local plan set and `L_D^[k]` is the sole maintained
  domain library. The font distinction between DFA states `Q_q^dfa` and query
  plans `Q_q` must remain explicit in typeset mathematics.

Use academic names consistently: action-schema candidate generation,
conditional module-completion summary, target-preserving resource discharge,
ranked cross-module precondition repair, preservation portfolio, joint
guard-establishment certificate, and balanced binary transition-repair tree.
Do not use the ambiguous phrases `schema closure`, `candidate space`,
`existential preparation projection`, `whole-guard helper`, or bare `repair
tree` in the method exposition.

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

Use one small Blocks example across the Introduction, Method, Temporal
Composition, and Evaluation case study. The Introduction first defines Blocks
World in plain language: a robot rearranges blocks, placing one block on another
requires holding the first block and clearing the destination, and an executable
library must know how to achieve that missing condition. Introduce exact
predicate and action notation only after this explanation, in the method figure
and formal sections.

The evidence-side example begins with a readable MOOSE singleton-goal rule for
`on(X,Y)`, such as a regressed condition that permits `stack(X,Y)`. The compiler
generates modules for the domain-wide producible target universe even when MOOSE
did not observe those predicates as training goals. A representative recursive
result is:

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
opaque. For target-preserving resource discharge, an illustrative acquisition deletes
`free(R)` and adds `held(R,O)`; the method must state that names are placeholders
and that the certificate is inferred from shared arguments and PDDL effects. For
a mixed transition such as `at(P,L) and fuel(V)=3`, explain that one symbolic
effect proof must establish both conditions in the same state. Do not replace
these semantics with labels such as `certificate-dependent`.

### Abstract

The abstract follows a five-part structure:

1. **Problem:** generalized planners return reusable policies, while BDI agents
   require executable and maintainable plan libraries.
2. **Gap:** direct translation may omit executable plans for subsidiary goals
   and does not support safe temporal composition. Keep detailed certificate
   names out of the abstract.
3. **Method:** validate and lift generalized-planning evidence, complete missing
   achievable subgoals from PDDL action schemas, select a compact executable
   core, and append finite-trace query controllers without relearning it. Name
   concrete software components only in the method and evaluation sections.
4. **Guarantee boundary:** state soundness for the supported fragment and
   fail-closed rejection; defer candidate grammar and individual proof
   obligations to the formal sections.
5. **Results:** after the clean final runs, report one atomic-compilation number,
   one Jason+VAL execution number, and one DFA-acceptance or TEG-translation
   number. Do not insert unpinned diagnostic results.

### 1. Introduction

The Introduction establishes the representation bridge rather than listing
software components.

1. Contrast one grounded classical plan, one generalized policy, and one BDI
   plan library.
2. Explain why compilation is not formatting at a conceptual level: a policy
   may rely on subsidiary conditions for which an executable library has no
   plan. Defer the complete binding, closure, recursion, and resource
   certificate inventory to the method.
3. Explain why a temporally extended goal (TEG), meaning a goal over a finite
   state trace, cannot generally be replaced by an arbitrary sequence of
   achievement calls.
4. Introduce the Blocks running example in plain language before using
   `on(X,Y)`, `stack(X,Y)`, `holding(X)`, or `clear(Y)` notation. Keep the exact
   rule and temporal formula in the figure caption and method sections.
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
- a trigger--context--body BDI plan rule, a lifted module, and internal-call closure;
- AgentSpeak(L) as the concrete rendering used by the implementation and Jason
  as its evaluated interpreter, without claiming portability to unevaluated BDI
  languages;
- an LTLf formula and its deterministic finite automaton (DFA);
- the domain-compilation input `(D, I_train, E)` and atomic-core output `M_D`;
- the per-query input `(M_D, hat(tau)_q)`, where
  `hat(tau)_q=(tau_q,theta_q)`, and query-plan output `Q_q`; and
- the sole maintained library after an ordered sequence `q_1, ..., q_k`,
  `L_D^[k] = M_D union (union_{i=1}^k Q_{q_i})`, with `L_D^[0] = M_D`.

`M_D` is the certified atomic module core: the query-independent selected BDI
branches, such as `+!on(X,Y)` and `+!clear(X)`. `Q_q` is the query-local plan set,
including `+!g_query` and `+!g_query_trans_1`. Appending it changes
`L_D^[k]` to `L_D^[k+1] = L_D^[k] union Q_q`. These are logical subsets of the
one maintained library, not separately maintained files. State the allowed
output vocabulary and supported temporal fragment in this section.

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

### 4. Certified Atomic-Module Compilation

This section covers only the post-evidence domain compiler. Its candidate and
certificate representation is defined at the trigger--context--body BDI
plan-rule level; the implemented final rendering targets AgentSpeak(L).

1. Normalize the raw provider artifact `E_raw` into a provider-neutral singleton-goal evidence
   program. Do not expose an internal class name in the main narrative.
2. Define the domain-wide producible target universe
   `T_D(E) = goalPred(E) union prod(D)`, where `prod(D)` contains every predicate
   appearing in a positive PDDL add effect. Static predicates remain contexts;
   delete-only dynamic predicates are not invented as positive targets. Keep
   this target expansion distinct from internal-call closure of the selected
   branch set.
3. Define the finite candidate-construction grammar `G` and instantiate
   `C_D(E)=Inst_D(G,T_D(E),T_D^Z(E))`: direct producers;
   backward STRIPS regression over acyclic producer dependencies; and finite
   causal resource-mode discharge. Regression unifies producer preconditions
   with compatible open requirements before introducing fresh variables.
   Termination comes from
   forbidding repeated alpha-normalized requirement/producer roles and resource
   modes, not from an arbitrary action-depth bound. Validated evidence macros
   are never truncated. Cyclic dependencies require provider evidence or a
   separately certified recursive module; this is not an instance-level planner.
4. Summarize the implemented certificates in one table: binding, symbolic
   executability, achievement, internal-call closure, relation-ranked recursive progress,
   finite resource-mode discharge, and Clingo-selected acyclic cross-predicate
   preparation with strictly decreasing dependency ranks.
5. Explain feasible-core optimization over evidence and action-schema-derived
   candidates.
   The precise claim is global optimality only inside the generated certified
   certified candidate set `C^check_{D,E}`.
6. Render the selected modules as the certified atomic module core `M_D`. State
   explicitly that AgentSpeak(L) is the evaluated realization, not the
   definition of the compilation contribution and not a second maintained
   library.

Detailed certificate definitions may remain in the main paper when required to
understand a contribution. Long proof steps and secondary implementation cases
belong in supplementary material so that final results fit the seven-page AAAI
technical-content limit.

### 5. DFA-Guided Composition of Temporally Extended Goals

This section covers only query-specific control over the selected atomic core
`M_D`. Open by defining the semantic input boundary rather than prescribing a
surface grammar for users. The evaluated front end receives a source utterance,
the public PDDL symbol catalogue, declared typed parameters, and binding
constraints; it returns the exact eight-key lifted LTLf artifact. Explain its
formula, atom-table, parameter, constraint, metadata, and support-status fields
as one parametric specification. Parameters are externally bound at invocation,
not quantified or exhaustively grounded. The controlled utterances in the
released benchmark define the evaluated distribution rather than a required
user syntax. Keep the frozen prompt and field-by-field schema in the Technical
Supplement and public artifact.

Before describing the automaton, give the compact grammar for `Phi_syn` and
state that negation applies only directly to an atom. Define `Phi_bench` as the
five registered profile schemas and `Phi_cert(D,M_D)` as the bound formulas
whose required DFA progress obligations pass all compiler certificates. Parsing
is not a planning-completeness claim. Put the full non-empty finite-trace
satisfaction clauses for conjunction, strong Next, Eventually, and strong Until
in the Technical Supplement. Define `val_q` for both bound PDDL predicates and
bounded integer equalities.

1. Validate the structured artifact fail-closed, meaning rejection rather than
   silent repair. Require the exact schema; exactly one atom-table entry for
   every formula symbol and no unused entry; PDDL catalogue membership; valid
   arities, parameter types, numeric values, and temporal operators. Gold-formula
   equivalence is an evaluation oracle, not a deployment-time input requirement.
2. Construct the deterministic automaton for validated lifted LTLf JSON with
   `ltlf2dfa` and MONA. Do not use an ordered-sequence approximation.
   Explain that MONA may return several valuation cubes representing Boolean
   alternatives. Each cube is compiled as one conjunctive guard; several cubes
   are not one admitted disjunctive guard, and the monitor retains every original
   cube even when same-source/same-target cubes share a certified objective.
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
   single-action joint guard-establishment certificate as three bounded
   strategies rather than claiming arbitrary numeric planning. A joint
   guard-establishment branch must be
   callable from every positive literal it establishes and must carry the
   certificate's complete anchor arguments.
9. For an Until source state, extract common waiting-loop literals as source
   invariants. Require primitive-prefix preservation until the single positive
   progress literal is established. Explain lexicographic predicate/numeric
   precondition preparation, repeatable non-unifying numeric steps, exact
   terminal predecessors, and capture-avoiding composition.
10. Compile the certified order into a balanced binary transition-repair tree. The tree is
   an AgentSpeak indexing structure with trigger fan-out and individual plan-body
   length at most two; it does not reorder DFA transitions or add planning
   semantics. Contrast it with a semantically equivalent linear rendering,
   whose single plan body and intention continuation grow with guard size. Include a compact
   construction algorithm defining the signed leaves, midpoint range recursion,
   transition entry, and two completion alternatives.
11. Advance the real deterministic finite automaton after the initial valuation
   and every successful primitive PDDL action. Explain that the integrated
   runtime monitor gives the declared formula fragment primitive-step trace
   semantics, while action-strategy synthesis remains incomplete. Source-state
   exit is tested only by the done helper after one full repair pass; it does not
   interrupt an atomic call or the remaining tree ranges. Prove that the suffix
   contains only observations or certified, prefix-preserving repairs and that
   every primitive suffix action remains visible to the same DFA. It may cross
   further actual edges, including rejection, but cannot manufacture acceptance.
   The top-level controller then dispatches from the actual monitor state.

### 6. Conditional Guarantees

Keep guarantees separate from algorithm exposition, following the MOOSE
presentation.

The main paper should contain:

1. **Local atomic-branch soundness:** under its certified context and
   type-consistent grounding, an accepted branch is executable and establishes
   its trigger when it returns, assuming called modules satisfy their own
   conditional module-completion summaries.
2. **Certified-candidate-set optimality:** Clingo satisfies every encoded
   evidence and internal-call obligation and returns the lexicographic optimum inside
   the generated certified candidate set `C^check_{D,E}`.
3. **Supported-transition composition soundness:** if signed obligations are
   initially satisfied or established by their certified repair plans, selected
   modules terminate, and their certified completion effects preserve earlier
   positive and negative obligations, a complete repair pass retries exactly
   when the monitor still reports its source state. If the source is left during
   a call, the remaining suffix stays PDDL-executable and prefix-preserving at
   module returns, while primitive-step monitoring makes every later transition
   an actual DFA edge; rejection fails rather than becoming false success.
4. **Balanced transition-repair complexity:** for `n` signed literals and `e`
   certified repair
   plans, the generated query-local tree has `2n+e+2` plans, maximum trigger
   fan-out two, maximum plan-body length two, logarithmic nesting depth, linear
   work per pass, and the same certified literal order.
5. **Runtime-monitor trace fidelity:** monitor-state beliefs are the result of
   deterministic DFA transition evaluation after every primitive action, not a
   second planning semantics or a domain fluent.
6. **Initial-acceptance trace semantics:** zero primitive actions denote the singleton
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
  internal-call closure change module coverage and held-out execution.
- **Contributions of candidate generation and selection.** Separate the effects
  of action-only producible-target expansion, recursive/resource/preparation
  candidates, and joint Clingo selection on coverage, size, and runtime.
- **Preservation of temporal guards.** Against a controller with the same real
  DFA, atomic library, monitor, and Jason runtime but no effect-preservation
  reasoning, measure the effect of threat ordering and preservation portfolios on
  VAL- and DFA-valid execution.
- **Controller structure.** Compare flat and balanced repair controllers while
  preserving literal order and occurrence-specific preservation portfolios;
  report controller size,
  trigger fan-out, loading cost, and execution time without assigning semantic
  credit to the tree.
- **End-to-end behavior.** Across domains, formula profiles, and evidence seeds,
  report valid traces and keep one-time core compilation, query append, and
  execution costs separate. Do not claim amortization without a measured
  break-even analysis. Compare Raw MOOSE and per-instance planners only on
  their declared scopes.

After the questions and protocol, present evidence in dependency order. First,
paired component ablations identify which mechanisms change coverage or
structure. Second, full-system results report five-seed atomic robustness and
fixed-library temporal validation. Third, external planning references place
those results in context. Use compact tables at the point where each claim is
introduced. Do not add a dashboard-style empirical figure that duplicates
endpoint values already reported exactly in those tables.

The registered atomic comparison is cumulative and paired on one exact
normalized evidence hash:

1. **Evidence Only:** validate provider macros against the PDDL schemas and
   retain them without producible-target expansion, internal-module synthesis,
   or optimization.
2. **Direct Producers:** expand over the producible target universe using only
   action-only producer candidates.
3. **Maximum Feasible:** add progress-, preparation-, and resource-certified
   decomposed candidates, then select a maximum-cardinality jointly feasible
   branch set under all hard certificates.
4. **Full GP2PL:** minimize branch, context, and body cost over exactly the
   same generated certified set and hard constraints as Maximum Feasible.

The registered temporal comparison holds the DFA, atomic-library hash, query
binding, and Jason runtime fixed:

For the final combined run, the shared atomic input is not copied from the
long-running evidence batch. It is the seed-0 Full GP2PL output produced by
the atomic stage of the same run and confirmed method-source equivalence class.
The evidence batch supplies only the MOOSE model and readable policy. Exact
atomic-library and controller-input hashes, rather than Git commit identity,
prevent different semantic inputs from entering a paired temporal comparison.

1. **Unprotected Serialization:** canonical within-edge serialization, the same
   MONA-derived DFA,
   and primitive-step monitor, but no threat ordering or preservation portfolio.
2. **Certified Flat:** add complete-effect threat ordering and preserving
   portfolios, retaining flat sibling control.
3. **Certified Balanced:** replace only flat control with the balanced binary
   transition-repair tree.
4. **Module-Return Monitor:** retain completion-effect certification and balanced
   control, observe the DFA only after an atomic module returns, and omit
   primitive-prefix source-invariant filtering because intermediate primitive
   states are not observable under this ablation. Run it on the complete paired
   benchmark, but attribute observation-boundary effects only on cases with
   intermediate-state obligations.

These four cumulative atomic rows are the complete registered matrix. Do not
claim additional one-certificate-off experiments: retaining an uncertified
branch would be unsound, while removing one branch-constructor class changes
internal-call feasibility rather than isolating a single subsequent mechanism.
Use the 13-case
fail-closed and symbol-invariance matrix to test the individual certificate
families. Likewise, signed-negative and bounded-numeric cases stay in the full
temporal benchmark with explicit support and failure statuses; do not invent
unregistered capability-switch rows. The historical sequence-only controller
may appear only as an evaluation-only weak reference; it must not return as an
operational shortcut.

The benchmark section must describe how the TEG dataset is constructed, not
only its released fields and translation results. The main paper gives the
compact dependency-ordered flow:

```text
PDDL domain + held-out problem initial state
-> bounded legal non-repeating rollouts
-> five-profile temporal candidate pool
-> typed parameter lifting + hidden binding/witness
-> deterministic profile/signature-balanced selection
-> deterministic controlled-English rendering
-> problem-complete manifest
-> complete-input translation deduplication
```

State explicitly that the original PDDL achievement goal is provenance only:
it does not affect rollout enumeration, candidate ranking, query wording, or
construction success. The main paper must include one concrete lifted example
and direct readers to Technical Supplement, Sec. 4.1.

Technical Supplement, Sec. 4.1 must define the construction record
`B_i=<D,P_i,q_i,T_i,theta_i,pi_i>`, the event extraction rules, all five formula
profiles and their witness conditions, nontriviality filters, typed lifting,
deterministic selection, public/private boundary, and complete-input
deduplication. It must also report the primary and expanded registered bounds
and explain that bounded failure is not an impossibility proof. Keep the frozen
prompt in Sec. 4.2 and PDDL provenance in Sec. 4.3.


The main benchmark section records all 16 domain families, the split
provenance, and the independent five-seed design. Its scientific purpose is to
estimate variation caused by MOOSE's randomized goal-order sampling. Exact
memory limits, timeouts, worker configuration, run identifiers, and source
hashes belong in the Technical Supplement. Every seed is compiled and evaluated
independently; report the mean and sample standard deviation in the main paper,
and preserve every individual result in the supplement. Never union evidence or
select a best seed. Concurrent launch is only an artifact-level throughput
choice, and contended wall time is not a method result. Cross-seed
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
with its underscore encoding are explicit unsupported cases. The pinned MOOSE
artifact is executed through a hash-checked extracted sandbox, with one private
`/work/out` mount per Raw MOOSE or LAMA case. FOND4LTLf redirects the fixed
`ltlf2dfa` `automa.mona` scratch path into one private directory per case. The
registered remote LAMA/MRP+HJ and direct FOND4LTLf matrices therefore use 20
case workers without host-wide planner or compiler locks. Partition the MOOSE
coverage reference before execution: use Table 4 of arXiv `2511.11095v1` for
all twelve original MOOSE domains and local five-seed Raw MOOSE runs for all
four GP2PL-added domains. Label these rows `Reported` and `Measured`,
respectively. Never switch an individual domain between sources after observing
its score. The reported row supplies coverage only; do not compare its runtime
or memory with local measurements. A local full-seed run is a reproduction
diagnostic rather than a source for selectively replacing published cells.
Other published numbers
from different splits or hardware may be cited as prior results but must not be
inserted into paired experiment tables. Plan4Past is a design precedent for
holding the task-level planner fixed while comparing temporal compilations; it
is not directly comparable until any future-LTLf-to-past-LTLf translation has
been proved language-equivalent.

Repair only cases explicitly recorded as infrastructure failures in those
complete 20-worker matrices. Run the exact repair set serially with one worker,
then fail closed on extra or missing cases, input-fingerprint changes,
toolchain or resource-limit drift, and recurring infrastructure failures. Keep
both source revisions, both summary hashes, and per-case replacement
provenance. The experiment owner confirms equivalent local and remote machine
configurations and comparable resource availability; case runtime excludes
queue waiting, so repaired records remain eligible for PAR-2. Never repair a
planner failure, timeout, unsupported input, compiler failure, or validation
failure.

Treat the generated FOND4LTLf Python entry point and MONA libtool launcher as
path-embedded launchers rather than portable binaries. If their raw hashes
differ across the two equivalent machines, verify the retry file against its
recorded hash, rewrite only its recorded absolute installation prefix, and
require the rewritten bytes to match the primary hash. Keep pinned revisions,
versions, the isolation-wrapper hash, and planner artifacts exact. This is a
verified relocation equivalence, not a relaxed toolchain comparison.

Atomic metrics are producible-predicate coverage, internal-call closure, held-out
Jason+VAL coverage, branch/context/body costs, ASL bytes, and compile time.
Producible-predicate coverage has one paired denominator per seed/domain: all
predicate symbols in positive PDDL action effects. Every method is scored by
the module triggers it actually emits against that same set. Never let Evidence
Only or another reduced variant redefine the denominator through absent
target-universe metadata.
Temporal metrics are compile/rejection status, Jason success, VAL validity,
gold-DFA acceptance, action count, PAR-2 runtime, append time, controller size,
and maximum trigger fan-out. Plan length is compared only on jointly solved
instances. Report paired coverage differences, every seed, mean and sample
standard deviation. A rejection challenge suite and symbol-renaming,
parameter-permutation, object-renaming, and irrelevant-fluent metamorphic tests
are mandatory evidence for fail-closed and domain-independent behavior.

The five atomic seeds repeat the same 1,228 held-out identifiers. Seed--case
totals are descriptive; inferential analysis first averages the paired binary
difference within each case identifier and applies a two-sided exact sign test
to the 130 nonzero case-level differences. Temporal queries cluster by domain
and share 475 translation inputs, so temporal coverage changes use discordant
counts and domain/profile concentration without a case-level p-value.

The result narrative must locate effects rather than only report aggregates.
All 640 Direct-to-Maximum seed--case gains occur in the four added domains. On
those same 740 five-seed evaluations, Full GP2PL validates 720 traces and Raw
MOOSE 117. Four numeric domains account for 113 of the 114 net
Unprotected-to-Flat temporal gains. These are scope statements, not domain
routing rules.

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

### 8. Conclusion and Future Work

The merged section first answers three questions: what representation gap was
closed, why the output can be executed by a BDI agent, and which temporal goals
are certified. Do not repeat the implementation inventory.

Compress the main-paper limitations into one short sentence for each claim
boundary: evidence-provider and candidate-grammar scope; temporal-dataset and
fixed-core scope; and incomplete strategy synthesis. Preserve the detailed
rejection categories and implemented bounds in the Technical Supplement.

Close the section with generator-assisted domain onboarding as a bounded future
extension. A pinned parameterized PDDL problem generator may create a finite
training curriculum for a compatible generalized-planning provider, provided
that generated problems validate against the domain and a disjoint held-out set
is sealed first. Describe this as scaling evidence acquisition and domain
onboarding, not as expanding the supported PDDL-times-LTLf fragment, proving
representative sampling, or changing any compiler certificate.

## Supplementary and Public Artifact Contract

The standalone source
`latex_code/aamas_method_paper/technical_appendix.tex` is the canonical
technical appendix. It contains the full formal definitions, assumptions,
proofs of every proposition, theory-to-code map, novel-data description,
the witness-backed TEG construction algorithm and registered search bounds,
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
present in the paper, appendix, or submitted archive. Atomic coverage inference
uses a two-sided exact sign test over distinct held-out case identifiers after
within-case seed aggregation. Temporal coverage, PAR-2, action count, and size
remain descriptive because of domain/input clustering; Flat versus Balanced is
structural because their valid-case sets are identical.

## Final Visual Program

The visual hierarchy follows the representation-compilation contribution rather
than forcing every result into a chart. Figure 1 is the single-column framework
overview on the first page. Figure 2 is a full-width, domain-independent view
inside the two compiler stages. Figure 3 is a small single-column atomic-lifting
case placed beside candidate construction, and Figure 4 is a small single-column
temporal-composition case placed beside DFA-guided composition. The two case
figures instantiate the abstract stages without crowding Figure 2.

The main paper has no empirical result figure. Exact endpoint comparisons over
heterogeneous domains are reported in compact `booktabs` tables at the point of
the corresponding claim. The main paper retains the supported-fragment,
candidate-constructor, paired atomic, paired temporal, compact five-seed,
compact fixed-core temporal, and same-scope evidence-to-library tables.
Per-profile, per-domain, per-seed, runtime-distribution, and diagnostic views
belong in the Technical Supplement, together with the complete
scope-separated external-reference matrix.

### Figure Production Handoff Contract

Figures 1--4 and the planned supplementary DFA diagram are conceptual. Their
labels and examples below come from the implemented architecture, evidence, and
domain schemas, not from estimated experimental measurements. Experimental
numbers enter the manuscript only through deterministic tables generated from
pinned JSON artifacts. No colleague or paper-writing agent may infer missing
values from prose, terminal logs, an earlier run, or another method.

Use one normalized coordinate system for all object specifications below:
`x=0,y=0` is the top-left corner; `x`, `y`, `w`, and `h` are percentages of the
complete slide. Snap objects to the specified coordinates within 0.5 percentage
points. Captions are LaTeX text below the imported graphic and must not be drawn
inside the PowerPoint slide.

Canvas, PowerPoint, Python, and export settings:

- Main Figure 1 uses the approved 2558-by-1256, 330-DPI PNG and is inserted at
  3.25 inches wide (approximately 1.60 inches high). Main Figure 2 uses a
  13.333-by-4.2-inch PowerPoint export canvas and is inserted at 7.0 inches
  wide. Figures 3 and 4 each use a 6.5-by-2.7-inch canvas and are inserted at
  one column. The supplementary DFA figure uses a 13.333-by-5.333-inch
  PowerPoint canvas. Figure 1 retains its supplied alpha channel and must be
  verified on the paper's white page; generated conceptual figures use a white
  opaque background.
- Use Arial Regular 18 pt for labels and panel headings, and Courier New Regular
  18 pt for domain schemas, AgentSpeak, formulas encoded as text, and artifact
  field names. Do not use bold text inside any figure. These fonts become at
  least 9 pt after scaling to their final AAAI dimensions.
- Use square or 0.06-inch-corner rectangles. Do not use shadows, gradients,
  three-dimensional effects, icons, decorative illustrations, or screenshots.
- Main Figure 1 is the approved, version-controlled raster asset
  `fig1_architecture.png`; its SHA-256 identity is enforced by the method-figure
  generator and tests. Figures 2--4 and the supplementary DFA figure may share
  the editable source deck `aaai_method_figures_source.pptx`, with exactly one
  figure per slide.
- Main figure files are `fig1_architecture.png`,
  `fig2_compiler_stages.pdf`, `fig3_atomic_case.pdf`, and
  `fig4_temporal_case.pdf`. The supplementary vector file is
  `figS1_dfa_controller.pdf`; all files live under
  `latex_code/aamas_method_paper/figures/` when delivered.
- Embed fonts in vector PDFs, crop to the slide boundary, and verify all text at
  its final include width. Do not rasterize Figures 2--4 or
  resample/recompress the locked Figure 1 PNG.

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
  dependency, subgoal call, effect-summary use, or internal-call relation. Its label
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

### Figure 1: GP2PL Representation Bridge

Use a single-column `figure[htbp]` in the first page's right column. Place its
source after the Introduction's compact singleton-goal example and before the
temporal-goal motivation. In the AAAI two-column layout, this leaves the abstract
and opening domain-compilation motivation in the left column while the overview
occupies the top of the right column without forced placement. Insert the approved
`fig1_architecture.png` at `\columnwidth` and its native aspect ratio; do not
regenerate, resample, or recompress it. The locked SHA-256 is recorded in the
figure generator. The placeholder reserves 1.40 inches of artwork height before
the caption. The figure is a problem-level overview, not a software-component
inventory.

Use a compact vertical flow with one side input and one final library artifact:

- `Domain model D` and `Singleton-goal policy evidence E` converge on
  `(1) Lift + certify core once`, producing
  `Certified atomic module core $\mathcal M_D$`.
- Draw one solid reuse arrow from `$\mathcal M_D$` to `(2) Compose + append`.
  A side input `Bound temporal query $\widehat\tau_q=(\tau_q,\theta_q)$` enters this
  second operation.
- Label the output arrow `query plans $\mathcal Q_q$`; do not draw
  `$\mathcal Q_q$` as a separately maintained component.
- End at one emphasized stacked-document artifact labelled
  `Executable BDI domain library $\mathcal L_D^{[k]}$`. Place the append equation
  `$\mathcal L_D^{[k+1]}=\mathcal L_D^{[k]}\cup\mathcal Q_q$` beside the output
  arrow rather than drawing a second library artifact.
- Do not use a dashed outer library container or the implementation-level
  `reuse module contracts` feedback connector.

Do not place PDDL syntax, MOOSE, Clingo, MONA, Jason, VAL, certificate tables,
`Layer A/B/C`, `tg_state`, a second domain library, or a language model inside
Figure 1. Those details belong in Figure 2, the algorithms, and Evaluation.
Draft caption:

> **Figure 1:** GP2PL separates reusable domain compilation from query-specific
> temporal compilation. An external generalized-planning backend derives raw
> singleton-goal evidence $\mathcal E_{\mathrm{raw}}$ from domain $D$ and training
> instances $\mathcal I_{\mathrm{train}}$. Validated policy lifting compiles these
> inputs once into $\mathcal M_D=\mathcal L_D^{[0]}$; DFA-guided temporal
> compilation maps each bound query $\widehat{\tau}_q$ to query-local plans
> $\mathcal Q_q$, updating the sole maintained library by
> $\mathcal L_D^{[k+1]}=\mathcal L_D^{[k]}\cup\mathcal Q_q$.

### Figure 2: Inside the Two GP2PL Compiler Stages

Place this full-width `figure*[t!]` after Figure 1. Use two adjacent process
panels separated by one thin rule. This figure explains compiler stages only:
it contains no domain objects, PDDL snippets, AgentSpeak plans, candidate rows,
or repair tree.

- Panel (a), `Query-independent atomic-core compiler`, shows
  `$D,\mathcal I_{\mathrm{train}},\mathcal E_{\mathrm{raw}}$` entering
  `normalize and canonically lift`, then `construct candidates over the
  producible target universe`, `certify branches`, and `joint lexicographic
  selection`, yielding `$\mathcal M_D=\mathcal L_D^{[0]}$`.
- Panel (b), `Query-specific temporal compiler`, shows
  `$\widehat\tau_q$` entering `real LTLf2DFA/MONA construction`, then `signed
  progress obligations`, `completion and preservation certification`, and
  `balanced controller rendering`, yielding `$\mathcal Q_q$` and the append
  equation `$\mathcal L_D^{[k+1]}=\mathcal L_D^{[k]}\cup\mathcal Q_q$`.
- A single reuse connector carries certified completion summaries from
  `$\mathcal M_D$` to temporal certification. Label it `reuse; no relearning`.
- Use short noun phrases and the notation already defined in the paper. The
  figure must show mathematical transformations, not software components.

Approved caption:

> Figure 2: Inside the two GP2PL compiler stages. The query-independent stage
> normalizes and lifts evidence, constructs and certifies schema-derived
> candidates, and selects $\mathcal M_D=\mathcal L_D^{[0]}$. The query-specific
> stage compiles a bound temporal query through its DFA progress obligations,
> certified preservation constraints, and query-local controller
> $\mathcal Q_q$, which is appended without relearning the core. The worked
> cases are separated into Figures 3 and 4.

### Figure 3: Atomic Lifting Case

Place this single-column figure at the end of Action-Schema Candidate
Generation, immediately before Candidate Soundness Certificates. It
instantiates Figure 2(a) with Blocks World:

- Start with lifted evidence for `on(X,Y)` and the validated
  `stack(X,Y)` macro.
- Show the relevant producible target universe containing `on/2`, `clear/1`,
  and `holding/1`; label the connection from `stack` requirements as
  `producer preconditions`.
- Show three compact candidate rows: already satisfied, direct producer, and
  recursive preparation via `!clear(Y)`. A longer feasible macro may appear in
  gray as a higher-cost alternative.
- End with the selected `+!on(X,Y)` fragment and a visible call edge to a
  selected `+!clear(Y)` module. The closure statement is `every internal call
  resolves inside $\mathcal M_D$`.
- State visually that names are illustrative; construction uses typed schemas
  and effects, not Blocks-specific rules.

Approved caption:

> Figure 3: Atomic lifting case in Blocks World. Evidence for `on(X,Y)`
> supplies a validated `stack(X,Y)` macro; the producible target universe
> additionally admits modules such as `clear/1` and `holding/1`. A direct
> producer handles the ready context, while certified recursive preparation via
> `!clear(Y)` covers an obstructed destination. Joint selection retains a
> compact implementation whose internal call resolves inside $\mathcal M_D$.

### Figure 4: Temporal Composition Case

Place this single-column figure after the signed transition obligation is
defined and before Conditional Module-Completion Summaries. It instantiates
Figure 2(b) with the same domain:

- Show the bound eventual tower query and its object binding.
- Show only the relevant MONA progress edge, whose guard contains the three
  required `on` literals.
- Show completion-summary threats inducing the bottom-up order
  `on(b3,b4)`, `on(b2,b3)`, `on(b1,b2)`.
- Show the compact balanced repair tree and its output
  `$\mathcal Q_q$`; end at the append equation rather than drawing another
  maintained library.

Approved caption:

> Figure 4: Temporal composition case in Blocks World. For a bound eventual
> tower query, one MONA progress guard requires three `on` literals to hold
> together. Conditional completion summaries induce a bottom-up
> preservation-safe order; the balanced transition-repair tree realizes that
> fixed order and emits $\mathcal Q_q$. The controller is appended to
> $\mathcal L_D^{[k]}$ without changing $\mathcal M_D$.

### Supplementary Figure S1: DFA Transition Compilation and Runtime Monitoring

Place this full-width figure in the technical supplement beside the formal
transition-compilation rules. Use four panels. The decoded MONA example is
`phi = F(on(A,B) & on(B,C) & not holding(A))`. Define the complete progress
guard once as `G`; all subsequent labels refer to that same guard. This is a
semantic method example, not one measured benchmark trace.

Panel containers:

- `(a)` is `x=1,y=2,w=23,h=96`, heading `MONA-derived DFA transition`.
- `(b)` is `x=26,y=2,w=21,h=96`, heading `Signed obligations`.
- `(c)` is `x=49,y=2,w=27,h=96`, heading
  `Certified balanced transition-repair tree`.
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
- Put `decoded real ltlf2dfa/MONA DFA` in gray 18 pt text at `x=4,y=88`.
  Do not show a hand-authored ordered sequence or a `tg_state` belief.

Panel (b):

- `F3-B0`: `x=28,y=15,w=17,h=10`. Blue box: `Conditional module-completion`
  and `summaries`.
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
  strip in gray 18 pt text.
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
- In an 18 pt gray inset at `x=50,y=95,w=14,h=3`, state:
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
  Route it through the empty lower gutter so it does not cross the
  transition-repair tree.
- Draw a solid green arrow from the final `q1 accepting` badge to
  `top-level DFA dispatch` at `x=83,y=76,w=13,h=10`.
- Under the timeline, draw a gray bracket from `s0` through `sk` labelled
  `one committed state trace`. Do not insert a noop before `s0`, and do not
  imply that failed Jason prefixes are committed plans.

All helper names in panel (c) omit the common prefix
`g_query_17_trans_1_` only to remain legible; print this note in gray 18 pt at
`x=65,y=95,w=10,h=3`, to the right of the singleton inset. Draft caption:

> **Supplementary Figure S1: Preservation-safe compilation of one DFA progress
> transition.**
> Conditional module-completion summaries induce a threat-induced precedence
> relation over signed guard obligations. A balanced binary transition-repair
> tree, rendered here in AgentSpeak(L),
> realizes that fixed order with trigger fan-out at most two, while the DFA
> monitor observes every primitive action. Uncertified cyclic threats or
> negative-literal repairs are rejected rather than serialized heuristically.

### Reproducibility-Only Diagnostic Plot

Do not insert this plot into the main paper. The checked-in script remains a
reproducibility diagnostic for the frozen paired-ablation artifact and owns
every point, interval, curve, label, and style; PowerPoint must not be used to
reconstruct its data marks.

The canonical command is:

```bash
uv run python scripts/generate_aaai_figures.py \
  --ablation-results \
  paper_artifacts/gp2pl_evaluation/v1/paired_ablation_results.json \
  --output-file \
  latex_code/aamas_method_paper/figures/fig3_evaluation.png
```

The generator accepts only the frozen paired-ablation artifact. It requires the
four registered atomic variants, the four registered temporal variants, seeds
0--4, all 16 domains, the common case contracts, certified atomic and temporal
pairing, the 1,800-second limit, six workers, and the 64-MiB Java stack. It
recomputes every per-domain coverage, per-seed coverage, summary success count,
and cumulative temporal curve from the portable records. For temporal success,
Jason, neutral-goal VAL, gold-DFA acceptance, and predicted-DFA acceptance must
all agree. A mismatch writes a diagnostic and leaves the existing PNG untouched.

When regenerated for diagnosis, use one horizontal three-panel layout on a
7.0-by-2.833-inch canvas. Export
directly at 600 dpi, producing exactly 4,200 by 1,700 pixels. Use regular
Helvetica at 9 pt or larger, an opaque white background, light-gray major grids,
and no top or right spines. The palette is colorblind-safe, while printed cell
values, marker shapes, and line styles make every comparison independent of
color. Do not use stars or bold text.

Panel (a), `Atomic coverage by domain`:

- Recompute Jason-plus-VAL coverage for all four atomic variants from all five
  paired seeds. Display every domain for which any variant differs. Aggregate
  the remaining domains in one `Other N` row only when all four variants have
  identical coverage there. This rule is data-independent and prevents
  favorable-domain selection.
- Use a four-column numeric matrix with the method order Evidence Only, Direct
  Producers, Maximum Feasible, and Full GP2PL. Print each percentage in its
  cell; fill intensity is redundant. Outline the selected Full column without
  implying significance.
- The frozen release currently yields five differing domains and 11 unchanged
  domains, all at 100 percent. The exact per-seed domain distribution remains
  in the generated Technical Supplement table.

Panel (b), `Blocksworld Tower time-to-valid-trace`:

- Use every one of the 385 paired seed--instance records in the registered
  Blocksworld Tower size series, which spans 12--50 blocks. This is the corpus's
  monotonic size stress family and therefore gives a principled scaling view;
  no individual instance is selected after observing its outcome.
- Plot right-continuous cumulative valid-trace curves for Maximum Feasible and
  Full GP2PL on a logarithmic time axis. Evidence Only and Direct Producers
  solve 0/385 and are reported as an explicit annotation rather than two
  coincident zero curves.
- Failures remain in each method's denominator. Do not smooth or interpolate
  the empirical curves.

Panel (c), `Temporal time-to-valid-trace`:

- Plot one right-continuous cumulative curve for each temporal variant over the
  identical 1,228-query paired set. A query enters the numerator only when its
  complete execution satisfies Jason, neutral-goal VAL, and both DFA oracles.
  Failed and timed-out queries remain in the denominator.
- Use a logarithmic end-to-end time axis and mark 1, 10, 100, and 1,800 seconds.
  The dashed vertical line is the registered deadline. Do not smooth or
  interpolate the empirical step curves.
- Use short labels `Unprotected`, `Certified flat`, `Certified balanced`, and
  `Module return`; the exact success counts, PAR-2, controller plans, and trigger
  fan-out remain in the generated table.

Diagnostic description, not a manuscript caption:

> Paired-ablation diagnostic. Panel (a) reports descriptive Jason-plus-VAL
> coverage over five evidence seeds for every domain on which the atomic
> variants differ; the other 11 domains are aggregated because all variants
> reach 100 percent. Panel (b) gives cumulative valid traces over end-to-end
> time for all 385 seed--instance pairs in the registered 12--50-block Tower
> series. Panel (c) gives cumulative valid-trace coverage for all 1,228 paired
> temporal queries. Failures remain in every denominator, and the dashed line
> marks the 1,800-second limit. Repeated atomic seeds are not treated as
> independent inferential units; numeric labels, markers, and line styles
> duplicate color.

When the diagnostic is regenerated, verify its totals against both generated
ablation tables and require the same frozen source SHA-256 in its metadata.
Never copy values from a PDF or LaTeX table back into the plotting source.

### Figure Delivery and LaTeX Insertion Contract

The colleague may deliver the editable method deck and planned conceptual
figures separately. The optional diagnostic plot remains script-owned and is
not part of the main-paper figure manifest. If the planned conceptual assets
are delivered, assemble the
multi-asset `aaai_figure_manifest.json` only after recording their dimensions,
data sources, and embedded fonts. Any font substitution is a release blocker.

Use these LaTeX placements and labels. Figures 2--4 retain visible placeholders
until their colleague-produced vector PDFs are delivered:

```latex
\begin{figure}[htbp]
  \centering
  \IfFileExists{\gpplfigureonepath}{
    \includegraphics[width=\columnwidth]{\gpplfigureonepath}
  }{<single-column placeholder>}
  \caption{<approved Figure 1 caption from this outline>}
  \label{fig:architecture}
\end{figure}

\begin{figure*}[t!]
  \centering
  \IfFileExists{\gpplfiguretwopath}{
    \includegraphics[width=\textwidth]{\gpplfiguretwopath}
  }{<full-width placeholder>}
  \caption{<approved Figure 2 caption from this outline>}
  \label{fig:compiler-stages}
\end{figure*}

\begin{figure}[htbp]
  \centering
  \IfFileExists{\gpplatomiccasepath}{
    \includegraphics[width=\columnwidth]{\gpplatomiccasepath}
  }{<single-column placeholder>}
  \caption{<approved Figure 3 caption from this outline>}
  \label{fig:atomic-case}
\end{figure}

\begin{figure}[htbp]
  \centering
  \IfFileExists{\gppltemporalcasepath}{
    \includegraphics[width=\columnwidth]{\gppltemporalcasepath}
  }{<single-column placeholder>}
  \caption{<approved Figure 4 caption from this outline>}
  \label{fig:temporal-case}
\end{figure}
```

The Evaluation source contains no empirical figure path or result-plot float.
Exact endpoint values enter through generated tables. The historical
`fig3_evaluation.png` and its script remain reproducibility diagnostics only.

The angle-bracket caption placeholders are instructions and must be replaced by
the approved caption text before compilation. Never duplicate a caption inside
the graphic. Inspect the compiled paper at 100 and 200 percent zoom, print one
grayscale proof, and verify that line style and labels preserve every semantic
distinction without color. Run `pdffonts` on vector assets and require all fonts
to report embedded. The final manuscript must cite each figure before it
appears.

### Table 1: Supported Fragment and Rejection Boundary

Keep one compact single-column table with columns:

```text
Construct | Accepted strategy | Rejection boundary
```

Rows cover positive predicates, numeric equalities, positive conjunctions,
negative literals, mixed Boolean/numeric guards, disjunction, and primitive-
state safety. This table answers what the method supports; it must not contain
experimental success counts.

### Table 2: Candidate Constructors and Soundness Obligations

Merge the previous schema-grammar and certificate tables into one full-width
table with columns:

```text
Branch constructor | Additional acceptance obligation | Excluded failure
```

Rows cover validated evidence macros, direct producers, acyclic regression,
relational recursion, resource-mode discharge, and cross-module preparation.
The caption states the obligations shared by every branch: typed binding,
symbolic executability and target achievement; the selected set additionally
satisfies internal-call closure.

### Atomic Baseline/Ablation Table

Use short method names (Evidence Only, Direct Producers, Maximum Feasible, and
Full GP2PL) and report paired results for every fixed evidence seed:

```text
compile/rejection status
producible target coverage
internal-call closure
held-out Jason+VAL coverage
branch/context/body counts
ASL bytes
compiler time
```

Use short descriptive column phrases such as `Method`, `Coverage`, `Branches`,
`Library Size`, and `Time (s)`. Keep stable experiment identifiers in the
machine-readable artifact, not as `C0`/`C1`-style table labels.

### Temporal Baseline/Ablation Table

Use short method names (Unprotected Serialization, Certified Flat, Certified
Balanced, and Module-Return Monitor) on the same query/DFA/library hashes:

```text
controller compiled/rejected
Jason success
VAL validity
gold-DFA acceptance
PAR-2 runtime
action count on jointly solved cases
controller plan count
maximum transition-repair trigger fan-out
```

Use the method names above directly. Do not replace them with numbered temporal
variants or compressed one-letter oracle headings.

The main paper uses one compact same-scope table for Raw MOOSE evidence and
Full GP2PL on the identical 740 added-domain seed--case evaluations. Keep
MOOSE, Raw MOOSE extension, LAMA, MRP+HJ, and FOND4LTLf + LAMA in a separate
Technical-Supplement reference table with short columns such as `Method`,
`Source`, `Scope`, `Coverage`, `Unsupported`, and `PAR-2`. Do not mix their
output representations or costs into the compiler ablation table. The
completed hash-locked matrix gives
LAMA 591/868, MRP+HJ 253/360, and FOND4LTLf plus LAMA 298/492 on its supported
subset, with 736 explicitly unsupported temporal inputs. Retain every row in
the Technical Supplement; moving the matrix out of the main paper changes
placement, not the registered comparison protocol.

Generate all three comparison tables with
`scripts/generate_aaai_comparison_tables.py`. Its mandatory inputs are the
complete paired compiler result, the checked MOOSE arXiv-v1 Table-4 reference
artifact, four-domain Raw MOOSE extension summaries explicitly assigned to
seeds 0--4, the native LAMA/MRP+HJ summary, the direct FOND4LTLf summary, and
the challenge summary. The script must fail rather than render a partial table
when a method, seed, case, hash pairing, or source-equivalence condition is
missing. Inputs normally identify clean source commits. A paired long run that
spans commits instead retains every child revision and supplies a SHA-256-bound
experiment-owner confirmation that method-defining code remained equivalent;
the confirmation cannot be reused after any child revision record changes.
The final generator must fail closed over the registered corpus rather than
only compare methods with each other. It recomputes immutable identifier-set
digests for all 1,228 achievement cases, all 1,228 temporal cases, the 868
classical LAMA cases, and the 360 numeric MRP+HJ cases; duplicates and shared
omissions are invalid. It additionally requires the five Raw MOOSE runs to use
the exact 148-case extension scope, seed-specific model-batch manifests, and canonical hashes of every
per-domain model/readable-policy pair consumed by the paired compiler runs,
clean source records or an exact hash-bound method-source equivalence
confirmation, six workers for paired
compiler and Raw MOOSE extension runs, 20 workers for remote LAMA/MRP+HJ and direct
FOND4LTLf runs, the remaining registered resource protocol, pinned external
binaries, and exactly 13 unique successful challenge nodes. A repaired external
summary must additionally prove that its primary matrix retained 20 workers,
its exact infrastructure-only retry used one worker, both revisions were clean,
and hardware-equivalent case runtimes remain comparable. Report a failed
contract as an infrastructure failure, never as a method score.

### TEG Table

### Main Five-Seed Atomic Table

The main paper reports one compact, non-pooled table:

```text
Scope | Cases per seed | Success-count range per seed |
Coverage mean +/- sample standard deviation
```

Rows contain the complete 16-domain corpus, the transparent aggregate of
domains that complete in every seed, and every remaining varying domain
individually. The complete-domain set and varying-domain rows are computed from
the frozen matrix rather than named in the generator. Values are mean $\pm$
sample standard deviation over five independently compiled libraries
($n=5$); the success range preserves the raw minimum and maximum. The Technical
Supplement's domain--seed table preserves the complete within-domain
distribution.

The Technical Supplement contains `result_five_seed_atomic_domain_table.tex`,
with raw Seed 0--4 counts and one combined mean $\pm$ sample-standard-deviation
coverage column. It also contains `result_domain_table.tex`, explicitly
labelled as the fixed seed-0 input table for the separate temporal evaluation.
The latter must never be described as a five-seed robustness result.

### Main Fixed-Core Temporal Summary

Use one compact single-column table with explicit rows:

```text
Validation unit | Valid | Total
Distinct translated specifications | language-equivalent | translated
Bound temporal queries | end-to-end valid | bound queries
```

The caption defines translation validity as exact finite-trace language
equivalence and end-to-end validity as controller compilation, Jason
completion, neutral-goal VAL, and both DFA trace checks. Move the five
per-profile rows and runtime/action distributions to the Technical Supplement.

### Failure and Rejection Reporting

The main paper keeps only the compact five-seed and fixed-core temporal summary
tables. The Technical Supplement and machine-readable artifact preserve all raw
domain--seed, per-profile, and fixed-input values. The supplementary artifact should always
keep translation errors, schema validation
errors, unsupported DFA structure, certificate rejection, Jason failure,
timeout, VAL failure, and DFA-trace rejection as separate statuses. A failed or
timed-out Jason action prefix is diagnostic evidence, not a successful plan.

Main-paper result prose reports scientific aggregates, cross-seed variation,
domain-level concentration of failures, causal interpretation, and the claim
boundary. Do not repeat every seed's raw numerator, timeout/exit status, worker
count, hash, run identifier, or individual case identifier in the main paper.
Those audit facts remain in the Technical Supplement. A concrete failure mode
may remain in the main paper when it explains a method limitation, but express
it at the level of the missing certificate or hypothesis-class boundary rather
than as runner bookkeeping.

### AAAI Figure and Table Style Contract

- Use the official AAAI-27 author kit files `aaai2027.sty` and
  `aaai2027.bst` without locally redefining margins, fonts, caption spacing,
  or bibliography style. The style loads its required fonts; do not add legacy
  `times`, `helvet`, or `courier` packages.
- In manuscript prose, use the Author Kit's normal Times-like roman text for
  ordinary technical terms, including producer, regression, recursion,
  precondition repair, resource discharge, and numeric progress. Write cited
  software-system names such as MOOSE, LTLf2DFA, MONA, Clingo, AgentSpeak(L),
  Jason, and VAL in roman text. Use Courier through `\texttt{}` only for literal
  code, predicate, action, module-signature, path, and artifact identifiers such
  as `clear/1`, `stack(X,Y)`, and `summary.json`. Use
  upright serif mathematical notation for formal named summaries such as
  $\mathrm{MayAdd}$ and conventional operators such as
  $\operatorname{realizes}$; do not use sans-serif math as generic emphasis.
- Retain the Author Kit's required `\usepackage{caption}` declaration; do not
  load packages or define commands that override float placement or caption
  spacing.
- Cite every figure or table in the body before it appears. Figure captions go
  below figures, and table captions go below the tabular content. Use `[htbp]`
  on every figure, table, and algorithm float so LaTeX can keep each visual near
  its first substantive discussion without manual page breaks. Use one
  `\\FloatBarrier` before Conclusion and Future Work so every result table
  remains ahead of the final section and references.
- A caption must define the population/denominator, aggregation over seeds, and
  every abbreviation needed to read the visual independently. State a time
  limit only when it is visually encoded or necessary to interpret coverage;
  exact resource configuration otherwise belongs in the Technical Supplement.
  The body explains interpretation rather than restating every cell.
- Use `booktabs` and no vertical rules or colored table cells. Bold marks a
  genuine tied-best comparable result. Blue bold may identify the selected
  configuration and the structurally motivated metric that distinguishes it,
  but the caption must state that rule and the same distinction must remain in
  bold without color. Do not rank rows drawn from disjoint case sets. Use `--`
  for not applicable and never overload zero. Avoid `\tiny`, `\scriptsize`, and
  `\footnotesize`; final table text must remain at least 9 pt.
- Use vector PDF for PowerPoint method figures with embedded fonts. Set the slide
  canvas to the final aspect ratio, use at least 9 pt text at final printed size, and
  export tightly cropped. Raster content, if unavoidable, must be at least
  250 dpi at final size.
- Use a colorblind-safe palette and redundant shape/line encodings. Figure text
  and mathematical symbols must remain readable in grayscale; never convey a
  certificate or failure state by color alone.
- Conceptual Figures 2--4 and Supplementary Figure S1 may be authored in
  PowerPoint and exported as vector PDF. Any optional diagnostic plot must be
  regenerated by its checked-in script from frozen records and must not be
  promoted to a main-paper result figure.

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
   Conclusion and Future Work, reproducibility checklist, and this outline in
   one coherent change;
7. preserve the supported-fragment and primitive-step observation assumptions even
   if an empirical case happens to pass outside them.
8. retain the zero-action conformance result as a separate semantic boundary;
   do not add a synthetic noop or merge it into the non-empty VAL denominator.
9. generate baseline and ablation values from the checked comparison release;
   do not hand-edit numeric LaTeX cells.

## Submission Readiness

The following result insertions are complete:

1. the frozen five-seed Full GP2PL atomic result: 1,224, 1,219, 1,187,
   1,205, and 1,224 original-goal Jason-plus-VAL successes out of 1,228,
   giving 98.68% mean and 1.29 percentage-point sample standard deviation;
2. the pinned predicted-controller execution result from commit `e28bcea4`:
   1,228/1,228 Jason and neutral-goal VAL successes, with the same 1,228 traces
   accepted independently by both gold and predicted DFAs;
3. 475/475 frozen GPT-5.5 predictions satisfying the JSON contract and exact
   gold/predicted DFA-language equivalence;
4. the five profile totals from that run: 273 ordered-two, 272 ordered-three,
   275 strong-Until, 137 same-state conjunction, and 271 same-state with
   negation;
5. a generated 16-domain table for the exact hashed atomic-library inputs:
   1,568 certified candidates, 1,527 selected branches, and 638.4 KiB of ASL;
6. deterministic LaTeX macros and domain/profile tables generated by the
   conference-neutral `scripts/generate_evaluation_tables.py`, plus the
   five-seed compact record and tables generated by
   `scripts/freeze_five_seed_full_compiler_results.py`; and
7. the Raw MOOSE extension result frozen by
   `scripts/freeze_raw_moose_extension_results.py`: five valid-plan counts of
   26, 23, 23, 25, and 20 over the predeclared 148-case added-domain scope,
   combined in the paper only with the explicitly Reported arXiv-v1 Table-4
   coverage for the disjoint original-domain scope; and
8. the corresponding quantitative Abstract, Introduction, Evaluation,
   failure-boundary explanation, and Conclusion and Future Work text; and
9. the paired ablation release generated by
   `scripts/freeze_paired_ablation_results.py`: 24,560 atomic outcomes and
   4,912 temporal outcomes, with 6,059/6,140 Full GP2PL atomic successes,
   1,227/1,228 Certified Balanced temporal successes, exact adjacent-method
   paired contrasts, corrected transition-repair fan-out, and generated main
   and supplementary tables.

The remaining submission tasks are:

1. full or supplementary proofs for any claim stronger than the current proof
   sketches; and
2. final camera-ready author and artifact metadata. With empirical completeness
   retained before page-budget editing, the current compiled draft places the
   final section and the start of the references on page 14; references continue
   through page 16 and the checklist occupies pages 16--17.

The five-seed compiler artifact records seed 4's
`tracked_source_changes=true` flag instead of relabelling the run clean. The
common sealed input snapshot, exact summary hashes, and byte-identical committed
method-defining source-file set are the eligibility evidence. Timing is not reported because the
runs overlapped unrelated workloads; this qualification does not change the
coverage or independent VAL outcomes.

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
| Related work, conclusion, and future work | 0.5 |

When results are inserted, compress detailed certificate prose into tables and
move long proofs to supplementary material before removing definitions or
failure boundaries. The paper source, this outline, and both normative research
design documents must never disagree about architecture, terminology, or
supported capabilities.
