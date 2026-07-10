# Parametric Natural-Language LTLf Input and Evaluation Design

## Status and Scope

This document is the normative pre-paper design for the Input component and
the temporally extended goal evaluation path. It specifies how a PDDL world is
turned into a natural-language query benchmark, how a language model translates
that query into a typed lifted LTLf template, how the template is compiled by
the real `ltlf2dfa` and MONA toolchain, and how a Jason action trace is validated
against the intended temporal goal.

The required semantics are **typed, externally bound, parametric LTLf**. A
template such as `phi(X,Y)` is compiled once and can be invoked with any
type-correct assignment such as `X=b1, Y=b2`. It does not mean either
`exists X,Y. phi(X,Y)` or `forall X,Y. phi(X,Y)`. Existential binding search and
universal quantification are different first-order temporal-logic problems and
are outside the current claim.

The document uses the following requirement terms:

- **MUST** is required for a paper result to count as valid.
- **MUST NOT** marks a semantic or methodological error.
- **SHOULD** is the default unless an experiment explicitly justifies a
  deviation.
- **MAY** describes an optional extension that does not change the core claim.

## Canonical End-to-End Contract

The complete path has four modules and two independently evaluated concerns:

```text
PDDL domain + training split
-> Evidence Module
-> Validated Policy-Lifting Compiler
-> one maintained atomic AgentSpeak(L) library per domain

natural-language parametric query
-> Input Component
-> typed lifted LTLf template
-> real ltlf2dfa/MONA DFA
-> Temporal Query Compiler
-> query-local parametric AgentSpeak(L) wrapper
-> Jason committed primitive-action trace
-> PDDL action validation + independent DFA trace acceptance
```

The Input Component translates user intent. The Validated Policy-Lifting
Compiler produces the reusable atomic library. The Temporal Query Compiler
connects a query DFA to that library. The Execution Validation Module validates
the resulting trace. These responsibilities MUST remain separate so that an
input-translation failure is not reported as an atomic-library failure.

## Formal Model

### PDDL Evaluation World

A source PDDL problem is written as:

```text
I = <D, O, s0, g_classical>
```

where `D` is the PDDL domain schema, `O` is the finite typed object set, `s0`
is the initial state, and `g_classical` is the original achievement goal. A TEG
evaluation world reuses `D`, `O`, and `s0` but does not use `g_classical` as the
temporal success oracle:

```text
I_phi = <D, O, s0, T, theta>
```

`T` is a lifted temporal template and `theta` is one externally supplied typed
assignment. The original goal remains provenance metadata and MAY be evaluated
as an additional classical condition, but it MUST NOT be silently conjoined
with the user query.

### Lifted Temporal Template

A lifted temporal template is:

```text
T = <V, tau, C, phi, eta>
```

- `V` is a finite ordered set of parameters, for example `{X,Y}`.
- `tau` maps each parameter to a declared PDDL type, for example
  `tau(X)=block`.
- `C` is a conjunction of parameter constraints such as `X != Y`.
- `phi` is an LTLf formula over proposition identifiers.
- `eta` maps each proposition identifier to one lifted PDDL state condition.

Example:

```text
V   = {X,Y}
tau = {X:block, Y:block}
C   = {X != Y}
eta(ap_0001) = clear(Y)
eta(ap_0002) = on(X,Y)
phi = F(ap_0001 & X(F(ap_0002)))
```

The temporal `X` operator and the query parameter `X` are distinct syntactic
categories. Structured JSON MUST preserve that distinction; implementations
MUST NOT infer it from untyped string replacement.

### Runtime Assignment

For a problem instance `I`, an assignment is:

```text
theta : V -> O
```

It MUST bind every parameter exactly once, preserve PDDL typing, and satisfy
all constraints in `C`. For example:

```text
theta = {X -> b1, Y -> b2}
```

The grounded validation projection is obtained by capture-avoiding
substitution:

```text
phi_theta = phi[eta(ap) := eta(ap)theta]
```

For the example, this is:

```text
F(clear(b2) & X(F(on(b1,b2))))
```

`phi_theta` is called the **gold grounded LTLf** for that invocation. It is an
evaluation oracle only. The maintained query artifact remains lifted, and the
same DFA topology and wrapper template MUST be reusable under other valid
assignments.

## Normative Artifacts and JSON Schemas

