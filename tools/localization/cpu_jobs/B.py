#!/usr/bin/env python3
"""B343 q060 C342: remove duplicate English BEST TIME beneath localized 최고 기록.
Target source-matched retained glyphs only; DO NOT erase unrelated orange sprites.
Unapproved native trial, direct producer visual inspection required before promotion.
"""
import os,io,sys,struct,json,hashlib,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation,label
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics");OUT=G/"role_B/20261010-B343-Q060-BEST-TIME-RESIDUE-PILOT"
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
SRC="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
CUR="d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01"
c2=json.loads((G/"role_C/20261010-C342-C2-Q060-PERSISTED-ORANGE-OVERLAP/C342_Q060_CONTROLLER_C2_VISUAL_REWORK.json").read_text())
assert c2["queue_index"]==60 and c2["decision"]=="REWORK_REQUIRED" and c2["exact_dds"]["saved_candidate_sha256"]==CUR
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","60"],capture_output=True,text=True,check=True)
triage=json.loads(tri.stdout)["assets"][0]
assert triage["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),tri.stdout
safe=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","60","--require-safe-rerender"],capture_output=True,text=True)
assert safe.returncode in (0,2)
path=G/"hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
cur=path.read_bytes()
assert sha(cur)==CUR
srcpath=G/"hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
if srcpath.is_file():
 original=srcpath.read_bytes()
else:
 url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
 with urllib.request.urlopen(url,timeout=120) as f:original=f.read()
assert sha(original)==SRC and len(cur)==len(original)==33554560
assert cur[:128]==original[:128]
assert struct.unpack_from("<II",original,12)==(2048,4096)
masks=struct.unpack_from("<IIII",cur,92)
assert masks in ((255,65280,16711680,4278190080),(16711680,65280,255,4278190080)),masks
def dec(b):
 return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S=dec(original);O=dec(cur);N=O.copy()
assert S.shape==O.shape==(2048,4096,4)
# Source BEST TIME is below cream OUTRUN MILES in the *same* atlas; last B332R
# protected this English orange label as sibling. C342 now proves it collides
# with localized 최고 기록. Constrain to exact SOURCE warm-stroke footprint.
# Probe box is a detector bound, never a blanket rectangular eraser.
l,t,r,b=2090,337,3120,485
s=S[t:b,l:r];old=O[t:b,l:r];red=s[:,:,0].astype(np.int16);green=s[:,:,1].astype(np.int16);blue=s[:,:,2].astype(np.int16)
warm=(red>160)&(green>60)&(green<240)&(blue<140)&(red>green+35)&(s[:,:,3]>80)
# Source glyph material source-face must be plentiful and broad enough.
yy,xx=np.nonzero(warm)
assert xx.size>12000,(xx.size,"no English BEST TIME face")
bbox=(l+int(xx.min()),t+int(yy.min()),l+int(xx.max()+1),t+int(yy.max()+1))
assert bbox[0]>l and bbox[2]<r and bbox[1]>t and bbox[3]<b,("clipped source English bbox",bbox)
# Dilation includes original navy outline/effect; do not remove foreign art
# outside this glyph-footprint envelope or newly generated Korean pixels.
remove_footprint=binary_dilation(warm,iterations=11)
identity=np.all(s==old,axis=2)
removable=remove_footprint&identity&(old[:,:,3]>0)
removed=int(np.count_nonzero(removable))
assert removed>10000,("source English not retained?",removed)
before=old.copy();after=before.copy();after[removable]=0
N[t:b,l:r]=after
# New Hangul pixels (NOT identical to canonical source) strictly preserved.
korean=(~identity)&(old[:,:,3]>0)
assert np.array_equal(after[korean],before[korean])
all_changes=np.any(O!=N,axis=2)
scope=np.zeros(all_changes.shape,bool);scope[t:b,l:r]=True
assert int(np.count_nonzero(all_changes&~scope))==0
assert int(np.count_nonzero(all_changes))==removed
# Machine pixel invariants are NOT sufficient to claim all source residue gone.
order=[0,1,2,3] if masks[0]==255 else [2,1,0,3]
trial=cur[:128]+np.flipud(N)[:,:,order].copy().tobytes()
assert trial[:128]==cur[:128] and len(trial)==len(cur)
assert np.array_equal(dec(trial),N)
outdds=OUT/"B343_Q060_BEST_TIME_GLYPH_RESIDUE_UNAPPROVED.dds"
outdds.write_bytes(trial)
# Each comparison opens real canonical SOURCE / saved CURRENT / saved TRIAL;
# gray+black and readable/RAW and 100/75/50, no older resized source.
views=[]
def flat(z,color):
 bg=Image.new("RGBA",(z.shape[1],z.shape[0]),color+(255,))
 bg.alpha_composite(Image.fromarray(z,"RGBA"))
 return bg.convert("RGB")
for orient in ("FLIPY","RAW"):
 for color,bg in (("GRAY",(128,128,128)),("BLACK",(0,0,0))):
  for percent in (100,75,50):
   box=(1950,150,3150,550);x0,y0,x1,y1=box
   imgs=[flat(z[y0:y1,x0:x1].copy(),bg) for z in (S,O,N)]
   if orient=="RAW":imgs=[im.transpose(Image.Transpose.FLIP_TOP_BOTTOM) for im in imgs]
   if percent!=100:imgs=[im.resize((round(im.width*percent/100),round(im.height*percent/100)),Image.Resampling.LANCZOS) for im in imgs]
   combo=Image.new("RGB",(sum(im.width for im in imgs)+12,max(im.height for im in imgs)),bg)
   pos=0
   for im in imgs:combo.paste(im,(pos,0));pos+=im.width+6
   name=f"B343_{orient}_{color}_{percent}_SOURCE_OLD_TRIAL.png"
   combo.save(OUT/name,optimize=True);views.append(name)
Image.fromarray((remove_footprint*255).astype(np.uint8),"L").save(OUT/"B343_SOURCE_BEST_TIME_REMOVAL_ENVELOPE.png")
Image.fromarray((removable*255).astype(np.uint8),"L").save(OUT/"B343_ONLY_SOURCE_IDENTICAL_RESIDUE_PIXELS.png")
qa={"run":"B343","role":"B","index":60,"reason":"C342_C2_VERIFIED_ENGLISH_BEST_TIME_VISIBLE_BEHIND_HANGUL",
"original_source_sha256":SRC,"current_candidate_sha256":CUR,"trial_sha256":sha(trial),
"source_face_bbox":bbox,"source_face_pixels":int(xx.size),"source_matched_visible_english_removed":removed,
"source_equal_before":int(np.count_nonzero(identity&(old[:,:,3]>0))),
"native":[4096,2048],"dds":"RGBA32","mips":1,"raw_mirror_y_roundtrip":"EXACT",
"pixel_changes_outside_detection_box":0,"Korean_pixels_changed":0,
"source_detection_box":[l,t,r,b],"changed_current_candidates":0,"new_trial_dds":1,
"machine_scope_only":"NOT FULL SOURCE-FAMILY VALIDATION. A source-equal pixel is not alone semantic proof; direct visual C review of all English residues required.",
"views":views,"producer_visual":"PENDING_DIRECT_REVIEW","C2":"C342_REWORK_UNCHANGED",
"C3":"BLOCKED","IGR044":"OPEN_USER_INGAME_FAIL","RUNTIME_VALIDATION":"UNTESTED",
"backend":"GITHUB_ACTIONS_GITHUB_SOURCE_BYTES","forbidden_domains_touched":[]}
(OUT/"B343_TRIAL_MACHINE_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print("B343_TRIAL",qa["trial_sha256"],removed,bbox,flush=True)
