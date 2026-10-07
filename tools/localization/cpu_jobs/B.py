#!/usr/bin/env python3
# B233: q100 53CE39D5 source-relative line-anchor repair.
# B-even has no active P0/P1 material return, direct REWORK, RENDER_READY or ONE_STAGE item.
# Current PRE_INGAME #005 exposes a source-placement false negative in the old C117 candidate:
# mode-card Korean rows are centered inside each exact source glyph bbox while the English family
# is left-anchored per line. Reposition accepted B30 Korean raster/effects only; no rerender.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib,json,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageChops

repo=Path.cwd()
run="20261007-B233-Q100-53CE39D5-ANCHOR"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_selector_cvt_Exst/53CE39D5_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION30/53CE39D5_HD_CLEAN_PLATE.png"
b30_report_path=repo/"localization/graphics/role_B/20261005-B-PRODUCTION30/B_PRODUCTION30_53CE_REPORT.json"
SOURCE_SHA="cfed1de58cefd8c235fc464e27058439ffd26427294a3bce17192e584679426a"
BEFORE_SHA="08467408b4ef087a8e2a5e8408b159e4f635fe0c261ad2ccae76a1499be5ced1"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/53CE39D5_512x512.dds"

tmp=Path("/tmp/b233"); tmp.mkdir(exist_ok=True)
src_dds=tmp/"source.dds"; urllib.request.urlretrieve(SOURCE_URL,src_dds)

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
    mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
    if mode is None or (w,h)!=(2048,2048) or len(b)!=128+w*h*4:
        raise RuntimeError(("DDS structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return raw,readable,{"w":w,"h":h,"mips":mips,"mode":mode}
def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def rectmask(h,w,bb):
    m=np.zeros((h,w),dtype=bool); x0,y0,x1,y1=bb; m[y0:y1,x0:x1]=True; return m
def changed(a,b): return np.any(a!=b,axis=2)
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255)); z.alpha_composite(im); return z.convert("RGB")

sb=src_dds.read_bytes(); ob=cand.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb),SOURCE_SHA))
if sha(ob)!=BEFORE_SHA: raise RuntimeError(("candidate drift",sha(ob),BEFORE_SHA))
sraw,src,meta=decode(sb); oraw,old,ometa=decode(ob)
if meta!=ometa or sb[:128]!=ob[:128]: raise RuntimeError("header/structure drift")
if meta["mips"]!=1: raise RuntimeError(("unexpected mips",meta["mips"]))
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=old.size: raise RuntimeError(("clean size",clean.size,old.size))
b30=json.loads(b30_report_path.read_text(encoding="utf-8"))
if b30.get("candidate_sha256")!=BEFORE_SHA: raise RuntimeError("B30 report candidate mismatch")

rows=b30["rows"]
selected=[r for r in rows if r["target"]!="random"]
if len(selected)!=18: raise RuntimeError(("expected 18 mode-card lines",len(selected)))
sa=np.asarray(src); oa=np.asarray(old); ca=np.asarray(clean)
H,W=oa.shape[:2]

# The old candidate is C117-accepted for clean plate, raster family, right slant and protection.
# Current hardening only reopens horizontal source placement: each line was centered inside its
# source glyph bbox. Reuse the exact accepted localized pixels and shift them to source-left +2.
final_np=oa.copy()
selected_allowed=np.zeros((H,W),bool)
all_allowed=np.zeros((H,W),bool)
for r in rows: all_allowed |= rectmask(H,W,r["original_bbox"])
for r in selected:
    bb=r["original_bbox"]; selected_allowed |= rectmask(H,W,bb)
    x0,y0,x1,y1=bb
    final_np[y0:y1,x0:x1]=ca[y0:y1,x0:x1]

new_masks=[]
outrows=[]
for r in selected:
    bb=r["original_bbox"]; lb_old=r["localized_bbox"]
    x0,y0,x1,y1=bb
    region_old=oa[y0:y1,x0:x1]
    region_clean=ca[y0:y1,x0:x1]
    dm=changed(region_old,region_clean)
    dmb=bbox(dm)
    if dmb is None: raise RuntimeError(("no localized diff",r["target"],r["line_index"]))
    global_diff=[x0+dmb[0],y0+dmb[1],x0+dmb[2],y0+dmb[3]]
    # Historical report bbox must match actual candidate-vs-clean localized footprint.
    if global_diff!=lb_old:
        raise RuntimeError(("localized bbox drift",r["target"],r["line_index"],global_diff,lb_old))
    dx=(x0+2)-lb_old[0]
    ys,xs=np.nonzero(dm)
    gxs=x0+xs; gys=y0+ys
    nxs=gxs+dx; nys=gys
    if nxs.min()<=x0 or nxs.max()>=x1-1:
        raise RuntimeError(("positive horizontal margin fail",r["target"],r["line_index"],int(nxs.min()),int(nxs.max()),bb))
    # Write exact accepted pixels at shifted coordinates onto the B30 validated clean plate.
    final_np[nys,nxs]=oa[gys,gxs]
    nm=np.zeros((H,W),bool); nm[nys,nxs]=True
    new_masks.append(nm)
    nb=bbox(nm)
    margins=[nb[0]-x0,x1-nb[2],nb[1]-y0,y1-nb[3]]
    outrows.append({
      "target":r["target"],"line_index":r["line_index"],"korean":r["korean"],
      "original_bbox":bb,"before_localized_bbox":lb_old,"final_localized_bbox":nb,
      "source_size":[x1-x0,y1-y0],"localized_size":[nb[2]-nb[0],nb[3]-nb[1]],
      "shift_x":dx,"margins":margins,
      "style_preservation":"PIXEL_EXACT_B30_LOCALIZED_RASTER_EFFECT_MOVED_ONLY",
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
    })

