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
   an AgentSpeak indexing structure with trigger fan-out at most two; it does
   not reorder DFA transitions or add planning semantics. Include a compact
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

### 6. Formal Guarantees

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
   fan-out two, logarithmic nesting depth, linear work per pass, and the same
   certified literal order.
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
  report valid traces and reusable-library amortization relative to raw MOOSE
  and per-instance planning references.

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
the atomic stage of the same clean source revision. The evidence batch supplies
only the MOOSE model and readable policy. This prevents libraries compiled at
different repository revisions from entering a paired temporal comparison.

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
overloaded producers that require different nested precondition-repair branch sets remain
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
present in the paper, appendix, or submitted archive. The current statistical
answer is `yes` because the paper makes no inferential performance-difference
claim from descriptive fixed-release results. The registered paired five-seed
comparison remains a mandatory gate before adding any future improvement or
significance claim; a repository link or additional prose cannot substitute for
that experiment.

## Final Visual Program

During result insertion, empirical completeness takes priority over the
seven-page limit. The main paper uses exactly three planned figures: the
single-column framework overview as Figure 1 on the first page's right column,
the full-width policy-lifting example as Figure 2 at the top of page 2, and the
five-seed empirical result as Figure 3. The main paper contains exactly four
core tables: the supported fragment and rejection boundary, the candidate
constructors and soundness obligations, a compact five-seed atomic summary, and the temporal-profile
summary. The complete domain--seed matrix and fixed seed-0 temporal input table
belong in the Technical Supplement, where they preserve every audit value
without duplicating the headline main-paper views. The detailed DFA-controller
diagram also remains a supplementary asset.

### Figure Production Handoff Contract

Figures 1 and 2 and the planned supplementary DFA diagram are conceptual. Their
labels and examples below come from the implemented architecture, evidence, and
domain schemas, not from estimated experimental measurements. Main Figure 3 is
empirical: its axes may be laid out in
advance, but every data mark must be generated from pinned JSON artifacts. No
colleague or paper-writing agent may infer missing values from prose, terminal
logs, an earlier run, or another method.

Use one normalized coordinate system for all object specifications below:
`x=0,y=0` is the top-left corner; `x`, `y`, `w`, and `h` are percentages of the
complete slide. Snap objects to the specified coordinates within 0.5 percentage
points. Captions are LaTeX text below the imported graphic and must not be drawn
inside the PowerPoint slide.

Canvas, PowerPoint, Python, and export settings:

- Main Figure 1 uses a 6.500 by 4.800 inch PowerPoint export canvas and is
  inserted at 3.25 inches wide. Main Figure 2 uses a 13.333 by 6.000 inch
  PowerPoint export canvas and is inserted at 7.0 inches wide. The supplementary
  DFA figure uses a 13.333 by 5.333 inch PowerPoint canvas. Main Figure 3 is
  generated by Matplotlib at exactly 7.0 by 4.25 inches. Keep a white opaque
  background.
- Use Arial Regular 18 pt for labels and panel headings, and Courier New Regular
  18 pt for domain schemas, AgentSpeak, formulas encoded as text, and artifact
  field names. Do not use bold text inside any figure. These fonts become at
  least 9 pt after scaling to their final AAAI dimensions.
- Use square or 0.06-inch-corner rectangles. Do not use shadows, gradients,
  three-dimensional effects, icons, decorative illustrations, or screenshots.
- Figures 1--2 and the supplementary DFA figure share one editable source deck named
  `latex_code/aamas_method_paper/figures/aaai_method_figures_source.pptx`, with
  exactly one figure per slide. Main Figure 3 is produced by the checked-in
  Matplotlib script, not by PowerPoint.
- Main vector files are `fig1_architecture.pdf`, `fig2_policy_lifting.pdf`, and
  the existing empirical artifact `fig2_evaluation.pdf`, which is inserted as
  Figure 3 through `\gpplfigurethreepath`. The supplementary vector file is
  `figS1_dfa_controller.pdf`; all files live under
  `latex_code/aamas_method_paper/figures/` when delivered.
- Embed fonts in the PDF, crop to the slide boundary, and verify all text at
  `\includegraphics[width=\textwidth]`. Do not rasterize any figure.
- Main Figure 3 uses regular-weight Helvetica throughout, with every panel
  heading, axis label, tick label, domain label, legend, and annotation at least
  9 pt. Do not use bold text inside the data figure. Hide the top and right
  spines and retain only light-gray major grid lines. Use the colorblind-safe
  palette together with redundant marker and line-style encodings; the figure
  must remain decipherable in grayscale, but it is not restricted to grayscale.

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
temporal-goal motivation. In the AAAI two-column layout, this leaves the
abstract and opening domain-compilation motivation in the left column while the
overview occupies the top of the right column without forced placement. Its
final artwork is inserted at
`\columnwidth`; the placeholder reserves 1.40 inches of artwork height before
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

