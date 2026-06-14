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

from domain_level_planning.gp_backends import (
	DEFAULT_BACKEND_ROOT,
	GPBackendRunner,
	discover_backend_manifest,
	parse_dlplan_policy,
)


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


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"command",
		choices=(
			"status",
			"install",
			"install-deps",
			"blocksworld-smoke-command",
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
	parser.add_argument("--proxy", help="Optional HTTP/HTTPS proxy for GitHub access.")
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
		print_blocksworld_smoke_command(args.backend_root)
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


def print_blocksworld_smoke_command(root: Path) -> None:
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
	print(" ".join(command))


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
