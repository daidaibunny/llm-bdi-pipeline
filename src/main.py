"""
Command-line entry point for DFA-driven BDI plan-library generation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_src_dir = str(Path(__file__).parent)
if _src_dir not in sys.path:
	sys.path.insert(0, _src_dir)

from plan_library import PlanLibraryGenerationPipeline
from domain_level_planning import (
	ExternalSketchPolicySource,
	SketchCompilationTarget,
	compile_learner_sketch_policy_to_asl,
	synthesize_domain_level_asl_library,
)
from plan_library.rendering import render_plan_library_asl


def _absolute_path(path_text: str | None) -> str | None:
	if not path_text:
		return None
	return str(Path(path_text).expanduser().resolve())


def _require_existing_path(path_text: str | None, *, label: str) -> str:
	resolved_path = _absolute_path(path_text)
	if not resolved_path or not Path(resolved_path).exists():
		print("=" * 80)
		print(f"ERROR: {label} Not Found")
		print("=" * 80)
		print(f"\nProvided path does not exist:\n{resolved_path}")
		sys.exit(1)
	return resolved_path


def build_argument_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description=(
			"Generate DFA-driven high-level AgentSpeak(L) plan libraries from PDDL "
			"domains and stored LTLf task specifications."
		),
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  python src/main.py generate-library --domain-file ./src/domains/blocksworld/domain.pddl --query-id query_1
  python src/main.py generate-library --domain-file ./src/domains/transport/domain.pddl --query-domain transport --output-root ./artifacts/plan_library/transport/query_1
		""",
	)
	subparsers = parser.add_subparsers(dest="command")

	generate_parser = subparsers.add_parser(
		"generate-library",
		help="Generate a DFA-driven high-level AgentSpeak(L) plan library.",
	)
	generate_parser.add_argument("--domain-file", required=True, help="Path to the PDDL domain file.")
	generate_parser.add_argument(
		"--query-dataset",
		help="Optional path to a stored temporal-specification dataset. Defaults to queries_LTLf.json.",
	)
	generate_parser.add_argument(
		"--query-domain",
		help="Optional explicit dataset domain key. Otherwise inferred from the domain file.",
	)
	generate_parser.add_argument(
		"--query-id",
		action="append",
		help=(
			"Stored benchmark query identifier to include in generation. "
			"Repeat to generate from multiple selected queries. Defaults to all domain queries."
		),
	)
	generate_parser.add_argument(
		"--output-root",
		help="Optional explicit output root for the persisted plan-library artifact bundle.",
	)
	generate_parser.add_argument(
		"--fast-downward",
		help=(
			"Optional path to the Fast Downward driver. If omitted, FAST_DOWNWARD "
			"or PATH is used."
		),
	)
	generate_parser.add_argument(
		"--disable-low-level-planning",
		action="store_true",
		help=(
			"Disable Fast Downward for diagnostics. Context-driven generation requires "
			"primitive low-level actions for progress plans."
		),
	)
	generate_parser.add_argument(
		"--render-primitive-actions",
		action="store_true",
		default=True,
		help="Deprecated compatibility flag; primitive ASL actions are rendered by default.",
	)

	sketch_parser = subparsers.add_parser(
		"compile-sketch-policy",
		help="Compile a bound learner-sketches policy into AgentSpeak(L).",
	)
	sketch_parser.add_argument("--domain-file", required=True, help="Path to the PDDL domain file.")
	sketch_parser.add_argument("--policy-file", required=True, help="Path to a DLPlan policy file.")
	sketch_parser.add_argument("--output-file", help="Optional path for the generated .asl file.")
	sketch_parser.add_argument("--target-symbol", default="g", help="ASL achievement-goal target symbol.")
	sketch_parser.add_argument(
		"--target-argument",
		action="append",
		default=[],
		help="Lifted target argument. Repeat for multiple arguments.",
	)
	sketch_parser.add_argument(
		"--no-recurse",
		action="store_true",
		help="Do not append a recursive call to the target goal.",
	)

	domain_level_parser = subparsers.add_parser(
		"synthesize-domain-library",
		help="Synthesize a unified domain-level lifted AgentSpeak(L) library.",
	)
	domain_level_parser.add_argument("--domain-file", required=True, help="Path to the PDDL domain file.")
	domain_level_parser.add_argument(
		"--training-problem",
		action="append",
		default=[],
		help="Training PDDL problem file. Repeat for multiple problems.",
	)
	domain_level_parser.add_argument("--output-file", help="Optional path for the generated .asl file.")
	domain_level_parser.add_argument(
		"--external-sketch-policy",
		action="append",
		default=[],
		help="Optional external sketch policy as name=/path/to/policy.txt.",
	)
	return parser


