# Input-Only Lifted LTLf Benchmark and Translation Design

## Terminology

This glossary is normative. Later sections refine these terms but do not change
their meanings.

| Term | Definition and example |
| --- | --- |
| **PDDL domain (D)** | A Planning Domain Definition Language file containing types, predicates/functions, and action schemas. Example: `stack(X,Y)` requires `holding(X)` and `clear(Y)`. |
| **PDDL problem (P_i)** | One typed object universe, initial state, and original classical goal interpreted under `D`. |
| **Initial state (s0)** | The facts and numeric values true before the first source-trace action. |
| **Dynamic fluent** | A predicate that appears in an action add or delete effect. Example: `on(X,Y)`. |
| **Static context** | A predicate that never appears in an action effect. It may constrain a binding but is not selected as a nontrivial achievement milestone. |
| **Producible fluent** | A predicate that appears in a positive action effect and can therefore become true through domain actions. |
| **TEG** | A temporally extended goal whose truth depends on a finite state trace, not only its final state. |
| **LTLf** | Linear temporal logic interpreted over finite traces. |
| **Formula AST** | A JSON abstract syntax tree representing an LTLf formula without trusting free-form formula text. |
| **Lifted** | Expressed with typed parameters, for example `on(X,Y)`, rather than fixed problem objects. |
| **Grounded** | Expressed with concrete problem objects, for example `on(b1,b2)`. |
| **Gold template (T_i)** | The automatically constructed, witness-certified lifted LTLf oracle for sample `i`. It is hidden from the evaluated model. |
| **Predicted template** | The normalized lifted LTLf returned by the evaluated natural-language translation model. |
| **Assignment (theta_i)** | A complete typed map from parameters in `T_i` to objects in `P_i`, for example `{X:b1,Y:b2}`. |
| **Source witness (pi_i)** | An independently generated PDDL-valid primitive-action trace proving that `T_i[theta_i]` is realizable in `P_i`. |
| **Natural-language query (q_i)** | Controlled English rendered deterministically from `T_i`; it contains parameters, not the objects in `theta_i`. |
| **Atomic proposition (AP)** | A safe identifier such as `ap_0001` used to replace one lifted PDDL atom before calling `ltlf2dfa`. |
| **Proposition map** | The reversible map from APs to lifted atoms, for example `ap_0001 -> clear(Y)`. |
| **DFA** | A deterministic finite automaton compiled from one propositionized LTLf formula. |
| **DFA language equivalence** | Equality of the finite-trace languages accepted by predicted and gold complete DFAs. |
| **Input benchmark manifest** | The machine-readable index containing one construction outcome for every selected test problem. |
| **Structured non-construction** | A retained outcome such as `source_witness_not_found`; the problem is not silently removed. |

Requirement words are normative:

- **MUST** is required for a paper result to count.
- **MUST NOT** marks a semantic or methodological error.
- **SHOULD** is the default unless an experiment records a justification.
- **MAY** describes an optional extension outside the primary claim.

## Scope Boundary

This document specifies only the Input component:

```text
PDDL domain + one held-out PDDL problem
-> one independently valid source trace
-> one gold lifted LTLf template
-> one deterministic controlled-English query
-> language-model translation
-> predicted/gold DFA language-equivalence result
```

A downstream consumer may use the predicted lifted LTLf artifact, but this
document ends at the Input equivalence result and specifies no downstream
implementation.

The Input benchmark answers one research question:

> Given a PDDL vocabulary and a parametric natural-language query, does the
> Input model produce a well-typed lifted LTLf formula with the same finite-trace
> semantics as the automatically certified gold formula?

## Achievement Goal Versus Input TEG

| Property | Classical achievement benchmark | This Input TEG benchmark |
| --- | --- | --- |
| Goal source | Grounded conjunction in `problem.pddl` | Automatically selected ordered milestones from a valid state trace |
| Success semantics | Final PDDL state | Complete finite state trace |
| Parameters | Fixed problem objects | Lifted typed variables plus a separate assignment |
| Evaluation unit | One PDDL problem | One Input sample constructed from one PDDL problem |
| Correctness oracle | Original goal satisfaction | Predicted/gold DFA language equivalence |

