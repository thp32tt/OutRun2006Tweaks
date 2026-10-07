#!/usr/bin/env python3
# C2 q100 53CE39D5 / B233 fresh independent C + mandatory exact-SHA C3.
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw

repo=Path.cwd()
RUN="20261007-C2-Q100-53CE39D5-B233-FRESH-C3"
out=repo/"localization/graphics/role_C"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_selector_cvt_Exst/53CE39D5_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
SOURCE_SHA="cfed1de58cefd8c235fc464e27058439ffd26427294a3bce17192e584679426a"
PRIOR_SHA="08467408b4ef087a8e2a5e8408b159e4f635fe0c261ad2ccae76a1499be5ced1"
CURRENT_SHA="7235731a2add8e947476cd22b971e5b57a7de390ae134609f4254a2f493a557d"
source_commit="a95efe01d1f136514cef94b0d9e9fd61df021754"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+source_commit+"/Release/spr_sprani_selector_cvt_Exst/53CE39D5_512x512.dds"
clean_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION30/53CE39D5_HD_CLEAN_PLATE.png"

cards=[
 ("random", [1120,0,1480,125], 1),
 ("time_attack_or2",[0,1630,365,1830],3),
 ("heart_attack_or2",[380,1630,735,1830],3),
 ("outrun_or2",[750,1615,1080,1810],3),
 ("time_attack_special",[1110,1535,1465,1710],3),
 ("heart_attack_special",[1470,1485,1840,1680],3),
 ("outrun_special",[1020,1820,1360,2020],3),
]
semantic={
 "random":["랜덤"],
 "time_attack_or2":["타임 어택","모드","아웃런2"],
 "heart_attack_or2":["하트 어택","모드","아웃런2"],
 "outrun_or2":["아웃런","모드","아웃런2"],
 "time_attack_special":["타임 어택","모드","스페셜 투어"],
 "heart_attack_special":["하트 어택","모드","스페셜 투어"],
 "outrun_special":["아웃런","모드","스페셜 투어"],
}