The implementation MUST keep templates and invocations separate. The existing
schema version 1 combines a formula and per-case bindings; the Input
implementation MUST introduce schema version 2 with the contracts below.
Schema version 1 may remain as a legacy reader, but it MUST NOT be used for the
paper's parametric-query evaluation artifacts.

All displayed top-level fields are required unless explicitly described as
optional. Parsers MUST reject unknown executable fields; implementations may
reserve one optional `metadata` object for non-semantic provenance. Identifiers
use these canonical forms:

```text
query_id, template_id, invocation_id: [a-z][a-z0-9_]*
parameter:                           [A-Z][A-Za-z0-9_]*
atom_id:                             a[0-9]+
MONA proposition:                    ap_[0-9]{4,}
ASL query goal:                      g_[a-z][A-Za-z0-9_]*
```

JSON Schema implementations SHOULD set `additionalProperties: false` for all
semantic objects. Arrays whose order contributes to canonical hashing, such as
variables, atoms, formula operands, states, and transitions, MUST use the order
specified by this document rather than object-map iteration order.

### 1. Natural-Language Query Record

This is the benchmark input seen by the language model:

```json
{
  "schema_version": 2,
  "artifact_kind": "parametric_temporal_query_text",
  "query_id": "blocks_clear_then_on_001",
  "domain": "blocksworld-on",
  "source_text": "Given distinct blocks X and Y, make Y clear and later place X on Y.",
  "declared_parameters": [
    {"name": "X", "pddl_type": "block"},
    {"name": "Y", "pddl_type": "block"}
  ],
  "parameter_semantics": "externally_bound",
  "source_provenance": {
    "author_kind": "human_paraphrase",
    "generator_model": null,
    "human_reviewed": true
  }
}
```

Parameter names MUST match `[A-Z][A-Za-z0-9_]*`. The wording SHOULD use
"given parameters" rather than "for every" or "there exists". A free-form
query with ambiguous quantification MUST be rejected or sent for clarification.

### 2. Language-Model Input Envelope

The model MUST receive only information needed to ground the language into the
declared PDDL vocabulary:

```json
{
  "schema_version": 2,
  "task": "natural_language_to_parametric_ltlf",
  "logic_profile": "typed_parametric_ltlf_v1",
  "domain": {
    "name": "blocksworld-on",
    "predicates": [
      {
        "name": "clear",
        "parameters": [{"position": 0, "pddl_type": "block"}],
        "role": "producible_dynamic_fluent"
      },
      {
        "name": "on",
        "parameters": [
          {"position": 0, "pddl_type": "block"},
          {"position": 1, "pddl_type": "block"}
        ],
        "role": "producible_dynamic_fluent"
      }
    ],
    "numeric_functions": []
  },
  "query": {
    "query_id": "blocks_clear_then_on_001",
    "source_text": "Given distinct blocks X and Y, make Y clear and later place X on Y.",
    "declared_parameters": [
      {"name": "X", "pddl_type": "block"},
      {"name": "Y", "pddl_type": "block"}
    ]
  },
  "output_contract": "parametric_lifted_ltlf_template_v2"
}
```

Predicate roles MUST be derived from PDDL effects. Domain-specific prose MAY
be supplied for language grounding, but the executable compiler MUST NOT use
that prose as a replacement for predicate, arity, or type validation.

### 3. Language-Model Output: Lifted LTLf Template

The language model MUST return JSON only. Formula structure MUST be represented
as an abstract syntax tree; formula text is derived by deterministic rendering
and is not independently trusted.

```json
{
  "schema_version": 2,
  "artifact_kind": "parametric_lifted_ltlf_template",
  "goal_specification_kind": "temporal_extended_goal",
  "temporal_logic": "LTLf",
  "logic_profile": "typed_parametric_ltlf_v1",
  "query_id": "blocks_clear_then_on_001",
  "domain": "blocksworld-on",
  "parameter_semantics": "externally_bound",
  "variables": [
    {"name": "X", "pddl_type": "block"},
    {"name": "Y", "pddl_type": "block"}
  ],
  "constraints": [
    {"operator": "not_equal", "left": "X", "right": "Y"}
  ],
  "atoms": [
    {
      "atom_id": "a0",
      "kind": "predicate",
      "predicate": "clear",
      "arguments": ["Y"]
    },
    {
      "atom_id": "a1",
      "kind": "predicate",
      "predicate": "on",
      "arguments": ["X", "Y"]
    }
  ],
  "formula_ast": {
    "operator": "eventually",
    "operand": {
      "operator": "and",
      "operands": [
        {"operator": "atom", "atom_id": "a0"},
        {
          "operator": "next",
          "operand": {
            "operator": "eventually",
            "operand": {"operator": "atom", "atom_id": "a1"}
          }
        }
      ]
    }
  }
}
```

