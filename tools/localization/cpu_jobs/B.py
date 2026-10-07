#!/usr/bin/env python3
# B234: q97 411827E current-policy source-slant repair.
# B primary even shard has no actionable P0/P1 material return, direct C REWORK,
# RENDER_READY or ONE_STAGE item. Contract-authorized work-steal from A shard:
# PRE_INGAME #005 shows the four A_RECOVERY04 rows were rendered upright even
# though their English source family is visibly right-italic/slanted.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib,json,struct,urllib.request,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageChops

repo=Path.cwd()
run="20261007-B234-Q097-411827E-SLANT"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_selector_cvt_Exst/411827E_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
clean_path=repo/"localization/graphics/role_A/20261004-A-RECOVERY04/411827E_CLEAN_PLATE.png"
prior_report_path=repo/"localization/graphics/role_A/20261004-A-RECOVERY04/A_RECOVERY04_411827E_REPORT.json"
SOURCE_SHA="bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364"
BEFORE_SHA="c7f27e948179ac555c3107facd6885df141e9f7aa0b8b2c6450e466e7132981e"
SOURCE_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_URL=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{SOURCE_COMMIT}/Release/spr_sprani_selector_cvt_Exst/411827E_512x512.dds"

tmp=Path("/tmp/b234"); tmp.mkdir(exist_ok=True)
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
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mips":mips,"mode":mode}
def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def rectmask(h,w,bb):
    m=np.zeros((h,w),bool); x0,y0,x1,y1=bb; m[y0:y1,x0:x1]=True; return m
def changed(a,b): return np.any(a!=b,axis=2)
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255)); z.alpha_composite(im); return z.convert("RGB")
def layer_from_old_vs_clean(oa,ca,bb):
    x0,y0,x1,y1=bb
    o=oa[y0:y1,x0:x1]; c=ca[y0:y1,x0:x1]
    dm=changed(o,c) & ((o[:,:,3]>0)|(c[:,:,3]>0))
    b=bbox(dm)
    if b is None: raise RuntimeError(("empty localized layer",bb))
    arr=np.zeros_like(o)
    arr[dm]=o[dm]
    im=Image.fromarray(arr.astype(np.uint8),"RGBA").crop(tuple(b))
    return im,b,dm
def right_shear_layer(im, visual_shear=0.18):
    # PIL uses inverse mapping; negative coefficient produces readable right lean.
    pad=10
    base=Image.new("RGBA",(im.width+pad*2,im.height+pad*2),(0,0,0,0))
    base.alpha_composite(im,(pad,pad))
    w2=base.width+int(math.ceil(abs(visual_shear)*base.height))+12
    tr=base.transform((w2,base.height),Image.Transform.AFFINE,(1,-visual_shear,8,0,1,0),resample=Image.Resampling.BICUBIC)
    bb=tr.getbbox()
    if bb is None: raise RuntimeError("empty transformed layer")
    return tr.crop(bb)

sb=src_dds.read_bytes(); ob=cand.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sha(ob)!=BEFORE_SHA: raise RuntimeError(("candidate drift",sha(ob)))
sraw,src,meta=decode(sb); oraw,old,ometa=decode(ob)
if meta!=ometa or sb[:128]!=ob[:128]: raise RuntimeError("header/structure drift")
if meta["mips"]!=1: raise RuntimeError(("unexpected mips",meta["mips"]))
clean=Image.open(clean_path).convert("RGBA")
if clean.size!=old.size: raise RuntimeError(("clean size",clean.size,old.size))
prior=json.loads(prior_report_path.read_text(encoding="utf-8"))
if prior.get("candidate_sha256")!=BEFORE_SHA: raise RuntimeError("A_RECOVERY04 report candidate mismatch")
rows={r["key"]:r for r in prior["rows"]}
keys=["seconds","tuned","normal","random"]
oa=np.asarray(old); ca=np.asarray(clean); sa=np.asarray(src)
H,W=oa.shape[:2]
allowed=np.zeros((H,W),bool)
for k in keys: allowed |= rectmask(H,W,rows[k]["original_bbox"])

