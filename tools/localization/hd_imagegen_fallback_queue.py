#!/usr/bin/env python3
"""Stage reproducible HD A/B ImageGen work orders in an isolated GitHub branch.

No image creation is claimed here. Existing A/B candidate bytes + source DDS
SHA + original readable ROI crop are the mandatory evidence. The existing
reuse-only QA queue and release controls stay untouched.
"""
import argparse
import json
import os
from pathlib import Path

import hd_rework_queue as queue
import publish_hd_rework_queue as publish

FALLBACK_PREFIX = "localization/automation_runs/hd_imagegen_fallback"
MAX_ACTIVE = 8


def stage(repo_root, queue_root, output, *, token=None, publish_remote=False):
    root = Path(repo_root).resolve()
    qroot = Path(queue_root).resolve()
    out = Path(output).resolve()
    report_path = qroot / "localization/automation_runs/hd_rework_queue/last_report.json"
    last = qroot / FALLBACK_PREFIX / "latest.json"
    state = qroot / FALLBACK_PREFIX / "state"

    if not report_path.is_file():
        raise ValueError("SOURCE_QA_REPORT_NOT_AVAILABLE")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (report.get("schema") != "outrun.ab-imagegen-hd-strict.v2"
            or report.get("release_approved") is not False
            or report.get("runtime_validation") != "UNTESTED"
            or report.get("active_roi_total") != 954
            or report.get("imported_roi_total") != 954):
        raise ValueError("NOT_VERIFIED_STRICT_REUSE_ONLY_QA_SOURCE")
    for k in ("source_dds_missing_rows", "source_sha_conflict_rows"):
        if report.get(k) != 0:
            raise ValueError("SOURCE_PROVENANCE_NOT_EXACT")

    superseded = []
    previous_source = None
    if last.is_file():
        previous = json.loads(last.read_text(encoding="utf-8"))
        previous_source = previous.get("source_asset_sha256")
        if (previous.get("schema") != "outrun-hd-qa-chat-workqueue-v1"
                or previous.get("release_approved") is not False
                or not isinstance(previous.get("tasks"), list)
                or not isinstance(previous_source, str)
                or len(previous_source) != 64):
            raise ValueError("PRIOR_QUEUE_INVALID")
        # Never overwrite a still-relevant task merely because the native DDS
        # report changed. But an old ImageGen ticket can be definitively
        # superseded when the same ROI is now a geometry/segmentation HOLD:
        # regenerating its letters cannot fix its current blocker.
        still_open = [t for t in previous["tasks"]
                      if not (state / (t["task_id"] + ".json")).is_file()]
        if still_open and previous_source == report["zip_sha256"]:
            print(json.dumps({"status": "WAIT_UNCLAIMED_IMAGEGEN_TASKS",
                              "open_task_count": len(still_open),
                              "source_sha": previous_source}))
            return {"status": "WAIT_UNCLAIMED_IMAGEGEN_TASKS",
                    "open_task_count": len(still_open), "tasks": previous["tasks"]}
        if still_open:
            held, _ = queue.flatten_holds(report)
            still_relevant = [
                t for t in still_open
                if held.get(t.get("roi_id")) is not None
                and queue.category(held[t["roi_id"]]) == "AB_IMAGE_AND_CLEAN_REWORK"
            ]
            if still_relevant:
                # Preserve all prior open tickets as a group; mixing sources
                # or replacing live browser work would lose SHA provenance.
                print(json.dumps({"status": "WAIT_STALE_SOURCE_WITH_RELEVANT_TASKS",
                                  "source_sha": previous_source,
                                  "current_source_sha": report["zip_sha256"],
                                  "still_relevant_tasks": len(still_relevant),
                                  "open_task_count": len(still_open)}))
                return {"status": "WAIT_STALE_SOURCE_WITH_RELEVANT_TASKS",
                        "still_relevant_tasks": len(still_relevant),
                        "open_task_count": len(still_open),
                        "tasks": previous["tasks"]}
            superseded = [{
                "task_id": t["task_id"], "roi_id": t["roi_id"],
                "new_hold_reason": held.get(t["roi_id"], "ROI_NO_LONGER_HELD")
            } for t in still_open]

    work = queue.build_queue(root, report, out, state, reuse_only=False)
    if superseded:
        # Immutable historical source references and prior GitHub queue
        # commits are retained. Only the *active* queue is refreshed.
        work["superseded_unclaimed_previous_tasks"] = superseded
        work["superseded_previous_source_sha256"] = previous_source
        work["supersession_policy"] = (
            "SOURCE_SHA_CHANGED_AND_ALL_OLD_OPEN_TASKS_NO_LONGER_IMAGEGEN_ELIGIBLE"
        )
        # build_queue writes queue.json before its return. Persist the exact
        # amended work order or the publisher would silently drop the
        # supersession receipts from the active GitHub queue.
        out.mkdir(parents=True, exist_ok=True)
        (out / "queue.json").write_text(
            json.dumps(work, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8"
        )
    if (work.get("new_imagegen_disabled") is not False
            or work.get("release_approved") is not False
            or work.get("runtime_validation") != "UNTESTED"
            or work.get("source_asset_sha256") != report.get("zip_sha256")
            or len(work["tasks"]) > MAX_ACTIVE):
        raise ValueError("FAIL_CLOSED_WORKQUEUE_CONTRACT")
    # Every source image and task SHA must match the exact native HD original.
    for task in work["tasks"]:
        p = out / task["reference"]["name"]
        if (not p.is_file()
                or queue.atlas.sha(p.read_bytes()) != task["reference"]["sha256"]
                or task["qa_authority"] != "NOT_C1_APPROVED_NOT_GAME_APPROVED"):
            raise ValueError("UNVERIFIED_HD_SOURCE_REFERENCE")

    if publish_remote:
        if not token:
            raise ValueError("GITHUB_TOKEN_NOT_AVAILABLE")
        prior = publish.PREFIX
        try:
            publish.PREFIX = FALLBACK_PREFIX
            publish.publish(out, token)
        finally:
            publish.PREFIX = prior
    print(json.dumps({
        "status": "STAGED_NOT_GENERATED",
        "active_tasks": len(work["tasks"]),
        "hold_count": work["hold_count"],
        "source_sha": work["source_asset_sha256"],
        "release_approved": False,
        "runtime_validation": "UNTESTED",
    }, ensure_ascii=False))
    return work


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=".")
    p.add_argument("--queue-root", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--publish", action="store_true")
    args = p.parse_args()
    stage(args.repo_root, args.queue_root, args.out,
          token=os.environ.get("GH_TOKEN"), publish_remote=args.publish)