The formula grammar is:

```text
phi ::= true
      | false
      | atom(atom_id)
      | not(phi)
      | and(phi_1, ..., phi_n)       where n >= 2
      | next(phi)
      | eventually(phi)
      | always(phi)
      | until(phi, phi)
      | release(phi, phi)
```

Explicit `or` and implication are excluded from the version 1 model-output
grammar. This restriction does not imply that MONA transition guards will be
free of disjunction. Automaton minimization can introduce arbitrary Boolean
guards, which the DFA capability checker must handle or reject explicitly.

The Input validator MUST enforce all of the following:

- every variable is declared exactly once;
- every formula atom identifier exists exactly once;
- every atom uses a PDDL-declared predicate or supported numeric function;
- predicate arity and argument types match the PDDL declaration;
- constants, when allowed, are declared PDDL constants rather than invented
  object names;
- static predicates are not silently treated as achievement subgoals;
- all variables used by atoms are declared template parameters;
- constraints are type-compatible and refer to declared terms;
- the formula abstract syntax tree is acyclic, finite, and follows the grammar;
- no natural-language text is copied into executable predicate identifiers;
- malformed or unsupported output is rejected without heuristic repair.

Rejection MUST be represented separately from a template and MUST identify the
stage and a stable error code:

```json
{
  "schema_version": 1,
  "artifact_kind": "temporal_input_diagnostic",
  "query_id": "blocks_clear_then_on_001",
  "status": "rejected",
  "stage": "pddl_vocabulary_validation",
  "error_code": "predicate_arity_mismatch",
  "message": "Predicate on expects arity 2 but atom a1 supplied arity 1.",
  "details": {"atom_id": "a1", "expected_arity": 2, "actual_arity": 1}
}
```

The implementation MUST NOT store a partially repaired formula as if it were
the model output. Any optional retry is a new attempt with its own provenance.

### 4. Numeric Atom Schema

Numeric comparisons are first-class state conditions:

```json
{
  "atom_id": "a2",
  "kind": "numeric_comparison",
  "function": "capacity",
  "arguments": ["V"],
  "comparator": "=",
  "value": 0
}
```

Version 1 supports one declared numeric fluent compared with one integer
constant. Arbitrary arithmetic, real-valued tolerances, function-to-function
comparison, and optimization metrics MUST be rejected unless their semantics
are separately specified.

### 5. Runtime Invocation

Bindings belong to an invocation, not to the lifted template:

```json
{
  "schema_version": 2,
  "artifact_kind": "parametric_temporal_query_invocation",
  "invocation_id": "blocks_p01_clear_then_on_b1_b2",
  "template_id": "blocks_clear_then_on_001",
  "domain": "blocksworld-on",
  "problem_file": "src/domains/blocksworld-on/test/p01.pddl",
  "assignment": {"X": "b1", "Y": "b2"},
  "trace_scope": "query_invocation_to_top_level_completion",
  "original_pddl_goal_role": "provenance_only"
}
```

The invocation validator MUST check total binding, object declaration, PDDL
type membership, constants, and parameter constraints before Jason execution.

### 6. Proposition Map

`ltlf2dfa` and MONA operate over propositional symbols. The propositionizer
MUST replace lifted atoms with safe opaque identifiers and persist a reversible
map:

```json
{
  "schema_version": 1,
  "artifact_kind": "lifted_proposition_map",
  "template_id": "blocks_clear_then_on_001",
  "propositions": [
    {
      "proposition": "ap_0001",
      "atom_id": "a0",
      "atom": {"kind": "predicate", "predicate": "clear", "arguments": ["Y"]}
    },
    {
      "proposition": "ap_0002",
      "atom_id": "a1",
      "atom": {"kind": "predicate", "predicate": "on", "arguments": ["X", "Y"]}
    }
  ],
  "propositional_formula": "F(ap_0001 & X(F(ap_0002)))"
}
```

Identifiers MUST be assigned deterministically by first abstract-syntax-tree
occurrence after atom deduplication. Predicate names, commas, parentheses,
PDDL hyphens, objects, and variables MUST NOT be passed directly as MONA
proposition identifiers.