Place this full-width `figure*[t!]` immediately after Figure 1 so it is
eligible for the top of page 2. Use a 7.0 by approximately 3.1 inch canvas with
two adjacent panels separated by one thin rule. Panel (a) occupies 52 percent
and panel (b) 48 percent. This is one continuous Blocks World example, not an
architecture inventory. Body text must remain at least 8 pt at final size, use
regular weight, and remain interpretable in grayscale.

Panel (a), `Reusable lifted-core compilation`, expands operation (1) from
Figure 1:

- Begin with `Domain model D` and `Raw singleton-goal evidence E_raw`. The
  evidence card carries the small provenance tag `external GP backend`; do not
  expand the upstream learner inside the compiler panel.
- Make canonical lifting explicit as `Lift_D(E_0)=E`, including the example
  `on(u,v); stack(u,v) -> on(X,Y); stack(X,Y)` and the guarantees `typed
  variables`, `shared terms preserved`, and `domain constants fixed`.
- Show `Lift typed schemas` and the relevant slice of
  `$T_D(E)=\operatorname{goalPred}(E)\cup\operatorname{prod}(D)$` containing
  `on/2`, `clear/1`, `holding/1`, `arm-empty/0`, and `on-table/1`. Connect the
  `stack` schema to `holding/1` and `clear/1` with the exact label
  `producer preconditions`; do not draw a target-specific closure edge.
- Show candidate rows `C0 already satisfied`, `C1 direct producer`, `C2
  recursive preparation via clear/1`, and gray `C3 longer feasible macro,
  higher cost`. Send them to one `Certify + joint Clingo selection` node with
  `Bind`, `Execute`, `Achieve`, and `Progress` checks.
- Emit one code card headed `Certified lifted atomic core
  $\mathcal M_D=\mathcal L_D^{[0]}$`, containing the already-satisfied, direct
  `stack`, and recursive `!clear(Y); !on(X,Y)` branches plus a `+!clear(Y)`
  excerpt. Do not introduce a selected-set symbol.
- Replace the old set equation with the plain-language closure statement
  `Internally closed: every !goal resolves inside $\mathcal M_D$`. A green
  dashed arrow from `!clear(Y)` to the `+!clear(Y)` excerpt is the concrete
  witness. A small flat Blocks inset may show an obstruction removed before
  placing `X` on `Y`.

Panel (b), `DFA-guided query compilation and append`, expands operation (2):

- Start from the bound query
  `$\widehat\tau_q=F(on(A,B)\land on(B,C)\land on(C,D))$` and binding
  `$\theta_q=\{A\mapsto b_1,B\mapsto b_2,C\mapsto b_3,D\mapsto b_4\}$`, beside
  a flat four-block target stack.
- Show the decoded LTLf2DFA/MONA automaton with `q0`, accepting `qf`, progress
  guard `$\chi=on(b_1,b_2)\land on(b_2,b_3)\land on(b_3,b_4)$`, waiting loop
  `not chi`, and accepting loop `true`.
- Reuse the core's certified completion summaries through a blue dash-dot arrow
  labelled `reuse; no relearning`. Derive the preservation-safe bottom-up order
  `on(b3,b4) -> on(b2,b3) -> on(b1,b2)` from possible delete effects, then show
  its balanced binary repair tree.
- Emit a purple `Query-local controller $\mathcal Q_q$` code card and append it
  to one stacked-document artifact labelled `One maintained domain library`.
  Show the green core layer and purple query layer together with
  `$\mathcal L_D^{[k+1]}=\mathcal L_D^{[k]}\cup\mathcal Q_q$`, `append only; no
  relearning`, and `$\operatorname{Closed}_D(\mathcal L_D^{[k+1]})$`.

Use schema blue, evidence amber, certified-core green, temporal purple, and
omitted-candidate gray. Solid arrows denote transformations, blue dash-dot
arrows completion-summary reuse, green dashed arrows internal module calls, and
purple arrows query append. Circles are reserved for DFA states and a hexagon
for optimization. Do not use gradients, shadows, decorative icons, or color as
the only distinction.

Approved caption:

