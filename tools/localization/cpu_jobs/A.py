#!/usr/bin/env python3
"""A243 q193: source-native mixed numeral/Hangul '15 CONT.' lettering pilot.

Only one exact native atlas cell; NO official hd_candidates promotion.
A243 material change: rebuild a true transparent CLEAN from canonical English
rather than reuse A208's six text-bearing inherited "CLEAN" cells, and draw
native Noto heavy real Hangul outlines with source-width hierarchy guard.
"""
import csv
import hashlib
import io
import json
import os
import struct
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

assert os.environ.get("OUTRUN_CPU_WORKER") == "github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE") == "A"
ROOT = Path.cwd()
OUT = ROOT / "localization/graphics/role_A/20261011-A243-Q193-15CONT-SOURCE-CLEAN-PILOT"
OUT.mkdir(parents=True, exist_ok=True)
ASSET = "97E863AD_512x256.dds"
CURRENT = ROOT / "localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst" / ASSET
SOURCE_URL = ("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
              "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/"
              "spr_sprani_sumo_fe_cvt_Exst/" + ASSET)
SOURCE_SHA = "d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451"
BASE_SHA = "9ea15d130693dd99bcd0ffa445b4799132665c5c93728c1c11783c94ba25b0f3"
SOURCE_BBOX = (1413, 221, 1622, 268)  # C1 2026-10-11 first independent native bbox
CELL = (1408, 215, 1628, 274)         # inclusive space isolates English letters
ENGLISH = "15 CONT."
KOREAN = "15 연속전"  # semantic '15 continuous races'; game-language confirmation pending
FONT = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
FONT_INDEX = 1
FONT_SIZE = 44
AA = 4

def sha(b): return hashlib.sha256(b).hexdigest()
def file_sha(p): return sha(p.read_bytes())
def ref(p): return {"path": str(p.relative_to(ROOT)), "sha256": file_sha(p)}
def save_png(name, im):
    p = OUT / name
    im.save(p, "PNG")
    return ref(p)
def save_json(name, obj):
    p = OUT / name
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ref(p)
def decoded(b):
    assert b[:4] == b"DDS " and len(b) == 128 + 2048 * 1024 * 4
    assert struct.unpack_from("<II", b, 12) == (1024, 2048)
    assert struct.unpack_from("<I", b, 28)[0] == 1
    assert struct.unpack_from("<I", b, 88)[0] == 32
    assert struct.unpack_from("<IIII", b, 92) == (255, 65280, 16711680, 4278190080)
    return Image.frombytes("RGBA", (2048, 1024), b[128:]).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def opaque(im, bg):
    return Image.alpha_composite(Image.new("RGBA", im.size, (*bg, 255)), im).convert("RGB")
def check(q, reason):
    if not q: raise RuntimeError(reason)

assert FONT.is_file()
with (ROOT / "localization/graphics/asset_queue.csv").open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
row = next(x for x in rows if x["index"].strip("\ufeff") == "193")
check(row["action"] == "localize_text" and "rework" in row["artwork_status"].lower(),
      "q193 no longer an active A rework; stop")
import subprocess, sys
triage = subprocess.run([sys.executable, "tools/localization/rework_triage.py", "--index", "193"],
                        capture_output=True, text=True, check=True)
save_json("A243_TRIAGE.json", {"actual_exit": triage.returncode, "stdout": triage.stdout,
                               "chosen": "material correction to 15 CONT. of C1 six inherited failed cells"})
base_bytes = CURRENT.read_bytes()
check(sha(base_bytes) == BASE_SHA, "q193 official candidate SHA changed, fail closed")
old = decoded(base_bytes)
with tempfile.TemporaryDirectory(prefix="a243-original-") as t:
    source_path = Path(t) / ASSET
    urllib.request.urlretrieve(SOURCE_URL, source_path)
    src_bytes = source_path.read_bytes()
    check(sha(src_bytes) == SOURCE_SHA, "canonical English upstream SHA mismatch")
    check(src_bytes[:128] == base_bytes[:128], "DDS header or pixel format drift")
    source = decoded(src_bytes)
    (OUT / "A243_PINNED_CANONICAL_SOURCE.dds").write_bytes(src_bytes)

s = np.asarray(source).copy()
b = np.asarray(old).copy()
x0, y0, x1, y1 = CELL
alpha_region = s[y0:y1, x0:x1, 3] > 0
check(int(alpha_region.sum()) > 2000, "source English region alpha not found")
ys, xs = np.nonzero(alpha_region)
original_bbox = (x0+int(xs.min()), y0+int(ys.min()),
                 x0+int(xs.max())+1, y0+int(ys.max())+1)
check(original_bbox == SOURCE_BBOX, f"canonical English bbox drift {original_bbox}")
check(all(a >= x0 and c <= x1 for a,c in [(SOURCE_BBOX[0], SOURCE_BBOX[2])]) and
      SOURCE_BBOX[1] >= y0 and SOURCE_BBOX[3] <= y1, "outside isolated target cell")
