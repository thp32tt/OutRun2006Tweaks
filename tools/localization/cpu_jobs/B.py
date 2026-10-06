#!/usr/bin/env python3
# B210: manual PRE_INGAME JPG QA false-negative rework for q050 CBF8ECBF.
# Reuses the prior native-HD Korean raster/effects at full resolution, then applies
# source-matching readable right lean and maximum safe source-relative scale.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

import hashlib, json, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

repo=Path.cwd()
run="20261006-B-MANUALQA210-CBF8ECBF"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

rel="textures/load/spr_sprani_etc_cvt_Exst/CBF8ECBF_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/rel
clean_path=repo/"localization/graphics/role_B/20261004-B-RECOVERY08/CBF8ECBF_CLEAN_PLATE.png"
old_report_path=repo/"localization/graphics/role_B/20261004-B-RECOVERY08/B_RECOVERY08_CBF8ECBF_REPORT.json"

EXPECTED_BEFORE="ecc4cbb6cdc064d2c7ccccfc378569f1dc7fc8339c46330ec68ec81c8f899df1"
SOURCE_SHA="3a2a40256a6c3c945dfd4fab275edba5ec05802e4cff54f2ad93d5196cd992fe"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_etc_cvt_Exst/CBF8ECBF_1024x512.dds"

def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

if sha_file(candidate)!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift before B210",sha_file(candidate),EXPECTED_BEFORE))
old_report=json.loads(old_report_path.read_text(encoding="utf-8"))
if old_report.get("candidate_sha256")!=EXPECTED_BEFORE:
    raise RuntimeError("B_RECOVERY08 provenance drift")

src_dds=Path("/tmp/B210_CBF8ECBF_SOURCE.dds")
urllib.request.urlretrieve(SOURCE_URL,src_dds)
if sha_file(src_dds)!=SOURCE_SHA:
    raise RuntimeError(("source sha drift",sha_file(src_dds),SOURCE_SHA))

def dds_meta(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",p))
    import struct
    h=struct.unpack_from("<I",b,12)[0]
    w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]
    masks=struct.unpack_from("<4I",b,92)
    return b,w,h,mips,fourcc,masks

def load_readable(p):
    b,w,h,mips,fourcc,masks=dds_meta(p)
    if fourcc!=b"\0\0\0\0":
        raise RuntimeError(("B210 expects uncompressed RGBA32",fourcc))
    if masks[:3]!=(0xff,0xff00,0xff0000):
        raise RuntimeError(("unexpected channel masks",masks))
    if len(b)!=128+w*h*4:
        raise RuntimeError(("DDS byte size",len(b),w,h))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
    return raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM), {
        "header":b[:128],"w":w,"h":h,"mips":mips,"fourcc":"RGBA32","masks":list(masks)
    }

def write_readable(p,readable,meta):
    raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload=meta["header"]+raw.tobytes("raw","RGBA")
    Path(p).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()

source,srcmeta=load_readable(src_dds)
old,meta=load_readable(candidate)
clean=Image.open(clean_path).convert("RGBA")
if source.size!=old.size or clean.size!=old.size or old.size!=(4096,2048):
    raise RuntimeError(("size mismatch",source.size,old.size,clean.size))
if srcmeta["w"]!=meta["w"] or srcmeta["h"]!=meta["h"]:
    raise RuntimeError("source/candidate dimension mismatch")

# User-requested/manual PRE_INGAME review identified a C104 visual false negative:
# the three hero labels are materially less source-italic and lose source hierarchy.
targets={
    "time_over":{"bbox":[241,1274,1610,1515],"text":"시간 종료","slant":0.18,"max_scale":1.04},
    "game_over":{"bbox":[1915,1287,3409,1525],"text":"게임 오버","slant":0.18,"max_scale":1.04},
    "goal":{"bbox":[1620,1660,2814,2024],"text":"골","slant":0.18,"max_scale":1.10},
}

oa=np.asarray(old,dtype=np.int16)
ca=np.asarray(clean,dtype=np.int16)
new=old.copy()
allowed=np.zeros((old.height,old.width),bool)
rows=[]

def extract_old_localized(bbox):
    x1,y1,x2,y2=bbox
    o=np.asarray(old.crop(bbox),dtype=np.uint8)
    c=np.asarray(clean.crop(bbox),dtype=np.uint8)
    diff=np.max(np.abs(o.astype(np.int16)-c.astype(np.int16)),axis=2)>3
    ys,xs=np.nonzero(diff)
    if len(xs)<100:
        raise RuntimeError(("localized diff too small",bbox,len(xs)))
    bx1,bx2=int(xs.min()),int(xs.max()+1)
    by1,by2=int(ys.min()),int(ys.max()+1)
    tile=o[by1:by2,bx1:bx2].copy()
    # Keep only pixels belonging to the old Korean/effect delta; clean background stays transparent.
    dm=diff[by1:by2,bx1:bx2]
    tile[~dm]=0
    return Image.fromarray(tile,"RGBA"),[x1+bx1,y1+by1,x1+bx2,y1+by2]

