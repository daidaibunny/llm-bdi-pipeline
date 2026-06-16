#!/usr/bin/env python3
"""
Run the reproducible Blocksworld first-20 domain-level library experiment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from domain_level_planning.experiments import run_domain_level_experiment  # noqa: E402


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Run the Blocksworld first-20 lifted ASL library experiment.",
	)
	parser.add_argument(
		"--output",
		type=Path,
		default=Path("tmp/blocksworld-first20-experiment/report.json"),
		help="Path where the JSON report should be written.",
	)
	parser.add_argument(
		"--train-count",
		type=int,
		default=1,
		help="Number of earliest Blocksworld problems used for synthesis training.",
	)
	parser.add_argument(
		"--eval-count",
		type=int,
		default=20,
		help="Number of earliest Blocksworld problems used for evaluation.",
	)
	parser.add_argument("--max-steps", type=int, default=10000)
	parser.add_argument("--max-depth", type=int, default=1000)
	args = parser.parse_args()

	blocks_root = PROJECT_ROOT / "src" / "domains" / "blocksworld"
	problems = tuple(sorted((blocks_root / "problems").glob("p*.pddl")))
	if args.train_count < 1:
		raise ValueError("--train-count must be positive.")
	if args.eval_count < 1:
		raise ValueError("--eval-count must be positive.")
	if len(problems) < max(args.train_count, args.eval_count):
		raise ValueError(
			"Not enough Blocksworld problems for requested split: "
			f"found {len(problems)}.",
		)

	report = run_domain_level_experiment(
		experiment_name="blocksworld-first20",
		domain_file=blocks_root / "domain.pddl",
		training_problem_files=problems[: args.train_count],
		evaluation_problem_files=problems[: args.eval_count],
		max_execution_steps=args.max_steps,
		max_depth=args.max_depth,
	)
	args.output.parent.mkdir(parents=True, exist_ok=True)
	args.output.write_text(
		json.dumps(report, indent=2, sort_keys=True),
		encoding="utf-8",
	)
	print(
		"wrote "
		f"{args.output} "
		f"coverage={report['coverage']['solved_count']}/"
		f"{report['evaluation_problem_count']}",
	)


if __name__ == "__main__":
	main()
