#!/usr/bin/env python3
"""Low-impact existing Portainer controller for GitHub-hosted Korean QA.

All image processing, DDS encoding/QA, and ZIP packaging happen on GitHub Actions
ubuntu runner (normal Python; NOT Docker). This process only polls GitHub REST
and optionally dispatches workflow on changed asset SHA using Actions:write PAT.
No image downloads, no subprocess worker, no GPU, no browser or costly job.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "thp32tt/OutRun2006Tweaks"
BRANCH = "korean-localization-recovery-20260928"
WORKFLOW = "outrun-ab-multi-atlas.yml"
API = "https://api.github.com/repos/" + REPO
EXPECTED_SHA = re.compile(r"^[0-9a-f]{40}$")
MAX_REMOTE_BYTES = 512 * 1024


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def api_call(path: str, token: str = "", method: str = "GET",
             json_body: dict | None = None) -> dict | None:
    if not path.startswith("/") or "://" in path or "\\" in path:
        raise ValueError("INVALID_API_PATH")
    url = API + path
    body = json.dumps(json_body, separators=(",", ":")).encode() if json_body is not None else None
    req = urllib.request.Request(
        url, method=method, data=body,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "outrun-portainer-github-light-controller",
            **({"Authorization": "Bearer " + token} if token else {}),
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        data = response.read(MAX_REMOTE_BYTES + 1)
    if len(data) > MAX_REMOTE_BYTES:
        raise ValueError("GITHUB_API_RESPONSE_TOO_BIG")
    return json.loads(data) if data.strip() else None


def latest_asset_sha(token: str) -> str:
    obj = api_call("/branches/" + urllib.parse.quote(BRANCH, safe=""), token)
    sha = obj["commit"]["sha"]
    if not EXPECTED_SHA.fullmatch(sha):
        raise ValueError("INVALID_HEAD_SHA")
    return sha


def latest_qa_run(token: str) -> dict:
    path = "/actions/workflows/" + WORKFLOW + "/runs?branch=" + urllib.parse.quote(BRANCH, safe="") + "&per_page=20"
    obj = api_call(path, token)
    runs = obj.get("workflow_runs", [])
    if not isinstance(runs, list):
        raise ValueError("INVALID_WORKFLOW_RUN_RESPONSE")
    if not runs:
        return {"run_id": None, "status": "NO_RUN_YET", "conclusion": None, "url": None}
    run = runs[0]
    return {
        "run_id": run.get("id"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "url": run.get("html_url"),
        "head_sha": run.get("head_sha"),
    }


def dispatch_qa(token: str) -> None:
    if not token:
        raise ValueError("TOKEN_REQUIRED_TO_DISPATCH")
    path = "/actions/workflows/" + WORKFLOW + "/dispatches"
    api_call(path, token, method="POST", json_body={"ref": BRANCH})



REPAIR_WORKFLOW="outrun-hd-cleanplate-repair.yml"
REPAIR_QUEUE_BRANCH="korean-localization-qa-queue-20261104"
REPAIR_QUEUE_ROOT="localization/automation_runs/hd_cleanplate_repair"

def repair_pointer(token):
    import base64
    try:
        data=api_call("/contents/"+REPAIR_QUEUE_ROOT+"/latest.json?ref="+REPAIR_QUEUE_BRANCH,token)
    except urllib.error.HTTPError as exc:
        if exc.code==404:return None
        raise
    if not isinstance(data,dict) or data.get("encoding")!="base64":
        raise ValueError("REPAIR_POINTER_RESPONSE")
    ptr=json.loads(base64.b64decode(data["content"]))
    if ptr.get("schema")!="outrun.hd.cleanplate-queue-pointer.v1":
        raise ValueError("REPAIR_POINTER_SCHEMA")
    return ptr

def repair_cycle(sha,token,prior):
    obj=api_call("/actions/workflows/"+REPAIR_WORKFLOW+"/runs?per_page=5",token)
    runs=obj.get("workflow_runs",[])
    if not isinstance(runs,list):raise ValueError("REPAIR_RUNS_INVALID")
    ptr=repair_pointer(token)
    last=runs[0] if runs else {}
    active=any(r.get("status") in ("queued","in_progress","pending","waiting","requested") for r in runs)
    receipt=prior.get("last_repair_dispatched_sha")
    status="GITHUB_SCHEDULE_FALLBACK"
    if active:
        status="REPAIR_RUNNING_OR_QUEUED"
    elif ptr and ptr.get("asset_sha")==sha:
        status="REPAIR_QUEUE_PUBLISHED_GPT_FEEDBACK_ON_SCHEDULE"
    elif token and receipt!=sha and not any(r.get("display_title")=="HD cleanplate "+sha for r in runs):
        api_call("/actions/workflows/"+REPAIR_WORKFLOW+"/dispatches",token,method="POST",
                 json_body={"ref":"master","inputs":{"asset_sha":sha}})
        receipt=sha;status="REPAIR_DISPATCHED"
    elif token:
        status="REPAIR_DEDUP_OR_SCHEDULE_RETRY"
    return {"status":status,"last_repair_dispatched_sha":receipt,
            "run_id":last.get("id"),"run_status":last.get("status"),"run_conclusion":last.get("conclusion"),
            "published_run_id":ptr.get("run_id") if ptr else None,
            "published_asset_sha":ptr.get("asset_sha") if ptr else None,
            "published_counts":ptr.get("counts") if ptr else None,
            "runtime_validation":"UNTESTED","release_approved":False}


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".gh-monitor-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def check_cycle(home: Path, token: str) -> dict:
    """No N100 image access; see both asset-push and default-branch scheduled runs."""
    home.mkdir(parents=True, exist_ok=True)
    previous_file = home / "last_status.json"
    prior = json.loads(previous_file.read_text(encoding="utf-8")) if previous_file.exists() else {}
    sha = latest_asset_sha(token)
    qa = latest_qa_run(token)

    # GitHub push and schedule can start the workflow without a Docker token.
    # Only dispatch if there is a PAT AND a new SHA has no run for this same SHA.
    dispatch = "GITHUB_SCHEDULE_AND_PUSH"
    if token:
        if prior.get("last_dispatched_sha") == sha:
            dispatch = "DEDUP_SHA_ALREADY_DISPATCHED"
        elif qa.get("head_sha") == sha and qa.get("status") in ("queued", "in_progress", "completed"):
            dispatch = "ALREADY_RUN_FOR_SHA"
        else:
            dispatch_qa(token)
            dispatch = "WORKFLOW_DISPATCHED"

    data = {
        "schema": "outrun-portainer-light-github-controller-v1",
        "checked_utc": now(),
        "asset_sha": sha,
        "github_workflow": WORKFLOW,
        "execution_location": "GITHUB_ACTIONS_UBUNTU_HOSTED_RUNNER",
        "github_uses_docker": False,
        "local_dds_processing": False,
        "local_image_processing": False,
        "dispatch": dispatch,
        "last_dispatched_sha": sha if dispatch in ("WORKFLOW_DISPATCHED", "DEDUP_SHA_ALREADY_DISPATCHED") else
            prior.get("last_dispatched_sha"),
        "latest_run": qa,
        "runtime_validation": "UNTESTED",
        "release_approved": False,
    }
    if os.environ.get("OUTRUN_CLEANPLATE_REPAIR_ENABLED","0")=="1":
        try:
            info=repair_cycle(sha,token,prior)
            data["cleanplate_repair"]=info
            data["last_repair_dispatched_sha"]=info["last_repair_dispatched_sha"]
        except Exception as exc:
            data["cleanplate_repair"]={"status":"REPAIR_MONITOR_HOLD","error_type":type(exc).__name__}
            data["last_repair_dispatched_sha"]=prior.get("last_repair_dispatched_sha")
    atomic_json(previous_file, data)
    return data


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--home", default=None)
    args = p.parse_args()
    if args.self_test:
        assert EXPECTED_SHA.fullmatch("a"*40)
        assert not EXPECTED_SHA.fullmatch("a"*39)
        assert WORKFLOW.endswith(".yml")
        print("LIGHT_CONTROLLER_SELFTEST_PASS")
        return
    home = Path(args.home or os.environ.get("OUTRUN_GITOPS_HOME", "/data/gitops"))
    if not home.is_absolute():
        p.error("home must be an absolute path")
    token = os.environ.get("OUTRUN_GITHUB_ACTIONS_TOKEN", "").strip()
    poll = int(os.environ.get("OUTRUN_GITOPS_POLL_SECONDS", "900"))
    if not 600 <= poll <= 86400:
        p.error("poll must be 600..86400 seconds")
    while True:
        try:
            result = check_cycle(home, token)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        except Exception as exc:
            # Never print tokens, URLs with query secrets, or raw HTTP exception bodies.
            error = {"checked_utc": now(), "status": "HOLD_RETRY",
                     "error_type": type(exc).__name__}
            atomic_json(home / "last_error.json", error)
            print(json.dumps(error, sort_keys=True), flush=True)
            if args.once:
                raise SystemExit(2)
        if args.once:
            break
        time.sleep(poll)


if __name__ == "__main__":
    main()
