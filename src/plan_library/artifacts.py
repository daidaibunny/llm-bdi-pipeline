"""
Artifact persistence for generated DFA-driven plan-library bundles.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from temporal_specification import QueryInstructionRecord, TemporalSpecificationRecord

from .models import LibraryValidationRecord, PlanGenerationSummary, PlanLibrary


@dataclass(frozen=True)
class PlanLibraryArtifactBundle:
	"""Persisted artifact bundle for one generated plan library."""

	domain_name: str
	query_sequence: Sequence[QueryInstructionRecord]
	temporal_specifications: Sequence[TemporalSpecificationRecord]
	plan_library: PlanLibrary
	generation_summary: PlanGenerationSummary
	library_validation: LibraryValidationRecord
	dfa_metadata: Dict[str, Any]
	artifact_root: str | None = None
	plan_library_asl_file: str | None = None

	def to_dict(self) -> Dict[str, Any]:
		return {
			"domain_name": self.domain_name,
			"query_sequence": [record.to_dict() for record in self.query_sequence],
			"temporal_specifications": [record.to_dict() for record in self.temporal_specifications],
			"plan_library": self.plan_library.to_dict(),
			"generation_summary": self.generation_summary.to_dict(),
			"library_validation": self.library_validation.to_dict(),
			"dfa_metadata": dict(self.dfa_metadata),
			"artifact_root": self.artifact_root,
			"plan_library_asl_file": self.plan_library_asl_file,
		}

	@classmethod
	def from_dict(cls, payload: Dict[str, Any]) -> "PlanLibraryArtifactBundle":
		return cls(
			domain_name=str(payload.get("domain_name") or "").strip(),
			query_sequence=tuple(
				QueryInstructionRecord.from_dict(item)
				for item in (payload.get("query_sequence") or ())
				if isinstance(item, dict)
			),
			temporal_specifications=tuple(
				TemporalSpecificationRecord.from_dict(item)
				for item in (payload.get("temporal_specifications") or ())
				if isinstance(item, dict)
			),
			plan_library=PlanLibrary.from_dict(dict(payload.get("plan_library") or {})),
			generation_summary=PlanGenerationSummary.from_dict(
				dict(payload.get("generation_summary") or {}),
			),
			library_validation=LibraryValidationRecord.from_dict(
				dict(payload.get("library_validation") or {}),
			),
			dfa_metadata=dict(payload.get("dfa_metadata") or {}),
			artifact_root=(
				str(payload.get("artifact_root")).strip()
				if payload.get("artifact_root") is not None
				else None
			),
			plan_library_asl_file=(
				str(payload.get("plan_library_asl_file")).strip()
				if payload.get("plan_library_asl_file") is not None
				else None
			),
		)


def persist_plan_library_artifact_bundle(
	*,
	artifact_root: str | Path,
	artifact: PlanLibraryArtifactBundle,
	plan_library_asl_text: str | None = None,
) -> Dict[str, str]:
	"""Persist a plan-library bundle under one stable artifact root."""

	root = Path(artifact_root).expanduser().resolve()
	root.mkdir(parents=True, exist_ok=True)

	artifact_metadata_path = root / "artifact_metadata.json"
	query_sequence_path = root / "query_sequence.json"
	temporal_specifications_path = root / "temporal_specifications.json"
	plan_library_path = root / "plan_library.json"
	plan_library_asl_path = root / "plan_library.asl"
	generation_summary_path = root / "generation_summary.json"
	library_validation_path = root / "library_validation.json"
	dfa_metadata_path = root / "dfa_metadata.json"

	artifact_metadata_path.write_text(
		json.dumps(
			{
				"domain_name": artifact.domain_name,
				"query_count": len(tuple(artifact.query_sequence or ())),
				"temporal_specification_count": len(tuple(artifact.temporal_specifications or ())),
			},
			indent=2,
		)
		+ "\n",
		encoding="utf-8",
	)
	query_sequence_path.write_text(
		json.dumps([record.to_dict() for record in artifact.query_sequence], indent=2) + "\n",
		encoding="utf-8",
	)
	temporal_specifications_path.write_text(
		json.dumps([record.to_dict() for record in artifact.temporal_specifications], indent=2)
		+ "\n",
		encoding="utf-8",
	)
	plan_library_path.write_text(
		json.dumps(artifact.plan_library.to_dict(), indent=2) + "\n",
		encoding="utf-8",
	)
	generation_summary_path.write_text(
		json.dumps(artifact.generation_summary.to_dict(), indent=2) + "\n",
		encoding="utf-8",
	)
	library_validation_path.write_text(
		json.dumps(artifact.library_validation.to_dict(), indent=2) + "\n",
		encoding="utf-8",
	)
	dfa_metadata_path.write_text(
		json.dumps(artifact.dfa_metadata, indent=2, default=str) + "\n",
		encoding="utf-8",
	)
	if plan_library_asl_text is not None:
		plan_library_asl_path.write_text(str(plan_library_asl_text), encoding="utf-8")

	paths = {
		"artifact_metadata": str(artifact_metadata_path),
		"query_sequence": str(query_sequence_path),
		"temporal_specifications": str(temporal_specifications_path),
		"plan_library": str(plan_library_path),
		"generation_summary": str(generation_summary_path),
		"library_validation": str(library_validation_path),
		"dfa_metadata": str(dfa_metadata_path),
	}
	if plan_library_asl_text is not None:
		paths["plan_library_asl"] = str(plan_library_asl_path)
	return paths


def load_plan_library_artifact_bundle(
	library_artifact: str | Path | Dict[str, Any] | PlanLibraryArtifactBundle,
) -> PlanLibraryArtifactBundle:
	"""Load a plan-library artifact bundle from disk or memory."""

	if isinstance(library_artifact, PlanLibraryArtifactBundle):
		return library_artifact
	if isinstance(library_artifact, dict):
		return PlanLibraryArtifactBundle.from_dict(library_artifact)

	artifact_root = Path(library_artifact).expanduser().resolve()
	if artifact_root.is_file():
		artifact_root = artifact_root.parent

	query_sequence_payload = json.loads((artifact_root / "query_sequence.json").read_text())
	temporal_specifications_payload = json.loads(
		(artifact_root / "temporal_specifications.json").read_text(),
	)
	plan_library_payload = json.loads((artifact_root / "plan_library.json").read_text())
	generation_summary_payload = json.loads((artifact_root / "generation_summary.json").read_text())
	library_validation_payload = json.loads((artifact_root / "library_validation.json").read_text())
	dfa_metadata_path = artifact_root / "dfa_metadata.json"
	dfa_metadata = json.loads(dfa_metadata_path.read_text()) if dfa_metadata_path.exists() else {}
	artifact_metadata_path = artifact_root / "artifact_metadata.json"
	artifact_metadata = (
		json.loads(artifact_metadata_path.read_text())
		if artifact_metadata_path.exists()
		else {}
	)
	plan_library_asl_path = artifact_root / "plan_library.asl"
	return PlanLibraryArtifactBundle(
		domain_name=str(artifact_metadata.get("domain_name") or artifact_root.name),
		query_sequence=tuple(
			QueryInstructionRecord.from_dict(item)
			for item in query_sequence_payload
			if isinstance(item, dict)
		),
		temporal_specifications=tuple(
			TemporalSpecificationRecord.from_dict(item)
			for item in temporal_specifications_payload
			if isinstance(item, dict)
		),
		plan_library=PlanLibrary.from_dict(dict(plan_library_payload)),
		generation_summary=PlanGenerationSummary.from_dict(dict(generation_summary_payload)),
		library_validation=LibraryValidationRecord.from_dict(dict(library_validation_payload)),
		dfa_metadata=dict(dfa_metadata),
		artifact_root=str(artifact_root),
		plan_library_asl_file=(
			str(plan_library_asl_path) if plan_library_asl_path.exists() else None
		),
	)
