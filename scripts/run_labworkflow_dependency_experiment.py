#!/usr/bin/env python3
"""
Run a non-Blocksworld goal-dependency refinement experiment.
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
		description="Run the Labworkflow goal-dependency lifted-library experiment.",
	)
	parser.add_argument(
		"--output",
		type=Path,
		default=Path("tmp/labworkflow-dependency-experiment/report.json"),
		help="Path where the JSON report should be written.",
	)
	parser.add_argument("--max-steps", type=int, default=100)
	parser.add_argument("--max-depth", type=int, default=50)
	parser.add_argument(
		"--ablation-label",
		default=None,
		help="Explicit ablation label for the experiment protocol.",
	)
	parser.add_argument(
		"--disable-synthesis-mechanism",
		action="append",
		default=[],
		choices=("layer_c_ordering",),
		help=(
			"Disable one synthesis mechanism for ablation. May be repeated. "
			"Currently supported: layer_c_ordering."
		),
	)
	args = parser.parse_args()

	lab_root = PROJECT_ROOT / "src" / "domains" / "labworkflow"
	report = run_domain_level_experiment(
		experiment_name="labworkflow-dependency",
		domain_file=lab_root / "domain.pddl",
		training_problem_files=(lab_root / "problems" / "p01.pddl",),
		evaluation_problem_files=(
			lab_root / "problems" / "p01.pddl",
			lab_root / "problems" / "p02.pddl",
		),
		use_counterexample_refinement=True,
		disabled_synthesis_mechanisms=tuple(
			args.disable_synthesis_mechanism or (),
		),
		max_refinement_rounds=1,
		max_execution_steps=args.max_steps,
		max_depth=args.max_depth,
		ablation_label=args.ablation_label
		or "bootstrap_counterexample_refinement",
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
		f"{report['evaluation_problem_count']} "
		f"converged={report['refinement_trace']['converged']}",
	)


if __name__ == "__main__":
	main()
