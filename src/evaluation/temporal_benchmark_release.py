"""Reproduce a canonical TEG benchmark release from sealed source archives."""

from __future__ import annotations

import hashlib
import gzip
import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from contextlib import nullcontext
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any
from typing import Callable
from typing import Mapping

from .temporal_benchmark import write_temporal_goal_benchmark
from .temporal_validation_batch import run_temporal_goal_validation_batch


def build_temporal_benchmark_release(
	*,
	delivery_archive: str | Path,
	delivery_archive_sha256: str,
	delivery_archive_origin_sha256: str | None = None,
	public_handoff_archive: str | Path,
	public_handoff_archive_sha256: str,
	private_validation_archive: str | Path,
	private_validation_archive_sha256: str,
	benchmark_id: str,
	run_id: str,
	output_dir: str | Path,
	project_root: str | Path,
	domains_root: str | Path,
	mona_bin: str | Path,
	validation_implementation_commit: str,
	progress: Callable[[str], None] | None = None,
	work_dir: str | Path | None = None,
	reuse_independent_validation: bool = False,
) -> dict[str, object]:
	"""Independently validate a frozen model run and emit its tracked benchmark."""

	delivery = _verified_file(delivery_archive, delivery_archive_sha256)
	public = _verified_file(public_handoff_archive, public_handoff_archive_sha256)
	private = _verified_file(private_validation_archive, private_validation_archive_sha256)
	project = Path(project_root).resolve()
	domains = Path(domains_root).resolve()
	output = Path(output_dir).resolve()
	for reserved in (
		"benchmark.json",
		"manifest.json",
		"domains",
		"model_run",
		"validation",
		"release_validation.json",
		"source",
	):
		if (output / reserved).exists():
			raise ValueError(f"Refusing to overwrite existing release artifact: {output / reserved}")
	output.mkdir(parents=True, exist_ok=True)
	source_output = output / "source"
	source_output.mkdir()
	portable_delivery = source_output / delivery.name
	normalization = write_portable_delivery_archive(
		source_archive=delivery,
		destination_archive=portable_delivery,
		benchmark_id=benchmark_id,
		run_id=run_id,
	)
	published_public = source_output / public.name
	published_private = source_output / private.name
	shutil.copyfile(public, published_public)
	shutil.copyfile(private, published_private)
	origin_sha256 = _validated_sha256(
		delivery_archive_origin_sha256 or delivery_archive_sha256,
		label="delivery_archive_origin_sha256",
	)
	published_archives = (portable_delivery, published_private, published_public)
	(source_output / "SHA256SUMS").write_text(
		"".join(f"{_sha256(path)}  {path.name}\n" for path in sorted(published_archives)),
		encoding="utf-8",
	)
	mona = Path(mona_bin).resolve()
	if not mona.is_file():
		raise ValueError(f"MONA executable does not exist: {mona}")

	workspace_context = (
		nullcontext(str(Path(work_dir).resolve()))
		if work_dir is not None
		else tempfile.TemporaryDirectory(prefix="teg-benchmark-release-")
	)
	with workspace_context as temporary:
		workspace = Path(temporary)
		workspace.mkdir(parents=True, exist_ok=True)
		for archive in published_archives:
			safe_extract_tar(archive, workspace)
		handoff_root = (
			workspace / "artifacts/temporal_nl_handoffs" / benchmark_id
		)
		private_root = (
			workspace / "artifacts/temporal_nl_benchmarks" / benchmark_id
		)
		delivery_root = workspace / "artifacts/temporal_predictions" / run_id
		for required in (handoff_root, private_root, delivery_root):
			if not required.is_dir():
				raise ValueError(f"Sealed archive is missing expected directory {required}.")
		predictions_file = delivery_root / "translation_predictions.jsonl"
		prediction_sha256 = _sha256(predictions_file)
		declared_prediction_sha256 = _declared_prediction_sha256(
			delivery_root / "translation_predictions.sha256",
		)
		if prediction_sha256 != declared_prediction_sha256:
			raise ValueError("Frozen prediction SHA-256 differs from its declared digest.")

		independent_output = workspace / "independent_validation"
		if reuse_independent_validation:
			_validate_reusable_independent_output(independent_output)
			summary = _read_json(independent_output / "summary.json")
		else:
			previous_mona = os.environ.get("MONA_BIN")
			os.environ["MONA_BIN"] = str(mona)
			try:
				summary = run_temporal_goal_validation_batch(
					handoff_root=handoff_root,
					benchmark_root=private_root,
					predictions_file=predictions_file,
					output_dir=independent_output,
					project_root=project,
					domains_root=domains,
					progress=progress,
				)
			finally:
				if previous_mona is None:
					os.environ.pop("MONA_BIN", None)
				else:
					os.environ["MONA_BIN"] = previous_mona
		if summary.get("translation_success_count") != summary.get("translation_total"):
			raise ValueError("Independent translation validation did not pass completely.")
		if summary.get("problem_success_count") != summary.get("problem_total"):
			raise ValueError("Independent witness validation did not pass completely.")
		delivered_validation = delivery_root / "goal_validation"
		comparison = compare_validation_outputs(
			delivered_validation=delivered_validation,
			independent_validation=independent_output,
		)
		if not all(comparison.values()):
			raise ValueError(
				"Delivered validation differs from independent reproduction: "
				f"{comparison}.",
			)

		manifest = write_temporal_goal_benchmark(
			handoff_manifest_file=handoff_root / "handoff_manifest.json",
			manifest_file=handoff_root / "natural_language_manifest.jsonl",
			worklist_file=handoff_root / "translation_worklist.jsonl",
			predictions_file=predictions_file,
			translation_results_file=(
				independent_output / "translation_validation_results.jsonl"
			),
			problem_results_file=independent_output / "problem_validation_results.jsonl",
			validated_append_datasets_dir=(
				independent_output / "validated_append_datasets"
			),
			domains_root=domains,
			source_delivery_archive={
				"filename": portable_delivery.name,
				"sha256": _sha256(portable_delivery),
				"normalization": {
					"method": "release_relative_metadata_paths_v1",
					"source_sha256": origin_sha256,
					"normalized_files": normalization["normalized_files"],
				},
			},
			sealed_input_archives={
				"public_handoff": {
					"filename": published_public.name,
					"sha256": _sha256(published_public),
				},
				"private_validation": {
					"filename": published_private.name,
					"sha256": _sha256(published_private),
				},
			},
			validation_implementation_commit=validation_implementation_commit,
			output_dir=output,
		)
		model_run_output = output / "model_run"
		model_run_output.mkdir()
		for filename in (
			"translation_predictions.jsonl",
			"translation_predictions.sha256",
			"DELIVERY.md",
		):
			shutil.copyfile(delivery_root / filename, model_run_output / filename)
		model_run_config = _portable_metadata_value(
			_read_json(delivery_root / "run_config.json"),
			member_name=f"artifacts/temporal_predictions/{run_id}/run_config.json",
			benchmark_id=benchmark_id,
		)
		if not isinstance(model_run_config, Mapping):
			raise ValueError("Published model run configuration must be an object.")
		_write_json(model_run_output / "run_config.json", model_run_config)
		validation_output = output / "validation"
		validation_output.mkdir()
		for filename in (
			"translation_validation_results.jsonl",
			"problem_validation_results.jsonl",
		):
			shutil.copyfile(independent_output / filename, validation_output / filename)
		published_summary = dict(summary)
		published_summary["validated_append_dataset_root"] = "domains"
		_write_json(validation_output / "summary.json", published_summary)

		report = {
			"schema_version": 1,
			"artifact_kind": "temporal_goal_benchmark_release_validation",
			"benchmark_id": benchmark_id,
			"source_archive_sha256_verified": True,
			"published_source_archives": {
				path.name: _sha256(path) for path in published_archives
			},
			"delivery_archive_normalization": {
				"method": "release_relative_metadata_paths_v1",
				"source_sha256": origin_sha256,
				"normalized_files": normalization["normalized_files"],
			},
			"frozen_predictions_sha256": prediction_sha256,
			"delivered_validation_matches_independent": comparison,
			"independent_summary": _normalized_summary(summary),
			"mona": {
				"sha256": _sha256(mona),
				"version": _mona_version(mona),
			},
			"release_manifest_sha256": _sha256(output / "manifest.json"),
			"benchmark_sha256": manifest["benchmark_sha256"],
		}
		_write_json(output / "release_validation.json", report)
		return report


