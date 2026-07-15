from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts/run_external_reference_infrastructure_repairs.sh"


def test_repair_script_runs_only_serial_exact_retries_and_merges_results() -> None:
	text = SCRIPT.read_text(encoding="utf-8")

	assert text.count("--num-workers 1") == 2
	assert "--num-workers 20" not in text
	assert text.count("--resume") == 2
	assert "expected_count=9" in text
	assert "expected_count=46" in text
	assert "--kind achievement" in text
	assert "--kind direct_temporal" in text
	assert "--list-only" in text
