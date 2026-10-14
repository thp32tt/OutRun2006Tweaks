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

SOURCE_DIR = "inputs/A/HD_EN_TILES_20261014"
STATE_DIR = "ab_batches"
LIBRARY_FOLDER = "아웃런 한글화 신규"
QUARANTINED = "Q046_AA04D779_BASE_READABLE_FLIPY__r03c01__x0_y1340__683x708.png"
RANGES = {"A": (1, 500), "B": (501, 986)}
SLOTS = {"A": (0, 10, 20, 30, 40, 50), "B": (5, 15, 25, 35, 45, 55)}
SIZE = 5
MAX_ROLLING_UPLOADS = 75  # Account upload cap may be stricter.

def state_path(root, role):
    return Path(root) / STATE_DIR / (role + "_state.json")

def _now():
    return dt.datetime.now(dt.timezone.utc)

def _read_sources(root):
    root = Path(root)
    tiles = _csv(root / SOURCE_DIR / "ALL_TILE_MAPPING.csv")
    if len(tiles) != 986 or len({r["part_filename"] for r in tiles}) != 986:
        raise ValueError("EXPECTED_EXACT_986_ORIGINAL_ORDINALS")
    originals = _csv(root / SOURCE_DIR / "SOURCE_MANIFEST_108.csv")
    if len(originals) != 108:
        raise ValueError("EXPECTED_EXACT_108_DDS")
    by_dds = {r["source_dds_path"]: r for r in originals}
    trans = {}
    for row in _csv(root / SOURCE_DIR / "OUTRUN_HD_FULL_TRANSLATION_MAPPING_20261013.csv"):
        en, ko = row["english_source"].strip(), row["korean_approved"].strip()
        if en and ko:
            value = (en, ko, row.get("protected_original", "[]"))
            bag = trans.setdefault(row["queue_index"], [])
            if value not in bag:bag.append(value)
    return tiles, by_dds, trans

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
    name = source_row["part_filename"]
    if name != Path(name).name or not name.endswith(".png"):
        raise ValueError("INVALID_SOURCE_FILENAME")
    parent = original.get(source_row["source_dds_path"])
    if parent is None or not re.fullmatch(r"[0-9a-f]{64}", parent["dds_sha256"]):
        raise ValueError("UNKNOWN_DDS_SOURCE:" + name)
    source_path = Path(src) / name
    size = (int(source_row["width"]), int(source_row["height"]))
    _sha_png(source_path, source_row["part_png_sha256"], size)
    direction = resolve_upright_source(Path(src).parents[2], source_row, source_path)
    _sha_png(Path(direction["path"]), direction["sha256"], size)
    return {
        "ordinal": ordinal, "filename": name,
        "output_filename": name[:-4] + "_k.png", "path": direction["path"],
        "sha256": direction["sha256"],
        "source_png_sha256": source_row["part_png_sha256"],
        "source_dds_sha256": parent["dds_sha256"],
        "source_dds_path": source_row["source_dds_path"],
        "source_to_upright": direction["source_to_upright"],
        "upright_to_source": direction["upright_to_source"],
        "working_orientation": "READABLE_UPRIGHT",
        "width": size[0], "height": size[1],
        "queue_indexes": source_row["queue_indexes"],
        "x": int(source_row["x"]), "y": int(source_row["y"]),
    }

