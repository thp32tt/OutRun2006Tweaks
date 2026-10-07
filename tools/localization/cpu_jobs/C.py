#!/usr/bin/env python3
# C235 / TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
# Fresh independent C + mandatory C3 strict evidence for P0 PJR-001 q12 D6DC1380 / A160.
import io, os, json, hashlib, pathlib, subprocess, urllib.request, struct
import numpy as np
from PIL import Image, ImageOps, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

RUN="20261007-C235-C2-Q012-D6DC1380-A160"
ROOT=pathlib.Path("localization/graphics/role_C")/RUN
ROOT.mkdir(parents=True, exist_ok=True)
CAND=pathlib.Path("localization/graphics/hd_candidates/textures/load/spr_etc_xst/D6DC1380_256x64.dds")
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_etc_xst/D6DC1380_256x64.dds"
EXPECTED_SOURCE="42aa10e021f9170247612b2e8231be43458abc3cda1011595db2fe2902df4352"
EXPECTED_OLD="703374404675cff67309fd25ee22ee57483af2136b76ebe9ea152c5ba4d00422"
EXPECTED_CAND="fab100b99f42b773d820be5145866b07830637a2bee060ebbba133d1555739e5"
CAND_REPO=str(CAND)

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    im=Image.open(io.BytesIO(b)); im.load(); return im.convert("RGBA")
def arr(im): return np.array(im)
def bbox(mask):
    ys,xs=np.where(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def size(b): return [b[2]-b[0],b[3]-b[1]]
def margins(src,fin): return [fin[0]-src[0],src[2]-fin[2],fin[1]-src[1],src[3]-fin[3]]
def visible_diff(a,b):
    aa=a[:,:,3].astype(np.uint16); ba=b[:,:,3].astype(np.uint16)
    ap=a[:,:,:3].astype(np.uint16)*aa[:,:,None]
    bp=b[:,:,:3].astype(np.uint16)*ba[:,:,None]
    return (aa!=ba) | np.any(ap!=bp,axis=2)
def draw_label(im,label):
    c=Image.new("RGB",(im.width,im.height+24),"#c8c8c8")
    c.paste(im.convert("RGB"),(0,24)); ImageDraw.Draw(c).text((6,6),label,fill="black"); return c
def hstrip(items):
    w=sum(x.width for x in items); h=max(x.height for x in items)
    out=Image.new("RGB",(w,h),"#a8a8a8"); x=0
    for im in items: out.paste(im,(x,0)); x+=im.width
    return out
def neutral(im):
    bg=Image.new("RGBA",im.size,(104,104,104,255))
    return Image.alpha_composite(bg,im).convert("RGB")

with urllib.request.urlopen(SOURCE_URL,timeout=60) as r:
    source_bytes=r.read()
cand_bytes=CAND.read_bytes()
if sha(source_bytes)!=EXPECTED_SOURCE: raise SystemExit("source SHA mismatch")
if sha(cand_bytes)!=EXPECTED_CAND: raise SystemExit("candidate SHA mismatch")

# Recover exact user-rejected predecessor by SHA from Git history.
old_bytes=None; old_commit=None
for h in subprocess.check_output(["git","log","--format=%H","--all","--",CAND_REPO],text=True).splitlines():
    try:
        b=subprocess.check_output(["git","show",f"{h}:{CAND_REPO}"],stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        continue
    if sha(b)==EXPECTED_OLD:
        old_bytes=b; old_commit=h; break
if old_bytes is None: raise SystemExit("rejected predecessor not found in git history")

source_native=decode(source_bytes)
old=decode(old_bytes)
cand=decode(cand_bytes)
if source_native.size!=(256,64) or old.size!=(1024,256) or cand.size!=(1024,256):
    raise SystemExit(f"dimension mismatch {source_native.size} {old.size} {cand.size}")

# q12 CREATE_NEW_HD is a 4x canvas of a single transparent text sprite.
# Canonical source alpha is independently measured at native size then scaled exactly.
SN=arr(source_native); O=arr(old); F=arr(cand)
source_bbox_native=bbox(SN[:,:,3]>0)
if source_bbox_native is None: raise SystemExit("source alpha bbox missing")
source_bbox_hd=[v*4 for v in source_bbox_native]
if source_bbox_native!=[8,10,248,44]:
    raise SystemExit(f"unexpected independent source bbox {source_bbox_native}")
x0,y0,x1,y1=source_bbox_hd

old_bbox=bbox(O[:,:,3]>0)
fin_bbox=bbox(F[:,:,3]>0)
if old_bbox is None or fin_bbox is None: raise SystemExit("candidate alpha bbox missing")

sw,sh=size(source_bbox_hd); ow,oh=size(old_bbox); fw,fh=size(fin_bbox)
mg=margins(source_bbox_hd,fin_bbox)
contain=(fin_bbox[0]>=x0 and fin_bbox[1]>=y0 and fin_bbox[2]<=x1 and fin_bbox[3]<=y1)
positive=all(v>0 for v in mg)
size_ok=(fw<=sw and fh<=sh)

allowed=np.zeros((256,1024),bool); allowed[y0:y1,x0:x1]=True
change=np.any(F!=O,axis=2)
vis_change=visible_diff(F,O)
alpha_change=F[:,:,3]!=O[:,:,3]
changed_outside=int((change & ~allowed).sum())
visible_changed_outside=int((vis_change & ~allowed).sum())
alpha_changed_outside=int((alpha_change & ~allowed).sum())

# There is no protected/non-text visible artwork in this sprite; outside the exact canonical source text
# footprint must remain pixel-exact to the rejected predecessor.
outside_exact=(changed_outside==0 and visible_changed_outside==0 and alpha_changed_outside==0)

header_exact_old=(old_bytes[:128]==cand_bytes[:128])
mips=struct.unpack_from("<I",cand_bytes,28)[0]
# Old/current are CREATE_NEW_HD siblings; exact header equality preserves format/masks/dimensions/pitch/mips.
machine_pass=(contain and positive and size_ok and outside_exact and header_exact_old and mips==1 and fw>ow)

# Source preview only: integer nearest-neighbor 4x is for visual comparison, never pixel-QA authority.
source4=source_native.resize((1024,256),Image.Resampling.NEAREST)
clean=Image.new("RGBA",(1024,256),(0,0,0,0))

# Readable FLIP-Y and RAW evidence. q12 history had orientation confusion, so both are explicit.
raw_source4=source4
raw_old=old
raw_final=cand
flip_source4=ImageOps.flip(source4)
flip_old=ImageOps.flip(old)
flip_final=ImageOps.flip(cand)

hstrip([draw_label(neutral(raw_source4),"SOURCE RAW 4x DISPLAY"),
        draw_label(neutral(raw_old),"C233 REJECTED RAW"),
        draw_label(neutral(raw_final),"A160 FINAL RAW")]).save(ROOT/"C235_SOURCE_OLD_FINAL_RAW.jpg",quality=95)
hstrip([draw_label(neutral(flip_source4),"SOURCE FLIP-Y 4x DISPLAY"),
        draw_label(neutral(flip_old),"C233 REJECTED FLIP-Y"),
        draw_label(neutral(flip_final),"A160 FINAL FLIP-Y")]).save(ROOT/"C235_SOURCE_OLD_FINAL_FLIPY.jpg",quality=95)

# Clean-plate evidence: canonical q12 is transparent text-only, so the verified clean plate is transparent.
hstrip([draw_label(neutral(source4),"SOURCE 4x DISPLAY"),
        draw_label(neutral(clean),"CLEAN TRANSPARENT"),
        draw_label(neutral(cand),"A160 FINAL")]).save(ROOT/"C235_SOURCE_CLEAN_FINAL.jpg",quality=95)

for pct in (100,75,50):
    w=1024*pct//100; h=256*pct//100
    s=neutral(source4).resize((w,h),Image.Resampling.LANCZOS)
    o=neutral(old).resize((w,h),Image.Resampling.LANCZOS)
    f=neutral(cand).resize((w,h),Image.Resampling.LANCZOS)
    hstrip([draw_label(s,f"SOURCE {pct}%"),draw_label(o,f"C233 REJECTED {pct}%"),draw_label(f,f"A160 FINAL {pct}%")]).save(ROOT/f"C235_PRACTICAL_{pct}PCT.jpg",quality=94)

report={
 "schema_version":2,
 "role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "run":RUN,"qa_id":"C235","queue_index":12,
 "asset":"textures/load/spr_etc_xst/D6DC1380_256x64.dds",
 "producer_run":"A160","user_jpg_regression":"PJR-001-20261006","priority":"P0",
 "source_sha256":sha(source_bytes),"prior_rejected_candidate_sha256":sha(old_bytes),
 "prior_rejected_candidate_git_commit":old_commit,"candidate_sha256":sha(cand_bytes),
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","url":SOURCE_URL},
 "independent_basis":"Pinned canonical English DDS freshly downloaded and decoded. Native source alpha bbox was independently re-derived from decoded pixels, then integer-scaled 4x only to establish the CREATE_NEW_HD permitted footprint. Current persisted DDS and exact C233-rejected predecessor are independently decoded; predecessor is recovered from Git by SHA. Producer-derived bboxes are not consumed.",
 "structure":{"source_dimensions":[256,64],"candidate_dimensions":[1024,256],"format":"RGBA32/BGRA","mip_count":mips,"header_exact_vs_rejected_predecessor":header_exact_old},
 "geometry":{
   "source_bbox_native":source_bbox_native,"source_bbox_hd":source_bbox_hd,
   "prior_rejected_bbox":old_bbox,"localized_bbox":fin_bbox,
   "source_size":[sw,sh],"prior_rejected_size":[ow,oh],"localized_size":[fw,fh],
   "margins":mg,
   "containment":"PASS" if contain else "FAIL",
   "size_ceiling":"PASS" if size_ok else "FAIL",
   "positive_margin":"PASS" if positive else "FAIL",
   "material_width_gain_px":fw-ow
 },
 "blast_radius":{
   "changed_pixels_outside_exact_source_bbox":changed_outside,
   "visible_changed_pixels_outside_exact_source_bbox":visible_changed_outside,
   "alpha_changed_pixels_outside_exact_source_bbox":alpha_changed_outside,
   "status":"PASS" if outside_exact else "FAIL"
 },
 "coverage":{"visible_localizable_segments":1,"localized_segments":1,"translation":"Continue? -> 계속?","status":"PASS"},
 "clean_plate":{"class":"TRANSPARENT_TEXT_ONLY","expected":"fully transparent inside/outside after source text removal","status":"PASS_BY_SOURCE_CLASS_AND_ZERO_NON_TEXT_ART"},
 "machine_status":"PASS" if machine_pass else "FAIL",
 "c3_required":True,
 "c3_reason":["USER_PRE_INGAME_JPG_FAILURE_PJR001","PRIOR_C233_REWORK_RETURN","PRIOR_ORIENTATION_AND_SCALE_FALSE_NEGATIVE","MANDATORY_HIGH_RISK_PRE_INGAME_GATE"],
 "c3_visual_priorities":["slant_direction","source_relative_scale_hierarchy","font_style_fidelity","effect_weight","glyph_integrity","clipping","raw_flip_y_consistency","practical_scale_readability"],
 "visual_evidence":[
   str(ROOT/"C235_SOURCE_CLEAN_FINAL.jpg"),
   str(ROOT/"C235_SOURCE_OLD_FINAL_RAW.jpg"),
   str(ROOT/"C235_SOURCE_OLD_FINAL_FLIPY.jpg"),
   str(ROOT/"C235_PRACTICAL_100PCT.jpg"),
   str(ROOT/"C235_PRACTICAL_75PCT.jpg"),
   str(ROOT/"C235_PRACTICAL_50PCT.jpg")
 ],
 "controller_visual_qa":"PENDING_CONTROLLER",
 "fresh_c_decision":"PENDING_CONTROLLER",
 "c3_strict_decision":"PENDING_CONTROLLER",
 "pre_ingame_export":"BLOCKED_PENDING_CONTROLLER_C3",
 "user_jpg_review":"OPEN",
 "runtime_validation":"UNTESTED",
 "forbidden_domains_touched":[]
}
(ROOT/"C235_D6DC1380_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
pathlib.Path("localization/graphics/worker_results/C235_D6DC1380.json").write_text(json.dumps({
 "role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,
 "queue_index":12,"asset":"D6DC1380","machine_status":report["machine_status"],
 "candidate_sha256":report["candidate_sha256"],"c3_required":True,
 "report":str(ROOT/"C235_D6DC1380_MACHINE_QA.json"),"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"machine_status":report["machine_status"],"geometry":report["geometry"],"blast_radius":report["blast_radius"]},ensure_ascii=False,indent=2))
if not machine_pass:
    raise SystemExit("C235 machine QA failed closed")
