# LLM BDI Pipeline

This project generates high-level AgentSpeak(L) plan libraries from persisted LTLf
temporal specifications and PDDL benchmark domains.

The current architecture has two explicit levels:

- High level: use the stored LTLf formula for each benchmark query, compile it to
  a DFA with `ltlf2dfa`, analyze which outgoing transitions can still reach an
  accepting state, and render those progress transitions as context-selected
  `+!g` AgentSpeak(L) plans.
- Low level: each generated transition target is compiled into a PDDL goal
  problem. Fast Downward finds the primitive action trace, and those actions are
  rendered directly in the AgentSpeak(L) plan body when the driver is available.

## Core Flow

1. Load a PDDL domain from `src/domains/<domain>/domain.pddl`.
2. Load stored query records from `src/benchmark_data/queries_LTLf.json`.
3. Compile each stored LTLf formula into a DFA.
4. Convert transition labels to AgentSpeak(L) plan contexts without exposing
   internal `dfa_state(...)` beliefs.
5. Compile each transition target context into a PDDL goal problem and ask Fast
   Downward for a low-level trace.
6. Persist:
   - `plan_library.json`
   - `plan_library.asl`
   - `dfa_metadata.json`
   - `generation_summary.json`
   - `library_validation.json`

All generated high-level plans use `!g` as the entrypoint. Transition plans run
their primitive action trace and recurse to `!g`; accepting-context plans
terminate.

## Low-Level Planning

Fast Downward is invoked through its `fast-downward.py` driver. The default
configuration uses `--alias lama-first`; pass `--fast-downward` to point at a
local driver explicitly.

```bash
uv run python src/main.py generate-library \
  --domain-file ./src/domains/blocksworld/domain.pddl \
  --query-domain blocksworld \
  --query-id query_1 \
  --fast-downward /path/to/fast-downward.py
```

For debugging or for environments without Fast Downward installed, use:

```bash
uv run python src/main.py generate-library \
  --domain-file ./src/domains/blocksworld/domain.pddl \
  --query-domain blocksworld \
  --query-id query_1 \
  --disable-low-level-planning
```

Fast Downward's official usage documentation is at
https://www.fast-downward.org/latest/documentation/planner-usage/. Its landmark
factory documentation, including HPS, RHW, and Zhu/Givan landmarks, is at
https://www.fast-downward.org/latest/documentation/search/LandmarkFactory/.

## Benchmarks

Benchmark files are PDDL:

- `src/domains/blocksworld`
- `src/domains/marsrover`
- `src/domains/satellite`
- `src/domains/transport`

The stored LTLf formulas are not regenerated during plan-library generation.
Stored benchmark temporal atoms are mapped to PDDL fluents, for example:

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
  tests/low_level_planning \
  tests/plan_library
```
