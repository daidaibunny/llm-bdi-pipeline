"""
Artifact pipeline for using DFA temporal controllers over domain-level libraries.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from domain_model.query_sequence import infer_query_domain
from domain_model.query_sequence import load_query_sequence_records
from evaluation.temporal_compilation import DFABuilder
from plan_library.rendering import render_plan_library_asl
from temporal_specification import QueryInstructionRecord
from temporal_specification import TemporalSpecificationRecord
from utils.pddl_parser import PDDLParser

from .dfa_adapter import DFAAchievementRequest
from .dfa_adapter import inspect_dfa_guard_to_achievement_request
from .dfa_controller import progress_transitions_from_dfa_state
from .library_synthesis import ExternalSketchPolicySource
from .library_synthesis import UnifiedSynthesisResult
from .library_synthesis import synthesize_domain_level_asl_library


@dataclass(frozen=True)
class DomainLevelTemporalArtifact:
	"""Domain-level ASL library plus query-specific DFA controller metadata."""

	domain_name: str
	query_domain: str
	query_sequence: tuple[QueryInstructionRecord, ...]
	temporal_specifications: tuple[TemporalSpecificationRecord, ...]
	synthesis_result: UnifiedSynthesisResult
	dfa_metadata: dict[str, dict[str, Any]]
	dfa_progress_requests: dict[str, tuple[DFAAchievementRequest, ...]]
	dfa_progress_diagnostics: dict[str, tuple[dict[str, object], ...]]

	@property
	def plan_library(self):
		return self.synthesis_result.plan_library

	def to_dict(self) -> dict[str, object]:
		return {
			"domain_name": self.domain_name,
			"query_domain": self.query_domain,
			"query_sequence": [record.to_dict() for record in self.query_sequence],
			"temporal_specifications": [
				record.to_dict() for record in self.temporal_specifications
			],
			"plan_library": self.plan_library.to_dict(),
			"synthesis_report": dict(self.synthesis_result.report),
			"dfa_metadata": dict(self.dfa_metadata),
			"dfa_progress_requests": _progress_requests_to_dict(
				self.dfa_progress_requests,
			),
			"dfa_progress_diagnostics": _progress_diagnostics_to_dict(
				self.dfa_progress_diagnostics,
			),
		}


def build_domain_level_temporal_artifact(
	*,
	domain_file: str | Path,
	training_problem_files: Sequence[str | Path] = (),
	query_dataset: str | Path | None = None,
	query_domain: str | None = None,
	query_ids: Sequence[str] | None = None,
	dfa_builder: DFABuilder | None = None,
	external_sketch_policies: Sequence[ExternalSketchPolicySource] = (),
	synthesis_profile: str = "bootstrap",
) -> DomainLevelTemporalArtifact:
	"""Build a domain-level library and DFA request metadata for selected TEG queries."""

	domain_path = Path(domain_file).expanduser().resolve()
	domain = PDDLParser.parse_domain(domain_path)
	resolved_query_domain = infer_query_domain(
		domain_file=domain_path,
		explicit_domain=query_domain,
	)
	query_sequence, temporal_specifications = load_query_sequence_records(
		domain_file=domain_path,
		dataset_path=query_dataset,
		query_domain=resolved_query_domain,
		query_ids=query_ids,
	)
	synthesis_result = synthesize_domain_level_asl_library(
		domain_file=domain_path,
		training_problem_files=training_problem_files,
		external_sketch_policies=external_sketch_policies,
		synthesis_profile=synthesis_profile,
	)
	builder = dfa_builder or DFABuilder()
	dfa_metadata: dict[str, dict[str, Any]] = {}
	dfa_progress_requests: dict[str, tuple[DFAAchievementRequest, ...]] = {}
	dfa_progress_diagnostics: dict[str, tuple[dict[str, object], ...]] = {}
	for record in temporal_specifications:
		payload = dict(builder.build(record))
		dfa_metadata[record.instruction_id] = payload
		requests, diagnostics = _inspect_progress_requests_from_initial_state(
			payload=payload,
			domain_key=resolved_query_domain,
			domain_file=domain_path,
			declared_predicates=domain.predicates,
		)
		dfa_progress_requests[record.instruction_id] = requests
		dfa_progress_diagnostics[record.instruction_id] = diagnostics
	return DomainLevelTemporalArtifact(
		domain_name=domain.name,
		query_domain=resolved_query_domain,
		query_sequence=tuple(query_sequence),
		temporal_specifications=tuple(temporal_specifications),
		synthesis_result=synthesis_result,
		dfa_metadata=dfa_metadata,
		dfa_progress_requests=dfa_progress_requests,
		dfa_progress_diagnostics=dfa_progress_diagnostics,
	)


def persist_domain_level_temporal_artifact(
	*,
	artifact_root: str | Path,
	artifact: DomainLevelTemporalArtifact,
) -> dict[str, str]:
	"""Persist the domain-level library and query-specific DFA controller metadata."""

	root = Path(artifact_root).expanduser().resolve()
	root.mkdir(parents=True, exist_ok=True)
	paths = {
		"artifact_metadata": root / "artifact_metadata.json",
		"query_sequence": root / "query_sequence.json",
		"temporal_specifications": root / "temporal_specifications.json",
		"plan_library": root / "plan_library.json",
		"plan_library_asl": root / "plan_library.asl",
		"synthesis_report": root / "synthesis_report.json",
		"dfa_metadata": root / "dfa_metadata.json",
		"dfa_progress_requests": root / "dfa_progress_requests.json",
		"dfa_progress_diagnostics": root / "dfa_progress_diagnostics.json",
	}
	metadata = {
		"domain_name": artifact.domain_name,
		"query_domain": artifact.query_domain,
		"query_count": len(artifact.query_sequence),
		"temporal_specification_count": len(artifact.temporal_specifications),
		"domain_level_library_plan_count": len(artifact.plan_library.plans),
		"dfa_count": len(artifact.dfa_metadata),
		"dfa_progress_request_count": sum(
			len(requests) for requests in artifact.dfa_progress_requests.values()
		),
	}
	_write_json(paths["artifact_metadata"], metadata)
	_write_json(paths["query_sequence"], [record.to_dict() for record in artifact.query_sequence])
	_write_json(
		paths["temporal_specifications"],
		[record.to_dict() for record in artifact.temporal_specifications],
	)
	_write_json(paths["plan_library"], artifact.plan_library.to_dict())
	paths["plan_library_asl"].write_text(
		render_plan_library_asl(artifact.plan_library),
		encoding="utf-8",
	)
	_write_json(paths["synthesis_report"], dict(artifact.synthesis_result.report))
	_write_json(paths["dfa_metadata"], artifact.dfa_metadata)
	_write_json(
		paths["dfa_progress_requests"],
		_progress_requests_to_dict(artifact.dfa_progress_requests),
	)
	_write_json(
		paths["dfa_progress_diagnostics"],
		_progress_diagnostics_to_dict(artifact.dfa_progress_diagnostics),
	)
	return {name: str(path) for name, path in paths.items()}


def _progress_requests_to_dict(
	requests: Mapping[str, Sequence[DFAAchievementRequest]],
) -> dict[str, list[dict[str, object]]]:
	return {
		query_id: [request.to_dict() for request in tuple(query_requests or ())]
		for query_id, query_requests in requests.items()
	}


def _progress_diagnostics_to_dict(
	diagnostics: Mapping[str, Sequence[Mapping[str, object]]],
) -> dict[str, list[dict[str, object]]]:
	return {
		query_id: [dict(item) for item in tuple(query_diagnostics or ())]
		for query_id, query_diagnostics in diagnostics.items()
	}


def _inspect_progress_requests_from_initial_state(
	*,
	payload: Mapping[str, Any],
	domain_key: str,
	domain_file: Path,
	declared_predicates: Sequence[object],
) -> tuple[tuple[DFAAchievementRequest, ...], tuple[dict[str, object], ...]]:
	requests: list[DFAAchievementRequest] = []
	diagnostics: list[dict[str, object]] = []
	for transition in progress_transitions_from_dfa_state(
		dfa_payload=payload,
		current_dfa_state=str(payload.get("initial_state") or ""),
	):
		request, diagnostic = _progress_transition_diagnostic(
			transition=transition,
			domain_key=domain_key,
			domain_file=domain_file,
			declared_predicates=declared_predicates,
		)
		if request is not None:
			requests.append(request)
		diagnostics.append(diagnostic)
	return tuple(requests), tuple(diagnostics)


def _progress_transition_diagnostic(
	*,
	transition: Mapping[str, object],
	domain_key: str,
	domain_file: Path,
	declared_predicates: Sequence[object],
) -> tuple[DFAAchievementRequest | None, dict[str, object]]:
	diagnostic = inspect_dfa_guard_to_achievement_request(
		str(transition.get("raw_label") or "true"),
		domain_key=domain_key,
		domain_file=domain_file,
		declared_predicates=declared_predicates,
	)
	request = None
	if diagnostic.request is not None:
		request = DFAAchievementRequest(
			raw_guard=diagnostic.request.raw_guard,
			state_literals=diagnostic.request.state_literals,
			goal_facts=diagnostic.request.goal_facts,
			body_steps=diagnostic.request.body_steps,
			source_state=str(transition.get("source_state") or "").strip() or None,
			target_state=str(transition.get("target_state") or "").strip() or None,
		)
	return request, {
		"source_state": str(transition.get("source_state") or "").strip(),
		"target_state": str(transition.get("target_state") or "").strip(),
		"raw_guard": str(transition.get("raw_label") or "true").strip() or "true",
		"diagnostic": diagnostic.to_dict(),
	}


def _write_json(path: Path, payload: object) -> None:
	path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
