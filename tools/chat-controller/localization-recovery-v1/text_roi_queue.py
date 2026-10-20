"""A/B HD PNG ImageGen queue: five distinct sources per fresh-chat 10-minute slot.

A owns original mapping ordinals 1..500; B owns 501..986. Never re-index
after quarantining a corrupt file. This queue does not call a paid API.

A batch is NOT complete until:
  1. the chat turn is confirmed with every source attachment,
  2. exactly the same number of distinct assistant ImageGen images are visible,
  3. a positive ChatGPT Library folder 'outrun_kor' verification is recorded.
Downloaded _k.png files are unapproved candidates until independent pixel QA.
"""
import base64
import csv
import datetime as dt
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import re

try:
    from app.tile_batch_queue import _csv, _sha_png, _atomic_json
    from app.tile_orientation_policy import resolve_upright_source
except ImportError:
    from tile_batch_queue import _csv, _sha_png, _atomic_json
    from tile_orientation_policy import resolve_upright_source

SOURCE_DIR = "text_roi_batches/inputs"
STATE_DIR = "text_roi_batches"
LIBRARY_FOLDER = "아웃런 한글화 신규"
QUARANTINED = ""
RANGES = {"A": (1, 99999), "B": (1, 99999)}
SLOTS = {"A": (0, 10, 20, 30, 40, 50), "B": (5, 15, 25, 35, 45, 55)}
SIZE = 5
MAX_ROLLING_UPLOADS = 75  # Account upload cap may be stricter.

def state_path(root, role):
    return Path(root) / STATE_DIR / (role + "_state.json")

def _now():
    return dt.datetime.now(dt.timezone.utc)

def _read_sources(root):
    manifest = Path(root) / "text_roi_batches" / "production_manifest.json"
    if not manifest.is_file() or manifest.is_symlink():
        raise ValueError("ROI_MANIFEST_NOT_STAGED")
    if manifest.stat().st_size > 3_000_000:
        raise ValueError("ROI_MANIFEST_TOO_LARGE")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema") != "outrun-text-roi-production-v1" or not isinstance(data.get("items"), list):
        raise ValueError("ROI_MANIFEST_INVALID_SCHEMA")
    groups = {role: [] for role in RANGES}
    ids = set()
    paths = set()
    for e in data["items"]:
        if not isinstance(e, dict):
            raise ValueError("INVALID_ROI_ENTRY")
        ident = e.get("id")
        if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_-]{4,96}", ident) or ident in ids:
            raise ValueError("ROI_ID_DUPLICATE_OR_INVALID")
        ids.add(ident)
        if e.get("status") != "ROI_APPROVED_FOR_IMAGEGEN":
            continue
        role = e.get("role")
        if role not in groups:
            raise ValueError("ROI_UNKNOWN_ROLE")
        png = e.get("imagegen_input_png")
        if not isinstance(png, str) or not png.endswith(".png") or png in paths:
            raise ValueError("ROI_INPUT_DUPLICATE_OR_INVALID")
        paths.add(png)
        for field in ("english", "korean", "imagegen_input_sha256", "source_dds_sha256",
                      "source_png_sha256", "source_dds_path"):
            if not isinstance(e.get(field), str) or not e[field]:
                raise ValueError("ROI_MISSING_PROOF:" + ident + ":" + field)
        if e["english"] == e["korean"] or not re.fullmatch("[0-9a-f]{64}", e["imagegen_input_sha256"]) or not re.fullmatch("[0-9a-f]{64}", e["source_dds_sha256"]) or not re.fullmatch("[0-9a-f]{64}", e["source_png_sha256"]):
            raise ValueError("ROI_INVALID_TRANSLATION_OR_SHA")
        if e.get("source_provenance") not in ("DIRECT_FULL_HD_PNG", "DDS_PIXEL_VERIFIED_FULL_SOURCE", "SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG"):
            raise ValueError("ROI_UNVERIFIED_FULL_SOURCE:" + ident)
        bbox = e.get("bbox_xyxy")
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(type(v) is int for v in bbox) and
                bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] > bbox[0] and bbox[3] > bbox[1]):
            raise ValueError("ROI_INVALID_SOURCE_BBOX")
        if e.get("alpha_crop_margin_checked") is not True:
            raise ValueError("ROI_CROP_EDGE_NOT_VERIFIED")
        groups[role].append(e)
    return groups, None, None


def _state(root, role):
    if role not in RANGES:
        raise ValueError("UNKNOWN_SLOT")
    path = state_path(root, role)
    if not path.exists():
        low, high = RANGES[role]
        state = {
            "version": 3, "role": role, "range": [low, high],
            "next_ordinal": low, "active": None,
            "completed_files": 0, "completed_batches": 0,
            "quarantined": [], "status": "READY",
        }
        _atomic_json(path, state)
    else:
        state = json.loads(path.read_text(encoding="utf-8"))
    low, high = RANGES[role]
    if state.get("version") != 3 or state.get("role") != role or state.get("range") != [low, high]:
        raise ValueError("SLOT_STATE_CONTRACT_MISMATCH")
    if not (low <= state["next_ordinal"] <= high + 1):
        raise ValueError("SLOT_STATE_RANGE_INVALID")
    return state

