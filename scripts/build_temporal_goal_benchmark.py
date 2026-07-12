#!/usr/bin/env python3
"""Reproduce and write the tracked paper TEG benchmark from sealed archives."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.temporal_benchmark_release import build_temporal_benchmark_release


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--delivery-archive", type=Path, required=True)
	parser.add_argument("--delivery-archive-sha256", required=True)
	parser.add_argument("--public-handoff-archive", type=Path, required=True)
	parser.add_argument("--public-handoff-archive-sha256", required=True)
	parser.add_argument("--private-validation-archive", type=Path, required=True)
	parser.add_argument("--private-validation-archive-sha256", required=True)
	parser.add_argument("--benchmark-id", required=True)
	parser.add_argument("--run-id", required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	parser.add_argument(
		"--mona-bin",
		type=Path,
		default=PROJECT_ROOT / ".external/mona-1.4/Front/mona",
	)
	parser.add_argument("--validation-implementation-commit", required=True)
	parser.add_argument("--work-dir", type=Path)
	parser.add_argument("--reuse-independent-validation", action="store_true")
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	report = build_temporal_benchmark_release(
		delivery_archive=args.delivery_archive,
		delivery_archive_sha256=args.delivery_archive_sha256,
		public_handoff_archive=args.public_handoff_archive,
		public_handoff_archive_sha256=args.public_handoff_archive_sha256,
		private_validation_archive=args.private_validation_archive,
		private_validation_archive_sha256=args.private_validation_archive_sha256,
		benchmark_id=args.benchmark_id,
		run_id=args.run_id,
		output_dir=args.output_dir,
		project_root=PROJECT_ROOT,
		domains_root=PROJECT_ROOT / "src/domains",
		mona_bin=args.mona_bin,
		validation_implementation_commit=args.validation_implementation_commit,
		progress=lambda message: print(message, flush=True),
		work_dir=args.work_dir,
		reuse_independent_validation=args.reuse_independent_validation,
	)
	print(
		"[done] "
		f"benchmark={report['benchmark_id']} "
		f"translations={report['independent_summary']['translation_success_count']}/"
		f"{report['independent_summary']['translation_total']} "
		f"problems={report['independent_summary']['problem_success_count']}/"
		f"{report['independent_summary']['problem_total']} "
		f"output={args.output_dir}",
		flush=True,
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