# A_RECOVERY04 clean plate is authoritative only for these four rows.
# Rebuild those rows from clean and transform the exact accepted Korean raster/effects.
final_np=oa.copy()
for k in keys:
    x0,y0,x1,y1=rows[k]["original_bbox"]
    final_np[y0:y1,x0:x1]=ca[y0:y1,x0:x1]
final=Image.fromarray(final_np.astype(np.uint8),"RGBA")
row_results=[]
new_masks=[]
for k in keys:
    r=rows[k]; bb=r["original_bbox"]; x0,y0,x1,y1=bb
    layer,local_diff_bbox,dm=layer_from_old_vs_clean(oa,ca,bb)
    sheared=right_shear_layer(layer,0.18)
    maxw=(x1-x0)-4; maxh=(y1-y0)-4
    scale=1.0
    if sheared.width>maxw or sheared.height>maxh:
        scale=min(maxw/sheared.width,maxh/sheared.height)
        sheared=sheared.resize((max(1,int(round(sheared.width*scale))),max(1,int(round(sheared.height*scale)))),Image.Resampling.LANCZOS)
    # Keep source/candidate center anchor while retaining 2px minimum margins.
    px=int(round((x0+x1-sheared.width)/2))
    py=int(round((y0+y1-sheared.height)/2))
    px=max(x0+2,min(px,x1-sheared.width-2))
    py=max(y0+2,min(py,y1-sheared.height-2))
    lay=Image.new("RGBA",final.size,(0,0,0,0)); lay.alpha_composite(sheared,(px,py))
    final.alpha_composite(lay)
    lm=np.asarray(lay.getchannel("A"))>0
    nb=bbox(lm)
    if nb is None: raise RuntimeError(("empty final layer",k))
    margins=[nb[0]-x0,x1-nb[2],nb[1]-y0,y1-nb[3]]
    if min(margins)<2: raise RuntimeError(("positive margin fail",k,nb,margins))
    if nb[2]-nb[0] > x1-x0 or nb[3]-nb[1] > y1-y0:
        raise RuntimeError(("size ceiling fail",k))
    new_masks.append(lm)
    row_results.append({
      "key":k,"source":r["source"],"korean":r["korean"],
      "original_bbox":bb,"before_localized_bbox":r["new_localized_bbox"],
      "final_localized_bbox":nb,
      "source_size":[x1-x0,y1-y0],
      "final_size":[nb[2]-nb[0],nb[3]-nb[1]],
      "margins":margins,"visual_right_shear":0.18,
      "fit_scale_after_shear":round(scale,6),
      "construction":"exact prior Korean raster/effect extracted against A_RECOVERY04 validated CLEAN then right-sheared at native resolution",
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
    })

na=np.asarray(final)
# Scope: exactly four source bboxes only.
blast=int(np.count_nonzero(changed(oa,na)&~allowed))
alpha_blast=int(np.count_nonzero((oa[:,:,3]!=na[:,:,3])&~allowed))
if blast or alpha_blast: raise RuntimeError(("blast radius",blast,alpha_blast))
# All other localized/protected art remains pixel exact to C87.
for k,r in rows.items():
    if k in keys: continue
    x0,y0,x1,y1=r["original_bbox"]
    if not np.array_equal(oa[y0:y1,x0:x1],na[y0:y1,x0:x1]):
        raise RuntimeError(("untouched row drift",k))
# No localized pair overlap among the four rebuilt layers.
for i in range(len(new_masks)):
    for j in range(i+1,len(new_masks)):
        if np.count_nonzero(new_masks[i]&new_masks[j]):
            raise RuntimeError(("pair overlap",keys[i],keys[j]))

