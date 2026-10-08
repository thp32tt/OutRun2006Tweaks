#!/usr/bin/env python3
"""B289 q060 IGR-044: recolor existing italic Korean pixels with SOURCE white face.
This is a native material transfer, NOT another Noto/width/shear rerender.
Writes a fail-closed trial, pixel masks, separate unmodified source/current,
actual persisted-byte comparison and compositing previews. No automatic promotion.
"""
import hashlib, io, json, os, sys, tempfile, urllib.request, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt, binary_dilation
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
CAND=G/"hd_candidates"/REL
OUT=G/"role_B/20261009-B289-Q060-P0-WHITE-FACE-PIXEL-MATERIAL"
OUT.mkdir(parents=True,exist_ok=True)
SOURCE_SHA="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
PRIOR_SHA="457f29f6e3a42b674411baae993c6660addca8e6aa4c0f3904af60ec4e0a20e2"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
sha=lambda b:hashlib.sha256(b).hexdigest()
tri=json.loads(subprocess.check_output([sys.executable,"tools/localization/rework_triage.py","--index","60","--require-safe-rerender"],text=True))["assets"][0]
assert tri["next_action"]=="MATERIAL_REWORK",tri
prior=CAND.read_bytes();assert sha(prior)==PRIOR_SHA,("CONCURRENT_CHANGED_Q060",sha(prior))
with tempfile.TemporaryDirectory(prefix="b289_") as tmp:
 p=Path(tmp)/"source.dds"
 urllib.request.urlretrieve(source_url,p);raw_src=p.read_bytes()
assert sha(raw_src)==SOURCE_SHA
assert raw_src[:128]==prior[:128] and len(prior)==128+4096*2048*4
def dec(b):return np.asarray(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)).copy()
english=dec(raw_src);current=dec(prior)
assert english.shape==current.shape==(2048,4096,4)
# Independently measured C315/A167 authoritative source and candidate effect masks.
source_box=(1090,245,1930,385)
glyph_box=(1096,256,1816,374)
l,t,r,b=glyph_box
a=current[t:b,l:r].copy()
rgb=a[:,:,:3].astype(np.int16)
alpha=a[:,:,3]
maxi=rgb.max(axis=2); mini=rgb.min(axis=2)
# Existing silver core is preserved geometrically. Only neutral metallic
# ink belonging to the known glyph silhouette is recolored to solid white.
white_face=(mini>=154)&((maxi-mini)<=49)&(alpha>=30)
assert int(white_face.sum())>=2600,("insufficient_pinned_Korean_face",int(white_face.sum()))
# Use only existing opaque pixels, near original white/gray face; never fill
# transparent holes or introduce a rectangle, shadow or new foreign object.
distance=distance_transform_edt(~white_face)
neutral=(maxi-mini)<=45
core=white_face
soft=(alpha>=22)&neutral&(distance<=4.5)
# Fail closed if too many pixels to be touched: protects colored line art.
assert int(soft.sum())<int(white_face.sum())*3.3
src=english[source_box[1]:source_box[3],source_box[0]:source_box[2]]
srgb=src[:,:,:3];sa=src[:,:,3]
source_white=((srgb.min(axis=2)>=195)&(sa>=64))
assert int(source_white.sum())>3000
# Original English near-solid white/gray, not chrome outline. Render three
# brightness bands INSIDE the old Korean alpha and preserve old alpha exactly.
new=current.copy()
tile=new[t:b,l:r]
tile[core,0]=252;tile[core,1]=252;tile[core,2]=250
rim=soft&~core
# Smooth bright edge: 229-243 rather than navy hollow metallic edge.
v=np.clip(np.rint(244-(distance-0.5)*4.0),224,244).astype(np.uint8)
for ch in range(3):tile[:,:,ch][rim]=v[rim]
assert np.array_equal(new[:,:,3],current[:,:,3]),"alpha changed"
change=np.any(new!=current,axis=2)
allowed=np.zeros(change.shape,bool);allowed[t:b,l:r]=True
assert int(change[~allowed].sum())==0
# All non-neutral blue/navy art stays pixel-identical.
outside_neutral=(~soft)&(~core)
assert np.array_equal(a[outside_neutral],new[t:b,l:r][outside_neutral])
assert np.array_equal(current[:t],new[:t]) and np.array_equal(current[b:],new[b:])
# DDS is exactly RGBA32 on disk (unlike BGRA assets), RAW Y mirror.
import struct
assert struct.unpack_from("<4I",prior,92)==(255,65280,16711680,4278190080)
trial=prior[:128]+np.flipud(new).copy().tobytes()
assert len(trial)==len(prior) and trial[:128]==prior[:128] and sha(trial)!=PRIOR_SHA
persist=dec(trial)
assert np.array_equal(new,persist)
def lay(ar,bg):
 im=Image.new("RGBA",(ar.shape[1],ar.shape[0]),bg)
 im.alpha_composite(Image.fromarray(ar,"RGBA"))
 return im.convert("RGB")
