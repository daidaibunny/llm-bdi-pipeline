#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTINATION="${PROJECT_ROOT}/.external/moose"
REPOSITORY_URL="https://github.com/DillonZChen/moose"
REVISION="ce1e99bc12e9c839c5e8e870aac878fd5d31cf9e"

MODE="setup"
if [[ "${1:-}" == "--check" ]]; then
	MODE="check"
elif [[ $# -gt 0 ]]; then
	printf 'usage: %s [--check]\n' "$0" >&2
	exit 2
fi

if [[ ! -d "${DESTINATION}/.git" ]]; then
	if [[ "${MODE}" == "check" ]]; then
		printf '[moose] missing path=%s\n' "${DESTINATION}" >&2
		exit 1
	fi
	mkdir -p "$(dirname "${DESTINATION}")"
	printf '[moose] clone repository=%s\n' "${REPOSITORY_URL}"
	git clone "${REPOSITORY_URL}" "${DESTINATION}"
fi

if [[ -n "$(git -C "${DESTINATION}" status --porcelain)" ]]; then
	printf '[moose] refusing dirty checkout path=%s\n' "${DESTINATION}" >&2
	exit 1
fi

CURRENT_REVISION="$(git -C "${DESTINATION}" rev-parse HEAD)"
if [[ "${CURRENT_REVISION}" != "${REVISION}" ]]; then
	if [[ "${MODE}" == "check" ]]; then
		printf '[moose] revision mismatch expected=%s actual=%s\n' \
			"${REVISION}" "${CURRENT_REVISION}" >&2
		exit 1
	fi
	git -C "${DESTINATION}" fetch origin "${REVISION}"
	git -C "${DESTINATION}" checkout --detach "${REVISION}"
	CURRENT_REVISION="$(git -C "${DESTINATION}" rev-parse HEAD)"
fi

printf '[moose] ok revision=%s path=%s\n' \
	"${CURRENT_REVISION}" "${DESTINATION}"
