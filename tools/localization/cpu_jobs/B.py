#!/usr/bin/env python3
"""B324 q214: lossless canonical-source clean-plate boundary repair.

This is a one-stage PRE-RENDER reconstruction proof for METHOD_CHANGE_REQUIRED,
not a repeat of B260/B261's rejected SDF/palette DDS generation.  Output is a
source-native CLEAN_PLATE and independent, lossless contacts; no unapproved
BC3 candidate is touched or marked producer/C PASS.
"""
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation

assert os.getenv("OUTRUN_CPU_WORKER") == "github-actions"
assert os.getenv("OUTRUN_CPU_ROLE") == "B"
G = Path("localization/graphics")
R = Path("localization/graphics/role_B/20261009-B324-Q214-CANONICAL-PLATE-BOUNDARY")
R.mkdir(parents=True, exist_ok=True)
rel = Path("textures/load/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds")
clean_path = G / "role_B/20261006-B-PRODUCTION194-BF229CF4-START-GOAL/B194_CLEAN_PLATE.png"
src_url = ("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
           "3da79726739ac631d8e2703a65330dbb0c310770/"
           "Release/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds")
source_hash = "9a2e428bdb87399a7589338053b49efdcfd103d14f12a33a4bcde7705ab76c6b"
current_hash = "ace42cb3d539df7c538c6d93b6c3f001e3d18e4f41aaa29bdab1466fe412fc30"
h = lambda b: hashlib.sha256(b).hexdigest()

with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
    q = next(x for x in csv.DictReader(f) if x["index"].lstrip("\ufeff") == "214")
assert "rework_required" in q["artwork_status"]
p = subprocess.run([sys.executable, "tools/localization/rework_triage.py",
                    "--index", "214"], capture_output=True, text=True, check=True)
triage = json.loads(p.stdout)["assets"][0]
assert triage["next_action"] == "METHOD_CHANGE_REQUIRED", triage
guard = subprocess.run([sys.executable, "tools/localization/rework_triage.py",
                        "--index", "214", "--require-safe-rerender"],
                       capture_output=True, text=True)
assert guard.returncode != 0, "unsafe same-method rerender was unexpectedly permitted"
with urllib.request.urlopen(src_url, timeout=120) as response:
    src_bytes = response.read()
assert h(src_bytes) == source_hash, "canonical source is not pinned"
current_bytes = (G/"hd_candidates"/rel).read_bytes()
assert h(current_bytes) == current_hash, "concurrent q214 revision; stop"
assert src_bytes[:128] == current_bytes[:128], "DDS header mismatch"

def decoded(data):
    return np.array(Image.open(io.BytesIO(data)).convert("RGBA").transpose(
        Image.Transpose.FLIP_TOP_BOTTOM), dtype=np.uint8)

source = decoded(src_bytes)
old = decoded(current_bytes)
archived_bytes = clean_path.read_bytes()
archived = np.array(Image.open(io.BytesIO(archived_bytes)).convert("RGBA"),dtype=np.uint8)
assert source.shape == old.shape == archived.shape == (2048,2048,4)
bboxes = {
    "START": (815,495,899,517),
    "GOAL": (1343,764,1417,787),
}
allowed = np.zeros(source.shape[:2], dtype=bool)
for l,t,r,b in bboxes.values():
    allowed[t:b,l:r] = True
outside_old = np.any(source != archived,axis=2) & ~allowed
outside_count = int(outside_old.sum())
assert 1 <= outside_count < 5000, (
    "original archived CLEAN outside-effect drift changed unexpectedly",outside_count
)
# Restore the EXACT original source outside the authorized glyph-effect regions.
# This is a construction-layer repair only; preserve all original map, photos,
# badge rim, red backdrop and logos, not an attempt to patch finished DDS blocks.
clean = source.copy()
for l,t,r,b in bboxes.values():
    clean[t:b,l:r] = archived[t:b,l:r]
assert int(np.count_nonzero(np.any(clean != source,axis=2)&~allowed)) == 0
assert np.array_equal(clean[~allowed],source[~allowed])
assert np.array_equal(clean[allowed],archived[allowed])
assert int(np.count_nonzero(np.any(clean != archived,axis=2))) == outside_count
assert int(np.count_nonzero((clean[:,:,3]!=source[:,:,3])&~allowed)) == 0
assert np.array_equal(source[:128,:128],clean[:128,:128])
png = R/"B324_CANONICAL_BOUNDARY_CLEAN_PLATE_LOSSLESS.png"
Image.fromarray(clean,"RGBA").save(png,optimize=True)
reload = np.array(Image.open(png).convert("RGBA"))
assert np.array_equal(clean,reload)
def rgba_composite(arr,bg):
    canvas=Image.new("RGBA",(arr.shape[1],arr.shape[0]),(*bg,255))
    canvas.alpha_composite(Image.fromarray(arr,"RGBA"))
    return canvas.convert("RGB")
