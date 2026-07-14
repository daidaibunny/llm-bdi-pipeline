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
| **Natural-language manifest** | The problem-complete public handoff containing one row per test problem, with `q_i`, declared parameters, constraints, profile, and a reference to the domain catalogue. It contains no assignment, witness, or gold formula. Version 1 has 1,228 rows. |
| **Translation input signature** | A SHA-256 hash of the complete language-model input: the rendered domain system prompt plus `source_text`, declared parameters, constraints, and parameter semantics. Two rows may share this signature only when the model would receive byte-equivalent semantic inputs. |
| **Translation worklist** | The deduplicated public call list containing one row per unique complete language-model input. Each row retains `member_sample_ids` so one prediction can be expanded back to every covered problem row. Version 1 has 475 rows and therefore requires 475 primary model calls. |
| **Construction audit** | The private artifact containing `T_i`, `theta_i`, `pi_i`, and state fingerprints. It allows reproducibility checks without leaking answers to the translation model. |
| **Smoke translation set** | Five pre-registered worklist rows, one for each supported formula profile, used to check model connectivity, prompt rendering, JSON capture, and public payload validation before continuing the primary run. These five calls are retained as part of the 475 primary calls; they are not rerun. |
| **Prediction contract validation** | A fail-closed check of one model response against the public input and domain catalogue. It verifies the exact JSON shape, copied parameters and constraints, declared symbols, arities, types, atom table, and allowed operators. It does not inspect the hidden gold formula. |
| **DFA language equivalence** | Exact comparison of the finite-trace languages accepted by the hidden gold deterministic finite automaton and predicted deterministic finite automaton. A product-state search either proves equality or returns a distinguishing finite valuation trace. |
| **Hidden-witness acceptance** | Replay of the sealed PDDL action witness `pi_i`, followed by evaluation of both gold and predicted deterministic finite automata on the resulting state trace. It checks the prediction on every problem-level binding covered by a deduplicated translation. |
| **Execution-trace validation** | Optional downstream validation of a generated primitive-action plan. Every action must replay legally from `P_i`, an independent PDDL plan verifier must accept it against a neutral final goal, and both gold and predicted deterministic finite automata must accept the complete state trace. |
| **Validated append dataset** | One per-domain LTLf JSON artifact containing only predictions that passed the public payload contract, exact DFA language equivalence, and hidden-witness acceptance. It is the only prediction artifact eligible for later temporal-goal append. |
| **Structured non-construction** | A retained row such as `source_witness_not_found`. A problem is never silently dropped. |

Requirement words are normative:

- **MUST** is required for a paper result to count.
- **MUST NOT** marks a semantic or methodological error.
- **SHOULD** is the pre-registered default.
- **MAY** describes an extension outside the primary result.

## Scope and Handoff Boundary

This repository owns the benchmark-construction path:

```text
PDDL domain D + held-out test problem P_i
-> typed bounded legal rollouts
-> nontrivial temporal candidate pool
-> deterministic profile/signature-balanced selection
-> hidden lifted semantic oracle T_i + assignment theta_i + witness pi_i
-> deterministic controlled-English query q_i
-> problem-complete natural-language manifest
-> deduplicated translation worklist
```

It also owns the post-model validation path:

```text
canonical translation_predictions.jsonl
-> public prediction-contract validation
-> real LTLf2DFA/MONA compilation
-> exact hidden-gold/predicted DFA language equivalence
-> hidden PDDL witness replay and finite-trace acceptance
-> optional execution trace + independent VAL + DFA acceptance
-> validation reports + validated per-domain append datasets
```

The public input handoff has two required files. `natural_language_manifest.jsonl`
retains all 1,228 problem rows for traceability and result expansion.
`translation_worklist.jsonl` deduplicates those rows into 475 unique complete
model inputs and is the only language-model call list. The colleague owns the
model calls and invokes the provided post-model validator after freezing all
predictions. The hidden benchmark audit is local validation data and MUST never
be included in a model message or retry.

The local builder MUST NOT call a language model, classical planner, generalized
planner, AgentSpeak runtime, or downstream temporal controller.

This repository also provides the normative prompt builders that define the
handoff contract. Providing prompt text does not move model execution into the
local construction scope.

## Colleague-Only Procedure

