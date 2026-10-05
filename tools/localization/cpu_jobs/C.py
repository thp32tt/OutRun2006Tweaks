#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,base64,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C180-560FA536"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
pd=repo/"localization/graphics/role_A/20261005-A-PRODUCTION38"
pr=json.loads((pd/"A38_560FA536_REPORT.json").read_text())
asset=pr["asset"]; candidate=repo/pr["candidate_path"]
src_commit=pr["source_provenance"]["commit"]
expected_source_sha=pr["source_provenance"]["sha256"]
expected_candidate_sha=pr["candidate_sha256"]
folder=asset.split("/")[-2]; name=asset.split("/")[-1]
tmp=Path("/tmp/c180"); tmp.mkdir(exist_ok=True)
srcdds=tmp/"source.dds"
prevdds=tmp/"a36.dds"
urllib.request.urlretrieve(f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{src_commit}/Release/{folder}/{name}",srcdds)
# Previous rejected C179 input: A36 exact candidate, used only for regression-diff confinement.
urllib.request.urlretrieve(
    f"https://raw.githubusercontent.com/thp32tt/OutRun2006Tweaks/d049d2357e858af01a9b969ef1de05244fc453ec/localization/graphics/hd_candidates/{asset}",
    prevdds
)

def sha(b): return hashlib.sha256(b).hexdigest()
def count(m): return int(np.count_nonzero(m))
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def decode(data):
    if data[:4]!=b"DDS ": raise RuntimeError("not dds")
    H,W,pitch,depth,mips=struct.unpack_from("<5I",data,12)
    pf=struct.unpack_from("<8I",data,76); masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if mode is None or len(data)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(data)))
    raw=Image.frombytes("RGBA",(W,H),data[128:],"raw",mode)
    return raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),raw,[W,H],mips,mode
def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_b64_jpg(im,path,quality=94):
    bio=io.BytesIO(); im.save(bio,"JPEG",quality=quality,optimize=True)
    path.write_text(base64.b64encode(bio.getvalue()).decode("ascii"))

sb=srcdds.read_bytes(); cb=candidate.read_bytes(); pb=prevdds.read_bytes()
if sha(sb)!=expected_source_sha: raise RuntimeError(("source sha drift",sha(sb),expected_source_sha))
if sha(cb)!=expected_candidate_sha: raise RuntimeError(("candidate sha drift",sha(cb),expected_candidate_sha))
if sha(pb)!="4b4dbb1f645c526fb812e500c01a0fa03894dc1aff2267682ea9f8b283c05744":
    raise RuntimeError(("A36 predecessor drift",sha(pb)))
src,raw_src,dims,mips,mode=decode(sb)
final,raw_final,dims2,mips2,mode2=decode(cb)
prev,raw_prev,dims3,mips3,mode3=decode(pb)
if dims!=[4096,4096] or dims2!=dims or dims3!=dims or mips2!=mips or mips3!=mips or cb[:128]!=sb[:128] or pb[:128]!=sb[:128]:
    raise RuntimeError("structure/header drift")
W,H=dims
prodsrc=Image.open(pd/"560FA536_HD_SOURCE_READABLE.png").convert("RGBA")
if ImageChops.difference(src,prodsrc).getbbox(): raise RuntimeError("producer source PNG differs from independent canonical decode")
clean=Image.open(pd/"560FA536_HD_CLEAN_PLATE.png").convert("RGBA")
sa=np.asarray(src,dtype=np.uint8); ca=np.asarray(clean,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8); pa=np.asarray(prev,dtype=np.uint8)

rows=pr["rows"]; allowed=np.zeros((H,W),bool); rowchecks=[]
for r in rows:
    ob=[int(v) for v in r["source_effect_bbox"]]; lb=[int(v) for v in r["localized_bbox"]]
    x0,y0,x1,y1=ob; a,b,c,d=lb; allowed[y0:y1,x0:x1]=True
    dl,dr,dt,db=a-x0,x1-c,b-y0,y1-d
    rowchecks.append({
      "idx":r["idx"],"kind":r.get("kind"),"korean_lines":r.get("korean_lines"),
      "original_bbox":ob,"localized_bbox":lb,
      "delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,
      "containment":"PASS" if a>=x0 and b>=y0 and c<=x1 and d<=y1 else "FAIL",
      "size_ceiling":"PASS" if c-a<=x1-x0 and d-b<=y1-y0 else "FAIL",
      "positive_margin":"PASS" if min(dl,dr,dt,db)>0 else "FAIL"
    })
if len(rowchecks)!=13: raise RuntimeError(("row count",len(rowchecks)))

cdiff=np.any(ca!=sa,axis=2)
fdiff=np.any(fa!=sa,axis=2)
render=np.any(fa!=ca,axis=2)
machine={
 "clean_changed_outside_union_source_bboxes":count(cdiff&~allowed),
 "final_changed_outside_union_source_bboxes":count(fdiff&~allowed),
 "clean_alpha_outside_union_source_bboxes":count((ca[:,:,3]!=sa[:,:,3])&~allowed),
 "final_alpha_outside_union_source_bboxes":count((fa[:,:,3]!=sa[:,:,3])&~allowed),
 "render_outside_union_source_bboxes":count(render&~allowed)
}

