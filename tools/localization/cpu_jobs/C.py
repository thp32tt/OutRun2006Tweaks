#!/usr/bin/env python3
# C242 C1 q49 BF3EE5C6 A136 fresh independent C + mandatory C3 evidence
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import os, json, hashlib, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
RUN="20261007-C242-C1-Q049-BF3EE5C6-A136"
asset=Path("textures/load/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds")
cand=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_A/20261006-A-USERREWORK136-BF3-SLANT/BF3EE5C6_HD_CLEAN_PLATE.png"
producer_report=repo/"localization/graphics/role_A/20261006-A-USERREWORK136-BF3-SLANT/A136_USER_REWORK_BF3_BF3EE5C6_REPORT.json"
SOURCE_SHA="b5c0a868add94395745af1827c21ddddd178439b5b4614fbadd8f0e4135a9887"
PRIOR_SHA="3d5d132b8aada285bd6efebdb2d8cd9dd3f6625f2f8b4ca26420cd26712efb37"
CURRENT_SHA="a7eb06e2441956f4418f4cc95da52313696bc13d7864f7c7f76c8efdf909f85d"
SRC_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SRC_URL=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{SRC_COMMIT}/Release/spr_sprani_etc_cvt_Exst/BF3EE5C6_512x512.dds"
ROWS=[
 ("rank_stage",(12,163,615,245),False),("normal",(729,192,1012,251),False),
 ("tuned_a",(1116,193,1342,251),False),("tuned_b",(1476,193,1702,251),False),
 ("top_ghost",(572,272,1374,392),True),("double",(0,400,500,528),False),
 ("strike",(548,392,1000,528),False),("goal",(600,552,1016,680),True),
 ("spare",(1104,544,1520,688),False),("shift_up",(158,710,900,878),False),
 ("rank",(1068,756,1413,882),False),("turkey",(1572,992,2012,1140),False),
 ("go",(25,1161,805,1517),False),
]

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6],pf[7])
    if masks[:3]==(0xff,0xff00,0xff0000): mode="RGBA"
    elif masks[:3]==(0xff0000,0xff00,0xff): mode="BGRA"
    else: raise RuntimeError(("unsupported masks",masks))
    if len(b)!=128+w*h*4: raise RuntimeError(("unexpected payload",w,h,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return raw,readable,{"w":w,"h":h,"pitch":pitch,"depth":depth,"mips":mips,"mode":mode,"masks":masks}
def dm(a,b): return np.any(np.asarray(a)!=np.asarray(b),axis=2)
def adm(a,b): return np.asarray(a)[:,:,3]!=np.asarray(b)[:,:,3]
def bbox(m):
    ys,xs=np.where(m)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def rect(shape,bb):
    m=np.zeros(shape,bool);x1,y1,x2,y2=bb;m[y1:y2,x1:x2]=True;return m
def history_bytes(target_sha,path):
    commits=subprocess.check_output(["git","log","--format=%H","--",str(path)],text=True).splitlines()
    for c in commits:
        try: b=subprocess.check_output(["git","show",f"{c}:{path}"],stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError: continue
        if sha(b)==target_sha:return b,{"commit":c,"path":str(path)}
    raise RuntimeError(("history sha not found",target_sha,str(path)))
def comp(im):
    z=Image.new("RGBA",im.size,(92,92,92,255));z.alpha_composite(im);return z.convert("RGB")
def lab(im,t):
    o=Image.new("RGB",(im.width,im.height+28),(18,18,18));o.paste(im,(0,28))
    ImageDraw.Draw(o).text((5,6),t,fill="white",font=ImageFont.load_default());return o

cb=cand.read_bytes()
if sha(cb)!=CURRENT_SHA: raise RuntimeError(("candidate drift",sha(cb)))
req=urllib.request.Request(SRC_URL,headers={"User-Agent":"OutRun-C242"})
with urllib.request.urlopen(req,timeout=90) as r: sb=r.read()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
pb,prior_prov=history_bytes(PRIOR_SHA,Path("localization/graphics/hd_candidates")/asset)
sraw,src,sm=decode(sb); praw,prior,pm=decode(pb); craw,cur,cm=decode(cb)
if sm!=pm or sm!=cm or (sm["w"],sm["h"],sm["mips"])!=(2048,2048,1): raise RuntimeError(("structure mismatch",sm,pm,cm))
if cb[:128]!=sb[:128] or pb[:128]!=sb[:128]: raise RuntimeError("header mismatch")
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=src.size: raise RuntimeError(("clean size mismatch",clean.size,src.size))
pr=json.loads(producer_report.read_text(encoding="utf-8"))
if pr.get("candidate_sha256")!=CURRENT_SHA or pr.get("source_sha256")!=SOURCE_SHA: raise RuntimeError("producer SHA drift")

shape=(2048,2048)
union=np.zeros(shape,bool); rework=np.zeros(shape,bool)
loc_masks={}; row_results=[]
for key,bb,preserved in ROWS:
    rm=rect(shape,bb);union|=rm
    if not preserved: rework|=rm
    srcd=dm(src,clean)&rm
    locd=dm(cur,clean)&rm
    sbb=bbox(srcd); lbb=bbox(locd)
    if sbb!=list(bb): raise RuntimeError(("independent source bbox mismatch",key,sbb,list(bb)))
    if lbb is None: raise RuntimeError(("missing localized pixels",key))
    sw,sh=sbb[2]-sbb[0],sbb[3]-sbb[1]; lw,lh=lbb[2]-lbb[0],lbb[3]-lbb[1]
    margins=[lbb[0]-sbb[0],sbb[2]-lbb[2],lbb[1]-sbb[1],sbb[3]-lbb[3]]
    if not(lbb[0]>=sbb[0] and lbb[1]>=sbb[1] and lbb[2]<=sbb[2] and lbb[3]<=sbb[3] and lw<=sw and lh<=sh and min(margins)>0):
        raise RuntimeError(("containment/size/margin fail",key,sbb,lbb,margins))
    loc_masks[key]=locd
    row_results.append({"key":key,"preserved_from_input":preserved,"source_bbox":sbb,"localized_bbox":lbb,
      "source_size":[sw,sh],"localized_size":[lw,lh],"margins_lrtb":margins,
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

sc=dm(src,clean); cc=dm(cur,clean); src_cur=dm(src,cur); prior_cur=dm(prior,cur)
machine={
 "source_to_clean_changed_outside_13_source_bboxes":int(np.count_nonzero(sc&~union)),
 "source_to_clean_alpha_changed_outside_13_source_bboxes":int(np.count_nonzero(adm(src,clean)&~union)),
 "current_to_clean_changed_outside_13_source_bboxes":int(np.count_nonzero(cc&~union)),
 "current_to_clean_alpha_changed_outside_13_source_bboxes":int(np.count_nonzero(adm(cur,clean)&~union)),
 "source_to_current_changed_outside_13_source_bboxes":int(np.count_nonzero(src_cur&~union)),
 "prior_to_current_changed_outside_11_reworked_bboxes":int(np.count_nonzero(prior_cur&~rework)),
}
if any(machine.values()): raise RuntimeError(("scope fail",machine))
for key,bb,preserved in ROWS:
    if preserved:
        n=int(np.count_nonzero(prior_cur&rect(shape,bb)));machine[f"preserved_{key}_pixel_diff_vs_input"]=n
        if n: raise RuntimeError(("preserved row drift",key,n))

ks=[x[0] for x in ROWS]; ovsum=0; touchsum=0
for i in range(len(ks)):
    for j in range(i+1,len(ks)):
        a,b=loc_masks[ks[i]],loc_masks[ks[j]]
        ovsum+=int(np.count_nonzero(a&b))
        touchsum+=int(np.count_nonzero(binary_dilation(a,iterations=1)&b))
if ovsum or touchsum: raise RuntimeError(("pair overlap/touch",ovsum,touchsum))
machine.update({
 "localized_pair_overlap_pixels":ovsum,"localized_pair_touch1_pixels":touchsum,
 "header_128_exact_source_prior_current":True,"dimensions":[2048,2048],"mip_count":1,"raw_mode":sm["mode"]
})

out=repo/"localization/graphics/role_C"/RUN;out.mkdir(parents=True,exist_ok=True)
cards=[]
for t,im in [("EN SOURCE",src),("A136 CLEAN",clean),("A82 INPUT",prior),("A136 CURRENT",cur)]:
    cards.append(lab(comp(im).resize((720,720),Image.Resampling.LANCZOS),t+" READABLE/FLIP-Y"))
sheet=Image.new("RGB",(2880,748),(10,10,10));x=0
for c in cards:sheet.paste(c,(x,0));x+=c.width
sheet.save(out/"C242_FULL_SOURCE_CLEAN_INPUT_CURRENT_READABLE.jpg","JPEG",quality=94,subsampling=0)

rawcards=[]
for t,im in [("EN SOURCE RAW",sraw),("A82 INPUT RAW",praw),("A136 CURRENT RAW",craw)]:
    rawcards.append(lab(comp(im).resize((700,700),Image.Resampling.LANCZOS),t))
rawsheet=Image.new("RGB",(2100,728),(10,10,10));x=0
for c in rawcards:rawsheet.paste(c,(x,0));x+=c.width
rawsheet.save(out/"C242_FULL_RAW_SOURCE_INPUT_CURRENT.jpg","JPEG",quality=94,subsampling=0)

strips=[]
for key,bb,preserved in ROWS:
    x1,y1,x2,y2=bb;pad=16;crop=(max(0,x1-pad),max(0,y1-pad),min(2048,x2+pad),min(2048,y2+pad))
    rowcards=[]
    scale=2 if (crop[2]-crop[0])<=820 else 1
    for t,im in [("SOURCE",src),("CLEAN",clean),("INPUT",prior),("CURRENT",cur)]:
        z=comp(im.crop(crop))
        if scale==2:z=z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST)
        rowcards.append(lab(z,key+" "+t+(" PRESERVED" if preserved else "")))
    w=sum(c.width for c in rowcards);h=max(c.height for c in rowcards)
    rs=Image.new("RGB",(w,h),(8,8,8));xx=0
    for c in rowcards:rs.paste(c,(xx,0));xx+=c.width
    strips.append(rs)
contacts=Image.new("RGB",(max(x.width for x in strips),sum(x.height for x in strips)),(8,8,8));yy=0
for s in strips:contacts.paste(s,(0,yy));yy+=s.height
contacts.save(out/"C242_13ROW_SOURCE_CLEAN_INPUT_CURRENT_HIGHZOOM.jpg","JPEG",quality=95,subsampling=0)

blocks=[]
for pct in (50,25):
    sz=(round(2048*pct/100),round(2048*pct/100))
    a=lab(comp(src).resize(sz,Image.Resampling.LANCZOS),f"SOURCE {pct}%")
    b=lab(comp(cur).resize(sz,Image.Resampling.LANCZOS),f"CURRENT {pct}%")
    z=Image.new("RGB",(a.width+b.width,max(a.height,b.height)),(8,8,8));z.paste(a,(0,0));z.paste(b,(a.width,0));blocks.append(z)
prac=Image.new("RGB",(max(x.width for x in blocks),sum(x.height for x in blocks)),(8,8,8));yy=0
for z in blocks:prac.paste(z,(0,yy));yy+=z.height
prac.save(out/"C242_PRACTICAL_50_25.jpg","JPEG",quality=94,subsampling=0)

report={
 "schema_version":2,"run":RUN,"role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":49,"asset":asset.as_posix(),"regressions":["IGR-008","IGR-011"],"priority":"P0/P1",
 "producer_run":"A136","source_sha256":SOURCE_SHA,
 "source_provenance":{"repo":"Sonic-TV/OR2006Sprites","commit":SRC_COMMIT,"url":SRC_URL},
 "prior_candidate_sha256":PRIOR_SHA,"prior_provenance":prior_prov,"candidate_sha256":CURRENT_SHA,
 "rows":row_results,"machine_qa":machine,
 "fresh_c_machine_status":"PASS_PENDING_CONTROLLER_VISUAL",
 "mandatory_c3":"REQUIRED_USER_INGAME_REGRESSION_PLUS_PRIOR_STYLE_SLANT_FALSE_NEGATIVE",
 "controller_visual_qa":"PENDING","c3_strict_decision":"PENDING_CONTROLLER",
 "pre_ingame_export":"BLOCKED_UNTIL_CONTROLLER_C3",
 "ingame_backlog_closure":"BLOCKED_PENDING_NEW_ACTUAL_INGAME_RETEST",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[],
 "visual_evidence":[
   f"localization/graphics/role_C/{RUN}/C242_FULL_SOURCE_CLEAN_INPUT_CURRENT_READABLE.jpg",
   f"localization/graphics/role_C/{RUN}/C242_FULL_RAW_SOURCE_INPUT_CURRENT.jpg",
   f"localization/graphics/role_C/{RUN}/C242_13ROW_SOURCE_CLEAN_INPUT_CURRENT_HIGHZOOM.jpg",
   f"localization/graphics/role_C/{RUN}/C242_PRACTICAL_50_25.jpg"
 ]
}
(out/"C242_BF3EE5C6_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
(wr/"C242_BF3EE5C6.json").write_text(json.dumps({
 "run":RUN,"role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":49,"candidate_sha256":CURRENT_SHA,"machine_status":"PASS_PENDING_CONTROLLER_VISUAL",
 "report":f"localization/graphics/role_C/{RUN}/C242_BF3EE5C6_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"queue_index":49,"candidate_sha256":CURRENT_SHA,"rows":len(row_results),"machine":machine,"status":"PASS_PENDING_CONTROLLER_VISUAL"},ensure_ascii=False,indent=2))
