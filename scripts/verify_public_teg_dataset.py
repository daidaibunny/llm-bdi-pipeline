#!/usr/bin/env python3
"""Verify the public GP2PL temporally extended goal benchmark release."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.public_temporal_dataset import verify_public_temporal_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "paper_artifacts/temporal_goal_benchmark/v1"


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET)
	args = parser.parse_args()
	report = verify_public_temporal_dataset(args.dataset_root)
	print(
		"[ok] public TEG dataset "
		f"benchmark={report['benchmark_id']} "
		f"domains={report['domain_count']} "
		f"translations={report['unique_translation_input_count']} "
		f"queries={report['problem_case_count']}",
		flush=True,
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
