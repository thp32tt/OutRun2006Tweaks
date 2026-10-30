#!/usr/bin/env python3
"""ChatGPT browser-attachment vision OCR fallback. No external API."""
from __future__ import annotations
import csv, datetime as dt, hashlib, io, json, os, re, tempfile, zipfile
from functools import lru_cache
from pathlib import Path
from PIL import Image

C_ROOT=Path("/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only")
SRC=C_ROOT/"hd_original_108_verified"
ZIP=C_ROOT/"hd_original_108_zip_inbox/OutRun_ALL_HD_Korean_Source_PNG_PART01_of_05_20261013.zip"
REPORT=C_ROOT/"hd108_ocr"
OUT=C_ROOT/"hd108_outputs"
GPT_OUT=C_ROOT/"gpt_vision_chat_ocr_outputs"
QUEUE_DIR=C_ROOT/"gpt_vision_chat_ocr"
STATE_PATH=QUEUE_DIR/"state.json"
AUDIT_PATH=QUEUE_DIR/"audit.jsonl"
# Host-side OCR triage is exported to the existing read/write imagegen bind
# mount. This read-only rescue input is strictly SHA-bound and cannot approve
# an OCR result; it only allows a verified chat-vision retry.
HOST_RETRY_PATH=Path("/data/imagegen/text_roi_batches/ocr_host_verified_retries.json")
PRODUCTION_MANIFEST=Path("/data/imagegen/text_roi_batches/production_manifest.json")
VERSION="gpt-chat-vision-ocr-v1-20261025"
OCR_EXHAUSTED_ATTEMPTS=21
MAX_CHAT_ATTEMPTS_PER_FINGERPRINT=2
RESPONSE_STALL_SECONDS=max(300,int(os.environ.get("OUTRUN_GPT_OCR_RESPONSE_STALL_SECONDS","600")))
SUBMISSION_STALL_SECONDS=max(60,int(os.environ.get("OUTRUN_GPT_OCR_SUBMIT_STALL_SECONDS","300")))
RESPONSE_EXTRACTOR_VERSION="search-unit-assistant-v4-dual-lane-poll-20261030"
TASK_RE=re.compile(r"^OUTRUN-GPT-OCR-Q\d{3}-[A-F0-9]{8}(?:-C2)?(?:-R[12])?$")

def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def _digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()

def _norm(text):
    return re.sub(r"\s+"," ",(text or "").strip()).casefold()

def _atomic_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    try: os.chmod(path.parent,0o755)
    except OSError: pass
    with tempfile.NamedTemporaryFile("w",dir=path.parent,delete=False,encoding="utf-8") as f:
        json.dump(obj,f,ensure_ascii=False,indent=2);f.write("\n");tmp=Path(f.name)
    os.chmod(tmp,0o644);os.replace(tmp,path)

def _audit(row):
    QUEUE_DIR.mkdir(parents=True,exist_ok=True)
    payload={"time_utc":_now(),"version":VERSION,**row}
    with AUDIT_PATH.open("a",encoding="utf-8") as f:
        f.write(json.dumps(payload,ensure_ascii=False)+"\n")
    try: os.chmod(AUDIT_PATH,0o644)
    except OSError: pass

def _state():
    if not STATE_PATH.exists():
        return {"version":VERSION,"active":None,"attempts":{},"completed":[],"updated_at":_now()}
    obj=json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if obj.get("version")!=VERSION or not isinstance(obj.get("attempts"),dict) or not isinstance(obj.get("completed"),list):
        raise ValueError("GPT_OCR_STATE_INVALID")
    return obj

def _save_state(obj):
    obj["updated_at"]=_now();_atomic_json(STATE_PATH,obj)

def _migrate_response_extractor_state(st):
    """Give timeout-only tasks a fresh chance after a response-DOM extractor upgrade."""
    if st.get("response_extractor_version")==RESPONSE_EXTRACTOR_VERSION:
        return []
    success=set()
    timed_out=set()
    for rec in st.get("completed",[]):
        if not isinstance(rec,dict):
            continue
        fp=rec.get("fingerprint")
        if not isinstance(fp,str):
            continue
        lane=rec.get("ocr_lane") or (
            "C2" if re.search(r"-C2(?:-R[12])?$",str(rec.get("task_id") or "")) else "C1")
        if lane not in ("C1","C2"):
            continue
        key=_attempt_key(fp,lane)
        status=rec.get("status")
        if status in ("APPLIED","APPLIED_MCP_BRIDGE") and int(rec.get("applied",0) or 0)>0:
            success.add(key)
        elif status in ("RESPONSE_TIMEOUT_RETRY","RESPONSE_TIMEOUT_MAX_ATTEMPTS"):
            timed_out.add(key)
    reset=sorted(timed_out-success)
    for key in reset:
        st["attempts"][key]=0
    st["response_extractor_version"]=RESPONSE_EXTRACTOR_VERSION
    st["response_extractor_migrated_at"]=_now()
    st["response_extractor_retry_reset_count"]=len(reset)
    return reset