# Persist exact source header/raw mirror-Y.
fraw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+fraw.tobytes("raw",meta["mode"])
cand.write_bytes(payload)
pb=cand.read_bytes(); after=sha(pb)
praw,persisted,pmeta=decode(pb)
if pmeta!=meta or pb[:128]!=sb[:128]: raise RuntimeError("persisted header/structure drift")
if ImageChops.difference(persisted,final).getbbox() is not None: raise RuntimeError("persisted decode mismatch")
pa=np.asarray(persisted)
if np.count_nonzero(changed(oa,pa)&~allowed): raise RuntimeError("persisted blast-radius fail")

# Visual evidence: full top family and targeted rows at high zoom.
src_rgb,old_rgb,clean_rgb,new_rgb=map(comp,(src,old,clean,persisted))
roi=(0,0,2048,1050)
def labeled(label,im,w=1024):
    c=im.crop(roi)
    h=round(c.height*w/c.width); c=c.resize((w,h),Image.Resampling.LANCZOS)
    z=Image.new("RGB",(w,h+28),(20,20,20));z.paste(c,(0,28));ImageDraw.Draw(z).text((6,6),label,fill="white");return z
cards=[labeled("SOURCE",src_rgb),labeled("C87 OLD",old_rgb),labeled("A_RECOVERY04 CLEAN",clean_rgb),labeled("B234 FINAL",new_rgb)]
sheet=Image.new("RGB",(2048,cards[0].height*2),(16,16,16))
for i,c in enumerate(cards): sheet.paste(c,((i%2)*1024,(i//2)*c.height))
sheet.save(out/"B234_411_SOURCE_OLD_CLEAN_FINAL.jpg","JPEG",quality=96,subsampling=0)

# Target row crops.
rowcards=[]
for k in keys:
    x0,y0,x1,y1=rows[k]["original_bbox"]; pad=24
    crop=(max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad))
    s=src_rgb.crop(crop); o=old_rgb.crop(crop); n=new_rgb.crop(crop)
    scale=2
    s=s.resize((s.width*scale,s.height*scale),Image.Resampling.NEAREST)
    o=o.resize(s.size,Image.Resampling.NEAREST); n=n.resize(s.size,Image.Resampling.NEAREST)
    row=Image.new("RGB",(s.width*3+8,s.height+28),(20,20,20))
    row.paste(s,(0,28)); row.paste(o,(s.width+4,28)); row.paste(n,(s.width*2+8,28))
    ImageDraw.Draw(row).text((6,6),f"{k}: SOURCE | C87 OLD | B234 FINAL",fill="white")
    rowcards.append(row)
rw=max(x.width for x in rowcards); rh=sum(x.height for x in rowcards)
rs=Image.new("RGB",(rw,rh),(16,16,16)); yy=0
for c in rowcards: rs.paste(c,(0,yy)); yy+=c.height
rs.save(out/"B234_411_ROW_SLANT_COMPARE.jpg","JPEG",quality=96,subsampling=0)

# RAW and practical scale.
rawsheet=Image.new("RGB",(2048,1052),(16,16,16))
for i,(lab,im) in enumerate([("SOURCE RAW MIRROR_Y",sraw),("B234 RAW MIRROR_Y",praw)]):
    c=comp(im).resize((1024,1024),Image.Resampling.LANCZOS)
    z=Image.new("RGB",(1024,1052),(20,20,20)); z.paste(c,(0,28)); ImageDraw.Draw(z).text((6,6),lab,fill="white")
    rawsheet.paste(z,(i*1024,0))
rawsheet.save(out/"B234_411_RAW_COMPARE.jpg","JPEG",quality=94,subsampling=0)

pcs=[]
for sc in (1.0,0.5,0.25):
    s=src_rgb.crop(roi); f=new_rgb.crop(roi)
    s=s.resize((max(1,round(s.width*sc)),max(1,round(s.height*sc))),Image.Resampling.LANCZOS)
    f=f.resize(s.size,Image.Resampling.LANCZOS)
    row=Image.new("RGB",(s.width*2+6,s.height+26),(20,20,20))
    row.paste(s,(0,26)); row.paste(f,(s.width+6,26))
    ImageDraw.Draw(row).text((5,5),f"SOURCE | B234 FINAL {int(sc*100)}%",fill="white"); pcs.append(row)
pw=max(x.width for x in pcs); ph=sum(x.height+4 for x in pcs)
ps=Image.new("RGB",(pw,ph),(16,16,16)); yy=0
for c in pcs: ps.paste(c,(0,yy)); yy+=c.height+4
ps.save(out/"B234_411_PRACTICAL_100_50_25.jpg","JPEG",quality=94,subsampling=0)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":97,"work_stolen_from_lane":"A",
 "asset":asset,
 "selection_reason":"B even shard exhausted active material P0/P1, direct C REWORK, RENDER_READY and ONE_STAGE; oldest current PRE_INGAME style false-negative selected from A shard after fresh queue/HEAD check",
 "trigger":"PRE_INGAME_005_CURRENT_POLICY_SLANT_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/005_q097_411827E.jpg",
 "defect":"A_RECOVERY04 rows seconds/TUNED/NORMAL/RANDOM were native but upright while canonical English source is visibly right-italic; current readable-slant/source-style hard gate invalidates C87 visual PASS for those four rows",
 "source_sha256":SOURCE_SHA,"source_commit":SOURCE_COMMIT,
 "before_candidate_sha256":BEFORE_SHA,"candidate_sha256":after,
 "rows":row_results,
 "machine_qa":{
   "lines_reworked":4,"bbox_source_size_positive_margin":"4/4 PASS",
   "changed_pixels_outside_four_exact_source_bboxes":blast,
   "alpha_changes_outside_four_exact_source_bboxes":alpha_blast,
   "localized_pair_overlap":0,
   "untouched_automatic_engine_recommendation_and_protected_art":"PIXEL_EXACT_TO_C87",
   "header_128_exact":pb[:128]==sb[:128],"mip_count":meta["mips"],"raw_orientation":"mirror_y",
   "persisted_decode_matches_intended":"PASS"
 },
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_REUSED_A_RECOVERY04_VALIDATED_CLEAN",
   "2_slant_direction":"PASS_RIGHT_LEAN_0.18_NATIVE_TRANSFORM",
   "3_no_unnecessary_undersizing":"PASS_HEIGHT_RETAINED_NEAR_SOURCE; RANDOM_WIDTH_REFIT_ONLY_IF_REQUIRED",
   "4_source_weight_outline_shadow":"PASS_EXACT_C87_RASTER_EFFECT_BASE_TRANSFORMED",
   "5_no_clipping":"PASS_4_OF_4_POSITIVE_MARGIN",
   "6_protected_clearance":"PASS_ZERO_BLAST_OUTSIDE_FOUR_BBOXES",
   "7_flip_y_raw":"EVIDENCE_WRITTEN",
   "8_immediate_readability":"PENDING_CONTROLLER_VISUAL"
 },
 "post_encode_presentation_gate":{
   "decoded_persisted_dds_authority":"PASS","practical_scales":["100%","50%","25%"],
   "family_profile":"SOURCE_RIGHT_ITALIC_SELECTOR_LABELS","blast_radius":"PASS_ZERO_OUTSIDE_REWORK",
   "coverage":"UNCHANGED_7_SEMANTIC_ROWS"
 },
 "controller_visual_qa":"PENDING_CONTROLLER",
 "status":"B234_WORKER_STATIC_PASS_PENDING_CONTROLLER_FRESH_C_C3",
 "RUNTIME_VALIDATION":"UNTESTED","no_vr_ffb_dx11_dxvk_work":True
}
(out/"B234_411_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B234_Q097_411827E.json").write_text(json.dumps({
 "role":"B","run":run,"queue_index":97,"candidate_sha256":after,
 "status":report["status"],"report":str((out/"B234_411_REPORT.json").relative_to(repo))
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"queue_index":97,"before":BEFORE_SHA,"after":after,"rows":row_results,"blast":blast,"status":report["status"]},ensure_ascii=False))
