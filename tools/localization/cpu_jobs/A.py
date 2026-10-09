#!/usr/bin/env python3
"""A211 source-chrome/real-glyph q175 SHOWROOM representative, trial only.

Distinct from A204 Orbit and A209/A210 hand-authored rail geometry:
render true Korean glyph outlines (font SHA in recipe), preserve counters,
derive chrome face from pinned source, then emit persisted BGRA DDS and
native/75/50 source-clean-prior-trial comparisons. No candidate promotion.
"""
import hashlib
import json
import os
import struct
import tempfile
import traceback
import urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt, gaussian_filter1d, gaussian_filter
from fontTools.ttLib import TTCollection

assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
ROOT=Path.cwd()
OUT=ROOT/"localization/graphics/role_A/20261010-A211-Q175-TRUE-GLYPH-CHROME-PILOT"
OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/"localization/graphics/role_A/20261008-A188-Q175-CHROME-FACE-RECOVERY"
CAND=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
SOURCE_SHA="9314372585b8309f2f8b3e714076ef1ad1999d770422a570398ef20a80ac10a5"
PROMOTED_SHA="b9f60b4582ddb4db525806454078471e1045f30a2d65e6da4d4681b87ee6ba73"
FONT=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
REGION=(6,397,956,529)
NAME="쇼룸"

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read_dds(path):
 data=Path(path).read_bytes()
 if data[:4]!=b"DDS " or len(data)!=128+2048*1024*4:raise RuntimeError("DDS format or size mismatch")
 h,w=struct.unpack_from("<II",data,12)
 masks=struct.unpack_from("<IIII",data,92)
 if (w,h)!=(2048,1024) or masks!=(16711680,65280,255,4278190080) or struct.unpack_from("<I",data,28)[0]!=1:
  raise RuntimeError("pinned DDS native format/mip mismatch")
 return data[:128],Image.frombytes("RGBA",(w,h),data[128:],"raw","BGRA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def save_dds(header,img,p):
 Path(p).write_bytes(header+img.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","BGRA"))
def comp(im,rgb):
 bg=Image.new("RGBA",im.size,(*rgb,255));bg.alpha_composite(im)
 return bg.convert("RGB")
def font_check():
 if not FONT.is_file():raise RuntimeError("pinned CJK licensed font missing")
 fonts=TTCollection(str(FONT))
 # The installed TTC font face must contain each Hangul precomposed glyph.
 maps=[set().union(*(t.cmap.keys() for t in x["cmap"].tables)) for x in fonts.fonts]
 if not any(all(ord(c) in cm for c in NAME) for cm in maps):
  raise RuntimeError("font does not cover target Korean syllables")
 return sha(FONT)
def glyph():
 # New glyph-native silhouette with unaltered real syllable topology.
 # Render at native final pixel height and crop, never upscale a prior DDS.
 for px in range(158,95,-1):
  ft=ImageFont.truetype(str(FONT),px)
  image=Image.new("L",(950,220),0)
  d=ImageDraw.Draw(image)
  d.text((20,1),NAME,font=ft,fill=255,stroke_width=1,stroke_fill=255)
  box=image.getbbox()
  if box is None:continue
  crop=image.crop(box)
  if 105<=crop.height<=114 and 180<=crop.width<=370:
   a=np.asarray(crop).astype(np.float32)
   # One source-independent corner rounding: 0.6px AA only, no glyph merging.
   sm=gaussian_filter(a,0.6)
   out=Image.fromarray(np.clip(sm,0,255).astype(np.uint8),"L")
   return out,px
 raise RuntimeError("No native Korean glyph size meets strict source height and counter gate")
def source_profile(box):
 arr=np.asarray(box.convert("RGBA"));a=arr[:,:,3]
 v=[]
 for y in range(len(a)):
  rgb=arr[y,:,:3].astype(np.float32)
  good=a[y]>150
  v.append(float(np.percentile(rgb[good].mean(axis=1),65)) if good.sum()>=18 else np.nan)
 vv=np.asarray(v,dtype=np.float32)
 g=np.where(np.isfinite(vv))[0]
 if len(g)<25:raise RuntimeError("not enough English-source chrome pixels")
 return np.clip(gaussian_filter1d(np.interp(np.arange(len(vv)),g,vv[g]),1.15),28,245)
def stage():
 if not CAND.exists() or sha(CAND)!=PROMOTED_SHA:raise RuntimeError("promoted q175 exact SHA drift")
 fontsha=font_check()
 hdr,prior=read_dds(CAND)
 with tempfile.TemporaryDirectory(prefix="outrun_A211_") as tmp:
  src=Path(tmp)/"canonical.dds"
  urllib.request.urlretrieve(SOURCE_URL,src)
  if sha(src)!=SOURCE_SHA:raise RuntimeError("English source canonical SHA mismatch")
  source_header,source=read_dds(src)
  clean=Image.open(BASE/"754F0599_HD_CLEAN_PLATE.png").convert("RGBA")
  if hdr!=source_header or source.size!=prior.size or clean.size!=source.size:raise RuntimeError("source/prior/clean shape mismatch")
  x0,y0,x1,y1=REGION
  S=np.asarray(source);B=np.asarray(prior)
  plate=prior.copy();plate.paste(clean.crop(REGION),(x0,y0))
  P=np.asarray(plate)
  # Dedicated CLEAN stage happens and is persisted before letter composition.
  if np.any(P[y0:y1,x0:x1,3]):raise RuntimeError("not a genuinely transparent CLEAN region")
  allow=np.zeros((1024,2048),dtype=bool);allow[y0:y1,x0:x1]=True
  if np.any(np.any(P!=B,axis=2)&~allow):raise RuntimeError("P1 CLEAN outside source effects")
  plate.save(OUT/"A211_PLATE_ONLY_READABLE.png")
  mask,ppem=glyph()
  g=np.asarray(mask)
  # Independent counter topology (font preserves native syllable counters).
  if int(np.count_nonzero((g>128)))<8500:raise RuntimeError("font glyph too thin")
  gx=x0+18;gy=y0+9
  if gy+mask.height+5>=y1:raise RuntimeError("effect would touch source bottom")
  density=(g>20)
  dist=distance_transform_edt(density)
  nx=np.gradient(dist.astype(np.float32),axis=1)
  ny=np.gradient(dist.astype(np.float32),axis=0)
  # Real English pixel profile plus directional metal relief, unlike A210 flat
  # manually drawn rails. Normalize *within* source sprite native coordinates.
  yy=np.clip(np.arange(mask.height)+gy-y0,0,y1-y0-1)
  bands=source_profile(source.crop(REGION))[yy][:,None]
  base=np.broadcast_to(bands,g.shape)
  light=np.clip(0.5-np.minimum(0,nx+ny),0,1.3)*23
  dark=np.clip(0.4+np.maximum(0,nx+ny),0,1.5)*25
  face=np.clip(base+light-dark+8*np.clip(dist/5,0,1),23,253)
  rgba=np.zeros((*g.shape,4),dtype=np.uint8)
  rgba[:,:,:3]=face.astype(np.uint8)[:,:,None]
  rgba[:,:,3]=g
  layer=Image.fromarray(rgba,"RGBA")
  # Keep dark metal-side extrusion independently on transparent layer;
  # clip all effects inside source bbox with strictly positive margins.
  shadow=Image.new("RGBA",mask.size,(26,27,36,0))
  shadow.putalpha(Image.fromarray((g.astype(np.float32)*0.62).astype(np.uint8),"L"))
  final=plate.copy()
  final.alpha_composite(shadow,(gx+3,gy+4))
  final.alpha_composite(layer,(gx,gy))
  effect=np.zeros((1024,2048),dtype=bool)
  effect[gy:gy+mask.height,gx:gx+mask.width]|=(g>0)
  effect[gy+4:gy+4+mask.height,gx+3:gx+3+mask.width]|=(g>0)
  F=np.asarray(final);changes=np.any(F!=B,axis=2)
  glyph_change=np.any(F!=P,axis=2)
  ys,xs=np.nonzero(effect)
  bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
  margins=[bbox[0]-x0,x1-bbox[2],bbox[1]-y0,y1-bbox[3]]
  gate={
   "clean_alpha_nonzero":int(np.count_nonzero(P[y0:y1,x0:x1,3])),
   "prior_final_RGBA_changed_outside_source":int(np.count_nonzero(changes&~allow)),
   "prior_final_alpha_changed_outside_source":int(np.count_nonzero((B[:,:,3]!=F[:,:,3])&~allow)),
   "clean_final_changed_outside_glyph_effect":int(np.count_nonzero(glyph_change&~effect)),
   "margins":margins,"bbox":bbox
  }
  if any(gate[k] for k in ("clean_alpha_nonzero","prior_final_RGBA_changed_outside_source","prior_final_alpha_changed_outside_source","clean_final_changed_outside_glyph_effect")) or min(margins)<1:
   raise RuntimeError(("P3 source/protection fail",gate))
  path=OUT/"A211_Q175_SHOWROOM_TRUEGLYPH_CHROME_TRIAL.dds"
  save_dds(hdr,final,path)
  fh,saved=read_dds(path)
  if fh!=hdr or not np.array_equal(np.asarray(saved),F):raise RuntimeError("persisted exact DDS roundtrip failed")
  saved.save(OUT/"A211_PERSISTED_READABLE.png")
  saved.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT/"A211_PERSISTED_RAW.png")
  mask.save(OUT/"A211_LETTERING_MASK.png")
  for name,rgb in (("GRAY",(104,104,104)),("WHITE",(255,255,255)),("BLACK",(0,0,0))):
   samples=[comp(im,rgb).crop((0,y0-8,x1+14,y1+14)) for im in (source,plate,prior,saved)]
   w,h=samples[0].size
   sheet=Image.new("RGB",(w*4+36,h+35),rgb)
   d=ImageDraw.Draw(sheet);d.text((8,7),"A211 SOURCE | CLEAN | PREV A188 | NEW NATIVE GLYPH",fill=(250,210,0) if name!="WHITE" else (0,0,0))
   for i,img in enumerate(samples):sheet.paste(img,(i*(w+12),35))
   for scale in (100,75,50):
    view=sheet if scale==100 else sheet.resize((sheet.width*scale//100,sheet.height*scale//100),Image.Resampling.LANCZOS)
    view.save(OUT/f"A211_{name}_{scale}.jpg",quality=94)
  report={"run":"A211","role":"A","queue_index":175,"priority":"P1","issue":"IGR-032",
   "status":"TRIAL_ONLY_AWAITING_CONTROLLER_VISUAL","source_sha256":SOURCE_SHA,
   "promoted_current_sha256":PROMOTED_SHA,"trial_sha256":sha(path),
   "trial_dds":1,"production_dds":0,"font_path":str(FONT),"font_sha256":fontsha,
   "font_license":"NotoSansCJK Open Font License; system package fonts-noto-cjk",
   "native_ppem":ppem,"original_bbox":list(REGION),"trial_bbox":bbox,
   "trial_size":[bbox[2]-bbox[0],bbox[3]-bbox[1]],
   "source_size":[x1-x0,y1-y0],"numerical":gate,"persisted_dds":"BGRA32 2048x1024 mip1 mirror_Y decoded match",
   "method":"Genuine licensed Hangul glyph strokes, source-derived chrome bands with local edge-normal light, isolated depth layer; not A204 Orbit or A209/A210 hand rail",
   "new_user_game":"NOT_TESTED","independent_C1":"BLOCKED_UNTIL_PRODUCER_VISUAL","C3":"BLOCKED",
   "RUNTIME_VALIDATION":"UNTESTED"}
  (OUT/"A211_PILOT_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
  print("A211_PERSISTED_TRIAL",json.dumps({"sha256":report["trial_sha256"],"bbox":bbox,"gate":gate},ensure_ascii=False),flush=True)

try:stage()
except Exception as ex:
 fail={"run":"A211","role":"A","queue_index":175,"status":"PRODUCER_FAIL_CANDIDATE_UNCHANGED",
 "error_type":type(ex).__name__,"error":str(ex),"traceback":traceback.format_exc(),
 "production_dds":0,"RUNTIME_VALIDATION":"UNTESTED"}
 (OUT/"A211_EXECUTION_FAIL.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
 print("A211_ABORTED",str(ex),flush=True)
