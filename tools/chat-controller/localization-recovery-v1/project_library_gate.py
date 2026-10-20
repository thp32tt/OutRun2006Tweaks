"""Verify generated image bytes are stored in the existing ChatGPT project Library.

Do NOT create a separate Library folder: ChatGPT saves images in the project's
built-in Library folder. Fail closed on ambiguous, missing or mismatched images.

Only browser/UI inspection via the user's existing authorized Playwright session.
Does not send ChatGPT messages, alter the Library, or approve texture quality.
"""
import asyncio
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re

DEFAULT_PROJECT_LIBRARY = "아웃런 한글화 신규"
MAX_SCAN = max(25, min(1000, int(os.environ.get("OUTRUN_LIBRARY_MAX_SCAN", "500"))))
MAX_IMAGE_BYTES = 30_000_000

def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def expected_library_name():
    expected = os.environ.get("OUTRUN_AB_PROJECT_LIBRARY_NAME", DEFAULT_PROJECT_LIBRARY).strip()
    project = os.environ.get("OUTRUN_AB_PROJECT_NAME", DEFAULT_PROJECT_LIBRARY).strip()
    if not expected or expected != project:
        raise ValueError("PROJECT_LIBRARY_PROJECT_NAME_MISMATCH")
    return expected

def _hex64(s):
    return isinstance(s,str) and bool(re.fullmatch(r"[0-9a-f]{64}",s))


def _known_library_url(root, project):
    """Reuse a previously SHA-verified project Library folder route."""
    if root is None:
        return None
    evidence=Path(root)/"text_roi_batches"/"library_evidence"
    if not evidence.is_dir():
        return None
    candidates=sorted(evidence.glob("*.json"), key=lambda p:p.stat().st_mtime, reverse=True)
    for p in candidates[:40]:
        try:
            j=json.loads(p.read_text(encoding="utf-8"))
            url=j.get("library_folder_url")
            if (j.get("folder")==project and isinstance(url,str) and
                re.fullmatch(r"https://chatgpt\.com/library/d/[0-9a-zA-Z_-]+",url)):
                return url
        except Exception:
            continue
    return None


def _trusted_export_hashes(active, root):
    """Return SHA-bound generated candidate hashes from prior verified export.

    This is used after a container/browser restart when the original ChatGPT
    turn is no longer mounted in the restored persistent tab. It never trusts
    filenames alone: task, role, expected output names, file bytes and SHA256
    must all agree with the active queue record.
    """
    if root is None:
        return None
    root=Path(root).resolve()
    task=active.get("task_id")
    role=active.get("role")
    expected=active.get("count")
    items=active.get("items") or []
    if not isinstance(task,str) or role not in ("A","B") or not isinstance(expected,int):
        return None
    if len(items)!=expected:
        return None
    evidence=root/"text_roi_batches"/"export_evidence"/(task+".json")
    if not evidence.is_file() or evidence.is_symlink():
        return None
    try:
        doc=json.loads(evidence.read_text(encoding="utf-8"))
    except Exception:
        return None
    if (doc.get("task_id")!=task or doc.get("role")!=role or
        doc.get("status")!="UNAPPROVED_LOCAL_CANDIDATES_NOT_LIBRARY_PASS"):
        return None
    rows=doc.get("files")
    if not isinstance(rows,list) or len(rows)!=expected:
        return None
    by_name={r.get("name"):r for r in rows if isinstance(r,dict)}
    expected_names=[x.get("output_filename") for x in items]
    if len(by_name)!=expected or set(by_name)!=set(expected_names):
        return None
    hashes=[]
    base=root/"text_roi_batches"/"candidate_outputs"/role
    for name in expected_names:
        rec=by_name.get(name) or {}
        sha=rec.get("sha256")
        p=base/name
        if not _hex64(sha) or not p.is_file() or p.is_symlink():
            return None
        h=hashlib.sha256()
        with p.open("rb") as fh:
            for chunk in iter(lambda:fh.read(1<<20),b""):
                h.update(chunk)
        if h.hexdigest()!=sha:
            return None
        hashes.append(sha)
    if len(set(hashes))!=expected:
        return None
    return hashes

