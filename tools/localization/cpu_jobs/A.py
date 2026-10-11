#!/usr/bin/env python3
"""A244 q012 P0 new rounded-bevel Korean font geometry vs C388 confirmed visual failure.
Creates genuinely new, SHA-bound *unpromoted* persisted BGRA DDS from exact native
English source, preserving all non-target bytes, plus 100/75/50 and RAW evidence.
No English-width matching or forced sentence aspect under Oct-11 glyph policy.
"""
import csv
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

assert os.environ.get("OUTRUN_CPU_WORKER") == "github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE") == "A"
R=Path.cwd()
OUT=R/"localization/graphics/role_A/20261011-A244-Q012-ROUNDED-SOURCE-BEVEL-TRIAL"
OUT.mkdir(parents=True,exist_ok=True)
SRC=R/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_etc_xst/D6DC1380_256x64.dds"
OFF=R/"localization/graphics/hd_candidates/textures/load/spr_etc_xst/D6DC1380_256x64.dds"
SOURCE_SHA="42aa10e021f9170247612b2e8231be43458abc3cda1011595db2fe2902df4352"
OFFICIAL_SHA="1df64df712f990ee5d92c53998269604ff7b9fc4ccdff8913d648f18aa604013"
SRC_BOX=(32,80,992,216) # READABLE x4 canonical English glyph+effect bbox
W,H=1024,256
RUN_KEY="OUTRUN-KOR-A244-Q012-C388-ROUND-BEVEL-NATIVE-20261011-2000"
FONT=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
font_index=1
def sha(b):return hashlib.sha256(b).hexdigest()
def read_ref(p):return {"path":str(p.relative_to(R)),"sha256":sha(p.read_bytes())}
def savej(n,o):
 p=OUT/n;p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");return read_ref(p)
def png(n,im):
 p=OUT/n;im.save(p,"PNG");return read_ref(p)
def decode(data,expected):
 assert data[:4]==b"DDS " and len(data)==128+expected[0]*expected[1]*4
 assert struct.unpack_from("<II",data,12)==(expected[1],expected[0])
 assert struct.unpack_from("<I",data,28)[0]==1
 assert struct.unpack_from("<I",data,88)[0]==32
 assert struct.unpack_from("<IIII",data,92)==(16711680,65280,255,4278190080)
 return Image.frombytes("RGBA",expected,data[128:],"raw","BGRA")
def check(t,msg):
 if not t:raise RuntimeError(msg)
def box_of_alpha(im):
 bb=im.getchannel("A").getbbox()
 check(bb is not None,"alpha empty")
 return bb
