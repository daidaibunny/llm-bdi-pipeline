#!/usr/bin/env python3
"""Validate model-generated lifted LTLf predictions and optional execution traces."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.temporal_validation_batch import run_temporal_goal_validation_batch


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--handoff-root", type=Path, required=True)
	parser.add_argument("--benchmark-root", type=Path, required=True)
	parser.add_argument("--predictions-file", type=Path, required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
	parser.add_argument("--domains-root", type=Path, default=PROJECT_ROOT / "src/domains")
	parser.add_argument("--execution-traces-root", type=Path)
	parser.add_argument("--plan-verifier-command")
	parser.add_argument("--plan-verifier-timeout-seconds", type=int, default=1800)
	parser.add_argument("--expected-prompt-config", default="full")
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	summary = run_temporal_goal_validation_batch(
		handoff_root=args.handoff_root,
		benchmark_root=args.benchmark_root,
		predictions_file=args.predictions_file,
		output_dir=args.output_dir,
		project_root=args.project_root,
		domains_root=args.domains_root,
		execution_traces_root=args.execution_traces_root,
		plan_verifier_command=args.plan_verifier_command,
		plan_verifier_timeout_seconds=args.plan_verifier_timeout_seconds,
		progress=lambda message: print(message, flush=True),
		expected_prompt_config=args.expected_prompt_config,
	)
	print(
		"[done] "
		f"translations={summary['translation_success_count']}/{summary['translation_total']} "
		f"problems={summary['problem_success_count']}/{summary['problem_total']} "
		f"output={args.output_dir}",
		flush=True,
	)
	return 0 if (
		summary["translation_success_count"] == summary["translation_total"]
		and summary["problem_success_count"] == summary["problem_total"]
	) else 1


if __name__ == "__main__":
	raise SystemExit(main())