def _count_recent(root):
    now = _now()
    count = 0
    for path in (Path(root) / "sent").glob("*_OUTRUN-AB-*.json"):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
            when = dt.datetime.fromisoformat(rec["submitted_at"].replace("Z", "+00:00"))
            if when.tzinfo and dt.timedelta(0) <= now - when < dt.timedelta(hours=3):
                count += max(1, len(rec.get("tiles", [])))
        except (OSError, KeyError, ValueError, TypeError):
            continue
    return count

def _filemap(source_row, ordinal, src, original):
    from PIL import Image
    p = Path(src).resolve()
    filename = source_row["imagegen_input_png"]
    if Path(filename).name != filename or not re.fullmatch(r"[A-Za-z0-9_.-]+\.png", filename):
        raise ValueError("ROI_UNSAFE_IMAGE_FILENAME")
    srcpath = p / filename
    if not srcpath.is_file() or srcpath.is_symlink() or not srcpath.resolve().is_relative_to(p):
        raise ValueError("ROI_IMAGE_MISSING")
    raw = srcpath.read_bytes()
    if hashlib.sha256(raw).hexdigest() != source_row["imagegen_input_sha256"]:
        raise ValueError("ROI_IMAGE_SHA_MISMATCH")
    if len(raw) > 32_000_000:
        raise ValueError("ROI_IMAGE_TOO_LARGE")
    with Image.open(srcpath) as im:
        if im.format != "PNG" or im.mode != "RGBA" or not (8 <= im.width <= 2048 and 8 <= im.height <= 2048):
            raise ValueError("ROI_INVALID_RGBA_OR_SIZE")
        w,h=im.size
    return {
        "ordinal": ordinal, "filename": filename,
        "output_filename": filename[:-4] + "_k.png", "path": str(srcpath),
        "sha256": source_row["imagegen_input_sha256"],
        "source_dds_sha256": source_row["source_dds_sha256"],
        "source_png_sha256": source_row["source_png_sha256"],
        "source_dds_path": source_row["source_dds_path"],
        "working_orientation": "READABLE_UPRIGHT",
        "width": w, "height": h,
        "queue_indexes": source_row.get("queue_index", ""),
        "x": source_row["bbox_xyxy"][0], "y": source_row["bbox_xyxy"][1],
        "english": source_row["english"], "korean": source_row["korean"],
        "region_id": source_row["id"],
    }


def _prompt(role, batch_id, tiles, translations):
    lines = [
        "@Create image — OutRun 2006 HD UI 문구별 투명 PNG 한글화",
        f"RUN_SLOT={role}; BATCH_ID={batch_id}; BATCH_COUNT={len(tiles)}; LIBRARY_FOLDER={LIBRARY_FOLDER}",
        "입력 이미지는 검증된 원본 HD 전체 이미지에서 추출한 서로 독립된 한 문구 ROI입니다.",
        f"입력 {len(tiles)}개 → 투명 RGBA 한글 글자/외곽선/그림자 결과 {len(tiles)}개, 각각 완전히 분리하여 생성하세요.",
        f"중요: 이미지 생성 도구 호출의 출력 개수(n)를 반드시 BATCH_COUNT={len(tiles)}로 설정하세요. 결과 이미지 파일은 정확히 {len(tiles)}개여야 합니다.",
        f"한 장만 생성하거나 한 장 안에 {len(tiles)}개를 합치는 것은 실패입니다. 입력 1개당 독립 출력 1개씩 총 {len(tiles)}장을 생성하세요.",
        "원문 문구의 채움, 기울기 방향, 외곽선, 광택과 그림자를 가능한 보존하면서 표시된 한국어 정확한 텍스트만 생성하세요.",
        "결과에 영문 원문, 다른 이미지의 글자, 차량, 배경, 버튼/아이콘, 합본·콜라주, 구석에 설명/번호를 넣지 마세요.",
        "글자와 그림자는 PNG 가장자리에서 잘리지 않으며, 글자 사이 충돌/가짜 글자가 없어야 합니다.",
        "한글 이미지 개수와 입력 파일 순서/개별 대응을 보존하세요.",
        f"기존 프로젝트 '{LIBRARY_FOLDER}'의 라이브러리에 각각 실제로 저장하고, 확인 없는 저장 성공 주장은 하지 마세요.",
        "영문→승인 한글 대상:",
    ]
    for i,item in enumerate(tiles,1):
        lines.append(f"[{i}/{len(tiles)}] {item['filename']} : {item['english']} → {item['korean']}; {item['width']}×{item['height']} px; 출력 {item['output_filename']}")
    lines.append("전송과 결과 검증은 각 PNG 실제 첨부·생성물 수량·저장 SHA 증빙이 필요합니다. 게임 DDS/실게임 PASS를 주장하지 마세요.")
    prompt="\n".join(lines)
    if len(prompt) > 26000:
        raise ValueError("ROI_PROMPT_TOO_LONG")
    return prompt


