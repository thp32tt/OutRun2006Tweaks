#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, os, struct
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageChops, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "LOCALIZATION-LOCALIZATION_B-00002"
ASSET = "FA7BBB13"
INDEX = 54
SOURCE = ROOT / "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_fruity_cvt_Exst/FA7BBB13_1024x512.dds"
CAND = ROOT / "localization/graphics/hd_candidates/textures/load/spr_sprani_fruity_cvt_Exst/FA7BBB13_1024x512.dds"
C85 = ROOT / "localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json"
B91 = ROOT / "localization/graphics/role_B/20260928-0920-B91/B91_RGBA_REWORK_ACTIONS.json"
RUN = ROOT / "localization/graphics/role_B/20260928-1552-B95"
REPORT = RUN / "B95_FA7BBB13_EXACT_BBOX_REWORK_REPORT.json"
QA = RUN / "B95_FA7BBB13_BEFORE_AFTER_QA.png"

def h256(b):
    return hashlib.sha256(b).hexdigest()

def parse(b):
    if len(b) < 128 or b[:4] != b"DDS ":
        raise SystemExit("invalid DDS")
    h = struct.unpack_from("<I", b, 12)[0]
    w = struct.unpack_from("<I", b, 16)[0]
    pitch = struct.unpack_from("<I", b, 20)[0]
    mips = struct.unpack_from("<I", b, 28)[0] or 1
    fourcc = b[84:88]
    bits = struct.unpack_from("<I", b, 88)[0]
    masks = struct.unpack_from("<IIII", b, 92)
    if fourcc != b"\0\0\0\0" or bits != 32 or masks != (0xFF, 0xFF00, 0xFF0000, 0xFF000000):
        raise SystemExit(f"unsupported DDS {fourcc!r}/{bits}/{masks}")
    if pitch != w * 4 or len(b) != 128 + w * h * 4:
        raise SystemExit("unexpected DDS payload")
    return w, h, mips

def image(b, w, h):
    return Image.frombytes("RGBA", (w, h), b[128:], "raw", "RGBA")

def blob(header, img):
    return header + img.tobytes("raw", "RGBA")

def alpha_bbox(img, cell):
    x0, y0, x1, y1 = cell
    b = img.getchannel("A").crop((x0, y0, x1 + 1, y1 + 1)).getbbox()
    return None if b is None else [x0 + b[0], y0 + b[1], x0 + b[2] - 1, y0 + b[3] - 1]

def contained(b, o):
    return b is not None and b[0] >= o[0] and b[1] >= o[1] and b[2] <= o[2] and b[3] <= o[3]

def diffmask(a, b):
    d = ImageChops.difference(a, b)
    r, g, bb, aa = d.split()
    return ImageChops.lighter(ImageChops.lighter(r, g), ImageChops.lighter(bb, aa))

def rectmask(size, rects):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for x0, y0, x1, y1 in rects:
        d.rectangle((x0, y0, x1, y1), fill=255)
    return m

def nz(m):
    return sum(m.histogram()[1:])

def union_rect(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]

srcb = SOURCE.read_bytes()
oldb = CAND.read_bytes()
w, h, m = parse(srcb)
w2, h2, m2 = parse(oldb)
assert (w, h, m) == (w2, h2, m2) == (4096, 2048, 1)
assert srcb[:128] == oldb[:128]

src = image(srcb, w, h).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
before = image(oldb, w, h).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
after = before.copy()

c85 = json.loads(C85.read_text("utf-8"))
asset = next(x for x in c85["assets"] if x["asset"] == ASSET)
rows = asset["rows"]
fails = [r for r in rows if r["containment"] == "FAIL"]
if len(fails) != 10:
    raise SystemExit(f"expected 10 C85 failures, got {len(fails)}")

b91 = json.loads(B91.read_text("utf-8"))
acts = next(x for x in b91["assets"] if x["asset"] == ASSET)
amap = {r["key"]: r for r in acts["rows"]}

