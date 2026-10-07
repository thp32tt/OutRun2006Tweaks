#!/usr/bin/env python3
# C2 q100 53CE39D5 / B233 fresh independent C + mandatory exact-SHA C3 retry.
# TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib, json, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw

repo=Path.cwd()
RUN="20261007-C2-Q100-53CE39D5-B233-FRESH-C3-R2"
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

# Stable semantic/card mapping from prior accepted C117 source identification.
# Fresh C re-derives exact pixel bboxes from SOURCE-vs-CLEAN / CURRENT-vs-CLEAN; it does not consume producer masks/bboxes.
line_specs=[
 ("random",1,"랜덤",(1120,0,1480,125)),
 ("time_attack_or2",1,"타임 어택",(0,1640,370,1719)),
 ("time_attack_or2",2,"모드",(0,1719,370,1760)),
 ("time_attack_or2",3,"아웃런2",(0,1760,370,1825)),
 ("heart_attack_or2",1,"하트 어택",(380,1640,740,1719)),
 ("heart_attack_or2",2,"모드",(380,1719,740,1760)),
 ("heart_attack_or2",3,"아웃런2",(380,1760,740,1825)),
 ("outrun_or2",1,"아웃런",(750,1630,1080,1687)),
 ("outrun_or2",2,"모드",(750,1687,1080,1728)),
 ("outrun_or2",3,"아웃런2",(750,1728,1080,1795)),
 ("time_attack_special",1,"타임 어택",(1110,1545,1465,1607)),
 ("time_attack_special",2,"모드",(1110,1607,1465,1648)),
 ("time_attack_special",3,"스페셜 투어",(1110,1648,1465,1705)),
 ("heart_attack_special",1,"하트 어택",(1470,1495,1840,1559)),
 ("heart_attack_special",2,"모드",(1470,1559,1840,1600)),
 ("heart_attack_special",3,"스페셜 투어",(1470,1600,1840,1670)),
 ("outrun_special",1,"아웃런",(1020,1835,1360,1895)),
 ("outrun_special",2,"모드",(1020,1895,1360,1936)),
 ("outrun_special",3,"스페셜 투어",(1020,1936,1360,2010)),
]
view_cards=[
 ("time_attack_or2",(0,1630,370,1830)),
 ("heart_attack_or2",(380,1630,740,1830)),
 ("outrun_or2",(750,1615,1080,1810)),
 ("time_attack_special",(1110,1535,1465,1710)),
 ("heart_attack_special",(1470,1485,1840,1680)),
 ("outrun_special",(1020,1820,1360,2020)),
]

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
    for c in subprocess.check_output(["git","log","--all","--format=%H","--",path],text=True).splitlines():
        try: b=subprocess.check_output(["git","show",f"{c}:{path}"],stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError: continue
        if sha(b)==target_sha: return b,c
    raise RuntimeError("exact prior candidate not found: "+target_sha)
def comp(im,bg=(102,102,102,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def panel(label,im,target_w=900):
    z=comp(im)
    if z.width!=target_w:
        nh=max(1,round(z.height*target_w/z.width)); z=z.resize((target_w,nh),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(z.width,z.height+28),(20,20,20)); c.paste(z,(0,28)); ImageDraw.Draw(c).text((6,6),label,fill="white"); return c
def hstrip(xs):
    o=Image.new("RGB",(sum(x.width for x in xs),max(x.height for x in xs)),(18,18,18)); xx=0
    for x in xs:o.paste(x,(xx,0));xx+=x.width
    return o
def vstack(xs):
    o=Image.new("RGB",(max(x.width for x in xs),sum(x.height for x in xs)),(18,18,18)); yy=0
    for x in xs:o.paste(x,(0,yy));yy+=x.height
    return o

tmp=Path("/tmp/c2q100r2"); tmp.mkdir(exist_ok=True)
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
sa,pa,ca,fa=map(np.asarray,(src,prior,clean,cur)); H,W=sa.shape[:2]

source_clean=changed(sa,ca)
prior_clean=changed(pa,ca)
current_clean=changed(fa,ca)
prior_current=changed(pa,fa)
prior_current_alpha=pa[:,:,3]!=fa[:,:,3]

semantic_windows=np.zeros((H,W),bool)
for _,_,_,win in line_specs: semantic_windows |= rect((H,W),win)
clean_diff_outside_semantic_windows=int(np.count_nonzero(source_clean & ~semantic_windows))
if clean_diff_outside_semantic_windows:
    raise RuntimeError(("clean diff outside semantic windows",clean_diff_outside_semantic_windows))

allowed=np.zeros((H,W),bool); rework_allowed=np.zeros((H,W),bool)
row_reports=[]; current_line_masks=[]
for key,line,ko,win in line_specs:
    wmask=rect((H,W),win)
    ob=bbox(source_clean & wmask)
    pbbox=bbox(prior_clean & wmask)
    lb=bbox(current_clean & wmask)
    if ob is None or pbbox is None or lb is None:
        raise RuntimeError(("missing line bbox",key,line,ob,pbbox,lb))
    allowed |= rect((H,W),ob)
    if key!="random": rework_allowed |= rect((H,W),ob)
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    contain=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
    sizeok=lw<=sw and lh<=sh; positive=min(margins)>0
    lm=current_clean & rect((H,W),lb); current_line_masks.append(lm)
    row_reports.append({
      "target":key,"line_index":line,"korean":ko,
      "original_bbox":ob,"prior_localized_bbox":pbbox,"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lw,lh],
      "delta_left":lb[0]-ob[0],"delta_right":lb[2]-ob[2],
      "delta_top":lb[1]-ob[1],"delta_bottom":lb[3]-ob[3],
      "margins":margins,
      "containment":"PASS" if contain else "FAIL",
      "size_ceiling":"PASS" if sizeok else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL",
    })

if len(row_reports)!=19: raise RuntimeError(("row count",len(row_reports)))
source_clean_outside_allowed=int(np.count_nonzero(source_clean & ~allowed))
current_clean_outside_allowed=int(np.count_nonzero(current_clean & ~allowed))
current_alpha_outside_allowed=int(np.count_nonzero((ca[:,:,3]!=fa[:,:,3]) & ~allowed))
prior_current_outside_rework=int(np.count_nonzero(prior_current & ~rework_allowed))
prior_current_alpha_outside_rework=int(np.count_nonzero(prior_current_alpha & ~rework_allowed))

random_ob=row_reports[0]["original_bbox"]
random_exact=bool(np.array_equal(pa[random_ob[1]:random_ob[3],random_ob[0]:random_ob[2]],fa[random_ob[1]:random_ob[3],random_ob[0]:random_ob[2]]))
pair_overlap=0
for i in range(len(current_line_masks)):
    for j in range(i+1,len(current_line_masks)):
        pair_overlap += int(np.count_nonzero(current_line_masks[i]&current_line_masks[j]))

row_pass=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in row_reports)
machine_pass=(row_pass and source_clean_outside_allowed==0 and current_clean_outside_allowed==0 and current_alpha_outside_allowed==0 and prior_current_outside_rework==0 and prior_current_alpha_outside_rework==0 and random_exact and pair_overlap==0)

focus=(0,1450,1880,2048)
views=[panel(lab,im.crop(focus),940) for lab,im in [("SOURCE READABLE",src),("C117 PRIOR",prior),("VALIDATED CLEAN",clean),("B233 CURRENT",cur)]]
vstack([hstrip(views[:2]),hstrip(views[2:])]).save(out/"C2Q100_SOURCE_PRIOR_CLEAN_CURRENT_READABLE.jpg","JPEG",quality=95,subsampling=0)

raw_focus=(0,0,2048,650)
hstrip([panel("SOURCE RAW MIRROR_Y",src_raw.crop(raw_focus),1024),panel("B233 RAW MIRROR_Y",cur_raw.crop(raw_focus),1024)]).save(out/"C2Q100_SOURCE_CURRENT_RAW.jpg","JPEG",quality=95,subsampling=0)

contacts=[]
for key,b in view_cards:
    x0,y0,x1,y1=b; crop=(max(0,x0-12),max(0,y0-12),min(W,x1+12),min(H,y1+12))
    contacts.append(hstrip([panel("SRC "+key,src.crop(crop),560),panel("CLEAN "+key,clean.crop(crop),560),panel("PRIOR "+key,prior.crop(crop),560),panel("CURRENT "+key,cur.crop(crop),560)]))
vstack(contacts).save(out/"C2Q100_MODE_CARD_CONTACTS.jpg","JPEG",quality=95,subsampling=0)

pr=[]
for pct in (100,50,25):
    sc=pct/100; pair=[]
    for lab,im in [("SOURCE",src.crop(focus)),("CURRENT",cur.crop(focus))]:
        z=comp(im); z=z.resize((max(1,round(z.width*sc)),max(1,round(z.height*sc))),Image.Resampling.LANCZOS)
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
 "independent_basis":"Fresh C downloads/decodes pinned source, recovers exact prior C117 bytes by SHA, and uses only the previously validated B30 clean plate plus stable semantic line windows. Exact 19 source/current pixel bboxes are re-derived from SOURCE-vs-CLEAN and CURRENT-vs-CLEAN; producer masks, producer bbox values and producer counters are not consumed.",
 "structure":sm,"rows":row_reports,
 "summary":{
   "bbox_size_positive_margin":f"{sum(1 for r in row_reports if r['containment']=='PASS' and r['size_ceiling']=='PASS' and r['positive_margin']=='PASS')}/19 PASS",
   "source_clean_changed_outside_19_derived_bboxes":source_clean_outside_allowed,
   "current_changed_outside_19_source_bboxes":current_clean_outside_allowed,
   "current_alpha_changed_outside_19_source_bboxes":current_alpha_outside_allowed,
   "prior_to_current_changed_outside_18_rework_bboxes":prior_current_outside_rework,
   "prior_to_current_alpha_changed_outside_18_rework_bboxes":prior_current_alpha_outside_rework,
   "random_row_pixel_exact_to_C117":random_exact,
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
 "visual_evidence":[f"localization/graphics/role_C/{RUN}/C2Q100_SOURCE_PRIOR_CLEAN_CURRENT_READABLE.jpg",f"localization/graphics/role_C/{RUN}/C2Q100_MODE_CARD_CONTACTS.jpg",f"localization/graphics/role_C/{RUN}/C2Q100_SOURCE_CURRENT_RAW.jpg",f"localization/graphics/role_C/{RUN}/C2Q100_PRACTICAL_100_50_25.jpg"],
 "controller_visual_qa":"PENDING_CONTROLLER","c3_strict_decision":"PENDING_CONTROLLER" if machine_pass else "BLOCKED_MACHINE_FAIL",
 "pre_ingame_export":"BLOCKED_UNTIL_CONTROLLER_C3","runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"C2Q100_53CE39D5_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C2Q100_53CE39D5.json").write_text(json.dumps({"role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,"queue_index":100,"asset":"53CE39D5","candidate_sha256":CURRENT_SHA,"machine_status":report["machine_status"],"c3_machine_status":report["c3_machine_status"],"report":f"localization/graphics/role_C/{RUN}/C2Q100_53CE39D5_MACHINE_QA.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"machine_status":report["machine_status"],"summary":report["summary"],"coverage":report["coverage"]},ensure_ascii=False,indent=2))
if not machine_pass: raise SystemExit("C2 q100 machine QA failed closed")