This section is the complete operational handoff to the colleague. It is split
into preflight, a five-call smoke, the remaining primary calls, and post-freeze
validation. Hidden validation results MUST NOT be used to edit a prediction,
change a prompt, add a retry, or tune the model configuration.

### Phase 0: Preflight

The colleague MUST:

1. Use the finalized public handoff directory
   `artifacts/temporal_nl_handoffs/temporal-nl-v1-20260711-final/` and verify
   that it contains
   `handoff_manifest.json`, `natural_language_manifest.jsonl`,
   `translation_worklist.jsonl`, and every referenced
   `domains/<domain>/catalog.json`.
2. Check out a new development branch from the latest `main`. Treat
   `translation_worklist.jsonl` as the only primary model-call list. Its 475
   rows require exactly 475 primary calls. Do not call the model once for each
   of the 1,228 rows in `natural_language_manifest.jsonl`.
3. For each worklist row, load its `catalog_file` relative to the handoff root,
   render the system message with `build_lifted_ltlf_system_prompt(catalog)`,
   and render the user message with `build_lifted_ltlf_user_prompt(row)`.
4. Use one pre-registered model version, decoding configuration, full prompt
   configuration, and retry budget for the entire primary run. Record these
   settings and the prompt-source commit with every run. All 475 primary records
   MUST use the same `model_id`, `model_parameters`, and `prompt_config`, and
   `prompt_source_commit` MUST equal the commit sealed in `handoff_manifest.json`.
5. Validate every response before acceptance with
   `validate_prediction_payload(...)`: require the exact eight-key JSON
   payload, exact copied sample identifier/parameters/constraints, complete and
   nonredundant atom definitions, catalogue-valid symbols and arities,
   subtype-compatible arguments, integer numeric equalities, and only `F`, `X`,
   `U`, `&`, and `!`.
6. Retry only model-correctable failures using `build_retry_feedback(...)` and
   `build_retry_user_message(...)`. Network/model timeouts and
   LTLf2DFA/MONA/runtime failures are infrastructure outcomes, not instructions
   to simplify or change the query.

### Phase 1: Five-call smoke

7. Run exactly the following five pre-registered translation identifiers first.
   They are the lexicographically first worklist rows for the five supported
   formula profiles. The profile labels are local selection metadata and MUST
   NOT be added to either model message:

   ```text
   tpl_000d5be64911d3435d804c820b5e75f6bdf448f34a6945ac022e6dbb4b0aaefb
   tpl_001484b28b81589305521f6298a5d2686e2b18c17de5dd455e4c8233487c41c3
   tpl_00b322960aee1adf91aabfa6876975d6d495a40c4c1aba230dc875cef4415863
   tpl_01c942f143dae8d45b32837af9bc3b8e9a191bab11ac50f82f5be306cdb7c609
   tpl_37c39e3e8fac0d969fcb37ff03757ddd556b1b13528423a5ca3b167914d65e38
   ```

8. For the smoke, inspect only infrastructure and public contract outcomes:
   prompt rendering, model response capture, canonical record construction,
   `validate_prediction_payload(...)`, and restricted-LTLf parsing. Do not run
   hidden-gold equivalence on an incomplete five-row file and do not inspect the
   private construction audit. If an implementation bug is found, discard the
   incomplete run, fix it, and restart all five under one newly recorded run.
   If the pipeline is sound, retain these exact five canonical records as the
   first completed members of the primary run.

### Phase 2: Complete and freeze all predictions

9. Continue with the remaining 470 worklist rows using the identical model,
   decoding parameters, prompt configuration, prompt-source commit, validation
   code, and pre-registered retry budget. Do not rerun the five smoke calls.
10. Write exactly one canonical record per `translation_id` to
   `translation_predictions.jsonl`. An accepted record has the following exact
   outer shape; `prediction` is the validated eight-key model payload and
   `raw_response` is the unmodified model response:

   ```json
   {
     "schema_version": 1,
     "translation_id": "tpl_<sha256>",
     "outcome": "accepted",
     "attempt_count": 1,
     "model_id": "<provider/model-version>",
     "model_parameters": {"temperature": 0},
     "prompt_config": "full",
     "prompt_source_commit": "<git-commit>",
     "raw_response": "<exact response text>",
     "prediction": {"schema_version": 1},
     "terminal_error": null
   }
   ```

   A terminal failure uses `outcome: "terminal_failure"`, `prediction: null`,
   and a non-null `terminal_error` object. Do not omit a failed worklist row.
   For an accepted record, parsing `raw_response` as JSON MUST reproduce
   `prediction` exactly; post-hoc edits are not accepted as the model response.
