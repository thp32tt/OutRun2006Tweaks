#!/usr/bin/env python3
# C243R C1 q51 FF2462BB: small corrective rework after independent exact-bbox FAIL.
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import os, json, hashlib, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted role C required")

repo=Path.cwd()
RUN="20261007-C243R-C1-Q051-FF2462BB-CORRECTIVE"
asset=Path("textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds")
candidate=repo/"localization/graphics/hd_candidates"/asset
source=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset
SOURCE_SHA="5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67"
A163R_SHA="0dccb6318fafa20725427227fddf00c451bfdab814de5dc2da497d79d13b862e"
PRE_A144_SHA="4fff8c59a44a1b7d03cee192124915f87eb73b3988c7673feb3228785ce67726"
PRE_A144_COMMIT="5bd0324d1acb9ce8f9465bb4de282a28a7334e06"
READ_TARGET=(3002,1405,3512,1566)
READ_TOP=(3002,1405,3512,1486)
READ_BOTTOM=(3002,1486,3512,1566)
WRONG_A144_READ=(3002,482,3512,643)
SHIFT_X=-4

def sha(b): return hashlib.sha256(b).hexdigest()
def load_bytes(b):
    p=Path("/tmp/c243r.dds");p.write_bytes(b)
    raw=Image.open(p).convert("RGBA");return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def load_path(p):
    raw=Image.open(p).convert("RGBA");return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def dm(a,b): return np.any(np.asarray(a)!=np.asarray(b),axis=2)
def bbox(mask,off=(0,0)):
    ys,xs=np.where(mask)
    if len(xs)==0:return None
    ox,oy=off;return [ox+int(xs.min()),oy+int(ys.min()),ox+int(xs.max())+1,oy+int(ys.max())+1]
def abox(im,box):
    x1,y1,x2,y2=box
    return bbox(np.asarray(im.crop(box))[:,:,3]>0,(x1,y1))
def rect(shape,box):
    x1,y1,x2,y2=box;m=np.zeros(shape,bool);m[y1:y2,x1:x2]=True;return m
def margins(i,o): return [i[0]-o[0],o[2]-i[2],i[1]-o[1],o[3]-i[3]]
def comp(im):
    z=Image.new("RGBA",im.size,(80,80,80,255));z.alpha_composite(im);return z.convert("RGB")
def lab(im,t):
    o=Image.new("RGB",(im.width,im.height+28),(18,18,18));o.paste(im,(0,28))
    ImageDraw.Draw(o).text((5,6),t,fill="white",font=ImageFont.load_default());return o

cb=candidate.read_bytes(); sb=source.read_bytes()
if sha(cb)!=A163R_SHA: raise RuntimeError(("candidate drift",sha(cb)))
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
prior_b=subprocess.check_output(["git","show",f"{PRE_A144_COMMIT}:localization/graphics/hd_candidates/{asset.as_posix()}"])
if sha(prior_b)!=PRE_A144_SHA: raise RuntimeError(("pre-A144 drift",sha(prior_b)))
if cb[:128]!=sb[:128] or prior_b[:128]!=sb[:128]: raise RuntimeError("header mismatch")
src_raw,src=load_path(source); before_raw,before=load_path(candidate); prior_raw,prior=load_bytes(prior_b)
if src.size!=(4096,2048) or before.size!=src.size or prior.size!=src.size: raise RuntimeError("size mismatch")
W,H=src.size

# Reproduce the independent C failure exactly before correction.
source_top=abox(src,READ_TOP); source_bottom=abox(src,READ_BOTTOM)
before_top=abox(before,READ_TOP); before_bottom=abox(before,READ_BOTTOM)
pre_fail={
 "top_source_bbox":source_top,"top_candidate_bbox":before_top,"top_margins":margins(before_top,source_top),
 "bottom_source_bbox":source_bottom,"bottom_candidate_bbox":before_bottom,"bottom_margins":margins(before_bottom,source_bottom)
}
if before_bottom[2]-source_bottom[2] != 3:
    raise RuntimeError(("expected 3px right overflow not reproduced",pre_fail))

# Small C corrective rework: move only bottom localized line 4px left.
final=before.copy()
x1,y1,x2,y2=READ_BOTTOM
bottom=before.crop(READ_BOTTOM)
final.paste(Image.new("RGBA",(x2-x1,y2-y1),(0,0,0,0)),(x1,y1))
final.alpha_composite(bottom,(x1+SHIFT_X,y1))

# Persist exact RGBA32 raw orientation while preserving original header.
raw_before=before_raw
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
mode=None
for m in ("RGBA","BGRA"):
    try:
        if raw_before.tobytes("raw",m)==cb[128:]: mode=m; break
    except Exception: pass
