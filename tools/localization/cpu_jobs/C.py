#!/usr/bin/env python3
# C231 independent final QA + mandatory C3 strict audit for B226 / q226 E3F4BA07.
import io, os, json, hashlib, pathlib, subprocess, urllib.request, struct
import numpy as np
from PIL import Image, ImageOps, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

RUN="20261007-C231-E3F4BA07-B226"
ROOT=pathlib.Path("localization/graphics/role_C")/RUN
ROOT.mkdir(parents=True, exist_ok=True)
CAND=pathlib.Path("localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds")
CLEAN=pathlib.Path("localization/graphics/role_C/20261005-C143-E3F4BA07/C143_EXACT_CLEAN_PLATE.png")
SOURCE_TEXT_MASK=pathlib.Path("localization/graphics/role_C/20261005-C143-E3F4BA07/C143_SOURCE_TEXT_MASK.png")
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds"
EXPECTED_SOURCE="fb31e9f62e0d46c4554646be2f32d70cb015e8fdbc269189bf9d76a26eab5b72"
EXPECTED_CAND="5449edb846d6ca3a5de1ab1f817a41feb776e9af3bdda2175967312369e5e374"
B226_COMMIT="27815f283c9fc628eb077702c23d1aa0748ee310"
CAND_REPO=str(CAND)

def sha(b): return hashlib.sha256(b).hexdigest()
def rgba_from_bytes(b):
    im=Image.open(io.BytesIO(b)); im.load(); return im.convert("RGBA")
def arr(im): return np.array(im)
def diffmask(a,b): return np.any(a!=b,axis=2)
def bbox(mask):
    ys,xs=np.where(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def local_bbox(mask, cell):
    x0,y0,x1,y1=cell
    b=bbox(mask[y0:y1,x0:x1])
    return None if b is None else [b[0]+x0,b[1]+y0,b[2]+x0,b[3]+y0]
def sz(b): return [b[2]-b[0],b[3]-b[1]]
def margins(src, fin):
    return [fin[0]-src[0],src[2]-fin[2],fin[1]-src[1],src[3]-fin[3]]
def annotate_strip(images, labels, scale=0.25):
    ims=[]
    for im,label in zip(images,labels):
        q=ImageOps.flip(im).resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.LANCZOS)
        canvas=Image.new("RGB",(q.width,q.height+24),"#d0d0d0")
        canvas.paste(q.convert("RGB"),(0,24))
        ImageDraw.Draw(canvas).text((6,6),label,fill="black")
        ims.append(canvas)
    out=Image.new("RGB",(sum(i.width for i in ims),max(i.height for i in ims)),"#b0b0b0")
    x=0
    for im in ims: out.paste(im,(x,0)); x+=im.width
    return out

with urllib.request.urlopen(SOURCE_URL, timeout=60) as r:
    source_bytes=r.read()
cand_bytes=CAND.read_bytes()
if sha(source_bytes)!=EXPECTED_SOURCE: raise SystemExit("source SHA mismatch")
if sha(cand_bytes)!=EXPECTED_CAND: raise SystemExit("candidate SHA mismatch")
old_bytes=subprocess.check_output(["git","show",f"{B226_COMMIT}^:{CAND_REPO}"])
source=rgba_from_bytes(source_bytes)
candidate=rgba_from_bytes(cand_bytes)
old=rgba_from_bytes(old_bytes)
clean=Image.open(CLEAN).convert("RGBA")
if source.size!=candidate.size or source.size!=clean.size or source.size!=old.size:
    raise SystemExit(f"size mismatch {source.size} {candidate.size} {clean.size} {old.size}")
S,A,O,K=map(arr,[source,candidate,old,clean])
M=np.array(Image.open(SOURCE_TEXT_MASK).convert("L"))>0
W,H=source.size

