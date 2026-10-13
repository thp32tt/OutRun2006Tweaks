"""Fail-closed, source-bound ChatGPT composer PNG uploads (localization A/B only).

Input is an operator-staged JSON manifest in /data/imagegen/pending_A.json or
pending_B.json. This module never invokes the paid Images API, starts Docker,
or marks an image as generated. UI attachment is not ImageGen completion.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import zlib

ROOT = Path("/data/imagegen")
SHA = re.compile(r"[0-9a-f]{64}\Z")
TASK = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
PREVIEW = (
    "[data-testid*='attachment'], [data-testid*='upload-preview'], "
    "[data-testid*='file-upload'], button[aria-label*='Remove file'], "
    "button[aria-label*='Remove attachment'], img[src^='blob:']"
)


def load_binding(role, root=ROOT):
    """Return (binding, reason). Missing/invalid inputs MUST NOT send text only."""
    if role not in ("A", "B"):
        return None, "NOT_A_PRODUCER"
    pilot = os.environ.get("OUTRUN_A_SINGLE_SMOKE_TASK_ID", "").strip()
    if pilot and not TASK.fullmatch(pilot):
        return None, "INVALID_PILOT_TASK_ID"
    if pilot and role != "A":
        return None, "PILOT_ROLE_BLOCKED"
    root = Path(root).resolve()
    manifest = root / ("pending_" + role + ".json")
    if not manifest.is_file() or manifest.is_symlink():
        return None, "SOURCE_REFERENCE_NOT_BOUND"
    try:
        if manifest.stat().st_size > 256 * 1024:
            return None, "MANIFEST_TOO_LARGE"
        entry = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(entry, dict) or entry.get("role") != role:
            return None, "ROLE_MISMATCH"
        task = entry.get("task_id")
        digest = entry.get("png_sha256")
        source_digest = entry.get("source_dds_sha256")
        prompt = entry.get("prompt")
        rel = entry.get("png")
        if not isinstance(task, str) or not TASK.fullmatch(task):
            return None, "INVALID_TASK_ID"
        if pilot and task != pilot:
            return None, "PILOT_TASK_ID_MISMATCH"
        if not isinstance(digest, str) or not SHA.fullmatch(digest):
            return None, "INVALID_PNG_SHA"
        if not isinstance(source_digest, str) or not SHA.fullmatch(source_digest):
            return None, "INVALID_DDS_SHA"
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 25000:
            return None, "MISSING_APPROVED_PROMPT"
        if not isinstance(rel, str) or not rel.endswith(".png"):
            return None, "INVALID_PNG_PATH"
        base = (root / "inputs").resolve()
        target = (base / rel).resolve()
        if not target.is_relative_to(base) or target.is_symlink() or not target.is_file():
            return None, "INVALID_PNG_PATH"
        if target.stat().st_size > 32 * 1024 * 1024:
            return None, "PNG_TOO_LARGE"
        data = target.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            return None, "PNG_SHA_MISMATCH"
        if len(data) < 45 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            return None, "INVALID_PNG"
        offset, seen_idat, seen_end = 8, False, False
        while offset + 12 <= len(data):
            size = struct.unpack_from(">I", data, offset)[0]
            end = offset + 12 + size
            if size > 32 * 1024 * 1024 or end > len(data):
                return None, "INVALID_PNG"
            kind = data[offset + 4:offset + 8]
            crc = struct.unpack_from(">I", data, end - 4)[0]
            if zlib.crc32(data[offset + 4:end - 4]) != crc:
                return None, "INVALID_PNG_CRC"
            if kind == b"IDAT":
                seen_idat = True
            if kind == b"IEND":
                seen_end = True
                if size != 0 or end != len(data):
                    return None, "INVALID_PNG"
                break
            offset = end
        if not seen_idat or not seen_end:
            return None, "INVALID_PNG"
        width, height = struct.unpack(">II", data[16:24])
        if not (1 <= width <= 8192 and 1 <= height <= 8192):
            return None, "INVALID_PNG_DIMENSIONS"
        if (root / "sent" / (role + "_" + task + ".json")).exists():
            return None, "ALREADY_SENT"
        return {
            "role": role, "task_id": task, "path": str(target),
            "png_sha256": digest, "source_dds_sha256": source_digest,
            "prompt": prompt, "dimensions": [width, height],
        }, None
    except (OSError, ValueError, UnicodeError, KeyError, TypeError, json.JSONDecodeError):
        return None, "INVALID_MANIFEST"


async def prepare_a_project_target(page, project_name, allow_saved_chat=False):
    """Require the intended A project or verified existing chat before upload."""
    from urllib.parse import urlsplit
    try:
        url=urlsplit(page.url)
        if url.scheme!="https" or url.hostname!="chatgpt.com":
            return "TARGET_ORIGIN_NOT_CHATGPT"
        if allow_saved_chat and "/c/" in url.path and "local-chatgpt" not in page.url:
            await page.locator('[role="textbox"][contenteditable="true"]').first.wait_for(state="visible",timeout=12000)
            return "A_PROJECT_COMPOSER_READY"
        if not project_name:
            return "A_PROJECT_NAME_MISSING"
        in_project="/g/" in url.path and url.path.endswith("/project")
        if in_project:
            try:
                await page.get_by_role("heading", name=project_name, exact=True).wait_for(
                    state="visible", timeout=20000)
            except Exception:
                in_project=False
        if not in_project:
            btn=page.get_by_role("button",name="New chat in "+project_name,exact=True)
            if await btn.count()!=1:
                return "A_PROJECT_NEW_CHAT_BUTTON_NOT_FOUND"
            await btn.dispatch_event("click")
            await page.wait_for_url("**/g/*/project",timeout=18000)
        try:
            await page.get_by_role("heading", name=project_name, exact=True).wait_for(
                state="visible", timeout=20000)
        except Exception:
            return "A_PROJECT_IDENTITY_NOT_VERIFIED"
        await page.locator('[role="textbox"][contenteditable="true"]').first.wait_for(state="visible",timeout=12000)
        return "A_PROJECT_COMPOSER_READY"
    except Exception:
        return "A_PROJECT_NAVIGATION_UNVERIFIED"


async def attach_png(page,binding):
    """Wait for a completed visible named file upload, not only a spinner."""
    filename=Path(binding["path"]).name
    try:
        await page.locator('[role="textbox"][contenteditable="true"]').first.wait_for(state="visible",timeout=12000)
        if not page.url.startswith("https://chatgpt.com/"):
            return "TARGET_ORIGIN_NOT_CHATGPT"
        prev=page.locator('button[aria-label="Remove '+filename+'"]')
        if await prev.count():
            await prev.first.dispatch_event("click")
            await page.wait_for_timeout(500)
        inp=page.locator('input[type="file"][aria-label="Attach files"]')
        if await inp.count()!=1:
            return "ATTACH_FILES_INPUT_NOT_FOUND"
        await inp.set_input_files(binding["path"],timeout=25000)
        await page.wait_for_function(
            """filename => {
             const visible=e=>!!e.getClientRects().length;
             const image=[...document.querySelectorAll('img[alt]')].some(e=>
                  visible(e) && e.alt===filename && e.complete && e.naturalWidth>0);
             const remove=[...document.querySelectorAll('button[aria-label]')].some(e=>
                  e.getAttribute('aria-label')==='Remove '+filename);
             const loading=[...document.querySelectorAll('[aria-label]')].some(e=>
                  e.getAttribute('aria-label')==='Uploading '+filename);
             return image && remove && !loading;
            }""",arg=filename,timeout=90000)
        return "ATTACHMENT_UPLOAD_COMPLETED"
    except Exception:
        return "ATTACHMENT_UPLOAD_NOT_VERIFIED"


async def verify_submission_receipt(page,task_id,filename):
    """Require a durable chat URL and a user message with the task ID and image."""
    try:
        await page.wait_for_function(
            """task => {
              if(location.hostname!=='chatgpt.com' ||
                 !location.pathname.includes('/c/') ||
                 location.href.includes('local-chatgpt'))return false;
              return [...document.querySelectorAll('[data-message-author-role="user"]')]
                 .some(row=>(row.innerText||'').includes('UPLOAD_TASK_ID='+task) &&
                   [...row.querySelectorAll('img')].some(img=>img.complete &&
                     img.naturalWidth>0 && !!img.src));
            }""",arg=task_id,timeout=45000)
        return "PERSISTED_CHAT_USER_MESSAGE_WITH_IMAGE_CONFIRMED"
    except Exception:
        return "SEND_UNVERIFIED"

def mark_sent(binding, root=ROOT, status="CHAT_MESSAGE_SENT_ATTACHMENT_UI_VERIFIED_NOT_IMAGEGEN_PASS"):
    """Prevent re-sending a stale source on later automatic schedules."""
    target = Path(root) / "sent" / (
        binding["role"] + "_" + binding["task_id"] + ".json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": binding["task_id"], "role": binding["role"],
        "png_sha256": binding["png_sha256"],
        "source_dds_sha256": binding["source_dds_sha256"],
        "status": status,
    }
    with target.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return str(target)