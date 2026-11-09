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
ASSISTANT_IMAGE_JS = r"""({task,english,korean,sha})=>{
  // The current ChatGPT Project UI uses data-markdown-text-tone and
  // data-chatgpt-search-unit-key (confirmed by the upload send receipt).
  // Older UIs expose data-message-author-role. Accept BOTH, and never search
  // user-uploaded reference images as candidate assistant outputs.
  if(location.hostname!=='chatgpt.com'||!location.pathname.includes('/c/'))
    return {status:'NOT_CHAT_CONVERSATION'};
  const roleSelector=[
    '[data-markdown-text-tone="user-message"]',
    '[data-markdown-text-tone="assistant"]',
    '[data-message-author-role="user"]',
    '[data-message-author-role="assistant"]',
    '[data-testid="conversation-turn-user"]',
    '[data-testid="conversation-turn-assistant"]'
  ].join(',');
  const candidates=[...document.querySelectorAll(roleSelector)];
  const isUser=n=>n.matches(
    '[data-markdown-text-tone="user-message"],[data-message-author-role="user"],[data-testid="conversation-turn-user"]'
  );
  const isAssistant=n=>n.matches(
    '[data-markdown-text-tone="assistant"],[data-message-author-role="assistant"],[data-testid="conversation-turn-assistant"]'
  );
  const scope=n=>n.closest('[data-chatgpt-search-unit-key]')||
    n.closest('[data-content-search-unit-key]')||
    n.closest('[data-turn-key]')||
    n;
  // Distinct chat turns; multiple Markdown paragraphs inside one turn should
  // be grouped without accidentally combining the user and assistant turns.
  const items=[];
  for(const node of candidates){
    const turn=scope(node), role=isUser(node)?'user':isAssistant(node)?'assistant':null;
    if(!role)continue;
    const prev=items[items.length-1];
    if(prev&&prev.turn===turn&&prev.role===role){
      if(!prev.parts.includes(node))prev.parts.push(node);
    } else items.push({turn,role,parts:[node]});
  }
  const users=items.filter(x=>x.role==='user');
  if(!users.length)return {status:'CHAT_USER_TURNS_NOT_RENDERED'};
  const visible=x=>x.parts.map(p=>p.innerText||p.textContent||'').join(' ').replace(/\s+/g,' ');
  const idMarker='UPLOAD_TASK_ID='+task;
  const byId=users.filter(x=>visible(x).includes(idMarker));
  if(byId.length>1)return {status:'TASK_MARKER_AMBIGUOUS'};
  let exact=byId[0],method='TASK_ID';
  if(!exact){
    // Some regenerated ChatGPT turns no longer expose the footer marker.
    // Accept ONLY the exact original English + Korean + DDS SHA in the same
    // individual USER turn, anchored to the previously verified chat URL.
    if(typeof english!=='string'||!english.trim()||
       typeof korean!=='string'||!korean.trim()||
       typeof sha!=='string'||!/^[0-9a-f]{64}$/.test(sha))
      return {status:'SOURCE_BINDING_REQUIRED'};
    const matches=users.filter(x=>{
      const content=visible(x);
      return content.includes('영문 원문: '+english) &&
        content.includes('한국어 번역: '+korean) &&
        content.includes('원본 DDS SHA: '+sha);
    });
    if(matches.length!==1)return {status:matches.length?
      'SOURCE_BOUND_USER_TURN_AMBIGUOUS':'SOURCE_BOUND_USER_TURN_MISSING'};
    exact=matches[0];method='SOURCE_TRIPLE';
  }
  const start=items.indexOf(exact);
  if(start<0)return {status:'USER_TURN_MISSING'};
  const replies=[];
  for(let i=start+1;i<items.length;i++){
    const row=items[i];
    if(row.role==='user')break;
    if(row.role==='assistant'&&!replies.includes(row.turn))replies.push(row.turn);
  }
  // ChatGPT ImageGen output can be its own tool/media turn with no
  // data-message-author-role="assistant" text node. The A/B send receipt
  // independently proves the exact user turn and ChatGPT conversation URL.
  // Search only explicitly generated-image elements in document order AFTER
  // this user turn and BEFORE the next distinct user turn.
  const generationSelector=[
    'button[aria-label^="Show generated image "] img',
    '[data-testid="generated-image-preview"] img',
    '[data-testid*="generated-image"] img',
    '[data-testid*="imagegen"] img',
    'img[alt^="Generated image"]',
    'img[alt^="generated image"]'
  ].join(',');
  const inReply=n=>replies.some(t=>t===n||t.contains?.(n));
  const anchor=exact.parts[exact.parts.length-1];
  const nextUser=users[users.indexOf(exact)+1];
  const nextAnchor=nextUser?nextUser.parts[0]:null;
  const isWithinBoundedReply=n=>{
    if(!(anchor.compareDocumentPosition(n)&4))return false;
    if(nextAnchor&&!(n.compareDocumentPosition(nextAnchor)&4))return false;
    // Explicitly reject any user message, even one containing imagegen-like
    // thumbnails or markup. This is an independent provenance boundary.
    const owner=n.closest?.(
      '[data-chatgpt-search-unit-key],[data-content-search-unit-key],'+
      '[data-turn-key],[data-message-author-role],[data-testid="conversation-turn-user"]'
    );
    if(owner&&(owner===exact.turn||
       owner.querySelector?.(
        '[data-markdown-text-tone="user-message"],'+
        '[data-message-author-role="user"],[data-testid="conversation-turn-user"]'
       )))return false;
    return !n.closest?.(
      '[data-message-author-role="user"],[data-testid="conversation-turn-user"]'
    );
  };
  // One generated preview can also have a carousel thumbnail. Favor a
  // carousel's selected/generated image only if it is the sole item.
  const carousel=[...new Set([...document.querySelectorAll(
    'button[aria-label^="Show generated image "] img'
  )].filter(isWithinBoundedReply))];
  if(carousel.length>1)return {status:'ASSISTANT_IMAGE_AMBIGUOUS'};
  let images=carousel;
  if(!images.length){
    const candidates=[...new Set([...document.querySelectorAll(
      generationSelector
    )].filter(isWithinBoundedReply))];
    if(candidates.length>1){
      const urls=[...new Set(candidates.map(n=>n.currentSrc||n.src))];
      if(urls.length>1)return {status:'ASSISTANT_IMAGE_AMBIGUOUS'};
    }
    images=candidates;
  }
  if(!images.length){
    // Non-sensitive numeric UI evidence differentiates missing assistant
    // responses from image-selector mismatch and visible login gates.
    // Never export user/assistant text, cookies, URLs or image contents here.
    const ui={
      assistant:Math.min(replies.length,9),
      generated:Math.min(document.querySelectorAll(generationSelector).length,9),
      user:Math.min(users.length,9),
      auth:document.querySelectorAll('input[type="password"]').length?1:0
    };
    // A confirmed failure message is not an in-progress image and must not
    // be silently reported as "assistant not ready". The text is inspected
    // only AFTER the SHA-bound user message, BEFORE the next user message,
    // and never saved/copied out to GitHub.
    const errorMessages=[
      'something went wrong while generating your image',
      'there was a problem generating your image',
      'we couldn\u2019t generate your image',
      'we could not generate your image',
      'image generation failed',
      '이미지를 생성하는 동안 문제가 발생',
      '이미지 생성 중 오류가 발생'
    ];
    const errors=[...document.querySelectorAll(
      'p,[role="alert"],[data-testid*="error"],[data-testid*="imagegen"]'
    )].filter(isWithinBoundedReply);
    if(errors.some(n=>{
      const t=(n.innerText||n.textContent||'').toLowerCase();
      return t.length<800&&errorMessages.some(e=>t.includes(e));
    }))return {status:'IMAGEGEN_FAILED_UI',ui};
    return {
      status:replies.length?
        'ASSISTANT_GENERATED_IMAGE_SELECTOR_MISSING':
        'ASSISTANT_GENERATED_IMAGE_NOT_RENDERED',
      ui
    };
  }
  const ready=images.filter(n=>n.complete&&n.naturalWidth>0&&n.naturalHeight>0);
  if(!ready.length)return {status:'ASSISTANT_IMAGE_LOADING'};
  const urls=[...new Set(ready.map(n=>n.currentSrc||n.src).filter(Boolean))];
  if(urls.length!==1)return {status:'ASSISTANT_IMAGE_AMBIGUOUS'};
  return {status:'ASSISTANT_IMAGE_SOURCE_VERIFIED',url:urls[0],
          width:ready[0].naturalWidth,height:ready[0].naturalHeight,
          match_method:method};
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


def save_candidate_evidence(root, role, task_id, png, dimensions, original_sha, match_method="TASK_ID"):
    if role not in ("A", "B") or not TASK_ID.fullmatch(task_id):
        raise ValueError("UNBOUND_ASSISTANT_CANDIDATE")
    if match_method not in ("TASK_ID", "SOURCE_TRIPLE"):
        raise ValueError("UNSUPPORTED_ASSISTANT_TURN_PROOF")
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
            "pairing": "ONE_VERIFIED_" + match_method + "_USER_TURN_TO_ONE_ASSISTANT_GENERATED_IMAGE",
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


async def rescue_single_image_candidate(page, task_id, role, root, binding=None):
    """Return (status, safe detail) for one assistant-generated output."""
    if not TASK_ID.fullmatch(task_id) or role not in ("A", "B"):
        raise ValueError("INVALID_ASSISTANT_TASK")
    binding = binding or {}
    if not isinstance(binding, dict):
        raise ValueError("INVALID_ASSISTANT_SOURCE_BINDING")
    params = {
        "task": task_id,
        "english": binding.get("english"),
        "korean": binding.get("korean"),
        "sha": binding.get("source_dds_sha256"),
    }
    try:
        result = await page.evaluate(ASSISTANT_IMAGE_JS, params)
    except Exception:
        return "WAIT_ASSISTANT_RESULT_UI", "RESULT_DOM_PROBE_EXCEPTION"
    if not isinstance(result, dict) or result.get("status") != "ASSISTANT_IMAGE_SOURCE_VERIFIED":
        status = (result or {}).get("status") if isinstance(result, dict) else None
        if status not in (
            "NOT_CHAT_CONVERSATION", "TASK_MARKER_AMBIGUOUS", "USER_TURN_MISSING",
            "CHAT_USER_TURNS_NOT_RENDERED", "SOURCE_BINDING_REQUIRED",
            "SOURCE_BOUND_USER_TURN_AMBIGUOUS", "SOURCE_BOUND_USER_TURN_MISSING",
            "ASSISTANT_TURN_NOT_READY", "ASSISTANT_GENERATED_IMAGE_SELECTOR_MISSING",
            "ASSISTANT_IMAGE_LOADING", "ASSISTANT_IMAGE_AMBIGUOUS",
            "ASSISTANT_GENERATED_IMAGE_NOT_RENDERED",
            "IMAGEGEN_FAILED_UI",
        ):
            status = "ASSISTANT_RESULT_NOT_VERIFIED"
        # Only append bounded, non-sensitive node counts when the real UI
        # supplied them; tests/older clients without a probe remain compatible.
        ui = result.get("ui") if isinstance(result, dict) else None
        if isinstance(ui, dict) and status in (
            "ASSISTANT_GENERATED_IMAGE_NOT_RENDERED",
            "ASSISTANT_GENERATED_IMAGE_SELECTOR_MISSING",
            "IMAGEGEN_FAILED_UI",
        ):
            try:
                nums = [int(ui.get(key)) for key in
                        ("assistant", "generated", "user", "auth")]
                if (all(0 <= n <= 9 for n in nums) and nums[-1] <= 1):
                    status += "_A%d_G%d_U%d_L%d" % tuple(nums)
            except (ValueError, TypeError, OverflowError):
                pass
        return "WAIT_ASSISTANT_RESULT_UI", status
    try:
        png, dims = await read_assistant_image(page, result.get("url"))
        sha = hashlib.sha256(png).hexdigest()
        saved = save_candidate_evidence(
            root, role, task_id, png, dims, sha,
            match_method=result.get("match_method", "TASK_ID"),
        )
        return saved, "ASSISTANT_ONLY_ONE_IMAGE_SHA_VERIFIED"
    except (ValueError, OSError, RuntimeError) as e:
        return "WAIT_ASSISTANT_RESULT_EXPORT", type(e).__name__ + "_" + str(e)[:90]
