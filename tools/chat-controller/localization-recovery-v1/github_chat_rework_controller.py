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
from chat_image_result_rescue import rescue_single_image_candidate

REPO = "thp32tt/OutRun2006Tweaks"
QUEUE_BRANCH = "korean-localization-qa-queue-20261104"
ASSETS_BRANCH = "korean-localization-recovery-20260928"
# Only these two existing GitHub queue namespaces are permitted.
# The fallback queue contains verified original HD reference PNGs, and is
# intentionally separate from the immutable reuse-only QA queue.
QUEUE_NAME = os.getenv("OUTRUN_REWORK_QUEUE_NAME", "hd_imagegen_fallback").strip()
if QUEUE_NAME not in ("hd_rework_queue", "hd_imagegen_fallback"):
    raise ValueError("OUTRUN_REWORK_QUEUE_NAME_NOT_ALLOWED")
QROOT = "localization/automation_runs/" + QUEUE_NAME
LEGACY_QROOT = "localization/automation_runs/hd_rework_queue"
APPROVED = "localization/automation_inputs/qa_rework/approved"
API = "https://api.github.com/repos/" + REPO
ROOT = Path(os.getenv("OUTRUN_REWORK_HOME", "/data/hd-rework")).resolve()
PROJECT_URL = os.getenv("CHATGPT_PROJECT_URL", "https://chatgpt.com/").strip()
TOKEN = os.getenv("OUTRUN_GITHUB_CONTENTS_TOKEN", "").strip()
POLL = int(os.getenv("OUTRUN_REWORK_POLL_SECONDS", "600"))
# User policy 2026-11-05: reuse existing A/B PNGs; no new ImageGen sends.
REUSE_ONLY = os.getenv("OUTRUN_REWORK_REUSE_ONLY", "1").strip() != "0"
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

def is_saved_chat_url(value):
    """Allow both native /c/... and ChatGPT Project /g/g-p-.../c/... links."""
    if not isinstance(value, str) or len(value) > 350:
        return False
    parsed = urllib.parse.urlparse(value)
    if (parsed.scheme != "https" or parsed.netloc != "chatgpt.com"
            or parsed.params or parsed.query or parsed.fragment):
        return False
    return re.fullmatch(
        r"/(?:g/g-p-[A-Za-z0-9_-]+/)?c/[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}",
        parsed.path,
    ) is not None


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
        if not (rel.startswith(QROOT+"/") or rel.startswith(LEGACY_QROOT+"/state/") or rel.startswith(APPROVED+"/")):
            raise ValueError("UNTRUSTED_PATH")
        if branch not in (QUEUE_BRANCH,ASSETS_BRANCH):
            raise ValueError("UNAPPROVED_BRANCH")
        if (payload is not None and QROOT != LEGACY_QROOT
                and rel.startswith(LEGACY_QROOT + "/")):
            raise ValueError("LEGACY_QUEUE_IS_READ_ONLY")
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

def recover_previous_sent_task(gh, task):
    """Resume an existing original-source ChatGPT send; NEVER send a duplicate.

    Old reuse-only queue states from 2026-11-05 can refer to exactly the same
    TASK_ID, source SHA, and PNG as the new fallback queue. A successful AB_SENT
    is durable submission evidence, even though its output was not collected.
    The old namespace is only read, never modified.
    """
    if QROOT == LEGACY_QROOT:
        return "NEW"
    old, _ = gh.read_json(
        LEGACY_QROOT + "/state/" + task["task_id"] + ".json", QUEUE_BRANCH
    )
    if old is None:
        return "NEW"
    # Compare the whole task: source SHA alone is not sufficient evidence.
    if (old.get("schema") != "outrun-hd-qa-chat-status-v1"
            or old.get("task_id") != task["task_id"]
            or old.get("task") != task or old.get("role") != task["role"]
            or old.get("release_approved") is not False):
        stage_state(gh, task, "HOLD", {
            "hold_reason": "LEGACY_TASK_PROVENANCE_CONFLICT_NO_RESEND",
            "recovered_from_legacy_queue": False,
        })
        return "HOLD_LEGACY_TASK_CONFLICT"
    status = old.get("status")
    if status == "AB_SENT" and is_saved_chat_url(old.get("ab_chat_url")):
        stage_state(gh, task, "AB_SENT", {
            "ab_chat_url": old["ab_chat_url"],
            "recovered_from_legacy_queue": True,
            "recovery_status": "ORIGINAL_CHAT_SENT_DO_NOT_RESEND",
        })
        return "RECOVERED_AB_SENT_NO_RESEND"
    # AB_CLAIMED, HOLD, old approvals or an invalid old chat URL are not
    # permission to create a second user message. Isolate for manual triage.
    stage_state(gh, task, "HOLD", {
        "hold_reason": "LEGACY_TASK_ALREADY_EXISTS_NO_RESEND:" + str(status)[:80],
        "recovered_from_legacy_queue": False,
    })
    return "HOLD_LEGACY_TASK_NO_RESEND"


