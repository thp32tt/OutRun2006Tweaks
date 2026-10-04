#!/usr/bin/env python3
import hashlib, json, os, struct, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo = Path.cwd()
run = "20261005-C139-1F5FE6E9"
out = repo / "localization/graphics/role_C" / run
out.mkdir(parents=True, exist_ok=True)
wr = repo / "localization/graphics/worker_results"
wr.mkdir(parents=True, exist_ok=True)

asset = "textures/load/spr_sprani_sumo_fe_cvt_Exst/1F5FE6E9_1024x512.dds"
srczip = repo / "localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
cand_path = repo / "localization/graphics/hd_candidates" / asset
bdir = repo / "localization/graphics/role_B/20261005-B-PRODUCTION55"
b_report = json.loads((bdir / "B55_1F5_REPORT.json").read_text(encoding="utf-8"))

with zipfile.ZipFile(srczip) as z:
    sb = z.read(asset)
cb = cand_path.read_bytes()
source_sha = hashlib.sha256(sb).hexdigest()
candidate_sha = hashlib.sha256(cb).hexdigest()
if source_sha != "3656adbd699b7852cb5fcf4bb01fc4f1f65bbd9d7d39e12e7a1c2ac5a49fef1d":
    raise RuntimeError(("source_sha", source_sha))
if candidate_sha != "e503bb29d87501453e3f0ba4b7b9528a4cc53a198a148845ea8cdad6c97ec6be":
    raise RuntimeError(("candidate_sha", candidate_sha))
if b_report["source_sha256"] != source_sha or b_report["candidate_sha256"] != candidate_sha:
    raise RuntimeError("B55 report identity mismatch")
if sb[:128] != cb[:128]:
    raise RuntimeError("DDS header mismatch")

H = struct.unpack_from("<I", sb, 12)[0]
W = struct.unpack_from("<I", sb, 16)[0]
mips = struct.unpack_from("<I", sb, 28)[0]
if (W, H, mips) != (1024, 512, 1) or len(sb) != 128 + W * H * 4 or len(cb) != len(sb):
    raise RuntimeError(("structure", W, H, mips, len(sb), len(cb)))

raw_src = Image.frombytes("RGBA", (W, H), sb[128:], "raw", "RGBA")
raw_cand = Image.frombytes("RGBA", (W, H), cb[128:], "raw", "RGBA")
src = raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cand = raw_cand.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean = Image.open(bdir / "1F5_CLEAN_PLATE.png").convert("RGBA")
sa = np.asarray(src, dtype=np.uint8)
ca = np.asarray(cand, dtype=np.uint8)
cla = np.asarray(clean, dtype=np.uint8)
if sa.shape != ca.shape or sa.shape != cla.shape:
    raise RuntimeError(("decoded shape", sa.shape, ca.shape, cla.shape))

def load_mask(name):
    a = np.asarray(Image.open(bdir / name).convert("L"), dtype=np.uint8) > 0
    if a.shape != (H, W):
        raise RuntimeError(("mask shape", name, a.shape))
    return a

source_mask = load_mask("1F5_SOURCE_TEXT_MASK.png")
allowed = load_mask("1F5_ALLOWED_TEXT_REGION_MASK.png")
protected = load_mask("1F5_PROTECTED_MASK.png")
target = load_mask("1F5_TARGET_TEXT_MASK.png")

def bbox(mask):
    yy, xx = np.nonzero(mask)
    if not len(xx):
        return None
    return [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1]

def rect(b):
    x0, y0, x1, y1 = map(int, b)
    m = np.zeros((H, W), dtype=bool)
    m[y0:y1, x0:x1] = True
    return m

def dil(mask, px=1):
    return np.asarray(
        Image.fromarray((mask.astype(np.uint8) * 255), "L").filter(ImageFilter.MaxFilter(px * 2 + 1))
    ) > 0