def main() -> None:
	parser = build_argument_parser()
	args = parser.parse_args()
	if not args.command:
		parser.print_help()
		sys.exit(2)

	if args.command == "generate-library":
		domain_file = _require_existing_path(args.domain_file, label="Domain File")
		pipeline = PlanLibraryGenerationPipeline(
			domain_file=domain_file,
			query_dataset=_absolute_path(args.query_dataset),
			query_domain=args.query_domain,
			query_ids=tuple(args.query_id or ()),
			fast_downward_executable=args.fast_downward,
			enable_low_level_planning=not args.disable_low_level_planning,
			render_primitive_actions=True,
		)
		results = pipeline.build_library_bundle(output_root=_absolute_path(args.output_root))
	elif args.command == "compile-sketch-policy":
		domain_file = _require_existing_path(args.domain_file, label="Domain File")
		policy_file = _require_existing_path(args.policy_file, label="Policy File")
		target = SketchCompilationTarget(
			symbol=str(args.target_symbol).strip() or "g",
			arguments=tuple(
				str(argument).strip()
				for argument in tuple(args.target_argument or ())
				if str(argument).strip()
			),
			recurse=not args.no_recurse,
		)
		result = compile_learner_sketch_policy_to_asl(
			domain_file=domain_file,
			policy_file=policy_file,
			target=target,
		)
		asl_text = render_plan_library_asl(result.plan_library)
		if args.output_file:
			output_file = Path(args.output_file).expanduser().resolve()
			output_file.parent.mkdir(parents=True, exist_ok=True)
			output_file.write_text(asl_text, encoding="utf-8")
		results = {
			"success": True,
			"plan_count": len(result.plan_library.plans),
			"unsupported_features": dict(result.unsupported_features),
			"output_file": _absolute_path(args.output_file),
		}
	elif args.command == "synthesize-domain-library":
		domain_file = _require_existing_path(args.domain_file, label="Domain File")
		training_problems = tuple(
			_require_existing_path(path, label="Training Problem")
			for path in tuple(args.training_problem or ())
		)
		external_policies = tuple(
			_parse_external_sketch_policy(value)
			for value in tuple(args.external_sketch_policy or ())
		)
		result = synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=training_problems,
			external_sketch_policies=external_policies,
		)
		asl_text = render_plan_library_asl(result.plan_library)
		if args.output_file:
			output_file = Path(args.output_file).expanduser().resolve()
			output_file.parent.mkdir(parents=True, exist_ok=True)
			output_file.write_text(asl_text, encoding="utf-8")
		results = {
			"success": True,
			"report": dict(result.report),
			"rejected_external_features": dict(result.rejected_external_features),
			"output_file": _absolute_path(args.output_file),
		}
	else:
		parser.error(f"Unsupported command {args.command!r}")
		return

	print(json.dumps(results, indent=2, default=str))
	sys.exit(0 if results.get("success", False) else 1)


def _parse_external_sketch_policy(value: str) -> ExternalSketchPolicySource:
	text = str(value or "").strip()
	if "=" not in text:
		raise ValueError("--external-sketch-policy must use name=/path/to/policy.txt")
	name, path = text.split("=", 1)
	policy_file = _require_existing_path(path, label="External Sketch Policy")
	return ExternalSketchPolicySource(
		name=name.strip() or Path(policy_file).stem,
		policy_file=policy_file,
	)


if __name__ == "__main__":
	main()
