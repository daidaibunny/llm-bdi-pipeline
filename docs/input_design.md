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

Key terms used throughout:

- **PDDL** is the Planning Domain Definition Language domain/problem input.
- **TEG** is a temporally extended goal whose success depends on a finite state
  trace, not only the final state.
- **LTLf** is linear temporal logic interpreted over finite traces.
- **DFA** is the deterministic finite automaton produced from one LTLf formula.
- **MONA** is the external decision-procedure backend used by `ltlf2dfa`.
- **Lifted** means predicates contain typed parameters such as `on(X,Y)` rather
  than one fixed object assignment such as `on(b1,b2)`.
- **Gold** means a human-audited formal artifact used only as an evaluation
  oracle; it is never shown to the translation model.
- **ASL wrapper** means the query-local AgentSpeak(L) plans that invoke the
  reusable atomic plan library according to certified DFA progress transitions.

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

## Implementation Blueprint

This section is the implementation handoff. Later sections define the schemas,
semantics, benchmark protocol, and paper acceptance criteria in detail.

### Stage Interfaces

| Stage | Required input | Required output | Implementation rule |
| --- | --- | --- | --- |
| 1. PDDL catalogue | `domain.pddl` | Typed predicate/function catalogue with dynamic/static roles | Derive roles only from declarations and add/delete effects. |
| 2. Query translation | Catalogue + natural-language query record | Lifted template v2 or structured diagnostic | LLM returns the formula AST; deterministic code validates it. |
| 3. Invocation validation | Lifted template + `problem.pddl` + assignment | Typed runtime invocation | Bind every parameter exactly once; never expand all objects. |
| 4. Propositionization | Validated lifted template | Canonical propositional formula + reversible proposition map | Traverse the AST; do not regex-rewrite predicate strings. |
| 5. DFA construction | Propositional formula + map | Audited DFA artifact + raw MONA output | Use real `ltlf2dfa`/MONA under recorded limits; no fallback DFA. |
| 6. Query compilation | DFA + map + lifted template + atomic library | Parametric ASL query wrapper appended to the domain library | Restore atoms from the map; preserve template variables as goal arguments. |
| 7. Execution | Appended library + problem initial state + invocation | Jason status + committed primitive-action trace | Invoke `!g_template(theta(X),...)`; failed prefixes are diagnostic only. |
| 8. Temporal validation | Gold/predicted templates + invocation + committed trace | PDDL replay, DFA runs, equivalence, and validation record | End-to-end success uses PDDL legality and gold-DFA acceptance. |

No stage may infer missing semantics from a later stage. In particular, the DFA
builder does not repair an invalid LLM formula, and Jason success does not
replace independent trace validation.

Every rejected stage writes `temporal_input_diagnostic` with one stable code.
The minimum code set is:

| Stage | Required codes |
| --- | --- |
| PDDL catalogue | `pddl_parse_error`, `unsupported_pddl_feature` |
| Translation | `model_provider_error`, `model_response_schema_invalid`, `model_identity_mismatch` |
| Semantic validation | `unknown_symbol`, `predicate_arity_mismatch`, `argument_type_mismatch`, `unsupported_formula_operator` |
| Invocation | `invalid_grounding`, `incomplete_assignment`, `parameter_constraint_violation` |
| Propositionization | `propositionization_error`, `non_reversible_proposition_map` |
| DFA | the `ltlf2dfa_*`, `mona_*`, and `dfa_*` codes defined under state-explosion risk |
| Query compilation | `unsupported_controller_topology`, `missing_atomic_module`, `uncertified_transition_serialization` |
| Execution/validation | `jason_failed`, `jason_timeout`, `pddl_trace_invalid`, `gold_dfa_rejected` |

Unexpected implementation faults are not converted into semantic rejection;
they fail the run with `internal_error` and retain a traceback in the artifact
log.

### Repository Integration Map

The implementer MUST use these ownership boundaries:

