#!/usr/bin/env python3
"""Optional authenticated browser bridge: GitHub QA HOLD -> A/B image -> C1 QA.

No paid image API. A/B and C1 use real ChatGPT browser conversations with
source PNG attachments; never claim success without persisted image evidence.
All DDS synthesis remains on GitHub Actions, not on N100.
"""
from __future__ import annotations
import asyncio
import base64
import datetime as dt
import hashlib
import io
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from playwright.async_api import async_playwright

from controller_png_attach import (
    ensure_image_tool, attach_png, attach_batch_pngs,
    verify_submission_receipt, clear_attachment_previews,
)

REPO = "thp32tt/OutRun2006Tweaks"
QUEUE_BRANCH = "korean-localization-qa-queue-20261104"
ASSETS_BRANCH = "korean-localization-recovery-20260928"
QROOT = "localization/automation_runs/hd_rework_queue"
APPROVED = "localization/automation_inputs/qa_rework/approved"
API = "https://api.github.com/repos/" + REPO
ROOT = Path(os.getenv("OUTRUN_REWORK_HOME", "/data/hd-rework")).resolve()
PROJECT_URL = os.getenv("CHATGPT_PROJECT_URL", "https://chatgpt.com/").strip()
TOKEN = os.getenv("OUTRUN_GITHUB_CONTENTS_TOKEN", "").strip()
POLL = int(os.getenv("OUTRUN_REWORK_POLL_SECONDS", "300"))
CHAT_TASK = re.compile(r"^HDRW-[AB]-[0-9a-f]{20}$")
HASH = re.compile(r"^[0-9a-f]{64}$")
MAX_CONTENTS_PNG = 650 * 1024
MAX_QUEUE_JSON = 512 * 1024
SEND_STATES = ("AB_SENT", "C1_READY", "C1_SENT")
FINAL_STATES = ("C1_PASS_STAGED_FOR_GITHUB_TEST_ONLY", "C1_REWORK_REQUIRED", "HOLD")

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

def check_project_url(value):
    u = urllib.parse.urlparse(value)
    if u.scheme != "https" or u.netloc != "chatgpt.com" or u.username or u.password:
        raise ValueError("CHATGPT_PROJECT_URL_MUST_BE_HTTPS_CHATGPT_COM")
    return value

def safe_file_name(value):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,110}",value):
        raise ValueError("INVALID_FILE_NAME")
    return value

def valid_task(task):
    return isinstance(task,dict) and CHAT_TASK.fullmatch(task.get("task_id","")) and (
        task.get("role") in ("A","B") and task["task_id"].startswith("HDRW-"+task["role"]+"-") and
        HASH.fullmatch(task.get("source_dds_sha256","")) and
        HASH.fullmatch(task.get("old_candidate_sha256","")) and
        isinstance(task.get("reference"),dict) and
        HASH.fullmatch(task["reference"].get("sha256",""))
    )