def _manifest_rows():
    if not ZIP.is_file() or ZIP.is_symlink(): raise ValueError("HD108_ZIP_MISSING")
    with zipfile.ZipFile(ZIP) as z:
        rows=list(csv.DictReader(io.StringIO(z.read("01_DDS_PNG_MANIFEST_108.csv").decode("utf-8-sig"))))
    if len(rows)!=108 or len({r["png_filename"] for r in rows})!=108: raise ValueError("HD108_SOURCE_MANIFEST_INVALID")
    return {r["png_filename"]:r for r in rows}

def _output_roots():
    return (OUT,GPT_OUT)

@lru_cache(maxsize=3)
def _production_regions_cached(path,mtime_ns,size):
    """Only SHA-bound, registered English UI regions; read once per manifest version."""
    try:
        if size<=0 or size>20000000:
            return {}
        j=json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(j,dict) or j.get("schema")!="outrun-text-roi-production-v1":
            return {}
        items=j.get("items")
        if not isinstance(items,list) or j.get("item_count")!=len(items):
            return {}
        by_sha={}
        for item in items:
            if not isinstance(item,dict) or item.get("status") not in (
                    "ROI_APPROVED_FOR_IMAGEGEN","ROI_REBALANCED_TO_B"):
                continue
            source_sha=item.get("source_png_sha256")
            english=item.get("english")
            box=item.get("bbox_xyxy")
            if (not isinstance(source_sha,str) or not re.fullmatch(r"[0-9a-f]{64}",source_sha)
                    or not isinstance(english,str) or not english.strip()
                    or not isinstance(box,list) or len(box)!=4
                    or not all(type(x) is int for x in box)
                    or box[0]<0 or box[1]<0 or box[2]<=box[0] or box[3]<=box[1]):
                continue
            by_sha.setdefault(source_sha,[]).append((english.strip(),tuple(box)))
        return by_sha
    except (OSError,ValueError,TypeError,json.JSONDecodeError):
        return {}


def _production_regions(source_sha):
    """Production records are ROI coverage, not evidence of image/game QA."""
    p=PRODUCTION_MANIFEST
    try:
        if not p.is_file() or p.is_symlink():
            return []
        st=p.stat()
        return _production_regions_cached(str(p),st.st_mtime_ns,st.st_size).get(source_sha,[])
    except OSError:
        return []


def _covered_phrases(source_png,source_sha):
    covered=set()
    for root in _output_roots():
        sourceout=root/Path(source_png).stem
        if not sourceout.is_dir():
            continue
        for mp in sourceout.glob("*/manifest.json"):
            try:
                j=json.loads(mp.read_text(encoding="utf-8"))
                if j.get("source_sha256")==source_sha and isinstance(j.get("english"),str):
                    covered.add(_norm(j["english"]))
            except Exception:
                pass
    covered.update(_norm(english) for english,_ in _production_regions(source_sha))
    return covered

def _exhausted_candidates():
    rows=_manifest_rows();done=REPORT/"processed_v3";out=[]
    for name,row in sorted(rows.items()):
        rec=done/(name+".json")
        if not rec.is_file() or rec.is_symlink(): continue
        try: r=json.loads(rec.read_text(encoding="utf-8"))
        except Exception: continue
        if r.get("source_png")!=name or r.get("source_sha256")!=row.get("png_sha256"): continue
        if int(r.get("attempts",0) or 0)<OCR_EXHAUSTED_ATTEMPTS: continue
        unresolved=r.get("unresolved_after")
        if not isinstance(unresolved,list): continue
        covered=_covered_phrases(name,row["png_sha256"]);seen=set();remaining=[]
        for phrase in unresolved:
            if not isinstance(phrase,str) or not phrase.strip(): continue
            code=_norm(phrase)
            if code in covered or code in seen: continue
            seen.add(code);remaining.append(phrase.strip())
        if not remaining: continue
        src=SRC/name
        if not src.is_file() or src.is_symlink() or src.stat().st_size!=int(row["png_size_bytes"]) or _digest(src)!=row["png_sha256"]: continue
        out.append((row,remaining))
    return out

