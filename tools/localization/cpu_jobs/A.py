#!/usr/bin/env python3
import os, json, hashlib, struct, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A162-Q012-D6DC1380-RAW-ORIENTATION"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_etc_xst/D6DC1380_256x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
EXPECTED_BEFORE="fab100b99f42b773d820be5145866b07830637a2bee060ebbba133d1555739e5"
SOURCE_SHA="42aa10e021f9170247612b2e8231be43458abc3cda1011595db2fe2902df4352"
CANONICAL_RAW_BBOX=[32,40,992,176]
MIRROR_RAW_BBOX=[32,80,992,216]
EXPECTED_OLD_RAW_BBOX=[117,82,907,214]
EXPECTED_NEW_RAW_BBOX=[117,42,907,174]

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def count(mask): return sum(mask.histogram()[1:])
def diffmask(a,b):
    d=ImageChops.difference(a,b)
    bands=d.split()
    m=bands[0]
    for z in bands[1:]:
        m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def dds_meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf_flags=struct.unpack_from("<I",b,80)[0]
    fourcc=b[84:88]
    masks=struct.unpack_from("<4I",b,92)
    return w,h,pitch,depth,mips,pf_flags,fourcc,masks

oldb=candidate.read_bytes()
if sha_bytes(oldb)!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift",sha_bytes(oldb),EXPECTED_BEFORE))
W,H,pitch,depth,mips,pff,fourcc,masks=dds_meta(oldb)
if (W,H,mips)!=(1024,256,1):
    raise RuntimeError(("unexpected candidate",W,H,mips,fourcc,masks))
if len(oldb)!=128+W*H*4:
    raise RuntimeError(("unexpected payload",len(oldb)))

# Pin the same canonical English source used by A160/C235.
work=Path("/tmp/outrun_A162")
work.mkdir(parents=True,exist_ok=True)
urls=[
 "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_etc_xst/D6DC1380_256x64.dds",
 "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_etc_xst/D6DC1380_256x64.dds"
]
source=None
source_url=None
for i,u in enumerate(urls):
    p=work/f"source{i}.dds"
    try:
        urllib.request.urlretrieve(u,p)
        if sha_bytes(p.read_bytes())==SOURCE_SHA:
            source=p
            source_url=u
            break
    except Exception:
        pass
if source is None:
    raise RuntimeError("canonical source SHA not found")

sb=source.read_bytes()
sW,sH,_,_,sM,_,_,_=dds_meta(sb)
if (sW,sH,sM)!=(256,64,1):
    raise RuntimeError(("source dimensions",sW,sH,sM))
src_raw=Image.open(source).convert("RGBA")
src_native_bbox=list(src_raw.getchannel("A").getbbox() or ())
if src_native_bbox!=[8,10,248,44]:
    raise RuntimeError(("canonical source bbox drift",src_native_bbox))
src4=src_raw.resize((1024,256),Image.Resampling.NEAREST)
src4_bbox=list(src4.getchannel("A").getbbox() or ())
if src4_bbox!=CANONICAL_RAW_BBOX:
    raise RuntimeError(("canonical HD bbox drift",src4_bbox,CANONICAL_RAW_BBOX))

old_raw=Image.open(candidate).convert("RGBA")
old_raw_bbox=list(old_raw.getchannel("A").getbbox() or ())
if old_raw_bbox!=EXPECTED_OLD_RAW_BBOX:
    raise RuntimeError(("A160 raw bbox drift",old_raw_bbox,EXPECTED_OLD_RAW_BBOX))

# C235 proved A160 preserved the wrong mirror-Y storage orientation. The q12
# candidate is text-only on transparency, so the material fix is an exact
# vertical reorientation of the persisted pixels: no rerasterization, no
# rescaling, no style change.
new_raw=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
new_raw_bbox=list(new_raw.getchannel("A").getbbox() or ())
if new_raw_bbox!=EXPECTED_NEW_RAW_BBOX:
    raise RuntimeError(("new raw bbox",new_raw_bbox,EXPECTED_NEW_RAW_BBOX))

# Infer exact payload channel order from A160 persisted bytes and rewrite only
# pixel rows, preserving the 128-byte DDS header byte-for-byte.
rawmode=None
for mode in ("BGRA","RGBA"):
    try:
        if old_raw.tobytes("raw",mode)==oldb[128:]:
            rawmode=mode
            break
    except Exception:
        pass
