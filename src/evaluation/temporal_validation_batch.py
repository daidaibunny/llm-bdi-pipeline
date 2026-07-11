"""Batch orchestration for paper-grade lifted LTLf goal validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping
from typing import Sequence

from temporal_specification.prediction_validation import PredictionValidationError
from temporal_specification.prediction_validation import ValidatedLTLfPrediction
from temporal_specification.prediction_validation import validate_prediction_payload

from .temporal_goal_validation import compare_gold_and_prediction
from .temporal_goal_validation import expand_translation_predictions
from .temporal_goal_validation import validate_execution_trace
from .temporal_goal_validation import validate_prediction_on_witness


_PREDICTION_RECORD_KEYS = frozenset(
	{
		"schema_version",
		"translation_id",
		"outcome",
		"attempt_count",
		"model_id",
		"model_parameters",
		"prompt_config",
		"prompt_source_commit",
		"raw_response",
		"prediction",
		"terminal_error",
	},
)


@dataclass(frozen=True)
class TranslationPredictionRecord:
	"""One auditable model outcome for a deduplicated translation input."""

	translation_id: str
	outcome: str
	attempt_count: int
	model_id: str
	model_parameters: Mapping[str, Any]
	prompt_config: str
	prompt_source_commit: str
	raw_response: str
	prediction: Mapping[str, Any] | None
	terminal_error: Mapping[str, Any] | None


def parse_translation_prediction_record(
	payload: Mapping[str, Any],
) -> TranslationPredictionRecord:
	"""Parse the canonical model-run record without accepting ambiguous variants."""

	if not isinstance(payload, Mapping) or frozenset(payload) != _PREDICTION_RECORD_KEYS:
		raise ValueError(
			"Prediction record must contain exactly the canonical eleven fields; "
			f"expected={sorted(_PREDICTION_RECORD_KEYS)}.",
		)
	if payload.get("schema_version") != 1:
		raise ValueError("Prediction record schema_version must be integer 1.")
	translation_id = _nonempty_text(payload, "translation_id")
	outcome = _nonempty_text(payload, "outcome")
	if outcome not in {"accepted", "terminal_failure"}:
		raise ValueError("Prediction record outcome must be accepted or terminal_failure.")
	attempt_count = payload.get("attempt_count")
	if isinstance(attempt_count, bool) or not isinstance(attempt_count, int) or attempt_count < 1:
		raise ValueError("Prediction record attempt_count must be a positive integer.")
	model_parameters = payload.get("model_parameters")
	if not isinstance(model_parameters, Mapping):
		raise ValueError("Prediction record model_parameters must be a JSON object.")
	prediction = payload.get("prediction")
	terminal_error = payload.get("terminal_error")
	if outcome == "accepted":
		if not isinstance(prediction, Mapping) or terminal_error is not None:
			raise ValueError("Accepted record requires prediction object and null terminal_error.")
		raw_response = str(payload.get("raw_response") or "")
		try:
			raw_payload = json.loads(raw_response)
		except json.JSONDecodeError as error:
			raise ValueError("Accepted record raw_response must be the exact JSON response.") from error
		if raw_payload != prediction:
			raise ValueError("Accepted record prediction must equal parsed raw_response exactly.")
	else:
		if prediction is not None or not isinstance(terminal_error, Mapping):
			raise ValueError("Terminal failure requires null prediction and terminal_error object.")
	return TranslationPredictionRecord(
		translation_id=translation_id,
		outcome=outcome,
		attempt_count=attempt_count,
		model_id=_nonempty_text(payload, "model_id"),
		model_parameters=dict(model_parameters),
		prompt_config=_nonempty_text(payload, "prompt_config"),
		prompt_source_commit=_nonempty_text(payload, "prompt_source_commit"),
		raw_response=str(payload.get("raw_response") or ""),
		prediction=dict(prediction) if isinstance(prediction, Mapping) else None,
		terminal_error=dict(terminal_error) if isinstance(terminal_error, Mapping) else None,
	)


def run_temporal_goal_validation_batch(
	*,
	handoff_root: str | Path,
	benchmark_root: str | Path,
	predictions_file: str | Path,
	output_dir: str | Path,
	project_root: str | Path,
	domains_root: str | Path,
	execution_traces_root: str | Path | None = None,
	plan_verifier_command: Sequence[str] | str | None = None,
	plan_verifier_timeout_seconds: int = 1800,
	progress: Callable[[str], None] | None = None,
	expected_prompt_config: str = "full",
) -> dict[str, object]:
	"""Validate translation semantics, hidden witnesses, and optional execution traces."""

	handoff = Path(handoff_root).resolve()
	benchmark = Path(benchmark_root).resolve()
	project = Path(project_root).resolve()
	domains = Path(domains_root).resolve()
	output = Path(output_dir).resolve()
	output.mkdir(parents=True, exist_ok=True)
	worklist_rows = _read_jsonl(handoff / "translation_worklist.jsonl")
	manifest_rows = _read_jsonl(handoff / "natural_language_manifest.jsonl")
	raw_prediction_rows = _read_jsonl(Path(predictions_file))
	prediction_records = tuple(
		parse_translation_prediction_record(row) for row in raw_prediction_rows
	)
	handoff_manifest = _read_json(handoff / "handoff_manifest.json")
	_validate_run_provenance(
		prediction_records,
		expected_prompt_config=expected_prompt_config,
		expected_prompt_source_commit=_nonempty_text(
			handoff_manifest,
			"prompt_source_commit",
		),
	)
	record_payloads = [
		{"translation_id": record.translation_id, "prediction": record.prediction}
		for record in prediction_records
	]
	expanded = expand_translation_predictions(
		worklist_rows=worklist_rows,
		prediction_rows=record_payloads,
		expected_sample_ids={_nonempty_text(row, "sample_id") for row in manifest_rows},
	)
	audit_by_sample = _load_audit_rows(benchmark)
	manifest_by_sample = {
		_nonempty_text(row, "sample_id"): row for row in manifest_rows
	}
	record_by_translation_id = {
		record.translation_id: record for record in prediction_records
	}
	validated_by_translation_id: dict[str, ValidatedLTLfPrediction] = {}
	translation_results: list[dict[str, object]] = []

	for worklist_row in worklist_rows:
		translation_id = _nonempty_text(worklist_row, "translation_id")
		record = record_by_translation_id[translation_id]
		result: dict[str, object] = {
			"translation_id": translation_id,
			"sample_id": _nonempty_text(worklist_row, "sample_id"),
			"outcome": record.outcome,
			"attempt_count": record.attempt_count,
			"model_id": record.model_id,
			"prompt_config": record.prompt_config,
		}
		if record.outcome == "terminal_failure":
			result.update(
				{
					"success": False,
					"status": "terminal_model_failure",
					"error": dict(record.terminal_error or {}),
				},
			)
			translation_results.append(result)
			_emit_progress(progress, "translation", translation_id, result["status"])
			continue
		try:
			catalog = _read_json(handoff / _nonempty_text(worklist_row, "catalog_file"))
			validated = validate_prediction_payload(
				record.prediction or {},
				expected_sample=worklist_row,
				catalog=catalog,
			)
			audit = audit_by_sample[_nonempty_text(worklist_row, "sample_id")]
			equivalence = compare_gold_and_prediction(
				audit_row=audit,
				prediction=validated,
			)
			result["dfa_equivalence"] = equivalence.to_dict()
			if not equivalence.equivalent:
				result.update({"success": False, "status": "semantic_mismatch"})
			else:
				result.update({"success": True, "status": "semantically_equivalent"})
				validated_by_translation_id[translation_id] = validated
		except PredictionValidationError as error:
			result.update(
				{
					"success": False,
					"status": "prediction_contract_error",
					"error": {"code": error.code.value, "message": str(error)},
				},
			)
		except Exception as error:  # noqa: BLE001 - reported as non-model infrastructure failure.
			result.update(
				{
					"success": False,
					"status": "validation_infrastructure_error",
					"error": {"type": type(error).__name__, "message": str(error)},
				},
			)
		translation_results.append(result)
		_emit_progress(progress, "translation", translation_id, result["status"])

	translation_id_by_sample = {
		sample_id: _nonempty_text(record, "translation_id")
		for sample_id, record in expanded.items()
	}
	problem_results: list[dict[str, object]] = []
	validated_cases_by_domain: dict[str, dict[str, object]] = {}
	translation_result_by_id = {
		str(item["translation_id"]): item for item in translation_results
	}
	traces_root = Path(execution_traces_root).resolve() if execution_traces_root else None

	for sample_id in sorted(manifest_by_sample):
		manifest_row = manifest_by_sample[sample_id]
		translation_id = translation_id_by_sample[sample_id]
		translation_result = translation_result_by_id[translation_id]
		problem_result: dict[str, object] = {
			"sample_id": sample_id,
			"domain": _nonempty_text(manifest_row, "domain"),
			"translation_id": translation_id,
		}
		validated = validated_by_translation_id.get(translation_id)
		if validated is None:
			problem_result.update(
				{
					"success": False,
					"status": "translation_failed",
					"translation_status": translation_result.get("status"),
				},
			)
			problem_results.append(problem_result)
			_emit_progress(progress, "problem", sample_id, problem_result["status"])
			continue
		try:
			audit = audit_by_sample[sample_id]
			domain_name = _nonempty_text(manifest_row, "domain")
			domain_file = domains / domain_name / "domain.pddl"
			problem_file = project / _nonempty_text(manifest_row, "problem_file")
			witness = validate_prediction_on_witness(
				audit_row=audit,
				prediction=validated,
				domain_file=domain_file,
				problem_file=problem_file,
			)
			problem_result["witness_validation"] = witness.to_dict()
			witness_success = witness.gold_accepted and witness.prediction_accepted
			problem_result.update(
				{
					"success": witness_success,
					"status": "witness_accepted" if witness_success else "witness_rejected",
				},
			)
			if witness_success:
				validated_cases_by_domain.setdefault(domain_name, {})[sample_id] = (
					_append_case_payload(
						manifest_row=manifest_row,
						audit_row=audit,
						prediction=validated,
					)
				)
			if traces_root is not None:
				plan_file = traces_root / f"{sample_id}.plan"
				if plan_file.is_file():
					execution = validate_execution_trace(
						audit_row=audit,
						prediction=validated,
						domain_file=domain_file,
						problem_file=problem_file,
						plan_file=plan_file,
						output_dir=output / "execution" / domain_name / sample_id,
						plan_verifier_command=plan_verifier_command,
						plan_verifier_timeout_seconds=plan_verifier_timeout_seconds,
					)
					problem_result["execution_validation"] = execution.to_dict()
					problem_result["success"] = bool(problem_result["success"]) and execution.success
					if not execution.success:
						problem_result["status"] = "execution_rejected"
				else:
					problem_result["execution_validation"] = {"status": "not_attempted"}
		except Exception as error:  # noqa: BLE001 - retained for audit, never hidden.
			problem_result.update(
				{
					"success": False,
					"status": "problem_validation_error",
					"error": {"type": type(error).__name__, "message": str(error)},
				},
			)
		problem_results.append(problem_result)
		_emit_progress(progress, "problem", sample_id, problem_result["status"])

	_write_jsonl(output / "translation_validation_results.jsonl", translation_results)
	_write_jsonl(output / "problem_validation_results.jsonl", problem_results)
	dataset_root = output / "validated_append_datasets"
	for domain_name, cases in sorted(validated_cases_by_domain.items()):
		_write_json(
			dataset_root / f"{domain_name}.json",
			{
				"schema_version": 1,
				"goal_specification_kind": "temporal_extended_goal",
				"temporal_logic": "LTLf",
				"domain": domain_name,
				"cases": cases,
			},
		)
	summary = {
		"schema_version": 1,
		"artifact_kind": "temporal_goal_validation_report",
		"translation_total": len(translation_results),
		"translation_success_count": sum(bool(item.get("success")) for item in translation_results),
		"problem_total": len(problem_results),
		"problem_success_count": sum(bool(item.get("success")) for item in problem_results),
		"execution_attempted_count": sum(
			isinstance(item.get("execution_validation"), Mapping)
			and item["execution_validation"].get("status") != "not_attempted"
			for item in problem_results
		),
		"execution_success_count": sum(
			isinstance(item.get("execution_validation"), Mapping)
			and item["execution_validation"].get("success") is True
			for item in problem_results
		),
		"validated_append_dataset_root": str(dataset_root),
	}
	_write_json(output / "summary.json", summary)
	return summary


def _append_case_payload(
	*,
	manifest_row: Mapping[str, Any],
	audit_row: Mapping[str, Any],
	prediction: ValidatedLTLfPrediction,
) -> dict[str, object]:
	atoms: list[dict[str, object]] = []
	for atom in prediction.atoms:
		if atom.kind == "predicate":
			atoms.append(
				{"symbol": atom.symbol, "predicate": atom.name, "args": list(atom.args)},
			)
		else:
			atoms.append(
				{
					"symbol": atom.symbol,
					"predicate": atom.name,
					"args": [*atom.args, str(atom.value)],
				},
			)
	sample_id = _nonempty_text(manifest_row, "sample_id")
	return {
		"goal_name": _goal_name(sample_id),
		"problem_file": _nonempty_text(manifest_row, "problem_file"),
		"source_text": _nonempty_text(manifest_row, "source_text"),
		"ltlf_formula": prediction.ltlf_formula,
		"atoms": atoms,
		"bindings": dict(audit_row.get("assignment") or {}),
		"atom_vocabulary": "pddl_fluents",
		"status": "supported",
	}


def _load_audit_rows(benchmark_root: Path) -> dict[str, Mapping[str, Any]]:
	result: dict[str, Mapping[str, Any]] = {}
	for path in sorted((benchmark_root / "domains").glob("*/construction_audit.jsonl")):
		for row in _read_jsonl(path):
			sample_id = _nonempty_text(row, "sample_id")
			if sample_id in result:
				raise ValueError(f"Duplicate construction audit sample_id {sample_id!r}.")
			result[sample_id] = row
	return result


def _goal_name(sample_id: str) -> str:
	normalized = re.sub(r"[^A-Za-z0-9_]", "_", sample_id)
	if not normalized or not normalized[0].isalpha():
		normalized = f"query_{normalized}"
	return f"g_{normalized}"


def _validate_run_provenance(
	records: Sequence[TranslationPredictionRecord],
	*,
	expected_prompt_config: str,
	expected_prompt_source_commit: str,
) -> None:
	if not records:
		raise ValueError("Prediction artifact must contain at least one record.")
	model_ids = {record.model_id for record in records}
	model_parameters = {
		json.dumps(record.model_parameters, sort_keys=True, separators=(",", ":"))
		for record in records
	}
	prompt_configs = {record.prompt_config for record in records}
	prompt_commits = {record.prompt_source_commit for record in records}
	if len(model_ids) != 1 or len(model_parameters) != 1:
		raise ValueError("Primary prediction run must use one model and decoding configuration.")
	if prompt_configs != {expected_prompt_config}:
		raise ValueError(
			f"Prediction prompt_config must be {expected_prompt_config!r}; "
			f"received {sorted(prompt_configs)}.",
		)
	if prompt_commits != {expected_prompt_source_commit}:
		raise ValueError(
			"Prediction prompt_source_commit does not match the sealed handoff; "
			f"expected={expected_prompt_source_commit!r}, received={sorted(prompt_commits)}.",
		)


def _read_json(path: Path) -> dict[str, Any]:
	payload = json.loads(path.read_text(encoding="utf-8"))
	if not isinstance(payload, dict):
		raise ValueError(f"Expected JSON object in {path}.")
	return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
	rows: list[dict[str, Any]] = []
	for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
		if not line.strip():
			continue
		payload = json.loads(line)
		if not isinstance(payload, dict):
			raise ValueError(f"{path}:{line_number} must contain a JSON object.")
		rows.append(payload)
	return rows


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		"".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
		encoding="utf-8",
	)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
		encoding="utf-8",
	)


def _nonempty_text(payload: Mapping[str, Any], field: str) -> str:
	value = str(payload.get(field) or "").strip()
	if not value:
		raise ValueError(f"{field} must be a non-empty string.")
	return value


def _emit_progress(
	callback: Callable[[str], None] | None,
	kind: str,
	identifier: str,
	status: object,
) -> None:
	if callback is not None:
		callback(f"[{kind}] id={identifier} status={status}")
