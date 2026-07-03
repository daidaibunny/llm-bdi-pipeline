# LLM BDI Pipeline

This project studies domain-level lifted AgentSpeak(L) plan-library generation
from PDDL domains. The current paper path is intentionally narrower than a
universal generalized planner: it imports or learns atomic predicate/literal
templates from external generalized-planning backends, then appends
query-specific temporal wrappers from validated lifted LTLf goals.

The current architecture has two research-facing layers:

- Atomic template layer: parse a PDDL domain and training split, select a
  backend by the required atomic templates, normalize a verified backend
  artifact into `LiftedPolicyProgram`, compile lifted `+!P(Args)` plans, and
  validate without runtime full-trace planning.
- Temporal append layer: consume lifted LTLf JSON from the external Input
  component, compile it to a DFA, validate singleton-literal transition guards,
  and append query-specific `+!g_query` wrappers to the same domain library.

## Core Flow

1. Load the achievement-goal benchmark registry from
   `src/benchmark_registry/achievement_goals`.
2. Load a selected IPC PDDL domain from `src/domains/<domain>/domain.pddl`.
3. Use the domain's `train` split to identify required atomic goal templates
   and the `test` split as held-out goal-specification cases.
4. Select an external generalized-planning backend by atomic template needs, not
   by assigning the whole domain to a routing class.
5. Normalize the backend artifact into `LiftedPolicyProgram`.
6. Compile accepted lifted atomic rules into an AgentSpeak(L) library whose plan
   heads are PDDL predicate goals such as `+!clear(X)` or `+!on(X,Y)`.
7. Append lifted LTLf/DFA query wrappers only when each relevant DFA transition
   guard is a singleton literal over the PDDL vocabulary.

Generated domain-level atomic libraries are maintained one per domain. Query
wrappers may introduce top-level names such as `g_query_17`, but generated ASL
must not emit synthetic names such as `achieve_*`, `transition_*`, or exposed
`dfa_state(...)` beliefs.

The older in-repository schema-derived synthesizer and conjunctive-goal
ordering path have been removed from the current code path. Atomic templates
must come from verified external generalized-planning artifacts.

## Planner Use

Classical planners may be used inside external generalized-planning backends,
artifact reproduction, and validation. They are not the runtime low-level method
for the final domain-level library claim, and this repository no longer carries
an in-repository planner-trace synthesis path.

## Benchmarks

Formal achievement-goal benchmarks are materialized from pinned reputable
generalized-planning benchmark sources: `potassco/pddl-instances`,
`DillonZChen/moose-dataset`, `bonetblai/learner-sketches`, and
`bonetblai/learner-policies-from-examples`.

The materialized benchmark corpus and backend policy are described in
`docs/gp_backend_strategy.md`.

| Evaluation group | Target domains | Purpose |
| --- | --- | --- |
| Singleton regression-friendly classical goals | `ferry`, `miconic` | Check MOOSE-style positive singleton predicate templates. |
| Multi-object classical achievement goals | `gripper`, `logistics` | Check reusable atomic templates over many objects. |
| Structural or temporalized achievement goals | `blocks`, `8puzzle-1tile` | Check Blocks-style interaction and compact rearrangement via temporal wrappers. |

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
