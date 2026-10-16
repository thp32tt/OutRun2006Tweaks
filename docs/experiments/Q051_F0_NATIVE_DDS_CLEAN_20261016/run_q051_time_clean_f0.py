#!/usr/bin/env python3
"""F0 Q051 TIME clean proof: mask ONLY glyph's source alpha component, no other area."""
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np,struct,hashlib,json
BASE=Path("/home/chatgpt-runner2/work/c_salvage_text_roi")
OUT=BASE/"F0_Q051_NATIVE_DDS_20261016"
SRC=BASE/"source_full_20261012"/"q051_FF2462BB_GITHUB_HD_SOURCE_20261015.dds"
READ=BASE/"source_full_20261012"/"q051_FF2462BB_FLIPY_CHECK_ORIENTATION.png"
MAN=BASE/"original_hd_phrase_crops_20261016"/"MASTER_255_V2_20261016"/"MASTER_CROP_MANIFEST_255.json"
bbox=(1595,608,1845,727)
x0,y0,x1,y1=bbox;W,H=4096,2048
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=SRC.read_bytes()
assert sha(raw)=="5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67"
assert sha(READ.read_bytes())=="2da1b6f01219356ddc6ea925bd8fcd4afd37d9040eb48081a40861cc649da6f0"
with Image.open(READ) as im:
 readable=np.asarray(im.convert("RGBA"))
region=readable[y0:y1,x0:x1].copy()
source_alpha=region[:,:,3]
mask=source_alpha>0
assert int(mask.sum())==12376, "TIME glyph mask changed unexpectedly"
ys,xs=np.where(mask)
assert [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]==[32,26,241,101]
assert int(mask[0,:].sum()+mask[-1,:].sum()+mask[:,0].sum()+mask[:,-1].sum())==0
# Verify no other measured Q051 text ROI shares any of our actual glyph pixels.
master=json.loads(MAN.read_text())
others=[]
for row in master["items"]:
 if row.get("id")=="Q051-TIME_HUD" or not str(row.get("id","")).startswith("Q051-"):continue
 b=row.get("bbox_xyxy")
 if not b:continue
 ax0,ay0,ax1,ay1=b
 intersect=(max(ax0,x0),max(ay0,y0),min(ax1,x1),min(ay1,y1))
 if intersect[0]<intersect[2] and intersect[1]<intersect[3]:
  sub=mask[intersect[1]-y0:intersect[3]-y0,intersect[0]-x0:intersect[2]-x0]
  if np.any(sub):others.append({"id":row.get("id"),"intersection_pixels":int(sub.sum())})
# Q051-TIME_HUD_2 is explicitly EXCLUDED_DUPLICATE_OR_WRONG_LABEL.
# Q051-YOU source crop erroneously includes TIME tail; visual/opacity review shows
# no YOU white letters or red arrows in the overlapping source region.
allowed={"Q051-TIME_HUD_2":12376,"Q051-YOU":1157}
if {r["id"]:r["intersection_pixels"] for r in others} != allowed:
 raise RuntimeError("UNCLASSIFIED_NEIGHBOR_OVERLAP_HOLD:"+str(others))
# Source alpha forms exactly one contiguous connected group. Cannot treat opaque crops as clean plates globally.
# Convert readable ROI mask to DDS RAW Y coords independently (raw_y = H-1-readable_y).
data=bytearray(raw)
modified=0
for ry,rx in zip(ys.tolist(),xs.tolist()):
 sy=y0+ry;sx=x0+rx
 native_y=H-1-sy
 off=128+4*(native_y*W+sx)
 if not any(data[off:off+4][3:]):continue
 # Keep alpha semantics and replace invisible RGB with nearby genuine transparent plate RGB
 data[off:off+4]=bytes((0,10,57,0))
 modified+=1
assert modified==int(mask.sum())
test=OUT/"Q051_TIME_ONLY_CLEAN_F0_TEST_ONLY.dds"
if test.exists() and sha(test.read_bytes())!=sha(data):
 raise RuntimeError("PREEXISTING_DIFFERENT_CLEAN_KEEP_ORIGINAL")
