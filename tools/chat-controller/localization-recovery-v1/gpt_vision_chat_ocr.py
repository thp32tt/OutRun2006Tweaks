#!/usr/bin/env python3
"""ChatGPT browser-attachment vision OCR fallback. No external API."""
from __future__ import annotations
import csv, datetime as dt, hashlib, io, json, os, re, tempfile, zipfile
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
VERSION="gpt-chat-vision-ocr-v1-20261025"
OCR_EXHAUSTED_ATTEMPTS=21
MAX_CHAT_ATTEMPTS_PER_FINGERPRINT=2
RESPONSE_STALL_SECONDS=max(300,int(os.environ.get("OUTRUN_GPT_OCR_RESPONSE_STALL_SECONDS","600")))
SUBMISSION_STALL_SECONDS=max(60,int(os.environ.get("OUTRUN_GPT_OCR_SUBMIT_STALL_SECONDS","300")))
RESPONSE_EXTRACTOR_VERSION="search-unit-assistant-v3-slot-aligned-20261026"
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
        status=rec.get("status")
        if status in ("APPLIED","APPLIED_MCP_BRIDGE") and int(rec.get("applied",0) or 0)>0:
            success.add(fp)
        elif status in ("RESPONSE_TIMEOUT_RETRY","RESPONSE_TIMEOUT_MAX_ATTEMPTS"):
            timed_out.add(fp)
    reset=sorted(timed_out-success)
    for fp in reset:
        st["attempts"][fp]=0
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

def _prompt(task_id,row,phrases):
    phrase_lines="\n".join("- "+p for p in phrases)
    return f"""OutRun 2006 HD 원본 이미지의 영문 UI 위치 분석 작업입니다.
이미지를 수정하거나 새 이미지를 만들지 마세요. 첨부된 원본 PNG를 직접 보고 아래 승인 영문 문구만 찾으세요.

TASK_ID={task_id}
SOURCE_PNG={row["png_filename"]}
IMAGE_SIZE={row["width"]}x{row["height"]}

찾을 문구:
{phrase_lines}

규칙:
1. 첨부 이미지를 직접 시각적으로 읽으세요.
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
    for row,phrases in _exhausted_candidates():
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
        completed={"task_id":task_id,"source_png":a["source_png"],"fingerprint":a["fingerprint"],
          "status":"APPLIED" if applied else "NO_VALID_DETECTIONS","applied":applied,"rejected":rejected[:50],
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
    st=_state();candidates=_exhausted_candidates()
    lanes={}
    retryable_sources=0;retryable_phrases=0
    for lane in ("C1","C2"):
        lane_rows=[]
        for row,phrases in candidates:
            if _lane_for_source(row["png_filename"])!=lane:
                continue
            fp=_fingerprint(row,phrases);used=int(st.get("attempts",{}).get(_attempt_key(fp,lane),0) or 0)
            lane_rows.append((phrases,used))
        rs=sum(1 for phrases,used in lane_rows if used<MAX_CHAT_ATTEMPTS_PER_FINGERPRINT)
        rp=sum(len(phrases) for phrases,used in lane_rows if used<MAX_CHAT_ATTEMPTS_PER_FINGERPRINT)
        retryable_sources+=rs;retryable_phrases+=rp
        lanes[lane]={"candidate_sources":len(lane_rows),
                     "candidate_phrases":sum(len(phrases) for phrases,_ in lane_rows),
                     "retryable_sources":rs,"retryable_phrases":rp,
                     "exhausted_sources":len(lane_rows)-rs}
    return {"version":VERSION,"active":st.get("active"),"candidate_sources":len(candidates),
      "candidate_phrases":sum(len(p) for _,p in candidates),
      "retryable_sources":retryable_sources,"retryable_phrases":retryable_phrases,
      "exhausted_sources":len(candidates)-retryable_sources,"lanes":lanes,
      "completed_records":len(st.get("completed",[])),"external_api_used":False}