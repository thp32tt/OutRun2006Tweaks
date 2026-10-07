#!/usr/bin/env python3
# A164: q197 9F060EC1 current-policy exact-source-bbox/family repair.
# Current candidate is a historical C85 PASS, but the modern hard gate is not
# grandfathered: A88 recorded 4/5 Korean glyph bboxes taller than the exact
# English source bboxes, and the title also starts left of its source bbox.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

import hashlib, json, struct, subprocess
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image, ImageDraw, ImageFont, ImageChops

repo=Path.cwd()
run="20261007-A164R-Q197-9F060EC1-EXACT-BBOX"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/9F060EC1_512x512.dds"
source_path=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset
candidate=repo/"localization/graphics/hd_candidates"/asset
a88_report_path=repo/"localization/graphics/role_A/20260927-2030-A88/A88_9F060EC1_PRODUCTION_REPORT.json"

SOURCE_SHA="177e3be8f3a8fd4d0482bcf1849cbe333cef6f86486afbc4ca6307ec417c2e05"
BEFORE_SHA="39d917ca74552a86b459d1110ddcc351a07705e078d75160aabae49c7de20a60"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6])
    mode="BGRA" if masks==(0xff0000,0xff00,0xff) else ("RGBA" if masks==(0xff,0xff00,0xff0000) else None)
    if mode is None or (w,h)!=(2048,2048) or len(b)!=128+w*h*4:
        raise RuntimeError(("DDS structure",w,h,mips,masks,len(b)))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    return raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mips":mips,"mode":mode,"masks":masks}
def bbox(mask):
    ys,xs=np.nonzero(mask)
    return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
def rectmask(h,w,bb):
    m=np.zeros((h,w),bool); x0,y0,x1,y1=bb; m[y0:y1,x0:x1]=True; return m
def changed(a,b): return np.any(a!=b,axis=2)
def comp(im):
    z=Image.new("RGBA",im.size,(104,104,104,255)); z.alpha_composite(im); return z.convert("RGB")
def dilate1(m):
    z=m.copy()
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if dx==0 and dy==0: continue
            yy0=max(0,dy); yy1=m.shape[0]+min(0,dy)
            xx0=max(0,dx); xx1=m.shape[1]+min(0,dx)
            z[yy0:yy1,xx0:xx1] |= m[yy0-dy:yy1-dy,xx0-dx:xx1-dx]
    return z
def inpaint_nearest(arr,mask):
    # Euclidean nearest-background fill avoids the horizontal streaking that
    # controller visual QA rejected in A164's first clean reconstruction.
    if not np.any(mask): return arr.copy()
    _,inds=distance_transform_edt(mask,return_indices=True)
    out=arr.copy()
    yy,xx=np.nonzero(mask)
    out[yy,xx]=arr[inds[0,yy,xx],inds[1,yy,xx]]
    return out

sb=source_path.read_bytes()
OLD_COMMIT="882f5a5d5daff5fe00d3da1d0775127c4948cfd9"
ob=subprocess.check_output(["git","show",OLD_COMMIT+":localization/graphics/hd_candidates/"+asset])
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sha(ob)!=BEFORE_SHA: raise RuntimeError(("candidate drift",sha(ob)))
sraw,source,meta=decode(sb); oraw,old,ometa=decode(ob)
if meta!=ometa or sb[:128]!=ob[:128] or meta["mips"]!=1:
    raise RuntimeError("source/candidate structure mismatch")

a88=json.loads(a88_report_path.read_text(encoding="utf-8"))
if a88.get("candidate_sha256")!=BEFORE_SHA or a88.get("canonical_sha256")!=SOURCE_SHA:
    raise RuntimeError("A88 provenance mismatch")

