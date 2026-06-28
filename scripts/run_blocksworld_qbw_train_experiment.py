#!/usr/bin/env python3
"""
Run the reproducible Blocksworld QBW train-split domain-level library experiment.
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
	parser = argparse.ArgumentParser(
		description="Run the Blocksworld QBW train-split lifted ASL library experiment.",
	)
	parser.add_argument(
		"--output",
		type=Path,
		default=Path("tmp/blocksworld-qbw-train-experiment/report.json"),
		help="Path where the JSON report should be written.",
	)
	parser.add_argument(
		"--train-count",
		type=int,
		default=1,
		help="Number of earliest Blocksworld QBW training problems used for synthesis.",
	)
	parser.add_argument(
		"--eval-count",
		type=int,
		default=20,
		help="Number of earliest Blocksworld QBW training problems used for evaluation.",
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
		"--allow-paper-profile-failures",
		action="store_true",
		help=(
			"Write a diagnostic report even when strict paper-profile checks fail. "
			"Default behavior remains fail-fast."
		),
	)
	args = parser.parse_args()

	blocks_root = PROJECT_ROOT / "src" / "domains" / "blocksworld_qbw"
	problems = tuple(sorted((blocks_root / "train").glob("p*.pddl")))
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
		experiment_name="blocksworld-qbw-train20",
		domain_file=blocks_root / "domain.pddl",
		training_problem_files=problems[: args.train_count],
		evaluation_problem_files=problems[: args.eval_count],
		external_sketch_policies=_parse_external_sketch_policies(
			tuple(args.external_sketch_policy or ()),
			tuple(args.external_sketch_vocabulary or ()),
		),
		synthesis_profile=args.synthesis_profile,
		disabled_synthesis_mechanisms=tuple(
			args.disable_synthesis_mechanism or (),
		),
		ablation_label=_default_ablation_label(
			explicit_label=args.ablation_label,
			synthesis_profile=args.synthesis_profile,
			external_policy_count=len(tuple(args.external_sketch_policy or ())),
		),
		max_execution_steps=args.max_steps,
		max_depth=args.max_depth,
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


def _default_ablation_label(
	*,
	explicit_label: str | None,
	synthesis_profile: str,
	external_policy_count: int,
) -> str:
	label = str(explicit_label or "").strip()
	if label:
		return label
	profile = str(synthesis_profile or "bootstrap").strip().lower()
	if profile == "paper" and external_policy_count:
		return "paper_external_sketch"
	if profile == "paper":
		return "paper_profile"
	if external_policy_count:
		return "bootstrap_external_sketch"
	return "bootstrap_schema_only"


if __name__ == "__main__":
	main()