def result_poll_diagnostic(gh, state, reason):
    """Record a sanitized WAIT code, max once per 30 min for unchanged reason."""
    if state.get("status") != "AB_SENT":
        return False
    reason = re.sub(r"[^A-Za-z0-9_:-]", "_", str(reason))[:120]
    if not reason:
        reason = "WAIT_UNKNOWN"
    now = dt.datetime.now(dt.timezone.utc)
    stamp = state.get("last_result_poll_utc")
    if state.get("last_result_poll_reason") == reason and isinstance(stamp, str):
        try:
            previous = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if previous.tzinfo and (now-previous).total_seconds() < 1800:
                return False
        except (ValueError, TypeError, OverflowError):
            pass
    stage_state(gh, state["task"], "AB_SENT", {
        "last_result_poll_utc": now.isoformat(timespec="seconds"),
        "last_result_poll_reason": reason,
        "candidate_status": "RESULT_NOT_YET_EXPORTED_OR_QA_APPROVED",
    })
    return True


def fair_task_files(files, after=None):
    """Round-robin all persisted tasks instead of starving later task IDs."""
    ordered = sorted(files, key=lambda file: file.name)
    if not ordered or not after:
        return ordered
    index = next((i for i, file in enumerate(ordered) if file.stem > after), 0)
    return ordered[index:] + ordered[:index]


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

def compact_generated_png_lossless(raw):
    """Normalize sparse lettering PNG before the 650 KiB GitHub Contents gate.

    Only transparent empty margins may be removed; no glyph pixels, alpha,
    dimensions of the original source HD atlas, or text effects are resampled.
    A source whose alpha already touches the frame is rejected before padding.
    """
    if not isinstance(raw, bytes) or len(raw) < 100 or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("CANDIDATE_NOT_PNG")
    with Image.open(io.BytesIO(raw)) as source:
        if source.format != "PNG" or not (24 <= source.width <= 4096
                                           and 12 <= source.height <= 4096):
            raise ValueError("CANDIDATE_IMAGE_DIMENSIONS")
        rgba=source.convert("RGBA")
    alpha=rgba.getchannel("A")
    bbox=alpha.getbbox()
    if not bbox or min(bbox[0],bbox[1],rgba.width-bbox[2],rgba.height-bbox[3]) < 2:
        raise ValueError("CANDIDATE_ALPHA_TOUCHES_FRAME")
    # Crop only actual all-zero-alpha borders, preserving every visible pixel.
    cropped=rgba.crop(bbox)
    packed=Image.new("RGBA",(cropped.width+16,cropped.height+16),(0,0,0,0))
    packed.paste(cropped,(8,8))
    buffer=io.BytesIO()
    packed.save(buffer,format="PNG",optimize=True,compress_level=9)
    compact=buffer.getvalue()
    if len(compact)>MAX_CONTENTS_PNG:
        raise ValueError("CANDIDATE_LOSSLESS_PNG_EXCEEDS_GITHUB_LIMIT")
    return compact


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
    for raw in re.findall(r"\{[^{}]{50,4000}\}",body):
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



