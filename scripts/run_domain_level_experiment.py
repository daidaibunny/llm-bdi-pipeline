#!/usr/bin/env python3
"""
Run a generic PDDL domain-level lifted-library experiment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from domain_level_planning.experiments import run_domain_level_experiment  # noqa: E402
from domain_level_planning.library_synthesis import ExternalSketchPolicySource  # noqa: E402


def main() -> None:
	"""Parse a PDDL split, run synthesis/evaluation, and write a JSON report."""

	parser = argparse.ArgumentParser(
		description="Run a generic domain-level lifted ASL library experiment.",
	)
	parser.add_argument(
		"--experiment-name",
		required=True,
		help="Stable name recorded in the JSON report.",
	)
	parser.add_argument(
		"--domain-file",
		type=Path,
		required=True,
		help="PDDL domain file.",
	)
	parser.add_argument(
		"--train-problem",
		type=Path,
		action="append",
		default=[],
		help="Training PDDL problem file. May be repeated.",
	)
	parser.add_argument(
		"--eval-problem",
		type=Path,
		action="append",
		default=[],
		help="Evaluation PDDL problem file. May be repeated.",
	)
	parser.add_argument(
		"--counterexample-problem",
		type=Path,
		action="append",
		default=[],
		help="Counterexample PDDL problem file supplied to synthesis. May be repeated.",
	)
	parser.add_argument(
		"--use-counterexample-refinement",
		action="store_true",
		help="Run the bounded counterexample-guided synthesis loop.",
	)
	parser.add_argument(
		"--max-refinement-rounds",
		type=int,
		default=1,
		help="Maximum counterexample-refinement rounds.",
	)
	parser.add_argument("--max-steps", type=int, default=10000)
	parser.add_argument("--max-depth", type=int, default=1000)
	parser.add_argument(
		"--synthesis-profile",
		choices=("bootstrap", "paper"),
		default="bootstrap",
		help="Synthesis strictness profile passed to the unified learner.",
	)
	parser.add_argument(
		"--external-sketch-policy",
		action="append",
		default=[],
		metavar="NAME=PATH",
		help=(
			"External learner-sketches policy artifact to consume. "
			"May be repeated; NAME= may be omitted."
		),
	)
	parser.add_argument(
		"--ablation-label",
		default=None,
		help="Explicit ablation label for the experiment protocol.",
	)
	parser.add_argument(
		"--output",
		type=Path,
		required=True,
		help="Path where the JSON report should be written.",
	)
	args = parser.parse_args()

	training_problems = tuple(args.train_problem or ())
	evaluation_problems = tuple(args.eval_problem or ())
	if not training_problems:
		raise ValueError("At least one --train-problem is required.")
	if not evaluation_problems:
		raise ValueError("At least one --eval-problem is required.")

	external_policies = _parse_external_sketch_policies(
		tuple(args.external_sketch_policy or ()),
	)
	report = run_domain_level_experiment(
		experiment_name=args.experiment_name,
		domain_file=args.domain_file,
		training_problem_files=training_problems,
		evaluation_problem_files=evaluation_problems,
		counterexample_problem_files=tuple(args.counterexample_problem or ()),
		external_sketch_policies=external_policies,
		synthesis_profile=args.synthesis_profile,
		max_execution_steps=args.max_steps,
		max_depth=args.max_depth,
		use_counterexample_refinement=args.use_counterexample_refinement,
		max_refinement_rounds=args.max_refinement_rounds,
		ablation_label=args.ablation_label,
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


def _parse_external_sketch_policies(
	raw_sources: tuple[str, ...],
) -> tuple[ExternalSketchPolicySource, ...]:
	"""Parse repeated NAME=PATH or PATH policy references."""

	sources: list[ExternalSketchPolicySource] = []
	for index, raw_source in enumerate(tuple(raw_sources or ()), start=1):
		text = str(raw_source or "").strip()
		if not text:
			continue
		if "=" in text:
			name, raw_path = text.split("=", 1)
			source_name = name.strip() or f"external-sketch-{index}"
			policy_path = Path(raw_path.strip())
		else:
			source_name = f"external-sketch-{index}"
			policy_path = Path(text)
		sources.append(
			ExternalSketchPolicySource(
				name=source_name,
				policy_file=policy_path,
				backend_name="learner-sketches",
			),
		)
	return tuple(sources)


if __name__ == "__main__":
	main()
