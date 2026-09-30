#!/usr/bin/env python3
from __future__ import annotations
import json
import pathlib

root = pathlib.Path(__file__).resolve().parents[2]
cfg = json.loads((root / "localization" / "controller_roles.json").read_text(encoding="utf-8"))

if int(cfg.get("schema_version", 0)) < 16:
    raise SystemExit("controller_roles schema_version must be >= 16")

rr = cfg.get("runtime_recovery") or {}
wa = rr.get("wait_actions") or {}
cr = rr.get("conversation_rollover") or {}
wd = rr.get("watchdog") or {}
cp = rr.get("continuous_progression") or {}
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
    "continuous_progression.producer_commit_releases_same_lane": cp.get("producer_commit_releases_same_lane") is True,
    "continuous_progression.producer_commit_enqueues_qa": cp.get("producer_commit_enqueues_qa") is True,
    "continuous_progression.producer_waits_for_actions": cp.get("producer_waits_for_actions") is False,
    "continuous_progression.c_batch_waits_for_actions": cp.get("c_batch_waits_for_actions") is True,
    "continuous_progression.c_completion_gates_producers": cp.get("c_completion_gates_producers") is False,
    "continuous_progression.qa_failure_gates_producers": cp.get("qa_failure_gates_producers") is False,
    "continuous_progression.terminal_transition_target_seconds": int(cp.get("terminal_transition_target_seconds", 9999)) <= 30,
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
    "runtime_tuning.queue_next_task_delay_seconds": int(rt.get("queue_next_task_delay_seconds", 9999)) <= 30,
    "runtime_tuning.parallel_lane_stagger_seconds": int(rt.get("parallel_lane_stagger_seconds", 9999)) <= 45,
    "runtime_tuning.parallel_distinct_slot_send_gap_seconds": int(rt.get("parallel_distinct_slot_send_gap_seconds", 9999)) <= 60,
    "runtime_tuning.localization_qa_batch_size": int(rt.get("localization_qa_batch_size", 0)) == 4,
    "runtime_tuning.localization_qa_coalesce_seconds": int(rt.get("localization_qa_coalesce_seconds", 9999)) <= 60,
    "runtime_tuning.localization_same_slot_send_gap_seconds": int(rt.get("localization_same_slot_send_gap_seconds", 9999)) <= 30,
    "runtime_tuning.localization_slot_dedup_seconds": int(rt.get("localization_slot_dedup_seconds", 9999)) <= 30,
    "runtime_observability.queue_loop_heartbeat_seconds": int(obs.get("queue_loop_heartbeat_seconds", 9999)) <= 15,
    "runtime_observability.heartbeat_stale_after_seconds": int(obs.get("heartbeat_stale_after_seconds", 9999)) <= 45,
    "runtime_observability.active_state_source_of_truth": obs.get("active_state_source_of_truth") == "active_by_lane",
    "runtime_observability.queue_active_semantics": obs.get("queue_active_semantics") == "derived_summary_with_independent_qa",
    "runtime_observability.queue_active_null_allowed_only_when_active_by_lane_empty": obs.get("queue_active_null_allowed_only_when_active_by_lane_empty") is True,
}

expected_failures = {"failure","cancelled","timed_out","action_required","stale"}
required["wait_actions.retry_terminal_failure_conclusions"] = expected_failures.issubset(set(wa.get("retry_terminal_failure_conclusions") or []))

ga = cfg.get("github_access_validation") or {}
required["github_access_validation.repository"] = ga.get("repository") == "thp32tt/OutRun2006Tweaks"
required["github_access_validation.refresh_before_permission_block"] = ga.get("refresh_before_permission_block") is True
required["github_access_validation.authenticated_github_connector_first"] = ga.get("authenticated_github_connector_first") is True
required["github_access_validation.public_web_search_is_authoritative"] = ga.get("public_web_search_is_authoritative") is False
required["github_access_validation.public_web_search_failure_never_implies_permission_denied"] = ga.get("public_web_search_failure_never_implies_permission_denied") is True
required["github_access_validation.required_preflight_order"] = (ga.get("required_preflight_order") or [])[:2] == ["AUTHENTICATED_GITHUB_REPOSITORY_METADATA", "REFRESH_KOREAN_LOCALIZATION_CLEAN_HEAD"]
forbid_permission_inference = set(ga.get("forbid_permission_inference_from") or [])
required["github_access_validation.forbid_public_search_permission_inference"] = {"PUBLIC_WEB_SEARCH_MISS","PUBLIC_SEARCH_ONLY_UPSTREAM_RESULT"}.issubset(forbid_permission_inference)
required["github_access_validation.generated_prompt_directive"] = ("authenticated GitHub connector/API" in str(ga.get("generated_prompt_directive") or "") and "공개 웹 검색" in str(ga.get("generated_prompt_directive") or ""))
required["github_access_validation.authoritative_write_capabilities"] = {"push","maintain","admin"}.issubset(set(ga.get("authoritative_write_capabilities") or []))
permission_rule = str(ga.get("permission_denied_only_when") or "")
required["github_access_validation.permission_denied_requires_fresh_evidence"] = ("fresh repository permission metadata" in permission_rule and "401/403" in permission_rule)
non_permission = set(ga.get("do_not_classify_as_permission_denied") or [])
required["github_access_validation.non_permission_failures"] = {"404_PATH_OR_REF_NOT_FOUND","UNSUPPORTED_CONNECTOR_OR_API_OPERATION","STALE_BLOB_SHA_CONFLICT","BRANCH_HEAD_RACE","VALIDATION_FAILURE","RATE_LIMIT","LOCAL_OR_N100_WORKSPACE_UNAVAILABLE"}.issubset(non_permission)

