#!/usr/bin/env python3
"""
Install and inspect external generalized-planning learner backends.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from domain_level_planning.gp_backends import (
	DEFAULT_BACKEND_ROOT,
	GPBackendRunner,
	MOOSE_BACKEND,
	PINNED_BACKENDS,
	PROJECT_EXTERNAL_ROOT,
	backend_audit_matrix,
	discover_backend_manifest,
	discover_learning_general_policies_policy_file,
	parse_dlplan_policy,
)
from domain_level_planning.moose_policy_adapter import (
	compile_moose_readable_policy_to_asl_library,
	compile_moose_readable_policy_to_minimal_module_asl_library,
	policy_program_from_moose_readable_policy,
)
from domain_level_planning.policy_program import policy_program_from_sketch_policy
from plan_library.rendering import render_plan_library_asl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKENDS = tuple(PINNED_BACKENDS)


@dataclass(frozen=True)
class SmokeConfig:
	domain_file: Path
	problems_directory: Path
	workspace: Path
	width: int = 1


@dataclass(frozen=True)
class LearnerSketchesExperiment:
	name: str
	benchmark_family: str
	domain_name: str
	width: int
	domain_file: Path
	problems_directory: Path
	workspace: Path


@dataclass(frozen=True)
class LearningGeneralPoliciesExperiment:
	name: str
	benchmark_family: str
	domain_name: str
	width: int
	domain_file: Path
	problems_directory: Path
	workspace: Path
	planner: str = "bfws"


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"command",
		choices=(
			"status",
			"usage",
			"capability",
			"install",
			"install-deps",
			"blocksworld-smoke-command",
			"moose-atomic-command",
			"moose-readable-summary",
			"moose-readable-compile-asl",
			"learner-sketches-command",
			"learner-sketches-summary",
			"learning-general-policies-command",
			"learning-general-policies-docker-build-command",
			"learning-general-policies-docker-command",
			"learning-general-policies-summary",
			"d2l-docker-commands",
			"parse-policy",
		),
	)
	parser.add_argument(
		"--backend-root",
		type=Path,
		default=DEFAULT_BACKEND_ROOT,
		help="Directory for external backend repositories.",
	)
	parser.add_argument(
		"--audit-output-root",
		type=Path,
		default=PROJECT_ROOT / "tmp" / "gp-backend-audit",
		help="Root directory for backend audit workspaces and summaries.",
	)
	parser.add_argument(
		"--policy-file",
		type=Path,
		help="Policy file to parse for parse-policy or moose-readable-summary.",
	)
	parser.add_argument(
		"--domain-file",
		type=Path,
		help="PDDL domain file for MOOSE command generation or minimal module synthesis.",
	)
	parser.add_argument(
		"--training-dir",
		type=Path,
		help="Training problem directory for MOOSE atomic command generation.",
	)
	parser.add_argument(
		"--save-file",
		type=Path,
		help="Output MOOSE model file for moose-atomic-command.",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		help="Output directory for commands that materialize project artifacts.",
	)
	parser.add_argument("--random-seed", type=int, default=0)
	parser.add_argument("--num-permutations", type=int, default=3)
	parser.add_argument("--goal-max-size", type=int, default=1)
	parser.add_argument(
		"--domain-name",
		default="unknown",
		help="Domain name for readable-policy summaries.",
	)
	parser.add_argument(
		"--experiment",
		default="all",
		help="Backend experiment name to print or summarize, or 'all'.",
	)
	parser.add_argument("--proxy", help="Optional HTTP/HTTPS proxy for GitHub access.")
	parser.add_argument(
		"--max-rss-gb",
		type=float,
		default=16.0,
		help="Memory guard for printed external learner commands.",
	)
	parser.add_argument(
		"--timeout-seconds",
		type=int,
		help="Optional wall-clock guard for printed external learner commands.",
	)
	parser.add_argument(
		"--max-num-instances",
		type=int,
		help=(
			"Optional KR 2025 backend instance cap for smoke runs. "
			"Omit for paper-profile commands."
		),
	)
	parser.add_argument(
		"--unsafe-direct",
		action="store_true",
		help="Print raw paper backend commands without the resource guard.",
	)
	parser.add_argument(
		"--minimal-modules",
		action="store_true",
		help="Deprecated alias for --post-moose-recursive.",
	)
	parser.add_argument(
		"--post-moose-recursive",
		action="store_true",
		help="Compile MOOSE singleton evidence into compact recursive atomic modules.",
	)
	args = parser.parse_args()

	if args.command == "install":
		install_backends(args.backend_root, proxy=args.proxy)
		return 0
	if args.command == "install-deps":
		install_backend_dependencies(args.backend_root)
		return 0
	if args.command == "status":
		print_backend_status(args.backend_root)
		return 0
	if args.command == "usage":
		print_backend_usage(args.backend_root)
		return 0
	if args.command == "capability":
		print_backend_capabilities(args.backend_root)
		return 0
	if args.command == "blocksworld-smoke-command":
		print_blocksworld_smoke_command(
			args.backend_root,
			max_rss_gb=args.max_rss_gb,
			timeout_seconds=args.timeout_seconds,
			unsafe_direct=args.unsafe_direct,
		)
		return 0
	if args.command == "moose-atomic-command":
		print_moose_atomic_command(
			domain_file=_required_path(args.domain_file, "--domain-file"),
			training_dir=_required_path(args.training_dir, "--training-dir"),
			save_file=_required_path(args.save_file, "--save-file"),
			random_seed=args.random_seed,
			num_permutations=args.num_permutations,
			goal_max_size=args.goal_max_size,
			max_rss_gb=args.max_rss_gb,
			timeout_seconds=args.timeout_seconds,
		)
		return 0
	if args.command == "moose-readable-summary":
		print_moose_readable_summary(
			policy_file=_required_path(args.policy_file, "--policy-file"),
			domain_name=args.domain_name,
		)
		return 0
	if args.command == "moose-readable-compile-asl":
		compile_moose_readable_atomic_library(
			policy_file=_required_path(args.policy_file, "--policy-file"),
			domain_name=args.domain_name,
			domain_file=args.domain_file,
			output_dir=_required_path(args.output_dir, "--output-dir"),
			minimal_modules=bool(args.minimal_modules or args.post_moose_recursive),
		)
		return 0
	if args.command == "learner-sketches-command":
		print_learner_sketches_commands(
			args.backend_root,
			experiment=args.experiment,
			max_rss_gb=args.max_rss_gb,
			timeout_seconds=args.timeout_seconds,
			max_num_instances=args.max_num_instances,
			unsafe_direct=args.unsafe_direct,
		)
		return 0
	if args.command == "learner-sketches-summary":
		print_learner_sketches_summary(args.backend_root, experiment=args.experiment)
		return 0
	if args.command == "learning-general-policies-command":
		print_learning_general_policies_commands(
			args.backend_root,
			audit_output_root=args.audit_output_root,
			experiment=args.experiment,
			max_rss_gb=args.max_rss_gb,
			timeout_seconds=args.timeout_seconds,
			max_num_instances=args.max_num_instances,
			unsafe_direct=args.unsafe_direct,
		)
		return 0
	if args.command == "learning-general-policies-docker-build-command":
		print_learning_general_policies_docker_build_command(
			args.backend_root,
			proxy=args.proxy,
		)
		return 0
	if args.command == "learning-general-policies-docker-command":
		print_learning_general_policies_docker_commands(
			args.backend_root,
			audit_output_root=args.audit_output_root,
			experiment=args.experiment,
			max_rss_gb=args.max_rss_gb,
			timeout_seconds=args.timeout_seconds,
			max_num_instances=args.max_num_instances,
		)
		return 0
	if args.command == "learning-general-policies-summary":
		print_learning_general_policies_summary(
			args.backend_root,
			audit_output_root=args.audit_output_root,
			experiment=args.experiment,
		)
		return 0
	if args.command == "d2l-docker-commands":
		print_d2l_docker_commands(args.backend_root)
		return 0
	if args.command == "parse-policy":
		if args.policy_file is None:
			parser.error("--policy-file is required for parse-policy")
		print_policy_summary(args.policy_file)
		return 0
	raise AssertionError(f"Unhandled command: {args.command}")


def install_backends(root: Path, *, proxy: str | None = None) -> None:
	root.mkdir(parents=True, exist_ok=True)
	install_moose_backend(root, proxy=proxy)
	for backend in BACKENDS:
		manifest = discover_backend_manifest(
			root=root,
			name=backend["name"],
			url=backend["url"],
			commit=backend["commit"],
		)
		if not manifest.present:
			_run_git(("clone", backend["url"], str(manifest.path)), proxy=proxy)
		_run_git(("-C", str(manifest.path), "fetch", "--depth", "1", "origin", backend["commit"]), proxy=proxy)
		_run_git(("-C", str(manifest.path), "checkout", "--detach", backend["commit"]), proxy=proxy)


def install_moose_backend(root: Path, *, proxy: str | None = None) -> None:
	default_root = DEFAULT_BACKEND_ROOT.expanduser().resolve()
	target = (
		Path(MOOSE_BACKEND["path"])
		if root.expanduser().resolve() == default_root
		else root / "moose"
	)
	if not target.exists():
		target.parent.mkdir(parents=True, exist_ok=True)
		_run_git(("clone", str(MOOSE_BACKEND["url"]), str(target)), proxy=proxy)
	_run_git(
		(
			"-C",
			str(target),
			"fetch",
			"--depth",
			"1",
			"origin",
			str(MOOSE_BACKEND["commit"]),
		),
		proxy=proxy,
	)
	_run_git(("-C", str(target), "checkout", "--detach", str(MOOSE_BACKEND["commit"])), proxy=proxy)


def install_backend_dependencies(root: Path) -> None:
	venv = root / ".venv"
	if not venv.exists():
		subprocess.run(("uv", "venv", str(venv)), check=True)
	env = {
		**os.environ,
		"UV_HTTP_TIMEOUT": "600",
	}
	subprocess.run(
		(
			"uv",
			"pip",
			"install",
			"--python",
			str(venv / "bin" / "python"),
			"-r",
			str(root / "learner-sketches" / "requirements.txt"),
		),
		check=True,
		env=env,
	)
	subprocess.run(
		(
			"uv",
			"pip",
			"install",
			"--python",
			str(venv / "bin" / "python"),
			"intbitset",
			"bloom-filter2",
			"tqdm",
			"tarski",
		),
		check=True,
		env=env,
	)


def print_backend_status(root: Path) -> None:
	for entry in backend_audit_matrix(root=root):
		state = "present" if entry["present"] else "missing"
		observed = entry["observed_commit"] or "unknown"
		pinned = entry["pin_status"]
		print(
			f"{entry['name']}: {state}; observed={observed}; "
			f"pinned={pinned}; path={entry['path']}"
		)


def print_backend_usage(root: Path) -> None:
	for entry in backend_audit_matrix(root=root):
		print(f"{entry['name']}:")
		print(f"  path: {entry['path']}")
		print(f"  role: {entry['paper_role']}")
		print(f"  preferred_use: {entry['preferred_use']}")
		print(
			"  consumption: "
			f"{entry['current_consumption_role']['consumption_mode']}; "
			"atomic_library="
			f"{entry['current_consumption_role']['consumed_by_atomic_library']}"
		)
		usage = tuple(str(item) for item in entry.get("usage_entrypoints") or ())
		if usage:
			print("  usage:")
			for item in usage:
				print(f"    - {item}")
		else:
			print("  usage: see backend README or existing command-specific audit helper")


def print_backend_capabilities(root: Path) -> None:
	for entry in backend_audit_matrix(root=root):
		capability = dict(entry["paper_code_capability"])
		print(f"{entry['name']}:")
		print(f"  status: {capability['status']}")
		print(f"  pinned: {entry['pin_status']}")
		print(f"  present: {entry['present']}")
		print("  basis:")
		for item in tuple(str(value) for value in capability.get("basis") or ()):
			print(f"    - {item}")
		gaps = tuple(str(value) for value in capability.get("reproduction_gap") or ())
		if gaps:
			print("  reproduction_gap:")
			for item in gaps:
				print(f"    - {item}")


def print_blocksworld_smoke_command(
	root: Path,
	*,
	max_rss_gb: float,
	timeout_seconds: int | None,
	unsafe_direct: bool,
) -> None:
	backend = _backend_definition("learner-sketches")
	manifest = discover_backend_manifest(
		root=root,
		name=backend["name"],
		url=backend["url"],
		commit=backend["commit"],
	)
	config = _blocksworld_smoke_config()
	runner = GPBackendRunner(manifest)
	command = runner.learner_sketches_command(
		domain_file=config.domain_file,
		problems_directory=config.problems_directory,
		workspace=config.workspace,
		python_executable=root / ".venv" / "bin" / "python",
		width=1,
		max_states_per_instance=1000,
		max_time_per_instance=30,
	)
	if not unsafe_direct:
		command = runner.guarded_command(
			command,
			label="learner-sketches:blocksworld-smoke",
			max_rss_gb=max_rss_gb,
			timeout_seconds=timeout_seconds,
		)
	print(shlex.join(command))


def print_moose_atomic_command(
	*,
	domain_file: Path,
	training_dir: Path,
	save_file: Path,
	random_seed: int,
	num_permutations: int,
	goal_max_size: int,
	max_rss_gb: float,
	timeout_seconds: int | None,
) -> None:
	"""Print the guarded MOOSE train plus readable-policy dump command."""

	domain_project_path = _project_container_path(domain_file)
	training_project_path = _project_container_path(training_dir)
	save_project_path = _project_container_path(save_file)
	readable_project_path = f"{save_project_path}.readable"
	inner_script = "\n".join(
		(
			"set -euo pipefail",
			"mkdir -p " + shlex.quote(str(Path(save_project_path).parent)),
			"apptainer run --bind /work --bind /project /work/moose.sif "
			+ shlex.join(
				(
					"train",
					domain_project_path,
					training_project_path,
					"--save-file",
					save_project_path,
					"--random-seed",
					str(random_seed),
					"--num-permutations",
					str(num_permutations),
					"--goal-max-size",
					str(goal_max_size),
				),
			),
			"apptainer run --bind /work --bind /project /work/moose.sif "
			+ shlex.join(("policy", save_project_path, "--dump-policy"))
			+ " > "
			+ shlex.quote(readable_project_path),
		),
	)
	docker_command = (
		"docker",
		"run",
		"--rm",
		"--platform",
		"linux/amd64",
		f"--memory={int(max_rss_gb)}g",
		"--privileged",
		"-v",
		f"{PROJECT_EXTERNAL_ROOT / 'moose'}:/work",
		"-v",
		f"{PROJECT_ROOT}:/project",
		"-w",
		"/work",
		"moose-exact-ubuntu22:local",
		"bash",
		"-lc",
		inner_script,
	)
	command = _guarded_command(
		docker_command,
		label="moose:atomic-template-train-dump",
		max_rss_gb=max_rss_gb,
		timeout_seconds=timeout_seconds,
	)
	print(shlex.join(command))


def print_moose_readable_summary(*, policy_file: Path, domain_name: str) -> None:
	"""Print adapter status for a MOOSE readable policy artifact."""

	text = policy_file.read_text(encoding="utf-8")
	source_name = policy_file.stem.replace(".model", "")
	program = policy_program_from_moose_readable_policy(
		text,
		domain_name=domain_name,
		source_name=source_name,
		policy_file=policy_file,
	)
	library = compile_moose_readable_policy_to_asl_library(
		text,
		domain_name=domain_name,
		source_name=source_name,
		policy_file=policy_file,
	)
	print(
		f"{policy_file}: policy_program=ok; backend=moose; "
		f"rules={len(program.rules)}; modules={len(program.modules)}; "
		f"asl_plans={len(library.plans)}",
	)
	for rule in program.rules:
		print(f"  rule {rule.name}: conditions={len(rule.conditions)} effects={len(rule.effects)}")


def compile_moose_readable_atomic_library(
	*,
	policy_file: Path,
	domain_name: str,
	domain_file: Path | None,
	output_dir: Path,
	minimal_modules: bool = False,
) -> None:
	"""Materialize a domain-level atomic ASL library from a MOOSE readable policy."""

	text = policy_file.read_text(encoding="utf-8")
	source_name = policy_file.stem.replace(".model", "")
	if minimal_modules:
		if domain_file is None:
			raise ValueError("--domain-file is required with --minimal-modules.")
		library = compile_moose_readable_policy_to_minimal_module_asl_library(
			text,
			domain_file=domain_file,
			domain_name=domain_name,
			source_name=source_name,
			policy_file=policy_file,
		)
	else:
		library = compile_moose_readable_policy_to_asl_library(
			text,
			domain_name=domain_name,
			source_name=source_name,
			policy_file=policy_file,
		)
	program = policy_program_from_moose_readable_policy(
		text,
		domain_name=domain_name,
		source_name=source_name,
		policy_file=policy_file,
	)
	output_dir.mkdir(parents=True, exist_ok=True)
	library_json = output_dir / "plan_library.json"
	library_asl = output_dir / "plan_library.asl"
	metadata_file = output_dir / "atomic_library_metadata.json"
	library_json.write_text(
		json.dumps(library.to_dict(), indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	library_asl.write_text(render_plan_library_asl(library), encoding="utf-8")
	metadata_file.write_text(
		json.dumps(
			{
				"backend": "moose",
				"domain_name": domain_name,
				"domain_file": str(domain_file) if domain_file is not None else None,
				"policy_file": str(policy_file),
				"source_name": source_name,
				"minimal_modules": minimal_modules,
				"raw_rule_count": int(
					library.metadata.get("raw_rule_count")
					or library.metadata.get("source_raw_rule_count")
					or 0,
				),
				"source_raw_rule_count": int(
					library.metadata.get("source_raw_rule_count")
					or library.metadata.get("raw_rule_count")
					or 0,
				),
				"source_seed_predicates": list(
					library.metadata.get("source_seed_predicates") or (),
				),
				"compiled_plan_count": len(library.plans),
				"compiled_singleton_rule_count": (
					int(library.metadata.get("compiled_singleton_rule_count") or 0)
					if not minimal_modules
					else 0
				),
				"policy_program_rule_count": len(program.rules),
				"policy_program_module_count": len(program.modules),
				"library_quality": dict(library.metadata.get("library_quality") or {}),
				"artifact_contract": (
					"domain-level lifted atomic AgentSpeak(L) library generated "
					"from MOOSE readable singleton-goal rules"
				),
			},
			indent=2,
			sort_keys=True,
		)
		+ "\n",
		encoding="utf-8",
	)
	print(
		f"{policy_file}: wrote atomic ASL library; "
		f"plans={len(library.plans)}; json={library_json}; asl={library_asl}; "
		f"metadata={metadata_file}"
	)


def print_learner_sketches_commands(
	root: Path,
	*,
	experiment: str,
	max_rss_gb: float,
	timeout_seconds: int | None,
	unsafe_direct: bool,
) -> None:
	manifest = _learner_sketches_manifest(root)
	runner = GPBackendRunner(manifest)
	for config in _selected_learner_sketches_experiments(root, experiment):
		command = runner.learner_sketches_command(
			domain_file=config.domain_file,
			problems_directory=config.problems_directory,
			workspace=config.workspace,
			python_executable=root / ".venv" / "bin" / "python",
			width=config.width,
		)
		if not unsafe_direct:
			command = runner.guarded_command(
				command,
				label=f"learner-sketches:{config.name}",
				max_rss_gb=max_rss_gb,
				timeout_seconds=timeout_seconds,
			)
		env_prefix = (
			f"PYTHONPATH={manifest.path} "
			f"SKETCH_LEARNER_DIR={manifest.path}"
		)
		print(f"# {config.name}")
		print(env_prefix, shlex.join(command))


def print_learning_general_policies_commands(
	root: Path,
	*,
	audit_output_root: Path,
	experiment: str,
	max_rss_gb: float,
	timeout_seconds: int | None,
	max_num_instances: int | None,
	unsafe_direct: bool,
) -> None:
	manifest = _learning_general_policies_manifest(root)
	runner = GPBackendRunner(manifest)
	for config in _selected_learning_general_policies_experiments(
		root,
		audit_output_root,
		experiment,
	):
		command = runner.learning_general_policies_command(
			domain_file=config.domain_file,
			problems_directory=config.problems_directory,
			workspace=config.workspace,
			python_executable=root / ".venv" / "bin" / "python",
			width=config.width,
			planner=config.planner,
			max_num_instances=max_num_instances,
		)
		if not unsafe_direct:
			command = runner.guarded_command(
				command,
				label=f"learner-policies-from-examples:{config.name}",
				max_rss_gb=max_rss_gb,
				timeout_seconds=timeout_seconds,
			)
		env_prefix = (
			f"PYTHONPATH={manifest.path / 'learning'} "
			f"LEARNER_POLICIES_FROM_EXAMPLES_DIR={manifest.path}"
		)
		print(f"# {config.name}")
		print(env_prefix, shlex.join(command))


def print_learning_general_policies_docker_build_command(
	root: Path,
	*,
	proxy: str | None = None,
) -> None:
	manifest = _learning_general_policies_manifest(root)
	runner = GPBackendRunner(manifest)
	print(
		shlex.join(
			runner.learning_general_policies_docker_build_command(
				build_args=_docker_proxy_build_args(proxy),
			),
		),
	)


def print_learning_general_policies_docker_commands(
	root: Path,
	*,
	audit_output_root: Path,
	experiment: str,
	max_rss_gb: float,
	timeout_seconds: int | None,
	max_num_instances: int | None,
) -> None:
	manifest = _learning_general_policies_manifest(root)
	runner = GPBackendRunner(manifest)
	for config in _selected_learning_general_policies_experiments(
		root,
		audit_output_root,
		experiment,
	):
		command = runner.learning_general_policies_docker_run_command(
			domain_file=config.domain_file,
			problems_directory=config.problems_directory,
			workspace=config.workspace,
			width=config.width,
			planner=config.planner,
			max_num_instances=max_num_instances,
			max_rss_gb=max_rss_gb,
			timeout_seconds=timeout_seconds,
		)
		print(f"# {config.name}")
		print(shlex.join(command))


def print_learner_sketches_summary(root: Path, *, experiment: str) -> None:
	for config in _selected_learner_sketches_experiments(root, experiment):
		policy_file = config.workspace / "output" / f"sketch_minimized_{config.width}.txt"
		raw_policy_file = config.workspace / "output" / f"sketch_{config.width}.txt"
		if not policy_file.exists():
			print(f"{config.name}: missing; expected={policy_file}")
			continue
		policy = parse_dlplan_policy(policy_file.read_text(encoding="utf-8"))
		raw_policy = (
			parse_dlplan_policy(raw_policy_file.read_text(encoding="utf-8"))
			if raw_policy_file.exists()
			else None
		)
		program = policy_program_from_sketch_policy(
			policy=policy,
			domain_name=config.domain_name,
			source_name=config.name,
			backend_name="learner-sketches",
			policy_file=policy_file,
		)
		print(
			f"{config.name}: present; width={config.width}; "
			f"features={len(policy.features)}; rules={len(policy.parsed_rules)}; "
			f"raw_rules={len(raw_policy.parsed_rules) if raw_policy else 'unknown'}; "
			f"policy={policy_file}; policy_program=ok; "
			f"backend={program.backend_name}; "
			"atomic_asl_compiler=pending_verified_adapter",
		)
		for feature_id, feature_repr in policy.features.items():
			print(f"  feature {feature_id}: {feature_repr}")
		for index, rule in enumerate(policy.parsed_rules, start=1):
			conditions = ", ".join(
				f"{condition.operator} {condition.feature_id}"
				for condition in rule.conditions
			) or "true"
			effects = ", ".join(
				f"{effect.operator} {effect.feature_id}"
				for effect in rule.effects
			) or "none"
			print(f"  rule {index}: if {conditions} then {effects}")


def print_learning_general_policies_summary(
	root: Path,
	*,
	audit_output_root: Path,
	experiment: str,
) -> None:
	for config in _selected_learning_general_policies_experiments(
		root,
		audit_output_root,
		experiment,
	):
		policy_file = discover_learning_general_policies_policy_file(
			config.workspace,
			width=config.width,
		)
		raw_policy_file = discover_learning_general_policies_policy_file(
			config.workspace,
			width=config.width,
			minimized=False,
		)
		if policy_file is None:
			expected = config.workspace / f"output.<uuid>/sketch_minimized_{config.width}.txt"
			print(f"{config.name}: missing; expected={expected}")
			continue
		policy = parse_dlplan_policy(policy_file.read_text(encoding="utf-8"))
		raw_policy = (
			parse_dlplan_policy(raw_policy_file.read_text(encoding="utf-8"))
			if raw_policy_file is not None
			else None
		)
		program = policy_program_from_sketch_policy(
			policy=policy,
			domain_name=config.domain_name,
			source_name=config.name,
			backend_name="learner-policies-from-examples",
			policy_file=policy_file,
		)
		print(
			f"{config.name}: present; width={config.width}; "
			f"features={len(policy.features)}; rules={len(policy.parsed_rules)}; "
			f"raw_rules={len(raw_policy.parsed_rules) if raw_policy else 'unknown'}; "
			f"policy={policy_file}; policy_program=ok; "
			f"backend={program.backend_name}; representation={program.representation}",
		)
		for feature in program.features:
			print(f"  feature {feature.identifier} [{feature.kind}]: {feature.expression}")
		for rule in program.rules:
			conditions = ", ".join(
				f"{operator} {feature_id}"
				for feature_id, operator in rule.conditions
			) or "true"
			effects = ", ".join(
				f"{operator} {feature_id}"
				for feature_id, operator in rule.effects
			) or "none"
			print(f"  rule {rule.name}: if {conditions} then {effects}")


def print_d2l_docker_commands(root: Path) -> None:
	backend = _backend_definition("d2l")
	manifest = discover_backend_manifest(
		root=root,
		name=backend["name"],
		url=backend["url"],
		commit=backend["commit"],
	)
	runner = GPBackendRunner(manifest)
	workspace = PROJECT_ROOT / "tmp" / "gp-backend-audit" / "d2l"
	build_command = (
		"docker",
		"build",
		"--platform",
		"linux/amd64",
		"-t",
		"d2l-official-env:local",
		"-f",
		str(manifest.path / "containers" / "Dockerfile"),
		str(manifest.path),
	)
	print(shlex.join(build_command))
	for experiment in ("blocks:clear", "blocks:on", "blocks:all_at_5"):
		print(
			shlex.join(
				runner.d2l_docker_run_command(
					experiment=experiment,
					workspace=workspace,
				),
			),
		)


def print_policy_summary(policy_file: Path) -> None:
	policy = parse_dlplan_policy(policy_file.read_text(encoding="utf-8"))
	print(f"features={len(policy.features)}")
	print(f"rules={len(policy.rules)}")
	for feature_id, feature_repr in policy.features.items():
		print(f"feature {feature_id}: {feature_repr}")
	for rule in policy.rules:
		print(rule)


def _blocksworld_smoke_config() -> SmokeConfig:
	return SmokeConfig(
		domain_file=PROJECT_ROOT / "src" / "domains" / "blocksworld" / "domain.pddl",
		problems_directory=PROJECT_ROOT / "src" / "domains" / "blocksworld" / "problems",
		workspace=PROJECT_ROOT / "tmp" / "gp-backend-audit" / "blocksworld-learner-sketches",
	)


def _learner_sketches_manifest(root: Path):
	backend = _backend_definition("learner-sketches")
	return discover_backend_manifest(
		root=root,
		name=backend["name"],
		url=backend["url"],
		commit=backend["commit"],
	)


def _learning_general_policies_manifest(root: Path):
	backend = _backend_definition("learner-policies-from-examples")
	return discover_backend_manifest(
		root=root,
		name=backend["name"],
		url=backend["url"],
		commit=backend["commit"],
	)


def _selected_learner_sketches_experiments(
	root: Path,
	experiment: str,
) -> tuple[LearnerSketchesExperiment, ...]:
	experiments = tuple(_learner_sketches_blocksworld_experiments(root))
	if experiment == "all":
		return experiments
	return tuple(config for config in experiments if config.name == experiment)


def _selected_learning_general_policies_experiments(
	root: Path,
	audit_output_root: Path,
	experiment: str,
) -> tuple[LearningGeneralPoliciesExperiment, ...]:
	experiments = tuple(_learning_general_policies_experiments(root, audit_output_root))
	if experiment == "all":
		return experiments
	return tuple(config for config in experiments if config.name == experiment)


def _learner_sketches_blocksworld_experiments(
	root: Path,
) -> Iterable[LearnerSketchesExperiment]:
	backend_path = root / "learner-sketches"
	benchmarks = backend_path / "learning" / "benchmarks"
	audit_root = PROJECT_ROOT / "tmp" / "gp-backend-audit" / "learner-sketches"
	experiment_specs = (
		("tractable", "blocks_4_clear", (0, 1, 2)),
		("tractable", "blocks_4_on", (0, 1, 2)),
		("ipc2023", "blocks_4", (0, 1, 2)),
	)
	for family, domain_name, widths in experiment_specs:
		for width in widths:
			yield LearnerSketchesExperiment(
				name=f"{domain_name}_{width}",
				benchmark_family=family,
				domain_name=domain_name,
				width=width,
				domain_file=benchmarks / family / domain_name / "domain.pddl",
				problems_directory=benchmarks / family / domain_name / "training" / "easy",
				workspace=audit_root / f"{domain_name}_{width}",
			)


def _learning_general_policies_experiments(
	root: Path,
	audit_output_root: Path,
) -> Iterable[LearningGeneralPoliciesExperiment]:
	backend_path = root / "learner-policies-from-examples"
	benchmarks = backend_path / "learning" / "benchmarks"
	audit_root = audit_output_root / "learner-policies-from-examples"
	experiment_specs = (
		("other", "blocks_4_clear", (0,)),
		("other", "blocks_4_on", (0,)),
		("tractable", "blocks_4", (0,)),
		("tractable", "gripper", (0,)),
		("tractable", "miconic", (0,)),
		("tractable", "logistics", (0,)),
		("tractable", "childsnack", (0,)),
		("tractable", "visitall", (0,)),
		("tractable", "ferry", (0,)),
	)
	for family, domain_name, widths in experiment_specs:
		for width in widths:
			yield LearningGeneralPoliciesExperiment(
				name=f"{domain_name}_{width}",
				benchmark_family=family,
				domain_name=domain_name,
				width=width,
				domain_file=benchmarks / family / domain_name / "domain.pddl",
				problems_directory=benchmarks / family / domain_name / "training" / "easy",
				workspace=audit_root / f"{domain_name}_{width}",
			)


def _backend_definition(name: str) -> dict[str, str]:
	for backend in BACKENDS:
		if backend["name"] == name:
			return backend
	raise KeyError(f"Unknown pinned backend: {name}")


def _docker_proxy_build_args(proxy: str | None) -> dict[str, str]:
	if proxy:
		return {
			"HTTP_PROXY": proxy,
			"HTTPS_PROXY": proxy,
			"http_proxy": proxy,
			"https_proxy": proxy,
		}
	build_args: dict[str, str] = {}
	for name in (
		"http_proxy",
		"https_proxy",
		"HTTP_PROXY",
		"HTTPS_PROXY",
		"no_proxy",
		"NO_PROXY",
	):
		value = os.environ.get(name)
		if value:
			build_args[name] = value
	return build_args


def _required_path(value: Path | None, flag: str) -> Path:
	if value is None:
		raise SystemExit(f"{flag} is required for this command")
	return value


def _project_container_path(path: Path) -> str:
	resolved = path.expanduser().resolve()
	try:
		relative = resolved.relative_to(PROJECT_ROOT)
	except ValueError as error:
		raise SystemExit(
			f"MOOSE command paths must live under the project root: {resolved}",
		) from error
	return f"/project/{relative.as_posix()}"


def _guarded_command(
	command: tuple[str, ...],
	*,
	label: str,
	max_rss_gb: float,
	timeout_seconds: int | None,
) -> tuple[str, ...]:
	guarded = [
		sys.executable,
		str(PROJECT_ROOT / "scripts" / "resource_guard.py"),
		"--max-rss-gb",
		str(max_rss_gb),
		"--label",
		label,
	]
	if timeout_seconds is not None:
		guarded.extend(("--timeout-seconds", str(timeout_seconds)))
	guarded.append("--")
	guarded.extend(command)
	return tuple(guarded)


def _run_git(args: tuple[str, ...], *, proxy: str | None = None) -> None:
	env = None
	if proxy:
		env = {
			**os.environ,
			"http_proxy": proxy,
			"https_proxy": proxy,
		}
	subprocess.run(("git", *args), check=True, env=env)


if __name__ == "__main__":
	sys.exit(main())
