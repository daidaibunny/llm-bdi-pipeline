#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
	echo "usage: validate_with_docker_val.sh DOMAIN.pddl PROBLEM.pddl PLAN.plan" >&2
	exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="${VAL_DOCKER_IMAGE:-moose-exact-ubuntu22:local}"
PARSER_STACK_DEPTH="${VAL_PARSER_STACK_DEPTH:-1000000}"

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
	-e "VAL_PARSER_STACK_DEPTH=$PARSER_STACK_DEPTH" \
	"$IMAGE_NAME" \
	bash -lc '
		set -euo pipefail

		BUILD_DIR=/project/tmp/val-large-stack/build/linux64/Release
		VALIDATE_BIN="$BUILD_DIR/bin/Validate"
		LOCK_DIR=/project/tmp/val-large-stack/.build.lock
		SOURCE_DIR=/project/.external/VAL
		STACK_DEPTH="${VAL_PARSER_STACK_DEPTH:-1000000}"

		build_large_stack_val() {
			mkdir -p /project/tmp/val-large-stack
			while ! mkdir "$LOCK_DIR" 2>/dev/null; do
				if [[ -x "$VALIDATE_BIN" ]]; then
					return 0
				fi
				sleep 1
			done
			trap '\''rmdir "$LOCK_DIR" 2>/dev/null || true'\'' EXIT
			if [[ ! -x "$VALIDATE_BIN" ]]; then
				cmake -S "$SOURCE_DIR" \
					-B "$BUILD_DIR" \
					-DCMAKE_BUILD_TYPE=Release \
					-DCMAKE_CXX_FLAGS="-DYYMAXDEPTH=$STACK_DEPTH" \
					>/dev/null
				cmake --build "$BUILD_DIR" --target Validate -j 4 >/dev/null
			fi
		}

		build_large_stack_val
		export LD_LIBRARY_PATH="$BUILD_DIR/bin:${LD_LIBRARY_PATH:-}"
		exec "$VALIDATE_BIN" "$@"
	' validate_with_docker_val "$DOMAIN_FILE" "$PROBLEM_FILE" "$PLAN_FILE"
