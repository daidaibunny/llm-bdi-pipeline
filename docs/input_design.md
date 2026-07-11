# Automatic Natural-Language TEG Benchmark Construction

## Terminology

This glossary is normative.

| Term | Definition and example |
| --- | --- |
| **PDDL domain (`D`)** | The domain file containing types, predicates, numeric functions, and action schemas. An action schema is a parameterized action such as `stack(X,Y)` with preconditions and effects. |
| **PDDL problem (`P_i`)** | One held-out test problem providing concrete objects and an initial state. Its original achievement goal is not used to construct the temporal query. |
| **Temporally extended goal (TEG)** | A goal whose truth depends on a finite sequence of states, not only the final state. “Hold `A`, then later hold `B`” is a TEG. |
| **Linear temporal logic on finite traces (LTLf)** | Temporal logic interpreted over a finite state trace. This builder creates a hidden structured oracle with LTLf semantics but does not call a model or produce a predicted LTLf manifest. |
| **Legal rollout** | A short action sequence generated from the PDDL initial state in which every action satisfies its typed propositional and numeric preconditions. Example: `unstack(b1,b8); stack(b1,b4)`. |
| **Witness trace (`pi_i`)** | One legal rollout plus every replayed state. It proves that the selected temporal condition is realizable for one assignment in `P_i`; it is not required to solve the original PDDL goal. |
| **Milestone** | A grounded predicate or numeric equality selected from a state change. Example: `holding(b1)` or `capacity(truck1)=1`. |
| **Candidate pool** | All nontrivial temporal-query candidates mined within the pre-registered rollout bounds for one problem. The builder selects from a pool instead of taking the first applicable action. |
| **Formula profile** | One supported temporal structure, such as ordered two-milestone `F(A & X(F(B)))` or persistence-until `A U B`. |
| **Lifted** | Written with typed parameters rather than problem objects. Example: `on(X,Y)`, not `on(b1,b4)`. |
| **Assignment (`theta_i`)** | The hidden typed map from lifted parameters to objects in `P_i`, for example `{X:b1,Y:b4}`. |
| **Hidden semantic oracle (`T_i`)** | The structured, automatically constructed lifted temporal formula from which the natural-language query is rendered. It is retained only in the private construction audit and never included in model input. |
| **Controlled natural-language query (`q_i`)** | English generated deterministically from `T_i`, using explicit PDDL symbols and typed parameters. No person or language model writes individual queries. |
| **Externally bound parameter** | A lifted parameter declared by the query but not assigned to a problem object during translation. For example, `X:block` remains `X`; the language model must not choose `b4`. |
| **Propositional atom identifier** | A MONA-safe name such as `a0` used inside the LTLf formula. Its `atoms` entry reversibly maps it to a lifted PDDL atom such as `on(X,Y)`. |
| **Predicted lifted LTLf payload** | The language model's self-contained JSON translation: an LTLf formula over `a0`, `a1`, and so on, plus the atom table that restores the lifted PDDL meaning. It contains no problem-object assignment. |
| **Semantic signature** | A SHA-256 hash of the alpha-normalized profile, typed variable-sharing structure, atoms, constraints, and formula abstract syntax tree. Ground object names are absent, so alpha-equivalent samples share a signature. |
| **Natural-language manifest** | The public handoff containing one row per test problem, with `q_i`, declared parameters, constraints, profile, and a reference to the domain catalogue. It contains no assignment, witness, or gold formula. |
| **Construction audit** | The private artifact containing `T_i`, `theta_i`, `pi_i`, and state fingerprints. It allows reproducibility checks without leaking answers to the translation model. |
| **Structured non-construction** | A retained row such as `source_witness_not_found`. A problem is never silently dropped. |

Requirement words are normative:

- **MUST** is required for a paper result to count.
- **MUST NOT** marks a semantic or methodological error.
- **SHOULD** is the pre-registered default.
- **MAY** describes an extension outside the primary result.

## Scope and Handoff Boundary

