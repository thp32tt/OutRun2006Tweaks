#!/usr/bin/env python3
"""A245: new source-derived ONLINE -> 온라인 true-CLEAN native DDS trial (q193).

One independently C1-rejected inherited pixelated sprite, distinct from the
A243 15 Cont. and A208 Goal A pilots. No official candidate overwrite or
false final C2 approval; string-width ratio is diagnostic, not failure.
"""
import csv
import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

assert os.environ.get("OUTRUN_CPU_WORKER") == "github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE") == "A"
ROOT=Path.cwd()
OUT=ROOT/"localization/graphics/role_A/20261011-A245-Q193-ONLINE-CLEAN-REAL-GLYPH"
OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/"localization/graphics/role_A/20261009-A208-Q193-GOAL-A-FLAT-UI-PILOT/A208_SOURCE_CANONICAL_RGBA32.dds"
OFF=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds"
SRC_SHA="d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451"
OFF_SHA="9ea15d130693dd99bcd0ffa445b4799132665c5c93728c1c11783c94ba25b0f3"
BOX=(1660,156,1832,194)          # C1 fresh independent original English sprite bbox
CELL=(1651,150,1840,201)         # isolated text-only native crop, exact clean scope
FONT=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
FONT_INDEX=1
TARGET="온라인"
RUN_KEY="OUTRUN-KOR-A245-Q193-ONLINE-SOURCE-NATIVE-20261011-2100"
def sha(b):return hashlib.sha256(b).hexdigest()
def fileref(p):return {"path":str(p.relative_to(ROOT)),"sha256":sha(p.read_bytes())}
def png(n,im):
 p=OUT/n;im.save(p,"PNG");return fileref(p)
def report(n,o):
 p=OUT/n;p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf8");return fileref(p)
def check(x,why):
 if not x:raise RuntimeError(why)
