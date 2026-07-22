#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL_DIR="${ROOT_DIR}/.external"
ENHSP_ROOT="${EXTERNAL_DIR}/enhsp-socs24"
FOND4LTLF_ROOT="${EXTERNAL_DIR}/fond4ltlf-0.0.4"
TIDE_ROOT="${EXTERNAL_DIR}/tide"
MONA_EXECUTABLE="${EXTERNAL_DIR}/mona-1.4/Front/mona"
MONA_VERSION="1.4-18"
MOOSE_ROOT="${EXTERNAL_DIR}/moose"
MOOSE_SANDBOX="${MOOSE_ROOT}/moose.sandbox"
MOOSE_SANDBOX_MARKER="${MOOSE_ROOT}/moose.sandbox.sha256"
VAL_ROOT="${EXTERNAL_DIR}/VAL"

ENHSP_URL="https://github.com/hstairs/jpddlplus.git"
ENHSP_REVISION="537bed55a60d9456975c56afbadd50fc8acb1dc9"
ENHSP_JAR_SHA256="7e82ec74844a3722e48acafb25eafdd334e1ee35a3b9ba52a8cb6c2baae1dcd6"
FOND4LTLF_URL="https://github.com/whitemech/FOND4LTLf.git"
FOND4LTLF_REVISION="011d9d9a5bfd6406d2c358faf8f63167f6c839bb"
FOND4LTLF_RELEASE="v0.0.4"
TIDE_URL="https://github.com/YuliiaSuprun/TIDE.git"
TIDE_REVISION="9bdd247752817352714eac115ea6b78d90f26c09"
TIDE_DOCKER_IMAGE="gp2pl-tide:${TIDE_REVISION:0:12}"
TIDE_DOCKER_PLATFORM="linux/amd64"
FOND_PYTHON="3.12"
CLICK_VERSION="8.4.2"
PLY_VERSION="3.11"
LTLF2DFA_VERSION="1.0.2"
MOOSE_DOCKER_IMAGE="moose-exact-ubuntu22:local"
MOOSE_ARTIFACT_SHA256="ab342530125b2ae73a72086b702d417dfa1677d55041907a24b67e160b67742f"
VAL_URL="https://github.com/KCL-Planning/VAL.git"
VAL_REVISION="3c7a1f330bdab0ba28a4762bb45c3f06c27fb6d4"

MODE="setup"
if [[ "${1:-}" == "--check" ]]; then
	MODE="check"
