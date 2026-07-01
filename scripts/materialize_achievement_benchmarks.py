#!/usr/bin/env python3
"""Materialize the routed achievement-goal benchmark corpus."""

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
TRAIN_RATIO = 2 / 3


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
	benchmark_class_id: str
	display_name: str
	ipc_year: str
	ipc_variant: str
	problem_globs: tuple[str, ...]
	source_domain_file: str = "domain.pddl"


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
		"MOOSE goal-regression benchmark families",
	),
	"learner_sketches": SourceSpec(
		"learner_sketches",
		"bonetblai/learner-sketches",
		"https://github.com/bonetblai/learner-sketches",
		PROJECT_ROOT / ".external" / "gp-backends" / "learner-sketches",
		"7a7ea6a6356035afa16ed958b53d8edc86994e0a",
		"learned-sketch benchmark and testing families",
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
}


def main() -> None:
	"""Regenerate local IPC PDDL snapshots and the achievement registry."""

	_validate_source()
	_reset_directory(DOMAINS_ROOT)
	specs = _domain_specs()
	for spec in specs:
		_materialize_domain(spec)
	_write_registry(specs)
	print(f"materialized {len(specs)} routed achievement benchmark domains")


def _validate_source() -> None:
	for source in SOURCES.values():
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
	return (
		DomainSpec(
			"gripper",
			"pddl_instances",
			"ipc-1998/domains/gripper-round-1-strips",
			"goal_separable_serialisable_achievement_classes",
			"Gripper",
			"1998",
			"gripper-round-1-strips",
			("instances/*.pddl",),
		),
		DomainSpec(
			"ferry",
			"moose_dataset",
			"ferry",
			"goal_separable_serialisable_achievement_classes",
			"Ferry",
			"MOOSE 2026",
			"ferry",
			("training/*.pddl", "testing/*.pddl"),
		),
		DomainSpec(
			"miconic",
			"pddl_instances",
			"ipc-2000/domains/elevator-strips-simple-typed",
			"goal_separable_serialisable_achievement_classes",
			"Miconic",
			"2000",
			"elevator-strips-simple-typed",
			("instances/*.pddl",),
		),
		DomainSpec(
			"logistics",
			"pddl_instances",
			"ipc-2000/domains/logistics-strips-typed",
			"goal_separable_serialisable_achievement_classes",
			"Logistics",
			"2000",
			"logistics-strips-typed",
			("instances/*.pddl",),
		),
		DomainSpec(
			"barman",
			"pddl_instances",
			"ipc-2011/domains/barman-sequential-satisficing",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Barman",
			"2011",
			"barman-sequential-satisficing",
			("instances/*.pddl",),
		),
		DomainSpec(
			"childsnack",
			"pddl_instances",
			"ipc-2014/domains/child-snack-sequential-satisficing",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Childsnack",
			"2014",
			"child-snack-sequential-satisficing",
			("instances/*.pddl",),
		),
		DomainSpec(
			"visitall",
			"pddl_instances",
			"ipc-2011/domains/visit-all-sequential-satisficing",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Visitall",
			"2011",
			"visit-all-sequential-satisficing",
			("instances/*.pddl",),
		),
		DomainSpec(
			"delivery",
			"learner_sketches",
			"testing/benchmarks/delivery",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Delivery",
			"learner-sketches",
			"delivery-testing-benchmark",
			("*.pddl",),
		),
		DomainSpec(
			"spanner",
			"learner_sketches",
			"testing/benchmarks/spanner",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Spanner",
			"learner-sketches",
			"spanner-testing-benchmark",
			("*.pddl",),
		),
		DomainSpec(
			"blocks",
			"pddl_instances",
			"ipc-2000/domains/blocks-strips-typed",
			"feature_definable_goal_dependent_construction_classes",
			"Blocks",
			"2000",
			"blocks-strips-typed",
			("instances/*.pddl",),
		),
		DomainSpec(
			"8puzzle-1tile",
			"kr2025_policies",
			"learning/benchmarks/tractable/8puzzle-1tile",
			"feature_definable_goal_dependent_construction_classes",
			"8puzzle-1tile",
			"KR 2025",
			"8puzzle-1tile",
			("training/easy/*.pddl",),
		),
		DomainSpec(
			"sokoban-1stone",
			"kr2025_policies",
			"learning/benchmarks/tractable/sokoban-1stone-v3-7x7",
			"feature_definable_goal_dependent_construction_classes",
			"Sokoban-1stone",
			"KR 2025",
			"sokoban-1stone-v3-7x7",
			("training/easy/*.pddl",),
		),
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
	split = math.floor(len(problem_paths) * TRAIN_RATIO)
	_copy_source_file(spec, spec.source_domain_file, domain_root / "domain.pddl")
	for index, source_problem in enumerate(problem_paths, start=1):
		target_root = train_root if index <= split else test_root
		_copy_source_file(spec, source_problem, target_root / Path(source_problem).name)
	source = SOURCES[spec.source_id]
	source_record = {
		"source": source.name,
		"source_id": source.source_id,
		"source_url": source.url,
		"source_commit": source.commit,
		"source_path": spec.source_path,
		"source_domain_file": f"{spec.source_path}/{spec.source_domain_file}",
		"source_problem_globs": list(spec.problem_globs),
		"ipc_year": spec.ipc_year,
		"ipc_variant": spec.ipc_variant,
		"instance_count": len(problem_paths),
		"train_count": split,
		"test_count": len(problem_paths) - split,
		"split_policy": "floor(2/3 * instance_count) train, remaining test",
	}
	(domain_root / "source.json").write_text(
		json.dumps(source_record, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def _source_problem_paths(spec: DomainSpec) -> tuple[str, ...]:
	output = subprocess.check_output(
		(
			"git",
			"-C",
			str(SOURCES[spec.source_id].local_root),
			"ls-tree",
			"-r",
			"--name-only",
			f"HEAD:{spec.source_path}",
		),
		text=True,
	)
	paths: list[Path] = []
	source_paths = tuple(
		line
		for line in output.splitlines()
		if line.endswith(".pddl") and Path(line).name != spec.source_domain_file
	)
	for glob_text in spec.problem_globs:
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
	full_path = f"{spec.source_path}/{relative_path}"
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


def _benchmark_sources_payload() -> tuple[dict[str, str], ...]:
	return tuple(
		{
			"id": source.source_id,
			"name": source.name,
			"url": source.url,
			"commit": source.commit,
			"coverage": source.coverage,
		}
		for source in SOURCES.values()
	)


def _write_registry(specs: tuple[DomainSpec, ...]) -> None:
	_reset_directory(REGISTRY_ROOT)
	(REGISTRY_ROOT / "registry.json").write_text(
		json.dumps(
			{
				"schema_version": 1,
				"goal_specification_layer": "achievement_goal_layer",
				"future_goal_specification_layers": ["temporal_extended_goal_layer"],
				"selected_domain_class_ids": [
					"goal_separable_serialisable_achievement_classes",
					"bounded_width_sketchable_subgoal_structure_classes",
					"feature_definable_goal_dependent_construction_classes",
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
				"scope": "positive_conjunctive_achievement_goals",
				"benchmark_source": {
					"name": "selected reputable generalized-planning benchmark sources",
					"coverage": "12 routed achievement-goal planning families",
				},
				"benchmark_sources": _benchmark_sources_payload(),
			},
			indent=2,
			sort_keys=True,
		)
		+ "\n",
		encoding="utf-8",
	)
	for spec in specs:
		record_dir = REGISTRY_ROOT / spec.benchmark_class_id / spec.domain_id
		record_dir.mkdir(parents=True)
		problem_paths = _local_problem_paths(spec.domain_id)
		train_paths = tuple(path for path in problem_paths if "/train/" in path)
		test_paths = tuple(path for path in problem_paths if "/test/" in path)
		payload = {
			"schema_version": 1,
			"goal_specification_layer": "achievement_goal_layer",
			"benchmark_class_id": spec.benchmark_class_id,
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
				"source_domain_file": f"{spec.source_path}/{spec.source_domain_file}",
				"source_problem_globs": list(spec.problem_globs),
				"ipc_year": spec.ipc_year,
				"ipc_variant": spec.ipc_variant,
				"instance_count": len(problem_paths),
				"train_count": len(train_paths),
				"test_count": len(test_paths),
				"split_policy": "floor(2/3 * instance_count) train, remaining test",
			},
			"baseline_groups": {},
			"experiments": [
				{
					"name": f"{spec.domain_id}-ipc-full-smoke",
					"order": 100,
					"matrix": "preset",
					"preset_tags": ["paper-expanded-smoke"],
					"train_problem_set": "train",
					"eval_problem_set": "goal_specification",
					"synthesis_profile": "bootstrap",
					"use_synthesis_planner_traces": True,
					"synthesis_planner_executable": "fast-downward/fast-downward.py",
					"synthesis_planner_timeout_seconds": 60,
					"max_steps": 10000,
					"max_depth": 1000,
					"timeout_seconds": 1800,
					"evaluation_timeout_seconds": 15,
					"ablation_label": f"{spec.domain_id}_ipc_full_smoke",
				},
				{
					"name": f"{spec.domain_id}-ipc-full-main",
					"order": 100,
					"matrix": "main",
					"train_problem_set": "train",
					"eval_problem_set": "goal_specification",
					"synthesis_profile": "bootstrap",
					"use_synthesis_planner_traces": True,
					"synthesis_planner_executable": "fast-downward/fast-downward.py",
					"synthesis_planner_timeout_seconds": 60,
					"max_steps": 10000,
					"max_depth": 1000,
					"timeout_seconds": 1800,
					"evaluation_timeout_seconds": 15,
					"ablation_label": f"{spec.domain_id}_ipc_full_main",
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