def next_binding(role, root="/data/imagegen"):
    root=Path(root).resolve()
    if role not in RANGES:
        return None,"INVALID_SLOT"
    if os.getenv("OUTRUN_AB_TEXT_ROI_QUEUE","false").lower() != "true":
        return None,"ROI_QUEUE_DISABLED"
    try:
        groups,_,_= _read_sources(root)
        rows=groups[role]
        st=_state(root,role)
        old=st.get("active")
        if old and old["status"] != "STAGED":
            return None,"BATCH_AWAITING_RESULT_AND_LIBRARY:"+old["task_id"]
        if not old and st["next_ordinal"]>len(rows):
            return None,"ROI_ROLE_QUEUE_EMPTY_OR_FINISHED"
        if not old and _count_recent(root) >= MAX_ROLLING_UPLOADS:
            return None,"SHARED_ROLLING_UPLOAD_QUOTA_HOLD"
        selected=[]
        if old:
            ordinals=old["ordinals"]
            after=old["next_ordinal_after"]
            task=old["task_id"]
            for o in ordinals:
                if o < 1 or o > len(rows) or rows[o-1]["id"] != old["items"][len(selected)]["region_id"]:
                    raise ValueError("STAGED_ROI_QUEUE_CHANGED")
                selected.append(_filemap(rows[o-1],o,root/SOURCE_DIR,None))
        else:
            first=st["next_ordinal"]
            allowed=min(SIZE,MAX_ROLLING_UPLOADS-_count_recent(root))
            for idx in range(first,min(len(rows),first+allowed-1)+1):
                selected.append(_filemap(rows[idx-1],idx,root/SOURCE_DIR,None))
            if not selected:
                return None,"SHARED_ROLLING_UPLOAD_QUOTA_HOLD"
            ordinals=[x["ordinal"] for x in selected]
            after=ordinals[-1]+1
            task=f"OUTRUN-ROI-{role}-{st['completed_batches']+1:04d}-{sha_indices(selected)}"
        prompt=_prompt(role,task,selected,None)
        if not old:
            active={"task_id":task,"role":role,"ordinals":ordinals,
                    "next_ordinal_after":after,"count":len(selected),
                    "items":[{k:v for k,v in item.items() if k!="path"} for item in selected],
                    "created_at":_now().isoformat(),"status":"STAGED","source_chat_url":None}
            st["active"]=active
            st["status"]="STAGED"
            _atomic_json(state_path(root,role),st)
        return {"role":role,"task_id":task,"path":selected[0]["path"],
                "paths":[x["path"] for x in selected],
                "png_sha256":selected[0]["sha256"],"source_dds_sha256":selected[0]["source_dds_sha256"],
                "prompt":prompt,"items":selected,
                "tiles":[{"filename":x["filename"],"sha256":x["sha256"],"ordinal":x["ordinal"],"output_filename":x["output_filename"]} for x in selected],
                "expected_images":len(selected),"library_folder":LIBRARY_FOLDER},None
    except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
        return None,"ROI_QUEUE_INPUT_ERROR:"+str(exc)[:150]

def sha_indices(items):
    return hashlib.sha256(("|".join(x["region_id"]+":"+x["sha256"] for x in items)).encode()).hexdigest()[:8].upper()


def stage_submission(role, task_id, root="/data/imagegen"):
    root = Path(root)
    st = _state(root, role)
    active = st["active"]
    if not active or active["task_id"] != task_id:
        return "MISSING_ACTIVE_TASK"
    if active["status"] != "STAGED":
        return "SUBMISSION_ALREADY_ATTEMPTED"
    active["status"] = "SUBMITTING"
    st["status"] = "SUBMITTING"
    _atomic_json(state_path(root, role), st)
    return "SUBMITTING"