# Independently audit the corrected warning-row extent against the canonical source.
warn=next(x for x in rowchecks if x["idx"]==31)
wx0,wy0,wx1,wy1=warn["original_bbox"]
if warn["original_bbox"]!=[3006,25,3932,168]:
    raise RuntimeError(("unexpected corrected warning bbox",warn["original_bbox"]))
# Extended visual/audit band intentionally reaches left of both C179 and A38 boxes.
audit=[2850,0,4096,205]
ax0,ay0,ax1,ay1=audit
# A38 should differ from the exact A36 predecessor only inside the newly expanded warning edit region.
prev_diff=np.any(fa!=pa,axis=2)
warning_allowed=np.zeros((H,W),bool); warning_allowed[wy0:wy1,wx0:wx1]=True
machine["a38_vs_a36_changed_outside_corrected_warning_bbox"]=count(prev_diff&~warning_allowed)
machine["a38_vs_a36_changed_inside_corrected_warning_bbox"]=count(prev_diff&warning_allowed)
# Confirm A38 actually changed pixels in the newly admitted left strip [3006,3074).
new_strip=np.zeros((H,W),bool); new_strip[25:168,3006:3074]=True
machine["a38_vs_a36_changed_in_new_left_strip"]=count(prev_diff&new_strip)
# Source-to-clean changed footprint inside warning box and exact residual equality after Korean render.
warnmask=np.zeros((H,W),bool); warnmask[wy0:wy1,wx0:wx1]=True
warn_removed=cdiff & warnmask
rguard=np.asarray(Image.fromarray((render.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(5)))>0
machine["warning_clean_changed_pixels"]=count(warn_removed)
machine["warning_removed_source_pixels_unchanged_in_final_outside_korean_guard"]=count(warn_removed & np.all(fa==sa,axis=2) & ~rguard)
# Look for source->clean changes in the 68px newly admitted strip to prove the correction is material.
machine["warning_clean_changed_in_new_left_strip"]=count(cdiff & new_strip)
# No A38 clean/final edits may touch the left audit ring outside corrected warning box.
left_ring=np.zeros((H,W),bool); left_ring[0:205,2850:3006]=True
machine["warning_clean_changed_in_left_audit_ring_outside_bbox"]=count(cdiff&left_ring)
machine["warning_final_changed_in_left_audit_ring_outside_bbox"]=count(fdiff&left_ring)

# Producer protected mask is used only as an integrity cross-check; canonical source identity is independently pinned above.
protected=np.asarray(Image.open(pd/"560FA536_HD_PROTECTED_VISIBLE_MASK.png").convert("L"))>0
machine["protected_clean_changed"]=count(cdiff&protected)
machine["protected_final_changed"]=count(fdiff&protected)

# Pairwise localized separation using final-clean render masks within each declared source cell.
masks=[]
for rc in rowchecks:
    x0,y0,x1,y1=rc["original_bbox"]; m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=render[y0:y1,x0:x1]; masks.append(m)
ov=touch=0
for i,mi in enumerate(masks):
    di=np.asarray(Image.fromarray((mi.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0
    for mj in masks[i+1:]:
        ov+=count(mi&mj); touch+=count(di&mj)
machine["localized_pair_overlap_pixels"]=ov
machine["localized_pair_1px_touch_pixels"]=touch

hard_zero_keys=[
 "clean_changed_outside_union_source_bboxes","final_changed_outside_union_source_bboxes",
 "clean_alpha_outside_union_source_bboxes","final_alpha_outside_union_source_bboxes",
 "render_outside_union_source_bboxes","a38_vs_a36_changed_outside_corrected_warning_bbox",
 "warning_removed_source_pixels_unchanged_in_final_outside_korean_guard",
 "warning_clean_changed_in_left_audit_ring_outside_bbox","warning_final_changed_in_left_audit_ring_outside_bbox",
 "protected_clean_changed","protected_final_changed","localized_pair_overlap_pixels","localized_pair_1px_touch_pixels"
]
rowpass=all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["positive_margin"]=="PASS" for x in rowchecks)
material_fix=machine["a38_vs_a36_changed_in_new_left_strip"]>0 and machine["warning_clean_changed_in_new_left_strip"]>0
status="PASS" if rowpass and material_fix and all(machine[k]==0 for k in hard_zero_keys) else "FAIL"

# Evidence 1: all 13 SOURCE/CLEAN/FINAL row contacts.
font=ImageFont.load_default(); cards=[]
for rc in rowchecks:
    x0,y0,x1,y1=rc["original_bbox"]; pad=24
    crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    ims=[comp(z).crop(crop) for z in (src,clean,final)]
    th=min(220,max(100,max(z.height for z in ims))); rr=[]
    for z in ims:
        if z.height>th: z=z.resize((max(1,round(z.width*th/z.height)),th),Image.Resampling.LANCZOS)
        rr.append(z)
    pw=max(330,max(z.width for z in rr))
    card=Image.new("RGB",(pw*3+24,th+34),"white"); d=ImageDraw.Draw(card)
    for ci,(lab,z) in enumerate(zip(("SOURCE","CLEAN","FINAL"),rr)):
        ox=ci*pw+8; card.paste(z,(ox,28)); d.text((ox,6),lab,fill="black",font=font)
    d.text((pw*2+120,6),f"idx {rc['idx']} {rc.get('kind','')}",fill="black",font=font)
    cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8*(len(cards)-1)),"white")
yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+8
if sheet.width>1900: sheet=sheet.resize((1900,round(sheet.height*1900/sheet.width)),Image.Resampling.LANCZOS)
save_b64_jpg(sheet,out/"C180_ALL_CONTACTS_B64.txt",93)

# Evidence 2: expanded warning-row audit, well beyond corrected box on both sides.
audit_ims=[comp(z).crop(tuple(audit)) for z in (src,clean,final)]
scale=1
aw,ah=audit_ims[0].size
detail=Image.new("RGB",(aw*3,ah+30),"white"); dd=ImageDraw.Draw(detail)
for i,(lab,z) in enumerate(zip(("SOURCE_EXTENDED","CLEAN_EXTENDED","FINAL_EXTENDED"),audit_ims)):
    detail.paste(z,(i*aw,30)); dd.text((i*aw+5,6),lab,fill="black",font=font)
# Draw corrected bbox boundary positions relative to audit for orientation.
for x in (wx0,wx1):
    rx=x-ax0
    if 0<=rx<aw:
        for i in range(3): dd.line((i*aw+rx,30,i*aw+rx,30+ah-1),fill="red",width=1)
save_b64_jpg(detail,out/"C180_WARNING_EXTENDED_B64.txt",96)

# Evidence 3: A36 vs A38 warning-only regression comparison.
prev_crop=comp(prev).crop(tuple(audit)); final_crop=comp(final).crop(tuple(audit))
reg=Image.new("RGB",(aw*2,ah+30),"white"); rd=ImageDraw.Draw(reg)
reg.paste(prev_crop,(0,30)); reg.paste(final_crop,(aw,30))
rd.text((5,6),"A36_PREVIOUS_REJECTED",fill="black",font=font); rd.text((aw+5,6),"A38_CURRENT",fill="black",font=font)
save_b64_jpg(reg,out/"C180_A36_A38_WARNING_COMPARE_B64.txt",96)

# Evidence 4: raw orientation full-atlas overview.
rawcard=Image.new("RGB",(1024,2070),"white")
for i,(lab,z) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_final))):
    zz=comp(z).resize((1024,1024),Image.Resampling.LANCZOS); rawcard.paste(zz,(0,i*1035+22)); ImageDraw.Draw(rawcard).text((5,i*1035+4),lab,fill="black")
