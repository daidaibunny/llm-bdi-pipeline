#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
	echo "usage: validate_with_docker_val.sh DOMAIN.pddl PROBLEM.pddl PLAN.plan" >&2
	exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="${VAL_DOCKER_IMAGE:-moose-exact-ubuntu22:local}"

to_container_path() {
	local path="$1"
	if [[ "$path" != /* ]]; then
		path="$PWD/$path"
	fi
	if [[ "$path" == "$PROJECT_ROOT/"* ]]; then
		printf '/project/%s\n' "${path#"$PROJECT_ROOT"/}"
	else
		printf '%s\n' "$path"
	fi
}

DOMAIN_FILE="$(to_container_path "$1")"
PROBLEM_FILE="$(to_container_path "$2")"
PLAN_FILE="$(to_container_path "$3")"

docker run --rm \
	--platform linux/amd64 \
	-v "$PROJECT_ROOT:/project" \
	-w /project \
	"$IMAGE_NAME" \
	bash -lc '
		export LD_LIBRARY_PATH=/project/.external/VAL/build/linux64/Release/bin:${LD_LIBRARY_PATH:-}
		exec /project/.external/VAL/build/linux64/Release/bin/Validate "$@"
	' validate_with_docker_val "$DOMAIN_FILE" "$PROBLEM_FILE" "$PLAN_FILE"
