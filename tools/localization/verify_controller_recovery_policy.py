#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib

root = pathlib.Path(__file__).resolve().parents[2]
path = root / "localization" / "controller_roles.json"
cfg = json.loads(path.read_text(encoding="utf-8"))

if int(cfg.get("schema_version", 0)) < 3:
    raise SystemExit("controller_roles schema_version must be >= 3")

rr = cfg.get("runtime_recovery") or {}
wa = rr.get("wait_actions") or {}
cr = rr.get("conversation_rollover") or {}
wd = rr.get("watchdog") or {}
wp = rr.get("wave_progression") or {}

required = {
    "wait_actions.authoritative_lookup": wa.get("authoritative_lookup") == "github_actions_run_by_id",
    "wait_actions.bypass_generic_actions_cache": wa.get("bypass_generic_actions_cache") is True,
    "wait_actions.bound_run_nonterminal_cache_ttl_seconds": wa.get("bound_run_nonterminal_cache_ttl_seconds") == 0,
    "wait_actions.retry_same_task_id": wa.get("retry_same_task_id") is True,
    "wait_actions.retry_increments_attempt": wa.get("retry_increments_attempt") is True,
    "wait_actions.ci_failure_consumes_chat_rollover": wa.get("ci_failure_consumes_chat_rollover") is False,
    "conversation_rollover.applies_to_ci_failure": cr.get("applies_to_ci_failure") is False,
    "watchdog.observe_only_allowed_for_wait_actions": wd.get("observe_only_allowed_for_wait_actions") is False,
    "wave_progression.ab_pass_to_c_immediately": wp.get("ab_pass_to_c_immediately") is True,
    "wave_progression.c_pass_to_next_ab_immediately": wp.get("c_pass_to_next_ab_immediately") is True,
    "wave_progression.wait_for_chat_expiry_after_terminal_result": wp.get("wait_for_chat_expiry_after_terminal_result") is False,
}

expected_failures = {"failure", "cancelled", "timed_out", "action_required", "stale"}
actual_failures = set(wa.get("retry_terminal_failure_conclusions") or [])
required["wait_actions.retry_terminal_failure_conclusions"] = expected_failures.issubset(actual_failures)

bad = [name for name, ok in required.items() if not ok]
if bad:
    raise SystemExit("controller recovery policy invalid: " + ", ".join(bad))

print("controller recovery policy PASS")
print("WAIT_ACTIONS exact-run polling is cache-bypassed; CI retry is separate from chat rollover")