def sha(b): return hashlib.sha256(b).hexdigest()
def decode_dds(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if not mode or len(b)!=128+w*h*4:
        raise RuntimeError(("unsupported structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,{"width":w,"height":h,"pitch":pitch,"mips":mips or 1,"mode":mode,"masks":[hex(x) for x in masks]}
def changed(a,b): return np.any(a!=b,axis=2)
def bbox(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def rect(shape,b):
    m=np.zeros(shape,dtype=bool); x0,y0,x1,y1=b; m[y0:y1,x0:x1]=True; return m
def recover_exact(target_sha,path):
    commits=subprocess.check_output(["git","log","--all","--format=%H","--",path],text=True).splitlines()
    for c in commits:
        try: b=subprocess.check_output(["git","show",f"{c}:{path}"],stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError: continue
        if sha(b)==target_sha: return b,c
    raise RuntimeError("exact prior candidate not found: "+target_sha)
def y_runs(mask,x0,y0,x1,y1):
    # Derive source/final line bands independently from actual diff pixels in each semantic card window.
    sub=mask[y0:y1,x0:x1]
    ys=np.any(sub,axis=1)
    runs=[]; s=None
    for i,v in enumerate(ys):
        if v and s is None: s=i
        if s is not None and ((not v) or i==len(ys)-1):
            e=i if not v else i+1
            if e-s>=2: runs.append((y0+s,y0+e))
            s=None
    return runs
def card_line_bboxes(mask, card):
    key,b,n=card; x0,y0,x1,y1=b
    runs=y_runs(mask,x0,y0,x1,y1)
    if len(runs)!=n:
        raise RuntimeError(("line-run count",key,len(runs),runs))
    out=[]
    for ys,ye in runs:
        m=mask & rect(mask.shape,(x0,ys,x1,ye))
        bb=bbox(m)
        if bb is None: raise RuntimeError(("empty line",key,ys,ye))
        out.append(bb)
    return out
def comp(im,bg=(102,102,102,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def panel(label,im,target_w=900):
    z=comp(im)
    if z.width!=target_w:
        nh=max(1,round(z.height*target_w/z.width)); z=z.resize((target_w,nh),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(z.width,z.height+28),(20,20,20)); c.paste(z,(0,28)); ImageDraw.Draw(c).text((6,6),label,fill="white"); return c
def hstrip(xs):
    w=sum(x.width for x in xs); h=max(x.height for x in xs)
    o=Image.new("RGB",(w,h),(18,18,18)); xx=0
    for x in xs:o.paste(x,(xx,0));xx+=x.width
    return o
def vstack(xs):
    w=max(x.width for x in xs); h=sum(x.height for x in xs)
    o=Image.new("RGB",(w,h),(18,18,18)); yy=0
    for x in xs:o.paste(x,(0,yy));yy+=x.height
    return o

tmp=Path("/tmp/c2q100"); tmp.mkdir(exist_ok=True)
sp=tmp/"source.dds"; urllib.request.urlretrieve(source_url,sp)
sb=sp.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sha(cb)!=CURRENT_SHA: raise RuntimeError(("candidate drift",sha(cb)))
pb,prior_commit=recover_exact(PRIOR_SHA,"localization/graphics/hd_candidates/"+asset)

src_raw,sm=decode_dds(sb); prior_raw,pm=decode_dds(pb); cur_raw,cm=decode_dds(cb)
if sm!=pm or sm!=cm or sb[:128]!=pb[:128] or sb[:128]!=cb[:128]:
    raise RuntimeError(("DDS structure/header drift",sm,pm,cm))
if (sm["width"],sm["height"])!=(2048,2048) or sm["mips"]!=1:
    raise RuntimeError(("unexpected structure",sm))
src=ImageOps.flip(src_raw); prior=ImageOps.flip(prior_raw); cur=ImageOps.flip(cur_raw)
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError(("clean size",clean.size,src.size))
sa,pa,ca,fa=map(np.asarray,(src,prior,clean,cur))
H,W=sa.shape[:2]

source_clean=changed(sa,ca)
prior_clean=changed(pa,ca)
current_clean=changed(fa,ca)
prior_current=changed(pa,fa)
prior_current_alpha=pa[:,:,3]!=fa[:,:,3]

# The validated clean plate may only differ from source within the seven semantic card windows.
card_window_union=np.zeros((H,W),bool)
for _,b,_ in cards: card_window_union |= rect((H,W),b)
clean_diff_outside_windows=int(np.count_nonzero(source_clean & ~card_window_union))
if clean_diff_outside_windows:
    raise RuntimeError(("clean changed outside semantic windows",clean_diff_outside_windows))

# Fresh C derives source/current line bboxes from SOURCE-vs-CLEAN and CURRENT-vs-CLEAN, not producer masks/bboxes.
source_rows=[]; current_rows=[]; prior_rows=[]
for c in cards:
    key,b,n=c
    sbs=card_line_bboxes(source_clean,c)
    cbs=card_line_bboxes(current_clean,c)
    pbs=card_line_bboxes(prior_clean,c)
    if len(sbs)!=len(cbs) or len(sbs)!=len(pbs): raise RuntimeError(("row count mismatch",key))
    for i,(ob,lb,pb_) in enumerate(zip(sbs,cbs,pbs),1):
        source_rows.append((key,i,ob))
        current_rows.append((key,i,lb))
        prior_rows.append((key,i,pb_))

if len(source_rows)!=19 or len(current_rows)!=19:
    raise RuntimeError(("expected 19 lines",len(source_rows),len(current_rows)))

allowed=np.zeros((H,W),bool)
row_reports=[]; localized_masks=[]
for (key,i,ob),(_,_,lb),(_,_,pbb) in zip(source_rows,current_rows,prior_rows):
    allowed |= rect((H,W),ob)
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]
    lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    contain=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
    sizeok=lw<=sw and lh<=sh
    positive=min(margins)>0
    lm=current_clean & rect((H,W),lb)
    localized_masks.append(lm)
    ko=semantic[key][i-1]
    row_reports.append({
      "target":key,"line_index":i,"korean":ko,
      "original_bbox":ob,"prior_localized_bbox":pbb,"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":lb[0]-ob[0],"delta_right":lb[2]-ob[2],
      "delta_top":lb[1]-ob[1],"delta_bottom":lb[3]-ob[3],
      "margins":margins,
      "containment":"PASS" if contain else "FAIL",
      "size_ceiling":"PASS" if sizeok else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL",
    })

# Exact blast-radius and containment checks.
source_clean_outside_allowed=int(np.count_nonzero(source_clean & ~allowed))
current_clean_outside_allowed=int(np.count_nonzero(current_clean & ~allowed))
current_alpha_outside_allowed=int(np.count_nonzero((ca[:,:,3]!=fa[:,:,3]) & ~allowed))

# B233 must only alter the 18 non-RANDOM rows; RANDOM remains byte/pixel exact to C117.
random_box=source_rows[0][2]
random_mask=rect((H,W),random_box)
rework_allowed=allowed & ~random_mask
prior_current_outside_rework=int(np.count_nonzero(prior_current & ~rework_allowed))
prior_current_alpha_outside_rework=int(np.count_nonzero(prior_current_alpha & ~rework_allowed))
random_pixel_exact=bool(np.array_equal(pa[random_box[1]:random_box[3],random_box[0]:random_box[2]],fa[random_box[1]:random_box[3],random_box[0]:random_box[2]]))

pair_overlap=0
for i in range(len(localized_masks)):
    for j in range(i+1,len(localized_masks)):
        pair_overlap += int(np.count_nonzero(localized_masks[i]&localized_masks[j]))

row_pass=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in row_reports)
machine_pass=(row_pass and source_clean_outside_allowed==0 and current_clean_outside_allowed==0 and current_alpha_outside_allowed==0 and prior_current_outside_rework==0 and prior_current_alpha_outside_rework==0 and random_pixel_exact and pair_overlap==0)

# Evidence: focused readable region, per-card high zoom, raw and practical scales.
focus=(0,1450,1880,2048)
imgs=[]
for lab,im in [("SOURCE READABLE",src),("C117 PRIOR",prior),("VALIDATED CLEAN",clean),("B233 CURRENT",cur)]:
    imgs.append(panel(lab,im.crop(focus),940))
vstack([hstrip(imgs[:2]),hstrip(imgs[2:])]).save(out/"C2Q100_SOURCE_PRIOR_CLEAN_CURRENT_READABLE.jpg","JPEG",quality=95,subsampling=0)

raw_focus=(0,0,2048,650)
hstrip([panel("SOURCE RAW MIRROR_Y",src_raw.crop(raw_focus),1024),panel("B233 RAW MIRROR_Y",cur_raw.crop(raw_focus),1024)]).save(out/"C2Q100_SOURCE_CURRENT_RAW.jpg","JPEG",quality=95,subsampling=0)

card_sheets=[]
for key,b,n in cards[1:]:
    pad=12; x0,y0,x1,y1=b; crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    card_sheets.append(hstrip([
      panel("SRC "+key,src.crop(crop),560),
      panel("CLEAN "+key,clean.crop(crop),560),
      panel("PRIOR "+key,prior.crop(crop),560),
      panel("CURRENT "+key,cur.crop(crop),560),
    ]))
vstack(card_sheets).save(out/"C2Q100_MODE_CARD_CONTACTS.jpg","JPEG",quality=95,subsampling=0)

pr=[]
for pct in (100,50,25):
    sc=pct/100
    pair=[]
    for lab,im in [("SOURCE",src.crop(focus)),("CURRENT",cur.crop(focus))]:
        z=comp(im)
        z=z.resize((max(1,round(z.width*sc)),max(1,round(z.height*sc))),Image.Resampling.LANCZOS)
        pair.append(panel(f"{lab} {pct}%",z,max(600,z.width)))
    pr.append(hstrip(pair))
vstack(pr).save(out/"C2Q100_PRACTICAL_100_50_25.jpg","JPEG",quality=95,subsampling=0)

report={
 "schema_version":2,"role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "run":RUN,"queue_index":100,"asset":asset,"producer_run":"B233",
 "trigger":"PRE_INGAME_005_SOURCE_RELATIVE_PLACEMENT_FALSE_NEGATIVE",
 "source_sha256":SOURCE_SHA,"prior_c117_sha256":PRIOR_SHA,"candidate_sha256":CURRENT_SHA,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":source_commit,"url":source_url},
 "prior_candidate_git_commit":prior_commit,
 "independent_basis":"Fresh C downloads and decodes the pinned canonical source, recovers the exact prior C117 candidate by SHA, uses the C117/B30 validated clean plate only as reconstruction evidence, then independently derives all 19 source and current line footprints from SOURCE-vs-CLEAN and CURRENT-vs-CLEAN pixel deltas inside seven semantic card windows. Producer masks/bboxes/counters are not consumed.",
 "structure":sm,
 "rows":row_reports,
 "summary":{
   "bbox_size_positive_margin":f"{sum(1 for r in row_reports if r['containment']=='PASS' and r['size_ceiling']=='PASS' and r['positive_margin']=='PASS')}/19 PASS",
   "source_clean_changed_outside_19_derived_bboxes":source_clean_outside_allowed,
   "current_changed_outside_19_source_bboxes":current_clean_outside_allowed,
   "current_alpha_changed_outside_19_source_bboxes":current_alpha_outside_allowed,
   "prior_to_current_changed_outside_18_rework_bboxes":prior_current_outside_rework,
   "prior_to_current_alpha_changed_outside_18_rework_bboxes":prior_current_alpha_outside_rework,
   "random_row_pixel_exact_to_C117":random_pixel_exact,
   "localized_pair_overlap_pixels":pair_overlap,
   "header_128_exact_source_prior_current":sb[:128]==pb[:128]==cb[:128],
   "persisted_decode_authority":"PASS"
 },
 "coverage":{"semantic_groups":7,"physical_lines":19,"random_preserved":True,"mode_card_lines_reworked":18,"status":"PASS_ALL_19_ACCOUNTED"},
 "machine_status":"PASS" if machine_pass else "FAIL",
 "fresh_c_decision":"PENDING_CONTROLLER" if machine_pass else "REWORK_REQUIRED",
 "c3_required":True,
 "c3_reason":["PRE_INGAME_JPG_REJECTION","SOURCE_RELATIVE_PLACEMENT_FALSE_NEGATIVE","MULTILINE_TRANSFORMED_SMALL_TEXT","PRIOR_C117_VISUAL_FALSE_NEGATIVE"],
 "c3_machine_status":"PASS" if machine_pass else "BLOCKED_MACHINE_FAIL",
 "c3_visual_priorities":["source_relative_placement","slant_direction","clean_plate","source_style","line_hierarchy_scale","glyph_integrity","protected_separation","FLIP_Y_RAW_consistency","practical_scale","coverage"],
 "visual_evidence":[
   f"localization/graphics/role_C/{RUN}/C2Q100_SOURCE_PRIOR_CLEAN_CURRENT_READABLE.jpg",
   f"localization/graphics/role_C/{RUN}/C2Q100_MODE_CARD_CONTACTS.jpg",
   f"localization/graphics/role_C/{RUN}/C2Q100_SOURCE_CURRENT_RAW.jpg",
   f"localization/graphics/role_C/{RUN}/C2Q100_PRACTICAL_100_50_25.jpg",
 ],
 "controller_visual_qa":"PENDING_CONTROLLER",
 "c3_strict_decision":"PENDING_CONTROLLER" if machine_pass else "BLOCKED_MACHINE_FAIL",
 "pre_ingame_export":"BLOCKED_UNTIL_CONTROLLER_C3",
 "runtime_validation":"UNTESTED",
 "forbidden_domains_touched":[]
}
(out/"C2Q100_53CE39D5_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C2Q100_53CE39D5.json").write_text(json.dumps({
 "role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,"queue_index":100,"asset":"53CE39D5",
 "candidate_sha256":CURRENT_SHA,"machine_status":report["machine_status"],"c3_machine_status":report["c3_machine_status"],
 "report":f"localization/graphics/role_C/{RUN}/C2Q100_53CE39D5_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"machine_status":report["machine_status"],"summary":report["summary"],"coverage":report["coverage"]},ensure_ascii=False,indent=2))
if not machine_pass: raise SystemExit("C2 q100 machine QA failed closed")
