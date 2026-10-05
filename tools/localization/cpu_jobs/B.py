#!/usr/bin/env python3
import base64, hashlib, json, math, os, struct, subprocess, urllib.request
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "B":
    raise SystemExit("B hosted worker only")

repo = Path.cwd()
run = "20261006-B-PRODUCTION160-A8CE-BC3-SCALE"
out = repo / "localization/graphics/role_B" / run
out.mkdir(parents=True, exist_ok=True)
wr = repo / "localization/graphics/worker_results"
wr.mkdir(parents=True, exist_ok=True)

asset = "textures/load/spr_sprani_fight_Exst/A8CE339F_512x256.dds"
candidate = repo / "localization/graphics/hd_candidates" / asset
candidate.parent.mkdir(parents=True, exist_ok=True)

COMMIT = "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_SHA256 = "08afacc681737d6a138496cefce559853985084cf779921ac32ef2ebfe06883b"
BASE = "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/" + COMMIT
tmp = Path("/tmp/outrun_B160_A8CE")
tmp.mkdir(parents=True, exist_ok=True)
dds = tmp / "A8CE339F_HD.dds"
atlasp = tmp / "A8CE339F_atlas.json"
urllib.request.urlretrieve(BASE + "/Release/spr_sprani_fight_Exst/A8CE339F_512x256.dds", dds)
urllib.request.urlretrieve(
    BASE + "/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_fight_Exst/4x_A8CE339F_512x256_atlas.json",
    atlasp,
)

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def dds_meta(b):
    if b[:4] != b"DDS ":
        raise RuntimeError("not DDS")
    h = struct.unpack_from("<I", b, 12)[0]
    w = struct.unpack_from("<I", b, 16)[0]
    mips = struct.unpack_from("<I", b, 28)[0]
    fourcc = b[84:88]
    need = 128 + ((w + 3) // 4) * ((h + 3) // 4) * 16
    if fourcc != b"DXT5" or mips not in (0, 1) or len(b) != need:
        raise RuntimeError(("unexpected DDS", w, h, mips, fourcc, len(b), need))
    return w, h, mips, fourcc

sb = dds.read_bytes()
if sha256_bytes(sb) != SOURCE_SHA256:
    raise RuntimeError(("pinned A8 source drift", sha256_bytes(sb)))
W, H, MIPS, FOURCC = dds_meta(sb)
if (W, H) != (2048, 1024):
    raise RuntimeError(("dimension drift", W, H))

atlas = json.loads(atlasp.read_text(encoding="utf-8"))
regs = {int(r["idx"]): list(map(int, r["rect"])) for r in atlas["regions"]}
for idx in (24, 25, 26, 27, 28, 29, 30, 31, 32, 33):
    if idx not in regs:
        raise RuntimeError(("required atlas region missing", idx))

raw_src = Image.open(dds).convert("RGBA")
src = raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa = np.asarray(src, dtype=np.uint8)

# Same source family precedent: C86 already approved Start/Goal -> 시작/골 on FF2462BB.
# A8CE is BC3 rather than FF's RGBA32, so we reuse the semantic/typography precedent,
# not FF candidate bytes.
C86_PRECEDENT = {
    "asset": "FF2462BB",
    "candidate_sha256": "9e6f0247e54302b0c81d84f24f02ec255af4c027916e3bdfe4726f0839f2de08",
    "decision": "C86_PIXEL_VISUAL_PASS_PENDING_INGAME",
    "start_source_size": [114, 48],
    "goal_source_size": [103, 48],
    "start_korean": "시작",
    "goal_korean": "골",
}

subprocess.run(["sudo", "apt-get", "update", "-qq"], check=True)
subprocess.run(
    ["sudo", "apt-get", "install", "-y", "-qq", "fonts-noto-cjk", "fonts-noto-cjk-extra", "libnvtt-bin"],
    check=True,
)
FONT = subprocess.check_output(
    ["fc-match", "-f", "%{file}", "Noto Sans CJK KR:style=Black"], text=True
).strip()
if not FONT or not Path(FONT).exists() or "NotoSansCJK" not in Path(FONT).name:
    raise RuntimeError(("CJK font unavailable", FONT))
if not Path("/usr/bin/nvcompress").exists():
    raise RuntimeError("nvcompress unavailable")

def bbox_from_mask(mask):
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]