> Figure 2: Certified lifting and temporal composition in Blocks World. Left:
> GP2PL canonically lifts singleton-goal evidence, instantiates typed
> action-schema candidates, and selects the internally closed atomic core
> $\mathcal M_D=\mathcal L_D^{[0]}$. Right: for a bound LTLf query, GP2PL
> decodes the MONA-derived DFA, derives a preservation-safe order for each
> progress guard, renders the balanced query-local controller $\mathcal Q_q$,
> and appends it to the sole maintained library without relearning the core.

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

### Figure 3: Five-Seed Empirical Evidence

Use a full-width `figure*[htbp]` in the main Evaluation section after the protocol
and metric definitions and before the result subsections. This figure is
generated from artifacts, not manually drawn. The
checked-in plotting script places every point, interval, annotation, and curve;
PowerPoint must not be used to reconstruct the data marks.

The required generator is `scripts/generate_aaai_figures.py`. The submitted
empirical figure uses
`--five-seed-results`, `--validation-run-root`, and `--output-file`. The separate
`--paired-results` mode remains available for the registered compiler and
temporal ablations after that matrix completes; it is not used to fabricate
missing ablation points in the submitted figure. Both modes exit nonzero without
replacing the PDF when a gate fails and write machine-readable diagnostic and
provenance sidecars.

Data-release gate:

- Treat the raw runner aggregate at
  `artifacts/parser_order_full_val_logs/pddl-five-seed-20260713-153900/`
  `five_seed_summary.json` as an index, not as the sole result oracle. Freeze
  its SHA-256 only after its five-seed protocol, child run identifiers,
  evidence-generation status, per-seed domain counts, means, and sample
  standard deviations agree exactly with the independently read child runs.
- Coverage values read exactly one frozen
  `paper_artifacts/gp2pl_evaluation/v1/five_seed_full_compiler_summary.json`.
  Require the Full GP2PL method, seeds 0--4, independent evidence runs, no
  evidence union, no best-seed selection, all 16 domains, and a compiler/runtime
  source-file set whose hash is byte-identical to every formal execution revision.
- Runtime values read only the five child summaries named by that frozen
  artifact. Require each child `summary.json` SHA-256 to match the frozen row,
  the same Full GP2PL settings and Jason worker count, a 1,800-second Jason and
  VAL limit, and a 64-MiB Java stack. A successful case must have Jason success,
  attempted and successful VAL validation, and a `timing_profile.run_seconds`
  value within the Jason deadline.
- Recompute all per-domain and pooled counts from the child records and require
  exact agreement with the frozen artifact. If any input, hash, denominator,
  success oracle, runtime, or compiler source-file hash gate fails, leave the prior PDF
  untouched and persist a diagnostic. Do not render a partial panel.

Use a two-panel asymmetric layout. Panel (a) is wide enough for all 16 domain
labels; panel (b) receives slightly more horizontal space for the logarithmic
time axis. Both panels share one 7.0 by 4.25 inch `figure*` canvas.

- `(a)` is headed `Five-seed held-out coverage`.
- `(b)` is headed `Time-to-valid-trace by benchmark group`.
- Use Helvetica, embedded as TrueType in the PDF, with a 9-pt minimum for every
  visible text element. Plot backgrounds are white; all plot text uses regular
  weight; top and right spines are omitted; and only light gray major grid lines
  remain. Use the colorblind-safe palette with redundant marker and line-style
  encodings so no distinction depends on color alone. Stars are not used: in
  empirical figures they commonly
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
- For every domain, plot all five Full GP2PL seed coverages as small translucent
  blue points. Plot their mean as a filled blue diamond with a horizontal capped
  sample-standard-deviation interval. Annotate only domains with nonzero seed
  variation; the complete numeric table follows in the Technical Supplement.
- Coverage is `100 * valid_trace_count / test_count` from that domain's original
  held-out PDDL achievement tests. A valid trace requires Jason completion and
  VAL acceptance. Do not pool domains before plotting and do not substitute
  producible-predicate target coverage for executable held-out coverage.

Panel (b) specification:

- Do not select visually favorable domains. Aggregate all registered domains by
  the three report groups fixed before plotting: eight classical MOOSE domains,
  four bounded-integer domains, and four serialized-width domains. These groups
  are reporting strata, never backend routes.
- For each group and seed, sort `jason_validation.json` values from
  `timing_profile.run_seconds` for cases that complete in Jason and pass VAL.
  At each time, divide the solved count by every test case in that group; failed
  and timed-out cases stay in the denominator. This follows MOOSE's
  absolute-time cumulative-coverage convention, but the time measure is
  explicitly Jason process execution rather than VAL or concurrent queue time.