def right_lean_native(tile,amount):
    # readable orientation: upper rows shift right relative to lower rows.
    # Work at the native 4096x2048 atlas resolution with padding before crop.
    shift=max(1,int(np.ceil(amount*(tile.height-1)))+4)
    pad=12+shift
    canvas=Image.new("RGBA",(tile.width+2*pad,tile.height+24),(0,0,0,0))
    canvas.alpha_composite(tile,(pad,12))
    outi=Image.new("RGBA",canvas.size,(0,0,0,0))
    for y in range(canvas.height):
        dx=round(amount*(canvas.height-1-y))
        outi.alpha_composite(canvas.crop((0,y,canvas.width,y+1)),(dx,y))
    bb=outi.getchannel("A").getbbox()
    if not bb: raise RuntimeError("empty sheared tile")
    return outi.crop(bb)

# Rebuild only the three visually failed hero rows from the already validated clean plate.
for key,spec in targets.items():
    bbox=spec["bbox"]
    x1,y1,x2,y2=bbox
    allowed[y1:y2,x1:x2]=True
    tile,old_bbox=extract_old_localized(bbox)
    source_w=x2-x1; source_h=y2-y1

    # Scale as large as safely possible without distorting aspect ratio or violating
    # the exact source bbox. The prior raster was native-HD; this is not low-res upscaling.
    scale=min(spec["max_scale"],(source_w-12)/tile.width,(source_h-12)/tile.height)
    if scale>1.001:
        tile=tile.resize((max(1,round(tile.width*scale)),max(1,round(tile.height*scale))),Image.Resampling.LANCZOS)
    tile=right_lean_native(tile,spec["slant"])

    # If slant growth makes the tile too large, refit isotropically.
    fit=min(1.0,(source_w-10)/tile.width,(source_h-10)/tile.height)
    if fit<1.0:
        tile=tile.resize((max(1,round(tile.width*fit)),max(1,round(tile.height*fit))),Image.Resampling.LANCZOS)
    bb=tile.getchannel("A").getbbox()
    if bb: tile=tile.crop(bb)

    if tile.width>source_w-2 or tile.height>source_h-2:
        raise RuntimeError(("cannot safely fit B210 tile",key,tile.size,(source_w,source_h)))
    px=x1+(source_w-tile.width)//2
    py=y1+(source_h-tile.height)//2
    localized_bbox=[px,py,px+tile.width,py+tile.height]
    if not (x1<localized_bbox[0] and y1<localized_bbox[1] and localized_bbox[2]<x2 and localized_bbox[3]<y2):
        raise RuntimeError(("positive margin fail",key,bbox,localized_bbox))

    # Restore exact validated clean plate within the source region before relayering.
    new.paste(clean.crop(bbox),(x1,y1))
    layer=Image.new("RGBA",new.size,(0,0,0,0))
    layer.alpha_composite(tile,(px,py))
    new.alpha_composite(layer)

    rows.append({
      "key":key,"korean":spec["text"],"source_bbox":bbox,"prior_localized_bbox":old_bbox,
      "localized_bbox":localized_bbox,"source_size":[source_w,source_h],
      "localized_size":[tile.width,tile.height],
      "delta_left":localized_bbox[0]-x1,"delta_right":x2-localized_bbox[2],
      "delta_top":localized_bbox[1]-y1,"delta_bottom":y2-localized_bbox[3],
      "readable_right_lean":spec["slant"],"native_raster_transform":True,
      "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS"
    })

na=np.asarray(new,dtype=np.uint8)
old_arr=np.asarray(old,dtype=np.uint8)
changed=np.any(na!=old_arr,axis=2)
changed_outside=int(np.logical_and(changed,~allowed).sum())
alpha_outside=int(np.logical_and(na[:,:,3]!=old_arr[:,:,3],~allowed).sum())
if changed_outside or alpha_outside:
    raise RuntimeError(("B210 scope violation",changed_outside,alpha_outside))

after=write_readable(candidate,new,meta)
decoded,dmeta=load_readable(candidate)
if dmeta["header"]!=meta["header"]:
    raise RuntimeError("DDS header changed")