# P1: source-derived transparent plate for exactly one sprite. Other cells are
# byte-for-byte preserved; the contaminated A208 CLEAN is never reused.
clean_a = b.copy()
clean_a[y0:y1, x0:x1] = 0
check(np.count_nonzero(clean_a[y0:y1, x0:x1, 3]) == 0, "source plate not empty")
check(np.array_equal(b[:y0], clean_a[:y0]) and np.array_equal(b[y1:], clean_a[y1:]),
      "CLEAN changed outside row")
clean = Image.fromarray(clean_a, "RGBA")
save_png("A243_SOURCE_READABLE.png", source)
save_png("A243_BEFORE_READABLE.png", old)
save_png("A243_PLATE_ONLY_READABLE.png", clean)
save_png("A243_PLATE_ONLY_RAW.png", clean.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
save_png("A243_SOURCE_ONLY_NATIVE.png", source.crop(SOURCE_BBOX))
save_png("A243_PLATE_ONLY_NATIVE.png", clean.crop(SOURCE_BBOX))
# P2: true native heavy Hangul face at 4x raster resolution, 15 numeral retained.
# No arbitrary source-width stretch, fabricated image-generation, or old font pixels.
fnt = ImageFont.truetype(str(FONT), FONT_SIZE * AA, index=FONT_INDEX)
text_canvas = Image.new("L", (1000 * AA, 120 * AA))
draw = ImageDraw.Draw(text_canvas)
draw.text((20*AA, 0), KOREAN, font=fnt, fill=255)
gbox = text_canvas.getbbox()
check(gbox is not None, "font produced empty native glyph")
tight = text_canvas.crop(gbox)
glyph = tight.resize((round(tight.width / AA), round(tight.height / AA)), Image.Resampling.LANCZOS)
aw, ah = SOURCE_BBOX[2]-SOURCE_BBOX[0], SOURCE_BBOX[3]-SOURCE_BBOX[1]
check(0.74 <= glyph.width/aw <= 0.95 and .78 <= glyph.height/ah <= .94,
      f"source hierarchy unmet: {glyph.size}, source {(aw, ah)}")
gx = SOURCE_BBOX[0] + 3
gy = SOURCE_BBOX[1] + (ah-glyph.height)//2
check(gx + glyph.width <= SOURCE_BBOX[2]-2 and gy >= SOURCE_BBOX[1]+1 and
      gy + glyph.height <= SOURCE_BBOX[3]-1, "lettering exceeds source 1px ceiling")
# Source-derived opaque face color; alpha/spacing/effects remain native and
# no added background rectangle, rim, unwanted bevel, or fake Hangul stroke.
source_face = s[SOURCE_BBOX[1]:SOURCE_BBOX[3], SOURCE_BBOX[0]:SOURCE_BBOX[2]]
colors = source_face[:, :, :3][source_face[:, :, 3] >= 230]
check(len(colors) > 100, "unable to measure original English face color")
face_rgb = tuple(int(x) for x in np.median(colors, axis=0))
geometry_readable = Image.new("L", (2048, 1024))
geometry_readable.paste(glyph, (gx, gy))
geometry_raw = geometry_readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
geom_ref = save_png("A243_GEOMETRY_RAW_L.png", geometry_raw)
letter_readable = Image.new("RGBA", (2048, 1024))
face = Image.new("RGBA", glyph.size, (*face_rgb, 0))
face.putalpha(glyph)
letter_readable.alpha_composite(face, (gx, gy))
letter_raw = letter_readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
face_ref = save_png("A243_FACE_RAW.png", letter_raw)
# P3: only an isolated ROI is blended; all original other atlas pixels
# including transparent hidden RGB and protected art remain byte-identical.
final_a = clean_a.copy()
final_crop = Image.alpha_composite(clean.crop(CELL), letter_readable.crop(CELL))
final_a[y0:y1, x0:x1] = np.asarray(final_crop)
check(np.array_equal(final_a[:, :x0], b[:, :x0]) and
      np.array_equal(final_a[:, x1:], b[:, x1:]), "neighboring atlas columns changed")
new_rgba = np.any(final_a != b, axis=2)
allowed = np.zeros(new_rgba.shape, bool)
allowed[y0:y1, x0:x1] = True
check(int(np.count_nonzero(new_rgba & ~allowed)) == 0, "other sprite/protected art changed")
alpha_new = final_a[y0:y1, x0:x1, 3] > 0
ys, xs = np.nonzero(alpha_new)
check(len(xs) > 300, "native Hangul candidate vanished")
candidate_bbox=(x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1)
check(candidate_bbox[0] >= SOURCE_BBOX[0]+1 and
      candidate_bbox[1] >= SOURCE_BBOX[1]+1 and
      candidate_bbox[2] <= SOURCE_BBOX[2]-1 and
      candidate_bbox[3] <= SOURCE_BBOX[3]-1, "saved mask escaped source")
out = OUT / "A243_Q193_15CONT_TRUE_CLEAN_NATIVE_TRIAL_UNPROMOTED.dds"
final_image=Image.fromarray(final_a,"RGBA")
out.write_bytes(src_bytes[:128] + final_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw", "RGBA"))
persisted=decoded(out.read_bytes())
check(np.array_equal(np.asarray(persisted), final_a), "persisted native DDS decode mismatch")
save_png("A243_PERSISTED_FLIPY_READABLE.png", persisted)
save_png("A243_PERSISTED_RAW.png", persisted.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
save_png("A243_LETTERING_ONLY_READABLE.png", letter_readable)
# independent comparisons available for manual producer self-review, not C approval
cx0,cy0,cx1,cy1=(1393,207,1643,282)
for name, bg in [("GRAY",(100,100,100)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
    panels=[opaque(x,bg).crop((cx0,cy0,cx1,cy1)) for x in
            (source, old, clean, letter_readable, persisted)]
    for pct in (100,75,50):
        width=max(1,round((cx1-cx0)*pct/100))
        height=max(1,round((cy1-cy0)*pct/100))
        panel=Image.new("RGB",(width*len(panels),height),bg)
        for i,p in enumerate(panels):
            panel.paste(p.resize((width,height),Image.Resampling.LANCZOS),(i*width,0))
        save_png(f"A243_SOURCE_OLD_CLEAN_GLYPH_SAVED_{name}_{pct}.png",panel)
# File outputs are *evidence and trial*, not official production candidate.
recipe=save_json("A243_NATIVE_FONT_GEOMETRY_RECIPE.json", {
    "version": "source-native-a243-geometry-v1", "queue_index": 193,
    "source": ref(OUT / "A243_PINNED_CANONICAL_SOURCE.dds"),
    "font": {"path_on_runner": str(FONT), "sha256": file_sha(FONT),
             "family": "NotoSansCJK-Bold", "font_index":FONT_INDEX,
             "license": "SIL Open Font License 1.1"},
    "text": KOREAN, "english": ENGLISH, "native_point_size": FONT_SIZE,
    "raster_supersampling": AA, "coordinates": "native_readable_then_raw_mirror_y",
    "glyph_bbox": candidate_bbox, "source_bbox": SOURCE_BBOX,
    "face_color_measured_source_rgba_median": face_rgb,
    "source_style_qualification": "PENDING_FIRSTHAND_AND_C2",
    "method_delta": "C1 six legacy underfilled cells: this one independently source-derived clean + font contours; no reused low-res Korean"}
)
report={
    "schema_version":2,"run":"A243","role":"A","index":193,
    "source_sha256":SOURCE_SHA,"previous_official_sha256":BASE_SHA,
    "new_trial_sha256":file_sha(out),"candidate_path":str(out.relative_to(ROOT)),
    "source_english":ENGLISH,"semantic_korean":KOREAN,
    "original_bbox":SOURCE_BBOX,"result_bbox":candidate_bbox,
    "width_ratio":round((candidate_bbox[2]-candidate_bbox[0])/aw,4),
    "height_ratio":round((candidate_bbox[3]-candidate_bbox[1])/ah,4),
    "glyph_rect":(gx,gy,gx+glyph.width,gy+glyph.height),
    "clean_alpha_remaining":0,
    "previous_to_trial_rgba_changed":int(np.count_nonzero(new_rgba)),
    "changed_outside_roi":int(np.count_nonzero(new_rgba & ~allowed)),
    "raw_flip_y_roundtrip":True,"header_equal":src_bytes[:128]==base_bytes[:128],
    "font_geometry_ref":geom_ref,"face_ref":face_ref,
    "geometry_recipe_ref":recipe,
    "producer_gate":"SCOPED_NUMERIC_PASS_PENDING_MANUAL_NATIVE_100_75_50_VISUAL",
    "status":"UNPROMOTED_TRIAL_PENDING_PRODUCER_OPTICAL_AND_C2",
    "no_official_hd_candidate_change":True,"c2":"NOT_RUN","c3":"NOT_RUN",
    "user_actual_game_retest":"OPEN_IGR003_IGR019_IGR033",
    "RUNTIME_VALIDATION":"UNTESTED",
    "exclusions":["VR","FFB","DX11","DXVK"],
    "execution_backend":"github-actions-binary-DDs-source-not-materialized-chatgpt"
}
save_json("A243_MACHINE_AND_HANDOFF.json",report)
print(json.dumps({"A243":"NEW_PERSISTED_SCOPED_TRIAL","sha":report["new_trial_sha256"],
                  "width_ratio":report["width_ratio"],"modified_px":report["previous_to_trial_rgba_changed"],
                  "promotion":0},ensure_ascii=False),flush=True)
