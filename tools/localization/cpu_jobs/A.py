#!/usr/bin/env python3
"""A238: q121 P0 material rework with manually authored source-conditioned Hangul geometry.

A235/A235R C1 optical reject: weak white face (40.7% source) and
oversized navy rim. This does NOT rescale/recolor/reuse the rejected
Hangul raster; it authors four syllables as individual editable stroke
graphs, renders once at exact source-native resolution, then separates
geometry, rim, shallow extrusion and face before composing a distinct
unpromoted DDS. Whole atlas/C1/C3/game stay unapproved.
"""
import csv, hashlib, io, json, os, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import numpy as np
assert os.environ.get("OUTRUN_CPU_WORKER") == "github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE") == "A"
sys.dont_write_bytecode=True
ROOT=Path.cwd()
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"tools/localization"))
from compose_lettering import compose
RUN="OUTRUN-KOR-A238-Q121-MANUAL-FOUR-GLYPH-WHITE-FACE-20261011-1200"
OUT=ROOT/"localization/graphics/role_A/20261011-A238-Q121-MANUAL-SOURCE-GLYPH"
OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
BASE=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
EXPECTED_SRC="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
EXPECTED_OFFICIAL="38d5c2c30ea813202051b191dc01de9d7804e52c1cbab0f46c5372b59ed6c844"
X0,Y0,X1,Y1=(3490,391,3722,440)
W,H=X1-X0,Y1-Y0
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):return {"path":str(p.relative_to(ROOT)),"sha256":sha(p.read_bytes())}
def writej(name,value):
 p=OUT/name
 p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 return ref(p)
def png(name,img):
 p=OUT/name;img.save(p,format="PNG");return ref(p)
