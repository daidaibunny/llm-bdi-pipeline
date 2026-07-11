from __future__ import annotations

import json
from pathlib import Path

import pytest

from temporal_input.translation_worklist import build_translation_worklist
from temporal_input.translation_worklist import write_translation_worklist
from temporal_specification.prompts import build_lifted_ltlf_system_prompt
from temporal_specification.prompts import build_lifted_ltlf_user_prompt


def _row(
	*,
	domain: str,
	sample_id: str,
	signature: str,
	source_text: str = "Given parameter X, eventually make ready(X) hold.",
) -> dict[str, object]:
	return {
		"sample_id": sample_id,
		"domain": domain,
		"problem_file": f"src/domains/{domain}/test/{sample_id}.pddl",
		"catalog_file": f"domains/{domain}/catalog.json",
		"status": "constructed_temporal_query",
		"profile": "ordered_two_milestone",
		"construction_tier": "primary",
		"parameter_semantics": "externally_bound",
		"source_text": source_text,
		"declared_parameters": [{"name": "X", "pddl_type": "object"}],
		"constraints": [],
		"semantic_signature": signature,
		"failure_reason": None,
	}


def test_worklist_groups_only_identical_model_inputs() -> None:
	signature_a = "a" * 64
	signature_b = "b" * 64
	worklist = build_translation_worklist(
		[
			_row(domain="domain-a", sample_id="case_2", signature=signature_a),
			_row(domain="domain-a", sample_id="case_1", signature=signature_a),
			_row(
				domain="domain-a",
				sample_id="case_3",
				signature=signature_b,
				source_text="Given parameter X, eventually make alternate(X) hold.",
			),
			_row(domain="domain-b", sample_id="case_4", signature=signature_a),
			_row(domain="domain-c", sample_id="case_5", signature=signature_a),
		],
		prompt_context_by_catalog_file={
			"domains/domain-a/catalog.json": "system prompt alpha",
			"domains/domain-b/catalog.json": "system prompt beta",
			"domains/domain-c/catalog.json": "system prompt alpha",
		},
	)

	assert len(worklist) == 3
	assert len({item["translation_id"] for item in worklist}) == 3
	assert sum(int(item["member_count"]) for item in worklist) == 5
	group = next(
		item
		for item in worklist
		if item["domain"] == "domain-a"
		and item["semantic_signature"] == signature_a
	)
	assert group["sample_id"] == "case_1"
	assert group["representative_sample_id"] == "case_1"
	assert group["member_sample_ids"] == ["case_1", "case_2", "case_5"]
	assert group["benchmark_domains"] == ["domain-a", "domain-c"]
	assert group["equivalent_catalog_files"] == [
		"domains/domain-a/catalog.json",
		"domains/domain-c/catalog.json",
	]
	assert group["member_count"] == 3


def test_worklist_fails_closed_when_one_group_has_conflicting_public_input() -> None:
	signature = "a" * 64

	with pytest.raises(ValueError, match="inconsistent source_text"):
		build_translation_worklist(
			[
				_row(domain="domain-a", sample_id="case_1", signature=signature),
				_row(
					domain="domain-a",
					sample_id="case_2",
					signature=signature,
					source_text="A conflicting translation task.",
				),
			],
			prompt_context_by_catalog_file={
				"domains/domain-a/catalog.json": "system prompt alpha",
			},
		)


def test_worklist_rejects_one_model_input_with_conflicting_gold_semantics() -> None:
	with pytest.raises(ValueError, match="conflicting semantic signatures"):
		build_translation_worklist(
			[
				_row(domain="domain-a", sample_id="case_1", signature="a" * 64),
				_row(domain="domain-b", sample_id="case_2", signature="b" * 64),
			],
			prompt_context_by_catalog_file={
				"domains/domain-a/catalog.json": "identical system prompt",
				"domains/domain-b/catalog.json": "identical system prompt",
			},
		)


def test_worklist_row_can_be_passed_directly_to_prompt_without_membership_leak() -> None:
	worklist = build_translation_worklist(
		[
			_row(domain="domain-a", sample_id="case_1", signature="a" * 64),
			_row(domain="domain-a", sample_id="case_2", signature="a" * 64),
		],
		prompt_context_by_catalog_file={
			"domains/domain-a/catalog.json": "system prompt alpha",
		},
	)
	prompt = build_lifted_ltlf_user_prompt(worklist[0])

	assert "case_1" in prompt
	assert "case_2" not in prompt
	assert "member_sample_ids" not in prompt
	assert "translation_id" not in prompt


def test_write_worklist_preserves_every_manifest_member_once(tmp_path: Path) -> None:
	manifest_path = tmp_path / "natural_language_manifest.jsonl"
	output_path = tmp_path / "translation_worklist.jsonl"
	rows = [
		_row(domain="domain-a", sample_id="case_1", signature="a" * 64),
		_row(domain="domain-a", sample_id="case_2", signature="a" * 64),
		_row(
			domain="domain-a",
			sample_id="case_3",
			signature="b" * 64,
			source_text="Given parameter X, eventually make alternate(X) hold.",
		),
	]
	manifest_path.write_text(
		"".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
		encoding="utf-8",
	)
	catalog_path = tmp_path / "domains" / "domain-a" / "catalog.json"
	catalog_path.parent.mkdir(parents=True)
	catalog_path.write_text(
		json.dumps(
			{
				"domain": "domain-a",
				"predicates": [
					{"name": "ready", "argument_types": ["object"]},
					{"name": "alternate", "argument_types": ["object"]},
				],
				"numeric_functions": [],
				"constants": [],
				"type_parents": {},
			},
		),
		encoding="utf-8",
	)
	prompt_context = build_lifted_ltlf_system_prompt(
		json.loads(catalog_path.read_text(encoding="utf-8")),
	)

	summary = write_translation_worklist(
		manifest_path=manifest_path,
		output_path=output_path,
	)
	written = [
		json.loads(line)
		for line in output_path.read_text(encoding="utf-8").splitlines()
	]

	assert summary == {
		"problem_row_count": 3,
		"translation_template_count": 2,
		"output_path": str(output_path),
	}
	assert written == list(
		build_translation_worklist(
			rows,
			prompt_context_by_catalog_file={
				"domains/domain-a/catalog.json": prompt_context,
			},
		)
	)
	assert sorted(
		sample_id
		for item in written
		for sample_id in item["member_sample_ids"]
	) == ["case_1", "case_2", "case_3"]