def safe_extract_tar(archive: str | Path, destination: str | Path) -> None:
	"""Extract a tar archive after rejecting absolute paths and traversal."""

	archive_path = Path(archive)
	destination_path = Path(destination).resolve()
	with tarfile.open(archive_path, mode="r:gz") as bundle:
		accepted_members: list[tarfile.TarInfo] = []
		for member in bundle.getmembers():
			member_path = Path(member.name)
			if _is_platform_metadata(member_path):
				continue
			if member_path.is_absolute() or ".." in member_path.parts:
				raise ValueError(f"Unsafe archive member {member.name!r}.")
			resolved = (destination_path / member_path).resolve()
			if destination_path != resolved and destination_path not in resolved.parents:
				raise ValueError(f"Archive member escapes destination: {member.name!r}.")
			if member.issym() or member.islnk():
				raise ValueError(f"Archive links are not accepted: {member.name!r}.")
			accepted_members.append(member)
		bundle.extractall(destination_path, members=accepted_members, filter="data")


def write_portable_delivery_archive(
	*,
	source_archive: str | Path,
	destination_archive: str | Path,
	benchmark_id: str,
	run_id: str,
) -> dict[str, object]:
	"""Write a deterministic delivery archive with release-relative metadata paths."""

	source = Path(source_archive).resolve()
	destination = Path(destination_archive).resolve()
	if not source.is_file():
		raise ValueError(f"Delivery archive does not exist: {source}")
	root = f"artifacts/temporal_predictions/{run_id}"
	required_metadata = {
		f"{root}/run_config.json",
		f"{root}/goal_validation/summary.json",
	}
	destination.parent.mkdir(parents=True, exist_ok=True)
	normalized_files: set[str] = set()
	with tempfile.NamedTemporaryFile(
		dir=destination.parent,
		prefix=f".{destination.name}.",
		delete=False,
	) as temporary_file:
		temporary_path = Path(temporary_file.name)
	try:
		with (
			tarfile.open(source, mode="r:gz") as source_bundle,
			temporary_path.open("wb") as raw_output,
			gzip.GzipFile(
				filename="",
				mode="wb",
				fileobj=raw_output,
				mtime=0,
			) as compressed_output,
			tarfile.open(
				fileobj=compressed_output,
				mode="w",
				format=tarfile.PAX_FORMAT,
			) as destination_bundle,
		):
			for source_member in sorted(
				source_bundle.getmembers(),
				key=lambda member: member.name,
			):
				member_path = Path(source_member.name)
				if _is_platform_metadata(member_path):
					continue
				if member_path.is_absolute() or ".." in member_path.parts:
					raise ValueError(f"Unsafe archive member {source_member.name!r}.")
				if source_member.issym() or source_member.islnk():
					raise ValueError(
						f"Archive links are not accepted: {source_member.name!r}.",
					)
				if not (source_member.isdir() or source_member.isfile()):
					raise ValueError(
						f"Unsupported archive member type: {source_member.name!r}.",
					)
				content = b""
				if source_member.isfile():
					extracted = source_bundle.extractfile(source_member)
					if extracted is None:
						raise ValueError(
							f"Could not read archive member {source_member.name!r}.",
						)
					content = extracted.read()
					if source_member.name.endswith((".json", ".jsonl")):
						if source_member.name.endswith(".jsonl"):
							portable_content = _portable_jsonl_metadata(
								content,
								member_name=source_member.name,
								benchmark_id=benchmark_id,
							)
						else:
							portable_content = _portable_json_metadata(
								content,
								member_name=source_member.name,
								benchmark_id=benchmark_id,
							)
						if portable_content != content:
							content = portable_content
							normalized_files.add(source_member.name)
						if _contains_portable_metadata_field(content, source_member.name):
							normalized_files.add(source_member.name)
					if source_member.name in required_metadata:
						payload = json.loads(content.decode("utf-8"))
						if not isinstance(payload, dict):
							raise ValueError(
								f"Expected JSON object in {source_member.name!r}.",
							)
						if source_member.name.endswith("run_config.json"):
							expected = f"artifacts/temporal_nl_handoffs/{benchmark_id}"
							if payload.get("handoff_root") != expected:
								raise ValueError("Portable handoff_root normalization failed.")
						elif Path(
							str(payload.get("validated_append_dataset_root") or ""),
						).is_absolute():
							raise ValueError(
								"Portable validation summary normalization failed.",
							)
						normalized_files.add(source_member.name)
				member = tarfile.TarInfo(source_member.name)
				member.type = source_member.type
				member.mode = source_member.mode
				member.size = len(content)
				member.uid = 0
				member.gid = 0
				member.uname = ""
				member.gname = ""
				member.mtime = 0
				destination_bundle.addfile(
					member,
					io.BytesIO(content) if source_member.isfile() else None,
				)
		missing = required_metadata.difference(normalized_files)
		if missing:
			raise ValueError(
				"Delivery archive is missing required metadata: "
				+ ", ".join(sorted(missing)),
			)
		os.replace(temporary_path, destination)
	finally:
		if temporary_path.exists():
			temporary_path.unlink()
	return {
		"source_sha256": _sha256(source),
		"published_sha256": _sha256(destination),
		"normalized_files": sorted(normalized_files),
	}