elif [[ $# -gt 0 ]]; then
	printf 'usage: %s [--check]\n' "$0" >&2
	exit 2
fi

require_command() {
	local command_name="$1"
	if ! command -v "${command_name}" >/dev/null 2>&1; then
		printf '[external-reference] missing command: %s\n' "${command_name}" >&2
		exit 1
	fi
}

sha256_file() {
	local file="$1"
	if command -v shasum >/dev/null 2>&1; then
		shasum -a 256 "${file}" | awk '{print $1}'
		return
	fi
	sha256sum "${file}" | awk '{print $1}'
}

verify_revision() {
	local root="$1"
	local expected="$2"
	local label="$3"
	if [[ ! -d "${root}/.git" ]]; then
		printf '[external-reference] missing %s repository: %s\n' "${label}" "${root}" >&2
		exit 1
	fi
	local actual
	actual="$(git -C "${root}" rev-parse HEAD)"
	if [[ "${actual}" != "${expected}" ]]; then
		printf '[external-reference] %s revision mismatch: expected=%s actual=%s\n' \
			"${label}" "${expected}" "${actual}" >&2
		exit 1
	fi
}

checkout_pinned_repository() {
	local root="$1"
	local url="$2"
	local revision="$3"
	local label="$4"
	if [[ ! -d "${root}/.git" ]]; then
		printf '[external-reference] cloning %s\n' "${label}"
		git clone "${url}" "${root}"
	fi
	if [[ -n "$(git -C "${root}" status --porcelain)" ]]; then
		printf '[external-reference] refusing to change dirty %s repository: %s\n' \
			"${label}" "${root}" >&2
		exit 1
	fi
	if [[ "$(git -C "${root}" rev-parse HEAD)" != "${revision}" ]]; then
		git -C "${root}" fetch origin "${revision}"
		git -C "${root}" checkout --detach "${revision}"
	fi
}

build_tide_image() {
	local image_revision
	image_revision="$(docker image inspect \
		--format '{{ index .Config.Labels "org.gp2pl.tide.revision" }}' \
		"${TIDE_DOCKER_IMAGE}" 2>/dev/null || true)"
	if [[ "${image_revision}" == "${TIDE_REVISION}" ]]; then
		return
	fi
	printf '[external-reference] building pinned TIDE image=%s\n' \
		"${TIDE_DOCKER_IMAGE}"
	docker build \
		--platform "${TIDE_DOCKER_PLATFORM}" \
		--label org.gp2pl.tide.revision="${TIDE_REVISION}" \
		--tag "${TIDE_DOCKER_IMAGE}" \
		"${TIDE_ROOT}"
}

materialize_moose_sandbox() {
	local moose_sha="$1"
	if [[ -d "${MOOSE_SANDBOX}" ]] \
		&& [[ -f "${MOOSE_SANDBOX_MARKER}" ]] \
		&& [[ "$(tr -d '[:space:]' < "${MOOSE_SANDBOX_MARKER}")" == "${moose_sha}" ]]; then
		return
	fi
	if ! docker image inspect "${MOOSE_DOCKER_IMAGE}" >/dev/null 2>&1; then
		printf '[external-reference] missing MOOSE runtime image: %s\n' \
			"${MOOSE_DOCKER_IMAGE}" >&2
		exit 1
	fi
	if [[ -L "${MOOSE_SANDBOX}" || -L "${MOOSE_SANDBOX_MARKER}" ]]; then
		printf '[external-reference] refusing symlinked MOOSE sandbox paths\n' >&2
		exit 1
	fi
	local staging
	staging="$(mktemp -d "${MOOSE_ROOT}/.moose.sandbox.build.XXXXXX")"
	printf '[external-reference] extracting loop-device-free MOOSE sandbox\n'
	if ! docker run --rm --platform linux/amd64 --privileged \
		-v "${MOOSE_ROOT}:/work:ro" \
		-w /tmp \
		"${MOOSE_DOCKER_IMAGE}" \
		bash -lc \
		'apptainer build --sandbox /tmp/moose.sandbox /work/moose.sif >&2 && tar -C /tmp/moose.sandbox -cf - .' \
		| tar -C "${staging}" -xf -; then
		rm -rf -- "${staging}"
		printf '[external-reference] failed to extract MOOSE sandbox\n' >&2
		exit 1
	fi
	if [[ ! -f "${staging}/.singularity.d/actions/run" ]]; then
		rm -rf -- "${staging}"
		printf '[external-reference] extracted MOOSE sandbox has no runscript\n' >&2
		exit 1
	fi
	rm -rf -- "${MOOSE_SANDBOX}"
	mv "${staging}" "${MOOSE_SANDBOX}"
	printf '%s\n' "${moose_sha}" > "${MOOSE_SANDBOX_MARKER}.tmp"
	mv "${MOOSE_SANDBOX_MARKER}.tmp" "${MOOSE_SANDBOX_MARKER}"
}

verify_installation() {
	verify_revision "${ENHSP_ROOT}" "${ENHSP_REVISION}" "ENHSP"
	verify_revision "${FOND4LTLF_ROOT}" "${FOND4LTLF_REVISION}" "FOND4LTLf"
	verify_revision "${TIDE_ROOT}" "${TIDE_REVISION}" "TIDE"
	verify_revision "${VAL_ROOT}" "${VAL_REVISION}" "VAL"
	if git -C "${TIDE_ROOT}" submodule status --recursive | grep -Eq '^[+-]'; then
		printf '[external-reference] TIDE submodules are missing or not pinned\n' >&2
		exit 1
	fi
	if ! java -version >/dev/null 2>&1; then
		printf '[external-reference] java exists but no working Java runtime is installed\n' >&2
		exit 1
	fi
	if [[ ! -f "${ENHSP_ROOT}/enhsp.jar" ]]; then
		printf '[external-reference] missing ENHSP jar\n' >&2
		exit 1
	fi
	local jar_sha
	jar_sha="$(sha256_file "${ENHSP_ROOT}/enhsp.jar")"
	if [[ "${jar_sha}" != "${ENHSP_JAR_SHA256}" ]]; then
		printf '[external-reference] ENHSP jar digest mismatch: %s\n' "${jar_sha}" >&2
		exit 1
	fi
	if [[ ! -x "${FOND4LTLF_ROOT}/.venv/bin/fond4ltlf" ]]; then
		printf '[external-reference] missing FOND4LTLf virtual environment\n' >&2
		exit 1
	fi
	"${FOND4LTLF_ROOT}/.venv/bin/python" -c \
		"import importlib.metadata as m; assert m.version('fond4ltlf') == '0.0.4'; assert m.version('click') == '${CLICK_VERSION}'; assert m.version('ply') == '${PLY_VERSION}'; assert m.version('ltlf2dfa') == '${LTLF2DFA_VERSION}'"
	if [[ ! -x "${MONA_EXECUTABLE}" ]]; then
		printf '[external-reference] missing MONA executable: %s\n' "${MONA_EXECUTABLE}" >&2
		exit 1
	fi
	local mona_version_output
	mona_version_output="$("${MONA_EXECUTABLE}" -v 2>&1 || true)"
	if [[ "${mona_version_output}" != *"MONA v${MONA_VERSION}"* ]]; then
		printf '[external-reference] MONA version mismatch: expected=%s output=%s\n' \
			"${MONA_VERSION}" "${mona_version_output%%$'\n'*}" >&2
		exit 1
	fi
	if [[ ! -f "${MOOSE_ROOT}/moose.sif" ]]; then
		printf '[external-reference] missing official MOOSE image\n' >&2
		exit 1
	fi
	local moose_sha
	moose_sha="$(sha256_file "${MOOSE_ROOT}/moose.sif")"
	if [[ "${moose_sha}" != "${MOOSE_ARTIFACT_SHA256}" ]]; then
		printf '[external-reference] MOOSE image digest mismatch: %s\n' \
			"${moose_sha}" >&2
		exit 1
	fi
	if [[ ! -d "${MOOSE_SANDBOX}" ]] \
		|| [[ ! -f "${MOOSE_SANDBOX_MARKER}" ]] \
		|| [[ "$(tr -d '[:space:]' < "${MOOSE_SANDBOX_MARKER}" 2>/dev/null || true)" != "${moose_sha}" ]] \
		|| [[ ! -f "${MOOSE_SANDBOX}/.singularity.d/actions/run" ]]; then
		printf '[external-reference] missing or stale MOOSE sandbox; rerun setup\n' >&2
		exit 1
	fi
	if ! docker image inspect "${MOOSE_DOCKER_IMAGE}" >/dev/null 2>&1; then
		printf '[external-reference] missing MOOSE runtime image: %s\n' \
			"${MOOSE_DOCKER_IMAGE}" >&2
		exit 1
	fi
	if ! docker image inspect "${TIDE_DOCKER_IMAGE}" >/dev/null 2>&1; then
		printf '[external-reference] missing TIDE image: %s\n' \
			"${TIDE_DOCKER_IMAGE}" >&2
		exit 1
	fi
	local tide_image_revision
	tide_image_revision="$(docker image inspect \
		--format '{{ index .Config.Labels "org.gp2pl.tide.revision" }}' \
		"${TIDE_DOCKER_IMAGE}")"
	if [[ "${tide_image_revision}" != "${TIDE_REVISION}" ]]; then
		printf '[external-reference] TIDE image revision mismatch: expected=%s actual=%s\n' \
			"${TIDE_REVISION}" "${tide_image_revision}" >&2
		exit 1
	fi
	if ! docker run --rm --platform "${TIDE_DOCKER_PLATFORM}" \
		"${TIDE_DOCKER_IMAGE}" test -x /app/bin/main_single; then
		printf '[external-reference] TIDE image has no executable main_single\n' >&2
		exit 1
	fi
	printf '[external-reference] ENHSP revision=%s planner=sat-hmrphj\n' \
		"${ENHSP_REVISION}"
	printf '[external-reference] FOND4LTLf release=%s revision=%s\n' \
		"${FOND4LTLF_RELEASE}" "${FOND4LTLF_REVISION}"
	printf '[external-reference] MONA executable=%s\n' "${MONA_EXECUTABLE}"
	printf '[external-reference] MOOSE image=%s\n' "${MOOSE_DOCKER_IMAGE}"
	printf '[external-reference] TIDE revision=%s image=%s\n' \
		"${TIDE_REVISION}" "${TIDE_DOCKER_IMAGE}"
}

require_command git
require_command uv
require_command java
require_command docker
require_command tar
mkdir -p "${EXTERNAL_DIR}"

if [[ "${MODE}" == "setup" ]]; then
	checkout_pinned_repository \
		"${ENHSP_ROOT}" "${ENHSP_URL}" "${ENHSP_REVISION}" "ENHSP"
	checkout_pinned_repository \
		"${FOND4LTLF_ROOT}" "${FOND4LTLF_URL}" "${FOND4LTLF_REVISION}" "FOND4LTLf"
	checkout_pinned_repository \
		"${TIDE_ROOT}" "${TIDE_URL}" "${TIDE_REVISION}" "TIDE"
	git -C "${TIDE_ROOT}" submodule sync --recursive
	git -C "${TIDE_ROOT}" submodule update --init --recursive
	checkout_pinned_repository \
		"${VAL_ROOT}" "${VAL_URL}" "${VAL_REVISION}" "VAL"
	if [[ ! -x "${FOND4LTLF_ROOT}/.venv/bin/python" ]]; then
		uv venv --python "${FOND_PYTHON}" "${FOND4LTLF_ROOT}/.venv"
	fi
	uv pip install --python "${FOND4LTLF_ROOT}/.venv/bin/python" \
		"click==${CLICK_VERSION}" \
		"ply==${PLY_VERSION}" \
		"ltlf2dfa==${LTLF2DFA_VERSION}"
	uv pip install --python "${FOND4LTLF_ROOT}/.venv/bin/python" \
		--no-deps --editable "${FOND4LTLF_ROOT}"
	if [[ ! -x "${MONA_EXECUTABLE}" ]]; then
		bash "${ROOT_DIR}/scripts/setup_mona.sh"
	fi
	if [[ -f "${MOOSE_ROOT}/moose.sif" ]]; then
		moose_sha="$(sha256_file "${MOOSE_ROOT}/moose.sif")"
		if [[ "${moose_sha}" == "${MOOSE_ARTIFACT_SHA256}" ]]; then
			materialize_moose_sandbox "${moose_sha}"
		fi
	fi
	build_tide_image
fi

verify_installation