This repository owns exactly this construction path:

```text
PDDL domain D + held-out test problem P_i
-> typed bounded legal rollouts
-> nontrivial temporal candidate pool
-> deterministic profile/signature-balanced selection
-> hidden lifted semantic oracle T_i + assignment theta_i + witness pi_i
-> deterministic controlled-English query q_i
-> public natural-language manifest
```

The public natural-language manifest is the final output of this document.
The colleague starts from that manifest, calls the language model, and produces
the predicted LTLf manifest. Model calls, predicted LTLf parsing, LTLf2DFA,
MONA, DFA comparison, planning, AgentSpeak compilation, Jason, and VAL are
outside this document's implementation scope.

The local builder MUST NOT call a language model, classical planner, generalized
planner, AgentSpeak runtime, or downstream temporal controller.

This repository also provides the normative prompt builders that define the
handoff contract. Providing prompt text does not move model execution into the
local construction scope.

## Normative NL-to-Lifted-LTLf Prompt Handoff

The only authoritative prompt source on `main` is:

```text
src/temporal_specification/prompts.py
  build_lifted_ltlf_system_prompt(catalog, config)
  build_lifted_ltlf_user_prompt(sample)
  build_retry_user_message(feedback)

src/temporal_specification/errors.py
  TranslationErrorCode
  build_retry_feedback(...)
```

There is no Prompt 1 language-model stage. `q_i` is already rendered
deterministically by the local builder. The colleague uses only Prompt 2 to
translate `q_i` into lifted LTLf.

### Model-call input

One system message is rendered from the domain's public `catalog.json`. It
contains predicate signatures, numeric-function signatures, typed domain
constants, and the type hierarchy. It contains no actions, problem objects,
initial state, original goal, witness, or hidden temporal oracle.

One user message is rendered from a constructed public row and contains only:

```json
{
  "sample_id": "blocksworld_on_p_50_0",
  "source_text": "Given parameter X ...",
  "declared_parameters": [
    {"name": "X", "pddl_type": "object"},
    {"name": "Y", "pddl_type": "object"}
  ],
  "constraints": [
    {"operator": "not_equal", "left": "X", "right": "Y"}
  ],
  "parameter_semantics": "externally_bound"
}
```

Although `profile`, `construction_tier`, and `semantic_signature` are public
benchmark metadata, the prompt builder deliberately omits them. `profile`
would reveal the target operator structure; the other fields are irrelevant to
semantic translation. The builder also rejects non-constructed rows instead of
asking the model to fabricate a formula.

`externally_bound` denotes a parameterized formula schema. The schema can be
instantiated with any assignment satisfying the declared PDDL types and
constraints, but one later invocation supplies one concrete assignment. During
translation `X` is therefore neither a problem object nor an LTLf-quantified
variable; the model preserves `X` exactly and introduces no quantifier.

### Why the formula uses `a0`, `a1`, and so on

PDDL atoms such as `on(X,Y)` contain uppercase parameters, parentheses, and
commas that are unsuitable as raw MONA propositions. The model therefore writes
the LTLf formula over deterministic propositional atom identifiers and supplies
a reversible lifted atom table:

```json
{
  "schema_version": 1,
  "sample_id": "example_1",
  "temporal_logic": "LTLf",
  "ltlf_formula": "F(a0 & X(F(a1)))",
  "atoms": [
    {
      "symbol": "a0",
      "kind": "predicate",
      "predicate": "holding",
      "args": ["X"]
    },
    {
      "symbol": "a1",
      "kind": "predicate",
      "predicate": "on",
      "args": ["X", "Y"]
    }
  ],
  "declared_parameters": [
    {"name": "X", "pddl_type": "object"},
    {"name": "Y", "pddl_type": "object"}
  ],
  "constraints": [
    {"operator": "not_equal", "left": "X", "right": "Y"}
  ],
  "status": "supported"
}
```

For a numeric milestone, the formula still uses a propositional identifier and
the atom table carries the numeric meaning:

```json
{
  "symbol": "a0",
  "kind": "numeric_equality",
  "function": "fuel-level",
  "args": ["X"],
  "value": 1
}
```

The atom table is the reversible propositionization boundary: LTLf2DFA/MONA
sees `a0`; later validation restores `a0` to the declared lifted predicate or
numeric equality. The model MUST NOT add a problem-object `binding` field.

### Formula fragment

Benchmark version 1 allows exactly `F`, `X`, `U`, `&`, and `!`. The five tested
structures are:

```text
F(a0 & a1)
F(a0 & !a1)
F(a0 & X(F(a1)))
F(a0 & X(F(a1 & X(F(a2)))))
a0 U a1
```

Disjunction, global, release, weak-next, implication, equivalence, and
quantifiers are out of scope. This restriction matches the formulas generated
by the local benchmark; it is not a claim about unrestricted LTLf.

### Required prediction validation

Before accepting a model response, the colleague's implementation MUST check:

- exactly the eight required top-level keys and no prose;
- exact `sample_id`, declared parameters, constraints, and parameter spelling;
- every `a<number>` used by the formula is defined exactly once, in first-use
  order, and no atom-table entry is unused;
- catalogue membership, arity, and subtype-compatible arguments for every
  predicate or numeric function;
- integer values for `numeric_equality` atoms;
- use of only the benchmark-version-1 operators;
- successful restricted-LTLf parsing before invoking LTLf2DFA/MONA.

Only model-correctable JSON, syntax, vocabulary, arity, type, parameter,
operator, atom-table, or unsatisfiability errors may produce a retry message.
Network failures, model timeouts, LTLf2DFA failures, MONA failures/timeouts, and
malformed DFA output are infrastructure outcomes and MUST NOT be reframed as
instructions to simplify or semantically change the query.

## Research Unit

For every test problem the private construction record is:

```text
B_i = <D, P_i, q_i, T_i, theta_i, pi_i>
```

- `D` supplies the PDDL vocabulary and action semantics.
- `P_i` supplies typed objects and the initial state.
- `q_i` is the public natural-language query.
- `T_i` is the hidden lifted temporal oracle.
- `theta_i` grounds `T_i` in `P_i`.
- `pi_i` is the replay-valid witness for `T_i[theta_i]`.

The model-facing row contains only `D`'s public catalogue, `q_i`, the declared
parameters, their types, and explicit inequality constraints. It MUST NOT
contain `T_i`, `theta_i`, `pi_i`, replayed states, or the original PDDL goal.

## Why the Original PDDL Goal Is Not Used

The original benchmark goal is normally one grounded final-state conjunction.
Mechanically rewriting it as `F(g1 & ... & gn)` would preserve an achievement
goal in temporal syntax but would not test temporal ordering. The builder uses
only `P_i`'s object universe and initial state, then constructs a new realizable
TEG from legal state changes.

The original goal MAY be recorded as provenance but MUST NOT affect rollout
ordering, candidate ranking, query wording, or construction success.

## Inputs and Outputs

### Inputs

```text
src/domains/<domain>/domain.pddl
src/domains/<domain>/test/*.pddl
```

The supported fragment is finite-domain typed or untyped STRIPS with:

- positive and negative conjunctive predicate preconditions;
- positive and delete predicate effects;
- integer numeric comparisons;
- constant integer `increase` and `decrease` effects;
- transitive PDDL subtype membership;
- typed domain constants.

Unsupported nested disjunction, quantification, conditional effects, derived
predicates, arbitrary arithmetic, or durative actions MUST fail closed with a
structured diagnostic.

### Public output

```text
artifacts/temporal_nl_benchmarks/<benchmark_id>/
  manifest.json
  natural_language_manifest.jsonl
  domains/<domain>/catalog.json
  domains/<domain>/natural_language_manifest.json
```

This is the only handoff to the colleague.

### Private construction output

```text
artifacts/temporal_nl_benchmarks/<benchmark_id>/
  domains/<domain>/construction_audit.jsonl
```

