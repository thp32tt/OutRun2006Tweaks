#!/usr/bin/env python3
import json,hashlib,struct,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,ImageDraw
root=Path.cwd()
r= root/"localization/graphics/role_A/20261011-A243-Q193-15CONT-SOURCE-CLEAN-PILOT"
out=root/"localization/graphics/role_C/20261011-C2-Q193-A243-FIRST-PIXEL-INDEPENDENT"
out.mkdir(parents=True,exist_ok=True)
files={
"source":r/"A243_PINNED_CANONICAL_SOURCE.dds",
"official":root/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds",
"trial":r/"A243_Q193_15CONT_TRUE_CLEAN_NATIVE_TRIAL_UNPROMOTED.dds",
"plate":r/"A243_PLATE_ONLY_READABLE.png",
"glyph":r/"A243_LETTERING_ONLY_READABLE.png"}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta={}
for k,p in files.items():
 if not p.is_file(): raise RuntimeError(f"missing {k} {p}")
 im=Image.open(p).convert("RGBA")
 meta[k]={"path":str(p.relative_to(root)),"sha256":sha(p),"size":list(im.size),"mode":im.mode}
 if p.suffix==".dds":
  b=p.read_bytes()
  meta[k]["header"]={"fourcc":b[84:88].hex(),"mipmap_count":struct.unpack_from("<I",b,28)[0],"pixel_fourcc":b[84:88].hex(),"header_sha256":hashlib.sha256(b[:128]).hexdigest()}
# source/trial/official orientation native DDS raw; native readable as y-flip
def decoded(k):
 im=Image.open(files[k]).convert("RGBA")
 return np.asarray(ImageOps.flip(im)).copy()
s,o,t=decoded("source"),decoded("official"),decoded("trial")
h,w=t.shape[:2]
x0,y0,x1,y1=1413,221,1622,268
rect=(slice(y0,y1),slice(x0,x1))
mask=np.any(o!=t,axis=2)
alpha=(o[:,:,3]!=t[:,:,3])
allowed=np.zeros(mask.shape,dtype=bool);allowed[rect]=True
outside=int(np.count_nonzero(mask&~allowed))
aoutside=int(np.count_nonzero(alpha&~allowed))
within=int(np.count_nonzero(mask&allowed))
border=(x0,y0,x1,y1)
mraw=np.asarray(Image.open(files["trial"]).convert("RGBA"))
raw_consistent=bool(np.array_equal(mraw,np.flipud(t)))
# candidate visible alpha ROI and source exact source top/bottom anchoring
def bbox_region(a):
 ys,xs=np.nonzero(a)
 return [int(xs.min()+x0),int(ys.min()+y0),int(xs.max()+x0+1),int(ys.max()+y0+1)] if len(xs) else None
src_box=bbox_region(s[rect][:,:,3]>0); new_box=bbox_region(t[rect][:,:,3]>0)
# compare against producer plates and isolate isolated coverage
pl=np.asarray(Image.open(files["plate"]).convert("RGBA"))
gl=np.asarray(Image.open(files["glyph"]).convert("RGBA"))
meta["plate"]["dims_compare_to_native"]=list(pl.shape)
meta["glyph"]["dims_compare_to_native"]=list(gl.shape)
print(json.dumps({"files":meta,"numeric":{"size":[w,h],"roi":border,"source_alpha_bbox":src_box,"trial_alpha_bbox":new_box,"changed_rgba_inside":within,"changed_rgba_outside":outside,"changed_alpha_outside":aoutside,"raw_flip_y_exact":raw_consistent}},ensure_ascii=False)[:6000])
# native SOURCE/official/trial crop compare directly from decoded DDS, not producer collages
frames=[]
for name,arr in [("SOURCE",s),("OFFICIAL",o),("A243 TRIAL",t)]:
  crop=Image.fromarray(arr[rect],"RGBA")
  # same neutral gray matte all views
  matte=Image.new("RGBA",crop.size,(160,160,160,255)); matte.alpha_composite(crop)
  frames.append((name,matte.convert("RGB")))
cw=x1-x0; ch=y1-y0
panel=Image.new("RGB",(cw*3,ch+28),(170,170,170))
draw=ImageDraw.Draw(panel)
for i,(name,im) in enumerate(frames):
 panel.paste(im,(i*cw,28));draw.text((i*cw+4,5),name,fill=(0,0,0))
panel.save(out/"C2_SOURCE_OFFICIAL_TRIAL_NATIVE_GRAY.png")
# focus RAW/FLIPY crop independently from persisted trial
read=Image.fromarray(t[rect],"RGBA")
raw_roi=(x0,h-y1,x1,h-y0)
raw=Image.open(files["trial"]).convert("RGBA").crop(raw_roi)
read.save(out/"C2_TRIAL_READABLE_NATIVE.png")
raw.save(out/"C2_TRIAL_RAW_NATIVE.png")
metrics={"review_id":"C2-20261011-1950-Q193-A243-FIRST-INDEPENDENT","base_head_at_materialization":"413ef6968ae816f81d91d04fa4b0654d1ca4ad81","queue_index":193,"source_producer":"A243","files":meta,"pixel_metrics":{"native_size":[w,h],"roi_readable":list(border),"source_alpha_bbox_native":src_box,"trial_alpha_bbox_native":new_box,"changed_rgba_inside_source_roi":within,"changed_rgba_outside_source_roi":outside,"changed_alpha_outside_source_roi":aoutside,"persisted_dds_raw_flipY_identity":raw_consistent},"mechanical_scope":"isolated 15 Cont. cell; source/official/trial native persisted full DDS inspected; NOT an atlas-wide family/plate/C3/game PASS","independent_evidence":[str(p.relative_to(root)) for p in [out/"C2_SOURCE_OFFICIAL_TRIAL_NATIVE_GRAY.png",out/"C2_TRIAL_READABLE_NATIVE.png",out/"C2_TRIAL_RAW_NATIVE.png"]],"runtime_validation":"UNTESTED"}
(out/"C2_Q193_A243_MECHANICAL.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+"\n")
