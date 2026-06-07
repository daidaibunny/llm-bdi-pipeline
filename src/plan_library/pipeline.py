"""
DFA-driven plan-library generation pipeline.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from domain_model import infer_query_domain, load_query_sequence_records
from evaluation.temporal_compilation import DFABuilder
from low_level_planning import (
	FastDownwardPlannerConfig,
	FastDownwardTransitionPlanner,
	TransitionPlanningRequest,
)
from plan_library.dfa_high_level import (
	LowLevelPlanningRequest,
	LowLevelPlanningResponse,
	build_high_level_plan_library,
)
from utils.pddl_parser import PDDLParser

from .artifacts import (
	PlanLibraryArtifactBundle,
	persist_plan_library_artifact_bundle,
)
from .models import PlanGenerationSummary
from .rendering import render_plan_library_asl
from .set_semantics import deduplicate_plan_library
from .validation import build_library_validation_record


class PlanLibraryGenerationPipeline:
	"""Generate a high-level AgentSpeak(L) plan library from stored LTLf specifications."""

	def __init__(
		self,
		*,
		domain_file: str,
		query_dataset: str | None = None,
		query_domain: str | None = None,
		query_ids: Sequence[str] | None = None,
		dfa_builder: DFABuilder | None = None,
		fast_downward_executable: str | None = None,
		enable_low_level_planning: bool = True,
		render_primitive_actions: bool = True,
	) -> None:
		self.project_root = Path(__file__).resolve().parents[2]
		self.domain_file = str(Path(domain_file).expanduser().resolve())
		self.domain = PDDLParser.parse_domain(self.domain_file)
		self._query_dataset = query_dataset
		self._query_domain = query_domain
		self._query_ids = tuple(
			query_id_text
			for query_id_text in (str(query_id or "").strip() for query_id in (query_ids or ()))
			if query_id_text
		)
		self._dfa_builder = dfa_builder or DFABuilder()
		self._fast_downward_executable = fast_downward_executable
		self._enable_low_level_planning = enable_low_level_planning
		self._render_primitive_actions = render_primitive_actions

	def build_library_bundle(
		self,
		*,
		output_root: Optional[str] = None,
	) -> Dict[str, Any]:
		"""Build and persist the DFA-driven high-level plan library."""

		start_time = time.perf_counter()
		query_sequence, temporal_specifications = load_query_sequence_records(
			domain_file=self.domain_file,
			dataset_path=self._query_dataset,
			query_domain=self._query_domain,
			query_ids=self._query_ids,
		)
		query_domain = infer_query_domain(
			domain_file=self.domain_file,
			explicit_domain=self._query_domain,
		)
		artifact_root = (
			Path(output_root).expanduser().resolve()
			if output_root is not None
			else self._default_artifact_root(query_domain)
		)

		try:
			dfa_payloads: Dict[str, Dict[str, Any]] = {}
			for record in temporal_specifications:
				dfa_payloads[record.instruction_id] = self._dfa_builder.build(record)

			low_level_planners = self._build_low_level_planners(
				query_domain=query_domain,
				temporal_specifications=temporal_specifications,
				artifact_root=artifact_root,
			)
			plan_library = build_high_level_plan_library(
				domain_key=query_domain,
				domain_name=self.domain.name,
				dfa_payloads=dfa_payloads,
				low_level_planners=low_level_planners,
			)
			set_result = deduplicate_plan_library(plan_library)
			plan_library = set_result.plan_library
			plan_library_asl = render_plan_library_asl(plan_library)
			generation_summary = PlanGenerationSummary(
				domain_name=self.domain.name,
				dfa_count=len(dfa_payloads),
				transition_count=sum(
					len(tuple(payload.get("guarded_transitions") or ()))
					for payload in dfa_payloads.values()
				),
				plans_generated=len(tuple(plan_library.plans or ())),
				initial_belief_count=len(tuple(plan_library.initial_beliefs or ())),
				metadata={
					"query_domain": query_domain,
					"removed_duplicate_plans": set_result.removed_duplicate_plans,
					"renamed_plans": set_result.renamed_plans,
					"elapsed_seconds": time.perf_counter() - start_time,
				},
			)
			library_validation = build_library_validation_record(
				domain_name=self.domain.name,
				plan_library=plan_library,
				generation_summary=generation_summary,
			)
			if not library_validation.passed:
				raise RuntimeError(library_validation.failure_reason or "Library validation failed.")

			bundle = PlanLibraryArtifactBundle(
				domain_name=self.domain.name,
				query_sequence=query_sequence,
				temporal_specifications=temporal_specifications,
				plan_library=plan_library,
				generation_summary=generation_summary,
				library_validation=library_validation,
				dfa_metadata=dfa_payloads,
				artifact_root=str(artifact_root),
				plan_library_asl_file=str(artifact_root / "plan_library.asl"),
			)
			artifact_paths = persist_plan_library_artifact_bundle(
				artifact_root=artifact_root,
				artifact=bundle,
				plan_library_asl_text=plan_library_asl,
			)
			artifact_summary = _artifact_summary(bundle, artifact_paths)
			return {
				"success": True,
				"artifact": artifact_summary,
				"artifact_summary": artifact_summary,
				"artifact_paths": artifact_paths,
			}
		except Exception as exc:
			return {
				"success": False,
				"error": str(exc),
			}

	def _default_artifact_root(self, query_domain: str) -> Path:
		artifact_root = (
			self.project_root
			/ "artifacts"
			/ "plan_library"
			/ query_domain
		)
		if self._query_ids:
			return artifact_root / self._query_selection_artifact_slug()
		return artifact_root

	def _query_selection_artifact_slug(self) -> str:
		if not self._query_ids:
			return ""
		if len(self._query_ids) == 1:
			return _artifact_slug(self._query_ids[0])
		selection_key = "_".join(_artifact_slug(query_id) for query_id in self._query_ids[:5])
		if len(self._query_ids) > 5:
			selection_key = f"{selection_key}_plus_{len(self._query_ids) - 5}"
		return selection_key or "selected_queries"

	def _build_low_level_planners(
		self,
		*,
		query_domain: str,
		temporal_specifications: Sequence[Any],
		artifact_root: Path,
	) -> Dict[str, Any]:
		if not self._enable_low_level_planning:
			return {}
		transition_planner = FastDownwardTransitionPlanner(
			config=FastDownwardPlannerConfig(executable=self._fast_downward_executable),
			render_primitive_actions=self._render_primitive_actions,
		)
		planners: Dict[str, Any] = {}
		for record in temporal_specifications:
			problem_file = self._resolve_problem_file(
				query_domain=query_domain,
				problem_file=getattr(record, "problem_file", None),
			)
			work_dir = artifact_root / "low_level" / str(record.instruction_id)

			def _planner(
				request: LowLevelPlanningRequest,
				*,
				problem_file: Path = problem_file,
				work_dir: Path = work_dir,
			) -> LowLevelPlanningResponse:
				result = transition_planner.plan_transition(
					TransitionPlanningRequest(
						plan_name=request.plan_name,
						domain_file=self.domain_file,
						problem_file=str(problem_file),
						target_context=request.target_context,
						source_context=request.source_context,
						cumulative_context=request.cumulative_context,
						work_dir=str(work_dir),
					),
				)
				return LowLevelPlanningResponse(
					body_steps=result.body_steps,
					certificate=result.certificate,
					warnings=result.warnings,
				)

			planners[str(record.instruction_id)] = _planner
		return planners

	def _resolve_problem_file(self, *, query_domain: str, problem_file: str | None) -> Path:
		if not str(problem_file or "").strip():
			raise ValueError("Low-level planning requires each query to declare a problem_file.")
		problem_path = Path(str(problem_file).strip()).expanduser()
		if problem_path.is_absolute() and problem_path.exists():
			return problem_path.resolve()
		domain_dir = self.project_root / "src" / "domains" / query_domain
		domain_file_parent = Path(self.domain_file).resolve().parent
		candidates = (
			domain_file_parent / "problems" / str(problem_file).strip(),
			domain_file_parent / str(problem_file).strip(),
			domain_dir / "problems" / str(problem_file).strip(),
			domain_dir / str(problem_file).strip(),
		)
		for candidate in candidates:
			if candidate.exists():
				return candidate.resolve()
		raise FileNotFoundError(f"Could not resolve PDDL problem file: {problem_file}")


def _artifact_slug(value: str) -> str:
	text = str(value or "").strip().lower()
	buffer = [character if character.isalnum() else "_" for character in text]
	slug = "".join(buffer).strip("_")
	while "__" in slug:
		slug = slug.replace("__", "_")
	return slug or "query"


def _artifact_summary(
	bundle: PlanLibraryArtifactBundle,
	artifact_paths: Dict[str, str],
) -> Dict[str, Any]:
	return {
		"domain_name": bundle.domain_name,
		"query_count": len(tuple(bundle.query_sequence or ())),
		"temporal_specification_count": len(tuple(bundle.temporal_specifications or ())),
		"dfa_count": bundle.generation_summary.dfa_count,
		"transition_count": bundle.generation_summary.transition_count,
		"plan_count": len(tuple(bundle.plan_library.plans or ())),
		"generation_summary": bundle.generation_summary.to_dict(),
		"library_validation": bundle.library_validation.to_dict(),
		"artifact_root": bundle.artifact_root,
		"plan_library_file": artifact_paths.get("plan_library"),
		"plan_library_asl_file": artifact_paths.get("plan_library_asl"),
		"dfa_metadata_file": artifact_paths.get("dfa_metadata"),
		"generation_summary_file": artifact_paths.get("generation_summary"),
	}
