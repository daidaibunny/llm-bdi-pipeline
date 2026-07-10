#!/usr/bin/env python3
"""Build the complete controlled natural-language temporal benchmark handoff."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from temporal_input.nl_benchmark import DEFAULT_DOMAINS
from temporal_input.nl_benchmark import BuildConfig
from temporal_input.nl_benchmark import ManifestRow
from temporal_input.nl_benchmark import write_natural_language_benchmark


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description=(
			"Generate public natural-language manifests and private construction audits; "
			"this command does not call a language model."
		),
	)
	parser.add_argument(
		"--output-root",
		type=Path,
		default=None,
		help="Output directory (default: a timestamped artifacts/temporal_nl_benchmarks run).",
	)
	parser.add_argument(
		"--domain",
		action="append",
		dest="domains",
		help="Build one named domain; repeat to select several. Defaults to all 16 domains.",
	)
	parser.add_argument("--max-actions-per-state", type=int, default=12)
	parser.add_argument("--max-candidates-per-problem", type=int, default=1024)
	parser.add_argument("--max-join-bindings", type=int, default=64)
	parser.add_argument("--expanded-max-actions-per-state", type=int, default=32)
	parser.add_argument("--expanded-max-join-bindings", type=int, default=2048)
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	benchmark_id = datetime.now().strftime("temporal-nl-%Y%m%d-%H%M%S")
	output_root = args.output_root or (
		PROJECT_ROOT / "artifacts" / "temporal_nl_benchmarks" / benchmark_id
	)
	config = BuildConfig(
		max_actions_per_state=args.max_actions_per_state,
		max_candidates_per_problem=args.max_candidates_per_problem,
		max_join_bindings=args.max_join_bindings,
		expanded_max_actions_per_state=args.expanded_max_actions_per_state,
		expanded_max_join_bindings=args.expanded_max_join_bindings,
	)

	def report(row: ManifestRow, elapsed: float) -> None:
		label = "ok" if row.status == "constructed_temporal_query" else "skip"
		print(
			f"[{label}] domain={row.domain} problem={Path(row.problem_file).stem} "
			f"status={row.status} tier={row.construction_tier or 'none'} "
			f"elapsed={elapsed:.2f}s",
			flush=True,
		)

	summary = write_natural_language_benchmark(
		domains_root=PROJECT_ROOT / "src" / "domains",
		output_root=output_root,
		domain_names=tuple(args.domains or DEFAULT_DOMAINS),
		config=config,
		progress=report,
	)
	print(
		f"[done] constructed={summary['constructed_count']}/{summary['problem_count']} "
		f"output={output_root}",
		flush=True,
	)
	return 0 if summary["constructed_count"] == summary["problem_count"] else 1


if __name__ == "__main__":
	raise SystemExit(main())
