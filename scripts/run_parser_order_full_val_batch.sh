#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RUN_ID="${RUN_ID:-parser-order-val-$(date +%Y%m%d-%H%M%S)}"
BATCH_ID="${BATCH_ID:-$RUN_ID}"
VALIDATION_RUN_ID="${VALIDATION_RUN_ID:-$RUN_ID-full-test}"

WORKERS="${WORKERS:-6}"
MOOSE_WORKERS="${MOOSE_WORKERS:-$WORKERS}"
JASON_WORKERS="${JASON_WORKERS:-$WORKERS}"
TRAIN_TIMEOUT_SECONDS="${TRAIN_TIMEOUT_SECONDS:-43200}"
JASON_TIMEOUT_SECONDS="${JASON_TIMEOUT_SECONDS:-1800}"
VAL_TIMEOUT_SECONDS="${VAL_TIMEOUT_SECONDS:-1800}"
JASON_JAVA_STACK_SIZE="${JASON_JAVA_STACK_SIZE:-64m}"
PLAN_VERIFIER_COMMAND="${PLAN_VERIFIER_COMMAND:-bash $PROJECT_ROOT/scripts/validate_with_docker_val.sh}"
LOG_ROOT="$PROJECT_ROOT/artifacts/parser_order_full_val_logs/$RUN_ID"
MOOSE_STDOUT="$LOG_ROOT/moose_batch.stdout.log"
MOOSE_STDERR="$LOG_ROOT/moose_batch.stderr.log"

