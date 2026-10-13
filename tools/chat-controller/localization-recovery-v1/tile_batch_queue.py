"""Deterministic 5-tile, 10-minute A queue; no paid API, no fabricated imagegen PASS.

Only advance after five *separate* visible assistant images follow the exact user
batch ID. Saved ChatGPT-generated images appear automatically in Images/Library.
This module cannot independently verify Library persistence or image-pixel QA.
"""
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import zlib

TILE_DIR = "inputs/A/HD_EN_TILES_20261014"
STATE_NAME = "a_tile_batches/state.json"
SOURCE_CSV = "SOURCE_MANIFEST_108.csv"
MAX_UPLOADS_3H = 75
MAX_BATCH = 5


def _csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _now():
    return dt.datetime.now(dt.timezone.utc)


def _atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _sha_png(path, expected, size):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("PNG_MISSING_OR_OVERSIZE:" + path.name)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("PNG_SHA_MISMATCH:" + path.name)
    if len(raw) < 45 or raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR":
        raise ValueError("BAD_PNG_HEADER:" + path.name)
    w, h = struct.unpack(">II", raw[16:24])
    if (w, h) != size or not (1 <= w <= 1024 and 1 <= h <= 1024):
        raise ValueError("PNG_SIZE_MISMATCH:" + path.name)
    offset, has_idat, ended = 8, False, False
    while offset + 12 <= len(raw):
        amount = struct.unpack_from(">I", raw, offset)[0]
        end = offset + amount + 12
        if amount > 32 * 1024 * 1024 or end > len(raw):
            raise ValueError("PNG_LENGTH_BAD:" + path.name)
        typ = raw[offset + 4:offset + 8]
        crc, = struct.unpack_from(">I", raw, end - 4)
        if zlib.crc32(raw[offset + 4:end - 4]) != crc:
            raise ValueError("PNG_CRC_BAD:" + path.name)
        if typ == b"IDAT":
            has_idat = True
        if typ == b"IEND":
            ended = amount == 0 and end == len(raw)
            break
        offset = end
    if not has_idat or not ended:
        raise ValueError("PNG_INCOMPLETE:" + path.name)
    return len(raw)


def _source_rows(root):
    d = root / TILE_DIR
    mapping = _csv(d / "ALL_TILE_MAPPING.csv")
    if len(mapping) != 986 or len({r["part_filename"] for r in mapping}) != 986:
        raise ValueError("TILE_MANIFEST_EXPECTED_986")
    # N100 independent PNG CRC audit: 985 valid, one source tile truncated at IDAT.
    # Quarantine this exact tile; never mark it translated or silently alter its bytes.
    # Keep this mapping exclusion stable across restarts (manual repair = new QA task).
    corrupt_tile = "Q046_AA04D779_BASE_READABLE_FLIPY__r03c01__x0_y1340__683x708.png"
    mapping = [r for r in mapping if r["part_filename"] != corrupt_tile]
    originals = _csv(d / SOURCE_CSV)
    source_by_path = {r["source_dds_path"]: r for r in originals}
    if len(originals) != 108:
        raise ValueError("SOURCE_MANIFEST_EXPECTED_108")
    translation = _csv(d / "OUTRUN_HD_FULL_TRANSLATION_MAPPING_20261013.csv")
    by_index = {}
    for r in translation:
        en, ko = r["english_source"].strip(), r["korean_approved"].strip()
        if en and ko:
            by_index.setdefault(r["queue_index"], []).append((en, ko, r.get("protected_original", "[]")))
    if not by_index:
        raise ValueError("EMPTY_OFFICIAL_TRANSLATION_TABLE")
    return mapping, source_by_path, by_index