# Hash the exact generated ImageGen PNGs from the *specific* previous chat turn.
# One preview and N carousel selectors count as N images, not N+1.
GENERATED_PNG_HASHES_JS = r"""async ({task,expected})=>{
  if(location.hostname!=='chatgpt.com'||!location.pathname.includes('/c/'))
    return {error:'SOURCE_NOT_CHATGPT_CONVERSATION'};
  const user=[...document.querySelectorAll('[data-markdown-text-tone="user-message"]')]
    .find(el=>(el.innerText||'').includes('UPLOAD_TASK_ID='+task));
  const turn=user?.closest('[data-turn-key]');
  if(!turn)return {error:'SOURCE_TASK_TURN_MISSING'};
  const buttons=[...turn.querySelectorAll('button[aria-label^="Show generated image "]')];
  if(buttons.length!==expected)return {error:'SOURCE_GENERATED_IMAGE_COUNT_NOT_EXPECTED',count:buttons.length};
  const selectors=buttons.map(b=>{
    const m=(b.getAttribute('aria-label')||'').match(/^Show generated image ([1-9][0-9]*)$/);
    const img=b.querySelector('img');
    return m&&img?{index:Number(m[1]),src:img.currentSrc||img.src}:null;
  });
  if(selectors.some(x=>!x))return {error:'SOURCE_GENERATED_IMAGE_SELECTOR_INVALID'};
  selectors.sort((a,b)=>a.index-b.index);
  if(selectors.some((x,i)=>x.index!==i+1))return {error:'SOURCE_GENERATED_INDEX_NOT_SEQUENTIAL'};
  if(new Set(selectors.map(x=>x.src)).size!==expected)
    return {error:'SOURCE_GENERATED_IMAGE_DUPLICATE'};
  const out=[];
  for(const item of selectors){
    try{
      const response=await fetch(item.src);
      if(!response.ok)return{error:'SOURCE_GENERATED_BLOB_FETCH_FAILED'};
      const blob=await response.blob();
      if(blob.type!=='image/png'||blob.size<=100||blob.size>30000000)
        return{error:'SOURCE_GENERATED_IMAGE_NOT_PNG'};
      const digest=await crypto.subtle.digest('SHA-256',await blob.arrayBuffer());
      out.push({index:item.index,sha256:[...new Uint8Array(digest)]
        .map(x=>x.toString(16).padStart(2,'0')).join(''),bytes:blob.size});
    }catch(e){return{error:'SOURCE_GENERATED_BLOB_FETCH_EXCEPTION'};}
  }
  return {images:out,error:null};
}"""

LIBRARY_CARD_DIGEST_JS = r"""async card=>{
  const root=card.closest('[data-library-selection-id]');
  const id=root?.getAttribute('data-library-selection-id');
  const name=card.getAttribute('aria-label')||'';
  const img=card.querySelector('img[src]');
  const src=img?.currentSrc||img?.getAttribute('src');
  if(!/^libfile_[0-9a-zA-Z]+$/.test(id||'')||!src||
     !src.startsWith('https://chatgpt.com/api/library/files/'+id+'/content'))
     return {id,name,error:'INVALID_LIBRARY_CARD'};
  try{
    const r=await fetch(src,{cache:'no-store'});
    if(!r.ok)return{id,name,error:'LIBRARY_IMAGE_FETCH_HTTP_'+r.status};
    const blob=await r.blob();
    if(blob.type!=='image/png'||blob.size<=100||blob.size>30000000)
      return{id,name,error:'LIBRARY_IMAGE_NOT_PNG'};
    const hash=await crypto.subtle.digest('SHA-256',await blob.arrayBuffer());
    return {id,name,sha256:[...new Uint8Array(hash)]
      .map(x=>x.toString(16).padStart(2,'0')).join(''),bytes:blob.size};
  }catch(e){return{id,name,error:'LIBRARY_IMAGE_FETCH_EXCEPTION'};}
}"""