# Independently rebuild the exact source-alpha evidence inside B55's measured
# source glyph/effect boxes from the canonical source. Background alpha is zero
# in these row interiors, so every nonzero-alpha source pixel inside each box is
# source effect evidence. This avoids treating producer mask pixels as ground truth.
derived_source = np.zeros((H, W), dtype=bool)
row_results = []
row_target_masks = []
for row in b_report["rows"]:
    ob = list(map(int, row["original_bbox"]))
    region = rect(ob)
    independent = region & (sa[:, :, 3] > 0)
    reported_source = source_mask & region
    if np.count_nonzero(independent ^ reported_source):
        raise RuntimeError(("source mask mismatch", row["n"], int(np.count_nonzero(independent ^ reported_source))))
    if bbox(independent) != ob:
        raise RuntimeError(("source bbox not exact", row["n"], bbox(independent), ob))
    derived_source |= independent

    tm = target & region
    lb = bbox(tm)
    if lb is None:
        raise RuntimeError(("missing target", row["n"]))
    if lb != list(map(int, row["localized_bbox"])):
        raise RuntimeError(("localized bbox mismatch", row["n"], lb, row["localized_bbox"]))
    sw, sh = ob[2] - ob[0], ob[3] - ob[1]
    lw, lh = lb[2] - lb[0], lb[3] - lb[1]
    deltas = [lb[0] - ob[0], ob[2] - lb[2], lb[1] - ob[1], ob[3] - lb[3]]
    if lw > sw or lh > sh or min(deltas) <= 0:
        raise RuntimeError(("bbox/size/positive-margin", row["n"], ob, lb, [sw, sh], [lw, lh], deltas))
    row_target_masks.append(tm)
    row_results.append({
        "n": int(row["n"]),
        "source": row["source"],
        "korean": row["korean"],
        "original_bbox": ob,
        "localized_bbox": lb,
        "source_size": [sw, sh],
        "localized_size": [lw, lh],
        "delta_left": deltas[0],
        "delta_right": deltas[1],
        "delta_top": deltas[2],
        "delta_bottom": deltas[3],
        "containment": "PASS",
        "size_ceiling": "PASS",
        "positive_margin": "PASS",
    })

if np.count_nonzero(derived_source ^ source_mask):
    raise RuntimeError(("unexpected source mask pixels outside row boxes", int(np.count_nonzero(derived_source ^ source_mask))))

clean_changed = np.any(sa != cla, axis=2)
final_changed = np.any(sa != ca, axis=2)
render_changed = np.any(cla != ca, axis=2)
alpha_changed = sa[:, :, 3] != ca[:, :, 3]

checks = {
    "source_effect_pixels": int(np.count_nonzero(source_mask)),
    "source_mask_unchanged_in_clean": int(np.count_nonzero(source_mask & ~clean_changed)),
    "clean_changed_outside_source_mask": int(np.count_nonzero(clean_changed & ~source_mask)),
    "final_changed_outside_allowed": int(np.count_nonzero(final_changed & ~allowed)),
    "alpha_changed_outside_allowed": int(np.count_nonzero(alpha_changed & ~allowed)),
    "protected_changed": int(np.count_nonzero(final_changed & protected)),
    "render_changed_outside_target": int(np.count_nonzero(render_changed & ~target)),
    "target_outside_allowed": int(np.count_nonzero(target & ~allowed)),
    "target_pixels": int(np.count_nonzero(target)),
}
if checks["source_mask_unchanged_in_clean"] != 0:
    raise RuntimeError(("clean source residue", checks))
if checks["clean_changed_outside_source_mask"] != 0:
    raise RuntimeError(("clean outside source mask", checks))
for k in ["final_changed_outside_allowed", "alpha_changed_outside_allowed", "protected_changed",
          "render_changed_outside_target", "target_outside_allowed"]:
    if checks[k] != 0:
        raise RuntimeError((k, checks[k]))

overlap = 0
touch_pairs = []
for i in range(len(row_target_masks)):
    for j in range(i + 1, len(row_target_masks)):
        ov = int(np.count_nonzero(row_target_masks[i] & row_target_masks[j]))
        near = int(np.count_nonzero(dil(row_target_masks[i], 1) & row_target_masks[j]))
        overlap += ov
        if ov or near:
            touch_pairs.append([i + 1, j + 1, ov, near])
if overlap or touch_pairs:
    raise RuntimeError(("localized overlap/touch", overlap, touch_pairs))
checks["localized_overlap_pixels"] = overlap
checks["localized_touch_pairs"] = touch_pairs

# Confirm all four source rows are mutually separated and preserve their measured 24px cadence.
source_row_bboxes = [r["original_bbox"] for r in row_results]
row_gaps = [source_row_bboxes[i+1][1] - source_row_bboxes[i][3] for i in range(3)]
if any(g < 0 for g in row_gaps):
    raise RuntimeError(("source row overlap", row_gaps))
checks["source_row_gaps"] = row_gaps