The private audit is not model input. It stores the lifted atom table, hidden
formula abstract syntax tree, assignment, witness actions, and state
fingerprints.

## Stage 1: Typed PDDL Catalogue

### Input

```text
domain.pddl
```

### Output

`catalog.json` contains:

- the domain name;
- the transitive type-parent relation;
- typed PDDL domain constants, which are public vocabulary rather than problem objects;
- every predicate name and argument type;
- every numeric function name and argument type.

Action schemas remain private construction inputs. The catalogue contains no
problem objects or original goals.

### Symbol-independence rule

The builder may inspect only PDDL syntax and semantics. It MUST NOT check a
domain name, action name, predicate name, fixed parameter position, or a list
of known benchmark symbols. Consistently renaming all domain symbols must only
rename the corresponding output.

## Stage 2: Bounded Legal Rollouts

No classical planner is used. The builder only needs short legal trajectories,
not a solution of the original achievement goal.

Starting at the initial state, it:

1. joins positive action preconditions against indexed current facts;
2. fills still-unbound parameters from type-compatible objects;
3. checks all positive, negative, and numeric preconditions;
4. applies simultaneous predicate and numeric effects;
5. stores the successor only when the state changes;
6. rejects any path that repeats an earlier complete state.

An immediate inverse pair that restores the initial state is therefore rejected
without recognizing action names.

### Pre-registered bounds

```text
max_trace_depth: 3
max_actions_per_state: 12
max_first_actions: 4
max_second_actions_per_prefix: 4
max_three_step_prefixes: 1
max_third_actions_per_prefix: 4
max_join_bindings_per_schema: 64
max_candidates_per_problem: 1024
max_candidates_per_profile: 16
```

If and only if the primary candidate pool is empty, the same problem is retried
once with the pre-registered expanded evidence bounds:

```text
expanded_max_actions_per_state: 32
expanded_max_join_bindings_per_schema: 2048
```

All legality, nontriviality, profile, and selection rules remain identical.
The public row records `construction_tier` as `primary` or `expanded`. No
domain name, predicate, action, problem identifier, or observed downstream
result can activate the expanded tier.

Applicable actions are allocated in round-robin order across action schemas.
This prevents an alphabetically early schema with many groundings from starving
other schemas. Every retained grounding still passes the complete applicability
check. These limits make construction bounded but not complete: failure means
“no witness found under the registered bounds,” not “the TEG is impossible.”

## Stage 3: Temporal Candidate Mining

A positive predicate event is a fact false before an action and true after it.
A negative event is a fact true before an action and false after it. A numeric
event is a declared integer fluent whose value changes, represented by equality
to its successor value.

The builder mines five profiles. `A`, `B`, and `C` below are lifted only after
the grounded witness has been accepted.

| Profile | Hidden semantics | Required witness evidence | Controlled-English shape |
| --- | --- | --- | --- |
| `same_state_conjunction` | `F(A & B)` | One legal action makes distinct positive events `A` and `B` true in the same successor state. | “At some state, both A and B.” |
| `same_state_with_negation` | `F(A & !B)` | One legal action makes `A` true and `B` false in the same successor state. | “At some state, A while B does not hold.” |
| `ordered_two_milestone` | `F(A & X(F(B)))` | Two legal state-changing actions; `A` is an event after action one and `B` is a new event after action two. | “A, and at a strictly later state, B.” |
| `ordered_three_milestone` | `F(A & X(F(B & X(F(C)))))` | Three legal state-changing actions and four pairwise-distinct states. | “A, later B, and later after that C.” |
| `persistence_until` | `A U B` | Dynamic `A` holds in every replayed state before a new `B` event and `B` was absent initially. | “A continues to hold until B holds.” |

These profiles cover conjunction, negation, eventuality, strict-next ordering,
and strong-until semantics with one-, two-, and three-action witnesses. They do
not claim unrestricted LTLf coverage. Global `G`, release `R`, disjunction,
implication, quantified temporal goals, and free-form nesting are excluded from
benchmark version 1 and MUST NOT be implied by its results.