Mechanical conversion of the original goal to `F(g1 & ... & gn)` is prohibited
as the primary TEG construction because it tests final achievement in temporal
syntax rather than temporal ordering.

## Canonical Sample Contract

For every selected held-out test problem, the builder attempts to construct:

```text
B_i = <D, P_i, q_i, T_i, theta_i, pi_i>
```

The fields mean:

- `D`: the PDDL domain providing predicates, functions, types, constants,
  arities, and action effects;
- `P_i`: one held-out PDDL problem providing objects and initial state;
- `q_i`: one automatically rendered parametric natural-language query;
- `T_i`: one automatically constructed gold lifted LTLf template;
- `theta_i`: the typed assignment from `T_i` parameters to `P_i` objects;
- `pi_i`: one independently generated, replay-validated source witness.

The evaluated model receives the PDDL catalogue and `q_i`. It MUST NOT receive
`T_i`, `theta_i`, `pi_i`, the original PDDL goal, or the state trace used
to construct the sample.

The primary target is exactly one constructed query per test problem. If a
valid source trace or temporal milestone pair cannot be obtained under the
pre-registered limits, the manifest retains a structured non-construction
record instead of fabricating a query.

## End-to-End Input Construction

```text
Stage 1: D
-> typed PDDL catalogue

Stage 2: P_i
-> independent valid source trace pi_i
-> replayed states s0,...,sn

Stage 3: replayed states
-> one deterministic ordered milestone pair

Stage 4: grounded milestones
-> lifted atoms + assignment theta_i
-> gold template T_i

Stage 5: T_i
-> deterministic controlled-English q_i

Stage 6: D catalogue + q_i
-> evaluated model
-> predicted template

Stage 7: predicted template + T_i
-> real ltlf2dfa/MONA DFAs
-> exact language-equivalence result
```

No stage may repair an invalid output by changing its semantics.

## Stage 1: PDDL Catalogue

### Input

```text
domain.pddl
```

### Output

The catalogue contains:

- domain name and requirements;
- transitive PDDL type hierarchy;
- typed domain constants;
- every predicate name, arity, and argument type;
- every numeric function name, arity, and argument type;
- whether each predicate appears in positive effects;
- whether each predicate appears in delete effects;
- whether each predicate is static;
- action schemas required by source-trace replay.

Effect properties are independent. A predicate may be both producible and
deletable. No property is inferred from a predicate or domain name.

### Required implementation

```python
def build_pddl_catalog(domain_file: Path) -> PDDLCatalog: ...
```

The parser MUST reject unsupported PDDL constructs with
`unsupported_pddl_feature`; it MUST NOT silently ignore them.

## Stage 2: Source Witness Construction

The Input benchmark needs a valid trajectory, not necessarily a solution of the
original PDDL goal. The source-trace provider therefore uses this fixed order.

### Provider 1: Source-supplied plan

If the benchmark source includes a plan, replay it and retain it only when all
actions are legal. Goal satisfaction is recorded but is not required for using
a legal prefix containing an ordered milestone pair.

### Provider 2: Independent classical planner

Run a pre-registered planner on the original problem:

```text
P_i
-> independent classical planner
-> primitive-action plan
-> independent PDDL replay
-> optional VAL cross-check
```

The planner MUST be independent of the system evaluated elsewhere in the
project. The planner name, version, configuration, wall-time limit, memory
limit, exit status, and logs are recorded.

### Provider 3: Goal-independent legal-trace exploration

If the planner does not return a valid plan, this does not prove that the
problem is unsolvable. The builder next performs bounded deterministic search
for any legal trace with two useful state-changing events:

```text
initial state
-> enumerate applicable grounded actions in canonical order
-> breadth-first state exploration with duplicate-state detection
-> stop at the first state path containing an eligible ordered milestone pair
```

This fallback does not need to satisfy the original PDDL goal because that goal
is not the TEG oracle. It only needs a legal trace witnessing the generated
temporal query.

Default pre-registered limits are:

```text
planner_timeout_seconds: 1800
planner_memory_limit_mib: 16384
explorer_timeout_seconds: 300
explorer_max_depth: 8
explorer_max_states: 100000
```

Experiments MAY change these limits only before running the test split and MUST
record the actual values.

### Failure semantics

| Code | Meaning |
| --- | --- |
| `source_plan_invalid` | A supplied/planner plan failed independent replay. |
| `source_planner_timeout` | The independent planner exceeded its limit; this is not an unsolvability proof. |
| `source_planner_error` | The planner process failed. |
| `source_explorer_limit` | Bounded legal-trace exploration exhausted a declared limit. |
| `source_witness_not_found` | No provider produced an eligible valid trace. |

Every failure remains in the manifest. Translation accuracy is reported only
over constructed samples, while construction coverage is reported over the
complete test split.

## Stage 3: Deterministic Milestone Selection

Independent replay yields:

```text
s0 --a0--> s1 --a1--> ... --a(n-1)--> sn
```

### Candidate events

A positive propositional event at state `s_k` is:

```text
literal l is false in s(k-1) and true in s_k
```

`l` MUST use a producible dynamic predicate. A numeric event records a
declared numeric function whose value changed at `s_k`, represented by its new
integer equality.

### Eligible ordered pair

For events `e_i=(i,l_1)` and `e_j=(j,l_2)`, the pair is eligible when:

- `i < j`;
- `l_2` is false in `s_i`, so its satisfaction is genuinely later;
- every object in both literals has a declared type;
- both state conditions are supported by the Input atom schema.

### Deterministic ranking

Eligible pairs are sorted by this domain-independent key:

```text
1. prefer l_1 false in final state s_n;
2. prefer more shared problem objects between l_1 and l_2;
3. prefer larger transition distance j-i;
4. prefer lower total predicate/function arity;
5. canonical literal strings;
6. state indices i,j.
```

The first pair is selected. The algorithm MUST NOT inspect predicate names,
domain names, original-goal literal order, or any post-Input result.

### Singleton control fallback

If a valid trace has no eligible pair but has one positive event, the builder
MAY construct `F(l)` and mark the sample
`eventual_singleton_control`. Such a sample tests lifted translation but does
not count toward strict temporal-ordering coverage.

If neither an ordered pair nor a singleton event exists, record
`no_temporal_query_constructible`.

## Stage 4: Lifting and Gold LTLf

### Object-to-parameter lifting

Traverse the selected grounded literals in formula order:

1. keep declared PDDL domain constants unchanged;
2. map each first-seen problem object to the next canonical parameter name
   `X,Y,Z,A,B,...`;
3. assign the object's declared PDDL type to that parameter;
4. reuse the same parameter whenever the same object reappears;
5. add `not_equal` constraints for distinct source objects whose types permit
   aliasing;
6. store the reverse object map as `theta_i`.

Example source milestones:

```text
clear(b2) at state 3
on(b1,b2) at state 7
```

Lifted result:

```text
X:block -> b2
Y:block -> b1

A = clear(X)
B = on(Y,X)
T_i = F(A & X(F(B)))
```

The temporal operator `X(...)` and parameter `X` are distinct AST node
categories; string replacement is prohibited.

### Primary formula profile

The primary strict-temporal profile is:

```text
F(A & X(F(B)))
```

It means that `A` holds at some state and `B` holds at a strictly later
state. It does not prohibit `B` from occurring before that chosen `A` state.

The singleton control profile is:

```text
F(A)
```

This intentionally narrow profile supports a simple, reproducible Input claim.
Broader LTLf grammars may be added as separate benchmark versions; they MUST NOT
be implied by the primary results.

### Gold-template schema

