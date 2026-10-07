#!/usr/bin/env python3
# C232 / TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
# Fresh independent C + mandatory C3 strict audit for q95 37759842 / A137.
import io, os, json, hashlib, pathlib, subprocess, urllib.request, struct
import numpy as np
from PIL import Image, ImageOps, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

RUN="20261007-C232-C1-Q095-37759842-A137"
ROOT=pathlib.Path("localization/graphics/role_C")/RUN
ROOT.mkdir(parents=True, exist_ok=True)
CAND=pathlib.Path("localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds")
CLEAN=pathlib.Path("localization/graphics/role_A/20261006-A-PRODUCTION81-3775-BBOX/37759842_HD_CLEAN_PLATE.png")
PROTECTED=pathlib.Path("localization/graphics/role_A/20261006-A-PRODUCTION81-3775-BBOX/37759842_HD_PROTECTED_VISIBLE_MASK.png")
SOURCE_CORE=pathlib.Path("localization/graphics/role_A/20261006-A-PRODUCTION81-3775-BBOX/37759842_HD_SOURCE_CORE_MASK.png")
C221=pathlib.Path("localization/graphics/role_C/20261006-C221-37759842-A83/C221_37759842_MACHINE_QA.json")
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds"
EXPECTED_SOURCE="7b41a04e2b0736717dd0da4d82f9e18f3aac7c469a5738848c5cfa6bf28e15b5"
EXPECTED_CAND="ced8da1cbe46732f5f3793f9ddf63060efb6c856bb414b30499e2b39e2fa925b"
EXPECTED_OLD="2dac8ee099120f2978eaf8ba992ffff11ecad7c11912a98aca9269a1a78f6988"
CAND_REPO=str(CAND)

def sha(b): return hashlib.sha256(b).hexdigest()
def rgba_bytes(b):
    im=Image.open(io.BytesIO(b)); im.load(); return im.convert("RGBA")
def arr(im): return np.array(im)
def visible_diff(a,b):
    aa=a[:,:,3].astype(np.uint16); ba=b[:,:,3].astype(np.uint16)
    ap=a[:,:,:3].astype(np.uint16)*aa[:,:,None]
    bp=b[:,:,:3].astype(np.uint16)*ba[:,:,None]
    return (aa!=ba) | np.any(ap!=bp,axis=2)
