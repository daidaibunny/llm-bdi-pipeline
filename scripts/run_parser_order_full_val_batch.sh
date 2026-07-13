#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RUN_ID="${RUN_ID:-parser-order-val-$(date +%Y%m%d-%H%M%S)}"
BATCH_ID="${BATCH_ID:-$RUN_ID}"
VALIDATION_RUN_ID="${VALIDATION_RUN_ID:-$RUN_ID-full-test}"

WORKERS="${WORKERS:-6}"
MOOSE_WORKERS="${MOOSE_WORKERS:-1}"
MOOSE_SEEDS="${MOOSE_SEEDS:-0 1 2 3 4}"
MOOSE_SEED_PARALLELISM="${MOOSE_SEED_PARALLELISM:-5}"
JASON_WORKERS="${JASON_WORKERS:-$WORKERS}"
TRAIN_TIMEOUT_SECONDS="${TRAIN_TIMEOUT_SECONDS:-43200}"
JASON_TIMEOUT_SECONDS="${JASON_TIMEOUT_SECONDS:-1800}"
VAL_TIMEOUT_SECONDS="${VAL_TIMEOUT_SECONDS:-1800}"
JASON_JAVA_STACK_SIZE="${JASON_JAVA_STACK_SIZE:-64m}"
PLAN_VERIFIER_COMMAND="${PLAN_VERIFIER_COMMAND:-bash $PROJECT_ROOT/scripts/validate_with_docker_val.sh}"
LOG_ROOT="$PROJECT_ROOT/artifacts/parser_order_full_val_logs/$RUN_ID"

fail_configuration() {
	printf '[configuration-error] %s\n' "$1" >&2
	exit 2
}

is_positive_integer() {
	[[ "$1" =~ ^[1-9][0-9]*$ ]]
}

if [[ -n "${MOOSE_RANDOM_SEED+x}" ]]; then
	fail_configuration "MOOSE_RANDOM_SEED is obsolete; use the fixed five-seed MOOSE_SEEDS protocol."
fi
if [[ "$MOOSE_WORKERS" != "1" ]]; then
	fail_configuration "MOOSE_WORKERS must be 1 so a seed has one deterministic random stream; parallelize independent seeds with MOOSE_SEED_PARALLELISM."
fi
if ! is_positive_integer "$MOOSE_SEED_PARALLELISM"; then
	fail_configuration "MOOSE_SEED_PARALLELISM must be a positive integer."
fi
if ! is_positive_integer "$JASON_WORKERS"; then
	fail_configuration "JASON_WORKERS must be a positive integer."
fi
if ! is_positive_integer "$TRAIN_TIMEOUT_SECONDS"; then
	fail_configuration "TRAIN_TIMEOUT_SECONDS must be a positive integer."
fi
if ! is_positive_integer "$JASON_TIMEOUT_SECONDS"; then
	fail_configuration "JASON_TIMEOUT_SECONDS must be a positive integer."
fi
if ! is_positive_integer "$VAL_TIMEOUT_SECONDS"; then
	fail_configuration "VAL_TIMEOUT_SECONDS must be a positive integer."
fi

read -r -a MOOSE_SEED_VALUES <<< "$MOOSE_SEEDS"
if [[ "${#MOOSE_SEED_VALUES[@]}" -ne 5 ]]; then
	fail_configuration "MOOSE_SEEDS must contain exactly five independent integer seeds."
fi
if [[ "$MOOSE_SEED_PARALLELISM" -gt "${#MOOSE_SEED_VALUES[@]}" ]]; then
	fail_configuration "MOOSE_SEED_PARALLELISM cannot exceed the number of seeds."
