"""Single existing C1 browser: review ONE repaired DDS per normal poll.

Fetch only the compact evidence artifact (not native DDS), verify every
attachment SHA and persist a CAS-protected remote send receipt before Enter.
No paid API, second browser, extra poll, release approval or image generation.
"""
from __future__ import annotations
import asyncio,hashlib,json,os,re,tempfile,urllib.request,urllib.error,zipfile
from pathlib import Path

QROOT="localization/automation_runs/hd_cleanplate_repair"
BRANCH="korean-localization-qa-queue-20261104"
API="https://api.github.com/repos/thp32tt/OutRun2006Tweaks"
H64=re.compile(r"[0-9a-f]{64}\Z")
TID=re.compile(r"HDAT-[0-9a-f]{24}\Z")
MAX_ZIP=192*1024*1024
MAX_PNG=5*1024*1024
MAX_MANIFEST=32*1024*1024

def digest(raw):return hashlib.sha256(raw).hexdigest()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def fetch_evidence(pointer,home,token):
    if not token:raise ValueError("ATLAS_ACTIONS_READ_TOKEN_REQUIRED")
    if (pointer.get("schema")!="outrun.hd.cleanplate-queue-pointer.v1"
        or type(pointer.get("run_id")) is not int or pointer["run_id"]<=0
        or type(pointer.get("artifact_id")) is not int or pointer["artifact_id"]<=0
        or not H64.fullmatch(pointer.get("manifest_sha256",""))
        or pointer.get("release_approved") is not False
        or pointer.get("runtime_validation")!="UNTESTED"):
        raise ValueError("ATLAS_BAD_QUEUE_POINTER")
    cache=home/"atlas-vision"
    cache.mkdir(parents=True,exist_ok=True)
    path=cache/("run-"+str(pointer["run_id"])+".zip")
    def inspect(p):
        if not p.is_file() or p.stat().st_size>MAX_ZIP:raise ValueError("ATLAS_ZIP_SIZE")
        with zipfile.ZipFile(p) as z:
            names=z.namelist()
            if len(names)!=len(set(names)) or "manifest.json" not in names:
                raise ValueError("ATLAS_ZIP_MEMBERS")
            if z.getinfo("manifest.json").file_size>MAX_MANIFEST:raise ValueError("ATLAS_MANIFEST_SIZE")
            raw=z.read("manifest.json")
            if digest(raw)!=pointer["manifest_sha256"]:raise ValueError("ATLAS_MANIFEST_SHA")
            doc=json.loads(raw)
            if (doc.get("schema")!="outrun.hd.cleanplate-repair.v1" or doc.get("scope")!="FULL_104"
                or doc.get("asset_sha")!=pointer.get("asset_sha")
                or doc.get("release_approved") is not False or doc.get("runtime_validation")!="UNTESTED"
                or len(doc.get("tasks",[]))!=104):raise ValueError("ATLAS_MANIFEST_SCOPE")
            ids=set();expected={"manifest.json"}
            for t in doc["tasks"]:
                tid=t.get("task_id","")
                if not TID.fullmatch(tid) or tid in ids or not H64.fullmatch(t.get("source_dds_sha256","")) or not H64.fullmatch(t.get("candidate_dds_sha256","")):
                    raise ValueError("ATLAS_TASK_ID_OR_SHA")
                ids.add(tid)
                if set(t.get("images",{}))!={"source","clean","final"}:raise ValueError("ATLAS_TASK_IMAGES")
                for kind,item in t["images"].items():
                    name=tid+"_"+kind+".png"
                    if item.get("name")!=name or not H64.fullmatch(item.get("sha256","")) or z.getinfo(name).file_size>MAX_PNG:
                        raise ValueError("ATLAS_IMAGE_INVALID")
                    expected.add(name)
            if set(names)!=expected:raise ValueError("ATLAS_UNEXPECTED_ZIP_MEMBERS")
        return doc
    if path.exists():
        return path,inspect(path)
    # Never forward the GitHub bearer token to the artifact storage redirect.
    req=urllib.request.Request(API+"/actions/artifacts/"+str(pointer["artifact_id"])+"/zip",headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","User-Agent":"outrun-atlas-vision"})
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=30) as r:
            raise ValueError("ATLAS_EXPECTED_ARTIFACT_REDIRECT")
    except urllib.error.HTTPError as e:
        if e.code not in (302,303,307,308):raise RuntimeError("ATLAS_ARTIFACT_HTTP_"+str(e.code)) from None
        url=e.headers.get("Location","")
    from urllib.parse import urlsplit
    u=urlsplit(url)
    if u.scheme!="https" or not u.hostname or not (u.hostname.endswith(".blob.core.windows.net") or u.hostname.endswith(".actions.githubusercontent.com") or u.hostname.endswith(".githubusercontent.com")):
        raise ValueError("ATLAS_UNEXPECTED_ARTIFACT_HOST")
    fd,tmp=tempfile.mkstemp(dir=cache,suffix=".part")
    try:
        with os.fdopen(fd,"wb") as out,urllib.request.urlopen(url,timeout=60) as r:
            n=0
            while True:
                block=r.read(256*1024)
                if not block:break
                n+=len(block)
                if n>MAX_ZIP:raise ValueError("ATLAS_ARTIFACT_TOO_BIG")
                out.write(block)
        doc=inspect(Path(tmp))
        os.replace(tmp,path)
        # Keep exactly one immutable evidence archive; remote decisions survive.
        for old in cache.glob("run-*.zip"):
            if old!=path:old.unlink()
        return path,doc
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def stage_images(archive,task,home):
    dst=home/"atlas-vision"/"current"
    dst.mkdir(parents=True,exist_ok=True)
    paths=[]
    with zipfile.ZipFile(archive) as z:
        for kind in ("source","clean","final"):
            item=task["images"][kind]
            raw=z.read(item["name"])
            if digest(raw)!=item["sha256"] or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("ATLAS_ATTACHMENT_HASH")
            p=dst/item["name"]
            p.write_bytes(raw);paths.append(p)
    for old in dst.glob("HDAT-*.png"):
        if old not in paths:old.unlink()
    return paths