11. Require exactly 475 unique records and no missing worklist identifier.
    Freeze the file before hidden validation and record its SHA-256 digest. Any
    later correction is a new run with a new output directory; never edit the
    frozen file in place.
12. Retain the 475-row `translation_predictions.jsonl` without manually
   duplicating predictions. The local goal-validation batch uses
   `member_sample_ids` to expand it to all 1,228 problem rows after model output
   has been frozen; retries are reported separately from primary calls.
13. Fail closed if the worklist does not contain 475 unique
   `translation_input_signature` values, if its membership does not cover every
   manifest `sample_id` exactly once, if a referenced catalogue is missing, or
   if a response remains invalid after the pre-registered retry budget.

### Phase 3: Run post-freeze temporal-goal validation

14. After all 475 predictions are frozen, run:

    ```bash
    PYTHONDONTWRITEBYTECODE=1 uv run python \
      scripts/validate_temporal_goal_predictions.py \
      --handoff-root \
        artifacts/temporal_nl_handoffs/temporal-nl-v1-20260711-final \
      --benchmark-root \
        artifacts/temporal_nl_benchmarks/temporal-nl-v1-20260711-final \
      --predictions-file <run-dir>/translation_predictions.jsonl \
      --output-dir <run-dir>/goal_validation
    ```

    This complete-coverage command intentionally rejects partial prediction
    files. It validates 475 translation inputs, expands them through sealed
    `member_sample_ids`, and validates all 1,228 problem rows.
15. Treat `semantic_mismatch`, `witness_rejected`, terminal model failures, and
    contract errors as measured outcomes. Do not feed hidden distinguishing
    traces, hidden formulas, assignments, witnesses, or error details back to
    the model. Treat MONA, malformed sealed audit, PDDL replay disagreement, or
    missing dependency errors separately as infrastructure or benchmark errors.
16. Deliver the frozen predictions and the complete validation directory:

    ```text
    <run-dir>/translation_predictions.jsonl
    <run-dir>/goal_validation/summary.json
    <run-dir>/goal_validation/translation_validation_results.jsonl
    <run-dir>/goal_validation/problem_validation_results.jsonl
    <run-dir>/goal_validation/validated_append_datasets/<domain>.json
    ```

    Also deliver the run configuration and SHA-256 digest of the predictions
    file. The validation command may exit nonzero when measured model outcomes
    fail; the generated reports remain required evidence and MUST be retained.
17. If execution traces already exist, they MAY additionally be checked with
    `--execution-traces-root <trace-dir>` and an available VAL command. This is
    a separate downstream execution experiment, not a prerequisite for the
    translation result. Absence of execution traces must be reported as
    `not_attempted`, never as translation success or failure.

The colleague MUST NOT put `profile`, `construction_tier`,
`semantic_signature`, `translation_id`, `member_sample_ids`, benchmark-domain
membership, the original PDDL goal, hidden assignment, witness trace, hidden
formula, or construction audit into a model message. The prompt builders
already enforce this boundary; deduplication metadata is used only for local
bookkeeping and result expansion.

The colleague's model-call responsibility ends when
`translation_predictions.jsonl` is frozen. The colleague then invokes the
repository's deterministic validator and returns its unedited reports; hidden
validation remains local computation and is never a model input.

## Canonical Repository TEG Benchmark Release

The accepted version-1 result is tracked under:

```text
paper_artifacts/temporal_goal_benchmark/v1/
  benchmark.json
  manifest.json
  release_validation.json
  domains/<domain>.json
  model_run/translation_predictions.jsonl
  validation/translation_validation_results.jsonl
  validation/problem_validation_results.jsonl
  source/*.tar.gz
```

These files have three distinct roles. The `source/` archives are immutable
chain-of-custody evidence: the public handoff, construction audit sealed during
model inference, and model-run delivery. Publication normalizes only
machine-local directory fields in the delivery archive, records the original
archive digest and the exact normalized members, and leaves predictions and
semantic validation rows unchanged. `benchmark.json` is the canonical
single-file research benchmark containing all 16 domains and 1,228 cases.
`domains/<domain>.json` are byte-preserved operational views accepted by the
existing single-domain temporal-goal appender. One aggregate file is therefore
the paper benchmark, while domain views preserve the invariant that one domain
has one maintained AgentSpeak library.