if rawmode is None:
    raise RuntimeError(("cannot infer rawmode",masks))

newb=oldb[:128]+new_raw.tobytes("raw",rawmode)
if newb[:128]!=oldb[:128] or len(newb)!=len(oldb):
    raise RuntimeError("structure/header changed")
candidate.write_bytes(newb)

dec_raw=Image.open(candidate).convert("RGBA")
dec_raw_bbox=list(dec_raw.getchannel("A").getbbox() or ())
if dec_raw_bbox!=EXPECTED_NEW_RAW_BBOX:
    raise RuntimeError(("persisted raw bbox drift",dec_raw_bbox,EXPECTED_NEW_RAW_BBOX))
if ImageChops.difference(dec_raw,new_raw).getbbox() is not None:
    raise RuntimeError("persisted decode mismatch")

# Exact canonical-source containment and positive margins.
x0,y0,x1,y1=CANONICAL_RAW_BBOX
lx0,ly0,lx1,ly1=dec_raw_bbox
if not(lx0>x0 and ly0>y0 and lx1<x1 and ly1<y1):
    raise RuntimeError(("canonical positive margin fail",CANONICAL_RAW_BBOX,dec_raw_bbox))
if [lx1-lx0,ly1-ly0]!=[790,132]:
    raise RuntimeError(("A160 scale changed",dec_raw_bbox))

allowed=Image.new("L",(W,H),0)
ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
alpha_out=count(ImageChops.multiply(dec_raw.getchannel("A").point(lambda v:255 if v else 0),ImageOps.invert(allowed)))
if alpha_out:
    raise RuntimeError(("final alpha outside canonical source bbox",alpha_out))

# Rework blast radius: the only old->new changed pixels may lie in the union of
# the old mirror footprint and canonical-normal footprint. This includes
# clearing the old wrong-orientation pixels below the canonical source box.
union=Image.new("L",(W,H),0)
ud=ImageDraw.Draw(union)
ud.rectangle((CANONICAL_RAW_BBOX[0],CANONICAL_RAW_BBOX[1],CANONICAL_RAW_BBOX[2]-1,CANONICAL_RAW_BBOX[3]-1),fill=255)
ud.rectangle((MIRROR_RAW_BBOX[0],MIRROR_RAW_BBOX[1],MIRROR_RAW_BBOX[2]-1,MIRROR_RAW_BBOX[3]-1),fill=255)
dm=diffmask(old_raw,dec_raw)
changed_outside_union=count(ImageChops.multiply(dm,ImageOps.invert(union)))
if changed_outside_union:
    raise RuntimeError(("blast radius outside orientation union",changed_outside_union))

# Vertical flip must be exact and must not alter the rendered pixels/styles.
roundtrip_flip=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(roundtrip_flip,old_raw).getbbox() is not None:
    raise RuntimeError("orientation transform not exact")
if sorted(dec_raw.getdata())!=sorted(old_raw.getdata()):
    raise RuntimeError("pixel multiset changed")

def comp(im):
    bg=Image.new("RGBA",im.size,(96,96,96,255))
    bg.alpha_composite(im)
    return bg.convert("RGB")

# RAW source/A160/A162 evidence at matched 4x display.
raw_sheet=Image.new("RGB",(3072,256),(235,235,235))
for i,img in enumerate((src4,old_raw,dec_raw)):
    raw_sheet.paste(comp(img),(i*1024,0))
d=ImageDraw.Draw(raw_sheet)
d.text((8,4),"CANONICAL SOURCE RAW | A160 RAW (C235 FAIL) | A162 RAW FIX",fill="black")
raw_sheet.save(out/"A162_D6DC1380_RAW_SOURCE_OLD_FINAL.jpg",quality=95)

# Apply the same FLIP-Y transform to both source and candidate. They must stay
# transform-consistent; unlike A160, no opposite transform is needed to align
# source and final.
src_flip=src4.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
old_flip=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
new_flip=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
flip_sheet=Image.new("RGB",(3072,256),(235,235,235))
for i,img in enumerate((src_flip,old_flip,new_flip)):
    flip_sheet.paste(comp(img),(i*1024,0))