proofs=[]
rows=[]
for label,(l,t,r,b) in bboxes.items():
    # The visible neighboring badge and white rim are included in the proof,
    # not enlarged as a new valid text region.
    x0,y0,x1,y1=l-26,t-17,r+26,b+17
    delta=np.any(source!=archived,axis=2)[y0:y1,x0:x1]
    def patch(img):
        return img[y0:y1,x0:x1]
    pale=lambda x: ((x[:,:,0]>215)&(x[:,:,1]>148)&(x[:,:,2]>100)&
                    (x[:,:,1]>x[:,:,2]-15)&(x[:,:,3]>32))
    src_pale=int(pale(source[t:b,l:r]).sum())
    clean_pale=int(pale(clean[t:b,l:r]).sum())
    border=np.zeros(source.shape[:2],dtype=bool)
    border[t:b,l:r]=True
    border= binary_dilation(border,iterations=1)&~border
    archived_border_changes=int(np.count_nonzero(np.any(archived!=source,axis=2)&border))
    corrected_border_changes=int(np.count_nonzero(np.any(clean!=source,axis=2)&border))
    assert corrected_border_changes==0
    row={"name":label,"original_source_bbox":[l,t,r,b],
         "source_pale_proxy":src_pale,"clean_pale_proxy":clean_pale,
         "archived_near_boundary_outside_changed":archived_border_changes,
         "repaired_near_boundary_outside_changed":corrected_border_changes,
         "source_minus_repaired_outside_bbox_rgba_pixels":0,
         "source_minus_repaired_outside_bbox_alpha_pixels":0,
         "repaired_vs_archived_inside_bbox_changed":0,
         "plate_only_color_threshold_is_not_visual_acceptance":True}
    rows.append(row)
    for orientation in ("FLIPY","RAW"):
        for bg_name,bg in (("GRAY",(128,128,128)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
            for pct in (100,75,50):
                arrs=[patch(a) for a in (source,archived,clean,old)]
                if orientation=="RAW": arrs=[np.flipud(a) for a in arrs]
                tiles=[rgba_composite(a,bg) for a in arrs]
                if pct!=100:
                    tiles=[x.resize((max(1,round(x.width*pct/100)),
                                     max(1,round(x.height*pct/100))),
                                     Image.Resampling.LANCZOS) for x in tiles]
                sheet=Image.new("RGB",(sum(x.width for x in tiles)+12,
                                        max(x.height for x in tiles)+20),bg)
                pen=ImageDraw.Draw(sheet)
                px=0
                for tile,title in zip(tiles,("SOURCE","ARCHIVED CLEAN","REPAIRED CLEAN","CURRENT DDS")):
                    sheet.paste(tile,(px,20))
                    pen.text((px,2),title,fill=(255,255,0))
                    px+=tile.width+4
                out=R/f"{label}_{orientation}_{bg_name}_{pct}_SOURCE_OLD_CLEAN_REPAIRED_CURRENT.png"
                sheet.save(out,optimize=True)
                proofs.append(str(out.relative_to(G)))
    # Source-visible face / background isolation crop. Not a new bitmap glyph.
    for name,arr in (("SOURCE",source),("ARCHIVED_CLEAN",archived),("REPAIRED_CLEAN",clean)):
        Image.fromarray(patch(arr),"RGBA").save(R/f"{label}_{name}_LOSSLESS.png")
profile={
  "schema_version":1,"run":"B324","role":"B","queue_index":214,
  "decision":"PLATE_ONLY_BOUNDARY_RECONSTRUCTION_PENDING_MANUAL_VECTOR_LETTERING",
  "selection":"METHOD_CHANGE_REQUIRED", "ordinary_rerender_guard_exit":guard.returncode,
  "canonical_source_url":src_url,"canonical_source_sha256":source_hash,
  "current_candidate_sha256_unmodified":current_hash,
  "archived_clean_file":str(clean_path),"archived_clean_file_sha256":h(archived_bytes),
  "new_canonical_repaired_clean_png":str(png),
  "new_clean_png_sha256":h(png.read_bytes()),
  "native":[2048,2048],"source_format":"BC3/DXT5",
  "mirror_y":"AS_SOURCE","source_header":"EXACT",
  "source_archived_clean_modified_rgba_outside_2_boxes":outside_count,
  "source_repaired_clean_modified_rgba_outside_2_boxes":0,
  "source_repaired_clean_alpha_outside_2_boxes":0,
  "source_preserved_artwork_outside_2_boxes":"PIXEL_EXACT",
  "per_label":rows,
  "method_change_next":"Do not reuse B260/B261 flat SDF, palette recolor, shear-only or B259 matte text. Hand-construct per-Hangul-source-family angled vector face with continuous warm-cream highlight and orange undercut, reconcile red stripe under the glyph using this exact clean plate, then BC3-aware encode, persisted source-vs-clean-vs-final 100/75/50, RAW/FLIPY and fresh C2 approval.",
  "new_production_DDS":0,
  "new_lossless_contacts":len(proofs),
  "proofs":proofs,
  "visual_plate_edge":"PENDING_CONTROLLER_DIRECT_SOURCE_CLEAN_REPAIRED_REVIEW",
  "new_glyph_shape":"NOT_PRODUCED_MANUAL_VECTOR_REQUIRED",
  "producer_final_QA":"NOT_RUN",
  "independent_C2":"NOT_RUN","C3":"NOT_RUN","APPROVAL":False,
  "RUNTIME_VALIDATION":"UNTESTED","user_game":"UNTESTED",
  "backend":"GITHUB_ACTIONS","N100_used":False,
  "forbidden_domains_touched":[]
}
(R/"B324_CANONICAL_PLATE_MACHINE.json").write_text(
    json.dumps(profile,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B324_CLEAN_BOUNDARY_READY",outside_count,profile["new_clean_png_sha256"],
      "contacts",len(proofs),"NO_DDS_PROMOTION",flush=True)