| Path | Required change |
| --- | --- |
| `src/temporal_input/models.py` | New immutable models for query text, lifted template, invocation, proposition map, and diagnostics. |
| `src/temporal_input/schemas/*.schema.json` | New machine-readable closed JSON Schemas matching this document. |
| `src/temporal_input/pddl_catalog.py` | New domain-generic PDDL vocabulary/type/effect-role extractor. |
| `src/temporal_input/translator.py` | New provider-neutral LLM envelope builder, provider protocol, provenance recorder, and strict response parser. |
| `src/temporal_input/propositionizer.py` | New AST-to-proposition transformation and deterministic canonical renderer. |
| `src/temporal_input/benchmark_builder.py` | New formula-first benchmark construction and assignment selection logic. |
| `src/domain_level_planning/lifted_ltlf_goal_schema.py` | Keep schema v1 as a legacy reader only; do not extend its combined case/binding model for paper artifacts. |
| `src/evaluation/temporal_compilation/ltlf_to_dfa.py` | Reuse real MONA invocation, but add an entry point for an already-propositionized formula and explicit proposition map. The v2 path must bypass `PredicateToProposition.convert_formula`. |
| `src/evaluation/temporal_compilation/dfa_builder.py` | Accept the v2 propositionized artifact and emit the complete audited DFA artifact defined below. |
| `src/domain_level_planning/temporal_goal_appender.py` | Add a parametric append entry point; preserve query parameters in top-level and `trans` helper triggers/bodies. Keep v1 append only for legacy artifacts. |
| `src/evaluation/temporal_validation.py` | New independent PDDL trace replayer, proposition labeler, DFA runner, and gold/predicted validation-record writer. |
| `src/evaluation/dfa_equivalence.py` | New alpha-canonicalization and symmetric-difference DFA language-equivalence checker. |
| `src/main.py` | Add the three CLI contracts below without changing atomic-library compilation. |
| `pyproject.toml` | Include `temporal_input*`; add a JSON Schema validator dependency. |

The existing `dfa_adapter.py`, `dfa_controller.py`, certified-effect summaries,
and conjunctive transition serializer remain the capability gate after restored
PDDL atoms reach the Temporal Query Compiler.

The checked-in schema files MUST be named:

```text
query_text.schema.json
model_input_envelope.schema.json
parametric_ltlf_template.schema.json
temporal_invocation.schema.json
proposition_map.schema.json
dfa_artifact.schema.json
input_diagnostic.schema.json
temporal_validation.schema.json
```

### Existing and Required Capability

This table prevents an implementer from mistaking current code for the completed
version 2 path:

| Capability | Existing implementation | Required paper path |
| --- | --- | --- |
| Lifted JSON | Schema version 1 reader combines formulas and case bindings. | Version 2 keeps reusable templates separate from runtime invocations. |
| LTLf compilation | Real `ltlf2dfa` and MONA invocation exists. | Accept an already-propositionized formula and persist a reversible map and complete audit metadata. |
| DFA adaptation | Guard parsing and controller capability checks exist. | Consume version 2 proposition maps and preserve template parameters. |
| Query append | Version 1 emits zero-argument query and `trans` goals. | Emit `g_template(X,...)` and pass every required argument through every `trans` helper. |
| Execution | Jason can produce primitive PDDL action traces. | Mark a trace committed only after top-level query success; failed prefixes remain diagnostic. |
| Temporal validation | PDDL and achievement-goal validation exists. | Independently replay states and run both predicted and gold DFAs over the same finite trace. |
| TEG benchmark | No complete parametric natural-language benchmark builder exists. | Build formula-first, human-reviewed templates with certified positive and negative traces. |

### Required Public Python Interfaces

Names may change only if the replacement preserves these typed responsibilities:

```python
def build_pddl_catalog(domain_file: Path) -> PDDLCatalog: ...

def translate_parametric_query(
	*,
	query: ParametricTemporalQueryText,
	catalog: PDDLCatalog,
	template_id: str,
	provider: TemporalTranslationProvider,
) -> TranslationAttempt: ...

def parse_parametric_template(
	payload: Mapping[str, object],
	*,
	domain_file: Path,
) -> ParametricLTLfTemplate: ...

def validate_invocation(
	payload: Mapping[str, object],
	*,
	template: ParametricLTLfTemplate,
	problem_file: Path,
) -> TemporalQueryInvocation: ...

def propositionize_template(
	template: ParametricLTLfTemplate,
) -> PropositionizedLTLf: ...

def build_audited_dfa(
	propositionized: PropositionizedLTLf,
) -> DFAArtifact: ...

def append_parametric_temporal_template(
	*,
	plan_library: PlanLibrary,
	template: ParametricLTLfTemplate,
	dfa: DFAArtifact,
	domain_file: Path,
) -> PlanLibrary: ...

def validate_temporal_execution(
	*,
	domain_file: Path,
	problem_file: Path,
	invocation: TemporalQueryInvocation,
	committed_actions: Sequence[PDDLActionCall],
	predicted_template: ParametricLTLfTemplate,
	gold_template: ParametricLTLfTemplate,
) -> TemporalExecutionValidation: ...

def build_temporal_benchmark(
	*,
	domain_file: Path,
	problem_files: Sequence[Path],
	gold_templates: Sequence[ParametricLTLfTemplate],
	witness_provider: TemporalWitnessProvider,
) -> TemporalBenchmarkManifest: ...
```

All public functions MUST return typed values or raise a typed/structured
diagnostic. They MUST NOT return partially valid dictionaries after failure.
`TemporalTranslationProvider` supplies one raw model response plus provider
provenance; deterministic code owns validation and normalization.
`TemporalWitnessProvider` supplies candidate primitive-action traces; the
benchmark builder independently replays and accepts/rejects them before storing
them, so no provider can self-certify a case.

### Required Command-Line Interfaces

```bash
uv run python src/main.py translate-parametric-temporal-query \
  --domain-file src/domains/<domain>/domain.pddl \
  --query-json artifacts/input/query_text/<query_id>.json \
  --template-id <predicted_template_id> \
  --output-dir artifacts/input/templates/<domain>/<template_id>

uv run python src/main.py append-parametric-temporal-template \
  --domain-file src/domains/<domain>/domain.pddl \
  --template-json artifacts/input/templates/<domain>/<template_id>/template.json \
  --library-root artifacts/domain_libraries

uv run python src/main.py validate-parametric-temporal-invocation \
  --domain-file src/domains/<domain>/domain.pddl \
  --problem-file src/domains/<domain>/test/<problem>.pddl \
  --template-json artifacts/input/templates/<domain>/<template_id>/template.json \
  --invocation-json artifacts/input/invocations/<domain>/<invocation_id>.json \
  --library-root artifacts/domain_libraries \
  --output-dir artifacts/temporal_validation/<run_id>/<invocation_id>
```

Each command MUST print one concise completion/failure line and write detailed
metadata to files. It MUST NOT print the full LLM response, DFA, or metadata to
the terminal by default.

### Canonical Artifact Layout

```text
artifacts/input/query_text/<query_id>.json
artifacts/input/templates/<domain>/<template_id>/
  template.json
  llm_request.json
  llm_response.raw.json
  input_diagnostic.json                 # only on rejection
  proposition_map.json
  formula.ltlf
  dfa.json
  dfa.dot
  mona.stdout.txt
  mona.stderr.txt
artifacts/input/invocations/<domain>/<invocation_id>.json
artifacts/teg_benchmarks/<benchmark_id>/
  manifest.json
  templates.jsonl
  invocations.jsonl
  positive_traces/
  negative_traces/
artifacts/temporal_validation/<run_id>/<invocation_id>/
  committed_plan.plan
  state_trace.jsonl
  predicted_dfa_run.json
  gold_dfa_run.json
  val_output.txt
  validation.json
```

Generated template and evaluation artifacts are snapshots. Appended query plans
still live in the single canonical domain library under
`artifacts/domain_libraries/<domain>/`.