```json
{
  "schema_version": 1,
  "artifact_kind": "input_gold_lifted_ltlf",
  "sample_id": "blocksworld_on_p01",
  "domain": "blocksworld-on",
  "problem_file": "src/domains/blocksworld-on/test/p01.pddl",
  "profile": "ordered_two_milestone",
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
      "arguments": ["X"]
    },
    {
      "atom_id": "a1",
      "kind": "predicate",
      "predicate": "on",
      "arguments": ["Y", "X"]
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

Unknown semantic fields MUST be rejected. The checked-in JSON Schema MUST set
`additionalProperties: false` for semantic objects.

The assignment is a separate artifact because it is `theta_i`, not part of the
reusable lifted formula `T_i`:

```json
{
  "schema_version": 1,
  "artifact_kind": "input_parameter_assignment",
  "sample_id": "blocksworld_on_p01",
  "problem_file": "src/domains/blocksworld-on/test/p01.pddl",
  "bindings": {"X": "b2", "Y": "b1"}
}
```

## Stage 5: Deterministic Natural-Language Rendering

No per-sample human annotation or language-model generation is used in the
primary benchmark.

### Parameter clause

Render parameters in declaration order:

```text
Given parameter X of PDDL type block and parameter Y of PDDL type block, ...
```

When a `not_equal(X,Y)` constraint exists, render:

```text
Given distinct parameters X and Y of PDDL type block, ...
```

### Atom rendering

```text
predicate p(X,Y)
-> predicate p holds for arguments X and Y

numeric f(X) = 0
-> numeric function f for argument X equals 0
```

Predicate/function identifiers remain explicit. No unverified domain-specific
English gloss is introduced.

### Formula rendering

```text
F(A)
-> ensure that at some state, <A>.

