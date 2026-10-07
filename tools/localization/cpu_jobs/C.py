#!/usr/bin/env python3
# C243 C1 q51 FF2462BB A163R fresh independent C + mandatory exact-SHA C3 evidence
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import os, json, hashlib, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
RUN="20261007-C243-C1-Q051-FF2462BB-A163R"
asset=Path("textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds")
candidate=repo/"localization/graphics/hd_candidates"/asset
source=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset

SOURCE_SHA="5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67"
PRE_A144_SHA="4fff8c59a44a1b7d03cee192124915f87eb73b3988c7673feb3228785ce67726"
CURRENT_SHA="0dccb6318fafa20725427227fddf00c451bfdab814de5dc2da497d79d13b862e"
PRE_A144_COMMIT="5bd0324d1acb9ce8f9465bb4de282a28a7334e06"
RAW_TARGET=(3002,482,3512,643)
READ_TARGET=(3002,1405,3512,1566)
READ_TOP=(3002,1405,3512,1486)
READ_BOTTOM=(3002,1486,3512,1566)
WRONG_A144_READ=(3002,482,3512,643)

def sha(b): return hashlib.sha256(b).hexdigest()
def load_dds(path_or_bytes):
    if isinstance(path_or_bytes,(bytes,bytearray)):
        p=Path("/tmp/c243_tmp.dds"); p.write_bytes(path_or_bytes); im=Image.open(p).convert("RGBA")
    else:
        im=Image.open(path_or_bytes).convert("RGBA")
    raw=im.copy(); read=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return raw,read
def dmask(a,b):
    return np.any(np.asarray(a)!=np.asarray(b),axis=2)
def bbox(mask, offset=(0,0)):
    ys,xs=np.where(mask)
    if len(xs)==0:return None
    ox,oy=offset
    return [ox+int(xs.min()),oy+int(ys.min()),ox+int(xs.max())+1,oy+int(ys.max())+1]
def alpha_bbox(im, box):
    x1,y1,x2,y2=box
    a=np.asarray(im.crop(box))[:,:,3]>0
    return bbox(a,(x1,y1)),a
def rectmask(shape,box):
    x1,y1,x2,y2=box;m=np.zeros(shape,bool);m[y1:y2,x1:x2]=True;return m
def margins(inner,outer):
    return [inner[0]-outer[0],outer[2]-inner[2],inner[1]-outer[1],outer[3]-inner[3]]
def comp(im):
    bg=Image.new("RGBA",im.size,(80,80,80,255));bg.alpha_composite(im);return bg.convert("RGB")
def label(im,title):
    o=Image.new("RGB",(im.width,im.height+26),(18,18,18));o.paste(im,(0,26))
    ImageDraw.Draw(o).text((5,5),title,fill="white",font=ImageFont.load_default());return o

cb=candidate.read_bytes(); sb=source.read_bytes()
if sha(cb)!=CURRENT_SHA: raise RuntimeError(("candidate SHA drift",sha(cb)))
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source SHA drift",sha(sb)))
prior_b=subprocess.check_output(["git","show",f"{PRE_A144_COMMIT}:localization/graphics/hd_candidates/{asset.as_posix()}"])
if sha(prior_b)!=PRE_A144_SHA: raise RuntimeError(("pre-A144 SHA drift",sha(prior_b)))
if cb[:128]!=sb[:128] or prior_b[:128]!=sb[:128]: raise RuntimeError("DDS header drift")
src_raw,src=load_dds(source); prior_raw,prior=load_dds(prior_b); cur_raw,cur=load_dds(candidate)
if src.size!=(4096,2048) or prior.size!=src.size or cur.size!=src.size: raise RuntimeError(("size",src.size,prior.size,cur.size))
W,H=src.size

# Exact RAW<->readable target mapping.
rx1,ry1,rx2,ry2=RAW_TARGET
mapped=(rx1,H-ry2,rx2,H-ry1)
if mapped!=READ_TARGET: raise RuntimeError(("RAW/FLIP-Y mapping mismatch",mapped,READ_TARGET))

shape=(H,W); target=rectmask(shape,READ_TARGET); wrong=rectmask(shape,WRONG_A144_READ)
prior_cur=dmask(prior,cur)
outside=int(np.count_nonzero(prior_cur & ~target))
wrong_diff=int(np.count_nonzero(prior_cur & wrong))
if outside!=0: raise RuntimeError(("collateral change outside true target",outside))
if wrong_diff!=0: raise RuntimeError(("wrong A144 insertion not exact-restored",wrong_diff))