# Current-policy exact source glyph/effect bboxes reconstructed from the A88
# readable cells + source_text_mask_bbox_local evidence. Old localized bboxes
# are A88's persisted candidate evidence.
rows=[
 {"key":"license","text":"아웃런 라이선스","source_bbox":[41,1285,625,1347],"old_bbox":[25,1270,496,1339],"fill":[151,153,173,255],"kind":"title"},
 {"key":"complete","text":"달성률:","source_bbox":[399,1561,679,1608],"old_bbox":[398,1558,546,1607],"fill":[19,36,72,255],"kind":"body"},
 {"key":"vs_rank","text":"VS 랭크:","source_bbox":[397,1652,625,1699],"old_bbox":[398,1651,574,1697],"fill":[19,36,72,255],"kind":"body"},
 {"key":"win_ratio","text":"승률:","source_bbox":[398,1742,677,1789],"old_bbox":[399,1741,503,1789],"fill":[19,36,72,255],"kind":"body"},
 {"key":"drive_time","text":"주행 시간:","source_bbox":[400,1834,708,1879],"old_bbox":[399,1832,607,1881],"fill":[19,36,72,255],"kind":"body"},
]
# Explicitly prove the historical violation that makes this material work.
historical=[]
for r in rows:
    sw=r["source_bbox"][2]-r["source_bbox"][0]; sh=r["source_bbox"][3]-r["source_bbox"][1]
    ow=r["old_bbox"][2]-r["old_bbox"][0]; oh=r["old_bbox"][3]-r["old_bbox"][1]
    historical.append({"key":r["key"],"source_size":[sw,sh],"old_size":[ow,oh],
      "old_delta_left":r["old_bbox"][0]-r["source_bbox"][0],
      "old_delta_right":r["source_bbox"][2]-r["old_bbox"][2],
      "old_delta_top":r["old_bbox"][1]-r["source_bbox"][1],
      "old_delta_bottom":r["source_bbox"][3]-r["old_bbox"][3],
      "current_policy_pass":ow<=sw and oh<=sh and r["old_bbox"][0]>=r["source_bbox"][0] and r["old_bbox"][1]>=r["source_bbox"][1] and r["old_bbox"][2]<=r["source_bbox"][2] and r["old_bbox"][3]<=r["source_bbox"][3]})
if sum(1 for x in historical if not x["current_policy_pass"])<4:
    raise RuntimeError(("expected historical hard failures missing",historical))

oa=np.asarray(old).copy(); sa=np.asarray(source)
H,W=oa.shape[:2]
# Remove only the old Korean raster. Thresholds are deliberately restricted to
# the old localized bboxes; this never touches row numbers, OM, barcode/legal,
# watermark/frame regions outside those rectangles.
clean_np=oa.copy()
old_masks=[]
mask_debug=[]
for r in rows:
    x0,y0,x1,y1=r["old_bbox"]
    crop=oa[y0:y1,x0:x1,:3].astype(np.int16)
    if r["kind"]=="title":
        # gray-purple title against near-white strip
        lum=crop.mean(axis=2)
        seed=lum<220
    else:
        # navy body lettering against pale patterned plate
        lum=crop.mean(axis=2)
        seed=lum<155
    local=dilate1(seed)
    bb_local=bbox(local)
    if bb_local is None: raise RuntimeError(("empty old glyph mask",r["key"]))
    global_mask=np.zeros((H,W),bool)
    global_mask[y0:y1,x0:x1]=local
    old_masks.append(global_mask)
    mask_debug.append({"key":r["key"],"threshold_bbox_local":bb_local,"masked_pixels":int(local.sum())})
    # Nearest-background reconstruction operates on a padded local crop and fills
    # each glyph footprint from the closest intact plate pixels in 2D.
    px0=max(0,x0-8); py0=max(0,y0-3); px1=min(W,x1+8); py1=min(H,y1+3)
    local_arr=clean_np[py0:py1,px0:px1].copy()
    local_mask=global_mask[py0:py1,px0:px1]
    clean_np[py0:py1,px0:px1]=inpaint_nearest(local_arr,local_mask)

clean=Image.fromarray(clean_np.astype(np.uint8),"RGBA")

# Fail closed if obvious old text-core colors remain after clean reconstruction.
for r,m in zip(rows,old_masks):
    x0,y0,x1,y1=r["old_bbox"]
    crop=clean_np[y0:y1,x0:x1,:3]
    lum=crop.mean(axis=2)
    if r["kind"]=="title":
        # allow panel edge/other neutral pixels but not a dense text-shaped core
        remain=int(np.count_nonzero(lum<205))
        limit=120
    else:
        remain=int(np.count_nonzero(lum<125))
        limit=120
    if remain>limit:
        raise RuntimeError(("clean plate dark residue",r["key"],remain,limit))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font missing",FONT))
