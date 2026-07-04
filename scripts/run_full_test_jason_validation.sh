#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

BATCH_ID="${BATCH_ID:-latest}"
if [[ $# -gt 0 && "$1" != --* ]]; then
	BATCH_ID="$1"
	shift
fi

PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_full_test_jason_validation.py \
	--batch-id "$BATCH_ID" \
	--num-workers "${NUM_WORKERS:-6}" \
	"$@"
