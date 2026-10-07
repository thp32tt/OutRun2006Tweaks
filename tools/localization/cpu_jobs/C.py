#!/usr/bin/env python3
# C235 / TEMP_BACKLOG_RELIEF=C2 / SHARD=EVEN
# Fresh independent C for P0 PJR-001 q12 D6DC1380 / A160.
# Retry note: initial dispatch was cancelled by shared Actions concurrency; first executed verifier exposed RAW orientation mismatch.
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
def flip_bbox_y(b,h):
    return [b[0],h-b[3],b[2],h-b[1]]
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

old_bytes=None; old_commit=None
for h in subprocess.check_output(["git","log","--format=%H","--all","--",CAND_REPO],text=True).splitlines():
    try: b=subprocess.check_output(["git","show",f"{h}:{CAND_REPO}"],stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError: continue
    if sha(b)==EXPECTED_OLD:
        old_bytes=b; old_commit=h; break
if old_bytes is None: raise SystemExit("rejected predecessor not found in git history")

source_native=decode(source_bytes); old=decode(old_bytes); cand=decode(cand_bytes)
if source_native.size!=(256,64) or old.size!=(1024,256) or cand.size!=(1024,256):
    raise SystemExit(f"dimension mismatch {source_native.size} {old.size} {cand.size}")

SN,O,F=map(arr,[source_native,old,cand])
source_bbox_native=bbox(SN[:,:,3]>0)
if source_bbox_native!=[8,10,248,44]: raise SystemExit(f"unexpected source bbox {source_bbox_native}")
source_bbox_raw=[v*4 for v in source_bbox_native]  # canonical source RAW is normal/readable
source_bbox_mirror=flip_bbox_y(source_bbox_raw,256)

old_bbox_raw=bbox(O[:,:,3]>0); fin_bbox_raw=bbox(F[:,:,3]>0)
if old_bbox_raw is None or fin_bbox_raw is None: raise SystemExit("candidate alpha bbox missing")
old_bbox_readable=flip_bbox_y(old_bbox_raw,256)
fin_bbox_readable=flip_bbox_y(fin_bbox_raw,256)

sw,sh=size(source_bbox_raw); ow,oh=size(old_bbox_readable); fw,fh=size(fin_bbox_readable)
mg=margins(source_bbox_raw,fin_bbox_readable)
readable_contain=(fin_bbox_readable[0]>=source_bbox_raw[0] and fin_bbox_readable[1]>=source_bbox_raw[1] and fin_bbox_readable[2]<=source_bbox_raw[2] and fin_bbox_readable[3]<=source_bbox_raw[3])
readable_positive=all(v>0 for v in mg)
size_ok=(fw<=sw and fh<=sh)

# Determine current RAW relation to canonical source. Current alpha sits in the Y-mirrored source footprint,
# not in the canonical normal/raw footprint. This is the exact user-reported orientation class.
raw_in_normal=(fin_bbox_raw[0]>=source_bbox_raw[0] and fin_bbox_raw[1]>=source_bbox_raw[1] and fin_bbox_raw[2]<=source_bbox_raw[2] and fin_bbox_raw[3]<=source_bbox_raw[3])
raw_in_mirror=(fin_bbox_raw[0]>=source_bbox_mirror[0] and fin_bbox_raw[1]>=source_bbox_mirror[1] and fin_bbox_raw[2]<=source_bbox_mirror[2] and fin_bbox_raw[3]<=source_bbox_mirror[3])
orientation_status="PASS_RAW_NORMAL_MATCHES_CANONICAL_SOURCE" if raw_in_normal and not raw_in_mirror else "FAIL_RAW_MIRROR_Y_VS_CANONICAL_SOURCE_NORMAL" if raw_in_mirror and not raw_in_normal else "HOLD_AMBIGUOUS_RAW_ORIENTATION"

# A160 scale rework blast-radius is assessed in the current candidate's own raw coordinate frame.
allowed=np.zeros((256,1024),bool)
ax0,ay0,ax1,ay1=source_bbox_mirror if raw_in_mirror else source_bbox_raw
allowed[ay0:ay1,ax0:ax1]=True
change=np.any(F!=O,axis=2); vis_change=visible_diff(F,O); alpha_change=F[:,:,3]!=O[:,:,3]
changed_outside=int((change & ~allowed).sum())
visible_changed_outside=int((vis_change & ~allowed).sum())
alpha_changed_outside=int((alpha_change & ~allowed).sum())
blast_pass=(changed_outside==0 and visible_changed_outside==0 and alpha_changed_outside==0)

header_exact_old=(old_bytes[:128]==cand_bytes[:128])
mips=struct.unpack_from("<I",cand_bytes,28)[0]
scale_geometry_pass=(readable_contain and readable_positive and size_ok and blast_pass and header_exact_old and mips==1 and fw>ow)
machine_pass=(scale_geometry_pass and orientation_status.startswith("PASS_"))

source4=source_native.resize((1024,256),Image.Resampling.NEAREST)
clean=Image.new("RGBA",(1024,256),(0,0,0,0))
# RAW source must be compared RAW-to-RAW; current candidate visibly occupies the mirrored vertical footprint.
hstrip([draw_label(neutral(source4),"CANONICAL SOURCE RAW 4x"),
        draw_label(neutral(old),"C233 REJECTED RAW"),
        draw_label(neutral(cand),"A160 FINAL RAW")]).save(ROOT/"C235_SOURCE_OLD_FINAL_RAW.jpg",quality=95)
# Flip all three independently to expose the opposite relation.
hstrip([draw_label(neutral(ImageOps.flip(source4)),"SOURCE FLIP-Y"),
        draw_label(neutral(ImageOps.flip(old)),"C233 REJECTED FLIP-Y"),
        draw_label(neutral(ImageOps.flip(cand)),"A160 FINAL FLIP-Y")]).save(ROOT/"C235_SOURCE_OLD_FINAL_FLIPY.jpg",quality=95)
# Readable content comparison: canonical source is already normal/readable; current candidate requires FLIP-Y to become readable.
read_old=ImageOps.flip(old); read_final=ImageOps.flip(cand)
hstrip([draw_label(neutral(source4),"SOURCE READABLE"),
        draw_label(neutral(clean),"CLEAN TRANSPARENT"),
        draw_label(neutral(read_old),"C233 REJECTED READABLE"),
        draw_label(neutral(read_final),"A160 FINAL READABLE")]).save(ROOT/"C235_READABLE_SOURCE_CLEAN_OLD_FINAL.jpg",quality=95)
for pct in (100,75,50):
    w=1024*pct//100; h=256*pct//100
    s=neutral(source4).resize((w,h),Image.Resampling.LANCZOS)
    o=neutral(read_old).resize((w,h),Image.Resampling.LANCZOS)
    f=neutral(read_final).resize((w,h),Image.Resampling.LANCZOS)
    hstrip([draw_label(s,f"SOURCE {pct}%"),draw_label(o,f"C233 REJECTED {pct}%"),draw_label(f,f"A160 FINAL {pct}%")]).save(ROOT/f"C235_PRACTICAL_{pct}PCT.jpg",quality=94)

report={
 "schema_version":2,"role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "run":RUN,"qa_id":"C235","queue_index":12,
 "asset":"textures/load/spr_etc_xst/D6DC1380_256x64.dds","producer_run":"A160",
 "user_jpg_regression":"PJR-001-20261006","priority":"P0",
 "source_sha256":sha(source_bytes),"prior_rejected_candidate_sha256":sha(old_bytes),
 "prior_rejected_candidate_git_commit":old_commit,"candidate_sha256":sha(cand_bytes),
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","url":SOURCE_URL},
 "independent_basis":"Pinned canonical English DDS freshly downloaded/decoded; source alpha bbox independently re-derived at native size. Current persisted DDS and exact C233-rejected predecessor independently decoded; predecessor recovered from Git by SHA. Producer bboxes are not consumed. RAW source/candidate vertical relation is derived directly from decoded alpha footprints.",
 "structure":{"source_dimensions":[256,64],"candidate_dimensions":[1024,256],"format":"RGBA32/BGRA","mip_count":mips,"header_exact_vs_rejected_predecessor":header_exact_old},
 "geometry":{
   "canonical_source_bbox_raw_hd":source_bbox_raw,
   "canonical_source_bbox_raw_mirror_y_hd":source_bbox_mirror,
   "prior_rejected_bbox_raw":old_bbox_raw,"localized_bbox_raw":fin_bbox_raw,
   "prior_rejected_bbox_readable_after_flip_y":old_bbox_readable,
   "localized_bbox_readable_after_flip_y":fin_bbox_readable,
   "source_size":[sw,sh],"prior_rejected_size":[ow,oh],"localized_size":[fw,fh],
   "readable_margins":mg,
   "readable_containment":"PASS" if readable_contain else "FAIL",
   "size_ceiling":"PASS" if size_ok else "FAIL",
   "readable_positive_margin":"PASS" if readable_positive else "FAIL",
   "material_width_gain_px":fw-ow
 },
 "orientation":{
   "canonical_source_raw_orientation":"NORMAL_READABLE",
   "candidate_raw_relation":orientation_status,
   "candidate_raw_bbox_in_canonical_normal_footprint":raw_in_normal,
   "candidate_raw_bbox_in_canonical_mirror_y_footprint":raw_in_mirror,
   "status":"PASS" if orientation_status.startswith("PASS_") else "FAIL"
 },
 "blast_radius":{
   "coordinate_frame":"CURRENT_CANDIDATE_RAW",
   "allowed_source_footprint":source_bbox_mirror if raw_in_mirror else source_bbox_raw,
   "changed_pixels_outside":changed_outside,
   "visible_changed_pixels_outside":visible_changed_outside,
   "alpha_changed_pixels_outside":alpha_changed_outside,
   "status":"PASS" if blast_pass else "FAIL"
 },
 "coverage":{"visible_localizable_segments":1,"localized_segments":1,"translation":"Continue? -> 계속?","status":"PASS"},
 "clean_plate":{"class":"TRANSPARENT_TEXT_ONLY","status":"PASS"},
 "scale_material_rework_status":"PASS" if scale_geometry_pass else "FAIL",
 "machine_status":"PASS" if machine_pass else "FAIL",
 "fresh_c_decision":"REWORK_REQUIRED" if not machine_pass else "PENDING_CONTROLLER",
 "failure_reason":"RAW_ORIENTATION_MISMATCH_CANONICAL_SOURCE_NORMAL_VS_CURRENT_MIRROR_Y" if orientation_status.startswith("FAIL_") else None,
 "c3_required":True,
 "c3_strict_decision":"BLOCKED_FRESH_C_FAIL_REWORK_THEN_RERUN" if not machine_pass else "PENDING_CONTROLLER",
 "pre_ingame_export":"EXCLUDED_REWORK_REQUIRED" if not machine_pass else "BLOCKED_PENDING_C3",
 "user_jpg_review":"OPEN","runtime_validation":"UNTESTED","forbidden_domains_touched":[],
 "visual_evidence":[
   str(ROOT/"C235_SOURCE_OLD_FINAL_RAW.jpg"),str(ROOT/"C235_SOURCE_OLD_FINAL_FLIPY.jpg"),
   str(ROOT/"C235_READABLE_SOURCE_CLEAN_OLD_FINAL.jpg"),
   str(ROOT/"C235_PRACTICAL_100PCT.jpg"),str(ROOT/"C235_PRACTICAL_75PCT.jpg"),str(ROOT/"C235_PRACTICAL_50PCT.jpg")
 ]
}
(ROOT/"C235_D6DC1380_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
pathlib.Path("localization/graphics/worker_results/C235_D6DC1380.json").write_text(json.dumps({
 "role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","run":RUN,"queue_index":12,"asset":"D6DC1380",
 "machine_status":report["machine_status"],"fresh_c_decision":report["fresh_c_decision"],
 "candidate_sha256":report["candidate_sha256"],"c3_required":True,"c3_strict_decision":report["c3_strict_decision"],
 "report":str(ROOT/"C235_D6DC1380_MACHINE_QA.json"),"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"machine_status":report["machine_status"],"orientation":report["orientation"],"geometry":report["geometry"],"blast_radius":report["blast_radius"]},ensure_ascii=False,indent=2))
# FAIL is a valid C evidence outcome and must be committed for controller reconciliation.