def _portable_json_metadata(
	content: bytes,
	*,
	member_name: str,
	benchmark_id: str,
) -> bytes:
	payload = json.loads(content.decode("utf-8"))
	portable = _portable_metadata_value(
		payload,
		member_name=member_name,
		benchmark_id=benchmark_id,
	)
	if portable == payload:
		return content
	return (
		json.dumps(portable, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
	).encode("utf-8")


def _portable_jsonl_metadata(
	content: bytes,
	*,
	member_name: str,
	benchmark_id: str,
) -> bytes:
	lines = content.decode("utf-8").splitlines()
	rows = [json.loads(line) for line in lines if line.strip()]
	portable_rows = [
		_portable_metadata_value(
			row,
			member_name=member_name,
			benchmark_id=benchmark_id,
		)
		for row in rows
	]
	if portable_rows == rows:
		return content
	return "".join(
		json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
		for row in portable_rows
	).encode("utf-8")


def _portable_metadata_value(
	value: object,
	*,
	member_name: str,
	benchmark_id: str,
) -> object:
	if isinstance(value, Mapping):
		portable: dict[str, object] = {}
		for raw_key, item in value.items():
			key = str(raw_key)
			if key == "handoff_root" and isinstance(item, str) and Path(item).is_absolute():
				portable[key] = f"artifacts/temporal_nl_handoffs/{benchmark_id}"
			elif (
				key == "validated_append_dataset_root"
				and isinstance(item, str)
				and Path(item).is_absolute()
			):
				portable[key] = str(
					PurePosixPath(member_name).parent / "validated_append_datasets",
				)
			else:
				portable[key] = _portable_metadata_value(
					item,
					member_name=member_name,
					benchmark_id=benchmark_id,
				)
		return portable
	if isinstance(value, list):
		return [
			_portable_metadata_value(
				item,
				member_name=member_name,
				benchmark_id=benchmark_id,
			)
			for item in value
		]
	return value


def _contains_portable_metadata_field(content: bytes, member_name: str) -> bool:
	if member_name.endswith(".jsonl"):
		payloads = [
			json.loads(line)
			for line in content.decode("utf-8").splitlines()
			if line.strip()
		]
	else:
		payloads = [json.loads(content.decode("utf-8"))]
	return any(_contains_metadata_key(payload) for payload in payloads)


def _contains_metadata_key(value: object) -> bool:
	if isinstance(value, Mapping):
		if {"handoff_root", "validated_append_dataset_root"}.intersection(value):
			return True
		return any(_contains_metadata_key(item) for item in value.values())
	if isinstance(value, list):
		return any(_contains_metadata_key(item) for item in value)
	return False


def compare_validation_outputs(
	*,
	delivered_validation: str | Path,
	independent_validation: str | Path,
) -> dict[str, bool]:
	"""Compare semantic reports exactly and summaries after path normalization."""

	delivered = Path(delivered_validation)
	independent = Path(independent_validation)
	translation_match = _same_bytes(
		delivered / "translation_validation_results.jsonl",
		independent / "translation_validation_results.jsonl",
	)
	problem_match = _same_bytes(
		delivered / "problem_validation_results.jsonl",
		independent / "problem_validation_results.jsonl",
	)
	delivered_datasets = delivered / "validated_append_datasets"
	independent_datasets = independent / "validated_append_datasets"
	delivered_files = {
		path.name: _sha256(path)
		for path in delivered_datasets.glob("*.json")
		if not path.name.startswith("._")
	}
	independent_files = {
		path.name: _sha256(path)
		for path in independent_datasets.glob("*.json")
		if not path.name.startswith("._")
	}
	summary_match = _normalized_summary(_read_json(delivered / "summary.json")) == (
		_normalized_summary(_read_json(independent / "summary.json"))
	)
	return {
		"translation_results_exact": translation_match,
		"problem_results_exact": problem_match,
		"domain_datasets_exact": delivered_files == independent_files,
		"normalized_summary_exact": summary_match,
	}


def _verified_file(path: str | Path, expected_sha256: str) -> Path:
	file_path = Path(path).resolve()
	if not file_path.is_file():
		raise ValueError(f"Required source archive does not exist: {file_path}")
	if _sha256(file_path) != str(expected_sha256).strip().lower():
		raise ValueError(f"Source archive SHA-256 mismatch: {file_path}")
	return file_path


def _validated_sha256(value: str, *, label: str) -> str:
	digest = str(value or "").strip().lower()
	if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
		raise ValueError(f"{label} must be a SHA-256 digest.")
	return digest


def _validate_reusable_independent_output(output: Path) -> None:
	required_files = (
		output / "summary.json",
		output / "translation_validation_results.jsonl",
		output / "problem_validation_results.jsonl",
	)
	missing = [str(path) for path in required_files if not path.is_file()]
	datasets = tuple((output / "validated_append_datasets").glob("*.json"))
	if missing or len(datasets) != 16:
		raise ValueError(
			"Reusable independent validation is incomplete; "
			f"missing={missing}, domain_dataset_count={len(datasets)}.",
		)


def _is_platform_metadata(path: Path) -> bool:
	return any(
		part == "__MACOSX" or part == ".DS_Store" or part.startswith("._")
		for part in path.parts
	)


def _declared_prediction_sha256(path: Path) -> str:
	parts = path.read_text(encoding="utf-8").strip().split()
	if not parts or len(parts[0]) != 64:
		raise ValueError("Malformed translation_predictions.sha256 file.")
	return parts[0].lower()


def _normalized_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
	return {
		str(key): value
		for key, value in payload.items()
		if key != "validated_append_dataset_root"
	}


def _mona_version(mona: Path) -> str:
	completed = subprocess.run(
		[str(mona), "-v"],
		check=False,
		capture_output=True,
		text=True,
		timeout=30,
	)
	output = "\n".join((completed.stdout, completed.stderr)).strip()
	return output.splitlines()[0] if output else "unknown"


def _same_bytes(left: Path, right: Path) -> bool:
	return left.is_file() and right.is_file() and left.read_bytes() == right.read_bytes()


def _read_json(path: Path) -> dict[str, Any]:
	payload = json.loads(path.read_text(encoding="utf-8"))
	if not isinstance(payload, dict):
		raise ValueError(f"Expected JSON object in {path}.")
	return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.write_text(
		json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def _sha256(path: str | Path) -> str:
	return hashlib.sha256(Path(path).read_bytes()).hexdigest()
