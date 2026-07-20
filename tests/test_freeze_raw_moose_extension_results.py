from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.freeze_raw_moose_extension_results import (
	build_raw_moose_extension_dataset,
)
from scripts.freeze_raw_moose_extension_results import render_moose_reference_table


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXTENSION_DOMAINS = (
	"blocksworld-clear",
	"blocksworld-on",
	"blocksworld-tower",
	"depots",
)


def test_registered_frozen_result_is_complete_portable_and_manifested() -> None:
	release_root = PROJECT_ROOT / "paper_artifacts/gp2pl_evaluation/v1"
	result_file = release_root / "raw_moose_extension_five_seed_summary.json"
	result = json.loads(result_file.read_text(encoding="utf-8"))

	assert result["artifact_kind"] == "gp2pl_raw_moose_extension_five_seed_result"
	assert result["protocol"]["record_count"] == 740
	assert [row["valid_count"] for row in result["seed_results"]] == [
		26,
		23,
		23,
		25,
		20,
	]
	assert len(result["records"]) == 740
	assert len({(row["seed"], row["case_id"]) for row in result["records"]}) == 740
	assert "/Users/" not in result_file.read_text(encoding="utf-8")
	manifest = json.loads((release_root / "manifest.json").read_text(encoding="utf-8"))
	assert manifest["files"][result_file.name] == hashlib.sha256(
		result_file.read_bytes(),
	).hexdigest()


def test_manuscript_consumes_the_frozen_moose_reference_result() -> None:
	latex_root = PROJECT_ROOT / "latex_code/aamas_method_paper"
	main = (latex_root / "main.tex").read_text(encoding="utf-8")
	evaluation = (latex_root / "sections/evaluation.tex").read_text(encoding="utf-8")
	same_scope_table = (
		latex_root / "sections/result_same_scope_evidence_table.tex"
	).read_text(encoding="utf-8")
	appendix = (latex_root / "sections/technical_appendix_content.tex").read_text(
		encoding="utf-8",
	)

	assert r"\input{sections/result_moose_reference_macros}" in main
	assert r"\input{sections/result_moose_reference_table}" not in evaluation
	assert r"\input{sections/result_moose_reference_table}" in appendix
	assert r"\RawMooseExtensionSeedCounts{}" not in evaluation
	assert r"Table~\ref{tab:added-scope-evidence}" in evaluation
	assert "Raw MOOSE evidence & 117/740 & 15.8" in same_scope_table
	assert r"raw\_moose\_extension\_" in appendix
	assert r"five\_seed\_summary.json" in appendix


def test_freeze_filters_registered_extension_and_preserves_five_seed_counts(
	tmp_path: Path,
) -> None:
	case_ids = _extension_case_ids()
	valid_counts = (26, 23, 23, 25, 20)
	summaries: dict[int, Path] = {}
	for seed, valid_count in enumerate(valid_counts):
		results = [
			_result(case_id, valid=index < valid_count)
			for index, case_id in enumerate(case_ids)
		]
		if seed == 0:
			results.append(_result("ferry:p0_01.pddl", valid=True))
		summaries[seed] = _write_json(
			tmp_path / f"seed-{seed}.json",
			_summary(seed, results),
		)

	result = build_raw_moose_extension_dataset(
		summaries,
		published_reference_file=(
			PROJECT_ROOT
			/ "paper_artifacts/gp2pl_evaluation/v1/moose_published_reference.json"
		),
	)

	assert result["protocol"]["case_count_per_seed"] == 148
	assert result["protocol"]["record_count"] == 740
	assert [row["valid_count"] for row in result["seed_results"]] == list(
		valid_counts,
	)
	assert result["aggregate"]["mean_valid_count"] == 23.4
	assert len(result["records"]) == 740
	assert {record["domain"] for record in result["records"]} == set(
		EXTENSION_DOMAINS,
	)
	assert result["published_reference"]["mean_solved_count"] == 1079.6


def test_reference_table_labels_reported_and_measured_sources(tmp_path: Path) -> None:
	case_ids = _extension_case_ids()
	summaries = {
		seed: _write_json(
			tmp_path / f"seed-{seed}.json",
			_summary(seed, [_result(case_id, valid=True) for case_id in case_ids]),
		)
		for seed in range(5)
	}
	result = build_raw_moose_extension_dataset(
		summaries,
		published_reference_file=(
			PROJECT_ROOT
			/ "paper_artifacts/gp2pl_evaluation/v1/moose_published_reference.json"
		),
	)

	rendered = render_moose_reference_table(result)

	assert r"\textbf{Reported} (MOOSE Table~4)" in rendered
	assert r"\textbf{Measured} (local five seeds)" in rendered
	assert "Original 12 domains" in rendered
	assert "GP2PL-added 4" in rendered
	assert "Table~4" in rendered
	assert "cross-hardware runtime" in rendered
	assert "\\begin{table}[htbp]" in rendered


def _extension_case_ids() -> tuple[str, ...]:
	return tuple(
		sorted(
			f"{domain}:{problem_file.name}"
			for domain in EXTENSION_DOMAINS
			for problem_file in (PROJECT_ROOT / "src/domains" / domain / "test").glob(
				"*.pddl",
			)
		)
	)


def _summary(seed: int, results: list[dict[str, object]]) -> dict[str, object]:
	return {
		"success": True,
		"finished_at": "2026-07-15T00:00:00+08:00",
		"infrastructure_failure_count": 0,
		"run_id": f"raw-extension-seed-{seed}",
		"source_revision": {
			"commit": "9a0ee00d6646916060a2516b566bbf893470d069",
			"tracked_changes": True,
			"untracked_files": False,
		},
		"parameters": {
			"num_workers": 6,
			"timeout_seconds": 1800,
			"max_rss_gb": 8.0,
			"plan_verifier_timeout_seconds": 1800,
		},
		"toolchain": {
			"moose": {
				"artifact_sha256": "a" * 64,
				"docker_image_id": "sha256:" + "b" * 64,
				"git_revision": "c" * 40,
			},
		},
		"model_batch_manifest": {
			"sha256": str(seed) * 64,
			"artifact_sha256": str(seed) * 64,
			"settings": {
				"random_seed": seed,
				"num_workers": 1,
				"num_permutations": 3,
				"goal_max_size": 1,
				"train_timeout_seconds": 43200,
				"max_rss_gb": 16.0,
			},
		},
		"results": results,
	}


def _result(case_id: str, *, valid: bool) -> dict[str, object]:
	domain, problem_name = case_id.split(":", maxsplit=1)
	return {
		"method": "Raw MOOSE",
		"variant": "raw_moose",
		"domain": domain,
		"test": Path(problem_name).stem,
		"problem_file": f"/project/src/domains/{domain}/test/{problem_name}",
		"problem_sha256": "d" * 64,
		"domain_sha256": "e" * 64,
		"model_sha256": "f" * 64,
		"status": "valid" if valid else "planner_failed",
		"plan_verifier_success": True if valid else None,
		"planner_exit_code": 0 if valid else 1,
		"action_count": 1 if valid else 0,
		"elapsed_seconds": 1.0,
		"runtime_wall_seconds": 1.0,
	}


def _write_json(path: Path, payload: object) -> Path:
	path.write_text(json.dumps(payload), encoding="utf-8")
	return path