def _host_verified_candidates():
    """Read a bounded host-verified retry snapshot when container OCR sources diverge.

    The host and container may have different OCR processed-v3 views even while
    sharing state.json. Never trust raw phrases alone: pin source PNG bytes and
    exact processed-record bytes, require those phrases to be in the original
    unresolved_after record, and re-check current existing coverage.
    """
    p=HOST_RETRY_PATH
    if not p.is_file() or p.is_symlink() or p.stat().st_size>262144:
        return []
    try:
        doc=json.loads(p.read_text(encoding="utf-8"))
        if doc.get("schema")!="outrun.gpt_ocr.host_verified_retries.v1":
            return []
        rows=doc.get("items")
        if not isinstance(rows,list) or len(rows)>108:
            return []
        source_rows=_manifest_rows()
        result=[]
        seen=set()
        for entry in rows:
            if not isinstance(entry,dict):
                continue
            name=entry.get("source_png")
            if not isinstance(name,str) or name not in source_rows or name in seen:
                continue
            seen.add(name)
            row=source_rows[name]
            if entry.get("source_sha256")!=row.get("png_sha256"):
                continue
            src=SRC/name
            if (not src.is_file() or src.is_symlink()
                    or src.stat().st_size!=int(row["png_size_bytes"])
                    or _digest(src)!=row["png_sha256"]):
                continue
            proc=REPORT/"processed_v3"/(name+".json")
            if not proc.is_file() or proc.is_symlink() or proc.stat().st_size>131072:
                continue
            raw=proc.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=entry.get("processed_sha256"):
                continue
            record=json.loads(raw.decode("utf-8"))
            if (record.get("source_png")!=name
                    or record.get("source_sha256")!=row["png_sha256"]
                    or int(record.get("attempts",0) or 0)<OCR_EXHAUSTED_ATTEMPTS):
                continue
            unresolved=record.get("unresolved_after")
            targets=entry.get("target_phrases")
            if (not isinstance(unresolved,list) or not isinstance(targets,list)
                    or not targets or len(targets)>40
                    or not all(isinstance(x,str) and 0<len(x)<=220 for x in targets)
                    or len({_norm(x) for x in targets})!=len(targets)):
                continue
            allowed={_norm(x) for x in unresolved if isinstance(x,str)}
            if any(_norm(x) not in allowed for x in targets):
                continue
            covered=_covered_phrases(name,row["png_sha256"])
            remaining=[x for x in targets if _norm(x) not in covered]
            if not remaining or _fingerprint(row,remaining)!=entry.get("fingerprint"):
                continue
            result.append((row,remaining))
        return result
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
        return []


def _dispatch_candidates():
    """Normal OCR queue first; SHA-pinned host sidecar only supplies gaps."""
    regular=_exhausted_candidates()
    known={(row["png_filename"],_fingerprint(row,phrases)) for row,phrases in regular}
    for row,phrases in _host_verified_candidates():
        key=(row["png_filename"],_fingerprint(row,phrases))
        if key not in known:
            regular.append((row,phrases))
            known.add(key)
    return regular


def _fingerprint(row,phrases):
    return hashlib.sha256((row["png_filename"]+"|"+row["png_sha256"]+"|"+"\n".join(phrases)).encode()).hexdigest()

def _normalize_lane(lane):
    if lane is None:
        return None
    lane=str(lane).strip().upper()
    if lane not in ("C1","C2"):
        raise ValueError("GPT_OCR_LANE_INVALID")
    return lane

def _lane_for_source(source_png):
    m=re.match(r"^Q(\d{3})_",str(source_png or ""))
    if not m:
        raise ValueError("GPT_OCR_SOURCE_QUEUE_INDEX_INVALID")
    return "C1" if int(m.group(1)) % 2 else "C2"

def _attempt_key(fp,lane):
    # Preserve legacy C1 attempt counters; C2 is a new independent review lane.
    return ("C2:"+fp) if lane=="C2" else fp

def _duplicate_bbox_review_hold(st,fp,lane):
    """Treat an exact prior duplicate-only OCR response as a manual-review hold.

    The phrase fingerprint includes source identity and still-unresolved phrases,
    so a changed candidate set remains eligible for fresh OCR. Do not mark text
    as localized, and never infer a box from an overlapping, differently named
    historical ROI. Supports existing NO_VALID_DETECTIONS records.
    """
    for rec in reversed(st.get("completed",[])):
        if not isinstance(rec,dict) or rec.get("fingerprint")!=fp:
            continue
        rec_lane=rec.get("ocr_lane") or (
            "C2" if re.search(r"-C2(?:-R[12])?$",str(rec.get("task_id") or "")) else "C1")
        if rec_lane!=lane or int(rec.get("applied",0) or 0)!=0:
            continue
        rejected=rec.get("rejected")
        if (rec.get("status") in ("NO_VALID_DETECTIONS","REVIEW_REQUIRED_DUPLICATE_BBOX")
                and isinstance(rejected,list) and rejected
                and all(reason=="BBOX_DUPLICATES_EXISTING_REGION" for reason in rejected)):
            return rec
    return None


