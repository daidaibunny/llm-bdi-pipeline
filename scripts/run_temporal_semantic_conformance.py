#!/usr/bin/env python3
"""Run independent semantic and zero-action conformance checks for temporal goals."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from typing import Any
from typing import Mapping
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_SUITE_ROOT = PROJECT_ROOT / "paper_artifacts/temporal_semantic_conformance/v1"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts/temporal_semantic_conformance_runs"

if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from domain_level_planning.lifted_ltlf_goal_schema import LTLfAtomSpec  # noqa: E402
from domain_level_planning.lifted_ltlf_goal_schema import LiftedLTLfGoalCase  # noqa: E402
from domain_level_planning.temporal_goal_appender import (  # noqa: E402
	append_lifted_temporal_goal_case_to_library,
)
from evaluation.jason_runtime import JasonPlanLibraryRunner  # noqa: E402
from evaluation.ltlf_trace_semantics import evaluate_formula_ast_on_trace  # noqa: E402
from evaluation.temporal_compilation import DFABuilder  # noqa: E402
from evaluation.temporal_goal_validation import (  # noqa: E402
	evaluate_ltlf_formula_on_trace,
)
from evaluation.temporal_goal_validation import validate_execution_trace  # noqa: E402
from plan_library.models import PlanLibrary  # noqa: E402
from plan_library.rendering import render_plan_library_asl  # noqa: E402
from temporal_specification.prediction_validation import (  # noqa: E402
	ValidatedLTLfPrediction,
)
from temporal_specification.prediction_validation import (  # noqa: E402
	ValidatedTemporalAtom,
)


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--suite-root", type=Path, default=DEFAULT_SUITE_ROOT)
	parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
	parser.add_argument("--run-id")
	parser.add_argument("--timeout-seconds", type=int, default=180)
	parser.add_argument("--jason-java-stack-size", default="64m")
	parser.add_argument("--release-validation-file", type=Path)
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	started_at = datetime.now().isoformat(timespec="seconds")
	start = time.perf_counter()
	suite_root = args.suite_root.expanduser().resolve()
	verify_conformance_release(suite_root)
	suite_file = suite_root / "suite.json"
	suite = load_conformance_suite(suite_file)
	run_id = args.run_id or (
		"temporal-conformance-" + datetime.now().strftime("%Y%m%d-%H%M%S")
	)
	run_root = args.output_root.expanduser().resolve() / run_id
	if run_root.exists():
		raise ValueError(f"Output directory already exists: {run_root}")
	run_root.mkdir(parents=True)

	semantic_records = run_semantic_cases(suite)
	for record in semantic_records:
		print(_progress_line("semantic", record), flush=True)

	zero_action_records = tuple(
		run_zero_action_case(
			case,
			suite_root=suite_root,
			output_dir=run_root / "zero_action" / str(case["case_id"]),
			timeout_seconds=max(1, int(args.timeout_seconds)),
			jason_java_stack_size=str(args.jason_java_stack_size),
		)
		for case in _objects(suite, "zero_action_cases")
	)
	for record in zero_action_records:
		print(_progress_line("zero-action", record), flush=True)

	all_records = (*semantic_records, *zero_action_records)
	summary = {
		"schema_version": 1,
		"artifact_kind": "temporal_semantic_conformance_result",
		"suite_id": suite["suite_id"],
		"suite_file": _portable_path(suite_file),
		"suite_sha256": _sha256(suite_file),
		"fixture_sha256": _release_file_hashes(suite_root),
		"source_revision": _source_revision(),
		"toolchain": _toolchain_provenance(),
		"run_id": run_id,
		"started_at": started_at,
		"completed_at": datetime.now().isoformat(timespec="seconds"),
		"duration_seconds": time.perf_counter() - start,
		"parameters": {
			"jason_timeout_seconds": max(1, int(args.timeout_seconds)),
			"jason_java_stack_size": str(args.jason_java_stack_size),
			"external_val_policy": "not_applicable_for_zero_action_cases",
		},
		"semantic_case_count": len(semantic_records),
		"zero_action_case_count": len(zero_action_records),
		"success_count": sum(bool(record["success"]) for record in all_records),
		"success": bool(all_records) and all(bool(record["success"]) for record in all_records),
		"records": list(all_records),
	}
	_write_json(run_root / "summary.json", summary)
	if args.release_validation_file is not None:
		_write_json(args.release_validation_file.expanduser().resolve(), summary)
	print(
		f"[summary] success={summary['success']} "
		f"passed={summary['success_count']}/{len(all_records)} "
		f"summary={run_root / 'summary.json'}",
		flush=True,
	)
	return 0 if summary["success"] else 1


def load_conformance_suite(path: str | Path) -> Mapping[str, Any]:
	"""Load and fail closed over the tracked conformance-suite contract."""

	payload = json.loads(Path(path).read_text(encoding="utf-8"))
	if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
		raise ValueError("Temporal conformance suite requires schema_version 1.")
	if not str(payload.get("suite_id") or "").strip():
		raise ValueError("Temporal conformance suite requires a suite_id.")
	semantic_cases = _objects(payload, "semantic_cases")
	zero_action_cases = _objects(payload, "zero_action_cases")
	case_ids = [str(case.get("case_id") or "") for case in (*semantic_cases, *zero_action_cases)]
	if not case_ids or any(not case_id for case_id in case_ids):
		raise ValueError("Every temporal conformance case requires a case_id.")
	if len(case_ids) != len(set(case_ids)):
		raise ValueError("Temporal conformance case_id values must be unique.")
	for case in semantic_cases:
		if not str(case.get("requirement") or "").strip():
			raise ValueError(f"{case['case_id']} requires a semantic requirement.")
		if not str(case.get("ltlf_formula") or "").strip():
			raise ValueError(f"{case['case_id']} requires an LTLf formula.")
		if not isinstance(case.get("expected_acceptance"), bool):
			raise ValueError(f"{case['case_id']} requires Boolean expected_acceptance.")
		trace = _sequence(case, "trace")
		if not trace or any(not isinstance(state, Mapping) for state in trace):
			raise ValueError(f"{case['case_id']} requires a non-empty valuation trace.")
	for case in zero_action_cases:
		_validate_zero_action_case(case)
	_validate_declared_fragment(payload, semantic_cases, zero_action_cases)
	return payload


def verify_conformance_release(suite_root: str | Path) -> None:
	"""Verify the tracked suite and synthetic PDDL fixture hashes."""

	root = Path(suite_root)
	manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
	if not isinstance(manifest, Mapping) or manifest.get("schema_version") != 1:
		raise ValueError("Temporal conformance manifest requires schema_version 1.")
	files = _mapping(manifest.get("files"), "manifest files")
	if set(files) != {"suite.json", "domain.pddl", "problem.pddl"}:
		raise ValueError("Temporal conformance manifest has an unexpected file set.")
	for filename, expected_hash in files.items():
		path = root / str(filename)
		if not path.is_file() or _sha256(path) != str(expected_hash):
			raise ValueError(f"Temporal conformance release hash mismatch: {path}")


def run_semantic_cases(suite: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
	"""Compare manual finite-trace semantics with the real MONA-derived DFA."""

	records: list[dict[str, Any]] = []
	for case in _objects(suite, "semantic_cases"):
		formula_ast = _mapping(case.get("formula_ast"), "formula_ast")
		trace = tuple(
			{str(key): bool(value) for key, value in _mapping(item, "trace state").items()}
			for item in _sequence(case, "trace")
		)
		expected = bool(case.get("expected_acceptance"))
		direct = evaluate_formula_ast_on_trace(formula_ast, trace)
		dfa = evaluate_ltlf_formula_on_trace(str(case.get("ltlf_formula") or ""), trace)
		records.append(
			{
				"case_id": str(case["case_id"]),
				"requirement": str(case.get("requirement") or ""),
				"kind": "finite_trace_semantics",
				"expected_acceptance": expected,
				"direct_semantics_acceptance": direct,
				"mona_dfa_acceptance": dfa,
				"state_count": len(trace),
				"success": direct == expected and dfa == expected,
			},
		)
	return tuple(records)


def run_zero_action_case(
	case: Mapping[str, Any],
	*,
	suite_root: Path,
	output_dir: Path,
	timeout_seconds: int,
	jason_java_stack_size: str,
) -> dict[str, Any]:
	"""Run one initial-state acceptance case through Jason, replay, and both DFAs."""

	output_dir.mkdir(parents=True, exist_ok=True)
	domain_file = suite_root / "domain.pddl"
	problem_file = suite_root / "problem.pddl"
	atom = _mapping(case.get("atom"), "atom")
	case_id = str(case["case_id"])
	goal_name = f"g_conformance_{case_id}"
	bindings = {
		str(key): str(value)
		for key, value in _mapping(case.get("bindings"), "bindings").items()
	}
	goal_case = LiftedLTLfGoalCase(
		query_id=case_id,
		goal_name=goal_name,
		problem_file=str(problem_file),
		source_text=str(case.get("requirement") or ""),
		ltlf_formula=str(case.get("ltlf_formula") or ""),
		atoms=(
			LTLfAtomSpec(
				symbol=str(atom["symbol"]),
				predicate=str(atom["name"]),
				args=tuple(str(item) for item in _sequence(atom, "controller_arguments")),
			),
		),
		bindings=bindings,
	)
	updated, dfa_payload = append_lifted_temporal_goal_case_to_library(
		plan_library=PlanLibrary(domain_name="temporal-conformance", plans=()),
		goal_case=goal_case,
		domain_file=domain_file,
		dfa_builder=DFABuilder(),
	)
	_write_json(output_dir / "dfa_payload.json", dfa_payload)
	library_file = output_dir / "plan_library.asl"
	library_file.write_text(render_plan_library_asl(updated), encoding="utf-8")
	jason = JasonPlanLibraryRunner(
		timeout_seconds=timeout_seconds,
		jason_java_stack_size=jason_java_stack_size,
		require_plan_verifier=False,
	).validate(
		domain_file=domain_file,
		problem_file=problem_file,
		plan_library_asl=library_file,
		goal_name=goal_name,
		output_dir=output_dir / "jason",
		temporal_dfa_payload=dfa_payload,
	)
	committed_plan = Path(str(jason.artifacts.get("committed_plan_trace") or ""))
	if not jason.success or not committed_plan.is_file():
		return {
			"case_id": case_id,
			"kind": "zero_action_end_to_end",
			"success": False,
			"jason_success": jason.success,
			"error": jason.error or "Jason produced no committed trace.",
		}
	prediction = _prediction(case_id, case)
	execution = validate_execution_trace(
		audit_row=_audit_row(case),
		prediction=prediction,
		domain_file=domain_file,
		problem_file=problem_file,
		plan_file=committed_plan,
		output_dir=output_dir / "temporal_validation",
	)
	trace_is_empty = committed_plan.read_text(encoding="utf-8") == ""
	return {
		"case_id": case_id,
		"requirement": str(case.get("requirement") or ""),
		"kind": "zero_action_end_to_end",
		"success": jason.success and trace_is_empty and execution.success,
		"jason_success": jason.success,
		"committed_plan_is_empty": trace_is_empty,
		"action_count": execution.action_count,
		"state_count": execution.state_count,
		"val_attempted": execution.val_attempted,
		"val_success": execution.val_success,
		"legality_certificate": execution.legality_certificate,
		"gold_dfa_acceptance": execution.gold_accepted,
		"prediction_dfa_acceptance": execution.prediction_accepted,
	}


def _prediction(case_id: str, case: Mapping[str, Any]) -> ValidatedLTLfPrediction:
	atom = _mapping(case.get("atom"), "atom")
	return ValidatedLTLfPrediction(
		sample_id=case_id,
		ltlf_formula=str(case.get("ltlf_formula") or ""),
		atoms=(
			ValidatedTemporalAtom(
				symbol=str(atom["symbol"]),
				kind=str(atom["kind"]),
				name=str(atom["name"]),
				args=tuple(str(item) for item in _sequence(atom, "arguments")),
				value=int(atom["value"]) if atom.get("value") is not None else None,
			),
		),
		declared_parameters=tuple(
			(name, "item")
			for name in sorted(_mapping(case.get("bindings"), "bindings"))
		),
		constraints=(),
	)


def _audit_row(case: Mapping[str, Any]) -> dict[str, Any]:
	atom = _mapping(case.get("atom"), "atom")
	gold_atom: dict[str, Any] = {
		"atom_id": str(atom["symbol"]),
		"kind": str(atom["kind"]),
		"arguments": [str(item) for item in _sequence(atom, "arguments")],
	}
	if atom["kind"] == "predicate":
		gold_atom["predicate"] = str(atom["name"])
	else:
		gold_atom["function"] = str(atom["name"])
		gold_atom["value"] = int(atom["value"])
	return {
		"sample_id": str(case["case_id"]),
		"gold_atoms": [gold_atom],
		"gold_formula_ast": dict(_mapping(case.get("formula_ast"), "formula_ast")),
		"assignment": dict(_mapping(case.get("bindings"), "bindings")),
	}


def _validate_declared_fragment(
	suite: Mapping[str, Any],
	semantic_cases: Sequence[Mapping[str, Any]],
	zero_action_cases: Sequence[Mapping[str, Any]],
) -> None:
	declared = {str(item) for item in _sequence(suite, "declared_fragment")}
	observed: set[str] = set()
	for case in semantic_cases:
		_collect_operators(_mapping(case.get("formula_ast"), "formula_ast"), observed)
	for case in zero_action_cases:
		if _mapping(case.get("atom"), "atom").get("kind") == "numeric_equality":
			observed.add("numeric_equality_observation")
	missing = sorted(declared - observed)
	if missing:
		raise ValueError(f"Declared temporal fragment lacks conformance cases: {missing}")


def _collect_operators(node: Mapping[str, Any], observed: set[str]) -> None:
	operator = str(node.get("operator") or "")
	name_by_operator = {
		"atom": "atom",
		"not": "literal_negation",
		"and": "conjunction",
		"eventually": "eventually",
		"next": "strong_next",
		"until": "strong_until",
	}
	if operator not in name_by_operator:
		raise ValueError(f"Unsupported conformance formula operator {operator!r}.")
	observed.add(name_by_operator[operator])
	if operator in {"not", "eventually", "next"}:
		operand = _mapping(node.get("operand"), "operand")
		if operator == "not" and operand.get("operator") != "atom":
			raise ValueError("The declared fragment permits literal negation only.")
		_collect_operators(operand, observed)
	elif operator == "and":
		for operand in _objects(node, "operands"):
			_collect_operators(operand, observed)
	elif operator == "until":
		_collect_operators(_mapping(node.get("left"), "left"), observed)
		_collect_operators(_mapping(node.get("right"), "right"), observed)


def _validate_zero_action_case(case: Mapping[str, Any]) -> None:
	if not str(case.get("requirement") or "").strip():
		raise ValueError(f"{case['case_id']} requires a semantic requirement.")
	if not str(case.get("ltlf_formula") or "").strip():
		raise ValueError(f"{case['case_id']} requires an LTLf formula.")
	atom = _mapping(case.get("atom"), "atom")
	kind = str(atom.get("kind") or "")
	if kind not in {"predicate", "numeric_equality"}:
		raise ValueError(f"{case['case_id']} has unsupported atom kind {kind!r}.")
	for field in ("symbol", "name"):
		if not str(atom.get(field) or "").strip():
			raise ValueError(f"{case['case_id']} atom requires {field}.")
	_sequence(atom, "arguments")
	_sequence(atom, "controller_arguments")
	if kind == "numeric_equality" and (
		isinstance(atom.get("value"), bool) or not isinstance(atom.get("value"), int)
	):
		raise ValueError(f"{case['case_id']} numeric equality requires an integer value.")
	_mapping(case.get("bindings"), "bindings")


def _objects(payload: Mapping[str, Any], key: str) -> tuple[Mapping[str, Any], ...]:
	return tuple(_mapping(item, key) for item in _sequence(payload, key))


def _sequence(payload: Mapping[str, Any], key: str) -> Sequence[Any]:
	value = payload.get(key)
	if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
		raise ValueError(f"{key} must be an array.")
	return value


def _mapping(value: object, label: str) -> Mapping[str, Any]:
	if not isinstance(value, Mapping):
		raise ValueError(f"{label} must be an object.")
	return value


def _progress_line(kind: str, record: Mapping[str, Any]) -> str:
	status = "ok" if record.get("success") else "fail"
	return f"[{status}] kind={kind} case={record['case_id']}"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()


def _release_file_hashes(suite_root: Path) -> dict[str, str]:
	manifest = json.loads((suite_root / "manifest.json").read_text(encoding="utf-8"))
	return {
		str(filename): str(digest)
		for filename, digest in _mapping(manifest.get("files"), "manifest files").items()
	}


def _toolchain_provenance() -> dict[str, Any]:
	mona_candidate = str(os.getenv("MONA_BIN") or shutil.which("mona") or "").strip()
	mona_path = Path(mona_candidate).expanduser().resolve() if mona_candidate else None
	java = subprocess.run(
		("java", "-version"),
		capture_output=True,
		text=True,
		check=False,
	)
	java_output = (java.stderr or java.stdout).splitlines()
	return {
		"python": platform.python_version(),
		"ltlf2dfa": importlib.metadata.version("ltlf2dfa"),
		"mona_binary": _portable_path(mona_path) if mona_path is not None else None,
		"mona_sha256": (
			_sha256(mona_path) if mona_path is not None and mona_path.is_file() else None
		),
		"jason_maven_artifact": JasonPlanLibraryRunner.default_jason_maven_artifact,
		"java": java_output[0] if java_output else None,
	}


def _portable_path(path: Path) -> str:
	resolved = path.resolve()
	try:
		return str(resolved.relative_to(PROJECT_ROOT))
	except ValueError:
		return str(resolved)


def _source_revision() -> dict[str, Any]:
	commit = subprocess.run(
		("git", "rev-parse", "HEAD"),
		cwd=PROJECT_ROOT,
		capture_output=True,
		text=True,
		check=False,
	).stdout.strip()
	status = subprocess.run(
		("git", "status", "--porcelain", "--untracked-files=no"),
		cwd=PROJECT_ROOT,
		capture_output=True,
		text=True,
		check=False,
	).stdout.strip()
	return {"commit": commit, "tracked_changes": bool(status)}


if __name__ == "__main__":
	raise SystemExit(main())
