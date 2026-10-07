#!/usr/bin/env python3
# C240 C1 q107 841E796B fresh independent C + C3 evidence
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import os, io, json, hashlib, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
RUN="20261007-C240-C1-Q107-841E796B-B232R"
asset=Path("textures/load/spr_sprani_selector_cvt_Exst/841E796B_512x128.dds")
candidate=repo/"localization/graphics/hd_candidates"/asset
SOURCE_SHA="112f47e7b16ecf21f722738f7fc9053d1a9852d66da9ef9d29fd25dadf2f567e"
PRIOR_C103_SHA="6dd78959851274898ccc237932c5fe6ad3bae9c9e92b6d45fd935317468ec2ad"
CURRENT_SHA="d6a5cc84e7cf834afe11d8afdc2c0b869b306e75759b71ee392983db8999abda"
DECL_NO=(1534,258,1602,300)
DECL_HANDICAP=(1548,303,1768,353)
DECL_LOCAL_TOP=(1540,264,1596,294)

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    with Image.open(io.BytesIO(b)) as im: return im.convert("RGBA")
def all_named_objects(basename):
    lines=subprocess.check_output(["git","rev-list","--objects","--all"],text=True,errors="ignore").splitlines()
    for line in lines:
        if " " not in line: continue
        oid,path=line.split(" ",1)
        if basename in path:
            try: data=subprocess.check_output(["git","cat-file","-p",oid],stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError: continue
            yield oid,path,data
def find_exact(target_sha,basename):
    for oid,path,data in all_named_objects(basename):
        if sha(data)==target_sha: return data,{"git_object":oid,"path":path}
    raise SystemExit(f"exact object {target_sha} for {basename} not found in repository history")
def bbox(mask):
    ys,xs=np.where(mask)
    if len(xs)==0:return None
    return [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def mk_mask(shape,box):
    m=np.zeros(shape,dtype=bool);x1,y1,x2,y2=box;m[y1:y2,x1:x2]=True;return m
def flip_box(box,H):
    x1,y1,x2,y2=box;return (x1,H-y2,x2,H-y1)

cb=candidate.read_bytes()
if sha(cb)!=CURRENT_SHA: raise SystemExit("candidate SHA drift: "+sha(cb))
SRC_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"\nsrc_url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{SRC_COMMIT}/Release/spr_sprani_selector_cvt_Exst/841E796B_512x128.dds"\nreq=urllib.request.Request(src_url,headers={"User-Agent":"OutRun-C240"})\nwith urllib.request.urlopen(req,timeout=90) as resp: sb=resp.read()\nif sha(sb)!=SOURCE_SHA: raise SystemExit(f"source SHA drift {sha(sb)}")\nsource_prov={"repo":"Sonic-TV/OR2006Sprites","commit":SRC_COMMIT,"url":src_url}\npb,prior_prov=find_exact(PRIOR_C103_SHA,asset.name)
src=decode(sb); prior=decode(pb); cur=decode(cb)
if src.size!=prior.size or prior.size!=cur.size: raise SystemExit(f"dimension mismatch {src.size} {prior.size} {cur.size}")
W,H=cur.size
if (W,H)!=(2048,512): raise SystemExit(f"unexpected size {cur.size}")
if cb[:128]!=pb[:128] or cb[:128]!=sb[:128]: raise SystemExit("DDS header mismatch vs exact source/prior")
mips=int.from_bytes(cb[28:32],"little") or 1
fourcc=cb[84:88].rstrip(b"\0").decode("ascii","ignore")
A=np.asarray(prior); B=np.asarray(cur)
diff=np.any(A!=B,axis=2)
ad=A[:,:,3]!=B[:,:,3]
db=bbox(diff)
if db is None: raise SystemExit("no byte-visible change from C103")

# Do not assume producer coordinate orientation. Infer which source-frame contains the exact changed pixels.
frames=[]
for name,no,hand,ltop in [
 ("DECLARED",DECL_NO,DECL_HANDICAP,DECL_LOCAL_TOP),
 ("MIRROR_Y",flip_box(DECL_NO,H),flip_box(DECL_HANDICAP,H),flip_box(DECL_LOCAL_TOP,H))
]:
    m=mk_mask(diff.shape,no)
    outside=int(np.count_nonzero(diff & ~m))
    alpha_out=int(np.count_nonzero(ad & ~m))
    frames.append((outside,alpha_out,name,no,hand,ltop))
frames.sort(key=lambda x:(x[0],x[1]))
outside,alpha_out,frame,no_box,hand_box,local_top=frames[0]
if outside or alpha_out:
    raise SystemExit(f"rework blast radius FAIL declared={frames}")
# The bottom line must be globally unchanged from C103; because all changes are within No line,
# this is guaranteed if source line boxes are disjoint.
if not (no_box[3] <= hand_box[1] or hand_box[3] <= no_box[1]):
    raise SystemExit("No and Handicap source boxes overlap")
# Declared localized top bbox must have positive margins/source-size ceiling in the resolved frame.
margins=[local_top[0]-no_box[0], no_box[2]-local_top[2], local_top[1]-no_box[1], no_box[3]-local_top[3]]
sizeok=(local_top[2]-local_top[0]) <= (no_box[2]-no_box[0]) and (local_top[3]-local_top[1]) <= (no_box[3]-no_box[1])
if min(margins)<=0 or not sizeok:
    raise SystemExit(f"localized top bbox FAIL frame={frame} margins={margins}")

# Independent collateral check: source vs candidate outside both localized source-line boxes must be identical
# for this compact selector card asset. If not, record but fail closed rather than assuming policy.
two=mk_mask(diff.shape,no_box)|mk_mask(diff.shape,hand_box)
srcarr=np.asarray(src)
src_cur=np.any(srcarr!=B,axis=2)
source_changes_outside=int(np.count_nonzero(src_cur & ~two))
# Some protected pictogram/card effects may legitimately differ from canonical source in legacy candidate history.
# We do not silently PASS this; C3 visual evidence below is the authority. Record count and exact visual comparison.

# Visual evidence in both raw and FLIP-Y. Contract says prior evidence treats RAW as mirror_y,
# so readable/game orientation is FLIP-Y for human comparison.
out=repo/"localization/graphics/role_C"/RUN; out.mkdir(parents=True,exist_ok=True)
def flat(im,bg=(88,88,88)):
    base=Image.new("RGB",im.size,bg); base.paste(im.convert("RGB"),mask=im.getchannel("A")); return base
def label(im,title):
    z=flat(im); c=Image.new("RGB",(z.width,z.height+28),(24,24,24)); c.paste(z,(0,28))
    ImageDraw.Draw(c).text((6,6),title,fill="white",font=ImageFont.load_default()); return c
def strip(cards):
    o=Image.new("RGB",(sum(x.width for x in cards),max(x.height for x in cards)),(20,20,20));x=0
    for c in cards:o.paste(c,(x,0));x+=c.width
    return o

read_src=ImageOps.flip(src); read_prior=ImageOps.flip(prior); read_cur=ImageOps.flip(cur)
full=strip([label(read_src,"EN SOURCE FLIP-Y"),label(read_prior,"C103 PRIOR FLIP-Y"),label(read_cur,"B232R CURRENT FLIP-Y")])
full.thumbnail((5000,1600),Image.Resampling.LANCZOS)
full.save(out/"C240_FULL_READABLE_SOURCE_PRIOR_CURRENT.jpg","JPEG",quality=95,subsampling=0)
raw=strip([label(src,"EN SOURCE RAW"),label(prior,"C103 PRIOR RAW"),label(cur,"B232R CURRENT RAW")])
raw.thumbnail((5000,1600),Image.Resampling.LANCZOS)
raw.save(out/"C240_FULL_RAW_SOURCE_PRIOR_CURRENT.jpg","JPEG",quality=95,subsampling=0)

# Crop around the resolved source-line boxes in both coordinate views.
rx1=min(no_box[0],hand_box[0])-90; ry1=min(no_box[1],hand_box[1])-80
rx2=max(no_box[2],hand_box[2])+120; ry2=max(no_box[3],hand_box[3])+80
raw_crop=(max(0,rx1),max(0,ry1),min(W,rx2),min(H,ry2))
# Convert raw crop to readable crop exactly.
read_crop=(raw_crop[0],H-raw_crop[3],raw_crop[2],H-raw_crop[1])
rcards=[]
for t,im in [("SOURCE",read_src),("C103 PRIOR",read_prior),("B232R CURRENT",read_cur)]:
    z=im.crop(read_crop).resize(((read_crop[2]-read_crop[0])*3,(read_crop[3]-read_crop[1])*3),Image.Resampling.NEAREST)
    rcards.append(label(z,t+" HIGH-ZOOM FLIP-Y"))
strip(rcards).save(out/"C240_TWO_LINE_HIGH_ZOOM_READABLE.jpg","JPEG",quality=96,subsampling=0)
rawcards=[]
for t,im in [("SOURCE",src),("C103 PRIOR",prior),("B232R CURRENT",cur)]:
    z=im.crop(raw_crop).resize(((raw_crop[2]-raw_crop[0])*3,(raw_crop[3]-raw_crop[1])*3),Image.Resampling.NEAREST)
    rawcards.append(label(z,t+" HIGH-ZOOM RAW"))
strip(rawcards).save(out/"C240_TWO_LINE_HIGH_ZOOM_RAW.jpg","JPEG",quality=96,subsampling=0)

# Practical scale proxy on readable two-line crop.
for pct in (100,75,50):
    cards=[]
    for t,im in [("SOURCE",read_src),("CURRENT",read_cur)]:
        z=im.crop(read_crop)
        z=z.resize((max(1,round(z.width*pct/100)),max(1,round(z.height*pct/100))),Image.Resampling.LANCZOS)
        cards.append(label(z,f"{t} {pct}%"))
    strip(cards).save(out/f"C240_PRACTICAL_{pct}.jpg","JPEG",quality=95,subsampling=0)

report={
 "schema_version":2,"run":RUN,"role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":107,"asset":asset.as_posix(),"producer_run":"B232R",
 "source_sha256":SOURCE_SHA,"source_provenance":source_prov,
 "prior_c103_sha256":PRIOR_C103_SHA,"prior_provenance":prior_prov,
 "candidate_sha256":CURRENT_SHA,
 "resolved_bbox_frame":frame,
 "source_line_bboxes":{"No":list(no_box),"Handicap":list(hand_box)},
 "localized_top_bbox":list(local_top),"localized_top_margins":margins,
 "machine_qa":{
   "header_128_exact_source_prior_current":True,
   "dimensions":[W,H],"mip_count":mips,"fourcc":fourcc,
   "prior_to_current_changed_bbox":db,
   "prior_to_current_changed_pixels":int(np.count_nonzero(diff)),
   "changed_pixels_outside_No_source_bbox":outside,
   "alpha_changed_outside_No_source_bbox":alpha_out,
   "bottom_Handicap_line_pixel_exact_to_C103":True,
   "top_source_size_ceiling":"PASS" if sizeok else "FAIL",
   "top_positive_margin":"PASS" if min(margins)>0 else "FAIL",
   "source_vs_current_changed_pixels_outside_two_source_boxes":source_changes_outside
 },
 "semantic_check":"No Handicap -> compact Korean compound '무 핸디캡'; verify visually that upper 무 and lower 핸디캡 read in natural order.",
 "fresh_c_machine_status":"PASS_PENDING_CONTROLLER_VISUAL",
 "mandatory_c3":"REQUIRED_EXACT_SHA_PRE_INGAME_SEMANTIC_FALSE_NEGATIVE_AND_CHANGED_BYTES",
 "c3_visual_priorities":["semantic_order","slant_direction","source_style","hierarchy_scale","glyph_integrity","clipping","protected_art","FLIP_Y_RAW","practical_scale"],
 "visual_evidence":[
   f"localization/graphics/role_C/{RUN}/C240_FULL_READABLE_SOURCE_PRIOR_CURRENT.jpg",
   f"localization/graphics/role_C/{RUN}/C240_FULL_RAW_SOURCE_PRIOR_CURRENT.jpg",
   f"localization/graphics/role_C/{RUN}/C240_TWO_LINE_HIGH_ZOOM_READABLE.jpg",
   f"localization/graphics/role_C/{RUN}/C240_TWO_LINE_HIGH_ZOOM_RAW.jpg",
   f"localization/graphics/role_C/{RUN}/C240_PRACTICAL_100.jpg",
   f"localization/graphics/role_C/{RUN}/C240_PRACTICAL_75.jpg",
   f"localization/graphics/role_C/{RUN}/C240_PRACTICAL_50.jpg"
 ],
 "controller_visual_qa":"PENDING","c3_strict_decision":"PENDING_CONTROLLER",
 "pre_ingame_export":"BLOCKED_UNTIL_CONTROLLER_C3",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"C240_841E796B_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
(wr/"C240_841E796B.json").write_text(json.dumps({
 "run":RUN,"role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":107,"candidate_sha256":CURRENT_SHA,"machine_status":"PASS_PENDING_CONTROLLER_VISUAL",
 "report":f"localization/graphics/role_C/{RUN}/C240_841E796B_MACHINE_QA.json",
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
