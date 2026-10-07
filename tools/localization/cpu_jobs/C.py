#!/usr/bin/env python3
# C238 / TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
# Fresh independent C + mandatory exact-SHA C3 machine audit for q106 / B202 / IGR-017.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib,json,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,ImageDraw

repo=Path.cwd()
RUN="20261007-C238-C2-Q106-788CE557-B202"
out=repo/"localization/graphics/role_C"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_selector_cvt_Exst/788CE557_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
SOURCE_SHA="4e486f35ca8982266f7f52e4d45aca20a12a2a4fe2a62fee9083db72c7454f9b"
CAND_SHA="a9c10f0000cb915baee2c73cba586ada6f7103be20a6add5aedafda2f219f482"
source_commit="a95efe01d1f136514cef94b0d9e9fd61df021754"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+source_commit+"/Release/spr_sprani_selector_cvt_Exst/788CE557_512x256.dds"
bdir=repo/"localization/graphics/role_B/20261006-B-USERREWORK202-788CE557-SLANT"
clean_path=bdir/"788CE557_CLEAN_PLATE.png"
protected_path=bdir/"788CE557_PROTECTED_MASK.png"
mask_paths={
 "for_experts":bdir/"788CE557_SOURCE_MASK_for_experts.png",
 "transmission_black":bdir/"788CE557_SOURCE_MASK_transmission_black.png",
 "transmission_white":bdir/"788CE557_SOURCE_MASK_transmission_white.png",
 "music_change":bdir/"788CE557_SOURCE_MASK_music_change.png",
 "time_remaining":bdir/"788CE557_SOURCE_MASK_time_remaining.png",
}
semantic={
 "for_experts":{"source":"For Experts","ko":"상급자용","window":[0,60,900,210]},
 "transmission_black":{"source":"Transmission","ko":"변속기","window":[0,196,620,330]},
 "transmission_white":{"source":"Transmission","ko":"변속기","window":[520,196,1120,330]},
 "music_change":{"source":"Music Change","ko":"음악 변경","window":[900,45,1500,190]},
 "time_remaining":{"source":"Time remaining :","ko":"남은 시간:","window":[1120,160,1960,330]},
}

