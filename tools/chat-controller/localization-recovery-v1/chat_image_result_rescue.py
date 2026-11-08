"""Strict assistant-only recovery of a single ChatGPT ImageGen output.

Used only after the original visual selector cannot prove an image result.
Never captures the user-uploaded English reference, screenshots, CSS background,
or unrelated images. No paid API and no unverified generated-image claims.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

from PIL import Image, UnidentifiedImageError

TASK_ID = re.compile(r"^HDRW-[AB]-[0-9a-f]{20}$")
MAX_IMAGE_BYTES = 30_000_000
MAX_PIXELS = 4096 * 4096
ALLOWED_IMAGE_HOSTS = ("chatgpt.com", "oaiusercontent.com", "oaistatic.com", "openai.com")

# Search ONLY in assistant turns following exactly one matching user turn.
# Deliberately exclude general <img> and user attachment previews.
ASSISTANT_IMAGE_JS = r"""(task)=>{
  if(location.hostname!=='chatgpt.com'||!location.pathname.includes('/c/'))
    return {status:'NOT_CHAT_CONVERSATION'};
  const marker='UPLOAD_TASK_ID='+task;
  const msgs=[...document.querySelectorAll(
    '[data-message-author-role="user"],[data-message-author-role="assistant"]'
  )];
  const matches=msgs.map((node,i)=>({node,i})).filter(({node})=>
     node.getAttribute('data-message-author-role')==='user' &&
     (node.innerText||node.textContent||'').includes(marker));
  if(matches.length!==1)return {status:matches.length?'TASK_MARKER_AMBIGUOUS':'USER_TURN_MISSING'};
  const after=msgs.slice(matches[0].i+1);
  const reply=[];
  for(const node of after){
    if(node.getAttribute('data-message-author-role')==='user')break;
    if(node.getAttribute('data-message-author-role')==='assistant')reply.push(node);
  }
  if(!reply.length)return {status:'ASSISTANT_TURN_NOT_READY'};
  const selector=[
    '[data-testid="generated-image-preview"] img',
    '[data-testid*="generated-image"] img',
    'img[alt^="Generated image"]',
    'img[alt^="generated image"]',
    'button[aria-label^="Show generated image "] img'
  ].join(',');
  const nodes=[...new Set(reply.flatMap(n=>[...n.querySelectorAll(selector)]))];
  if(!nodes.length)return {status:'ASSISTANT_GENERATED_IMAGE_SELECTOR_MISSING'};
  const ready=nodes.filter(n=>n.complete&&n.naturalWidth>0&&n.naturalHeight>0);
  if(!ready.length)return {status:'ASSISTANT_IMAGE_LOADING'};
  const urls=[...new Set(ready.map(n=>n.currentSrc||n.src).filter(Boolean))];
  if(urls.length!==1)return {status:'ASSISTANT_IMAGE_AMBIGUOUS',count:urls.length};
  return {status:'ASSISTANT_IMAGE_SOURCE_VERIFIED',url:urls[0],
          width:ready[0].naturalWidth,height:ready[0].naturalHeight};
}"""


def safe_image_url(source):
    if not isinstance(source, str) or len(source) > 8192:
        return False
    if source.startswith("blob:"):
        return source.startswith("blob:https://chatgpt.com/")
    if source.startswith("data:image/"):
        return len(source) <= 8192  # full data-URLs are handled separately below
    try:
        u = urlsplit(source)
    except ValueError:
        return False
    if u.scheme != "https" or u.username or u.password or not u.hostname:
        return False
    host = u.hostname.lower()
    return any(host == allowed or host.endswith("." + allowed)
               for allowed in ALLOWED_IMAGE_HOSTS)


def checked_image_bytes(raw):
    if not isinstance(raw, bytes) or not 100 <= len(raw) <= MAX_IMAGE_BYTES:
        raise ValueError("ASSISTANT_IMAGE_BYTES_UNSAFE")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if (image.width < 24 or image.height < 12 or
                    image.width * image.height > MAX_PIXELS):
                raise ValueError("ASSISTANT_IMAGE_DIMENSIONS_UNSAFE")
            image.load()
            rgba = image.convert("RGBA")
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as e:
        raise ValueError("ASSISTANT_IMAGE_DECODING_FAILED") from e
    out = io.BytesIO()
    rgba.save(out, format="PNG", optimize=True)
    return out.getvalue(), [rgba.width, rgba.height]


async def read_assistant_image(page, source):
    if not safe_image_url(source):
        raise ValueError("UNTRUSTED_GENERATED_IMAGE_URL")
    if source.startswith("data:image/"):
        # Reject huge inline blobs, never read arbitrary base64 from page text.
        raise ValueError("GENERATED_DATA_URL_NOT_SUPPORTED")
    try:
        encoded = await page.evaluate("""async url=>{
          const res=await fetch(url,{credentials:'include'});
          if(!res.ok)throw Error('IMAGE_FETCH_FAILED');
          const blob=await res.blob();
          if(blob.size<100||blob.size>30000000||!blob.type.startsWith('image/'))
            throw Error('IMAGE_BLOB_UNVERIFIED');
          return await new Promise((resolve,reject)=>{
            const reader=new FileReader();
            reader.onload=()=>resolve(reader.result);
            reader.onerror=()=>reject(Error('IMAGE_READ_FAILED'));
            reader.readAsDataURL(blob);
          });
        }""", source)
        if isinstance(encoded, str) and encoded.startswith("data:image/") and "," in encoded:
            raw = base64.b64decode(encoded.split(",", 1)[1], validate=True)
            return checked_image_bytes(raw)
    except Exception:
        pass
    # Cross-origin CDN URLs can be displayed in the page but refuse JS fetch.
    # Use the same browser context's authenticated request, with an exact
    # allowlisted HTTPS host, no redirects and never disclose the signed URL.
    if not source.startswith("https://"):
        raise ValueError("ASSISTANT_IMAGE_BLOB_FETCH_UNAVAILABLE")
    response = await page.context.request.get(source, timeout=25000, max_redirects=0)
    if response.status != 200:
        raise ValueError("ASSISTANT_IMAGE_CDN_HTTP_ERROR")
    content_type = (response.headers.get("content-type") or "").lower()
    if not content_type.startswith("image/"):
        raise ValueError("ASSISTANT_IMAGE_CDN_TYPE_MISMATCH")
    return checked_image_bytes(await response.body())


def save_candidate_evidence(root, role, task_id, png, dimensions, original_sha):
    if role not in ("A", "B") or not TASK_ID.fullmatch(task_id):
        raise ValueError("UNBOUND_ASSISTANT_CANDIDATE")
    output = Path(root) / "text_roi_batches" / "candidate_outputs" / role / (task_id + ".png")
    evidence = Path(root) / "text_roi_batches" / "export_evidence" / (task_id + ".json")
    digest = hashlib.sha256(png).hexdigest()
    if output.exists() or evidence.exists():
        # Existing bytes only count when both file AND written proof match.
        if not output.is_file() or not evidence.is_file() or output.is_symlink() or evidence.is_symlink():
            raise ValueError("INCOMPLETE_PRIOR_CANDIDATE")
        try:
            old = json.loads(evidence.read_text(encoding="utf-8"))
        except (ValueError, OSError) as e:
            raise ValueError("PRIOR_CANDIDATE_EVIDENCE_CORRUPT") from e
        files = old.get("files") or []
        if (old.get("task_id") != task_id or old.get("role") != role or
                len(files) != 1 or files[0].get("sha256") != digest or
                files[0].get("name") != task_id + ".png" or
                hashlib.sha256(output.read_bytes()).hexdigest() != digest):
            raise ValueError("PRIOR_CANDIDATE_SHA_CONFLICT")
        return "EXISTING_CANDIDATES_VERIFIED"
    output.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as f:
        f.write(png)
    record = {
        "task_id": task_id, "role": role,
        "status": "UNAPPROVED_LOCAL_CANDIDATES_NOT_LIBRARY_PASS",
        "method": "ASSISTANT_TURN_ONLY_GENERATED_IMAGE",
        "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "files": [{
            "name": task_id + ".png", "sha256": digest,
            "generated_dimensions": dimensions, "raw_image_sha256": original_sha,
            "status": "PENDING_INDEPENDENT_C1_QA",
            "pairing": "ONE_EXACT_USER_MARKER_TO_ONE_ASSISTANT_GENERATED_IMAGE",
            "chatgpt_library": "UNVERIFIED"
        }],
    }
    fd, temp = tempfile.mkstemp(prefix=".assistant-evidence-", dir=evidence.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as h:
            json.dump(record, h, ensure_ascii=False, sort_keys=True, indent=2)
            h.flush()
            os.fsync(h.fileno())
        os.replace(temp, evidence)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return "LOCAL_CANDIDATES_EXPORTED_UNAPPROVED"


async def rescue_single_image_candidate(page, task_id, role, root):
    """Return (status, safe detail) for one assistant-generated output."""
    if not TASK_ID.fullmatch(task_id) or role not in ("A", "B"):
        raise ValueError("INVALID_ASSISTANT_TASK")
    try:
        result = await page.evaluate(ASSISTANT_IMAGE_JS, task_id)
    except Exception:
        return "WAIT_ASSISTANT_RESULT_UI", "RESULT_DOM_PROBE_EXCEPTION"
    if not isinstance(result, dict) or result.get("status") != "ASSISTANT_IMAGE_SOURCE_VERIFIED":
        status = (result or {}).get("status") if isinstance(result, dict) else None
        if status not in (
            "NOT_CHAT_CONVERSATION", "TASK_MARKER_AMBIGUOUS", "USER_TURN_MISSING",
            "ASSISTANT_TURN_NOT_READY", "ASSISTANT_GENERATED_IMAGE_SELECTOR_MISSING",
            "ASSISTANT_IMAGE_LOADING", "ASSISTANT_IMAGE_AMBIGUOUS",
        ):
            status = "ASSISTANT_RESULT_NOT_VERIFIED"
        return "WAIT_ASSISTANT_RESULT_UI", status
    try:
        png, dims = await read_assistant_image(page, result.get("url"))
        sha = hashlib.sha256(png).hexdigest()
        saved = save_candidate_evidence(root, role, task_id, png, dims, sha)
        return saved, "ASSISTANT_ONLY_ONE_IMAGE_SHA_VERIFIED"
    except (ValueError, OSError, RuntimeError) as e:
        return "WAIT_ASSISTANT_RESULT_EXPORT", type(e).__name__ + "_" + str(e)[:90]
