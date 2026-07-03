"""
Command-line entry point for the current atomic-library plus temporal-append path.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_src_dir = str(Path(__file__).parent)
if _src_dir not in sys.path:
	sys.path.insert(0, _src_dir)

from domain_level_planning import (
	append_lifted_temporal_goal_case_to_library,
	compile_moose_readable_policy_to_asl_library,
	load_lifted_ltlf_goal_dataset,
)
from plan_library.models import PlanLibrary
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
			"Build domain-level lifted AgentSpeak(L) atomic libraries from external "
			"generalized-planning artifacts, then append validated lifted LTLf/DFA "
			"query wrappers."
		),
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  python src/main.py compile-moose-atomic-library --policy-file .external/moose/exact-runs/ferry-seed0.model.readable --domain-name ferry --output-root artifacts/domain_libraries/ferry
  python src/main.py append-lifted-temporal-goal --domain-file src/domains/blocks/domain.pddl --plan-library-file artifacts/domain_libraries/blocks/plan_library.json --ltlf-goal-json artifacts/input/blocksworld_lifted_ltlf.json --query-id query_1 --output-root artifacts/domain_libraries/blocks
		""",
	)
	subparsers = parser.add_subparsers(dest="command")

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
	append_temporal_parser.add_argument(
		"--log-dir",
		help="Optional structured execution log directory for this temporal append run.",
	)
	return parser


def main() -> None:
	parser = build_argument_parser()
	args = parser.parse_args()
	if not args.command:
		parser.print_help()
		sys.exit(2)

	if args.command == "compile-moose-atomic-library":
		results = _compile_moose_atomic_library(args)
	elif args.command == "append-lifted-temporal-goal":
		results = _append_lifted_temporal_goal(args)
	else:
		parser.error(f"Unsupported command {args.command!r}")
		return

	print(json.dumps(results, indent=2, default=str))
	sys.exit(0 if results.get("success", False) else 1)


def _compile_moose_atomic_library(args: argparse.Namespace) -> dict[str, Any]:
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
	return {
		"success": True,
		"domain_name": library.domain_name,
		"plan_count": len(library.plans),
		"artifact_paths": artifact_paths,
	}


def _append_lifted_temporal_goal(args: argparse.Namespace) -> dict[str, Any]:
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
	logger = _start_temporal_append_logger(
		log_dir=args.log_dir,
		domain_file=domain_file,
		plan_library_file=plan_library_file,
		ltlf_goal_json=ltlf_goal_json,
		library=library,
		selected_cases=selected_cases,
	)

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
		log_path = _finish_failed_temporal_append_log(logger, errors)
		results: dict[str, Any] = {"success": False, "errors": errors}
		if log_path is not None:
			results["execution_log"] = str(log_path)
		return results

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
	log_path = _finish_successful_temporal_append_log(
		logger,
		dfa_payloads=allow_json_safe(dfa_payloads),
		selected_query_ids=tuple(case.query_id for case in selected_cases),
		artifact_paths=artifact_paths,
		appended_query_count=len(selected_cases),
		plan_count=len(updated_library.plans),
	)
	results = {
		"success": True,
		"domain_name": updated_library.domain_name,
		"appended_query_count": len(selected_cases),
		"plan_count": len(updated_library.plans),
		"artifact_paths": artifact_paths,
	}
	if log_path is not None:
		results["execution_log"] = str(log_path)
	return results


def allow_json_safe(payload: object) -> object:
	return json.loads(json.dumps(payload, default=str))


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


def _start_temporal_append_logger(
	*,
	log_dir: str | None,
	domain_file: str,
	plan_library_file: str,
	ltlf_goal_json: str,
	library: PlanLibrary,
	selected_cases: tuple[object, ...],
):
	if not log_dir:
		return None
	from execution_logging import ExecutionLogger

	source_text = "\n".join(
		str(getattr(case, "source_text", "") or getattr(case, "query_id", "") or "").strip()
		for case in selected_cases
	)
	logger = ExecutionLogger(log_dir)
	logger.start_pipeline(
		source_text,
		mode="temporal_goal_append",
		domain_file=domain_file,
		domain_name=library.domain_name,
	)
	logger.log_input_artifact(
		{
			"ltlf_json": Path(ltlf_goal_json).read_text(encoding="utf-8"),
			"plan_library": Path(plan_library_file).read_text(encoding="utf-8"),
		},
		status="success",
		metadata={
			"query_ids": [
				str(getattr(case, "query_id", "") or "").strip()
				for case in selected_cases
			],
			"case_count": len(selected_cases),
		},
	)
	return logger


def _finish_failed_temporal_append_log(logger, errors: list[dict[str, object]]) -> Path | None:
	if logger is None:
		return None
	logger.log_dfa_validation(
		None,
		status="failed",
		error=json.dumps(errors, default=str),
		metadata={"error_count": len(errors)},
	)
	return logger.end_pipeline(success=False)


def _finish_successful_temporal_append_log(
	logger,
	*,
	dfa_payloads: object,
	selected_query_ids: tuple[str, ...],
	artifact_paths: dict[str, str],
	appended_query_count: int,
	plan_count: int,
) -> Path | None:
	if logger is None:
		return None
	logger.log_dfa_conversion(
		{"dfa_payload": dfa_payloads},
		status="success",
		metadata={"query_count": len(selected_query_ids)},
	)
	logger.log_dfa_validation(
		None,
		status="success",
		metadata={"query_ids": list(selected_query_ids)},
	)
	logger.log_agentspeak_append(
		artifact_paths,
		status="success",
		metadata={
			"appended_query_count": appended_query_count,
			"plan_count": plan_count,
		},
	)
	return logger.end_pipeline(success=True)


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
