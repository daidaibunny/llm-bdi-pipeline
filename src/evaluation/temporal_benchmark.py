"""Canonical, provenance-carrying benchmark bundle for validated lifted TEGs."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from domain_level_planning.lifted_ltlf_goal_schema import (
	load_lifted_ltlf_goal_dataset,
)


_BUNDLE_KEYS = frozenset(
	{
		"schema_version",
		"artifact_kind",
		"benchmark_id",
		"temporal_logic",
		"formula_fragment",
		"provenance",
		"evaluation_protocol",
		"counts",
		"domains",
	},
)
_HIDDEN_KEYS = frozenset(
	{
		"assignment",
		"gold_atoms",
		"gold_formula",
		"gold_formula_ast",
		"state_fingerprints",
		"witness_actions",
	},
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_ATOM_RE = re.compile(r"a\d+")


def build_temporal_goal_benchmark_bundle(
	*,
	handoff_manifest_file: str | Path,
	manifest_file: str | Path,
	worklist_file: str | Path,
	predictions_file: str | Path,
	translation_results_file: str | Path,
	problem_results_file: str | Path,
	validated_append_datasets_dir: str | Path,
	domains_root: str | Path,
	source_delivery_archive: Mapping[str, str],
	validation_implementation_commit: str,
	sealed_input_archives: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, object]:
	"""Build one multi-domain benchmark from independently validated model output."""

	handoff_manifest_path = Path(handoff_manifest_file)
	manifest_path = Path(manifest_file)
	worklist_path = Path(worklist_file)
	predictions_path = Path(predictions_file)
	translation_results_path = Path(translation_results_file)
	problem_results_path = Path(problem_results_file)
	dataset_root = Path(validated_append_datasets_dir)
	domain_root = Path(domains_root)
	handoff_manifest = _read_json(handoff_manifest_path)
	manifest_rows = _read_jsonl(manifest_path)
	worklist_rows = _read_jsonl(worklist_path)
	prediction_rows = _read_jsonl(predictions_path)
	translation_results = _read_jsonl(translation_results_path)
	problem_results = _read_jsonl(problem_results_path)

	benchmark_id = _required_text(handoff_manifest, "benchmark_id")
	archive_provenance = _validated_archive_provenance(source_delivery_archive)
	input_archive_provenance = {
		str(name): _validated_archive_provenance(archive)
		for name, archive in sorted((sealed_input_archives or {}).items())
	}
	commit = str(validation_implementation_commit or "").strip().lower()
	if not _COMMIT_RE.fullmatch(commit):
		raise ValueError("validation_implementation_commit must be a full Git SHA-1.")

	manifest_by_sample = _unique_by(manifest_rows, "sample_id", label="manifest")
	worklist_by_translation = _unique_by(
		worklist_rows,
		"translation_id",
		label="worklist",
	)
	prediction_by_translation = _unique_by(
		prediction_rows,
		"translation_id",
		label="predictions",
	)
	translation_result_by_id = _unique_by(
		translation_results,
		"translation_id",
		label="translation results",
	)
	problem_result_by_sample = _unique_by(
		problem_results,
		"sample_id",
		label="problem results",
	)
	translation_ids = set(worklist_by_translation)
	if set(prediction_by_translation) != translation_ids:
		raise ValueError("Predictions must cover every worklist translation_id exactly once.")
	if set(translation_result_by_id) != translation_ids:
		raise ValueError("Translation results must cover every translation_id exactly once.")
	if set(problem_result_by_sample) != set(manifest_by_sample):
		raise ValueError("Problem results must cover every manifest sample_id exactly once.")

	translation_by_sample = _validated_membership(
		worklist_rows,
		expected_sample_ids=set(manifest_by_sample),
	)
	for translation_id in sorted(translation_ids):
		_prediction_success(prediction_by_translation[translation_id])
		_translation_success(translation_result_by_id[translation_id])
	for sample_id in sorted(manifest_by_sample):
		_problem_success(problem_result_by_sample[sample_id])

	model_records = {
		(
			_required_text(row, "model_id"),
			_canonical_json(row.get("model_parameters")),
			_required_text(row, "prompt_config"),
			_required_text(row, "prompt_source_commit"),
		)
		for row in prediction_rows
	}
	if len(model_records) != 1:
		raise ValueError("All prediction rows must use one model and prompt configuration.")
	model_id, model_parameters_json, prompt_config, prompt_source_commit = next(
		iter(model_records),
	)
	if prompt_source_commit != _required_text(handoff_manifest, "prompt_source_commit"):
		raise ValueError("Prediction prompt_source_commit differs from the sealed handoff.")

	domain_names = sorted({_required_text(row, "domain") for row in manifest_rows})
	domains: dict[str, object] = {}
	for domain_name in domain_names:
		dataset_file = dataset_root / f"{domain_name}.json"
		if not dataset_file.is_file():
			raise ValueError(f"Missing validated append dataset for domain {domain_name!r}.")
		dataset_payload = _read_json(dataset_file)
		dataset = load_lifted_ltlf_goal_dataset(dataset_file)
		if dataset.domain != domain_name:
			raise ValueError(f"Dataset domain mismatch for {domain_name!r}.")
		raw_cases = dataset_payload.get("cases")
		if not isinstance(raw_cases, Mapping):
			raise ValueError(f"Dataset {domain_name!r} has no cases object.")
		expected_sample_ids = {
			sample_id
			for sample_id, row in manifest_by_sample.items()
			if _required_text(row, "domain") == domain_name
		}
		if set(raw_cases) != expected_sample_ids:
			raise ValueError(
				f"Validated dataset membership mismatch for domain {domain_name!r}.",
			)
		domain_file = domain_root / domain_name / "domain.pddl"
		if not domain_file.is_file():
			raise ValueError(f"Missing PDDL domain file {domain_file}.")
		cases: dict[str, object] = {}
		for sample_id in sorted(expected_sample_ids):
			translation_id = translation_by_sample[sample_id]
			manifest_row = manifest_by_sample[sample_id]
			worklist_row = worklist_by_translation[translation_id]
			prediction_row = prediction_by_translation[translation_id]
			prediction = prediction_row.get("prediction")
			if not isinstance(prediction, Mapping):
				raise ValueError(f"Prediction {translation_id!r} has no payload.")
			translation_result = translation_result_by_id[translation_id]
			problem_result = problem_result_by_sample[sample_id]
			dataset_case = raw_cases[sample_id]
			if not isinstance(dataset_case, Mapping):
				raise ValueError(f"Dataset case {sample_id!r} must be an object.")
			if dataset_case.get("ltlf_formula") != prediction.get("ltlf_formula"):
				raise ValueError(f"Dataset formula differs from prediction for {sample_id!r}.")
			problem_file = _required_text(manifest_row, "problem_file")
			if dataset_case.get("problem_file") != problem_file:
				raise ValueError(f"Dataset problem file differs for {sample_id!r}.")
			cases[sample_id] = _canonical_case(
				sample_id=sample_id,
				translation_id=translation_id,
				manifest_row=manifest_row,
				worklist_row=worklist_row,
				prediction=prediction,
				translation_result=translation_result,
				problem_result=problem_result,
				dataset_case=dataset_case,
			)
		domains[domain_name] = {
			"domain_file": f"src/domains/{domain_name}/domain.pddl",
			"appender_dataset_file": f"domains/{domain_name}.json",
			"appender_dataset_sha256": _sha256(dataset_file),
			"case_count": len(cases),
			"cases": cases,
		}

	profiles = sorted({_required_text(row, "profile") for row in manifest_rows})
	predictions_sha256 = _sha256(predictions_path)
	counts = {
		"domain_count": len(domains),
		"execution_attempted_count": sum(
			isinstance(row.get("execution_validation"), Mapping)
			and row["execution_validation"].get("status") != "not_attempted"
			for row in problem_results
		),
		"problem_case_count": len(manifest_rows),
		"translation_equivalent_count": len(translation_results),
		"unique_translation_input_count": len(worklist_rows),
		"witness_accepted_count": len(problem_results),
	}
	return {
		"schema_version": 1,
		"artifact_kind": "multi_domain_lifted_ltlf_teg_benchmark",
		"benchmark_id": benchmark_id,
		"temporal_logic": "LTLf",
		"formula_fragment": {
			"allowed_operators": ["F", "X", "U", "&", "!"],
			"profiles": profiles,
			"disjunction_supported": False,
		},
		"provenance": {
			"source_delivery_archive": archive_provenance,
			"sealed_input_archives": input_archive_provenance,
			"frozen_predictions": {
				"sha256": predictions_sha256,
				"row_count": len(prediction_rows),
				"model_id": model_id,
				"model_parameters": json.loads(model_parameters_json),
				"prompt_config": prompt_config,
				"prompt_source_commit": prompt_source_commit,
			},
			"input_artifacts": {
				"handoff_manifest_sha256": _sha256(handoff_manifest_path),
				"natural_language_manifest_sha256": _sha256(manifest_path),
				"translation_worklist_sha256": _sha256(worklist_path),
			},
			"independent_validation": {
				"implementation_commit": commit,
				"translation_results_sha256": _sha256(translation_results_path),
				"problem_results_sha256": _sha256(problem_results_path),
			},
		},
		"evaluation_protocol": {
			"translation_unit": "unique_model_translation_input",
			"problem_unit": "grounded_problem_binding",
			"translation_success_requires": [
				"prediction_contract_valid",
				"exact_gold_prediction_dfa_language_equivalence",
			],
			"problem_success_requires": [
				"legal_hidden_pddl_witness_replay",
				"sealed_state_fingerprints_match",
				"gold_dfa_acceptance",
				"predicted_dfa_acceptance",
			],
			"execution_success_requires": [
				"query_append_success",
				"jason_execution_success",
				"primitive_pddl_trace_replay",
				"independent_val_acceptance_against_neutral_goal",
				"gold_dfa_trace_acceptance",
				"predicted_dfa_trace_acceptance",
			],
			"execution_status": (
				"not_attempted" if counts["execution_attempted_count"] == 0 else "partial"
			),
		},
		"counts": counts,
		"domains": domains,
	}


def write_temporal_goal_benchmark(
	*,
	output_dir: str | Path,
	**build_arguments: Any,
) -> dict[str, object]:
	"""Write the canonical bundle, byte-preserved domain views, and release manifest."""

	output = Path(output_dir)
	domain_output = output / "domains"
	domain_output.mkdir(parents=True, exist_ok=True)
	bundle = build_temporal_goal_benchmark_bundle(**build_arguments)
	source_datasets = Path(build_arguments["validated_append_datasets_dir"])
	domain_entries: list[dict[str, object]] = []
	for domain_name, domain_payload in sorted(bundle["domains"].items()):
		source = source_datasets / f"{domain_name}.json"
		destination = domain_output / f"{domain_name}.json"
		shutil.copyfile(source, destination)
		domain_entries.append(
			{
				"domain": domain_name,
				"path": f"domains/{domain_name}.json",
				"sha256": _sha256(destination),
				"case_count": int(domain_payload["case_count"]),
			},
		)
	bundle_file = output / "benchmark.json"
	_write_json(bundle_file, bundle)
	manifest = {
		"schema_version": 1,
		"artifact_kind": "temporal_goal_benchmark_release_manifest",
		"benchmark_id": bundle["benchmark_id"],
		"benchmark_file": "benchmark.json",
		"benchmark_sha256": _sha256(bundle_file),
		"counts": bundle["counts"],
		"source_delivery_archive": bundle["provenance"]["source_delivery_archive"],
		"sealed_input_archives": bundle["provenance"]["sealed_input_archives"],
		"domain_datasets": domain_entries,
	}
	_write_json(output / "manifest.json", manifest)
	validate_temporal_goal_benchmark_bundle(
		bundle,
		benchmark_root=output,
		domains_root=build_arguments["domains_root"],
	)
	return manifest


def validate_temporal_goal_benchmark_bundle(
	payload: Mapping[str, Any],
	*,
	benchmark_root: str | Path,
	domains_root: str | Path,
) -> None:
	"""Validate a bundle and every referenced operational domain dataset."""

	if not isinstance(payload, Mapping) or frozenset(payload) != _BUNDLE_KEYS:
		raise ValueError("Temporal benchmark bundle must contain exactly the canonical keys.")
	if payload.get("schema_version") != 1:
		raise ValueError("Temporal benchmark schema_version must be 1.")
	if payload.get("artifact_kind") != "multi_domain_lifted_ltlf_teg_benchmark":
		raise ValueError("Temporal benchmark artifact_kind is invalid.")
	if payload.get("temporal_logic") != "LTLf":
		raise ValueError("Temporal benchmark temporal_logic must be LTLf.")
	if _contains_hidden_key(payload):
		raise ValueError("Canonical temporal benchmark must not contain hidden gold evidence.")
	root = Path(benchmark_root)
	domain_root = Path(domains_root)
	domains = payload.get("domains")
	counts = payload.get("counts")
	if not isinstance(domains, Mapping) or not isinstance(counts, Mapping):
		raise ValueError("Temporal benchmark domains and counts must be objects.")
	case_count = 0
	translation_ids: set[str] = set()
	for domain_name, domain_payload in sorted(domains.items()):
		if not isinstance(domain_payload, Mapping):
			raise ValueError(f"Domain entry {domain_name!r} must be an object.")
		domain_file = domain_root / str(domain_name) / "domain.pddl"
		if not domain_file.is_file():
			raise ValueError(f"Missing domain file {domain_file}.")
		dataset_path = root / _required_text(domain_payload, "appender_dataset_file")
		if _sha256(dataset_path) != _required_text(domain_payload, "appender_dataset_sha256"):
			raise ValueError(f"Domain dataset SHA-256 mismatch for {domain_name!r}.")
		dataset = load_lifted_ltlf_goal_dataset(dataset_path)
		if dataset.domain != domain_name:
			raise ValueError(f"Domain dataset label mismatch for {domain_name!r}.")
		cases = domain_payload.get("cases")
		if not isinstance(cases, Mapping) or len(cases) != len(dataset.cases):
			raise ValueError(f"Domain case count mismatch for {domain_name!r}.")
		dataset_by_id = {case.query_id: case for case in dataset.cases}
		for sample_id, case_payload in cases.items():
			if not isinstance(case_payload, Mapping) or sample_id not in dataset_by_id:
				raise ValueError(f"Invalid canonical case {sample_id!r}.")
			problem_path = Path(_required_text(case_payload, "problem_file"))
			if not problem_path.is_absolute():
				problem_path = domain_root.parents[1] / problem_path
			if not problem_path.is_file():
				raise ValueError(f"Missing problem file for {sample_id!r}: {problem_path}.")
			translation = case_payload.get("translation_validation")
			witness = case_payload.get("witness_validation")
			if not isinstance(translation, Mapping) or translation.get("equivalent") is not True:
				raise ValueError(f"Case {sample_id!r} lacks translation equivalence.")
			if not isinstance(witness, Mapping) or not all(
				witness.get(key) is True
				for key in (
					"replay_valid",
					"state_fingerprints_match",
					"gold_accepted",
					"prediction_accepted",
				)
			):
				raise ValueError(f"Case {sample_id!r} lacks a valid hidden witness.")
			atoms = case_payload.get("atoms")
			if not isinstance(atoms, Sequence) or isinstance(atoms, (str, bytes)):
				raise ValueError(f"Case {sample_id!r} has no atom table.")
			atom_symbols = {
				_required_text(atom, "symbol")
				for atom in atoms
				if isinstance(atom, Mapping)
			}
			if atom_symbols != set(_ATOM_RE.findall(_required_text(case_payload, "ltlf_formula"))):
				raise ValueError(f"Case {sample_id!r} formula and atom table differ.")
			parameters = case_payload.get("declared_parameters")
			bindings = case_payload.get("bindings")
			if not isinstance(parameters, Sequence) or not isinstance(bindings, Mapping):
				raise ValueError(f"Case {sample_id!r} lacks parameters or bindings.")
			parameter_names = {
				_required_text(parameter, "name")
				for parameter in parameters
				if isinstance(parameter, Mapping)
			}
			if parameter_names != set(bindings):
				raise ValueError(f"Case {sample_id!r} bindings do not cover its parameters.")
			operational_case = dataset_by_id[sample_id]
			if (
				operational_case.ltlf_formula != case_payload.get("ltlf_formula")
				or dict(operational_case.bindings) != dict(bindings)
			):
				raise ValueError(f"Canonical and operational case differ for {sample_id!r}.")
			translation_ids.add(_required_text(case_payload, "translation_id"))
			case_count += 1
	if int(counts.get("domain_count") or -1) != len(domains):
		raise ValueError("Temporal benchmark domain_count is inconsistent.")
	if int(counts.get("problem_case_count") or -1) != case_count:
		raise ValueError("Temporal benchmark problem_case_count is inconsistent.")
	if int(counts.get("unique_translation_input_count") or -1) != len(translation_ids):
		raise ValueError("Temporal benchmark translation input count is inconsistent.")
	if int(counts.get("translation_equivalent_count") or -1) != len(translation_ids):
		raise ValueError("Temporal benchmark equivalent translation count is inconsistent.")
	if int(counts.get("witness_accepted_count") or -1) != case_count:
		raise ValueError("Temporal benchmark witness count is inconsistent.")


def _canonical_case(
	*,
	sample_id: str,
	translation_id: str,
	manifest_row: Mapping[str, Any],
	worklist_row: Mapping[str, Any],
	prediction: Mapping[str, Any],
	translation_result: Mapping[str, Any],
	problem_result: Mapping[str, Any],
	dataset_case: Mapping[str, Any],
) -> dict[str, object]:
	equivalence = translation_result.get("dfa_equivalence")
	witness = problem_result.get("witness_validation")
	if not isinstance(equivalence, Mapping) or not isinstance(witness, Mapping):
		raise ValueError(f"Case {sample_id!r} lacks validation certificates.")
	execution = problem_result.get("execution_validation")
	return {
		"translation_id": translation_id,
		"translation_input_signature": _required_text(
			worklist_row,
			"translation_input_signature",
		),
		"representative_sample_id": _required_text(
			worklist_row,
			"representative_sample_id",
		),
		"semantic_signature": _required_text(manifest_row, "semantic_signature"),
		"profile": _required_text(manifest_row, "profile"),
		"construction_tier": _required_text(manifest_row, "construction_tier"),
		"problem_file": _required_text(manifest_row, "problem_file"),
		"source_text": _required_text(manifest_row, "source_text"),
		"declared_parameters": list(prediction.get("declared_parameters") or ()),
		"constraints": list(prediction.get("constraints") or ()),
		"ltlf_formula": _required_text(prediction, "ltlf_formula"),
		"atoms": list(prediction.get("atoms") or ()),
		"bindings": dict(dataset_case.get("bindings") or {}),
		"translation_validation": {
			"status": _required_text(translation_result, "status"),
			"equivalent": equivalence.get("equivalent") is True,
			"gold_state_count": int(equivalence.get("gold_state_count") or 0),
			"prediction_state_count": int(equivalence.get("prediction_state_count") or 0),
			"explored_product_state_count": int(
				equivalence.get("explored_product_state_count") or 0,
			),
		},
		"witness_validation": dict(witness),
		"execution_validation": (
			dict(execution) if isinstance(execution, Mapping) else {"status": "not_attempted"}
		),
	}


def _validated_membership(
	worklist_rows: Sequence[Mapping[str, Any]],
	*,
	expected_sample_ids: set[str],
) -> dict[str, str]:
	membership: dict[str, str] = {}
	for row in worklist_rows:
		translation_id = _required_text(row, "translation_id")
		members = row.get("member_sample_ids")
		if not isinstance(members, Sequence) or isinstance(members, (str, bytes)):
			raise ValueError(f"Worklist {translation_id!r} has invalid membership.")
		for raw_sample_id in members:
			sample_id = str(raw_sample_id or "").strip()
			if sample_id in membership:
				raise ValueError(f"Duplicate worklist membership for {sample_id!r}.")
			membership[sample_id] = translation_id
	if set(membership) != expected_sample_ids:
		raise ValueError("Worklist membership must cover every manifest sample exactly once.")
	return membership


def _prediction_success(row: Mapping[str, Any]) -> None:
	if row.get("outcome") != "accepted" or not isinstance(row.get("prediction"), Mapping):
		raise ValueError(f"Prediction {_required_text(row, 'translation_id')!r} was not accepted.")
	raw_response = _required_text(row, "raw_response")
	try:
		raw_payload = json.loads(raw_response)
	except json.JSONDecodeError as error:
		raise ValueError("Accepted prediction raw_response is not JSON.") from error
	if raw_payload != row.get("prediction"):
		raise ValueError("Accepted prediction differs from raw_response.")


def _translation_success(row: Mapping[str, Any]) -> None:
	equivalence = row.get("dfa_equivalence")
	if (
		row.get("success") is not True
		or row.get("status") != "semantically_equivalent"
		or not isinstance(equivalence, Mapping)
		or equivalence.get("equivalent") is not True
	):
		raise ValueError(
			f"Translation {_required_text(row, 'translation_id')!r} is not equivalent.",
		)


def _problem_success(row: Mapping[str, Any]) -> None:
	witness = row.get("witness_validation")
	if (
		row.get("success") is not True
		or row.get("status") != "witness_accepted"
		or not isinstance(witness, Mapping)
		or not all(
			witness.get(key) is True
			for key in (
				"replay_valid",
				"state_fingerprints_match",
				"gold_accepted",
				"prediction_accepted",
			)
		)
	):
		raise ValueError(f"Problem {_required_text(row, 'sample_id')!r} lacks a valid witness.")


def _validated_archive_provenance(payload: Mapping[str, str]) -> dict[str, str]:
	filename = str(payload.get("filename") or "").strip()
	sha256 = str(payload.get("sha256") or "").strip().lower()
	if not filename or not _SHA256_RE.fullmatch(sha256):
		raise ValueError("Source delivery archive requires filename and SHA-256.")
	return {"filename": filename, "sha256": sha256}


def _unique_by(
	rows: Sequence[Mapping[str, Any]],
	key: str,
	*,
	label: str,
) -> dict[str, Mapping[str, Any]]:
	result: dict[str, Mapping[str, Any]] = {}
	for row in rows:
		value = _required_text(row, key)
		if value in result:
			raise ValueError(f"Duplicate {label} {key} {value!r}.")
		result[value] = row
	return result


def _contains_hidden_key(value: object) -> bool:
	if isinstance(value, Mapping):
		if _HIDDEN_KEYS.intersection(str(key) for key in value):
			return True
		return any(_contains_hidden_key(item) for item in value.values())
	if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
		return any(_contains_hidden_key(item) for item in value)
	return False


def _read_json(path: Path) -> dict[str, Any]:
	payload = json.loads(path.read_text(encoding="utf-8"))
	if not isinstance(payload, dict):
		raise ValueError(f"Expected a JSON object in {path}.")
	return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
	rows: list[dict[str, Any]] = []
	for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
		if not line.strip():
			continue
		payload = json.loads(line)
		if not isinstance(payload, dict):
			raise ValueError(f"Expected a JSON object at {path}:{line_number}.")
		rows.append(payload)
	return rows


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def _required_text(payload: Mapping[str, Any], key: str) -> str:
	value = str(payload.get(key) or "").strip()
	if not value:
		raise ValueError(f"Missing required field {key!r}.")
	return value


def _canonical_json(value: object) -> str:
	return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256(path: str | Path) -> str:
	return hashlib.sha256(Path(path).read_bytes()).hexdigest()
