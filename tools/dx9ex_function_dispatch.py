#!/usr/bin/env python3
"""DX9Ex full-function dispatch RECOMMENDATION, not an owner-claim or scheduler.

Controller must supply *authenticated* current claims and atomically obtain an
epoch/fencing lease before spawning any modifier. This tool does not write state,
mint TASK_IDs, run CI or touch Docker. Never infer ownership from a chat timer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "docs/VR_WORK_QUEUE.json"
POLICY = ROOT / "docs/automation/DX9EX_FEATURE_UNIT_POLICY.json"
RECORDS = ROOT / "docs/automation/runs"
FINISHED = ("COMPLETE", "DONE", "PASS")
HMD_FAIL = {"FAIL", "USER_REPORTED_FAIL", "REGRESSED"}
RUNNING = {"RUNNING", "VALIDATING", "WAITING_CI", "IMPLEMENTING", "IMPLEMENTED",
           "PENDING_CONTROLLER_EXACT_SHA", "NEEDS_VALIDATION", "WAITING_FOR_CI"}


def choose(queue: dict, policy: dict, records: list[dict],
           claims: list[dict] | None = None) -> dict:
    catalog = {f["feature_id"]: f for f in policy["feature_catalog"]}
    candidates = sorted(
        (x for x in queue["items"] if x.get("featureId") in catalog
         and x.get("status") in {"READY", "NEEDS_VALIDATION", "IN_PROGRESS"}),
        key=lambda x: (-int(x.get("priority", 0)), x["id"]),
    )
    if not candidates:
        return {"action": "NO_ACTIONABLE_FEATURE"}
    if claims is None:
        return {"action": "HOLD_OWNER_UNCONFIRMED", "candidate": candidates[0]["featureId"],
                "reason": "authenticated claims and fencing epoch required; never mint new TASK_ID"}
    active = [x for x in claims if x.get("verified_live") is True]
    unknown = [x for x in claims if x.get("owner_uncertain") is True]
    if unknown:
        return {"action": "HOLD_OWNER_UNCERTAIN",
                "reason": "lease/worker reconciliation must complete before modifying source"}
    scoped = [r for r in records if r.get("feature_id") in catalog]
    # First continue one unfinished or hardware-rejected *same* functional feature,
    # regardless of a newer queue item with a higher numbered priority.
    for r in scoped:
        state = str(r.get("status") or "").upper()
        visual_failed = str(r.get("runtime_validation") or "").upper() in HMD_FAIL
        if not state.startswith(FINISHED) or visual_failed:
            owning = [c for c in active if c.get("feature_id") == r.get("feature_id")]
            if owning:
                return {"action": "ATTACH_EXISTING_OWNER", "feature_id": r["feature_id"],
                        "task_id": r.get("task_id"), "new_task_allowed": False}
            return {"action": "RECONCILE_THEN_RESUME" if not visual_failed else "REOPEN_SAME_SYMPTOM",
                    "feature_id": r["feature_id"], "symptom_id": r.get("symptom_id"),
                    "task_id": r.get("task_id"), "new_task_allowed": False,
                    "score_delta": 0, "requires_fenced_claim": True}
    # BUILD_VERIFIED with HMD untested is not optical PASS, but can move to the
    # next independent source feature; a subsequent HMD FAIL will reopen same key.
    completed = {r["feature_id"] for r in scoped if
                 str(r.get("status") or "").upper().startswith(FINISHED)
                 and str(r.get("runtime_validation") or "").upper() not in HMD_FAIL}
    for item in candidates:
        fid = item["featureId"]
        if fid in completed:
            continue
        keys = set(item.get("conflictKeys") or [])
        collisions = [c for c in active if set(c.get("conflict_keys") or []) & keys]
        if collisions:
            continue
        return {"action": "PROPOSE_NEW_FUNCTIONAL_FEATURE", "feature_id": fid,
                "symptom_id": item.get("symptomId"), "queue_item": item["id"],
                "next": "atomic GitHub HEAD and owner/lease reconciliation",
                "new_task_allowed": False, "requires_fenced_claim": True}
    return {"action": "HOLD_OVERLAPPING_OWNER_OR_ALL_BUILD_VERIFIED",
            "new_task_allowed": False}


def main() -> int:
    arg = argparse.ArgumentParser()
    arg.add_argument("--recommend", action="store_true")
    arg.add_argument("--claims-json", type=Path)
    args = arg.parse_args()
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    if args.claims_json:
        claims = json.loads(args.claims_json.read_text(encoding="utf-8"))
    else:
        claims = None  # no implicit source ownership from absent external data
    records = []
    for path in RECORDS.glob("CONVERSION-DX9EX-*.json"):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict):
            records.append(rec)
    if args.recommend:
        print(json.dumps(choose(queue, policy, records, claims), ensure_ascii=False))
    else:
        print("DX9Ex whole-function dispatch planner available (read-only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
