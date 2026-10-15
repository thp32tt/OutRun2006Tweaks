from pathlib import Path
from PIL import Image, ImageChops
import hashlib, json
w=Path.home()/"work/c_roi_q097_normal_20261015_2333"
s=Path.home()/"work/c_roi_q097_20261015_2033/source/Q097_411827E_FULL_ORIGINAL_FLIPY_2048.png"
d=Path.home()/"work/q097_411827e_git_original.dds"
out=w/"output/Q097-normal_reference"
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert h(s)=="2ecc253ac9db49a9c1189f1f814d562a45462b660af94877ce1f66737cfe58af"
assert h(d)=="bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364"
bbox=[1260,850,1560,970]
with Image.open(d) as im: dds=im.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
with Image.open(s) as im: source=im.convert("RGBA")
assert source.size==dds.size==(2048,2048)
assert ImageChops.difference(dds,source).getbbox() is None, "DDS to full-readable source diff"
with Image.open(out/"english_text_roi_native.png") as im: native=im.convert("RGBA")
with Image.open(out/"imagegen_input_upscaled.png") as im: upscaled=im.convert("RGBA")
assert native.size==(300,120) and upscaled.size==(1200,480)
assert ImageChops.difference(source.crop(tuple(bbox)),native).getbbox() is None,"native crop wrong"
assert ImageChops.difference(native.resize((1200,480),resample=Image.Resampling.LANCZOS),upscaled).getbbox() is None,"upscale mismatch"
m=json.loads((out/"roi_manifest.json").read_text())
assert m["schema"]=="outrun-hd-text-roi-v1" and m["isolation"]=="reference_crop"
assert m["english"]=="NORMAL" and m["korean"]=="일반" and m["status"]=="IMAGEGEN_REFERENCE_TEST_ONLY"
assert m["native_png_sha256"]==h(out/"english_text_roi_native.png")
assert m["imagegen_input_sha256"]==h(out/"imagegen_input_upscaled.png")
import numpy as np
a=np.asarray(native.getchannel("A"))
borders=[int((a[:2]>0).sum()),int((a[-2:]>0).sum()),int((a[:,:2]>0).sum()),int((a[:,-2:]>0).sum())]
qa={
 "task_id":"OUTRUN-C-ROI-SOURCE-Q097-NORMAL-20261015-2333",
 "schema":"outrun-hd-text-roi-v1",
 "status":"TEST_ONLY_REFERENCE_ONLY",
 "source_original_kind":"DIRECT_GITHUB_HD_DDS_NOT_986_TILES",
 "source_github_branch":"korean-localization-recovery-20260928",
 "source_dds_path":m["source_dds_path"],
 "source_dds_sha256":h(d),
 "source_dds_git_blob":"d488d1a0ccd71b0f38410ece0b90e530e2c8ff71",
 "source_full_png_sha256":h(s),
 "direct_dds_flipy_pixel_exact_full_png":True,
 "source_dimensions":[2048,2048],
 "english":"NORMAL","korean":"일반",
 "translation_provenance":"previously user-prescribed NORMAL→일반; standalone official-mapping CSV not located on inspected branch",
 "bbox_xyxy":bbox,
 "native_dimensions":list(native.size),
 "upscale":4,
 "upscaled_dimensions":list(upscaled.size),
 "native_sha256":h(out/"english_text_roi_native.png"),
 "upscaled_sha256":h(out/"imagegen_input_upscaled.png"),
 "exact_native_crop":True,
 "exact_upscale_lanczos":True,
 "reference_crop_alpha_edge_counts_top_bottom_left_right":borders,
 "alpha_crop_margin_checked":False,
 "visual_phrase_complete":"MANUAL_REVIEW: NORMAL full text and outline visible, no text/effects crop-edge cut in preview",
 "opaque_or_plate_coverage":"Green UI plate embedded; alpha is NOT independently identified glyph layer",
 "hold":["HOLD_GLYPH_MASK_OR_PSD_TEXT_LAYER_UNREVIEWED","HOLD_CLEAN_PLATE_UNREVIEWED","HOLD_UI_CELL_UV_SAFE_BOUNDS_UNMEASURED","HOLD_OFFICIAL_MAPPING_CSV_RECHECK"],
 "imagegen_called":False,"production_queue_modified":False,
 "ab_state_modified":False,"ready_to_dispatch":False,
 "C1":"NOT_RUN","C3":"NOT_RUN","USER_GAME":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
 "resize_return_policy":"Preserve Korean result aspect ratio inside verified UI-cell/UV safe area; never reject by width alone; no unreviewed mask compositing"
}
(w/"SOURCE_ROI_QA_TEST_ONLY.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(qa,ensure_ascii=False))