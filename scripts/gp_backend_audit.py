#!/usr/bin/env python3
"""
Install and inspect external generalized-planning learner backends.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from domain_level_planning.gp_backends import (
	DEFAULT_BACKEND_ROOT,
	GPBackendRunner,
	discover_backend_manifest,
	parse_dlplan_policy,
)
from domain_level_planning.sketch_pipeline import compile_learner_sketch_policy_to_asl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKENDS = (
	{
		"name": "learner-sketches",
		"url": "https://github.com/bonetblai/learner-sketches.git",
		"commit": "7a7ea6a6356035afa16ed958b53d8edc86994e0a",
	},
	{
		"name": "h-policy-learner",
		"url": "https://github.com/drexlerd/h-policy-learner.git",
		"commit": "03e345537208ab804c1f4958bf183b65d4863a62",
	},
	{
		"name": "d2l",
		"url": "https://github.com/rleap-project/d2l.git",
		"commit": "0620e169c894d79b3c84f435dba1462996f7c270",
	},
)


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


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"command",
		choices=(
			"status",
			"install",
			"install-deps",
			"blocksworld-smoke-command",
			"learner-sketches-command",
			"learner-sketches-compile-asl",
			"learner-sketches-summary",
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
		"--policy-file",
		type=Path,
		help="DLPlan policy file to parse for the parse-policy command.",
	)
	parser.add_argument(
		"--experiment",
		choices=(
			"blocks_4_clear_0",
			"blocks_4_clear_1",
			"blocks_4_clear_2",
			"blocks_4_on_0",
			"blocks_4_on_1",
			"blocks_4_on_2",
			"blocks_4_0",
			"blocks_4_1",
			"blocks_4_2",
			"all",
		),
		default="all",
		help="Official learner-sketches Blocksworld experiment to print or summarize.",
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
		"--unsafe-direct",
		action="store_true",
		help="Print raw paper backend commands without the resource guard.",
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
	if args.command == "blocksworld-smoke-command":
		print_blocksworld_smoke_command(
			args.backend_root,
			max_rss_gb=args.max_rss_gb,
			timeout_seconds=args.timeout_seconds,
			unsafe_direct=args.unsafe_direct,
		)
		return 0
	if args.command == "learner-sketches-command":
		print_learner_sketches_commands(
			args.backend_root,
			experiment=args.experiment,
			max_rss_gb=args.max_rss_gb,
			timeout_seconds=args.timeout_seconds,
			unsafe_direct=args.unsafe_direct,
		)
		return 0
	if args.command == "learner-sketches-compile-asl":
		compile_learner_sketches_asl(args.backend_root, experiment=args.experiment)
		return 0
	if args.command == "learner-sketches-summary":
		print_learner_sketches_summary(args.backend_root, experiment=args.experiment)
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


def print_backend_status(root: Path) -> None:
	for backend in BACKENDS:
		manifest = discover_backend_manifest(
			root=root,
			name=backend["name"],
			url=backend["url"],
			commit=backend["commit"],
		)
		state = "present" if manifest.present else "missing"
		observed = manifest.observed_commit or "unknown"
		pinned = "ok" if observed.startswith(manifest.expected_commit[:12]) else "check"
		print(f"{manifest.name}: {state}; observed={observed}; pinned={pinned}; path={manifest.path}")


def print_blocksworld_smoke_command(
	root: Path,
	*,
	max_rss_gb: float,
	timeout_seconds: int | None,
	unsafe_direct: bool,
) -> None:
	backend = BACKENDS[0]
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
	print(" ".join(command))


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
			python_executable="uv run python",
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
		print(env_prefix, " ".join(command))


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
		binding_status = _learner_sketches_binding_status(
			domain_file=config.domain_file,
			policy_file=policy_file,
		)
		print(
			f"{config.name}: present; width={config.width}; "
			f"features={len(policy.features)}; rules={len(policy.parsed_rules)}; "
			f"raw_rules={len(raw_policy.parsed_rules) if raw_policy else 'unknown'}; "
			f"policy={policy_file}; {binding_status}",
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


def compile_learner_sketches_asl(root: Path, *, experiment: str) -> None:
	for config in _selected_learner_sketches_experiments(root, experiment):
		policy_file = config.workspace / "output" / f"sketch_minimized_{config.width}.txt"
		if not policy_file.exists():
			print(f"{config.name}: missing; expected={policy_file}")
			continue
		output_file = config.workspace / "output" / f"sketch_minimized_{config.width}.asl"
		result = compile_learner_sketch_policy_to_asl(
			domain_file=config.domain_file,
			policy_file=policy_file,
		)
		from plan_library.rendering import render_plan_library_asl

		output_file.write_text(
			render_plan_library_asl(result.plan_library),
			encoding="utf-8",
		)
		print(
			f"{config.name}: compiled; plans={len(result.plan_library.plans)}; "
			f"output={output_file}",
		)


def print_d2l_docker_commands(root: Path) -> None:
	backend = BACKENDS[2]
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
	print(" ".join(build_command))
	for experiment in ("blocks:clear", "blocks:on", "blocks:all_at_5"):
		print(
			" ".join(
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


def _learner_sketches_binding_status(*, domain_file: Path, policy_file: Path) -> str:
	try:
		result = compile_learner_sketch_policy_to_asl(
			domain_file=domain_file,
			policy_file=policy_file,
		)
	except Exception as error:
		return f"binding=blocked ({error})"
	return (
		f"binding=ok; plans={len(result.plan_library.plans)}; "
		f"unsupported_features={len(result.unsupported_features)}"
	)


def _blocksworld_smoke_config() -> SmokeConfig:
	return SmokeConfig(
		domain_file=PROJECT_ROOT / "src" / "domains" / "blocksworld" / "domain.pddl",
		problems_directory=PROJECT_ROOT / "src" / "domains" / "blocksworld" / "problems",
		workspace=PROJECT_ROOT / "tmp" / "gp-backend-audit" / "blocksworld-learner-sketches",
	)


def _learner_sketches_manifest(root: Path):
	backend = BACKENDS[0]
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