fi
for ((seed_index = 0; seed_index < ${#MOOSE_SEED_VALUES[@]}; seed_index += 1)); do
	seed="${MOOSE_SEED_VALUES[$seed_index]}"
	if [[ ! "$seed" =~ ^[0-9]+$ ]]; then
		fail_configuration "every MOOSE seed must be a non-negative integer: $seed"
	fi
	for ((prior_index = 0; prior_index < seed_index; prior_index += 1)); do
		if [[ "$seed" == "${MOOSE_SEED_VALUES[$prior_index]}" ]]; then
			fail_configuration "MOOSE_SEEDS must not contain duplicate seed $seed."
		fi
	done
done

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
echo "[run] moose_seeds=${MOOSE_SEED_VALUES[*]} evidence_merged=false"
echo "[run] moose_internal_workers=$MOOSE_WORKERS seed_parallelism=$MOOSE_SEED_PARALLELISM"
echo "[run] jason_workers=$JASON_WORKERS cross_seed_jason_parallelism=1"
echo "[run] moose_train_timeout_seconds=$TRAIN_TIMEOUT_SECONDS"
echo "[run] jason_timeout_seconds=$JASON_TIMEOUT_SECONDS val_timeout_seconds=$VAL_TIMEOUT_SECONDS jason_java_stack_size=$JASON_JAVA_STACK_SIZE"
echo "[run] plan_verifier_command=$PLAN_VERIFIER_COMMAND"
mkdir -p "$LOG_ROOT"

run_moose_seed() {
	local seed="$1"
	local seed_batch_id="${BATCH_ID}-seed${seed}"
	local seed_log_root="$LOG_ROOT/seed${seed}"
	local stdout_file="$seed_log_root/moose_batch.stdout.log"
	local stderr_file="$seed_log_root/moose_batch.stderr.log"
	local exit_code_file="$seed_log_root/moose_exit_code.txt"
	local started_at
	local elapsed_seconds
	local exit_code

	mkdir -p "$seed_log_root"
	started_at="$(date +%s)"
	echo "[stage 1:start] seed=$seed batch=$seed_batch_id"
	set +e
	PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_timestamped_moose_asl_batch.py \
		--timestamp-id "$seed_batch_id" \
		--num-workers "$MOOSE_WORKERS" \
		--random-seed "$seed" \
		--atomic-library-mode validated-policy-lifting \
		--skip-temporal-append \
		--resume \
		--train-timeout-seconds "$TRAIN_TIMEOUT_SECONDS" \
		--dump-timeout-seconds "${DUMP_TIMEOUT_SECONDS:-300}" \
		--append-timeout-seconds "${APPEND_TIMEOUT_SECONDS:-300}" \
		--jason-timeout-seconds "$JASON_TIMEOUT_SECONDS" \
		--jason-plan-verifier-timeout-seconds "$VAL_TIMEOUT_SECONDS" \
		"${DOMAIN_ARGS[@]}" \
		2>"$stderr_file" \
		| tee "$stdout_file" \
		| while IFS= read -r line; do
			case "$line" in
				"[moose-domain]"*) printf '[seed=%s] %s\n' "$seed" "$line" ;;
			esac
		done
	exit_code="${PIPESTATUS[0]}"
	set -e
	printf '%s\n' "$exit_code" > "$exit_code_file"
	elapsed_seconds="$(( $(date +%s) - started_at ))"
	echo "[stage 1:done] seed=$seed exit_code=$exit_code elapsed=${elapsed_seconds}s stdout=$stdout_file stderr=$stderr_file"
	return 0
}

SEED_PIDS=()

wait_for_moose_seed_group() {
	local pid
	for pid in "${SEED_PIDS[@]}"; do
		if ! wait "$pid"; then
			echo "[stage 1:internal-error] seed process pid=$pid exited unexpectedly" >&2
		fi
	done
	SEED_PIDS=()
}

echo "[stage 1] generating five independent MOOSE-backed atomic ASL batches"
for seed in "${MOOSE_SEED_VALUES[@]}"; do
	run_moose_seed "$seed" &
	SEED_PIDS+=("$!")
	if [[ "${#SEED_PIDS[@]}" -ge "$MOOSE_SEED_PARALLELISM" ]]; then
		wait_for_moose_seed_group
	fi
done
if [[ "${#SEED_PIDS[@]}" -gt 0 ]]; then
	wait_for_moose_seed_group
fi

OVERALL_EXIT_CODE=0
for seed in "${MOOSE_SEED_VALUES[@]}"; do
	seed_exit_file="$LOG_ROOT/seed${seed}/moose_exit_code.txt"
	if [[ ! -f "$seed_exit_file" ]]; then
		echo "[stage 1:fail] seed=$seed missing_exit_code=$seed_exit_file"
		OVERALL_EXIT_CODE=1
		continue
	fi
	seed_exit_code="$(<"$seed_exit_file")"
	if [[ "$seed_exit_code" -ne 0 ]]; then
		echo "[stage 1:fail] seed=$seed exit_code=$seed_exit_code"
		OVERALL_EXIT_CODE=1
	fi
done

print_validation_summary() {
	local seed="$1"
	local summary_file="$2"
	PYTHONDONTWRITEBYTECODE=1 uv run python - "$seed" "$summary_file" <<'PY'
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys

seed = int(sys.argv[1])
summary_file = Path(sys.argv[2])
if not summary_file.exists():
	print(f"[stage 2:summary-missing] seed={seed} path={summary_file}")
	raise SystemExit(0)

summary = json.loads(summary_file.read_text(encoding="utf-8"))
by_domain = defaultdict(list)
for record in summary.get("validations") or []:
	by_domain[str(record.get("domain"))].append(record)

for domain in sorted(by_domain):
	records = by_domain[domain]
	successes = sum(1 for record in records if record.get("success") is True)
	timeouts = sum(
		1
		for record in records
		if record.get("timed_out") or "timeout" in str(record.get("status") or "")
	)
	print(
		f"[stage 2:domain] seed={seed} domain={domain} "
		f"success={successes}/{len(records)} timeout={timeouts}"
	)
PY
}

run_validation_seed() {
	local seed="$1"
	local seed_batch_id="${BATCH_ID}-seed${seed}"
	local seed_validation_run_id="${VALIDATION_RUN_ID}-seed${seed}"
	local seed_log_root="$LOG_ROOT/seed${seed}"
	local exit_code_file="$seed_log_root/validation_exit_code.txt"
	local summary_file="$PROJECT_ROOT/artifacts/jason_full_test_runs/$seed_validation_run_id/summary.json"
	local started_at
	local elapsed_seconds
	local exit_code

	started_at="$(date +%s)"
	echo "[stage 2:start] seed=$seed batch=$seed_batch_id run=$seed_validation_run_id"
	set +e
	PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_full_test_jason_validation.py \
		--batch-id "$seed_batch_id" \
		--run-id "$seed_validation_run_id" \
		--num-workers "$JASON_WORKERS" \
		--timeout-seconds "$JASON_TIMEOUT_SECONDS" \
		--jason-java-stack-size "$JASON_JAVA_STACK_SIZE" \
		--plan-verifier-command "$PLAN_VERIFIER_COMMAND" \
		--require-plan-verifier \
		--plan-verifier-timeout-seconds "$VAL_TIMEOUT_SECONDS" \
		--atomic-library-mode validated-policy-lifting \
		--write-per-test-runtime-asl \
		--suppress-final-summary-json \
		--resume \
		"${DOMAIN_ARGS[@]}"
	exit_code="$?"
	set -e
	printf '%s\n' "$exit_code" > "$exit_code_file"
	elapsed_seconds="$(( $(date +%s) - started_at ))"
	echo "[stage 2:done] seed=$seed exit_code=$exit_code elapsed=${elapsed_seconds}s summary=$summary_file"
	print_validation_summary "$seed" "$summary_file"
	if [[ "$exit_code" -ne 0 ]]; then
		OVERALL_EXIT_CODE=1
	fi
}

echo "[stage 2] validating each seed library independently with Jason and VAL"
for seed in "${MOOSE_SEED_VALUES[@]}"; do
	seed_exit_file="$LOG_ROOT/seed${seed}/moose_exit_code.txt"
	if [[ ! -f "$seed_exit_file" ]] || [[ "$(<"$seed_exit_file")" -ne 0 ]]; then
		echo "[stage 2:skip] seed=$seed reason=moose_generation_failed"
		continue
	fi
	run_validation_seed "$seed"
done

AGGREGATE_FILE="$LOG_ROOT/five_seed_summary.json"
PYTHONDONTWRITEBYTECODE=1 uv run python - \
	"$PROJECT_ROOT" \
	"$RUN_ID" \
	"$BATCH_ID" \
	"$VALIDATION_RUN_ID" \
	"$MOOSE_SEEDS" \
	"$MOOSE_WORKERS" \
	"$MOOSE_SEED_PARALLELISM" \
	"$JASON_WORKERS" \
	"$AGGREGATE_FILE" <<'PY'
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from statistics import fmean, stdev
import sys

project_root = Path(sys.argv[1])
run_id = sys.argv[2]
batch_id = sys.argv[3]
validation_run_id = sys.argv[4]
seeds = [int(value) for value in sys.argv[5].split()]
moose_workers = int(sys.argv[6])
seed_parallelism = int(sys.argv[7])
jason_workers = int(sys.argv[8])
output_file = Path(sys.argv[9])
log_root = output_file.parent

sys.path.insert(0, str(project_root / "src"))
from domain_level_planning.evidence_module import parse_moose_readable_policy


def read_exit_code(path: Path) -> int | None:
	if not path.exists():
		return None
	return int(path.read_text(encoding="utf-8").strip())


def file_sha256(path: Path) -> str | None:
	if not path.exists():
		return None
	hasher = hashlib.sha256()
	with path.open("rb") as handle:
		for block in iter(lambda: handle.read(1024 * 1024), b""):
			hasher.update(block)
	return hasher.hexdigest()


def atom_payload(atom: object) -> tuple[str, tuple[str, ...]]:
	return (
		str(getattr(atom, "predicate")),
		tuple(str(value) for value in getattr(atom, "arguments")),
	)


def canonical_rule_set_sha256(path: Path) -> str | None:
	if not path.exists():
		return None
	rules = parse_moose_readable_policy(path.read_text(encoding="utf-8"))
	rows = []
	for rule in rules:
		rows.append(
			{
				"precedence": rule.precedence,
				"variables": tuple(rule.variables),
				"state_conditions": tuple(
					atom_payload(atom) for atom in rule.state_conditions
				),
				"goal_conditions": tuple(
					atom_payload(atom) for atom in rule.goal_conditions
				),
				"state_numeric_conditions": tuple(
					str(item) for item in rule.state_numeric_conditions
				),
				"goal_numeric_conditions": tuple(
					str(item) for item in rule.goal_numeric_conditions
				),
				"actions": tuple(atom_payload(atom) for atom in rule.actions),
			}
		)
	canonical = "\n".join(sorted(json.dumps(row, sort_keys=True) for row in rows))
	return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


repetitions = []
domain_rates: dict[str, list[float]] = defaultdict(list)
domain_totals: dict[str, int] = defaultdict(int)
domain_successes: dict[str, int] = defaultdict(int)

for seed in seeds:
	seed_batch_id = f"{batch_id}-seed{seed}"
	seed_validation_id = f"{validation_run_id}-seed{seed}"
	seed_log_root = log_root / f"seed{seed}"
	batch_root = project_root / "artifacts" / "moose_asl_batches" / seed_batch_id
	validation_root = project_root / "artifacts" / "jason_full_test_runs" / seed_validation_id
	batch_summary_file = batch_root / "run_logs" / "summary.json"
	validation_summary_file = validation_root / "summary.json"
	batch_summary = (
		json.loads(batch_summary_file.read_text(encoding="utf-8"))
		if batch_summary_file.exists()
		else {}
	)
	validation_summary = (
		json.loads(validation_summary_file.read_text(encoding="utf-8"))
		if validation_summary_file.exists()
		else {}
	)

	evidence = {}
	for domain_record in batch_summary.get("domains") or []:
		domain = str(domain_record.get("domain"))
		readable = batch_root / "run_logs" / domain / f"{domain}.model.readable"
		asl = batch_root / "domain_libraries" / domain / "plan_library.asl"
		evidence[domain] = {
			"generation_success": domain_record.get("success") is True,
			"readable_policy_sha256": file_sha256(readable),
			"canonical_rule_set_sha256": canonical_rule_set_sha256(readable),
			"compiled_asl_sha256": file_sha256(asl),
		}

	validation_by_domain = defaultdict(list)
	for record in validation_summary.get("validations") or []:
		validation_by_domain[str(record.get("domain"))].append(record)
	validation = {}
	for domain, records in sorted(validation_by_domain.items()):
		total = len(records)
		success = sum(1 for record in records if record.get("success") is True)
		timeout = sum(
			1
			for record in records
			if record.get("timed_out")
			or "timeout" in str(record.get("status") or "")
		)
		validation[domain] = {
			"total": total,
			"success": success,
			"timeout": timeout,
			"coverage": success / total if total else None,
		}
		if total:
			domain_rates[domain].append(success / total)
			domain_totals[domain] += total
			domain_successes[domain] += success

	moose_exit_code = read_exit_code(seed_log_root / "moose_exit_code.txt")
	validation_exit_code = read_exit_code(seed_log_root / "validation_exit_code.txt")
	repetitions.append(
		{
			"seed": seed,
			"batch_id": seed_batch_id,
			"validation_run_id": seed_validation_id,
			"moose_exit_code": moose_exit_code,
			"validation_exit_code": validation_exit_code,
			"success": moose_exit_code == 0 and validation_exit_code == 0,
			"evidence": evidence,
			"validation": validation,
		}
	)

aggregate_domains = {}
for domain in sorted(domain_rates):
	rates = domain_rates[domain]
	aggregate_domains[domain] = {
		"completed_repetitions": len(rates),
		"total_cases_across_repetitions": domain_totals[domain],
		"successful_cases_across_repetitions": domain_successes[domain],
		"mean_seed_coverage": fmean(rates),
		"sample_stddev_seed_coverage": stdev(rates) if len(rates) > 1 else 0.0,
	}

payload = {
	"schema_version": 1,
	"protocol": "five_independent_moose_synthesis_repetitions",
	"run_id": run_id,
	"seeds": seeds,
	"evidence_merged": False,
	"moose_internal_workers": moose_workers,
	"moose_seed_parallelism": seed_parallelism,
	"jason_workers_per_repetition": jason_workers,
	"cross_seed_jason_parallelism": 1,
	"repetitions": repetitions,
	"aggregate_domains": aggregate_domains,
}
output_file.write_text(
	json.dumps(payload, indent=2, sort_keys=True) + "\n",
	encoding="utf-8",
)

print("[aggregate] seed,moose_exit,jason_val_exit,success")
for repetition in repetitions:
	print(
		f"[aggregate] {repetition['seed']},{repetition['moose_exit_code']},"
		f"{repetition['validation_exit_code']},{repetition['success']}"
	)
print("[aggregate] domain,repetitions,success,total,mean_coverage,stddev")
for domain, record in aggregate_domains.items():
	print(
		f"[aggregate] {domain},{record['completed_repetitions']},"
		f"{record['successful_cases_across_repetitions']},"
		f"{record['total_cases_across_repetitions']},"
		f"{record['mean_seed_coverage']:.6f},"
		f"{record['sample_stddev_seed_coverage']:.6f}"
	)
print(f"[aggregate] file={output_file}")
PY

exit "$OVERALL_EXIT_CODE"