class ChatBridge:
    """One persistent Chrome context and separate A/B/C1 conversations."""
    def __init__(self, gh, playwright):
        self.gh=gh
        self.playwright=playwright
        self.context=None
        self.browser=None
        self.pages={}
        self.last_inspected_task=None

    async def ensure_context(self):
        """Attach only to the already-visible VNC Chromium; never spawn a second profile."""
        if self.context is None:
            # Local-only CDP port is started by entrypoint, never exposed to host.
            browser=await self.playwright.chromium.connect_over_cdp(
                "http://127.0.0.1:9222",timeout=30000)
            if len(browser.contexts)!=1:
                await browser.close()
                raise RuntimeError("HOLD_CHROME_CDP_CONTEXT_NOT_EXACTLY_ONE")
            self.browser=browser
            self.context=browser.contexts[0]
            # Reuse first visible tab, so user login goes into actual A/B session.
            if self.context.pages:
                self.pages["A"]=self.context.pages[0]
        return self.context

    async def bootstrap_login_page(self):
        """Open the visible ChatGPT login tab BEFORE polling GitHub or any queue.

        A missing token, GitHub outage, empty queue or composer login screen
        must never prevent the browser from appearing on the authenticated VNC.
        """
        await self.ensure_context()
        pg=self.pages.get("A")
        if pg is None or pg.is_closed():
            pg=await self.context.new_page()
            self.pages["A"]=pg
        try:
            await pg.bring_to_front()
            if pg.url.rstrip("/")!=PROJECT_URL.rstrip("/"):
                await pg.goto(PROJECT_URL,wait_until="domcontentloaded",timeout=30000)
            # Showing the browser window does not prove a logged-out session.
            return "CHATGPT_BROWSER_TAB_VISIBLE_AUTH_UNVERIFIED"
        except Exception as exc:
            # Chromium window is still visible for manual navigation.
            return "HOLD_CHATGPT_PAGE_NAVIGATION_"+type(exc).__name__

    async def page(self,role,url=None,*,read_only=False):
        """Read-only result retrieval never depends on a visible chat composer.

        A submitted message has an independently verified persisted chat URL.
        A missing/redirected URL is not proof of authentication and cannot be
        used to fetch an unrelated or user-uploaded image. New A/B/C1 sends
        still require the visible composer and attachment checks.
        """
        if role not in ("A","B","C1"):
            raise ValueError("INVALID_ROLE")
        if read_only and not is_saved_chat_url(url):
            return None
        await self.ensure_context()
        pg=self.pages.get(role)
        if pg is None or pg.is_closed():
            pg=await self.context.new_page()
            self.pages[role]=pg
        target=url if is_saved_chat_url(url) else PROJECT_URL
        if pg.url.rstrip("/")!=target.rstrip("/"):
            await pg.goto(target,wait_until="domcontentloaded",timeout=60000)
        if read_only:
            # A login redirect or an unexpected conversation must not be
            # mistaken for the original source-bound assistant response.
            if not is_saved_chat_url(pg.url) or pg.url.rstrip("/") != target.rstrip("/"):
                return None
            return pg
        composer=pg.locator('[role="textbox"][contenteditable="true"]').first
        try:
            await composer.wait_for(state="visible",timeout=11000)
        except Exception:
            return None
        return pg

    async def send_with_png(self,pg,task,prompt,paths,imagegen):
        if pg is None:
            return "HOLD_CHATGPT_LOGIN_REQUIRED"
        if imagegen:
            status=await ensure_image_tool(pg)
            if status!="CREATE_IMAGE_TOOL_SELECTED":
                return "HOLD_IMAGE_TOOL_NOT_VERIFIED"
        else:
            selected=pg.locator('[data-inline-selection-pill][data-system-hint-type="picture_v2"]')
            if await selected.count():
                return "HOLD_C1_IMAGE_TOOL_SELECTED"
        clear=await clear_attachment_previews(pg)
        if clear!="COMPOSER_ATTACHMENTS_CLEAR":
            return "HOLD_COMPOSER_ATTACHMENTS_NOT_CLEAR"
        binding={"path":str(paths[0])} if len(paths)==1 else {"paths":[str(x) for x in paths]}
        uploaded=(await attach_png(pg,binding)) if len(paths)==1 else (
            await attach_batch_pngs(pg,binding))
        if uploaded!="ATTACHMENT_UPLOAD_COMPLETED":
            return "HOLD_CHAT_UPLOAD_NOT_VERIFIED"
        box=pg.locator('[role="textbox"][contenteditable="true"]').first
        await box.click()
        await pg.keyboard.insert_text(prompt+"\n\nUPLOAD_TASK_ID="+task["task_id"])
        if "UPLOAD_TASK_ID="+task["task_id"] not in await box.inner_text():
            return "HOLD_CHAT_COMPOSER_MARKER_MISSING"
        await box.press("Enter")
        receipt=await verify_submission_receipt(
            pg,task["task_id"],[p.name for p in paths])
        if receipt!="PERSISTED_CHAT_USER_MESSAGE_WITH_IMAGE_CONFIRMED":
            return "HOLD_CHAT_SENT_UNVERIFIED"
        if "/c/" not in pg.url or "local-chatgpt" in pg.url:
            return "HOLD_CHAT_URL_NOT_PERSISTED"
        return "CHAT_SENT_VERIFIED"

    async def submit_producer(self,task):
        pg=await self.page(task["role"])
        if pg is None:
            return "HOLD_CHATGPT_LOGIN_REQUIRED"
        source=await asyncio.to_thread(stage_source_ref,self.gh,task)
        prompt=(
          "@Create image — OutRun 2006 HD 원본 영문 UI 문구를 한글 PNG로 교체.\n"
          "첨부는 원본 HD DDS SHA와 좌표가 검증된 원문 크롭입니다.\n"
          "영문 원문: "+task["english"]+"\n한국어 번역: "+task["korean"]+
          "\n원문 글자/외곽선/그림자만 한국어로 새로 만드세요."
          "\n배경, 자동차, 아이콘, 박스, 영어 원문은 새 PNG에 포함하지 마세요."
          "\n**투명한 RGBA PNG 한 장**, 글자와 효과가 PNG 가장자리에 닿지 않도록."
          "\n글자 크기, 기울기, 줄바꿈은 원본 HD의 개별 문구를 기준으로 하며"
          " 원문 텍스트/효과보다 크면 안 됩니다. 종횡비 강제 확대 금지."
          "\n원문 제거/CLEAN 배경 복원은 독립 QA에서 검증하며 덧쓰기만 하지 않습니다."
          "\n완성이라고 주장하지 말고 생성 PNG만 제공하세요."
          "\n원본 DDS SHA: "+task["source_dds_sha256"])
        await asyncio.to_thread(stage_state,self.gh,task,"AB_CLAIMED")
        state=await self.send_with_png(pg,task,prompt,[source],True)
        if state!="CHAT_SENT_VERIFIED":
            await asyncio.to_thread(stage_state,self.gh,task,"HOLD",{"hold_reason":state})
            return state
        await asyncio.to_thread(stage_state,self.gh,task,"AB_SENT",{
            "ab_chat_url":pg.url})
        return "AB_SENT"

    async def collect_producer(self,state):
        """Recover a previously sent single generated image, never resend."""
        import text_roi_queue as old
        task=state["task"]
        pg=await self.page(task["role"],state.get("ab_chat_url"),read_only=True)
        if pg is None:
            reason="WAIT_CHATGPT_COMPOSER_OR_LOGIN"
            await asyncio.to_thread(result_poll_diagnostic,self.gh,state,reason)
            return reason
        # Prefer the verified assistant-only probe; the legacy inspector
        # cannot recognize many newly rendered ChatGPT Project message turns.
        saved,why=await rescue_single_image_candidate(
            pg,task["task_id"],task["role"],str(ROOT),binding=task
        )
        if saved not in ("LOCAL_CANDIDATES_EXPORTED_UNAPPROVED",
                         "EXISTING_CANDIDATES_VERIFIED"):
            saved=None
            # domcontentloaded may precede ChatGPT's user/assistant hydration.
            # One 1.2s retry; no full reload or duplicate ImageGen request.
            if (why.startswith("CHAT_USER_TURNS_NOT_RENDERED") or
                    why.startswith("SOURCE_BOUND_USER_TURN_MISSING") or
                    why.startswith("ASSISTANT_GENERATED_IMAGE_NOT_RENDERED")):
                await pg.wait_for_timeout(1200)
                again,detail=await rescue_single_image_candidate(
                    pg,task["task_id"],task["role"],str(ROOT),binding=task
                )
                why=detail
                if again in ("LOCAL_CANDIDATES_EXPORTED_UNAPPROVED",
                             "EXISTING_CANDIDATES_VERIFIED"):
                    saved=again
        page_reloaded=False
        legacy_export_attempted=False
        probe=({"error":"RESCUED_ASSISTANT_IMAGE"} if saved else
               await old._probe_imagegen_result(pg,task["task_id"],1))
        if saved is None and probe.get("error")=="USER_TURN_MISSING":
            # Once the correct user turn is found but assistant media is not
            # rendered, avoid 24s legacy waits and repeated page reloads.
            if (why.startswith("CHAT_USER_TURNS_NOT_RENDERED") or
                    why.startswith("SOURCE_BOUND_USER_TURN_MISSING")):
                recovered=await old._recover_task_turn(pg,task["task_id"])
                if recovered:
                    page_reloaded=True
                    probe=await old._probe_imagegen_result(pg,task["task_id"],1)
        legacy_status="WAIT_IMAGEGEN_"+str(
            probe.get("error") or (
                "BUSY" if probe.get("busy")
                else "COUNT_"+str(probe.get("count","UNKNOWN"))
            )
        )
        if (saved is None and probe.get("error") is None
                and probe.get("count")==1 and not probe.get("busy")):
            source_name=task["reference"]["name"]
            active={"task_id":task["task_id"],"role":task["role"],"count":1,
                    "items":[{"output_filename":task["task_id"]+".png",
                              "ordinal":1,"filename":source_name,
                              "width":task["reference"]["width"],
                              "height":task["reference"]["height"]}]}
            legacy_export_attempted=True
            try:
                saved=await old.export_unapproved_k_candidates(pg,active,str(ROOT))
            except (ValueError,OSError) as exc:
                legacy_status="WAIT_IMAGEGEN_LEGACY_EXPORT_"+type(exc).__name__
        if saved not in ("LOCAL_CANDIDATES_EXPORTED_UNAPPROVED",
                         "EXISTING_CANDIDATES_VERIFIED"):
            # Strict assistant-turn detector excludes the user's English
            # attachment, unrelated cards, CSS screenshots and generic images.
            # Recheck after the legacy path only; never mistake a reference
            # image, loading placeholder or unrelated turn for generated PNG.
            if page_reloaded or legacy_export_attempted:
                rescued,detail=await rescue_single_image_candidate(
                    pg,task["task_id"],task["role"],str(ROOT),binding=task
                )
                if rescued in ("LOCAL_CANDIDATES_EXPORTED_UNAPPROVED",
                               "EXISTING_CANDIDATES_VERIFIED"):
                    saved=rescued
                else:
                    why=detail
            if saved not in ("LOCAL_CANDIDATES_EXPORTED_UNAPPROVED",
                             "EXISTING_CANDIDATES_VERIFIED"):
                reason=re.sub(r"[^A-Za-z0-9_:-]","_",str(why or legacy_status))[:120]
                await asyncio.to_thread(result_poll_diagnostic,self.gh,state,reason)
                return "WAIT_IMAGEGEN_"+reason
        file=ROOT/old.STATE_DIR/"candidate_outputs"/task["role"]/(task["task_id"]+".png")
        try:
            original_png=file.read_bytes()
            png=compact_generated_png_lossless(original_png)
            dimensions=valid_generated_image(png)
        except (ValueError,OSError) as exc:
            # An opaque or clipped generated image must not be approved.
            reason="CANDIDATE_ALPHA_OR_PNG_"+type(exc).__name__
            await asyncio.to_thread(stage_state,self.gh,task,"HOLD",{
                "hold_reason":reason,
                "candidate_status":"REWORK_REQUIRED_BEFORE_C1",
            })
            return "HOLD_"+reason
        digest=hashlib.sha256(png).hexdigest()
        rel=QROOT+"/candidates/"+task["task_id"]+".png"
        await asyncio.to_thread(self.gh.write,rel,QUEUE_BRANCH,png)
        await asyncio.to_thread(stage_state,self.gh,task,"C1_READY",{
            "ab_chat_url":pg.url,"candidate_sha256":digest,
            "candidate_dimensions":dimensions,
            "candidate_generated_raw_sha256":hashlib.sha256(original_png).hexdigest(),
            "candidate_gh_path":rel,
            "candidate_status":"IMAGEGEN_BLOB_SAVED_PENDING_C1",
        })
        return "C1_READY"

    async def submit_c1(self,state):
        task=state["task"]
        candidate_sha=state.get("candidate_sha256","")
        if not HASH.fullmatch(candidate_sha):
            raise ValueError("C1_CANDIDATE_HASH_MISSING")
        pg=await self.page("C1")
        if pg is None:
            return "HOLD_C1_LOGIN_REQUIRED"
        source=await asyncio.to_thread(stage_source_ref,self.gh,task)
        rel=state["candidate_gh_path"]
        if rel!=QROOT+"/candidates/"+task["task_id"]+".png":
            raise ValueError("C1_CANDIDATE_PATH_CHANGED")
        png,_=await asyncio.to_thread(self.gh.read,rel,QUEUE_BRANCH)
        if png is None or hashlib.sha256(png).hexdigest()!=candidate_sha:
            raise ValueError("C1_CANDIDATE_FILE_HASH_CHANGED")
        local=ROOT/"c1_candidates"/(task["task_id"]+"_HANGUL.png")
        local.parent.mkdir(parents=True,exist_ok=True)
        if local.is_file() and local.read_bytes()!=png:
            raise ValueError("C1_LOCAL_CANDIDATE_CONFLICT")
        local.write_bytes(png)
        prompt=(
            "OutRun 2006 한글화 C1 독립 시각 QA입니다. A/B 제작자가 아닙니다.\n"
            "첨부 1은 원본 HD DDS에서 읽는 방향으로 추출한 영문, 첨부 2는 생성된 한글입니다.\n"
            "원문 영문: "+task["english"]+"\n정확한 번역: "+task["korean"]+
            "\n원본 HD 네이티브 글자 크기·기울기·줄 수, 원문 제거/CLEAN 복원 가능성,"
            " 영문 잔상, 다른 UI 침범, 한글 맞춤법·깨짐을 검사하세요."
            "\n텍스트가 원본 크기보다 크거나 줄 수가 다르거나, 원문 위에 단순 덧쓴 듯하면 REWORK_REQUIRED."
            "\n불투명 배경을 복원할 독립 CLEAN 마스크 증거가 없으면 HOLD_EVIDENCE."
            "\n실게임 승인/최종 C3 PASS를 주장하지 마세요."
            "\n응답은 JSON 객체 한 개로만 작성하세요. 필드는"
            " task_id,source_dds_sha256,candidate_sha256,decision,reason 입니다."
            "\n결정값은 PASS_PROVISIONAL,REWORK_REQUIRED,HOLD_EVIDENCE 중 하나이며"
            " PASS_PROVISIONAL도 기계적 DDS·C3·인게임 검수 전 승인 아님."
            "\ntask_id: "+task["task_id"]+
            "\nsource_dds_sha256: "+task["source_dds_sha256"]+
            "\ncandidate_sha256: "+candidate_sha)
        outcome=await self.send_with_png(pg,task,prompt,[source,local],False)
        if outcome!="CHAT_SENT_VERIFIED":
            await asyncio.to_thread(stage_state,self.gh,task,"HOLD",{
                "hold_reason":outcome,"candidate_sha256":candidate_sha})
            return outcome
        await asyncio.to_thread(stage_state,self.gh,task,"C1_SENT",{
            "candidate_sha256":candidate_sha,
            "candidate_gh_path":rel,"ab_chat_url":state.get("ab_chat_url"),
            "c1_chat_url":pg.url})
        return "C1_SENT"

    async def inspect_c1(self,state):
        task=state["task"]
        pg=await self.page("C1",state.get("c1_chat_url"),read_only=True)
        if pg is None:
            return "HOLD_C1_LOGIN_REQUIRED"
        responses=await pg.locator(
            '[data-markdown-text-tone="assistant"],[data-message-author-role="assistant"]'
        ).all_inner_texts()
        body="\n".join(responses[-3:])
        candidate_sha=state["candidate_sha256"]
        decision=c1_decision_from_text(body,task["task_id"],
                    task["source_dds_sha256"],candidate_sha)
        if decision is None:
            return "WAIT_C1_EXACT_JSON"
        if decision["decision"]!="PASS_PROVISIONAL":
            await asyncio.to_thread(stage_state,self.gh,task,
                 "C1_REWORK_REQUIRED" if decision["decision"]=="REWORK_REQUIRED" else "HOLD",
                 {"hold_reason":decision["reason"],"c1_decision":decision,
                  "candidate_sha256":candidate_sha,
                  "c1_chat_url":pg.url})
            return decision["decision"]
        rel=QROOT+"/candidates/"+task["task_id"]+".png"
        png,_=await asyncio.to_thread(self.gh.read,rel,QUEUE_BRANCH)
        if not png or hashlib.sha256(png).hexdigest()!=candidate_sha:
            raise ValueError("C1_APPROVAL_PNG_SHA_MISSING")
        result=await asyncio.to_thread(publish_c1_candidate,
              self.gh,task,decision,png)
        await asyncio.to_thread(stage_state,self.gh,task,
             "C1_PASS_STAGED_FOR_GITHUB_TEST_ONLY",{
             "c1_chat_url":pg.url,"c1_decision":decision,
             "candidate_sha256":candidate_sha,
             "asset_candidate":APPROVED+"/"+task["task_id"]+".png",
             "asset_receipt":APPROVED+"/"+task["task_id"]+".json",
             "release_approved":False})
        return "C1_PASS_STAGED_FOR_GITHUB_TEST_ONLY"

    async def cycle(self):
        queue,_=await asyncio.to_thread(self.gh.read_json,
                                QROOT+"/latest.json",QUEUE_BRANCH)
        if not isinstance(queue,dict) or queue.get("schema")!="outrun-hd-qa-chat-workqueue-v1":
            return {"status":"HOLD_QUEUE_SCHEMA"}
        tasks=queue.get("tasks",[])
        if not isinstance(tasks,list) or len(tasks)>8:
            return {"status":"HOLD_QUEUE_SIZE"}
        if (queue.get("release_approved") is not False
                or queue.get("runtime_validation") != "UNTESTED"
                or (not REUSE_ONLY and queue.get("new_imagegen_disabled") is not False)
                or (QUEUE_NAME == "hd_imagegen_fallback"
                    and (queue.get("source_reference_count_verified") != len(tasks)
                         or any(t.get("qa_authority") != "NOT_C1_APPROVED_NOT_GAME_APPROVED"
                                for t in tasks)))):
            return {"status":"HOLD_QUEUE_AUTHORITY_OR_SOURCE_PROOF"}
        submitted=[]
        for task in ([] if REUSE_ONLY else tasks):
            if not valid_task(task):
                return {"status":"HOLD_INVALID_TASK"}
            prior,_=await asyncio.to_thread(self.gh.read_json,
                           task_state_path(task["task_id"]),QUEUE_BRANCH)
            if prior:
                # A restart or lost local checkpoint must not cause either
                # duplicate sending or permanent loss of C1 processing.
                if (prior.get("task") == task and
                        prior.get("status") in SEND_STATES):
                    await asyncio.to_thread(local_save, task["task_id"], prior)
                continue
            try:
                recovery=await asyncio.to_thread(recover_previous_sent_task, self.gh, task)
                result=(await self.submit_producer(task)) if recovery=="NEW" else recovery
            except Exception as exc:
                result="HOLD_"+type(exc).__name__
            submitted.append({"task_id":task["task_id"],"result":result})
            # Keep browser and account usage bounded: at most two sends per cycle.
            if len(submitted)>=2:
                break
        progressed=[]
        c1_sent_this_cycle=0
        tasks_root=ROOT/"tasks"
        files=(fair_task_files(tasks_root.glob("HDRW-*.json"),
                               self.last_inspected_task)
               if tasks_root.is_dir() else [])
        for file in files:
            self.last_inspected_task=file.stem
            try:
                entry=json.loads(file.read_text(encoding="utf-8"))
                if not valid_task(entry.get("task",{})):
                    continue
                task=entry["task"]
                if entry.get("status") not in SEND_STATES:
                    continue
                updated,_=await asyncio.to_thread(self.gh.read_json,
                                  task_state_path(task["task_id"]),QUEUE_BRANCH)
                if updated is None:
                    continue
                status=updated.get("status")
                if status=="AB_SENT":
                    result=await self.collect_producer(updated)
                elif status=="C1_READY":
                    if c1_sent_this_cycle>=1:
                        continue
                    result=await self.submit_c1(updated)
                    c1_sent_this_cycle+=1
                elif status=="C1_SENT":
                    result=await self.inspect_c1(updated)
                else:
                    continue
                progressed.append({"task_id":task["task_id"],"status":result})
                if len(progressed)>=3:
                    break
            except Exception as exc:
                progressed.append({"error_type":type(exc).__name__})
                if len(progressed)>=3:
                    break
        return {"status":"CYCLE_REUSE_ONLY" if REUSE_ONLY else "CYCLE_OK",
                 "new_imagegen_disabled":REUSE_ONLY,"active_queue":len(tasks),
                "sent":submitted,"processed":progressed,
                "release_approved":False}

    async def close(self):
        # The entrypoint owns Chromium and its persistent login profile.
        # Never call Browser.close() on this CDP connection: that could close
        # the manually authenticated visible window during a worker restart.
        self.context=None
        self.browser=None


