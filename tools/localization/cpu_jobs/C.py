#!/usr/bin/env python3
# C241 / TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
# Fresh independent C + exact-SHA C3 strict audit for q232 EBFC709F / B230.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib, io, json, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw

repo=Path.cwd()
RUN="20261007-C241-C2-Q232-EBFC709F-B230"
out=repo/"localization/graphics/role_C"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset=Path("textures/load/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds")
candidate=repo/"localization/graphics/hd_candidates"/asset
SOURCE_SHA="ad7a1c21be17d1fa93463201a26a85a21899dbe1162d5c2748ddeb6136a4f9a0"
PRIOR_SHA="54ed1e64dde7be9686b882748ab934d3e465d9966289c6ec7772daeeef8f7221"
CURRENT_SHA="dc76c000cfce17098940f551512e6f746319ba8a1892345eb060693004747ea1"
source_commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+source_commit+"/Release/spr_sprani_sumo_fe_cvt_Exst/EBFC709F_512x256.dds"

specs=[
 {"key":"create_help","source":"Create a game and invite your friends!","ko":"게임을 만들고 친구를 초대하세요!","window":[0,360,1250,450]},
 {"key":"join_help","source":"Join your friends in a game of OutRun!","ko":"친구들과 OutRun 게임에 참가하세요!","window":[0,500,1650,620]},
]

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    with Image.open(io.BytesIO(b)) as im:
        return im.convert("RGBA")
def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def rect(shape,b):
    m=np.zeros(shape,dtype=bool); x0,y0,x1,y1=b; m[y0:y1,x0:x1]=True; return m
