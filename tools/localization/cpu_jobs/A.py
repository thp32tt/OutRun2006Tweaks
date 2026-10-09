#!/usr/bin/env python3
"""A210: q175 source-shaped HAND-AUTHORED connected Hangul vector method pilot.

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
DIR=R/"localization/graphics/role_A/20261009-A210-Q175-SHOWROOM-ROUNDED-VECTOR-PILOT"
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
 # A210 topology-first Hangul outlines: separate ㅅ+ㅛ and ㄹ+ㅜ+ㅁ.
 # Counter-controlled curves supersede rejected A209 generic stroke rails.
 im=Image.new("L",(540,132),0)
 d=ImageDraw.Draw(im)
 def connected(points,width):
  d.line(points,fill=255,width=width,joint="curve")
  radius=width//2
  for x,y in (points[0],points[-1]):
   d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=255)
 # 쇼 upper ㅅ; distinct lower ㅛ with two uprights
 connected([(112,13),(104,22),(63,58)],18)
 connected([(112,13),(121,22),(166,58)],18)
 connected([(36,109),(196,109)],15)
 connected([(85,83),(85,108)],14)
 connected([(148,83),(148,108)],14)
 # 룸: connected ㄹ, separated ㅜ, counter-open ㅁ
 connected([(269,14),(458,14),(458,42),(289,42),(289,65),(458,65)],13)
 connected([(272,82),(452,82)],12)
 connected([(362,83),(362,96)],12)
 connected([(297,98),(297,121),(438,121),(438,98),(297,98)],11)
 A=np.asarray(im)>0
 # Compare specific counter/background pixels; preserve true Korean structure
 if np.any(A[106:114,319:420]):raise RuntimeError("manual ㅁ enclosed counter filled")
 if not np.any(A[117:122,319:420]):raise RuntimeError("manual ㅁ bottom missing")
 if np.any(A[73:75,310:425]):raise RuntimeError("ㄹ and ㅜ joined at wrong phoneme")
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
    with tempfile.TemporaryDirectory(prefix="outrun_a210_") as tmp:
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
     gx,gy=x0+12,y0
     if gx+mask.width>=x1-4 or gy+mask.height>=y1+2:
      raise RuntimeError("vector exceeds source sprite")
     m=np.asarray(mask).astype(np.uint8)
     alpha=m>0
     yaxis=np.clip(np.arange(mask.height)+gy-y0,0,y1-y0-1)
     profile=y_profile(original.crop(BOX))[yaxis][:,None]
     core=distance_transform_edt(alpha)
     # Local edge normals reproduce highlight/extrusion volume, not merely
     # the flat horizontal chrome rails of rejected A209.
     ny,nx=np.gradient(core.astype(np.float32))
     upper_left=np.clip(-(ny+nx)*14.0,0,21)
     lower_right=np.clip((ny+nx)*18.0,0,29)
     inner_ridge=np.minimum(core,3.0)/3.0
     yband=np.broadcast_to(profile,m.shape)
     cols=np.clip(yband+upper_left-lower_right+5*inner_ridge,25,254).astype("uint8")
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
      raise RuntimeError(("A210 trial mechanical scope FAIL",metrics))
     ey,ex=np.nonzero(union)
     bbox=[int(ex.min()),int(ey.min()),int(ex.max()+1),int(ey.max()+1)]
     if bbox[0]<=x0 or bbox[1]<=y0 or bbox[2]>=x1 or bbox[3]>=y1:
      raise RuntimeError(("vector effect crosses source bbox",bbox))
     # Actual decoded persisted DDS check, but NO production candidate promotion.
     trial=DIR/"A210_Q175_SHOWROOM_NATIVE_MANUAL_VECTOR_TRIAL.dds"
     save(hdr,final,trial)
     dh,decoded=read(trial)
     if dh!=hdr or not np.array_equal(np.asarray(decoded),F):raise RuntimeError("DDS roundtrip FAIL")
     # Isolated RAW/FLIPY source-clean-final and transparent-only proof for first look.
     original.save(DIR/"A210_SOURCE_READABLE.png")
     plate.save(DIR/"A210_CLEAN_SHOWROOM_READABLE.png")
     decoded.save(DIR/"A210_TRIAL_PERSISTED_READABLE.png")
     decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(DIR/"A210_TRIAL_PERSISTED_RAW.png")
     mask.save(DIR/"A210_SHO_ROOM_CUSTOM_VECTOR_MASK.png")
     for bgname,color in (("GRAY",(105,105,105)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
      crops=[flat(im,color).crop((0,y0-5,x1+10,y1+8)) for im in (original,plate,old,decoded)]
      w,h=crops[0].size
      sheet=Image.new("RGB",(4*w+24,h+28),color)
      ImageDraw.Draw(sheet).text((8,5),"ENGLISH | CLEAN | A188 REJECT | A210 HAND VECTOR",fill=(255,220,0) if bgname!="WHITE" else (0,0,0))
      for i,c in enumerate(crops):sheet.paste(c,(i*(w+8),28))
      for pct in (100,75,50):
       img=sheet if pct==100 else sheet.resize((sheet.width*pct//100,sheet.height*pct//100),Image.Resampling.LANCZOS)
       img.save(DIR/f"A210_SHOWROOM_{bgname}_{pct}.jpg",quality=94)
     report={
      "role":"A","run":"A210","queue_index":175,"priority":"P1","regression":"IGR-032",
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
     (DIR/"A210_PILOT_REPORT.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
     print("A210_VECTOR_TRIAL",json.dumps({"trial_sha":report["new_trial_sha256"],"bbox":bbox,"metrics":metrics}),flush=True)

except Exception as exc:
 import traceback
 issue={"role":"A","run":"A210","queue_index":175,
        "status":"EXECUTION_DIAGNOSTIC_ONLY_NOT_CANDIDATE",
        "exception":type(exc).__name__,
        "message":str(exc),
        "traceback":traceback.format_exc(),
        "new_promoted_dds":0,"new_trial_dds":0,
        "runtime_validation":"UNTESTED","candidate_preserved":True}
 (DIR/"A210_EXECUTION_FAIL.json").write_text(json.dumps(issue,ensure_ascii=False,indent=2)+chr(10),encoding="utf8")
 print("A210_WORKER_CAPTURED_FAILURE",issue["exception"],issue["message"],flush=True)