def bbox(mask):
    ys,xs=np.where(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def local_bbox(mask,b):
    x0,y0,x1,y1=b
    bb=bbox(mask[y0:y1,x0:x1])
    return None if bb is None else [bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
def size(b): return [b[2]-b[0],b[3]-b[1]]
def margins(src,fin): return [fin[0]-src[0],src[2]-fin[2],fin[1]-src[1],src[3]-fin[3]]
def strip(images, labels, scale, flip=True):
    parts=[]
    for im,label in zip(images,labels):
        q=ImageOps.flip(im) if flip else im
        q=q.resize((max(1,round(q.width*scale)),max(1,round(q.height*scale))),Image.Resampling.LANCZOS)
        cv=Image.new("RGB",(q.width,q.height+24),"#cfcfcf")
        cv.paste(q.convert("RGB"),(0,24)); ImageDraw.Draw(cv).text((6,6),label,fill="black")
        parts.append(cv)
    out=Image.new("RGB",(sum(x.width for x in parts),max(x.height for x in parts)),"#b0b0b0")
    x=0
    for p in parts: out.paste(p,(x,0)); x+=p.width
    return out

with urllib.request.urlopen(SOURCE_URL,timeout=90) as r: source_bytes=r.read()
cand_bytes=CAND.read_bytes()
if sha(source_bytes)!=EXPECTED_SOURCE: raise SystemExit(f"source SHA mismatch {sha(source_bytes)}")
if sha(cand_bytes)!=EXPECTED_CAND: raise SystemExit(f"candidate SHA mismatch {sha(cand_bytes)}")

# Recover exact C221-approved predecessor by content hash across Git history.
old_bytes=None; old_commit=None
for h in subprocess.check_output(["git","log","--format=%H","--all","--",CAND_REPO],text=True).splitlines():
    try: b=subprocess.check_output(["git","show",f"{h}:{CAND_REPO}"],stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError: continue
    if sha(b)==EXPECTED_OLD:
        old_bytes=b; old_commit=h; break
if old_bytes is None: raise SystemExit("exact C221 predecessor not found in git history")

source_raw=rgba_bytes(source_bytes); cand_raw=rgba_bytes(cand_bytes); old_raw=rgba_bytes(old_bytes)
# Canonical evidence/masks and all recorded text bboxes are in readable FLIP-Y orientation.
source=ImageOps.flip(source_raw); cand=ImageOps.flip(cand_raw); old=ImageOps.flip(old_raw)
clean=Image.open(CLEAN).convert("RGBA")
if not (source.size==cand.size==old.size==clean.size==(4096,4096)):
    raise SystemExit(f"decoded dimension mismatch {source.size} {cand.size} {old.size} {clean.size}")
S,A,O,K=map(arr,[source,cand,old,clean])
P=np.array(Image.open(PROTECTED).convert("L"))>0
SC=np.array(Image.open(SOURCE_CORE).convert("L"))>0
W,H=source.size

prior=json.loads(C221.read_text(encoding="utf-8"))
if prior.get("source_sha256")!=EXPECTED_SOURCE or prior.get("candidate_sha256")!=EXPECTED_OLD:
    raise SystemExit("C221 prior provenance mismatch")
rows=[]
for r in prior["row_checks"]:
    rows.append({"idx":int(r["idx"]),"kind":r["kind"],"source_bbox":[int(x) for x in r["source_effect_bbox"]]})
if len(rows)!=16: raise SystemExit(f"expected 16 transformed rows, got {len(rows)}")

final_delta=visible_diff(A,K)
old_delta=visible_diff(O,K)
change=visible_diff(A,O)
alpha_change=A[:,:,3]!=O[:,:,3]
allowed=np.zeros((H,W),bool)
checks=[]
for r in rows:
    sb=r["source_bbox"]; x0,y0,x1,y1=sb
    allowed[y0:y1,x0:x1]=True
    fb=local_bbox(final_delta,sb); ob=local_bbox(old_delta,sb)
    if fb is None or ob is None: raise SystemExit(f"missing localized bbox idx {r['idx']} {fb} {ob}")
    mg=margins(sb,fb)
    containment=fb[0]>=x0 and fb[1]>=y0 and fb[2]<=x1 and fb[3]<=y1
    positive=all(v>0 for v in mg)
    sw,sh=size(sb); fw,fh=size(fb); ow,oh=size(ob)
    exact_source_residue=int((SC[y0:y1,x0:x1] & np.all(A[y0:y1,x0:x1]==S[y0:y1,x0:x1],axis=2)).sum())
    checks.append({
      "idx":r["idx"],"kind":r["kind"],"source_bbox":sb,
      "prior_bbox":ob,"localized_bbox":fb,
      "source_size":[sw,sh],"prior_size":[ow,oh],"localized_size":[fw,fh],
      "margins":mg,
      "containment":"PASS" if containment else "FAIL",
      "size_ceiling":"PASS" if fw<=sw and fh<=sh else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL",
      "exact_source_core_pixels_remaining":exact_source_residue
    })

outside=int((change & ~allowed).sum())
alpha_outside=int((alpha_change & ~allowed).sum())
protected_changed=int((change & P).sum())
residue_total=sum(x["exact_source_core_pixels_remaining"] for x in checks)
header_exact=source_bytes[:128]==cand_bytes[:128]
mips=struct.unpack_from("<I",cand_bytes,28)[0]
row_pass=all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["positive_margin"]=="PASS" for x in checks)
machine_pass=row_pass and outside==0 and alpha_outside==0 and protected_changed==0 and residue_total==0 and header_exact and mips==1

# Evidence: full matched views, target contacts, practical display scale and RAW orientation.
strip([source,clean,old,cand],["SOURCE","CLEAN","C221 OLD","A137 CURRENT"],0.125,False).save(ROOT/"C232_SOURCE_CLEAN_OLD_FINAL_FLIPY_12P5.jpg",quality=94)
strip([source,cand],["SOURCE practical 25%","A137 practical 25%"],0.25,False).save(ROOT/"C232_SOURCE_FINAL_PRACTICAL_25PCT.jpg",quality=94)
strip([old,cand],["C221 old practical 25%","A137 current practical 25%"],0.25,False).save(ROOT/"C232_OLD_FINAL_PRACTICAL_25PCT.jpg",quality=94)
strip([source_raw,cand_raw],["SOURCE RAW","A137 RAW"],0.125,False).save(ROOT/"C232_SOURCE_FINAL_RAW_12P5.jpg",quality=94)

contacts=[]
for r in checks:
    x0,y0,x1,y1=r["source_bbox"]; pad=12
    box=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    ims=[]
    for im in (source,clean,old,cand):
        q=im.crop(box).resize(((box[2]-box[0])*2,(box[3]-box[1])*2),Image.Resampling.NEAREST).convert("RGB")
        ims.append(q)
    row=Image.new("RGB",(sum(i.width for i in ims),max(i.height for i in ims)),"#b0b0b0")
    x=0
    for im in ims: row.paste(im,(x,0)); x+=im.width
    contacts.append(row)
sheet=Image.new("RGB",(max(x.width for x in contacts),sum(x.height for x in contacts)),"#b0b0b0")
y=0
for im in contacts: sheet.paste(im,(0,y)); y+=im.height
sheet.save(ROOT/"C232_TRANSFORM_ROWS_SOURCE_CLEAN_OLD_FINAL_2X.jpg",quality=95)

report={
 "schema_version":2,"role":"C","run":RUN,"qa_id":"C232","queue_index":95,
 "asset":"textures/load/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds",
 "producer_run":"A137","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "user_ingame_regressions":["IGR-014","IGR-015","IGR-016"],
 "source_sha256":sha(source_bytes),"prior_candidate_sha256":sha(old_bytes),"prior_candidate_git_commit":old_commit,
 "candidate_sha256":sha(cand_bytes),
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","path":"Release/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds","url":SOURCE_URL},
 "independent_basis":"Pinned canonical English DDS freshly downloaded and decoded; exact C221-approved predecessor recovered by SHA from Git history; current persisted DDS decoded independently. The 16 source effect bboxes come from prior independent C221 provenance, while current localized bboxes are re-derived from current-vs-verified-clean decoded pixels. A137 producer localized bboxes are not consumed.",
 "structure":{"dimensions":[W,H],"format":"RGBA32/BGRA","header_128_exact":header_exact,"mip_count":mips,"raw_orientation":"mirror_y"},
 "row_checks":checks,
 "machine_checks":{
   "bbox_size_positive_margin":f"{sum(1 for x in checks if x['containment']=='PASS' and x['size_ceiling']=='PASS' and x['positive_margin']=='PASS')}/{len(checks)} PASS",
   "visible_changes_outside_16_source_bboxes_vs_C221":outside,
   "alpha_changes_outside_16_source_bboxes_vs_C221":alpha_outside,
   "protected_visible_pixels_changed_vs_C221":protected_changed,
   "exact_source_core_residue_pixels":residue_total,
   "header_128_exact":header_exact,"mip_count":mips,
   "post_encode_decode_authority":"PASS" if sha(cand_bytes)==EXPECTED_CAND else "FAIL"
 },
 "machine_status":"PASS" if machine_pass else "FAIL",
 "c3_required":True,
 "c3_reason":["USER_INGAME_P0_REGRESSION","PRIOR_VISUAL_FALSE_NEGATIVE_BAD_SLANT","TRANSFORMED_MULTILINE_TEXT"],
 "c3_visual_priorities":["slant_direction","clean_plate_source_removal","font_style_fidelity","scale_readability","glyph_integrity","protected_art_separation","source_faithful_placement","FLIP_Y_RAW_practical_scale"],
 "visual_evidence":[
   str(ROOT/"C232_SOURCE_CLEAN_OLD_FINAL_FLIPY_12P5.jpg"),
   str(ROOT/"C232_TRANSFORM_ROWS_SOURCE_CLEAN_OLD_FINAL_2X.jpg"),
   str(ROOT/"C232_SOURCE_FINAL_PRACTICAL_25PCT.jpg"),
   str(ROOT/"C232_OLD_FINAL_PRACTICAL_25PCT.jpg"),
   str(ROOT/"C232_SOURCE_FINAL_RAW_12P5.jpg")
 ],
 "controller_visual_qa":"PENDING_CONTROLLER",
 "c3_strict_decision":"PENDING_CONTROLLER",
 "decision":"PENDING_CONTROLLER",
 "backlog_close_allowed":False,
 "runtime_validation":"UNTESTED",
 "forbidden_domains_touched":[]
}
(ROOT/"C232_37759842_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
pathlib.Path("localization/graphics/worker_results/C232_37759842.json").write_text(json.dumps({
 "role":"C","run":RUN,"queue_index":95,"asset":"37759842",
 "TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "machine_status":report["machine_status"],"candidate_sha256":report["candidate_sha256"],
 "c3_required":True,"report":str(ROOT/"C232_37759842_MACHINE_QA.json"),
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"machine_status":report["machine_status"],"outside":outside,"alpha_outside":alpha_outside,"protected_changed":protected_changed,"residue":residue_total},ensure_ascii=False))
if not machine_pass: raise SystemExit("C232 machine QA failed closed")