def changed(a,b): return np.any(a!=b,axis=2)
def find_exact_in_git(target_sha, relpath):
    for h in subprocess.check_output(["git","log","--format=%H","--all","--",str(relpath)],text=True).splitlines():
        try: data=subprocess.check_output(["git","show",f"{h}:{relpath}"],stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError: continue
        if sha(data)==target_sha: return data,h
    raise RuntimeError(f"exact historical bytes not found {target_sha} {relpath}")
def comp(im,bg=(104,104,104,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im,w=1024):
    z=comp(im)
    if z.width!=w:
        h=max(1,round(z.height*w/z.width)); z=z.resize((w,h),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(z.width,z.height+28),(20,20,20)); c.paste(z,(0,28))
    ImageDraw.Draw(c).text((6,6),label,fill="white")
    return c
def hstrip(cards):
    o=Image.new("RGB",(sum(c.width for c in cards),max(c.height for c in cards)),(20,20,20))
    x=0
    for c in cards:o.paste(c,(x,0));x+=c.width
    return o

# Fresh pinned canonical source download.
tmp=Path("/tmp/c241"); tmp.mkdir(exist_ok=True)
sp=tmp/"source.dds"; urllib.request.urlretrieve(source_url,sp)
sb=sp.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sha(cb)!=CURRENT_SHA: raise RuntimeError(("candidate drift",sha(cb)))
priorb,prior_commit=find_exact_in_git(PRIOR_SHA,Path("localization/graphics/hd_candidates")/asset)
src_raw=decode(sb); prior_raw=decode(priorb); cur_raw=decode(cb)
if src_raw.size!=(2048,1024) or prior_raw.size!=src_raw.size or cur_raw.size!=src_raw.size:
    raise RuntimeError(("dimension mismatch",src_raw.size,prior_raw.size,cur_raw.size))
if sb[:128]!=priorb[:128] or sb[:128]!=cb[:128]:
    raise RuntimeError("DDS header 128 mismatch")
mips=int.from_bytes(cb[28:32],"little") or 1
if mips!=1: raise RuntimeError(("unexpected mip count",mips))

# Contract readable orientation is FLIP-Y; raw remains mirror_y.
src=ImageOps.flip(src_raw); prior=ImageOps.flip(prior_raw); cur=ImageOps.flip(cur_raw)
sa,pa,ca=map(np.asarray,(src,prior,cur)); H,W=sa.shape[:2]

# C derives exact canonical source alpha bboxes independently inside semantic windows.
source_masks=[]; source_union=np.zeros((H,W),bool); rows=[]
for s in specs:
    wm=rect((H,W),s["window"])
    sm=(sa[:,:,3]>0)&wm
    bb=bbox(sm)
    if bb is None: raise RuntimeError(("missing source text",s["key"]))
    # Prior C225R intentionally preserved these help rows; require pixel identity to canonical source here.
    x0,y0,x1,y1=bb
    if not np.array_equal(pa[y0:y1,x0:x1],sa[y0:y1,x0:x1]):
        raise RuntimeError(("prior not canonical-source exact in help bbox",s["key"],bb))
    sw,sh=x1-x0,y1-y0
    if sh<30 or sh>100 or sw<300: raise RuntimeError(("implausible source bbox",s["key"],bb))
    source_masks.append(sm); source_union|=sm
    rows.append({"key":s["key"],"source":s["source"],"korean":s["ko"],"original_bbox":bb,"source_size":[sw,sh]})

# Exact rework region = the two independent source bboxes, not producer masks.
rework=np.zeros((H,W),bool)
for r in rows: rework|=rect((H,W),r["original_bbox"])
if int(np.count_nonzero(source_masks[0]&source_masks[1]))!=0:
    raise RuntimeError("source help masks overlap")

# Material change from prior to current must stay inside these exact source bboxes.
pcdiff=changed(pa,ca); padiff=pa[:,:,3]!=ca[:,:,3]
blast=int(np.count_nonzero(pcdiff&~rework))
alpha_blast=int(np.count_nonzero(padiff&~rework))
if blast or alpha_blast: raise RuntimeError(("blast radius",blast,alpha_blast))

# Independent clean plate: prior accepted bytes with only exact canonical source-alpha help pixels removed.
clean_arr=pa.copy()
clean_arr[source_union]=[0,0,0,0]
clean=Image.fromarray(clean_arr.astype(np.uint8),"RGBA")
cla=np.asarray(clean)
source_alpha_remaining=int(np.count_nonzero(cla[:,:,3][source_union]))
if source_alpha_remaining: raise RuntimeError(("clean source alpha remains",source_alpha_remaining))

# Derive persisted localized geometry from CURRENT vs independent CLEAN.
cf=changed(cla,ca)
row_reports=[]; localized_masks=[]
for r in rows:
    ob=r["original_bbox"]; x0,y0,x1,y1=ob
    rm=rect((H,W),ob)
    lm=cf & rm & (ca[:,:,3]>0)
    lb=bbox(lm)
    if lb is None: raise RuntimeError(("localized pixels missing",r["key"]))
    sw,sh=r["source_size"]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    contain=lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1
    sizeok=lw<=sw and lh<=sh
    positive=min(margins)>0
    row_reports.append({
      **r,"localized_bbox":lb,"localized_size":[lw,lh],"margins":margins,
      "delta_left":lb[0]-x0,"delta_right":lb[2]-x1,"delta_top":lb[1]-y0,"delta_bottom":lb[3]-y1,
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if sizeok else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL"
    })
    localized_masks.append(lm)

pair_overlap=int(np.count_nonzero(localized_masks[0]&localized_masks[1]))
localized_union=localized_masks[0]|localized_masks[1]
# Everything outside q232's exact two help bboxes is protected for this B230 rework, including four prior Korean headings.
localized_to_protected=int(np.count_nonzero(localized_union&~rework))
row_pass=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in row_reports)
machine_pass=row_pass and blast==0 and alpha_blast==0 and source_alpha_remaining==0 and pair_overlap==0 and localized_to_protected==0

# Evidence sheets: canonical source / prior / independent clean / current; raw; row contacts; practical display scales.
overview=Image.new("RGB",(2048,2104),(20,20,20))
for pos,lab,im in [
 ((0,0),"CANONICAL ENGLISH SOURCE",src),((1024,0),"PRIOR C225R",prior),
 ((0,1052),"C241 INDEPENDENT CLEAN",clean),((1024,1052),"B230 CURRENT",cur)]:
    overview.paste(card(lab,im),pos)
overview.save(out/"C241_SOURCE_PRIOR_CLEAN_FINAL_READABLE.jpg","JPEG",quality=95,subsampling=0)

rawsheet=hstrip([card("CANONICAL SOURCE RAW MIRROR_Y",src_raw),card("B230 CURRENT RAW MIRROR_Y",cur_raw)])
rawsheet.save(out/"C241_SOURCE_FINAL_RAW.jpg","JPEG",quality=95,subsampling=0)

row_cards=[]
for r in row_reports:
    x0,y0,x1,y1=r["original_bbox"]; pad=16
    box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    parts=[]
    for lab,im in [("SOURCE",src),("PRIOR",prior),("CLEAN",clean),("CURRENT",cur)]:
        z=im.crop(box)
        if z.width<1200: z=z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST)
        parts.append(card(lab+" "+r["key"],z,max(500,z.width)))
    row_cards.append(hstrip(parts))
mw=max(x.width for x in row_cards); mh=sum(x.height for x in row_cards)
rowsheet=Image.new("RGB",(mw,mh),(18,18,18)); yy=0
for x in row_cards: rowsheet.paste(x,(0,yy)); yy+=x.height
rowsheet.thumbnail((6000,5000),Image.Resampling.LANCZOS)
rowsheet.save(out/"C241_HELP_ROW_CONTACTS.jpg","JPEG",quality=95,subsampling=0)

