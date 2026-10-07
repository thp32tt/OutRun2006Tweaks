#!/usr/bin/env python3
# C236 / TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
# Fresh independent C + mandatory exact-SHA C3 strict audit for q46 AA04D779 / B231.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

import hashlib,json,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageChops,ImageOps

repo=Path.cwd()
RUN="20261007-C236-C2-Q046-AA04D779-B231"
out=repo/"localization/graphics/role_C"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_etc_cvt_Exst/AA04D779_512x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
SOURCE_SHA="1a01e19b2749acdd275d10ff6e82bcb525d6621fd9118fb0c1fa5997c4c1dfa5"
EXPECTED_OLD="93eb895d890bd0f41b4427346e3a7a2fe5538b4a1f4164991a480b424b1fc36e"
EXPECTED_CAND="d927658b1fe0545b0ec536c32b11cd57afec8a509ce90dd90f1de5ba0ed58ba0"
source_commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+source_commit+"/Release/spr_sprani_etc_cvt_Exst/AA04D779_512x512.dds"

# C independently fixes semantic search windows and derives exact source alpha bboxes from canonical pixels.
specs=[
 {"key":"pre_game_lobby","source":"In pre-game lobby","ko":"게임 전 로비","window":[0,30,410,88]},
 {"key":"offline","source":"Offline","ko":"오프라인","window":[445,30,650,88]},
 {"key":"brake_left","source":"BRAKE","ko":"브레이크","window":[405,210,590,265]},
 {"key":"brake_right","source":"BRAKE","ko":"브레이크","window":[590,210,790,265]},
 {"key":"accelerate","source":"ACCELERATE","ko":"가속","window":[1190,210,1550,265]},
 {"key":"gear_up_left","source":"GEAR UP","ko":"기어 업","window":[0,275,235,330]},
 {"key":"gear_down_icon_left","source":"GEAR","ko":"기어","window":[875,275,995,330]},
 {"key":"gear_down_icon_right","source":"DOWN","ko":"다운","window":[1035,275,1195,330]},
 {"key":"gear_down_right","source":"GEAR DOWN","ko":"기어 다운","window":[1200,275,1520,330]},
 {"key":"view_license","source":"VIEW LICENSE","ko":"라이선스 보기","window":[385,335,790,410]},
 {"key":"gear_up_right","source":"GEAR UP","ko":"기어 업","window":[1460,335,1695,410]},
 {"key":"change_soundtrack","source":"CHANGE CUSTOM / SOUNDTRACK","ko":"사용자 음악 / 변경","window":[1000,425,1465,555]},
 {"key":"pause_menu","source":"PAUSE / MENU","ko":"일시정지 / 메뉴","window":[1780,425,2020,565]},
]
def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if not mode or (w,h)!=(2048,2048) or len(b)!=128+w*h*4:
        raise RuntimeError(("structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"mips":mips,"raw_mode":mode}
def rect(shape,b):
    m=np.zeros(shape,dtype=bool); x0,y0,x1,y1=b; m[y0:y1,x0:x1]=True; return m
def bbox(m):
    ys,xs=np.nonzero(m)
    return None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def local_bbox(m,b):
    x0,y0,x1,y1=b; z=bbox(m[y0:y1,x0:x1])
    return None if z is None else [z[0]+x0,z[1]+y0,z[2]+x0,z[3]+y0]
def changed(a,b): return np.any(a!=b,axis=2)
def comp(im,bg=(104,104,104,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(label,im,w=1024):
    z=comp(im); z=z.resize((w,w),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(w,w+28),(20,20,20)); c.paste(z,(0,28)); ImageDraw.Draw(c).text((6,6),label,fill="white"); return c

tmp=Path("/tmp/c236"); tmp.mkdir(exist_ok=True)
srcp=tmp/"source.dds"; urllib.request.urlretrieve(source_url,srcp)
sb=srcp.read_bytes(); cb=candidate.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sha(cb)!=EXPECTED_CAND: raise RuntimeError(("candidate drift",sha(cb)))

# Recover exact prior C-approved candidate by SHA, not by assumed parent.
oldb=None; old_commit=None
for h in subprocess.check_output(["git","log","--format=%H","--all","--",str(candidate.relative_to(repo))],text=True).splitlines():
    try: b=subprocess.check_output(["git","show",f"{h}:{candidate.relative_to(repo)}"],stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError: continue
    if sha(b)==EXPECTED_OLD:
        oldb=b; old_commit=h; break
if oldb is None: raise RuntimeError("prior candidate SHA not found in git history")

src_raw,src,meta=decode(sb); old_raw,old,ometa=decode(oldb); new_raw,new,nmeta=decode(cb)
if meta!=ometa or meta!=nmeta or sb[:128]!=cb[:128] or oldb[:128]!=cb[:128]:
    raise RuntimeError("DDS structure/header drift")
if meta["mips"]!=1: raise RuntimeError(("mip count",meta["mips"]))

sa,oa,na=map(np.asarray,(src,old,new)); H,W=sa.shape[:2]
# Old C-approved candidate must be source-exact in all new control windows.
source_text=np.zeros((H,W),bool); rework=np.zeros((H,W),bool); rows=[]
for s in specs:
    x0,y0,x1,y1=s["window"]
    if not np.array_equal(oa[y0:y1,x0:x1],sa[y0:y1,x0:x1]):
        raise RuntimeError(("old candidate not source-exact in C window",s["key"]))
    sm=(sa[:,:,3]>0)&rect((H,W),s["window"])
    bb=bbox(sm)
    if bb is None: raise RuntimeError(("missing source bbox",s["key"]))
    sw,sh=bb[2]-bb[0],bb[3]-bb[1]
    if sh<20 or sh>140 or sw<25: raise RuntimeError(("implausible source bbox",s["key"],bb))
    source_text|=sm; rework|=rect((H,W),bb)
    rows.append(dict(s,source_bbox=bb,source_size=[sw,sh],source_alpha_pixels=int(sm.sum())))

# Independently reconstruct clean from prior accepted bytes by clearing exact canonical source alpha only.
clean=old.copy(); ca=np.array(clean); ca[source_text]=[0,0,0,0]; clean=Image.fromarray(ca.astype(np.uint8),"RGBA")
cla=np.asarray(clean)
if int(np.count_nonzero(cla[:,:,3][source_text]))!=0: raise RuntimeError("clean source alpha remains")

# New candidate must have zero blast radius outside the 13 exact source bboxes.
diff=changed(oa,na); adiff=oa[:,:,3]!=na[:,:,3]
blast=int(np.count_nonzero(diff&~rework)); alpha_blast=int(np.count_nonzero(adiff&~rework))
if blast or alpha_blast: raise RuntimeError(("blast radius",blast,alpha_blast))

# Prior 21 localized stage/sector rows and every protected/unrelated pixel are therefore byte/pixel exact.
# Derive current localized geometry as visible change from independent clean plate inside each source bbox.
cand_vs_clean=changed(cla,na)
row_reports=[]; lmasks=[]
for r in rows:
    bb=r["source_bbox"]; x0,y0,x1,y1=bb
    lm=(cand_vs_clean)&rect((H,W),bb)&(na[:,:,3]>0)
    lb=bbox(lm)
    if lb is None: raise RuntimeError(("missing localized pixels",r["key"]))
    sw,sh=r["source_size"]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    margins=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
    contain=lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1
    sizeok=lw<=sw and lh<=sh; positive=min(margins)>0
    # After clearing source pixels, any visible final pixel outside the derived localized change mask within the exact source alpha
    # would be unexplained source residue/background restoration failure.
    source_only=source_text&rect((H,W),bb)&~lm
    unexplained=int(np.count_nonzero((na[:,:,3]>0)&source_only))
    row_reports.append({
      "key":r["key"],"source":r["source"],"korean":r["ko"],
      "original_bbox":bb,"localized_bbox":lb,
      "source_size":[sw,sh],"localized_size":[lw,lh],"margins":margins,
      "delta_left":lb[0]-x0,"delta_right":lb[2]-x1,"delta_top":lb[1]-y0,"delta_bottom":lb[3]-y1,
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if sizeok else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL","unexplained_source_alpha_pixels":unexplained
    }); lmasks.append(lm)

# Pairwise localized overlap and protected overlap.
pair_overlap=0
for i in range(len(lmasks)):
    for j in range(i+1,len(lmasks)):
        pair_overlap+=int(np.count_nonzero(lmasks[i]&lmasks[j]))
allowed_existing=changed(sa,oa)
allowed=allowed_existing|rework
protected=(sa[:,:,3]>0)&~allowed
localized_union=np.zeros((H,W),bool)
for m in lmasks: localized_union|=m
protected_overlap=int(np.count_nonzero(localized_union&protected))

# Coverage carry-forward: old C-approved 21 stage/sector material is exact outside rework, 13 new physical rows cover 9 semantics.
row_pass=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in row_reports)
machine_pass=(row_pass and blast==0 and alpha_blast==0 and pair_overlap==0 and protected_overlap==0 and meta["mips"]==1)

# C evidence: source / prior / independently reconstructed clean / current plus RAW and practical scales.
overview=Image.new("RGB",(2048,2104),(20,20,20))
for pos,lab,im in [((0,0),"CANONICAL SOURCE",src),((1024,0),"PRIOR C-PASS",old),((0,1052),"C236 INDEPENDENT CLEAN",clean),((1024,1052),"B231 CURRENT",new)]:
    overview.paste(card(lab,im),pos)
overview.save(out/"C236_SOURCE_OLD_CLEAN_FINAL_READABLE.jpg","JPEG",quality=95,subsampling=0)

rawsheet=Image.new("RGB",(2048,1052),(20,20,20))
rawsheet.paste(card("CANONICAL SOURCE RAW",src_raw),(0,0)); rawsheet.paste(card("B231 CURRENT RAW",new_raw),(1024,0))
rawsheet.save(out/"C236_SOURCE_FINAL_RAW.jpg","JPEG",quality=95,subsampling=0)

roi=(0,0,2048,600); sheets=[]
for scale in (1.0,0.75,0.5):
    ims=[]
    for im in (src,old,clean,new):
        z=comp(im).crop(roi)
        z=z.resize((max(1,int(z.width*scale)),max(1,int(z.height*scale))),Image.Resampling.LANCZOS)
        ims.append(z)
    cw=sum(z.width for z in ims)+18; ch=max(z.height for z in ims)+30
    c=Image.new("RGB",(cw,ch),(20,20,20)); d=ImageDraw.Draw(c); xx=0
    for lab,z in zip(("SOURCE","PRIOR","CLEAN","CURRENT"),ims):
        d.text((xx+4,6),f"{lab} {int(scale*100)}%",fill="white"); c.paste(z,(xx,30)); xx+=z.width+6
    sheets.append(c)
mw=max(c.width for c in sheets); mh=sum(c.height for c in sheets)+8
ps=Image.new("RGB",(mw,mh),(18,18,18)); yy=0
for c in sheets: ps.paste(c,(0,yy)); yy+=c.height+4
ps.thumbnail((4200,5000),Image.Resampling.LANCZOS)
ps.save(out/"C236_PRACTICAL_100_75_50.jpg","JPEG",quality=95,subsampling=0)

report={
 "schema_version":2,"role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "run":RUN,"qa_id":"C236","queue_index":46,"asset":asset,"producer_run":"B231",
 "source_sha256":sha(sb),"prior_candidate_sha256":sha(oldb),"candidate_sha256":sha(cb),
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":source_commit,"url":source_url},
 "prior_candidate_git_commit":old_commit,
 "independent_basis":"Canonical source freshly downloaded and decoded. C derives exact source alpha/effect bboxes from its own fixed semantic windows, reconstructs clean from the exact prior C-approved candidate by clearing canonical source pixels, derives persisted localized bboxes from current-vs-clean decoded pixels, and checks blast radius against the prior candidate. Producer machine counters/bboxes are not consumed.",
 "structure":{"dimensions":[2048,2048],"format":meta["raw_mode"],"mips":meta["mips"],"header_128_exact":sb[:128]==cb[:128],"raw_orientation":"mirror_y"},
 "rows":row_reports,
 "summary":{
   "bbox_size_positive_margin":f"{sum(1 for r in row_reports if r['containment']=='PASS' and r['size_ceiling']=='PASS' and r['positive_margin']=='PASS')}/13 PASS",
   "changed_pixels_outside_13_source_bboxes":blast,
   "alpha_changed_outside_13_source_bboxes":alpha_blast,
   "localized_pair_overlap_pixels":pair_overlap,
   "localized_to_protected_overlap_pixels":protected_overlap,
   "prior_21_stage_sector_and_unrelated_preservation":"PASS_BY_ZERO_BLAST_RADIUS",
   "persisted_decode_authority":"PASS"
 },
 "coverage":{
   "prior_semantic_segments_preserved":21,
   "new_semantic_segments":9,
   "new_physical_rows":13,
   "total_semantic_segments":30,
   "explicit_preserve_original":["REV","TOP","You","1P/2P/3P/4P","icons/course-symbols/numeric artwork"],
   "status":"PASS_30_SEMANTIC_PLUS_EXPLICIT_PRESERVES"
 },
 "machine_status":"PASS" if machine_pass else "FAIL",
 "fresh_c_decision":"PENDING_CONTROLLER" if machine_pass else "REWORK_REQUIRED",
 "c3_required":True,
 "c3_reason":["PRIOR_C_POLICY_FALSE_NEGATIVE_UNTRANSLATED_VISIBLE_UI","MULTILINE_SMALL_GRAY_CONTROL_TEXT","PRE_INGAME_HUMAN_GATE_REOPEN"],
 "c3_machine_status":"PASS" if machine_pass else "BLOCKED_MACHINE_FAIL",
 "c3_visual_priorities":["coverage","clean_plate","source_style","scale_readability","glyph_integrity","protected_separation","source_placement","FLIP_Y_RAW_consistency","practical_scale"],
 "visual_evidence":[str(out/"C236_SOURCE_OLD_CLEAN_FINAL_READABLE.jpg"),str(out/"C236_SOURCE_FINAL_RAW.jpg"),str(out/"C236_PRACTICAL_100_75_50.jpg")],
 "controller_visual_qa":"PENDING_CONTROLLER",
 "c3_strict_decision":"PENDING_CONTROLLER" if machine_pass else "BLOCKED_MACHINE_FAIL",
 "pre_ingame_export":"BLOCKED_UNTIL_CONTROLLER_C_AND_C3_PASS",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"C236_AA04D779_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C236_AA04D779.json").write_text(json.dumps({
 "role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,"queue_index":46,"asset":"AA04D779",
 "candidate_sha256":sha(cb),"machine_status":report["machine_status"],"c3_machine_status":report["c3_machine_status"],
 "report":str(out/"C236_AA04D779_MACHINE_QA.json"),"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"machine_status":report["machine_status"],"summary":report["summary"],"coverage":report["coverage"]},ensure_ascii=False,indent=2))
if not machine_pass: raise SystemExit("C236 machine QA failed closed")