F(A & X(F(B)))
-> ensure that at some state, <A>, and that at a strictly later state, <B>.
```

Example:

```text
Given distinct parameters X and Y of PDDL type block, ensure that at some
state, predicate clear holds for argument X, and that at a strictly later
state, predicate on holds for arguments Y and X.
```

The renderer MUST be a deterministic AST visitor. Rendering from arbitrary
formula strings or using an LLM is prohibited in the primary benchmark.

## Stage 6: Language-Model Translation

### Model input

The model receives:

- the controlled-English query;
- declared query parameters and types;
- the PDDL catalogue;
- the closed output JSON Schema;
- the supported formula profile.

It does not receive the gold formula, assignment, source witness, state trace,
or original PDDL goal.

```json
{
  "schema_version": 1,
  "task": "controlled_english_to_lifted_ltlf",
  "logic_profile": "ordered_two_milestone_v1",
  "domain": {
    "name": "blocksworld-on",
    "predicates": [
      {
        "name": "clear",
        "parameters": [{"position": 0, "pddl_type": "block"}],
        "dynamic": true,
        "producible": true,
        "deletable": true
      },
      {
        "name": "on",
        "parameters": [
          {"position": 0, "pddl_type": "block"},
          {"position": 1, "pddl_type": "block"}
        ],
        "dynamic": true,
        "producible": true,
        "deletable": true
      }
    ],
    "numeric_functions": []
  },
  "query": {
    "sample_id": "blocksworld_on_p01",
    "source_text": "Given distinct parameters X and Y of PDDL type block, ensure that at some state, predicate clear holds for argument X, and that at a strictly later state, predicate on holds for arguments Y and X.",
    "declared_parameters": [
      {"name": "X", "pddl_type": "block"},
      {"name": "Y", "pddl_type": "block"}
    ]
  },
  "output_contract": "predicted_lifted_ltlf_v1"
}
```

### Model output

The model returns JSON only:

```json
{
  "schema_version": 1,
  "artifact_kind": "predicted_lifted_ltlf",
  "sample_id": "blocksworld_on_p01",
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
      "arguments": ["X"]
    },
    {
      "atom_id": "a1",
      "kind": "predicate",
      "predicate": "on",
      "arguments": ["Y", "X"]
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

### Deterministic validation

The parser MUST verify:

- closed JSON Schema conformance;
- exact sample identity;
- complete parameter declarations;
- PDDL predicate/function existence;
- arity and transitive type compatibility;
- no problem-object constants in the lifted output;
- supported constraints only;
- supported formula-AST profile only;
- no executable identifiers copied from natural-language prose.

Invalid output is rejected. Any retry is a separate attempt with separate model
provenance; the validator MUST NOT repair predicate names or formula structure.

## Stage 7: Semantic Validation

### Gold realizability check

Ground `T_i` with `theta_i`, label the independently replayed states of
`pi_i`, and require the gold DFA to accept. If it does not, benchmark
construction failed with `gold_witness_rejected`.

### Predicted/gold equivalence

1. type-preserving alpha-normalize predicted and gold parameters;
2. canonicalize lifted atoms by predicate/function, argument positions, and
   normalized parameters;
3. build a shared AP vocabulary and reversible proposition maps;
4. render both ASTs deterministically to safe propositional LTLf;
5. invoke the real `ltlf2dfa` package and MONA for both formulas;
6. complete each DFA with an explicit rejecting sink when needed;
7. construct their symmetric-difference product;
8. report equivalent exactly when no product state with different acceptance is
   reachable.

String equality is not the oracle. For example, `F(A & B)` and `F(B & A)`
are semantically equivalent despite different text.

Acceptance of the single source witness by both formulas is also not the oracle.
An incorrect weaker formula may accept the same positive trace. Exact DFA
language equivalence is therefore the primary translation metric.

### Real tool requirement

`ltlf2dfa` and a local MONA binary are mandatory. A timeout, memory failure, or
parse failure produces a structured failure; no hand-written DFA or semantic
fallback is permitted.

Default limits:

```text
mona_timeout_seconds: 300
mona_memory_limit_mib: 16384
```

## Full Test-Split Policy

The current Input scope covers the complete test split of:

```text
barman
ferry
gripper
logistics
miconic
rovers
satellite
transport
numeric-ferry
numeric-miconic
numeric-minecraft
numeric-transport
blocksworld-clear
blocksworld-on
blocksworld-tower
depots
```

The manifest contains one row for every file in every selected domain's
`test/` directory:

```text
constructed_ordered_query
eventual_singleton_control
source_witness_not_found
no_temporal_query_constructible
unsupported_pddl_feature
internal_error
```

Only `constructed_ordered_query` counts toward strict temporal translation.
`eventual_singleton_control` is reported separately. No problem disappears
from construction-coverage statistics.

Templates are produced independently per problem because the Input evaluation
unit is one query translation. A template may happen to be alpha-equivalent to
another problem's template; this is recorded by canonical formula hash but does
not remove either sample.

## Data Leakage Boundary

- Source traces and gold queries for test problems are generated only after the
  construction algorithm and limits are frozen.
- The evaluated model never receives test gold formulas or source traces.
- Few-shot examples, if used, are generated only from the training split with
  the same deterministic procedure.
- Prompt bytes, model name, provider, base URL, request identifier, generation
  parameters, raw response, and retry count are recorded.
- API keys are read from environment variables and never persisted.

## Required Repository Ownership

The colleague implementing Input owns only:

```text
src/temporal_input/
  models.py
  pddl_catalog.py
  source_trace.py
  milestone_selector.py
  lifter.py
  controlled_english.py
  translator.py
  propositionizer.py
  dfa_equivalence.py
  benchmark_builder.py
  schemas/
    gold_lifted_ltlf.schema.json
    predicted_lifted_ltlf.schema.json
    parameter_assignment.schema.json
    controlled_query.schema.json
    model_input.schema.json
    source_trace_outcome.schema.json
    construction_record.schema.json
    evaluation_record.schema.json
```

The implementation MAY reuse repository PDDL parsing, replay, and real
`ltlf2dfa`/MONA process helpers through stable interfaces. It MUST NOT modify
or depend on downstream planning or execution modules.

## Required Public Interfaces

```python
def build_pddl_catalog(domain_file: Path) -> PDDLCatalog: ...

def obtain_source_trace(
    *,
    domain_file: Path,
    problem_file: Path,
    config: SourceTraceConfig,
) -> SourceTraceOutcome: ...

def replay_source_trace(
    *,
    domain: PDDLCatalog,
    problem_file: Path,
    actions: Sequence[PDDLActionCall],
) -> ReplayedStateTrace: ...

def select_temporal_milestones(
    *,
    domain: PDDLCatalog,
    states: ReplayedStateTrace,
) -> MilestoneSelectionOutcome: ...

def lift_milestones(
    *,
    domain: PDDLCatalog,
    problem_file: Path,
    milestones: SelectedMilestones,
) -> GoldLiftedLTLfSample: ...

def render_controlled_query(
    gold: GoldLiftedLTLfSample,
) -> ParametricQueryText: ...

def translate_query(
    *,
    query: ParametricQueryText,
    catalog: PDDLCatalog,
    provider: TemporalTranslationProvider,
) -> TranslationAttempt: ...

def compare_predicted_to_gold(
    *,
    predicted: PredictedLiftedLTLf,
    gold: GoldLiftedLTLfSample,
) -> InputSemanticEvaluation: ...
```

All functions return typed immutable values or structured outcomes. They MUST
NOT return partially valid dictionaries after failure.

## Required Command-Line Interfaces

```bash
uv run python src/main.py build-input-ltlf-benchmark \
  --domain-file src/domains/<domain>/domain.pddl \
  --test-dir src/domains/<domain>/test \
  --output-root artifacts/input_benchmarks/<benchmark_id> \
  --planner-timeout-seconds 1800 \
  --planner-memory-limit-mib 16384 \
  --explorer-timeout-seconds 300 \
  --explorer-max-depth 8 \
  --explorer-max-states 100000

uv run python src/main.py evaluate-input-ltlf-benchmark \
  --benchmark-root artifacts/input_benchmarks/<benchmark_id> \
  --output-root artifacts/input_evaluations/<run_id> \
  --model <model_name> \
  --base-url-env <environment_variable_name>
```

Each completed problem prints one concise progress line:

```text
[ok] domain=rovers problem=p01 status=constructed_ordered_query elapsed=1.24s
[skip] domain=rovers problem=p02 status=source_witness_not_found elapsed=300.00s
```

Full metadata and model responses are written to artifacts, not printed to the
terminal.

## Canonical Artifact Layout

```text
artifacts/input_benchmarks/<benchmark_id>/
  manifest.json
  config.json
  <domain>/<problem_id>/
    construction.json
    source_plan.plan
    source_trace.jsonl
    gold_template.json
    assignment.json
    query.json
    gold_proposition_map.json
    gold_formula.ltlf
    gold_dfa.json
    gold_dfa.dot
    source_provider.stdout.log
    source_provider.stderr.log
    mona.stdout.log
    mona.stderr.log

artifacts/input_evaluations/<run_id>/
  manifest.json
  <domain>/<problem_id>/
    model_request.json
    model_response.raw.json
    predicted_template.json
    predicted_proposition_map.json
    predicted_formula.ltlf
    predicted_dfa.json
    predicted_dfa.dot
    equivalence.json
    evaluation.json
```

Absent artifacts for a non-construction outcome are listed as `null` in
`construction.json`; empty placeholder files are prohibited.

## Metrics

### Construction metrics

- complete test problems;
- valid source-witness rate;
- ordered-query construction rate;
- singleton-control rate;
- source planner timeout/error rate;
- source explorer limit rate;
- milestone selection and lifting failures;
- construction time by domain and problem size.

### Translation metrics

- model-response JSON Schema validity;
- parameter declaration accuracy;
- predicate/function symbol accuracy;
- arity and type accuracy;
- argument-position accuracy;
- ordered-profile structural accuracy;
- predicted/gold DFA language-equivalence rate;
- MONA success, timeout, memory, state, and transition statistics;
- accuracy by domain and problem size.

The primary Input score is predicted/gold DFA language-equivalence rate over
`constructed_ordered_query` samples. Construction coverage is always reported
beside it so that difficult problems cannot be hidden.

## Stable Failure Codes

| Stage | Required codes |
| --- | --- |
| PDDL catalogue | `pddl_parse_error`, `unsupported_pddl_feature` |
| Source trace | `source_plan_invalid`, `source_planner_timeout`, `source_planner_error`, `source_explorer_limit`, `source_witness_not_found` |
| Milestones | `no_temporal_query_constructible`, `unsupported_numeric_event` |
| Lifting | `object_type_unknown`, `non_liftable_domain_constant`, `invalid_parameter_constraint` |
| Rendering | `controlled_renderer_error` |
| Translation | `model_provider_error`, `model_response_schema_invalid`, `model_identity_mismatch` |
| Semantic validation | `unknown_symbol`, `predicate_arity_mismatch`, `argument_type_mismatch`, `unsupported_formula_profile` |
| DFA | `ltlf_formula_invalid`, `ltlf2dfa_timeout`, `ltlf2dfa_memory_limit`, `mona_process_error`, `dfa_parse_error` |
| Equivalence | `dfa_equivalence_error`, `predicted_gold_not_equivalent` |
| Internal | `internal_error` |

`internal_error` retains a traceback and fails the run. It is not converted
into an expected semantic rejection.

## Required Tests

- PDDL catalogue extraction is invariant under domain/predicate/action
  renaming except for the corresponding output renaming.
- Source plans and fallback traces are independently replayed.
- Planner timeout is never classified as unsolvable.
- Milestone selection follows the declared ranking under predicate renaming.
- No selector checks domain names, predicate names, or original-goal order.
- Repeated source objects become repeated parameters; distinct compatible
  objects produce deterministic inequality constraints.
- No problem-object constant appears in a lifted template or query.
- Controlled-English rendering is byte-deterministic for the same gold AST.
- Every displayed JSON example validates against its checked-in schema.
- Proposition identifiers are deterministic and reversible.
- Real `ltlf2dfa`/MONA smoke, timeout, memory, and parse failures are tested.
- Alpha-equivalent formulas compare equivalent.
- Semantically different formulas that accept the same source witness compare
  non-equivalent.
- Every test problem produces either one construction artifact or one
  structured non-construction record.
- Predicate/action renaming and irrelevant-fluent injection do not change
  construction decisions except for corresponding symbol changes.

## Definition of Done

The Input implementation is complete only when:

- every selected test problem appears exactly once in the benchmark manifest;
- every constructed gold query has a replay-valid source witness accepted by
  its gold DFA;
- every primary query is lifted and stores its grounding only in `theta_i`;
- natural language is rendered deterministically without per-sample human or
  model generation;
- the evaluated model receives no gold, assignment, trace, or original-goal
  information;
- predicted formulas pass strict PDDL schema/type validation;
- semantic correctness is determined by exact DFA language equivalence;
- all failures are structured and all resource limits and tool versions are
  recorded;
- the implementation has no dependency on downstream planning/execution code.

## Paper Claim and Non-Claims

After implementation, the defensible Input claim is:

> For each held-out PDDL problem where an independent valid trajectory exposes
> an eligible ordered milestone pair, the benchmark automatically constructs
> one typed lifted LTLf specification and one semantics-preserving controlled-
> English query. Input predictions are evaluated by strict PDDL vocabulary/type
> validation and exact finite-trace language equivalence to the gold DFA.

The Input evaluation does not claim:

- unrestricted free-form human-language understanding;
- unrestricted first-order LTLf, existential search, or universal
  quantification;
- coverage of all LTLf formula families;
- that a planner timeout proves the PDDL problem or TEG impossible;
- downstream plan synthesis or execution correctness.

## Verified Research Basis

- Jorge A. Baier and Sheila A. McIlraith, *Planning with First-Order
  Temporally Extended Goals Using Heuristic Search*, AAAI 2006:
  <https://www.cs.toronto.edu/~sheila/publications/bai-mci-aaai06.pdf>.
- Giuseppe De Giacomo and Moshe Y. Vardi, *Linear Temporal Logic and Linear
  Dynamic Logic on Finite Traces*, IJCAI 2013:
  <https://repository.rice.edu/items/08ed8c8b-2c03-4e0e-9bea-f06fc9ca5dd3>.
- Yongchao Chen et al., *NL2TL: Transforming Natural Languages to Temporal
  Logics using Large Language Models*, EMNLP 2023:
  <https://arxiv.org/abs/2305.07766>.
- WhiteMech `ltlf2dfa`, the required MONA-backed implementation:
  <https://github.com/whitemech/ltlf2dfa>.
