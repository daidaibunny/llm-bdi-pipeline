"""Normalize paper-facing results to an outcome-only public schema."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


EXCLUDED_PUBLIC_KEYS = {
	"benchmark_compatibility",
	"command",
	"commit",
	"compiler_freeze",
	"compiler_lock_wait_seconds",
	"completed_at",
	"created_at",
	"derived_metric_correction",
	"domain_file",
	"environment_dir",
	"finished_at",
	"infrastructure_retry",
	"method_source_equivalence",
	"model_file",
	"node_id",
	"policy_file",
	"planner_exit_code",
	"problem_files",
	"provenance",
	"released_at",
	"repair_num_workers",
	"revision",
	"run_id",
	"runtime_lock_wait_seconds",
	"sha256",
	"shared_jason_environments",
	"source_aggregate",
	"source_file",
	"source_revision",
	"started_at",
	"stderr",
	"stdout",
	"tracked_change_seed_exceptions",
	"tracked_source_changes",
	"untracked_source_files",
}
EXCLUDED_PUBLIC_KEY_FRAGMENTS = (
	"byte_identical",
	"fingerprint",
)
EXCLUDED_PUBLIC_KEY_SUFFIXES = (
	"_bytes",
	"_commit",
	"_command",
	"_dir",
	"_directory",
	"_file",
	"_files",
	"_path",
	"_paths",
	"_revision",
	"_revisions",
	"_root",
	"_run_id",
	"_sha256",
)


def outcome_only_payload(value: Any) -> Any:
	"""Remove execution identity and byte-level provenance from public results."""

	if isinstance(value, Mapping):
		return {
			str(key): outcome_only_payload(item)
			for key, item in value.items()
			if not is_excluded_public_key(str(key))
		}
	if isinstance(value, Sequence) and not isinstance(
		value,
		(str, bytes, bytearray),
	):
		return [outcome_only_payload(item) for item in value]
	return value


def is_excluded_public_key(key: str) -> bool:
	"""Return whether a key identifies a run, source snapshot, or byte digest."""

	return (
		key in EXCLUDED_PUBLIC_KEYS
		or key.endswith(EXCLUDED_PUBLIC_KEY_SUFFIXES)
		or any(fragment in key for fragment in EXCLUDED_PUBLIC_KEY_FRAGMENTS)
	)