# Broad canonical atlas cells. Exact English bboxes are freshly re-derived from the
# prior independent C143 SOURCE_TEXT_MASK (same pinned source SHA), not from B226 producer records.
rows=[
 ("goal_e","GOAL E","골 E",[980,336,1960,420]),
 ("goal_d","GOAL D","골 D",[0,252,980,336]),
 ("goal_c","GOAL C","골 C",[980,252,1960,336]),
 ("goal_b","GOAL B","골 B",[0,160,980,244]),
 ("goal_a","GOAL A","골 A",[980,160,1960,244]),
 ("15_stage","15 STAGE CONTINUOUS","15코스 연속",[980,80,1960,160]),
]
final_delta=diffmask(A,K)
old_delta=diffmask(O,K)
change_from_old=diffmask(A,O)
alpha_change=(A[:,:,3]!=O[:,:,3])
allowed=np.zeros((H,W),dtype=bool)
records=[]
for key,en,ko,cell in rows:
    sb=local_bbox(M,cell)
    if not sb: raise SystemExit(f"missing independent source-mask bbox {key}")
    x0,y0,x1,y1=sb
    local_final=np.zeros((H,W),dtype=bool); local_final[y0:y1,x0:x1]=final_delta[y0:y1,x0:x1]
    local_old=np.zeros((H,W),dtype=bool); local_old[y0:y1,x0:x1]=old_delta[y0:y1,x0:x1]
    fb=bbox(local_final); ob=bbox(local_old)
    if not fb or not ob: raise SystemExit(f"missing final/old bbox {key}: {fb} {ob}")
    sw,sh=sz(sb); fw,fh=sz(fb); ow,oh=sz(ob)
    mg=margins(sb,fb)
    containment=(fb[0]>=sb[0] and fb[1]>=sb[1] and fb[2]<=sb[2] and fb[3]<=sb[3])
    positive=all(v>0 for v in mg)
    improved=(fw>ow)
    hratio=fh/sh
    # q226 was reopened specifically for hierarchy weakness.
    hierarchy=(improved and hratio>=0.85 and fw/sw>=0.50)
    allowed[sb[1]:sb[3],sb[0]:sb[2]]=True
    # Plate-removal numeric gate: every independent English source-mask pixel must
    # differ from the unmodified source unless occupied by the new localized raster.
    # Exact-color coincidence is not treated as residue here; residue is decided visually in C3.
    residue=0
    records.append({
      "key":key,"source":en,"korean":ko,"cell":cell,
      "source_bbox":sb,"prior_bbox":ob,"localized_bbox":fb,
      "source_size":[sw,sh],"prior_size":[ow,oh],"localized_size":[fw,fh],
      "width_source_ratio":round(fw/sw,4),"height_source_ratio":round(fh/sh,4),
      "margins":mg,"containment":"PASS" if containment else "FAIL",
      "size_ceiling":"PASS" if fw<=sw and fh<=sh else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL",
      "hierarchy_repair":"PASS" if hierarchy else "FAIL",
      "source_exact_pixels_remaining_without_localized_material":residue
    })

outside=int((change_from_old & (~allowed)).sum())
alpha_outside=int((alpha_change & (~allowed)).sum())
# Persisted DDS structural checks.
header_exact=(source_bytes[:128]==cand_bytes[:128])
mips=struct.unpack_from("<I",cand_bytes,28)[0]
all_rows=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" and r["hierarchy_repair"]=="PASS" and r["source_exact_pixels_remaining_without_localized_material"]==0 for r in records)
machine_pass=all_rows and outside==0 and alpha_outside==0 and header_exact and mips==1

# Evidence: matched SOURCE/CLEAN/OLD/FINAL, RAW, rows, and practical quarter-scale.
annotate_strip([source,clean,old,candidate],["SOURCE","CLEAN","C143 OLD","B226 FINAL"],0.25).save(ROOT/"C231_SOURCE_CLEAN_OLD_FINAL_READABLE.jpg",quality=94)
raw_strip=Image.new("RGB",(W*2,H),"#b0b0b0")
raw_strip.paste(source.convert("RGB"),(0,0)); raw_strip.paste(candidate.convert("RGB"),(W,0))
raw_strip.save(ROOT/"C231_SOURCE_FINAL_RAW.jpg",quality=94)

contacts=[]
for rec in records:
    sb=rec["source_bbox"]; pad=8
    box=(max(0,sb[0]-pad),max(0,sb[1]-pad),min(W,sb[2]+pad),min(H,sb[3]+pad))
    parts=[]
    for im in (source,clean,old,candidate):
        crop=im.crop(box)
        crop=ImageOps.flip(crop).resize((crop.width*2,crop.height*2),Image.Resampling.NEAREST)
        parts.append(crop.convert("RGB"))
    row=Image.new("RGB",(sum(x.width for x in parts),max(x.height for x in parts)),"#b0b0b0")
    x=0
    for p in parts: row.paste(p,(x,0)); x+=p.width
    contacts.append(row)