### 7. DFA Artifact

The real tool output MUST be normalized without inventing transitions:

```json
{
  "schema_version": 1,
  "artifact_kind": "ltlf_dfa",
  "template_id": "blocks_clear_then_on_001",
  "formula_sha256": "...",
  "proposition_map_sha256": "...",
  "construction": {
    "library": "ltlf2dfa",
    "library_version": "recorded-at-runtime",
    "backend": "MONA",
    "mona_version": "recorded-at-runtime",
    "mona_binary_sha256": "...",
    "timeout_seconds": 60
  },
  "states": ["q0", "q1", "q2"],
  "initial_state": "q0",
  "accepting_states": ["q2"],
  "transitions": [
    {
      "source_state": "q0",
      "target_state": "q1",
      "raw_guard": "ap_0001",
      "guard_ast": {"operator": "atom", "proposition": "ap_0001"}
    }
  ],
  "statistics": {
    "formula_node_count": 5,
    "proposition_count": 2,
    "state_count": 3,
    "transition_count": 5,
    "construction_seconds": 0.12
  }
}
```

The normalized artifact MUST pass:

- every state and accepting state is declared;
- every transition endpoint is declared;
- every guard references only proposition-map identifiers;
- outgoing guards are mutually exclusive for each source state;
- outgoing guards are exhaustive or an explicit rejecting sink is present;
- the initial state is unique;
- the artifact is deterministic;
- accepting-state semantics are preserved exactly;
- raw tool output is retained as an audit artifact.

For small proposition sets, exclusivity and exhaustiveness MAY be checked by
enumerating valuations. For larger sets, they SHOULD be checked by a Boolean
solver rather than enumerating `2^|AP|` valuations.

### Current Temporal Query Compiler Capability Gate

A valid DFA is not automatically executable by the current AgentSpeak(L)
controller. The current paper-facing compiler accepts only DFAs for which it
can certify all of the following:

- there is one unique progress path from the initial state to an accepting
  state after non-progress waiting edges are excluded;
- every progress edge on that path is emitted as exactly one query-local
  `trans` helper;
- accepting `true` self-loops are treated as automaton plumbing rather than
  achievement subgoals;
- each selected transition guard normalizes to one conjunction of positive and
  negative state literals, with no alternative disjunctive guard branch;
- every positive predicate literal has a compatible atomic achievement module;
- negative literals are context checks and are never compiled as negative
  achievements;
- conjunctive positive literals have a complete typed may-delete summary and an
  acyclic certificate-backed serialization;
- numeric conjunctions have the required effect-preservation certificate.

A singleton positive transition is compiled as one atomic subgoal followed by
guard rechecking, which is action-equivalent to the former linear call. A DFA
with branching progress choices, a cyclic threat graph, an incomplete effect
summary, or unsupported negative achievement MUST return
`unsupported_controller_topology`. It MUST NOT fall back to parser order, a
hand-written linear sequence, or synthetic DFA-state beliefs.

### 8. Validation Record

Every formal result MUST preserve separate oracles:

```json
{
  "schema_version": 1,
  "artifact_kind": "temporal_execution_validation",
  "invocation_id": "blocks_p01_clear_then_on_b1_b2",
  "jason_success": true,
  "committed_action_count": 8,
  "pddl_action_trace_valid": true,
  "predicted_dfa_accepting": true,
  "gold_dfa_accepting": true,
  "predicted_gold_language_equivalent": true,
  "original_pddl_goal_satisfied": null,
  "end_to_end_intent_success": true,
  "failure_stage": null,
  "artifact_paths": {
    "committed_plan": "...",
    "state_trace": "...",
    "dfa_run": "...",
    "val_output": "..."
  }
}
```

`end_to_end_intent_success` is true only when the committed trace is PDDL-valid
and the **gold** DFA accepts it. Acceptance by the model's own predicted DFA is
not sufficient.

## Constructing Natural-Language TEG Queries from PDDL

### Do Not Rewrite Every Original Goal

The current achievement benchmark remains a separate full-test evaluation.
Mechanical conversion of every original goal to `F(g1 & ... & gn)` does not
test temporal expressiveness. The TEG benchmark SHOULD reuse all feasible test
problems as initial-state environments, while reusing a smaller set of lifted
query templates across many instances and assignments.

The desired structure is:

