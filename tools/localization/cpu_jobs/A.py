#!/usr/bin/env python3
"""A213: map A212 q121 canonical-source vs clean/current unexpected pixels.

Read-only P0 original-art attribution probe, not a production DDS edit.
"""
import os,json,hashlib,struct,tempfile,urllib.request,traceback
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
R=Path.cwd(); OUT=R/"localization/graphics/role_A/20261010-A213-Q121-SOURCE-PROTECTION-ROOT-CAUSE"
OUT.mkdir(parents=True,exist_ok=True)
SRC="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
C=R/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
P=R/"localization/graphics/role_A/20261008-A176-Q121-TRANSPARENT-PLATE/A176_Q121_CLEAN.png"
SH="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
CH="38d5c2c30ea813202051b191dc01de9d7804e52c1cbab0f46c5372b59ed6c844"
BOXES=[(166,819,1166,973),(243,947,1156,1111),(302,1062,1085,1213)]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 v=Path(p).read_bytes()
 if v[:4]!=b"DDS " or len(v)!=128+4096*4096*4:raise ValueError("wrong DDS")
 if struct.unpack_from("<II",v,12)!=(4096,4096):raise ValueError("wrong size")
 return Image.frombytes("RGBA",(4096,4096),v[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def run():
 if digest(C)!=CH:raise RuntimeError("q121 CURRENT SHA changed")
 with tempfile.TemporaryDirectory(prefix="outrun_a213_") as td:
  src=Path(td)/"original.dds"
  urllib.request.urlretrieve(SRC,src)
  if digest(src)!=SH:raise RuntimeError("q121 SOURCE hash drift")
  original=load(src)
  plate=Image.open(P).convert("RGBA")
  final=load(C)
  S=np.asarray(original);Q=np.asarray(plate);F=np.asarray(final)
  affected=np.zeros((4096,4096),np.bool_)
  for x0,y0,x1,y1 in BOXES:affected[y0:y1,x0:x1]=True
  mismatched=np.any(S!=F,axis=2)&~affected
  alpha_missing=(S[:,:,3]>0)&(F[:,:,3]==0)&~affected
  alpha_added=(S[:,:,3]==0)&(F[:,:,3]>0)&~affected
  plate_missing=(S[:,:,3]>0)&(Q[:,:,3]==0)&~affected
  # 8-connected components of changed pixels, rank major regions by size.
  comps,n=ndimage.label(mismatched,structure=np.ones((3,3),dtype=np.uint8))
  sizes=np.bincount(comps.ravel());sizes[0]=0
  order=np.argsort(sizes)[-30:][::-1]
  regions=[]
  for ix in order:
   if sizes[ix]<20:continue
   ys,xs=np.where(comps==ix)
   bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
   reg=(slice(bbox[1],bbox[3]),slice(bbox[0],bbox[2]))
   count=int(sizes[ix])
   lost=int(np.count_nonzero(alpha_missing[reg]&(comps[reg]==ix)))
   new=int(np.count_nonzero(alpha_added[reg]&(comps[reg]==ix)))
   regions.append({"rank":len(regions)+1,"changed_pixels":count,"bbox_readable":bbox,"alpha_disappeared":lost,"alpha_appeared":new})
  # Full atlas NEAREST-neighbor view to retain glyph layout, no C/game claims.
  imgs=[original,plate,final]
  small=[im.resize((1024,1024),Image.Resampling.LANCZOS) for im in imgs]
  for bgname,background in (("GRAY",(100,100,100)),("BLACK",(0,0,0))):
   out=Image.new("RGB",(3*1024+24,1060),background)
   d=ImageDraw.Draw(out)
   for i,img in enumerate(small):
    pix=Image.new("RGBA",img.size,(*background,255));pix.alpha_composite(img)
    out.paste(pix.convert("RGB"),(i*(1024+12),28))
   d.text((5,5),"CANONICAL ENGLISH SOURCE     A176 CLEAN PLATE     CURRENT A202 KOREAN DDS",fill=(240,240,0))
   out.save(OUT/f"A213_ATLAS_SOURCE_CLEAN_FINAL_{bgname}_25PCT.jpg",quality=91)
  def heat(mask,label):
   thumb=Image.fromarray((mask.astype(np.uint8)*255),"L")
   thumb.resize((1024,1024),Image.Resampling.NEAREST).save(OUT/f"A213_{label}_DIFFMASK_25PCT.png")
  heat(mismatched,"OUTSIDE_THREE_SOURCE_TEXT_BBOXES")
  heat(alpha_missing,"CANONICAL_ALPHA_LOST")
  heat(plate_missing,"SOURCE_TO_CLEAN_ALPHA_LOST")
  report={
   "role":"A","run":"A213","queue_index":121,"priority":"P0",
   "source_sha256":SH,"current_candidate_sha256":CH,
   "source_plate_sha256":digest(P),"atlas_pixels":4096*4096,
   "outside_three_source_title_bbox_RGBA_changed":int(np.count_nonzero(mismatched)),
   "outside_three_source_title_bbox_source_alpha_lost_to_final":int(np.count_nonzero(alpha_missing)),
   "outside_three_source_title_bbox_source_alpha_added_in_final":int(np.count_nonzero(alpha_added)),
   "outside_three_source_title_bbox_source_alpha_lost_to_clean":int(np.count_nonzero(plate_missing)),
   "changed_components_count":int(n),
   "ranked_components":regions,
   "diagnosis":"CANONICAL_PIXEL_CHANGED_OUTSIDE_KNOWN_THREE_TITLE_BOXES; UNKNOWN_IF_OTHER_LOCALIZED_TEXT_OR_PROTECTED_ART_UNTIL_DIRECT_VISUAL",
   "candidate_written":False,"new_DDS":0,
   "qa":"HOLD_SOURCE_ART_PROVENANCE_VISUAL_MAPPING_REQUIRED",
   "C1":"HOLD_STRICT_RECHECK_NO_INDEPENDENT_PASS",
   "actual_game":"IGR030_IGR031_IGR040_OPEN",
   "RUNTIME_VALIDATION":"UNTESTED",
   "next":"Map pixels in ranked component boxes to text vs protected icon/vehicle/logo from native source; if truly protected, restore losslessly before lettering; do not blanket copy English text back over localized cells.",
  }
  (OUT/"A213_P0_ROOT_CAUSE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
  print("A213_SOURCE_PIXEL_AUDIT",json.dumps({k:report[k] for k in ["outside_three_source_title_bbox_RGBA_changed","outside_three_source_title_bbox_source_alpha_lost_to_final","changed_components_count"]}))
try:run()
except Exception as e:
 report={"run":"A213","status":"FAIL_CLOSED_EVIDENCE_NOT_VERIFIED","error":repr(e),"traceback":traceback.format_exc(),"new_DDS":0,"RUNTIME_VALIDATION":"UNTESTED"}
 (OUT/"A213_EXECUTION_HOLD.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
 print("A213_HOLD",repr(e))
