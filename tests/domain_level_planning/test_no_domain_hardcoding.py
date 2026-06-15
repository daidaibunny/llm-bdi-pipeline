from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_domain_level_planning_production_code_has_no_blocksworld_special_cases() -> None:
	forbidden_tokens = (
		"blocksworld",
		"blocks_4",
		"stack(",
		"unstack(",
		"pick-up",
		"put-down",
		"arm-empty",
		"on-table",
	)
	paths = tuple(
		path
		for path in (PROJECT_ROOT / "src" / "domain_level_planning").glob("*.py")
		if path.name != "__init__.py"
	)

	violations: list[str] = []
	for path in paths:
		text = path.read_text(encoding="utf-8").lower()
		for token in forbidden_tokens:
			if token in text:
				violations.append(f"{path.name}:{token}")

	assert violations == []