font_index=1 if FONT.lower().endswith(".ttc") else 0

def raster(text,fs,fill):
    font=ImageFont.truetype(FONT,fs,index=font_index)
    c=Image.new("RGBA",(1400,180),(0,0,0,0)); d=ImageDraw.Draw(c)
    bb=d.textbbox((10,10),text,font=font)
    d.text((10-bb[0],10-bb[1]),text,font=font,fill=tuple(fill))
    gb=c.getchannel("A").getbbox()
    if gb is None: raise RuntimeError(("empty glyph",text,fs))
    return c.crop(gb)

# Shared source family => all four body rows use one shared font size.
body_rows=[r for r in rows if r["kind"]=="body"]
body_fs=None; body_layers={}
for fs in range(58,20,-1):
    trial={}
    ok=True
    for r in body_rows:
        im=raster(r["text"],fs,r["fill"])
        sw=r["source_bbox"][2]-r["source_bbox"][0]-4
        sh=r["source_bbox"][3]-r["source_bbox"][1]-4
        if im.width>sw or im.height>sh:
            ok=False; break
        trial[r["key"]]=im
    if ok:
        body_fs=fs; body_layers=trial; break
if body_fs is None: raise RuntimeError("no shared body font fit")

# Title gets its own source-intentional hierarchy but must obey exact bbox.
title=rows[0]; title_layer=None; title_fs=None
for fs in range(78,28,-1):
    im=raster(title["text"],fs,title["fill"])
    sw=title["source_bbox"][2]-title["source_bbox"][0]-4
    sh=title["source_bbox"][3]-title["source_bbox"][1]-4
    if im.width<=sw and im.height<=sh:
        title_fs=fs; title_layer=im; break
if title_layer is None: raise RuntimeError("no title font fit")

final=clean.copy()
results=[]
layers=[]
for r in rows:
    box=r["source_bbox"]; x0,y0,x1,y1=box
    im=title_layer if r["kind"]=="title" else body_layers[r["key"]]
    # Preserve source-left cadence with >=2 px left margin; vertically center.
    px=x0+2
    py=y0+(y1-y0-im.height)//2
    if py<y0+2: py=y0+2
    if px+im.width>x1-2 or py+im.height>y1-2:
        raise RuntimeError(("placement overflow",r["key"],im.size,box,px,py))
    lay=Image.new("RGBA",final.size,(0,0,0,0)); lay.alpha_composite(im,(px,py))
    final.alpha_composite(lay)
    lm=np.asarray(lay.getchannel("A"))>0
    bb=bbox(lm)
    margins=[bb[0]-x0,x1-bb[2],bb[1]-y0,y1-bb[3]]
    if min(margins)<2: raise RuntimeError(("positive margin",r["key"],margins))
    sw=x1-x0; sh=y1-y0; fw=bb[2]-bb[0]; fh=bb[3]-bb[1]
    if fw>sw or fh>sh: raise RuntimeError(("size ceiling",r["key"],[fw,fh],[sw,sh]))
    layers.append(lm)
    results.append({"key":r["key"],"text":r["text"],"source_bbox":box,"old_bbox":r["old_bbox"],
      "localized_bbox":bb,"source_size":[sw,sh],"localized_size":[fw,fh],
      "delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
      "font_size":title_fs if r["kind"]=="title" else body_fs})

# No overlap between localized labels.
for i in range(len(layers)):
    for j in range(i+1,len(layers)):
        if np.count_nonzero(layers[i]&layers[j]):
            raise RuntimeError(("localized overlap",rows[i]["key"],rows[j]["key"]))

fa=np.asarray(final)
# Declared material rework scope is union(old Korean bboxes, exact source bboxes).
allowed=np.zeros((H,W),bool)
for r in rows:
    allowed |= rectmask(H,W,r["old_bbox"])
    allowed |= rectmask(H,W,r["source_bbox"])
blast=int(np.count_nonzero(changed(oa,fa)&~allowed))
alpha_blast=int(np.count_nonzero((oa[:,:,3]!=fa[:,:,3])&~allowed))
if blast or alpha_blast: raise RuntimeError(("blast radius",blast,alpha_blast))