def _known_ocr_regions(source_png,source_sha):
    """Historical boxes for this *exact* source SHA; never use another variant."""
    found=set()
    for root in _output_roots():
        sourceout=root/Path(source_png).stem
        if not sourceout.is_dir():
            continue
        for mp in sourceout.glob("*/manifest.json"):
            try:
                j=json.loads(mp.read_text(encoding="utf-8"))
                box=j.get("bbox_xyxy");phrase=j.get("english")
                if (j.get("source_sha256")!=source_sha or
                        not (isinstance(box,list) and len(box)==4
                             and all(type(v) is int for v in box))):
                    continue
                if not isinstance(phrase,str) or not phrase.strip():
                    continue
                found.add((phrase.strip()[:100],tuple(box)))
            except Exception:
                continue
    found.update(_production_regions(source_sha))
    return sorted(found,key=lambda x:(x[1],x[0]))


def _prompt(task_id,row,phrases):
    phrase_lines="\n".join("- "+p for p in phrases)
    regions=_known_ocr_regions(row["png_filename"],row["png_sha256"])
    limit=40
    old_box_lines="\n".join(
        "- "+json.dumps({"english":english,"bbox_xyxy":list(box)},ensure_ascii=False)
        for english,box in regions[:limit])
    if len(regions)>limit:
        old_box_lines+="\n- ... 이미 등록된 좌표 "+str(len(regions)-limit)+"건 추가 생략"
    if not old_box_lines:
        old_box_lines="- 없음"
    return f"""OutRun 2006 HD 원본 이미지의 영문 UI 위치 분석 작업입니다.
이미지를 수정하거나 새 이미지를 만들지 마세요. 첨부된 원본 PNG를 직접 보고 아래 승인 영문 문구만 찾으세요.

TASK_ID={task_id}
SOURCE_PNG={row["png_filename"]}
IMAGE_SIZE={row["width"]}x{row["height"]}

찾을 문구:
{phrase_lines}

이미 등록된 원문 ROI 좌표(동일 이미지 SHA 확인, 신규 검출 대상으로 재사용하지 마세요):
{old_box_lines}

규칙:
1. 첨부 이미지를 직접 시각적으로 읽으세요.
1-1. 위 기존 좌표와 90% 이상 겹치는 영역은 다른 문구로 다시 제출하지 마세요. 승인 문구의 위치가 다른 부분에서 확인되지 않거나 모호하면 detections에 추측 좌표를 만들지 말고 uncertain에 넣으세요.
2. 위 목록에 있는 문구만 반환하고 보이지 않으면 만들지 마세요.
3. bbox는 원본 이미지 픽셀 좌표 [x0,y0,x1,y1]이고 글자/외곽선/그림자를 포함하세요.
4. 좌상단은 (0,0), x는 오른쪽, y는 아래쪽입니다.
5. 확실하지 않은 항목은 uncertain에 넣으세요.
6. 이미지 생성/수정은 하지 마세요.
7. 설명문이나 코드펜스 없이 JSON 객체 하나만 답하세요.

{{"task_id":"{task_id}","source_png":"{row["png_filename"]}","detections":[{{"english":"승인 목록의 정확한 원문","bbox_xyxy":[0,0,1,1],"confidence":0.0}}],"uncertain":[{{"english":"승인 목록의 정확한 원문","reason":"이유"}}]}}"""

