#!/usr/bin/env python3
import hashlib, json, os, struct, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo = Path.cwd()
run = "20261005-C140-31C58963"
out = repo / "localization/graphics/role_C" / run
out.mkdir(parents=True, exist_ok=True)
wr = repo / "localization/graphics/worker_results"
wr.mkdir(parents=True, exist_ok=True)

asset = "textures/load/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds"
cand_path = repo / "localization/graphics/hd_candidates" / asset
bdir = repo / "localization/graphics/role_B/20261005-B-PRODUCTION58"

COMMIT = "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1 = "2da84d800f3df0606df148c353f25c2f25a47573"
ATLAS_BLOB_SHA1 = "7829c90426d563960440dd70b9b7ae74b3b76c0d"
SOURCE_SHA256 = "ae048d04fef96108f6ee30c41022aedb78083d76386448df5483ae0ccd083dcd"
CANDIDATE_SHA256 = "b6d8bcc2f2cc05d45d4af3fbfab30f0a71e8fa68a89dee4c78b6f8a6aeca4cd3"
BASE = "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/" + COMMIT

tmp = Path("/tmp/outrun_C140")
tmp.mkdir(parents=True, exist_ok=True)
source_path = tmp / "31C58963_HD.dds"
atlas_path = tmp / "4x_31C58963_512x256_atlas.json"
urllib.request.urlretrieve(BASE + "/Release/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds", source_path)
urllib.request.urlretrieve(BASE + "/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_31C58963_512x256_atlas.json", atlas_path)

def git_blob_sha1(b):
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def sha256b(b):
    return hashlib.sha256(b).hexdigest()

def bbox(mask):
    yy, xx = np.nonzero(mask)
    if not len(xx):
        return None
    return [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1]

def rect(shape, b):
    h, w = shape
    x0, y0, x1, y1 = map(int, b)
    m = np.zeros((h, w), dtype=bool)
    m[y0:y1, x0:x1] = True
    return m

def dil(mask, px=1):
    return np.asarray(
        Image.fromarray((mask.astype(np.uint8) * 255), "L").filter(ImageFilter.MaxFilter(px * 2 + 1))
    ) > 0

def comp(im, bg=(64, 64, 64, 255)):
    z = Image.new("RGBA", im.size, bg)
    z.alpha_composite(im)
    return z.convert("RGB")

sb = source_path.read_bytes()
ab = atlas_path.read_bytes()
cb = cand_path.read_bytes()

if git_blob_sha1(sb) != SOURCE_BLOB_SHA1:
    raise RuntimeError(("source_blob_sha1", git_blob_sha1(sb)))
if git_blob_sha1(ab) != ATLAS_BLOB_SHA1:
    raise RuntimeError(("atlas_blob_sha1", git_blob_sha1(ab)))
if sha256b(sb) != SOURCE_SHA256:
    raise RuntimeError(("source_sha256", sha256b(sb)))
if sha256b(cb) != CANDIDATE_SHA256:
    raise RuntimeError(("candidate_sha256", sha256b(cb)))
if sb[:128] != cb[:128]:
    raise RuntimeError("DDS header mismatch")

H, W, pitch, depth, mips = struct.unpack_from("<5I", sb, 12)
pf = struct.unpack_from("<8I", sb, 76)
if (W, H, pitch, mips) != (2048, 1024, 8192, 1):
    raise RuntimeError(("structure", W, H, pitch, depth, mips))
if len(sb) != 128 + W * H * 4 or len(cb) != len(sb):
    raise RuntimeError(("byte_length", len(sb), len(cb)))
masks = (pf[4], pf[5], pf[6])
if masks == (0xff, 0xff00, 0xff0000):
    RAWMODE = "RGBA"
elif masks == (0xff0000, 0xff00, 0xff):
    RAWMODE = "BGRA"
else:
    raise RuntimeError(("raw_mode", masks))

