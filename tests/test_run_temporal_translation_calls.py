from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_SPEC = importlib.util.spec_from_file_location(
	"run_temporal_translation_calls",
	PROJECT_ROOT / "scripts" / "run_temporal_translation_calls.py",
)
runner = importlib.util.module_from_spec(_SPEC)
sys.modules["run_temporal_translation_calls"] = runner
_SPEC.loader.exec_module(runner)


SEALED_COMMIT = "sealedcommit0000000000000000000000000000"


def _catalog() -> dict[str, object]:
	return {
		"domain": "toy",
		"predicates": [{"name": "ready", "argument_types": ["object"]}],
		"numeric_functions": [],
		"constants": [],
		"type_parents": {},
	}


def _worklist_row(translation_id: str, sample_id: str) -> dict[str, object]:
	return {
		"schema_version": 1,
		"translation_id": translation_id,
		"translation_input_signature": f"sig_{translation_id}",
		"domain": "toy",
		"benchmark_domains": ["toy"],
		"catalog_file": "domains/toy/catalog.json",
		"equivalent_catalog_files": ["domains/toy/catalog.json"],
		"sample_id": sample_id,
		"representative_sample_id": sample_id,
		"source_text": (
			"Given parameter X of PDDL type object, ensure that at some state "
			"predicate ready holds for argument X."
		),
		"declared_parameters": [{"name": "X", "pddl_type": "object"}],
		"constraints": [],
		"parameter_semantics": "externally_bound",
		"semantic_signature": f"sem_{translation_id}",
		"prompt_context_sha256": f"ctx_{translation_id}",
		"member_sample_ids": [sample_id],
		"member_count": 1,
		"status": "constructed_temporal_query",
	}


