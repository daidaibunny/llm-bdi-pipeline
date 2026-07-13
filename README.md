# GP2PL

**GP2PL** (Generalized Planning to Plan Libraries) is a framework for compiling
generalized-planning evidence into certified Belief--Desire--Intention (BDI)
plan libraries and composing temporally extended goals over those libraries.

The framework addresses a representation problem. A generalized planner may
return a lifted policy or macro rule, while a BDI interpreter requires a closed
trigger--context--body library whose variables are bound, primitive actions are
executable, internal achievement calls are implemented, and recursion has a
progress argument. GP2PL treats those requirements as proof obligations rather
than assuming that a policy can be transcribed directly.

## Formal Interface

The reusable domain compilation is

```text
PDDL domain + training instances + singleton-goal policy evidence
-> certified lifted BDI domain plan library
```

A singleton-goal policy evidence rule is an externally supplied rule for one
goal literal. For example, MOOSE may report that `stack(X,Y)` achieves
`on(X,Y)` when `holding(X)` and `clear(Y)` hold. The compiler combines such
evidence with PDDL action schemas, generates closure modules such as
`clear(X)`, certifies candidate branches, and asks Clingo to select a
minimum-cost feasible library within the generated candidate language.

The query-specific temporal compilation is

```text
typed and bound LTLf specification + real ltlf2dfa/MONA automaton
-> certified query-local BDI controllers appended to the domain library
```

A controller interprets one deterministic finite automaton transition guard as
one signed state condition. Positive literals are achievement obligations;
negative literals are absence obligations and never become synthetic negative
goals. Completion-effect summaries determine a preservation-safe literal order,
and a balanced binary repair tree bounds plan-trigger fan-out. A runtime monitor
advances the real automaton after every successful primitive PDDL action.

The implementation renders the resulting BDI rules in AgentSpeak(L) and runs
them with Jason. AgentSpeak(L) is the evaluated realization, not the definition
of the framework.

## Supported Scope

- Typed STRIPS PDDL and a bounded constant-integer resource extension.
- Positive singleton predicate goals and supported integer equalities for
  reusable atomic modules.
- LTLf formulas using `F`, `X`, strong `U`, conjunction, and literal negation,
  provided that every required progress transition receives a certificate.
- Fail-closed rejection for unresolved binding, closure, progress, resource,
  preservation, or numeric obligations.

The method does not claim complete planning for arbitrary PDDL-times-LTLf
products, global optimality over all BDI programs, or support for arbitrary
arithmetic and unrestricted disjunction.

## Installation

Python 3.12 and [`uv`](https://docs.astral.sh/uv/) are required.

```bash
uv sync
bash scripts/setup_mona.sh
bash scripts/setup_moose.sh
```

Jason is resolved as Maven artifact `io.github.jason-lang:jason:3.1.2` when a
runtime validation is first requested. Docker is required by the supplied VAL
wrapper.

## Benchmark Materialization

The PDDL benchmarks are drawn from pinned public repositories. Because several
upstream repositories do not declare redistribution licenses, the GP2PL public
artifact does not relicense their files. Materialize exact local copies with:

```bash
bash scripts/setup_benchmark_sources.sh
uv run python scripts/materialize_achievement_benchmarks.py
```

Every materialized domain records its source URL, source commit, and split
policy in `src/domains/<domain>/source.json`.

## Reproducing Reported Artifacts

The versioned temporal benchmark is under
`paper_artifacts/temporal_goal_benchmark/v1`. The fixed libraries, compact
execution records, certificate challenges, distributions, and SHA-256 manifest
are under `paper_artifacts/gp2pl_evaluation/v1`.

Regenerate the manuscript result tables from those fixed records after
materializing the PDDL corpus:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python \
  scripts/generate_aaai_result_tables.py \
  --execution-summary \
  paper_artifacts/gp2pl_evaluation/v1/temporal_execution_summary.json \
  --atomic-library-root \
  paper_artifacts/gp2pl_evaluation/v1/atomic_libraries
```

Run the certificate and symbol-invariance matrix:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python \
  scripts/run_certificate_challenge_matrix.py
```

The complete environment, parameters, source revisions, and experimental
commands are listed in [REPRODUCING.md](REPRODUCING.md) and the manuscript's
technical appendix.

## Development Checks

```bash
PYTHONDONTWRITEBYTECODE=1 uv run ruff check src scripts tests
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q
```

## Paper and Public Artifact

The manuscript source is in `latex_code/aamas_method_paper`. The public
artifact is <https://github.com/daidaibunny/gp2pl>. The anonymous submission PDF
does not display this identifying URL; the camera-ready source contains a
conditional artifact statement.

## Licensing

GP2PL source code is licensed under Apache-2.0. Original benchmark annotations,
temporal specifications, and generated result records are licensed under
CC BY 4.0 as described in [DATA_LICENSE.md](DATA_LICENSE.md). Third-party PDDL,
software, and papers retain their original terms; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