if mode is None: raise RuntimeError("raw channel mode unresolved")
newb=cb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(newb)
newsha=sha(newb)
dec_raw,dec=load_path(candidate)
if np.any(np.asarray(dec)!=np.asarray(final)): raise RuntimeError("persisted decode mismatch")

# Exact-source bbox / size / margin after correction.
lines=[]
for name,box in (("top",READ_TOP),("bottom",READ_BOTTOM)):
    sbb=abox(src,box); cbb=abox(dec,box)
    sw,sh=sbb[2]-sbb[0],sbb[3]-sbb[1]; cw,ch=cbb[2]-cbb[0],cbb[3]-cbb[1]
    mg=margins(cbb,sbb)
    ok=cbb[0]>=sbb[0] and cbb[1]>=sbb[1] and cbb[2]<=sbb[2] and cbb[3]<=sbb[3] and cw<=sw and ch<=sh and min(mg)>0
    if not ok: raise RuntimeError(("post-correction bbox fail",name,sbb,cbb,mg))
    lines.append({"line":name,"source_effect_bbox":sbb,"localized_effect_bbox":cbb,
      "source_size":[sw,sh],"localized_size":[cw,ch],"margins_lrtb":mg,
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

shape=(H,W); target=rect(shape,READ_TARGET); bottom_region=rect(shape,READ_BOTTOM); wrong=rect(shape,WRONG_A144_READ)
prior_final=dm(prior,dec); before_final=dm(before,dec)
outside_target=int(np.count_nonzero(prior_final&~target))
correction_outside_bottom=int(np.count_nonzero(before_final&~bottom_region))
wrong_diff=int(np.count_nonzero(prior_final&wrong))
alpha_out=int(np.count_nonzero((np.asarray(prior)[:,:,3]!=np.asarray(dec)[:,:,3])&~target))
if any((outside_target,correction_outside_bottom,wrong_diff,alpha_out)):
    raise RuntimeError(("blast radius",outside_target,correction_outside_bottom,wrong_diff,alpha_out))

# Top line must remain pixel-exact to A163R.
top_region=rect(shape,READ_TOP)
top_diff=int(np.count_nonzero(before_final&top_region))
if top_diff: raise RuntimeError(("top line changed",top_diff))

# 1px line separation.
topmask=np.zeros(shape,bool); botmask=np.zeros(shape,bool)
for mask,box in ((topmask,READ_TOP),(botmask,READ_BOTTOM)):
    x1,y1,x2,y2=box;mask[y1:y2,x1:x2]=np.asarray(dec.crop(box))[:,:,3]>0
dil=topmask.copy()
for dy in (-1,0,1):
    for dx in (-1,0,1):
        ys=slice(max(0,dy),min(H,H+dy));yt=slice(max(0,-dy),min(H,H-dy))
        xs=slice(max(0,dx),min(W,W+dx));xt=slice(max(0,-dx),min(W,W-dx))
        dil[yt,xt] |= topmask[ys,xs]
overlap=int(np.count_nonzero(topmask&botmask));touch=int(np.count_nonzero(dil&botmask))
if overlap or touch: raise RuntimeError(("line overlap/touch",overlap,touch))

out=repo/"localization/graphics/role_C"/RUN;out.mkdir(parents=True,exist_ok=True)
pad=90;crop=(READ_TARGET[0]-pad,READ_TARGET[1]-pad,READ_TARGET[2]+pad,READ_TARGET[3]+pad)
cards=[]
for t,im in [("EN SOURCE",src),("A163R BEFORE C",before),("C243R CORRECTED",dec)]:
    z=comp(im.crop(crop)).resize(((crop[2]-crop[0])*2,(crop[3]-crop[1])*2),Image.Resampling.NEAREST)
    cards.append(lab(z,t+" READABLE HIGH-ZOOM"))
sheet=Image.new("RGB",(sum(z.width for z in cards),max(z.height for z in cards)),(12,12,12));xx=0
for z in cards:sheet.paste(z,(xx,0));xx+=z.width
sheet.save(out/"C243R_TARGET_SOURCE_BEFORE_AFTER_READABLE.jpg","JPEG",quality=96,subsampling=0)

raw_target=(3002,482,3512,643);rcrop=(raw_target[0]-90,raw_target[1]-90,raw_target[2]+90,raw_target[3]+90)
cards=[]
for t,im in [("EN SOURCE RAW",src_raw),("A163R BEFORE RAW",before_raw),("C243R AFTER RAW",dec_raw)]:
    z=comp(im.crop(rcrop)).resize(((rcrop[2]-rcrop[0])*2,(rcrop[3]-rcrop[1])*2),Image.Resampling.NEAREST)
    cards.append(lab(z,t))
sheet=Image.new("RGB",(sum(z.width for z in cards),max(z.height for z in cards)),(12,12,12));xx=0
for z in cards:sheet.paste(z,(xx,0));xx+=z.width
sheet.save(out/"C243R_TARGET_SOURCE_BEFORE_AFTER_RAW.jpg","JPEG",quality=96,subsampling=0)

wcrop=(WRONG_A144_READ[0]-70,WRONG_A144_READ[1]-70,WRONG_A144_READ[2]+70,WRONG_A144_READ[3]+70)
cards=[]
for t,im in [("EN SOURCE",src),("PRE-A144",prior),("C243R AFTER",dec)]:
    cards.append(lab(comp(im.crop(wcrop)),t+" WRONG-INSERTION AREA"))
sheet=Image.new("RGB",(sum(z.width for z in cards),max(z.height for z in cards)),(12,12,12));xx=0
for z in cards:sheet.paste(z,(xx,0));xx+=z.width
sheet.save(out/"C243R_WRONG_INSERTION_RESTORED.jpg","JPEG",quality=95,subsampling=0)

blocks=[]
for pct in (100,75,50):
    z=comp(dec.crop(crop));sz=(round(z.width*pct/100),round(z.height*pct/100))
    blocks.append(lab(z.resize(sz,Image.Resampling.LANCZOS),f"C243R {pct}%"))
sheet=Image.new("RGB",(sum(z.width for z in blocks),max(z.height for z in blocks)),(12,12,12));xx=0
for z in blocks:sheet.paste(z,(xx,0));xx+=z.width
sheet.save(out/"C243R_PRACTICAL_100_75_50.jpg","JPEG",quality=95,subsampling=0)

report={
 "schema_version":2,"run":RUN,"role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":51,"asset":asset.as_posix(),"regression":"PJR-014-20261006","priority":"P0",
 "producer_run":"A163R","source_sha256":SOURCE_SHA,"input_candidate_sha256":A163R_SHA,
 "candidate_sha256":newsha,
 "initial_independent_c_failure":{"workflow_run":37589027590,"reason":"BOTTOM_EXACT_SOURCE_BBOX_RIGHT_OVERFLOW_3PX","evidence":pre_fail},
 "small_corrective_rework":{"allowed_by_contract":True,"operation":"bottom localized line x shift","shift_xy":[SHIFT_X,0],"top_line_pixel_exact_to_input":True},
 "lines":lines,
 "machine_qa":{
   "changed_pixels_outside_true_target_vs_pre_a144":outside_target,
   "corrective_changed_pixels_outside_bottom_line_region":correction_outside_bottom,
   "wrong_a144_insertion_pixel_diff_vs_pre_a144":wrong_diff,
   "alpha_changed_outside_true_target_vs_pre_a144":alpha_out,
   "top_line_pixel_diff_vs_a163r":top_diff,
   "line_overlap_pixels":overlap,"line_touch_1px_pixels":touch,
   "header_128_exact":newb[:128]==cb[:128],"dimensions":[W,H],"mip_count":1,"raw_mode":mode,
   "persisted_decode_exact":True
 },
 "fresh_c_machine_status":"PASS_AFTER_SMALL_CORRECTIVE_REWORK_PENDING_CONTROLLER_VISUAL",
 "mandatory_c3":"REQUIRED_EXACT_SHA_PJR014_MULTI_LINE_STYLE_FALSE_NEGATIVE",
 "controller_visual_qa":"PENDING","c3_strict_decision":"PENDING_CONTROLLER",
 "pre_ingame_export":"BLOCKED_UNTIL_CONTROLLER_C3","user_jpg_review":"PENDING","actual_ingame_validation":"PENDING",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[],
 "visual_evidence":[
   f"localization/graphics/role_C/{RUN}/C243R_TARGET_SOURCE_BEFORE_AFTER_READABLE.jpg",
   f"localization/graphics/role_C/{RUN}/C243R_TARGET_SOURCE_BEFORE_AFTER_RAW.jpg",
   f"localization/graphics/role_C/{RUN}/C243R_WRONG_INSERTION_RESTORED.jpg",
   f"localization/graphics/role_C/{RUN}/C243R_PRACTICAL_100_75_50.jpg"
 ]
}
(out/"C243R_FF2462BB_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
(wr/"C243R_FF2462BB.json").write_text(json.dumps({
 "run":RUN,"role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":51,"input_candidate_sha256":A163R_SHA,"candidate_sha256":newsha,
 "machine_status":"PASS_AFTER_SMALL_CORRECTIVE_REWORK_PENDING_CONTROLLER_VISUAL",
 "report":f"localization/graphics/role_C/{RUN}/C243R_FF2462BB_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"input_sha":A163R_SHA,"candidate_sha":newsha,"initial_fail":pre_fail,
 "post_lines":lines,"machine":report["machine_qa"]},ensure_ascii=False,indent=2))
