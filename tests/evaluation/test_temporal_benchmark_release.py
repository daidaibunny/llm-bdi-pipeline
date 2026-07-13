from __future__ import annotations

import io
import hashlib
import json
import tarfile
from pathlib import Path

import pytest

from evaluation.temporal_benchmark_release import compare_validation_outputs
from evaluation.temporal_benchmark_release import safe_extract_tar
from evaluation.temporal_benchmark_release import write_portable_delivery_archive


def test_safe_extract_tar_accepts_relative_files(tmp_path: Path) -> None:
	archive = tmp_path / "safe.tar.gz"
	with tarfile.open(archive, "w:gz") as bundle:
		content = b"sealed\n"
		member = tarfile.TarInfo("artifacts/input.txt")
		member.size = len(content)
		bundle.addfile(member, io.BytesIO(content))

	safe_extract_tar(archive, tmp_path / "output")

	assert (tmp_path / "output/artifacts/input.txt").read_bytes() == b"sealed\n"


def test_safe_extract_tar_rejects_path_traversal(tmp_path: Path) -> None:
	archive = tmp_path / "unsafe.tar.gz"
	with tarfile.open(archive, "w:gz") as bundle:
		content = b"escape\n"
		member = tarfile.TarInfo("../outside.txt")
		member.size = len(content)
		bundle.addfile(member, io.BytesIO(content))

	with pytest.raises(ValueError, match="Unsafe archive member"):
		safe_extract_tar(archive, tmp_path / "output")


def test_safe_extract_tar_ignores_macos_appledouble_metadata(tmp_path: Path) -> None:
	archive = tmp_path / "macos.tar.gz"
	with tarfile.open(archive, "w:gz") as bundle:
		for name, content in (
			("artifacts/result.json", b'{"ok":true}\n'),
			("artifacts/._result.json", b"appledouble"),
			("artifacts/.DS_Store", b"finder"),
		):
			member = tarfile.TarInfo(name)
			member.size = len(content)
			bundle.addfile(member, io.BytesIO(content))

	safe_extract_tar(archive, tmp_path / "output")

	assert (tmp_path / "output/artifacts/result.json").is_file()
	assert not (tmp_path / "output/artifacts/._result.json").exists()
	assert not (tmp_path / "output/artifacts/.DS_Store").exists()


def test_compare_validation_outputs_ignores_only_output_root(tmp_path: Path) -> None:
	delivered = tmp_path / "delivered"
	independent = tmp_path / "independent"
	for root, dataset_root in (
		(delivered, "/machine-a/datasets"),
		(independent, "/machine-b/datasets"),
	):
		(root / "validated_append_datasets").mkdir(parents=True)
		(root / "translation_validation_results.jsonl").write_text('{"ok":true}\n')
		(root / "problem_validation_results.jsonl").write_text('{"ok":true}\n')
		(root / "validated_append_datasets/tiny.json").write_text('{"cases":{}}\n')
		(root / "summary.json").write_text(
			json.dumps(
				{
					"translation_total": 1,
					"validated_append_dataset_root": dataset_root,
				},
			),
		)

	assert all(
		compare_validation_outputs(
			delivered_validation=delivered,
			independent_validation=independent,
		).values(),
	)
	(independent / "problem_validation_results.jsonl").write_text('{"ok":false}\n')
	comparison = compare_validation_outputs(
		delivered_validation=delivered,
		independent_validation=independent,
	)
	assert comparison["problem_results_exact"] is False


def test_portable_delivery_archive_replaces_machine_local_paths(
	tmp_path: Path,
) -> None:
	source = tmp_path / "delivery.tar.gz"
	root = "artifacts/temporal_predictions/run-1"
	with tarfile.open(source, "w:gz") as bundle:
		_add_tar_text(
			bundle,
			f"{root}/run_config.json",
			json.dumps({"handoff_root": "/Users/example/private/handoff"}),
		)
		_add_tar_text(
			bundle,
			f"{root}/goal_validation/summary.json",
			json.dumps(
				{
					"translation_total": 1,
					"validated_append_dataset_root": "/private/tmp/result/datasets",
				},
			),
		)
		_add_tar_text(bundle, f"{root}/translation_predictions.jsonl", '{"ok":true}\n')

	first = tmp_path / "first.tar.gz"
	second = tmp_path / "second.tar.gz"
	report = write_portable_delivery_archive(
		source_archive=source,
		destination_archive=first,
		benchmark_id="benchmark-1",
		run_id="run-1",
	)
	write_portable_delivery_archive(
		source_archive=source,
		destination_archive=second,
		benchmark_id="benchmark-1",
		run_id="run-1",
	)

	assert first.read_bytes() == second.read_bytes()
	assert report["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
	assert report["published_sha256"] == hashlib.sha256(first.read_bytes()).hexdigest()
	assert report["normalized_files"] == [
		f"{root}/goal_validation/summary.json",
		f"{root}/run_config.json",
	]
	extracted = tmp_path / "extracted"
	safe_extract_tar(first, extracted)
	run_config = json.loads((extracted / root / "run_config.json").read_text())
	summary = json.loads(
		(extracted / root / "goal_validation/summary.json").read_text(),
	)
	assert run_config["handoff_root"] == (
		"artifacts/temporal_nl_handoffs/benchmark-1"
	)
	assert summary["validated_append_dataset_root"] == (
		f"{root}/goal_validation/validated_append_datasets"
	)
	assert "/Users/" not in first.read_bytes().decode("latin-1")
	assert "/private/tmp/" not in first.read_bytes().decode("latin-1")


def test_portable_delivery_archive_rejects_unexpected_missing_metadata(
	tmp_path: Path,
) -> None:
	source = tmp_path / "delivery.tar.gz"
	with tarfile.open(source, "w:gz") as bundle:
		_add_tar_text(bundle, "artifacts/temporal_predictions/run-1/data.json", "{}")

	with pytest.raises(ValueError, match="missing required metadata"):
		write_portable_delivery_archive(
			source_archive=source,
			destination_archive=tmp_path / "portable.tar.gz",
			benchmark_id="benchmark-1",
			run_id="run-1",
		)


def _add_tar_text(bundle: tarfile.TarFile, name: str, text: str) -> None:
	content = text.encode("utf-8")
	member = tarfile.TarInfo(name)
	member.size = len(content)
	bundle.addfile(member, io.BytesIO(content))