- Draw one right-continuous mean curve per group: classical in blue with circle
  markers, numeric in green with square markers, and serialized-width in amber
  with diamond markers. Shade the seed minimum-to-maximum envelope at each time.
  The envelope is descriptive seed variation, not a confidence interval.
- X-axis is `Jason execution time (s, log scale)` from 0.5 to just beyond the
  1,800-second deadline. Y-axis is `VAL-valid cases solved (%)` from 0 to 100.
  Mark 1, 10, 100, and 1,800 seconds on each curve and draw a vertical dashed
  deadline. Do not smooth or interpolate the step curves.
- This panel reports representative coverage and execution scale across the
  complete corpus. It does not establish superiority over MOOSE or another
  planner. Add external-baseline curves only after a hash-paired full matrix is
  available; never insert published numbers from different hardware or splits.

Draft caption:

> **Figure 3: Five-seed held-out execution.** Panel (a) gives per-domain
> Jason-plus-VAL coverage for five independently seeded MOOSE
> evidence runs; points are seeds and diamonds with bars show mean plus or minus
> sample standard deviation. Panel (b) gives mean cumulative VAL-valid coverage
> over Jason execution time for three predeclared benchmark families; bands span
> the seed minimum and maximum. Failures remain in the denominator and the dashed
> line marks the per-instance time limit.

Before delivery, verify the figure totals against the corresponding generated
LaTeX tables. The figure and table must name the same run IDs and input hashes.
No one may copy values from a PDF table back into the plot source.

### Figure Delivery and LaTeX Insertion Contract

The colleague may deliver the editable method deck and planned conceptual
figures separately. The plotting script delivers the current empirical figure.
Its `fig2_evaluation.metadata.json` records the frozen five-seed result, the
verified source-runner aggregate hash, five hash-locked child summaries,
compiler source-file hash, dimensions, and plotting contract. If the planned conceptual
assets are delivered, assemble the
multi-asset `aaai_figure_manifest.json` only after recording their dimensions,
data sources, and embedded fonts. Any font substitution is a release blocker.
The plotting script, not the colleague, owns the empirical figure's numeric
data.

Use these exact LaTeX placements and labels. Figures 1 and 2 retain visible
placeholders until their colleague-produced vector PDFs are delivered:

```latex
\begin{figure}[htbp]
  \centering
  \IfFileExists{\gpplfigureonepath}{
    \includegraphics[width=\columnwidth]{\gpplfigureonepath}
  }{<single-column placeholder>}
  \caption{<approved Figure 1 caption from this outline>}
  \label{fig:architecture}
\end{figure}

\begin{figure*}[htbp]
  \centering
  \IfFileExists{\gpplfiguretwopath}{
    \includegraphics[width=\textwidth]{\gpplfiguretwopath}
  }{<full-width placeholder>}
  \caption{<approved Figure 2 caption from this outline>}
  \label{fig:policy-lifting-example}
\end{figure*}

\begin{figure*}[htbp]
  \centering
  \includegraphics[width=\textwidth]{\gpplfigurethreepath}
  \caption{<approved Figure 3 caption from this outline>}
  \label{fig:evaluation-summary}
\end{figure*}
```

The main Evaluation source contains the Figure 3 `figure*[htbp]` placement before
its result subsections. Until the frozen five-seed
result and every child hash pass the plotting gate, `\IfFileExists` omits the
figure and emits a package warning; no synthetic or partial empirical graphic
is allowed to enter the review PDF. A layout-only preview may override
`\gpplfigurethreepath` in an untracked build, but it is never a paper artifact.