def globalize(cell, bb):
    x, y, w, h = cell
    return [x + bb[0], y + bb[1], x + bb[2], y + bb[3]]

def region_rgba(idx):
    x, y, w, h = regs[idx]
    return sa[y:y+h, x:x+w]

def word_masks_for_bar(idx):
    """Find only Start and Goal in atlas progress-bar cells; fail closed if ambiguous."""
    arr = region_rgba(idx)
    alpha_hi = arr[:, :, 3] > 8
    alpha_all = arr[:, :, 3] > 1
    h, w = alpha_hi.shape

    # In readable orientation Start/Goal are above the bar/ticks.
    top_h = min(66, h)
    top = alpha_hi[:top_h]
    col = np.any(top, axis=0)
    # Bridge intraword letter gaps, not the large Start->Goal spacing.
    closed = ndimage.binary_closing(col, structure=np.ones(13, dtype=bool))
    labs, n = ndimage.label(closed)
    groups = []
    for k in range(1, n + 1):
        xs = np.nonzero(labs == k)[0]
        if not len(xs):
            continue
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        if x1 - x0 < 40:
            continue
        # Exact visible bbox from strong alpha first.
        local = top[:, x0:x1]
        bb = bbox_from_mask(local)
        if bb is None:
            continue
        bb = [x0 + bb[0], bb[1], x0 + bb[2], bb[3]]
        ww, hh = bb[2] - bb[0], bb[3] - bb[1]
        if 65 <= ww <= 155 and 28 <= hh <= 62:
            groups.append(bb)

    # Prefer exactly two word groups. If compression split a word, morphology fallback in 2-D.
    if len(groups) != 2:
        dil = ndimage.binary_dilation(top, structure=np.ones((3, 7), dtype=bool), iterations=1)
        labs2, n2 = ndimage.label(dil)
        groups2 = []
        for k in range(1, n2 + 1):
            m = labs2 == k
            bb = bbox_from_mask(m)
            if bb is None:
                continue
            ww, hh = bb[2] - bb[0], bb[3] - bb[1]
            if 65 <= ww <= 165 and 28 <= hh <= 66:
                # Refine to source high-alpha pixels under component extent.
                x0, y0, x1, y1 = bb
                ref = bbox_from_mask(top[y0:y1, x0:x1])
                if ref:
                    groups2.append([x0+ref[0], y0+ref[1], x0+ref[2], y0+ref[3]])
        groups = groups2

    groups = sorted(groups, key=lambda b: b[0])
    if len(groups) != 2:
        raise RuntimeError(("ambiguous Start/Goal groups", idx, groups))

    # Source precedent: Start is wider than Goal and is left of Goal.
    left, right = groups
    if (left[2] - left[0]) <= (right[2] - right[0]):
        raise RuntimeError(("Start/Goal width ordering unexpected", idx, left, right))

    out = {}
    for word, strong in (("Start", left), ("Goal", right)):
        sx0, sy0, sx1, sy1 = strong
        # Expand just enough to capture low-alpha BC3 fringe, while staying above the bar.
        ex0 = max(0, sx0 - 3)
        ex1 = min(w, sx1 + 3)
        ey0 = max(0, sy0 - 3)
        ey1 = min(top_h, sy1 + 3)
        m = np.zeros((h, w), dtype=bool)
        m[ey0:ey1, ex0:ex1] = alpha_all[ey0:ey1, ex0:ex1]
        bb = bbox_from_mask(m)
        if bb is None:
            raise RuntimeError(("empty word source mask", idx, word))
        ww, hh = bb[2] - bb[0], bb[3] - bb[1]
        # Allow BC3 fringe vs exact C86 RGBA sizes, but fail if grossly different.
        expw, exph = C86_PRECEDENT["start_source_size" if word == "Start" else "goal_source_size"]
        if abs(ww - expw) > 14 or abs(hh - exph) > 10:
            raise RuntimeError(("same-family source size drift", idx, word, [ww, hh], [expw, exph]))
        out[word] = m
    return out

