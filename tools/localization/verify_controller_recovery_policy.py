#!/usr/bin/env python3
from __future__ import annotations
import json
import pathlib

root = pathlib.Path(__file__).resolve().parents[2]
cfg = json.loads((root / "localization" / "controller_roles.json").read_text(encoding="utf-8"))

if int(cfg.get("schema_version", 0)) < 4:
    raise SystemExit("controller_roles schema_version must be >= 4")

rr = cfg.get("runtime_recovery") or {}
wa = rr.get("wait_actions") or {}
cr = rr.get("conversation_rollover") or {}
wd = rr.get("watchdog") or {}
wp = rr.get("wave_progression") or {}
sr = rr.get("startup_reconcile") or {}
rt = cfg.get("runtime_tuning") or {}
obs = cfg.get("runtime_observability") or {}

required = {
    "wait_actions.authoritative_lookup": wa.get("authoritative_lookup") == "github_actions_run_by_id",
    "wait_actions.bypass_generic_actions_cache": wa.get("bypass_generic_actions_cache") is True,
    "wait_actions.bound_run_nonterminal_cache_ttl_seconds": wa.get("bound_run_nonterminal_cache_ttl_seconds") == 0,
    "wait_actions.force_uncached_refresh_after_poll_intervals": int(wa.get("force_uncached_refresh_after_poll_intervals", 99)) <= 2,
    "wait_actions.force_uncached_refresh_after_seconds": int(wa.get("force_uncached_refresh_after_seconds", 9999)) <= 60,
    "wait_actions.refresh_jobs_with_forced_run_refresh": wa.get("refresh_jobs_with_forced_run_refresh") is True,
    "wait_actions.retry_same_task_id": wa.get("retry_same_task_id") is True,
    "wait_actions.retry_increments_attempt": wa.get("retry_increments_attempt") is True,
    "wait_actions.ci_failure_consumes_chat_rollover": wa.get("ci_failure_consumes_chat_rollover") is False,
    "conversation_rollover.applies_to_ci_failure": cr.get("applies_to_ci_failure") is False,
    "watchdog.observe_only_allowed_for_wait_actions": wd.get("observe_only_allowed_for_wait_actions") is False,
    "watchdog.queue_idle_rearm_seconds": int(wd.get("queue_idle_rearm_seconds", 9999)) <= 90,
    "watchdog.queue_idle_requires_unfinished_work": wd.get("queue_idle_requires_unfinished_work") is True,
    "watchdog.wait_actions_stale_seconds": int(wd.get("wait_actions_stale_seconds", 9999)) <= 90,
    "watchdog.busy_stall_seconds": int(wd.get("busy_stall_seconds", 0)) >= 1800,
    "watchdog.force_stop_active_generation": wd.get("force_stop_active_generation") is False,
    "wave_progression.ab_pass_to_c_immediately": wp.get("ab_pass_to_c_immediately") is True,
    "wave_progression.c_pass_to_next_ab_immediately": wp.get("c_pass_to_next_ab_immediately") is True,
    "wave_progression.wait_for_chat_expiry_after_terminal_result": wp.get("wait_for_chat_expiry_after_terminal_result") is False,
    "wave_progression.terminal_transition_target_seconds": int(wp.get("terminal_transition_target_seconds", 9999)) <= 30,
    "startup_reconcile.enabled": sr.get("enabled") is True,
    "startup_reconcile.refresh_branch_head_first": sr.get("refresh_branch_head_first") is True,
    "startup_reconcile.clear_discovery_cache_first": sr.get("clear_discovery_cache_first") is True,
    "startup_reconcile.reconcile_all_nonterminal_lanes": sr.get("reconcile_all_nonterminal_lanes") is True,
    "startup_reconcile.exact_run_lookup_for_wait_actions": sr.get("exact_run_lookup_for_wait_actions") is True,
    "startup_reconcile.refresh_branch_head_before_retry": sr.get("refresh_branch_head_before_retry") is True,
    "runtime_tuning.queue_check_seconds": rt.get("queue_check_seconds") == 15,
    "runtime_tuning.github_bound_run_poll_seconds": int(rt.get("github_bound_run_poll_seconds", 9999)) <= 30,
    "runtime_tuning.github_discovery_poll_seconds": int(rt.get("github_discovery_poll_seconds", 9999)) <= 60,
    "runtime_tuning.bound_run_nonterminal_cache_ttl_seconds": rt.get("bound_run_nonterminal_cache_ttl_seconds") == 0,
    "runtime_tuning.queue_next_task_delay_seconds": int(rt.get("queue_next_task_delay_seconds", 9999)) <= 15,
    "runtime_tuning.parallel_lane_stagger_seconds": int(rt.get("parallel_lane_stagger_seconds", 9999)) <= 15,
    "runtime_tuning.parallel_distinct_slot_send_gap_seconds": int(rt.get("parallel_distinct_slot_send_gap_seconds", 9999)) <= 15,
    "runtime_observability.queue_loop_heartbeat_seconds": int(obs.get("queue_loop_heartbeat_seconds", 9999)) <= 15,
    "runtime_observability.heartbeat_stale_after_seconds": int(obs.get("heartbeat_stale_after_seconds", 9999)) <= 45,
    "runtime_observability.active_state_source_of_truth": obs.get("active_state_source_of_truth") == "active_by_lane",
    "runtime_observability.queue_active_semantics": obs.get("queue_active_semantics") == "derived_summary",
    "runtime_observability.queue_active_null_allowed_only_when_active_by_lane_empty": obs.get("queue_active_null_allowed_only_when_active_by_lane_empty") is True,
}

expected_failures = {"failure","cancelled","timed_out","action_required","stale"}
required["wait_actions.retry_terminal_failure_conclusions"] = expected_failures.issubset(set(wa.get("retry_terminal_failure_conclusions") or []))
runtime_fields = {"queue_loop_heartbeat_at","last_scheduler_decision_at","last_scheduler_decision","blocked_reason"}
required["runtime_observability.required_runtime_fields"] = runtime_fields.issubset(set(obs.get("required_runtime_fields") or []))

bad = [name for name, ok in required.items() if not ok]
if bad:
    raise SystemExit("controller recovery policy invalid: " + ", ".join(bad))

print("controller recovery policy PASS")
print("bound Actions poll <=30s, WAIT_ACTIONS recovery <=90s, idle rearm <=90s")
print("A/B stagger <=15s, heartbeat <=15s, startup reconciliation mandatory")
