#!/usr/bin/env python3
"""Materialize the achievement-goal benchmark corpus from one generator source."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Callable, Iterable, NamedTuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / ".external" / "benchmark-sources" / "pddl-generators"
DOMAINS_ROOT = PROJECT_ROOT / "src" / "domains"
REGISTRY_ROOT = PROJECT_ROOT / "src" / "benchmark_registry" / "achievement_goals"
SOURCE_URL = "https://github.com/AI-Planning/pddl-generators"
SOURCE_COMMIT = "d5c22c9ab21ecaf90db82daf2a0537973c661009"
INSTANCE_COUNT = 30
TRAIN_RATIO = 2 / 3


class DomainSpec(NamedTuple):
	domain_id: str
	source_domain: str
	source_domain_file: str
	benchmark_class_id: str
	display_name: str
	generator: Callable[[Path], list[str]]
	problem_class: str | None = None


def main() -> None:
	"""Regenerate local PDDL benchmark snapshots and the achievement registry."""

	_validate_source()
	_prepare_generators()
	_reset_directory(DOMAINS_ROOT)
	for spec in _domain_specs():
		_materialize_domain(spec)
	_write_registry()
	print(f"materialized {len(_domain_specs())} achievement benchmark domains")


def _validate_source() -> None:
	if not SOURCE_ROOT.exists():
		raise FileNotFoundError(
			f"missing benchmark source {SOURCE_ROOT}; clone AI-Planning/pddl-generators first",
		)
	head = subprocess.check_output(
		("git", "-C", str(SOURCE_ROOT), "rev-parse", "HEAD"),
		text=True,
	).strip()
	if head != SOURCE_COMMIT:
		raise RuntimeError(
			f"unexpected pddl-generators commit {head}; expected {SOURCE_COMMIT}",
		)


def _prepare_generators() -> None:
	for directory in ("gripper", "ferry", "miconic", "visitall"):
		subprocess.run(
			("make", "-C", str(SOURCE_ROOT / directory)),
			check=True,
			stdout=subprocess.DEVNULL,
		)
	subprocess.run(
		("make", "-C", str(SOURCE_ROOT / "blocksworld"), "4ops"),
		check=True,
		stdout=subprocess.DEVNULL,
	)


def _reset_directory(path: Path) -> None:
	if path.exists():
		shutil.rmtree(path)
	path.mkdir(parents=True)


def _domain_specs() -> tuple[DomainSpec, ...]:
	return (
		DomainSpec(
			"gripper",
			"gripper",
			"domain.pddl",
			"goal_separable_serialisable_achievement_classes",
			"Gripper",
			_generate_gripper,
		),
		DomainSpec(
			"ferry",
			"ferry",
			"domain.pddl",
			"goal_separable_serialisable_achievement_classes",
			"Ferry",
			_generate_ferry,
		),
		DomainSpec(
			"miconic",
			"miconic",
			"domain.pddl",
			"goal_separable_serialisable_achievement_classes",
			"Miconic",
			_generate_miconic,
		),
		DomainSpec(
			"spanner",
			"spanner",
			"domain.pddl",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Spanner",
			_generate_spanner,
		),
		DomainSpec(
			"childsnack",
			"childsnack",
			"domain.pddl",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Childsnack",
			_generate_childsnack,
		),
		DomainSpec(
			"barman",
			"barman",
			"domain.pddl",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Barman",
			_generate_barman,
		),
		DomainSpec(
			"visitall",
			"visitall",
			"domain.pddl",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Visitall",
			_generate_visitall,
		),
		DomainSpec(
			"delivery",
			"delivery",
			"domain.pddl",
			"bounded_width_sketchable_subgoal_structure_classes",
			"Delivery",
			_generate_delivery,
		),
		DomainSpec(
			"blocksworld_qclear",
			"blocksworld",
			"4ops/domain.pddl",
			"feature_definable_goal_dependent_construction_classes",
			"Blocksworld Qclear",
			_generate_blocksworld_qclear,
			"qclear",
		),
		DomainSpec(
			"blocksworld_qon",
			"blocksworld",
			"4ops/domain.pddl",
			"feature_definable_goal_dependent_construction_classes",
			"Blocksworld Qon",
			_generate_blocksworld_qon,
			"qon",
		),
		DomainSpec(
			"blocksworld_qbw",
			"blocksworld",
			"4ops/domain.pddl",
			"feature_definable_goal_dependent_construction_classes",
			"Blocksworld Qbw",
			_generate_blocksworld_qbw,
			"qbw",
		),
	)


def _materialize_domain(spec: DomainSpec) -> None:
	domain_root = DOMAINS_ROOT / spec.domain_id
	train_root = domain_root / "train"
	test_root = domain_root / "test"
	train_root.mkdir(parents=True)
	test_root.mkdir(parents=True)
	shutil.copyfile(
		SOURCE_ROOT / spec.source_domain / spec.source_domain_file,
		domain_root / "domain.pddl",
	)
	problems = spec.generator(domain_root)
	if len(problems) != INSTANCE_COUNT:
		raise RuntimeError(
			f"{spec.domain_id} generated {len(problems)} problems; expected {INSTANCE_COUNT}",
		)
	split = math.floor(len(problems) * TRAIN_RATIO)
	for index, problem_text in enumerate(problems, start=1):
		target_root = train_root if index <= split else test_root
		target = target_root / f"p{index:03d}.pddl"
		target.write_text(
			_normalize_problem_name(problem_text, f"{spec.domain_id}-p{index:03d}"),
			encoding="utf-8",
		)
	source_record = {
		"source": "AI-Planning/pddl-generators",
		"source_url": SOURCE_URL,
		"source_commit": SOURCE_COMMIT,
		"source_domain": spec.source_domain,
		"source_domain_file": spec.source_domain_file,
		"problem_class": spec.problem_class,
		"instance_count": INSTANCE_COUNT,
		"train_count": split,
		"test_count": len(problems) - split,
	}
	(domain_root / "source.json").write_text(
		json.dumps(source_record, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def _normalize_problem_name(problem_text: str, name: str) -> str:
	return re.sub(
		r"\(define\s+\(problem\s+[^)\s]+",
		f"(define (problem {name}",
		problem_text,
		count=1,
		flags=re.IGNORECASE,
	)


def _run(command: Iterable[str], *, cwd: Path) -> str:
	completed = subprocess.run(
		tuple(command),
		cwd=cwd,
		check=True,
		capture_output=True,
		text=True,
	)
	return completed.stdout


def _generate_gripper(_domain_root: Path) -> list[str]:
	root = SOURCE_ROOT / "gripper"
	return [_run(("./gripper", "-n", str(index + 1)), cwd=root) for index in range(1, 31)]


def _generate_ferry(_domain_root: Path) -> list[str]:
	root = SOURCE_ROOT / "ferry"
	problems: list[str] = []
	for index in range(1, 31):
		cars = index
		locations = max(2, index // 2 + 2)
		problems.append(
			_run(
				("./ferry", "-l", str(locations), "-c", str(cars), "-s", str(1000 + index)),
				cwd=root,
			),
		)
	return problems


def _generate_miconic(_domain_root: Path) -> list[str]:
	root = SOURCE_ROOT / "miconic"
	return [
		_run(
			(
				"./miconic",
				"-f",
				str(max(2, index * 2)),
				"-p",
				str(index),
				"-r",
				str(2000 + index),
			),
			cwd=root,
		)
		for index in range(1, 31)
	]


def _generate_spanner(_domain_root: Path) -> list[str]:
	root = SOURCE_ROOT / "spanner"
	problems: list[str] = []
	for index in range(1, 31):
		nuts = index
		spanners = nuts + 1
		locations = max(2, index // 2 + 2)
		problems.append(
			_run(
				(
					sys.executable,
					"spanner-generator.py",
					str(spanners),
					str(nuts),
					str(locations),
					"--seed",
					str(3000 + index),
					"--problem-name",
					f"spanner-p{index:03d}",
				),
				cwd=root,
			),
		)
	return problems


def _generate_childsnack(_domain_root: Path) -> list[str]:
	root = SOURCE_ROOT / "childsnack"
	problems: list[str] = []
	for index in range(1, 31):
		children = 5 + index
		trays = 2 if index <= 15 else 3
		problems.append(
			_run(
				(
					sys.executable,
					"child-snack-generator.py",
					"pool",
					str(4000 + index),
					str(children),
					str(trays),
					"0.4",
					"1.3",
				),
				cwd=root,
			),
		)
	return problems


def _generate_barman(_domain_root: Path) -> list[str]:
	root = SOURCE_ROOT / "barman"
	problems: list[str] = []
	for index in range(1, 31):
		cocktails = (index - 1) // 3 + 1
		ingredients = max(2, min(6, cocktails + 2))
		shots = cocktails + 2
		problems.append(
			_run(
				(
					sys.executable,
					"barman-generator.py",
					str(cocktails),
					str(ingredients),
					str(shots),
					str(5000 + index),
				),
				cwd=root,
			),
		)
	return problems


def _generate_visitall(_domain_root: Path) -> list[str]:
	root = SOURCE_ROOT / "visitall"
	problems: list[str] = []
	for index in range(1, 31):
		size = 4 + ((index - 1) // 3)
		ratio = "1.0" if index % 2 else "0.5"
		problems.append(
			_run(
				(
					"./grid",
					"-n",
					str(size),
					"-r",
					ratio,
					"-u",
					"0",
					"-s",
					str(6000 + index),
				),
				cwd=root,
			),
		)
	return problems


def _generate_delivery(_domain_root: Path) -> list[str]:
	root = SOURCE_ROOT / "delivery"
	script = (root / "generate.py").read_text(encoding="utf-8")
	script = script.replace(
		"args = arg_parser.parse_args()",
		"args = arg_parser.parse_args()\nrandom.seed(7001)",
		1,
	)
	output_root = root / "output"
	if output_root.exists():
		shutil.rmtree(output_root)
	argv = sys.argv
	cwd = Path.cwd()
	try:
		sys.argv = [
			"generate.py",
			"--grid_size_splits=6,6,6",
			"--max_nr_packages=3",
			"--nr_instances_per_setup=2",
		]
		os.chdir(root)
		exec(compile(script, str(root / "generate.py"), "exec"), {"__name__": "__main__"})
	finally:
		os.chdir(cwd)
		sys.argv = argv
	files = sorted((output_root / "train").glob("*.pddl"))
	problems = [path.read_text(encoding="utf-8") for path in files if path.name != "domain.pddl"]
	if output_root.exists():
		shutil.rmtree(output_root)
	return problems


def _generate_blocksworld_qbw(_domain_root: Path) -> list[str]:
	return _generated_blocksworld_problems("qbw")


def _generate_blocksworld_qon(_domain_root: Path) -> list[str]:
	return _generated_blocksworld_problems("qon")


def _generate_blocksworld_qclear(_domain_root: Path) -> list[str]:
	return _generated_blocksworld_problems("qclear")


def _generated_blocksworld_problems(problem_class: str) -> list[str]:
	root = SOURCE_ROOT / "blocksworld"
	problems: list[str] = []
	for index in range(1, 31):
		blocks = 4 + ((index - 1) // 3)
		raw = _run(("./blocksworld", "4", str(blocks), str(8000 + index)), cwd=root)
		if problem_class == "qbw":
			problems.append(raw)
		elif problem_class == "qon":
			problems.append(_with_blocksworld_on_goal(raw))
		elif problem_class == "qclear":
			problems.append(_with_blocksworld_clear_goal(raw))
		else:
			raise ValueError(problem_class)
	return problems


def _with_blocksworld_on_goal(problem_text: str) -> str:
	goal_on = _blocksworld_goal_on_atoms(problem_text)
	init_on = set(_section_atoms(problem_text, "init", "on"))
	selected = next((atom for atom in goal_on if atom not in init_on), goal_on[0])
	return _replace_goal(problem_text, f"(and\n{selected}\n)")


def _with_blocksworld_clear_goal(problem_text: str) -> str:
	objects = _blocksworld_objects(problem_text)
	goal_on = _blocksworld_goal_on_atoms(problem_text)
	non_clear = {support for _block, support in (_atom_args(atom) for atom in goal_on)}
	final_clear = [block for block in objects if block not in non_clear]
	init_clear = {args[0] for args in (_atom_args(atom) for atom in _section_atoms(problem_text, "init", "clear"))}
	selected = next((block for block in final_clear if block not in init_clear), final_clear[0])
	return _replace_goal(problem_text, f"(and\n(clear {selected})\n)")


def _blocksworld_objects(problem_text: str) -> list[str]:
	match = re.search(r"\(:objects\s+([^)]*)\)", problem_text, flags=re.IGNORECASE | re.DOTALL)
	if not match:
		raise ValueError("Blocksworld problem has no objects section")
	return re.findall(r"\bb\d+\b", match.group(1))


def _blocksworld_goal_on_atoms(problem_text: str) -> list[str]:
	goal = _extract_section(problem_text, "goal")
	atoms = re.findall(r"\(on\s+b\d+\s+b\d+\)", goal, flags=re.IGNORECASE)
	if not atoms:
		raise ValueError("Blocksworld qbw source problem has no on goal atoms")
	return atoms


def _section_atoms(problem_text: str, section: str, predicate: str) -> list[str]:
	text = _extract_section(problem_text, section)
	return re.findall(
		rf"\({re.escape(predicate)}\s+[^()]+\)",
		text,
		flags=re.IGNORECASE,
	)


def _atom_args(atom: str) -> tuple[str, ...]:
	return tuple(atom.strip("()").split()[1:])


def _extract_section(problem_text: str, section: str) -> str:
	start = problem_text.lower().find(f"(:{section}")
	if start < 0:
		raise ValueError(f"missing PDDL section :{section}")
	depth = 0
	for position in range(start, len(problem_text)):
		character = problem_text[position]
		if character == "(":
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0:
				return problem_text[start : position + 1]
	raise ValueError(f"unterminated PDDL section :{section}")


def _replace_goal(problem_text: str, goal_body: str) -> str:
	start = problem_text.lower().find("(:goal")
	if start < 0:
		raise ValueError("missing PDDL goal")
	depth = 0
	for position in range(start, len(problem_text)):
		character = problem_text[position]
		if character == "(":
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0:
				return problem_text[:start] + f"(:goal\n{goal_body}\n)" + problem_text[position + 1 :]
	raise ValueError("unterminated PDDL goal")


def _write_registry() -> None:
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
					"name": "AI-Planning/pddl-generators",
					"url": SOURCE_URL,
					"commit": SOURCE_COMMIT,
				},
			},
			indent=2,
			sort_keys=True,
		)
		+ "\n",
		encoding="utf-8",
	)
	for spec in _domain_specs():
		record_dir = REGISTRY_ROOT / spec.benchmark_class_id / spec.domain_id
		record_dir.mkdir(parents=True)
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
					"problems": [
						f"src/domains/{spec.domain_id}/train/p{index:03d}.pddl"
						for index in range(1, 21)
					]
					+ [
						f"src/domains/{spec.domain_id}/test/p{index:03d}.pddl"
						for index in range(21, 31)
					],
				},
			},
			"source": {
				"name": "AI-Planning/pddl-generators",
				"url": SOURCE_URL,
				"commit": SOURCE_COMMIT,
				"source_domain": spec.source_domain,
				"source_domain_file": spec.source_domain_file,
				"problem_class": spec.problem_class,
			},
			"baseline_groups": {},
			"experiments": [
				{
					"name": f"{spec.domain_id}-source-split-smoke",
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
					"ablation_label": f"{spec.domain_id}_source_split_smoke",
				},
				{
					"name": f"{spec.domain_id}-source-split-main",
					"order": 100,
					"matrix": "main",
					"train_problem_set": "train",
					"eval_problem_set": "goal_specification",
					"synthesis_profile": "bootstrap",
					"max_steps": 10000,
					"max_depth": 1000,
					"timeout_seconds": 180,
					"evaluation_timeout_seconds": 15,
					"ablation_label": f"{spec.domain_id}_source_split_main",
				},
			],
		}
		if spec.problem_class is not None:
			payload["problem_class"] = spec.problem_class
		(record_dir / "benchmark.json").write_text(
			json.dumps(payload, indent=2, sort_keys=True) + "\n",
			encoding="utf-8",
		)


if __name__ == "__main__":
	main()
