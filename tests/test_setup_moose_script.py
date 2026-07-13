from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_setup_moose_script_pins_the_official_repository() -> None:
	script = (PROJECT_ROOT / "scripts/setup_moose.sh").read_text(encoding="utf-8")

	assert "https://github.com/DillonZChen/moose" in script
	assert "ce1e99bc12e9c839c5e8e870aac878fd5d31cf9e" in script
	assert 'DESTINATION="${PROJECT_ROOT}/.external/moose"' in script
	assert 'if [[ "${1:-}" == "--check" ]]' in script
	assert "status --porcelain" in script
	assert "checkout --detach" in script