with (R/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 q=next(x for x in csv.DictReader(f) if x["index"].lstrip("\ufeff")=="12")
check(q["action"]=="localize_text" and "rework" in q["artwork_status"],"q012 no longer material rework; stop")
with (R/"localization/graphics/INGAME_REWORK_BACKLOG.csv").open(encoding="utf-8-sig",newline="") as f:
 backlog=[x for x in csv.DictReader(f) if x["queue_index"]=="12"]
check(any(x["owner_lane"]=="A" and x["priority"]=="P0" for x in backlog),"missing explicit A P0 ownership q012")
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","12","--require-safe-rerender"],capture_output=True,text=True)
savej("A244_READONLY_TRIAGE.json",{"returncode":tri.returncode,"stdout":tri.stdout[-8000:],"stderr":tri.stderr[-4000:],
 "run_key":RUN_KEY,"decision":"new source-derived rounded/beveled shape METHOD CHANGE, not exact same-method rerender"})
# require-safe-rerender can reject when material reconstruction required; read triage normally
tri2=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","12"],capture_output=True,text=True,check=True)
check("MATERIAL_REWORK" in tri2.stdout or "METHOD_CHANGE_REQUIRED" in tri2.stdout,
      "source material rework NOT confirmed")
a=SRC.read_bytes();b=OFF.read_bytes()
check(sha(a)==SOURCE_SHA,"canonical original source hash drift")
check(sha(b)==OFFICIAL_SHA,"current approved historical candidate drift")
source_raw=decode(a,(256,64))
old_raw=decode(b,(W,H))
src=source_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
old=old_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
# Source original is 256x64; only nearest-4x proof, not fabricated high-resolution source.
source4=src.resize((W,H),Image.Resampling.NEAREST)
sc=np.array(source4)
bb=box_of_alpha(source4)
check(bb==SRC_BOX,"source orientation/alpha bbox drift: "+repr(bb))
oldbb=box_of_alpha(old)
check(oldbb[0]>=bb[0] and oldbb[1]>=bb[1] and oldbb[2]<=bb[2] and oldbb[3]<=bb[3],
      "current old not confined to source footprint")
# SOURCE/CLEAN exact text-only texture: no background art present, all alpha removed
clean=Image.new("RGBA",(W,H),(0,0,0,0))
png("A244_CANONICAL_ENGLISH_DISPLAY_4X_ONLY.png",source4)
png("A244_OLD_PERSISTED_READABLE.png",old)
png("A244_CLEAN_PLATE_READABLE.png",clean)
png("A244_CLEAN_PLATE_RAW.png",clean.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
check(FONT.is_file(),"required native Korean font unavailable")
# P2 intrinsic native per-syllable geometry. Heavy real contours, with 4x AA and
# rounded radius blur; NOT a stretched old Korean glyph nor a width-fit.
AA=4
font=ImageFont.truetype(str(FONT),126*AA,index=font_index)
can=Image.new("L",(1000*AA,190*AA),0)
ImageDraw.Draw(can).text((30*AA,0),"계속?",font=font,fill=255)
tb=can.getbbox()
check(tb is not None,"font rendered empty Korean")
glyph=can.crop(tb)
# readable right-italic shear from source family (top edge ~right of bottom)
lean=0.23
slanted=Image.new("L",(glyph.width+int(glyph.height*lean)+8*AA,glyph.height),0)
for y in range(glyph.height):
    offset=round((glyph.height-1-y)*lean)
    slanted.paste(glyph.crop((0,y,glyph.width,y+1)),(offset,y))
c=slanted.crop(slanted.getbbox())
# source glyph/effect bbox is 960x136. leave >=2px top/bottom and 9px
# side for navy extrusion. If native font too tall scale uniformly, never x-only.
native_h=round(c.height/AA)
native_w=round(c.width/AA)
target_h=min(native_h,118)
scale=target_h/native_h
shape=c.resize((max(1,round(c.width/AA*scale)),target_h),Image.Resampling.LANCZOS)
# slight rounded-source contour/anti-jagged edge, no coarse block dilation
shape=shape.filter(ImageFilter.GaussianBlur(0.45))
mask=Image.new("L",(W,H),0)
pos=((W-shape.width)//2,(SRC_BOX[1]+SRC_BOX[3]-shape.height)//2-2)
check(pos[0]>=SRC_BOX[0]+9 and pos[0]+shape.width<=SRC_BOX[2]-9 and
      pos[1]>=SRC_BOX[1]+6 and pos[1]+shape.height<=SRC_BOX[3]-10,
      "per-glyph source safety margin exceeds native glyph; no forced width fit")
mask.paste(shape,pos)
# Softly curved optical volume source: differentiated outer navy rim, inner
# steel-edge bevel and deep down/right extrusion (not hard angular slab).
rim_alpha=mask.filter(ImageFilter.MaxFilter(9))
depth=ImageChops.offset(rim_alpha,6,5)
# Offset wraps; crop to SOURCE box and check unchanged target outside
def keep_inside(alpha):
    region=alpha.crop(SRC_BOX)
    out=Image.new("L",(W,H),0)
    out.paste(region,(SRC_BOX[0],SRC_BOX[1]))
    return out
depth=keep_inside(depth)
rim=keep_inside(rim_alpha)
# source-conditioned palette from actual opaque original glyph
s_rgba=np.asarray(source4)
samples=s_rgba[s_rgba[:,:,3]>192,:3]
check(len(samples)>1000,"source effect palette empty")
brightness=samples.mean(axis=1)
light=samples[brightness>=np.percentile(brightness,80)]
dark=samples[brightness<=np.percentile(brightness,18)]
silver=tuple(int(v) for v in np.median(light,axis=0))
navy=tuple(int(v) for v in np.median(dark,axis=0))
# Guarantee source colors are legibly distinct, no novelty hue.
check(min(silver)>150 and max(navy)<160,("source palette unexpected",silver,navy))
def color_layer(color,alpha):
 out=Image.new("RGBA",alpha.size,(*color,0))
 out.putalpha(alpha)
 return out
# layered effects with real bevel across Korean native strokes.
layers=[]
def layer(name,color,alpha):
 im=color_layer(color,alpha)
 png("A244_"+name+"_READABLE.png",im)
 png("A244_"+name+"_RAW.png",im.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
 layers.append((name,im))
layer("DEPTH",navy,depth)
layer("RIM",navy,rim)
# face gradient from original silver white top into mild steel-gray bottom
facealpha=np.asarray(mask,dtype=np.uint8)
yy=np.indices((H,W))[0]
fraction=np.clip((yy-pos[1])/max(1,shape.height),0,1)
c0=np.array(silver,dtype=np.float32)
face=np.empty((H,W,4),dtype=np.uint8)
for k in range(3):
    face[:,:,k]=np.clip(c0[k]*(1-0.13*fraction),0,255).astype(np.uint8)
face[:,:,3]=facealpha
f_im=Image.fromarray(face,"RGBA")
png("A244_FACE_READABLE.png",f_im)
png("A244_FACE_RAW.png",f_im.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
layers.append(("FACE",f_im))
# subtle bevel/hilight constrained to face; only source-family effect not extra art
inner=ImageChops.subtract(mask,mask.filter(ImageFilter.MinFilter(5)))
bright=inner.crop((0,0,W,max(0,pos[1]+shape.height//2)))
highlight=Image.new("L",(W,H),0)
highlight.paste(bright,(0,0))
layer("HIGHLIGHT",tuple(min(255,v+9) for v in silver),highlight)
letter=Image.new("RGBA",(W,H),(0,0,0,0))
for _,im in layers:letter=Image.alpha_composite(letter,im)
letter_bb=box_of_alpha(letter)
check(letter_bb[0]>=SRC_BOX[0]+1 and letter_bb[1]>=SRC_BOX[1]+1 and
      letter_bb[2]<=SRC_BOX[2]-1 and letter_bb[3]<=SRC_BOX[3]-1,
      ("source 1px overflow",letter_bb,SRC_BOX))
# Ensure entire actual pixel changes restricted to canonical source footprint.
out_bytes=b[:128]+letter.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","BGRA")
trial=OUT/"A244_Q012_ROUNDED_BEVEL_PERSISTED_UNPROMOTED.dds"
trial.write_bytes(out_bytes)
saved=decode(trial.read_bytes(),(W,H)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
check(np.array_equal(np.asarray(saved),np.asarray(letter)),"actual native persisted DDS != composed pixels")
oa=np.asarray(old);na=np.asarray(saved)
different=np.any(oa!=na,axis=2)
edit=np.zeros((H,W),dtype=bool);edit[SRC_BOX[1]:SRC_BOX[3],SRC_BOX[0]:SRC_BOX[2]]=True
outside=int(np.count_nonzero(different & ~edit))
check(outside==0,("changed outside original",outside))
png("A244_NEW_PERSISTED_READABLE.png",saved)
png("A244_NEW_PERSISTED_RAW.png",saved.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
png("A244_LETTERING_ONLY_READABLE.png",letter)
png("A244_GEOMETRY_RAW_L.png",mask.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
# Native, 75,50 on gray/black/white, source & old & CLEAN & lettering & persisted.
for nm,bg in [("GRAY",(105,105,105)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
    proof=[]
    for im in (source4,old,clean,letter,saved):
        proof.append(Image.alpha_composite(Image.new("RGBA",(W,H),(*bg,255)),im).convert("RGB"))
    for pct in (100,75,50):
        ww=round(W*pct/100);hh=round(H*pct/100)
        card=Image.new("RGB",(ww*len(proof),hh),bg)
        for k,im in enumerate(proof):
            card.paste(im.resize((ww,hh),Image.Resampling.LANCZOS),(k*ww,0))
        png("A244_SOURCE_OLD_CLEAN_GLYPH_SAVED_"+nm+"_"+str(pct)+".png",card)
savej("A244_SOURCE_FAMILY_AND_GLYPH_RECIPE.json",{
 "schema":"a244-native-rounded-bevel-v1","source_pinned":SOURCE_SHA,"source_native_wh":[256,64],
 "source_display_scale":4,"source_bbox_4x_readable":SRC_BOX,"font_sha256":sha(FONT.read_bytes()),
 "font_index":font_index,"font_size_native":126,"oversample":AA,
 "translation":"계속?","slant_native_shear":lean,"native_isotropic_target_height":target_h,
 "font_glyph_size":[shape.width,shape.height],"style_source_RGB":{"silver":silver,"navy":navy},
 "effect_layers":["DEPTH","RIM","FACE","HIGHLIGHT"],
 "note":"New rounded morphology and bevel; source 4x for display only, not an invented native-HD source. No source width-fit; consumer approval pending."
})
report={
 "schema_version":2,"run":"A244","run_key":RUN_KEY,"role":"A",
 "queue_index":12,"user_backlog":"PJR-001-20261006","source_sha256":SOURCE_SHA,
 "old_official_sha256":OFFICIAL_SHA,"new_trial_sha256":sha(out_bytes),
 "source_bbox_4x_readable":SRC_BOX,"new_bbox_readable":letter_bb,
 "glyph_shape_native":[shape.width,shape.height],
 "new_trial_path":str(trial.relative_to(R)),
 "modified_rgba_pixels":int(np.count_nonzero(different)),"changed_outside_original_source_bbox":outside,
 "alpha_outside_source_bbox":0,"clean_plate_alpha":0,"native_size":[W,H],
 "dds_header_exact":out_bytes[:128]==b[:128],"saved_roundtrip_exact":True,
 "raw_orientation":"original_source_mirror_y; readable_FLIPY",
 "source_family":"native true Noto Hangul + Gaussian-rounded contours, bevel highlight, navy rim/extrusion",
 "review":"NEW_MATERIAL_TRIAL_NEEDS_PRODUCER_FIRSTHAND_SOURCE_FAMILY_100_75_50_RAW",
 "official_hd_candidate_changed":False,"independent_C2":"NOT_RUN","C3":"NOT_RUN",
 "user_pre_ingame_jpg":"PJR001_OPEN","RUNTIME_VALIDATION":"UNTESTED",
 "backend":"GitHub Actions native build; CPU off N100",
 "excluded":["VR","FFB","DX11","DXVK"]
}
savej("A244_MACHINE_AND_HANDOFF.json",report)
print(json.dumps({"A244":"NEW_NATIVE_PERSISTED_TRIAL", "trial_sha256":report["new_trial_sha256"],
                  "changed":report["modified_rgba_pixels"],"bbox":letter_bb,"outside":outside},ensure_ascii=False),flush=True)
