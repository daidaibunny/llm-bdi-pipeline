#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRIMARY_ROOT="${EXTERNAL_REFERENCE_PRIMARY_ROOT:-${ROOT_DIR}/artifacts/external_reference_repairs/remote-c14c5ece-primary}"
C_PRIMARY="${PRIMARY_ROOT}/artifacts/external_planning_references/aaai-instance-references-72b0604f/summary.json"
D_PRIMARY="${PRIMARY_ROOT}/artifacts/direct_temporal_references/aaai-direct-temporal-72b0604f/summary.json"
C_RUN_ID="aaai-c-infrastructure-retry-f930f52a"
D_RUN_ID="aaai-d-infrastructure-retry-serial"
RETRY_ROOT="${ROOT_DIR}/artifacts/external_reference_repairs"
PLAN_VERIFIER_COMMAND="bash ${ROOT_DIR}/scripts/validate_with_docker_val.sh"

MODE="run"
if [[ "${1:-}" == "--list-only" ]]; then
	MODE="list"
elif [[ $# -gt 0 ]]; then
	printf 'usage: %s [--list-only]\n' "$0" >&2
	exit 2
fi

for summary in "${C_PRIMARY}" "${D_PRIMARY}"; do
	if [[ ! -f "${summary}" ]]; then
		printf '[repair] missing primary summary: %s\n' "${summary}" >&2
		exit 1
	fi
done

build_selector() {
	local summary_file="$1"
	local kind="$2"
	local expected_count="$3"
	uv run python - "${summary_file}" "${kind}" "${expected_count}" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import re
import sys


summary_file = Path(sys.argv[1])
kind = sys.argv[2]
expected_count = int(sys.argv[3])
payload = json.loads(summary_file.read_text(encoding="utf-8"))


def is_infrastructure_failure(status: object) -> bool:
	value = str(status or "")
	return value in {"runner_error", "tool_unavailable"} or value.endswith(
		("_runner_error", "_tool_unavailable"),
	)


records = [
	record
	for record in payload.get("results", ())
	if is_infrastructure_failure(record.get("status"))
]
if kind == "achievement":
	case_ids = sorted(
		f"{record['domain']}:{Path(record['problem_file']).name}"
		for record in records
	)
elif kind == "direct_temporal":
	case_ids = sorted(str(record["sample_id"]) for record in records)
else:
	raise SystemExit(f"unknown repair kind: {kind}")

if len(case_ids) != expected_count or len(case_ids) != len(set(case_ids)):
	raise SystemExit(
		f"{kind} infrastructure set mismatch: "
		f"expected={expected_count} observed={len(case_ids)}",
	)
for case_id in case_ids:
	print(f"[repair:{kind}] {case_id}", file=sys.stderr)
print("^(?:" + "|".join(re.escape(case_id) for case_id in case_ids) + ")$")
PY
}

expected_count=9
C_SELECTOR="$(build_selector "${C_PRIMARY}" achievement "${expected_count}")"
expected_count=46
D_SELECTOR="$(build_selector "${D_PRIMARY}" direct_temporal "${expected_count}")"

if [[ "${MODE}" == "list" ]]; then
	exit 0
fi

cd "${ROOT_DIR}"
if [[ -n "$(git status --porcelain --untracked-files=normal)" ]]; then
	printf '[repair] refusing to run from a dirty source tree\n' >&2
	exit 1
fi

bash scripts/setup_external_planning_references.sh --check

PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_external_planning_references.py \
	--output-root "${RETRY_ROOT}" \
	--run-id "${C_RUN_ID}" \
	--method lama \
	--domain blocksworld-tower \
	--domain depots \
	--case-id-regex "${C_SELECTOR}" \
	--num-workers 1 \
	--timeout-seconds 1800 \
	--max-rss-gb 8 \
	--plan-verifier-timeout-seconds 1800 \
	--plan-verifier-command "${PLAN_VERIFIER_COMMAND}" \
	--resume

PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_direct_temporal_reference.py \
	--benchmark-root paper_artifacts/temporal_goal_benchmark/v1 \
	--output-root "${RETRY_ROOT}" \
	--run-id "${D_RUN_ID}" \
	--sample-id-regex "${D_SELECTOR}" \
	--num-workers 1 \
	--timeout-seconds 1800 \
	--max-rss-gb 8 \
	--plan-verifier-timeout-seconds 1800 \
	--plan-verifier-command "${PLAN_VERIFIER_COMMAND}" \
	--resume

PYTHONDONTWRITEBYTECODE=1 uv run python scripts/merge_external_reference_retries.py \
	--kind achievement \
	--primary-summary "${C_PRIMARY}" \
	--retry-summary "${RETRY_ROOT}/${C_RUN_ID}/summary.json" \
	--output-summary "${ROOT_DIR}/artifacts/external_planning_references/aaai-instance-references-72b0604f/summary.json"

PYTHONDONTWRITEBYTECODE=1 uv run python scripts/merge_external_reference_retries.py \
	--kind direct_temporal \
	--primary-summary "${D_PRIMARY}" \
	--retry-summary "${RETRY_ROOT}/${D_RUN_ID}/summary.json" \
	--output-summary "${ROOT_DIR}/artifacts/direct_temporal_references/aaai-direct-temporal-72b0604f/summary.json"

printf '[repair] complete: C and D merged summaries are ready\n'