raw_src = Image.frombytes("RGBA", (W, H), sb[128:], "raw", RAWMODE)
raw_cand = Image.frombytes("RGBA", (W, H), cb[128:], "raw", RAWMODE)
src = raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cand = raw_cand.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa = np.asarray(src, dtype=np.uint8)
ca = np.asarray(cand, dtype=np.uint8)

atlas = json.loads(ab.decode("utf-8"))
regions = {int(r["idx"]): r["rect"] for r in atlas["regions"]}
expected_cells = {
    0: [0, 864, 1760, 160],
    1: [0, 704, 1760, 160],
    2: [0, 544, 1760, 160],
    3: [0, 384, 1760, 160],
    4: [0, 308, 744, 76],
}
if regions != expected_cells:
    raise RuntimeError(("atlas_drift", regions))

semantic = [
    (0, "SELECT STAGE", "스테이지 선택"),
    (1, "SELECT RACE", "레이스 선택"),
    (2, "SELECT MODE", "모드 선택"),
    (3, "SHOWROOM", "쇼룸"),
]

source_masks = []
allowed_masks = []
rows = []

# Rows 0-3 are transparent-background text-only atlas cells, so the canonical
# source alpha itself is the exact glyph/effect evidence.
for idx, en, ko in semantic:
    x, y, cw, ch = regions[idx]
    local = sa[y:y+ch, x:x+cw, 3] > 0
    bb = bbox(local)
    if bb is None:
        raise RuntimeError(("empty_source_cell", idx))
    ob = [x + bb[0], y + bb[1], x + bb[2], y + bb[3]]
    sm = np.zeros((H, W), dtype=bool)
    sm[y:y+ch, x:x+cw] = local
    am = rect((H, W), ob)
    source_masks.append(sm)
    allowed_masks.append(am)
    rows.append({"key": f"region_{idx}", "region_idx": idx, "source": en, "korean": ko, "original_bbox": ob})

# Independently split PRESS | Enter icon | KEY from canonical alpha by connected
# components and the two largest inter-component x gaps. This does not reuse the
# producer's word ranges or word bboxes.
x, y, cw, ch = regions[4]
local = sa[y:y+ch, x:x+cw, 3] > 0
lab, num = ndimage.label(local, np.ones((3,3), dtype=np.uint8))
comps = []
for i in range(1, num + 1):
    yy, xx = np.nonzero(lab == i)
    if len(xx) < 3:
        continue
    comps.append({
        "id": i,
        "bbox": [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1],
        "pixels": int(len(xx)),
    })
if len(comps) < 5:
    raise RuntimeError(("too_few_compound_components", len(comps), comps))
comps.sort(key=lambda c: (c["bbox"][0], c["bbox"][1]))
gaps = []
for i in range(len(comps)-1):
    gap = comps[i+1]["bbox"][0] - comps[i]["bbox"][2]
    gaps.append((int(gap), i))
cut_points = sorted([i for _, i in sorted(gaps, reverse=True)[:2]])
groups = []
start = 0
for cp in cut_points + [len(comps)-1]:
    end = cp + 1
    groups.append(comps[start:end])
    start = end
if len(groups) != 3 or any(not g for g in groups):
    raise RuntimeError(("compound_grouping", cut_points, groups))

group_masks = []
group_bboxes = []
for g in groups:
    ids = {c["id"] for c in g}
    gm_local = np.isin(lab, list(ids))
    bb = bbox(gm_local)
    gm = np.zeros((H, W), dtype=bool)
    gm[y:y+ch, x:x+cw] = gm_local
    group_masks.append(gm)
    group_bboxes.append([x+bb[0], y+bb[1], x+bb[2], y+bb[3]])

# Expected visual order is PRESS | protected Enter icon | KEY. Require the center
# group to be a compact icon, and left/right groups to be word-like.
left_bb, icon_bb, right_bb = group_bboxes
left_px, icon_px, right_px = [int(np.count_nonzero(g)) for g in group_masks]
if not (left_bb[2] < icon_bb[0] < icon_bb[2] < right_bb[0]):
    raise RuntimeError(("compound_order", group_bboxes))
