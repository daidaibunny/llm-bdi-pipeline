"""Deduplicate problem-complete NL rows into domain-scoped translation jobs."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from temporal_specification.prompts import build_lifted_ltlf_system_prompt


_CONSISTENCY_FIELDS = (
	"catalog_file",
	"status",
	"parameter_semantics",
	"source_text",
	"declared_parameters",
	"constraints",
)


def build_translation_worklist(
	rows: Sequence[Mapping[str, Any]],
	*,
	prompt_context_by_catalog_file: Mapping[str, str],
) -> tuple[dict[str, object], ...]:
	"""Group rows whose complete semantic model inputs are identical.

	Every problem row remains represented in ``member_sample_ids`` exactly once.
	Equal domain-scoped semantic signatures must first carry identical public
	inputs. Rows from different benchmark labels may then merge only when their
	rendered system-prompt context, source text, parameters, and constraints are
	identical and their hidden semantic signatures agree.
	"""

	domain_signature_groups: dict[
		tuple[str, str], list[Mapping[str, Any]]
	] = defaultdict(list)
	seen_sample_ids: set[str] = set()
	for index, row in enumerate(rows, start=1):
		if not isinstance(row, Mapping):
			raise ValueError(f"manifest row {index} must be a JSON object")
		sample_id = _required_text(row, "sample_id", index=index)
		if sample_id in seen_sample_ids:
			raise ValueError(f"duplicate sample_id {sample_id!r}")
		seen_sample_ids.add(sample_id)
		domain = _required_text(row, "domain", index=index)
		signature = _required_text(row, "semantic_signature", index=index)
		if row.get("status") != "constructed_temporal_query":
			raise ValueError(
				f"sample {sample_id!r} is not a constructed_temporal_query",
			)
		if row.get("failure_reason") not in {None, ""}:
			raise ValueError(f"sample {sample_id!r} carries a failure_reason")
		domain_signature_groups[(domain, signature)].append(row)

	for (domain, signature), members in domain_signature_groups.items():
		representative = members[0]
		for field in _CONSISTENCY_FIELDS:
			expected = _canonical_json(representative.get(field))
			for member in members[1:]:
				if _canonical_json(member.get(field)) != expected:
					raise ValueError(
						f"group {(domain, signature)!r} has inconsistent {field} "
						f"between {representative['sample_id']!r} and "
						f"{member['sample_id']!r}",
					)

	translation_groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
	prompt_context_by_input_signature: dict[str, str] = {}
	for row in rows:
		catalog_file = str(row["catalog_file"])
		if catalog_file not in prompt_context_by_catalog_file:
			raise ValueError(f"missing prompt context for {catalog_file!r}")
		prompt_context = str(prompt_context_by_catalog_file[catalog_file])
		input_signature = _translation_input_signature(row, prompt_context)
		translation_groups[input_signature].append(row)
		prompt_context_by_input_signature[input_signature] = prompt_context

	worklist: list[dict[str, object]] = []
	covered_sample_ids: set[str] = set()
	for input_signature, members in sorted(translation_groups.items()):
		ordered_members = sorted(members, key=lambda item: str(item["sample_id"]))
		representative = ordered_members[0]
		semantic_signatures = {
			str(member["semantic_signature"]) for member in ordered_members
		}
		if len(semantic_signatures) != 1:
			raise ValueError(
				f"translation input {input_signature!r} maps to conflicting semantic "
				f"signatures {sorted(semantic_signatures)!r}",
			)
		member_sample_ids = [str(item["sample_id"]) for item in ordered_members]
		covered_sample_ids.update(member_sample_ids)
		prompt_context = prompt_context_by_input_signature[input_signature]
		worklist.append(
			{
				"schema_version": 1,
				"translation_id": f"tpl_{input_signature}",
				"translation_input_signature": input_signature,
				"prompt_context_sha256": hashlib.sha256(
					prompt_context.encode("utf-8"),
				).hexdigest(),
				"domain": str(representative["domain"]),
				"benchmark_domains": sorted(
					{str(member["domain"]) for member in ordered_members},
				),
				"semantic_signature": next(iter(semantic_signatures)),
				"catalog_file": str(representative["catalog_file"]),
				"equivalent_catalog_files": sorted(
					{str(member["catalog_file"]) for member in ordered_members},
				),
				"status": "constructed_temporal_query",
				"parameter_semantics": str(
					representative["parameter_semantics"],
				),
				"sample_id": member_sample_ids[0],
				"representative_sample_id": member_sample_ids[0],
				"source_text": str(representative["source_text"]),
				"declared_parameters": copy.deepcopy(
					representative["declared_parameters"],
				),
				"constraints": copy.deepcopy(representative["constraints"]),
				"member_sample_ids": member_sample_ids,
				"member_count": len(member_sample_ids),
			},
		)
	if covered_sample_ids != seen_sample_ids:
		raise ValueError("translation worklist does not cover every manifest sample")
	return tuple(worklist)


def write_translation_worklist(
	*,
	manifest_path: str | Path,
	output_path: str | Path,
) -> dict[str, object]:
	"""Read a public manifest JSONL file and write its deduplicated worklist."""

	manifest = Path(manifest_path)
	output = Path(output_path)
	rows: list[Mapping[str, Any]] = []
	for line_number, line in enumerate(
		manifest.read_text(encoding="utf-8").splitlines(),
		start=1,
	):
		if not line.strip():
			continue
		try:
			payload = json.loads(line)
		except json.JSONDecodeError as error:
			raise ValueError(
				f"invalid JSON on manifest line {line_number}: {error.msg}",
			) from error
		if not isinstance(payload, Mapping):
			raise ValueError(f"manifest line {line_number} must be a JSON object")
		rows.append(payload)
	prompt_context_by_catalog_file: dict[str, str] = {}
	for catalog_file in sorted({str(row["catalog_file"]) for row in rows}):
		catalog_path = manifest.parent / catalog_file
		if not catalog_path.is_file():
			raise ValueError(f"catalog file does not exist: {catalog_path}")
		catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
		if not isinstance(catalog_payload, Mapping):
			raise ValueError(f"catalog file must contain a JSON object: {catalog_path}")
		prompt_context_by_catalog_file[catalog_file] = (
			build_lifted_ltlf_system_prompt(catalog_payload)
		)
	worklist = build_translation_worklist(
		rows,
		prompt_context_by_catalog_file=prompt_context_by_catalog_file,
	)
	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text(
		"".join(
			json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n"
			for item in worklist
		),
		encoding="utf-8",
	)
	return {
		"problem_row_count": len(rows),
		"translation_template_count": len(worklist),
		"output_path": str(output),
	}


def _required_text(
	row: Mapping[str, Any],
	field: str,
	*,
	index: int,
) -> str:
	value = str(row.get(field) or "").strip()
	if not value:
		raise ValueError(f"manifest row {index} has empty {field}")
	return value


def _canonical_json(value: object) -> str:
	return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _translation_input_signature(
	row: Mapping[str, Any],
	prompt_context: str,
) -> str:
	payload = _canonical_json(
		{
			"system_prompt": prompt_context,
			"source_text": row["source_text"],
			"declared_parameters": row["declared_parameters"],
			"constraints": row["constraints"],
			"parameter_semantics": row["parameter_semantics"],
		},
	).encode("utf-8")
	return hashlib.sha256(payload).hexdigest()