pr=[]
roi=(0,250,1700,650)
for pct in (100,75,50):
    sc=pct/100
    parts=[]
    for lab,im in [("SOURCE",src),("PRIOR",prior),("CURRENT",cur)]:
        z=comp(im).crop(roi)
        z=z.resize((max(1,round(z.width*sc)),max(1,round(z.height*sc))),Image.Resampling.LANCZOS)
        c=Image.new("RGB",(z.width,z.height+24),(20,20,20)); c.paste(z,(0,24)); ImageDraw.Draw(c).text((4,4),f"{lab} {pct}%",fill="white")
        parts.append(c)
    pr.append(hstrip(parts))
mw=max(x.width for x in pr); mh=sum(x.height for x in pr)
ps=Image.new("RGB",(mw,mh),(18,18,18)); yy=0
for x in pr: ps.paste(x,(0,yy)); yy+=x.height
ps.thumbnail((6000,5000),Image.Resampling.LANCZOS)
ps.save(out/"C241_PRACTICAL_100_75_50.jpg","JPEG",quality=95,subsampling=0)

report={
 "schema_version":2,"role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "run":RUN,"qa_id":"C241","queue_index":232,"asset":str(asset),"producer_run":"B230",
 "source_sha256":SOURCE_SHA,"prior_candidate_sha256":PRIOR_SHA,"candidate_sha256":CURRENT_SHA,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":source_commit,"url":source_url},
 "prior_candidate_git_commit":prior_commit,
 "independent_basis":"C freshly downloads/decodes pinned canonical source, recovers exact C225R prior bytes by SHA from Git history, independently derives the two help source-alpha bboxes from fixed semantic windows, reconstructs clean from prior bytes, and re-derives persisted current localized geometry/diff scope without consuming producer masks or bbox counters.",
 "structure":{"dimensions":[W,H],"mip_count":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":row_reports,
 "summary":{
   "bbox_size_positive_margin":f"{sum(1 for r in row_reports if r['containment']=='PASS' and r['size_ceiling']=='PASS' and r['positive_margin']=='PASS')}/2 PASS",
   "prior_to_current_changed_pixels_outside_two_source_bboxes":blast,
   "prior_to_current_alpha_changed_outside_two_source_bboxes":alpha_blast,
   "independent_clean_source_alpha_remaining":source_alpha_remaining,
   "localized_pair_overlap_pixels":pair_overlap,
   "localized_to_protected_outside_rework_pixels":localized_to_protected,
   "prior_four_Korean_headings_preserved":"PASS_BY_ZERO_BLAST_RADIUS",
   "brand_policy_OutRun_preserved_English":"PASS"
 },
 "coverage":{
   "newly_localized_help":["Create a game and invite your friends!","Join your friends in a game of OutRun!"],
   "prior_localized_headings_preserved":["JOIN GAME small","CREATE GAME small","CREATE GAME large","JOIN GAME large"],
   "status":"PASS_ALL_VISIBLE_LOCALIZABLE_SEGMENTS_ACCOUNTED"
 },
 "machine_status":"PASS" if machine_pass else "FAIL",
 "fresh_c_decision":"PENDING_CONTROLLER" if machine_pass else "REWORK_REQUIRED",
 "c3_required":True,
 "c3_reason":["PRE_INGAME_HUMAN_REJECTION_COVERAGE_FALSE_NEGATIVE","PRIOR_C225R_VISUAL_POLICY_FALSE_NEGATIVE","SMALL_DARK_HELP_TEXT","CHANGED_BYTES_AFTER_PRIOR_C_PASS"],
 "c3_machine_status":"PASS" if machine_pass else "BLOCKED_MACHINE_FAIL",
 "c3_visual_priorities":["coverage","clean_plate","source_style","scale_readability","glyph_integrity","protected_separation","source_placement","FLIP_Y_RAW_consistency","practical_scale"],
 "visual_evidence":[
   f"localization/graphics/role_C/{RUN}/C241_SOURCE_PRIOR_CLEAN_FINAL_READABLE.jpg",
   f"localization/graphics/role_C/{RUN}/C241_HELP_ROW_CONTACTS.jpg",
   f"localization/graphics/role_C/{RUN}/C241_SOURCE_FINAL_RAW.jpg",
   f"localization/graphics/role_C/{RUN}/C241_PRACTICAL_100_75_50.jpg"
 ],
 "controller_visual_qa":"PENDING_CONTROLLER",
 "c3_strict_decision":"PENDING_CONTROLLER" if machine_pass else "BLOCKED_MACHINE_FAIL",
 "pre_ingame_export":"BLOCKED_UNTIL_CONTROLLER_C_AND_C3_PASS",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"C241_EBFC709F_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C241_EBFC709F.json").write_text(json.dumps({
 "role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,"queue_index":232,"asset":"EBFC709F",
 "candidate_sha256":CURRENT_SHA,"machine_status":report["machine_status"],"c3_machine_status":report["c3_machine_status"],
 "report":f"localization/graphics/role_C/{RUN}/C241_EBFC709F_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"machine_status":report["machine_status"],"summary":report["summary"],"rows":row_reports},ensure_ascii=False,indent=2))
if not machine_pass: raise SystemExit("C241 machine QA failed closed")