def parse_decision(body,task):
    decoder=json.JSONDecoder()
    for pos in (m.start() for m in re.finditer(r"\{",body)):
        try:d,_=decoder.raw_decode(body[pos:])
        except ValueError:continue
        if not isinstance(d,dict):continue
        if (d.get("task_id")!=task["task_id"] or d.get("source_dds_sha256")!=task["source_dds_sha256"]
            or d.get("candidate_dds_sha256")!=task["candidate_dds_sha256"]
            or d.get("decision") not in ("PASS_PROVISIONAL","REWORK_REQUIRED","HOLD_EVIDENCE")
            or not isinstance(d.get("reason"),str) or not d["reason"].strip()):continue
        if task["hold_count"] and d["decision"]=="PASS_PROVISIONAL":
            d["decision"]="REWORK_REQUIRED"
            d["reason"]="Unresolved mechanical HOLD present. "+d["reason"]
        # Only contained native source bboxes for HELD ROI, no arbitrary pixels.
        held={r["roi_id"]:r["bbox_xyxy"] for r in task["holds"]}
        proposals=[];seen=set()
        if d["decision"]=="REWORK_REQUIRED" and isinstance(d.get("bbox_proposals"),list):
            for p in d["bbox_proposals"][:64]:
                if not isinstance(p,dict):continue
                rid=p.get("roi_id");b=p.get("bbox_xyxy");old=held.get(rid) if isinstance(rid,str) else None
                if (old and rid not in seen and isinstance(b,list) and len(b)==4 and all(type(x) is int for x in b)
                    and old[0]<=b[0]<b[2]<=old[2] and old[1]<=b[1]<b[3]<=old[3]
                    and b!=old and min(b[2]-b[0],b[3]-b[1])>=8):
                    proposals.append({"roi_id":rid,"bbox_xyxy":b});seen.add(rid)
        return {"task_id":d["task_id"],"source_dds_sha256":d["source_dds_sha256"],
                "candidate_dds_sha256":d["candidate_dds_sha256"],"decision":d["decision"],
                "reason":d["reason"][:1000],"bbox_proposals":proposals}
    return None

def prompt_for(t):
    rows=[{"roi_id":r["roi_id"],"english":r["english"],"korean":r["korean"],"bbox_xyxy":r["bbox_xyxy"],"reason":r["reason"]} for r in t["holds"]]
    return ("OutRun 2006 HD 전체 DDS 한 장 독립 시각 QA. 이미지 생성하지 마세요. "
            "첨부 순서 ORIGINAL / CLEAN / FINAL. 한 DDS만 비교하십시오. "
            "영문 잔상, 원문 제거 마스크, 차량/아이콘 침범, 검은 박스, 한글 과대/잘림/겹침/번역 매핑을 검사. "
            "미번역 HOLD는 통과 금지. 원문과 같은 줄 수, 원문 글자 효과 크기의 95% 이하 목표. "
            "작은 색/그림자 차이는 허용. 이미지 축소 때문에 확신 없으면 HOLD_EVIDENCE. "
            "HOLD 중 원본에 있는 정확한 해당 영문을 찾을 수 있으면 원본 native_size 픽셀 좌표로 기존 bbox 안에 더 좁은 bbox를 제안. "
            "원문 이미지와 좌표가 확실하지 않으면 제안 금지. 실제 적용/게임/C3 승인 아님. "
            "JSON 객체 하나만: task_id, source_dds_sha256, candidate_dds_sha256, decision(PASS_PROVISIONAL/REWORK_REQUIRED/HOLD_EVIDENCE), reason, bbox_proposals([{\"roi_id\":\"...\",\"bbox_xyxy\":[x0,y0,x1,y1]}]).\n"
            +json.dumps({k:t[k] for k in ("task_id","target","source_dds_sha256","candidate_dds_sha256","native_size","orientation","roi_count","painted_count","hold_count")},ensure_ascii=False)
            +"\nHOLD_SOURCE_ROIS="+json.dumps(rows,ensure_ascii=False))