The manuscript denotes the query-independent atomic module core by
`M_D` and the plans generated for one bound query `q` by `Q_q`. For an ordered
sequence `q_1, ..., q_k`, the sole maintained library is
`L_D^[k] = M_D union (union_{i=1}^k Q_{q_i})`; appending a new query `q` yields
`L_D^[k+1] = L_D^[k] union Q_q`. These symbols distinguish semantic roles; they
do not introduce separate persisted libraries. The operational domain view
continues to append `Q_q` to the same per-domain AgentSpeak file.

Every canonical case contains the public query, profile, lifted formula,
typed parameters, explicit predicate or `numeric_equality` atom kind, one
sealed problem binding, translation membership, and validation certificates.
It deliberately excludes the hidden gold formula, witness actions, and state
fingerprints. The benchmark is released only after model predictions are
frozen, so publishing model outputs and bindings cannot affect the completed
translation run.

The release is generated by
`scripts/build_temporal_goal_benchmark.py`. The command verifies all three
archive SHA-256 digests, safely ignores only recognized platform metadata,
re-runs real LTLf2DFA/MONA equivalence and all 1,228 PDDL witness replays, and
requires the delivered and independently generated translation reports,
problem reports, normalized summary, and 16 domain datasets to match. Any
semantic difference fails closed. `release_validation.json` records the MONA
version and executable digest used by this independent reproduction.

Version 1 contains 475 unique model translation inputs and 1,228 grounded
problem cases. Translation success means exact gold/predicted DFA-language
equivalence. Problem success means legal hidden-witness replay, sealed state
fingerprint agreement, and acceptance by both DFAs. Neither metric is an
execution metric. `benchmark.json` therefore records
`execution_status: not_attempted`; later Jason, VAL, and execution-trace DFA
acceptance are reported separately and cannot alter the frozen translation
scores.

The public dataset landing page is
`paper_artifacts/temporal_goal_benchmark/v1/README.md`. Dataset-level CC BY 4.0
and citation metadata are carried by `LICENSE.md` and `CITATION.cff`. The
release is fail-closed under `scripts/verify_public_teg_dataset.py`, which checks
counts, hashes, archive safety, and the absence of machine-local absolute paths.

The canonical execution runner is:

```bash
NUM_WORKERS=8 bash scripts/run_temporal_goal_benchmark_execution.sh
```

It uses the latest complete timestamped atomic AgentSpeak library batch unless
`ATOMIC_BATCH_ID` names one explicitly. Every problem row is compiled as a
separate externally bound invocation: the lifted formula and atom table remain
the translation unit, while the sealed case binding grounds only its
query-local wrapper. For example, `on(X,Y)` with `X=b1,Y=b4` calls
`!on(b1,b4)`; the shared atomic module remains `+!on(X,Y)`. A released binding
that differs from the private construction-audit assignment aborts loading.

For every selected case the runner records distinct statuses for DFA/controller
compilation, Jason completion, PDDL replay, neutral-goal VAL, gold-DFA
acceptance, and predicted-DFA acceptance. Unsupported temporal structure,
numeric-preservation gaps, negative-guard failures, timeout, and validator
infrastructure errors are not collapsed into one generic failure. The run root
is `artifacts/temporal_goal_execution_runs/<run-id>/`; `summary.json` contains
domain and formula-profile aggregates, while `cases/<domain>/<sample-id>/`
contains the auditable per-case artifacts. A nonzero process exit means at least
one selected case did not satisfy every end-to-end obligation; it does not
discard the completed records.

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
deterministically by the local builder. The operational model-call procedure is
specified only in **Colleague-Only Procedure** above.

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

### Prediction-validation contract

An implementation accepting a model response MUST check:

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
artifacts/temporal_nl_handoffs/<handoff_id>/
  handoff_manifest.json
  input_audit_report.json
  natural_language_manifest.jsonl
  translation_worklist.jsonl
  domains/<domain>/catalog.json
  domains/<domain>/natural_language_manifest.json