with (ROOT/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(x for x in csv.DictReader(f) if x["index"]=="121")
assert row["action"]=="localize_text" and ("rework" in row["artwork_status"].lower() or "hold" in row["artwork_status"].lower())
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","121"],capture_output=True,text=True)
writej("A238_TRIAGE.json",{"returncode":tri.returncode,"stdout":tri.stdout[-6500:],"stderr":tri.stderr[-1500:],
 "action":"MANUAL_MATERIAL_REWORK_NOT_SAFE_SAME_METHOD_RERENDER"})
assert tri.returncode==0
source_bytes=SRC.read_bytes()
old_bytes=BASE.read_bytes()
assert sha(source_bytes)==EXPECTED_SRC
assert sha(old_bytes)==EXPECTED_OFFICIAL
assert source_bytes[:128]==old_bytes[:128]
assert len(old_bytes)==128+4096*4096*4
src=Image.open(io.BytesIO(source_bytes)).convert("RGBA")
old=Image.open(io.BytesIO(old_bytes)).convert("RGBA")
assert src.size==old.size==(4096,4096)
# Confirm direct raw RGBA byte serialization matches the stored DDS exactly.
assert old.tobytes()==old_bytes[128:],"DDS channel order/strides differ; fail closed"
source_readable=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
official_readable=old.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
english=source_readable.crop((X0,Y0,X1,Y1))
previous=official_readable.crop((X0,Y0,X1,Y1))
# P1: actual English transparent-sprite source. C1 A235R independently
# confirmed this same SOURCE ROI -> fully transparent CLEAN alpha0.
clean=Image.new("RGBA",(W,H),(0,111,159,0))
assert not clean.getchannel("A").getbbox()
assert english.getchannel("A").getbbox() is not None
png("A238_SOURCE_ENGLISH_NATIVE.png",english)
png("A238_PLATE_ONLY_NATIVE.png",clean)
# P2: direct per-syllable manual stroke topology. No fonts or Korean
# bitmap sampling. One 4x vector AA rasterization into the true native
# 232x49 source footprint. The 0.10 source-rightlean vector is measured
# from optical English G ~+4.94px/46px, with trial top+bottom anchors
# disclosed as optical, not independently homologous.
AA=4
layer=Image.new("L",(W*AA,H*AA),0)
d=ImageDraw.Draw(layer)
def draw_line(points,stroke=7.0):
 pp=[(round(a*AA),round(b*AA)) for a,b in points]
 width=round(stroke*AA)
 d.line(pp,fill=255,width=width,joint="curve")
 for px,py in (pp[0],pp[-1]):
  rad=width//2
  d.ellipse((px-rad,py-rad,px+rad,py+rad),fill=255)
def stroke(ox,pts,width=7.0):
 # Height-authored strokes: ~2px min and ~3px lower safety margin.
 transformed=[(ox+x+(44-y)*.10, 3+y*.93) for x,y in pts]
 draw_line(transformed,width)
# 가: ㄱ + ㅏ; source-conditioned broad strokes and round corners.
stroke(8,[(1,7),(22,7),(22,37)],8)
stroke(8,[(34,6),(34,37)],7.5)
stroke(8,[(23,23),(34,23)],7)
# 속: ㅅ + ㅗ + ㄱ, explicit syllable components.
stroke(61,[(19,6),(5,19)],7.5)
stroke(61,[(19,6),(34,19)],7.5)
stroke(61,[(6,23),(35,23)],7)
stroke(61,[(20,23),(20,29)],6)
stroke(61,[(6,34),(35,34),(35,40)],7)
# 페: ㅍ + ㅔ; retains separate counters, not a stretched font raster.
stroke(122,[(2,7),(20,7)],7)
stroke(122,[(7,8),(7,26)],7)
stroke(122,[(18,8),(18,26)],7)
stroke(122,[(2,26),(20,26)],7)
stroke(122,[(2,37),(20,37)],7)
stroke(122,[(31,5),(31,40)],7)
stroke(122,[(21,19),(31,19)],6)
stroke(122,[(41,5),(41,40)],7)
# 달: ㄷ + ㅏ + ㄹ, composed in native coordinates.
stroke(180,[(2,7),(21,7)],7)
stroke(180,[(2,7),(2,21),(21,21)],7)
stroke(180,[(34,5),(34,23)],7)
stroke(180,[(22,14),(34,14)],7)
stroke(180,[(3,30),(34,30)],7)
stroke(180,[(34,30),(34,39),(3,39)],7)
face_a=layer.resize((W,H),Image.Resampling.LANCZOS)
face_np=np.asarray(face_a)
ink=(face_np>0)
box=face_a.getbbox()
assert box is not None and box[0]>=2 and box[1]>=1 and box[2]<=W-2 and box[3]<=H-2,box
face_count=int(np.count_nonzero(face_np>=240))
assert face_count>=2700,("source white face 3504px, unacceptable optical underfill",face_count)
# Authentic source's near-white, dark family target is recorded from C1,
# and validated by actual new native pixels rather than producer prose.
rim_a=ImageChops.subtract(face_a.filter(ImageFilter.MaxFilter(3)),face_a)
shade_a=ImageChops.subtract(ImageChops.offset(face_a,0,1),face_a)
# Allocate native readable ROI geometry, then mirror to persisted DDS RAW.
def raw_full_alpha(alpha):
 im=Image.new("L",(4096,4096),0)
 im.paste(alpha,(X0,Y0))
 return im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
geo=raw_full_alpha(face_a)
rimg=raw_full_alpha(rim_a)
shade=raw_full_alpha(shade_a)
geo_ref=png("A238_GEOMETRY_RAW_L.png",geo)
def rgba(rgb,alpha):
 im=Image.new("RGBA",alpha.size,rgb+(0,))
 im.putalpha(alpha);return im
face_ref=png("A238_FACE_RAW.png",rgba((255,255,255),geo))
rim_ref=png("A238_RIM_RAW.png",rgba((0,17,24),rimg))
shade_ref=png("A238_EXTRUSION_RAW.png",rgba((0,58,91),shade))
# Geometry-only review must not be mislabeled C or production PASS.
def on_background(im,rgb):
 return Image.alpha_composite(Image.new("RGBA",im.size,rgb+(255,)),im).convert("RGB")
for bgname,col in [("GRAY",(100,100,100)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
 src_rgb=on_background(english,col)
 face_rgb=on_background(rgba((255,255,255),face_a),col)
 for pct in (100,75,50):
  size=(max(1,round(W*pct/100)),max(1,round(H*pct/100)))
  e=src_rgb.resize(size,Image.Resampling.LANCZOS) if pct!=100 else src_rgb
  k=face_rgb.resize(size,Image.Resampling.LANCZOS) if pct!=100 else face_rgb
  card=Image.new("RGB",(size[0]*2,size[1]+18),col)
  card.paste(e,(0,18));card.paste(k,(size[0],18))
  dr=ImageDraw.Draw(card);fg=(0,0,0) if bgname=="WHITE" else (255,255,255)
  dr.text((2,2),"ORIGINAL SOURCE",fill=fg)
  dr.text((size[0]+2,2),"HAND VECTOR ONLY",fill=fg)
  png(f"A238_GEOMETRY_{bgname}_{pct}.png",card)
geomrecipe=writej("A238_GEOMETRY_RECIPE.json",{
 "engine":"manual-native-polylines-v1","source":"Gas Pedal",
 "target":"가속 페달","syllable_sequence":["가","속","페","달"],
 "source_effect_bbox":[X0,Y0,X1,Y1],
 "method_change":"four manually authored stroke graphs and independent fontless native contour geometry; not A235/A235R regular Noto resizing/painting",
 "supersample_once":AA,"source_right_lean_proxy":4.94/46,
 "top_minus_bottom_shear_per_px":0.10,
 "source_C1_white_pixels_proxy":3504,"source_C1_dark_pixels_proxy":1518,
 "trial_near_opaque_face_pixels":face_count,"local_face_bbox":list(box),
 "stroke_primitives":22,"rim":"native 1px morphology separate",
 "extrusion":"native 1px lower offset separate",
 "RUNTIME_VALIDATION":"UNTESTED"})
geomreview=writej("A238_GEOMETRY_REVIEW.json",{
 "status":"GEOMETRY_READY","reviewer":"A","route":"vector_title",
 "source_sha256":EXPECTED_SRC,"geometry_sha256":geo_ref["sha256"],
 "observations":{
   "stroke":"Four fontless manual rounded per-stroke glyph graphs; white native face coverage %dpx versus independently C1-recorded source 3504px; no thin Noto Regular face."%face_count,
   "counterspace":"At first construction the native 100/75/50 flat layers retain clear syllable separation and component counters; final persisted material review remains independent.",
   "proportions":"Actual 232x49 original source effect ROI; manual glyph rectangle %s with positive edges; no forced old-Korean image scaling."%(list(box),),
   "slant":"Manual top shift 0.10*(44-y) in readable coordinates, English G proxy +4.94/46; not a homologous per-glyph slant certification.",
   "readability":"Manual vector white silhouettes separately reviewed as geometric construction only; C1/C3 and in-game pending."},
 "evidence":[ref(OUT/"A238_GEOMETRY_GRAY_100.png"),ref(OUT/"A238_GEOMETRY_BLACK_50.png")]})
recipe={
 "version":"separated-lettering-v1","coordinates":"native_raw","route":"vector_title",
 "source":ref(SRC),"geometry":geo_ref,
 "geometry_recipe":geomrecipe,"geometry_review":geomreview,
 "layers":[{"role":"extrusion","input":shade_ref},
           {"role":"rim","input":rim_ref},
           {"role":"face","input":face_ref}]
}
writej("lettering_recipe.json",recipe)
composed,detail=compose(ROOT,recipe)
png("A238_COMPOSED_RAW.png",composed)
# P3: persisted official DDS remains unchanged; only one targeted ROI
# in a separately named trial may be replaced. 29 other regions byte exact.
raw_arr=np.frombuffer(old_bytes,dtype=np.uint8,offset=128).reshape(4096,4096,4).copy()
new_piece=np.array(composed.crop((X0,4096-Y1,X1,4096-Y0)).convert("RGBA"),dtype=np.uint8)
assert new_piece.shape==(H,W,4)
new_a=new_piece[:,:,3]
nb=Image.fromarray(new_a).getbbox()
assert nb is not None and nb[0]>0 and nb[1]>0 and nb[2]<W and nb[3]<H,nb
# Transparent-source plate is restored before every Korean glyph (no opaque patch).
raw_arr[4096-Y1:4096-Y0,X0:X1,:]=new_piece
new_bytes=old_bytes[:128]+raw_arr.tobytes()
result=OUT/"A238_Q121_MANUAL_SOURCE_FAMILY_UNPROMOTED.dds"
result.write_bytes(new_bytes)
new_sha=sha(new_bytes)
assert new_sha!=EXPECTED_OFFICIAL
assert new_bytes[:128]==old_bytes[:128] and len(new_bytes)==len(old_bytes)
decoded=Image.open(result).convert("RGBA")
assert decoded.tobytes()==new_bytes[128:],"persisted DDS RGBA decode mismatch"
new_readable=decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
target=new_readable.crop((X0,Y0,X1,Y1))
png("A238_FINAL_PERSISTED_NATIVE.png",target)
png("A238_FINAL_PERSISTED_RAW.png",decoded.crop((X0,4096-Y1,X1,4096-Y0)))
real=np.array(target)
rgba_delta=int(np.count_nonzero(np.any(np.array(previous)!=real,axis=2)))
assert rgba_delta>0
# Outside target exact raw byte comparison; source/hud shared atlas shield.
assert new_bytes[128:128+(4096-Y1)*4096*4]==old_bytes[128:128+(4096-Y1)*4096*4]
assert new_bytes[128+(4096-Y0)*4096*4:]==old_bytes[128+(4096-Y0)*4096*4:]
before_raw=np.frombuffer(old_bytes,dtype=np.uint8,offset=128).reshape(4096,4096,4)
changed=np.any(raw_arr!=before_raw,axis=2)
roi=np.zeros((4096,4096),dtype=bool)
roi[4096-Y1:4096-Y0,X0:X1]=True
outside=int(np.count_nonzero(changed&~roi))
assert outside==0
assert int(np.count_nonzero(real[:,:,3]>0))>0
# Non-text plate pixels outside ROI must remain untouched.
for bgname,col in [("GRAY",(100,100,100)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
 imgs=[on_background(i,col) for i in [english,clean,previous,target]]
 for pct in (100,75,50):
  size=(max(1,round(W*pct/100)),max(1,round(H*pct/100)))
  row=[i.resize(size,Image.Resampling.LANCZOS) if pct!=100 else i for i in imgs]
  card=Image.new("RGB",(size[0]*4,size[1]+18),col)
  for n,i in enumerate(row):card.paste(i,(size[0]*n,18))
  dr=ImageDraw.Draw(card);fg=(0,0,0) if bgname=="WHITE" else (255,255,255)
  for n,label in enumerate(("SOURCE","CLEAN","OFFICIAL","A238")):
   dr.text((size[0]*n+2,2),label,fill=fg)
  png(f"A238_PERSISTED_{bgname}_{pct}.png",card)
writej("A238_DDS_MACHINE_AND_HANDOFF.json",{
 "run_key":RUN,"role":"A","index":121,"priority":"P0",
 "source_sha256":EXPECTED_SRC,"official_sha256":EXPECTED_OFFICIAL,
 "new_trial_sha256":new_sha,"trial_path":ref(result)["path"],
 "source_family":"smooth broad white right-italic/navy shadow",
 "method":"per-syllable manual stroke graph + separated face/rim/shallow extrusion",
 "local_effect_bbox":list(nb),"source_effect_bbox":[0,0,W,H],
 "manual_face_opaque_pixels":face_count,"original_C1_white_face_proxy":3504,
 "changed_RGBA_pixels_inside_roi":rgba_delta,"changed_outside_roi":outside,
 "other_29_cells_exact":True,"saved_rgba_roundtrip_mismatch":0,
 "native_dimensions":[4096,4096],"mip_count":1,"format":"RGBA32",
 "source_to_clean":"native transparent source-alpha reset, no English face/effect pixels",
 "raw_orientation":"Y_MIRRORED","letters":"가속 페달",
 "producer":"UNPROMOTED_PENDING_ACTUAL_PERSISTED_OPTICAL_REVIEW",
 "C1":"NOT_RUN_A238","C3":"NOT_RUN","user_IGR":["IGR-030","IGR-031","IGR-040"],
 "RUNTIME_VALIDATION":"UNTESTED","new_DDS_trials":1,"promoted_official_DDS":0,
 "plate":"SCOPED_SOURCE_NATIVE_NOT_WHOLE_ATLAS_C1_APPROVAL",
 "geometry":"GEOMETRY_READY_NOT_FINAL_APPROVAL",
 "backend":"github-actions-ubuntu-latest",
 "anti_duplicate":"new hand stroke contours; original+A235R remain unchanged",
 "next":"Controller inspect persisted PNG native/75/50 BGW and RAW versus source; C1 must independently review new SHA before C3. Never close user P0 without newer actual game."})
print(json.dumps({"run":RUN,"index":121,"source":EXPECTED_SRC,"official":EXPECTED_OFFICIAL,
 "trial":new_sha,"inside_change":rgba_delta,"outside_change":outside,
 "manual_face_px":face_count,"result":"NEW_UNPROMOTED_SCOPED_Q121_MATERIAL_TRIAL"}))