def _handoff_root(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
	root = tmp_path / "handoff"
	(root / "domains" / "toy").mkdir(parents=True)
	(root / "domains" / "toy" / "catalog.json").write_text(json.dumps(_catalog()))
	(root / "translation_worklist.jsonl").write_text(
		"".join(json.dumps(row) + "\n" for row in rows),
	)
	(root / "handoff_manifest.json").write_text(
		json.dumps({"prompt_source_commit": SEALED_COMMIT}),
	)
	return root


def _valid_payload(sample_id: str) -> dict[str, object]:
	return {
		"schema_version": 1,
		"sample_id": sample_id,
		"temporal_logic": "LTLf",
		"ltlf_formula": "F(a0)",
		"atoms": [
			{"symbol": "a0", "kind": "predicate", "predicate": "ready", "args": ["X"]},
		],
		"declared_parameters": [{"name": "X", "pddl_type": "object"}],
		"constraints": [],
		"status": "supported",
	}


class FakeClient:
	"""Scripted OpenAI-compatible client; records every request."""

	def __init__(self, responses: list[str]) -> None:
		self._responses = list(responses)
		self.requests: list[dict[str, object]] = []
		self.chat = SimpleNamespace(
			completions=SimpleNamespace(create=self._create),
		)

	def _create(self, **kwargs: object) -> SimpleNamespace:
		self.requests.append(kwargs)
		if not self._responses:
			raise AssertionError("FakeClient exhausted")
		return SimpleNamespace(
			choices=[
				SimpleNamespace(
					message=SimpleNamespace(content=self._responses.pop(0)),
					finish_reason="stop",
				)
			]
		)


def _settings(max_semantic_retries: int = 3) -> "runner.RunSettings":
	return runner.RunSettings(
		model_id="test-model",
		model_parameters={"temperature": 0},
		prompt_config="full",
		prompt_source_commit=SEALED_COMMIT,
		max_semantic_retries=max_semantic_retries,
		timeout_seconds=10.0,
		max_tokens=1000,
	)


_CANONICAL_KEYS = {
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
}


def test_accepted_first_attempt(tmp_path: Path) -> None:
	rows = [_worklist_row("tpl_a", "toy_p_1")]
	root = _handoff_root(tmp_path, rows)
	raw = json.dumps(_valid_payload("toy_p_1"))
	client = FakeClient([raw])
	summary = runner.run_translation_calls(
		handoff_root=root,
		run_dir=tmp_path / "run",
		client=client,
		settings=_settings(),
		workers=1,
	)
	assert summary["accepted"] == 1 and summary["terminal_failure"] == 0
	record = json.loads((tmp_path / "run" / "records" / "tpl_a.json").read_text())
	assert set(record) == _CANONICAL_KEYS
	assert record["outcome"] == "accepted"
	assert record["attempt_count"] == 1
	assert record["terminal_error"] is None
	assert json.loads(record["raw_response"]) == record["prediction"]
	# The primary call carries exactly system + user messages.
	first_messages = client.requests[0]["messages"]
	assert [m["role"] for m in first_messages] == ["system", "user"]
	assert "member_sample_ids" not in first_messages[1]["content"]
	assert "tpl_a" not in first_messages[0]["content"] + first_messages[1]["content"]


def test_semantic_retry_then_success(tmp_path: Path) -> None:
	rows = [_worklist_row("tpl_b", "toy_p_2")]
	root = _handoff_root(tmp_path, rows)
	bad = json.dumps({**_valid_payload("toy_p_2"), "ltlf_formula": "G(a0)"})
	good = json.dumps(_valid_payload("toy_p_2"))
	client = FakeClient([bad, good])
	runner.run_translation_calls(
		handoff_root=root,
		run_dir=tmp_path / "run",
		client=client,
		settings=_settings(),
		workers=1,
	)
	record = json.loads((tmp_path / "run" / "records" / "tpl_b.json").read_text())
	assert record["outcome"] == "accepted"
	assert record["attempt_count"] == 2
	retry_messages = client.requests[1]["messages"]
	assert [m["role"] for m in retry_messages] == ["system", "user", "assistant", "user"]
	assert "model-correctable validation check" in retry_messages[3]["content"]
	assert "G(a0)" in retry_messages[3]["content"]


def test_terminal_failure_after_budget(tmp_path: Path) -> None:
	rows = [_worklist_row("tpl_c", "toy_p_3")]
	root = _handoff_root(tmp_path, rows)
	bad = json.dumps({**_valid_payload("toy_p_3"), "ltlf_formula": "G(a0)"})
	client = FakeClient([bad, bad, bad])
	runner.run_translation_calls(
		handoff_root=root,
		run_dir=tmp_path / "run",
		client=client,
		settings=_settings(max_semantic_retries=2),
		workers=1,
	)
	record = json.loads((tmp_path / "run" / "records" / "tpl_c.json").read_text())
	assert record["outcome"] == "terminal_failure"
	assert record["attempt_count"] == 3
	assert record["prediction"] is None
	assert record["terminal_error"]["error_type"] == "E_UNSUPPORTED_OPERATOR"
	assert record["terminal_error"]["attempt"] == 3


def test_resume_skips_existing_records(tmp_path: Path) -> None:
	rows = [_worklist_row("tpl_d", "toy_p_4"), _worklist_row("tpl_e", "toy_p_5")]
	root = _handoff_root(tmp_path, rows)
	run_dir = tmp_path / "run"
	client_one = FakeClient([json.dumps(_valid_payload("toy_p_4"))])
	runner.run_translation_calls(
		handoff_root=root,
		run_dir=run_dir,
		only_ids=["tpl_d"],
		client=client_one,
		settings=_settings(),
		workers=1,
	)
	client_two = FakeClient([json.dumps(_valid_payload("toy_p_5"))])
	summary = runner.run_translation_calls(
		handoff_root=root,
		run_dir=run_dir,
		client=client_two,
		settings=_settings(),
		workers=1,
	)
	assert summary["skipped_existing"] == 1
	assert summary["processed"] == 1
	assert len(client_two.requests) == 1  # tpl_d was not re-called


def test_assemble_requires_all_records_and_preserves_order(tmp_path: Path) -> None:
	rows = [_worklist_row("tpl_f", "toy_p_6"), _worklist_row("tpl_g", "toy_p_7")]
	root = _handoff_root(tmp_path, rows)
	run_dir = tmp_path / "run"
	client = FakeClient([json.dumps(_valid_payload("toy_p_6"))])
	runner.run_translation_calls(
		handoff_root=root,
		run_dir=run_dir,
		only_ids=["tpl_f"],
		client=client,
		settings=_settings(),
		workers=1,
	)
	with pytest.raises(RuntimeError, match="no record"):
		runner.assemble_predictions(handoff_root=root, run_dir=run_dir)
	client = FakeClient([json.dumps(_valid_payload("toy_p_7"))])
	runner.run_translation_calls(
		handoff_root=root,
		run_dir=run_dir,
		client=client,
		settings=_settings(),
		workers=1,
	)
	output = runner.assemble_predictions(handoff_root=root, run_dir=run_dir)
	lines = [json.loads(line) for line in output.read_text().splitlines()]
	assert [record["translation_id"] for record in lines] == ["tpl_f", "tpl_g"]
	with pytest.raises(RuntimeError, match="refusing to overwrite"):
		runner.assemble_predictions(handoff_root=root, run_dir=run_dir)


def test_transport_failure_is_terminal_not_retried(tmp_path: Path) -> None:
	rows = [_worklist_row("tpl_h", "toy_p_8")]
	root = _handoff_root(tmp_path, rows)

	class TimeoutClient:
		def __init__(self) -> None:
			self.calls = 0
			self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

		def _create(self, **kwargs: object) -> SimpleNamespace:
			self.calls += 1
			raise TimeoutError("simulated APITimeoutError")

	client = TimeoutClient()
	runner.run_translation_calls(
		handoff_root=root,
		run_dir=tmp_path / "run",
		client=client,
		settings=_settings(),
		workers=1,
	)
	record = json.loads((tmp_path / "run" / "records" / "tpl_h.json").read_text())
	assert record["outcome"] == "terminal_failure"
	assert record["terminal_error"]["error_type"] == "E_LLM_TIMEOUT"
	assert client.calls == 1  # infrastructure failures never re-prompt the model
