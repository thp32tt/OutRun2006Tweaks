#!/usr/bin/env python3
"""B297 q060 Stage material+stroke profile P0 trial. Preserves q060 B296 white fix.

English Stage face is white outer/navy separation/solid gold core; its old
Korean glyph was metallic line-like thin outline. Reconstruct existing slanted
Korean sprite's material and source-referenced native rim, not rerender font.
This writes an evidence trial ONLY; no automatic promotion.
"""
import os,io,json,hashlib,tempfile,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, binary_dilation
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
P=G/"hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
OUT=G/"role_B/20261009-B297-Q060-P0-STAGE-SOURCE-FAMILY-PIXEL-MATERIAL";OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
CURRENT="d938fdd1c92e43bd9fe2f51e3f0ba87c60662c39aaea41e8905e8f850901c2f2"
SRC="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
current=P.read_bytes();assert sha(current)==CURRENT,("q060 concurrent stage state drift",sha(current))
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
with tempfile.TemporaryDirectory(prefix="b297_") as tmp:
 p=Path(tmp)/"english.dds";urllib.request.urlretrieve(url,p);en=p.read_bytes()
assert sha(en)==SRC and en[:128]==current[:128] and len(en)==len(current)==128+4096*2048*4
def dec(b):return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
english=dec(en);old=dec(current)
assert english.shape==old.shape==(2048,4096,4)
# Exact C315 English Stage cell; no crops across ranking/rank HUD.
cell=(455,245,690,350)
l,t,r,b=cell
orig=english[t:b,l:r]
prior=old[t:b,l:r]
def sample_face(tile,name):
 rgb=tile[:,:,:3].astype(np.int16)
 a=tile[:,:,3]
 if name=="yellow":valid=(a>180)&(rgb[:,:,0]>170)&(rgb[:,:,1]>120)&(rgb[:,:,2]<125)
 if name=="navy":valid=(a>180)&(rgb[:,:,0]<55)&(rgb[:,:,1]<65)&(rgb[:,:,2]>28)&(rgb[:,:,2]<120)
 if name=="white":valid=(a>180)&(rgb.min(axis=2)>200)
 vals=rgb[valid]
 assert len(vals)>350,(name,len(vals))
 return np.rint(np.median(vals,axis=0)).astype(np.uint8),int(valid.sum())
gold,gold_count=sample_face(orig,"yellow")
navy,navy_count=sample_face(orig,"navy")
white,white_count=sample_face(orig,"white")
# Preserve native Korean slant/shape, only expand its filled glyph silhouette
# by a source-constrained one-pixel radius, creating no rectangular transfers.
m=prior[:,:,3]>=24
assert int(m.sum())>3000,int(m.sum())
# Guard the sprite's original effect boundary. Even 1 pixel escapes => FAIL.
expanded=binary_dilation(m,iterations=1)
assert np.count_nonzero(expanded[0])==0 and np.count_nonzero(expanded[-1])==0
assert np.count_nonzero(expanded[:,0])==0 and np.count_nonzero(expanded[:,-1])==0
dist=distance_transform_edt(expanded)
source_total_coverage=int((orig[:,:,3]>24).sum())
new=old.copy()
# Semantic pixel material: outer white rim, inner navy surround, filled gold.
# Calibrate three coats from the exact Stage source pixels. No font redraw.
tile=np.zeros_like(prior)
inner=expanded&(dist>4.0)
contour=expanded&(dist>2.0)&(dist<=4.0)
rim=expanded&(dist<=2.0)
tile[inner,:3]=gold
tile[contour,:3]=navy
tile[rim,:3]=white
# Preserve native anti-alias alpha on the original silhouette and softly add
# only the 1px exterior coverage, never an opaque box.
tile[:,:,3]=np.maximum(prior[:,:,3],(expanded&(~m)).astype(np.uint8)*160)
# Source-specific slight front shading; keep gold full fill instead of hollow.
new[t:b,l:r]=tile
changed=np.any(new!=old,axis=2)
allowed=np.zeros((2048,4096),bool);allowed[t:b,l:r]=True
outside=int((changed&~allowed).sum())
assert outside==0
assert np.all(old[~allowed]==new[~allowed])
# The newly created effect must remain smaller than original English bbox;
# 1px overlap with adjacent ranking/rank is not acceptable.
ys,xs=np.nonzero(new[t:b,l:r,3]>18)
bb=[l+int(xs.min()),t+int(ys.min()),l+int(xs.max()+1),t+int(ys.max()+1)]
assert bb[0]>l and bb[1]>t and bb[2]<r and bb[3]<b,bb
# Native source-only transparency is the plate restoration for this sprite;
# pixel identity outside Stage means no protected art was reconstructed.
clean=english.copy();clean[t:b,l:r,:]=0
assert np.all(clean[t:b,l:r,3]==0)
assert np.array_equal(clean[~allowed],english[~allowed])
trial=current[:128]+np.flipud(new).copy().tobytes()
assert trial[:128]==current[:128] and len(trial)==len(current)
persist=dec(trial)
assert np.array_equal(persist,new)
assert sha(trial)!=CURRENT
def comp(arr,bg):
 canvas=Image.new("RGBA",(arr.shape[1],arr.shape[0]),bg)
 canvas.alpha_composite(Image.fromarray(arr,"RGBA"))
 return canvas.convert("RGB")
