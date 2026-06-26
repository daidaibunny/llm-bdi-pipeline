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
		"--evaluation-timeout-seconds",
		type=float,
		default=None,
		help=(
			"Optional per-evaluation-problem wall-clock timeout. "
			"Timed-out problems are reported as failed and later problems continue."
		),
	)
	parser.add_argument(
		"--use-synthesis-planner-traces",
		action="store_true",
		help=(
			"Allow synthesis to call an offline planner for training traces when "
			"bounded transition-system evidence collection fails. Runtime evaluation "
			"still uses the generated library only."
		),
	)
	parser.add_argument(
		"--synthesis-planner-executable",
		type=Path,
		default=None,
		help="Optional Fast Downward executable for synthesis-time trace fallback.",
	)
	parser.add_argument(
		"--synthesis-planner-timeout-seconds",
		type=int,
		default=60,
		help="Per-problem Fast Downward timeout for synthesis-time trace fallback.",
	)
	parser.add_argument(
		"--synthesis-profile",
		choices=("bootstrap", "paper"),
		default="bootstrap",
		help="Synthesis strictness profile passed to the unified learner.",
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
		"--external-sketch-vocabulary",
		action="append",
		default=[],
		metavar="NAME=PATH",
		help=(
			"Explicit predicate vocabulary adapter JSON for one external policy "
			"source. NAME must match an --external-sketch-policy source."
		),
	)
	parser.add_argument(
		"--ablation-label",
		default=None,
		help="Explicit ablation label for the experiment protocol.",
	)
	parser.add_argument(
		"--baseline-json",
		type=Path,
		action="append",
		default=[],
		help=(
			"Completed baseline metadata JSON. The file may contain one object "
			"or a list of objects; no planner is run by this script."
		),
	)
	parser.add_argument(
		"--allow-paper-profile-failures",
		action="store_true",
		help=(
			"Write a diagnostic report even when strict paper-profile checks fail. "
			"Default behavior remains fail-fast."
		),
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
		tuple(args.external_sketch_vocabulary or ()),
	)
	report = run_domain_level_experiment(
		experiment_name=args.experiment_name,
		domain_file=args.domain_file,
		training_problem_files=training_problems,
		evaluation_problem_files=evaluation_problems,
		counterexample_problem_files=tuple(args.counterexample_problem or ()),
		external_sketch_policies=external_policies,
		synthesis_profile=args.synthesis_profile,
		disabled_synthesis_mechanisms=tuple(
			args.disable_synthesis_mechanism or (),
		),
		max_execution_steps=args.max_steps,
		max_depth=args.max_depth,
		evaluation_timeout_seconds=args.evaluation_timeout_seconds,
		use_synthesis_planner_traces=args.use_synthesis_planner_traces,
		synthesis_planner_executable=args.synthesis_planner_executable,
		synthesis_planner_timeout_seconds=args.synthesis_planner_timeout_seconds,
		use_counterexample_refinement=args.use_counterexample_refinement,
		max_refinement_rounds=args.max_refinement_rounds,
		ablation_label=args.ablation_label,
		baselines=_read_baseline_records(tuple(args.baseline_json or ())),
		fail_on_paper_profile_failure=not args.allow_paper_profile_failures,
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
	raw_vocabulary_sources: tuple[str, ...] = (),
) -> tuple[ExternalSketchPolicySource, ...]:
	"""Parse repeated NAME=PATH or PATH policy references."""

	vocabulary_files = _parse_external_sketch_vocabulary_sources(
		raw_vocabulary_sources,
	)
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
				vocabulary_file=vocabulary_files.get(source_name),
			),
		)
	unknown_vocabulary_sources = tuple(
		source_name
		for source_name in vocabulary_files
		if source_name not in {source.name for source in sources}
	)
	if unknown_vocabulary_sources:
		raise ValueError(
			"External sketch vocabulary source has no matching policy source: "
			+ ", ".join(unknown_vocabulary_sources),
		)
	return tuple(sources)


def _parse_external_sketch_vocabulary_sources(
	raw_sources: tuple[str, ...],
) -> dict[str, Path]:
	vocabulary_files: dict[str, Path] = {}
	for raw_source in tuple(raw_sources or ()):
		text = str(raw_source or "").strip()
		if not text:
			continue
		if "=" not in text:
			raise ValueError(
				"--external-sketch-vocabulary must use NAME=PATH so the adapter "
				"cannot be applied to the wrong learned policy.",
			)
		source_name, raw_path = text.split("=", 1)
		name = source_name.strip()
		if not name:
			raise ValueError("--external-sketch-vocabulary NAME must not be empty.")
		vocabulary_files[name] = Path(raw_path.strip())
	return vocabulary_files


def _read_baseline_records(paths: tuple[Path, ...]) -> tuple[dict[str, object], ...]:
	records: list[dict[str, object]] = []
	for path in tuple(paths or ()):
		raw = json.loads(path.read_text(encoding="utf-8"))
		items = raw if isinstance(raw, list) else [raw]
		for index, item in enumerate(items, start=1):
			if not isinstance(item, dict):
				raise ValueError(f"Baseline file {path} contains a non-object record.")
			records.append(_validate_baseline_record(path=path, index=index, record=item))
	return tuple(records)


def _validate_baseline_record(
	*,
	path: Path,
	index: int,
	record: dict[str, object],
) -> dict[str, object]:
	required_fields = ("label", "solved_count", "failed_count", "coverage_ratio")
	for field in required_fields:
		if field not in record:
			raise ValueError(
				f"Baseline file {path} record {index} missing required baseline field "
				f"{field!r}.",
			)
	label = str(record["label"]).strip()
	if not label:
		raise ValueError(f"Baseline file {path} record {index} has an empty label.")
	solved_count = _baseline_non_negative_int(
		record["solved_count"],
		field="solved_count",
		path=path,
		index=index,
	)
	failed_count = _baseline_non_negative_int(
		record["failed_count"],
		field="failed_count",
		path=path,
		index=index,
	)
	coverage_ratio = _baseline_coverage_ratio(
		record["coverage_ratio"],
		path=path,
		index=index,
	)
	validated = dict(record)
	validated["label"] = label
	validated["solved_count"] = solved_count
	validated["failed_count"] = failed_count
	validated["coverage_ratio"] = coverage_ratio
	return validated


def _baseline_non_negative_int(
	value: object,
	*,
	field: str,
	path: Path,
	index: int,
) -> int:
	if isinstance(value, bool) or not isinstance(value, int) or value < 0:
		raise ValueError(
			f"Baseline file {path} record {index} field {field!r} must be a "
			"non-negative integer.",
		)
	return value


def _baseline_coverage_ratio(value: object, *, path: Path, index: int) -> float:
	if isinstance(value, bool) or not isinstance(value, int | float):
		raise ValueError(
			f"Baseline file {path} record {index} field 'coverage_ratio' must be "
			"a number in [0, 1].",
		)
	ratio = float(value)
	if ratio < 0.0 or ratio > 1.0:
		raise ValueError(
			f"Baseline file {path} record {index} field 'coverage_ratio' must be "
			"a number in [0, 1].",
		)
	return ratio


if __name__ == "__main__":
	main()
