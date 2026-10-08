#!/usr/bin/env python3
"""B295 P0 q060 white banner genuine plate reconstruction: source DDS+
pinned native source-text mask, then retain only previously rendered Korean
glyph pixels. Trial only until direct SOURCE/CLEAN/FINAL visual acceptance.
"""
import os,sys,io,json,hashlib,tempfile,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
P=G/"hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
F=G/"role_B/20261009-B289-Q060-P0-WHITE-FACE-PIXEL-MATERIAL/A064FDFC_B289_TRIAL_NOT_PROMOTED.dds"
MASK=G/"role_B/20261004-B-RECOVERY02/A064FDFC_SOURCE_TEXT_MASK.png"
OUT=G/"role_B/20261009-B295-Q060-P0-SOURCE-CLEAN-GLYPH-PLATE";OUT.mkdir(parents=True,exist_ok=True)
E="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
O="457f29f6e3a42b674411baae993c6660addca8e6aa4c0f3904af60ec4e0a20e2"
B289="068b4f5795e85b960493efad832f9060984387c978c4936f9708133e6227fb85"
M="d7aa1ceff89e15bcfeae221b5eac0f7720d063913dec4f1a3220517c64ffb2a1"
sha=lambda x:hashlib.sha256(x).hexdigest()
prior=P.read_bytes();material=F.read_bytes();mask_b=MASK.read_bytes()
assert sha(prior)==O and sha(material)==B289 and sha(mask_b)==M
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
with tempfile.TemporaryDirectory(prefix="b291_") as tmp:
 e=Path(tmp)/"source.dds";urllib.request.urlretrieve(url,e);eb=e.read_bytes()