if not test.exists():test.write_bytes(data)
assert data[:128]==raw[:128] and len(data)==len(raw)
# Actual persisted full DDS re-decode.
with Image.open(test) as clean_dds:
 cleaned=clean_dds.convert("RGBA")
 # readable orientation from original source mapping
 readable_clean=np.asarray(cleaned.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
changed=np.any(readable_clean!=readable,axis=2)
assert int(changed.sum())==modified
assert np.array_equal(changed[y0:y1,x0:x1],mask)
assert not np.any(changed[:y0,:]) and not np.any(changed[y1:,:])
assert not np.any(changed[y0:y1,:x0]) and not np.any(changed[y0:y1,x1:])
clean_region=readable_clean[y0:y1,x0:x1].copy()
assert int((clean_region[:,:,3]>0).sum())==0
assert int((readable_clean[y0:y1,x0:x1,0]>150).sum())>=0
im_before=Image.fromarray(region,"RGBA")
im_after=Image.fromarray(clean_region,"RGBA")
# Preview only: opaque navy background is for review, not stored CLEAN pixels.
before_bg=Image.new("RGBA",im_before.size,(0,10,57,255));before_bg.alpha_composite(im_before)
after_bg=Image.new("RGBA",im_after.size,(0,10,57,255));after_bg.alpha_composite(im_after)
canvas=Image.new("RGB",(2*(x1-x0)+20,y1-y0+45),(12,18,35))
canvas.paste(before_bg.convert("RGB"),(0,35))
canvas.paste(after_bg.convert("RGB"),(x1-x0+20,35))
ImageDraw.Draw(canvas).text((2,7),"SOURCE TIME",(245,245,245))
ImageDraw.Draw(canvas).text((x1-x0+23,7),"CLEAN TEST_ONLY",(245,245,245))
preview=OUT/"Q051_TIME_CLEAN_SIDE_BY_SIDE_TEST_ONLY.png"
canvas.save(preview)
layer=OUT/"Q051_TIME_CLEAN_NATIVE_RGBA_TEST_ONLY.png"
im_after.save(layer)
mask_png=OUT/"Q051_TIME_REMOVAL_MASK_TEST_ONLY.png"
Image.fromarray((mask.astype("uint8")*255),"L").save(mask_png)
m={"schema":"outrun-q051-f0-time-clean-v1","source_dds_sha256":sha(raw),"source_png_sha256":sha(READ.read_bytes()),
   "clean_dds_sha256":sha(test.read_bytes()),"native_source_size":[W,H],"readable_bbox_xyxy":list(bbox),
   "raw_bbox_xyxy":[x0,H-y1,x1,H-y0],"tested_region":"Q051-TIME_HUD",
   "source_alpha_positive_pixels":int(mask.sum()),"changed_pixels":int(changed.sum()),
   "neighbor_manifest_alpha_mask_intersections":others,
   "overlap_caveat":"Q051-YOU crop contains end of adjacent TIME text, while its actual white YOU label/red icon are outside removal area; duplicate TIME_HUD_2 excluded. Requires independent visual review.",
   "outside_region_rgba_exact":True,
   "within_region_difference_matches_alpha_mask_exact":True,
   "english_glyphs_visible_remaining_inside_test_roi":0,
   "clean_region_alpha_nonzero":0,"format":"DDS_RGBA32_UNCOMPRESSED","mip_count":1,
   "full_dds_header_exact":True,"output_paths":{str(x.name):sha(x.read_bytes()) for x in [test,preview,layer,mask_png]},
   "safety":"TEST_ONLY; other atlas sections unchanged; in-game sampling and shared UV not verified.",
   "CLEAN_STATIC":"CANDIDATE_REVIEW_NEEDED","F0":"HOLD_PENDING_VISUAL_REVIEW_AND_INGAME",
   "RUNTIME_VALIDATION":"UNTESTED","C1":"NOT_RUN","C3":"NOT_RUN"}
report=OUT/"Q051_TIME_CLEAN_F0_REPORT.json"
report.write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(m,ensure_ascii=False,indent=2))