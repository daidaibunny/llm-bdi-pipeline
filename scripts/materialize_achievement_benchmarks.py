#!/usr/bin/env python3
"""Materialize the achievement-goal benchmark corpus from IPC instances."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import NamedTuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / ".external" / "benchmark-sources" / "pddl-instances"
SOURCE_CACHE_ROOT = PROJECT_ROOT / ".external" / "benchmark-sources" / "pddl-instances-cache"
DOMAINS_ROOT = PROJECT_ROOT / "src" / "domains"
REGISTRY_ROOT = PROJECT_ROOT / "src" / "benchmark_registry" / "achievement_goals"
SOURCE_NAME = "potassco/pddl-instances"
SOURCE_URL = "https://github.com/potassco/pddl-instances"
SOURCE_RAW_URL = "https://raw.githubusercontent.com/potassco/pddl-instances"
SOURCE_COMMIT = "cf19edf7c53d1540ddbb396c642595e0926ee552"
TRAIN_RATIO = 2 / 3
DOWNLOAD_ATTEMPTS = 5
GIT_BLOB_TIMEOUT_SECONDS = 120


class DomainSpec(NamedTuple):
	domain_id: str
	source_path: str
	benchmark_class_id: str
	display_name: str
	ipc_year: str
	ipc_variant: str
	problem_layout: str = "instances"


def main() -> None:
	"""Regenerate local IPC PDDL snapshots and the achievement registry."""

	_validate_source()
	_reset_directory(DOMAINS_ROOT)
	specs = _domain_specs()
	for spec in specs:
		_materialize_domain(spec)
	_write_registry(specs)
	print(f"materialized {len(specs)} IPC achievement benchmark domains")


def _validate_source() -> None:
	if not SOURCE_ROOT.exists():
		raise FileNotFoundError(
			f"missing IPC benchmark source {SOURCE_ROOT}; clone potassco/pddl-instances first",
		)
	head = subprocess.check_output(
		("git", "-C", str(SOURCE_ROOT), "rev-parse", "HEAD"),
		text=True,
	).strip()
	if head != SOURCE_COMMIT:
		raise RuntimeError(
			f"unexpected pddl-instances commit {head}; expected {SOURCE_COMMIT}",
		)


def _reset_directory(path: Path) -> None:
	if path.exists():
		shutil.rmtree(path)
	path.mkdir(parents=True)


def _domain_specs() -> tuple[DomainSpec, ...]:
	return (
		DomainSpec(
			"gripper",
			"ipc-1998/domains/gripper-round-1-strips",
			"goal_separable_serialisable_achievement_classes",
			"Gripper",
			"1998",
			"gripper-round-1-strips",
		),
		DomainSpec(
			"miconic",
			"ipc-2000/domains/elevator-strips-simple-typed",
			"goal_separable_serialisable_achievement_classes",
			"Miconic",
			"2000",
			"elevator-strips-simple-typed",
		),
		DomainSpec(
			"barman",
			"ipc-2011/domains/barman-sequential-satisficing",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Barman",
			"2011",
			"barman-sequential-satisficing",
		),
		DomainSpec(
			"childsnack",
			"ipc-2014/domains/child-snack-sequential-satisficing",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Childsnack",
			"2014",
			"child-snack-sequential-satisficing",
		),
		DomainSpec(
			"visitall",
			"ipc-2011/domains/visit-all-sequential-satisficing",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Visitall",
			"2011",
			"visit-all-sequential-satisficing",
		),
		DomainSpec(
			"blocks",
			"ipc-2000/domains/blocks-strips-typed",
			"feature_definable_goal_dependent_construction_classes",
			"Blocks",
			"2000",
			"blocks-strips-typed",
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
		raise RuntimeError(f"{spec.domain_id} has no IPC instances in {spec.source_path}")
	split = math.floor(len(problem_paths) * TRAIN_RATIO)
	_copy_source_file(f"{spec.source_path}/domain.pddl", domain_root / "domain.pddl")
	for index, source_problem in enumerate(problem_paths, start=1):
		target_root = train_root if index <= split else test_root
		_copy_source_file(source_problem, target_root / Path(source_problem).name)
	source_record = {
		"source": SOURCE_NAME,
		"source_url": SOURCE_URL,
		"source_commit": SOURCE_COMMIT,
		"source_path": spec.source_path,
		"source_domain_file": f"{spec.source_path}/domain.pddl",
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
			str(SOURCE_ROOT),
			"ls-tree",
			"-r",
			"--name-only",
			f"HEAD:{spec.source_path}/{spec.problem_layout}",
		),
		text=True,
	)
	return tuple(
		f"{spec.source_path}/{spec.problem_layout}/{path}"
		for path in sorted(
			(line for line in output.splitlines() if line.endswith(".pddl")),
			key=_instance_sort_key,
		)
	)


def _instance_sort_key(path: str) -> tuple[int, str]:
	match = re.search(r"instance-(\d+)\.pddl$", path)
	if match:
		return (int(match.group(1)), path)
	return (10**9, path)


def _copy_source_file(source_path: str, target_path: Path) -> None:
	cache_path = SOURCE_CACHE_ROOT / SOURCE_COMMIT / source_path
	if not cache_path.exists():
		_download_source_file(source_path, cache_path)
	_write_pddl_snapshot(cache_path.read_bytes(), target_path)


def _write_pddl_snapshot(content: bytes, target_path: Path) -> None:
	text = content.decode("utf-8")
	lines = [
		line.replace("\t", "  ").rstrip()
		for line in text.replace("\r\n", "\n").split("\n")
	]
	target_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _download_source_file(source_path: str, target_path: Path) -> None:
	target_path.parent.mkdir(parents=True, exist_ok=True)
	last_error: Exception | None = None
	for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
		try:
			content = _read_source_file_content(source_path)
			if not content.strip():
				raise RuntimeError(f"empty PDDL source file at {source_path}")
			target_path.write_bytes(content)
			return
		except (HTTPError, OSError, RuntimeError, URLError) as error:
			last_error = error
			if attempt < DOWNLOAD_ATTEMPTS:
				time.sleep(attempt)
	raise RuntimeError(f"failed to download {source_path}") from last_error


def _read_source_file_content(source_path: str) -> bytes:
	blob_sha = _source_blob_sha(source_path)
	try:
		return _read_blob_with_git(blob_sha)
	except (OSError, RuntimeError, subprocess.SubprocessError):
		return _download_blob_with_github_api(blob_sha)


def _source_blob_sha(source_path: str) -> str:
	output = subprocess.check_output(
		(
			"git",
			"-C",
			str(SOURCE_ROOT),
			"ls-tree",
			"HEAD",
			source_path,
		),
		text=True,
	)
	parts = output.strip().split()
	if len(parts) < 3 or parts[1] != "blob":
		raise RuntimeError(f"cannot locate source blob for {source_path}")
	return parts[2]


def _read_blob_with_git(blob_sha: str) -> bytes:
	env = os.environ.copy()
	env["GIT_TERMINAL_PROMPT"] = "0"
	result = subprocess.run(
		("git", "-C", str(SOURCE_ROOT), "cat-file", "-p", blob_sha),
		check=False,
		capture_output=True,
		env=env,
		timeout=GIT_BLOB_TIMEOUT_SECONDS,
	)
	if result.returncode != 0:
		stderr = result.stderr.decode("utf-8", errors="replace")
		raise RuntimeError(f"git cat-file failed for {blob_sha}: {stderr}")
	return result.stdout


def _download_blob_with_github_api(blob_sha: str) -> bytes:
	url = f"https://api.github.com/repos/{SOURCE_NAME}/git/blobs/{blob_sha}"
	request = Request(
		url,
		headers={
			"Accept": "application/vnd.github.raw",
			"User-Agent": "llm-bdi-pipeline-ipc-materializer",
		},
	)
	with urlopen(request, timeout=60) as response:
		return response.read()


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
					"name": SOURCE_NAME,
					"url": SOURCE_URL,
					"commit": SOURCE_COMMIT,
					"coverage": "IPC 1998-2014 complete collection",
				},
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
				"name": SOURCE_NAME,
				"url": SOURCE_URL,
				"commit": SOURCE_COMMIT,
				"source_path": spec.source_path,
				"source_domain_file": f"{spec.source_path}/domain.pddl",
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
					"max_steps": 10000,
					"max_depth": 1000,
					"timeout_seconds": 180,
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
					"max_steps": 10000,
					"max_depth": 1000,
					"timeout_seconds": 180,
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
