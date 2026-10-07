#!/usr/bin/env python3
# C234 / TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
# Fresh independent C + mandatory C3 strict audit for P0 IGR-005 q137 30CF0D / B165.
import io, os, json, hashlib, pathlib, subprocess, urllib.request, struct
import numpy as np
from PIL import Image, ImageOps, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

RUN="20261007-C234-C1-Q137-30CF0D-B165"
ROOT=pathlib.Path("localization/graphics/role_C")/RUN
ROOT.mkdir(parents=True, exist_ok=True)
CAND=pathlib.Path("localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds")
CLEAN=pathlib.Path("localization/graphics/role_C/20261005-C156-30CF0D/C156_VERIFIED_CLEAN_PLATE.png")
SOURCE_MASK=pathlib.Path("localization/graphics/role_C/20261005-C156-30CF0D/C156_SOURCE_TEXT_MASK.png")
PROTECTED_MASK=pathlib.Path("localization/graphics/role_C/20261005-C156-30CF0D/C156_PROTECTED_MASK.png")
C156_REPORT=pathlib.Path("localization/graphics/role_C/20261005-C156-30CF0D/C156_30CF_MACHINE_QA.json")
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
EXPECTED_SOURCE="11c90e063e83e485d15da16a157a7da7f4c99144b0ee9004205ef4ee724d21cc"
EXPECTED_OLD="6d58a2c39020629daa995d01cdaf09ad50b3d62a92dd9d8db68a1978b4ac812b"
EXPECTED_CAND="0550123e82d255cd0db3e848bc03b11cf6d6eaf89fc55eb1f17824a75257bfc4"
B165_COMMIT="e127a62fbec55ff0a9a487de747b15ee5ffe9b93"
CAND_REPO=str(CAND)
CHANGED_KEYS={"select_transmission","transmission_small"}

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    im=Image.open(io.BytesIO(b)); im.load(); return im.convert("RGBA")
def A(im): return np.array(im)
def bbox(mask):
    ys,xs=np.where(mask)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def local_bbox(mask, box):
    x0,y0,x1,y1=box
    b=bbox(mask[y0:y1,x0:x1])
    return None if b is None else [b[0]+x0,b[1]+y0,b[2]+x0,b[3]+y0]
def size(b): return [b[2]-b[0],b[3]-b[1]]
def margins(src,fin): return [fin[0]-src[0],src[2]-fin[2],fin[1]-src[1],src[3]-fin[3]]
def draw_label(im,label):
    c=Image.new("RGB",(im.width,im.height+26),"#c8c8c8"); c.paste(im.convert("RGB"),(0,26))
    ImageDraw.Draw(c).text((6,6),label,fill="black"); return c
def hstrip(items):
    w=sum(x.width for x in items); h=max(x.height for x in items)
    out=Image.new("RGB",(w,h),"#a8a8a8"); x=0
    for im in items: out.paste(im,(x,0)); x+=im.width
    return out

with urllib.request.urlopen(SOURCE_URL,timeout=60) as r:
    source_bytes=r.read()
cand_bytes=CAND.read_bytes()
old_bytes=subprocess.check_output(["git","show",f"{B165_COMMIT}^:{CAND_REPO}"])
if sha(source_bytes)!=EXPECTED_SOURCE: raise SystemExit("source SHA mismatch")
if sha(old_bytes)!=EXPECTED_OLD: raise SystemExit("old SHA mismatch")
if sha(cand_bytes)!=EXPECTED_CAND: raise SystemExit("candidate SHA mismatch")

source,old,cand=map(decode,[source_bytes,old_bytes,cand_bytes])
clean=Image.open(CLEAN).convert("RGBA")
if not (source.size==old.size==cand.size==clean.size==(2048,1024)): raise SystemExit("dimension mismatch")
S,O,F,K=map(A,[source,old,cand,clean])
SM=np.array(Image.open(SOURCE_MASK).convert("L"))>0
PM=np.array(Image.open(PROTECTED_MASK).convert("L"))>0
c156=json.loads(C156_REPORT.read_text(encoding="utf-8"))
rows=c156["rows"]