async def run_forever():
    if not 120<=POLL<=3600:
        raise ValueError("OUTRUN_REWORK_POLL_SECONDS_OUT_OF_BOUNDS")
    check_project_url(PROJECT_URL)
    ROOT.mkdir(parents=True,exist_ok=True)
    gh=Github(TOKEN) if TOKEN else None
    async with async_playwright() as playwright:
        bridge=ChatBridge(gh,playwright)
        try:
            # Independent from GitHub availability, task queue and user login.
            while True:
                try:
                    browser_state=await bridge.bootstrap_login_page()
                    print(json.dumps({"status":browser_state,"checked_utc":utc()},
                                     ensure_ascii=False,sort_keys=True),flush=True)
                    break
                except Exception as exc:
                    # Retry startup rather than leaving a blank VNC desktop.
                    print(json.dumps({"status":"HOLD_BROWSER_BOOTSTRAP_RETRY",
                        "error_type":type(exc).__name__,"checked_utc":utc()},
                        sort_keys=True),flush=True)
                    await asyncio.sleep(30)
            while True:
                try:
                    if not TOKEN:
                        result={"status":"HOLD_GITHUB_CONTENTS_TOKEN_MISSING",
                                "browser_login_available":True}
                    else:
                        result=await bridge.cycle()
                except Exception as exc:
                    # Fail closed without exposing token, page or user content.
                    result={"status":"HOLD_RETRY","error_type":type(exc).__name__}
                result["checked_utc"]=utc()
                print(json.dumps(result,ensure_ascii=False,sort_keys=True),flush=True)
                await asyncio.sleep(POLL)
        finally:
            await bridge.close()


if __name__=="__main__":
    asyncio.run(run_forever())