def next_binding(lane=None):
    lane=_normalize_lane(lane)
    if os.environ.get("OUTRUN_GPT_CHAT_OCR_ENABLED","true").lower()!="true":
        return None,"GPT_CHAT_OCR_DISABLED"
    st=_state()
    reset=_migrate_response_extractor_state(st)
    if reset:
        _save_state(st)
        _audit({"status":"RESPONSE_EXTRACTOR_UPGRADE_RETRY_RESET",
                "response_extractor_version":RESPONSE_EXTRACTOR_VERSION,
                "fingerprints_reset":len(reset),"external_api_used":False})
    elif st.get("response_extractor_version")!=RESPONSE_EXTRACTOR_VERSION:
        _save_state(st)
    active=st.get("active")
    if isinstance(active,dict):
        status=active.get("status")
        if status=="STAGED": return dict(active),None
        if status=="SENT_AWAITING_RESPONSE": return None,"ACTIVE_AWAITING_RESPONSE:"+str(active.get("task_id"))
        if status=="SUBMITTING":
            try:
                started=dt.datetime.fromisoformat(str(active.get("submitting_at","")))
                if started.tzinfo is None: started=started.replace(tzinfo=dt.timezone.utc)
                age=(dt.datetime.now(dt.timezone.utc)-started.astimezone(dt.timezone.utc)).total_seconds()
            except Exception:
                age=10**9
            if age >= 300:
                active["status"]="STAGED"
                active["last_presend_failure"]="STALE_SUBMITTING_AUTO_RECOVERY"
                active["last_presend_failure_at"]=_now()
                active["stale_submission_recoveries"]=int(active.get("stale_submission_recoveries",0) or 0)+1
                _save_state(st)
                _audit({"status":"STALE_SUBMITTING_RECOVERED","task_id":active.get("task_id"),
                        "source_png":active.get("source_png"),"external_api_used":False})
                return dict(active),None
            return None,"ACTIVE_SUBMISSION_AMBIGUOUS:"+str(active.get("task_id"))
        raise ValueError("GPT_OCR_ACTIVE_STATE_INVALID")
    for row,phrases in _dispatch_candidates():
        source_lane=_lane_for_source(row["png_filename"])
        if lane is not None and source_lane!=lane:
            continue
        effective_lane=lane or "C1"
        fp=_fingerprint(row,phrases);attempt_key=_attempt_key(fp,effective_lane)
        used=int(st["attempts"].get(attempt_key,0) or 0)
        bridged=any(
            isinstance(rec,dict) and rec.get("fingerprint")==fp and
            rec.get("status")=="APPLIED_MCP_BRIDGE" and
            int(rec.get("applied",0) or 0)>=len(phrases)
            for rec in st.get("completed",[])
        )
        if bridged:
            if used<MAX_CHAT_ATTEMPTS_PER_FINGERPRINT:
                st["attempts"][attempt_key]=MAX_CHAT_ATTEMPTS_PER_FINGERPRINT;_save_state(st)
            continue
        if _duplicate_bbox_review_hold(st,fp,effective_lane):
            # Prevent repeated, identical cross-label region collisions. A
            # qualified reviewer must inspect these missing English phrases.
            continue
        if used>=MAX_CHAT_ATTEMPTS_PER_FINGERPRINT: continue
        suffix="" if used==0 else f"-R{used}"
        lane_suffix="-C2" if effective_lane=="C2" else ""
        task=f"OUTRUN-GPT-OCR-{row['png_filename'][:4]}-{fp[:8].upper()}{lane_suffix}{suffix}"
        if not TASK_RE.fullmatch(task): raise ValueError("GPT_OCR_TASK_ID_INVALID")
        b={"task_id":task,"role":effective_lane+"OCR","ocr_lane":effective_lane,"attempt_key":attempt_key,
           "source_png":row["png_filename"],"source_sha256":row["png_sha256"],
           "source_dds_path":row["source_dds_path"],"source_dds_sha256":row["dds_sha256"],
           "queue_indexes":row["queue_indexes"],"path":str(SRC/row["png_filename"]),"paths":[str(SRC/row["png_filename"])],
           "dimensions":[int(row["width"]),int(row["height"])],"target_phrases":phrases,"fingerprint":fp,
           "attempt_index":used,"status":"STAGED","created_at":_now(),"chat_url":None}
        b["prompt"]=_prompt(task,row,phrases);st["active"]=b;_save_state(st)
        _audit({"status":"STAGED","task_id":task,"source_png":row["png_filename"],"target_count":len(phrases),"external_api_used":False})
        return dict(b),None
    return None,"GPT_CHAT_OCR_QUEUE_EMPTY_OR_EXHAUSTED"

def stage_submission(task_id):
    st=_state();a=st.get("active")
    if not isinstance(a,dict) or a.get("task_id")!=task_id:return "STATE_TASK_MISMATCH"
    if a.get("status")!="STAGED":return "SUBMISSION_ALREADY_ATTEMPTED"
    a["status"]="SUBMITTING";a["submitting_at"]=_now();_save_state(st);return "SUBMITTING"

def rollback_submission(task_id,reason):
    st=_state();a=st.get("active")
    if not isinstance(a,dict) or a.get("task_id")!=task_id:return "STATE_TASK_MISMATCH"
    if a.get("status")!="SUBMITTING":return "ROLLBACK_STATE_NOT_SUBMITTING"
    a["status"]="STAGED";a["last_presend_failure"]=str(reason)[:180];a["last_presend_failure_at"]=_now();_save_state(st)
    return "ROLLED_BACK_TO_STAGED"

def record_chat_url(task_id,url):
    if not re.fullmatch(r"https://chatgpt\.com/(?:g/[^?#]+/)?c/[A-Za-z0-9-]+",url or ""):return "CHAT_URL_UNVERIFIED"
    st=_state();a=st.get("active")
    if not isinstance(a,dict) or a.get("task_id")!=task_id:return "STATE_TASK_MISMATCH"
    if a.get("status")!="SUBMITTING":return "STATE_NOT_SUBMITTING"
    a["status"]="SENT_AWAITING_RESPONSE";a["chat_url"]=url;a["sent_at"]=_now()
    fp=a["fingerprint"];attempt_key=a.get("attempt_key") or _attempt_key(fp,a.get("ocr_lane") or "C1")
    st["attempts"][attempt_key]=int(st["attempts"].get(attempt_key,0) or 0)+1;_save_state(st)
    _audit({"status":"SENT_AWAITING_RESPONSE","task_id":task_id,"source_png":a["source_png"],"chat_url":url,"external_api_used":False})
    return "URL_RECORDED"