### Nontriviality filters

A candidate is rejected when:

- an action has no state effect;
- any complete replay state repeats;
- the second action exactly restores the initial state;
- an ordered milestone is not a newly satisfied event at its selected step;
- an until right-hand milestone was already true initially;
- an atom uses an unknown object or unsupported value type.

The witness proves realizability of the selected grounded formula. It does not
prove that all assignments of the lifted variables are realizable.

## Stage 4: Lifting

Objects are traversed in formula order:

1. declared domain constants remain constants;
2. the first unseen problem object becomes `X`, then `Y`, `Z`, `A`, and so on;
3. the object's declared PDDL type is copied to the parameter;
4. repeated objects reuse the same parameter;
5. distinct objects with type-compatible domains receive `not_equal` constraints;
6. the reverse map is stored only in hidden `theta_i`.

Example:

```text
witness milestones: holding(b1), then on(b1,b4)
assignment theta_i: {X:b1, Y:b4}
hidden T_i: F(holding(X) & X(F(on(X,Y))))
public q_i:
  Given parameter X of PDDL type object and parameter Y of PDDL type object,
  where X differs from Y, ensure that at some state predicate holding holds
  for argument X, and at a strictly later state predicate on holds for
  arguments X and Y.
```

The public query contains no `b1` or `b4`.

## Stage 5: Diversity-Balanced Deterministic Selection

Taking the first rollout for every problem would produce duplicates and bias
the benchmark toward alphabetically early actions. Instead, all retained
candidates receive an alpha-normalized semantic signature containing:

- profile;
- variable types and sharing pattern;
- inequality constraints;
- predicate/function symbols and argument order;
- hidden formula abstract syntax tree.

Ground object names and witness action names are excluded from the signature.

Problems are processed in canonical path order. Selection minimizes, in order:

1. prior usage count of the formula profile in that domain;
2. prior usage count of the semantic signature in that domain;
3. a domain-independent quality key preferring nonpersistent first milestones,
   shared variables, numeric coverage, and lower arity;
4. a structure-only SHA-256 tie-break built from first-occurrence canonical
   symbol/type identifiers, typed variable sharing, and object declaration
   positions.

The selection tie-break contains no domain, predicate, function, action, type,
or object spelling. Raw symbols remain in the reporting signature and rendered
query because they are part of the translation task, but they cannot influence
which candidate is selected.

This policy improves coverage but does not make duplicate semantics impossible.
The manifest retains duplicate rows because each binding belongs to a different
problem. Evaluation MUST report both micro accuracy over rows and macro accuracy
over unique semantic signatures so repeated templates cannot dominate the score.

## Stage 6: Controlled Natural-Language Rendering

Rendering is a deterministic visitor over the hidden structured formula. It
does not use a language model or hand-written domain glosses.

Atoms are rendered with explicit PDDL identifiers:

```text
on(X,Y)
-> predicate on holds for arguments X and Y

capacity(X) = 1
-> numeric function capacity for argument X equals 1
```

Parameter declarations and inequalities are explicit. The same construction
record always produces byte-identical text. The renderer MUST NOT inspect the
ground assignment when choosing wording.

## Natural-Language Manifest Contract

The aggregate `natural_language_manifest.jsonl` contains exactly one row per
selected test problem:

```json
{
  "sample_id": "blocksworld_on_p_50_0",
  "domain": "blocksworld-on",
  "problem_file": "src/domains/blocksworld-on/test/p-50-0.pddl",
  "catalog_file": "domains/blocksworld-on/catalog.json",
  "status": "constructed_temporal_query",
  "profile": "ordered_two_milestone",
  "construction_tier": "primary",
  "parameter_semantics": "externally_bound",
  "source_text": "Given parameter X ...",
  "declared_parameters": [
    {"name": "X", "pddl_type": "object"},
    {"name": "Y", "pddl_type": "object"}
  ],
  "constraints": [
    {"operator": "not_equal", "left": "X", "right": "Y"}
  ],
  "semantic_signature": "<sha256>",
  "failure_reason": null
}
```