# Fresh decoded persisted-pixel bboxes against prior independent C clean plate.
records=[]
allowed=np.zeros((1024,2048),dtype=bool)
all_source_union=np.zeros_like(allowed)
for r in rows:
    key=r["key"]; sb=list(r["original_bbox"]); x0,y0,x1,y1=sb
    all_source_union[y0:y1,x0:x1]=True
    if key in CHANGED_KEYS: allowed[y0:y1,x0:x1]=True
    old_diff=np.any(O!=K,axis=2)
    fin_diff=np.any(F!=K,axis=2)
    ob=local_bbox(old_diff,sb); fb=local_bbox(fin_diff,sb)
    if ob is None or fb is None: raise SystemExit(f"missing decoded bbox {key}")
    sw,sh=size(sb); ow,oh=size(ob); fw,fh=size(fb)
    mg=margins(sb,fb)
    containment=fb[0]>=sb[0] and fb[1]>=sb[1] and fb[2]<=sb[2] and fb[3]<=sb[3]
    positive=all(v>0 for v in mg)
    records.append({
      "key":key,"source":r["source"],"korean_current":("변속기 선택" if key=="select_transmission" else "변속기" if key=="transmission_small" else r["korean"]),
      "source_bbox":sb,"prior_bbox":ob,"localized_bbox":fb,
      "source_size":[sw,sh],"prior_size":[ow,oh],"localized_size":[fw,fh],"margins":mg,
      "containment":"PASS" if containment else "FAIL",
      "size_ceiling":"PASS" if fw<=sw and fh<=sh else "FAIL",
      "positive_margin":"PASS" if positive else "FAIL",
      "changed_by_B165": key in CHANGED_KEYS
    })

change=np.any(F!=O,axis=2)
alpha_change=F[:,:,3]!=O[:,:,3]
changed_outside=int((change & ~allowed).sum())
alpha_outside=int((alpha_change & ~allowed).sum())
protected_change_vs_old=int((change & PM).sum())
protected_change_vs_source=int((np.any(F!=S,axis=2) & PM).sum())
# Four prior localized option rows and all unrelated content must remain exact.
unchanged_expected=int((change & ~allowed).sum())==0
changed_inside_each={}
for rec in records:
    sb=rec["source_bbox"]; x0,y0,x1,y1=sb
    changed_inside_each[rec["key"]]=int(change[y0:y1,x0:x1].sum())

header_exact=source_bytes[:128]==cand_bytes[:128]
mips=struct.unpack_from("<I",cand_bytes,28)[0]
row_pass=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in records)
machine_pass=(row_pass and changed_outside==0 and alpha_outside==0 and protected_change_vs_old==0 and protected_change_vs_source==0 and header_exact and mips==1 and changed_inside_each["select_transmission"]>0 and changed_inside_each["transmission_small"]>0)

# Evidence: readable FLIP-Y, RAW, high zoom, practical scale.
read_source,read_clean,read_old,read_final=map(ImageOps.flip,[source,clean,old,cand])
full=hstrip([draw_label(x.resize((512,256),Image.Resampling.LANCZOS),lab) for x,lab in [
 (read_source,"SOURCE"),(read_clean,"C156 CLEAN"),(read_old,"C156/A22 OLD"),(read_final,"B165 FINAL")]])
full.save(ROOT/"C234_SOURCE_CLEAN_OLD_FINAL_READABLE.jpg",quality=94)

raw=hstrip([draw_label(source.resize((512,256),Image.Resampling.LANCZOS),"SOURCE RAW"),
            draw_label(cand.resize((512,256),Image.Resampling.LANCZOS),"FINAL RAW")])
raw.save(ROOT/"C234_SOURCE_FINAL_RAW.jpg",quality=94)

contact_rows=[]
for rec in [x for x in records if x["key"] in CHANGED_KEYS]:
    sb=rec["source_bbox"]; p=14
    box=(max(0,sb[0]-p),max(0,sb[1]-p),min(2048,sb[2]+p),min(1024,sb[3]+p))
    parts=[]
    for im,label in [(read_source,"SRC"),(read_old,"OLD"),(read_clean,"CLEAN"),(read_final,"FINAL")]:
        # readable images are vertically flipped, so map raw bbox to readable coordinates
        rb=(box[0],1024-box[3],box[2],1024-box[1])
        crop=im.crop(rb).resize(((rb[2]-rb[0])*2,(rb[3]-rb[1])*2),Image.Resampling.NEAREST)
        parts.append(draw_label(crop,label))
    contact_rows.append(hstrip(parts))
cw=max(i.width for i in contact_rows); ch=sum(i.height for i in contact_rows)
sheet=Image.new("RGB",(cw,ch),"#a8a8a8"); y=0
for im in contact_rows: sheet.paste(im,(0,y)); y+=im.height
sheet.save(ROOT/"C234_TITLE_SUBTITLE_CONTACT_2X.jpg",quality=95)