# Pairwise localized target isolation remains strict.
for i in range(len(new_masks)):
    for j in range(i+1,len(new_masks)):
        if np.count_nonzero(new_masks[i]&new_masks[j]):
            raise RuntimeError(("localized overlap",i,j))

final=Image.fromarray(final_np.astype(np.uint8),"RGBA")
# No previous-candidate collateral outside the 18 exact source-line bboxes.
prev_delta=changed(oa,final_np)
blast=int(np.count_nonzero(prev_delta&~selected_allowed))
alpha_blast=int(np.count_nonzero((oa[:,:,3]!=final_np[:,:,3])&~selected_allowed))
if blast or alpha_blast: raise RuntimeError(("blast radius",blast,alpha_blast))
# RANDOM and all protected/non-target content remain byte/pixel exact to the prior accepted candidate.
random_row=next(r for r in rows if r["target"]=="random")
rb=random_row["original_bbox"]; rx0,ry0,rx1,ry1=rb
if not np.array_equal(oa[ry0:ry1,rx0:rx1],final_np[ry0:ry1,rx0:rx1]):
    raise RuntimeError("RANDOM row drift")
# Canonical source-vs-final changes must remain inside the original 19 line bboxes.
if np.count_nonzero(changed(sa,final_np)&~all_allowed):
    raise RuntimeError("source-vs-final changed outside 19 source bboxes")

# Persist exact DDS/header/raw mirror-Y.
fraw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+fraw.tobytes("raw",meta["mode"])
cand.write_bytes(payload)
pb=cand.read_bytes(); after=sha(pb)
praw,persisted,pmeta=decode(pb)
if pmeta!=meta or pb[:128]!=sb[:128]: raise RuntimeError("persisted header/structure drift")
if ImageChops.difference(persisted,final).getbbox() is not None: raise RuntimeError("persisted decode mismatch")
pa=np.asarray(persisted)
if np.count_nonzero(changed(oa,pa)&~selected_allowed): raise RuntimeError("persisted blast radius fail")
if np.count_nonzero(changed(sa,pa)&~all_allowed): raise RuntimeError("persisted source scope fail")

# Evidence focused on the selector mode-card family.
src_rgb,old_rgb,clean_rgb,new_rgb=map(comp,(src,old,clean,persisted))
roi=(0,1440,1860,2048)
def card(label,im,scale=0.5):
    c=im.crop(roi)
    c=c.resize((round(c.width*scale),round(c.height*scale)),Image.Resampling.LANCZOS)
    z=Image.new("RGB",(c.width,c.height+28),(20,20,20)); z.paste(c,(0,28))
    ImageDraw.Draw(z).text((6,6),label,fill="white"); return z
