#!/usr/bin/env python3
"""Build the portable GP2PL result bundle used by the paper and public release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import statistics
import sys
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from scripts.public_result_schema import outcome_only_payload  # noqa: E402


ATOMIC_LIBRARY_FILENAMES = (
	"plan_library.asl",
	"plan_library.json",
	"atomic_library_metadata.json",
)
DIAGNOSTIC_PATH_KEYS = {
	"output_dir",
	"neutral_problem_file",
	"stderr",
	"stdout",
}


def build_reproducibility_release(
	*,
	project_root: Path,
	execution_summary_file: Path,
	atomic_library_root: Path,
	challenge_summary_file: Path,
	benchmark_file: Path,
	output_dir: Path,
) -> dict[str, Any]:
	"""Write a path-portable result bundle without copying transient run logs.

	The paper tables need the complete execution outcomes and the atomic
	libraries, but not run-local paths or execution identities.
	"""

	root = project_root.expanduser().resolve()
	execution_path = execution_summary_file.expanduser().resolve()
	atomic_root = atomic_library_root.expanduser().resolve()
	challenge_path = challenge_summary_file.expanduser().resolve()
	benchmark_path = benchmark_file.expanduser().resolve()
	release_root = output_dir.expanduser().resolve()
	if release_root.exists():
		raise ValueError(f"Reproducibility release output already exists: {release_root}")

	execution = _read_json(execution_path)
	challenge = _read_json(challenge_path)
	benchmark = _read_json(benchmark_path)
	if execution.get("benchmark_id") != benchmark.get("benchmark_id"):
		raise ValueError("Execution and release benchmark identifiers differ.")
	atomic_inputs = dict(execution.get("atomic_library_inputs") or {})
	if not atomic_inputs:
		raise ValueError("Execution summary does not identify atomic library inputs.")
	if challenge.get("success") is not True:
		raise ValueError("Certificate challenge matrix is not complete and successful.")

	release_root.mkdir(parents=True)
	release_atomic_root = release_root / "atomic_libraries"
	portable_inputs: dict[str, dict[str, Any]] = {}
	for domain in sorted(atomic_inputs):
		source_domain_root = atomic_root / domain
		target_domain_root = release_atomic_root / domain
		target_domain_root.mkdir(parents=True)
		for filename in ATOMIC_LIBRARY_FILENAMES:
			source = source_domain_root / filename
			if not source.is_file():
				raise FileNotFoundError(f"Missing atomic library file: {source}")
			target = target_domain_root / filename
			if source.suffix == ".json":
				_write_json(target, outcome_only_payload(_read_json(source)))
			else:
				shutil.copy2(source, target)
		portable_inputs[domain] = {
			"plan_library_asl": f"atomic_libraries/{domain}/plan_library.asl",
			"plan_library_json": f"atomic_libraries/{domain}/plan_library.json",
		}

	portable_execution = outcome_only_payload(
		_portable_payload(execution, project_root=root),
	)
	portable_execution["atomic_library_inputs"] = portable_inputs
	portable_challenge = outcome_only_payload(
		_portable_payload(challenge, project_root=root),
	)
	_write_json(release_root / "temporal_execution_summary.json", portable_execution)
	_write_json(release_root / "certificate_challenge_summary.json", portable_challenge)
	distribution = _execution_distribution(tuple(execution.get("results") or ()))
	_write_json(release_root / "execution_distribution.json", distribution)
	(release_root / "README.md").write_text(
		_release_readme(
			benchmark_file=_repository_relative_path(benchmark_path, project_root=root),
		),
		encoding="utf-8",
	)

	files = [
		str(path.relative_to(release_root))
		for path in sorted(release_root.rglob("*"))
		if path.is_file()
	]
	manifest = {
		"schema_version": 1,
		"artifact_kind": "gp2pl_reproducibility_release",
		"domain_count": len(atomic_inputs),
		"result_count": len(tuple(execution.get("results") or ())),
		"challenge_case_count": len(tuple(challenge.get("records") or ())),
		"files": files,
	}
	_write_json(release_root / "manifest.json", manifest)
	return manifest


def _portable_payload(payload: Any, *, project_root: Path, key: str | None = None) -> Any:
	if isinstance(payload, Mapping):
		return {
			str(item_key): _portable_payload(
				item_value,
				project_root=project_root,
				key=str(item_key),
			)
			for item_key, item_value in payload.items()
		}
	if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
		return [
			_portable_payload(item, project_root=project_root, key=key) for item in payload
		]
	if not isinstance(payload, str):
		return payload
	if key in DIAGNOSTIC_PATH_KEYS and _contains_project_path(payload, project_root):
		return None
	return payload.replace(f"{project_root}/", "")


def _contains_project_path(value: str, project_root: Path) -> bool:
	return value == str(project_root) or f"{project_root}/" in value


def _repository_relative_path(path: Path, *, project_root: Path) -> str:
	try:
		return str(path.relative_to(project_root))
	except ValueError as error:
		raise ValueError(f"Release input path is outside the project root: {path}") from error


def _execution_distribution(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
	durations = [float(row["duration_seconds"]) for row in results]
	actions = [int(row["action_count"]) for row in results]
	return {
		"result_count": len(results),
		"duration_seconds": _distribution(durations),
		"action_count": _distribution(actions),
	}


def _distribution(values: Sequence[float | int]) -> dict[str, float | int | None]:
	if not values:
		return {
			"minimum": None,
			"first_quartile": None,
			"median": None,
			"third_quartile": None,
			"maximum": None,
			"mean": None,
			"sample_standard_deviation": None,
		}
	quartiles = (
		statistics.quantiles(values, n=4, method="inclusive")
		if len(values) > 1
		else [values[0], values[0], values[0]]
	)
	return {
		"minimum": min(values),
		"first_quartile": quartiles[0],
		"median": statistics.median(values),
		"third_quartile": quartiles[2],
		"maximum": max(values),
		"mean": statistics.mean(values),
		"sample_standard_deviation": statistics.stdev(values) if len(values) > 1 else 0.0,
	}


def _release_readme(
	*,
	benchmark_file: str,
) -> str:
	return f"""# GP2PL Evaluation Release

This directory contains the fixed atomic libraries and compact result records
used by the reported evaluation. The temporal benchmark is `{benchmark_file}`.

- `atomic_libraries/` contains the exact structured and AgentSpeak(L) libraries.
- `temporal_execution_summary.json` contains one record for every bound query.
- `certificate_challenge_summary.json` records fail-closed and renaming tests.
- `execution_distribution.json` records distributional execution statistics.
- `manifest.json` lists the public files and result counts.

Run identifiers, source revisions, byte digests, transient Jason logs, and
machine-local paths are intentionally excluded. Public records contain outcomes
and the experimental parameters needed to interpret them.
"""


def _read_json(path: Path) -> dict[str, Any]:
	return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		json.dumps(payload, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--execution-summary", type=Path, required=True)
	parser.add_argument("--atomic-library-root", type=Path, required=True)
	parser.add_argument("--challenge-summary", type=Path, required=True)
	parser.add_argument("--benchmark-file", type=Path, required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	manifest = build_reproducibility_release(
		project_root=PROJECT_ROOT,
		execution_summary_file=args.execution_summary,
		atomic_library_root=args.atomic_library_root,
		challenge_summary_file=args.challenge_summary,
		benchmark_file=args.benchmark_file,
		output_dir=args.output_dir,
	)
	print(
		"[done] "
		f"domains={manifest['domain_count']} "
		f"results={manifest['result_count']} "
		f"output={args.output_dir}",
		flush=True,
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
