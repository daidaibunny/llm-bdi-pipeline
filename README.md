# GP2PL

**GP2PL** (Generalized Planning to Plan Libraries) is a framework for compiling
generalized-planning evidence into certified Belief--Desire--Intention (BDI)
plan libraries and composing ordinary achievement goals or their temporal
extensions over those libraries.

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
evidence with PDDL action schemas, expands the producible target universe to
include internal targets such as `clear(X)`, certifies candidate branches, and
asks Clingo to select a minimum-cost feasible core from the generated certified
candidate set.

The query-specific compilation is

```text
typed and bound achievement or TEG specification + real ltlf2dfa/MONA automaton
-> certified query-local BDI controllers appended to the domain library
```

An ordinary achievement query is an LTLf state formula with no temporal
operator. GP2PL embeds it as `F(formula)` for execution; a temporally extended
goal is unchanged. Both then use the same automaton and controller pipeline.

A controller interprets one deterministic finite automaton transition guard as
one signed state condition. Positive literals are achievement obligations;
negative literals are absence obligations and never become synthetic negative
goals. Conditional module-completion summaries determine a preservation-safe
literal order, and a balanced binary transition-repair tree bounds plan-trigger
fan-out. A runtime monitor
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
- Fail-closed rejection for unresolved binding, internal-call closure, progress, resource,
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

Jason is resolved from Maven coordinate `io.github.jason-lang:jason:3.1.2` when a
runtime validation is first requested. Docker is required by the supplied VAL
wrapper.

## Benchmark Materialization

The PDDL benchmarks are drawn from pinned public repositories. Because several
upstream repositories do not declare redistribution licenses, the GP2PL public
code-and-data release does not relicense their files. Materialize exact local copies with:

```bash
bash scripts/setup_benchmark_sources.sh
uv run python scripts/materialize_achievement_benchmarks.py
```

Every materialized domain records its source URL, source commit, and split
policy in `src/domains/<domain>/source.json`.

## Reproducing Reported Results

The versioned temporal benchmark has a dedicated
[dataset landing page](paper_artifacts/temporal_goal_benchmark/v1/README.md)
and a [versioned public release](https://github.com/daidaibunny/gp2pl/releases/tag/teg-benchmark-v1).
The fixed libraries, compact execution records, certificate challenges,
distributions, and outcome-only manifest are under
`paper_artifacts/gp2pl_evaluation/v1`. Public result records omit run identifiers,
source revisions, byte digests, and machine-local paths.

Verify the complete TEG dataset, including source archives and portability:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/verify_public_teg_dataset.py
```

Regenerate the manuscript result tables from those fixed records after
materializing the PDDL corpus:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python \
  scripts/generate_evaluation_tables.py \
  --execution-summary \
  paper_artifacts/gp2pl_evaluation/v1/temporal_execution_summary.json \
  --atomic-library-root \
  paper_artifacts/gp2pl_evaluation/v1/atomic_libraries \
  --output-dir artifacts/evaluation_tables
```

Run the certificate and symbol-invariance matrix:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python \
  scripts/run_certificate_challenge_matrix.py
```

The complete environment, parameters, and experimental commands are listed in
[REPRODUCING.md](REPRODUCING.md) and the manuscript's technical appendix.

## Development Checks

```bash
PYTHONDONTWRITEBYTECODE=1 uv run ruff check src scripts tests
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q
```

## Paper and Public Release

The manuscript source is in `latex_code/aamas_method_paper`. The public
code-and-data release is <https://github.com/daidaibunny/gp2pl>. The anonymous submission PDF
does not display this identifying URL; the camera-ready source contains a
conditional code-and-data availability statement.

## Licensing

GP2PL source code is licensed under Apache-2.0. Original benchmark annotations,
temporal specifications, and generated result records are licensed under
CC BY 4.0 as described in [DATA_LICENSE.md](DATA_LICENSE.md). Third-party PDDL,
software, and papers retain their original terms; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
