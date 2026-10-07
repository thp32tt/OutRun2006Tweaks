#!/usr/bin/env python3
# C239 C1 retry of q51 FF2462BB fresh C QA.
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import os, io, json, hashlib, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
repo=Path.cwd()
RUN="20261007-C239-C1-Q051-FF2462BB-A144"
asset=Path("textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds")
candidate=repo/"localization/graphics/hd_candidates"/asset
CURRENT="3a046a8b695ee6b0a766fca223455616a45a9480b72e28b0c39ddf42821d0b6d"
BEFORE="4fff8c59a44a1b7d03cee192124915f87eb73b3988c7673feb3228785ce67726"
source_commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
source_url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{source_commit}/Release/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"
# A144 bboxes are readable/FLIP-Y coordinates, not raw storage coordinates.
readable_source=[(3002,482,3512,562),(3002,562,3512,643)]
readable_local=[(3117,491,3397,553),(3068,571,3445,634)]
def sha(b): return hashlib.sha256(b).hexdigest()
def dec(b):
    with Image.open(io.BytesIO(b)) as im:return im.convert("RGBA")
cb=candidate.read_bytes()
if sha(cb)!=CURRENT: raise SystemExit("candidate SHA drift "+sha(cb))
hist=subprocess.check_output(["git","rev-list","--max-count=120","HEAD","--",candidate.relative_to(repo).as_posix()],text=True).splitlines()
oldb=None; oldcommit=None
for c in hist:
    try:b=subprocess.check_output(["git","show",f"{c}:{candidate.relative_to(repo).as_posix()}"],stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:continue
    if sha(b)==BEFORE:oldb=b;oldcommit=c;break
if oldb is None:raise SystemExit("prior candidate not found")
req=urllib.request.Request(source_url,headers={"User-Agent":"OutRun-C239"})
with urllib.request.urlopen(req,timeout=90) as r: sb=r.read()
cur=dec(cb); old=dec(oldb); src_native=dec(sb)
W,H=cur.size
if (W,H)!=(4096,2048) or old.size!=cur.size:raise SystemExit(f"unexpected size {cur.size} {old.size}")
src_disp=src_native.resize(cur.size,Image.Resampling.NEAREST) if src_native.size==(1024,512) else src_native
if src_disp.size!=cur.size:raise SystemExit(f"source display mismatch {src_native.size}")
def flipbox(bb):
    x1,y1,x2,y2=bb; return (x1,H-y2,x2,H-y1)
raw_source=[flipbox(x) for x in readable_source]
raw_local=[flipbox(x) for x in readable_local]
A=np.asarray(old); B=np.asarray(cur)
diff=np.any(A!=B,axis=2); ad=A[:,:,3]!=B[:,:,3]
allowed=np.zeros((H,W),bool)
for x1,y1,x2,y2 in raw_source:allowed[y1:y2,x1:x2]=True
out_vis=int(np.count_nonzero(diff&~allowed)); out_alpha=int(np.count_nonzero(ad&~allowed))
if out_vis or out_alpha:raise SystemExit(f"raw blast radius fail visible={out_vis} alpha={out_alpha}")
rows=[]
for n,(sbb,lbb,rbb,rlbb) in enumerate(zip(readable_source,readable_local,raw_source,raw_local),1):
    x1,y1,x2,y2=rbb; ys,xs=np.where(diff[y1:y2,x1:x2])
    if len(xs)==0:raise SystemExit(f"line {n} no material change")
    db=(x1+int(xs.min()),y1+int(ys.min()),x1+int(xs.max())+1,y1+int(ys.max())+1)
    dm=[db[0]-x1,x2-db[2],db[1]-y1,y2-db[3]]
    lm=[lbb[0]-sbb[0],sbb[2]-lbb[2],lbb[1]-sbb[1],sbb[3]-lbb[3]]
    sizeok=(lbb[2]-lbb[0])<=(sbb[2]-sbb[0]) and (lbb[3]-lbb[1])<=(sbb[3]-sbb[1])
    if min(dm)<1 or min(lm)<1 or not sizeok:raise SystemExit(f"line {n} containment fail diff={db} dm={dm} lm={lm}")
    rows.append({"line":n,"readable_source_bbox":sbb,"readable_localized_bbox":lbb,
      "raw_source_bbox":rbb,"raw_localized_bbox":rlbb,"raw_changed_bbox":db,
      "changed_positive_margins_raw":dm,"localized_positive_margins_readable":lm,
      "source_size":[sbb[2]-sbb[0],sbb[3]-sbb[1]],"localized_size":[lbb[2]-lbb[0],lbb[3]-lbb[1]],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"})
if cb[:128]!=oldb[:128]:raise SystemExit("DDS header drift")
mips=int.from_bytes(cb[28:32],"little") or 1
fourcc=cb[84:88].rstrip(b"\0").decode("ascii","ignore")
out=repo/"localization/graphics/role_C"/RUN;out.mkdir(parents=True,exist_ok=True)
def flat(im):
    z=Image.new("RGB",im.size,(88,88,88)); z.paste(im.convert("RGB"),mask=im.getchannel("A")); return z
def card(parts,title,path,maxw=1600):
    ims=[]
    for p in parts:
        z=flat(p)
        if z.width>maxw:z=z.resize((maxw,round(z.height*maxw/z.width)),Image.Resampling.LANCZOS)
        ims.append(z)
    hh=max(i.height for i in ims); canvas=Image.new("RGB",(sum(i.width for i in ims),hh+40),(25,25,25));x=0
    for i in ims:canvas.paste(i,(x,40));x+=i.width
    ImageDraw.Draw(canvas).text((8,8),title,fill="white",font=ImageFont.load_default());canvas.save(path,"JPEG",quality=95,subsampling=0)
card([ImageOps.flip(src_disp),ImageOps.flip(cur)],"FLIP-Y/readable: ENGLISH SOURCE | A144 CURRENT",out/"C239_READABLE_SOURCE_FINAL.jpg")
card([src_disp,cur],"RAW DDS: ENGLISH SOURCE | A144 CURRENT",out/"C239_RAW_SOURCE_FINAL.jpg")
# high zoom around the exact two-line area, in readable orientation
box=(2940,430,3580,700)
s=ImageOps.flip(src_disp).crop(box); c=ImageOps.flip(cur).crop(box)
s=s.resize((s.width*2,s.height*2),Image.Resampling.NEAREST);c=c.resize((c.width*2,c.height*2),Image.Resampling.NEAREST)
card([s,c],"HIGH ZOOM readable: source | current; inspect bottom outline/effect clipping",out/"C239_TWO_LINE_HIGH_ZOOM.jpg",maxw=9999)
report={
 "schema_version":2,"run":RUN,"role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":51,"asset":asset.as_posix(),"producer_run":"A144","user_jpg_regression":"PJR-014-20261006",
 "prior_candidate_sha256":BEFORE,"prior_candidate_commit":oldcommit,"candidate_sha256":CURRENT,
 "english_source":{"repo":"Sonic-TV/OR2006Sprites","commit":source_commit,"sha256":sha(sb),"native_size":list(src_native.size),"display_scale_visual_only":4 if src_native.size==(1024,512) else 1},
 "orientation_note":"A144/source bboxes are readable coordinates; independent blast-radius is evaluated in RAW after exact Y-flip conversion.",
 "rows":rows,"summary":{"2_of_2_bbox_size_positive_margin":"PASS","changed_pixels":int(diff.sum()),"changed_pixels_outside_exact_raw_source_bboxes":out_vis,"alpha_changed_outside_exact_raw_source_bboxes":out_alpha,"header_exact_vs_prior":True,"mips":mips,"fourcc":fourcc},
 "machine_status":"PASS","controller_visual_decision":"PENDING","mandatory_c3":"REQUIRED_EXACT_SHA_PRIOR_USER_JPG_CLIPPING_FAIL",
 "visual_evidence":[
   f"localization/graphics/role_C/{RUN}/C239_READABLE_SOURCE_FINAL.jpg",
   f"localization/graphics/role_C/{RUN}/C239_RAW_SOURCE_FINAL.jpg",
   f"localization/graphics/role_C/{RUN}/C239_TWO_LINE_HIGH_ZOOM.jpg"],
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"C239_FF2462BB_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
(wr/"C239_FF2462BB.json").write_text(json.dumps({"run":RUN,"TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)","queue_index":51,"candidate_sha256":CURRENT,"machine_status":"PASS","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