L,T,R,B=(1075,236,1950,399)
panels=[("SOURCE_ENGLISH",english),("CURRENT_KOREAN",current),("B289_NATIVE_MATERIAL",persist)]
for label,ar in panels:
 crop=ar[T:B,L:R]
 Image.fromarray(crop,"RGBA").save(OUT/f"{label}_NATIVE_RGBA.png")
 for bgname,bg in [("GRAY",(77,77,77,255)),("BLACK",(0,0,0,255)),("WHITE",(255,255,255,255))]:
  for ratio in [100,75,50]:
   p=lay(crop,bg)
   if ratio!=100:p=p.resize((p.width*ratio//100,p.height*ratio//100),Image.Resampling.LANCZOS)
   p.save(OUT/f"{label}_{bgname}_{ratio}.png")
 rawcrop=np.flipud(ar[T:B,L:R])
 lay(rawcrop,(77,77,77,255)).save(OUT/f"{label}_RAW_MIRROR_Y.png")
for ratio in [100,75,50]:
 cells=[]
 for label,ar in panels:
  pp=lay(ar[T:B,L:R],(77,77,77,255))
  if ratio!=100:pp=pp.resize((pp.width*ratio//100,pp.height*ratio//100),Image.Resampling.LANCZOS)
  cells.append(pp)
 w=sum(c.width for c in cells)+12
 sheet=Image.new("RGB",(w,max(c.height for c in cells)),(77,77,77))
 x=0
 for c in cells:sheet.paste(c,(x,0));x+=c.width+6
 sheet.save(OUT/f"B289_SOURCE_CURRENT_TRIAL_{ratio}.png")
# Explicit alpha-only mask, changed-only compositing, no invented clean plate.
Image.fromarray((soft.astype(np.uint8)*255),"L").save(OUT/"KOREAN_EXISTING_GLYPH_NEUTRAL_MASK.png")
Image.fromarray((change[t:b,l:r].astype(np.uint8)*255),"L").save(OUT/"COMPOSITE_ONLY_CHANGED_PIXEL_MASK.png")
trialpath=OUT/"A064FDFC_B289_TRIAL_NOT_PROMOTED.dds"
trialpath.write_bytes(trial)
qa={
 "schema_version":2,"role":"B","run":"B289","queue_index":60,"priority":"P0","regression":"IGR-044",
 "canonical_source_sha256":SOURCE_SHA,"current_candidate_sha256":PRIOR_SHA,
 "trial_sha256":sha(trial),"source_url":source_url,
 "trial_path":str(trialpath),"method":"SOURCE_FAMILY_EXISTING_KOREAN_GLYPH_MATERIAL_RECOLOR_NO_NEW_FONT_NO_RERENDER",
 "source_bbox":list(source_box),"preexisting_korean_bbox":list(glyph_box),
 "source_white_core_pixels":int(source_white.sum()),
 "localized_neutral_white_core_pixels":int(white_face.sum()),
 "new_material_pixels":int(change.sum()),"eligible_localized_ink_pixels":int(soft.sum()),
 "pixels_outside_localized_glyph_bbox_changed":0,"whole_atlas_alpha_changes":0,
 "protected_non_neutral_pixels_changed":0,"header_byte_equal":True,
 "raw_native_roundtrip":"PASS","dimensions":[4096,2048],"codec":"RGBA32_MIP1",
 "product_status":"TRIAL_NOT_PROMOTED","producer_visual":"REQUIRES_DIRECT_CONTROLLER_100_75_50_RAW_AND_CLEAN_GATE",
 "PLATE_ONLY":"HOLD_CANONICAL_CLEAN_REVIEW_REQUIRED","COMPOSITE_ONLY":"MASK_AND_SOURCE_CURRENT_TRIAL_SAVED",
 "C":"NOT_RUN","C3":"NOT_RUN","APPROVAL":False,"RUNTIME_VALIDATION":"UNTESTED",
 "other_two_visual_fail_regions":["stage","outrun_miles_gold"],"new_production_dds":0,
 "execution_backend":"GITHUB_ACTIONS_BINARY_SOURCE_FALLBACK_NOT_LOCAL_SANDBOX",
 "exclusions":["VR","FFB","DX11","DXVK"]
}
(OUT/"B289_MACHINE_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B289","trial":sha(trial),"changed":int(change.sum()),"core":int(white_face.sum())},ensure_ascii=False))