# Persist with exact source header and raw mirror-Y encoding.
fraw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
newb=sb[:128]+fraw.tobytes("raw",meta["mode"])
candidate.write_bytes(newb)
pb=candidate.read_bytes(); newsha=sha(pb)
praw,persisted,pmeta=decode(pb)
if pmeta!=meta or pb[:128]!=sb[:128]: raise RuntimeError("persisted structure/header drift")
if ImageChops.difference(persisted,final).getbbox() is not None: raise RuntimeError("persisted decode mismatch")
pa=np.asarray(persisted)
if np.count_nonzero(changed(oa,pa)&~allowed): raise RuntimeError("persisted blast radius")
if np.count_nonzero((oa[:,:,3]!=pa[:,:,3])&~allowed): raise RuntimeError("persisted alpha blast radius")

# Visual evidence.
src_rgb,old_rgb,clean_rgb,new_rgb=map(comp,(source,old,clean,persisted))
roi=(0,1160,900,1960)
def card(label,im,w=900):
    c=im.crop(roi)
    h=round(c.height*w/c.width); c=c.resize((w,h),Image.Resampling.LANCZOS)
    z=Image.new("RGB",(w,h+30),(20,20,20)); z.paste(c,(0,30)); ImageDraw.Draw(z).text((6,6),label,fill="white"); return z
