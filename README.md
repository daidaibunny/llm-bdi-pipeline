# LLM BDI Pipeline

This project studies domain-level lifted AgentSpeak(L) plan-library generation
from PDDL domains. The current paper path is intentionally narrower than a
universal generalized planner: it imports or learns atomic predicate/literal
templates from external generalized-planning backends, then appends
query-specific temporal wrappers from validated lifted LTLf goals.

The current architecture has two research-facing components:

- Atomic minimal literal module generation: parse a PDDL domain and training
  split, use a verified generalized-planning artifact as evidence for required
  atomic predicates, synthesize compact lifted recursive modules from PDDL
  action schemas, and validate without runtime full-trace planning.
- Temporal append: consume lifted LTLf JSON from the external Input
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
5. Normalize the backend artifact into `LiftedPolicyProgram` or use it as
   target-predicate evidence for atomic minimal literal module synthesis.
6. Compile accepted lifted atomic rules or synthesized minimal modules into an
   AgentSpeak(L) library whose plan heads are PDDL predicate goals such as
   `+!clear(X)` or `+!on(X,Y)`.
7. Append lifted LTLf/DFA query wrappers only when each relevant DFA transition
   guard is a singleton literal over the PDDL vocabulary.

Generated domain-level libraries are maintained in one canonical directory per
domain:

```text
artifacts/domain_libraries/<domain>/plan_library.json
artifacts/domain_libraries/<domain>/plan_library.asl
artifacts/domain_libraries/<domain>/artifact_metadata.json
```

The main CLI refuses non-canonical output roots and non-canonical append input
files. Query wrappers may introduce top-level names such as `g_query_17`, but
generated ASL must not emit synthetic names such as `achieve_*`,
`transition_*`, or exposed `dfa_state(...)` beliefs.

The older in-repository generalized-planning synthesizer and conjunctive-goal
ordering path have been removed from the current code path. The current schema
logic is narrower: it compresses verified singleton-goal backend evidence into
atomic minimal literal modules; it is not a universal generalized planner.

## Planner Use

Classical planners may be used inside external generalized-planning backends,
artifact reproduction, and validation. They are not the runtime low-level method
for the final domain-level library claim, and this repository no longer carries
an in-repository planner-trace synthesis path.

## Benchmarks

Formal achievement-goal benchmarks are materialized from pinned reputable
generalized-planning benchmark sources: `potassco/pddl-instances`,
`DillonZChen/moose-dataset`, `bonetblai/learner-policies-from-examples`, and
`rleap-project/d2l`.

The materialized benchmark corpus and backend policy are described in
`docs/gp_backend_strategy.md`.

| Evaluation group | Target domains | Purpose |
| --- | --- | --- |
| ESHO classical domains | `barman`, `ferry`, `gripper`, `logistics`, `miconic`, `rovers`, `satellite`, `transport` | Check lifted atomic modules on the classical easy-to-solve, hard-to-optimise benchmark family used by MOOSE. |
| Numeric fluent domains | `numeric-ferry`, `numeric-miconic`, `numeric-minecraft`, `numeric-transport` | Include MOOSE numeric train/test domains for experimental support. |
| Feature-definable serialized-width domains | `blocksworld-clear`, `blocksworld-on`, `blocksworld-tower`, `depots` | Check feature-defined subgoal serialization and schema-derived internal atomic modules. |

Each selected domain has `domain.pddl`, `train`, `test`, and `source.json`
under `src/domains/<domain>`. MOOSE domains use the official companion
`training/` and `testing/` split. `blocksworld-clear` and `blocksworld-on`
use the KR 2025 learner-policies no-constants train/test folders.
`blocksworld-tower` and `depots` use the project feature-definable
serialized-width split described in `docs/gp_backend_strategy.md`.

## Usage

```bash
uv run python src/main.py compile-moose-atomic-library \
  --policy-file tmp/moose-blocks-e2e/blocks-probe-first4.model.readable \
  --domain-file src/domains/blocksworld-tower/domain.pddl \
  --domain-name blocksworld-tower \
  --validated-policy-lifting

uv run python src/main.py append-lifted-temporal-goal \
  --domain-file src/domains/blocksworld-tower/domain.pddl \
  --ltlf-goal-json artifacts/input/blocksworld_lifted_ltlf.json \
  --query-id query_1

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
