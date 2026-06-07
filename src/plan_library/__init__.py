"""
Plan-library exports for the dissertation workflow.

Keep package import side effects minimal so stage modules can import
plan-library types without triggering the full generation pipeline.
"""

from __future__ import annotations

from typing import Any

__all__ = [
	"AgentSpeakBodyStep",
	"AgentSpeakPlan",
	"AgentSpeakTrigger",
	"LibraryValidationRecord",
	"PlanGenerationSummary",
	"PlanLibrary",
	"PlanLibraryArtifactBundle",
	"PlanLibraryGenerationPipeline",
	"PlanLibrarySetResult",
	"build_high_level_plan_library",
	"build_high_level_plan_library_from_dfa",
	"build_library_validation_record",
	"deduplicate_plan_library",
	"load_plan_library_artifact_bundle",
	"persist_plan_library_artifact_bundle",
	"plan_fingerprint",
	"render_plan_library_asl",
]


def __getattr__(name: str) -> Any:
	if name in {
		"PlanLibraryArtifactBundle",
		"load_plan_library_artifact_bundle",
		"persist_plan_library_artifact_bundle",
	}:
		from .artifacts import (
			PlanLibraryArtifactBundle,
			load_plan_library_artifact_bundle,
			persist_plan_library_artifact_bundle,
		)

		return {
			"PlanLibraryArtifactBundle": PlanLibraryArtifactBundle,
			"load_plan_library_artifact_bundle": load_plan_library_artifact_bundle,
			"persist_plan_library_artifact_bundle": persist_plan_library_artifact_bundle,
		}[name]
	if name in {
		"AgentSpeakBodyStep",
		"AgentSpeakPlan",
		"AgentSpeakTrigger",
		"LibraryValidationRecord",
		"PlanGenerationSummary",
		"PlanLibrary",
	}:
		from .models import (
			AgentSpeakBodyStep,
			AgentSpeakPlan,
			AgentSpeakTrigger,
			LibraryValidationRecord,
			PlanGenerationSummary,
			PlanLibrary,
		)

		return {
			"AgentSpeakBodyStep": AgentSpeakBodyStep,
			"AgentSpeakPlan": AgentSpeakPlan,
			"AgentSpeakTrigger": AgentSpeakTrigger,
			"LibraryValidationRecord": LibraryValidationRecord,
			"PlanGenerationSummary": PlanGenerationSummary,
			"PlanLibrary": PlanLibrary,
		}[name]
	if name == "PlanLibraryGenerationPipeline":
		from .pipeline import PlanLibraryGenerationPipeline

		return PlanLibraryGenerationPipeline
	if name in {"build_high_level_plan_library", "build_high_level_plan_library_from_dfa"}:
		from .dfa_high_level import (
			build_high_level_plan_library,
			build_high_level_plan_library_from_dfa,
		)

		return {
			"build_high_level_plan_library": build_high_level_plan_library,
			"build_high_level_plan_library_from_dfa": build_high_level_plan_library_from_dfa,
		}[name]
	if name == "render_plan_library_asl":
		from .rendering import render_plan_library_asl

		return render_plan_library_asl
	if name == "build_library_validation_record":
		from .validation import build_library_validation_record

		return build_library_validation_record
	if name in {"PlanLibrarySetResult", "deduplicate_plan_library", "plan_fingerprint"}:
		from .set_semantics import (
			PlanLibrarySetResult,
			deduplicate_plan_library,
			plan_fingerprint,
		)

		return {
			"PlanLibrarySetResult": PlanLibrarySetResult,
			"deduplicate_plan_library": deduplicate_plan_library,
			"plan_fingerprint": plan_fingerprint,
		}[name]
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