def _prompt(role, batch_id, tiles, translations):
    p = [
        "@이미지 생성 — OutRun 2006 HD GUI 독립 이미지 한글화",
        f"RUN_SLOT={role}; BATCH_ID={batch_id}; BATCH_COUNT={len(tiles)}; LIBRARY_FOLDER={LIBRARY_FOLDER}",
        "위 식별자는 추적용입니다. 생성 이미지에 표시하지 마세요.",
        "",
        "최우선 필수 규칙: 첨부된 영어 원본 PNG 각각을 '개별 편집 이미지'로 변환하세요.",
        f"입력 이미지 {len(tiles)}개 → 서로 분리된 결과 이미지 정확히 {len(tiles)}개.",
        "한 이미지를 다섯 영역으로 나누거나 합치기, 콜라주, 접합, 스프라이트 시트, 비교판, 설명용 목업은 절대 생성하지 마세요.",
        "원본 PNG 1개당 결과 PNG 1개이며, 출력 이미지마다 다른 입력 파일의 내용이 섞이면 실패입니다.",
        "문자 이외의 모든 픽셀은 가능한 한 보존하고 원본 아이콘·버튼·테두리·패턴·레이아웃을 임의로 다시 그리지 마세요.",
        "원본 캔버스의 폭/높이/비율 및 RGBA 투명 알파, 텍스트 색, 질감, 하이라이트, 그림자, 테두리, 경사를 최대한 재현하세요.",
        "화면에 실제로 보이는 영어 UI 텍스트만 승인 번역으로 대체합니다. 보이지 않는 문구는 새로 만들지 마세요.",
        "자동차 제조사명, 자동차 모델, 브랜드 로고, 노래 제목, 고유명사는 원문 그대로 보존하세요.",
        "글자가 다른 UI를 침범하거나 원래 글자 영역 밖으로 1px이라도 벗어나지 않게 하세요. 글자끼리 겹치면 안 됩니다.",
        "참조 이미지는 사람이 읽는 정방향입니다. 한국어 글자도 동일하게 정상 방향으로 생성하세요. 새 상하반전 금지.",
        f"이 채팅이 속한 프로젝트 '{LIBRARY_FOLDER}'의 프로젝트 라이브러리에 생성한 PNG 이미지를 각각 저장하세요.",
        "별도의 outrun_kor 라이브러리 폴더를 생성하거나 이동하려 하지 마세요. 기존 프로젝트 라이브러리를 사용합니다.",
        "이미지가 프로젝트 라이브러리에 실제 기록되지 않았다면 저장 성공이라고 주장하지 마세요.",
        "저장 이름은 원본 영문 파일명에서 .png 앞에 소문자 _k를 삽입하세요. 이름 변경이 불가능하면 실제 이름을 알려주세요.",
        "결과를 단순 설명문이나 코드로 대체하지 마세요. 총 결과 이미지 개수를 우선 충족해야 합니다.",
        "입력/생성 수량·라이브러리 저장이 불충분하면 임의 성공 선언 금지.",
        "",
        "파일별 정확한 작업 대상:",
    ]
    grouped = {}
    for i, item in enumerate(tiles, 1):
        p.append(f"[{i}/{len(tiles)}] #{item['ordinal']:03d} {item['filename']}")
        p.append(f"  정방향 캔버스 {item['width']}x{item['height']}, 결과명 {item['output_filename']}")
        p.append(f"  원본 DDS {item['source_dds_path']}")
        group_key = tuple(sorted(re.findall(r"\d+", item["queue_indexes"])))
        grouped.setdefault(group_key, [])
        for key in group_key:
            for val in translations.get(str(int(key)), []):
                if val not in grouped[group_key]:grouped[group_key].append(val)
    p.append("")
    p.append("공식 영문→한국어 번역표(해당 타일에 보이는 문구만 적용):")
    for keys, entries in grouped.items():
        p.append("queue_indexes=" + ",".join(keys))
        for en, ko, protected in entries:
            p.append(f"  {en} → {ko}")
            if protected not in ("", "[]"):
                p.append("  보호 문구 원문 유지: " + protected)
    p.append("")
    p.append(f"최종 확인: {len(tiles)}개 입력 각각 별개 이미지 {len(tiles)}장. 결합하지 말 것. 프로젝트 '{LIBRARY_FOLDER}'의 Library에 각 이미지 저장을 확인할 것.")
    prompt = "\n".join(p)
    if len(prompt) > 26000:
        raise ValueError("BATCH_PROMPT_TOO_LONG")
    return prompt