elements = []
def add_element(idx, source_text, korean, local_mask, kind):
    x, y, w, h = regs[idx]
    alpha = region_rgba(idx)[:, :, 3] > 1
    if local_mask.shape != alpha.shape:
        raise RuntimeError(("mask shape mismatch", idx, local_mask.shape, alpha.shape))
    local_mask = local_mask & alpha
    bb = bbox_from_mask(local_mask)
    if bb is None:
        raise RuntimeError(("empty source element", idx, source_text))
    gb = globalize(regs[idx], bb)
    gm = np.zeros((H, W), dtype=bool)
    gm[y:y+h, x:x+w] = local_mask
    elements.append({
        "region_idx": idx,
        "source": source_text,
        "korean": korean,
        "kind": kind,
        "cell": [x, y, w, h],
        "source_mask": gm,
        "original_bbox": gb,
        "source_mask_pixels": int(np.count_nonzero(gm)),
    })

for idx in (24, 25):
    wm = word_masks_for_bar(idx)
    add_element(idx, "Start", "시작", wm["Start"], "bar_label")
    add_element(idx, "Goal", "골", wm["Goal"], "bar_label")

# idx26 is an isolated Extra Time sprite. Keep its full visible effect footprint.
arr26 = region_rgba(26)
m26 = arr26[:, :, 3] > 1
bb26 = bbox_from_mask(m26)
if bb26 is None:
    raise RuntimeError("Extra Time source absent")
ew, eh = bb26[2] - bb26[0], bb26[3] - bb26[1]
if not (240 <= ew <= regs[26][2] and 40 <= eh <= regs[26][3]):
    raise RuntimeError(("Extra Time bbox unexpected", bb26, [ew, eh], regs[26]))
add_element(26, "Extra Time", "추가 시간", m26, "extra_time")

if len(elements) != 5:
    raise RuntimeError(("physical element count", len(elements)))

# Ensure source masks don't overlap.
source_union = np.zeros((H, W), dtype=bool)
for e in elements:
    overlap = source_union & e["source_mask"]
    if np.any(overlap):
        raise RuntimeError(("source element overlap", e["region_idx"], e["source"], int(np.count_nonzero(overlap))))
    source_union |= e["source_mask"]

# Only exact source bboxes may change after BC3 decode.
allowed = np.zeros((H, W), dtype=bool)
for e in elements:
    x0, y0, x1, y1 = e["original_bbox"]
    allowed[y0:y1, x0:x1] = True

# Explicitly protect player identifiers, numeric glyphs, bars/ticks/arrows and all other atlas regions.
protected_region_indices = sorted(set(i for i in regs if i not in (24, 25, 26)))
protected_before = {}
for idx in protected_region_indices:
    x, y, w, h = regs[idx]
    protected_before[idx] = sa[y:y+h, x:x+w].copy()

# Clean source text/effect alpha only; RGB bytes are later constrained by BC3 patch policy.
clean_arr = sa.copy()
clean_arr[source_union, 3] = 0
clean = Image.fromarray(clean_arr, "RGBA")

def style_from_mask(mask):
    pix = sa[mask]
    p = pix[pix[:, 3] > 24]
    if not len(p):
        p = pix
    lum = p[:, :3].astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    hi = p[lum >= np.quantile(lum, 0.68)]
    lo = p[lum <= np.quantile(lum, 0.25)]
    if not len(hi):
        hi = p
    if not len(lo):
        lo = p
    fill = tuple(int(np.median(hi[:, k])) for k in range(3)) + (255,)
    stroke = tuple(int(np.median(lo[:, k])) for k in range(3)) + (255,)
    if sum(fill[:3]) - sum(stroke[:3]) < 100:
        fill = tuple(min(255, int(v) + 75) for v in fill[:3]) + (255,)
        stroke = tuple(max(0, int(v) - 45) for v in stroke[:3]) + (255,)
    return fill, stroke

def shear_alpha(alpha, shear=0.14):
    w, h = alpha.size
    extra = int(math.ceil(abs(shear) * h)) + 2
    return alpha.transform(
        (w + extra, h),
        Image.Transform.AFFINE,
        (1.0, -shear, shear * h, 0.0, 1.0, 0.0),
        resample=Image.Resampling.BICUBIC,
    )

