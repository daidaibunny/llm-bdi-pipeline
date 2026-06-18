#!/usr/bin/env python3
"""
Compare completed domain-level lifted-library experiment reports.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from domain_level_planning.experiments import (  # noqa: E402
	compare_domain_level_experiment_reports,
)


def main() -> None:
	"""Read completed report JSON files and write a comparison table."""

	parser = argparse.ArgumentParser(
		description="Compare completed domain-level experiment reports.",
	)
	parser.add_argument(
		"--report",
		type=Path,
		action="append",
		default=[],
		help="Completed experiment report JSON. May be repeated.",
	)
	parser.add_argument(
		"--output",
		type=Path,
		required=True,
		help="Path where the comparison JSON should be written.",
	)
	args = parser.parse_args()

	report_paths = tuple(args.report or ())
	if not report_paths:
		raise ValueError("At least one --report is required.")
	reports = tuple(_read_report(path) for path in report_paths)
	comparison = compare_domain_level_experiment_reports(reports)
	args.output.parent.mkdir(parents=True, exist_ok=True)
	args.output.write_text(
		json.dumps(comparison, indent=2, sort_keys=True),
		encoding="utf-8",
	)
	print(
		"wrote "
		f"{args.output} "
		f"reports={comparison['report_count']} "
		f"best={comparison['best_by_coverage']}",
	)


def _read_report(path: Path) -> dict[str, object]:
	return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
	main()
