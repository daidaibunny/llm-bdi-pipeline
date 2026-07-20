from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = PROJECT_ROOT / "paper_artifacts/gp2pl_evaluation/v1"
RESULT_FILE = RELEASE_ROOT / "external_reference_results.json"
LATEX_ROOT = PROJECT_ROOT / "latex_code/aamas_method_paper"


def test_registered_external_reference_result_is_complete_portable_and_manifested() -> None:
	result = json.loads(RESULT_FILE.read_text(encoding="utf-8"))

	assert result["artifact_kind"] == "gp2pl_external_reference_results"
	assert result["protocol"]["achievement_case_count"] == 1228
	assert result["protocol"]["temporal_case_count"] == 1228
	assert result["protocol"]["record_count"] == 2456
	assert len(result["records"]) == 2456
	assert len(
		{(record["record_kind"], record["case_id"]) for record in result["records"]}
	) == 2456
	assert "/Users/" not in RESULT_FILE.read_text(encoding="utf-8")

	rows = {row["method"]: row for row in result["rows"]}
	assert rows["MOOSE"]["par2_seconds"] is None
	assert rows["Raw MOOSE extension"]["par2_seconds"] is None
	assert rows["LAMA"]["valid_trace_count"] == 591
	assert rows["LAMA"]["par2_seconds"] == pytest.approx(1178.449831605116)
	assert rows["MRP+HJ"]["valid_trace_count"] == 253
	assert rows["MRP+HJ"]["par2_seconds"] == pytest.approx(1127.3508548983668)
	assert rows["FOND4LTLf + LAMA"]["supported_case_count"] == 492
	assert rows["FOND4LTLf + LAMA"]["unsupported_case_count"] == 736
	assert rows["FOND4LTLf + LAMA"]["valid_trace_count"] == 298
	assert rows["FOND4LTLf + LAMA"]["par2_seconds"] == pytest.approx(
		1457.5163589505448,
	)
	direct_repair = result["provenance"]["direct_infrastructure_repair"]
	assert direct_repair["toolchain_verified"] is True
	verification = direct_repair["toolchain_verification"]
	assert verification["semantic_identity"] == "exact_pinned_revisions_and_versions"
	assert set(verification["path_embedded_launchers"]) == {"fond4ltlf", "mona"}
	for launcher in verification["path_embedded_launchers"].values():
		assert launcher["equivalence"] == "absolute_install_prefix_rewrite"
		assert launcher["retry_file_sha256_verified"] is True

	manifest = json.loads((RELEASE_ROOT / "manifest.json").read_text(encoding="utf-8"))
	assert manifest["external_reference_record_count"] == 2456
	for relative_path, expected_sha256 in manifest["files"].items():
		artifact = RELEASE_ROOT / relative_path
		assert artifact.is_file()
		assert hashlib.sha256(artifact.read_bytes()).hexdigest() == expected_sha256


def test_manuscript_consumes_frozen_external_reference_results() -> None:
	main = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	technical_appendix = (LATEX_ROOT / "technical_appendix.tex").read_text(
		encoding="utf-8",
	)
	evaluation = (LATEX_ROOT / "sections/evaluation.tex").read_text(encoding="utf-8")
	appendix = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")
	table = (
		LATEX_ROOT / "sections/result_external_reference_table.tex"
	).read_text(encoding="utf-8")

	assert r"\input{sections/result_external_reference_macros}" in main
	assert (
		r"\input{sections/result_external_reference_macros}" in technical_appendix
	)
	assert r"\ExternalLAMAValidCount{}" not in evaluation
	assert r"\ExternalLAMAValidCount{}" in appendix
	assert r"\ExternalDirectValidCount{}" not in evaluation
	assert r"\ExternalDirectValidCount{}" in appendix
	assert r"external\_reference\_results.json" in appendix
	assert r"\input{sections/result_external_reference_table}" not in evaluation
	assert r"\input{sections/result_external_reference_table}" in appendix
	assert "LAMA & Measured & Classical achievement & 591/868 & 0 & 1178.4" in table
	assert "MRP+HJ & Measured & Numeric achievement & 253/360 & 0 & 1127.4" in table
	assert "FOND4LTLf + LAMA & Measured & Supported Boolean TEG" in table
	assert "298/492 & 736 & 1457.5" in table
	raw_line = next(
		line for line in table.splitlines() if line.startswith("Raw MOOSE extension")
	)
	assert raw_line.endswith("& 0 & -- " + "\\\\")
