#!/usr/bin/env python3
"""A209: q175 source-shaped HAND-AUTHORED connected Hangul vector method pilot.

Produces one showroom trial DDS in role_A only. Never changes hd_candidates
without independent SOURCE/CLEAN/TRIAL pixel inspection and final pixel manifest.
No generic shear/stretch, A204 Orbit glyph, or blind width target.
"""
import hashlib
import json
import os
import struct
import tempfile
import urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter1d, distance_transform_edt
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
R=Path.cwd()
DIR=R/"localization/graphics/role_A/20261009-A209-Q175-SHOWROOM-ROUNDED-VECTOR-PILOT"
DIR.mkdir(parents=True,exist_ok=True)
BASE=R/"localization/graphics/role_A/20261008-A188-Q175-CHROME-FACE-RECOVERY"
CAND=R/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
SOURCE_SHA="9314372585b8309f2f8b3e714076ef1ad1999d770422a570398ef20a80ac10a5"
OLD_SHA="b9f60b4582ddb4db525806454078471e1045f30a2d65e6da4d4681b87ee6ba73"
BOX=(6,397,956,529)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 data=Path(p).read_bytes()
 if data[:4]!=b"DDS " or len(data)!=128+2048*1024*4:raise RuntimeError("unexpected DDS byte length")
 h,w=struct.unpack_from("<II",data,12)
 m=struct.unpack_from("<IIII",data,92)
 if (w,h)!=(2048,1024) or m!=(16711680,65280,255,4278190080):raise RuntimeError("DDS format/header changed")
 if struct.unpack_from("<I",data,28)[0]!=1:raise RuntimeError("DDS mip chain changed")
 return data[:128],Image.frombytes("RGBA",(w,h),data[128:],"raw","BGRA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def save(h,im,path):
 raw=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","BGRA")
 Path(path).write_bytes(h+raw)
def flat(im,rgb):
 bg=Image.new("RGBA",im.size,(*rgb,255)); bg.alpha_composite(im);return bg.convert("RGB")
def stroke(d,pts,width=15):
 # True rounded-skeleton terminals, unlike the rejected A204 angular font.
 d.line(pts,fill=255,width=width,joint="curve")
 r=width//2
 for x,y in (pts[0],pts[-1]):
  d.ellipse((x-r,y-r,x+r,y+r),fill=255)
def contour():
 # Source-wide but natural Hangul lettering. Hand-authored near-continuous
 # syllable strokes, no font file, no glyph fallback or resampled old Korean.
 im=Image.new("L",(530,132),0);d=ImageDraw.Draw(im)
 # 쇼 = ㅅ + ㅛ, rounded rail-like terminals.
 stroke(d,[(112,17),(48,66)],17)
 stroke(d,[(112,17),(180,66)],17)
 stroke(d,[(41,103),(191,103)],16)
 stroke(d,[(89,78),(89,101)],15)
 stroke(d,[(144,78),(144,101)],15)
 # 룸 = ㄹ + ㅜ + ㅁ, explicit open counters and rail joins.
 stroke(d,[(275,17),(477,17),(477,42),(300,42),(300,60),(474,60)],16)
 stroke(d,[(272,78),(475,78)],16)
 stroke(d,[(376,78),(376,92)],15)
 stroke(d,[(290,97),(290,119),(458,119),(458,97),(290,97)],14)
 # A font-independent joint connects only *decorative lower rails* without
 # crossing open Hangul counters; preserve >=10px true glyph separation.
 return im
def y_profile(english):
 px=np.asarray(english);a=px[:,:,3]
 nums=[]
 for y in range(px.shape[0]):
  z=np.asarray(px[y,:,:3],dtype=np.float32)
  good=a[y]>160
  nums.append(float(np.percentile(z[good].mean(axis=1),55)) if good.sum()>20 else float("nan"))
 nums=np.asarray(nums,dtype=np.float32)
 have=np.flatnonzero(np.isfinite(nums))
 if len(have)<30:raise RuntimeError("English source chrome face insufficient")
 v=np.interp(np.arange(len(nums)),have,nums[have])
 return np.clip(gaussian_filter1d(v,1.5),35,250)
try:
    if not CAND.exists() or digest(CAND)!=OLD_SHA:raise RuntimeError("candidate drift; fail closed")
    hdr,old=read(CAND)
    clean=Image.open(BASE/"754F0599_HD_CLEAN_PLATE.png").convert("RGBA")
    with tempfile.TemporaryDirectory(prefix="outrun_a209_") as tmp:
     src=Path(tmp)/"source.dds";urllib.request.urlretrieve(URL,src)
     if digest(src)!=SOURCE_SHA:raise RuntimeError("canonical English source drift")
     sh,original=read(src)
     if hdr!=sh or original.size!=old.size or clean.size!=old.size:raise RuntimeError("DDS/CLEAN dimension/header drift")
     x0,y0,x1,y1=BOX
     S=np.array(original);B=np.array(old);C=np.array(clean)
     allowed=np.zeros((1024,2048),bool);allowed[y0:y1,x0:x1]=True
     # Source is canonical proof, not the prior already damaged candidate.
     outside_old=int(np.count_nonzero(np.any(S!=B,axis=2)&~allowed))
     # Other two headers are existing localized regions. Check only old->trial outside.
     plate=old.copy()
     plate.paste(clean.crop(BOX),BOX[:2])
     P=np.asarray(plate).copy()
     if np.count_nonzero(np.any(B!=P,axis=2)&~allowed):raise RuntimeError("plate changed protected other region")
     if np.any(P[y0:y1,x0:x1,3]):raise RuntimeError("source glyph residue in CLEAN")
     # Native vector strokes, published masks and isolated plate before lettering.
     mask=contour()
     if mask.getbbox() is None:raise RuntimeError("vector empty")
     gx,gy=x0+12,y0+1
     if gx+mask.width>=x1-4 or gy+mask.height>=y1+2:
      raise RuntimeError("vector exceeds source sprite")
     m=np.asarray(mask).astype(np.uint8)
     alpha=m>0
     yaxis=np.clip(np.arange(mask.height)+gy-y0,0,y1-y0-1)
     profile=y_profile(original.crop(BOX))[yaxis][:,None]
     core=distance_transform_edt(alpha)
     bright=np.clip(profile + 9*np.clip(4-core,0,4)/4,34,255)
     bevel=np.clip(bright-13*(core<2),32,250).astype("uint8")
     cols=np.broadcast_to(bevel,m.shape)
     ink=np.zeros((mask.height,mask.width,4),dtype=np.uint8)
     ink[:,:,:3]=cols[:,:,None];ink[:,:,3]=m
     layer=Image.fromarray(ink,"RGBA")
     depth=Image.new("RGBA",mask.size,(20,22,28,0))
     depth.putalpha(Image.fromarray((m.astype(np.float32)*0.69).astype("uint8"),"L"))
     final=plate.copy()
     final.alpha_composite(depth,(gx+4,gy+5))
     final.alpha_composite(layer,(gx,gy))
     F=np.asarray(final)
     union=np.zeros((1024,2048),bool)
     union[gy:gy+mask.height,gx:gx+mask.width]|=alpha
     union[gy+5:gy+5+mask.height,gx+4:gx+4+mask.width]|=alpha
     changed=np.any(F!=B,axis=2)
     effect=np.any(F!=P,axis=2)
     metrics={
      "previous_vs_trial_changed_outside_showroom":int(np.sum(changed&~allowed)),
      "previous_vs_trial_alpha_changed_outside_showroom":int(np.sum((F[:,:,3]!=B[:,:,3])&~allowed)),
      "source_vs_trial_change_in_untouched_headers":int(np.sum(np.any(F!=B,axis=2)&~allowed)),
      "source_derived_plate_alpha_in_showroom":int(np.count_nonzero(P[y0:y1,x0:x1,3])),
      "clean_vs_trial_changed_outside_glyph_and_depth":int(np.sum(effect&~union)),
      "source_vs_plate_protected_outside_region_not_a_global_test":outside_old,
     }
     if any(v for k,v in metrics.items() if k!="source_vs_plate_protected_outside_region_not_a_global_test"):
      raise RuntimeError(("A209 trial mechanical scope FAIL",metrics))
     ey,ex=np.nonzero(union)
     bbox=[int(ex.min()),int(ey.min()),int(ex.max()+1),int(ey.max()+1)]
     if bbox[0]<=x0 or bbox[1]<=y0 or bbox[2]>=x1 or bbox[3]>=y1:
      raise RuntimeError(("vector effect crosses source bbox",bbox))
     # Actual decoded persisted DDS check, but NO production candidate promotion.
     trial=DIR/"A209_Q175_SHOWROOM_NATIVE_MANUAL_VECTOR_TRIAL.dds"
     save(hdr,final,trial)
     dh,decoded=read(trial)
     if dh!=hdr or not np.array_equal(np.asarray(decoded),F):raise RuntimeError("DDS roundtrip FAIL")
     # Isolated RAW/FLIPY source-clean-final and transparent-only proof for first look.
     original.save(DIR/"A209_SOURCE_READABLE.png")
     plate.save(DIR/"A209_CLEAN_SHOWROOM_READABLE.png")
     decoded.save(DIR/"A209_TRIAL_PERSISTED_READABLE.png")
     decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(DIR/"A209_TRIAL_PERSISTED_RAW.png")
     mask.save(DIR/"A209_SHO_ROOM_CUSTOM_VECTOR_MASK.png")
     for bgname,color in (("GRAY",(105,105,105)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
      crops=[flat(im,color).crop((0,y0-5,x1+10,y1+8)) for im in (original,plate,old,decoded)]
      w,h=crops[0].size
      sheet=Image.new("RGB",(4*w+24,h+28),color)
      ImageDraw.Draw(sheet).text((8,5),"ENGLISH | CLEAN | A188 REJECT | A209 HAND VECTOR",fill=(255,220,0) if bgname!="WHITE" else (0,0,0))
      for i,c in enumerate(crops):sheet.paste(c,(i*(w+8),28))
      for pct in (100,75,50):
       img=sheet if pct==100 else sheet.resize((sheet.width*pct//100,sheet.height*pct//100),Image.Resampling.LANCZOS)
       img.save(DIR/f"A209_SHOWROOM_{bgname}_{pct}.jpg",quality=94)
     report={
      "role":"A","run":"A209","queue_index":175,"priority":"P1","regression":"IGR-032",
      "status":"MANUAL_VECTOR_METHOD_PILOT_TRIAL_ONLY_PENDING_CONTROLLER_VISUAL",
      "source_sha256":SOURCE_SHA,"prior_promoted_sha256":OLD_SHA,
      "new_trial_sha256":digest(trial),"new_promoted_dds":0,"new_trial_dds":1,
      "source_bbox":list(BOX),"trial_bbox":bbox,
      "source_size":[x1-x0,y1-y0],"trial_size":[bbox[2]-bbox[0],bbox[3]-bbox[1]],
      "recipe":"Hand-authored rounded Hangul stroke skeleton 쇼룸 (no Orbit/generic Noto); source English row chromatic chrome + bevel + in-cell shadow, custom rail joins, no raster text resize",
      "construction":"SOURCE→clean copied from pinned A188→source-derived custom vector layer→DDS encode/decode→source/protected exact scope, BGW 100/75/50, RAW",
      "machine":metrics,"source_alpha_cleared_in_full_sprite":True,
      "independent_C1":"BLOCKED_UNTIL_PRODUCER_VISUAL","C3":"BLOCKED",
      "other_titles":"PRESERVED_EXACT_PRIOR_DDS_PIXELS_NOT_REPAIRED",
      "runtime_validation":"UNTESTED","user_game":"OPEN_USER_INGAME_FAIL",
      "consumer_first_unproven_link":"trial->production promotion (not done); preview/game load untested",
     }
     (DIR/"A209_PILOT_REPORT.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
     print("A209_VECTOR_TRIAL",json.dumps({"trial_sha":report["new_trial_sha256"],"bbox":bbox,"metrics":metrics}),flush=True)

except Exception as exc:
 import traceback
 issue={"role":"A","run":"A209","queue_index":175,
        "status":"EXECUTION_DIAGNOSTIC_ONLY_NOT_CANDIDATE",
        "exception":type(exc).__name__,
        "message":str(exc),
        "traceback":traceback.format_exc(),
        "new_promoted_dds":0,"new_trial_dds":0,
        "runtime_validation":"UNTESTED","candidate_preserved":True}
 (DIR/"A209_EXECUTION_FAIL.json").write_text(json.dumps(issue,ensure_ascii=False,indent=2)+"\\n",encoding="utf8")
 print("A209_WORKER_CAPTURED_FAILURE",issue["exception"],issue["message"],flush=True)
