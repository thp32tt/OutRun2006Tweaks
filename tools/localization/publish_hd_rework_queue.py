#!/usr/bin/env python3
"""Push only small SHA-addressed source proofs + JSON workqueue to a queue branch.

GitHub Actions has contents:write for its own repository. No N100 DDS/CPU work.
The queue branch is NOT the production asset branch, preventing a run loop.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "thp32tt/OutRun2006Tweaks"
BRANCH = "korean-localization-qa-queue-20261104"
PREFIX = "localization/automation_runs/hd_rework_queue"
API = "https://api.github.com/repos/" + REPO
MAX_PNG = 4 * 1024 * 1024
TASK_ID = re.compile(r"^HDRW-[AB]-[0-9a-f]{20}$")


def api(path, token, payload=None):
    if not token or not path.startswith("/repos/") or "://" in path or ".." in path:
        raise ValueError("GITHUB_QUEUE_API_OR_TOKEN_INVALID")
    raw = json.dumps(payload, separators=(",",":")).encode() if payload is not None else None
    req = urllib.request.Request(
        "https://api.github.com"+path, data=raw,
        method="PUT" if raw is not None else "GET",
        headers={"Accept":"application/vnd.github+json",
                 "Content-Type":"application/json",
                 "User-Agent":"outrun-hd-qa-queue-publisher",
                 "X-GitHub-Api-Version":"2022-11-28",
                 "Authorization":"Bearer "+token})
    try:
        with urllib.request.urlopen(req,timeout=35) as res:
            body = res.read(7*1024*1024)
        return json.loads(body)
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and raw is None:
            return None
        # Only return a sanitized GitHub API error *classification*, never
        # response headers, token, auth URL or arbitrary remote text.
        try:
            msg=json.loads(exc.read(4096).decode("utf-8")).get("message","")
        except (ValueError,UnicodeDecodeError):
            msg=""
        if "Resource not accessible by integration" in msg:
            reason="ACTIONS_TOKEN_CONTENTS_WRITE_DENIED"
        elif "secondary rate limit" in msg.lower():
            reason="GITHUB_SECONDARY_RATE_LIMIT"
        elif "rate limit" in msg.lower():
            reason="GITHUB_PRIMARY_RATE_LIMIT"
        elif "branch protection" in msg.lower() or "rule" in msg.lower():
            reason="GITHUB_BRANCH_RULESET_REJECTED"
        elif "not permitted" in msg.lower() or "permission" in msg.lower():
            reason="GITHUB_PERMISSION_DENIED"
        else:
            reason="GITHUB_OTHER_API_DENIAL"
        raise RuntimeError("GITHUB_QUEUE_HTTP_"+str(exc.code)+"_"+reason) from None


def content_path(rel):
    if ".." in rel.split("/") or not re.fullmatch(r"[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)*",rel):
        raise ValueError("UNSAFE_QUEUE_PATH")
    return "/repos/"+REPO+"/contents/"+PREFIX+"/"+rel


def put_exact(rel, raw, token, allow_update=False):
    endpoint = content_path(rel)
    old = api(endpoint+"?ref="+BRANCH,token)
    encoded = base64.b64encode(raw).decode("ascii")
    if old:
        if not allow_update:
            if old.get("encoding") != "base64" or (
                base64.b64decode(old.get("content","")) != raw):
                raise ValueError("IMMUTABLE_QUEUE_REF_CONTENT_CONFLICT")
            return "EXACT_ALREADY_PRESENT"
        old_sha = old.get("sha")
        if not isinstance(old_sha,str) or not re.fullmatch(r"[0-9a-f]{40}",old_sha):
            raise ValueError("INVALID_OLD_QUEUE_SHA")
    else:
        old_sha = None
    payload={"message":"localization(qa): publish HD source/queue "+rel,
             "content":encoded,"branch":BRANCH}
    if old_sha:
        payload["sha"]=old_sha
    res=api(endpoint,token,payload)
    if not re.fullmatch(r"[0-9a-f]{40}",res.get("commit",{}).get("sha","")):
        raise RuntimeError("QUEUE_COMMIT_MISSING")
    # Hash+content readback; no self-reported success.
    updated=api(endpoint+"?ref="+BRANCH,token)
    if updated is None or updated.get("encoding")!="base64" or (
        base64.b64decode(updated.get("content","")) != raw):
        raise RuntimeError("QUEUE_REMOTE_READBACK_MISMATCH")
    return "VERIFIED_COMMIT"


def publish(directory,token,report_path=None):
    directory=Path(directory)
    q=json.loads((directory/"queue.json").read_text(encoding="utf-8"))
    if q.get("schema") != "outrun-hd-qa-chat-workqueue-v1" or q.get("release_approved") is not False:
        raise ValueError("NOT_A_FAIL_CLOSED_HD_QA_QUEUE")
    if len(q.get("tasks",[]))>8 or any(not TASK_ID.fullmatch(t.get("task_id","")) for t in q["tasks"]):
        raise ValueError("INVALID_HUMAN_CHAT_BATCH")
    if report_path:
        report=Path(report_path).read_bytes()
        if len(report)>MAX_PNG:
            raise ValueError("QA_SOURCE_REPORT_TOO_LARGE_FOR_GITHUB_CONTENTS")
        parsed=json.loads(report)
        if parsed.get("schema")!="outrun.ab-imagegen-hd-strict.v2":
            raise ValueError("NON_STRICT_SOURCE_QA_REPORT")
        if parsed.get("release_approved") is not False:
            raise ValueError("INVALID_RELEASE_APPROVAL")
        put_exact("last_report.json",report,token,allow_update=True)
    published=[]
    for task in q["tasks"]:
        ref=task["reference"]
        path=directory/ref["name"]
        if path.name!=task["task_id"]+"_HD_SOURCE.png" or not path.is_file() or path.is_symlink():
            raise ValueError("SOURCE_REF_FILENAME_UNVERIFIED")
        raw=path.read_bytes()
        if len(raw)>MAX_PNG or hashlib.sha256(raw).hexdigest()!=ref["sha256"]:
            raise ValueError("SOURCE_REF_SHA_OR_SIZE_INVALID")
        dest="refs/"+path.name
        put_exact(dest,raw,token)
        published.append(dest)
    q["remote_reference_prefix"]=PREFIX+"/refs"
    q["source_reference_count_verified"]=len(published)
    queue_bytes=(json.dumps(q,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode()
    if len(queue_bytes)>450000:
        raise ValueError("QUEUE_JSON_EXCEEDS_DOCKER_READ_CAP")
    status=put_exact("latest.json",queue_bytes,token,allow_update=True)
    print(json.dumps({"status":status,"verified_refs":len(published),
                      "active_chat_tasks":len(q["tasks"]),"hold_count":q["hold_count"],
                      "release_approved":False},ensure_ascii=False))
    return status


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--queue-dir",required=True)
    p.add_argument("--qa-report",default=None)
    args=p.parse_args()
    publish(args.queue_dir,os.environ.get("GH_TOKEN",""),args.qa_report)
