#!/usr/bin/env python3
# C238 q51 FF2462BB fresh independent C + C3 evidence
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import os, io, json, hashlib, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
asset_rel=Path("textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds")
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
expected_current="3a046a8b695ee6b0a766fca223455616a45a9480b72e28b0c39ddf42821d0b6d"
expected_before="4fff8c59a44a1b7d03cee192124915f87eb73b3988c7673feb3228785ce67726"
source_commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
source_url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{source_commit}/Release/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"
bboxes=[(3002,482,3512,562),(3002,562,3512,643)]
localized_report=[(3117,491,3397,553),(3068,571,3445,634)]

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    with Image.open(io.BytesIO(b)) as im: return im.convert("RGBA")
cur_bytes=candidate.read_bytes()
if sha(cur_bytes)!=expected_current:
    raise SystemExit(f"current candidate SHA mismatch {sha(cur_bytes)}")

# Recover the exact immediately-prior candidate by content hash from recent path history.
hist=subprocess.check_output(["git","rev-list","--max-count=80","HEAD","--",str(candidate.relative_to(repo))],text=True).splitlines()
old_bytes=None; old_commit=None
for c in hist:
    try:
        b=subprocess.check_output(["git","show",f"{c}:{candidate.relative_to(repo).as_posix()}"],stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        continue
    if sha(b)==expected_before:
        old_bytes=b; old_commit=c; break
if old_bytes is None:
    raise SystemExit("prior candidate SHA not found in recent history")

req=urllib.request.Request(source_url,headers={"User-Agent":"OutRun-Korean-C238"})
with urllib.request.urlopen(req,timeout=90) as resp: src_bytes=resp.read()

cur=decode(cur_bytes); old=decode(old_bytes); src_native=decode(src_bytes)
if cur.size!=(4096,2048) or old.size!=cur.size:
    raise SystemExit(f"unexpected candidate dimensions cur={cur.size} old={old.size}")

# Pinned public English source is quarter-size; x4 NN is visual evidence only.
if src_native.size==(1024,512):
    src_display=src_native.resize(cur.size,Image.Resampling.NEAREST)
    source_display_scale=4
elif src_native.size==cur.size:
    src_display=src_native
    source_display_scale=1
else:
    raise SystemExit(f"unexpected English source size {src_native.size}")

A=np.array(old,dtype=np.uint8); B=np.array(cur,dtype=np.uint8)
diff=np.any(A!=B,axis=2)
alpha_diff=A[:,:,3]!=B[:,:,3]
allowed=np.zeros(diff.shape,dtype=bool)
for x1,y1,x2,y2 in bboxes: allowed[y1:y2,x1:x2]=True
outside=int(np.count_nonzero(diff & ~allowed))
alpha_outside=int(np.count_nonzero(alpha_diff & ~allowed))
if outside or alpha_outside:
    raise SystemExit(f"blast radius failure visible_outside={outside} alpha_outside={alpha_outside}")

# Independent per-line changed-pixel containment and positive margins.
line_results=[]
for i,(bb,lbb) in enumerate(zip(bboxes,localized_report),1):
    x1,y1,x2,y2=bb
    ys,xs=np.where(diff[y1:y2,x1:x2])
    if len(xs)==0:
        raise SystemExit(f"line {i} has no material byte/pixel change")
    db=(x1+int(xs.min()),y1+int(ys.min()),x1+int(xs.max())+1,y1+int(ys.max())+1)
    contained=(db[0]>=x1 and db[1]>=y1 and db[2]<=x2 and db[3]<=y2)
    margins=[db[0]-x1,x2-db[2],db[1]-y1,y2-db[3]]
    if not contained or min(margins)<1:
        raise SystemExit(f"line {i} containment/margin fail diff_bbox={db} margins={margins}")
    lx1,ly1,lx2,ly2=lbb
    report_contained=(lx1>=x1 and ly1>=y1 and lx2<=x2 and ly2<=y2 and (lx2-lx1)<= (x2-x1) and (ly2-ly1)<= (y2-y1))
    report_margins=[lx1-x1,x2-lx2,ly1-y1,y2-ly2]
    if not report_contained or min(report_margins)<1:
        raise SystemExit(f"line {i} reported localized bbox fail")
    line_results.append({"line":i,"source_bbox":bb,"changed_bbox":db,"changed_margins":margins,
                         "localized_bbox":lbb,"localized_margins":report_margins,
                         "source_size":[x2-x1,y2-y1],"localized_size":[lx2-lx1,ly2-ly1]})

# Header / format / roundtrip checks.
header_exact=cur_bytes[:128]==old_bytes[:128]
if not header_exact: raise SystemExit("DDS header drift")
with Image.open(io.BytesIO(cur_bytes)) as im:
    persisted_size=list(im.size)
    mip_count=int.from_bytes(cur_bytes[28:32],"little") or 1
    fourcc=cur_bytes[84:88].rstrip(b"\x00").decode("ascii","ignore")

# Build independent visual evidence: full FLIP-Y/RAW + high-zoom source/current row.
outdir=repo/"localization/graphics/role_C/20261007-C238-C1-Q051-FF2462BB-A144"
outdir.mkdir(parents=True,exist_ok=True)
bg=(88,88,88)
def flat(im):
    base=Image.new("RGB",im.size,bg); base.paste(im.convert("RGB"),mask=im.getchannel("A")); return base
def fit(im,maxw=1600):
    if im.width<=maxw:return im
    h=round(im.height*maxw/im.width); return im.resize((maxw,h),Image.Resampling.LANCZOS)

raw_src=fit(flat(src_display)); raw_cur=fit(flat(cur))
flip_src=fit(flat(ImageOps.flip(src_display))); flip_cur=fit(flat(ImageOps.flip(cur)))
W=max(raw_src.width+raw_cur.width,flip_src.width+flip_cur.width); H=raw_src.height+flip_src.height
canvas=Image.new("RGB",(W,H+120),(32,32,32))
canvas.paste(flip_src,(0,60)); canvas.paste(flip_cur,(flip_src.width,60))
y=60+flip_src.height+60; canvas.paste(raw_src,(0,y)); canvas.paste(raw_cur,(raw_src.width,y))
d=ImageDraw.Draw(canvas); f=ImageFont.load_default()
d.text((10,10),"FLIP-Y: ENGLISH SOURCE | CURRENT KOREAN",font=f,fill="white")
d.text((10,60+flip_src.height+10),"RAW DDS: ENGLISH SOURCE | CURRENT KOREAN",font=f,fill="white")
fulljpg=outdir/"C238_FF2462BB_SOURCE_FINAL_RAW_FLIPY.jpg"; canvas.save(fulljpg,"JPEG",quality=95,subsampling=0)

# Crop both lines together with context; source display x4 is visual only.
crop=(2940,430,3580,700)
s_crop=ImageOps.flip(src_display).crop(crop).resize((1280,540),Image.Resampling.NEAREST)
c_crop=ImageOps.flip(cur).crop(crop).resize((1280,540),Image.Resampling.NEAREST)
card=Image.new("RGB",(2560,600),(40,40,40)); card.paste(flat(s_crop),(0,60)); card.paste(flat(c_crop),(1280,60))
dc=ImageDraw.Draw(card); dc.text((10,10),"HIGH ZOOM FLIP-Y: ENGLISH SOURCE | CURRENT KOREAN (two-line clipping regression)",font=f,fill="white")
cropjpg=outdir/"C238_FF2462BB_TWO_LINE_HIGH_ZOOM.jpg"; card.save(cropjpg,"JPEG",quality=96,subsampling=0)

report={
 "run":"20261007-C238-C1-Q051-FF2462BB-A144",
 "role":"C","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "queue_index":51,"asset":"FF2462BB","producer_run":"A144",
 "candidate_sha256":expected_current,"prior_candidate_sha256":expected_before,"prior_candidate_commit":old_commit,
 "english_source":{"origin":"Sonic-TV/OR2006Sprites","commit":source_commit,"url":source_url,
                   "sha256":sha(src_bytes),"native_size":list(src_native.size),"display_scale_visual_only":source_display_scale},
 "machine_status":"PASS_PENDING_CONTROLLER_VISUAL",
 "changed_pixels":int(np.count_nonzero(diff)),"changed_pixels_outside_two_exact_source_bboxes":outside,
 "alpha_changed_outside_two_exact_source_bboxes":alpha_outside,
 "line_results":line_results,"dds":{"size":persisted_size,"mip_count":mip_count,"fourcc":fourcc,"header_vs_prior_exact":header_exact},
 "fresh_c_visual_checks":["bottom_outline_clipping","glyph_effect_clipping","source_style_and_weight","readability","raw_and_flipy_orientation"],
 "mandatory_c3":"REQUIRED_EXACT_SHA_DUE_PRIOR_USER_JPG_FAIL_AND_CLIPPING_FALSE_NEGATIVE",
 "controller_visual_decision":"PENDING",
 "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(outdir/"C238_FF2462BB_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