def active_task():
    a=_state().get("active");return dict(a) if isinstance(a,dict) else None

def recover_stale_active(max_age_seconds=None):
    """Release stale pre-send or response-wait state so one browser interruption cannot stop the queue."""
    response_threshold=RESPONSE_STALL_SECONDS if max_age_seconds is None else max(1,int(max_age_seconds))
    st=_state();a=st.get("active")
    if not isinstance(a,dict):
        return {"status":"NO_STALE_ACTIVE","recovered":False}
    active_status=a.get("status")
    if active_status=="SUBMITTING":
        raw=a.get("submitting_at") or a.get("created_at")
        try:
            started=dt.datetime.fromisoformat(str(raw))
            if started.tzinfo is None:started=started.replace(tzinfo=dt.timezone.utc)
            age=(dt.datetime.now(dt.timezone.utc)-started.astimezone(dt.timezone.utc)).total_seconds()
        except Exception:
            age=SUBMISSION_STALL_SECONDS+1
        if age<SUBMISSION_STALL_SECONDS:
            return {"status":"SUBMISSION_WITHIN_LIMIT","recovered":False,"age_seconds":int(max(0,age))}
        a["status"]="STAGED"
        a["last_presend_failure"]="STALE_SUBMITTING_WATCHDOG_RECOVERY"
        a["last_presend_failure_at"]=_now()
        a["stale_submission_recoveries"]=int(a.get("stale_submission_recoveries",0) or 0)+1
        _save_state(st)
        recovered={"status":"STALE_SUBMITTING_RECOVERED","recovered":True,
                   "task_id":a.get("task_id"),"source_png":a.get("source_png"),
                   "age_seconds":int(max(0,age))}
        _audit({**recovered,"external_api_used":False})
        return recovered
    if active_status!="SENT_AWAITING_RESPONSE":
        return {"status":"NO_STALE_RESPONSE_WAIT","recovered":False}
    raw=a.get("sent_at") or a.get("submitting_at") or a.get("created_at")
    try:
        started=dt.datetime.fromisoformat(str(raw))
        if started.tzinfo is None:started=started.replace(tzinfo=dt.timezone.utc)
        age=(dt.datetime.now(dt.timezone.utc)-started.astimezone(dt.timezone.utc)).total_seconds()
    except Exception:
        age=response_threshold+1
    if age<response_threshold:
        return {"status":"RESPONSE_WAIT_WITHIN_LIMIT","recovered":False,"age_seconds":int(max(0,age))}
    fp=a.get("fingerprint");attempt_key=a.get("attempt_key") or _attempt_key(fp,a.get("ocr_lane") or "C1")
    used=int(st.get("attempts",{}).get(attempt_key,0) or 0)
    status="RESPONSE_TIMEOUT_RETRY" if used<MAX_CHAT_ATTEMPTS_PER_FINGERPRINT else "RESPONSE_TIMEOUT_MAX_ATTEMPTS"
    completed={"task_id":a.get("task_id"),"source_png":a.get("source_png"),"fingerprint":fp,
      "status":status,"applied":0,"completed_at":_now(),"chat_url":a.get("chat_url"),
      "age_seconds":int(max(0,age)),"attempts_used":used}
    st["completed"].append(completed);st["completed"]=st["completed"][-500:];st["active"]=None
    _save_state(st);_audit(completed)
    return {**completed,"recovered":True}

def _extract_json(text):
    if not isinstance(text,str) or not text.strip(): raise ValueError("GPT_OCR_RESPONSE_EMPTY")
    raw=text.strip()
    if raw.startswith(chr(96)*3):
        raw=re.sub(r"^"+re.escape(chr(96)*3)+r"(?:json)?\s*","",raw,flags=re.I)
        raw=re.sub(r"\s*"+re.escape(chr(96)*3)+r"$","",raw)
    try:return json.loads(raw)
    except json.JSONDecodeError:
        start,end=raw.find("{"),raw.rfind("}")
        if start<0 or end<=start: raise ValueError("GPT_OCR_RESPONSE_JSON_NOT_FOUND")
        return json.loads(raw[start:end+1])

def _overlap_ratio(a,b):
    x0=max(a[0],b[0]);y0=max(a[1],b[1]);x1=min(a[2],b[2]);y1=min(a[3],b[3])
    inter=max(0,x1-x0)*max(0,y1-y0)
    if not inter:return 0.0
    aa=max(1,(a[2]-a[0])*(a[3]-a[1]));bb=max(1,(b[2]-b[0])*(b[3]-b[1]))
    return inter/min(aa,bb)