def _prompt(items):
    lines = [
        f"OutRun 2006 HD GUI 영어 원본 PNG 타일 {len(items)}개를 각각 별도의 한국어 이미지 {len(items)}장으로 편집하세요.",
        f"합성 이미지, 콜라주, 새 UI 디자인 금지. 입력 1개당 출력 1개만, 총 {len(items)}개 개별 PNG 결과.",
        "파일명을 대응시켜 정확히 영문 UI 글자만 한국어로 번역합니다.",
        "원본 해상도(각 파일 최대 1024x1024), RGBA 알파, 캔버스, 아이콘, 버튼, 테두리, 광택, 경사, 그림자 보존.",
        "음악 제목, 자동차/회사/브랜드명, 고유명사는 원어 그대로. 원본 glyph/effect bbox 밖으로 확장하거나 다른 글자에 겹치지 않기.",
        "아래 공식 번역표 중 해당 타일에서 실제 보이는 문구만 교체하세요. 글자가 없는 타일은 변경 없이 그대로 두세요.",
        "각 출력은 같은 파일명에 _KOR 를 붙인 이름으로 구분하고 개별 이미지로 제시하세요.",
        "제작할 수 없는 타일은 어떤 타일인지 밝혀주고 임의의 대체 이미지는 만들지 마세요.",
    ]
    per_source = {}
    for i, item in enumerate(items, 1):
        lines.append(f"\n[{i}/{len(items)}] {item['filename']} ({item['width']}x{item['height']}, queue={item['queue_indexes']})")
        per_source.setdefault(item["queue_indexes"], item["translations"])
    lines.append("\n[공식 영한 번역표 / 같은 queue는 모든 해당 타일에 적용]")
    for queue_name, translations in per_source.items():
        lines.append("queue " + queue_name + ":")
        for en, ko, protected in translations:
            lines.append(f"  {en} => {ko}")
            if protected not in ("", "[]"):
                lines.append("  protected original: " + protected)
    return "\n".join(lines)


def _recent_files(root, now):
    count = 0
    for path in (root / "sent").glob("A_OUTRUN-A-HD5-*.json"):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            when = dt.datetime.fromisoformat(row["submitted_at"].replace("Z", "+00:00"))
            if when.tzinfo is None:
                continue
            if dt.timedelta(0) <= now - when < dt.timedelta(hours=3):
                count += len(row.get("tiles", []))
        except (ValueError, KeyError, OSError):
            continue
    return count