The benchmark `manifest.json` MUST map each `query_id` to its hidden
`gold_template_id`, list every invocation and trace hash, identify the PDDL
source commit and split, and record the witness-trace provider and version. This
manifest is evaluation metadata and MUST NOT be included in the model prompt.

### Dependencies and Runtime Configuration

- Python is managed by `uv`; the repository currently requires Python 3.12 or
  later.
- `ltlf2dfa>=1.0.2` and MONA are mandatory. Install MONA with
  `bash scripts/setup_mona.sh`.
- The current safe defaults are a 300-second MONA timeout and a 16-GiB memory
  limit. They may be configured, but every run records the actual values.
- Use the existing `dd` Binary Decision Diagram package to audit symbolic guard
  overlap/exhaustiveness and DFA products without enumerating `2^|AP|` when the
  alphabet is large.
- Add `jsonschema` through `uv add jsonschema`; every normative JSON example and
  fixture must validate against the checked-in schema.
- Jason and VAL remain execution dependencies, not Input translation
  dependencies.
- The LLM provider is injected behind a protocol. Model name, base URL, request
  identifier, prompt hash, generation parameters, and raw response are recorded;
  API keys are read only from environment variables and never persisted.

For reproducible translation, request structured JSON output when the provider
supports it, use deterministic decoding where available, and record all model
settings. No model name is part of the research algorithm.

### Implementation Order and Definition of Done

1. Add JSON Schemas and typed models; make every valid/invalid schema fixture
   pass before adding model calls.
2. Add the PDDL catalogue and strict LLM envelope/response validator.
3. Add AST canonicalization and propositionization; prove object-count
   invariance with the same template over small and large problems.
4. Add the propositionized real-MONA entry point and DFA audits.
5. Add parameter-carrying ASL wrappers and invocation goal arguments.
6. Add independent state replay, DFA monitoring, and formula equivalence.
7. Add benchmark generation, positive/negative trace certification, and the
   three evaluation tracks.
8. Add CLIs, concise logging, artifact manifests, documentation fixtures, and
   end-to-end tests.

Implementation is complete only when the same template and DFA hash are used
for at least two held-out problems and two assignments, Jason is invoked with
different concrete arguments, both traces are independently replayed, and the
gold DFA produces the expected accept/reject result.

### Required Test Matrix

The implementation MUST include automated tests for:

- every valid and invalid JSON fixture, including unknown-field rejection;
- undeclared predicates, wrong arity, wrong types, incomplete assignments, and
  violated parameter constraints;
- deterministic atom deduplication, formula rendering, hashing, and reversible
  proposition restoration;
- alpha-renaming and predicate/action renaming invariance;
- identical formula, proposition-map, and DFA hashes when only problem object
  count or runtime assignment changes;
- a real MONA smoke test plus timeout, memory, malformed-output, determinism,
  completeness, and state-limit failures;
- propagation of all parameters through the top-level ASL goal and every
  recursive `trans` helper;
- singleton-transition action equivalence with one direct atomic goal call;
- conjunction serialization, negative context guards, and fail-closed rejection
  of unsupported DFA topology;
- independent replay including the initial state, numeric updates, failed-prefix
  exclusion, positive acceptance, and PDDL-valid negative rejection;
- gold/predicted DFA equivalence and non-equivalence witnesses;
- one end-to-end template reused across two held-out problems and two distinct
  typed assignments without regenerating the DFA.

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

