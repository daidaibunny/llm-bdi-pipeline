#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="setup"
if [[ "${1:-}" == "--check" ]]; then
	MODE="check"
elif [[ $# -gt 0 ]]; then
	printf 'usage: %s [--check]\n' "$0" >&2
	exit 2
fi

checkout_pinned_source() {
	local name="$1"
	local url="$2"
	local revision="$3"
	local destination="$4"
	if [[ ! -d "${destination}/.git" ]]; then
		if [[ "${MODE}" == "check" ]]; then
			printf '[benchmark-source] missing name=%s path=%s\n' \
				"${name}" "${destination}" >&2
			exit 1
		fi
		mkdir -p "$(dirname "${destination}")"
		printf '[benchmark-source] clone name=%s\n' "${name}"
		git clone "${url}" "${destination}"
	fi
	if [[ -n "$(git -C "${destination}" status --porcelain)" ]]; then
		printf '[benchmark-source] refusing dirty source name=%s path=%s\n' \
			"${name}" "${destination}" >&2
		exit 1
	fi
	local current_revision
	current_revision="$(git -C "${destination}" rev-parse HEAD)"
	if [[ "${current_revision}" != "${revision}" ]]; then
		if [[ "${MODE}" == "check" ]]; then
			printf '[benchmark-source] revision mismatch name=%s expected=%s actual=%s\n' \
				"${name}" "${revision}" "${current_revision}" >&2
			exit 1
		fi
		git -C "${destination}" fetch origin "${revision}"
		git -C "${destination}" checkout --detach "${revision}"
		current_revision="$(git -C "${destination}" rev-parse HEAD)"
	fi
	printf '[benchmark-source] ok name=%s revision=%s\n' \
		"${name}" "${current_revision}"
}

checkout_pinned_source \
	"DillonZChen/moose-dataset" \
	"https://github.com/DillonZChen/moose-dataset" \
	"e00970516154e9042b783a4613a1ed7286c9beee" \
	"${PROJECT_ROOT}/.external/moose-dataset"

checkout_pinned_source \
	"potassco/pddl-instances" \
	"https://github.com/potassco/pddl-instances" \
	"cf19edf7c53d1540ddbb396c642595e0926ee552" \
	"${PROJECT_ROOT}/.external/benchmark-sources/pddl-instances"

checkout_pinned_source \
	"bonetblai/learner-policies-from-examples" \
	"https://github.com/bonetblai/learner-policies-from-examples" \
	"9991926f7655c4b6c8dc2f0404123639e42056f2" \
	"${PROJECT_ROOT}/.external/gp-backends/learner-policies-from-examples"

checkout_pinned_source \
	"rleap-project/d2l" \
	"https://github.com/rleap-project/d2l" \
	"0620e169c894d79b3c84f435dba1462996f7c270" \
	"${PROJECT_ROOT}/.external/gp-backends/d2l"