runtime_fields = {"queue_loop_heartbeat_at","last_scheduler_decision_at","last_scheduler_decision","blocked_reason"}
required["runtime_observability.required_runtime_fields"] = runtime_fields.issubset(set(obs.get("required_runtime_fields") or []))

execution = cfg.get("execution") or {}
qa = cfg.get("qa_deduplication") or {}
required["execution.mode"] = execution.get("mode") == "continuous_three_producers_with_c_batch_gate"
required["execution.qa_consumer"] = execution.get("qa_consumer") == "C"
required["execution.producer_next_after"] = execution.get("producer_next_after") == "OWN_LANE_DURABLE_COMMIT"
required["execution.producer_individual_actions_gate"] = execution.get("producer_individual_actions_gate") is False
required["execution.batch_gate_role"] = execution.get("batch_gate_role") == "C"
required["execution.batch_gate_is_only_runner_validation"] = execution.get("batch_gate_is_only_runner_validation") is True
required["execution.c_gates_production"] = execution.get("c_gates_production") is False
required["execution.qa_batch_size"] = int(execution.get("qa_batch_size", 0)) == 4
required["execution.qa_coalesce_seconds"] = int(execution.get("qa_coalesce_seconds", 9999)) <= 60
required["execution.max_parallel_production"] = int(execution.get("max_parallel_production", 0)) == 3
required["execution.concurrent_group"] = execution.get("concurrent_group") == ["A", "B", "E"]
required["execution.e_backlog_throttle"] = (execution.get("extra_producer_backlog_throttle") or {}).get("lane") == "E"
qprio = execution.get("qa_priority_policy") or {}
required["execution.candidate_bearing_qa_first"] = qprio.get("primary") == "CANDIDATE_BEARING_RESULTS_FIRST" and qprio.get("preflight_must_not_delay_candidate_batch") is True
required["qa_deduplication.identity"] = qa.get("identity") == "TASK_ID@RESULT_SHA"
required["qa_deduplication.reuse_unchanged_pass_evidence"] = qa.get("reuse_unchanged_pass_evidence") is True
required["qa_deduplication.shared_state_merge_frequency"] = qa.get("shared_state_merge_frequency") == "once_per_c_batch"

strategy = cfg.get("production_strategy") or {}
required["production_strategy.mode"] = strategy.get("mode") == "candidate_completion_first"
required["production_strategy.forbid_new_preflight_while_ready_exists"] = strategy.get("forbid_new_preflight_while_ready_exists") is True
required["production_strategy.max_new_preflight_only_batches_when_no_ready_assets"] = int(strategy.get("max_new_preflight_only_batches_when_no_ready_assets", 99)) <= 1
required["production_strategy.candidate_target_per_invocation_when_ready_exists"] = int(strategy.get("candidate_target_per_invocation_when_ready_exists", 0)) >= 2
batch_policy = strategy.get("candidate_batch_policy") or {}
required["production_strategy.candidate_batch_default"] = int(batch_policy.get("default_target", 0)) >= 2
required["production_strategy.candidate_batch_max"] = int(batch_policy.get("max_target", 0)) == 4
required["production_strategy.family_fast_path_target"] = int(batch_policy.get("family_fast_path_target", 0)) == 4
preflight = strategy.get("preflight_suppression") or {}
required["production_strategy.preflight_forbidden_with_completion_work"] = preflight.get("forbid_when_any_runnable_completion_tier_exists") is True
required["production_strategy.preflight_not_throughput"] = preflight.get("preflight_result_never_counts_as_candidate_throughput") is True
exception = strategy.get("exception_queue") or {}
required["production_strategy.exception_after_three"] = int(exception.get("max_repair_attempts_same_dependency_fingerprint", 0)) == 3 and exception.get("route_after_limit") == "EXCEPTION_QUEUE"
required["production_strategy.exception_nonblocking"] = exception.get("blocks_independent_assets") is False
completion = strategy.get("completion_semantics") or {}
required["production_strategy.production_complete_static_c"] = completion.get("production_complete") == "C_STATIC_QA_PASS_ON_CURRENT_V2_CANDIDATE"
required["production_strategy.runtime_separate"] = completion.get("production_complete_requires_runtime") is False and completion.get("runtime_state_separate") is True
cprio = strategy.get("candidate_qa_priority") or {}
required["production_strategy.c_candidate_first"] = cprio.get("candidate_bearing_first") is True and cprio.get("preflight_only_secondary") is True
required["production_strategy.continue_to_next_ready_asset_after_fail_closed"] = strategy.get("continue_to_next_ready_asset_after_fail_closed") is True
required["production_strategy.qa_strictness_unchanged"] = strategy.get("qa_strictness_unchanged") is True
required["production_strategy.readiness_tiers"] = strategy.get("readiness_tiers") == ["RENDER_READY", "ONE_STAGE_TO_RENDER", "PREFLIGHT_ONLY"]