def rollback_submission(role, task_id, reason, root="/data/imagegen"):
    """Return a definitely-unsent active task to STAGED.

    This is allowed only before any persisted sent receipt exists. It prevents a
    composer/tool-selection failure from leaving the queue permanently stuck in
    SUBMITTING while preserving the same task id and source ordinals.
    """
    root=Path(root)
    st=_state(root,role)
    active=st.get("active")
    if not active or active.get("task_id")!=task_id:
        return "STATE_TASK_MISMATCH"
    if active.get("status")!="SUBMITTING":
        return "ROLLBACK_STATE_NOT_SUBMITTING"
    receipt=root/"sent"/(role+"_"+task_id+".json")
    if receipt.exists():
        return "ROLLBACK_BLOCKED_SENT_RECEIPT_EXISTS"
    if not isinstance(reason,str) or not reason or len(reason)>180:
        return "ROLLBACK_REASON_INVALID"
    active["status"]="STAGED"
    active["last_presend_failure"]=reason
    active["last_presend_failure_at"]=_now().isoformat()
    active["presend_retry_count"]=int(active.get("presend_retry_count",0))+1
    st["status"]="STAGED"
    _atomic_json(state_path(root,role),st)
    return "ROLLED_BACK_TO_STAGED"


def record_chat_url(role, task_id, url, root="/data/imagegen"):
    if not re.fullmatch(r"https://chatgpt\.com/(?:g/[^?#]+/)?c/[a-zA-Z0-9-]+",url):
        return "CHAT_URL_UNVERIFIED"
    st = _state(root,role)
    active=st["active"]
    if not active or active["task_id"] != task_id:
        return "STATE_TASK_MISMATCH"
    active["source_chat_url"] = url
    st["status"] = "SENT_AWAITING_GENERATED_IMAGES"
    _atomic_json(state_path(root,role),st)
    return "URL_RECORDED"

def _library_evidence_path(root, task):
    return Path(root) / STATE_DIR / "library_evidence" / (task + ".json")


def _retry_same_five(st, active, root, reason, observed=None):
    """Quarantine an ambiguous/unsaved five-image turn and restage identical inputs.

    Ordinals never advance. Any exported candidate bytes are SHA-verified before
    being moved out of the active candidate namespace so the retry cannot
    accidentally overwrite or reuse them.
    """
    if active.get("count") != 5:
        return False, "RETRY_REQUIRES_FIVE_IMAGE_BATCH"
    retry=int(active.get("retry_count",0))
    if retry >= 2:
        return False, "FIVE_IMAGE_RETRY_LIMIT_REACHED:"+reason
    task=active["task_id"]
    qroot=Path(root)/STATE_DIR/"quarantine"/task
    qroot.mkdir(parents=True,exist_ok=True)

    export=Path(root)/STATE_DIR/"export_evidence"/(task+".json")
    if export.exists():
        if export.is_symlink():
            return False,"RETRY_EXPORT_EVIDENCE_SYMLINK"
        try:
            doc=json.loads(export.read_text(encoding="utf-8"))
        except Exception:
            return False,"RETRY_EXPORT_EVIDENCE_INVALID"
        rows=doc.get("files")
        if doc.get("task_id")!=task or not isinstance(rows,list) or len(rows)!=5:
            return False,"RETRY_EXPORT_EVIDENCE_BINDING_MISMATCH"
        outdir=Path(root)/STATE_DIR/"candidate_outputs"/active["role"]
        archived=qroot/"candidate_outputs"
        archived.mkdir(exist_ok=True)
        for row in rows:
            name=row.get("name")
            sha=row.get("sha256")
            if (not isinstance(name,str) or Path(name).name!=name or
                not isinstance(sha,str) or not re.fullmatch(r"[0-9a-f]{64}",sha)):
                return False,"RETRY_CANDIDATE_METADATA_INVALID"
            src=outdir/name
            if not src.is_file() or src.is_symlink():
                return False,"RETRY_CANDIDATE_MISSING"
            if hashlib.sha256(src.read_bytes()).hexdigest()!=sha:
                return False,"RETRY_CANDIDATE_SHA_CHANGED"
        for row in rows:
            src=outdir/row["name"]
            os.replace(src,archived/row["name"])
        os.replace(export,qroot/"export_evidence.json")

    generated=Path(root)/STATE_DIR/"generated_visible"/(task+".json")
    if generated.exists() and not generated.is_symlink():
        os.replace(generated,qroot/"generated_visible.json")
    library=_library_evidence_path(root,task)
    if library.exists() and not library.is_symlink():
        os.replace(library,qroot/"library_evidence.json")

    failed=dict(active)
    failed["status"]="QUARANTINED_FOR_SAME_FIVE_RETRY"
    failed["retry_reason"]=reason
    failed["observed_generated_images"]=observed
    failed["quarantined_at"]=_now().isoformat()
    st.setdefault("quarantined",[]).append(failed)

    base_task=re.sub(r"-R[0-9]+$","",task)
    replacement=dict(active)
    replacement["task_id"]=base_task+f"-R{retry+1}"
    replacement["retry_count"]=retry+1
    replacement["retry_of"]=task
    replacement["status"]="STAGED"
    replacement["source_chat_url"]=None
    replacement["created_at"]=_now().isoformat()
    st["active"]=replacement
    st["status"]="STAGED_RETRY_EXACT_FIVE_OUTPUTS"
    _atomic_json(state_path(root,active["role"]),st)
    return True,"FIVE_IMAGE_BATCH_RETRY_STAGED"

