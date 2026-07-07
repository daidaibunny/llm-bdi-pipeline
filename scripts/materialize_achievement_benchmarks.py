#!/usr/bin/env python3
"""Materialize the selected achievement-goal benchmark corpus."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
import shutil
import subprocess
from fnmatch import fnmatch
from typing import NamedTuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOMAINS_ROOT = PROJECT_ROOT / "src" / "domains"
REGISTRY_ROOT = PROJECT_ROOT / "src" / "benchmark_registry" / "achievement_goals"
PDDL_INSTANCE_CACHE_ROOT = (
	PROJECT_ROOT / ".external" / "benchmark-sources" / "pddl-instances-cache"
)
STRUCTURAL_TRAIN_RATIO = 1 / 4


class SourceSpec(NamedTuple):
	source_id: str
	name: str
	url: str
	local_root: Path
	commit: str
	coverage: str


class DomainSpec(NamedTuple):
	domain_id: str
	source_id: str
	source_path: str
	benchmark_property_group_id: str
	display_name: str
	ipc_year: str
	ipc_variant: str
	problem_globs: tuple[str, ...]
	source_domain_file: str = "domain.pddl"
	split_strategy: str = "ratio"
	train_ratio: float = 2 / 3
	split_policy: str = "floor(2/3 * instance_count) train, remaining test"
	test_source_path: str | None = None
	test_problem_globs: tuple[str, ...] = ()


SOURCES: dict[str, SourceSpec] = {
	"pddl_instances": SourceSpec(
		"pddl_instances",
		"potassco/pddl-instances",
		"https://github.com/potassco/pddl-instances",
		PROJECT_ROOT / ".external" / "benchmark-sources" / "pddl-instances",
		"cf19edf7c53d1540ddbb396c642595e0926ee552",
		"IPC benchmark directories used for standard classical PDDL domains",
	),
	"moose_dataset": SourceSpec(
		"moose_dataset",
		"DillonZChen/moose-dataset",
		"https://github.com/DillonZChen/moose-dataset",
		PROJECT_ROOT / ".external" / "moose-dataset",
		"e00970516154e9042b783a4613a1ed7286c9beee",
		"MOOSE companion benchmark families with official train/test splits",
	),
	"kr2025_policies": SourceSpec(
		"kr2025_policies",
		"bonetblai/learner-policies-from-examples",
		"https://github.com/bonetblai/learner-policies-from-examples",
		PROJECT_ROOT
		/ ".external"
		/ "gp-backends"
		/ "learner-policies-from-examples",
		"9991926f7655c4b6c8dc2f0404123639e42056f2",
		"KR 2025 feature-policy benchmark families",
	),
	"d2l": SourceSpec(
		"d2l",
		"rleap-project/d2l",
		"https://github.com/rleap-project/d2l",
		PROJECT_ROOT / ".external" / "gp-backends" / "d2l",
		"0620e169c894d79b3c84f435dba1462996f7c270",
		"D2L benchmark domains used as reputable GP-family PDDL sources",
	),
}


def main() -> None:
	"""Regenerate local IPC PDDL snapshots and the achievement registry."""

	specs = _domain_specs()
	_validate_source(specs)
	_reset_directory(DOMAINS_ROOT)
	for spec in specs:
		_materialize_domain(spec)
	_write_registry(specs)
	print(f"materialized {len(specs)} selected achievement benchmark domains")


def _validate_source(specs: tuple[DomainSpec, ...]) -> None:
	used_source_ids = {spec.source_id for spec in specs}
	for source in SOURCES.values():
		if source.source_id not in used_source_ids:
			continue
		if not source.local_root.exists():
			raise FileNotFoundError(
				f"missing benchmark source {source.local_root}; clone {source.name} first",
			)
		head = subprocess.check_output(
			("git", "-C", str(source.local_root), "rev-parse", "HEAD"),
			text=True,
		).strip()
		if head != source.commit:
			raise RuntimeError(
				f"unexpected {source.name} commit {head}; expected {source.commit}",
			)


def _reset_directory(path: Path) -> None:
	if path.exists():
		shutil.rmtree(path)
	path.mkdir(parents=True)


def _domain_specs() -> tuple[DomainSpec, ...]:
	moose_split_policy = (
		"MOOSE official artifact split: training/ as train and testing/ as test"
	)
	return (
		_moose_domain_spec(
			"ferry",
			"esho_classical_domains",
			"Ferry",
			"ferry",
			moose_split_policy,
		),
		_moose_domain_spec(
			"gripper",
			"esho_classical_domains",
			"Gripper",
			"gripper",
			moose_split_policy,
		),
		_moose_domain_spec(
			"logistics",
			"esho_classical_domains",
			"Logistics",
			"logistics",
			moose_split_policy,
		),
		_moose_domain_spec(
			"miconic",
			"esho_classical_domains",
			"Miconic",
			"miconic",
			moose_split_policy,
		),
		_moose_domain_spec(
			"transport",
			"esho_classical_domains",
			"Transport",
			"transport",
			moose_split_policy,
		),
		_moose_domain_spec(
			"barman",
			"esho_classical_domains",
			"Barman",
			"barman",
			moose_split_policy,
		),
		_moose_domain_spec(
			"rovers",
			"esho_classical_domains",
			"Rovers",
			"rovers",
			moose_split_policy,
		),
		_moose_domain_spec(
			"satellite",
			"esho_classical_domains",
			"Satellite",
			"satellite",
			moose_split_policy,
		),
		_moose_domain_spec(
			"numeric-ferry",
			"numeric_fluent_domains",
			"Numeric Ferry",
			"numeric-ferry",
			moose_split_policy,
		),
		_moose_domain_spec(
			"numeric-miconic",
			"numeric_fluent_domains",
			"Numeric Miconic",
			"numeric-miconic",
			moose_split_policy,
		),
		_moose_domain_spec(
			"numeric-minecraft",
			"numeric_fluent_domains",
			"Numeric Minecraft",
			"numeric-minecraft",
			moose_split_policy,
		),
		_moose_domain_spec(
			"numeric-transport",
			"numeric_fluent_domains",
			"Numeric Transport",
			"numeric-transport",
			moose_split_policy,
		),
		_kr2025_blocksworld_singleton_spec(
			"blocksworld-clear",
			"Blocksworld Clear",
			"blocks_4_clear_no_constants",
			"QClear Blocksworld family: official no-constants train/test split "
			"from the KR 2025 learner-policies benchmark",
		),
		_kr2025_blocksworld_singleton_spec(
			"blocksworld-on",
			"Blocksworld On",
			"blocks_4_on_no_constants",
			"QOn Blocksworld family: official no-constants train/test split "
			"from the KR 2025 learner-policies benchmark",
		),
		DomainSpec(
			"blocksworld-tower",
			"pddl_instances",
			"ipc-2000/domains/blocks-strips-typed",
			"feature_definable_serialized_width_domains",
			"Blocksworld Tower",
			"2000",
			"blocks-strips-typed",
			("instances/*.pddl",),
			train_ratio=STRUCTURAL_TRAIN_RATIO,
			split_policy=(
				"floor(1/4 * instance_count) train for feature-definable "
				"serialized-width tower-construction policy audit, remaining test"
			),
		),
		DomainSpec(
			"depots",
			"d2l",
			"domains/depot",
			"feature_definable_serialized_width_domains",
			"Depots",
			"D2L",
			"depot",
			("p*.pddl",),
			train_ratio=STRUCTURAL_TRAIN_RATIO,
			split_policy=(
				"floor(1/4 * instance_count) train for feature-definable "
				"serialized-width policy audit, remaining test"
			),
		),
	)


def _kr2025_blocksworld_singleton_spec(
	domain_id: str,
	display_name: str,
	family_name: str,
	split_policy: str,
) -> DomainSpec:
	return DomainSpec(
		domain_id,
		"kr2025_policies",
		f"learning/benchmarks/tractable/{family_name}",
		"feature_definable_serialized_width_domains",
		display_name,
		"KR 2025",
		family_name,
		("training/easy/*.pddl",),
		split_strategy="paired_source_directories",
		split_policy=split_policy,
		test_source_path=f"testing/benchmarks/{family_name}",
		test_problem_globs=("*.pddl",),
	)


def _moose_domain_spec(
	domain_id: str,
	benchmark_property_group_id: str,
	display_name: str,
	ipc_variant: str,
	split_policy: str,
) -> DomainSpec:
	return DomainSpec(
		domain_id,
		"moose_dataset",
		domain_id,
		benchmark_property_group_id,
		display_name,
		"MOOSE 2026",
		ipc_variant,
		("training/*.pddl", "testing/*.pddl"),
		split_strategy="source_directories",
		split_policy=split_policy,
	)


def _materialize_domain(spec: DomainSpec) -> None:
	domain_root = DOMAINS_ROOT / spec.domain_id
	train_root = domain_root / "train"
	test_root = domain_root / "test"
	train_root.mkdir(parents=True)
	test_root.mkdir(parents=True)
	problem_paths = _source_problem_paths(spec)
	if not problem_paths:
		raise RuntimeError(
			f"{spec.domain_id} has no benchmark instances in {spec.source_path}",
		)
	_copy_source_file(spec, spec.source_domain_file, domain_root / "domain.pddl")
	train_paths, test_paths = _split_problem_paths(spec, problem_paths)
	for source_problem in train_paths:
		_copy_source_file(spec, source_problem, train_root / Path(source_problem).name)
	for source_problem in test_paths:
		_copy_source_file(spec, source_problem, test_root / Path(source_problem).name)
	source = SOURCES[spec.source_id]
	source_record = {
		"source": source.name,
		"source_id": source.source_id,
		"source_url": source.url,
		"source_commit": source.commit,
		"source_path": spec.source_path,
		"test_source_path": spec.test_source_path,
		"source_domain_file": f"{spec.source_path}/{spec.source_domain_file}",
		"source_problem_globs": list(spec.problem_globs),
		"test_source_problem_globs": list(spec.test_problem_globs),
		"ipc_year": spec.ipc_year,
		"ipc_variant": spec.ipc_variant,
		"instance_count": len(problem_paths),
		"train_count": len(train_paths),
		"test_count": len(test_paths),
		"split_policy": spec.split_policy,
	}
	(domain_root / "source.json").write_text(
		json.dumps(source_record, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def _split_problem_paths(
	spec: DomainSpec,
	problem_paths: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
	if spec.split_strategy == "source_directories":
		train_paths = tuple(path for path in problem_paths if path.startswith("training/"))
		test_paths = tuple(path for path in problem_paths if path.startswith("testing/"))
		if not train_paths or not test_paths:
			raise RuntimeError(
				f"{spec.domain_id} expects source training/ and testing/ directories",
			)
		return train_paths, test_paths
	if spec.split_strategy == "paired_source_directories":
		train_paths = tuple(path for path in problem_paths if path.startswith("training/"))
		test_paths = tuple(path for path in problem_paths if path.startswith("testing/"))
		if not train_paths or not test_paths:
			raise RuntimeError(
				f"{spec.domain_id} expects paired source training/ and testing/ data",
			)
		return train_paths, test_paths
	if spec.split_strategy == "ratio":
		split = math.floor(len(problem_paths) * spec.train_ratio)
		return problem_paths[:split], problem_paths[split:]
	raise ValueError(f"unknown split strategy {spec.split_strategy!r}")


def _source_problem_paths(spec: DomainSpec) -> tuple[str, ...]:
	if spec.split_strategy == "paired_source_directories":
		if spec.test_source_path is None:
			raise RuntimeError(f"{spec.domain_id} is missing test_source_path")
		train_paths = _source_problem_paths_under(
			spec.source_id,
			spec.source_path,
			spec.problem_globs,
			spec.source_domain_file,
		)
		test_paths = _source_problem_paths_under(
			spec.source_id,
			spec.test_source_path,
			spec.test_problem_globs,
			spec.source_domain_file,
		)
		return tuple(
			str(Path("training") / path)
			if not str(path).startswith("training/")
			else str(path)
			for path in train_paths
		) + tuple(str(Path("testing") / path) for path in test_paths)
	return _source_problem_paths_under(
		spec.source_id,
		spec.source_path,
		spec.problem_globs,
		spec.source_domain_file,
	)


def _source_problem_paths_under(
	source_id: str,
	source_path: str,
	problem_globs: tuple[str, ...],
	source_domain_file: str,
) -> tuple[str, ...]:
	output = subprocess.check_output(
		(
			"git",
			"-C",
			str(SOURCES[source_id].local_root),
			"ls-tree",
			"-r",
			"--name-only",
			f"HEAD:{source_path}",
		),
		text=True,
	)
	paths: list[Path] = []
	source_paths = tuple(
		line
		for line in output.splitlines()
		if line.endswith(".pddl") and Path(line).name != source_domain_file
	)
	for glob_text in problem_globs:
		paths.extend(
			Path(path)
			for path in source_paths
			if fnmatch(path, glob_text)
		)
	return tuple(str(path) for path in sorted(paths, key=_instance_sort_key))


def _instance_sort_key(path: str | Path) -> tuple[tuple[int, ...], str]:
	text = str(path)
	numbers = tuple(int(item) for item in re.findall(r"\d+", text))
	return (numbers or (10**9,), text)


def _copy_source_file(spec: DomainSpec, relative_path: str, target_path: Path) -> None:
	content = _read_source_file(spec, relative_path)
	_write_pddl_snapshot(content, target_path)


def _read_source_file(spec: DomainSpec, relative_path: str) -> bytes:
	source = SOURCES[spec.source_id]
	source_path = spec.source_path
	source_relative_path = relative_path
	if relative_path.startswith("testing/") and spec.test_source_path is not None:
		source_path = spec.test_source_path
		source_relative_path = relative_path.removeprefix("testing/")
	full_path = f"{source_path}/{source_relative_path}"
	cache_path = PDDL_INSTANCE_CACHE_ROOT / source.commit / full_path
	if source.source_id == "pddl_instances" and cache_path.exists():
		return cache_path.read_bytes()
	return subprocess.check_output(
		(
			"git",
			"-C",
			str(source.local_root),
			"show",
			f"HEAD:{full_path}",
		),
	)


def _write_pddl_snapshot(content: bytes, target_path: Path) -> None:
	text = content.decode("utf-8")
	lines = [
		line.replace("\t", "  ").rstrip()
		for line in text.replace("\r\n", "\n").split("\n")
	]
	target_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _benchmark_sources_payload(specs: tuple[DomainSpec, ...]) -> tuple[dict[str, str], ...]:
	used_source_ids = {spec.source_id for spec in specs}
	return tuple(
		{
			"id": source.source_id,
			"name": source.name,
			"url": source.url,
			"commit": source.commit,
			"coverage": source.coverage,
		}
		for source in SOURCES.values()
		if source.source_id in used_source_ids
	)


def _write_registry(specs: tuple[DomainSpec, ...]) -> None:
	_reset_directory(REGISTRY_ROOT)
	(REGISTRY_ROOT / "registry.json").write_text(
		json.dumps(
			{
				"schema_version": 1,
				"goal_specification_layer": "achievement_goal_layer",
				"future_goal_specification_layers": ["temporal_extended_goal_layer"],
				"selected_domain_ids": [spec.domain_id for spec in specs],
				"selected_benchmark_property_group_ids": [
					"esho_classical_domains",
					"numeric_fluent_domains",
					"feature_definable_serialized_width_domains",
				],
				"matrix_names": {
					"main": "paper-final-main-library",
					"ablation": "paper-final-ablations",
					"limitation": "paper-final-limitations",
				},
				"preset_includes": {
					"current-minimum": ["current-minimum"],
					"paper-diagnostic-smoke": [
						"current-minimum",
						"paper-diagnostic-smoke",
					],
					"paper-expanded-smoke": [
						"current-minimum",
						"paper-diagnostic-smoke",
						"paper-expanded-smoke",
					],
				},
				"scope": "positive_conjunctive_or_numeric_achievement_goals",
				"benchmark_source": {
					"name": "selected reputable generalized-planning benchmark sources",
					"coverage": (
						"all MOOSE direct train/test benchmark domains plus "
						"project-added feature-definable serialized-width benchmarks"
					),
				},
				"benchmark_sources": _benchmark_sources_payload(specs),
			},
			indent=2,
			sort_keys=True,
		)
		+ "\n",
		encoding="utf-8",
	)
	for spec in specs:
		record_dir = REGISTRY_ROOT / spec.benchmark_property_group_id / spec.domain_id
		record_dir.mkdir(parents=True)
		problem_paths = _local_problem_paths(spec.domain_id)
		train_paths = tuple(path for path in problem_paths if "/train/" in path)
		test_paths = tuple(path for path in problem_paths if "/test/" in path)
		payload = {
			"schema_version": 1,
			"goal_specification_layer": "achievement_goal_layer",
			"benchmark_property_group_id": spec.benchmark_property_group_id,
			"domain_id": spec.domain_id,
			"display_name": spec.display_name,
			"domain_role": "main_claim",
			"support_level": "main_claim",
			"target_paper_domains": [spec.domain_id],
			"domain_file": f"src/domains/{spec.domain_id}/domain.pddl",
			"problem_sets": {
				"train": {
					"base": f"src/domains/{spec.domain_id}/train",
					"glob": "*.pddl",
				},
				"goal_specification": {
					"base": f"src/domains/{spec.domain_id}/test",
					"glob": "*.pddl",
				},
				"all": {
					"problems": list(problem_paths),
				},
			},
			"source": {
				"name": SOURCES[spec.source_id].name,
				"id": SOURCES[spec.source_id].source_id,
				"url": SOURCES[spec.source_id].url,
				"commit": SOURCES[spec.source_id].commit,
				"source_path": spec.source_path,
				"test_source_path": spec.test_source_path,
				"source_domain_file": f"{spec.source_path}/{spec.source_domain_file}",
				"source_problem_globs": list(spec.problem_globs),
				"test_source_problem_globs": list(spec.test_problem_globs),
				"ipc_year": spec.ipc_year,
				"ipc_variant": spec.ipc_variant,
				"instance_count": len(problem_paths),
				"train_count": len(train_paths),
				"test_count": len(test_paths),
				"split_policy": spec.split_policy,
			},
			"baseline_groups": {},
			"experiments": [
				{
					"name": f"{spec.domain_id}-atomic-backend-smoke",
					"order": 100,
					"matrix": "preset",
					"preset_tags": ["paper-expanded-smoke"],
					"train_problem_set": "train",
					"eval_problem_set": "goal_specification",
					"artifact_kind": "atomic_template_library_candidate",
					"primary_atomic_backend": "moose",
					"backend_artifact_gate": [
						"parse",
						"LiftedPolicyProgram",
						"atomic_asl_compile",
						"held_out_validation",
					],
					"runtime_full_trace_planner": False,
					"timeout_seconds": 1800,
					"evaluation_timeout_seconds": 15,
					"ablation_label": f"{spec.domain_id}_atomic_backend_smoke",
				},
				{
					"name": f"{spec.domain_id}-atomic-backend-main",
					"order": 100,
					"matrix": "main",
					"train_problem_set": "train",
					"eval_problem_set": "goal_specification",
					"artifact_kind": "atomic_template_library_candidate",
					"primary_atomic_backend": "moose",
					"backend_artifact_gate": [
						"parse",
						"LiftedPolicyProgram",
						"atomic_asl_compile",
						"held_out_validation",
					],
					"runtime_full_trace_planner": False,
					"timeout_seconds": 1800,
					"evaluation_timeout_seconds": 15,
					"ablation_label": f"{spec.domain_id}_atomic_backend_main",
				},
			],
		}
		(record_dir / "benchmark.json").write_text(
			json.dumps(payload, indent=2, sort_keys=True) + "\n",
			encoding="utf-8",
		)


def _local_problem_paths(domain_id: str) -> tuple[str, ...]:
	domain_root = DOMAINS_ROOT / domain_id
	paths = tuple(sorted((domain_root / "train").glob("*.pddl"), key=_local_instance_key)) + tuple(
		sorted((domain_root / "test").glob("*.pddl"), key=_local_instance_key),
	)
	return tuple(str(path.relative_to(PROJECT_ROOT)) for path in paths)


def _local_instance_key(path: Path) -> tuple[int, str]:
	return _instance_sort_key(path.name)


if __name__ == "__main__":
	main()
