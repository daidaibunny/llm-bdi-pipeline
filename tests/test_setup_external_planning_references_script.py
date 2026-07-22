from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_external_reference_setup_pins_sources_and_python_dependencies() -> None:
	script = (
		PROJECT_ROOT / "scripts/setup_external_planning_references.sh"
	).read_text(encoding="utf-8")

	assert 'ENHSP_REVISION="537bed55a60d9456975c56afbadd50fc8acb1dc9"' in script
	assert 'FOND4LTLF_REVISION="011d9d9a5bfd6406d2c358faf8f63167f6c839bb"' in script
	assert 'FOND4LTLF_RELEASE="v0.0.4"' in script
	assert 'TIDE_REVISION="9bdd247752817352714eac115ea6b78d90f26c09"' in script
	assert 'TIDE_URL="https://github.com/YuliiaSuprun/TIDE.git"' in script
	assert 'VAL_REVISION="3c7a1f330bdab0ba28a4762bb45c3f06c27fb6d4"' in script
	assert 'CLICK_VERSION="8.4.2"' in script
	assert 'PLY_VERSION="3.11"' in script
	assert 'LTLF2DFA_VERSION="1.0.2"' in script
	assert "uv venv" in script
	assert "uv pip install" in script
	assert 'MODE="check"' in script


def test_external_reference_setup_verifies_native_artifacts() -> None:
	script = (
		PROJECT_ROOT / "scripts/setup_external_planning_references.sh"
	).read_text(encoding="utf-8")

	assert "ENHSP_JAR_SHA256" in script
	assert "MOOSE_ARTIFACT_SHA256" in script
	assert 'MONA_EXECUTABLE="${EXTERNAL_DIR}/mona-1.4/Front/mona"' in script
	assert 'MONA_VERSION="1.4-18"' in script
	assert 'MOOSE_DOCKER_IMAGE="moose-exact-ubuntu22:local"' in script
	assert 'MOOSE_SANDBOX="${MOOSE_ROOT}/moose.sandbox"' in script
	assert "materialize_moose_sandbox" in script
	assert "apptainer build --sandbox" in script
	assert 'docker image inspect "${MOOSE_DOCKER_IMAGE}"' in script
	assert 'java -version' in script
	assert 'mona_version_output="$("${MONA_EXECUTABLE}" -v 2>&1 || true)"' in script
	assert '"MONA v${MONA_VERSION}"' in script
	assert 'if ! "${MONA_EXECUTABLE}" -v' not in script
	assert 'verify_revision "${VAL_ROOT}" "${VAL_REVISION}" "VAL"' in script
	assert 'verify_revision "${TIDE_ROOT}" "${TIDE_REVISION}" "TIDE"' in script
	assert 'docker image inspect "${TIDE_DOCKER_IMAGE}"' in script
	assert 'org.gp2pl.tide.revision="${TIDE_REVISION}"' in script
	assert 'submodule update --init --recursive' in script