if icon_px < 1000 or left_px < 1000 or right_px < 500:
    raise RuntimeError(("compound_pixel_evidence", left_px, icon_px, right_px))

for key, en, ko, gm, ob in [
    ("press_word", "PRESS", "누르세요", group_masks[0], left_bb),
    ("key_word", "KEY", "키", group_masks[2], right_bb),
]:
    source_masks.append(gm)
    allowed_masks.append(rect((H, W), ob))
    rows.append({"key": key, "region_idx": 4, "source": en, "korean": ko, "original_bbox": ob})

source_mask = np.logical_or.reduce(source_masks)
allowed = np.logical_or.reduce(allowed_masks)
icon_mask = group_masks[1]
protected = (sa[:, :, 3] > 0) & ~source_mask

# Producer CLEAN must equal an independent canonical reconstruction: exact source
# pixels outside source glyph/effect mask and transparent RGBA inside it.
expected_clean = sa.copy()
expected_clean[source_mask] = 0
bclean = np.asarray(Image.open(bdir / "31C_HD_CLEAN_PLATE.png").convert("RGBA"), dtype=np.uint8)
if bclean.shape != expected_clean.shape:
    raise RuntimeError(("clean_shape", bclean.shape))
clean_diff = np.any(bclean != expected_clean, axis=2)
if np.count_nonzero(clean_diff):
    raise RuntimeError(("producer_clean_not_exact", int(np.count_nonzero(clean_diff)), bbox(clean_diff)))

# Exact candidate-vs-source containment and protected preservation.
final_diff = np.any(ca != sa, axis=2)
alpha_diff = ca[:, :, 3] != sa[:, :, 3]
outside = int(np.count_nonzero(final_diff & ~allowed))
alpha_outside = int(np.count_nonzero(alpha_diff & ~allowed))
protected_changed = int(np.count_nonzero(final_diff & protected))
if outside or alpha_outside or protected_changed:
    raise RuntimeError(("outside_or_protected", outside, alpha_outside, protected_changed))