cards=[card("SOURCE FLIP-Y",src_rgb),card("C117/B30 OLD",old_rgb),card("B30 CLEAN",clean_rgb),card("B233 FINAL",new_rgb)]
sheet=Image.new("RGB",(cards[0].width*2,cards[0].height*2),(16,16,16))
for i,c in enumerate(cards): sheet.paste(c,((i%2)*c.width,(i//2)*c.height))
sheet.save(out/"B233_Q100_SOURCE_OLD_CLEAN_FINAL.jpg","JPEG",quality=96,subsampling=0)

# RAW full-atlas orientation pair.
def fullcard(label,im):
    c=comp(im).resize((1024,1024),Image.Resampling.LANCZOS)
    z=Image.new("RGB",(1024,1052),(20,20,20)); z.paste(c,(0,28)); ImageDraw.Draw(z).text((6,6),label,fill="white"); return z
rawsheet=Image.new("RGB",(2048,1052),(16,16,16))
rawsheet.paste(fullcard("SOURCE RAW MIRROR_Y",sraw),(0,0)); rawsheet.paste(fullcard("B233 RAW MIRROR_Y",praw),(1024,0))
rawsheet.save(out/"B233_Q100_RAW_COMPARE.jpg","JPEG",quality=94,subsampling=0)

# Practical-scale source vs final; include 100/50/25% of the native-HD ROI.
pcs=[]
for sc in (1.0,0.5,0.25):
    s=src_rgb.crop(roi); f=new_rgb.crop(roi)
    s=s.resize((max(1,round(s.width*sc)),max(1,round(s.height*sc))),Image.Resampling.LANCZOS)
    f=f.resize(s.size,Image.Resampling.LANCZOS)
    row=Image.new("RGB",(s.width*2+6,s.height+26),(20,20,20))
    row.paste(s,(0,26)); row.paste(f,(s.width+6,26))
    ImageDraw.Draw(row).text((5,5),f"SOURCE | B233 FINAL  {int(sc*100)}%",fill="white")
    pcs.append(row)
pw=max(x.width for x in pcs); ph=sum(x.height for x in pcs)+8
ps=Image.new("RGB",(pw,ph),(16,16,16)); yy=0
for c in pcs: ps.paste(c,(0,yy)); yy+=c.height+4
ps.save(out/"B233_Q100_PRACTICAL_100_50_25.jpg","JPEG",quality=94,subsampling=0)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":100,"asset":asset,
 "selection_reason":"B primary even shard has no active material P0/P1 return, C-returned REWORK, RENDER_READY or ONE_STAGE item; existing C117 candidate is eligible material rework under current presentation hardening",
 "trigger":"PRE_INGAME_005_SOURCE_RELATIVE_PLACEMENT_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/005_q100_53CE39D5.jpg",
 "defect":"MODE_CARD_LINE_ALIGNMENT/HIERARCHY: C117 candidate centered every shortened Korean row inside each English glyph bbox, visibly shifting left-anchored source lines inward and compressing the source line hierarchy",
 "source_sha256":SOURCE_SHA,"before_candidate_sha256":BEFORE_SHA,"candidate_sha256":after,
 "source_provenance":SOURCE_URL,
 "method":"reuse C117/B30 validated clean plate and exact accepted Korean raster/effects; clear only 18 mode-card source line bboxes and translate each accepted localized raster horizontally to source-left+2; RANDOM and protected content unchanged",
 "rows":outrows,
 "machine_qa":{
   "lines_reworked":len(outrows),"bbox_size_positive_margin":"18/18 PASS",
   "previous_candidate_changed_pixels_outside_18_rework_bboxes":blast,
   "previous_candidate_alpha_changes_outside_18_rework_bboxes":alpha_blast,
   "source_vs_final_changes_outside_all_19_source_bboxes":0,
   "localized_pair_overlap":0,"random_row_pixel_exact_to_C117":True,
   "header_128_exact":pb[:128]==sb[:128],"mip_count":meta["mips"],"raw_orientation":"mirror_y",
   "persisted_decode_matches_intended":"PASS"
 },
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_REUSED_C117_B30_VALIDATED_CLEAN",
   "2_slant_direction":"PASS_PIXEL_EXACT_ACCEPTED_B30_RASTER",
   "3_no_unnecessary_undersizing":"UNCHANGED_RASTER_SIZE; SOURCE_RELATIVE_PLACEMENT_RESTORED",
   "4_source_weight_outline_shadow":"PASS_PIXEL_EXACT_ACCEPTED_B30_RASTER",
   "5_no_clipping":"PASS_18_OF_18_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_ZERO_PREVIOUS_CANDIDATE_BLAST_OUTSIDE_REWORK",
   "7_flip_y_raw":"EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER_VISUAL"
 },
 "post_encode_presentation_gate":{
   "decoded_persisted_dds_authority":"PASS",
   "practical_scales":["100%","50%","25%"],
   "family_profile":"ORANGE_DARK_OUTLINE_RIGHT_SLANT_MODE_CARD_FAMILY",
   "rework_blast_radius":"PASS_ZERO_OUTSIDE_18_LINE_BBOXES",
   "coverage":"UNCHANGED_7_SEMANTIC_19_PHYSICAL_LINES"
 },
 "controller_visual_qa":"PENDING_CONTROLLER",
 "status":"B233_WORKER_STATIC_PASS_PENDING_CONTROLLER_FRESH_C_C3",
 "RUNTIME_VALIDATION":"UNTESTED","no_vr_ffb_dx11_dxvk_work":True
}
(out/"B233_Q100_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B233_Q100_53CE39D5.json").write_text(json.dumps({
 "role":"B","run":run,"queue_index":100,"candidate_sha256":after,
 "status":report["status"],"report":str((out/"B233_Q100_REPORT.json").relative_to(repo))
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"queue_index":100,"before":BEFORE_SHA,"after":after,"lines":len(outrows),"blast":blast,"alpha_blast":alpha_blast,"status":report["status"]},ensure_ascii=False))