class Github:
    def __init__(self, token):
        if not token:
            raise ValueError("OUTRUN_GITHUB_CONTENTS_TOKEN_REQUIRED_TO_SEND_OR_SAVE")
        self.token=token

    def req(self, rel, branch, payload=None):
        if not (rel.startswith(QROOT+"/") or rel.startswith(APPROVED+"/")):
            raise ValueError("UNTRUSTED_PATH")
        if branch not in (QUEUE_BRANCH,ASSETS_BRANCH):
            raise ValueError("UNAPPROVED_BRANCH")
        if ".." in rel or "\\" in rel or any(not re.fullmatch(r"[A-Za-z0-9_.-]+",x) for x in rel.split("/")):
            raise ValueError("UNSAFE_REPOSITORY_PATH")
        uri=API+"/contents/"+"/".join(urllib.parse.quote(p,safe="") for p in rel.split("/"))
        if payload is None:
            uri+="?ref="+urllib.parse.quote(branch,safe="")
        data=json.dumps(payload,separators=(",",":")).encode() if payload is not None else None
        req=urllib.request.Request(uri,method="PUT" if payload is not None else "GET",data=data,
            headers={"Accept":"application/vnd.github+json","Content-Type":"application/json",
                     "X-GitHub-Api-Version":"2022-11-28",
                     "User-Agent":"outrun-hd-qa-chat-bridge",
                     "Authorization":"Bearer "+self.token})
        try:
            with urllib.request.urlopen(req,timeout=40) as res:
                raw=res.read(7*1024*1024)
            return json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code==404 and payload is None:
                return None
            # Do not print request URL, response body or bearer token.
            raise RuntimeError("GITHUB_CONTENTS_HTTP_"+str(exc.code)) from None

    def read(self,rel,branch):
        j=self.req(rel,branch)
        if j is None:
            return None,None
        if not isinstance(j,dict) or j.get("encoding")!="base64":
            raise ValueError("QUEUE_CONTENT_NOT_INLINE_BASE64")
        raw=base64.b64decode(j.get("content",""),validate=False)
        if len(raw)>MAX_QUEUE_JSON and not rel.endswith(".png"):
            raise ValueError("QUEUE_JSON_TOO_BIG")
        if len(raw)>MAX_CONTENTS_PNG and rel.endswith(".png"):
            raise ValueError("QUEUE_PNG_TOO_BIG")
        return raw,j["sha"]

    def write(self,rel,branch,payload,expected=None,overwrite=False):
        if not isinstance(payload,bytes) or len(payload)>MAX_CONTENTS_PNG:
            raise ValueError("GITHUB_SUBMIT_PAYLOAD_TOO_BIG")
        existing,sha=self.read(rel,branch)
        if existing is not None:
            if existing==payload:
                return "ALREADY_STAGED_EXACT"
            if not overwrite or expected!=sha:
                raise ValueError("QUEUE_CAS_CONFLICT_OR_EXISTING_DIFFERENT")
        body={"message":"localization(qa): stage SHA-bound "+rel.split("/")[-1],
              "content":base64.b64encode(payload).decode("ascii"),"branch":branch}
        if sha:
            body["sha"]=sha
        saved=self.req(rel,branch,body)
        if not re.fullmatch(r"[0-9a-f]{40}",saved.get("commit",{}).get("sha","")):
            raise RuntimeError("GITHUB_COMMIT_NOT_VERIFIED")
        check,_=self.read(rel,branch)
        if check!=payload:
            raise RuntimeError("GITHUB_WRITE_READBACK_MISMATCH")
        return saved["commit"]["sha"]

    def read_json(self,rel,branch):
        raw,sha=self.read(rel,branch)
        return (json.loads(raw) if raw is not None else None),sha

    def write_json(self,rel,branch,data,expected=None,overwrite=False):
        raw=(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode()
        return self.write(rel,branch,raw,expected,overwrite)


def task_state_path(task_id):
    if not CHAT_TASK.fullmatch(task_id):
        raise ValueError("INVALID_TASK_ID")
    return QROOT+"/state/"+task_id+".json"

def local_task_path(task_id):
    if not CHAT_TASK.fullmatch(task_id):
        raise ValueError("INVALID_TASK_ID")
    return ROOT/"tasks"/(task_id+".json")

def local_save(task_id,data):
    path=local_task_path(task_id)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".rework-",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as h:
            json.dump(data,h,ensure_ascii=False,sort_keys=True,indent=2)
            h.write("\n")
            h.flush()
            os.fsync(h.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def stage_state(gh,task,status,extras=None):
    task_id=task["task_id"]
    path=task_state_path(task_id)
    prior,sha=gh.read_json(path,QUEUE_BRANCH)
    if prior and prior.get("task_id")!=task_id:
        raise ValueError("STATE_TASK_ID_CONFLICT")
    if prior and prior.get("source_dds_sha256")!=task["source_dds_sha256"]:
        raise ValueError("STATE_ORIGINAL_SHA_CHANGED")
    result=dict(prior or {})
    result.update({"schema":"outrun-hd-qa-chat-status-v1",
                   "task_id":task_id,"role":task["role"],"roi_id":task["roi_id"],
                   "source_dds_sha256":task["source_dds_sha256"],
                   "old_candidate_sha256":task["old_candidate_sha256"],
                   "status":status,"updated_utc":utc(),
                   "release_approved":False,"runtime_validation":"UNTESTED",
                   "task":task})
    result.update(extras or {})
    gh.write_json(path,QUEUE_BRANCH,result,expected=sha,overwrite=True)
    local_save(task_id,result)
    return result

def stage_source_ref(gh,task):
    if not valid_task(task):
        raise ValueError("INVALID_GITHUB_WORK_TICKET")
    name=safe_file_name(task["reference"]["name"])
    if name!=task["task_id"]+"_HD_SOURCE.png":
        raise ValueError("TASK_SOURCE_REFERENCE_NAME_MISMATCH")
    raw,_=gh.read(QROOT+"/refs/"+name,QUEUE_BRANCH)
    if not raw or hashlib.sha256(raw).hexdigest()!=task["reference"]["sha256"]:
        raise ValueError("TASK_SOURCE_REFERENCE_SHA_MISMATCH")
    if raw[:8]!=b"\x89PNG\r\n\x1a\n":
        raise ValueError("TASK_SOURCE_REFERENCE_NOT_PNG")
    target=ROOT/"inputs"/name
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and target.read_bytes()!=raw:
        raise ValueError("TASK_SOURCE_LOCAL_CONFLICT")
    target.write_bytes(raw)
    return target

def valid_generated_image(raw):
    if len(raw)>MAX_CONTENTS_PNG or len(raw)<100 or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("CANDIDATE_NOT_SAFE_GITHUB_PNG")
    try:
        with Image.open(io.BytesIO(raw)) as handle:
            if handle.format!="PNG" or not (24<=handle.width<=4096 and 12<=handle.height<=4096):
                raise ValueError("CANDIDATE_IMAGE_DIMENSIONS")
            handle.load()
            im=handle.convert("RGBA")
    except (OSError,UnidentifiedImageError) as exc:
        raise ValueError("CANDIDATE_PNG_DECODE_FAIL") from exc
    alpha=im.getchannel("A")
    bbox=alpha.getbbox()
    if not bbox or min(bbox[0],bbox[1],im.width-bbox[2],im.height-bbox[3])<2:
        raise ValueError("CANDIDATE_ALPHA_TOUCHES_FRAME")
    if alpha.getpixel((0,0))!=0 or alpha.getpixel((im.width-1,im.height-1))!=0:
        raise ValueError("CANDIDATE_BACKGROUND_NOT_TRANSPARENT")
    # This verifies PNG structure, not actual Korean wording, font or clean plate.
    return [im.width,im.height]


# Stage 2: browser task execution remains separately gated by logged-in UI evidence.


def c1_decision_from_text(body, task_id, source_sha, candidate_sha):
    """Recognize only an exact structured independent reviewer response."""
    if not isinstance(body,str) or len(body)>20000:
        return None
    matches=[]
    for raw in re.findall(r"\\{[^{}]{50,4000}\\}",body):
        try:
            decision=json.loads(raw)
        except ValueError:
            continue
        if (decision.get("task_id")==task_id
            and decision.get("source_dds_sha256")==source_sha
            and decision.get("candidate_sha256")==candidate_sha
            and decision.get("decision") in
                 ("PASS_PROVISIONAL","REWORK_REQUIRED","HOLD_EVIDENCE")
            and isinstance(decision.get("reason"),str)
            and 15<=len(decision["reason"])<=1500):
            matches.append(decision)
    return matches[0] if len(matches)==1 else None


def publish_c1_candidate(gh,task,decision,png):
    """Store only a C1 provisional candidate; DDS/C3/game gate still pending."""
    if decision.get("decision")!="PASS_PROVISIONAL":
        raise ValueError("C1_NOT_PROVISIONAL_PASS")
    candidate_sha=hashlib.sha256(png).hexdigest()
    if decision.get("candidate_sha256")!=candidate_sha:
        raise ValueError("C1_CANDIDATE_HASH_MISMATCH")
    dimensions=valid_generated_image(png)
    receipt={
        "schema":"outrun-hd-rework-c1-provisional-v1",
        "task_id":task["task_id"],"role":task["role"],"roi_id":task["roi_id"],
        "source_dds_path":task["source_dds_path"],
        "source_dds_sha256":task["source_dds_sha256"],
        "old_candidate_sha256":task["old_candidate_sha256"],
        "candidate_sha256":candidate_sha,
        "candidate_native_dimensions":dimensions,
        "c1_decision":"C1_PRELIMINARY_PASS_NOT_C3",
        "c1_reason":decision["reason"],
        "release_approved":False,"runtime_validation":"UNTESTED",
        "visual_qa":"C1_PRELIMINARY_NEEDS_HD_DDS_AND_C3",
    }
    rel=APPROVED+"/"+task["task_id"]
    gh.write(rel+".png",ASSETS_BRANCH,png)
    gh.write_json(rel+".json",ASSETS_BRANCH,receipt)
    return receipt