# Build localized target masks directly from candidate alpha within each exact
# source bbox. CLEAN is transparent in those regions.
target_masks = []
row_results = []
for r, am in zip(rows, allowed_masks):
    tm = am & (ca[:, :, 3] > 0)
    lb = bbox(tm)
    if lb is None:
        raise RuntimeError(("missing_target", r["key"]))
    ob = r["original_bbox"]
    sw, sh = ob[2]-ob[0], ob[3]-ob[1]
    lw, lh = lb[2]-lb[0], lb[3]-lb[1]
    deltas = [lb[0]-ob[0], ob[2]-lb[2], lb[1]-ob[1], ob[3]-lb[3]]
    if lw > sw or lh > sh or min(deltas) <= 0:
        raise RuntimeError(("bbox_size_margin", r["key"], ob, lb, [sw,sh], [lw,lh], deltas))
    target_masks.append(tm)
    row_results.append({
        **r,
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

target = np.logical_or.reduce(target_masks)
render_diff = np.any(ca != expected_clean, axis=2)
render_outside_target = int(np.count_nonzero(render_diff & ~target & ~icon_mask))
source_residue = int(np.count_nonzero(source_mask & ~target & (ca[:, :, 3] > 0)))
if render_outside_target or source_residue:
    raise RuntimeError(("render_or_residue", render_outside_target, source_residue))

# The protected Enter-key icon must be byte/pixel identical.
icon_changed = int(np.count_nonzero(np.any(ca != sa, axis=2) & icon_mask))
if icon_changed:
    raise RuntimeError(("icon_changed", icon_changed))

overlap = 0
touch_pairs = []
for i in range(len(target_masks)):
    for j in range(i+1, len(target_masks)):
        ov = int(np.count_nonzero(target_masks[i] & target_masks[j]))
        near = int(np.count_nonzero(dil(target_masks[i], 1) & target_masks[j]))
        overlap += ov
        if ov or near:
            touch_pairs.append([rows[i]["key"], rows[j]["key"], ov, near])
if overlap or touch_pairs:
    raise RuntimeError(("target_overlap_touch", overlap, touch_pairs))

compound_protected_near = {}
for idx in [4, 5]:
    near = int(np.count_nonzero(dil(target_masks[idx], 1) & icon_mask))
    compound_protected_near[rows[idx]["key"]] = near
    if near:
        raise RuntimeError(("target_touches_icon", rows[idx]["key"], near))

# Simple source-style color checks: large rows remain white; compound words retain
# both yellow fill and dark outline. Controller review remains the visual style gate.
style = {}
for i, r in enumerate(row_results):
    px = ca[target_masks[i]]
    if i < 4:
        white = int(np.count_nonzero((px[:,0] >= 240) & (px[:,1] >= 240) & (px[:,2] >= 240)))
        frac = white / max(1, len(px))
        style[r["key"]] = {"target_pixels": int(len(px)), "near_white_fraction": frac}
        if frac < 0.80:
            raise RuntimeError(("white_style_fraction", r["key"], frac))
    else:
        yellow = int(np.count_nonzero((px[:,0] >= 170) & (px[:,1] >= 90) & (px[:,2] <= 100)))
        dark = int(np.count_nonzero((px[:,0] <= 70) & (px[:,1] <= 70) & (px[:,2] <= 70)))
        style[r["key"]] = {"target_pixels": int(len(px)), "yellow_pixels": yellow, "dark_outline_pixels": dark}
        if yellow < 50 or dark < 50:
            raise RuntimeError(("compound_style", r["key"], yellow, dark))

# Evidence images.
clean_img = Image.fromarray(expected_clean, "RGBA")
for name, mask in [
    ("C140_SOURCE_TEXT_MASK.png", source_mask),
    ("C140_ALLOWED_BBOX_MASK.png", allowed),
    ("C140_PROTECTED_VISIBLE_MASK.png", protected),
    ("C140_TARGET_TEXT_MASK.png", target),
    ("C140_ENTER_ICON_MASK.png", icon_mask),
]:
    Image.fromarray((mask.astype(np.uint8) * 255), "L").save(out / name)
clean_img.save(out / "C140_EXACT_CLEAN_PLATE.png")

def card(label, im, bg=(64,64,64,255)):
    v = comp(im, bg)
    c = Image.new("RGB", (W, H+28), "white")
    c.paste(v, (0,28))
    ImageDraw.Draw(c).text((5,5), label, fill="black")
    return c

cards = [
    card("SOURCE_READABLE", src),
    card("C140_EXACT_CLEAN", clean_img),
    card("C140_FINAL", cand),
    card("C140_FINAL_WHITE", cand, (255,255,255,255)),
]
sheet = Image.new("RGB", (W*2, (H+28)*2), "white")
sheet.paste(cards[0], (0,0)); sheet.paste(cards[1], (W,0))
sheet.paste(cards[2], (0,H+28)); sheet.paste(cards[3], (W,H+28))
sheet.resize((2048, 1052), Image.Resampling.LANCZOS).save(out / "C140_31C_COMPARE.jpg", quality=96)

sr, cl, fi = comp(src), comp(clean_img), comp(cand)
contacts = []
for r in row_results:
    x0,y0,x1,y1 = r["original_bbox"]
    p = 12
    cr = (max(0,x0-p), max(0,y0-p), min(W,x1+p), min(H,y1+p))
    ims = [z.crop(cr) for z in (sr,cl,fi)]
    ims = [z.resize((z.width*2,z.height*2), Image.Resampling.NEAREST) for z in ims]
    c = Image.new("RGB", (sum(z.width for z in ims)+12, max(z.height for z in ims)+28), "white")
    xx=0
    for z in ims:
        c.paste(z,(xx,28)); xx += z.width+6
    ImageDraw.Draw(c).text((5,5), f'{r["source"]} -> {r["korean"]}', fill="black")
    contacts.append(c)
rs = Image.new("RGB", (max(c.width for c in contacts), sum(c.height for c in contacts)+4*(len(contacts)-1)), "white")
yy=0
for c in contacts:
    rs.paste(c,(0,yy)); yy += c.height+4
rs.save(out / "C140_31C_ROW_CONTACT_2X.jpg", quality=96)

rawsheet = Image.new("RGB", (1024,1080), "white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("C140_FINAL_RAW_MIRROR_Y",raw_cand)]):
    z=comp(im).resize((1024,512),Image.Resampling.LANCZOS)
    rawsheet.paste(z,(0,i*540+28))
    ImageDraw.Draw(rawsheet).text((5,i*540+5),label,fill="black")
rawsheet.save(out / "C140_31C_RAW_COMPARE.jpg", quality=96)

checks = {
    "source_blob_sha1": git_blob_sha1(sb),
    "source_sha256": sha256b(sb),
    "candidate_sha256": sha256b(cb),
    "header_128_exact": True,
    "raw_orientation": "mirror_y",
    "producer_clean_exact_vs_independent_reconstruction_diff_pixels": int(np.count_nonzero(clean_diff)),
    "final_changed_outside_allowed": outside,
    "alpha_changed_outside_allowed": alpha_outside,
    "protected_visible_pixels_changed": protected_changed,
    "render_changed_outside_target_or_icon": render_outside_target,
    "source_residue_pixels": source_residue,
    "enter_icon_pixels": icon_px,
    "enter_icon_changed_pixels": icon_changed,
    "localized_overlap_pixels": overlap,
    "localized_touch_pairs": touch_pairs,
    "compound_target_icon_1px_near_pixels": compound_protected_near,
    "compound_groups": {"left_press_bbox": left_bb, "enter_icon_bbox": icon_bb, "right_key_bbox": right_bb},
    "style": style,
}
report = {
    "schema_version": 1,
    "role": "C",
    "run": run,
    "queue_index": 140,
    "asset": asset,
    "producer_run": "20261005-B-PRODUCTION58",
    "source_provenance": {
        "repository": "Sonic-TV/OR2006Sprites",
        "commit": COMMIT,
        "source_git_blob_sha1": SOURCE_BLOB_SHA1,
        "atlas_git_blob_sha1": ATLAS_BLOB_SHA1,
        "source_sha256": SOURCE_SHA256,
    },
    "candidate_sha256": CANDIDATE_SHA256,
    "candidate_changed_by_C": False,
    "independent_method": "pinned canonical source + atlas download; exact alpha bboxes for text-only cells; PRESS/icon/KEY split by connected components and two largest x gaps; independent clean reconstruction; candidate decode/header/containment/protected/icon/overlap/style gates",
    "structure": {"dimensions":[W,H],"format":"RGBA32","raw_mode":RAWMODE,"mipmaps":mips,"raw_orientation":"mirror_y"},
    "rows": row_results,
    "machine_checks": checks,
    "machine_status": "PASS",
    "controller_visual_qa": "PENDING",
    "decision": "PENDING_CONTROLLER_VISUAL_QA",
    "RUNTIME_VALIDATION": "UNTESTED",
}
(out / "C140_31C_MACHINE_QA.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
summary = {
    "run": run,
    "asset": "31C58963",
    "index": 140,
    "source_sha256": SOURCE_SHA256,
    "candidate_sha256": CANDIDATE_SHA256,
    "machine_status": "PASS",
    "bbox_size_positive_margin": "6/6",
    "clean_exact_diff_pixels": int(np.count_nonzero(clean_diff)),
    "outside": outside,
    "alpha_outside": alpha_outside,
    "protected_changed": protected_changed,
    "source_residue": source_residue,
    "icon_changed": icon_changed,
    "overlap": overlap,
    "touch_pairs": len(touch_pairs),
    "runtime_validation": "UNTESTED",
    "report": f"localization/graphics/role_C/{run}/C140_31C_MACHINE_QA.json",
}
(wr / "C140_31C58963.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False), flush=True)