def prepare_next_binding(root):
    root = Path(root).resolve()
    if os.environ.get("OUTRUN_A_TILE_BATCH_QUEUE", "false").lower() != "true":
        return None, "BATCH_QUEUE_DISABLED"
    folder = root / TILE_DIR
    if not folder.is_dir():
        return None, "TILE_DIR_MISSING"
    state_path = root / STATE_NAME
    try:
        mapping, original, translated = _source_rows(root)
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
        else:
            state = {"version": 1, "offset": 0, "active": None, "completed": 0}
        if state.get("version") != 1:
            return None, "BATCH_STATE_VERSION_UNEXPECTED"
        active = state.get("active")
        if active:
            sent_file = root / "sent" / ("A_" + active["task_id"] + ".json")
            if sent_file.exists():
                return None, "WAITING_FOR_FIVE_GENERATED_IMAGES"
            indexes = active["indexes"]
        else:
            if state["offset"] >= len(mapping):
                return None, "ALL_TILES_SUBMITTED_AND_RESULT_VISIBLE"
            # ChatGPT rolling file-upload limit is 80 per 3 hours. Cap at 75.
            if _recent_files(root, _now()) + MAX_BATCH > MAX_UPLOADS_3H:
                return None, "UPLOAD_RATE_WINDOW_HOLD"
            indexes = list(range(state["offset"], min(state["offset"] + MAX_BATCH, len(mapping))))
            # Stable sequence and task ID; prevent duplicates across controller restarts.
            task_id = "OUTRUN-A-HD5-" + str(state["offset"] // MAX_BATCH + 1).zfill(4) + "-20261014"
            active = {"task_id": task_id, "indexes": indexes, "created_at": _now().isoformat()}
            state["active"] = active
            _atomic_json(state_path, state)
        task = active["task_id"]
        if (root / "sent" / ("A_" + task + ".json")).exists():
            return None, "ALREADY_SENT_WAIT_FOR_GENERATION"
        items = []
        for idx in indexes:
            row = mapping[idx]
            name = row["part_filename"]
            if name != Path(name).name or not name.endswith(".png"):
                raise ValueError("INVALID_TILE_NAME")
            base = original.get(row["source_dds_path"])
            if base is None or not re.fullmatch(r"[0-9a-f]{64}", base["dds_sha256"]):
                raise ValueError("DDS_MAPPING_MISSING:" + name)
            keys = re.findall(r"\d+", row["queue_indexes"])
            tr = []
            seen = set()
            for key in keys:
                for en, ko, protect in translated.get(str(int(key)), []):
                    if (en, ko) not in seen:
                        seen.add((en, ko))
                        tr.append((en, ko, protect))
            path = folder / name
            _sha_png(path, row["part_png_sha256"], (int(row["width"]), int(row["height"])))
            items.append({
                "filename": name, "path": str(path), "sha256": row["part_png_sha256"],
                "source_dds_path": row["source_dds_path"],
                "source_dds_sha256": base["dds_sha256"],
                "queue_indexes": row["queue_indexes"], "width": int(row["width"]),
                "height": int(row["height"]), "translations": tr,
            })
        prompt = _prompt(items)
        if len(prompt) > 25000:
            return None, "APPROVED_PROMPT_TOO_LONG"
        return {
            "role": "A", "task_id": task, "path": items[0]["path"],
            "paths": [r["path"] for r in items],
            "png_sha256": items[0]["sha256"],
            "source_dds_sha256": items[0]["source_dds_sha256"],
            "prompt": prompt, "tiles": [
                {k: v for k, v in row.items() if k != "translations"}
                for row in items
            ],
            "expected_images": len(items),
        }, None
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        return None, "BATCH_INPUT_ERROR:" + str(exc)[:120]


async def confirm_visible_results(page, root):
    """Non-destructive result probe: require all distinct loaded assistant images."""
    root = Path(root).resolve()
    state_path = root / STATE_NAME
    if not state_path.exists():
        return "NO_BATCH_STATE"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        active = state.get("active")
        if not active:
            return "NO_BATCH_PENDING"
        sent_file = root / "sent" / ("A_" + active["task_id"] + ".json")
        if not sent_file.is_file():
            return "BATCH_NOT_SUBMITTED"
        receipt = json.loads(sent_file.read_text(encoding="utf-8"))
        if receipt.get("status") != "CHAT_MESSAGE_SENT_ATTACHMENT_UI_VERIFIED_NOT_IMAGEGEN_PASS":
            return "UNVERIFIED_SUBMISSION_HOLD"
        expected = len(active["indexes"])
        # Count visible *assistant* images after the exact user batch message.
        result = await page.evaluate("""({taskId,expected}) => {
           const msg=[...document.querySelectorAll('[data-message-author-role]')];
           const userIndex=msg.findIndex(n=>n.getAttribute('data-message-author-role')==='user'
                        && (n.innerText||'').includes('UPLOAD_TASK_ID='+taskId));
           if(userIndex<0)return {status:'NO_USER_REQUEST'};
           const later=msg.slice(userIndex+1).filter(n=>n.getAttribute('data-message-author-role')==='assistant');
           const imgs=later.flatMap(n=>[...n.querySelectorAll('img')])
                .filter(i=>i.complete&&i.naturalWidth>0&&i.naturalHeight>0&&i.getClientRects().length>0);
           return {status:imgs.length>=expected?'RESULTS_VISIBLE':'RESULTS_NOT_YET_VISIBLE',count:imgs.length};
        }""", {"taskId": active["task_id"], "expected": expected})
        if result.get("status") != "RESULTS_VISIBLE":
            return "WAITING:" + str(result.get("count", 0)) + "/" + str(expected)
        proof = root / "a_tile_batches" / "visible_results" / (active["task_id"] + ".json")
        _atomic_json(proof, {
            "task_id": active["task_id"], "input_count": expected,
            "assistant_images_visible": result["count"],
            "status": "IMAGES_VISIBLE_LIBRARY_AND_PIXEL_QA_UNVERIFIED",
            "observed_at": _now().isoformat()
        })
        state["offset"] += expected
        state["completed"] += expected
        state["active"] = None
        _atomic_json(state_path, state)
        return "BATCH_IMAGES_VISIBLE_CONFIRMED"
    except Exception as exc:
        return "BATCH_RESULT_PROBE_ERROR:" + str(exc)[:120]