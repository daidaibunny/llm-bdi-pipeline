from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest

from evaluation.temporal_benchmark_release import compare_validation_outputs
from evaluation.temporal_benchmark_release import safe_extract_tar


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