def next_binding(role, root="/data/imagegen"):
    """Make one immutable batch reservation per role. No implicit retry of sent work."""
    root = Path(root).resolve()
    if role not in RANGES:
        return None, "INVALID_SLOT"
    if os.getenv("OUTRUN_AB_BATCH_QUEUE", "false").lower() != "true":
        return None, "AB_QUEUE_DISABLED"
    if os.getenv("OUTRUN_AB_BATCH_SIZE", "5") != "5":
        return None, "BATCH_SIZE_MUST_BE_FIVE"
    if os.getenv("OUTRUN_AB_LIBRARY_FOLDER", LIBRARY_FOLDER) != LIBRARY_FOLDER:
        return None, "LIBRARY_FOLDER_CONFIG_MISMATCH"
    try:
        state = _state(root, role)
        previous = state["active"]
        if previous and previous["status"] != "STAGED":
            return None, "BATCH_AWAITING_RESULT_AND_LIBRARY:" + previous["task_id"]
        if not previous and state["next_ordinal"] > RANGES[role][1]:
            return None, "SLOT_RANGE_FINISHED"
        if not previous and _count_recent(root) + SIZE > MAX_ROLLING_UPLOADS:
            return None, "SHARED_ROLLING_UPLOAD_QUOTA_HOLD"
        rows, originals, trans = _read_sources(root)
        _, high = RANGES[role]
        picked = []
        excluded = []
        ordinal = state["next_ordinal"]
        if previous:
            ordinal_list = previous["ordinals"]
            task_id = previous["task_id"]
            ordinal = previous["next_ordinal_after"]
            if (root / "sent" / (role + "_" + task_id + ".json")).exists():
                return None, "STAGED_TASK_HAS_SENT_RECEIPT"
            for position in ordinal_list:
                if not (RANGES[role][0] <= position <= high):
                    raise ValueError("PREVIOUS_BATCH_RANGE_MISMATCH")
                picked.append(_filemap(rows[position-1],position,root / SOURCE_DIR,originals))
            if [p["filename"] for p in picked] != [p["filename"] for p in previous["items"]]:
                raise ValueError("PREVIOUS_BATCH_SOURCE_CHANGED")
        else:
            while ordinal <= high and len(picked) < SIZE:
                row = rows[ordinal - 1]  # Preserve original 986-ordinal mapping.
                if row["part_filename"] == QUARANTINED:
                    excluded.append({"ordinal": ordinal, "filename": row["part_filename"], "status": "REWORK_PNG_CORRUPT"})
                    ordinal += 1
                    continue
                picked.append(_filemap(row, ordinal, root / SOURCE_DIR, originals))
                ordinal += 1
            if not picked:
                state["next_ordinal"] = ordinal
                state["quarantined"].extend(excluded)
                state["status"] = "SLOT_RANGE_FINISHED"
                _atomic_json(state_path(root, role), state)
                return None, "SLOT_RANGE_FINISHED_WITH_QUARANTINE"
            batch_number = state["completed_batches"] + 1
            task_id = f"OUTRUN-AB-{role}-{batch_number:04d}-20261014"
            if (root / "sent" / (role + "_" + task_id + ".json")).exists():
                return None, "TASK_ID_COLLISION"
        prompt = _prompt(role, task_id, picked, trans)
        if not previous:
            active = {
                "task_id": task_id, "role": role,
                "ordinals": [p["ordinal"] for p in picked],
                "next_ordinal_after": ordinal, "count": len(picked),
                "items": [{key:value for key,value in it.items() if key != "path"} for it in picked],
                "created_at": _now().isoformat(), "status": "STAGED",
                "source_chat_url": None,
            }
            state["active"] = active
            state["quarantined"].extend(excluded)
            state["status"] = "STAGED"
            _atomic_json(state_path(root, role), state)
        return {
            "role": role, "task_id": task_id, "path": picked[0]["path"],
            "paths": [p["path"] for p in picked],
            "png_sha256": picked[0]["sha256"],
            "source_dds_sha256": picked[0]["source_dds_sha256"],
            "prompt": prompt, "items": picked,
            "tiles": [{"filename":p["filename"],"sha256":p["sha256"],
                      "ordinal":p["ordinal"],"output_filename":p["output_filename"]}
                     for p in picked],
            "expected_images": len(picked), "library_folder": LIBRARY_FOLDER,
        }, None
    except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
        return None, "AB_QUEUE_INPUT_ERROR:" + str(exc)[:150]

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
    if not active.get("source_chat_url"):
        return False, "CHAT_URL_NOT_RECORDED"
    if page.url.rstrip("/") != active["source_chat_url"].rstrip("/"):
        return False, "ACTIVE_CHAT_NOT_OPEN"
    expected=active["count"]
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
        return False, "IMAGEGEN_OUTPUT_COUNT_MISMATCH:"+str(result.get("count"))+"/"+str(expected)
    try:
        export_status=await export_unapproved_k_candidates(page,active,root)
    except Exception as exc:
        return False, "GENERATED_CANDIDATE_EXPORT_UNVERIFIED:"+str(exc)[:110]
    evidence=root/STATE_DIR/"generated_visible"/(task+".json")
    evidence.parent.mkdir(parents=True,exist_ok=True)
    _atomic_json(evidence,{"task_id":task,"role":role,"distinct_generated_images":expected,
                           "verification_method":result.get("verified_by"),
                           "status":"IMAGES_VISIBLE_NOT_LIBRARY_PROOF",
                           "export_status":export_status,"checked_at":_now().isoformat()})
    verified, reason=_library_confirmed(root,active)
    if not verified:
        # Inspect ChatGPT's actual existing project Library (no extra folder).
        # The verifier opens a disposable read-only tab and matches every PNG
        # by full SHA256 to this batch's five generated image carousel blobs.
        try:
            from app.project_library_gate import verify_project_library_images
        except ModuleNotFoundError:
            from project_library_gate import verify_project_library_images
        proof, error = await verify_project_library_images(page,active)
        if error or not proof:
            return False,"PROJECT_LIBRARY_NOT_VERIFIED:"+str(error or "NO_PROOF")
        _atomic_json(_library_evidence_path(root,task),proof)
        verified,reason=_library_confirmed(root,active)
        if not verified:
            return False,reason
    st["next_ordinal"]=active["next_ordinal_after"]
    st["completed_files"]+=active["count"]
    st["completed_batches"]+=1
    st["active"]=None
    st["status"]="BATCH_COMPLETE_LIBRARY_VERIFIED"
    _atomic_json(state_path(root,role),st)
    return True, "BATCH_COMPLETE_LIBRARY_VERIFIED"

def expected_counts(root):
    """Inspection summary, never count raw/hash-only files as translated."""
    return {role:_state(root,role) for role in RANGES}