def _local_export_confirmed(root, active):
    """Require exact locally persisted generated PNG bytes before queue advance.

    Library UI persistence is supplemental. Production may advance only when the
    active task/role/count, expected output filenames, candidate bytes and SHA256
    all match the export evidence created from the verified five-image turn.
    """
    root=Path(root).resolve()
    task=active.get("task_id")
    role=active.get("role")
    expected=active.get("count")
    items=active.get("items") or []
    if role not in ("A","B") or not isinstance(task,str) or not isinstance(expected,int):
        return None,"LOCAL_EXPORT_ACTIVE_BINDING_INVALID"
    if len(items)!=expected:
        return None,"LOCAL_EXPORT_ITEM_COUNT_INVALID"
    ep=root/STATE_DIR/"export_evidence"/(task+".json")
    if not ep.is_file() or ep.is_symlink():
        return None,"LOCAL_EXPORT_EVIDENCE_MISSING"
    try:
        doc=json.loads(ep.read_text(encoding="utf-8"))
    except Exception:
        return None,"LOCAL_EXPORT_EVIDENCE_INVALID"
    if (doc.get("task_id")!=task or doc.get("role")!=role or
        doc.get("status")!="UNAPPROVED_LOCAL_CANDIDATES_NOT_LIBRARY_PASS"):
        return None,"LOCAL_EXPORT_EVIDENCE_BINDING_MISMATCH"
    rows=doc.get("files")
    if not isinstance(rows,list) or len(rows)!=expected:
        return None,"LOCAL_EXPORT_FILE_COUNT_INVALID"
    by_name={r.get("name"):r for r in rows if isinstance(r,dict)}
    names=[x.get("output_filename") for x in items]
    if len(by_name)!=expected or set(by_name)!=set(names):
        return None,"LOCAL_EXPORT_FILENAME_SET_MISMATCH"
    outdir=root/STATE_DIR/"candidate_outputs"/role
    hashes=[]
    statuses=[]
    for name in names:
        row=by_name.get(name) or {}
        sha=row.get("sha256")
        p=outdir/name
        if not isinstance(sha,str) or not re.fullmatch(r"[0-9a-f]{64}",sha):
            return None,"LOCAL_EXPORT_SHA_INVALID"
        if not p.is_file() or p.is_symlink():
            return None,"LOCAL_EXPORT_FILE_MISSING"
        actual=hashlib.sha256(p.read_bytes()).hexdigest()
        if actual!=sha:
            return None,"LOCAL_EXPORT_SHA_CHANGED"
        hashes.append(sha)
        statuses.append(row.get("status"))
    if len(set(hashes))!=expected:
        return None,"LOCAL_EXPORT_DUPLICATE_SHA"
    return {
        "task_id":task,"role":role,"count":expected,
        "output_filenames":names,"sha256":hashes,
        "candidate_statuses":statuses,
        "verification_method":"local_candidate_file_sha256_recheck",
        "library_status":"PENDING_NONBLOCKING",
        "verified_at":_now().isoformat(),
        "qa_status":"PENDING_C1",
        "dds_status":"UNTESTED",
    },None


def _local_completion_path(root, task):
    return Path(root)/STATE_DIR/"local_completion"/(task+".json")


def _library_confirmed(root, active):
    """Read *content-hash-matched* existing project Library proof.

    Naming or text saying 'saved' cannot substitute for actual PNG hash matching
    between the finished ChatGPT turn and N separately stored project files.
    """
    path=_library_evidence_path(root,active["task_id"])
    if not path.is_file():
        return False,"PROJECT_LIBRARY_NOT_VERIFIED"
    try:
        record=json.loads(path.read_text(encoding="utf-8"))
        ids=record.get("library_item_ids")
        source_shas=record.get("generated_image_sha256")
        saved_shas=record.get("library_content_sha256")
        count=active["count"]
        if (
            record.get("task_id")!=active["task_id"] or
            record.get("slot")!=active["role"] or
            record.get("folder")!=LIBRARY_FOLDER or
            record.get("folder_visible_label")!=LIBRARY_FOLDER or
            record.get("verification_method")!="browser_content_sha256_match" or
            record.get("match_status")!="EXACT_GENERATED_LIBRARY_PNG_SHA256_MATCH" or
            not isinstance(record.get("verified_at"),str) or
            not isinstance(ids,list) or len(ids)!=count or
            len(set(ids))!=count or not all(isinstance(x,str) and
                                            re.fullmatch(r"libfile_[a-zA-Z0-9]+",x) for x in ids) or
            not isinstance(source_shas,list) or len(source_shas)!=count or
            not isinstance(saved_shas,list) or len(saved_shas)!=count or
            len(set(source_shas))!=count or source_shas!=saved_shas or
            not all(isinstance(x,str) and re.fullmatch(r"[0-9a-f]{64}",x) for x in source_shas) or
            not isinstance(record.get("library_folder_url"),str) or
            not re.fullmatch(r"https://chatgpt\.com/library/d/[0-9a-zA-Z_-]+",
                             record["library_folder_url"])
        ):
            return False,"PROJECT_LIBRARY_EVIDENCE_INCOMPLETE"
        return True,"PROJECT_LIBRARY_IMAGE_HASHES_CONFIRMED"
    except (OSError,ValueError,TypeError):
        return False,"PROJECT_LIBRARY_EVIDENCE_INVALID"


