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

    if last.is_file():
        previous = json.loads(last.read_text(encoding="utf-8"))
        if (previous.get("schema") != "outrun-hd-qa-chat-workqueue-v1"
                or previous.get("release_approved") is not False
                or not isinstance(previous.get("tasks"), list)):
            raise ValueError("PRIOR_QUEUE_INVALID")
        # Avoid replacing an unfinished task list with a new one.
        still_open = [t["task_id"] for t in previous["tasks"]
                      if not (state / (t["task_id"] + ".json")).is_file()]
        if still_open:
            print(json.dumps({"status": "WAIT_UNCLAIMED_IMAGEGEN_TASKS",
                              "open_task_count": len(still_open),
                              "source_sha": previous["source_asset_sha256"]}))
            return {"status": "WAIT_UNCLAIMED_IMAGEGEN_TASKS",
                    "open_task_count": len(still_open), "tasks": previous["tasks"]}

    work = queue.build_queue(root, report, out, state, reuse_only=False)
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