assert sha(eb)==E and prior[:128]==material[:128]==eb[:128]
def decode(data):return np.array(Image.open(io.BytesIO(data)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
src=decode(eb);old=decode(prior);painted=decode(material)
m=np.array(Image.open(MASK).convert("L"))>127
assert src.shape==old.shape==painted.shape==(2048,4096,4) and m.shape==(2048,4096)
assert np.array_equal(old[:,:,3],painted[:,:,3])
# Independent English source face only (native upper band) and original
# side-line/miles below preserved. Mask file is source-derived pre-2026-10-09.
yy=np.arange(2048)[:,None];xx=np.arange(4096)[None,:]
upper=(yy>=238)&(yy<335)&(xx>=1090)&(xx<1930)
# The old selection mask misses top AA/text effects. Reconstruct native
# grayscale/white source glyph and shadow directly from the English DDS.
srgb=src[:,:,:3].astype(np.int16)
saturation=srgb.max(axis=2)-srgb.min(axis=2)
semantic_native=(src[:,:,3]>7)&(saturation<65)&(srgb.max(axis=2)>30)&upper
english_ink=(m|semantic_native)&upper
assert int(english_ink.sum())>=30000
# Include subpixel halo but never leave the authoritative source title band.
english_fx=binary_dilation(english_ink,iterations=2)&upper
clean=src.copy()
clean[english_fx]=0
assert int((clean[english_fx,3]>0).sum())==0
assert np.array_equal(src[~english_fx],clean[~english_fx]),"SOURCE_NON-TEXT_MISMATCH"
# Korean mask reconstructed from B289's pixel-material-only diff, rather
# than selecting an opaque rectangle or original English contour.
changed_material=np.any(painted!=old,axis=2)
assert int(changed_material.sum())>=40000
localized_zone=(yy>=256)&(yy<374)&(xx>=1096)&(xx<1816)
glyph=binary_dilation(changed_material,iterations=5)&localized_zone&(painted[:,:,3]>12)
assert int(glyph.sum())>30000
# Only the upper 88px text row is reconstructed; below stays preserved
# current B289 to avoid touching the independently protected lower title.
result=painted.copy()
# Strip source-title effects only. Preserve all unrelated prior localization
# and source art even inside the larger source cell.
# The SOURCE CLEAN proof removes the complete English effect from y238.
# The existing candidate has an unrelated protected sprite at y238..244:
# the FINAL must not alter even a single existing pixel outside the
# source's B-approved bbox. CURRENT already has no English text there.
final_english_fx=english_fx&(yy>=245)
result[final_english_fx]=0
retain=glyph&upper
result[retain]=painted[retain]
# Lower/non-target atlas stays pixel exact; no source text/opaque plate survives
# outside the glyph in the reconstructed SOURCE_WHITE zone.
assert np.array_equal(result[~upper],painted[~upper])
plate_no_english=int(np.count_nonzero(clean[english_fx,3]));assert plate_no_english==0
# Debug leftover English ink in FINAL allowed only where Korean glyph replaces
# old English; no self-claimed under-glyph source ghost.
not_korean=final_english_fx&(~retain)
assert int(np.count_nonzero(result[not_korean,3]))==0
# Fail if actual original source English glyph remnants survive anywhere
# in the upper title band, including pixels above the catalogue bbox y245.
residual_upper_source=int(np.count_nonzero(clean[english_fx,3]))
assert residual_upper_source==0

# Changes vs preexisting candidate restricted to source-white upper band.
ch=np.any(result!=old,axis=2); allowed=(yy>=245)&(yy<385)&(xx>=1090)&(xx<1930)
assert int(ch[~allowed].sum())==0
assert not np.array_equal(result,old)
import struct
assert struct.unpack_from("<4I",prior,92)==(255,65280,16711680,4278190080)
outdds=prior[:128]+np.flipud(result).copy().tobytes()
assert len(outdds)==len(prior) and np.array_equal(decode(outdds),result)
def plate(ar,background=(74,74,74,255)):
 x=Image.new("RGBA",(ar.shape[1],ar.shape[0]),background)
 x.alpha_composite(Image.fromarray(ar,"RGBA"))
 return x.convert("RGB")
L,T,R,B=(1075,236,1950,399)
views=[("ENGLISH",src),("SOURCE_CLEAN",clean),("CURRENT",old),("B289_MATERIAL",painted),("B295_FINAL",result)]
for ratio in (100,75,50):
 cs=[]
 for key,ar in views:
  p=plate(ar[T:B,L:R])
  if ratio!=100:p=p.resize((p.width*ratio//100,p.height*ratio//100),Image.Resampling.LANCZOS)
  p.save(OUT/f"{key}_{ratio}pct_GRAY.png");cs.append(p)
 sh=Image.new("RGB",(sum(c.width for c in cs)+len(cs)*4,max(c.height for c in cs)),(74,74,74))
 cx=0
 for c in cs:sh.paste(c,(cx,0));cx+=c.width+4
 sh.save(OUT/f"B295_SOURCE_CLEAN_OLD_MATERIAL_FINAL_{ratio}pct.png")
raws=[plate(np.flipud(ar[T:B,L:R])) for _,ar in views]
sh=Image.new("RGB",(sum(c.width for c in raws)+len(raws)*4,max(c.height for c in raws)),(74,74,74))
cx=0
for c in raws:sh.paste(c,(cx,0));cx+=c.width+4
sh.save(OUT/"B295_SOURCE_CLEAN_FINAL_RAW.png")
Image.fromarray(clean[T:B,L:R],"RGBA").save(OUT/"SOURCE_CLEAN_NATIVE_RGBA.png")
Image.fromarray(english_fx[T:B,L:R].astype("uint8")*255,"L").save(OUT/"SOURCE_WHITE_REMOVAL_MASK.png")
Image.fromarray(retain[T:B,L:R].astype("uint8")*255,"L").save(OUT/"KOREAN_GLYPH_RESTORE_MASK.png")
outpath=OUT/"A064FDFC_B295_TRIAL_NOT_PROMOTED.dds";outpath.write_bytes(outdds)
qa={"schema_version":2,"role":"B","run":"B295","index":60,"priority":"P0","regression":"IGR-044",
"source_sha256":E,"old_sha256":O,"material_trial_sha256":B289,"new_trial_sha256":sha(outdds),
"source_mask_sha256":M,"plate_method":"SOURCE_NATIVE_NEUTRAL_FACE_AND_APPROVED_MASK_REMOVAL_WITH_2PX_FRINGE",
"glyph_method":"RESTORE_SOURCE_CONDITIONED_B289_KOREAN_GLYPH_PRESERVE_OTHER_CURRENT_ART",
"changed_pix":int(ch.sum()),"changed_outside_original_white_bbox":int(ch[~allowed].sum()),
"source_clean_english_effect_removed":int(english_fx.sum()),"source_clean_english_alpha_remaining":plate_no_english,
"native_source_effect_upper_band":[1090,238,1930,335],
"source_effect_above_catalog_bbox_covered":True,
"final_source_effect_mask_protected_above_bbox":True,
"native_upper_source_alpha_remaining":residual_upper_source,
"source_clean_untouched_protected_outside_mask":True,
"source_clean_final_english_ghost_outside_korean":0,
"native":[4096,2048],"codec":"RGBA32_MIP1","header_exact":True,"RAW":"mirror_y",
"persisted_decode_exact":True,"stage_gold_unchanged_from_B289":True,"new_production_dds":0,
"producer_visual":"PENDING_CONTROLLER_SOURCE_CLEAN_AND_FINAL_NATIVE_100_75_50_RAW",
"C":"NOT_RUN","C3":"NOT_RUN","USER_INGAME":"OPEN_USER_INGAME_FAIL",
"APPROVAL":False,"RUNTIME_VALIDATION":"UNTESTED",
"backend":"GITHUB_ACTIONS_NO_BINARY_SOURCE_IN_CHATGPT_LOCAL",
"exclusions":["VR","FFB","DX11","DXVK"]}
(OUT/"B295_MACHINE_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B295","sha":sha(outdds),"changed":int(ch.sum()),"retained":int(retain.sum())}))