save_b64_jpg(rawcard,out/"C180_RAW_B64.txt",90)

report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C180","queue_index":pr["index"],"asset":asset,
 "producer_run":pr["run"],"source_sha256":expected_source_sha,"candidate_sha256":expected_candidate_sha,
 "predecessor_a36_candidate_sha256":"4b4dbb1f645c526fb812e500c01a0fa03894dc1aff2267682ea9f8b283c05744",
 "independent_source_decode_matches_producer_png":True,
 "structure":{"dimensions":dims,"format":"RGBA32","mipmaps":mips,"raw_orientation":"mirror_y","header_exact":cb[:128]==sb[:128]},
 "row_checks":rowchecks,"all_13_bbox_size_positive_margin_pass":rowpass,
 "warning_audit":{"corrected_source_effect_bbox":[3006,25,3932,168],"prior_c179_bbox":[3074,25,3932,168],"extended_visual_audit_bbox":audit,"material_fix_present":material_fix},
 "machine_checks":machine,"machine_status":status,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C180_REWORK_REQUIRED_MACHINE_GATE",
 "runtime_validation":"UNTESTED",
 "preview_b64_files":[
  "localization/graphics/role_C/20261005-C180-560FA536/C180_ALL_CONTACTS_B64.txt",
  "localization/graphics/role_C/20261005-C180-560FA536/C180_WARNING_EXTENDED_B64.txt",
  "localization/graphics/role_C/20261005-C180-560FA536/C180_A36_A38_WARNING_COMPARE_B64.txt",
  "localization/graphics/role_C/20261005-C180-560FA536/C180_RAW_B64.txt"
 ]
}
(out/"C180_560FA536_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"C180_560FA536.json").write_text(json.dumps({
 "run":run,"qa_id":"C180","index":pr["index"],"asset":"560FA536","candidate_sha256":expected_candidate_sha,
 "machine_status":status,"all_13_bbox_size_positive_margin_pass":rowpass,"warning_material_fix_present":material_fix,
 "machine_checks":machine,"report":f"localization/graphics/role_C/{run}/C180_560FA536_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"qa_id":"C180","machine_status":status,"material_fix":material_fix,"machine_checks":machine},ensure_ascii=False))
