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

## NL → LTLf Goal Specification

LTLf is the single goal-specification surface (BDI.md §2, §3, §5, §6). For any
supported domain and any goal, a SOTA language model converts one natural-language
instruction into one LTLf formula whose atoms are **PDDL fluents** (predicates such
as `on(b4, b2)`), never action or event names. A temporal extended goal (TEG) uses
temporal operators, e.g. `F(on(b4, b2) & X(F(on(b1, b4))))`; a plain achievement
goal degenerates to a pure conjunction with no temporal operators, e.g.
`on(b4, b2) & on(b3, b1)`.

The generator (`src/temporal_specification/nl_to_ltlf.py`) is domain-generic: it
derives every legal atom from the parsed PDDL domain, so adding a supported domain
needs no code change here.

### Configure the model

Copy `.env.example` to `.env` and set the API key. The default points at Aliyun
DashScope's OpenAI-compatible endpoint; override `LANGUAGE_MODEL_*` /
`LTLF_GENERATION_*` for any other OpenAI-compatible provider.

### Train/test workflow

Each domain's instances are split deterministically: the first ~2/3 train the plan
library and the held-out ~1/3 supply the goals that test it.

```bash
# 1. Deterministic 2/3-train / 1/3-test split of the four supported domains.
uv run python scripts/generate_domain_instance_split.py

# 2. Generate fluent-grounded LTLf goals from the NL benchmark queries (needs the key).
uv run python scripts/generate_ltlf_dataset.py --query-domain blocksworld

# 3. Synthesize the library from the training split and evaluate the generated
#    held-out goals (achievement and TEG) against it. No live LLM needed here.
uv run python scripts/run_nl_to_ltlf_eval.py \
  --query-domain blocksworld \
  --split-file ./src/benchmark_data/instance_split.json
```

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