async def export_unapproved_k_candidates(page, active, root):
    """Copy generated browser images into deterministic _k.png local filenames.

    Browser preview order is NOT guaranteed to correspond to source order:
    provenance is recorded as UNVERIFIED, never mark DDS or Library PASS.
    """
    from PIL import Image

    expected=active["count"]
    output_dir=Path(root)/STATE_DIR/"candidate_outputs"/active["role"]
    evidence=Path(root)/STATE_DIR/"export_evidence"/(active["task_id"]+".json")
    if evidence.exists():
        prev=json.loads(evidence.read_text(encoding="utf-8"))
        if prev.get("task_id")!=active["task_id"] or len(prev.get("files",[]))!=expected:
            raise ValueError("EXISTING_CANDIDATE_PROVENANCE_CONFLICT")
        for row in prev["files"]:
            target=output_dir/row["name"]
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=row["sha256"]:
                raise ValueError("EXISTING_CANDIDATE_HASH_CHANGED")
        return "EXISTING_CANDIDATES_VERIFIED"
    entries=await page.evaluate(r"""task=>{
      const text=[...document.querySelectorAll('[data-markdown-text-tone="user-message"]')]
       .find(n=>(n.innerText||'').includes('UPLOAD_TASK_ID='+task));
      const turn=text?.closest('[data-turn-key]');
      if(!turn)return[];
      // ChatGPT renders N generated images as ONE large preview plus N image
      // selector buttons. The button thumbnail blobs contain the distinct
      // full-resolution images; never count the preview itself as a second image.
      const selectors=[...turn.querySelectorAll('button[aria-label^="Show generated image "]')];
      if(selectors.length){
        const listed=selectors.map(button=>{
          const label=button.getAttribute('aria-label')||'';
          const m=label.match(/^Show generated image ([1-9][0-9]*)$/);
          const im=button.querySelector('img');
          return m&&im?{index:Number(m[1]),src:im.currentSrc||im.src,
                         width:im.naturalWidth,height:im.naturalHeight}:null;
        });
        if(listed.some(item=>!item))return[];
        listed.sort((a,b)=>a.index-b.index);
        if(listed.some((it,i)=>it.index!==i+1))return[];
        return listed;
      }
      return [...turn.querySelectorAll('[data-testid="generated-image-preview"] img[alt^="Generated image"]')]
       .filter(x=>x.complete&&x.naturalWidth>0&&x.naturalHeight>0)
       .map((x,i)=>({index:i+1,src:x.currentSrc||x.src,width:x.naturalWidth,height:x.naturalHeight}));
    }""",active["task_id"])
    sources=[e["src"] for e in entries]
    if len(sources)!=expected or len(set(sources))!=expected:
        raise ValueError("WRONG_GENERATED_IMAGE_COUNT")
    files=[]
    pending=[]
    for idx,entry in enumerate(entries):
        raw=await page.evaluate("""async uri=>{
         const response=await fetch(uri);
         if(!response.ok)throw Error('BLOB_FETCH_NOT_OK');
         const blob=await response.blob();
         if(blob.size>30000000)throw Error('BLOB_TOO_LARGE');
         return await new Promise((resolve,reject)=>{
          const r=new FileReader();r.onload=()=>resolve(r.result);
          r.onerror=()=>reject(Error('BLOB_READ_FAILED'));r.readAsDataURL(blob);
         });
        }""",entry["src"])
        if not isinstance(raw,str) or not raw.startswith("data:image/") or "," not in raw:
            raise ValueError("BLOB_IS_NOT_IMAGE")
        image_data=base64.b64decode(raw.split(",",1)[1],validate=True)
        if len(image_data)>30_000_000:
            raise ValueError("BLOB_PAYLOAD_TOO_LARGE")
        with Image.open(BytesIO(image_data)) as parsed:
            parsed.load()
            before_mode=parsed.mode
            before_size=parsed.size
            image=parsed.convert("RGBA")
        out=BytesIO()
        image.save(out,format="PNG")
        binary=out.getvalue()
        item=active["items"][idx]
        name=item["output_filename"]
        report={
            "name":name,"sha256":hashlib.sha256(binary).hexdigest(),
            "source_ordinal":item["ordinal"],
            "source_file":item["filename"],"generated_dimensions":list(before_size),
            "original_dimensions":[item["width"],item["height"]],
            "original_generated_mode":before_mode,
            "status":"REWORK_DIMENSIONS" if before_size!=(item["width"],item["height"]) else "PENDING_PIXEL_QA",
            "orientation":"UPRIGHT_READABLE",
            "pairing":"OUTPUT_ORDER_ONLY_NOT_VISUALLY_VERIFIED",
            "chatgpt_library":"UNVERIFIED",
        }
        pending.append((name,binary))
        files.append(report)
    output_dir.mkdir(parents=True,exist_ok=True)
    # Keep existing candidates immutable. Never overwrite prior outputs.
    if any((output_dir/name).exists() for name,_ in pending):
        raise ValueError("UNTRACKED_PRIOR_CANDIDATE_EXISTS")
    for name,binary in pending:
        dest=output_dir/name
        with dest.open("xb") as f:f.write(binary)
    _atomic_json(evidence,{"task_id":active["task_id"],"role":active["role"],
                           "status":"UNAPPROVED_LOCAL_CANDIDATES_NOT_LIBRARY_PASS",
                           "files":files,"exported_at":_now().isoformat()})
    return "LOCAL_CANDIDATES_EXPORTED_UNAPPROVED"