```text
one lifted query template
-> many held-out PDDL instances
-> multiple deterministic typed assignments per instance
```

It is not:

```text
one original PDDL final goal
-> one unique instance-specific LTLf sentence
```

### Schema-Derived Atom Catalogue

For each PDDL domain, the benchmark builder MUST classify state symbols from
the action schemas:

- `producible_dynamic_fluent`: appears in a positive add effect;
- `deletable_dynamic_fluent`: appears in a delete effect;
- `static_context`: appears in state descriptions but no add/delete effect;
- `numeric_state_function`: declared PDDL function with supported state
  semantics.

Positive achievement milestones MUST use producible dynamic fluents or
supported numeric targets. Static predicates MAY constrain bindings or describe
the world but SHOULD NOT be used as nontrivial temporal achievements.

### Independent Witness Traces

The benchmark MUST NOT use the evaluated ASL library to certify its own query
set. An independent classical planner, product-automaton planner, or manually
verified source trace MUST supply witness traces. From a valid trace:

```text
s0 --a0--> s1 --a1--> ... --a(n-1)--> sn
```

the builder identifies change events such as an atom becoming true, becoming
false, or a numeric comparison crossing its threshold. Formula patterns are
then instantiated only when the trace contains the required milestones.

Every supported positive case MUST have at least one PDDL-valid witness trace.
Every formal pattern MUST also have at least one PDDL-valid negative trace that
the gold DFA rejects. Whenever domain dynamics permit, positive and negative
traces SHOULD end with the same query-atom valuation but differ in temporal
order. Such a pair proves that a final-state conjunction cannot distinguish the
case.

### Required Lifted Formula Families

The benchmark SHOULD cover the following structural families without naming
specific domain predicates in the generation algorithm:

| Family | Lifted shape | Capability tested |
| --- | --- | --- |
| Eventual singleton | `F(A(X))` | Basic parametric achievement |
| Binary relation | `F(R(X,Y))` | Typed multi-argument binding |
| Later achievement | `F(A(X) & X(F(B(X))))` | Shared parameter over time |
| Dependency chain | `F(R(X,Y) & X(F(R(Y,Z))))` | Cross-position variable reuse |
| Same-state conjunction | `F(A(X) & B(Y))` | One conjunctive DFA guard |
| Ordered conjunction blocks | `F((A(X)&B(Y)) & X(F(C(X)&D(Y))))` | Multiple guard transitions |
| Negative state guard | `F(A(X) & not B(X))` | Negative context semantics |
| Strict precedence | `(not B(X)) U (A(X) & not B(X) & X(F(B(X))))` | No premature B occurrence |
| Repeated condition | `F(A(X) & X(F(not A(X) & X(F(A(X))))))` | Non-monotone temporal state |
| Numeric milestone | `F(N(V)=k)` | Parameterized numeric labeling |

The natural-language phrase "A and later B" corresponds to
`F(A & X(F B))`; it does not forbid an earlier B. The phrase "B only after A"
requires a precedence formula. Annotation guidelines MUST preserve this
distinction.

### Realizable and Challenge Partitions

Benchmark records MUST be partitioned before evaluation:

- `supported_realizable`: independently witnessed and within the current
  controller contract;
- `supported_unrealizable`: well-formed but no witness under the bounded
  evaluation procedure, reported separately rather than as ordinary timeouts;
- `unsupported_logic`: outside the declared input grammar;
- `unsupported_controller_topology`: valid LTLf but its DFA requires branching,
  cyclic protection, negative achievement, or another controller capability
  that is not implemented;
- `invalid_grounding`: undeclared symbols, wrong arity/type, incomplete
  assignment, or violated parameter constraint.

Fail-closed behavior is part of evaluation. Unsupported cases MUST NOT be
silently approximated by a linear sequence.

## Natural-Language Generation and Annotation

### Formula-First Production

Gold data SHOULD be produced in this order:

```text
verified lifted formula pattern
-> typed PDDL atom instantiation
-> independent positive/negative trace checks
-> canonical controlled English
-> diverse paraphrases
-> independent semantic adjudication
```

An LLM MAY generate candidate natural-language paraphrases, but formal test
queries MUST be human reviewed. The generation model and evaluated translation
model MUST be recorded. A test set produced and translated by the same model
family MUST be reported as potentially circular and cannot be the sole language
evaluation.

### Annotation Protocol

For each gold template:

1. A formal annotator selects or verifies the lifted LTLf pattern.
2. A language annotator writes or reviews canonical English without changing
   parameter identity or temporal strength.
3. At least one independent annotator maps the paraphrase back to a formal
   pattern without seeing the original formula.
4. The two formulas are checked for alpha-equivalence and DFA language
   equivalence.
5. Disagreements are adjudicated; ambiguous queries are removed or explicitly
   marked ambiguous.

The final test set SHOULD include both reviewed LLM paraphrases and a smaller
free-form human-authored challenge set.

### Data Splits

Random sentence splitting is invalid because paraphrases of the same formula
would leak across train and test. The dataset SHOULD report:

- utterance holdout: unseen paraphrases of known formula structures;
- formula-skeleton holdout: unseen temporal compositions;
- assignment holdout: unseen object bindings;
- problem-size holdout: larger held-out PDDL instances;
- domain holdout: unseen predicate vocabularies and PDDL domains;
- composition-length holdout: longer milestone chains than demonstrations.

Lang2LTL evaluates lifted language and environment grounding separately, while
VLTL-Bench separates lifting, grounding, translation, and trace verification.
This benchmark follows the same methodological separation but uses finite-trace
PDDL state semantics.

## LTLf Propositionalization and DFA Construction

### Lifted Propositionalization

The propositionizer compiles the formula structure, not the object universe.
For a lifted template with `m` distinct atoms, MONA sees exactly `m`
propositions regardless of whether an invocation problem contains 5 or 50,000
objects.

Correct:

```text
clear(Y) -> ap_0001
on(X,Y)  -> ap_0002
F(ap_0001 & X(F(ap_0002)))
```

Incorrect:

```text
clear(b1), clear(b2), ..., clear(b50000)
on(b1,b1), on(b1,b2), ...
```

The incorrect expansion changes parametric semantics into universal or
existential grounding and creates object-count-dependent automata. It MUST NOT
be used for externally bound templates.

### State-Explosion Risk

Lifted compilation prevents object-count explosion, but it does not remove
automata-theoretic worst cases. DFA size can grow sharply with:

- formula abstract-syntax-tree size;
- number of distinct proposition identifiers;
- temporal nesting depth;
- interacting `until`, `release`, `always`, and negation operators;
- determinization and minimization complexity.

The tool invocation MUST run with recorded wall-time and memory limits. It MUST
record formula size, proposition count, state count, transition count, tool
versions, and raw logs. Required structured failures are:

```text
ltlf_formula_invalid
ltlf2dfa_timeout
ltlf2dfa_memory_limit
mona_process_error
dfa_state_limit_exceeded
dfa_transition_limit_exceeded
dfa_guard_parse_error
dfa_not_deterministic
dfa_not_complete
unsupported_controller_topology
```

No failure may trigger a hand-written ordered-sequence DFA, parser-order
wrapper, or formula simplification that changes semantics. A canonical formula
hash SHOULD cache successful DFA artifacts.

### Restoring Lifted Atoms

MONA transition guards reference only `ap_XXXX`. The Temporal Query Compiler
restores each proposition through the persisted map, not string guessing:

```text
ap_0001 -> clear(Y)
ap_0002 -> on(X,Y)
```

The generated parametric ASL shape is expected to preserve parameters:

```asl
blocks_clear_then_on.

+!g_blocks_clear_then_on(X, Y) :
	blocks_clear_then_on & obj_tp(X, block) & obj_tp(Y, block) & X \== Y <-
	!g_blocks_clear_then_on_trans_1(X, Y);
	!g_blocks_clear_then_on_trans_2(X, Y).
```

Every query-local transition helper MUST receive the variables required by its
guard and recursive calls. One maintained domain library may contain many query
templates, but every template remains parametric and is invoked with concrete
arguments only at runtime.

## DFA-Based Goal Validation

### State-Trace Semantics

Let the committed primitive-action trace be:

```text
pi = <a0, a1, ..., a(n-1)>
```

Independent PDDL replay from the invocation state produces:

```text
sigma = <s0, s1, ..., sn>
```

For assignment `theta`, the lifted proposition labeling is:

```text
L_theta(si) = { ap in AP | si satisfies eta(ap)theta }
```

Numeric propositions are evaluated from the numeric values in `si`. Negative
guards are evaluated by absence or comparison failure under the supported PDDL
closed-world state semantics; they are not negative achievement actions.

