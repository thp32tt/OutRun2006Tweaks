#!/usr/bin/env python3
# A145: manual PRE_INGAME JPG visual false-negative rework for q089 43B07A77.
# Rebuilds the Korean "Game Over" row from the validated native-HD clean plate,
# preserving its existing native-HD color/outline/shadow raster while correcting
# source-relative hierarchy and readable right-italic direction.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

import hashlib, json, urllib.request, struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

repo=Path.cwd()
run="20261006-A-MANUALQA145-43B07A77"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

rel="textures/load/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/rel
clean_path=repo/"localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_CLEAN_PLATE.png"
old_report_path=repo/"localization/graphics/role_A/20261004-A-PRODUCTION12/A_PRODUCTION12_43B07A77_REPORT.json"
EXPECTED_BEFORE="d2311d4c20327363bacf8b336e925e527ef8c5c8f13a385b0a2fb2e25a946cbc"
SOURCE_SHA="906a17ef9534bcb43d8296ae1d2ac339a53910f7113b954a52475368ab9b4175"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds"
SOURCE_BBOX=[1,13,1494,251]
TARGET_KOREAN="게임 오버"

def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha_file(candidate)!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift before A145",sha_file(candidate),EXPECTED_BEFORE))
old_report=json.loads(old_report_path.read_text(encoding="utf-8"))
if old_report.get("candidate_sha256")!=EXPECTED_BEFORE:
    raise RuntimeError("A_PRODUCTION12 provenance drift")

src_dds=Path("/tmp/A145_43B07A77_SOURCE.dds")
urllib.request.urlretrieve(SOURCE_URL,src_dds)
if sha_file(src_dds)!=SOURCE_SHA:
    raise RuntimeError(("source SHA drift",sha_file(src_dds),SOURCE_SHA))

def meta(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",p))
    h,w=struct.unpack_from("<II",b,12)
    mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]
    masks=struct.unpack_from("<4I",b,92)
    return b,w,h,mips,fourcc,masks

def load_readable(p):
    b,w,h,mips,fourcc,masks=meta(p)
    if fourcc!=b"\0\0\0\0": raise RuntimeError(("expected RGBA32",fourcc))
    if masks[:3]!=(0xff,0xff00,0xff0000): raise RuntimeError(("unexpected masks",masks))
    if len(b)!=128+w*h*4: raise RuntimeError(("DDS size",len(b),w,h))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
    return raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"header":b[:128],"w":w,"h":h,"mips":mips,"masks":list(masks)}

def write_readable(p,im,m):
    raw=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload=m["header"]+raw.tobytes("raw","RGBA")
    Path(p).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()

source,sm=load_readable(src_dds)
old,m=load_readable(candidate)
clean=Image.open(clean_path).convert("RGBA")
if source.size!=old.size or clean.size!=old.size or old.size!=(2048,256):
    raise RuntimeError(("size mismatch",source.size,old.size,clean.size))

x1,y1,x2,y2=SOURCE_BBOX
oa=np.asarray(old,dtype=np.uint8)
ca=np.asarray(clean,dtype=np.uint8)
region_old=oa[y1:y2,x1:x2]
region_clean=ca[y1:y2,x1:x2]
diff=np.max(np.abs(region_old.astype(np.int16)-region_clean.astype(np.int16)),axis=2)>3
ys,xs=np.nonzero(diff)
if len(xs)<1000: raise RuntimeError(("localized delta too small",len(xs)))
bx1,bx2=int(xs.min()),int(xs.max()+1)
by1,by2=int(ys.min()),int(ys.max()+1)
prior_bbox=[x1+bx1,y1+by1,x1+bx2,y1+by2]
tile_arr=region_old[by1:by2,bx1:bx2].copy()
dm=diff[by1:by2,bx1:bx2]
tile_arr[~dm]=0
tile=Image.fromarray(tile_arr,"RGBA")

# The old Korean row was only ~55% of the English source width and visually upright.
# Preserve the native-HD effect raster, widen it to restore source hierarchy, then
# apply readable right lean. No low-resolution bitmap is used.
source_w=x2-x1; source_h=y2-y1
target_width=int(source_w*0.82)
sx=target_width/max(1,tile.width)
sy=min(1.02,(source_h-12)/max(1,tile.height))
tile=tile.resize((max(1,round(tile.width*sx)),max(1,round(tile.height*sy))),Image.Resampling.LANCZOS)

def right_lean_native(im,amount=0.18):
    shift=max(1,int(np.ceil(amount*(im.height-1)))+4)
    pad=16+shift
    canvas=Image.new("RGBA",(im.width+2*pad,im.height+32),(0,0,0,0))
    canvas.alpha_composite(im,(pad,16))
    outi=Image.new("RGBA",canvas.size,(0,0,0,0))
    for yy in range(canvas.height):
        dx=round(amount*(canvas.height-1-yy))
        outi.alpha_composite(canvas.crop((0,yy,canvas.width,yy+1)),(dx,yy))
    bb=outi.getchannel("A").getbbox()
    if not bb: raise RuntimeError("empty transformed tile")
    return outi.crop(bb)

tile=right_lean_native(tile,0.18)
fit=min(1.0,(source_w-12)/tile.width,(source_h-12)/tile.height)
if fit<1.0:
    tile=tile.resize((max(1,round(tile.width*fit)),max(1,round(tile.height*fit))),Image.Resampling.LANCZOS)
bb=tile.getchannel("A").getbbox()
if bb: tile=tile.crop(bb)
if tile.width>=source_w or tile.height>=source_h:
    raise RuntimeError(("source bbox ceiling",tile.size,(source_w,source_h)))

