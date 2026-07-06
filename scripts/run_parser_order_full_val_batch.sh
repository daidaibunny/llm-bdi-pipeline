#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RUN_ID="${RUN_ID:-parser-order-val-$(date +%Y%m%d-%H%M%S)}"
BATCH_ID="${BATCH_ID:-$RUN_ID}"
VALIDATION_RUN_ID="${VALIDATION_RUN_ID:-$RUN_ID-full-test}"

MOOSE_WORKERS="${MOOSE_WORKERS:-4}"
JASON_WORKERS="${JASON_WORKERS:-6}"
TRAIN_TIMEOUT_SECONDS="${TRAIN_TIMEOUT_SECONDS:-1800}"
JASON_TIMEOUT_SECONDS="${JASON_TIMEOUT_SECONDS:-1800}"
VAL_TIMEOUT_SECONDS="${VAL_TIMEOUT_SECONDS:-1800}"

if [[ $# -gt 0 ]]; then
	DOMAINS=("$@")
else
	DOMAINS=(ferry miconic gripper logistics blocks depots)
fi

DOMAIN_ARGS=()
for domain in "${DOMAINS[@]}"; do
	DOMAIN_ARGS+=(--domain "$domain")
done

echo "[run] id=$RUN_ID"
echo "[run] domains=${DOMAINS[*]}"
echo "[stage 1] generating MOOSE-backed atomic ASL libraries"

PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_timestamped_moose_asl_batch.py \
	--timestamp-id "$BATCH_ID" \
	--num-workers "$MOOSE_WORKERS" \
	--atomic-library-mode validated-policy-lifting \
	--train-timeout-seconds "$TRAIN_TIMEOUT_SECONDS" \
	--dump-timeout-seconds "${DUMP_TIMEOUT_SECONDS:-300}" \
	--append-timeout-seconds "${APPEND_TIMEOUT_SECONDS:-300}" \
	--jason-timeout-seconds "$JASON_TIMEOUT_SECONDS" \
	--jason-plan-verifier-timeout-seconds "$VAL_TIMEOUT_SECONDS" \
	"${DOMAIN_ARGS[@]}"

echo "[stage 2] appending PDDL parser-order full-test goals, running Jason, then VAL"

PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_full_test_jason_validation.py \
	--batch-id "$BATCH_ID" \
	--run-id "$VALIDATION_RUN_ID" \
	--num-workers "$JASON_WORKERS" \
	--timeout-seconds "$JASON_TIMEOUT_SECONDS" \
	--plan-verifier-command "bash $PROJECT_ROOT/scripts/validate_with_docker_val.sh" \
	--require-plan-verifier \
	--plan-verifier-timeout-seconds "$VAL_TIMEOUT_SECONDS" \
	--atomic-library-mode validated-policy-lifting \
	--write-domain-long-asl \
	"${DOMAIN_ARGS[@]}"

SUMMARY_FILE="$PROJECT_ROOT/artifacts/jason_full_test_runs/$VALIDATION_RUN_ID/summary.json"

echo "[summary] $SUMMARY_FILE"
PYTHONDONTWRITEBYTECODE=1 uv run python - "$SUMMARY_FILE" <<'PY'
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

summary_file = Path(sys.argv[1])
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
