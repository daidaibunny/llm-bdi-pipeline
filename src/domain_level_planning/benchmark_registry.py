"""Class-based benchmark registry for achievement-goal experiments."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ACHIEVEMENT_REGISTRY = (
	PROJECT_ROOT / "src" / "benchmark_registry" / "achievement_goals"
)


@dataclass(frozen=True)
class BenchmarkRecord:
	"""One domain entry in the achievement-goal benchmark registry."""

	path: Path
	payload: dict[str, object]

	@property
	def benchmark_class_id(self) -> str:
		return str(self.payload.get("benchmark_class_id") or "")

	@property
	def domain_id(self) -> str:
		return str(self.payload.get("domain_id") or "")

	@property
	def domain_file(self) -> str | None:
		value = self.payload.get("domain_file")
		if value is None:
			return None
		text = str(value).strip()
		return text or None


@dataclass(frozen=True)
class AchievementBenchmarkRegistry:
	"""Loaded achievement-goal benchmark registry."""

	root: Path
	control: dict[str, object]
	records: tuple[BenchmarkRecord, ...]

	def selected_records(self) -> tuple[BenchmarkRecord, ...]:
		"""Return records that belong to one of the selected paper classes."""

		selected_class_ids = set(
			str(item)
			for item in tuple(self.control.get("selected_domain_class_ids") or ())
		)
		return tuple(
			record
			for record in self.records
			if record.benchmark_class_id in selected_class_ids
			and str(record.payload.get("support_level") or "") in {
				"main_claim",
				"planned_claim_target",
			}
		)

	def runnable_records(self) -> tuple[BenchmarkRecord, ...]:
		"""Return records that already have a local PDDL domain file."""

		return tuple(record for record in self.records if record.domain_file is not None)

	def experiments_for_matrix(
		self,
		matrix: str,
		*,
		output_dir: Path | None = None,
	) -> tuple[dict[str, object], ...]:
		"""Render experiment entries for a final-data matrix."""

		candidates = (
			(record, raw_experiment)
			for record in self.records
			for raw_experiment in _experiments(record)
			if str(raw_experiment.get("matrix") or "") == matrix
		)
		return tuple(
			self._render_experiment(record, raw_experiment, output_dir=output_dir)
			for record, raw_experiment in sorted(candidates, key=_experiment_sort_key)
		)

	def experiments_for_preset(self, preset: str) -> tuple[dict[str, object], ...]:
		"""Render experiment entries for an interactive smoke preset."""

		tags = _preset_tags(self.control, preset)
		candidates = (
			(record, raw_experiment)
			for record in self.records
			for raw_experiment in _experiments(record)
			if str(raw_experiment.get("matrix") or "") == "preset"
			and bool(tags.intersection(_raw_preset_tags(raw_experiment)))
		)
		return tuple(
			self._render_experiment(record, raw_experiment, output_dir=None)
			for record, raw_experiment in sorted(candidates, key=_experiment_sort_key)
		)

	def matrix_name(self, matrix: str) -> str:
		"""Return the configured public name for a final-data matrix."""

		matrix_names = dict(self.control.get("matrix_names") or {})
		return str(matrix_names.get(matrix) or matrix)

	def _render_experiment(
		self,
		record: BenchmarkRecord,
		raw_experiment: Mapping[str, object],
		*,
		output_dir: Path | None,
	) -> dict[str, object]:
		if record.domain_file is None:
			raise ValueError(
				f"Benchmark record {record.domain_id!r} has no domain_file "
				"and cannot render runnable experiments.",
			)
		experiment = dict(raw_experiment)
		rendered: dict[str, object] = {
			"name": str(experiment.pop("name")),
			"domain_file": record.domain_file,
		}
		_apply_problem_set(
			rendered,
			record=record,
			experiment=experiment,
			source_key="train_problem_set",
			target_prefix="train",
		)
		_apply_problem_set(
			rendered,
			record=record,
			experiment=experiment,
			source_key="eval_problem_set",
			target_prefix="eval",
		)
		_apply_problem_set(
			rendered,
			record=record,
			experiment=experiment,
			source_key="counterexample_problem_set",
			target_prefix="counterexample",
		)
		_apply_external_sketch_sources(rendered, record=record, experiment=experiment)
		baseline_group = str(experiment.pop("baseline_group", "") or "")
		if baseline_group:
			if output_dir is None:
				raise ValueError(
					"baseline_group can only be rendered when output_dir is provided.",
				)
			rendered["baseline_json"] = [
				str(_baseline_group_output(record, baseline_group, output_dir=output_dir)),
			]
		for skipped_key in ("matrix", "preset_tags", "order"):
			experiment.pop(skipped_key, None)
		rendered.update(experiment)
		return rendered


def load_achievement_benchmark_registry(
	root: Path = DEFAULT_ACHIEVEMENT_REGISTRY,
) -> AchievementBenchmarkRegistry:
	"""Load the class-based achievement-goal benchmark registry."""

	root = root.expanduser().resolve()
	control_file = root / "registry.json"
	if not control_file.exists():
		raise FileNotFoundError(f"missing achievement benchmark registry: {control_file}")
	control = json.loads(control_file.read_text(encoding="utf-8"))
	records = tuple(
		BenchmarkRecord(
			path=path,
			payload=json.loads(path.read_text(encoding="utf-8")),
		)
		for path in sorted(root.glob("*/*/benchmark.json"))
	)
	_validate_registry(control=control, records=records)
	return AchievementBenchmarkRegistry(root=root, control=control, records=records)


def build_matrix_config_from_registry(
	*,
	matrix: str,
	output_dir: Path,
	registry: AchievementBenchmarkRegistry | None = None,
) -> dict[str, object]:
	"""Build a final-paper matrix config from the benchmark registry."""

	registry = registry or load_achievement_benchmark_registry()
	return {
		"matrix_name": registry.matrix_name(matrix),
		"experiments": list(
			registry.experiments_for_matrix(matrix, output_dir=output_dir),
		),
	}


def build_preset_config_from_registry(
	preset: str,
	*,
	registry: AchievementBenchmarkRegistry | None = None,
) -> dict[str, object]:
	"""Build a smoke matrix preset from the benchmark registry."""

	registry = registry or load_achievement_benchmark_registry()
	return {
		"matrix_name": preset,
		"experiments": list(registry.experiments_for_preset(preset)),
	}


def baseline_group_specs(
	*,
	registry: AchievementBenchmarkRegistry | None = None,
) -> tuple[tuple[BenchmarkRecord, str, dict[str, object]], ...]:
	"""Return all declared baseline group specs."""

	registry = registry or load_achievement_benchmark_registry()
	return tuple(
		(record, name, dict(spec))
		for record in registry.records
		for name, spec in dict(record.payload.get("baseline_groups") or {}).items()
	)


def resolve_problem_set(
	record: BenchmarkRecord,
	name: str,
	*,
	project_root: Path = PROJECT_ROOT,
) -> tuple[Path, ...]:
	"""Resolve one named problem set to concrete files."""

	problem_sets = dict(record.payload.get("problem_sets") or {})
	if name not in problem_sets:
		raise KeyError(
			f"Benchmark record {record.domain_id!r} has no problem set {name!r}.",
		)
	spec = dict(problem_sets[name])
	explicit = tuple(spec.get("problems") or ())
	if explicit:
		return tuple(_resolve_path(path, project_root=project_root) for path in explicit)
	base = _resolve_path(spec.get("base") or ".", project_root=project_root)
	glob_text = str(spec.get("glob") or "").strip()
	if not glob_text:
		raise ValueError(
			f"Problem set {record.domain_id}.{name} must define problems or glob.",
		)
	files = tuple(sorted(base.glob(glob_text)))
	count = spec.get("count")
	if count is not None:
		files = files[: int(count)]
	return files


def resolve_registry_path(value: object, *, project_root: Path = PROJECT_ROOT) -> Path:
	"""Resolve a registry path relative to the project root."""

	return _resolve_path(value, project_root=project_root)


def _validate_registry(
	*,
	control: dict[str, object],
	records: tuple[BenchmarkRecord, ...],
) -> None:
	if int(control.get("schema_version") or 0) != 1:
		raise ValueError("unsupported achievement benchmark registry schema_version")
	if str(control.get("goal_specification_layer") or "") != "achievement_goal_layer":
		raise ValueError("achievement registry must declare achievement_goal_layer")
	selected_class_ids = tuple(control.get("selected_domain_class_ids") or ())
	if not selected_class_ids:
		raise ValueError("achievement registry must declare selected domain classes")
	seen_domain_ids: set[str] = set()
	for record in records:
		if int(record.payload.get("schema_version") or 0) != 1:
			raise ValueError(f"unsupported benchmark schema_version: {record.path}")
		if str(record.payload.get("goal_specification_layer") or "") != (
			"achievement_goal_layer"
		):
			raise ValueError(f"benchmark must use achievement_goal_layer: {record.path}")
		if not record.benchmark_class_id:
			raise ValueError(f"benchmark missing class id: {record.path}")
		if not record.domain_id:
			raise ValueError(f"benchmark missing domain id: {record.path}")
		if record.domain_id in seen_domain_ids:
			raise ValueError(f"duplicate benchmark domain id: {record.domain_id}")
		seen_domain_ids.add(record.domain_id)
		for raw_experiment in _experiments(record):
			_validate_experiment(record, raw_experiment)


def _validate_experiment(
	record: BenchmarkRecord,
	raw_experiment: Mapping[str, object],
) -> None:
	if not str(raw_experiment.get("name") or "").strip():
		raise ValueError(f"experiment missing name: {record.path}")
	if not str(raw_experiment.get("matrix") or "").strip():
		raise ValueError(f"experiment missing matrix: {record.path}")
	if record.domain_file is None:
		raise ValueError(
			f"planned benchmark {record.domain_id!r} cannot declare experiments.",
		)
	for key in ("train_problem_set", "eval_problem_set", "counterexample_problem_set"):
		if key in raw_experiment:
			problem_set = str(raw_experiment[key])
			problem_sets = dict(record.payload.get("problem_sets") or {})
			if problem_set not in problem_sets:
				raise ValueError(
					f"experiment {raw_experiment['name']!r} references missing "
					f"problem set {problem_set!r}.",
				)


def _experiments(record: BenchmarkRecord) -> tuple[dict[str, object], ...]:
	return tuple(dict(item) for item in tuple(record.payload.get("experiments") or ()))


def _raw_preset_tags(raw_experiment: Mapping[str, object]) -> set[str]:
	return set(str(item) for item in tuple(raw_experiment.get("preset_tags") or ()))


def _experiment_sort_key(
	item: tuple[BenchmarkRecord, Mapping[str, object]],
) -> tuple[int, str, str]:
	record, raw_experiment = item
	return (
		int(raw_experiment.get("order") or 10000),
		record.domain_id,
		str(raw_experiment.get("name") or ""),
	)


def _preset_tags(control: Mapping[str, object], preset: str) -> set[str]:
	includes = dict(control.get("preset_includes") or {})
	if preset in includes:
		return set(str(item) for item in tuple(includes[preset] or ()))
	return {preset}


def _apply_problem_set(
	rendered: dict[str, object],
	*,
	record: BenchmarkRecord,
	experiment: dict[str, object],
	source_key: str,
	target_prefix: str,
) -> None:
	problem_set_name = experiment.pop(source_key, None)
	if problem_set_name is None:
		return
	problem_sets = dict(record.payload.get("problem_sets") or {})
	spec = dict(problem_sets[str(problem_set_name)])
	if spec.get("problems"):
		rendered[f"{target_prefix}_problems"] = list(spec["problems"])
		return
	rendered[f"{target_prefix}_base"] = str(spec.get("base") or "")
	rendered[f"{target_prefix}_glob"] = str(spec.get("glob") or "")
	if spec.get("count") is not None:
		rendered[f"{target_prefix}_count"] = int(spec["count"])


def _apply_external_sketch_sources(
	rendered: dict[str, object],
	*,
	record: BenchmarkRecord,
	experiment: dict[str, object],
) -> None:
	source_names = tuple(experiment.pop("external_sketch_source_names", ()) or ())
	if not source_names:
		return
	sources = dict(record.payload.get("external_sketch_sources") or {})
	policies: list[str] = []
	vocabularies: list[str] = []
	for source_name in source_names:
		name = str(source_name)
		source = dict(sources[name])
		policies.append(f"{name}={source['policy_file']}")
		vocabularies.append(f"{name}={source['vocabulary_file']}")
	rendered["external_sketch_policies"] = policies
	rendered["external_sketch_vocabularies"] = vocabularies


def _baseline_group_output(
	record: BenchmarkRecord,
	group_name: str,
	*,
	output_dir: Path,
) -> Path:
	groups = dict(record.payload.get("baseline_groups") or {})
	if group_name not in groups:
		raise KeyError(
			f"Benchmark record {record.domain_id!r} has no baseline group "
			f"{group_name!r}.",
		)
	group = dict(groups[group_name])
	return output_dir / "baselines" / str(group["output_file"])


def _resolve_path(value: object, *, project_root: Path) -> Path:
	path = Path(str(value)).expanduser()
	if path.is_absolute():
		return path
	return (project_root / path).resolve()