px=x1+(source_w-tile.width)//2
py=y1+(source_h-tile.height)//2
localized_bbox=[px,py,px+tile.width,py+tile.height]
if not (x1<px and y1<py and localized_bbox[2]<x2 and localized_bbox[3]<y2):
    raise RuntimeError(("positive margin fail",localized_bbox,SOURCE_BBOX))

new=old.copy()
new.paste(clean.crop(SOURCE_BBOX),(x1,y1))
layer=Image.new("RGBA",new.size,(0,0,0,0))
layer.alpha_composite(tile,(px,py))
new.alpha_composite(layer)

na=np.asarray(new,dtype=np.uint8)
changed=np.any(na!=oa,axis=2)
allowed=np.zeros((old.height,old.width),bool); allowed[y1:y2,x1:x2]=True
changed_outside=int(np.logical_and(changed,~allowed).sum())
alpha_outside=int(np.logical_and(na[:,:,3]!=oa[:,:,3],~allowed).sum())
if changed_outside or alpha_outside:
    raise RuntimeError(("scope violation",changed_outside,alpha_outside))

after=write_readable(candidate,new,m)
decoded,dmmeta=load_readable(candidate)
if dmmeta["header"]!=m["header"]: raise RuntimeError("DDS header drift")
if not np.array_equal(np.asarray(decoded,dtype=np.uint8),na): raise RuntimeError("RGBA roundtrip mismatch")

def flatten(im,bg=(104,104,104,255)):
    base=Image.new("RGBA",im.size,bg); base.alpha_composite(im); return base.convert("RGB")

# Comparison evidence at readable and RAW orientations.
def make_compare(raw=False):
    ims=[]
    for im in (source,old,decoded):
        x=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if raw else im
        ims.append(flatten(x))
    W=sum(i.width for i in ims); H=max(i.height for i in ims)+42
    c=Image.new("RGB",(W,H),(28,28,28)); d=ImageDraw.Draw(c)
    labels=("ENGLISH SOURCE","OLD KOREAN","A145 REWORK")
    xx=0
    for lab,im in zip(labels,ims):
        d.text((xx+8,8),lab,fill="white")
        c.paste(im,(xx,42)); xx+=im.width
    return c

make_compare(False).save(out/"A145_SOURCE_OLD_NEW_READABLE.jpg","JPEG",quality=95,subsampling=0)
make_compare(True).save(out/"A145_SOURCE_OLD_NEW_RAW.jpg","JPEG",quality=95,subsampling=0)
decoded.save(out/"A145_FINAL_READABLE.png")
decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out/"A145_FINAL_RAW.png")

report={
 "schema_version":1,"role":"A","run":"A145","queue_index":89,"asset":rel,
 "trigger":"MANUAL_PRE_INGAME_JPG_REVIEW_023_VISUAL_FALSE_NEGATIVE",
 "review_jpg":"localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/023_q089_43B07A77.jpg",
 "prior_c_status":"C104_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "defects":["TEXT_SCALE_TOO_SMALL_VS_SOURCE","WRONG_OR_WEAK_SLANT_DIRECTION","SOURCE_HIERARCHY_MISMATCH"],
 "source_sha256":SOURCE_SHA,"before_sha256":EXPECTED_BEFORE,"candidate_sha256":after,
 "translation":{"source":"Game Over","korean":TARGET_KOREAN},
 "source_bbox":SOURCE_BBOX,"prior_localized_bbox":prior_bbox,"localized_bbox":localized_bbox,
 "source_size":[source_w,source_h],"localized_size":[tile.width,tile.height],
 "delta_left":localized_bbox[0]-x1,"delta_right":x2-localized_bbox[2],
 "delta_top":localized_bbox[1]-y1,"delta_bottom":y2-localized_bbox[3],
 "method":"validated native-HD clean plate + prior native-HD Korean effect raster isolation + width hierarchy refit + readable right-lean transform + exact-header RGBA32 DDS",
 "qa":{
   "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
   "changed_pixels_outside_source_bbox":changed_outside,
   "alpha_changed_outside_source_bbox":alpha_outside,
   "dds_header_128_exact":True,"rgba32_roundtrip_exact":True,
   "ordered_gate":{
      "1_source_text_removed_and_plate_restored":"INHERITED_VALIDATED_CLEAN_PLATE",
      "2_source_matching_readable_slant_direction":"REWORKED_PENDING_CONTROLLER_VISUAL",
      "3_no_unnecessary_undersizing":"REWORKED_TO_82_PERCENT_SOURCE_WIDTH_BEFORE_SLANT",
      "4_source_faithful_weight_outline_shadow":"PRESERVED_FROM_NATIVE_HD_KOREAN_EFFECT_RASTER",
      "5_no_clipped_pixels":"PASS_POSITIVE_MARGIN",
      "6_protected_art_clearance":"PASS_SOURCE_BBOX_CONFINED",
      "7_flip_y_and_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_VISUAL",
      "8_immediate_readability_vs_source":"PENDING_CONTROLLER_VISUAL"
   }
 },
 "runtime_validation":"UNTESTED",
 "status":"A145_WORKER_STATIC_PASS_PENDING_CONTROLLER_VISUAL_QA_AND_FRESH_C",
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"A145_43B07A77_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A145_43B07A77.json").write_text(json.dumps({
 "role":"A","run":"A145","queue_index":89,"asset":rel,"candidate_sha256":after,
 "report":str((out/"A145_43B07A77_REPORT.json").relative_to(repo)),
 "status":report["status"],"runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"A145","before":EXPECTED_BEFORE,"after":after,"source_bbox":SOURCE_BBOX,"prior_bbox":prior_bbox,"new_bbox":localized_bbox,"status":report["status"]},ensure_ascii=False))