async def verify_project_library_images(page,active, root=None, max_scan=MAX_SCAN):
    """Return (evidence, error), without touching queue state or files.

    SHA256 equality to every generated PNG of this batch is mandatory.
    Old items with similar names, or previews from other chats, cannot pass.
    """
    expected=active["count"]
    if not isinstance(expected,int) or not 1<=expected<=5:
        return None,"BAD_EXPECTED_IMAGE_COUNT"
    try:
        project=expected_library_name()
        source_shas=_trusted_export_hashes(active,root)
        source_hash_method="verified_local_export_evidence"
        if source_shas is None:
            originals=await page.evaluate(GENERATED_PNG_HASHES_JS,
                                          {"task":active["task_id"],"expected":expected})
            if originals.get("error"):
                return None,originals["error"]
            images=originals.get("images",[])
            source_shas=[x.get("sha256") for x in images]
            source_hash_method="source_chat_generated_blob_sha256"
        if len(source_shas)!=expected or len(set(source_shas))!=expected or not all(map(_hex64,source_shas)):
            return None,"INVALID_SOURCE_IMAGE_HASHES"
    except Exception as exc:
        return None,"SOURCE_HASH_FAILED:"+str(exc)[:95]

    # A new disposable Library tab does not disturb either persistent A/B tab.
    folder_page=None
    try:
        folder_page=await page.context.new_page()
        known=_known_library_url(root,project)
        if known:
            # The project Library folder route is stable across batches and was
            # already proven by earlier exact SHA matches. Reuse it directly so
            # a slow responsive folder-card click cannot stall production.
            await folder_page.goto(known,wait_until="domcontentloaded",timeout=35000)
            await folder_page.wait_for_url(
                re.compile(r"^https://chatgpt\.com/library/d/[0-9a-zA-Z_-]+(?:[?].*)?$"),
                timeout=15000)
        else:
            await folder_page.goto("https://chatgpt.com/library?tab=folders",
                                   wait_until="domcontentloaded",timeout=35000)
            await folder_page.get_by_role("tab",name="Folders",exact=True).wait_for(
                state="visible",timeout=45000)
            # ChatGPT can render duplicate responsive copies of the same folder
            # card. Duplicate DOM nodes are presentation duplicates, not Library
            # identity ambiguity. Destination route + exact PNG SHA remain mandatory.
            located=folder_page.get_by_role("button",name=project,exact=True)
            await located.last.wait_for(state="visible",timeout=25000)
            await located.last.click(timeout=20000)
            await folder_page.wait_for_url(
                re.compile(r"^https://chatgpt\.com/library/d/[0-9a-zA-Z_-]+(?:[?].*)?$"),
                timeout=25000)
        library_url=folder_page.url.split("?")[0]
        if not re.fullmatch(r"https://chatgpt\.com/library/d/[0-9a-zA-Z_-]+",library_url):
            return None,"LIBRARY_URL_NOT_PROJECT_FOLDER"
        # Folder data might still be streaming after navigation; require cards.
        cards=folder_page.locator('[data-library-selection-id] button[aria-label]:has(img[src])')
        await cards.first.wait_for(state="visible",timeout=35000)
        seen=set()
        matched={}
        attempts=0
        failures=[]
        inspected=0
        idle=0
        while inspected < max_scan:
            card_count=await cards.count()
            if inspected >= card_count:
                # Library adds 20-article chunks on scrolling. A fixed initial
                # .count() silently misses older files still in this folder.
                await folder_page.mouse.move(900,500)
                await folder_page.mouse.wheel(0,1250)
                await asyncio.sleep(1.1)
                if await cards.count() <= inspected:
                    idle+=1
                    if idle>=3:break
                else:idle=0
                continue
            card=cards.nth(inspected)
            inspected+=1
            label=await card.get_attribute("aria-label")
            if not label or not label.lower().endswith(".png"):
                continue
            # Explicit scrolling triggers lazy image loading.
            await card.scroll_into_view_if_needed(timeout=7000)
            # Image lazy-load fetches may initially route to a HTML shell.
            # Decode means the real project PNG resource has become readable.
            try:
                img=card.locator("img[src]").first
                await asyncio.wait_for(img.evaluate("im=>im.decode()"), timeout=7)
            except Exception:
                pass
            rec=None
            for retry in range(4):
                rec=await card.evaluate(LIBRARY_CARD_DIGEST_JS)
                if rec.get("sha256"):
                    break
                await asyncio.sleep(.6*(retry+1))
            if not rec or not rec.get("sha256"):
                failures.append((label,rec.get("error") if rec else "NONE"))
                continue
            attempts+=1
            if rec["sha256"] in source_shas:
                if rec["sha256"] in matched or rec.get("id") in seen:
                    return None,"DUPLICATED_MATCHED_LIBRARY_ITEM"
                seen.add(rec["id"])
                matched[rec["sha256"]]=rec
                if len(matched)==expected:
                    break
        if len(matched)!=expected:
            return None,(f"PROJECT_LIBRARY_HASH_MATCH_INCOMPLETE:{len(matched)}/{expected}"
                         f":SCANNED={inspected}:LOAD_ERRORS={len(failures)}")
        ordered=[matched[sha] for sha in source_shas]
        evidence={
            "task_id":active["task_id"],
            "slot":active["role"],
            "folder":project,
            "folder_visible_label":project,
            "verification_method":"browser_content_sha256_match",
            "source_hash_method":source_hash_method,
            "verified_at":_now(),
            "library_folder_url":library_url,
            "library_item_ids":[x["id"] for x in ordered],
            "library_item_filenames":[x["name"] for x in ordered],
            "generated_image_sha256":source_shas,
            "library_content_sha256":[x["sha256"] for x in ordered],
            "match_status":"EXACT_GENERATED_LIBRARY_PNG_SHA256_MATCH",
            "dds_quality_status":"UNTESTED",
        }
        return evidence,None
    except Exception as exc:
        return None,"PROJECT_LIBRARY_PROBE_FAILED:"+str(exc)[:105]
    finally:
        if folder_page is not None:
            try:await folder_page.close()
            except Exception:pass