```

Both JSONL files are required. The first is the problem-complete record and the
second is its deduplicated model-call list. Neither contains private
construction evidence.

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

`translation_worklist.jsonl` is generated from the problem-complete manifest
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

The membership list is sufficient to expand each predicted translation back to
its problem rows. Predicted LTLf generation and expansion remain separate
artifacts and are not performed by the natural-language benchmark builder.

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

Post-model temporal-goal validation code:

```text
src/temporal_specification/prediction_validation.py
src/evaluation/temporal_goal_validation.py
src/evaluation/temporal_validation_batch.py
src/evaluation/external_plan_verifier.py
scripts/validate_temporal_goal_predictions.py
tests/temporal_specification/test_prediction_validation.py
tests/evaluation/test_temporal_goal_validation.py
tests/evaluation/test_temporal_validation_batch.py
tests/evaluation/test_external_plan_verifier.py
```

Construction may depend on `utils.pddl_parser`. Worklist deduplication depends
on the normative system-prompt renderer because equality is defined over the
actual model context, not approximate catalogue similarity. Neither path may
depend on generalized planning backends, atomic-module synthesis, query
wrappers, Jason, or VAL.

Post-model validation is a separate path. It depends on the sealed private
construction audit, the real LTLf2DFA/MONA toolchain, PDDL action replay, and,
only when execution traces are supplied, an independent VAL-compatible plan
verifier. It does not call the translation model or modify model responses.

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

def validate_prediction_payload(
    payload: Mapping[str, object],
    *,
    expected_sample: Mapping[str, object],
    catalog: Mapping[str, object],
) -> ValidatedLTLfPrediction: ...

def run_temporal_goal_validation_batch(
    *,
    handoff_root: Path,
    benchmark_root: Path,
    predictions_file: Path,
    output_dir: Path,
    project_root: Path,
    domains_root: Path,
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

Before publishing the public handoff, the worklist builder MUST additionally
verify:

- every constructed manifest `sample_id` occurs in exactly one
  `member_sample_ids` list;
- every `translation_id` and `translation_input_signature` is unique;
- every merged worklist row has one unambiguous `semantic_signature`;
- every referenced catalogue exists under the handoff root;
- regeneration from the same manifest and prompt source is byte-identical;
- the finalized version-1 counts are 1,228 problem rows and 475 unique model
  inputs.

The implementation proves action applicability and state replay during
construction, then independently evaluates the hidden formula abstract syntax
tree on the replayed finite trace before accepting the candidate.

After freezing `translation_predictions.jsonl`, the temporal-goal validator
MUST additionally verify:

- the predictions file has exactly one canonical record for every one of the
  475 worklist identifiers and no additional identifier;
- all records use one model identifier, one decoding-parameter object, the
  `full` prompt configuration, and the prompt-source commit sealed in the
  handoff manifest;
- accepted `raw_response` text parses to exactly the stored prediction, with no
  manual correction between the two fields;
- every prediction passes the public payload, catalogue, arity, type, atom-table,
  parameter, constraint, and restricted-operator checks;
- the gold and predicted formulas are independently compiled by the real
  LTLf2DFA/MONA toolchain and accept exactly the same finite-trace language;
- each prediction is expanded through sealed membership to all covered problem
  rows exactly once;
- each hidden PDDL witness replays legally and is accepted by both the gold and
  predicted deterministic finite automata;
- only translation/problem pairs passing all required gates enter a validated
  append dataset;
- infrastructure and benchmark-consistency errors remain separate from model
  contract errors and semantic mismatches.

When an execution trace is supplied, execution success MUST additionally
require legal PDDL replay, independent VAL acceptance against a neutral final
goal, gold-DFA acceptance, and predicted-DFA acceptance. A trace that is absent
or was not attempted does not affect the translation-only result.

The one explicit exception is a zero-action execution. LTLf is evaluated on a
non-empty state trace, so zero actions produce the singleton trace containing
only the PDDL initial state. VAL 1.4 has no accepted empty-plan syntax and
reports a zero-byte plan as malformed. The validator MUST NOT insert a noop,
because doing so would add a state transition and can change strong-Next and
Until truth. Instead it MUST require successful zero-step PDDL replay, exactly
one replayed state, gold- and predicted-DFA acceptance, and an explicit Jason
success with an empty committed trace. It records the action-legality
certificate as `vacuous_zero_action_pddl_replay` and records VAL as not
applicable rather than successful. Non-empty traces still require VAL.

The execution runner advances the same grounded deterministic finite automaton
after the initial valuation and after every successful primitive PDDL action.
Its query-local monitor-state and accepting beliefs select appended AgentSpeak
transition controllers; they are not PDDL fluents or hidden replacements for
the formula. For same-source/same-target MONA valuation cubes, controller
construction may use only their common achievement objective, while monitor
advancement still evaluates each complete original cube. Positive, negative,
and numeric atoms therefore retain finite-trace semantics at primitive-action
boundaries. This execution contract does not imply that the controller can find
an action strategy for every satisfiable PDDL-times-LTLf product. A syntactically
and semantically valid query can still produce `execution_rejected` or timeout
when the atomic library and schema certificates provide no applicable progress
action; that outcome is not an input-translation error.

A transition helper checks completion after one full balanced-tree repair pass.
It returns when the runtime monitor then differs from that helper's source state,
not only when it equals the immediately adjacent target state; otherwise it
replays the same transition. One atomic module may contain several primitive
actions, and the monitor can therefore cross several deterministic finite
automaton edges before the module returns. Source-state exit does not interrupt
that module or the certified suffix of the current pass. Every suffix leaf is
either an observation or a previously certified repair that preserves the
established signed prefix, and every primitive suffix action advances the exact
runtime monitor. The suffix may therefore reach a rejecting state, but it cannot
hide that transition or manufacture success: no accepting belief is emitted,
and the top-level controller has no success plan for that state. After the pass,
source-state exit lets the top-level dispatcher continue from the actual
monitored state and prevents replaying an already completed transition.

For a cyclic threat resolved by an enforced atomic-branch portfolio, helper
selection is scoped to each ordered guard-literal occurrence. Two occurrences
of the same predicate may therefore call different query-local aliases when
their already-established sibling sets differ. The appender may share an alias
only when the certified branch portfolios are identical. Certificate metadata
records the literal index, complete literal atom, and selected source branch
names; a recursive strategy label is emitted only when the selected portfolio
actually contains a recursive atomic branch.

Positive integer numeric equalities may receive a schema-derived one-action
repair only under a constant-delta certificate. Unit changes use a strict
directional comparison and may be replayed monotonically; larger changes require
the exact predecessor value. A single action may establish a complete mixed
Boolean/numeric guard only when symbolic execution proves every required net
effect. Negated numeric equality remains an exact observation unless a separate
certified change-away strategy exists.

For Until profiles, literals common to every non-progress self-loop cube are
treated as source-state invariants during strategy synthesis. The benchmark
fragment has one positive progress literal per such state. Every primitive
prefix of a selected action-only macro must preserve those invariants until the
progress literal is established. Predicate preparation reduces the count of
missing producer preconditions; numeric preparation reduces a constant-bounded
prerequisite deficit without changing the target fluent. Repeated numeric steps
use effect-derived non-unification guards to avoid protected objects, while an
invariant-consuming terminal step is allowed only at the exact numeric
predecessor. All nested module variables are alpha-renamed away from query and
outer-producer variables before composition.

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

Post-model validation uses separate outcome classes:

| Outcome | Meaning |
| --- | --- |
| `prediction_contract_error` | The model response violates the public JSON, catalogue, typing, parameter, atom-table, or formula-fragment contract. |
| `semantic_mismatch` | Both formulas compiled, but exact DFA product search found a finite trace accepted by only one formula. |
| `witness_rejected` | The prediction was language-equivalent at translation level only if this status cannot occur under a consistent audit; retain it as benchmark-consistency evidence rather than silently overriding it. |
| `terminal_model_failure` | The pre-registered model/retry procedure did not produce an accepted payload. |
| `validation_infrastructure_error` | MONA, LTLf2DFA, file, dependency, or other validation infrastructure failed; this is not model inaccuracy. |
| `problem_validation_error` | A sealed problem, assignment, witness, PDDL replay, or benchmark linkage failed consistency checking. |
| `execution_rejected` | An optional generated plan failed PDDL replay, independent VAL, gold-DFA acceptance, or predicted-DFA acceptance. |

## Temporal Compiler Comparison Protocol

Temporal translation accuracy and temporal action-strategy compilation are
different experiments. Translation compares predicted and sealed gold DFA
languages before execution. Compiler ablations begin only after one validated
lifted LTLf payload, binding, and real MONA-derived DFA have been fixed.

The primary temporal baseline is `dfa_aware_unprotected`: it retains the real
DFA, source-state dispatch, primitive-step monitor, and the same atomic-library
hash, but serializes conjunction literals in a deterministic canonical order
without completion-effect threat ordering or preservation-safe branch
portfolios. It is an evaluation mode rather than a production fallback. The
full method adds effect-certified ordering and branch portfolios. A second
paired ablation changes only the AgentSpeak control structure from flat sibling
plans to the balanced binary repair tree. A semantic-boundary ablation advances
the monitor only when an atomic module returns and is evaluated against cases
whose intermediate primitive states matter.

Every temporal variant must record the validated input hash, binding, DFA hash,
atomic JSON/ASL hashes, controller strategy, observation boundary, selected
literal order, and selected preservation portfolios. Required outcomes are
controller compilation or structured rejection, Jason success, neutral-goal
VAL, gold-DFA acceptance, predicted-DFA acceptance, action count, append time,
runtime or PAR-2, controller plan count, and maximum trigger fan-out. A failed
variant cannot change the input formula, binding, DFA, atomic library, or timeout
and retry under a different query.

A direct LTLf planning compilation is an external reference on its supported
grounded Boolean subset, not a replacement for this paired compiler ablation.
Pure-past systems such as Plan4Past require an independently verified
language-equivalent translation before their numbers can be compared. Existing
published results over different formula sets are related-work evidence only.

## Metrics and Paper Claim

Construction reports:

- constructed rows / all test problems;
- profile counts by domain;
- unique semantic signatures and duplicate multiplicities;
- propositional versus numeric milestone counts;
- witness action-length distribution;
- construction time and failure code by problem;
- micro row count and macro semantic-signature count.

Translation evaluation separately reports 475 unique-input results and their
expanded 1,228 problem-row results. A model is called once per unique input;
expansion does not create additional primary calls. Required reporting includes
contract-valid rate, exact DFA-equivalent rate, terminal model failures,
infrastructure errors, hidden-witness acceptance, micro problem-row accuracy,
and macro accuracy over unique translation inputs. Optional execution results
are reported separately and never folded into translation accuracy.

The pinned downstream execution result is
`artifacts/temporal_goal_execution_runs/teg-paper-clean-e28bcea4`. At commit
`e28bcea4`, all 1,228 released problem-level bindings obtained an explicit Jason
success marker, a complete primitive PDDL trace accepted by neutral-goal VAL,
and acceptance by both gold and predicted DFAs. This is execution evidence for
the released bindings and supplied atomic-library hashes; it is not additional
translation-model calls and is not a claim of universal realizability for all
type-compatible assignments.

The executed controller is compiled from the frozen predicted payload after
exact gold/predicted DFA-language equivalence. The complete state trace is then
replayed against both automata. Accordingly, the result contains one execution
per problem binding and two independent DFA acceptance checks; it must not be
described as separate gold-controller and predicted-controller runs. Gold-only
semantic checking is additionally isolated by the conformance suite below.

Evaluation macros and tables are generated by
`scripts/generate_evaluation_tables.py`. The generator fails closed on a dirty
tracked execution revision, benchmark or prediction hash mismatch, incomplete
sample coverage, or an atomic-library hash mismatch. This is the only supported
path for inserting aggregate translation or execution counts into the paper.

The separate temporal semantic conformance suite is tracked under
`paper_artifacts/temporal_semantic_conformance/v1/`. It does not add or replace
benchmark rows. Its manually specified valuation traces are checked by both a
direct recursive evaluator and a real MONA-derived DFA. Two additional
integration cases verify initial-state acceptance for a predicate and a numeric
equality, including the zero-action singleton-state boundary described above.
Pinned clean-commit run `temporal-conformance-paper-67b82843` passes all 14
formula-semantics cases and both zero-action integration cases. Its complete
provenance and records are stored in the suite's `release_validation.json`.

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
- gold/predicted DFA equivalence establishes translation semantics, not that the
  downstream controller can realize every binding;
- hidden-witness acceptance proves one sealed realizable binding per problem,
  not universal realizability for all type-compatible assignments;
- downstream planning or execution is established only for supplied traces that
  separately pass PDDL replay, independent VAL, and both DFA acceptance checks.