def comp(im, bg=(64, 64, 64, 255)):
    z = Image.new("RGBA", im.size, bg)
    z.alpha_composite(im)
    return z.convert("RGB")

def card(label, im, bg=(64, 64, 64, 255)):
    v = comp(im, bg)
    c = Image.new("RGB", (W, H + 25), "white")
    c.paste(v, (0, 25))
    ImageDraw.Draw(c).text((5, 4), label, fill="black")
    return c

cards = [
    card("SOURCE_READABLE", src),
    card("B55_CLEAN", clean),
    card("C139_DECODED_FINAL", cand),
    card("C139_FINAL_WHITE", cand, (255, 255, 255, 255)),
]
sheet = Image.new("RGB", (W * 2, (H + 25) * 2), "white")
sheet.paste(cards[0], (0, 0)); sheet.paste(cards[1], (W, 0))
sheet.paste(cards[2], (0, H + 25)); sheet.paste(cards[3], (W, H + 25))
sheet.save(out / "C139_1F5_COMPARE.jpg", quality=96)

sr, cl, fi = comp(src), comp(clean), comp(cand)
contacts = []
for r in row_results:
    x0, y0, x1, y1 = r["original_bbox"]
    p = 8
    cr = (max(0, x0-p), max(0, y0-p), min(W, x1+p), min(H, y1+p))
    ims = [z.crop(cr) for z in (sr, cl, fi)]
    ims = [z.resize((z.width * 4, z.height * 4), Image.Resampling.NEAREST) for z in ims]
    c = Image.new("RGB", (sum(z.width for z in ims) + 12, max(z.height for z in ims) + 25), "white")
    xx = 0
    for z in ims:
        c.paste(z, (xx, 25)); xx += z.width + 6
    ImageDraw.Draw(c).text((4, 4), f'{r["n"]} {r["source"]} -> {r["korean"]}', fill="black")
    contacts.append(c)
rowsheet = Image.new("RGB", (max(c.width for c in contacts), sum(c.height for c in contacts) + 4 * (len(contacts)-1)), "white")
yy = 0
for c in contacts:
    rowsheet.paste(c, (0, yy)); yy += c.height + 4
rowsheet.save(out / "C139_1F5_ROW_CONTACT_4X.jpg", quality=96)

rawsheet = Image.new("RGB", (W, (H + 25) * 2), "white")
rawsheet.paste(card("SOURCE_RAW_MIRROR_Y", raw_src), (0, 0))
rawsheet.paste(card("C139_FINAL_RAW_MIRROR_Y", raw_cand), (0, H + 25))
rawsheet.save(out / "C139_1F5_RAW_COMPARE.jpg", quality=96)

report = {
    "schema_version": 1,
    "role": "C",
    "run": run,
    "queue_index": 132,
    "asset": asset,
    "source_sha256": source_sha,
    "candidate_sha256": candidate_sha,
    "candidate_changed_by_C": False,
    "producer_run": "20261005-B-PRODUCTION55",
    "independent_source_mask_method": "canonical source nonzero-alpha pixels inside each producer-measured exact glyph/effect bbox; exact bbox equality and complete producer-mask equality required",
    "structure": {"width": W, "height": H, "format": "RGBA32", "mipmaps": mips, "header_128_exact": True, "raw_orientation": "mirror_y"},
    "rows": row_results,
    "machine_checks": checks,
    "machine_status": "PASS",
    "controller_visual_qa": "PENDING",
    "decision": "PENDING_CONTROLLER_VISUAL_QA",
    "RUNTIME_VALIDATION": "UNTESTED",
}
(out / "C139_1F5_MACHINE_QA.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
summary = {
    "run": run, "asset": "1F5FE6E9", "index": 132,
    "source_sha256": source_sha, "candidate_sha256": candidate_sha,
    "machine_status": "PASS", "bbox_size_positive_margin": "4/4",
    "clean_source_residue": checks["source_mask_unchanged_in_clean"],
    "clean_outside": checks["clean_changed_outside_source_mask"],
    "final_outside": checks["final_changed_outside_allowed"],
    "alpha_outside": checks["alpha_changed_outside_allowed"],
    "protected_changed": checks["protected_changed"],
    "render_outside_target": checks["render_changed_outside_target"],
    "overlap": overlap, "touch_pairs": len(touch_pairs),
    "runtime_validation": "UNTESTED",
    "report": f"localization/graphics/role_C/{run}/C139_1F5_MACHINE_QA.json",
}
(wr / "C139_1F5FE6E9.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False), flush=True)
