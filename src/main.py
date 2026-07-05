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

from domain_level_planning import (  # noqa: E402
	append_lifted_temporal_goal_case_to_library,
	compile_moose_readable_policy_to_minimal_module_asl_library,
	compile_moose_readable_policy_to_asl_library,
	load_lifted_ltlf_goal_dataset,
)
from evaluation.jason_runtime import JasonPlanLibraryRunner  # noqa: E402
from plan_library.models import PlanLibrary  # noqa: E402
from plan_library.rendering import render_plan_library_asl  # noqa: E402
from utils.pddl_parser import PDDLParser  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOMAIN_LIBRARY_ROOT = PROJECT_ROOT / "artifacts" / "domain_libraries"


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
  python src/main.py compile-moose-atomic-library --policy-file .external/moose/exact-runs/ferry-seed0.model.readable --domain-name ferry
  python src/main.py compile-moose-atomic-library --policy-file tmp/moose-blocks-e2e/blocks-probe-first4.model.readable --domain-file src/domains/blocks/domain.pddl --domain-name blocks --minimal-modules
  python src/main.py append-lifted-temporal-goal --domain-file src/domains/blocks/domain.pddl --ltlf-goal-json artifacts/input/blocksworld_lifted_ltlf.json --query-id query_1
  python src/main.py validate-jason-plan-library --domain-file src/domains/blocks/domain.pddl --problem-file src/domains/blocks/test/instance-69.pddl --goal-name g_blocks_user_goal_1
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
		"--domain-file",
		help="PDDL domain file. Required when --minimal-modules is set.",
	)
	moose_parser.add_argument(
		"--minimal-modules",
		action="store_true",
		help=(
			"Deprecated alias for --post-moose-recursive."
		),
	)
	moose_parser.add_argument(
		"--post-moose-recursive",
		action="store_true",
		help=(
			"Use MOOSE singleton predicate evidence and PDDL action schemas to "
			"synthesize compact recursive atomic literal modules before ASL rendering."
		),
	)
	moose_parser.add_argument(
		"--library-root",
		default=str(DEFAULT_DOMAIN_LIBRARY_ROOT),
		help=(
			"Root directory for canonical per-domain libraries. The command writes "
			"<library-root>/<domain>/plan_library.{json,asl}."
		),
	)
	moose_parser.add_argument(
		"--output-root",
		help=(
			"Deprecated compatibility alias for the canonical domain directory. "
			"If provided, it must equal <library-root>/<domain>."
		),
	)
	moose_parser.add_argument(
		"--overwrite",
		action="store_true",
		help="Allow rebuilding an existing canonical domain library.",
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
		help=(
			"Existing canonical domain plan_library.json file. Defaults to "
			"<library-root>/<domain>/plan_library.json and must match it if provided."
		),
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
		"--library-root",
		default=str(DEFAULT_DOMAIN_LIBRARY_ROOT),
		help=(
			"Root directory for canonical per-domain libraries. The command updates "
			"<library-root>/<domain>/plan_library.{json,asl} in place."
		),
	)
	append_temporal_parser.add_argument(
		"--output-root",
		help=(
			"Deprecated compatibility alias for the canonical domain directory. "
			"If provided, it must equal <library-root>/<domain>."
		),
	)
	append_temporal_parser.add_argument(
		"--log-dir",
		help="Optional structured execution log directory for this temporal append run.",
	)

	jason_parser = subparsers.add_parser(
		"validate-jason-plan-library",
		help="Run a canonical domain AgentSpeak(L) library in the real Jason interpreter.",
	)
	jason_parser.add_argument("--domain-file", required=True, help="Path to the PDDL domain file.")
	jason_parser.add_argument("--problem-file", required=True, help="Path to the PDDL problem file.")
	jason_parser.add_argument(
		"--goal-name",
		required=True,
		help="Top-level AgentSpeak achievement goal to run, for example g_blocks_user_goal_1.",
	)
	jason_parser.add_argument(
		"--plan-library-asl",
		help=(
			"Canonical plan_library.asl file. Defaults to "
			"<library-root>/<domain>/plan_library.asl and must match it if provided."
		),
	)
	jason_parser.add_argument(
		"--library-root",
		default=str(DEFAULT_DOMAIN_LIBRARY_ROOT),
		help="Root directory for canonical per-domain libraries.",
	)
	jason_parser.add_argument(
		"--output-dir",
		help="Directory for Jason runtime artifacts. Defaults to artifacts/jason_validation/<domain>/<goal>.",
	)
	jason_parser.add_argument(
		"--timeout-seconds",
		type=int,
		default=60,
		help="Hard timeout for the Jason runtime process.",
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
	elif args.command == "validate-jason-plan-library":
		results = _validate_jason_plan_library(args)
	else:
		parser.error(f"Unsupported command {args.command!r}")
		return

	print(json.dumps(results, indent=2, default=str))
	sys.exit(0 if results.get("success", False) else 1)


def _compile_moose_atomic_library(args: argparse.Namespace) -> dict[str, Any]:
	policy_file = _require_existing_path(args.policy_file, label="MOOSE Policy File")
	use_post_moose_recursive = bool(
		getattr(args, "post_moose_recursive", False)
		or getattr(args, "minimal_modules", False),
	)
	domain_file = (
		_require_existing_path(args.domain_file, label="Domain File")
		if use_post_moose_recursive
		else _absolute_path(args.domain_file)
	)
	pddl_domain_name = (
		PDDLParser.parse_domain(domain_file).name
		if domain_file is not None
		else str(args.domain_name).strip()
	)
	source_metadata = _domain_source_metadata(domain_file)
	domain_name = _canonical_domain_key_for_domain_file(
		domain_file,
		fallback_domain_name=str(args.domain_name).strip(),
	)
	output_root = _canonical_domain_library_dir(
		library_root=args.library_root,
		domain_name=domain_name,
		output_root=args.output_root,
	)
	policy_text = Path(policy_file).read_text(encoding="utf-8")
	source_name = Path(policy_file).stem.replace(".model", "")
	if use_post_moose_recursive:
		library = compile_moose_readable_policy_to_minimal_module_asl_library(
			policy_text,
			domain_file=str(domain_file),
			domain_name=domain_name,
			source_name=source_name,
			policy_file=policy_file,
		)
	else:
		library = compile_moose_readable_policy_to_asl_library(
			policy_text,
			domain_name=domain_name,
			source_name=source_name,
			policy_file=policy_file,
		)
	artifact_paths = _persist_current_plan_library(
		plan_library=library,
		output_root=output_root,
		metadata={
			"artifact_kind": (
				"moose_seeded_atomic_minimal_literal_module_library"
				if use_post_moose_recursive
				else "moose_atomic_library"
			),
			"backend": "moose",
			"domain_file": domain_file,
			"pddl_domain_name": pddl_domain_name,
			"minimal_modules": use_post_moose_recursive,
			"post_moose_recursive": use_post_moose_recursive,
			"moose_backend_path": (
				"post_moose_recursive_module_synthesis"
				if use_post_moose_recursive
				else "native_train_dump_policy"
			),
			"moose_official_benchmark": _is_moose_official_benchmark(source_metadata),
			"policy_file": policy_file,
			"source_name": source_name,
			"source_metadata": source_metadata,
		},
		allow_overwrite=bool(getattr(args, "overwrite", False)),
	)
	return {
		"success": True,
		"domain_name": library.domain_name,
		"plan_count": len(library.plans),
		"artifact_paths": artifact_paths,
	}


def _append_lifted_temporal_goal(args: argparse.Namespace) -> dict[str, Any]:
	domain_file = _require_existing_path(args.domain_file, label="Domain File")
	domain = PDDLParser.parse_domain(domain_file)
	domain_key = _canonical_domain_key_for_domain_file(
		domain_file,
		fallback_domain_name=domain.name,
	)
	output_root = _canonical_domain_library_dir(
		library_root=args.library_root,
		domain_name=domain_key,
		output_root=args.output_root,
	)
	canonical_plan_library_file = str(Path(output_root) / "plan_library.json")
	plan_library_file = _require_existing_path(
		args.plan_library_file or canonical_plan_library_file,
		label="Plan Library File",
	)
	if Path(plan_library_file).resolve() != Path(canonical_plan_library_file).resolve():
		raise ValueError(
			"noncanonical_domain_library: append-lifted-temporal-goal must update "
			f"the canonical library for domain {domain.name!r}: "
			f"{canonical_plan_library_file}",
		)
	ltlf_goal_json = _require_existing_path(
		args.ltlf_goal_json,
		label="Lifted LTLf Goal JSON",
	)
	library = PlanLibrary.from_dict(
		json.loads(Path(plan_library_file).read_text(encoding="utf-8")),
	)
	if library.domain_name not in {domain_key, domain.name}:
		raise ValueError(
			"domain_library_mismatch: loaded plan library domain "
			f"{library.domain_name!r} does not match canonical domain key "
			f"{domain_key!r} or PDDL domain {domain.name!r}.",
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

	existing_metadata = _existing_artifact_metadata(output_root)
	artifact_paths = _persist_current_plan_library(
		plan_library=updated_library,
		output_root=output_root,
		metadata={
			**existing_metadata,
			"base_artifact_kind": existing_metadata.get("artifact_kind"),
			"artifact_kind": "domain_library_with_temporal_append",
			"source_plan_library_file": plan_library_file,
			"ltlf_goal_json": ltlf_goal_json,
			"pddl_domain_name": domain.name,
			"query_ids": [case.query_id for case in selected_cases],
			"dfa_payloads": dfa_payloads,
		},
		allow_overwrite=True,
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


def _validate_jason_plan_library(args: argparse.Namespace) -> dict[str, Any]:
	domain_file = _require_existing_path(args.domain_file, label="Domain File")
	problem_file = _require_existing_path(args.problem_file, label="Problem File")
	domain = PDDLParser.parse_domain(domain_file)
	domain_key = _canonical_domain_key_for_domain_file(
		domain_file,
		fallback_domain_name=domain.name,
	)
	output_root = _canonical_domain_library_dir(
		library_root=args.library_root,
		domain_name=domain_key,
		output_root=None,
	)
	canonical_asl = Path(output_root) / "plan_library.asl"
	plan_library_asl = _require_existing_path(
		args.plan_library_asl or str(canonical_asl),
		label="Plan Library ASL File",
	)
	if Path(plan_library_asl).resolve() != canonical_asl.resolve():
		raise ValueError(
			"noncanonical_domain_library: validate-jason-plan-library must run "
			f"the canonical ASL library for domain {domain_key!r}: {canonical_asl}",
		)
	goal_name = str(args.goal_name or "").strip()
	if not goal_name:
		raise ValueError("goal_name is required for Jason validation.")
	output_dir = (
		Path(args.output_dir).expanduser().resolve()
		if args.output_dir
		else PROJECT_ROOT
		/ "artifacts"
		/ "jason_validation"
		/ domain_key
		/ goal_name
	)
	runner = JasonPlanLibraryRunner(timeout_seconds=max(1, int(args.timeout_seconds or 60)))
	result = runner.validate(
		domain_file=domain_file,
		problem_file=problem_file,
		plan_library_asl=plan_library_asl,
		goal_name=goal_name,
		output_dir=output_dir,
	)
	return result.to_dict()


def allow_json_safe(payload: object) -> object:
	return json.loads(json.dumps(payload, default=str))


def _canonical_domain_library_dir(
	*,
	library_root: str | None,
	domain_name: str,
	output_root: str | None,
) -> str:
	root = Path(library_root or DEFAULT_DOMAIN_LIBRARY_ROOT).expanduser().resolve()
	domain_key = _domain_library_key(domain_name)
	canonical_dir = (root / domain_key).resolve()
	if output_root:
		resolved_output_root = Path(output_root).expanduser().resolve()
		if resolved_output_root != canonical_dir:
			raise ValueError(
				"noncanonical_domain_library: this pipeline maintains exactly one "
				f"ASL library per domain. Domain {domain_name!r} must use "
				f"{canonical_dir}, not {resolved_output_root}.",
			)
	return str(canonical_dir)


def _canonical_domain_key_for_domain_file(
	domain_file: str | Path | None,
	*,
	fallback_domain_name: str,
) -> str:
	if domain_file is None:
		return _domain_library_key(fallback_domain_name)
	path = Path(domain_file).expanduser().resolve()
	if path.parent.parent.name == "domains" and path.name == "domain.pddl":
		return _domain_library_key(path.parent.name)
	return _domain_library_key(fallback_domain_name)


def _domain_library_key(domain_name: str) -> str:
	key = str(domain_name or "").strip().lower()
	if not key:
		raise ValueError("Domain name is required for canonical library storage.")
	if "/" in key or "\\" in key or key in {".", ".."}:
		raise ValueError(f"Invalid domain name for library storage: {domain_name!r}")
	return key


def _persist_current_plan_library(
	*,
	plan_library: PlanLibrary,
	output_root: str,
	metadata: dict[str, object],
	allow_overwrite: bool,
) -> dict[str, str]:
	root = Path(output_root).expanduser().resolve()
	root.mkdir(parents=True, exist_ok=True)
	library_json = root / "plan_library.json"
	library_asl = root / "plan_library.asl"
	metadata_file = root / "artifact_metadata.json"
	if not allow_overwrite and (library_json.exists() or library_asl.exists()):
		raise ValueError(
			"domain_library_exists: refusing to overwrite the canonical domain "
			f"library for {plan_library.domain_name!r}. Use --overwrite only when "
			"you intentionally want to rebuild the base atomic library.",
		)
	library_json.write_text(
		json.dumps(plan_library.to_dict(), indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	library_asl.write_text(render_plan_library_asl(plan_library), encoding="utf-8")
	metadata_file.write_text(
		json.dumps(
			{
				**dict(metadata),
				"canonical_domain_library": True,
				"domain_library_dir": str(root),
				"domain_name": plan_library.domain_name,
				"plan_count": len(plan_library.plans),
				"library_quality": dict(plan_library.metadata.get("library_quality") or {}),
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


def _existing_artifact_metadata(output_root: str) -> dict[str, object]:
	metadata_file = Path(output_root).expanduser().resolve() / "artifact_metadata.json"
	if not metadata_file.exists():
		return {}
	try:
		payload = json.loads(metadata_file.read_text(encoding="utf-8"))
	except json.JSONDecodeError:
		return {}
	return dict(payload) if isinstance(payload, dict) else {}


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


def _domain_source_metadata(domain_file: str | None) -> dict[str, object]:
	if not domain_file:
		return {}
	source_file = Path(domain_file).resolve().parent / "source.json"
	if not source_file.exists():
		return {}
	try:
		payload = json.loads(source_file.read_text(encoding="utf-8"))
	except json.JSONDecodeError:
		return {"source_file": str(source_file), "source_parse_error": True}
	return dict(payload) if isinstance(payload, dict) else {"source_file": str(source_file)}


def _is_moose_official_benchmark(source_metadata: dict[str, object]) -> bool:
	return str(source_metadata.get("source_id") or "") == "moose_official_artifact"


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
	if "duplicate_temporal_goal" in message:
		return "duplicate_temporal_goal"
	if "singleton-literal transition contract" in message:
		return "dfa_singleton_literal_validation_failed"
	if "Failed to convert LTLf to DFA" in message:
		return "ltlf_to_dfa_execution_failure"
	if "negative_literal_template_not_supported" in message:
		return "negative_literal_template_not_supported"
	if "nonlinear_temporal_goal_not_supported" in message:
		return "nonlinear_temporal_goal_not_supported"
	if "undeclared PDDL predicate" in message:
		return "unsupported_predicate"
	if "wrong arity" in message:
		return "wrong_arity"
	return type(error).__name__


if __name__ == "__main__":
	main()