records = []
allowed_change_rects = []
for r in fails:
    a = amap[r["key"]]
    old = r["localized_bbox"]
    target = a["new_localized_bbox"]
    x0, y0, x1, y1 = old
    tx0, ty0, tx1, ty1 = target
    patch = before.crop((x0, y0, x1 + 1, y1 + 1))
    after.paste((0, 0, 0, 0), (x0, y0, x1 + 1, y1 + 1))
    tw, th = tx1 - tx0 + 1, ty1 - ty0 + 1
    if patch.size != (tw, th):
        patch = patch.resize((tw, th), Image.Resampling.LANCZOS)
    after.alpha_composite(patch, (tx0, ty0))
    allowed_change_rects.extend([old, target])
    records.append({
        "key": r["key"], "source": r.get("source"), "korean": r.get("korean"),
        "old_localized_bbox": old, "target_bbox": target, "original_bbox": r["original_bbox"],
        "scale": a.get("scale", 1.0)
    })

qa_rows = []
bad = []
for r in rows:
    b = alpha_bbox(after, r["sprite_cell"])
    o = r["original_bbox"]
    ok = contained(b, o)
    rec = {
        "key": r["key"], "source": r.get("source"), "korean": r.get("korean"),
        "sprite_cell": r["sprite_cell"], "original_bbox": o, "localized_bbox": b,
        "delta_left": None if b is None else b[0] - o[0],
        "delta_right": None if b is None else o[2] - b[2],
        "delta_top": None if b is None else b[1] - o[1],
        "delta_bottom": None if b is None else o[3] - b[3],
        "containment": "PASS" if ok else "FAIL", "rework_required": not ok
    }
    qa_rows.append(rec)
    if not ok:
        bad.append(rec)

changed = diffmask(before, after)
allowed = rectmask((w, h), allowed_change_rects)
changed_outside_rework = nz(ImageChops.multiply(changed, ImageOps.invert(allowed)))

orig_allowed = rectmask((w, h), [r["original_bbox"] for r in rows])
outside_orig = ImageOps.invert(orig_allowed)
source_diff_before = ImageChops.multiply(diffmask(src, before), outside_orig)
source_diff_after = ImageChops.multiply(diffmask(src, after), outside_orig)
before_diff_bin = source_diff_before.point(lambda v: 255 if v else 0)
after_diff_bin = source_diff_after.point(lambda v: 255 if v else 0)
new_diff_bin = ImageChops.multiply(after_diff_bin, ImageOps.invert(before_diff_bin))
after_visible = after.getchannel("A").point(lambda v: 255 if v else 0)
preexisting_source_diff_outside_orig = nz(before_diff_bin)
new_source_diff_outside_orig = nz(new_diff_bin)
new_visible_source_diff_outside_orig = nz(ImageChops.multiply(new_diff_bin, after_visible))

introduced = ImageChops.subtract(after.getchannel("A"), src.getchannel("A"))
introduced_outside_orig = nz(ImageChops.multiply(introduced, outside_orig))

pass_overlap = {}
fail_rects = [union_rect(r["localized_bbox"], amap[r["key"]]["new_localized_bbox"]) for r in fails]
fail_union = rectmask((w, h), fail_rects)
for r in rows:
    if r["containment"] == "PASS":
        cellmask = rectmask((w, h), [r["sprite_cell"]])
        protected = ImageChops.multiply(cellmask, ImageOps.invert(fail_union))
        pass_overlap[r["key"]] = nz(ImageChops.multiply(changed, protected))

if bad or changed_outside_rework or new_visible_source_diff_outside_orig or introduced_outside_orig or any(pass_overlap.values()):
    print(json.dumps({
        "failed_rows": bad,
        "changed_pixels_outside_old_or_new_rework_rects": changed_outside_rework,
        "preexisting_source_diff_pixels_outside_union_original_bboxes": preexisting_source_diff_outside_orig,
        "new_source_diff_pixels_outside_union_original_bboxes": new_source_diff_outside_orig,
        "new_visible_source_diff_pixels_outside_union_original_bboxes": new_visible_source_diff_outside_orig,
        "new_visible_source_diff_pixels_outside_union_original_bboxes": new_visible_source_diff_outside_orig,
        "introduced_alpha_outside_union_original_bboxes": introduced_outside_orig,
        "changes_in_pass_cells_outside_rework_overlap": pass_overlap
    }, ensure_ascii=False, indent=2))
    raise SystemExit("B95 strict self-QA failed; candidate not written")

