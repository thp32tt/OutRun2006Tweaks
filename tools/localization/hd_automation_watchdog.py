#!/usr/bin/env python3
"""OutRun HD Korean self-healing GitHub Actions dispatcher (no DDS processing).

Runs on GitHub-hosted Python. Schedules exactly one strict rebuild per changed
asset branch SHA; never loops on unchanged failed or completed inputs. A failed
run is retried at most once. Completion still requires independent visual and
actual game QA; TEST_ONLY is never promoted.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = "thp32tt/OutRun2006Tweaks"
ASSET_BRANCH = "korean-localization-recovery-20260928"
QA_BRANCH = "korean-localization-qa-queue-20261104"
WORKFLOW = "outrun-ab-multi-atlas.yml"
ACTIVE = {"queued", "in_progress", "requested", "waiting", "pending"}


def decision(head_sha, runs, artifact_present, qa=None):
    """Return an auditable action, not an unbounded background worker."""
    if qa and qa.get("release_approved") is True and qa.get("runtime_validation") == "PASS":
        return {"action": "COMPLETE_NO_DISPATCH", "reason": "Game and visual QA still require independent evidence"}
    active = [r for r in runs if r.get("status") in ACTIVE]
    if active:
        chosen = active[0]
        return {"action": "WAIT_ACTIVE", "run_id": chosen["id"],
                "running_sha": chosen.get("head_sha"), "reason": "Avoid canceling a potentially expensive in-flight DDS build"}
    same = [r for r in runs if r.get("head_sha") == head_sha]
    if not same:
        return {"action": "DISPATCH", "reason": "No DDS workflow run for newest exact asset SHA"}
    latest = same[0]
    if latest.get("conclusion") == "success":
        if artifact_present(latest["id"]):
            return {"action": "WAIT_FOR_NEW_SOURCE", "run_id": latest["id"],
                    "reason": "Verified current-SHA DDS output; unchanged inputs must not burn another long build"}
        return {"action": "BLOCKED_MISSING_ARTIFACT", "run_id": latest["id"],
                "reason": "Successful workflow lacks exact DDS artifact; manual evidence required"}
    if latest.get("conclusion") in ("failure", "timed_out", "action_required"):
        if int(latest.get("run_attempt") or 1) == 1:
            return {"action": "RETRY_FAILED_ONCE", "run_id": latest["id"],
                    "reason": "First failure only; retry once and preserve failure evidence"}
        return {"action": "BLOCKED_REPEATED_FAILURE", "run_id": latest["id"],
                "reason": "Retry cap reached: require actual code/config fix before further build"}
    if latest.get("conclusion") == "cancelled":
        return {"action": "BLOCKED_CANCELLED_SAME_SHA", "run_id": latest["id"],
                "reason": "Avoid dispatch loops after unexpected cancellation; await source change"}
    return {"action": "BLOCKED_UNKNOWN_STATE", "run_id": latest["id"],
            "reason": "Fail closed on unexpected GitHub conclusion"}


class API:
    def __init__(self, token):
        if not token:
            raise ValueError("GH_TOKEN_REQUIRED_FOR_DISPATCH")
        self.token = token
        self.base = f"https://api.github.com/repos/{REPO}"

    def call(self, path, method="GET", payload=None):
        if not path.startswith("/") or ".." in path:
            raise ValueError("BAD_API_PATH")
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self.base + path, method=method, data=data,
            headers={"Authorization": f"Bearer {self.token}",
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "Content-Type": "application/json",
                     "User-Agent": "OutRun-HD-Korean-GitHub-Controller"})
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response) if response.status != 204 else {}


def fetch_qa(api):
    try:
        data = api.call("/contents/localization/automation_runs/hd_rework_queue/last_report.json"
                        f"?ref={urllib.parse.quote(QA_BRANCH)}")
        import base64
        text = base64.b64decode(data["content"]).decode("utf-8")
        report = json.loads(text)
        if report.get("active_roi_total") != 954:
            raise ValueError("QA_WRONG_SOURCE_COUNT")
        return report
    except (KeyError, ValueError, urllib.error.HTTPError) as exc:
        # Never infer completion from unavailable or stale QA branch evidence.
        print(f"QA_CURRENT_UNVERIFIED: {type(exc).__name__}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Permission to dispatch/retry a run, not permission to install or release")
    args = parser.parse_args()
    repo = os.getenv("GITHUB_REPOSITORY")
    if args.apply and repo != REPO:
        raise SystemExit("CONTROLLER_WRONG_REPOSITORY")
    api = API(os.getenv("GH_TOKEN"))
    head = api.call(f"/git/ref/heads/{ASSET_BRANCH}")["object"]["sha"]
    args_runs = urllib.parse.urlencode({"branch": ASSET_BRANCH, "per_page": 100})
    runs = api.call(f"/actions/workflows/{WORKFLOW}/runs?{args_runs}")["workflow_runs"]
    qa = fetch_qa(api)
    def artifact_present(run_id):
        result = api.call(f"/actions/runs/{run_id}/artifacts?per_page=100")
        return any(a.get("name") == f"outrun-ab-multi-atlas-{run_id}"
                   and not a.get("expired", False)
                   and int(a.get("size_in_bytes", 0)) > 0
                   for a in result.get("artifacts", []))
    result = decision(head, runs, artifact_present, qa)
    result["asset_sha"] = head
    result["checked_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    if qa:
        result["last_published_qa"] = {
            "source_zip_sha256": qa.get("zip_sha256"),
            "active_roi": qa.get("active_roi_total"),
            "test_only_painted": qa.get("translated_roi_generated"),
            "held_roi": sum(qa.get("hold_roi_reason_counts", {}).values()),
            "release_approved": qa.get("release_approved"),
            "runtime_validation": qa.get("runtime_validation"),
        }
        result["qa_may_be_stale"] = True
    else:
        result["qa_status"] = "UNVERIFIED"
    if args.apply and result["action"] == "DISPATCH":
        api.call(f"/actions/workflows/{WORKFLOW}/dispatches", method="POST",
                 payload={"ref": ASSET_BRANCH})
        result["side_effect"] = "DISPATCH_ACCEPTED_BY_GITHUB"
    elif args.apply and result["action"] == "RETRY_FAILED_ONCE":
        api.call(f"/actions/runs/{result['run_id']}/rerun-failed-jobs", method="POST")
        result["side_effect"] = "RERUN_REQUEST_ACCEPTED_BY_GITHUB"
    else:
        result["side_effect"] = "NONE"
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("## OutRun HD Korean automatic controller\n\n")
            out.write(f"- Action: **{result['action']}**\n")
            out.write(f"- Asset SHA: \`{head}\`\n")
            out.write(f"- Reason: {result['reason']}\n")
            if qa:
                out.write(f"- Last published report (may lag): {result['last_published_qa']['test_only_painted']}/954 TEST_ONLY, {result['last_published_qa']['held_roi']} HOLD\n")
            out.write("- **No game deployment, no ImageGen, no font fallback, no auto-release.**\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