# Independent source and current alpha/effect bboxes in the two exact source line cells.
line_results=[]
cur_masks=[]
for name,box in (("top",READ_TOP),("bottom",READ_BOTTOM)):
    sbb,sm=alpha_bbox(src,box); cbb,cm=alpha_bbox(cur,box)
    if sbb is None or cbb is None: raise RuntimeError(("missing alpha",name,sbb,cbb))
    sw,sh=sbb[2]-sbb[0],sbb[3]-sbb[1]; cw,ch=cbb[2]-cbb[0],cbb[3]-cbb[1]
    mg=margins(cbb,sbb)
    contain=cbb[0]>=sbb[0] and cbb[1]>=sbb[1] and cbb[2]<=sbb[2] and cbb[3]<=sbb[3]
    sizeok=cw<=sw and ch<=sh
    positive=min(mg)>0
    if not(contain and sizeok and positive):
        raise RuntimeError(("exact source bbox/size/margin FAIL",name,sbb,cbb,mg))
    # Ensure no candidate effect touches its exact source effect boundary.
    line_results.append({"line":name,"source_effect_bbox":sbb,"localized_effect_bbox":cbb,
      "source_size":[sw,sh],"localized_size":[cw,ch],"margins_lrtb":mg,
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})
    full=np.zeros(shape,bool);x1,y1,x2,y2=box;full[y1:y2,x1:x2]=cm;cur_masks.append(full)

pair_overlap=int(np.count_nonzero(cur_masks[0]&cur_masks[1]))
# 1px separation check using manual 3x3 dilation without scipy.
m=cur_masks[0]; dil=m.copy()
for dy in (-1,0,1):
    for dx in (-1,0,1):
        ys=slice(max(0,dy),min(H,H+dy)); yt=slice(max(0,-dy),min(H,H-dy))
        xs=slice(max(0,dx),min(W,W+dx)); xt=slice(max(0,-dx),min(W,W-dx))
        dil[yt,xt] |= m[ys,xs]
pair_touch=int(np.count_nonzero(dil&cur_masks[1]))
if pair_overlap or pair_touch: raise RuntimeError(("line overlap/touch",pair_overlap,pair_touch))

# Verify candidate pixels inside true target are fully contained and no alpha extends outside target relative to pre-A144.
alpha_delta=np.asarray(prior)[:,:,3]!=np.asarray(cur)[:,:,3]
alpha_outside=int(np.count_nonzero(alpha_delta&~target))
if alpha_outside: raise RuntimeError(("alpha collateral",alpha_outside))

# Visual evidence generated independently from exact bytes.
out=repo/"localization/graphics/role_C"/RUN;out.mkdir(parents=True,exist_ok=True)
pad=90
crop=(READ_TARGET[0]-pad,READ_TARGET[1]-pad,READ_TARGET[2]+pad,READ_TARGET[3]+pad)
cards=[]
for t,im in [("EN SOURCE",src),("PRE-A144",prior),("A163R CURRENT",cur)]:
    z=comp(im.crop(crop)).resize(((crop[2]-crop[0])*2,(crop[3]-crop[1])*2),Image.Resampling.NEAREST)
    cards.append(label(z,t+" READABLE HIGH-ZOOM"))
sheet=Image.new("RGB",(sum(x.width for x in cards),max(x.height for x in cards)),(12,12,12));xx=0
for z in cards:sheet.paste(z,(xx,0));xx+=z.width
sheet.save(out/"C243_TARGET_SOURCE_PRIOR_CURRENT_READABLE.jpg","JPEG",quality=96,subsampling=0)

wcrop=(WRONG_A144_READ[0]-70,WRONG_A144_READ[1]-70,WRONG_A144_READ[2]+70,WRONG_A144_READ[3]+70)
cards=[]
for t,im in [("EN SOURCE",src),("PRE-A144",prior),("A163R CURRENT",cur)]:
    z=comp(im.crop(wcrop));cards.append(label(z,t+" WRONG-INSERTION AREA"))
sheet=Image.new("RGB",(sum(x.width for x in cards),max(x.height for x in cards)),(12,12,12));xx=0
for z in cards:sheet.paste(z,(xx,0));xx+=z.width
sheet.save(out/"C243_WRONG_INSERTION_EXACT_RESTORED.jpg","JPEG",quality=95,subsampling=0)

