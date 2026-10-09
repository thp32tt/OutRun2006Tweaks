#!/usr/bin/env python3
"""A212 q121 P0 provenance handoff to independent C1; NO material DDS write.

New exact-byte original/CLEAN/final native RGBA32 scope and readable/RAW
contacts address C335 HOLD on native/alpha evidence. C1 must review independently.
"""
import os, tempfile, struct, json, hashlib, urllib.request, traceback
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
ROOT=Path.cwd()
OUT=ROOT/"localization/graphics/role_A/20261010-A212-Q121-NATIVE-C335-EVIDENCE-HANDOFF"
OUT.mkdir(parents=True,exist_ok=True)
P=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
CLEAN=ROOT/"localization/graphics/role_A/20261008-A176-Q121-TRANSPARENT-PLATE/A176_Q121_CLEAN.png"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
SOURCE_SHA="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
TARGET_SHA="38d5c2c30ea813202051b191dc01de9d7804e52c1cbab0f46c5372b59ed6c844"
ATLAS_REGIONS=[
 {"key":"select_game_mode","source_bbox":[166,819,1166,973],"candidate_bbox":[291,825,1040,948]},
 {"key":"select_car","source_bbox":[243,947,1156,1111],"candidate_bbox":[287,964,1111,1072]},
 {"key":"select_course","source_bbox":[302,1062,1085,1213],"candidate_bbox":[462,1088,924,1202]},
]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_dds(path):
 d=Path(path).read_bytes()
 if d[:4]!=b"DDS " or len(d)!=128+4096*4096*4:raise RuntimeError("DDS header/bytes mismatch")
 height,width=struct.unpack_from("<II",d,12)
 pitch=struct.unpack_from("<I",d,20)[0]
 mips=struct.unpack_from("<I",d,28)[0]
 masks=struct.unpack_from("<IIII",d,92)
 if (width,height,pitch,mips,masks)!=(4096,4096,16384,1,(255,65280,16711680,4278190080)):
  raise RuntimeError(f"dds format not pinned: {width,height,pitch,mips,masks}")
 img=Image.frombytes("RGBA",(width,height),d[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 return d[:128],img
def roi_hash(array):return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()
def flat_crop(im,rgb,box):
 p=im.crop(box)
 bg=Image.new("RGBA",p.size,(*rgb,255));bg.alpha_composite(p)
 return bg.convert("RGB")
def main():
 if not P.is_file() or sha(P)!=TARGET_SHA:raise RuntimeError("q121 exact candidate drift")
 if not CLEAN.is_file():raise RuntimeError("A176 source plate missing")
 header,final=read_dds(P)
 with tempfile.TemporaryDirectory(prefix="outrun_A212_") as td:
  src=Path(td)/"source.dds"
  urllib.request.urlretrieve(SOURCE_URL,src)
  if sha(src)!=SOURCE_SHA:raise RuntimeError("canonical pinned q121 HD source sha drift")
  sh,original=read_dds(src)
  if sh!=header:raise RuntimeError("exact DDS header of canonical and final differs")
  clean=Image.open(CLEAN).convert("RGBA")
  if clean.size!=original.size:raise RuntimeError("native plate size drift")
  S=np.asarray(original);P=np.asarray(clean);F=np.asarray(final)
  affected=np.zeros((4096,4096),dtype=bool)
  for r in ATLAS_REGIONS:
   x0,y0,x1,y1=r["source_bbox"]
   affected[y0:y1,x0:x1]=True
  d0=np.any(S!=P,axis=2)
  d1=np.any(P!=F,axis=2)
  d2=np.any(S!=F,axis=2)
  base={
   "source_to_clean_changed_outside_three_original_regions":int(np.count_nonzero(d0&~affected)),
   "clean_to_final_changed_outside_three_original_regions":int(np.count_nonzero(d1&~affected)),
   "source_to_final_changed_outside_three_original_regions":int(np.count_nonzero(d2&~affected)),
   "source_to_clean_alpha_changed_outside_three_original_regions":int(np.count_nonzero((S[:,:,3]!=P[:,:,3])&~affected)),
   "clean_to_final_alpha_changed_outside_three_original_regions":int(np.count_nonzero((P[:,:,3]!=F[:,:,3])&~affected)),
  }
  # This source is a transparency-only sprite atlas: every source title
  # footprint must be clear in CLEAN; never apply this to colored plates.
  sample={}
  for r in ATLAS_REGIONS:
   x0,y0,x1,y1=r["source_bbox"]
   sr=S[y0:y1,x0:x1];pl=P[y0:y1,x0:x1];fn=F[y0:y1,x0:x1]
   x2,y2,x3,y3=r["candidate_bbox"]
   sample[r["key"]]={
    "source_pixel_sha256":roi_hash(sr),
    "plate_pixel_sha256":roi_hash(pl),
    "final_pixel_sha256":roi_hash(fn),
    "plate_alpha_nonzero_original_rect":int(np.count_nonzero(pl[:,:,3])),
    "new_region_positive_margins":[x2-x0,x1-x3,y2-y0,y1-y3],
    "source_alpha_nonzero":int(np.count_nonzero(sr[:,:,3])),
    "final_alpha_nonzero":int(np.count_nonzero(fn[:,:,3])),
    "visual_comparison_png":"A212_"+r["key"]+"_SOURCE_CLEAN_FINAL_NATIVE.png",
   }
   if min(sample[r["key"]]["new_region_positive_margins"])<1:raise RuntimeError("candidate geometry touches original")
   # Three native RGBA pixel layers, not a JPEG with opaque background.
   native=Image.new("RGBA",((x1-x0)*3+24,y1-y0),(0,0,0,0))
   for i,im in enumerate((original,clean,final)):
    native.paste(im.crop((x0,y0,x1,y1)),(i*(x1-x0+12),0))
   native.save(OUT/sample[r["key"]]["visual_comparison_png"])
   # Practical 100/75/50 on white, gray, black from exactly saved DDS
   for bgname,rgb in (("GRAY",(103,103,103)),("WHITE",(255,255,255)),("BLACK",(0,0,0))):
    crops=[flat_crop(im,rgb,(x0,y0,x1,y1)) for im in (original,clean,final)]
    w,h=crops[0].size
    panel=Image.new("RGB",(3*w+24,h+25),rgb)
    ImageDraw.Draw(panel).text((5,6),"SOURCE     CLEAN       FINAL (native DDS)",fill=(220,210,10) if bgname!="WHITE" else (0,0,0))
    for i,img in enumerate(crops):panel.paste(img,(i*(w+12),25))
    for pct in (100,75,50):
     im=panel if pct==100 else panel.resize((panel.width*pct//100,panel.height*pct//100),Image.Resampling.LANCZOS)
     im.save(OUT/f"A212_{r['key']}_{bgname}_{pct}.jpg",quality=92)
  # Pixel-identical RAW↔FLIPY certificate derived from persisted DDS, no
  # in-game claim and no unmeasured source-to-Hangul same-stroke anchors.
  car=ATLAS_REGIONS[1]["source_bbox"]
  for ident,im in (("SOURCE",original),("CLEAN",clean),("FINAL",final)):
   im.crop((150,780,1200,1250)).save(OUT/f"A212_{ident}_READABLE_NATIVE.png")
   im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop((150,4096-1250,1200,4096-780)).save(OUT/f"A212_{ident}_RAW_NATIVE.png")
  fail=[]
  for k,v in base.items():
   if v:fail.append(k+":"+str(v))
  for k,v in sample.items():
   if v["plate_alpha_nonzero_original_rect"]:fail.append("CLEAN_GHOST_"+k+":"+str(v["plate_alpha_nonzero_original_rect"]))
  report={
   "role":"A","run":"A212","queue_index":121,"priority":"P0","IGR":["IGR-030","IGR-031","IGR-040"],
   "type":"NEW_NATIVE_SOURCE_CLEAN_PERSISTED_DDS_EVIDENCE_ONLY_NO_NEW_DDS",
   "candidate_sha256":TARGET_SHA,"source_sha256":SOURCE_SHA,
   "source_url":SOURCE_URL,"source_clean":str(CLEAN.relative_to(ROOT)),
   "clean_png_sha256":sha(CLEAN),
   "current_dds_changed":False,"produced_dds":0,
   "native_4096x4096_RGBA32_mip1":True,
   "raw_flipY":"PREVIEWED_FROM_SAVED_BYTES_NO_GAME_VALIDATION",
   "outside_three_bboxes":base,"regions":sample,
   "mechanical":"PASS_SCOPED" if not fail else "FAIL_SCOPED",
   "fails":fail,"visual_status":"PENDING_CONTROLLER_NATIVE_PIXELS_FIRST_HAND",
   "independent_C1":"PENDING_FRESH_INDEPENDENT_C1_RECHECK_C335_HOLD_NOT_SUPERSEDED",
   "actual_game":"IGR030_031_040_OPEN","RUNTIME_VALIDATION":"UNTESTED",
   "no_claims":["full atlas independent C certified","matched source-Hangul slant-anchor equivalence","Dino logo and dynamic info mapping","game compositing/consumer chain"],
  }
  (OUT/"A212_EVIDENCE_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
  print("A212_NATIVE_PROOF",json.dumps({"scope":base,"regions":{k:v["plate_alpha_nonzero_original_rect"] for k,v in sample.items()},"fail":fail},ensure_ascii=False),flush=True)
try:main()
except Exception as e:
 failure={"run":"A212","queue_index":121,"status":"HOLD_INPUT_OR_SOURCE_PIXEL_PROOF_FAILED",
 "reason":type(e).__name__+":"+str(e),"traceback":traceback.format_exc(),
 "produced_dds":0,"RUNTIME_VALIDATION":"UNTESTED"}
 (OUT/"A212_EXECUTION_HOLD.json").write_text(json.dumps(failure,ensure_ascii=False,indent=2)+"\n")
 print("A212_HOLD",failure["reason"],flush=True)