The public row MUST NOT contain `gold_formula_ast`, `assignment`,
`witness_actions`, state facts, or state fingerprints.

The problem-complete manifest is retained for traceability and downstream
problem-level expansion. It is not the language-model call list.

## Deduplicated Translation Worklist

The colleague MUST call the model from `translation_worklist.jsonl`, generated
by:

```bash
uv run python scripts/build_temporal_translation_worklist.py \
  --manifest <public-handoff>/natural_language_manifest.jsonl \
  --output <public-handoff>/translation_worklist.jsonl
```

One worklist row is one unique complete translation input. Deduplication hashes:

```text
rendered domain system prompt
+ source_text
+ declared_parameters
+ constraints
+ parameter_semantics
```

It does not deduplicate by raw English alone. Rows from different benchmark
labels merge only when their rendered system prompts and every public semantic
input above are identical. All merged rows must additionally have one identical
hidden `semantic_signature`; otherwise construction fails closed as an
ambiguous translation input.

One worklist row has this shape:

```json
{
  "schema_version": 1,
  "translation_id": "tpl_<sha256>",
  "translation_input_signature": "<sha256>",
  "domain": "blocksworld-clear",
  "benchmark_domains": ["blocksworld-clear", "blocksworld-on"],
  "catalog_file": "domains/blocksworld-clear/catalog.json",
  "equivalent_catalog_files": [
    "domains/blocksworld-clear/catalog.json",
    "domains/blocksworld-on/catalog.json"
  ],
  "sample_id": "blocksworld_clear_p_50_0",
  "representative_sample_id": "blocksworld_clear_p_50_0",
  "source_text": "Given parameter X ...",
  "declared_parameters": [],
  "constraints": [],
  "parameter_semantics": "externally_bound",
  "semantic_signature": "<sha256>",
  "member_sample_ids": ["..."],
  "member_count": 2,
  "status": "constructed_temporal_query"
}
```

The row can be passed directly to `build_lifted_ltlf_user_prompt`; that function
exposes only the representative `sample_id` and semantic input fields. It never
passes `member_sample_ids`, benchmark membership, or deduplication metadata to
the model.

For the final version-1 artifact:

```text
1,228 problem-complete rows
496 domain-scoped semantic templates
475 unique complete model translation inputs
475 required primary language-model calls
```

The membership list is sufficient for the colleague to expand each predicted
translation back to its problem rows. Predicted LTLf generation and expansion
remain separate artifacts and are not performed by the NL benchmark builder.

## Complete Test-Split Scope

Version 1 contains every PDDL file in the complete `test/` split of:

```text
barman                 90
ferry                  90
gripper                90
logistics              90
miconic                90
rovers                 90
satellite              90
transport              90
numeric-ferry          90
numeric-miconic        90
numeric-minecraft      90
numeric-transport      90
blocksworld-clear      30
blocksworld-on         30
blocksworld-tower      77
depots                  11
total                 1228
```

Every problem MUST appear exactly once as either:

```text
constructed_temporal_query
source_witness_not_found
```

An unsupported PDDL construct or internal exception aborts the run before the
aggregate manifest is finalized. Such a partial directory is not a benchmark
artifact and MUST NOT be reported as construction coverage.

Construction coverage is reported over all 1,228 rows. Translation metrics
must never hide non-construction rows.

## Implementation Ownership

Local construction code:

```text
src/temporal_input/nl_benchmark.py
src/temporal_input/translation_worklist.py
scripts/build_temporal_nl_manifests.py
scripts/build_temporal_translation_worklist.py
tests/temporal_input/test_nl_benchmark_builder.py
tests/temporal_input/test_translation_worklist.py
```

Normative model-handoff prompt code:

```text
src/temporal_specification/prompts.py
src/temporal_specification/errors.py
tests/temporal_specification/test_prompts.py
tests/temporal_specification/test_errors.py
```

Construction may depend on `utils.pddl_parser`. Worklist deduplication depends
on the normative system-prompt renderer because equality is defined over the
actual model context, not approximate catalogue similarity. Neither path may
depend on generalized planning backends, atomic-module synthesis, query
wrappers, Jason, or VAL.

Public interfaces:

```python
def build_problem_candidates(
    *,
    domain_file: Path,
    problem_file: Path,
    config: BuildConfig,
) -> tuple[Candidate, ...]: ...

def build_domain_nl_manifest(
    *,
    domain_dir: Path,
    config: BuildConfig,
) -> DomainNLManifest: ...

def write_natural_language_benchmark(
    *,
    domains_root: Path,
    output_root: Path,
    domain_names: Sequence[str],
    config: BuildConfig,
) -> dict[str, object]: ...

def build_translation_worklist(
    rows: Sequence[Mapping[str, object]],
    *,
    prompt_context_by_catalog_file: Mapping[str, str],
) -> tuple[dict[str, object], ...]: ...

def write_translation_worklist(
    *,
    manifest_path: Path,
    output_path: Path,
) -> dict[str, object]: ...
```

Canonical command:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python \
  scripts/build_temporal_nl_manifests.py
```

Optional bounds are explicit command-line arguments. Every completed problem
prints one concise line; full metadata is written to artifacts.

## Validation Requirements

Before publishing a manifest, the builder MUST verify:

- every witness action is applicable in its predecessor state;
- predicate and numeric effects reproduce each stored successor state;
- all state fingerprints in a witness are distinct;
- the grounded hidden oracle is true on the witness trace under finite-trace semantics;
- every lifted parameter has a type-compatible hidden assignment;
- no problem object appears in public query text;
- public rows contain no hidden oracle, assignment, witness, or state data;
- the row count exactly equals the test-file count;
- sample identifiers and semantic signatures are deterministic;
- predicate/action renaming changes only the corresponding symbols;
- irrelevant static-fluent injection does not alter action legality or selected semantics;
- a second run with identical inputs produces byte-identical manifests.

The implementation proves action applicability and state replay during
construction, then independently evaluates the hidden formula abstract syntax
tree on the replayed finite trace before accepting the candidate.

## Failure Semantics

| Code | Meaning |
| --- | --- |
| `source_witness_not_found` | No eligible candidate was found under the pre-registered rollout bounds; this is not an impossibility proof. |
| `unsupported_pddl_feature` | The domain uses syntax outside the declared construction fragment; abort the run. |
| `object_type_unknown` | A selected object has no usable declared type; abort the run. |
| `controlled_renderer_error` | Deterministic rendering failed; abort the run. |
| `internal_error` | An unexpected implementation failure; abort the run and retain the traceback. |

No failure may be converted into a fabricated singleton query or a query based
on the original PDDL goal.

## Metrics and Paper Claim

Construction reports:

- constructed rows / all test problems;
- profile counts by domain;
- unique semantic signatures and duplicate multiplicities;
- propositional versus numeric milestone counts;
- witness action-length distribution;
- construction time and failure code by problem;
- micro row count and macro semantic-signature count.

The defensible construction claim is:

> From each held-out PDDL initial state, the bounded symbol-independent builder
> searches for short legal state-changing traces, mines one of five declared
> temporal profiles, lifts the selected grounded milestones into typed
> parameters, and deterministically renders a controlled natural-language
> query. The public handoff excludes the witness, grounding, original goal, and
> hidden temporal oracle; all construction failures remain visible.

Non-claims:

- rollout search is not complete and does not solve the original PDDL problem;
- one grounded witness does not prove universal realizability for every typed assignment;
- version 1 does not cover unrestricted natural language or unrestricted LTLf;
- duplicate semantic signatures may remain and must be macro-averaged;
- successful construction does not establish model translation accuracy;
- this document does not validate downstream planning or execution.