fresh = cfg.get("dispatch_freshness") or {}
required["dispatch_freshness.refresh_all_entrypoints"] = {"INITIAL_DISPATCH","RETRY","CONVERSATION_ROLLOVER"}.issubset(set(fresh.get("refresh_config_before") or []))
required["dispatch_freshness.required_prompt_tokens"] = {"CONTROLLER_SCHEMA_VERSION","CONTROLLER_CONFIG_BLOB_SHA"}.issubset(set(fresh.get("required_prompt_tokens") or []))
required["dispatch_freshness.reject_cached_prompt"] = fresh.get("reject_cached_prompt_after_config_blob_change") is True
required["dispatch_freshness.current_shard_rule"] = fresh.get("required_current_shard_rule") == "asset_queue.index % 3: A=0, B=1, E=2"
required["startup_reconcile.reload_controller_config"] = sr.get("reload_controller_config") is True
required["startup_reconcile.reject_stale_schema_prompt"] = sr.get("reject_stale_schema_prompt") is True
single = (cfg.get("actions_batching") or {}).get("single_dds_packaging") or {}
required["single_dds_packaging.optional_only"] = single.get("purpose") == "OPTIONAL_RUNTIME_TEST_ARTIFACT_ONLY"
required["single_dds_packaging.no_producer_gate"] = single.get("gates_producer_progress") is False
required["single_dds_packaging.no_c_gate"] = single.get("gates_c_batch_progress") is False
required["single_dds_packaging.external_candidate_skip"] = single.get("external_candidate_mode") == "SKIP_WITH_TYPED_NOTICE_EXTERNAL_CANDIDATE_NOT_IN_GIT"
required["execution.c_rework_owner_includes_e"] = (cfg.get("lanes") or {}).get("C", {}).get("candidate_write_policy") == "RETURN_REWORK_TO_OWNING_A_B_OR_E"
forbidden_fragments = set((cfg.get("dispatch_freshness") or {}).get("forbidden_prompt_fragments") or [])
required["dispatch_freshness.forbids_stale_two_producer_phrases"] = {"A: odd-index","B: even-index","A+B production wave","odd/even queue shards"}.issubset(forbidden_fragments)

commands_text = (root / "docs" / "KOREAN_LOCALIZATION_CONTROLLER_COMMANDS.md").read_text(encoding="utf-8")
for stale in ["A: odd-index", "B: even-index", "A+B production wave", "odd/even queue shards"]:
    required["controller_commands.no_stale_" + stale.replace(" ", "_")] = stale not in commands_text
required["controller_commands.has_e_command"] = "OutRun 한글화 E 실행" in commands_text
required["controller_commands.modulo3"] = "index % 3 == 0" in commands_text and "index % 3 == 1" in commands_text and "index % 3 == 2" in commands_text

workflow_text = (root / ".github" / "workflows" / "localization-automation-gate.yml").read_text(encoding="utf-8")
required["automation_gate.skips_a"] = "[AUTO:LOCALIZATION-LOCALIZATION_A-" in workflow_text
required["automation_gate.skips_b"] = "[AUTO:LOCALIZATION-LOCALIZATION_B-" in workflow_text
required["automation_gate.skips_e"] = "[AUTO:LOCALIZATION-LOCALIZATION_E-" in workflow_text
bad = [name for name, ok in required.items() if not ok]
if bad:
    raise SystemExit("controller recovery policy invalid: " + ", ".join(bad))

print("controller recovery policy PASS")
print("bound Actions poll <=30s, WAIT_ACTIONS recovery <=90s, idle rearm <=90s")
print("A/B/E release on durable commit; only C batch consumes runner-backed Actions validation")
print("candidate-completion-first production; no new preflight while render-ready work exists")
print("pressure-tuned three-producer dispatch; E backlog throttle enabled; heartbeat <=15s")