The current main paper inserts the existing `fig2_evaluation.pdf` empirical
artifact through the Figure 3 macro. Figures 1 and 2 deliberately show layout
placeholders until the final conceptual vector assets are delivered and
validated; the supplementary DFA asset remains optional until delivery.

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
maximum trigger fan-out
```

Use the method names above directly. Do not replace them with numbered temporal
variants or compressed one-letter oracle headings.

Keep MOOSE, Raw MOOSE extension, LAMA, MRP+HJ, and FOND4LTLf + LAMA in a
separate external reference table with short columns such as `Method`, `Source`,
`Scope`, `Coverage`, `Unsupported`, and `PAR-2`. Do not mix their output representations or
costs into the compiler ablation table. Do not spend main-paper space on an
all-empty external-reference table. The completed hash-locked matrix now gives
LAMA 591/868, MRP+HJ 253/360, and FOND4LTLf plus LAMA 298/492 on its supported
subset, with 736 explicitly unsupported temporal inputs. Keep this completed
external table in the main Evaluation section while
the manuscript is still in evidence-completeness mode; page-budget compression
is a later editorial decision and must not silently remove a comparison row.

Generate all three comparison tables with
`scripts/generate_aaai_comparison_tables.py`. Its mandatory inputs are the
complete paired compiler result, the checked MOOSE arXiv-v1 Table-4 reference
artifact, four-domain Raw MOOSE extension summaries explicitly assigned to
seeds 0--4, the native LAMA/MRP+HJ summary, the direct FOND4LTLf summary, and
the challenge summary. The script must fail rather than render a partial table
when a method, seed, case, hash pairing, or clean-source condition is missing.
Each input must identify a clean source commit, while commits may differ across
independently executed experiment groups.
The final generator must fail closed over the registered corpus rather than
only compare methods with each other. It recomputes immutable identifier-set
digests for all 1,228 achievement cases, all 1,228 temporal cases, the 868
classical LAMA cases, and the 360 numeric MRP+HJ cases; duplicates and shared
omissions are invalid. It additionally requires the five Raw MOOSE runs to use
the exact 148-case extension scope, seed-specific model-batch manifests, and canonical hashes of every
per-domain model/readable-policy pair consumed by the paired compiler runs, one
clean source commit for every derived result summary, six workers for paired
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
($n=5$); the success range preserves the raw minimum and maximum. Figure 3
retains all five per-domain seed points, so the compact table does not hide the
within-domain distribution.

The Technical Supplement contains `result_five_seed_atomic_domain_table.tex`,
with raw Seed 0--4 counts and one combined mean $\pm$ sample-standard-deviation
coverage column. It also contains `result_domain_table.tex`, explicitly
labelled as the fixed seed-0 input table for the separate temporal evaluation.
The latter must never be described as a five-seed robustness result.

### Main Temporal Profile Table

Use one compact single-column table with explicit columns:

```text
Profile | DFA-equivalent translations / total | End-to-end valid / bound queries |
Median actions | Median seconds
```

Add an `All` row computed from the aggregate machine record. The caption defines
end-to-end validity as controller compilation, Jason completion, neutral-goal
VAL, and both DFA trace checks. Per-profile and all-query runtime/action values
remain medians; they must not be converted to mean $\pm$ standard deviation.

### Failure and Rejection Reporting

The main paper keeps only the compact five-seed and temporal-profile empirical
tables. The Technical Supplement and machine-readable artifact preserve all raw
domain--seed and fixed-input values. The supplementary artifact should always
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
  its first substantive discussion without manual page breaks or float-queue
  overrides.
- A caption must define the population/denominator, aggregation over seeds, and
  every abbreviation needed to read the visual independently. State a time
  limit only when it is visually encoded or necessary to interpret coverage;
  exact resource configuration otherwise belongs in the Technical Supplement.
  The body explains interpretation rather than restating every cell.
- Use `booktabs`, no vertical rules, no colored table cells, and bold only for a
  genuine best comparable result. Use `--` for not applicable and never overload
  zero. Avoid `\tiny`, `\scriptsize`, and `\footnotesize`; final table text must
  remain at least 9 pt.
- Use vector PDF for PowerPoint method figures with embedded fonts. Set the slide
  canvas to the final aspect ratio, use at least 9 pt text at final printed size, and
  export tightly cropped. Raster content, if unavoidable, must be at least
  250 dpi at final size.
- Use a colorblind-safe palette and redundant shape/line encodings. Figure text
  and mathematical symbols must remain readable in grayscale; never convey a
  certificate or failure state by color alone.
- The final empirical figure must be regenerated by a checked-in script from
  one frozen five-seed result and its hash-locked child summaries. PowerPoint is
  acceptable for main Figures 1--2 and Supplementary Figure S1, but not for
  manually placing result points in main Figure 3.

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
   failure-boundary explanation, and Conclusion text.

The remaining submission tasks are:

1. completed registered atomic and temporal ablation runs, plus the remaining
   LAMA, ENHSP MRP+HJ, and FOND4LTLf references, with result tables inserted
   only from their machine-readable summaries;
2. full or supplementary proofs for any claim stronger than the current proof
   sketches; and
3. final camera-ready author and artifact metadata. The current compiled draft
   places all technical content, including the Conclusion, within pages 1--7;
   references begin on page 8 and the checklist follows on pages 9--10.

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
| Related work, limitations, conclusion | 0.5 |

When results are inserted, compress detailed certificate prose into tables and
move long proofs to supplementary material before removing definitions or
failure boundaries. The paper source, this outline, and both normative research
design documents must never disagree about architecture, terminology, or
supported capabilities.