cards=[card("SOURCE",src_rgb),card("A88/C85 OLD",old_rgb),card("A164 CLEAN",clean_rgb),card("A164 FINAL",new_rgb)]
sheet=Image.new("RGB",(1800,cards[0].height*2),(16,16,16))
for i,c in enumerate(cards): sheet.paste(c,((i%2)*900,(i//2)*c.height))
sheet.save(out/"A164R_Q197_SOURCE_OLD_CLEAN_FINAL.jpg","JPEG",quality=96,subsampling=0)

rowcards=[]
for r in rows:
    x0,y0,x1,y1=r["source_bbox"]; ox0,oy0,ox1,oy1=r["old_bbox"]
    cx0=max(0,min(x0,ox0)-20); cy0=max(0,min(y0,oy0)-14); cx1=min(W,max(x1,ox1)+20); cy1=min(H,max(y1,oy1)+14)
    ims=[src_rgb.crop((cx0,cy0,cx1,cy1)),old_rgb.crop((cx0,cy0,cx1,cy1)),clean_rgb.crop((cx0,cy0,cx1,cy1)),new_rgb.crop((cx0,cy0,cx1,cy1))]
    scale=2
    ims=[x.resize((x.width*scale,x.height*scale),Image.Resampling.NEAREST) for x in ims]
    row=Image.new("RGB",(sum(x.width for x in ims)+18,max(x.height for x in ims)+30),(20,20,20)); xx=0
    ImageDraw.Draw(row).text((6,6),r["key"]+" SOURCE | OLD | CLEAN | FINAL",fill="white")
    for im in ims:
        row.paste(im,(xx,30)); xx+=im.width+6
    rowcards.append(row)
rw=max(x.width for x in rowcards); rh=sum(x.height for x in rowcards)
rs=Image.new("RGB",(rw,rh),(16,16,16)); yy=0
for c in rowcards: rs.paste(c,(0,yy)); yy+=c.height
rs.save(out/"A164R_Q197_ROW_CONTACTS.jpg","JPEG",quality=97,subsampling=0)

raw_roi=(0,88,900,888)  # mirror-Y of readable lower card
raws=[]
for lab,im in [("SOURCE RAW",sraw),("OLD RAW",oraw),("A164 RAW",praw)]:
    c=comp(im).crop(raw_roi).resize((900,800),Image.Resampling.LANCZOS)
    z=Image.new("RGB",(900,830),(20,20,20));z.paste(c,(0,30));ImageDraw.Draw(z).text((6,6),lab,fill="white");raws.append(z)
rawsheet=Image.new("RGB",(2700,830),(16,16,16))
for i,c in enumerate(raws):rawsheet.paste(c,(i*900,0))
rawsheet.save(out/"A164R_Q197_RAW_COMPARE.jpg","JPEG",quality=95,subsampling=0)

pcs=[]
pr=src_rgb.crop(roi); pf=new_rgb.crop(roi)
for pct in (100,75,50):
    s=pr.resize((round(pr.width*pct/100),round(pr.height*pct/100)),Image.Resampling.LANCZOS)
    f=pf.resize(s.size,Image.Resampling.LANCZOS)
    row=Image.new("RGB",(s.width*2+6,s.height+28),(20,20,20));row.paste(s,(0,28));row.paste(f,(s.width+6,28))
    ImageDraw.Draw(row).text((5,5),f"SOURCE | A164 FINAL {pct}%",fill="white");pcs.append(row)
pw=max(x.width for x in pcs); ph=sum(x.height+4 for x in pcs)
ps=Image.new("RGB",(pw,ph),(16,16,16)); yy=0
for c in pcs:ps.paste(c,(0,yy));yy+=c.height+4
ps.save(out/"A164R_Q197_PRACTICAL_100_75_50.jpg","JPEG",quality=95,subsampling=0)

report={
 "schema_version":2,"role":"A","run":run,"queue_index":197,"asset":asset,
 "execution_backend":"github-actions because repository-backed 16MiB DDS bytes are not directly materialized in ChatGPT local runtime; N100 heavy image processing not used",
 "trigger":"A164_CONTROLLER_CLEAN_PLATE_VISUAL_REJECT_RETRY_CURRENT_POLICY_ZERO_PIXEL_SIZE_CEILING",
 "source_sha256":SOURCE_SHA,"prior_candidate_sha256":BEFORE_SHA,"candidate_sha256":newsha,
 "historical_current_policy_check":historical,
 "repair":"reconstruct only old Korean raster footprints from current clean-background context, then native Noto Sans CJK KR Bold rerender; shared body font size; exact source-left cadence",
 "font":{"path":FONT,"font_index":font_index,"title_size":title_fs,"shared_body_size":body_fs},
 "clean_plate":{"method":"Euclidean nearest-background reconstruction restricted to old Korean glyph masks; A164 horizontal-streak reconstruction rejected and superseded; no artwork outside declared correction rectangles modified","mask_debug":mask_debug},
 "rows":results,
 "machine_qa":{"bbox_size_positive_margin":"5/5 PASS","changed_pixels_outside_declared_rework_union":blast,
   "alpha_changed_outside_declared_rework_union":alpha_blast,"localized_pair_overlap":0,
   "header_128_exact":pb[:128]==sb[:128],"dimensions":[meta["w"],meta["h"]],"mips":meta["mips"],
   "raw_orientation":"mirror_y","persisted_decode_matches_intended":"PASS",
   "row_numbers_OM_barcode_legal_watermark_frame_outside_rework":"PIXEL_EXACT_TO_PRIOR_C85"},
 "ordered_generation_gate":{"1_plate_restoration":"PENDING_CONTROLLER_VISUAL; A164_HORIZONTAL_STREAK_METHOD_SUPERSEDED; MACHINE_SCOPE_ZERO_BLAST",
   "2_slant_direction":"PASS_SOURCE_UPRIGHT_FAMILY","3_no_unnecessary_undersizing":"PASS_MAX_SHARED_NATIVE_FONT_WITH_2PX_MIN_MARGIN",
   "4_source_weight_effects":"PASS_FLAT_SOURCE_COLOR_FAMILY; NO_INVENTED_OUTLINE_SHADOW",
   "5_no_clipping":"PASS_5_OF_5_POSITIVE_MARGIN","6_protected_clearance":"PASS_ZERO_BLAST_OUTSIDE_DECLARED_REWORK",
   "7_flip_y_raw":"EVIDENCE_WRITTEN","8_immediate_readability":"PENDING_CONTROLLER_VISUAL"},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","fresh_independent_c":"REQUIRED",
 "mandatory_c3_strict_audit":"REQUIRED_EXACT_SHA_DUE_HISTORICAL_POLICY_FALSE_NEGATIVE",
 "pre_ingame_export":"BLOCKED_UNTIL_FRESH_C_C3","runtime_validation":"UNTESTED","forbidden_domains_touched":[]
}
(out/"A164R_Q197_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"role":"A","run":run,"queue_index":197,"asset":"9F060EC1","candidate_sha256":newsha,
 "worker_status":"STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL","report":"localization/graphics/role_A/"+run+"/A164R_Q197_REPORT.json","runtime_validation":"UNTESTED"}
(wr/"A164R_Q197_9F060EC1.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))