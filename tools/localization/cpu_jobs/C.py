#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("This deterministic job must run in the GitHub-hosted localization CPU worker as role C.")

repo = Path.cwd()
run = "20261004-1650-C90"
outdir = repo / "localization/graphics/role_C" / run
outdir.mkdir(parents=True, exist_ok=True)

ASSETS = [
    {
        "key": "19CEDB9",
        "source": "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds",
        "candidate": "localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds",
        "producer_report": "localization/graphics/role_B/20261004-B-RECOVERY04/B_RECOVERY04_19CEDB9_REPORT.json",
        "source_mask": "localization/graphics/role_B/20261004-B-RECOVERY04/19CEDB9_SOURCE_TEXT_MASK.png",
        "clean": "localization/graphics/role_B/20261004-B-RECOVERY04/19CEDB9_CLEAN_PLATE.png",
        "clean_protected": "localization/graphics/role_B/20261004-B-RECOVERY04/19CEDB9_PROTECTED_MASK.png",
        "allowed": "localization/graphics/role_B/20261004-B-RECOVERY04/19CEDB9_ALLOWED_TEXT_REGION_MASK.png",
        "final_protected": "localization/graphics/role_B/20261004-B-RECOVERY04/19CEDB9_PROTECTED_MASK.png",
        "target_mask": "localization/graphics/role_B/20261004-B-RECOVERY04/19CEDB9_TARGET_TEXT_MASK.png",
        "source_sha256": "2472c7aab0751987bd736131b8b4c22be4a7613d9bd1478c9b9f35a615dd6c7e",
        "candidate_sha256": "3090f2664bab3065502b10a98f93d17e92a64a3725dc1b7a4bb790648a5da6e7",
        "expected_rows": 12,
        "return_context": "new hosted exact-HD candidate",
    },
    {
        "key": "2DA43E41",
        "source": "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds",
        "candidate": "localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/2DA43E41_1024x1024.dds",
        "producer_report": "localization/graphics/role_B/20261004-B-RECOVERY05/B_RECOVERY05_2DA43E41_REPORT.json",
        "source_mask": "localization/graphics/role_B/20261004-B-RECOVERY05/2DA43E41_SOURCE_TEXT_MASK_CANONICAL.png",
        "clean": "localization/graphics/role_B/20261004-B-RECOVERY05/2DA43E41_CLEAN_PLATE_CANONICAL.png",
        "clean_protected": "localization/graphics/role_B/20261004-B-RECOVERY05/2DA43E41_PROTECTED_MASK.png",
        "allowed": "localization/graphics/role_B/20261004-B-RECOVERY05/2DA43E41_ALLOWED_TEXT_REGION_MASK.png",
        "final_protected": "localization/graphics/role_B/20261004-B-RECOVERY05/2DA43E41_PROTECTED_MASK.png",
        "target_mask": "localization/graphics/role_B/20261004-B-RECOVERY05/2DA43E41_TARGET_TEXT_MASK.png",
        "source_sha256": "3e00bfda82c2175b28c1d45d3041f91e34ede6de52b867cd867c1c27d4837099",
        "candidate_sha256": "dce31f89fa30da614378d7cfd8e3b9e8b6d39bc037369f059249e358897c66ae",
        "expected_rows": 11,
        "return_context": "C88 canonical-decode visual corruption return repaired by B_RECOVERY05",
    },
    {
        "key": "39229D64",
        "source": "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds",
        "candidate": "localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds",
        "producer_report": "localization/graphics/role_A/20261004-A-RECOVERY06/A_RECOVERY06_39229D64_REPORT.json",
        "source_mask": "localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_SOURCE_TEXT_MASK.png",
        "clean": "localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_CLEAN_PLATE.png",
        "clean_protected": "localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_CLEAN_PLATE_PROTECTED_MASK.png",
        "allowed": "localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_ALLOWED_TEXT_REGION_MASK.png",
        "final_protected": "localization/graphics/role_A/20261004-A-RECOVERY06/39229D64_PROTECTED_MASK.png",
        "target_mask": None,
        "source_sha256": "2f2c19db5a9b7eda058ee380396160e42884760c0d0282d2e75254bf08070481",
        "candidate_sha256": "67d3fab3f00db249a89e59016f33f87d349bc7001f6ece865401fa87b50a3f8a",
        "expected_rows": 15,
        "return_context": "C87 DDS structure + clean-plate evidence return repaired by A_RECOVERY06",
    },
]

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_dds(path):
    p = Path(path)
    data = p.read_bytes()
    if data[:4] != b"DDS ":
        raise RuntimeError(f"not DDS: {p}")
    h = struct.unpack_from("<I", data, 12)[0]
    w = struct.unpack_from("<I", data, 16)[0]
    pitch = struct.unpack_from("<I", data, 20)[0]
    depth = struct.unpack_from("<I", data, 24)[0]
    mips = struct.unpack_from("<I", data, 28)[0]
    pf_flags = struct.unpack_from("<I", data, 80)[0]
    fourcc = data[84:88]
    bpp = struct.unpack_from("<I", data, 88)[0]
    masks = struct.unpack_from("<IIII", data, 92)
    if fourcc != b"\0\0\0\0" or bpp != 32:
        raise RuntimeError(f"unsupported C90 DDS format: {p} fourcc={fourcc!r} bpp={bpp}")
    if masks != (0x000000ff, 0x0000ff00, 0x00ff0000, 0xff000000):
        raise RuntimeError(f"unexpected channel masks: {p} {masks!r}")
    if pitch != w * 4 or len(data) != 128 + w * h * 4:
        raise RuntimeError(f"unexpected RGBA layout: {p}")
    raw = np.frombuffer(data, dtype=np.uint8, offset=128).reshape(h, w, 4).copy()
    readable = np.flipud(raw).copy()
    return {
        "bytes": data,
        "header": data[:128],
        "raw": raw,
        "readable": readable,
        "structure": {
            "width": w, "height": h, "pitch": pitch, "depth": depth, "mips": mips,
            "pf_flags": pf_flags, "fourcc": "00000000", "bpp": bpp,
            "masks": [hex(x) for x in masks],
        },
    }

