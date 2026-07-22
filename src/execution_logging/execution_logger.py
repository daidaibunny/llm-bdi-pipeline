"""
Structured logger for PDDL-only atomic-library and temporal-goal append runs.

This is a refactored subset of the historical execution logger. It keeps the
useful result-file externalization and a human-readable execution log, but
removes the old HDDL/HTN output model.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


STEP_TITLES = {
	"input_artifact": "INPUT FILE",
	"atomic_backend_selection": "ATOMIC BACKEND SELECTION",
	"atomic_library_generation": "ATOMIC LIBRARY GENERATION",
	"dfa_conversion": "DFA CONVERSION",
	"dfa_validation": "DFA VALIDATION",
	"agentspeak_append": "AGENTSPEAK APPEND",
	"heldout_validation": "HELD-OUT VALIDATION",
}

LLM_PAYLOAD_KEYS = frozenset({"prompt", "response"})
EXTERNAL_ARTIFACT_KEYS = frozenset(
	{
		"plan_library",
		"plan_library_asl",
		"dfa_payload",
		"ltlf_json",
		"backend_artifact",
	},
)

INLINE_LOG_SECTION_LIMIT_BYTES = 12_000
INLINE_TEXT_FIELD_LIMIT_CHARS = 2_000


@dataclass
class ExecutionRecord:
	"""Structured record for one pipeline execution."""

	timestamp: str
	natural_language: str
	success: bool
	status: str | None = None
	step: str | None = None
	mode: str = "temporal_goal_append"
	run_origin: str = "src"
	logs_root: str = "artifacts/runs"
	domain_name: str | None = None
	problem_name: str | None = None
	domain_file: str = ""
	problem_file: str | None = None
	output_dir: str = "output"
	execution_time_seconds: float = 0.0
	timings: dict[str, Any] = field(default_factory=dict)
	input_artifact: dict[str, Any] | None = None
	atomic_backend_selection: dict[str, Any] | None = None
	atomic_library_generation: dict[str, Any] | None = None
	dfa_conversion: dict[str, Any] | None = None
	dfa_validation: dict[str, Any] | None = None
	agentspeak_append: dict[str, Any] | None = None
	heldout_validation: dict[str, Any] | None = None


class ExecutionLogger:
	"""Persist semantic execution JSON and compact human-readable logs."""

	def __init__(self, logs_dir: str | Path = "logs", run_origin: str = "src") -> None:
		self.logs_dir = Path(logs_dir)
		self.logs_dir.mkdir(parents=True, exist_ok=True)
		self.run_origin = run_origin
		self.current_record: ExecutionRecord | None = None
		self.current_log_dir: Path | None = None
		self.start_time: datetime | None = None

	def start_pipeline(
		self,
		natural_language: str,
		*,
		mode: str = "temporal_goal_append",
		domain_file: str = "",
		problem_file: str | None = None,
		domain_name: str | None = None,
		problem_name: str | None = None,
		timestamp: str | None = None,
	) -> None:
		"""Start one structured execution record."""

		self.start_time = datetime.now()
		resolved_timestamp = timestamp or self.start_time.strftime("%Y%m%d_%H%M%S")
		dir_parts = [
			resolved_timestamp,
			self._slug_component(domain_name or Path(domain_file).stem or "domain"),
		]
		if problem_name:
			dir_parts.append(self._slug_component(problem_name))
		self.current_log_dir = self.logs_dir / "_".join(part for part in dir_parts if part)
		self.current_log_dir.mkdir(parents=True, exist_ok=True)
		self.current_record = ExecutionRecord(
			timestamp=resolved_timestamp,
			natural_language=self._compact_text_field(natural_language),
			success=False,
			mode=mode,
			run_origin=self.run_origin,
			logs_root=str(self.logs_dir),
			domain_name=domain_name,
			problem_name=problem_name,
			domain_file=domain_file,
			problem_file=problem_file,
			output_dir=str(self.current_log_dir),
		)
		self._save_current_state()

	def record_step_timing(
		self,
		step_name: str,
		total_seconds: float,
		*,
		breakdown: Mapping[str, Any] | None = None,
		metadata: Mapping[str, Any] | None = None,
	) -> None:
		if self.current_record is None:
			return
		self.current_record.timings[step_name] = {
			"total_seconds": float(total_seconds),
			"breakdown": dict(breakdown or {}),
			"metadata": dict(metadata or {}),
		}
		self._save_current_state()

	def log_input_artifact(
		self,
		artifacts: Mapping[str, Any] | None,
		*,
		status: str,
		error: str | None = None,
		metadata: Mapping[str, Any] | None = None,
		llm: Mapping[str, Any] | None = None,
	) -> None:
		self._set_step_payload(
			"input_artifact",
			status=status,
			error=error,
			artifacts=artifacts,
			metadata=metadata,
			llm=llm,
		)

	def log_atomic_backend_selection(
		self,
		artifacts: Mapping[str, Any] | None,
		*,
		status: str,
		error: str | None = None,
		metadata: Mapping[str, Any] | None = None,
	) -> None:
		self._set_step_payload(
			"atomic_backend_selection",
			status=status,
			error=error,
			artifacts=artifacts,
			metadata=metadata,
		)

	def log_atomic_library_generation(
		self,
		artifacts: Mapping[str, Any] | None,
		*,
		status: str,
		error: str | None = None,
		backend: str | None = None,
		metadata: Mapping[str, Any] | None = None,
	) -> None:
		self._set_step_payload(
			"atomic_library_generation",
			status=status,
			backend=backend,
			error=error,
			artifacts=artifacts,
			metadata=metadata,
		)

	def log_dfa_conversion(
		self,
		artifacts: Mapping[str, Any] | None,
		*,
		status: str,
		error: str | None = None,
		metadata: Mapping[str, Any] | None = None,
	) -> None:
		self._set_step_payload(
			"dfa_conversion",
			status=status,
			error=error,
			artifacts=artifacts,
			metadata=metadata,
		)

	def log_dfa_validation(
		self,
		artifacts: Mapping[str, Any] | None,
		*,
		status: str,
		error: str | None = None,
		metadata: Mapping[str, Any] | None = None,
	) -> None:
		self._set_step_payload(
			"dfa_validation",
			status=status,
			error=error,
			artifacts=artifacts,
			metadata=metadata,
		)

	def log_agentspeak_append(
		self,
		artifacts: Mapping[str, Any] | None,
		*,
		status: str,
		error: str | None = None,
		metadata: Mapping[str, Any] | None = None,
	) -> None:
		self._set_step_payload(
			"agentspeak_append",
			status=status,
			error=error,
			artifacts=artifacts,
			metadata=metadata,
		)

	def log_heldout_validation(
		self,
		artifacts: Mapping[str, Any] | None,
		*,
		status: str,
		error: str | None = None,
		metadata: Mapping[str, Any] | None = None,
	) -> None:
		self._set_step_payload(
			"heldout_validation",
			status=status,
			error=error,
			artifacts=artifacts,
			metadata=metadata,
		)

	def end_pipeline(self, *, success: bool) -> Path:
		"""Finalize and return the human-readable execution log path."""

		if self.current_record is None or self.current_log_dir is None:
			raise RuntimeError("No execution is currently active.")
		if self.start_time is not None:
			self.current_record.execution_time_seconds = (
				datetime.now() - self.start_time
			).total_seconds()
		self.current_record.success = bool(success)
		self.current_record.status = "success" if success else "failed"
		self._save_current_state()
		self._write_human_log()
		return self.current_log_dir / "execution.txt"

	def _set_step_payload(
		self,
		step_name: str,
		*,
		status: str,
		backend: str | None = None,
		error: str | None = None,
		metadata: Mapping[str, Any] | None = None,
		artifacts: Mapping[str, Any] | None = None,
		llm: Mapping[str, Any] | None = None,
	) -> None:
		if self.current_record is None:
			return
		payload: dict[str, Any] = {"status": str(status).lower()}
		if backend:
			payload["backend"] = backend
		if error:
			payload["error"] = str(error)
		if metadata:
			payload["metadata"] = self._compact_large_section(
				step_name,
				"metadata",
				self._sanitise_paths(dict(metadata)),
			)
		if artifacts:
			payload["artifacts"] = self._compact_artifacts_payload(
				step_name,
				self._sanitise_paths(dict(artifacts)),
			)
		if llm:
			payload["llm"] = self._compact_llm_payload(step_name, dict(llm))
		if payload["status"] == "failed":
			self.current_record.status = "failed"
			self.current_record.step = step_name
		setattr(self.current_record, step_name, payload)
		self._save_current_state()

	def _save_current_state(self) -> None:
		if self.current_record is None or self.current_log_dir is None:
			return
		execution_path = self.current_log_dir / "execution.json"
		execution_path.write_text(
			json.dumps(self._record_to_dict(), indent=2, default=str) + "\n",
			encoding="utf-8",
		)

	def _record_to_dict(self) -> dict[str, Any]:
		if self.current_record is None:
			return {}
		record = asdict(self.current_record)
		return self._json_safe(
			{
				key: value
				for key, value in record.items()
				if value not in (None, {}, [], "")
			},
		)

	def _write_human_log(self) -> None:
		if self.current_record is None or self.current_log_dir is None:
			return
		record = self._record_to_dict()
		header = self._mode_title(str(record.get("mode") or "pipeline_execution"))
		lines = [
			header,
			"=" * 80,
			f"Mode: {record.get('mode') or 'unknown'}",
			f"Success: {record.get('success')}",
			f"Domain: {record.get('domain_name') or 'N/A'}",
			f"Problem: {record.get('problem_name') or 'N/A'}",
			f"Execution seconds: {float(record.get('execution_time_seconds') or 0.0):.3f}",
			"",
		]
		for step_name, title in STEP_TITLES.items():
			payload = record.get(step_name)
			if not isinstance(payload, dict):
				continue
			lines.extend([title, "-" * 80, f"Status: {str(payload.get('status', '')).upper()}"])
			if payload.get("backend"):
				lines.append(f"Backend: {payload['backend']}")
			if payload.get("error"):
				lines.append(f"Error: {payload['error']}")
			if payload.get("metadata"):
				lines.append("Metadata:")
				lines.append(json.dumps(payload["metadata"], indent=2, default=str))
			if payload.get("artifacts"):
				lines.append("Files:")
				lines.append(json.dumps(payload["artifacts"], indent=2, default=str))
			if payload.get("llm"):
				lines.append("LLM:")
				lines.append(json.dumps(payload["llm"], indent=2, default=str))
			lines.append("")
		(self.current_log_dir / "execution.txt").write_text(
			"\n".join(lines).rstrip() + "\n",
			encoding="utf-8",
		)

	def _compact_llm_payload(self, step_name: str, llm: dict[str, Any]) -> dict[str, Any]:
		compact: dict[str, Any] = {}
		for key, value in llm.items():
			if key in LLM_PAYLOAD_KEYS and value is not None:
				reference = self._write_payload_file(
					step_name=step_name,
					payload_name=f"llm_{key}",
					value=value,
				)
				compact[f"{key}_file"] = reference["file"]
				compact[f"{key}_bytes"] = reference["bytes"]
				continue
			compact[key] = self._json_safe(value)
		return compact

	def _compact_artifacts_payload(
		self,
		step_name: str,
		artifacts: dict[str, Any],
	) -> dict[str, Any]:
		compact: dict[str, Any] = {}
		for key, value in artifacts.items():
			if key in EXTERNAL_ARTIFACT_KEYS and value is not None:
				reference = self._write_payload_file(
					step_name=step_name,
					payload_name=str(key),
					value=value,
				)
				compact[f"{key}_file"] = reference["file"]
				compact[f"{key}_bytes"] = reference["bytes"]
				continue
			compact[key] = self._json_safe(value)
		return self._compact_large_section(step_name, "artifacts", compact)

	def _compact_large_section(self, step_name: str, payload_name: str, value: Any) -> Any:
		payload = self._json_safe(value)
		payload_size = len(json.dumps(payload, default=str).encode("utf-8"))
		if payload_size <= INLINE_LOG_SECTION_LIMIT_BYTES:
			return payload
		reference = self._write_payload_file(
			step_name=step_name,
			payload_name=payload_name,
			value=payload,
		)
		return {
			"payload_file": reference["file"],
			"payload_bytes": reference["bytes"],
		}

	def _write_payload_file(
		self,
		*,
		step_name: str,
		payload_name: str,
		value: Any,
	) -> dict[str, Any]:
		if self.current_log_dir is None:
			return {"file": "", "bytes": 0}
		payload_dir = self.current_log_dir / "payloads"
		payload_dir.mkdir(parents=True, exist_ok=True)
		slug = self._slug_component(f"{step_name}_{payload_name}")
		is_text_payload = isinstance(value, str)
		payload_path = payload_dir / f"{slug}{'.txt' if is_text_payload else '.json'}"
		payload_text = value if is_text_payload else json.dumps(self._json_safe(value), indent=2)
		payload_path.write_text(payload_text, encoding="utf-8")
		return {
			"file": str(payload_path.relative_to(self.current_log_dir)),
			"bytes": len(payload_text.encode("utf-8")),
		}

	def _sanitise_paths(self, value: Any) -> Any:
		if self.current_log_dir is None:
			return value
		if isinstance(value, dict):
			return {key: self._sanitise_paths(item) for key, item in value.items()}
		if isinstance(value, list):
			return [self._sanitise_paths(item) for item in value]
		if isinstance(value, tuple):
			return [self._sanitise_paths(item) for item in value]
		if not isinstance(value, str):
			return value
		candidate = Path(value)
		if not candidate.is_absolute():
			return value
		try:
			return str(candidate.resolve().relative_to(self.current_log_dir.resolve()))
		except Exception:
			return value

	def _json_safe(self, value: Any) -> Any:
		if isinstance(value, dict):
			return {str(key): self._json_safe(item) for key, item in value.items()}
		if isinstance(value, list):
			return [self._json_safe(item) for item in value]
		if isinstance(value, tuple):
			return [self._json_safe(item) for item in value]
		if isinstance(value, bytes):
			return value.decode("utf-8", errors="replace")
		if isinstance(value, Path):
			return str(value)
		if isinstance(value, (str, int, float, bool)) or value is None:
			return value
		return str(value)

	@staticmethod
	def _compact_text_field(value: str) -> str:
		text = str(value or "")
		if len(text) <= INLINE_TEXT_FIELD_LIMIT_CHARS:
			return text
		digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
		return (
			f"{text[:INLINE_TEXT_FIELD_LIMIT_CHARS]}..."
			f"[truncated chars={len(text)} sha256={digest}]"
		)

	@staticmethod
	def _slug_component(value: str | None) -> str:
		slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value or "").strip()).strip("_")
		return slug or "run"

	@staticmethod
	def _mode_title(mode: str) -> str:
		return re.sub(r"[^a-zA-Z0-9]+", " ", mode).strip().upper() or "PIPELINE EXECUTION"
