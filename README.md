# LLM BDI Pipeline

This project studies domain-level lifted AgentSpeak(L) plan-library synthesis
from PDDL achievement-goal benchmark domains, with a future temporal layer where
persisted LTLf specifications compile to DFA controllers above the learned
achievement-goal library.

The current architecture has two research-facing levels:

- Achievement-goal library synthesis: parse a PDDL domain and training
  problems, generate lifted Layer B predicate-goal modules and Layer C
  conjunctive-goal composition rules, compile them into AgentSpeak(L), and
  validate on held-out problems without runtime full-trace planning.
- Temporal extended-goal control: use stored LTLf formulas from
  `src/benchmark_data/queries_LTLf.json`, compile them to DFA controllers, and
  dispatch each DFA transition guard to the achievement-goal library. This layer
  is not the current formal benchmark scope.

## Core Flow

1. Load the achievement-goal benchmark registry from
   `src/benchmark_registry/achievement_goals`.
2. Load a selected IPC PDDL domain from `src/domains/<domain>/domain.pddl`.
3. Use the domain's `train` split for synthesis evidence and the `test` split
   as held-out goal-specification problems.
4. Compile selected lifted rules into an AgentSpeak(L) library whose plan heads
   are PDDL predicate goals such as `+!clear(X)` or `+!on(X,Y)`.
5. Validate generated libraries without runtime full-trace planning.

Generated domain-level libraries use `!g` as the top-level composer entry point
and must not emit synthetic achievement names such as `achieve_*`,
`transition_*`, or exposed `dfa_state(...)` beliefs.

## Planner Use

Classical planners are allowed during offline synthesis, trace-evidence
generation, counterexample analysis, and baseline evaluation. They are not the
runtime low-level method for the final domain-level library claim.

## Benchmarks

Formal achievement-goal benchmarks are complete IPC PDDL directories
materialized from `potassco/pddl-instances` at commit
`cf19edf7c53d1540ddbb396c642595e0926ee552`.

Selected domains:

- `barman`
- `blocks`
- `childsnack`
- `gripper`
- `miconic`
- `visitall`

Each selected domain has `domain.pddl`, `train`, `test`, and `source.json`
under `src/domains/<domain>`. The train split is `floor(2/3 * N)` instances and
the remaining instances are held out.

## Usage

```bash
uv run python scripts/run_final_paper_data.py \
  --output-dir tmp/paper-final-latest \
  --config-only
```

## Development

Run focused tests:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q

PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_final_paper_data.py \
  --output-dir tmp/paper-final-latest \
  --config-only
```