def load_rgba_png(path, size):
    im = Image.open(path).convert("RGBA")
    if im.size != size:
        raise RuntimeError(f"PNG size mismatch {path}: {im.size} != {size}")
    return np.asarray(im, dtype=np.uint8).copy()

def load_mask(path, size):
    im = Image.open(path).convert("L")
    if im.size != size:
        raise RuntimeError(f"mask size mismatch {path}: {im.size} != {size}")
    return np.asarray(im, dtype=np.uint8) > 0

def bool_bbox(mask):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]

def validate_stage(src, cand, edit, protected):
    diff = np.any(src != cand, axis=2)
    adiff = src[:, :, 3] != cand[:, :, 3]
    return {
        "changed_pixels": int(diff.sum()),
        "changed_bbox": bool_bbox(diff),
        "changed_pixels_outside_edit_mask": int(np.logical_and(diff, np.logical_not(edit)).sum()),
        "changed_pixels_in_protected_mask": int(np.logical_and(diff, protected).sum()),
        "alpha_changed_outside_edit_mask": int(np.logical_and(adiff, np.logical_not(edit)).sum()),
    }

def panel(arr, label, max_w=700, max_h=700):
    im = Image.fromarray(arr, "RGBA")
    bg = Image.new("RGBA", im.size, (64, 64, 64, 255))
    bg.alpha_composite(im)
    v = bg.convert("RGB")
    v.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    f = ImageFont.load_default()
    card = Image.new("RGB", (v.width, v.height + 24), "white")
    card.paste(v, (0, 24))
    ImageDraw.Draw(card).text((5, 5), label, fill="black", font=f)
    return card

def save_full_compare(key, src, clean, final, raw_src, raw_final):
    cards = [
        panel(src, "SOURCE_READABLE"),
        panel(clean, "CLEAN_READABLE"),
        panel(final, "FINAL_READABLE"),
        panel(raw_src, "SOURCE_RAW"),
        panel(raw_final, "FINAL_RAW"),
    ]
    gap = 8
    top_h = max(c.height for c in cards[:3])
    bot_h = max(c.height for c in cards[3:])
    top_w = sum(c.width for c in cards[:3]) + gap * 2
    bot_w = sum(c.width for c in cards[3:]) + gap
    sheet = Image.new("RGB", (max(top_w, bot_w), top_h + bot_h + gap), "white")
    x = 0
    for c in cards[:3]:
        sheet.paste(c, (x, 0)); x += c.width + gap
    x = 0
    for c in cards[3:]:
        sheet.paste(c, (x, top_h + gap)); x += c.width + gap
    sheet.save(outdir / f"C90_{key}_FULL_COMPARE.jpg", quality=93)

