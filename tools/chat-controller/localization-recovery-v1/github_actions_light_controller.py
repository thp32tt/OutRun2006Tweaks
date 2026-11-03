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
WORKFLOW = "outrun-ab-imagegen-native.yml"
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
    path = "/actions/workflows/" + WORKFLOW + "/runs?per_page=5"
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
    poll = int(os.environ.get("OUTRUN_GITOPS_POLL_SECONDS", "3600"))
    if not 1800 <= poll <= 86400:
        p.error("poll must be 1800..86400 seconds")
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