async def atlas_cycle(bridge,home,token,is_saved_chat_url):
    gh=bridge.gh
    pointer,_=await asyncio.to_thread(gh.read_json,QROOT+"/latest.json",BRANCH)
    if pointer is None:return None
    rel=QROOT+"/visual/run-"+str(pointer["run_id"])+".json"
    state,etag=await asyncio.to_thread(gh.read_json,rel,BRANCH)
    if state is None:
        state={"schema":"outrun.hd.atlas-vision-state.v1","run_id":pointer["run_id"],
               "manifest_sha256":pointer["manifest_sha256"],"records":{}}
    if state.get("run_id")!=pointer["run_id"] or state.get("manifest_sha256")!=pointer["manifest_sha256"]:
        raise ValueError("ATLAS_STATE_POINTER_MISMATCH")
    records=state["records"]
    terminal={"DONE","HOLD_SEND_UNCERTAIN","HOLD_RESPONSE_TIMEOUT"}
    if len(records)==104 and all(x.get("status") in terminal for x in records.values()):
        return None
    archive,doc=await asyncio.to_thread(fetch_evidence,pointer,home,token)
    byid={t["task_id"]:t for t in doc["tasks"]}
    if not set(records)<=set(byid):raise ValueError("ATLAS_STATE_TASK_MISMATCH")
    async def save():
        nonlocal etag
        await asyncio.to_thread(gh.write_json,rel,BRANCH,state,etag,etag is not None)
        saved,etag=await asyncio.to_thread(gh.read_json,rel,BRANCH)
        if saved!=state:raise ValueError("ATLAS_STATE_READBACK")
    reviewed=None
    for tid,rec in records.items():
        if rec.get("status")=="CLAIMED":
            # Crash between claim and verified send: never silently re-send.
            rec["status"]="HOLD_SEND_UNCERTAIN";await save()
            return {"status":"ATLAS_SEND_UNCERTAIN_RECORDED","task_id":tid}
        if rec.get("status")=="SENT":
            url=rec.get("chat_url")
            if not is_saved_chat_url(url):raise ValueError("ATLAS_CHAT_URL_INVALID")
            pg=await bridge.page("C1",url,read_only=True)
            if pg is None:return {"status":"ATLAS_WAIT_LOGIN_OR_CHAT","task_id":tid}
            parts=await pg.locator('[data-markdown-text-tone="assistant"],[data-message-author-role="assistant"]').all_inner_texts()
            decision=parse_decision("\n".join(parts[-3:]),byid[tid])
            if decision is None:
                rec["wait_polls"]=int(rec.get("wait_polls",0))+1
                if rec["wait_polls"]>=6:
                    rec["status"]="HOLD_RESPONSE_TIMEOUT"
                    await save()
                    return {"status":"ATLAS_RESPONSE_TIMEOUT_RECORDED","task_id":tid}
                await save()
                return {"status":"ATLAS_WAIT_EXACT_JSON","task_id":tid}
            rec.update(status="DONE",decision=decision);await save()
            reviewed={"task_id":tid,"decision":decision["decision"]}
            break
    t=next((x for x in doc["tasks"] if x["task_id"] not in records),None)
    if t is None:
        # Preserve explicit uncertain receipts. Existing A/B loop can resume;
        # only all-104 DONE permits the feedback generation.
        return {"status":"ATLAS_LAST_REVIEW_SAVED","reviewed":reviewed,"completed":sum(x["status"]=="DONE" for x in records.values()),"total":104} if reviewed else None
    pg=await bridge.page("C1")
    if pg is None:return {"status":"ATLAS_WAIT_LOGIN"}
    paths=await asyncio.to_thread(stage_images,archive,t,home)
    tid=t["task_id"]
    rec={"status":"CLAIMED","target":t["target"],"source_dds_sha256":t["source_dds_sha256"],"candidate_dds_sha256":t["candidate_dds_sha256"]}
    records[tid]=rec
    await save()
    outcome=await bridge.send_with_png(pg,t,prompt_for(t),paths,False)
    if outcome=="CHAT_SENT_VERIFIED" and is_saved_chat_url(pg.url):
        rec.update(status="SENT",chat_url=pg.url)
    elif outcome in ("HOLD_C1_IMAGE_TOOL_SELECTED","HOLD_COMPOSER_ATTACHMENTS_NOT_CLEAR","HOLD_CHAT_UPLOAD_NOT_VERIFIED","HOLD_CHAT_COMPOSER_MARKER_MISSING"):
        # These outcomes occur strictly before Enter; safe to retry next cycle.
        del records[tid]
    else:rec.update(status="HOLD_SEND_UNCERTAIN",send_outcome=outcome)
    await save()
    return {"status":"ATLAS_"+outcome,"task_id":tid,"reviewed":reviewed,"completed":sum(x["status"]=="DONE" for x in records.values()),"total":104}