def _load_margin_check():
    import sys
    here=Path(__file__).resolve()
    for p in (here.parent/"c_english_crop",here.parent.parent/"c_english_crop"):
        if p.is_dir() and str(p) not in sys.path:sys.path.insert(0,str(p))
    import ocr_recognize
    return ocr_recognize.margin_check

def apply_response(task_id,assistant_text):
    st=_state();a=st.get("active")
    if not isinstance(a,dict) or a.get("task_id")!=task_id:return {"status":"STATE_TASK_MISMATCH","applied":0}
    if a.get("status")!="SENT_AWAITING_RESPONSE":return {"status":"STATE_NOT_AWAITING_RESPONSE","applied":0}
    try:
        data=_extract_json(assistant_text)
        if not isinstance(data,dict):raise ValueError("GPT_OCR_RESPONSE_NOT_OBJECT")
        if data.get("task_id")!=task_id or data.get("source_png")!=a["source_png"]:raise ValueError("GPT_OCR_RESPONSE_BINDING_MISMATCH")
        detections=data.get("detections")
        if not isinstance(detections,list):raise ValueError("GPT_OCR_DETECTIONS_NOT_LIST")
        row=_manifest_rows().get(a["source_png"])
        if not row or row.get("png_sha256")!=a["source_sha256"]:raise ValueError("GPT_OCR_SOURCE_MANIFEST_CHANGED")
        src=Path(a["path"])
        if not src.is_file() or src.is_symlink() or src.stat().st_size!=int(row["png_size_bytes"]) or _digest(src)!=a["source_sha256"]:
            raise ValueError("GPT_OCR_SOURCE_SHA_CHANGED")
        with Image.open(src) as im:
            if im.format!="PNG" or im.mode!="RGBA" or list(im.size)!=a["dimensions"]:raise ValueError("GPT_OCR_SOURCE_FORMAT_CHANGED")
            image=im.copy()
        targets={_norm(x):x for x in a["target_phrases"]}
        covered=_covered_phrases(a["source_png"],a["source_sha256"])
        existing=[]
        for root in _output_roots():
            prior=root/Path(a["source_png"]).stem
            if not prior.is_dir():
                continue
            for mp in prior.glob("*/manifest.json"):
                try:
                    j=json.loads(mp.read_text(encoding="utf-8"));box=j.get("bbox_xyxy")
                    if j.get("source_sha256")==a["source_sha256"] and isinstance(box,list) and len(box)==4 and all(type(v) is int for v in box):
                        existing.append(box)
                except Exception:
                    pass
        # GPT chat crops use a dedicated writable root. Legacy OCR output may be
        # root-owned on the host bind mount and must remain read-only.
        sourceout=GPT_OUT/Path(a["source_png"]).stem
        applied=0;rejected=[];seen=set()
        response_sha=hashlib.sha256(assistant_text.encode("utf-8")).hexdigest()
        for det in detections:
            if not isinstance(det,dict):rejected.append("DETECTION_NOT_OBJECT");continue
            english=det.get("english");box=det.get("bbox_xyxy");conf=det.get("confidence")
            code=_norm(english) if isinstance(english,str) else ""
            if code not in targets:rejected.append("PHRASE_NOT_APPROVED");continue
            if code in covered or code in seen:continue
            if not (isinstance(box,list) and len(box)==4 and all(type(v) is int for v in box)):rejected.append("BBOX_INVALID");continue
            x0,y0,x1,y1=box
            if not (0<=x0<x1<=image.width and 0<=y0<y1<=image.height):rejected.append("BBOX_OUT_OF_RANGE");continue
            if x1-x0<4 or y1-y0<4:rejected.append("BBOX_TOO_SMALL");continue
            if (x1-x0)*(y1-y0)>image.width*image.height*.90:rejected.append("BBOX_IMPLAUSIBLY_LARGE");continue
            if any(_overlap_ratio(box,old)>.90 for old in existing):rejected.append("BBOX_DUPLICATES_EXISTING_REGION");continue
            if not isinstance(conf,(int,float)) or isinstance(conf,bool) or not (0.0 <= float(conf) <= 1.0):
                rejected.append("CONFIDENCE_INVALID");continue
            if float(conf) < 0.60:
                rejected.append("CONFIDENCE_TOO_LOW");continue
            phrase=targets[code]
            label=hashlib.sha256((a["source_png"]+"|"+phrase+"|"+json.dumps(box)+"|"+VERSION+"|"+task_id).encode()).hexdigest()[:16]
            target=sourceout/label;mp=target/"manifest.json"
            if target.exists():
                if not mp.is_file():
                    raise ValueError("GPT_OCR_TARGET_COLLISION")
                prior=json.loads(mp.read_text(encoding="utf-8"))
                if prior.get("gpt_chat_task_id")!=task_id or prior.get("status")!="DIRECT_IMAGEGEN_READY":
                    raise ValueError("GPT_OCR_TARGET_COLLISION")
                seen.add(code);continue
            target.mkdir(parents=True,exist_ok=False)
            manifest={"status":"DIRECT_IMAGEGEN_READY","source_type":"SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG",
              "source_png":a["source_png"],"source_png_path":str(src),"source_sha256":a["source_sha256"],
              "reference_dds_path":row["source_dds_path"],"reference_dds_sha256":row["dds_sha256"],
              "independent_DDS_pixel_equality":"NOT_TESTED_FOR_THIS_PNG","queue_indexes":row["queue_indexes"],
              "english":phrase,"ocr_confidence":conf,"bbox_xyxy":box,"source_dimensions":list(image.size),
              "target_dimensions":[x1-x0,y1-y0],"direct_full_hd_reference":True,"crop_created":False,
              "human_review_required":True,"runtime_validation":"UNTESTED","old_split_tiles_used":False,
              "A_B":"DIRECT_FULL_HD_REFERENCE_PENDING","gpt_chat_ocr_version":VERSION,
              "gpt_chat_task_id":task_id,"gpt_chat_response_sha256":response_sha,
              "gpt_chat_bbox_source":"CHATGPT_ATTACHED_ORIGINAL_HD_IMAGE","external_api_used":False,
              "image_generation_used":False}
            _atomic_json(mp,manifest);existing.append(box);seen.add(code);applied+=1
        duplicate_only=(applied==0 and bool(rejected)
                        and all(reason=="BBOX_DUPLICATES_EXISTING_REGION" for reason in rejected))
        completed={"task_id":task_id,"source_png":a["source_png"],"fingerprint":a["fingerprint"],
          "ocr_lane":a.get("ocr_lane") or "C1",
          "status":"APPLIED" if applied else (
              "REVIEW_REQUIRED_DUPLICATE_BBOX" if duplicate_only else "NO_VALID_DETECTIONS"),
          "applied":applied,"rejected":rejected[:50],
          "manual_review_required":duplicate_only,
          "response_sha256":response_sha,"completed_at":_now(),"chat_url":a.get("chat_url")}
        st["completed"].append(completed);st["completed"]=st["completed"][-500:];st["active"]=None;_save_state(st);_audit(completed)
        return completed
    except Exception as exc:
        failed={"task_id":task_id,"source_png":a.get("source_png"),"fingerprint":a.get("fingerprint"),
          "status":"RESPONSE_HOLD","applied":0,"reason":type(exc).__name__+":"+str(exc)[:220],
          "failed_at":_now(),"chat_url":a.get("chat_url")}
        st["completed"].append(failed);st["completed"]=st["completed"][-500:];st["active"]=None;_save_state(st);_audit(failed)
        return failed

