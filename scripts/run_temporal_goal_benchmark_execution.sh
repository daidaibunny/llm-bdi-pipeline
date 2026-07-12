#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RUN_ID="${RUN_ID:-teg-execution-$(date +%Y%m%d-%H%M%S)}"
ATOMIC_BATCH_ID="${ATOMIC_BATCH_ID:-latest}"
NUM_WORKERS="${NUM_WORKERS:-8}"
JASON_TIMEOUT_SECONDS="${JASON_TIMEOUT_SECONDS:-1800}"
VAL_TIMEOUT_SECONDS="${VAL_TIMEOUT_SECONDS:-1800}"
JASON_JAVA_STACK_SIZE="${JASON_JAVA_STACK_SIZE:-64m}"
MONA_BIN="${MONA_BIN:-$PROJECT_ROOT/.external/mona-1.4/Front/mona}"
PLAN_VERIFIER_COMMAND="${PLAN_VERIFIER_COMMAND:-bash $PROJECT_ROOT/scripts/validate_with_docker_val.sh}"

if [[ ! -x "$MONA_BIN" ]]; then
	echo "[error] MONA executable missing: $MONA_BIN" >&2
	echo "[error] run: bash scripts/setup_mona.sh" >&2
	exit 2
fi

echo "[run] id=$RUN_ID"
echo "[run] benchmark=paper_artifacts/temporal_goal_benchmark/v1/benchmark.json"
echo "[run] atomic_batch_id=$ATOMIC_BATCH_ID workers=$NUM_WORKERS"
echo "[run] jason_timeout_seconds=$JASON_TIMEOUT_SECONDS val_timeout_seconds=$VAL_TIMEOUT_SECONDS"
echo "[run] jason_java_stack_size=$JASON_JAVA_STACK_SIZE"
echo "[run] validation=Jason + PDDL replay + neutral-goal VAL + gold/predicted DFA"

RUNNER_ARGS=(
	scripts/run_temporal_goal_benchmark_execution.py
	--run-id "$RUN_ID"
	--batch-id "$ATOMIC_BATCH_ID"
	--num-workers "$NUM_WORKERS"
	--timeout-seconds "$JASON_TIMEOUT_SECONDS"
	--plan-verifier-timeout-seconds "$VAL_TIMEOUT_SECONDS"
	--jason-java-stack-size "$JASON_JAVA_STACK_SIZE"
	--plan-verifier-command "$PLAN_VERIFIER_COMMAND"
)
for domain in "$@"; do
	RUNNER_ARGS+=(--domain "$domain")
done

set +e
PYTHONDONTWRITEBYTECODE=1 MONA_BIN="$MONA_BIN" uv run python "${RUNNER_ARGS[@]}"
EXIT_CODE=$?
set -e

SUMMARY_FILE="$PROJECT_ROOT/artifacts/temporal_goal_execution_runs/$RUN_ID/summary.json"
echo "[run] exit_code=$EXIT_CODE"
echo "[run] summary=$SUMMARY_FILE"
exit "$EXIT_CODE"