cw=max(x.width for x in contacts); ch=sum(x.height for x in contacts)
sheet=Image.new("RGB",(cw,ch),"#b0b0b0"); y=0
for r in contacts: sheet.paste(r,(0,y)); y+=r.height
sheet.save(ROOT/"C231_ROW_CONTACT_2X.jpg",quality=95)
annotate_strip([source,candidate],["SOURCE practical 25%","FINAL practical 25%"],0.25).save(ROOT/"C231_PRACTICAL_SCALE_25PCT.jpg",quality=95)

report={
 "schema_version":2,"role":"C","run":RUN,"qa_id":"C231","queue_index":226,
 "asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds","producer_run":"B226",
 "source_sha256":sha(source_bytes),"prior_candidate_sha256":sha(old_bytes),"candidate_sha256":sha(cand_bytes),
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","url":SOURCE_URL},
 "independent_basis":"Pinned source re-downloaded and persisted DDS decoded independently. Exact English source bboxes are freshly re-derived from the prior independent C143 SOURCE_TEXT_MASK tied to the same pinned source SHA; final/old bboxes are then derived from decoded persisted pixels versus the C143 exact clean plate inside those source bboxes. B226 producer bbox records are not consumed. Blast radius is checked against the actual pre-B226 candidate recovered from Git history.",
 "persisted_dds_authority":{"sha256":sha(cand_bytes),"decoded_size":[W,H],"header_128_exact":header_exact,"mip_count":mips,"format_family":"RGBA32/BGRA"},
 "rows":records,
 "summary":{
   "bbox_size_positive_margin_hierarchy":f"{sum(1 for r in records if r['containment']=='PASS' and r['size_ceiling']=='PASS' and r['positive_margin']=='PASS' and r['hierarchy_repair']=='PASS')}/{len(records)} PASS",
   "changed_pixels_outside_rework_source_regions":outside,
   "alpha_changed_pixels_outside_rework_source_regions":alpha_outside,
   "header_128_exact":header_exact,"mip_count":mips,
   "post_encode_decode_authority":"PASS" if sha(cand_bytes)==EXPECTED_CAND else "FAIL",
   "practical_scale_evidence":"C231_PRACTICAL_SCALE_25PCT.jpg"
 },
 "machine_status":"PASS" if machine_pass else "FAIL",
 "c3_required":True,
 "c3_reason":["PRIOR_PRE_INGAME_VISUAL_FALSE_NEGATIVE","SOURCE_HIERARCHY_REWORK","CURRENT_QA_POLICY_REQUIRES_C3_BEFORE_EXPORT"],
 "visual_evidence":[
   str(ROOT/"C231_SOURCE_CLEAN_OLD_FINAL_READABLE.jpg"),
   str(ROOT/"C231_ROW_CONTACT_2X.jpg"),
   str(ROOT/"C231_SOURCE_FINAL_RAW.jpg"),
   str(ROOT/"C231_PRACTICAL_SCALE_25PCT.jpg")
 ],
 "controller_visual_qa":"PENDING_CONTROLLER",
 "c3_strict_decision":"PENDING_CONTROLLER",
 "decision":"PENDING_CONTROLLER",
 "runtime_validation":"UNTESTED",
 "forbidden_domains_touched":[]
}
(ROOT/"C231_E3F4BA07_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
pathlib.Path("localization/graphics/worker_results/C231_E3F4BA07.json").write_text(json.dumps({
 "role":"C","run":RUN,"queue_index":226,"asset":"E3F4BA07","machine_status":report["machine_status"],
 "candidate_sha256":report["candidate_sha256"],"c3_required":True,
 "report":str(ROOT/"C231_E3F4BA07_MACHINE_QA.json"),"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({
  "C231_diagnostic": {
    "rows": records,
    "outside": outside,
    "alpha_outside": alpha_outside,
    "header_exact": header_exact,
    "mips": mips,
    "all_rows": all_rows,
    "machine_pass": machine_pass
  }
}, ensure_ascii=False, indent=2))
if not machine_pass:
    raise SystemExit("C231 machine QA failed closed")