For DFA:

```text
A_phi = <Q, 2^AP, delta, q0, F>
```

the unique run is:

```text
r0 = q0
r(i+1) = delta(ri, L_theta(si))     for 0 <= i <= n
```

The trace is accepted exactly when:

```text
r(n+1) in F
```

Visiting an accepting state earlier is not sufficient unless the trace ends
there. The evaluation trace begins at query invocation and ends when the
top-level query intention commits success. Failed action prefixes and abandoned
intentions are diagnostics and MUST NOT be submitted as successful traces.

### Independent Oracles

Evaluation MUST distinguish:

1. `predicted_dfa_accepting`: the trace satisfies the model-produced formula;
2. `gold_dfa_accepting`: the trace satisfies the human-audited intended formula;
3. `predicted_gold_language_equivalent`: the predicted and gold formulas accept
   the same finite traces.

End-to-end intent success requires PDDL action legality and gold-DFA acceptance.
A model can perfectly execute an incorrectly translated formula, so its own DFA
is not an independent intent oracle.

Formula equivalence SHOULD be checked by constructing complete deterministic
DFAs, taking their symmetric-difference product, and testing whether an
accepting product state is reachable. String equality is insufficient because
formulas such as `F(A & B)` and `F(B & A)` are semantically equivalent.
Before the product is built, predicted and gold parameters and proposition maps
MUST be canonicalized under a type-preserving alpha-renaming. Renaming
`X,Y` to `A,B` is harmless; swapping predicate argument roles is not.

### PDDL and VAL

VAL or an equivalent standards-based validator checks primitive action legality
and, when requested, a classical final goal. It does not validate arbitrary
external LTLf. TEG evaluation therefore reports:

```text
PDDL action trace validity
AND gold DFA finite-trace acceptance
```

A validation-only problem MAY reuse the original domain, objects, and initial
state with a tautological classical goal when the installed VAL version accepts
that syntax. Otherwise independent PDDL replay is the primary action-legality
oracle and VAL is used as an additional cross-check. A small subset SHOULD also
be cross-validated through an independent automaton-product PDDL compilation.

## Evaluation Matrix

### Track A: Existing Achievement Evaluation

All existing held-out PDDL test instances remain in the atomic-library
evaluation:

```text
original PDDL achievement goal -> Jason -> committed trace -> VAL
```

This track does not establish temporal-goal support.

### Track B: Gold Lifted TEG Controller Evaluation

The language model is bypassed:

```text
gold lifted template
-> real DFA
-> parametric query wrapper
-> multiple instances and assignments
-> Jason + PDDL replay + gold DFA acceptance
```

This isolates Temporal Query Compiler and atomic-library behavior.

### Track C: Natural-Language End-to-End Evaluation

```text
natural-language template
-> language model
-> predicted lifted LTLf
-> real DFA
-> Jason trace
-> gold DFA acceptance
```

This measures the full framework. Translation equivalence, predicted-DFA
acceptance, gold-DFA acceptance, and end-to-end intent success are reported
separately.

### Instance Coverage

Using all current test problems as TEG environments is encouraged when compute
permits, but the template set MUST remain lifted and reusable. A defensible
default is:

```text
per domain:
  4-8 lifted temporal templates
  x every held-out test problem with at least one certified valid assignment
  x 1-3 deterministic assignments per template/problem
```

Assignments SHOULD cover small, medium, and large problems; already-true and
not-yet-true milestones; shared variables; threat/interference contexts;
resource-consuming contexts; and type/alias edge cases. Skipped instances MUST
record why no certified assignment or witness was available.

The same template identifier, formula hash, proposition map, and DFA artifact
SHOULD be reused across assignments. Regenerating one object-specific formula
per instance does not demonstrate lifted generalization.

### Required Metrics

Input metrics:

- valid JSON and abstract-syntax-tree rate;
- predicate, arity, type, and parameter accuracy;
- complete assignment compatibility rate;
- alpha-renaming-normalized structural accuracy;
- predicted/gold DFA language-equivalence rate;
- supported/unsupported classification precision and recall.

DFA metrics:

- successful construction rate;
- construction time and peak memory;
- proposition, state, and transition counts;
- timeout and structured failure counts;
- determinism/completeness audit rate;
- controller-topology acceptance/rejection rate.

Execution metrics:

- Jason completion rate;
- committed primitive-action count;
- PDDL action-trace validity;
- predicted-DFA acceptance;
- gold-DFA acceptance;
- end-to-end intent success;
- runtime and timeout rate;
- success by formula family, domain, problem size, and assignment class.

## Paper Claims and Non-Claims

After this design is implemented and evaluated, the defensible claim is:

> The framework accepts typed, externally bound parametric LTLf templates,
> compiles each template once through a real LTLf-to-DFA toolchain, reuses the
> resulting controller across held-out PDDL instances and assignments, and
> validates committed action traces by independent PDDL replay and gold-DFA
> finite-trace acceptance.

The framework MUST NOT claim:

- unrestricted first-order LTLf;
- existential object selection by the planner;
- universal satisfaction over all object assignments;
- unrestricted LTLf controller support while branching or cyclic DFA
  structures remain rejected;
- that VAL alone establishes temporal-goal satisfaction;
- that acceptance by a predicted formula proves natural-language correctness;
- that one grounded formula per PDDL instance demonstrates lifted behavior.

## Implementation Acceptance Checklist

The Input implementation is paper-ready only when all items below pass:

- schema version 2 separates templates from invocations;
- structured formula AST is authoritative;
- LLM output is validated against the actual PDDL schema;
- template parameters are typed and externally bound;
- proposition identifiers are deterministic and reversible;
- the same DFA artifact is reused across multiple assignments;
- real `ltlf2dfa` and MONA are mandatory, with no semantic fallback;
- tool versions, hashes, limits, statistics, and raw output are recorded;
- DFA determinism and guard partitioning are audited;
- action traces are replayed independently from the initial state;
- final acceptance uses the full finite state trace, including `s0`;
- gold and predicted DFA outcomes are separate;
- formula equivalence is semantic rather than textual;
- positive and negative PDDL-valid traces exist for benchmark queries;
- natural-language test inputs are human reviewed;
- achievement, gold-TEG, and natural-language end-to-end tracks remain separate;
- every unsupported case fails with a structured reason;
- no domain, predicate, fluent, action, or fixed argument-position name appears
  in executable query-generation rules.

## Verified Research Basis

- Jorge A. Baier and Sheila A. McIlraith, *Planning with First-Order
  Temporally Extended Goals Using Heuristic Search*, AAAI 2006. The work uses a
  rich first-order temporal-goal fragment and parameterized automata:
  <https://www.cs.toronto.edu/~sheila/publications/bai-mci-aaai06.pdf>.
- Giuseppe De Giacomo and Moshe Y. Vardi, *Linear Temporal Logic and Linear
  Dynamic Logic on Finite Traces*, IJCAI 2013. This supplies the finite-trace
  semantics used by LTLf:
  <https://repository.rice.edu/items/08ed8c8b-2c03-4e0e-9bea-f06fc9ca5dd3>.
- Jorge A. Baier and Sheila A. McIlraith, *Planning with Temporally Extended
  Goals Using Heuristic Search*, ICAPS 2006. This provides the automata-based
  planning precedent:
  <https://cdn.aaai.org/ICAPS/2006/ICAPS06-036.pdf>.
- Matthew B. Dwyer, George S. Avrunin, and James C. Corbett, *Patterns in
  Property Specifications for Finite-State Verification*, ICSE 1999. This is
  the basis for pattern-controlled temporal-query generation:
  <https://www.cs.colostate.edu/~france/CS614/Readings/Readings2011/PropPatterns2p411-dwyer.pdf>.
- Jason Xinyu Liu et al., *Grounding Complex Natural Language Commands for
  Temporal Tasks in Unseen Environments*, CoRL 2023. This motivates separating
  lifted translation from environment grounding: <https://lang2ltl.github.io/>.
- Yongchao Chen et al., *NL2TL: Transforming Natural Languages to Temporal
  Logics using Large Language Models*, 2023. This provides the formula-first,
  LLM-augmentation, and human-annotation precedent:
  <https://arxiv.org/abs/2305.07766>.
- William H. English et al., *Verifiable Natural Language to Linear Temporal
  Logic Translation: A Benchmark Dataset and Evaluation Suite*, 2025. This
  motivates separate lifting, grounding, translation, and trace-verification
  metrics: <https://arxiv.org/abs/2507.00877>.
- The required implementation toolchain is the real WhiteMech `ltlf2dfa`
  package backed by MONA: <https://github.com/whitemech/ltlf2dfa>.