def load(b):
 check(b[:4]==b"DDS " and len(b)==128+2048*1024*4,"DDS length/header mismatch")
 check(struct.unpack_from("<II",b,12)==(1024,2048),"native DDS dimensions unexpected")
 check(struct.unpack_from("<I",b,28)[0]==1,"DDS mip count not one")
 check(struct.unpack_from("<I",b,88)[0]==32,"DDS bitcount unexpected")
 check(struct.unpack_from("<IIII",b,92)==(255,65280,16711680,4278190080),"DDS RGBA masks unexpected")
 raw=Image.frombytes("RGBA",(2048,1024),b[128:],"raw","RGBA")
 return raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def bbox(mask):
 ys,xs=np.nonzero(mask)
 check(len(xs)>0,"empty native alpha bbox")
 return (int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
def flatten(im,bg):
 return Image.alpha_composite(Image.new("RGBA",im.size,(*bg,255)),im).convert("RGB")
with (ROOT/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(x for x in csv.DictReader(f) if x["index"].lstrip("\ufeff")=="193")
check(row["action"]=="localize_text" and "rework" in row["artwork_status"].lower(),
      "q193 no longer active A rework; fail closed")
check("OUTRUN-KOR-A243-Q193-15CONT-NATIVE-SOURCE-CLEAN-PILOT-20261011-1900" in row["notes"],
      "prior A243 in-flight consistency missing")
check(FONT.is_file(),"native Noto real Hangul font missing")
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","193"],capture_output=True,text=True,check=True)
report("A245_TRIAGE.json",{"stdout":tri.stdout,"action":"MATERIAL_REWORK_OF_C1_CONFIRMED_STRIPED_ONLINE_ONLY",
"prior_A243":"UNPROMOTED_SCOPED_C2_HOLD","run_key":RUN_KEY})
src_b=SRC.read_bytes()
old_b=OFF.read_bytes()
check(sha(src_b)==SRC_SHA,"Canonical English source SHA drift")
check(sha(old_b)==OFF_SHA,"Current promoted official q193 SHA drift")
check(src_b[:128]==old_b[:128],"Source and official DDS header not identical")
src=load(src_b);old=load(old_b)
S=np.array(src);B=np.array(old)
x0,y0,x1,y1=CELL
s_ina=S[y0:y1,x0:x1,3]>0
bb=bbox(s_ina)
measured_source=(bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0)
check(measured_source==BOX,"Actual English original source bbox diverged "+repr(measured_source))
check(np.count_nonzero(s_ina)>500,"ONLINE original glyph missing")
check(np.count_nonzero(S[y0:y1,x0:x1,3]>0)==np.count_nonzero(S[BOX[1]:BOX[3],BOX[0]:BOX[2],3]>0),
      "SOURCE English not only isolated original sprite in CELL")
# P1: the previously recorded A208 CLEAN was NOT blank in six inherited
# sprite areas. This genuinely removes the old Korean from the full cell.
C=B.copy()
C[y0:y1,x0:x1]=0
clean=Image.fromarray(C,"RGBA")
check(np.count_nonzero(C[y0:y1,x0:x1,3])==0,"True CLEAN alpha residue")
check(np.array_equal(C[:y0],B[:y0]) and np.array_equal(C[y1:],B[y1:]),
      "Outside CLEAN row changed")
png("A245_SOURCE_ONLINE_READABLE_NATIVE.png",src.crop(CELL))
png("A245_OLD_ONLINE_READABLE_NATIVE.png",old.crop(CELL))
png("A245_TRUE_CLEAN_ONLINE_READABLE_NATIVE.png",clean.crop(CELL))
png("A245_TRUE_CLEAN_FULL_RAW.png",clean.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
# P2: 4x anti-aliased real Korean font *without horizontal stretch*.
AA=4
FONT_SIZE=37
font=ImageFont.truetype(str(FONT),FONT_SIZE*AA,index=FONT_INDEX)
canvas=Image.new("L",(330*AA,80*AA),0)
ImageDraw.Draw(canvas).text((3*AA,0),TARGET,font=font,fill=255)
gbox=canvas.getbbox()
check(gbox is not None,"No Hangul rendered")
glyph4=canvas.crop(gbox)
glyph=glyph4.resize((round(glyph4.width/AA),round(glyph4.height/AA)),Image.Resampling.LANCZOS)
# native 1px containment of original glyph+effect bbox, not a required width ratio
check(glyph.width<=BOX[2]-BOX[0]-5 and glyph.height<=BOX[3]-BOX[1]-4,
      "Glyph cannot fit source bbox; must redesign, not clip")
px=BOX[0]+3
py=BOX[1]+(BOX[3]-BOX[1]-glyph.height)//2
check(px>=BOX[0]+2 and px+glyph.width<=BOX[2]-2 and
      py>=BOX[1]+1 and py+glyph.height<=BOX[3]-1,"Glyph placement overflow")
rgb_original=S[BOX[1]:BOX[3],BOX[0]:BOX[2]]
opaque=rgb_original[:,:,:3][rgb_original[:,:,3]>=240]
check(len(opaque)>30,"No original source face sample")
face_rgb=tuple(int(v) for v in np.median(opaque,axis=0))
# dark flat label, no invented source shadow/outline beyond original effect family
letter=Image.new("RGBA",(2048,1024))
layer=Image.new("RGBA",glyph.size,(*face_rgb,0))
layer.putalpha(glyph)
letter.alpha_composite(layer,(px,py))
pnmask=Image.new("L",(2048,1024));pnmask.paste(glyph,(px,py))
png("A245_NATIVE_GEOMETRY_RAW_L.png",pnmask.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
png("A245_LETTERING_RAW.png",letter.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
png("A245_LETTERING_READABLE_NATIVE.png",letter.crop(CELL))
# P3: only isolated SOURCE ONLINE cell edited; all 12 other UI labels including
# Goal A and recent A243 trial ROI remain official unchanged.
final_a=C.copy()
new_cell=Image.alpha_composite(clean.crop(CELL),letter.crop(CELL))
final_a[y0:y1,x0:x1]=np.asarray(new_cell)
changed=np.any(final_a!=B,axis=2)
allowed=np.zeros(changed.shape,bool);allowed[y0:y1,x0:x1]=True
outside=int(np.count_nonzero(changed & ~allowed))
check(outside==0,"Non-target atlas RGB/alpha modified")
candidate_box=bbox(final_a[:,:,3]>0 & np.zeros((1024,2048),bool)) if False else None
alpha_cell=final_a[y0:y1,x0:x1,3]>0
bb2=bbox(alpha_cell)
candidate_box=(x0+bb2[0],y0+bb2[1],x0+bb2[2],y0+bb2[3])
check(candidate_box[0]>=BOX[0]+1 and candidate_box[1]>=BOX[1]+1 and
      candidate_box[2]<=BOX[2]-1 and candidate_box[3]<=BOX[3]-1,
      "Actual glyph/edge exceeds original English native bbox")
trial_img=Image.fromarray(final_a,"RGBA")
TRIAL=OUT/"A245_Q193_ONLINE_TRUE_CLEAN_NATIVE_TRIAL_UNPROMOTED.dds"
TRIAL.write_bytes(src_b[:128]+trial_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA"))
decoded=load(TRIAL.read_bytes())
check(np.array_equal(np.asarray(decoded),final_a),"Persisted DDS not pixel-exact")
png("A245_PERSISTED_READABLE_NATIVE.png",decoded.crop(CELL))
png("A245_PERSISTED_RAW.png",decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
# optical cards: five stages on three opaque backgrounds at native/75/50,
# never use these display downscales as the DDS input.
for bgname,col in [("GRAY",(103,103,103)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
 parts=[flatten(z,col).crop((x0-3,y0-3,x1+3,y1+3)) for z in
        (src,old,clean,letter,decoded)]
 for pct in (100,75,50):
  ww=round(parts[0].width*pct/100);hh=round(parts[0].height*pct/100)
  sheet=Image.new("RGB",(len(parts)*ww,hh),col)
  for k,p in enumerate(parts):
   sheet.paste(p.resize((ww,hh),Image.Resampling.LANCZOS),(k*ww,0))
  png(f"A245_SOURCE_OLD_CLEAN_LETTER_SAVED_{bgname}_{pct}.png",sheet)
recipe=report("A245_SOURCE_FAMILY_NATIVE_GEOMETRY_RECIPE.json",{
 "schema":"a245-q193-online-native-source-v1","index":193,
 "source_sha256":SRC_SHA,"official_sha256":OFF_SHA,
 "font":{"family":"NotoSansCJK-Bold","path":str(FONT),"ttc_index":FONT_INDEX,
         "sha256":sha(FONT.read_bytes()),"SIL_Open_Font_License":True},
 "word":{"english":"ONLINE","korean":TARGET},"native_font_size":FONT_SIZE,"aa":AA,
 "native_source_bbox":BOX,"native_sprite_cell":CELL,
 "native_effects":{"flat_face_rgb_median":face_rgb,"bevel":0,"stroke":0},
 "align":"source left anchor +3; glyph naturally narrower","glyph_box":candidate_box,
 "method_change":"regenerated native AA Korean outlines and true independent transparent CLEAN; not the inherited low-res striped bitmap, not the Goal A pilot re-render",
 "qualification":"A_GEOMETRY_SELF_QA_ONLY_PENDING_INDEPENDENT_C2"
})
machine={
 "schema_version":2,"run":"A245","run_key":RUN_KEY,"role":"A","queue_index":193,
 "region":"ONLINE","original_text":"ONLINE","translation":"온라인",
 "source_sha256":SRC_SHA,"previous_official_sha256":OFF_SHA,"trial_sha256":sha(TRIAL.read_bytes()),
 "native_dds_size":[2048,1024],"dds_RGBA32_mip1":True,
 "source_bbox":BOX,"candidate_bbox":candidate_box,"bbox_margin":[candidate_box[0]-BOX[0],BOX[2]-candidate_box[2],candidate_box[1]-BOX[1],BOX[3]-candidate_box[3]],
 "changed_rgba_pixels":int(np.count_nonzero(changed)),"changed_outside_cell":outside,
 "clean_alpha_nonzero":0,"save_decode_exact":True,"original_header_equal":True,
 "glyph_width_diagnostic_only":glyph.width,"glyph_height":glyph.height,
 "geometry_recipe":recipe,"official_dds_modified":False,
 "A_producer_visual":"PENDING_CONTROLLER_ACTUAL_SAVED_NATIVE_BGW_100_75_50_RAW",
 "C2":"NOT_RUN","C3":"NOT_RUN","user_game":"IGR003_IGR019_IGR033_OPEN",
 "RUNTIME_VALIDATION":"UNTESTED","scope_exclusions":["VR","FFB","DX11","DXVK"]
}
report("A245_MACHINE_AND_HANDOFF.json",machine)
print(json.dumps({"run":"A245","persisted_sha256":machine["trial_sha256"],
 "changed_pixels":machine["changed_rgba_pixels"],"other_atlas_pixels_changed":outside,
 "bbox":candidate_box,"promotion":0},ensure_ascii=False),flush=True)
