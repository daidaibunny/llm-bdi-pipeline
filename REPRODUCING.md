# Reproducing GP2PL

This document identifies the complete public inputs for the manuscript. It is
an execution guide, not part of the theoretical contribution.

## Fixed Research Artifacts

| Artifact | Path | Purpose |
| --- | --- | --- |
| Temporal-goal benchmark | [`paper_artifacts/temporal_goal_benchmark/v1`](paper_artifacts/temporal_goal_benchmark/v1/README.md) | 475 unique natural-language translations and 1,228 bound query cases over 16 domains. |
| Semantic conformance suite | `paper_artifacts/temporal_semantic_conformance/v1` | Direct finite-trace semantics versus MONA-derived automata, including zero-action cases. |
| Evaluation release | `paper_artifacts/gp2pl_evaluation/v1` | Exact atomic libraries, 1,228 compact execution records, 13 certificate challenges, distribution summaries, and SHA-256 manifest. |

The release contains no machine-local absolute paths. The canonical benchmark,
per-domain views, frozen predictions, semantic validation rows, and source
archives are hash-identified across `manifest.json` and
`release_validation.json`.

## Tested Environment

- Apple M4, 10 CPU cores, 24 GB unified memory; no GPU is required.
- macOS 26.4.1, arm64.
- Python 3.12.7 and uv 0.8.19.
- Clingo 5.8.0, Tarski 0.9.1, ltlf2dfa 1.0.2, MONA 1.4-18.
- Jason 3.1.2, OpenJDK 24, Maven 3.9.11.
- Docker 28.5.1 and VAL revision
  `3c7a1f330bdab0ba28a4762bb45c3f06c27fb6d4`.

The experiment scripts record the actual command, source revision, timeout,
memory bound, worker count, seed, and input hashes in every run manifest.

## Install Dependencies

```bash
uv sync
bash scripts/setup_mona.sh
bash scripts/setup_moose.sh
bash scripts/setup_benchmark_sources.sh
uv run python scripts/materialize_achievement_benchmarks.py
```

The MOOSE and benchmark setup scripts refuse dirty upstream checkouts and check
every pinned commit. The materializer deterministically reconstructs all
train/test splits.

For Jason and VAL execution, install Java, Maven, and Docker. Jason 3.1.2 is
resolved from Maven. The VAL wrapper expects the pinned local VAL image or
binary configured by `scripts/validate_with_docker_val.sh`.

## Verify the Released Data

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/verify_public_teg_dataset.py

PYTHONDONTWRITEBYTECODE=1 uv run pytest \
  tests/test_build_reproducibility_release.py \
  tests/test_generate_evaluation_tables.py \
  tests/test_certificate_challenge_matrix.py -q
```

The TEG verifier checks every count and hash, scans both ordinary files and
source archives for machine-local paths, and requires dataset-level license and
citation metadata. The release manifest is also checked by the conference-neutral
table generator. Regenerate the reported tables with:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python \
  scripts/generate_evaluation_tables.py \
  --execution-summary \
  paper_artifacts/gp2pl_evaluation/v1/temporal_execution_summary.json \
  --benchmark-compatibility \
  paper_artifacts/gp2pl_evaluation/v1/benchmark_compatibility.json \
  --atomic-library-root \
  paper_artifacts/gp2pl_evaluation/v1/atomic_libraries \
  --output-dir artifacts/evaluation_tables
```

The output directory contains `evaluation_results.json`, `result_macros.tex`,
`result_domain_table.tex`, and `result_profile_table.tex`. The generator rejects
dirty or hash-inconsistent inputs and incomplete benchmark coverage rather than
silently producing a partial table.

The compatibility certificate is limited to explicitly named fields below the
benchmark's `provenance` object. It reconstructs the benchmark hash stored by the
execution record and cannot change domains, formulas, bindings, or expected
semantics.

## Registered Experimental Parameters

### Generalized-planning evidence

