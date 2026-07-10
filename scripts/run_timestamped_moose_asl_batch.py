#!/usr/bin/env python3
"""Run a timestamped MOOSE-native ASL-library generation batch."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence

try:
	from run_moose_faithful_e2e import DEFAULT_DOMAINS
	from run_moose_faithful_e2e import MOOSE_PAPER_GOAL_PERMUTATIONS
	from run_moose_faithful_e2e import MOOSE_PAPER_PLANNING_TIMEOUT_SECONDS
	from run_moose_faithful_e2e import MOOSE_PAPER_SYNTHESIS_TIMEOUT_SECONDS
	from run_moose_faithful_e2e import MOOSE_ROOT
	from run_moose_faithful_e2e import PROJECT_ROOT
except ModuleNotFoundError:  # pragma: no cover - used when imported by pytest.
	from scripts.run_moose_faithful_e2e import DEFAULT_DOMAINS
	from scripts.run_moose_faithful_e2e import MOOSE_PAPER_GOAL_PERMUTATIONS
	from scripts.run_moose_faithful_e2e import MOOSE_PAPER_PLANNING_TIMEOUT_SECONDS
	from scripts.run_moose_faithful_e2e import MOOSE_PAPER_SYNTHESIS_TIMEOUT_SECONDS
	from scripts.run_moose_faithful_e2e import MOOSE_ROOT
	from scripts.run_moose_faithful_e2e import PROJECT_ROOT


DEFAULT_ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "moose_asl_batches"


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--domain",
		action="append",
		help="Domain to run. Repeat to run multiple domains. Defaults to all selected domains.",
	)
	parser.add_argument(
		"--artifact-root",
		type=Path,
		default=DEFAULT_ARTIFACT_ROOT,
		help="Root for timestamped ASL batch outputs.",
	)
	parser.add_argument(
		"--timestamp-id",
		help="Stable output id. Defaults to local timestamp YYYYmmdd-HHMMSS.",
	)
	parser.add_argument("--num-workers", type=int, default=4)
	parser.add_argument(
		"--num-permutations",
		type=int,
		default=MOOSE_PAPER_GOAL_PERMUTATIONS,
		help="Goal orderings per problem; Algorithm 1 in the MOOSE paper defaults to 3.",
	)
	parser.add_argument("--goal-max-size", type=int, default=1)
	parser.add_argument(
		"--atomic-library-mode",
		choices=("faithful", "validated-policy-lifting"),
		default="faithful",
		help=(
			"Compile raw MOOSE decision-list macros faithfully, or validate and "
			"lift MOOSE singleton policy evidence with the PDDL schema before "
			"ASL rendering."
		),
	)
	parser.add_argument("--max-rss-gb", type=float, default=16.0)
	parser.add_argument(
		"--train-timeout-seconds",
		type=int,
		default=MOOSE_PAPER_SYNTHESIS_TIMEOUT_SECONDS,
		help="MOOSE synthesis wall-clock cap; the paper uses 12 hours.",
	)
	parser.add_argument("--dump-timeout-seconds", type=int, default=300)
	parser.add_argument("--append-timeout-seconds", type=int, default=300)
	parser.add_argument("--jason-timeout-seconds", type=int, default=1800)
	parser.add_argument(
		"--moose-plan-timeout-seconds",
		type=int,
		default=MOOSE_PAPER_PLANNING_TIMEOUT_SECONDS,
		help="MOOSE test-time planning cap; the paper uses 1800 seconds.",
	)
	parser.add_argument("--moose-plan-bound", type=int, default=5000)
	parser.add_argument(
		"--jason-plan-verifier-command",
		help="Optional VAL or IPC verifier command for Jason-exported PDDL traces.",
	)
	parser.add_argument(
		"--require-jason-plan-verifier",
		action="store_true",
		help="Require Jason-exported PDDL plan traces to pass VAL/IPC verification.",
	)
	parser.add_argument(
		"--jason-plan-verifier-timeout-seconds",
		type=int,
		default=1800,
		help="Hard timeout for VAL/IPC verification of Jason-exported traces.",
	)
	parser.add_argument(
		"--run-jason-validation",
		action="store_true",
		help="Also execute appended goals in Jason. Default only generates ASL artifacts.",
	)
	parser.add_argument(
		"--run-moose-policy-validation",
		action="store_true",
		help="Also execute MOOSE's own learned policy on two selected test problems.",
	)
	parser.add_argument(
		"--skip-temporal-append",
		action="store_true",
		help=(
			"Generate atomic ASL libraries only. This is the expected first stage "
			"for full-test Jason/VAL validation batches."
		),
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Write manifest and print the command without running MOOSE.",
	)
	parser.add_argument(
		"--overwrite",
		action="store_true",
		help="Allow reusing an existing timestamp output directory.",
	)
	args = parser.parse_args()
	args.atomic_library_mode = normalise_atomic_library_mode(args.atomic_library_mode)

	domains = tuple(args.domain or DEFAULT_DOMAINS)
	timestamp_id = args.timestamp_id or datetime.now().strftime("%Y%m%d-%H%M%S")
	batch_root = args.artifact_root.expanduser().resolve() / timestamp_id
	preflight_errors = preflight(domains=domains, batch_root=batch_root, overwrite=args.overwrite)
	if preflight_errors:
		for error in preflight_errors:
			print(f"preflight_error: {error}", file=sys.stderr)
		return 2

	command = build_moose_batch_command(args=args, domains=domains, batch_root=batch_root)
	manifest = batch_manifest(
		args=args,
		domains=domains,
		timestamp_id=timestamp_id,
		batch_root=batch_root,
		command=command,
	)
	batch_root.mkdir(parents=True, exist_ok=True)
	write_manifest(batch_root, manifest)
	print(json.dumps(manifest, indent=2, sort_keys=True))
	if args.dry_run:
		return 0

	completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
	manifest["completed_return_code"] = completed.returncode
	manifest["completed_at"] = datetime.now().isoformat(timespec="seconds")
	write_manifest(batch_root, manifest)
	return completed.returncode


def preflight(*, domains: Sequence[str], batch_root: Path, overwrite: bool) -> list[str]:
	"""Validate local inputs before starting a long MOOSE batch."""

	errors: list[str] = []
	if batch_root.exists() and not overwrite:
		errors.append(f"output directory already exists: {batch_root}")
	if shutil.which("docker") is None:
		errors.append("Docker is required for the MOOSE exact runtime.")
	else:
		image_check = subprocess.run(
			("docker", "image", "ls", "--format", "{{.Repository}}:{{.Tag}}"),
			check=False,
			capture_output=True,
			text=True,
		)
		images = set(image_check.stdout.splitlines())
		if image_check.returncode != 0 or "moose-exact-ubuntu22:local" not in images:
			errors.append("missing Docker image: moose-exact-ubuntu22:local")
	if not (MOOSE_ROOT / "moose.sif").exists():
		errors.append(f"missing MOOSE artifact image: {MOOSE_ROOT / 'moose.sif'}")
	for domain in domains:
		domain_root = PROJECT_ROOT / "src" / "domains" / domain
		domain_file = domain_root / "domain.pddl"
		train_dir = domain_root / "train"
		test_dir = domain_root / "test"
		if not domain_file.exists():
			errors.append(f"{domain}: missing domain.pddl")
			continue
		train_count = len(tuple(train_dir.glob("*.pddl")))
		test_count = len(tuple(test_dir.glob("*.pddl")))
		if train_count < 1:
			errors.append(f"{domain}: train split is empty")
		if test_count < 2:
			errors.append(f"{domain}: test split must contain at least two PDDL problems")
	return errors


def build_moose_batch_command(
	*,
	args: argparse.Namespace,
	domains: Sequence[str],
	batch_root: Path,
) -> list[str]:
	"""Build the underlying MOOSE-native generation command."""

	command = [
		sys.executable,
		str(PROJECT_ROOT / "scripts" / "run_moose_faithful_e2e.py"),
		"--output-root",
		str(batch_root / "run_logs"),
		"--library-root",
		str(batch_root / "domain_libraries"),
		"--moose-runtime",
		"docker",
		"--num-workers",
		str(args.num_workers),
		"--num-permutations",
		str(args.num_permutations),
		"--goal-max-size",
		str(args.goal_max_size),
		"--atomic-library-mode",
		args.atomic_library_mode,
		"--max-rss-gb",
		str(args.max_rss_gb),
		"--train-timeout-seconds",
		str(args.train_timeout_seconds),
		"--dump-timeout-seconds",
		str(args.dump_timeout_seconds),
		"--append-timeout-seconds",
		str(args.append_timeout_seconds),
		"--jason-timeout-seconds",
		str(args.jason_timeout_seconds),
		"--moose-plan-timeout-seconds",
		str(args.moose_plan_timeout_seconds),
		"--moose-plan-bound",
		str(args.moose_plan_bound),
		"--jason-plan-verifier-timeout-seconds",
		str(getattr(args, "jason_plan_verifier_timeout_seconds", 1800)),
	]
	jason_plan_verifier_command = getattr(args, "jason_plan_verifier_command", None)
	if jason_plan_verifier_command:
		command.extend(("--jason-plan-verifier-command", jason_plan_verifier_command))
	if getattr(args, "require_jason_plan_verifier", False):
		command.append("--require-jason-plan-verifier")
	for domain in domains:
		command.extend(("--domain", domain))
	if not args.run_jason_validation:
		command.append("--skip-jason-validation")
	if not args.run_moose_policy_validation:
		command.append("--skip-moose-policy-validation")
	if args.skip_temporal_append:
		command.append("--skip-temporal-append")
	return command


def batch_manifest(
	*,
	args: argparse.Namespace,
	domains: Sequence[str],
	timestamp_id: str,
	batch_root: Path,
	command: Sequence[str],
) -> dict[str, object]:
	"""Return a machine-readable manifest for locating generated ASL libraries."""

	return {
		"artifact_kind": "timestamped_moose_native_asl_batch",
		"timestamp_id": timestamp_id,
		"created_at": datetime.now().isoformat(timespec="seconds"),
		"batch_root": str(batch_root),
		"run_logs": str(batch_root / "run_logs"),
		"domain_library_root": str(batch_root / "domain_libraries"),
		"domains": list(domains),
		"expected_asl_files": [
			str(batch_root / "domain_libraries" / domain / "plan_library.asl")
			for domain in domains
		],
		"settings": {
			"num_workers": args.num_workers,
			"num_permutations": args.num_permutations,
			"goal_max_size": args.goal_max_size,
			"atomic_library_mode": args.atomic_library_mode,
			"max_rss_gb": args.max_rss_gb,
			"train_timeout_seconds": args.train_timeout_seconds,
			"run_jason_validation": bool(args.run_jason_validation),
			"run_moose_policy_validation": bool(args.run_moose_policy_validation),
			"temporal_append_in_stage1": not bool(args.skip_temporal_append),
			"test_query_count_per_domain": 0 if args.skip_temporal_append else 2,
			"domain_execution": "sequential",
			"moose_runtime": "docker_exact_apptainer",
			"atomic_library_backend": (
				"validated_policy_lifting_and_asl_compilation"
				if args.atomic_library_mode == "validated-policy-lifting"
				else "native_moose_train_dump_policy"
			),
		},
		"command": list(command),
	}


def normalise_atomic_library_mode(mode: str) -> str:
	"""Return the configured atomic library mode."""

	return mode


def write_manifest(batch_root: Path, manifest: dict[str, object]) -> None:
	(batch_root / "batch_manifest.json").write_text(
		json.dumps(manifest, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


if __name__ == "__main__":
	raise SystemExit(main())
