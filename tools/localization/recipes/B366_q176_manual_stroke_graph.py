#!/usr/bin/env python3
"""B366 q176 P2 manual stroke-graph Hangul geometry; source numeral 4 preserved.
Stage 1: geometry + 4-way lossless preview only. Geometry must be inspected by
the controller before a GEOMETRY_READY review and persisted unapproved DDS.
"""
import io,os,hashlib,json,sys,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
H=lambda b:hashlib.sha256(b).hexdigest()
G=Path("localization/graphics")
OUT=G/"role_B/20261011-B366-Q176-SOURCE-NUMERAL-MANUAL-STROKES"
OUT.mkdir(parents=True,exist_ok=True)
ASSET="textures/load/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
SRC_SHA="8ba40915abca8b7022acbcc743e93186970fdf7e29f0eb80e84903d31074c708"
CLEAN_SHA="29e77ca7391022eff23b84a197a41c123938f3aa03a6fb7c69a783d0ce0b6ebe"
OFFICIAL_SHA="494d42c09c58241405dd14de74ca976b5432d84eb250d4bceb5684e97fbad407"
old=(G/"hd_candidates"/ASSET).read_bytes()
assert H(old)==OFFICIAL_SHA,("OFFICIAL_CONCURRENT_CHANGE",H(old))
tri=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","176"],text=True,capture_output=True,check=True).stdout)["assets"][0]
assert tri["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),tri
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
with urllib.request.urlopen(url,timeout=90) as fh:source=fh.read()
assert H(source)==SRC_SHA and len(source)==len(old)==16777344 and source[:128]==old[:128]
cp=(G/"role_B/20261010-B346-Q176-SOURCE-HEAVY-RED-FONT-PILOT/B346_P1_CLEAN_SOURCE_ONLY.png").read_bytes()
assert H(cp)==CLEAN_SHA
def dec(b):
 return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
src=dec(source);off=dec(old);clean=np.array(Image.open(io.BytesIO(cp)).convert("RGBA"))
assert src.shape==off.shape==clean.shape==(2048,2048,4)
x0,y0,x1,y1=(8,49,988,204)
assert int(np.count_nonzero(clean[y0:y1,x0:x1,3]))==0
# Source-authentic integer symbol, retained rather than retyped. Find its
# RIGHTMOST opaque original source component after the last word-gap.
row=(src[y0:y1,x0:x1,3]>32)
col=np.count_nonzero(row,axis=0)
runs=[];start=None
for i,count in enumerate(col):
 if count and start is None:start=i
 if start is not None and (not count or i==len(col)-1):
  end=i if not count else i+1
  runs.append([start,end])
  start=None
candidates=[(a,b) for a,b in runs if a>650 and 45<=(b-a)<=160]
assert candidates,("SOURCE_DIGIT_ISOLATION_FAIL",runs)
nl,nr=candidates[-1]
assert nl>780 and nr<=980,("SOURCE_NUMERAL_NOT_FINAL",nl,nr)
number=np.zeros_like(src)
number[y0:y1,x0+nl:x0+nr]=src[y0:y1,x0+nl:x0+nr]
assert int(np.count_nonzero(number[:,:,3]))>1500
# Fully handcrafted native stroke graph. FOUR Hangul syllables are *not* from
# a previous font raster. Source-conditioned 150px uppercase stroke frame.
# Strokes and counter-spaces individually authored; no bitmap upscale, font
# swap, random shear, morphology or blind global width fitting.
S=3
W=790
glyph=Image.new("L",(W*S,155*S),0)
d=ImageDraw.Draw(glyph)
def polygon(points):d.polygon([(round(x*S),round(y*S)) for x,y in points],fill=255)
def rect(x,y,w,h):polygon([(x,y),(x+w,y),(x+w,y+h),(x,y+h)])
# 플 — top ㅍ, native horizontal vowel and lower ㄹ, square-source family.
X=10
rect(X+12,9,152,21);rect(X+33,34,21,38);rect(X+123,34,21,38)
rect(X+12,66,152,21);rect(X+12,91,152,19)
rect(X+12,112,23,30);rect(X+12,122,151,20)
# 래 — open ㄹ terminals, two independent vowels ㅐ.
X=210
rect(X+4,10,93,19);rect(X+77,15,20,43);rect(X+4,53,93,18)
rect(X+4,53,18,46);rect(X+4,86,93,18);rect(X+77,86,18,39)
rect(X+4,112,93,18)
rect(X+113,8,21,133);rect(X+137,52,36,18);rect(X+152,9,20,132)
# 그 — square heavy ㄱ and baseline ㅡ.
X=410
rect(X+4,9,152,23);rect(X+132,20,23,77);rect(X+4,116,152,23)
# 맨 — open ㅁ counter, ㅐ and native wide ㄴ.
X=600
rect(X+6,10,103,18);rect(X+6,10,20,75);rect(X+90,10,19,75)
rect(X+6,67,103,18)
rect(X+124,8,20,94);rect(X+146,39,31,19);rect(X+167,8,18,94)
rect(X+8,104,21,35);rect(X+8,121,169,18)
# Single explicitly documented 3x vector anti-alias raster-downsample.
mask=np.asarray(glyph.resize((W,155),Image.Resampling.LANCZOS))
mask=np.where(mask<4,0,mask).astype(np.uint8)
assert not np.any(mask[:,nl-4:]),("GLYPH_INTO_SOURCE_NUMBER",nl)
N=off.copy()
N[y0:y1,x0:x1]=clean[y0:y1,x0:x1]
roi=N[y0:y1,x0:x0+W]
rgb=np.array([186,0,0],dtype=np.uint8)
roi[mask>0,:3]=rgb;roi[:,:,3]=mask
# Number must keep the SOURCE pixels exactly, including original red face
# and antialias, rather than stretching newly drawn Korean/numeral font.
N[y0:y1,x0+nl:x0+nr]=number[y0:y1,x0+nl:x0+nr]
assert np.array_equal(N[y0:y1,x0+nl:x0+nr],src[y0:y1,x0+nl:x0+nr])
change=np.any(N!=off,axis=2)
allowed=np.zeros((2048,2048),bool);allowed[y0:y1,x0:x1]=True
assert int(np.count_nonzero(change&~allowed))==0
ink=np.argwhere(N[y0:y1,x0:x1,3]>0)
ymin,xmin=ink.min(axis=0);ymax,xmax=ink.max(axis=0)+1
bbox=[int(x0+xmin),int(y0+ymin),int(x0+xmax),int(y0+ymax)]
# The original numeral touches the English effect bbox right/bottom edge.
# Preserving those EXACT source pixels is permitted; only NEW Hangul must have
# positive margins, never enlarge by 1px beyond the canonical English bound.
assert bbox[0]>x0 and bbox[1]>y0 and bbox[2]<=x1 and bbox[3]<=y1,("SOURCE_GLYPH_CEILING",bbox)
assert np.count_nonzero(mask[-2:,:])==0 and np.count_nonzero(mask[:2,:])==0
# Source must be exact native RAW geometry. Direct repo-bound letter input
# created for later compose_lettering verification after controller first look.
Image.fromarray(src[::-1].copy(),"RGBA").save(OUT/"SOURCE_RAW_RGBA.png")
geometry=N[:,:,3].copy()
geometry[~allowed]=0
geometry=geometry[::-1].copy()
Image.fromarray(geometry,"L").save(OUT/"GEOMETRY_RAW_ALPHA.png")
face=np.zeros_like(src)
face[y0:y1,x0:x1]=N[y0:y1,x0:x1]
Image.fromarray(face[::-1].copy(),"RGBA").save(OUT/"FACE_RAW_RGBA.png")
# Preview source/CLEAN/official/trial in readable and RAW BEFORE promoting
# geometry review, with no pretense that controller has already seen it.
evidence=[]
for orient in ["FLIPY","RAW"]:
 for bg,pct in ([(128,100),(255,75),(0,50)] if orient=="FLIPY" else [(128,100)]):
  imgs=[]
  for image in ([src,clean,off,N] if orient=="FLIPY" else [v[::-1] for v in [src,clean,off,N]]):
   yy0,yy1=(y0-4,y1+4) if orient=="FLIPY" else (2048-y1-4,2048-y0+4)
   crop=Image.fromarray(image[yy0:yy1,x0-4:x1+4].copy(),"RGBA")
   back=Image.new("RGBA",crop.size,(bg,bg,bg,255));back.alpha_composite(crop)
   view=back.convert("RGB")
   if pct!=100:view=view.resize((view.width*pct//100,view.height*pct//100),Image.Resampling.LANCZOS)
   imgs.append(view)
  w,h=imgs[0].size
  montage=Image.new("RGB",(w*4+30,h),(bg,bg,bg))
  for i,im in enumerate(imgs):montage.paste(im,(i*(w+10),0))
  name=f"B366_SOURCE_CLEAN_OLD_MANUAL_{orient}_BG{bg}_{pct}.png"
  montage.save(OUT/name);evidence.append(name)
qa={"run":"B366","role":"B","index":176,"stage":"P2_GEOMETRY_PROPOSED_NO_DDS_YET",
"source_sha256":SRC_SHA,"clean_sha256":CLEAN_SHA,"official_sha256":OFFICIAL_SHA,
"source_number_component_relative":[nl,nr],"source_number_preserved_pixels":int(np.count_nonzero(number[:,:,3])),
"source_bbox":[x0,y0,x1,y1],"new_bbox":bbox,
"changed_inside_source_bbox":int(change.sum()),"outside":0,"other3":"EXACT_UNCHANGED",
"method":"Manual native 3x stroke graphs for 4 Hangul syllables with exact original source numeral 4; one explicit LANCZOS AA to 2048 native; no prior Hangul bitmap",
"route":"vector_title","geometry_status":"PENDING_CONTROLLER_VISUAL_REVIEW","C2":"NOT_RUN","C3":"NOT_RUN","game":"UNTESTED",
"dds_created":0,"evidence":evidence,"excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B366_GEOMETRY_PROPOSAL.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
(OUT/"B366_MANUAL_STROKE_GRAPH.json").write_text(json.dumps({"version":"manual-stroke-graph-v1","glyph":"플래그맨 4","vector_native":True,
"stroke_coordinates_native":True,"antialias":"Pillow LANCZOS x3 once","editable_script":"tools/localization/cpu_jobs/B.py",
"source_numeric_original_is_preserved":True,"source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
"glyph_bbox":bbox,"source_reference_sha256":SRC_SHA},ensure_ascii=False,indent=2)+"\n")
print(json.dumps(qa,ensure_ascii=False),flush=True)
