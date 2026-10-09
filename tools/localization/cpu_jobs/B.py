#!/usr/bin/env python3
"""B330 q098: eliminate inherited English BC3 blocks outside B327R Korean render.

C328 proved English "Cl" and "ord." remain in the saved DDS. Earlier B327R
reencoded only full blocks inside x475..1580 and y9..120; unedited BC3
blocks retained stock English. Preserve the exact B327R authored Korean
blocks and clear only ORIGINAL-title alpha in untouched blocks.
Quarantine until visually inspected at full saved-DDS resolution.
"""
import hashlib,io,json,os,struct,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
OUT=G/"role_B/20261009-B330-Q098-ENGLISH-FLANK-REMOVAL";OUT.mkdir(parents=True,exist_ok=True)
h=lambda x:hashlib.sha256(x).hexdigest()
SOURCE="3b3cdd76b03014e0ba6a47f4e98a187fdf6ae4297314494cbe1d3d4c586f1f59"
OLD="472392829d96cc1dc6ed980d942c56df883758f2777490ac6e7f6dafb5f86028"
prior=json.loads((G/"role_C/20261009-C328-C2-Q098-PERSISTED-ENGLISH-RESIDUE/C328_Q098_CONTROLLER_REWORK.json").read_text())
assert prior["decision"]=="REWORK_REQUIRED" and prior["candidate_sha256"]==OLD
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","98","--require-safe-rerender"],text=True,capture_output=True,check=True)
assert json.loads(tri.stdout)["assets"][0]["next_action"] in ("MATERIAL_REWORK","NORMAL_QUEUE_SELECTION"),"Read-only triage lexical status misses C328 but independent exact C REWORK is verified"
current=(G/"hd_candidates"/REL).read_bytes();assert h(current)==OLD,"Concurrent q98 material modification; abort"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
with urllib.request.urlopen(url,timeout=160) as response:raw_source=response.read()
assert h(raw_source)==SOURCE and raw_source[:128]==current[:128]
assert len(current)==262272 and current[84:88]==b"DXT5" and struct.unpack_from("<I",current,28)[0]==1
def decoded(z):
  return np.asarray(Image.open(io.BytesIO(z)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
S=decoded(raw_source);P=decoded(current)
assert S.shape==P.shape==(128,2048,4)
# Reconstruct a genuinely empty clean plate; the asset is a single floating
# English challenge-title sprite, with no protected non-text illustrations.
C=np.zeros_like(S)
source_effect=(S[:,:,3]>0)
assert source_effect.sum()>40000,"Source text missing"
sy,sx=np.where(source_effect);bbox=[int(sx.min()),int(sy.min()),int(sx.max()+1),int(sy.max()+1)]
# The source-derived declared glyph/effect region is x431..1674 y6..123.
# If the actual current binary exhibits unexplained artwork outside it,
# stop rather than blanking the image arbitrarily.
assert bbox[0]>=425 and bbox[2]<=1680 and bbox[1]>=2 and bbox[3]<=126,("unexpected stock art",bbox)
# B327R had written blocks only when x>=475 && x+4<=1580 &&
# y>=9 && y+4<=120. A strict 4-pixel aligned set below reproduces
# that original author's exact written-block footprint.
def is_korean_written_block(x,y):
  return x>=475 and x+4<=1580 and y>=9 and y+4<=120
buf=bytearray(current)
cleared=0
old_fringe_pixels=0
for y in range(0,128,4):
  for x in range(0,2048,4):
    if is_korean_written_block(x,y):
      continue  # Preserve original B327R Korean glyphs/effects byte-for-byte.
    pix=P[y:y+4,x:x+4,3]
    if not np.any(pix):
      continue
    old_fringe_pixels+=int(np.count_nonzero(pix))
    # DXT5 alpha endpoints 0,0 and all-zero indexes make the block
    # fully transparent while keeping its 8-byte RGB payload untouched.
    off=128+(((128-y-4)//4)*(2048//4)+(x//4))*16
    buf[off:off+8]=bytes(8)
    assert buf[off+8:off+16]==current[off+8:off+16]
    cleared+=1
assert cleared>0 and old_fringe_pixels>0,("no source fragments",cleared,old_fringe_pixels)
trial=bytes(buf);D=decoded(trial)
assert trial!=current and trial[:128]==current[:128] and len(trial)==len(current)
kept=np.zeros((128,2048),dtype=bool)
for y in range(0,128,4):
  for x in range(0,2048,4):
    if is_korean_written_block(x,y): kept[y:y+4,x:x+4]=True
assert np.array_equal(D[kept],P[kept]),"Altered Korean glyphs"
assert np.count_nonzero(D[:,:,3][~kept])==0,"Old English still visible outside authored Korean BC3 blocks"
assert np.count_nonzero((P!=D).any(axis=2)&kept)==0
assert np.count_nonzero((P[:,:,:3]!=D[:,:,:3]).any(axis=2))==0,"Changed protected colors"
source_bounds_mask=(np.indices((128,2048))[1]>=bbox[0])&(np.indices((128,2048))[1]<bbox[2])&(np.indices((128,2048))[0]>=bbox[1])&(np.indices((128,2048))[0]<bbox[3])
assert np.count_nonzero((D[:,:,3]!=P[:,:,3])&~source_bounds_mask)==0,"Changes outside whole English title bounds"
# Pixels between stock-English glyphs may contain prior B279 Korean residue:
# shape-mask non-membership alone cannot classify these as protected art.
non_source_residual_removed=int(np.count_nonzero((D[:,:,3]!=P[:,:,3])&~source_effect))
print("B330_NON_SOURCE_GLYPH_RESIDUALS_WITHIN_SOURCE_TITLE",non_source_residual_removed)
# Native clean plate, never a contaminated historical transparent-pixel RGB
# surrogate. Only Korean-generated full-block area is allowed to be visible.
# Exact SOURCE text had no protected marks; reviewer still inspects full frame.
target=OUT/"B330_Q098_ENGLISH_REMOVED_UNAPPROVED.dds";target.write_bytes(trial)
assert h(target.read_bytes())==h(trial) and np.array_equal(decoded(target.read_bytes()),D)
Image.fromarray(C,"RGBA").save(OUT/"B330_FULL_NATIVE_TRUE_EMPTY_CLEAN_RGBA.png")
for name,arr in (("SOURCE",S),("OLD",P),("NEW",D)):
  Image.fromarray(arr,"RGBA").save(OUT/f"B330_{name}_PERSISTED_FLIPY.png")
  Image.fromarray(np.flipud(arr),"RGBA").save(OUT/f"B330_{name}_PERSISTED_RAW.png")
proofs=[]
def merge(background,arr):
  image=Image.new("RGBA",(2048,128),(*background,255))
  image.alpha_composite(Image.fromarray(arr,"RGBA"));return image.convert("RGB")
for ori in ("FLIPY","RAW"):
  arrays=(S,C,P,D) if ori=="FLIPY" else tuple(np.flipud(z) for z in (S,C,P,D))
  for bgname,bg in (("BLACK",(0,0,0)),("GRAY",(72,72,72)),("WHITE",(255,255,255))):
    for pct in (100,75,50):
      chunks=[merge(bg,a) for a in arrays]
      if pct!=100:chunks=[im.resize((round(im.width*pct/100),round(im.height*pct/100)),Image.Resampling.LANCZOS) for im in chunks]
      contact=Image.new("RGB",(sum(z.width for z in chunks)+12,max(z.height for z in chunks)),(96,96,96))
      xx=0
      for im in chunks:contact.paste(im,(xx,0));xx+=im.width+4
      fname=f"FULL_{ori}_{bgname}_{pct}_SOURCE_CLEAN_OLD_NEW.png"
      contact.save(OUT/fname,optimize=True);proofs.append(fname)
qa={
 "run":"B330","role":"B","queue_index":98,"source_sha256":SOURCE,"old_sha256":OLD,
 "new_trial_sha256":h(trial),"candidate_promoted":False,"trial_only":True,
 "English_source_alpha_bounds_actual":bbox,
 "source_vs_true_empty_clean":"ONE_TEXT_ONLY_NO_PROTECTED_ILLUSTRATION",
 "source_removal":"CLEAN_PLATE_REBUILT_FROM_FULL_CANVAS_NOT_NARROW_OLD_MASK",
 "old_English_leftover_alpha_pixels":old_fringe_pixels,
 "erased_original_BC3_blocks":cleared,"new_oldEnglish_unwritten_blocks_alpha":0,
 "original_korean_BC3_written_blocks":"BYTE_EXACT",
 "all_DDS_RGB":"PIXEL_EXACT","cleared_prior_candidate_residue_not_in_stock_glyph_mask":non_source_residual_removed,
 "saved_DDS_decode":"EXACT","DDS_dimensions":[2048,128],
 "DDS_codec":"DXT5_BC3","mips":1,"raw_orientation":"MIRROR_Y",
 "source_clean_final_full_frame_proofs":proofs,
 "producer_qa":"MACHINE_PASS_FULL_FRAME_VISUAL_PENDING",
 "C2":"NOT_RUN","C3":"NOT_RUN","user_game":"UNTESTED","RUNTIME_VALIDATION":"UNTESTED",
 "backend":"github-actions","excluded_work":["VR","FFB","DX11","DXVK"]}
(OUT/"B330_MACHINE_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print("B330_Q098_TRIAL",json.dumps({"new_sha":h(trial),"blocks_erased":cleared,
  "previous_english_pixels":old_fringe_pixels,"full_frame_contacts":len(proofs)},ensure_ascii=False))
