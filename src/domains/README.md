# Materialized PDDL Benchmarks

This directory is generated from pinned public benchmark repositories. In the
public GP2PL code-and-data release, run:

```bash
bash scripts/setup_benchmark_sources.sh
uv run python scripts/materialize_achievement_benchmarks.py
```

Each generated domain contains `domain.pddl`, deterministic `train/` and
`test/` splits, and a `source.json` provenance record. The upstream PDDL files
are not licensed as original GP2PL data; see `THIRD_PARTY_NOTICES.md`.
