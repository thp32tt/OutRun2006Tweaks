#!/usr/bin/env python3
# C243 C1 q51 FF2462BB A163R fresh independent C + mandatory C3
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import os, io, json, hashlib, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
RUN="20261007-C243-C1-Q051-FF2462BB-A163R"
asset=Path("textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds")
candidate=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_A/20261004-A-RECOVERY01/FF2462BB_CLEAN_PLATE.png"
producer_report=repo/"localization/graphics/role_A/20261007-A163R-Q051-FF2462BB-C239-STYLE-REPAIR/A163R_FF2462BB_REPORT.json"

SOURCE_SHA="5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67"
PRE_A144_SHA="4fff8c59a44a1b7d03cee192124915f87eb73b3988c7673feb3228785ce67726"
A163_REJECTED_SHA="16ed98f52c2505cf32304eb2b61aa15491de87e78e9b11812c7add3c6fa3b112"
CURRENT_SHA="0dccb6318fafa20725427227fddf00c451bfdab814de5dc2da497d79d13b862e"
SRC_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SRC_URL=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{SRC_COMMIT}/Release/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"
TARGET=(3002,1405,3512,1566)
TOP=(3002,1405,3512,1486)
BOTTOM=(3002,1486,3512,1566)

def sha(b): return hashlib.sha256(b).hexdigest()
def decode_rgba32(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6],pf[7])
    if masks[:3]==(0xff,0xff00,0xff0000): mode="RGBA"
    elif masks[:3]==(0xff0000,0xff00,0xff): mode="BGRA"
    else: raise RuntimeError(("unsupported masks",masks))
    if len(b)!=128+w*h*4: raise RuntimeError(("payload mismatch",w,h,len(b)))
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
def hist(target_sha,path):
    for c in subprocess.check_output(["git","log","--format=%H","--",str(path)],text=True).splitlines():
        try:b=subprocess.check_output(["git","show",f"{c}:{path}"],stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:continue
        if sha(b)==target_sha:return b,{"commit":c,"path":str(path)}
    raise RuntimeError(("history sha not found",target_sha,str(path)))
def comp(im,bg=(82,82,82,255)):
    z=Image.new("RGBA",im.size,bg);z.alpha_composite(im);return z.convert("RGB")
def lab(im,t):
    o=Image.new("RGB",(im.width,im.height+28),(18,18,18));o.paste(im,(0,28))
    ImageDraw.Draw(o).text((6,6),t,fill="white",font=ImageFont.load_default());return o

cb=candidate.read_bytes()
if sha(cb)!=CURRENT_SHA: raise RuntimeError(("candidate drift",sha(cb),CURRENT_SHA))
req=urllib.request.Request(SRC_URL,headers={"User-Agent":"OutRun-C243"})
with urllib.request.urlopen(req,timeout=90) as r: sb=r.read()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb),SOURCE_SHA))
preb,preprov=hist(PRE_A144_SHA,Path("localization/graphics/hd_candidates")/asset)
rejb,rejprov=hist(A163_REJECTED_SHA,Path("localization/graphics/hd_candidates")/asset)

sraw,src,sm=decode_rgba32(sb); preraw,pre,pm=decode_rgba32(preb); rejraw,rej,rm=decode_rgba32(rejb); craw,cur,cm=decode_rgba32(cb)
if sm!=pm or sm!=rm or sm!=cm or (sm["w"],sm["h"],sm["mips"])!=(4096,2048,1):
    raise RuntimeError(("structure mismatch",sm,pm,rm,cm))
if not (cb[:128]==sb[:128]==preb[:128]==rejb[:128]): raise RuntimeError("header mismatch")
if not clean_path.exists(): raise RuntimeError("verified clean plate missing")
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=(4096,2048): raise RuntimeError(("clean size",clean.size))
pr=json.loads(producer_report.read_text(encoding="utf-8"))
if pr.get("candidate_sha256")!=CURRENT_SHA or pr.get("source_sha256")!=SOURCE_SHA:
    raise RuntimeError("producer report SHA drift")

shape=(2048,4096)
tm=rect(shape,TARGET); topm=rect(shape,TOP); botm=rect(shape,BOTTOM)

# Resolve clean orientation independently. A_RECOVERY01 clean plate may be stored readable or raw;
# choose the view whose SOURCE-vs-CLEAN target diff exactly occupies the known English target.
opts=[]
for name,sv in [("READABLE",src),("RAW",sraw)]:
    d=dm(sv,clean)&tm
    opts.append((name,bbox(d),int(np.count_nonzero(d))))
match=[o for o in opts if o[1] is not None and o[1][0]>=TARGET[0] and o[1][1]>=TARGET[1] and o[1][2]<=TARGET[2] and o[1][3]<=TARGET[3]]
if not match: raise RuntimeError(("clean orientation unresolved",opts))
clean_frame=match[0][0]
source_view=src if clean_frame=="READABLE" else sraw
current_view=cur if clean_frame=="READABLE" else craw
pre_view=pre if clean_frame=="READABLE" else preraw
rej_view=rej if clean_frame=="READABLE" else rejraw