async def inspect_slot(role, page, root="/data/imagegen"):
    """Probe only previous active batch; never resend or open a fresh chat here.

    Result is (can_start_new_batch, status). Library save must be positively
    confirmed BEFORE moving to the next range of source ordinals.
    """
    root = Path(root).resolve()
    st=_state(root,role)
    active=st.get("active")
    if not active:
        return True, "READY"
    if active["status"] == "STAGED":
        return True, "STAGED_UNSENT"
    task=active["task_id"]
    receipt=root/"sent"/(role+"_"+task+".json")
    if not receipt.exists():
        return False, "SUBMISSION_AMBIGUOUS_NO_RECEIPT"
    data=json.loads(receipt.read_text(encoding="utf-8"))
    if data.get("status") != "CHAT_MESSAGE_SENT_ATTACHMENT_UI_VERIFIED_NOT_IMAGEGEN_PASS":
        return False, "SUBMISSION_UNVERIFIED_NO_AUTORETRY"
    if (data.get("task_id") != task or data.get("role") != role or
        len(data.get("tiles",[])) != active["count"]):
        return False, "SENT_RECEIPT_BINDING_MISMATCH"
    expected=active["count"]
    generated_evidence=root/STATE_DIR/"generated_visible"/(task+".json")
    persisted_generated=False
    if generated_evidence.is_file() and not generated_evidence.is_symlink():
        try:
            prior=json.loads(generated_evidence.read_text(encoding="utf-8"))
            persisted_generated=(
                prior.get("task_id")==task and prior.get("role")==role and
                prior.get("distinct_generated_images")==expected and
                prior.get("status")=="IMAGES_VISIBLE_NOT_LIBRARY_PROOF" and
                prior.get("export_status") in (
                    "LOCAL_CANDIDATES_EXPORTED_UNAPPROVED",
                    "EXISTING_CANDIDATES_VERIFIED",
                )
            )
        except Exception:
            persisted_generated=False

    if not persisted_generated:
        if not active.get("source_chat_url"):
            return False, "CHAT_URL_NOT_RECORDED"
        target=active["source_chat_url"].strip()
        if not re.fullmatch(r"https://chatgpt\.com/(?:g/g-p-[^/]+/)?c/[^?#]+(?:[?#].*)?", target):
            return False, "ACTIVE_CHAT_URL_UNSAFE"
        if page.url.rstrip("/") != target.rstrip("/"):
            # Reopen the exact recorded chat only when we still need fresh DOM
            # evidence. A prior SHA-bound export can survive browser restarts.
            try:
                await page.goto(target, wait_until="domcontentloaded", timeout=45000)
            except Exception as exc:
                return False, "ACTIVE_CHAT_REOPEN_FAILED:" + type(exc).__name__
            if page.url.rstrip("/") != target.rstrip("/"):
                return False, "ACTIVE_CHAT_REOPEN_MISMATCH"
        try:
            result=await page.evaluate(r"""async ({task,expected})=>{
          if(location.hostname!=='chatgpt.com'|| !location.pathname.includes('/c/'))return{error:'NOT_CHAT'};
          const usr=[...document.querySelectorAll('[data-markdown-text-tone="user-message"]')]
            .find(n=>(n.innerText||'').includes('UPLOAD_TASK_ID='+task));
          const turn=usr?.closest('[data-turn-key]');
          if(!turn)return{error:'USER_TURN_MISSING'};
          const buttons=[...turn.querySelectorAll('button[aria-label^="Show generated image "]')];
          if(buttons.length){
            const items=buttons.map(b=>{
              const m=(b.getAttribute('aria-label')||'').match(/^Show generated image ([1-9][0-9]*)$/);
              const img=b.querySelector('img');
              return m&&img?{index:Number(m[1]),src:img.currentSrc||img.src}:null;
            });
            if(items.some(x=>!x))return{error:'BROKEN_IMAGE_SELECTOR'};
            items.sort((a,b)=>a.index-b.index);
            if(items.some((x,i)=>x.index!==i+1))return{error:'NONCONSECUTIVE_GENERATED_IMAGES'};
            const sources=[...new Set(items.map(x=>x.src))];
            if(sources.length!==items.length)return{error:'DUPLICATED_IMAGE_PREVIEWS'};
            // A thumbnail may have naturalWidth=0 until selected. Fetch its
            // blob instead; this confirms a real, distinct generated image.
            const checks=await Promise.all(sources.map(async url=>{
              if(!url||!url.startsWith('blob:'))return false;
              try{
                const res=await fetch(url);
                if(!res.ok)return false;
                const blob=await res.blob();
                return blob.size>100&&blob.size<=30000000&&blob.type.startsWith('image/');
              }catch(e){return false;}
            }));
            if(checks.some(ok=>!ok))return{error:'IMAGE_BLOB_NOT_READY'};
            return {count:sources.length,expected,busy:!!turn.querySelector('[data-talvt-turn-state="in_progress"]'),
                    verified_by:'CAROUSEL_DISTINCT_IMAGE_BLOBS',error:null};
          }
          const full=[...turn.querySelectorAll('[data-testid="generated-image-preview"] img[alt^="Generated image"]')]
            .filter(i=>i.complete&&i.naturalWidth>0&&i.naturalHeight>0&&!!i.getClientRects().length);
          const sources=[...new Set(full.map(i=>i.currentSrc||i.src))];
          return{count:sources.length,expected,busy:!!turn.querySelector('[data-talvt-turn-state="in_progress"]'),
                 verified_by:'SINGLE_VISIBLE_PREVIEW_FALLBACK',error:null};
        }""",{"task":task,"expected":expected})
        except Exception:
            return False, "IMAGEGEN_RESULT_UI_NOT_VERIFIED"
        if result.get("error"):
            return False, "IMAGEGEN_"+result["error"]
        if result.get("busy"):
            return False, "IMAGEGEN_STILL_RUNNING"
        if result.get("count") != expected:
            observed=result.get("count")
            if expected == 5 and observed == 1:
                retried,msg=_retry_same_five(
                    st,active,root,"IMAGEGEN_SINGLE_OF_FIVE",observed=1)
                if retried:
                    return True,msg
                return False,msg
            return False, "IMAGEGEN_OUTPUT_COUNT_MISMATCH:"+str(observed)+"/"+str(expected)
        try:
            export_status=await export_unapproved_k_candidates(page,active,root)
        except Exception as exc:
            return False, "GENERATED_CANDIDATE_EXPORT_UNVERIFIED:"+str(exc)[:110]
        generated_evidence.parent.mkdir(parents=True,exist_ok=True)
        _atomic_json(generated_evidence,{"task_id":task,"role":role,"distinct_generated_images":expected,
                               "verification_method":result.get("verified_by"),
                               "status":"IMAGES_VISIBLE_NOT_LIBRARY_PROOF",
                               "export_status":export_status,"checked_at":_now().isoformat()})
    # Production advancement is bound to the actual generated bytes persisted
    # on N100. Project Library is useful supplemental evidence but its UI is not
    # a durable queue transport and must not stall later A/B/C1 schedule slots.
    local_proof,local_error=_local_export_confirmed(root,active)
    if local_error or not local_proof:
        return False,"LOCAL_EXPORT_NOT_VERIFIED:"+str(local_error or "NO_PROOF")
    completion=_local_completion_path(root,task)
    completion.parent.mkdir(parents=True,exist_ok=True)
    _atomic_json(completion,local_proof)

    # Preserve any already-existing positive Library evidence, but do not probe
    # or block on Library here. A separate audit can fill Library evidence later.
    library_verified,library_reason=_library_confirmed(root,active)
    st["next_ordinal"]=active["next_ordinal_after"]
    st["completed_files"]+=active["count"]
    st["completed_batches"]+=1
    st["active"]=None
    st["status"]="BATCH_COMPLETE_LOCAL_SHA_VERIFIED"
    st["last_library_status"]=(library_reason if library_verified
                               else "PENDING_NONBLOCKING")
    _atomic_json(state_path(root,role),st)
    return True, "BATCH_COMPLETE_LOCAL_SHA_VERIFIED"

def expected_counts(root):
    """Inspection summary, never count raw/hash-only files as translated."""
    return {role:_state(root,role) for role in RANGES}