#!/usr/bin/env python3
"""Build a domain-scoped deduplicated NL-to-LTLf translation worklist."""

from __future__ import annotations

import argparse
from pathlib import Path

from temporal_input.translation_worklist import write_translation_worklist


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description=(
			"Group a problem-complete natural-language manifest by domain and "
			"semantic signature."
		),
	)
	parser.add_argument("--manifest", type=Path, required=True)
	parser.add_argument("--output", type=Path, required=True)
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	summary = write_translation_worklist(
		manifest_path=args.manifest,
		output_path=args.output,
	)
	print(
		f"[done] templates={summary['translation_template_count']} "
		f"problem_rows={summary['problem_row_count']} "
		f"output={summary['output_path']}",
		flush=True,
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
