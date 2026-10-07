#!/usr/bin/env python3
# C2 q26 63C91067 A144 user-JPG rework: fresh independent C + mandatory C3.
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw

repo=Path.cwd()
RUN="20261007-C244-C2-Q026-63C91067-A144"
out=repo/"localization/graphics/role_C"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
SOURCE_SHA="d44868cbb37f8412901fa6252638250fcaebfed87e23a65772f61e710e3273ab"
PRIOR_SHA="2afae053f48811b79ca3cbcf706e6edf4013e65d012010cb48b681169621f675"
CURRENT_SHA="0281b7b46b5c53598bab2bf4a01f65f391b166345710460c51791da8cf70d530"
source_commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+source_commit+"/Release/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds"

# Exact readable-orientation source text/effect bboxes were established by independent C193
# against the same pinned canonical source and remain immutable source geometry.
rows=[
 {"region":0,"source_text":"Total Rank","korean":"종합 랭킹","source_bbox":[747,1174,1271,1275]},
 {"region":1,"source_text":"Total Rank","korean":"종합 랭킹","source_bbox":[599,156,1124,246]},
]

def sha(b): return hashlib.sha256(b).hexdigest()
def decode_dds(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if not mode or len(b)!=128+w*h*4:
        raise RuntimeError(("unsupported DDS",w,h,mips,masks,len(b)))
    return Image.frombytes("RGBA",(w,h),b[128:],"raw",mode),{"width":w,"height":h,"pitch":pitch,"mips":mips or 1,"mode":mode,"masks":[hex(x) for x in masks]}
def recover_exact(target_sha,path):
    for c in subprocess.check_output(["git","log","--all","--format=%H","--",path],text=True).splitlines():
        try: b=subprocess.check_output(["git","show",f"{c}:{path}"],stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError: continue
        if sha(b)==target_sha: return b,c
    raise RuntimeError("exact prior candidate not found "+target_sha)
def rect(shape,b):
    m=np.zeros(shape,dtype=bool);x0,y0,x1,y1=b;m[y0:y1,x0:x1]=True;return m
def bbox(m):
    ys,xs=np.nonzero(m)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def changed(a,b): return np.any(a!=b,axis=2)
def title_dark_mask(arr,b):
    x0,y0,x1,y1=b
    sub=arr[y0:y1,x0:x1]
    rgb=sub[:,:,:3]; a=sub[:,:,3]
    # Navy/very-dark outline seed. Starburst/cloud fills are materially brighter/redder.
    m=(a>40)&(rgb[:,:,0]<95)&(rgb[:,:,1]<105)&(rgb[:,:,2]<145)
    full=np.zeros(arr.shape[:2],bool); full[y0:y1,x0:x1]=m
    return full
def comp(im,bg=(102,102,102,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def panel(label,im,target_w=760):
    z=comp(im) if im.mode!="RGB" else im.copy()
    if z.width!=target_w:
        nh=max(1,round(z.height*target_w/z.width)); z=z.resize((target_w,nh),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(z.width,z.height+28),(20,20,20)); c.paste(z,(0,28)); ImageDraw.Draw(c).text((6,6),label,fill="white"); return c
def hstrip(xs):
    o=Image.new("RGB",(sum(x.width for x in xs),max(x.height for x in xs)),(18,18,18));x=0
    for im in xs:o.paste(im,(x,0));x+=im.width
    return o
def vstack(xs):
    o=Image.new("RGB",(max(x.width for x in xs),sum(x.height for x in xs)),(18,18,18));y=0
    for im in xs:o.paste(im,(0,y));y+=im.height
    return o

tmp=Path("/tmp/c244q26");tmp.mkdir(exist_ok=True)
sp=tmp/"source.dds";urllib.request.urlretrieve(source_url,sp)
sb=sp.read_bytes();cb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sha(cb)!=CURRENT_SHA: raise RuntimeError(("candidate drift",sha(cb)))
pb,prior_commit=recover_exact(PRIOR_SHA,"localization/graphics/hd_candidates/"+asset)

src_raw,sm=decode_dds(sb); prior_raw,pm=decode_dds(pb); cur_raw,cm=decode_dds(cb)
if sm!=pm or sm!=cm or sb[:128]!=pb[:128] or sb[:128]!=cb[:128]:
    raise RuntimeError(("structure/header drift",sm,pm,cm))
if (sm["width"],sm["height"])!=(2048,2048) or sm["mips"]!=1:
    raise RuntimeError(("unexpected structure",sm))

src=ImageOps.flip(src_raw); prior=ImageOps.flip(prior_raw); cur=ImageOps.flip(cur_raw)
sa,pa,ca=map(np.asarray,(src,prior,cur)); H,W=sa.shape[:2]

allowed=np.zeros((H,W),bool)
for r in rows: allowed |= rect((H,W),r["source_bbox"])
src_cur=changed(sa,ca); prior_cur=changed(pa,ca)
src_cur_alpha=sa[:,:,3]!=ca[:,:,3]; prior_cur_alpha=pa[:,:,3]!=ca[:,:,3]
outside_src_cur=int(np.count_nonzero(src_cur & ~allowed))
outside_src_cur_alpha=int(np.count_nonzero(src_cur_alpha & ~allowed))
outside_prior_cur=int(np.count_nonzero(prior_cur & ~allowed))
outside_prior_cur_alpha=int(np.count_nonzero(prior_cur_alpha & ~allowed))

reports=[]
for r in rows:
    ob=r["source_bbox"]
    sdb=bbox(title_dark_mask(sa,ob))
    cdb=bbox(title_dark_mask(ca,ob))
    pdb=bbox(title_dark_mask(pa,ob))
    if cdb is None: raise RuntimeError(("no candidate title dark mask",r["region"]))
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; cw,ch=cdb[2]-cdb[0],cdb[3]-cdb[1]
    margins=[cdb[0]-ob[0],ob[2]-cdb[2],cdb[1]-ob[1],ob[3]-cdb[3]]
    contain=cdb[0]>=ob[0] and cdb[1]>=ob[1] and cdb[2]<=ob[2] and cdb[3]<=ob[3]
    reports.append({
      **r,"source_dark_bbox_fresh":sdb,"prior_dark_bbox":pdb,"localized_dark_bbox_fresh":cdb,
      "source_bbox_size":[sw,sh],"localized_dark_size":[cw,ch],"margins":margins,
      "containment":"PASS" if contain else "FAIL",
      "size_ceiling":"PASS" if cw<=sw and ch<=sh else "FAIL",
      "positive_margin":"PASS" if min(margins)>0 else "FAIL",
    })

# User rejected prior as too small. Current must materially gain visible title footprint.
growth=[]
for x in reports:
    if x["prior_dark_bbox"] is None: raise RuntimeError(("prior mask missing",x["region"]))
    pbx=x["prior_dark_bbox"]; cbx=x["localized_dark_bbox_fresh"]
    pw,ph=pbx[2]-pbx[0],pbx[3]-pbx[1]; cw,ch=cbx[2]-cbx[0],cbx[3]-cbx[1]
    growth.append({"region":x["region"],"prior_dark_size":[pw,ph],"current_dark_size":[cw,ch],"width_gain":cw-pw,"height_gain":ch-ph})

pair_overlap=int(np.count_nonzero(title_dark_mask(ca,rows[0]["source_bbox"]) & title_dark_mask(ca,rows[1]["source_bbox"])))
machine_pass=(outside_src_cur==0 and outside_src_cur_alpha==0 and outside_prior_cur==0 and outside_prior_cur_alpha==0 and
              pair_overlap==0 and all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["positive_margin"]=="PASS" for x in reports) and
              all(g["width_gain"]>0 or g["height_gain"]>0 for g in growth))

# Evidence: source/prior/current overview, per-title detail, raw, practical scales.
focus=(450,80,1350,1335)
vstack([
 hstrip([panel("SOURCE ENGLISH",src.crop(focus),760),panel("PRIOR USER-REJECTED",prior.crop(focus),760)]),
 hstrip([panel("CURRENT A144",cur.crop(focus),760),panel("SOURCE vs CURRENT",Image.blend(comp(src.crop(focus)),comp(cur.crop(focus)),0.5),760)])
]).save(out/"C244_Q26_SOURCE_PRIOR_CURRENT_OVERVIEW.jpg","JPEG",quality=95,subsampling=0)

contacts=[]
for r in rows:
    x0,y0,x1,y1=r["source_bbox"];pad=35;cr=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    contacts.append(hstrip([panel("SOURCE r"+str(r["region"]),src.crop(cr),620),panel("PRIOR",prior.crop(cr),620),panel("CURRENT",cur.crop(cr),620)]))
vstack(contacts).save(out/"C244_Q26_ROW_CONTACTS.jpg","JPEG",quality=95,subsampling=0)

raw_focus=(450,700,1350,1980)
hstrip([panel("SOURCE RAW MIRROR_Y",src_raw.crop(raw_focus),900),panel("CURRENT RAW MIRROR_Y",cur_raw.crop(raw_focus),900)]).save(out/"C244_Q26_RAW_COMPARE.jpg","JPEG",quality=95,subsampling=0)

pr=[]
for pct in (100,75,50):
    sc=pct/100
    pair=[]
    for lab,im in [("SOURCE",src.crop(focus)),("CURRENT",cur.crop(focus))]:
        z=comp(im); z=z.resize((max(1,round(z.width*sc)),max(1,round(z.height*sc))),Image.Resampling.LANCZOS)
        pair.append(panel(f"{lab} {pct}%",z,max(600,z.width)))
    pr.append(hstrip(pair))
vstack(pr).save(out/"C244_Q26_PRACTICAL_100_75_50.jpg","JPEG",quality=95,subsampling=0)

report={
 "schema_version":2,"role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "run":RUN,"queue_index":26,"asset":asset,"producer_run":"A144_USERJPG_REWORK",
 "trigger":"USER_PRE_INGAME_JPG_FAIL_002_TOTAL_RANK_TEXT_TOO_SMALL",
 "source_sha256":SOURCE_SHA,"prior_user_rejected_sha256":PRIOR_SHA,"candidate_sha256":CURRENT_SHA,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":source_commit,"url":source_url},
 "prior_candidate_git_commit":prior_commit,
 "source_geometry_basis":"Exact two source text/effect bboxes were independently established by C193 on the identical canonical source SHA. Fresh C244 re-downloads that source, exact-recovers prior user-rejected bytes by SHA, independently decodes current bytes and re-derives current/prior title dark-outline bboxes from pixels; A144 producer masks/counters are not consumed.",
 "structure":sm,"rows":reports,"material_growth_vs_user_rejected":growth,
 "summary":{
   "source_to_current_changed_pixels_outside_two_source_bboxes":outside_src_cur,
   "source_to_current_alpha_changed_outside_two_source_bboxes":outside_src_cur_alpha,
   "prior_to_current_changed_pixels_outside_two_source_bboxes":outside_prior_cur,
   "prior_to_current_alpha_changed_outside_two_source_bboxes":outside_prior_cur_alpha,
   "localized_pair_overlap_pixels":pair_overlap,
   "header_128_exact_source_prior_current":sb[:128]==pb[:128]==cb[:128],
   "persisted_decode_authority":"PASS"
 },
 "machine_status":"PASS" if machine_pass else "FAIL",
 "fresh_c_decision":"PENDING_CONTROLLER" if machine_pass else "REWORK_REQUIRED",
 "c3_required":True,
 "c3_reason":["PRIOR_USER_PRE_INGAME_JPG_FAIL","TOTAL_RANK_TEXT_TOO_SMALL","SOURCE_STYLE_SCALE_FALSE_NEGATIVE_HISTORY"],
 "c3_machine_status":"PASS" if machine_pass else "BLOCKED_MACHINE_FAIL",
 "c3_visual_priorities":["plate_restoration","source_relative_scale","right_slant_direction","font_style_weight","glyph_integrity","protected_art","FLIP_Y_RAW_consistency","practical_scale"],
 "visual_evidence":[
   f"localization/graphics/role_C/{RUN}/C244_Q26_SOURCE_PRIOR_CURRENT_OVERVIEW.jpg",
   f"localization/graphics/role_C/{RUN}/C244_Q26_ROW_CONTACTS.jpg",
   f"localization/graphics/role_C/{RUN}/C244_Q26_RAW_COMPARE.jpg",
   f"localization/graphics/role_C/{RUN}/C244_Q26_PRACTICAL_100_75_50.jpg"
 ],
 "controller_visual_qa":"PENDING_CONTROLLER","c3_strict_decision":"PENDING_CONTROLLER" if machine_pass else "BLOCKED_MACHINE_FAIL",
 "pre_ingame_export":"BLOCKED_UNTIL_CONTROLLER_C3","user_jpg_review":"PENDING_NEW_REVIEW","runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"C244_63C91067_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C244_Q026_63C91067.json").write_text(json.dumps({
 "role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,"queue_index":26,"asset":"63C91067",
 "candidate_sha256":CURRENT_SHA,"machine_status":report["machine_status"],"c3_machine_status":report["c3_machine_status"],
 "report":f"localization/graphics/role_C/{RUN}/C244_63C91067_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"machine_status":report["machine_status"],"rows":reports,"growth":growth,"summary":report["summary"]},ensure_ascii=False,indent=2))
if not machine_pass: raise SystemExit("C244 q26 machine QA failed closed")