def save_row_contact(key, src, clean, final, rows):
    f = ImageFont.load_default()
    cards = []
    for row in rows:
        b = row["original_bbox"]
        pad = 8
        x0 = max(0, int(b[0]) - pad); y0 = max(0, int(b[1]) - pad)
        x1 = min(src.shape[1], int(b[2]) + pad); y1 = min(src.shape[0], int(b[3]) + pad)
        crops = []
        for arr, tag in ((src, "SRC"), (clean, "CLEAN"), (final, "FINAL")):
            im = Image.fromarray(arr[y0:y1, x0:x1], "RGBA")
            bg = Image.new("RGBA", im.size, (70,70,70,255)); bg.alpha_composite(im)
            v = bg.convert("RGB")
            scale = min(2.0, 360 / max(1, v.width), 130 / max(1, v.height))
            if scale != 1.0:
                v = v.resize((max(1,int(v.width*scale)), max(1,int(v.height*scale))), Image.Resampling.NEAREST)
            card = Image.new("RGB", (370, 158), "white")
            card.paste(v, ((370-v.width)//2, 24 + (130-v.height)//2))
            ImageDraw.Draw(card).text((4,4), f"{row['key']} {tag}", fill="black", font=f)
            crops.append(card)
        strip = Image.new("RGB", (370*3+12, 158), "white")
        for i,c in enumerate(crops): strip.paste(c, (i*(370+6), 0))
        cards.append(strip)
    sheet = Image.new("RGB", (cards[0].width, sum(c.height for c in cards)), "white")
    y = 0
    for c in cards:
        sheet.paste(c, (0,y)); y += c.height
    sheet.save(outdir / f"C90_{key}_ROW_CONTACT.jpg", quality=94)

results = []
for spec in ASSETS:
    key = spec["key"]
    source_path = repo / spec["source"]
    candidate_path = repo / spec["candidate"]
    producer_path = repo / spec["producer_report"]
    if sha256(source_path) != spec["source_sha256"]:
        raise RuntimeError(f"{key} source SHA mismatch")
    if sha256(candidate_path) != spec["candidate_sha256"]:
        raise RuntimeError(f"{key} candidate SHA mismatch")

    src_dds = load_dds(source_path)
    cand_dds = load_dds(candidate_path)
    if src_dds["header"] != cand_dds["header"]:
        raise RuntimeError(f"{key} candidate header not exact source header")
    if src_dds["structure"] != cand_dds["structure"]:
        raise RuntimeError(f"{key} structure drift")

    h = src_dds["structure"]["height"]; w = src_dds["structure"]["width"]; size = (w,h)
    src = src_dds["readable"]
    final = cand_dds["readable"]
    clean = load_rgba_png(repo / spec["clean"], size)
    source_mask = load_mask(repo / spec["source_mask"], size)
    clean_protected = load_mask(repo / spec["clean_protected"], size)
    allowed = load_mask(repo / spec["allowed"], size)
    final_protected = load_mask(repo / spec["final_protected"], size)
    target = load_mask(repo / spec["target_mask"], size) if spec["target_mask"] else None

    producer = json.loads(producer_path.read_text(encoding="utf-8"))
    rows = producer["rows"]
    if len(rows) != spec["expected_rows"]:
        raise RuntimeError(f"{key} row count {len(rows)} != {spec['expected_rows']}")

    clean_gate = validate_stage(src, clean, source_mask, clean_protected)
    final_gate = validate_stage(src, final, allowed, final_protected)
    clean_mask_protected_overlap = int(np.logical_and(source_mask, clean_protected).sum())
    allowed_protected_overlap = int(np.logical_and(allowed, final_protected).sum())

    row_union = np.zeros((h,w), dtype=bool)
    row_checks = []
    edge_touch = []
    for row in rows:
        ob = [int(x) for x in row["original_bbox"]]
        lb = [int(x) for x in row.get("localized_bbox", row.get("localized_changed_bbox"))]
        contained = ob[0] <= lb[0] and ob[1] <= lb[1] and lb[2] <= ob[2] and lb[3] <= ob[3]
        if not contained or row.get("containment") != "PASS":
            raise RuntimeError(f"{key} bbox fail {row['key']}: {ob} {lb}")
        row_union[ob[1]:ob[3], ob[0]:ob[2]] = True
        deltas = [lb[0]-ob[0], ob[2]-lb[2], lb[1]-ob[1], ob[3]-lb[3]]
        if min(deltas) == 0:
            edge_touch.append(row["key"])
        row_checks.append({
            "key": row["key"],
            "original_bbox": ob,
            "localized_bbox": lb,
            "delta_left": deltas[0],
            "delta_right": deltas[1],
            "delta_top": deltas[2],
            "delta_bottom": deltas[3],
            "containment": "PASS",
            "rework_status": row.get("rework_status", "PRODUCER_RESULT_RECHECKED"),
        })

    allowed_outside_row_union = int(np.logical_and(allowed, np.logical_not(row_union)).sum())
    target_outside_allowed = int(np.logical_and(target, np.logical_not(allowed)).sum()) if target is not None else None
    target_in_protected = int(np.logical_and(target, final_protected).sum()) if target is not None else None

    machine_pass = (
        clean_gate["changed_pixels_outside_edit_mask"] == 0 and
        clean_gate["changed_pixels_in_protected_mask"] == 0 and
        clean_gate["alpha_changed_outside_edit_mask"] == 0 and
        final_gate["changed_pixels_outside_edit_mask"] == 0 and
        final_gate["changed_pixels_in_protected_mask"] == 0 and
        final_gate["alpha_changed_outside_edit_mask"] == 0 and
        clean_mask_protected_overlap == 0 and
        allowed_protected_overlap == 0 and
        allowed_outside_row_union == 0 and
        (target_outside_allowed in (None,0)) and
        (target_in_protected in (None,0))
    )
    if not machine_pass:
        raise RuntimeError(f"{key} C90 machine gate failed")

    save_full_compare(key, src, clean, final, src_dds["raw"], cand_dds["raw"])
    save_row_contact(key, src, clean, final, rows)

    results.append({
        "asset": key,
        "source_path": spec["source"],
        "candidate_path": spec["candidate"],
        "producer_report": spec["producer_report"],
        "source_sha256": spec["source_sha256"],
        "candidate_sha256": spec["candidate_sha256"],
        "return_context": spec["return_context"],
        "structure": {**src_dds["structure"], "header_128_exact_to_source": True, "raw_orientation": "mirror_y"},
        "clean_plate_gate": {**clean_gate, "status": "PASS"},
        "final_candidate_gate": {**final_gate, "status": "PASS"},
        "mask_consistency": {
            "source_text_protected_overlap_pixels": clean_mask_protected_overlap,
            "allowed_protected_overlap_pixels": allowed_protected_overlap,
            "allowed_pixels_outside_union_of_original_bboxes": allowed_outside_row_union,
            "target_pixels_outside_allowed": target_outside_allowed,
            "target_pixels_in_protected": target_in_protected,
            "status": "PASS",
        },
        "bbox_gate": {
            "elements": len(row_checks),
            "pass": len(row_checks),
            "fail": 0,
            "edge_touch_keys": edge_touch,
            "rows": row_checks,
            "status": "PASS",
        },
        "visual_evidence": {
            "full_compare": f"localization/graphics/role_C/{run}/C90_{key}_FULL_COMPARE.jpg",
            "row_contact": f"localization/graphics/role_C/{run}/C90_{key}_ROW_CONTACT.jpg",
            "controller_visual_qa": "PENDING",
        },
        "runtime_validation": "UNTESTED",
        "machine_decision": "STATIC_MACHINE_PASS_PENDING_CONTROLLER_VISUAL_QA",
    })

base_head = subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip()
report = {
    "schema_version": 1,
    "role": "C",
    "run": run,
    "base_head": base_head,
    "scope": "new shared-state pending-C candidates only; C88/C89-completed assets not repeated",
    "assets": results,
    "summary": {
        "assets_checked": len(results),
        "machine_pass": len(results),
        "machine_fail": 0,
        "runtime_validation": "UNTESTED",
        "vr_ffb_dx11_dxvk_changes": False,
    },
}
(outdir / "C90_HOSTED_STATIC_QA.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("C90_HOSTED_STATIC_QA_DONE", [x["asset"] for x in results])
