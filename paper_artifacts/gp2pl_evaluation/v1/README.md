# GP2PL Evaluation Release

This directory contains the fixed atomic libraries and compact result records
used by the manuscript tables. The temporal benchmark is `paper_artifacts/temporal_goal_benchmark/v1/benchmark.json`.

- `atomic_libraries/` contains the exact structured and AgentSpeak(L) libraries.
- `temporal_execution_summary.json` contains one record for every bound query.
- `certificate_challenge_summary.json` records fail-closed and renaming tests.
- `execution_distribution.json` records distributional execution statistics.
- `manifest.json` fixes every included file by SHA-256.

Transient Jason logs and machine-local paths are intentionally excluded. The
public reproduction commands regenerate those diagnostics when required.