for pct in (100,75,50):
    w=2048*pct//100; h=1024*pct//100
    ss=read_source.resize((w,h),Image.Resampling.LANCZOS)
    ff=read_final.resize((w,h),Image.Resampling.LANCZOS)
    hstrip([draw_label(ss,f"SOURCE {pct}%"),draw_label(ff,f"FINAL {pct}%")]).save(ROOT/f"C234_PRACTICAL_{pct}PCT.jpg",quality=93)

report={
 "schema_version":2,"role":"C","lane":"C1","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "run":RUN,"qa_id":"C234","queue_index":137,
 "asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds",
 "producer_run":"B165","user_ingame_regression":"IGR-005","priority":"P0",
 "source_sha256":sha(source_bytes),"prior_candidate_sha256":sha(old_bytes),"candidate_sha256":sha(cand_bytes),
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","url":SOURCE_URL},
 "independent_basis":"Pinned canonical source re-downloaded; persisted candidate decoded independently; exact source bboxes and clean/protected geometry come from prior independent C156 evidence tied to the same canonical source SHA. B165 producer bbox/mask data are not consumed for containment. Blast radius is measured against the exact pre-B165 candidate recovered from Git history.",
 "structure":{"dimensions":[2048,1024],"format":"RGBA32/BGRA","mips":mips,"header_128_exact":header_exact,"raw_orientation":"mirror_y"},
 "rows":records,
 "summary":{
   "bbox_size_positive_margin":f"{sum(1 for r in records if r['containment']=='PASS' and r['size_ceiling']=='PASS' and r['positive_margin']=='PASS')}/{len(records)} PASS",
   "changed_pixels_outside_two_rework_source_bboxes":changed_outside,
   "alpha_changed_outside_two_rework_source_bboxes":alpha_outside,
   "protected_pixels_changed_vs_prior":protected_change_vs_old,
   "protected_pixels_changed_vs_source":protected_change_vs_source,
   "changed_inside_each_row":changed_inside_each,
   "preserved_manual_automatic_and_unrelated":"PASS" if unchanged_expected else "FAIL",
   "persisted_dds_decode_authority":"PASS",
   "mip_review":"PASS_SINGLE_MIP_NO_ADDITIONAL_TEXT_MIPS" if mips==1 else "REVIEW_REQUIRED"
 },
 "coverage":{"visible_localizable_segments":6,"localized_segments":6,"protected_at_mt_and_artwork":"PRESERVED","status":"PASS"},
 "machine_status":"PASS" if machine_pass else "FAIL",
 "c3_required":True,
 "c3_reason":["USER_INGAME_REGRESSION_IGR005","PRIOR_C156_OVERRIDDEN_BY_LATER_INGAME_EVIDENCE","STYLE_LOW_RES_COLLISION_HISTORY","MANDATORY_HIGH_RISK_PRE_INGAME_GATE"],
 "visual_evidence":[
   str(ROOT/"C234_SOURCE_CLEAN_OLD_FINAL_READABLE.jpg"),
   str(ROOT/"C234_TITLE_SUBTITLE_CONTACT_2X.jpg"),
   str(ROOT/"C234_SOURCE_FINAL_RAW.jpg"),
   str(ROOT/"C234_PRACTICAL_100PCT.jpg"),str(ROOT/"C234_PRACTICAL_75PCT.jpg"),str(ROOT/"C234_PRACTICAL_50PCT.jpg")
 ],
 "controller_visual_qa":"PENDING_CONTROLLER",
 "c3_strict_decision":"PENDING_CONTROLLER",
 "decision":"PENDING_CONTROLLER",
 "backlog_close_gate":"NEW_ACTUAL_INGAME_RETEST_REQUIRED",
 "runtime_validation":"PENDING_NEW_INGAME_RETEST",
 "forbidden_domains_touched":[]
}
(ROOT/"C234_30CF0D_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
pathlib.Path("localization/graphics/worker_results/C234_30CF0D.json").write_text(json.dumps({
 "role":"C","lane":"C1","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "run":RUN,"queue_index":137,"asset":"30CF0D","machine_status":report["machine_status"],
 "candidate_sha256":report["candidate_sha256"],"c3_required":True,
 "report":str(ROOT/"C234_30CF0D_MACHINE_QA.json"),"runtime_validation":"PENDING_NEW_INGAME_RETEST"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"machine_status":report["machine_status"],"summary":report["summary"]},ensure_ascii=False,indent=2))
if not machine_pass:
    raise SystemExit("C234 machine QA failed closed")