da=np.asarray(decoded,dtype=np.uint8)
if not np.array_equal(da,na):
    raise RuntimeError("RGBA32 roundtrip mismatch")

# High-zoom source/old/new evidence in readable orientation.
def flatten(im,bg=(104,104,104,255)):
    b=Image.new("RGBA",im.size,bg); b.alpha_composite(im); return b.convert("RGB")

def contact_image(raw=False):
    panels=[]
    labels=[]
    src=source.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if raw else source
    bef=old.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if raw else old
    aft=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if raw else decoded
    for key,spec in targets.items():
        bbox=spec["bbox"]
        if raw:
            x1,y1,x2,y2=bbox
            bbox=[x1,old.height-y2,x2,old.height-y1]
        x1,y1,x2,y2=bbox
        pad=24
        crop=(max(0,x1-pad),max(0,y1-pad),min(old.width,x2+pad),min(old.height,y2+pad))
        triple=[]
        for im in (src,bef,aft):
            c=flatten(im.crop(crop))
            c.thumbnail((1100,340),Image.Resampling.LANCZOS)
            triple.append(c)
        w=sum(i.width for i in triple)+12
        h=max(i.height for i in triple)+38
        card=Image.new("RGB",(w,h),(36,36,36))
        d=ImageDraw.Draw(card)
        x=0
        for lab,im in zip(("SOURCE","OLD","B210"),triple):
            d.text((x+4,4),lab,fill="white")
            card.paste(im,(x,34)); x+=im.width+6
        panels.append(card); labels.append(key)
    W=max(i.width for i in panels); H=sum(i.height for i in panels)+8*(len(panels)-1)
    sheet=Image.new("RGB",(W,H),(24,24,24)); y=0
    for p in panels:
        sheet.paste(p,(0,y)); y+=p.height+8
    return sheet

contact_image(False).save(out/"B210_SOURCE_OLD_NEW_READABLE.jpg","JPEG",quality=95,subsampling=0)
contact_image(True).save(out/"B210_SOURCE_OLD_NEW_RAW.jpg","JPEG",quality=95,subsampling=0)
decoded.save(out/"B210_FINAL_READABLE.png")
decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out/"B210_FINAL_RAW.png")

report={
 "schema_version":1,"role":"B","run":"B210","queue_index":50,"asset":rel,
 "trigger":"B_MANUAL_PRE_INGAME_JPG_REVIEW_013_VISUAL_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/013_q050_CBF8ECBF.jpg",
 "prior_c_status":"C104_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "defects":["WRONG_SLANT_DIRECTION","SOURCE_STYLE_HIERARCHY_MISMATCH"],
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":after,
 "method":"native-HD prior Korean effect raster isolated against validated clean plate -> isotropic max-safe refit -> readable right-lean transform -> exact clean plate relayer -> RGBA32 exact-header DDS",
 "rows":rows,
 "qa":{
   "changed_pixels_outside_three_source_bboxes":changed_outside,
   "alpha_changed_outside_three_source_bboxes":alpha_outside,
   "untouched_small_rows_pixel_exact_vs_prior_candidate":True,
   "dds_header_128_exact":True,"rgba32_roundtrip_exact":True,
   "readable_source_old_new_visual_review":"PENDING_CONTROLLER",
   "raw_source_old_new_visual_review":"PENDING_CONTROLLER",
   "ordered_gate":{
      "plate_restoration":"INHERITED_VALIDATED_CLEAN_PLATE",
      "source_matching_slant_direction":"REWORKED_PENDING_CONTROLLER_VISUAL",
      "no_unnecessary_undersizing":"MAX_SAFE_ISOTROPIC_REFIT_WITH_SOURCE_BBOX_CEILING",
      "weight_outline_shadow":"PRESERVED_FROM_PRIOR_NATIVE_HD_KOREAN_EFFECT_RASTER",
      "clipping":"PASS_POSITIVE_MARGIN",
      "protected_art_clearance":"PASS_SCOPE_CONFINED_TO_PRIOR_SOURCE_BBOXES",
      "flip_y_and_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_VISUAL",
      "immediate_readability":"PENDING_CONTROLLER_VISUAL"
   }
 },
 "runtime_validation":"UNTESTED",
 "status":"B210_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"B210_CBF8ECBF_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B210_CBF8ECBF.json").write_text(json.dumps({
 "role":"B","run":"B210","queue_index":50,"asset":rel,
 "candidate_sha256":after,"report":str((out/"B210_CBF8ECBF_REPORT.json").relative_to(repo)),
 "status":report["status"],"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"B210","before":EXPECTED_BEFORE,"after":after,"rows":rows,"status":report["status"]},ensure_ascii=False))