ImageDraw.Draw(flip_sheet).text((8,4),"SOURCE FLIP-Y | A160 FLIP-Y | A162 FLIP-Y",fill="black")
flip_sheet.save(out/"A162_D6DC1380_FLIPY_SOURCE_OLD_FINAL.jpg",quality=95)

for pct in (100,75,50):
    sz=(round(W*pct/100),round(H*pct/100))
    trio=[comp(z).resize(sz,Image.Resampling.LANCZOS) for z in (src4,old_raw,dec_raw)]
    sheet=Image.new("RGB",(sum(z.width for z in trio),max(z.height for z in trio)),(235,235,235))
    xx=0
    for z in trio:
        sheet.paste(z,(xx,0))
        xx+=z.width
    sheet.save(out/f"A162_D6DC1380_PRACTICAL_RAW_{pct}.jpg",quality=94)

newsha=sha_bytes(newb)
report={
 "schema_version":1,
 "role":"A",
 "run":"A162",
 "queue_index":12,
 "asset":asset_rel,
 "priority":"P0",
 "trigger":"C235_REWORK_REQUIRED_RAW_ORIENTATION_MISMATCH",
 "user_jpg_regression":"PJR-001-20261006",
 "source_sha256":SOURCE_SHA,
 "source_url":source_url,
 "prior_candidate_sha256":EXPECTED_BEFORE,
 "candidate_sha256":newsha,
 "canonical_source_raw_bbox_hd":CANONICAL_RAW_BBOX,
 "prior_candidate_raw_bbox":EXPECTED_OLD_RAW_BBOX,
 "localized_raw_bbox":dec_raw_bbox,
 "localized_size":[790,132],
 "machine_qa":{
   "source_bbox_containment":"PASS",
   "positive_margin":"PASS",
   "final_alpha_pixels_outside_canonical_raw_bbox":alpha_out,
   "changed_pixels_outside_declared_orientation_union":changed_outside_union,
   "dds_header_128_exact":newb[:128]==oldb[:128],
   "mip_count":mips,
   "rawmode":rawmode,
   "pixel_multiset_preserved":True,
   "vertical_reorientation_exact":True,
   "source_and_candidate_same_raw_orientation":"PASS_NORMAL_READABLE"
 },
 "ordered_generation_gate":{
   "1_plate_restoration":"PASS_TEXT_ONLY_TRANSPARENT_PLATE_UNCHANGED",
   "2_slant_direction":"PASS_A160_PIXELS_PRESERVED_EXACTLY",
   "3_no_unnecessary_undersizing":"PASS_A160_790x132_PRESERVED",
   "4_weight_outline_shadow":"PASS_A160_STYLE_PIXELS_PRESERVED_EXACTLY",
   "5_clipping":"PASS_POSITIVE_MARGIN_85_2_85_2",
   "6_protected_clearance":"PASS_TEXT_ONLY_ASSET_FINAL_ALPHA_INSIDE_CANONICAL_SOURCE_BBOX",
   "7_flip_y_raw":"PASS_SOURCE_AND_A162_USE_SAME_RAW_NORMAL_ORIENTATION",
   "8_readability":"PASS_A160_SCALE_STYLE_PRESERVED_PENDING_CONTROLLER_VISUAL_CONFIRMATION"
 },
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "fresh_independent_c":"REQUIRED",
 "mandatory_exact_sha_c3_after_fresh_c":"REQUIRED",
 "pre_ingame_export":"BLOCKED_UNTIL_FRESH_C_AND_C3",
 "runtime_validation":"UNTESTED",
 "forbidden_domains_touched":[]
}
(out/"A162_D6DC1380_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
 "run":"A162",
 "queue_index":12,
 "asset":"D6DC1380",
 "prior_candidate_sha256":EXPECTED_BEFORE,
 "candidate_sha256":newsha,
 "raw_orientation":"PASS_CANONICAL_NORMAL",
 "localized_raw_bbox":dec_raw_bbox,
 "size":[790,132],
 "worker_status":"STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL",
 "runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261007-A162-Q012-D6DC1380-RAW-ORIENTATION/A162_D6DC1380_REPORT.json"
}
(wr/"A162_D6DC1380.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