crop=(420,227,902,397)
L,T,R,B=crop
views=[("SOURCE",english),("CLEAN_STAGE",clean),("CURRENT_B296",old),("B297_TRIAL",persist)]
for scale in (100,75,50):
 for bgname,bg in [("GRAY",(77,77,77,255)),("BLACK",(0,0,0,255)),("WHITE",(255,255,255,255))]:
  parts=[]
  for name,arr in views:
   p=comp(arr[T:B,L:R],bg)
   if scale!=100:p=p.resize((max(1,int(p.width*scale/100)),max(1,int(p.height*scale/100))),Image.Resampling.LANCZOS)
   parts.append(p)
  sheet=Image.new("RGB",(sum(x.width for x in parts)+3*5,max(x.height for x in parts)),(77,77,77))
  xx=0
  for p in parts:sheet.paste(p,(xx,0));xx+=p.width+5
  sheet.save(OUT/f"SOURCE_CLEAN_OLD_TRIAL_{bgname}_{scale}pct.png")
parts=[comp(np.flipud(arr[T:B,L:R]),(77,77,77,255)) for _,arr in views]
sheet=Image.new("RGB",(sum(p.width for p in parts)+15,max(p.height for p in parts)),(77,77,77))
xx=0
for p in parts:sheet.paste(p,(xx,0));xx+=p.width+5
sheet.save(OUT/"SOURCE_CLEAN_OLD_TRIAL_RAW.png")
Image.fromarray((expanded.astype(np.uint8)*255),"L").save(OUT/"STAGE_EFFECT_GLYPH_MASK.png")
Image.fromarray((changed[t:b,l:r].astype(np.uint8)*255),"L").save(OUT/"STAGE_CHANGED_MASK.png")
ddspath=OUT/"A064FDFC_B297_TRIAL_NOT_PROMOTED.dds";ddspath.write_bytes(trial)
report=dict(role="B",run="B297",run_key="OUTRUN-KOR-B297-Q060-IGR044-STAGE-NATIVE-FACE-20261009",
 asset_index=60,priority="P0",regression="IGR-044_OPEN_USER_INGAME_FAIL",
 source_sha256=SRC,current_candidate_sha256=CURRENT,trial_sha256=sha(trial),
 source_box=[l,t,r,b],localized_effect_bbox=bb,
 source_face_palette={"yellow":gold.tolist(),"navy":navy.tolist(),"white":white.tolist()},
 source_face_palette_counts={"yellow":gold_count,"navy":navy_count,"white":white_count},
 prior_korean_silhouette_pixels=int(m.sum()),source_english_effect_coverage=source_total_coverage,
 changed_pixels=int(changed.sum()),outside_changed_pixels=outside,
 new_alpha_only_within_stage_bbox=True,source_clean_stage_alpha_remaining=0,
 source_clean_protected_outside_exact=True,decoded_dds_roundtrip_exact=True,
 source_header_exact=True,dd_format="RGBA32_MIP1",raw_orientation="mirror_y",native=[4096,2048],
 new_production_dds=0,trial_dds=1,
 affected="STAGE_ONLY",unchanged=["RANKING","RANK","OUTRUN_MILES_WHITE_B296","OUTRUN_MILES_GOLD"],
 producer_visual="PENDING_DIRECT_PIXELS_FIRST_SOURCE_CLEAN_AND_NATIVE",
 C="NOT_RUN",C3="NOT_RUN",APPROVAL=False,USER_IN_GAME="OPEN_USER_INGAME_FAIL",
 RUNTIME_VALIDATION="UNTESTED",execution_backend="GITHUB_ACTIONS",
 excluded_domains=["VR","FFB","DX11","DXVK"])
(OUT/"B297_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B297","sha":sha(trial),"pixels":int(changed.sum()),"bbox":bb}))
