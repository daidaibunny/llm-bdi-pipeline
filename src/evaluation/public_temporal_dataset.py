"""Integrity and portability checks for the public GP2PL TEG benchmark."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
from typing import Any, Mapping, Sequence


_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_MACHINE_PATH_MARKERS = ("/Users/", "/home/", "/private/tmp/", "file://")


def find_nonportable_metadata_paths(root: str | Path) -> tuple[str, ...]:
	"""Return machine-local path locations in published JSON and source archives."""

	release_root = Path(root).resolve()
	findings: list[str] = []
	for path in sorted(release_root.rglob("*")):
		if not path.is_file():
			continue
		relative = path.relative_to(release_root).as_posix()
		if path.suffix == ".json":
			payload = json.loads(path.read_text(encoding="utf-8"))
			_find_payload_paths(payload, prefix=relative, findings=findings)
		elif path.suffix == ".jsonl":
			for line_number, line in enumerate(
				path.read_text(encoding="utf-8").splitlines(),
				start=1,
			):
				if not line.strip():
					continue
				payload = json.loads(line)
				_find_payload_paths(
					payload,
					prefix=f"{relative}:{line_number}",
					findings=findings,
				)
		elif path.name.endswith(".tar.gz"):
			_find_archive_paths(path, relative=relative, findings=findings)
	return tuple(sorted(findings))


def verify_public_temporal_dataset(root: str | Path) -> dict[str, object]:
	"""Fail closed unless the public TEG release is complete and portable."""

	release_root = Path(root).resolve()
	findings = find_nonportable_metadata_paths(release_root)
	if findings:
		raise ValueError(
			"Public TEG release contains a machine-local absolute path: "
			+ "; ".join(findings[:5]),
		)
	required = (
		"README.md",
		"LICENSE.md",
		"CITATION.cff",
		"benchmark.json",
		"manifest.json",
		"release_validation.json",
		"model_run/run_config.json",
		"model_run/translation_predictions.jsonl",
		"model_run/translation_predictions.sha256",
		"validation/summary.json",
		"validation/translation_validation_results.jsonl",
		"validation/problem_validation_results.jsonl",
		"source/SHA256SUMS",
	)
	missing = [name for name in required if not (release_root / name).is_file()]
	if missing:
		raise ValueError(f"Public TEG release is missing required files: {missing}")

	manifest = _read_json(release_root / "manifest.json")
	benchmark = _read_json(release_root / str(manifest.get("benchmark_file")))
	release_validation = _read_json(release_root / "release_validation.json")
	benchmark_hash = _sha256(release_root / str(manifest.get("benchmark_file")))
	_require_equal(benchmark_hash, manifest.get("benchmark_sha256"), "benchmark hash")
	_require_equal(
		benchmark_hash,
		release_validation.get("benchmark_sha256"),
		"release-validation benchmark hash",
	)
	_require_equal(
		_sha256(release_root / "manifest.json"),
		release_validation.get("release_manifest_sha256"),
		"release manifest hash",
	)
	_require_equal(
		benchmark.get("benchmark_id"),
		manifest.get("benchmark_id"),
		"benchmark id",
	)
	counts = benchmark.get("counts")
	if not isinstance(counts, Mapping):
		raise ValueError("Benchmark counts must be an object.")
	_require_equal(dict(counts), manifest.get("counts"), "manifest counts")
	validation_summary = _read_json(release_root / "validation/summary.json")
	_require_equal(
		validation_summary.get("translation_total"),
		counts.get("unique_translation_input_count"),
		"validation translation total",
	)
	_require_equal(
		validation_summary.get("translation_success_count"),
		counts.get("translation_equivalent_count"),
		"validation translation success count",
	)
	_require_equal(
		validation_summary.get("problem_total"),
		counts.get("problem_case_count"),
		"validation problem total",
	)
	_require_equal(
		validation_summary.get("problem_success_count"),
		counts.get("witness_accepted_count"),
		"validation problem success count",
	)
	domains = benchmark.get("domains")
	entries = manifest.get("domain_datasets")
	if not isinstance(domains, Mapping) or not isinstance(entries, Sequence):
		raise ValueError("Benchmark domains or domain manifest is malformed.")
	if len(domains) != int(counts.get("domain_count") or -1):
		raise ValueError("Domain count does not match benchmark contents.")
	case_count = 0
	translation_ids: set[str] = set()
	for entry in entries:
		if not isinstance(entry, Mapping):
			raise ValueError("Domain manifest entry must be an object.")
		domain = str(entry.get("domain") or "")
		path = release_root / str(entry.get("path") or "")
		if domain not in domains or not path.is_file():
			raise ValueError(f"Missing domain dataset for {domain!r}.")
		_require_equal(_sha256(path), entry.get("sha256"), f"{domain} dataset hash")
		domain_payload = domains[domain]
		if not isinstance(domain_payload, Mapping):
			raise ValueError(f"Malformed benchmark domain {domain!r}.")
		cases = domain_payload.get("cases")
		if not isinstance(cases, Mapping):
			raise ValueError(f"Malformed benchmark cases for {domain!r}.")
		_require_equal(len(cases), entry.get("case_count"), f"{domain} case count")
		case_count += len(cases)
		for case in cases.values():
			if not isinstance(case, Mapping):
				raise ValueError(f"Malformed benchmark case in {domain!r}.")
			translation_ids.add(str(case.get("translation_id") or ""))
	_require_equal(case_count, counts.get("problem_case_count"), "problem case count")
	_require_equal(
		len(translation_ids),
		counts.get("unique_translation_input_count"),
		"translation input count",
	)

	predictions = release_root / "model_run/translation_predictions.jsonl"
	prediction_hash = _sha256(predictions)
	declared_prediction_hash = (
		(release_root / "model_run/translation_predictions.sha256")
		.read_text(encoding="utf-8")
		.split()[0]
	)
	model_run = _read_json(release_root / "model_run/run_config.json")
	_require_equal(prediction_hash, declared_prediction_hash, "prediction digest file")
	_require_equal(
		prediction_hash,
		model_run.get("translation_predictions_sha256"),
		"model run prediction hash",
	)
	_require_equal(
		prediction_hash,
		release_validation.get("frozen_predictions_sha256"),
		"release-validation prediction hash",
	)
	_require_equal(
		_count_jsonl_rows(predictions),
		counts.get("unique_translation_input_count"),
		"prediction row count",
	)
	validation_provenance = dict(
		dict(benchmark.get("provenance") or {}).get("independent_validation") or {},
	)
	translation_results = (
		release_root / "validation/translation_validation_results.jsonl"
	)
	problem_results = release_root / "validation/problem_validation_results.jsonl"
	_require_equal(
		_sha256(translation_results),
		validation_provenance.get("translation_results_sha256"),
		"translation validation hash",
	)
	_require_equal(
		_sha256(problem_results),
		validation_provenance.get("problem_results_sha256"),
		"problem validation hash",
	)
	_require_equal(
		_count_jsonl_rows(translation_results),
		counts.get("unique_translation_input_count"),
		"translation validation row count",
	)
	_require_equal(
		_count_jsonl_rows(problem_results),
		counts.get("problem_case_count"),
		"problem validation row count",
	)
	comparison = release_validation.get("delivered_validation_matches_independent")
	if not isinstance(comparison, Mapping) or not comparison or not all(
		value is True for value in comparison.values()
	):
		raise ValueError("Independent release-validation comparisons did not all pass.")

	archive_hashes = _read_sha256s(release_root / "source/SHA256SUMS")
	for filename, expected_hash in archive_hashes.items():
		archive = release_root / "source" / filename
		if not archive.is_file():
			raise ValueError(f"Missing source archive {filename!r}.")
		_require_equal(_sha256(archive), expected_hash, f"source archive {filename}")
	for provenance in (
		manifest.get("source_delivery_archive"),
		*dict(manifest.get("sealed_input_archives") or {}).values(),
	):
		if not isinstance(provenance, Mapping):
			raise ValueError("Source archive provenance is malformed.")
		filename = str(provenance.get("filename") or "")
		_require_equal(
			archive_hashes.get(filename),
			provenance.get("sha256"),
			f"manifest source archive {filename}",
		)

	license_text = (release_root / "LICENSE.md").read_text(encoding="utf-8")
	if "CC BY 4.0" not in license_text:
		raise ValueError("Dataset license must identify CC BY 4.0.")
	citation_text = (release_root / "CITATION.cff").read_text(encoding="utf-8")
	if "type: dataset" not in citation_text:
		raise ValueError("Dataset CITATION.cff must identify a dataset.")
	return {
		"benchmark_id": str(benchmark.get("benchmark_id")),
		"domain_count": int(counts["domain_count"]),
		"problem_case_count": int(counts["problem_case_count"]),
		"unique_translation_input_count": int(
			counts["unique_translation_input_count"],
		),
	}


def _find_payload_paths(value: Any, *, prefix: str, findings: list[str]) -> None:
	if isinstance(value, Mapping):
		for key, item in value.items():
			_find_payload_paths(item, prefix=f"{prefix}:{key}", findings=findings)
	elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
		for index, item in enumerate(value):
			_find_payload_paths(item, prefix=f"{prefix}[{index}]", findings=findings)
	elif isinstance(value, str) and _is_machine_local_path(value):
		findings.append(f"{prefix}={value}")


def _find_archive_paths(path: Path, *, relative: str, findings: list[str]) -> None:
	with tarfile.open(path, mode="r:gz") as bundle:
		for member in bundle.getmembers():
			member_path = PurePosixPath(member.name)
			if member_path.is_absolute() or ".." in member_path.parts:
				findings.append(f"{relative}:{member.name}=unsafe_archive_member")
				continue
			if member.issym() or member.islnk():
				findings.append(f"{relative}:{member.name}=archive_link")
				continue
			if not member.isfile() or member.size > 10_000_000:
				continue
			extracted = bundle.extractfile(member)
			if extracted is None:
				continue
			try:
				text = extracted.read().decode("utf-8")
			except UnicodeDecodeError:
				continue
			if member.name.endswith(".json"):
				payload = json.loads(text)
				_find_payload_paths(
					payload,
					prefix=f"{relative}:{member.name}",
					findings=findings,
				)
			elif member.name.endswith(".jsonl"):
				for line_number, line in enumerate(text.splitlines(), start=1):
					if not line.strip():
						continue
					payload = json.loads(line)
					_find_payload_paths(
						payload,
						prefix=f"{relative}:{member.name}:{line_number}",
						findings=findings,
					)
			elif any(marker in text for marker in _MACHINE_PATH_MARKERS):
				findings.append(f"{relative}:{member.name}=machine_local_text")


def _is_machine_local_path(value: str) -> bool:
	stripped = value.strip()
	return (
		stripped.startswith("/")
		or bool(_WINDOWS_ABSOLUTE_PATH.match(stripped))
		or any(marker in stripped for marker in _MACHINE_PATH_MARKERS)
	)


def _read_json(path: Path) -> dict[str, Any]:
	payload = json.loads(path.read_text(encoding="utf-8"))
	if not isinstance(payload, dict):
		raise ValueError(f"Expected JSON object in {path}.")
	return payload


def _read_sha256s(path: Path) -> dict[str, str]:
	result: dict[str, str] = {}
	for line in path.read_text(encoding="utf-8").splitlines():
		if not line.strip():
			continue
		digest, filename = line.split(maxsplit=1)
		result[filename.strip()] = digest.strip().lower()
	return result


def _count_jsonl_rows(path: Path) -> int:
	return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _require_equal(actual: object, expected: object, label: str) -> None:
	if actual != expected:
		raise ValueError(f"{label} mismatch: actual={actual!r}, expected={expected!r}")


def _sha256(path: str | Path) -> str:
	return hashlib.sha256(Path(path).read_bytes()).hexdigest()