rcrop=(RAW_TARGET[0]-90,RAW_TARGET[1]-90,RAW_TARGET[2]+90,RAW_TARGET[3]+90)
cards=[]
for t,im in [("EN SOURCE RAW",src_raw),("PRE-A144 RAW",prior_raw),("A163R CURRENT RAW",cur_raw)]:
    z=comp(im.crop(rcrop)).resize(((rcrop[2]-rcrop[0])*2,(rcrop[3]-rcrop[1])*2),Image.Resampling.NEAREST)
    cards.append(label(z,t))
sheet=Image.new("RGB",(sum(x.width for x in cards),max(x.height for x in cards)),(12,12,12));xx=0
for z in cards:sheet.paste(z,(xx,0));xx+=z.width
sheet.save(out/"C243_TARGET_SOURCE_PRIOR_CURRENT_RAW.jpg","JPEG",quality=96,subsampling=0)

blocks=[]
for pct in (100,75,50):
    z=comp(cur.crop(crop));sz=(max(1,round(z.width*pct/100)),max(1,round(z.height*pct/100)))
    blocks.append(label(z.resize(sz,Image.Resampling.LANCZOS),f"A163R CURRENT {pct}%"))
practical=Image.new("RGB",(sum(x.width for x in blocks),max(x.height for x in blocks)),(12,12,12));xx=0
for z in blocks:practical.paste(z,(xx,0));xx+=z.width
practical.save(out/"C243_PRACTICAL_100_75_50.jpg","JPEG",quality=95,subsampling=0)

report={
 "schema_version":2,"run":RUN,"role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":51,"asset":asset.as_posix(),"regression":"PJR-014-20261006","priority":"P0",
 "producer_run":"A163R","source_sha256":SOURCE_SHA,
 "source_provenance":{"repo_path":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/"+asset.as_posix()},
 "pre_a144_sha256":PRE_A144_SHA,"pre_a144_commit":PRE_A144_COMMIT,
 "candidate_sha256":CURRENT_SHA,
 "mapping":{"raw_source_bbox":list(RAW_TARGET),"readable_source_bbox":list(READ_TARGET),"raw_to_readable_math":"PASS"},
 "lines":line_results,
 "machine_qa":{
   "changed_pixels_outside_true_target_vs_pre_a144":outside,
   "alpha_changed_outside_true_target_vs_pre_a144":alpha_outside,
   "wrong_a144_insertion_pixel_diff_vs_pre_a144":wrong_diff,
   "line_overlap_pixels":pair_overlap,"line_touch_1px_pixels":pair_touch,
   "header_128_exact_source_prior_current":True,"dimensions":[W,H],"mip_count":1
 },
 "fresh_c_machine_status":"PASS_PENDING_CONTROLLER_VISUAL",
 "mandatory_c3":"REQUIRED_EXACT_SHA_PJR014_MULTI_LINE_STYLE_FALSE_NEGATIVE",
 "c3_visual_priorities":["true_source_target","duplicate_removal","source_style_effect_layers","readable_right_lean","bottom_outline_clipping","glyph_integrity","protected_art","RAW_FLIPY","practical_scale"],
 "visual_evidence":[
   f"localization/graphics/role_C/{RUN}/C243_TARGET_SOURCE_PRIOR_CURRENT_READABLE.jpg",
   f"localization/graphics/role_C/{RUN}/C243_WRONG_INSERTION_EXACT_RESTORED.jpg",
   f"localization/graphics/role_C/{RUN}/C243_TARGET_SOURCE_PRIOR_CURRENT_RAW.jpg",
   f"localization/graphics/role_C/{RUN}/C243_PRACTICAL_100_75_50.jpg"
 ],
 "controller_visual_qa":"PENDING","c3_strict_decision":"PENDING_CONTROLLER",
 "pre_ingame_export":"BLOCKED_UNTIL_CONTROLLER_C3",
 "user_jpg_review":"PENDING","actual_ingame_validation":"PENDING",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"C243_FF2462BB_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
(wr/"C243_FF2462BB.json").write_text(json.dumps({
 "run":RUN,"role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":51,"candidate_sha256":CURRENT_SHA,"machine_status":"PASS_PENDING_CONTROLLER_VISUAL",
 "report":f"localization/graphics/role_C/{RUN}/C243_FF2462BB_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"queue_index":51,"candidate_sha256":CURRENT_SHA,"lines":line_results,
 "machine":report["machine_qa"],"status":"PASS_PENDING_CONTROLLER_VISUAL"},ensure_ascii=False,indent=2))