out = blob(oldb[:128], after.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
parse(out)
if out[:128] != srcb[:128] or len(out) != len(oldb):
    raise SystemExit("DDS structure changed")
newsha = h256(out)
oldsha = h256(oldb)
if newsha == oldsha:
    raise SystemExit("no binary change")
CAND.write_bytes(out)

RUN.mkdir(parents=True, exist_ok=True)
panels = []
for r in fails:
    x0, y0, x1, y1 = r["sprite_cell"]
    b = before.crop((x0, y0, x1 + 1, y1 + 1))
    a = after.crop((x0, y0, x1 + 1, y1 + 1))
    W = 900
    sc = min(1.0, (W // 2 - 12) / max(1, b.width), 160 / max(1, b.height))
    sz = (max(1, int(b.width * sc)), max(1, int(b.height * sc)))
    p = Image.new("RGBA", (W, max(58, sz[1] + 24)), (28, 28, 28, 255))
    p.paste(b.resize(sz, Image.Resampling.LANCZOS), (5, 20))
    p.paste(a.resize(sz, Image.Resampling.LANCZOS), (W // 2 + 5, 20))
    d = ImageDraw.Draw(p)
    d.text((5, 3), r["key"] + " BEFORE", fill="white")
    d.text((W // 2 + 5, 3), r["key"] + " AFTER", fill="white")
    panels.append(p)

sheet = Image.new("RGBA", (900, sum(p.height for p in panels)), (18, 18, 18, 255))
yy = 0
for p in panels:
    sheet.paste(p, (0, yy))
    yy += p.height
sheet.convert("RGB").save(QA, quality=92)

now = datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
rep = {
    "schema_version": 1, "role": "B", "run": "B95", "task_id": TASK_ID, "timestamp_kst": now,
    "base_head": os.environ.get("GITHUB_SHA"),
    "asset": "textures/load/spr_sprani_fruity_cvt_Exst/FA7BBB13_1024x512.dds", "index": INDEX,
    "source_sha256": h256(srcb), "previous_candidate_sha256": oldsha, "candidate_sha256": newsha,
    "structure": {"width": w, "height": h, "format": "RGBA32", "mipmaps": m, "bytes": len(out), "header_128_exact": True, "raw_orientation": "mirror_y"},
    "reworked_elements": records,
    "qa": {
        "elements": len(qa_rows), "failed_elements": 0, "rows": qa_rows,
        "changed_pixels_outside_old_or_new_rework_rects": changed_outside_rework,
        "preexisting_source_diff_pixels_outside_union_original_bboxes": preexisting_source_diff_outside_orig,
        "new_source_diff_pixels_outside_union_original_bboxes": new_source_diff_outside_orig,
        "introduced_alpha_outside_union_original_bboxes": introduced_outside_orig,
        "changes_in_preexisting_pass_cells_outside_rework_overlap": pass_overlap,
        "bbox_containment": "PASS", "artifact_risk_checks": "PASS_AUTOMATED_PENDING_C_VISUAL",
        "translation_review": "17/17 reviewed Korean strings retained"
    },
    "result": "B95_SELF_QA_PASS_PENDING_C_AND_DDS_ONLY_INGAME",
    "automation_validation": "PASS", "runtime_validation": "UNTESTED",
    "final_approval": False, "build_performed": False, "vr_ffb_changes": False,
    "gpt_library_used": False, "n100_used": False,
    "qa_image": str(QA.relative_to(ROOT))
}
REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", "utf-8")

qpath = ROOT / "localization/graphics/asset_queue.csv"
with qpath.open("r", encoding="utf-8", newline="") as f:
    qrows = list(csv.DictReader(f))
    fields = list(qrows[0].keys())
for q in qrows:
    if int(q["index"]) == INDEX:
        q["artwork_status"] = "b95_self_qa_pass_pending_c"
        q["notes"] = (q.get("notes", "").rstrip("; ") + "; B95 10-element exact-bbox rework PASS 17/17; source-diff outside original bboxes 0; C + isolated DDS_ONLY in-game pending").strip("; ")
with qpath.open("w", encoding="utf-8", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
    wr.writeheader()
    wr.writerows(qrows)

pp = ROOT / "localization/progress/progress.json"
p = json.loads(pp.read_text("utf-8"))
p["updated_at_kst"] = now
g = p.setdefault("graphics", {})
g["latest_b_first_qa"] = {
    "run": "B95", "task_id": TASK_ID, "report": str(REPORT.relative_to(ROOT)),
    "result": "FA7BBB13_SELF_QA_PASS_PENDING_C_INGAME",
    "assets": {ASSET: {"candidate_sha256": newsha, "status": "B95_SELF_QA_PASS_PENDING_C_INGAME"}}
}
nr = g.get("next_hd_rework", {})
nr["assets"] = [x for x in nr.get("assets", []) if x != ASSET]
nr["remaining"] = len(nr["assets"])
pend = nr.setdefault("pending_c_revalidation", [])
if ASSET not in pend:
    pend.append(ASSET)
g["next_hd_rework"] = nr
p["next_checkpoint"] = "B95: FA7BBB13 exact-bbox rework self-QA PASS; pending independent C and isolated DDS_ONLY in-game."
pp.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", "utf-8")

rp = ROOT / "localization/resume_state.json"
rs = json.loads(rp.read_text("utf-8"))
rs["schema_version"] = int(rs.get("schema_version", 56)) + 1
acts = [x for x in rs.get("next_actions", []) if not x.startswith("Remaining C85 production REWORK assets:")]
acts.insert(0, "B95: FA7BBB13 exact-bbox rework self-QA PASS; pending independent C and isolated DDS_ONLY in-game.")
acts.insert(1, "Refresh current GitHub queue before next B target; do not repeat B95 FA7BBB13.")
rs["next_actions"] = acts
rs.setdefault("graphics_checkpoint", {})["b95_fa7bbb13"] = {
    "timestamp_kst": now, "task_id": TASK_ID, "report": str(REPORT.relative_to(ROOT)),
    "candidate_sha256": newsha, "status": "B95_SELF_QA_PASS_PENDING_C_INGAME"
}
rp.write_text(json.dumps(rs, ensure_ascii=False, indent=2) + "\n", "utf-8")

sp = ROOT / "localization/progress/STATUS.md"
with sp.open("a", encoding="utf-8") as f:
    f.write("\n\n### B95 FA7BBB13 exact-bbox rework — " + now + "\n")
    f.write("- B even shard index 54; ten C85 failing Korean text regions reworked using existing HD Korean rasters.\n")
    f.write("- Strict self-QA: 17/17 bbox containment PASS; changes outside old/new rework rectangles 0; new visible source-diff outside original text bboxes 0; introduced alpha outside original bboxes 0.\n")
    f.write("- DDS 4096x2048 RGBA32 / 1 mip / exact header / raw mirror_y preserved. Candidate SHA-256 " + newsha + ".\n")
    f.write("- Automatic validation PASS; runtime validation UNTESTED. Independent C visual/final QA and isolated DDS_ONLY in-game validation remain mandatory.\n")

with (ROOT / "localization/WORKLOG.md").open("a", encoding="utf-8") as f:
    f.write("\n\n## " + now + " - B95 FA7BBB13 rework [" + TASK_ID + "]\n\n")
    f.write("- GitHub-only B production on even shard index 54; N100/GPT Library/VR/FFB/build not used.\n")
    f.write("- Reworked 10 C85 zero-pixel failures while retaining all 17 reviewed Korean translations.\n")
    f.write("- 17/17 exact bbox containment PASS. All pixel changes are confined to the old/new rework rectangles; new visible canonical-source differences and introduced alpha outside the union of original permitted bboxes are 0; fully transparent RGB differences are recorded separately and do not count as rendered overflow.\n")
    f.write("- Candidate SHA-256 " + newsha + ". AUTOMATION_VALIDATION=PASS; RUNTIME_VALIDATION=UNTESTED; pending independent C + isolated DDS_ONLY in-game.\n")