# Independently derive source and current target footprints against verified clean.
source_diff=dm(source_view,clean)
current_diff=dm(current_view,clean)
rows=[]
for key,box,mask in [("top",TOP,topm),("bottom",BOTTOM,botm)]:
    sbb=bbox(source_diff&mask); lbb=bbox(current_diff&mask)
    if sbb is None or lbb is None: raise RuntimeError(("missing row diff",key,sbb,lbb))
    sw,sh=sbb[2]-sbb[0],sbb[3]-sbb[1];lw,lh=lbb[2]-lbb[0],lbb[3]-lbb[1]
    margins=[lbb[0]-sbb[0],sbb[2]-lbb[2],lbb[1]-sbb[1],sbb[3]-lbb[3]]
    contain=(lbb[0]>=sbb[0] and lbb[1]>=sbb[1] and lbb[2]<=sbb[2] and lbb[3]<=sbb[3])
    sizeok=(lw<=sw and lh<=sh); pos=min(margins)>0
    if not(contain and sizeok and pos): raise RuntimeError(("bbox/size/margin fail",key,sbb,lbb,margins))
    rows.append({"line":key,"source_bbox":sbb,"localized_bbox":lbb,"source_size":[sw,sh],"localized_size":[lw,lh],"margins_lrtb":margins,"containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})

pre_cur=dm(pre,cur); pre_cur_a=adm(pre,cur)
rej_cur=dm(rej,cur)
machine={
 "clean_frame":clean_frame,
 "source_clean_target_bbox":bbox(source_diff&tm),
 "current_clean_target_bbox":bbox(current_diff&tm),
 "pre_a144_to_current_changed_pixels_outside_true_target":int(np.count_nonzero(pre_cur&~tm)),
 "pre_a144_to_current_alpha_changed_outside_true_target":int(np.count_nonzero(pre_cur_a&~tm)),
 "a163_rejected_to_current_changed_pixels_outside_true_target":int(np.count_nonzero(rej_cur&~tm)),
 "source_clean_changed_pixels_in_true_target":int(np.count_nonzero(source_diff&tm)),
 "current_clean_changed_pixels_in_true_target":int(np.count_nonzero(current_diff&tm)),
 "header_128_exact_source_pre_rejected_current":True,
 "dimensions":[4096,2048],"mip_count":1,"raw_mode":sm["mode"],
}
if machine["pre_a144_to_current_changed_pixels_outside_true_target"] or machine["pre_a144_to_current_alpha_changed_outside_true_target"] or machine["a163_rejected_to_current_changed_pixels_outside_true_target"]:
    raise RuntimeError(("blast radius fail",machine))

# Wrong A144 insertion was outside this true target; exact pre-A144 equality outside target proves restoration.
machine["wrong_a144_insertion_exactly_restored"]="PASS_BY_PRE_A144_EXACT_OUTSIDE_TRUE_TARGET"

# C239 target-mismatch regression: current text must exist only in the corrected target relative to pre-A144.
if int(np.count_nonzero(pre_cur&tm))==0: raise RuntimeError("no material target repair")
machine["pre_a144_to_current_changed_pixels_inside_true_target"]=int(np.count_nonzero(pre_cur&tm))

out=repo/"localization/graphics/role_C"/RUN;out.mkdir(parents=True,exist_ok=True)
# Target high zoom source/clean/pre/A163-rejected/current in readable frame.
crop=(2940,1360,3570,1610)
cards=[]
for t,im in [("EN SOURCE",src),("VERIFIED CLEAN",clean if clean_frame=="READABLE" else clean.transpose(Image.Transpose.FLIP_TOP_BOTTOM)),("PRE-A144",pre),("A163 STYLE-REJECTED",rej),("A163R CURRENT",cur)]:
    z=comp(im.crop(crop)).resize(((crop[2]-crop[0])*2,(crop[3]-crop[1])*2),Image.Resampling.NEAREST)
    cards.append(lab(z,t+" READABLE"))
sheet=Image.new("RGB",(sum(c.width for c in cards),max(c.height for c in cards)),(10,10,10));x=0
for c in cards:sheet.paste(c,(x,0));x+=c.width
sheet.save(out/"C243_TARGET_SOURCE_CLEAN_PRE_REJECTED_CURRENT_HIGHZOOM.jpg","JPEG",quality=96,subsampling=0)

# Raw exact target mapping.
raw_target=(TARGET[0],2048-TARGET[3],TARGET[2],2048-TARGET[1])
rcrop=(raw_target[0]-62,raw_target[1]-45,raw_target[2]+58,raw_target[3]+45)
rawcards=[]
for t,im in [("EN SOURCE RAW",sraw),("PRE-A144 RAW",preraw),("A163 REJECTED RAW",rejraw),("A163R CURRENT RAW",craw)]:
    z=comp(im.crop(rcrop)).resize(((rcrop[2]-rcrop[0])*2,(rcrop[3]-rcrop[1])*2),Image.Resampling.NEAREST)
    rawcards.append(lab(z,t))
rs=Image.new("RGB",(sum(c.width for c in rawcards),max(c.height for c in rawcards)),(10,10,10));x=0
for c in rawcards:rs.paste(c,(x,0));x+=c.width
rs.save(out/"C243_TARGET_RAW_SOURCE_PRE_REJECTED_CURRENT.jpg","JPEG",quality=96,subsampling=0)

# Full atlas source/current readable + raw at practical overview.
fullcards=[]
for t,im in [("SOURCE FLIP-Y",src),("CURRENT FLIP-Y",cur),("SOURCE RAW",sraw),("CURRENT RAW",craw)]:
    z=comp(im).resize((1024,512),Image.Resampling.LANCZOS)
    fullcards.append(lab(z,t))
fs=Image.new("RGB",(2048,1080),(10,10,10))
fs.paste(fullcards[0],(0,0));fs.paste(fullcards[1],(1024,0));fs.paste(fullcards[2],(0,540));fs.paste(fullcards[3],(1024,540))
fs.save(out/"C243_FULL_SOURCE_CURRENT_FLIPY_RAW.jpg","JPEG",quality=94,subsampling=0)

# Practical target scale 100/75/50.
pcards=[]
target_crop=(2960,1380,3550,1590)
for pct in (100,75,50):
    pair=[]
    for t,im in [("SOURCE",src),("CURRENT",cur)]:
        z=comp(im.crop(target_crop))
        z=z.resize((max(1,round(z.width*pct/100)),max(1,round(z.height*pct/100))),Image.Resampling.LANCZOS)
        pair.append(lab(z,f"{t} {pct}%"))
    row=Image.new("RGB",(pair[0].width+pair[1].width,max(pair[0].height,pair[1].height)),(10,10,10));row.paste(pair[0],(0,0));row.paste(pair[1],(pair[0].width,0));pcards.append(row)
ps=Image.new("RGB",(max(x.width for x in pcards),sum(x.height for x in pcards)),(10,10,10));y=0
for z in pcards:ps.paste(z,(0,y));y+=z.height
ps.save(out/"C243_TARGET_PRACTICAL_100_75_50.jpg","JPEG",quality=95,subsampling=0)

report={
 "schema_version":2,"run":RUN,"role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":51,"priority":"P0","asset":asset.as_posix(),"user_jpg_regression":"PJR-014-20261006",
 "defect_tags":["BOTTOM_OUTLINE_CLIPPED","GLYPH_EFFECT_CLIPPING"],
 "producer_run":"A163R","source_sha256":SOURCE_SHA,
 "source_provenance":{"repo":"Sonic-TV/OR2006Sprites","commit":SRC_COMMIT,"url":SRC_URL},
 "pre_a144_sha256":PRE_A144_SHA,"pre_a144_provenance":preprov,
 "a163_style_rejected_sha256":A163_REJECTED_SHA,"a163_rejected_provenance":rejprov,
 "candidate_sha256":CURRENT_SHA,"true_readable_target_bbox":list(TARGET),
 "rows":rows,"machine_qa":machine,
 "fresh_c_machine_status":"PASS_PENDING_CONTROLLER_VISUAL",
 "mandatory_c3":"REQUIRED_EXACT_SHA_PRIOR_USER_JPG_CLIPPING_FAIL_AND_C239_MAPPING_FALSE_NEGATIVE",
 "controller_visual_qa":"PENDING","c3_strict_decision":"PENDING_CONTROLLER",
 "pre_ingame_export":"BLOCKED_UNTIL_CONTROLLER_C3",
 "user_jpg_review":"PENDING_AFTER_FRESH_C",
 "actual_ingame_validation":"PENDING",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[],
 "visual_evidence":[
  f"localization/graphics/role_C/{RUN}/C243_TARGET_SOURCE_CLEAN_PRE_REJECTED_CURRENT_HIGHZOOM.jpg",
  f"localization/graphics/role_C/{RUN}/C243_TARGET_RAW_SOURCE_PRE_REJECTED_CURRENT.jpg",
  f"localization/graphics/role_C/{RUN}/C243_FULL_SOURCE_CURRENT_FLIPY_RAW.jpg",
  f"localization/graphics/role_C/{RUN}/C243_TARGET_PRACTICAL_100_75_50.jpg"
 ]
}
(out/"C243_FF2462BB_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
(wr/"C243_FF2462BB.json").write_text(json.dumps({
 "run":RUN,"role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":51,"candidate_sha256":CURRENT_SHA,"machine_status":"PASS_PENDING_CONTROLLER_VISUAL",
 "report":f"localization/graphics/role_C/{RUN}/C243_FF2462BB_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"queue_index":51,"candidate_sha256":CURRENT_SHA,"rows":rows,"machine":machine,"status":"PASS_PENDING_CONTROLLER_VISUAL"},ensure_ascii=False,indent=2))