if [[ $# -gt 0 ]]; then
	DOMAINS=("$@")
else
	DOMAINS=()
	while IFS= read -r domain; do
		[[ -n "$domain" ]] && DOMAINS+=("$domain")
	done < <(
		PYTHONDONTWRITEBYTECODE=1 uv run python - <<'PY'
import json
from pathlib import Path

registry = json.loads(
	Path("src/benchmark_registry/achievement_goals/registry.json").read_text(
		encoding="utf-8"
	)
)

for domain in registry["selected_domain_ids"]:
	print(domain)
PY
	)
fi

DOMAIN_ARGS=()
for domain in "${DOMAINS[@]}"; do
	DOMAIN_ARGS+=(--domain "$domain")
done

echo "[run] id=$RUN_ID"
echo "[run] domains=${DOMAINS[*]}"
echo "[run] moose_workers=$MOOSE_WORKERS jason_workers=$JASON_WORKERS"
echo "[run] moose_train_timeout_seconds=$TRAIN_TIMEOUT_SECONDS"
echo "[run] jason_timeout_seconds=$JASON_TIMEOUT_SECONDS val_timeout_seconds=$VAL_TIMEOUT_SECONDS jason_java_stack_size=$JASON_JAVA_STACK_SIZE"
echo "[run] plan_verifier_command=$PLAN_VERIFIER_COMMAND"
echo "[stage 1] generating MOOSE-backed atomic ASL libraries"
mkdir -p "$LOG_ROOT"

set +e
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_timestamped_moose_asl_batch.py \
	--timestamp-id "$BATCH_ID" \
	--num-workers "$MOOSE_WORKERS" \
	--atomic-library-mode validated-policy-lifting \
	--skip-temporal-append \
	--train-timeout-seconds "$TRAIN_TIMEOUT_SECONDS" \
	--dump-timeout-seconds "${DUMP_TIMEOUT_SECONDS:-300}" \
	--append-timeout-seconds "${APPEND_TIMEOUT_SECONDS:-300}" \
	--jason-timeout-seconds "$JASON_TIMEOUT_SECONDS" \
	--jason-plan-verifier-timeout-seconds "$VAL_TIMEOUT_SECONDS" \
	"${DOMAIN_ARGS[@]}" \
	>"$MOOSE_STDOUT" \
	2>"$MOOSE_STDERR"
MOOSE_EXIT_CODE=$?
set -e

PYTHONDONTWRITEBYTECODE=1 uv run python - "$PROJECT_ROOT" "$BATCH_ID" "$MOOSE_EXIT_CODE" "$MOOSE_STDOUT" "$MOOSE_STDERR" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

project_root = Path(sys.argv[1])
batch_id = sys.argv[2]
exit_code = int(sys.argv[3])
stdout_file = Path(sys.argv[4])
stderr_file = Path(sys.argv[5])
summary_file = project_root / "artifacts" / "moose_asl_batches" / batch_id / "run_logs" / "summary.json"

print(f"[stage 1] exit_code={exit_code} stdout={stdout_file} stderr={stderr_file}")
if not summary_file.exists():
	print(f"[stage 1] summary missing: {summary_file}")
	sys.exit(0)

summary = json.loads(summary_file.read_text(encoding="utf-8"))
print("[stage 1] domain,moose_train,compile_asl,status")
for item in summary.get("domains") or []:
	commands = item.get("commands") or {}

	def command_status(name: str) -> str:
		command = commands.get(name) or {}
		if command.get("success") is True:
			return "ok"
		if command.get("timed_out"):
			return "timeout"
		if command:
			return "fail"
		return "not_run"

	print(
		",".join(
			(
				str(item.get("domain")),
				command_status("moose_train"),
				command_status("compile_atomic_library"),
				"ok" if item.get("success") else "fail",
			)
		)
	)
PY

if [[ "$MOOSE_EXIT_CODE" -ne 0 ]]; then
	echo "[stage 1] failed; fix the failed domain above before Jason/VAL full-test validation."
	exit "$MOOSE_EXIT_CODE"
fi

echo "[stage 2] appending PDDL parser-order full-test goals, running Jason, then VAL"

set +e
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_full_test_jason_validation.py \
	--batch-id "$BATCH_ID" \
	--run-id "$VALIDATION_RUN_ID" \
	--num-workers "$JASON_WORKERS" \
	--timeout-seconds "$JASON_TIMEOUT_SECONDS" \
	--jason-java-stack-size "$JASON_JAVA_STACK_SIZE" \
	--plan-verifier-command "$PLAN_VERIFIER_COMMAND" \
	--require-plan-verifier \
	--plan-verifier-timeout-seconds "$VAL_TIMEOUT_SECONDS" \
	--atomic-library-mode validated-policy-lifting \
	--write-per-test-runtime-asl \
	--suppress-final-summary-json \
	"${DOMAIN_ARGS[@]}"
VALIDATION_EXIT_CODE=$?
set -e

SUMMARY_FILE="$PROJECT_ROOT/artifacts/jason_full_test_runs/$VALIDATION_RUN_ID/summary.json"

echo "[summary] $SUMMARY_FILE"
PYTHONDONTWRITEBYTECODE=1 uv run python - "$SUMMARY_FILE" <<'PY'
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

summary_file = Path(sys.argv[1])
if not summary_file.exists():
	print(f"summary_missing={summary_file}")
	sys.exit(0)
summary = json.loads(summary_file.read_text(encoding="utf-8"))
records = summary.get("validations") or []
by_domain: dict[str, list[dict[str, object]]] = defaultdict(list)
for record in records:
	by_domain[str(record.get("domain"))].append(record)

print("domain,total,jason_runtime_ok,val_ok,overall_ok,timeout,actions,total_seconds")
for domain in sorted(by_domain):
	items = by_domain[domain]
	jason_runtime_ok = sum(
		1
		for item in items
		if item.get("status")
		in {
			"success",
			"plan_verifier_failed",
			"plan_verifier_timeout",
			"plan_verifier_unavailable",
		}
	)
	val_ok = sum(1 for item in items if item.get("plan_verifier_success") is True)
	overall_ok = sum(1 for item in items if item.get("success") is True)
	timeout = sum(
		1
		for item in items
		if item.get("timed_out") or "timeout" in str(item.get("status") or "")
	)
	actions = sum(int(item.get("action_count") or 0) for item in items)
	total_seconds = sum(float(item.get("duration_seconds") or 0.0) for item in items)
	print(
		f"{domain},{len(items)},{jason_runtime_ok},{val_ok},{overall_ok},"
		f"{timeout},{actions},{total_seconds:.2f}"
	)

failed = [item for item in records if not item.get("success")]
if failed:
	print("\nfailed_cases:")
	for item in failed[:50]:
		print(
			f"- {item.get('domain')} test={item.get('test_index')} "
			f"status={item.get('status')} val={item.get('plan_verifier_success')} "
			f"actions={item.get('action_count')} output={item.get('output_dir')}"
		)
	if len(failed) > 50:
		print(f"- ... {len(failed) - 50} more")

print(f"\nrun_root={summary.get('run_root')}")
print(f"source_batch_root={summary.get('source_batch_root')}")
PY

exit "$VALIDATION_EXIT_CODE"
