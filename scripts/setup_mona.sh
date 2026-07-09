#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL_DIR="${ROOT_DIR}/.external"
MONA_VERSION="1.4-18"
MONA_TARBALL="mona-${MONA_VERSION}.tar.gz"
MONA_URL="https://www.brics.dk/mona/download/${MONA_TARBALL}"
MONA_SOURCE_DIR="${EXTERNAL_DIR}/mona-1.4"

mkdir -p "${EXTERNAL_DIR}"

if [[ ! -f "${EXTERNAL_DIR}/${MONA_TARBALL}" ]]; then
	printf '[mona] downloading %s\n' "${MONA_URL}"
	curl -fL "${MONA_URL}" -o "${EXTERNAL_DIR}/${MONA_TARBALL}"
else
	printf '[mona] using existing tarball %s\n' "${EXTERNAL_DIR}/${MONA_TARBALL}"
fi

if [[ ! -d "${MONA_SOURCE_DIR}" ]]; then
	printf '[mona] extracting %s\n' "${EXTERNAL_DIR}/${MONA_TARBALL}"
	tar -xzf "${EXTERNAL_DIR}/${MONA_TARBALL}" -C "${EXTERNAL_DIR}"
else
	printf '[mona] using existing source tree %s\n' "${MONA_SOURCE_DIR}"
fi

printf '[mona] configuring\n'
(
	cd "${MONA_SOURCE_DIR}"
	./configure --prefix="${MONA_SOURCE_DIR}/.local" \
		>"${EXTERNAL_DIR}/mona-configure.log" 2>&1
)

printf '[mona] building\n'
(
	cd "${MONA_SOURCE_DIR}"
	make -j"${MONA_JOBS:-$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)}" \
		>"${EXTERNAL_DIR}/mona-build.log" 2>&1
)

printf '[mona] ready: %s\n' "${MONA_SOURCE_DIR}/Front/mona"
printf '[mona] logs: %s %s\n' \
	"${EXTERNAL_DIR}/mona-configure.log" \
	"${EXTERNAL_DIR}/mona-build.log"