def sha(b): return hashlib.sha256(b).hexdigest()
def decode_dds(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if not mode or len(b)!=128+w*h*4: raise RuntimeError(("DDS structure",w,h,mips,masks,len(b)))
    im=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return im,{"width":w,"height":h,"pitch":pitch,"mips":mips,"mode":mode,"masks":[hex(x) for x in masks]}
def bbox(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def changed(a,b): return np.any(a!=b,axis=2)
def load_mask(p,size):
    im=Image.open(p)
    if im.size!=size: raise RuntimeError(("mask size",p,im.size,size))
    a=np.asarray(im.convert("RGBA"))
    alpha=a[:,:,3]
    rgb=np.max(a[:,:,:3],axis=2)
    if int(np.count_nonzero(alpha<255))>0 and int(np.count_nonzero(alpha))<alpha.size:
        m=alpha>0
    else:
        m=rgb>0
    if not m.any(): raise RuntimeError(("empty mask",str(p)))
    return m
def comp(im,bg=(56,56,56,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def label_card(label,im,target_w=1024):
    z=comp(im)
    if z.width!=target_w:
        h=round(z.height*target_w/z.width); z=z.resize((target_w,h),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(z.width,z.height+28),(20,20,20)); c.paste(z,(0,28))
    ImageDraw.Draw(c).text((6,6),label,fill="white")
    return c
def hstrip(cards):
    w=sum(c.width for c in cards); h=max(c.height for c in cards)
    o=Image.new("RGB",(w,h),(20,20,20)); x=0
    for c in cards:o.paste(c,(x,0));x+=c.width
    return o

tmp=Path("/tmp/c238"); tmp.mkdir(exist_ok=True)
sp=tmp/"source.dds"; urllib.request.urlretrieve(source_url,sp)
sb=sp.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sha(cb)!=CAND_SHA: raise RuntimeError(("candidate drift",sha(cb)))

src_raw,sm=decode_dds(sb); cand_raw,cm=decode_dds(cb)
if (sm["width"],sm["height"])!=(2048,1024) or cm!=sm: raise RuntimeError(("structure mismatch",sm,cm))
if sb[:128]!=cb[:128]: raise RuntimeError("header 128 mismatch")
if sm["mips"]!=1: raise RuntimeError(("mips",sm["mips"]))
src=ImageOps.flip(src_raw); final=ImageOps.flip(cand_raw)
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError(("clean size",clean.size,src.size))
sa,fa,ca=map(np.asarray,(src,final,clean))
H,W=sa.shape[:2]

masks={}
allowed=np.zeros((H,W),bool)
rows=[]
for key,p in mask_paths.items():
    m=load_mask(p,(W,H))
    bb=bbox(m)
    x0,y0,x1,y1=semantic[key]["window"]
    if bb is None or bb[0]<x0 or bb[1]<y0 or bb[2]>x1 or bb[3]>y1:
        raise RuntimeError(("mask/window mismatch",key,bb,semantic[key]["window"]))
    masks[key]=m; allowed|=m
    rows.append({"key":key,"source":semantic[key]["source"],"korean":semantic[key]["ko"],"original_bbox":bb})

protected=load_mask(protected_path,(W,H))
# Producer evidence masks must not overlap each other; target and protected must be disjoint.
pair_source_overlap=0
ks=list(masks)
for i in range(len(ks)):
    for j in range(i+1,len(ks)):
        pair_source_overlap+=int(np.count_nonzero(masks[ks[i]]&masks[ks[j]]))
mask_protected_overlap=int(np.count_nonzero(allowed&protected))
if pair_source_overlap or mask_protected_overlap:
    raise RuntimeError(("source mask overlap",pair_source_overlap,mask_protected_overlap))

src_clean_diff=changed(sa,ca)
src_final_diff=changed(sa,fa)
clean_final_diff=changed(ca,fa)
alpha_src_final=sa[:,:,3]!=fa[:,:,3]
clean_changed_outside=int(np.count_nonzero(src_clean_diff&~allowed))
final_changed_outside=int(np.count_nonzero(src_final_diff&~allowed))
alpha_changed_outside=int(np.count_nonzero(alpha_src_final&~allowed))
source_mask_unchanged_in_clean=int(np.count_nonzero((~src_clean_diff)&allowed))
if clean_changed_outside or final_changed_outside or alpha_changed_outside or source_mask_unchanged_in_clean:
    raise RuntimeError(("scope/clean failure",clean_changed_outside,final_changed_outside,alpha_changed_outside,source_mask_unchanged_in_clean))

localized_masks=[]
row_reports=[]
for r in rows:
    key=r["key"]; om=masks[key]; ob=r["original_bbox"]
    # Current Korean content = final-vs-clean change constrained to the exact source text mask footprint.
    lm=clean_final_diff & om
    lb=bbox(lm)
    if lb is None: raise RuntimeError(("no localized pixels",key))
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]
    lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    contain=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
    sizeok=lw<=sw and lh<=sh
    positive=min(margins)>0
    prot=int(np.count_nonzero(lm&protected))
    row_reports.append({
      "key":key,"source":r["source"],"korean":r["korean"],
      "original_bbox":ob,"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":lb[0]-ob[0],"delta_right":lb[2]-ob[2],
      "delta_top":lb[1]-ob[1],"delta_bottom":lb[3]-ob[3],
      "margins":margins,
      "containment":"PASS" if contain else "FAIL",
      "size_ceiling":"PASS" if sizeok else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL",
      "protected_overlap_pixels":prot
    })
    localized_masks.append(lm)

pair_localized_overlap=0
for i in range(len(localized_masks)):
    for j in range(i+1,len(localized_masks)):
        pair_localized_overlap+=int(np.count_nonzero(localized_masks[i]&localized_masks[j]))
localized_union=np.zeros((H,W),bool)
for m in localized_masks: localized_union|=m
localized_protected_overlap=int(np.count_nonzero(localized_union&protected))
row_pass=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" and r["protected_overlap_pixels"]==0 for r in row_reports)
machine_pass=(row_pass and pair_localized_overlap==0 and localized_protected_overlap==0 and clean_changed_outside==0 and final_changed_outside==0 and alpha_changed_outside==0 and source_mask_unchanged_in_clean==0)

# Evidence sheets.
hstrip([label_card("CANONICAL SOURCE READABLE",src),label_card("B202 CLEAN",clean),label_card("B202 CURRENT READABLE",final)]).save(out/"C238_SOURCE_CLEAN_FINAL.jpg","JPEG",quality=95,subsampling=0)
hstrip([label_card("CANONICAL SOURCE RAW",src_raw),label_card("B202 CURRENT RAW",cand_raw)]).save(out/"C238_RAW_SOURCE_FINAL.jpg","JPEG",quality=95,subsampling=0)

# Row contacts from source/clean/final using C-derived mask bboxes + padding.
row_cards=[]
for r in row_reports:
    x0,y0,x1,y1=r["original_bbox"]; pad=16
    box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    parts=[]
    for lab,im in [("SRC",src),("CLEAN",clean),("FINAL",final)]:
        z=im.crop(box)
        scale=2 if z.width<900 else 1
        if scale>1:z=z.resize((z.width*scale,z.height*scale),Image.Resampling.NEAREST)
        parts.append(label_card(lab+" "+r["key"],z,max(400,z.width)))
    row_cards.append(hstrip(parts))
mw=max(x.width for x in row_cards); mh=sum(x.height for x in row_cards)
rowsheet=Image.new("RGB",(mw,mh),(18,18,18)); yy=0
for x in row_cards: rowsheet.paste(x,(0,yy)); yy+=x.height
rowsheet.save(out/"C238_ROW_CONTACTS.jpg","JPEG",quality=95,subsampling=0)

pr=[]
for pct in (100,75,50):
    sc=pct/100
    srcs=comp(src).resize((round(W*sc),round(H*sc)),Image.Resampling.LANCZOS)
    fins=comp(final).resize((round(W*sc),round(H*sc)),Image.Resampling.LANCZOS)
    # top UI only is relevant, crop after scale.
    hh=max(1,round(360*sc))
    srcs=srcs.crop((0,0,srcs.width,min(srcs.height,hh)))
    fins=fins.crop((0,0,fins.width,min(fins.height,hh)))
    pr.append(hstrip([label_card(f"SOURCE {pct}%",srcs,max(700,srcs.width//2)),label_card(f"FINAL {pct}%",fins,max(700,fins.width//2))]))
mw=max(x.width for x in pr); mh=sum(x.height for x in pr)
ps=Image.new("RGB",(mw,mh),(18,18,18)); yy=0
for x in pr: ps.paste(x,(0,yy)); yy+=x.height
ps.thumbnail((5000,5000),Image.Resampling.LANCZOS)
ps.save(out/"C238_PRACTICAL_100_75_50.jpg","JPEG",quality=95,subsampling=0)

report={
 "schema_version":2,"role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "run":RUN,"queue_index":106,"asset":asset,"producer_run":"B202","priority":"P0","user_ingame_regression":"IGR-017",
 "source_sha256":SOURCE_SHA,"candidate_sha256":CAND_SHA,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":source_commit,"url":source_url},
 "independent_basis":"C freshly downloads/decodes the pinned source, decodes the exact current candidate, validates B202 clean/source/protected masks against the source with independent pixel logic, re-derives all persisted localized bboxes from FINAL-vs-CLEAN pixels, and recomputes containment, blast radius, alpha, overlap and protected-art gates.",
 "structure":sm,
 "rows":row_reports,
 "summary":{
   "bbox_size_positive_margin":f"{sum(1 for r in row_reports if r['containment']=='PASS' and r['size_ceiling']=='PASS' and r['positive_margin']=='PASS')}/5 PASS",
   "source_mask_pair_overlap_pixels":pair_source_overlap,
   "source_mask_vs_protected_overlap_pixels":mask_protected_overlap,
   "clean_changed_outside_source_masks":clean_changed_outside,
   "final_changed_outside_source_masks":final_changed_outside,
   "alpha_changed_outside_source_masks":alpha_changed_outside,
   "source_mask_pixels_unchanged_in_clean":source_mask_unchanged_in_clean,
   "localized_pair_overlap_pixels":pair_localized_overlap,
   "localized_to_protected_overlap_pixels":localized_protected_overlap,
   "OutRun2SP_and_unrelated_art_preservation":"PASS_BY_ZERO_OUTSIDE_CHANGE"
 },
 "machine_status":"PASS" if machine_pass else "FAIL",
 "fresh_c_decision":"PENDING_CONTROLLER" if machine_pass else "REWORK_REQUIRED",
 "c3_required":True,
 "c3_reason":["USER_INGAME_FAIL_IGR_017","PRIOR_BAD_SLANT","MULTI_STYLE_SELECTOR_ATLAS","TIGHT_PROTECTED_OUTRUN2SP_AND_ICONS"],
 "c3_machine_status":"PASS" if machine_pass else "BLOCKED_MACHINE_FAIL",
 "c3_visual_priorities":["slant_perspective","clean_plate","source_style","scale_readability","glyph_integrity","protected_separation","placement","FLIP_Y_RAW_consistency","practical_scale","coverage"],
 "visual_evidence":[
   "localization/graphics/role_C/"+RUN+"/C238_SOURCE_CLEAN_FINAL.jpg",
   "localization/graphics/role_C/"+RUN+"/C238_ROW_CONTACTS.jpg",
   "localization/graphics/role_C/"+RUN+"/C238_RAW_SOURCE_FINAL.jpg",
   "localization/graphics/role_C/"+RUN+"/C238_PRACTICAL_100_75_50.jpg"
 ],
 "coverage":{"localized_semantics":["For Experts","Transmission (black)","Transmission (white)","Music Change","Time remaining :"],"preserved_policy":["OutRun2SP product artwork","selector arrows","warning icon","vehicle silhouettes","steering wheels","numeric row","unrelated atlas art"],"status":"PASS"},
 "controller_visual_qa":"PENDING_CONTROLLER",
 "c3_strict_decision":"PENDING_CONTROLLER" if machine_pass else "BLOCKED_MACHINE_FAIL",
 "pre_ingame_export":"BLOCKED_UNTIL_CONTROLLER_C3",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"C238_788CE557_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C238_788CE557.json").write_text(json.dumps({
 "role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,"queue_index":106,"asset":"788CE557",
 "candidate_sha256":CAND_SHA,"machine_status":report["machine_status"],"c3_machine_status":report["c3_machine_status"],
 "report":"localization/graphics/role_C/"+RUN+"/C238_788CE557_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"machine_status":report["machine_status"],"summary":report["summary"],"rows":row_reports},ensure_ascii=False,indent=2))
if not machine_pass: raise SystemExit("C238 machine QA failed closed")
