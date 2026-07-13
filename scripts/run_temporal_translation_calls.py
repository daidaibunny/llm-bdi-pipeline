#!/usr/bin/env python3
"""Run the 475 primary NL-to-lifted-LTLf translation calls over the sealed worklist.

Colleague-side runner for docs/input_design.md "Colleague-Only Procedure":
one canonical eleven-field record per worklist translation_id, resumable by
skipping already-recorded ids, with the semantic retry channel limited to
build_retry_feedback/build_retry_user_message. Model messages contain only the
rendered system prompt and the public user prompt; no profile, signature,
translation_id, membership, witness, assignment, or hidden-audit data.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from language_model.openai_compatible import (  # noqa: E402
	create_openai_compatible_client,
	create_openai_compatible_json_completion,
)
from temporal_specification.errors import (  # noqa: E402
	NON_RETRYABLE_ERROR_CODES,
	TranslationErrorCode,
	build_retry_feedback,
)
from temporal_specification.prediction_validation import (  # noqa: E402
	PredictionValidationError,
	validate_prediction_payload,
)
from temporal_specification.prompts import (  # noqa: E402
	FULL_PROMPT_CONFIG,
	build_lifted_ltlf_system_prompt,
	build_lifted_ltlf_user_prompt,
	build_retry_user_message,
)
from utils.config import get_config  # noqa: E402

DEFAULT_HANDOFF_ROOT = (
	PROJECT_ROOT / "artifacts" / "temporal_nl_handoffs" / "temporal-nl-v1-20260711-final"
)

# Deduplication/bookkeeping fields that must never reach a model message.
_LEAK_FIELDS = (
	"translation_id",
	"translation_input_signature",
	"semantic_signature",
	"prompt_context_sha256",
	"member_sample_ids",
	"benchmark_domains",
	"profile",
	"construction_tier",
)


@dataclass(frozen=True)
class RunSettings:
	"""One pre-registered model/decoding/prompt configuration for the whole run."""

	model_id: str
	model_parameters: dict[str, Any]
	prompt_config: str
	prompt_source_commit: str
	max_semantic_retries: int
	timeout_seconds: float
	max_tokens: int


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
	rows: list[dict[str, Any]] = []
	for line in path.read_text(encoding="utf-8").splitlines():
		if line.strip():
			rows.append(json.loads(line))
	return rows


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
	tmp = path.with_suffix(path.suffix + ".tmp")
	tmp.write_text(
		json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
		encoding="utf-8",
	)
	tmp.replace(path)


def _assert_leak_free(messages: Sequence[Mapping[str, str]], row: Mapping[str, Any]) -> None:
	"""Fail closed if bookkeeping values leak into any model message."""

	rendered = "\n".join(str(message.get("content", "")) for message in messages)
	# The representative sample_id and its domain are public prompt content;
	# every other bookkeeping value must stay out of the model context.
	public = {str(row.get("sample_id") or ""), str(row.get("domain") or "")}
	for field in _LEAK_FIELDS:
		value = row.get(field)
		items = value if isinstance(value, (list, tuple)) else [value]
		for item in items:
			if isinstance(item, str) and item and item not in public and item in rendered:
				raise RuntimeError(
					f"leak guard: worklist field {field!r} appears in model message",
				)


def _previous_ltlf(raw_text: str) -> str:
	try:
		payload = json.loads(raw_text)
	except (json.JSONDecodeError, TypeError):
		return ""
	if isinstance(payload, Mapping):
		return str(payload.get("ltlf_formula") or "")
	return ""


def _classify_transport_error(error: Exception) -> TranslationErrorCode:
	name = type(error).__name__
	if "Timeout" in name:
		return TranslationErrorCode.E_LLM_TIMEOUT
	return TranslationErrorCode.E_NETWORK


def translate_one(
	row: Mapping[str, Any],
	*,
	catalog: Mapping[str, Any],
	client: Any,
	settings: RunSettings,
	attempt_log: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
	"""Produce the canonical eleven-field record for one worklist row."""

	system_prompt = build_lifted_ltlf_system_prompt(catalog, FULL_PROMPT_CONFIG)
	user_prompt = build_lifted_ltlf_user_prompt(row)
	messages: list[dict[str, str]] = [
		{"role": "system", "content": system_prompt},
		{"role": "user", "content": user_prompt},
	]
	_assert_leak_free(messages, row)

	record: dict[str, Any] = {
		"schema_version": 1,
		"translation_id": str(row["translation_id"]),
		"outcome": "terminal_failure",
		"attempt_count": 0,
		"model_id": settings.model_id,
		"model_parameters": settings.model_parameters,
		"prompt_config": settings.prompt_config,
		"prompt_source_commit": settings.prompt_source_commit,
		"raw_response": "",
		"prediction": None,
		"terminal_error": None,
	}

	max_attempts = 1 + settings.max_semantic_retries
	attempt = 0
	raw_text = ""
	while attempt < max_attempts:
		attempt += 1
		record["attempt_count"] = attempt
		try:
			response = create_openai_compatible_json_completion(
				client,
				model=settings.model_id,
				messages=messages,
				timeout=settings.timeout_seconds,
				max_tokens=settings.max_tokens,
				stream=True,
				temperature=0.0,
			)
			raw_text = str(response.choices[0].message.content or "")
		except Exception as error:  # noqa: BLE001 - transport failures become outcomes
			code = _classify_transport_error(error)
			detail = f"{type(error).__name__}: {error}"
			if attempt_log is not None:
				attempt_log.append(
					{"attempt": attempt, "error_type": code.value, "error_detail": detail},
				)
			record["raw_response"] = raw_text
			record["terminal_error"] = {
				"error_type": code.value,
				"error_detail": detail,
				"attempt": attempt,
			}
			return record

		record["raw_response"] = raw_text
		try:
			payload = json.loads(raw_text)
			if not isinstance(payload, Mapping):
				raise PredictionValidationError(
					TranslationErrorCode.E_JSON_FORMAT,
					"Model response must be one JSON object.",
				)
			validate_prediction_payload(payload, expected_sample=row, catalog=catalog)
		except json.JSONDecodeError as error:
			failure_code = TranslationErrorCode.E_JSON_FORMAT
			failure_detail = f"Response is not valid JSON: {error.msg} (pos {error.pos})."
		except PredictionValidationError as error:
			failure_code = error.code
			failure_detail = str(error)
		else:
			record["outcome"] = "accepted"
			# The canonical contract: prediction must equal parsed raw_response.
			record["prediction"] = json.loads(raw_text)
			record["terminal_error"] = None
			if attempt_log is not None:
				attempt_log.append({"attempt": attempt, "error_type": None})
			return record

		if attempt_log is not None:
			attempt_log.append(
				{
					"attempt": attempt,
					"error_type": failure_code.value,
					"error_detail": failure_detail,
				},
			)
		if failure_code in NON_RETRYABLE_ERROR_CODES or attempt >= max_attempts:
			record["terminal_error"] = {
				"error_type": failure_code.value,
				"error_detail": failure_detail,
				"attempt": attempt,
			}
			return record

		feedback = build_retry_feedback(
			previous_ltlf=_previous_ltlf(raw_text),
			error_code=failure_code,
			error_detail=failure_detail,
			attempt=attempt + 1,
		)
		messages.append({"role": "assistant", "content": raw_text})
		messages.append({"role": "user", "content": build_retry_user_message(feedback)})
		_assert_leak_free(messages, row)

	raise AssertionError("unreachable: loop returns a record")


def run_translation_calls(
	*,
	handoff_root: Path,
	run_dir: Path,
	only_ids: Optional[Sequence[str]] = None,
	limit: Optional[int] = None,
	workers: int = 4,
	client: Any = None,
	settings: Optional[RunSettings] = None,
) -> dict[str, Any]:
	worklist = _read_jsonl(handoff_root / "translation_worklist.jsonl")
	handoff_manifest = json.loads(
		(handoff_root / "handoff_manifest.json").read_text(encoding="utf-8"),
	)
	sealed_commit = str(handoff_manifest["prompt_source_commit"])

	if settings is None:
		config = get_config()
		settings = RunSettings(
			model_id=config.ltlf_generation_model,
			model_parameters={
				"temperature": 0,
				"max_tokens": config.ltlf_generation_max_tokens,
				"timeout_seconds": config.ltlf_generation_timeout,
				"response_format": "json_object",
				"stream": True,
			},
			prompt_config=FULL_PROMPT_CONFIG.name,
			prompt_source_commit=sealed_commit,
			max_semantic_retries=config.input_pipeline_max_semantic_retries,
			timeout_seconds=float(config.ltlf_generation_timeout),
			max_tokens=config.ltlf_generation_max_tokens,
		)
	if settings.prompt_source_commit != sealed_commit:
		raise RuntimeError(
			"prompt_source_commit mismatch: settings="
			f"{settings.prompt_source_commit!r} sealed={sealed_commit!r}",
		)

	if client is None:
		config = get_config()
		api_key = config.ltlf_generation_api_key
		if not api_key:
			raise RuntimeError("LTLF_GENERATION_API_KEY is not configured")
		client = create_openai_compatible_client(
			api_key=api_key,
			base_url=config.ltlf_generation_base_url,
			timeout=settings.timeout_seconds,
			max_retries=3,
		)

	records_dir = run_dir / "records"
	attempts_dir = run_dir / "attempt_log"
	records_dir.mkdir(parents=True, exist_ok=True)
	attempts_dir.mkdir(parents=True, exist_ok=True)

	run_config_path = run_dir / "run_config.json"
	run_config = {
		"handoff_root": str(handoff_root),
		"model_id": settings.model_id,
		"model_parameters": settings.model_parameters,
		"prompt_config": settings.prompt_config,
		"prompt_source_commit": settings.prompt_source_commit,
		"max_semantic_retries": settings.max_semantic_retries,
		"worklist_row_count": len(worklist),
		"started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
	}
	if run_config_path.exists():
		previous = json.loads(run_config_path.read_text(encoding="utf-8"))
		frozen_keys = (
			"model_id",
			"model_parameters",
			"prompt_config",
			"prompt_source_commit",
			"max_semantic_retries",
		)
		for key in frozen_keys:
			if previous.get(key) != run_config[key]:
				raise RuntimeError(
					f"run_config mismatch on resume for {key!r}: "
					f"existing={previous.get(key)!r} current={run_config[key]!r}",
				)
		run_config["started_at"] = previous.get("started_at", run_config["started_at"])
	_write_json_atomic(run_config_path, run_config)

	selected = list(worklist)
	if only_ids:
		wanted = set(only_ids)
		selected = [row for row in selected if row["translation_id"] in wanted]
		missing = wanted - {row["translation_id"] for row in selected}
		if missing:
			raise RuntimeError(f"--only-ids not found in worklist: {sorted(missing)}")
	pending = [
		row
		for row in selected
		if not (records_dir / f"{row['translation_id']}.json").exists()
	]
	skipped = len(selected) - len(pending)
	if limit is not None:
		pending = pending[: max(0, limit)]

	catalog_cache: dict[str, Mapping[str, Any]] = {}
	catalog_lock = threading.Lock()

	def load_catalog(catalog_file: str) -> Mapping[str, Any]:
		with catalog_lock:
			if catalog_file not in catalog_cache:
				catalog_cache[catalog_file] = json.loads(
					(handoff_root / catalog_file).read_text(encoding="utf-8"),
				)
			return catalog_cache[catalog_file]

	progress_lock = threading.Lock()
	done_counter = {"done": 0, "accepted": 0, "terminal": 0}

	def process(row: Mapping[str, Any]) -> None:
		translation_id = str(row["translation_id"])
		attempt_log: list[dict[str, Any]] = []
		record = translate_one(
			row,
			catalog=load_catalog(str(row["catalog_file"])),
			client=client,
			settings=settings,
			attempt_log=attempt_log,
		)
		_write_json_atomic(records_dir / f"{translation_id}.json", record)
		(attempts_dir / f"{translation_id}.jsonl").write_text(
			"".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in attempt_log),
			encoding="utf-8",
		)
		with progress_lock:
			done_counter["done"] += 1
			done_counter["accepted" if record["outcome"] == "accepted" else "terminal"] += 1
			print(
				f"[{done_counter['done']}/{len(pending)}] {translation_id} "
				f"outcome={record['outcome']} attempts={record['attempt_count']}",
				flush=True,
			)

	if pending:
		with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
			futures = [pool.submit(process, row) for row in pending]
			for future in concurrent.futures.as_completed(futures):
				future.result()

	completed = sum(
		1 for row in worklist if (records_dir / f"{row['translation_id']}.json").exists()
	)
	run_config["completed_record_count"] = completed
	run_config["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
	_write_json_atomic(run_config_path, run_config)
	return {
		"run_dir": str(run_dir),
		"selected": len(selected),
		"skipped_existing": skipped,
		"processed": done_counter["done"],
		"accepted": done_counter["accepted"],
		"terminal_failure": done_counter["terminal"],
		"completed_record_count": completed,
		"worklist_row_count": len(worklist),
	}


def assemble_predictions(*, handoff_root: Path, run_dir: Path) -> Path:
	"""Assemble the strict 475-line translation_predictions.jsonl in worklist order."""

	worklist = _read_jsonl(handoff_root / "translation_worklist.jsonl")
	records_dir = run_dir / "records"
	missing = [
		row["translation_id"]
		for row in worklist
		if not (records_dir / f"{row['translation_id']}.json").exists()
	]
	if missing:
		raise RuntimeError(
			f"cannot assemble: {len(missing)} worklist ids have no record, "
			f"first missing={missing[:3]}",
		)
	output = run_dir / "translation_predictions.jsonl"
	if output.exists():
		raise RuntimeError(f"refusing to overwrite existing predictions file: {output}")
	lines = []
	for row in worklist:
		record = json.loads(
			(records_dir / f"{row['translation_id']}.json").read_text(encoding="utf-8"),
		)
		lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
	output.write_text("\n".join(lines) + "\n", encoding="utf-8")
	return output


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--handoff-root", type=Path, default=DEFAULT_HANDOFF_ROOT)
	parser.add_argument(
		"--run-dir",
		type=Path,
		required=True,
		help="Run directory; existing per-id records are kept and skipped (resume).",
	)
	parser.add_argument("--only-ids", nargs="+", default=None)
	parser.add_argument("--limit", type=int, default=None)
	parser.add_argument("--workers", type=int, default=4)
	parser.add_argument(
		"--assemble",
		action="store_true",
		help="Assemble translation_predictions.jsonl (requires all 475 records).",
	)
	args = parser.parse_args()

	if args.assemble:
		output = assemble_predictions(handoff_root=args.handoff_root, run_dir=args.run_dir)
		print(f"[assembled] {output}", flush=True)
		return 0

	summary = run_translation_calls(
		handoff_root=args.handoff_root,
		run_dir=args.run_dir,
		only_ids=args.only_ids,
		limit=args.limit,
		workers=args.workers,
	)
	print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
