# LLM BDI Pipeline

This project generates high-level AgentSpeak(L) plan libraries from persisted LTLf
task specifications and PDDL benchmark domains.

The current architecture has two explicit levels:

- High level: use the stored LTLf formula for each benchmark query, compile it to
  a DFA with `ltlf2dfa`, and render DFA transitions as context-selected
  `+!g` AgentSpeak(L) plans.
- Low level: action or subgoal selection between DFA states is intentionally left
  open for the next design step.

## Core Flow

1. Load a PDDL domain from `src/domains/<domain>/domain.pddl`.
2. Load stored query records from `src/benchmark_data/queries_LTLf.json`.
3. Compile each stored LTLf formula into a DFA.
4. Convert transition guards to AgentSpeak(L) plan contexts.
5. Persist:
   - `plan_library.json`
   - `plan_library.asl`
   - `dfa_metadata.json`
   - `generation_summary.json`
   - `library_validation.json`

All generated high-level plans use `!g` as the entrypoint. Transition plans update
the `dfa_state(...)` belief and recurse to `!g`; accepting-state plans terminate.

## Benchmarks

Benchmark files are PDDL:

- `src/domains/blocksworld`
- `src/domains/marsrover`
- `src/domains/satellite`
- `src/domains/transport`

The stored LTLf formulas are not regenerated during plan-library generation.
Legacy task-event names in those formulas are mapped to PDDL fluents, for example:

- `do_put_on(x, y)` -> `on(x, y)`
- `get_soil_data(w)` -> `communicated_soil_data(w)`
- `do_observation(d, m)` -> `have_image(d, m)`
- `deliver(p, l)` -> `at(p, l)`

## Usage

```bash
uv run python src/main.py generate-library \
  --domain-file ./src/domains/blocksworld/domain.pddl \
  --query-domain blocksworld \
  --query-id query_1
```

The default output root is `artifacts/plan_library/<domain>`.

## Development

Run focused tests:

```bash
uv run pytest \
  tests/utils/test_pddl_parser.py \
  tests/temporal_specification/test_pddl_mapping.py \
  tests/temporal_specification/test_validation.py \
  tests/plan_library
```
