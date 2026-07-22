# GP2PL Evaluation Release

This directory contains the fixed atomic libraries and compact result records
used by the reported evaluation. The temporal benchmark is `paper_artifacts/temporal_goal_benchmark/v1/benchmark.json`.

- `atomic_libraries/` contains the exact structured and AgentSpeak(L) libraries.
- `temporal_execution_summary.json` contains one record for every bound query.
- `five_seed_full_compiler_summary.json` records all five independent Full
  GP2PL held-out matrices, per-case outcomes, per-domain variation, and failure
  patterns.
- `moose_published_reference.json` records the verified arXiv-v1 Table-4 MOOSE
  coverage values and disjoint case contracts for the 1,080 published-domain
  cases and 148 locally measured GP2PL extension cases.
- `raw_moose_extension_five_seed_summary.json` freezes all 740 portable
  case-level Raw MOOSE outcomes for the four GP2PL-added domains: 148 held-out
  cases under each of five independently trained evidence seeds. It records
  117 VAL-valid plans, 619 planner failures, and four timeouts without retaining
  machine-local paths.
- `external_reference_results.json` freezes the complete 1,228-case
  LAMA/MRP+HJ matrix and 1,228-case FOND4LTLf-plus-LAMA matrix. Its 2,456
  portable records retain method outcomes, runtimes, and validation status.
- `paired_ablation_results.json` freezes all 24,560 atomic and 4,912 temporal
  paired-ablation outcomes, their aggregate tables, adjacent-method exact
  paired contrasts, corrected transition-repair fan-out, and the 13-case
  challenge outcomes. Its integrated cross-seed extension adds 6,140
  Certified Balanced outcomes: the same 1,228 temporal queries over each of
  five independently seeded Full GP2PL atomic libraries.
- `certificate_challenge_summary.json` records fail-closed and renaming tests.
- `execution_distribution.json` records distributional execution statistics.
- `manifest.json` lists the public files and result counts.

Run identifiers, source revisions, byte digests, transient Jason logs, and
machine-local paths are intentionally excluded. Aggregate values are
recomputable from the released per-case outcomes.