- MOOSE goal size: 1, fixed by the singleton-goal evidence definition.
- Goal permutations per training problem: 3, following MOOSE Algorithm 1.
- Repetition seeds: 0, 1, 2, 3, 4.
- Internal MOOSE workers per seed: 1. Earlier diagnostic runs tried 6 and 12;
  one worker was fixed to prevent concurrent access to MOOSE's seeded random
  stream from changing the discovered rule set.
- Synthesis limit: 12 hours per domain and seed.
- Process memory guard: 16 GiB. This is a declared deviation from MOOSE's
  reported 32 GB synthesis allowance.
- Test-time planning limit: 30 minutes and 8 GiB per instance.

Each seed is trained, compiled, and evaluated independently. Evidence and rules
are never pooled across seeds, and no best seed is selected.

### Validated policy-lifting compiler

- Candidate scope: all implemented certified candidate families.
- Schema regression depth: no numeric depth cutoff. Search stops at repeated
  alpha-normalized requirement/producer roles or resource modes.
- Branch selector: Clingo lexicographic optimization over recursive capability,
  acyclic preparation capability, branch count, context count, and body cost.
- Balanced controller branching factor: 2, fixed by the proved binary-tree
  construction and not tuned on benchmark outcomes.

### Temporal translation and execution

- Translation model: `gpt-5.5`.
- Temperature: 0; maximum output tokens: 60,000; request timeout: 1,000 seconds;
  semantic retries: at most 3; JSON-object response mode.
- Temporal compiler: certified balanced controller with primitive-step monitor.
- Jason and VAL timeout: 30 minutes each per query.
- Java thread stack: 64 MiB.
- Final registered validation workers: 6. Diagnostic throughput runs tried 10,
  12, and 16; the final value was chosen before the registered matrix to reduce
  cross-process resource contention, not to improve solution coverage.

The compiler contains no learned numerical hyperparameters. Values above are
semantic bounds, external-method parameters, or resource controls. They are not
selected on the test set.

## Full MOOSE Evidence Reproduction

The five-seed atomic matrix is expensive: each domain/seed synthesis may use the
full 12-hour limit. The registered driver is:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python \
  scripts/run_paired_compiler_experiments.py \
  --stage all \
  --generate-evidence \
  --num-workers 6
```

This requires the official MOOSE repository installed by
`scripts/setup_moose.sh` and the planner environment described by
`scripts/setup_external_planning_references.sh`.
Incomplete smoke matrices are rejected as paper results unless the explicit
development-only flag is supplied.

## Statistical Reporting Boundary

The fixed temporal release reports the complete per-query distribution. Across
1,228 cases, execution time has median 5.49 seconds, interquartile range
4.28--8.49 seconds, and sample standard deviation 13.66 seconds; action count
has median 2, interquartile range 1--2, and sample standard deviation 0.80.

The current manuscript does not claim a statistically significant improvement
between compiler variants. All fixed-release differences are descriptive. The
checklist answer is therefore `yes` in a claim-scoped sense: no improvement or
decrease is presented as statistically significant without an appropriate paired
test. The registered five-seed comparison must complete before any such claim is
added; documentation alone cannot supply that evidence.

## Checklist Evidence Map

- All GP2PL-authored experiment, preprocessing, validation, and analysis source
  is included in `src/`, `scripts/`, and `tests/`, with the exact environment in
  `uv.lock`; it is released under Apache-2.0.
- Public third-party tools are installed at pinned revisions by the setup scripts
  and retain upstream terms. They are dependencies, not omitted GP2PL source.
- All novel temporal-goal data, including the construction audit sealed from the
  translation model during inference, is published under
  `paper_artifacts/temporal_goal_benchmark/v1` with CC BY 4.0 licensing, citation
  metadata, source archives, and integrity hashes.
- Existing PDDL datasets are publicly retrievable from cited, pinned revisions
  and are deterministically materialized. No non-public dataset is used.
- Complete per-instance records support descriptive distributions. Inferential
  compiler comparisons are admitted only after the registered paired analysis.

## Anonymous Submission and Public Release

AAAI review material must not point to a named public repository. The anonymous
submission is accompanied by an anonymized code-and-data archive. The
camera-ready manuscript enables the conditional link to
<https://github.com/daidaibunny/gp2pl>.