def make_text_alpha(text, fs, stroke_w, italic):
    font = ImageFont.truetype(FONT, fs)
    d = ImageDraw.Draw(Image.new("L", (8, 8), 0))
    tb = d.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
    pad = stroke_w + 6
    a = Image.new("L", (max(8, tb[2]-tb[0]+2*pad), max(8, tb[3]-tb[1]+2*pad)), 0)
    ImageDraw.Draw(a).text(
        (pad-tb[0], pad-tb[1]), text, font=font, fill=255, stroke_width=stroke_w, stroke_fill=255
    )
    bb = a.getbbox()
    if not bb:
        return None
    a = a.crop(bb)
    if italic:
        a = shear_alpha(a, 0.16)
        bb = a.getbbox()
        if bb:
            a = a.crop(bb)
    return a

def render_element(e):
    x0, y0, x1, y1 = e["original_bbox"]
    # Any target-containing BC3 block must be wholly inside the exact source bbox.
    bx0 = ((x0 + 3) // 4) * 4
    by0 = ((y0 + 3) // 4) * 4
    bx1 = (x1 // 4) * 4
    by1 = (y1 // 4) * 4
    if bx1 - bx0 < 12 or by1 - by0 < 12:
        raise RuntimeError(("no DXT5-safe interior", e["region_idx"], e["source"], e["original_bbox"]))
    # Keep only the policy-required positive pixel margin; do not shrink the source hierarchy
    # with an arbitrary 4px inner inset. Any target-containing 4x4 block still remains wholly
    # inside [bx0,by0,bx1,by1].
    ax0 = bx0 + (1 if bx0 == x0 else 0)
    ay0 = by0 + (1 if by0 == y0 else 0)
    ax1 = bx1 - (1 if bx1 == x1 else 0)
    ay1 = by1 - (1 if by1 == y1 else 0)
    maxw = ax1 - ax0
    maxh = ay1 - ay0

    fill, stroke = style_from_mask(e["source_mask"])
    italic = e["kind"] == "extra_time"
    start_fs = min(160, max(16, int((y1-y0) * (1.02 if e["kind"] == "bar_label" else 0.94))))
    best = None
    for fs in range(start_fs, 11, -1):
        stroke_w = max(1, int(round(fs * (0.085 if e["kind"] == "bar_label" else 0.075))))
        a = make_text_alpha(e["korean"], fs, stroke_w, italic)
        if a is None:
            continue
        scale = min(1.0, maxw / max(1, a.width), maxh / max(1, a.height))
        if scale < 0.50:
            continue
        if scale < 0.999:
            a = a.resize((max(1, int(a.width*scale)), max(1, int(a.height*scale))), Image.Resampling.LANCZOS)
            bb = a.getbbox()
            if bb:
                a = a.crop(bb)
        if a.width <= maxw and a.height <= maxh:
            best = (fs, stroke_w, a)
            break
    if best is None:
        raise RuntimeError(("render fit failed", e["region_idx"], e["source"], e["korean"], e["original_bbox"]))
    fs, stroke_w, a = best

    # Source-derived fill + dark outline. This follows the already-approved C86 semantic style
    # while keeping A8's own palette.
    inner = a.filter(ImageFilter.MinFilter(3))
    tile = Image.new("RGBA", a.size, (0, 0, 0, 0))
    outline_layer = Image.new("RGBA", a.size, stroke)
    outline_layer.putalpha(a)
    tile.alpha_composite(outline_layer)
    fill_layer = Image.new("RGBA", a.size, fill)
    fill_layer.putalpha(inner)
    tile.alpha_composite(fill_layer)

    px = ax0 + max(0, (maxw - a.width) // 2)
    py = ay0 + max(0, (maxh - a.height) // 2)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.alpha_composite(tile, (px, py))
    lb = layer.getchannel("A").getbbox()
    if not lb:
        raise RuntimeError(("empty localized render", e["region_idx"], e["source"]))
    lw, lh = lb[2] - lb[0], lb[3] - lb[1]
    sw, sh = x1 - x0, y1 - y0
    if not (lb[0] > x0 and lb[1] > y0 and lb[2] < x1 and lb[3] < y1 and lw <= sw and lh <= sh):
        raise RuntimeError(("pre-encode bbox gate", e["region_idx"], e["source"], e["original_bbox"], list(lb)))

    e.update({
        "block_safe_bbox": [bx0, by0, bx1, by1],
        "localized_bbox_preencode": list(lb),
        "source_width": sw,
        "source_height": sh,
        "localized_width_preencode": lw,
        "localized_height_preencode": lh,
        "delta_left_preencode": lb[0] - x0,
        "delta_right_preencode": x1 - lb[2],
        "delta_top_preencode": lb[1] - y0,
        "delta_bottom_preencode": y1 - lb[3],
        "containment_preencode": "PASS",
        "size_ceiling_preencode": "PASS",
        "positive_margin_preencode": "PASS",
        "font_file": Path(FONT).name,
        "font_size": fs,
        "stroke_width": stroke_w,
        "italic_shear": 0.16 if italic else 0.0,
        "fill_rgba": list(fill),
        "stroke_rgba": list(stroke),
    })
    return layer

final = clean.copy()
layers = []
target_union = np.zeros((H, W), dtype=bool)
for e in elements:
    layer = render_element(e)
    lm = np.asarray(layer.getchannel("A")) > 0
    if np.any(target_union & lm):
        raise RuntimeError(("localized overlap", e["region_idx"], e["source"], int(np.count_nonzero(target_union & lm))))
    target_union |= lm
    layers.append(layer)
    final.alpha_composite(layer)

touch_count = 0
layer_masks = [np.asarray(z.getchannel("A")) > 0 for z in layers]
for i, m1 in enumerate(layer_masks):
    dil = np.asarray(
        Image.fromarray((m1.astype(np.uint8) * 255), "L").filter(ImageFilter.MaxFilter(3))
    ) > 0
    for j in range(i + 1, len(layer_masks)):
        touch_count += int(np.count_nonzero(dil & layer_masks[j]))
if touch_count:
    raise RuntimeError(("localized 1px touch", touch_count))

# Encode full raw image once, then transplant only BC3 blocks proven safe.
raw_final = final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
tmp_png = tmp / "A8CE_final_raw.png"
tmp_dds = tmp / "A8CE_final_nv.dds"
raw_final.save(tmp_png)
subprocess.run(
    ["/usr/bin/nvcompress", "-bc3", "-nomips", str(tmp_png), str(tmp_dds)],
    check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)
tb = tmp_dds.read_bytes()
dds_meta(tb)

allowed_raw = np.flipud(allowed)
source_raw = np.flipud(source_union)
target_raw = np.flipud(target_union)
source_alpha_raw = np.flipud(sa[:, :, 3])
bw, bh = W // 4, H // 4
outb = bytearray(sb)
target_blocks = set()
source_full_blocks = set()
source_partial_blocks = set()

def alpha_indices(block):
    bits = int.from_bytes(block[2:8], "little")
    return [(bits >> (3 * i)) & 7 for i in range(16)]

def set_alpha_indices(block, idx):
    bits = sum((int(v) & 7) << (3 * i) for i, v in enumerate(idx))
    return block[:2] + bits.to_bytes(6, "little") + block[8:]

for by in range(bh):
    y = by * 4
    if not np.any(allowed_raw[y:y+4]):
        continue
    for bx in range(bw):
        x = bx * 4
        am = allowed_raw[y:y+4, x:x+4]
        sm = source_raw[y:y+4, x:x+4]
        tm = target_raw[y:y+4, x:x+4]
        if not np.any(sm) and not np.any(tm):
            continue
        off = 128 + (by * bw + bx) * 16
        if np.any(tm):
            if not np.all(am):
                raise RuntimeError(("target block crosses exact bbox", bx, by))
            outb[off:off+16] = tb[off:off+16]
            target_blocks.add((bx, by))
            continue
        if np.all(am):
            outb[off:off+16] = tb[off:off+8] + sb[off+8:off+16]
            source_full_blocks.add((bx, by))
            continue

        # Boundary cleanup: preserve original alpha endpoints and BC1 color bytes;
        # only source-owned alpha indices may change.
        ob = bytes(outb[off:off+16])
        idxs = alpha_indices(ob)
        a4 = source_alpha_raw[y:y+4, x:x+4]
        zero_candidates = [
            idxs[yy*4+xx]
            for yy in range(4)
            for xx in range(4)
            if not sm[yy, xx] and a4[yy, xx] <= 1
        ]
        if not zero_candidates:
            raise RuntimeError(("partial block lacks protected transparent alpha index", bx, by))
        zi = Counter(zero_candidates).most_common(1)[0][0]
        for yy in range(4):
            for xx in range(4):
                if sm[yy, xx]:
                    idxs[yy*4+xx] = zi
        nb = set_alpha_indices(ob, idxs)
        if nb[:2] != ob[:2] or nb[8:] != ob[8:]:
            raise RuntimeError(("boundary endpoint/color drift", bx, by))
        outb[off:off+16] = nb
        source_partial_blocks.add((bx, by))

candidate.write_bytes(outb)
candidate_sha = sha256_bytes(bytes(outb))
dec_raw = Image.open(candidate).convert("RGBA")
dec = dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
da = np.asarray(dec, dtype=np.uint8)

# Global decoded protection gates.
diff = np.any(sa != da, axis=2)
diff_out = int(np.count_nonzero(diff & ~allowed))
alpha_out = int(np.count_nonzero((sa[:, :, 3] != da[:, :, 3]) & ~allowed))
introduced_visible_out = int(np.count_nonzero((sa[:, :, 3] <= 1) & (da[:, :, 3] > 1) & ~allowed))
if diff_out or alpha_out or introduced_visible_out:
    raise RuntimeError(("decoded protected drift", diff_out, alpha_out, introduced_visible_out))

# Every non-target source pixel must be gone at visible alpha threshold.
guard = np.asarray(
    Image.fromarray((target_union.astype(np.uint8) * 255), "L").filter(ImageFilter.MaxFilter(5))
) > 0
source_residue = int(np.count_nonzero(source_union & (da[:, :, 3] > 8) & ~guard))
if source_residue:
    raise RuntimeError(("source residue", source_residue))

# Protected atlas cells must stay decoded-pixel exact.
protected_changed = {}
for idx, before in protected_before.items():
    x, y, w, h = regs[idx]
    protected_changed[str(idx)] = int(np.count_nonzero(np.any(before != da[y:y+h, x:x+w], axis=2)))
if any(protected_changed.values()):
    raise RuntimeError(("protected atlas region changed", {k:v for k,v in protected_changed.items() if v}))

# Decode-time bbox/size/positive-margin gates for all five physical labels.
for e in elements:
    x0, y0, x1, y1 = e["original_bbox"]
    cm = da[y0:y1, x0:x1, 3] > 8
    ys, xs = np.nonzero(cm)
    if not len(xs):
        raise RuntimeError(("decoded element empty", e["region_idx"], e["source"]))
    db = [x0+int(xs.min()), y0+int(ys.min()), x0+int(xs.max())+1, y0+int(ys.max())+1]
    dw, dh = db[2]-db[0], db[3]-db[1]
    sw, sh = x1-x0, y1-y0
    contain = db[0] >= x0 and db[1] >= y0 and db[2] <= x1 and db[3] <= y1
    size_ok = dw <= sw and dh <= sh
    positive = db[0] > x0 and db[1] > y0 and db[2] < x1 and db[3] < y1
    if not (contain and size_ok and positive):
        raise RuntimeError(("decoded bbox gate", e["region_idx"], e["source"], e["original_bbox"], db))
    e.update({
        "localized_bbox": db,
        "localized_width": dw,
        "localized_height": dh,
        "delta_left": db[0]-x0,
        "delta_right": x1-db[2],
        "delta_top": db[1]-y0,
        "delta_bottom": y1-db[3],
        "containment": "PASS",
        "size_ceiling": "PASS",
        "positive_margin": "PASS",
    })

# No post-encode localized bboxes may overlap or 1px-touch.
post_boxes = [e["localized_bbox"] for e in elements]
post_overlap = 0
post_touch = 0
for i, a in enumerate(post_boxes):
    for b in post_boxes[i+1:]:
        ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
        iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
        post_overlap += ix * iy
        near = not (a[2] < b[0]-1 or b[2] < a[0]-1 or a[3] < b[1]-1 or b[3] < a[1]-1)
        if near and ix * iy == 0:
            post_touch += 1
if post_overlap or post_touch:
    raise RuntimeError(("post encode overlap/touch", post_overlap, post_touch))

# PNG validator is an extra decoded scope guard; DXT5 byte checks above remain authoritative.
def save_mask(arr, name):
    p = out / name
    Image.fromarray((arr.astype(np.uint8) * 255), "L").save(p)
    return p

source_png = out / "B160_SOURCE_READABLE.png"
clean_png = out / "B160_CLEAN_READABLE.png"
final_png = out / "B160_FINAL_READABLE.png"
src.save(source_png)
clean.save(clean_png)
dec.save(final_png)
allowed_path = save_mask(allowed, "B160_ALLOWED_BBOX_MASK.png")
protected_path = save_mask(~allowed, "B160_PROTECTED_MASK.png")
save_mask(source_union, "B160_SOURCE_TEXT_MASK.png")
save_mask(target_union, "B160_LOCALIZED_RENDER_MASK.png")

validator = repo / "tools/localization/validate_clean_plate.py"
subprocess.run(
    ["python3", str(validator), str(source_png), str(clean_png), str(allowed_path),
     "--protected-mask", str(protected_path), "--report", str(out / "B160_CLEAN_VALIDATION.json")],
    check=True,
)
subprocess.run(
    ["python3", str(validator), str(source_png), str(final_png), str(allowed_path),
     "--protected-mask", str(protected_path), "--report", str(out / "B160_FINAL_VALIDATION.json")],
    check=True,
)
clean_validation = json.loads((out / "B160_CLEAN_VALIDATION.json").read_text())
final_validation = json.loads((out / "B160_FINAL_VALIDATION.json").read_text())
if clean_validation.get("status") != "PASS" or final_validation.get("status") != "PASS":
    raise RuntimeError(("decoded PNG validator", clean_validation.get("status"), final_validation.get("status")))

def composite(im, bg=(72, 72, 72, 255)):
    z = Image.new("RGBA", im.size, bg)
    z.alpha_composite(im)
    return z.convert("RGB")

def save_jpg_b64(im, name, quality=95):
    p = out / name
    im.convert("RGB").save(p, quality=quality, optimize=True)
    (out / (name + ".b64.txt")).write_text(base64.b64encode(p.read_bytes()).decode("ascii"))

# Focus evidence for each localized atlas cell.
for idx in (24, 25, 26):
    x, y, w, h = regs[idx]
    pad = 20
    box = (max(0, x-pad), max(0, y-pad), min(W, x+w+pad), min(H, y+h+pad))
    ims = [composite(im.crop(box)) for im in (src, clean, dec)]
    scale = min(3.0, 1800 / max(1, ims[0].width))
    ims = [im.resize((max(1, int(im.width*scale)), max(1, int(im.height*scale))), Image.Resampling.NEAREST) for im in ims]
    card = Image.new("RGB", (sum(im.width for im in ims)+20, max(im.height for im in ims)+50), "white")
    dr = ImageDraw.Draw(card)
    xx = 0
    for label, im in zip(("SOURCE", "CLEAN", "FINAL"), ims):
        card.paste(im, (xx, 50))
        dr.text((xx+6, 12), label, fill="black")
        xx += im.width + 10
    save_jpg_b64(card, f"B160_IDX{idx}_SOURCE_CLEAN_FINAL.jpg", 96)

overview = Image.new("RGB", (1600, 3*830), "white")
for i, (label, im) in enumerate((("SOURCE", src), ("CLEAN", clean), ("FINAL", dec))):
    z = composite(im)
    z.thumbnail((1580, 790), Image.Resampling.LANCZOS)
    overview.paste(z, (0, i*830+32))
    ImageDraw.Draw(overview).text((8, i*830+8), label, fill="black")
save_jpg_b64(overview, "B160_A8CE_SOURCE_CLEAN_FINAL.jpg", 93)

raw_overview = Image.new("RGB", (1600, 2*830), "white")
for i, (label, im) in enumerate((("SOURCE_RAW_MIRROR_Y", raw_src), ("FINAL_RAW_MIRROR_Y", dec_raw))):
    z = composite(im)
    z.thumbnail((1580, 790), Image.Resampling.LANCZOS)
    raw_overview.paste(z, (0, i*830+32))
    ImageDraw.Draw(raw_overview).text((8, i*830+8), label, fill="black")
save_jpg_b64(raw_overview, "B160_A8CE_RAW_COMPARE.jpg", 93)

serial_elements = []
for e in elements:
    d = {k:v for k,v in e.items() if k != "source_mask"}
    serial_elements.append(d)

report = {
    "schema_version": 1,
    "role": "B",
    "run": run,
    "queue_index": 52,
    "asset": asset,
    "readiness_tier": "ZOOM_REVIEW_POSITIVE_CLASSIFICATION_AND_PRODUCTION_SAME_INVOCATION",
    "source_provenance": {
        "repository": "Sonic-TV/OR2006Sprites",
        "commit": COMMIT,
        "source_sha256": SOURCE_SHA256,
    },
    "classification": {
        "prior_action": "zoom_review",
        "decision": "LOCALIZE_TEXT",
        "semantic_segments": [
            {"source": "Extra Time", "korean": "추가 시간", "physical_occurrences": 1},
            {"source": "Start", "korean": "시작", "physical_occurrences": 2},
            {"source": "Goal", "korean": "골", "physical_occurrences": 2},
        ],
        "protected": [
            "0-9 numeric sprites",
            "1P-6P player identifiers",
            "progress bars/ticks/arrows",
            "track fragments and non-text artwork",
        ],
    },
    "same_family_precedent": C86_PRECEDENT,
    "structure": {
        "width": W,
        "height": H,
        "format": FOURCC.decode("ascii"),
        "mipmaps": MIPS,
        "header_128_exact": bytes(outb[:128]) == sb[:128],
        "raw_orientation": "mirror_y",
    },
    "elements": serial_elements,
    "machine_checks": {
        "bbox_size_positive_margin": "5/5 PASS",
        "decoded_changed_outside_exact_source_bboxes": diff_out,
        "alpha_changed_outside_exact_source_bboxes": alpha_out,
        "introduced_visible_outside_exact_source_bboxes": introduced_visible_out,
        "source_script_residue_pixels": source_residue,
        "protected_atlas_changed_pixels": int(sum(protected_changed.values())),
        "localized_overlap_pixels": post_overlap,
        "localized_1px_touch_pairs": post_touch,
        "clean_png_validator": clean_validation.get("status"),
        "final_png_validator": final_validation.get("status"),
    },
    "compressed_patch": {
        "target_reencoded_blocks": len(target_blocks),
        "source_only_full_alpha_blocks": len(source_full_blocks),
        "boundary_alpha_index_only_blocks": len(source_partial_blocks),
        "changed_blocks": len(target_blocks | source_full_blocks | source_partial_blocks),
        "boundary_endpoints_and_color_bytes_preserved": True,
        "target_block_rule": "WHOLE_4X4_BLOCK_MUST_BE_INSIDE_EXACT_SOURCE_BBOX",
        "source_boundary_rule": "PRESERVE_ALPHA_ENDPOINTS_AND_BC1_COLOR_BYTES_CHANGE_SOURCE_OWNED_ALPHA_INDICES_ONLY",
    },
    "candidate_sha256": candidate_sha,
    "candidate_path": str(candidate.relative_to(repo)),
    "worker_static_qa": "PASS",
    "controller_visual_qa": "PENDING_CONTROLLER_SELF_QA",
    "status": "B160_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
    "runtime_validation": "UNTESTED",
}
(out / "B160_A8CE_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

(wr / "B160_A8CE339F.json").write_text(json.dumps({
    "run": "B160",
    "index": 52,
    "asset": "A8CE339F",
    "candidate_sha256": candidate_sha,
    "localized_semantic_segments": 3,
    "localized_physical_elements": 5,
    "bbox_size_positive_margin": "5/5 PASS",
    "outside": diff_out,
    "alpha_outside": alpha_out,
    "introduced_visible_outside": introduced_visible_out,
    "source_residue": source_residue,
    "protected_atlas_changed_pixels": int(sum(protected_changed.values())),
    "overlap": post_overlap,
    "touch": post_touch,
    "worker_status": report["status"],
    "report": f"localization/graphics/role_B/{run}/B160_A8CE_REPORT.json",
    "runtime_validation": "UNTESTED",
}, ensure_ascii=False, indent=2) + "\n")

print(json.dumps({
    "run": "B160",
    "asset": "A8CE339F",
    "candidate_sha256": candidate_sha,
    "structure": "2048x1024 DXT5 mirror_y",
    "localized_physical_elements": 5,
    "bbox_size_positive_margin": "5/5 PASS",
    "outside": diff_out,
    "alpha_outside": alpha_out,
    "introduced_visible_outside": introduced_visible_out,
    "source_residue": source_residue,
    "protected_atlas_changed_pixels": int(sum(protected_changed.values())),
    "overlap": post_overlap,
    "touch": post_touch,
}, ensure_ascii=False), flush=True)