Query, template, and invocation records use schema version 2 because they
replace the combined version 1 contract. Supporting artifacts such as proposition
maps, DFA records, diagnostics, and validation records start at their own schema
version 1. Hashes use SHA-256 over canonical UTF-8 JSON: object keys are sorted,
insignificant whitespace is removed, and arrays retain their specified semantic
order. Raw model and tool outputs are hashed as bytes and are never
canonicalized before preservation.

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
        "state_role": "dynamic_fluent",
        "producible": true,
        "deletable": true
      },
      {
        "name": "on",
        "parameters": [
          {"position": 0, "pddl_type": "block"},
          {"position": 1, "pddl_type": "block"}
        ],
        "state_role": "dynamic_fluent",
        "producible": true,
        "deletable": true
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
  "requested_output": {
    "template_id": "tpl_blocks_clear_then_on_001",
    "template_role": "predicted",
    "output_contract": "parametric_lifted_ltlf_template_v2"
  }
}
```

Predicate roles MUST be derived from PDDL effects. `state_role` is
`dynamic_fluent` when the predicate occurs in any add/delete effect and
`static_context` otherwise. `producible` and `deletable` are independent
Booleans because one predicate can have both roles. Domain-specific prose MAY be
supplied for language grounding, but the executable compiler MUST NOT use that
prose as a replacement for predicate, arity, or type validation.

The orchestration code, not the model, assigns `template_id` and
`template_role`. A predicted identifier MUST be unique to one query/attempt.
The validator requires the response to echo both values exactly. Gold templates
use the same schema with `template_role: "gold"`, but are created by the audited
benchmark process rather than the translation model.

The provider request consists of one versioned system instruction and this JSON
envelope. The system instruction states the externally bound parameter
semantics, requires JSON matching the output schema, forbids invented symbols or
undeclared constants, and forbids explanatory text. Its exact bytes and SHA-256
hash are recorded. Few-shot examples, when used, belong to the training or
development partition and are recorded separately; no test query or gold
formula may appear in them.

### 3. Normalized Lifted LTLf Template

For a predicted template, the language model MUST return JSON only and echo the
orchestrator-owned identity fields. Gold and predicted templates use the same
normalized schema. Formula structure MUST be represented as an abstract syntax
tree; formula text is derived by deterministic rendering and is not independently
trusted.

```json
{
  "schema_version": 2,
  "artifact_kind": "parametric_lifted_ltlf_template",
  "goal_specification_kind": "temporal_extended_goal",
  "temporal_logic": "LTLf",
  "logic_profile": "typed_parametric_ltlf_v1",
  "query_id": "blocks_clear_then_on_001",
  "template_id": "tpl_blocks_clear_then_on_001",
  "template_role": "predicted",
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

Explicit `or` and implication are excluded from the
`typed_parametric_ltlf_v1` logic profile. This restriction does not imply that
MONA transition guards will be free of disjunction. Automaton minimization can
introduce arbitrary Boolean guards, which the DFA capability checker must
handle or reject explicitly.

The `typed_parametric_ltlf_v1` profile contains only
`not_equal(left, right)` parameter constraints between type-compatible declared
parameters or declared PDDL domain constants.
Problem-instance object names MUST NOT occur in a reusable lifted template;
they enter only through an invocation assignment. This restriction does not
forbid a constant declared by the PDDL domain itself.

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

The `typed_parametric_ltlf_v1` profile supports one declared numeric fluent
compared with one integer constant. Arbitrary arithmetic, real-valued
tolerances, function-to-function comparison, and optimization metrics MUST be
rejected unless their semantics are separately specified.

### 5. Runtime Invocation

Bindings belong to an invocation, not to the lifted template:

```json
{
  "schema_version": 2,
  "artifact_kind": "parametric_temporal_query_invocation",
  "invocation_id": "blocks_p01_clear_then_on_b1_b2",
  "query_id": "blocks_clear_then_on_001",
  "template_id": "tpl_blocks_clear_then_on_001",
  "gold_template_id": "gold_blocks_clear_then_on_001",
  "domain": "blocksworld-on",
  "problem_file": "src/domains/blocksworld-on/test/p01.pddl",
  "assignment": {"X": "b1", "Y": "b2"},
  "trace_scope": "query_invocation_to_top_level_completion",
  "original_pddl_goal_role": "provenance_only"
}
```

`template_id` identifies the wrapper executed by Jason. In Track B it is the
gold template; in Track C it is the predicted template. `gold_template_id`
always identifies the hidden evaluation oracle. The invocation validator MUST
check query/template linkage, total binding, object declaration, PDDL type
membership, constants, and parameter constraints before Jason execution.

### 6. Proposition Map

`ltlf2dfa` and MONA operate over propositional symbols. The propositionizer
MUST replace lifted atoms with safe opaque identifiers and persist a reversible
map:

```json
{
  "schema_version": 1,
  "artifact_kind": "lifted_proposition_map",
  "template_id": "tpl_blocks_clear_then_on_001",
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
  "template_id": "tpl_blocks_clear_then_on_001",
  "formula_sha256": "...",
  "proposition_map_sha256": "...",
  "construction": {
    "library": "ltlf2dfa",
    "library_version": "recorded-at-runtime",
    "backend": "MONA",
    "mona_version": "recorded-at-runtime",
    "mona_binary_sha256": "...",
    "timeout_seconds": 300
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
  "executed_template_id": "tpl_blocks_clear_then_on_001",
  "gold_template_id": "gold_blocks_clear_then_on_001",
  "executed_formula_sha256": "...",
  "gold_formula_sha256": "...",
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
    "predicted_dfa_run": "...",
    "gold_dfa_run": "...",
    "val_output": "..."
  }
}
```

`end_to_end_intent_success` is true only when the committed trace is PDDL-valid
and the **gold** DFA accepts it. Acceptance by the model's own predicted DFA is
not sufficient.

The state trace is JSON Lines with one record for every consumed PDDL state,
including `state_index: 0` for the invocation initial state. Each row records
the preceding primitive action or `null`, a canonical state hash, relevant
numeric values, and proposition labels for the executed and gold templates.
The state trace is derived evidence; the independent replayer MUST reconstruct
it from `domain.pddl`, `problem.pddl`, and `committed_plan.plan` rather than
trusting labels emitted by Jason.

## Constructing Natural-Language TEG Queries from PDDL

### Benchmark Scope

The paper-facing TEG benchmark covers the complete held-out `test/` split of
every currently selected domain:

| Benchmark group | Domains |
| --- | --- |
| Classical | `barman`, `ferry`, `gripper`, `logistics`, `miconic`, `rovers`, `satellite`, `transport` |
| Numeric fluent | `numeric-ferry`, `numeric-miconic`, `numeric-minecraft`, `numeric-transport` |
| Feature-definable serialized-width | `blocksworld-clear`, `blocksworld-on`, `blocksworld-tower`, `depots` |

"Complete test split" means every test problem appears in the benchmark
manifest and denominator. It does **not** mean generating one grounded formula
from every original PDDL goal. The generation unit is:

```text
per domain:
  4-8 reusable lifted gold templates
  x every held-out test problem
  x 1-3 deterministic typed assignments when certifiable
```

For each domain/problem/template combination, the builder MUST record exactly
one of:

- `certified_invocations`: one or more type-correct assignments with an
  independently PDDL-valid positive witness;
- `no_valid_assignment`: no assignment satisfies typing and template
  constraints;
- `no_positive_witness`: assignments exist but the bounded independent witness
  procedure cannot certify realizability;
- `unsupported_logic` or `unsupported_controller_topology`: the formula is
  outside the declared Input or controller capability.

The witness bound, planner/provider, timeout, and failure reason are recorded.
`no_positive_witness` means "not certified under the recorded procedure", not a
proof that the temporal goal is impossible.

### Artifact Cardinality and Form

| Scope | Generated artifact | Reuse rule |
| --- | --- | --- |
| One domain | PDDL catalogue | Shared by all templates and invocations in that domain. |
| One intended temporal meaning | One gold lifted template, one proposition map, and one gold DFA | Compiled once; contains parameters, never test-instance object names. |
| One natural-language wording | One query-text record | Linked to one hidden gold template; never contains a runtime assignment. |
| One template/problem pairing | Zero or more invocation records | Each supplies one external typed assignment. |
| One invocation | One independently certified positive witness | Checked by the gold DFA and never produced by the evaluated ASL library. |
| One translation attempt | Predicted template, map, DFA, wrapper result, and provenance | Compared with the hidden gold template; retries remain separate attempts. |

Every gold template MUST additionally have at least one type-correct,
PDDL-valid negative trace across its invocation set; a negative trace per
invocation SHOULD be stored when independently obtainable.

Each gold template has one controlled-English query and at least three
human-reviewed paraphrases. At least one paraphrase is independently
human-authored; an LLM-generated paraphrase MUST be reviewed and its generator
recorded. The same wording and lifted template are reused across assignments;
object-specific sentences such as "put b1 on b2" do not count as lifted-query
evaluation.

Assignment selection is deterministic and domain-independent. For each
template/problem pair, construct type-compatible object lists using subtype
closure. Enumerate the complete Cartesian product when its size is at most a
pre-registered candidate budget; otherwise sample tuple indices without
replacement using a seed derived from the benchmark, domain, problem, and
template hashes. Filter the resulting tuples by parameter constraints and
select at most three certified assignments from distinct initial
atom-valuation strata when possible. The budget, seed, product size, sampled
count, rejected count, and witness outcomes MUST be recorded; the default
candidate budget is 256. This procedure samples bindings, not formulas, and
never changes the lifted template or DFA.

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

For each PDDL domain, the benchmark builder MUST derive these non-exclusive
properties from the action schemas:

- `state_role = dynamic_fluent` when a predicate appears in any add/delete
  effect, otherwise `state_role = static_context`;
- `producible = true` when it appears in a positive add effect;
- `deletable = true` when it appears in a delete effect;
- `numeric_state_function` for each declared PDDL function with supported state
  semantics.

Predicate/function signatures include argument position and declared type.
Type checking uses the transitive PDDL subtype closure, and domain constants are
included with their declared types. No role is inferred from predicate names,
benchmark goals, or natural-language descriptions.

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

The deterministic renderer uses these `ltlf2dfa` tokens:

| Abstract-syntax-tree operator | Canonical text |
| --- | --- |
| `true`, `false`, `atom` | `true`, `false`, `ap_NNNN` |
| `not` | `!(phi)` |
| `and` | `(phi_1 & ... & phi_n)` |
| `next`, `eventually`, `always` | `X(phi)`, `F(phi)`, `G(phi)` |
| `until`, `release` | `(phi_1 U phi_2)`, `(phi_1 R phi_2)` |

Parentheses are emitted exactly as shown. The renderer operates only on safe
proposition identifiers, so PDDL punctuation never reaches the formula parser.

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

+!g_blocks_clear_then_on_trans_1(X, Y) : clear(Y) <-
	true.

+!g_blocks_clear_then_on_trans_1(X, Y) : not clear(Y) <-
	!clear(Y);
	!g_blocks_clear_then_on_trans_1(X, Y).

+!g_blocks_clear_then_on_trans_2(X, Y) : on(X, Y) <-
	true.

+!g_blocks_clear_then_on_trans_2(X, Y) : not on(X, Y) <-
	!on(X, Y);
	!g_blocks_clear_then_on_trans_2(X, Y).
```

Every query-local transition helper MUST receive the variables required by its
guard and recursive calls. One maintained domain library may contain many query
templates, but every template remains parametric and is invoked with concrete
arguments only at runtime, for example `!g_blocks_clear_then_on(b1, b2)`. The
shown helpers illustrate parameter propagation and declarative guard rechecking;
the actual number and guards of `trans` helpers MUST come from the audited DFA,
not from the surface order of the formula or natural-language sentence.

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

The denominator and artifact cardinality are fixed by **Benchmark Scope** above.
Assignments SHOULD cover small, medium, and large problems; already-true and
not-yet-true milestones; shared variables; threat/interference contexts;
resource-consuming contexts; and type/alias edge cases.

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

- every selected domain's complete test split is represented in the benchmark
  manifest, including structured skip/unsupported outcomes;
- each domain has 4-8 reusable lifted gold templates rather than one grounded
  formula per problem;
- every gold template has reviewed language, a certified positive witness, and
  at least one PDDL-valid gold-DFA-rejected trace;
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