def summary():
    st=_state();candidates=_dispatch_candidates()
    lanes={}
    retryable_sources=0;retryable_phrases=0;manual_sources=0;manual_phrases=0;exhausted_sources=0
    for lane in ("C1","C2"):
        retryable=[];held=[];exhausted=[];lane_rows=[]
        for row,phrases in candidates:
            if _lane_for_source(row["png_filename"])!=lane:
                continue
            fp=_fingerprint(row,phrases);used=int(st.get("attempts",{}).get(_attempt_key(fp,lane),0) or 0)
            lane_rows.append((phrases,used))
            if _duplicate_bbox_review_hold(st,fp,lane):
                held.append((row,phrases))
            elif used<MAX_CHAT_ATTEMPTS_PER_FINGERPRINT:
                retryable.append((row,phrases))
            else:
                exhausted.append((row,phrases))
        rs=len(retryable);rp=sum(len(phrases) for _,phrases in retryable)
        ms=len(held);mp=sum(len(phrases) for _,phrases in held)
        retryable_sources+=rs;retryable_phrases+=rp;manual_sources+=ms;manual_phrases+=mp
        exhausted_sources+=len(exhausted)
        lanes[lane]={"candidate_sources":len(lane_rows),
                     "candidate_phrases":sum(len(phrases) for phrases,_ in lane_rows),
                     "retryable_sources":rs,"retryable_phrases":rp,
                     "manual_review_sources":ms,"manual_review_phrases":mp,
                     "exhausted_sources":len(exhausted)}
    return {"version":VERSION,"active":st.get("active"),"candidate_sources":len(candidates),
      "candidate_phrases":sum(len(p) for _,p in candidates),
      "retryable_sources":retryable_sources,"retryable_phrases":retryable_phrases,
      "manual_review_sources":manual_sources,"manual_review_phrases":manual_phrases,
      "exhausted_sources":exhausted_sources,"lanes":lanes,
      "completed_records":len(st.get("completed",[])),"external_api_used":False}