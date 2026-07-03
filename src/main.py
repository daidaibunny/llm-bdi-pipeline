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
from plan_library.models import PlanLibrary
from domain_level_planning import (
	discover_backend_manifest,
	ExternalSketchPolicySource,
	LearnerSketchesRunConfig,
	SketchCompilationTarget,
	append_lifted_temporal_goal_case_to_library,
	build_domain_level_temporal_artifact,
	compile_learner_sketch_policy_to_asl,
	compile_moose_readable_policy_to_asl_library,
	load_lifted_ltlf_goal_dataset,
	persist_domain_level_temporal_artifact,
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
  python src/main.py generate-library --domain-file ./src/domains/blocks/domain.pddl --query-domain blocksworld --query-id query_1
  python src/main.py synthesize-domain-library --domain-file ./src/domains/gripper/domain.pddl --training-problem ./src/domains/gripper/train/instance-1.pddl --output-file ./artifacts/domain_library/gripper.asl
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

	moose_parser = subparsers.add_parser(
		"compile-moose-atomic-library",
		help="Compile a MOOSE readable singleton-goal policy into a domain atomic ASL library.",
	)
	moose_parser.add_argument("--policy-file", required=True, help="MOOSE readable policy file.")
	moose_parser.add_argument("--domain-name", required=True, help="PDDL domain name for the output library.")
	moose_parser.add_argument(
		"--output-root",
		required=True,
		help="Output root for plan_library.json, plan_library.asl, and metadata.",
	)

	append_temporal_parser = subparsers.add_parser(
		"append-lifted-temporal-goal",
		help=(
			"Append lifted LTLf/DFA query wrappers to an existing domain atomic "
			"ASL library."
		),
	)
	append_temporal_parser.add_argument("--domain-file", required=True, help="Path to the PDDL domain file.")
	append_temporal_parser.add_argument(
		"--plan-library-file",
		required=True,
		help="Existing domain-level plan_library.json file.",
	)
	append_temporal_parser.add_argument(
		"--ltlf-goal-json",
		required=True,
		help="Lifted LTLf goal JSON produced by the external Input component.",
	)
	append_temporal_parser.add_argument(
		"--query-id",
		action="append",
		help="Query id to append. Repeat for multiple queries. Defaults to all cases.",
	)
	append_temporal_parser.add_argument(
		"--output-root",
		required=True,
		help="Output root for the updated library and DFA metadata.",
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
	domain_level_parser.add_argument(
		"--run-learner-sketches",
		action="store_true",
		help="Run the pinned learner-sketches backend and consume its minimized policy artifact.",
	)
	domain_level_parser.add_argument(
		"--learner-sketches-backend-root",
		help="Root containing .external/gp-backends/learner-sketches. Defaults to project .external/gp-backends.",
	)
	domain_level_parser.add_argument(
		"--learner-sketches-problems-directory",
		help="Training problems directory passed to learner-sketches. Defaults to the first training problem's parent.",
	)
	domain_level_parser.add_argument(
		"--learner-sketches-workspace",
		help="Workspace for learner-sketches output. Required when --run-learner-sketches is set.",
	)
	domain_level_parser.add_argument("--learner-sketches-width", type=int, default=1)
	domain_level_parser.add_argument("--learner-sketches-max-rss-gb", type=float, default=16.0)
	domain_level_parser.add_argument("--learner-sketches-timeout-seconds", type=int)
	domain_level_parser.add_argument(
		"--learner-sketches-max-states-per-instance",
		type=int,
		default=10000,
	)
	domain_level_parser.add_argument(
		"--learner-sketches-max-time-per-instance",
		type=int,
		default=10000,
	)
	domain_level_parser.add_argument(
		"--learner-sketches-python",
		help="Python executable for learner-sketches. Defaults to backend environment detection.",
	)
	domain_level_parser.add_argument(
		"--synthesis-profile",
		choices=("bootstrap", "paper"),
		default="bootstrap",
		help=(
			"bootstrap permits schema-derived fallback; paper requires executable "
			"external learned-policy bindings and bounded validation."
		),
	)

	temporal_artifact_parser = subparsers.add_parser(
		"build-temporal-domain-artifact",
		help="Build a domain-level ASL library plus query-specific DFA controller metadata.",
	)
	temporal_artifact_parser.add_argument("--domain-file", required=True, help="Path to the PDDL domain file.")
	temporal_artifact_parser.add_argument(
		"--training-problem",
		action="append",
		default=[],
		help="Training PDDL problem file. Repeat for multiple problems.",
	)
	temporal_artifact_parser.add_argument(
		"--query-dataset",
		help="Optional path to a stored temporal-specification dataset. Defaults to queries_LTLf.json.",
	)
	temporal_artifact_parser.add_argument(
		"--query-domain",
		help="Optional explicit dataset domain key. Otherwise inferred from the domain file.",
	)
	temporal_artifact_parser.add_argument(
		"--query-id",
		action="append",
		help="Stored benchmark query identifier to include. Repeat for multiple queries.",
	)
	temporal_artifact_parser.add_argument(
		"--output-root",
		required=True,
		help="Output root for the domain-level temporal artifact bundle.",
	)
	temporal_artifact_parser.add_argument(
		"--synthesis-profile",
		choices=("bootstrap", "paper"),
		default="bootstrap",
		help="Domain-level library synthesis profile.",
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
	elif args.command == "compile-moose-atomic-library":
		policy_file = _require_existing_path(args.policy_file, label="MOOSE Policy File")
		output_root = _require_output_root(args.output_root)
		policy_text = Path(policy_file).read_text(encoding="utf-8")
		source_name = Path(policy_file).stem.replace(".model", "")
		library = compile_moose_readable_policy_to_asl_library(
			policy_text,
			domain_name=str(args.domain_name).strip(),
			source_name=source_name,
			policy_file=policy_file,
		)
		artifact_paths = _persist_current_plan_library(
			plan_library=library,
			output_root=output_root,
			metadata={
				"artifact_kind": "moose_atomic_library",
				"backend": "moose",
				"policy_file": policy_file,
				"source_name": source_name,
			},
		)
		results = {
			"success": True,
			"domain_name": library.domain_name,
			"plan_count": len(library.plans),
			"artifact_paths": artifact_paths,
		}
	elif args.command == "append-lifted-temporal-goal":
		domain_file = _require_existing_path(args.domain_file, label="Domain File")
		plan_library_file = _require_existing_path(
			args.plan_library_file,
			label="Plan Library File",
		)
		ltlf_goal_json = _require_existing_path(
			args.ltlf_goal_json,
			label="Lifted LTLf Goal JSON",
		)
		output_root = _require_output_root(args.output_root)
		library = PlanLibrary.from_dict(
			json.loads(Path(plan_library_file).read_text(encoding="utf-8")),
		)
		dataset = load_lifted_ltlf_goal_dataset(ltlf_goal_json)
		selected_query_ids = {
			str(query_id).strip()
			for query_id in tuple(args.query_id or ())
			if str(query_id).strip()
		}
		selected_cases = tuple(
			case
			for case in dataset.cases
			if not selected_query_ids or case.query_id in selected_query_ids
		)
		if selected_query_ids and len(selected_cases) != len(selected_query_ids):
			found = {case.query_id for case in selected_cases}
			missing = sorted(selected_query_ids - found)
			raise ValueError(f"Unknown lifted LTLf query ids: {', '.join(missing)}")
		from evaluation.temporal_compilation import DFABuilder

		dfa_builder = DFABuilder()
		dfa_payloads: dict[str, object] = {}
		updated_library = library
		errors: list[dict[str, object]] = []
		for case in selected_cases:
			try:
				updated_library, dfa_payload = append_lifted_temporal_goal_case_to_library(
					plan_library=updated_library,
					goal_case=case,
					domain_file=domain_file,
					dfa_builder=dfa_builder,
				)
				dfa_payloads[case.query_id] = dict(dfa_payload)
			except Exception as error:  # noqa: BLE001 - returned as validator feedback.
				errors.append(
					{
						"query_id": case.query_id,
						"goal_name": case.goal_name,
						"error_type": _temporal_append_error_type(error),
						"message": str(error),
					},
				)
		if errors:
			results = {"success": False, "errors": errors}
		else:
			artifact_paths = _persist_current_plan_library(
				plan_library=updated_library,
				output_root=output_root,
				metadata={
					"artifact_kind": "domain_library_with_temporal_append",
					"source_plan_library_file": plan_library_file,
					"ltlf_goal_json": ltlf_goal_json,
					"query_ids": [case.query_id for case in selected_cases],
					"dfa_payloads": dfa_payloads,
				},
			)
			results = {
				"success": True,
				"domain_name": updated_library.domain_name,
				"appended_query_count": len(selected_cases),
				"plan_count": len(updated_library.plans),
				"artifact_paths": artifact_paths,
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
		learner_backend = None
		learner_runs = ()
		if args.run_learner_sketches:
			if not args.learner_sketches_workspace:
				parser.error("--learner-sketches-workspace is required with --run-learner-sketches")
			if not training_problems and not args.learner_sketches_problems_directory:
				parser.error(
					"--training-problem or --learner-sketches-problems-directory is required "
					"with --run-learner-sketches",
				)
			backend_root = (
				Path(args.learner_sketches_backend_root).expanduser().resolve()
				if args.learner_sketches_backend_root
				else Path(__file__).resolve().parents[1] / ".external" / "gp-backends"
			)
			learner_backend = discover_backend_manifest(
				root=backend_root,
				name="learner-sketches",
				url="https://github.com/bonetblai/learner-sketches.git",
				commit="7a7ea6a6356035afa16ed958b53d8edc86994e0a",
			)
			problems_directory = (
				_absolute_path(args.learner_sketches_problems_directory)
				if args.learner_sketches_problems_directory
				else str(Path(training_problems[0]).parent)
			)
			learner_runs = (
				LearnerSketchesRunConfig(
					domain_file=domain_file,
					problems_directory=problems_directory,
					workspace=_absolute_path(args.learner_sketches_workspace),
					width=args.learner_sketches_width,
					python_executable=args.learner_sketches_python,
					max_states_per_instance=args.learner_sketches_max_states_per_instance,
					max_time_per_instance=args.learner_sketches_max_time_per_instance,
					max_rss_gb=args.learner_sketches_max_rss_gb,
					timeout_seconds=args.learner_sketches_timeout_seconds,
					use_resource_guard=True,
				),
			)
		result = synthesize_domain_level_asl_library(
			domain_file=domain_file,
			training_problem_files=training_problems,
			external_sketch_policies=external_policies,
			learner_sketches_backend=learner_backend,
			learner_sketches_runs=learner_runs,
			synthesis_profile=args.synthesis_profile,
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
	elif args.command == "build-temporal-domain-artifact":
		domain_file = _require_existing_path(args.domain_file, label="Domain File")
		training_problems = tuple(
			_require_existing_path(path, label="Training Problem")
			for path in tuple(args.training_problem or ())
		)
		artifact = build_domain_level_temporal_artifact(
			domain_file=domain_file,
			training_problem_files=training_problems,
			query_dataset=_absolute_path(args.query_dataset),
			query_domain=args.query_domain,
			query_ids=tuple(args.query_id or ()),
			synthesis_profile=args.synthesis_profile,
		)
		artifact_paths = persist_domain_level_temporal_artifact(
			artifact_root=_require_output_root(args.output_root),
			artifact=artifact,
		)
		results = {
			"success": True,
			"artifact_root": _absolute_path(args.output_root),
			"artifact_paths": artifact_paths,
			"query_count": len(artifact.query_sequence),
			"dfa_count": len(artifact.dfa_metadata),
			"dfa_progress_request_count": sum(
				len(requests) for requests in artifact.dfa_progress_requests.values()
			),
			"domain_level_contract": dict(
				artifact.synthesis_result.report.get("domain_level_contract") or {},
			),
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


def _require_output_root(path_text: str | None) -> str:
	resolved_path = _absolute_path(path_text)
	if not resolved_path:
		print("=" * 80)
		print("ERROR: Output Root Required")
		print("=" * 80)
		sys.exit(1)
	return resolved_path


def _persist_current_plan_library(
	*,
	plan_library: PlanLibrary,
	output_root: str,
	metadata: dict[str, object],
) -> dict[str, str]:
	root = Path(output_root).expanduser().resolve()
	root.mkdir(parents=True, exist_ok=True)
	library_json = root / "plan_library.json"
	library_asl = root / "plan_library.asl"
	metadata_file = root / "artifact_metadata.json"
	library_json.write_text(
		json.dumps(plan_library.to_dict(), indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	library_asl.write_text(render_plan_library_asl(plan_library), encoding="utf-8")
	metadata_file.write_text(
		json.dumps(
			{
				**dict(metadata),
				"domain_name": plan_library.domain_name,
				"plan_count": len(plan_library.plans),
			},
			indent=2,
			sort_keys=True,
			default=str,
		)
		+ "\n",
		encoding="utf-8",
	)
	return {
		"plan_library": str(library_json),
		"plan_library_asl": str(library_asl),
		"artifact_metadata": str(metadata_file),
	}


def _temporal_append_error_type(error: Exception) -> str:
	message = str(error)
	if "singleton-literal transition contract" in message:
		return "dfa_singleton_literal_validation_failed"
	if "Failed to convert LTLf to DFA" in message:
		return "ltlf_to_dfa_execution_failure"
	if "negative_literal_template_not_supported" in message:
		return "negative_literal_template_not_supported"
	if "undeclared PDDL predicate" in message:
		return "unsupported_predicate"
	if "wrong arity" in message:
		return "wrong_arity"
	return type(error).__name__


if __name__ == "__main__":
	main()
