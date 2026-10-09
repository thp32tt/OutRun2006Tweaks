#!/usr/bin/env python3
"""B337: native source-conditioned chrome glyph PILOT for q228 CAR SELECT.

NEW METHOD: draw Korean outlines at final source native pixel grid, then
construct silver diffuse, edge normals, dark border, extrusion, separately.
The earlier B323 used the rejected B322 silhouette and smoothed local colour:
this pilot does NOT use that silhouette or recolour earlier candidates.
One pilot only; do not publish as hd_candidates without producer/C visual QA.
"""
import csv,hashlib,io,json,os,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw
from scipy.ndimage import binary_dilation,gaussian_filter,distance_transform_edt
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds"
OUT=G/"role_B/20261010-B337-Q228-CAR-SELECT-NATIVE-CHROME-PILOT"
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
SRC="3f98c940c51d2f054934d4e0b7c7d9745f9f8ad71d68548b0b336c62c1cf5154"
CUR="cab1ce0802739fdbe9f40df412bd3d469fe16630dad25a28873ccb81016df473"
TEXT="차량 선택"
RUN="OUTRUN-KOR-B337-Q228-CAR-SELECT-SOURCE-NORMAL-CHROME-20261010"
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(x for x in csv.DictReader(f) if x["index"].lstrip("\ufeff")=="228")
assert row["artwork_status"].startswith("c327_c2_b323_visual_rework_chrome12_"),row["artwork_status"]
with (G/"INGAME_REWORK_BACKLOG.csv").open(encoding="utf-8-sig",newline="") as f:
 assert any(r["id"].lstrip("\ufeff")=="IGR-038" and r["status"]=="OPEN_USER_INGAME_FAIL" for r in csv.DictReader(f))
tri=subprocess.run([sys.executable,"-B","tools/localization/rework_triage.py","--index","228","--require-safe-rerender"],capture_output=True,text=True)
assert tri.returncode==0,(tri.stdout,tri.stderr)
classification=json.loads(tri.stdout)["assets"][0]["next_action"]
if classification=="NORMAL_QUEUE_SELECTION":
 # The q228 queue status encodes C327's actual visual rework in a shorthand
 # lacking the triage substring. Bind the exact independent C review+SHA.
 c=json.loads((G/"role_C/20261009-C327-C2-Q212-Q228-VISUAL/C327_Q228_B323_THIRTEEN_REGION_REWORK.json").read_text())
 assert c["decision"]=="REWORK_REQUIRED" and c["queue_index"]==228
 assert c["current_candidate_sha256"]=="cab1ce0802739fdbe9f40df412bd3d469fe16630dad25a28873ccb81016df473"
else:
 assert classification=="MATERIAL_REWORK",classification
old=(G/"hd_candidates"/REL).read_bytes()
assert sha(old)==CUR,"q228 concurrently modified: stop rather than overwriting"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds"
with urllib.request.urlopen(url,timeout=120) as f: srcbytes=f.read()
assert sha(srcbytes)==SRC and len(srcbytes)==len(old)==128+2048*2048*4
def dec(buf):
 arr=np.asarray(Image.open(io.BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
 assert arr.shape==(2048,2048,4)
 return arr
S=dec(srcbytes);P=dec(old)
history=json.loads((G/"role_B/20261005-B-PRODUCTION68/B68_E7F6_REPORT.json").read_text())
assert history["source_sha256"]==SRC and len(history["rows"])==13
region=next(z for z in history["rows"] if z["source"]=="car select")
l,t,r,b=region["original_bbox"]
assert [l,t,r,b]==[5,182,1124,301]
w,h=r-l,b-t
C=np.asarray(Image.open(G/"role_B/20261005-B-PRODUCTION68/E7F6_CLEAN_PLATE.png").convert("RGBA"),dtype=np.uint8)
assert C.shape==S.shape
allowed_source=np.zeros(S.shape[:2],bool)
for region0 in history["rows"]:
 x0,y0,x1,y1=region0["original_bbox"]
 allowed_source[y0:y1,x0:x1]=True
assert not np.any(np.any(S!=C,axis=2)&~allowed_source)
assert not np.any(C[t:b,l:r,3]),"Source-derived clean not transparent"
fontpath=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
fontdata=fontpath.read_bytes()
assert sha(fontdata)=="faa5f3656a78b2e2d450d27fe8382c778bc2b6bb5ea29c986664a6a435056ceb"
from fontTools.ttLib import TTCollection
col=TTCollection(str(fontpath),lazy=True)
chars=sorted(set(TEXT))
cmap=set().union(*(set(x.cmap.keys()) for tbl in col.fonts[1]["cmap"].tables if tbl.isUnicode() for x in [tbl]))
assert all(ord(ch) in cmap for ch in chars),chars
for face in col.fonts:face.close()
# Source-size-constrained native glyph. Do not upscale an older Korean raster.
lay=None
for ppem in range(118,65,-1):
 fnt=ImageFont.truetype(str(fontpath),ppem,index=1)
 meas=ImageDraw.Draw(Image.new("L",(w,h))).textbbox((0,0),TEXT,font=fnt,stroke_width=1)
 gw,gh=meas[2]-meas[0],meas[3]-meas[1]
 if gw<=w-20 and gh<=h-17:
  lay=(fnt,ppem,meas,gw,gh);break
assert lay,"Failed source-bbox size gate"
fnt,ppem,bbox,gw,gh=lay
layer=Image.new("L",(w,h))
d=ImageDraw.Draw(layer)
x=8-bbox[0]
y=(h-gh)//2-bbox[1]
d.text((x,y),TEXT,font=fnt,fill=255,stroke_width=1,stroke_fill=255)
A=np.asarray(layer,dtype=np.uint8)
# Source-family right-italic displacement in READABLE coordinates, never raw.
shear=0.11
B=np.zeros_like(A)
for yi in range(h):
 sh=int(round(shear*(h//2-yi)))
 if sh>=0:
  B[yi,sh:]=A[yi,:w-sh]
 else:
  B[yi,:w+sh]=A[yi,-sh:]
A=B
face=A>=110
# Rounded contour at native ppem while preserving negative-space counters.
soft=gaussian_filter(face.astype(np.float32),sigma=0.7)
face=soft>0.48
dist=distance_transform_edt(face)
ys,xs=np.where(face)
assert len(xs)>10000,"font unexpectedly tiny"
glyph_box=[int(xs.min()+l),int(ys.min()+t),int(xs.max()+l+1),int(ys.max()+t+1)]
assert glyph_box[0]>=l+3 and glyph_box[1]>=t+3 and glyph_box[2]<=r-3 and glyph_box[3]<=b-3,glyph_box
# Real source per-scanline reflected silver: anchored in native English pixels.
stock=S[t:b,l:r].astype(np.float32)
alpha=stock[:,:,3]
rgb=stock[:,:,:3]
brightness=rgb.mean(axis=2)
source_metal=(alpha>140)&(brightness>96)&(abs(rgb[:,:,0]-rgb[:,:,1])<36)
assert int(source_metal.sum())>7000
profile=[]
for yi in range(h):
 pts=rgb[yi][source_metal[yi]]
 if len(pts)<8: profile.append([np.nan]*3)
 else: profile.append(np.percentile(pts,65,axis=0))
profile=np.asarray(profile,np.float32)
good=np.isfinite(profile[:,0])
assert int(good.sum())>30
for ch in range(3):
 profile[:,ch]=np.interp(np.arange(h),np.flatnonzero(good),profile[good,ch])
profile=gaussian_filter(profile,sigma=(3,0),mode="nearest")
# Create *distinct* metallic face, bevel/side and rim from fresh glyph
# normals. The old hollow Korean bitmap contributes NO glyph pixels.
left=np.zeros_like(face);left[:,1:]=face[:,:-1]
right=np.zeros_like(face);right[:,:-1]=face[:,1:]
upper=np.zeros_like(face);upper[1:]=face[:-1]
lower=np.zeros_like(face);lower[:-1]=face[1:]
topedge=face&~upper
bottomedge=face&~lower
topzone=binary_dilation(topedge,iterations=3)&face&(dist<=5)
bottomzone=binary_dilation(bottomedge,iterations=4)&face&(dist<=6)
ledge=face&~left
rzone=binary_dilation(ledge,iterations=3)&face
block=C[t:b,l:r].copy()
safe=np.zeros_like(face);safe[3:-3,3:-3]=True
assert not np.any(face&~safe)
# Extruded steel shadow and charcoal ring strictly inside original glyph
# source box; preserve the remainder of all 13 atlas regions bit-exact.
extr=np.zeros_like(face)
extr[3:,2:]=face[:-3,:-2]
shadow=binary_dilation(extr,iterations=2)&safe
rim=binary_dilation(face,iterations=2)&safe
block[shadow,:3]=[23,24,27];block[shadow,3]=np.maximum(block[shadow,3],np.uint8(155))
block[rim,:3]=[31,32,36];block[rim,3]=np.maximum(block[rim,3],np.uint8(245))
# The per-row source-glyph reflection is attenuated by native edge-normal
# field, not flat silver recolor or seven artificial horizontal stripes.
shade=np.broadcast_to(profile[:,None,:],(h,w,3)).copy()
shade=np.clip(shade*1.02+4,88,251)
shade[topzone]=np.clip(shade[topzone]*0.38+np.asarray([254,253,251])*0.62,0,255)
shade[bottomzone]=np.clip(shade[bottomzone]*0.58+np.asarray([57,60,66])*0.42,0,255)
shade[rzone]=np.clip(shade[rzone]*0.80+np.asarray([245,245,245])*0.20,0,255)
block[face,:3]=np.uint8(np.clip(shade[face].round(),0,255))
block[face,3]=255
# Subpixel antialias preserved on the face boundary, without crop alpha boxes.
aaf=gaussian_filter(face.astype(np.float32),sigma=.55)
aa=(aaf>.07)&~face&rim
block[aa,:3]=[124,125,127]
block[aa,3]=np.maximum(block[aa,3],np.uint8(np.clip((aaf[aa]*130).round(),0,130)))
assert not np.any(block[~safe,3]),"new shadow outside bbox safety"
out=P.copy();out[t:b,l:r]=block
changed=np.any(out!=P,axis=2)
selected=np.zeros(S.shape[:2],bool);selected[t:b,l:r]=True
assert 15000<int(changed.sum())<130000
assert not np.any(changed&~selected)
assert np.array_equal(out[~selected],P[~selected])
assert not np.any((out[:,:,3]!=P[:,:,3])&~selected)
# Published trial only, not source approved candidate. Source DDS mask = BGRA.
raw=np.frombuffer(srcbytes[128:],dtype=np.uint8).reshape(2048,2048,4)
assert np.array_equal(raw[::-1,:,[2,1,0,3]],S)
dds=old[:128]+out[::-1,:,[2,1,0,3]].copy().tobytes()
assert len(dds)==len(old) and sha(dds)!=CUR
assert np.array_equal(dec(dds),out),"saved DDS roundtrip changed colour/alpha"
(OUT/"B337_Q228_CAR_SELECT_NOT_PROMOTED.dds").write_bytes(dds)
def composite(crop,bg):
 img=Image.new("RGBA",(crop.shape[1],crop.shape[0]),(*bg,255))
 img.alpha_composite(Image.fromarray(crop.copy(),"RGBA"))
 return img.convert("RGB")
views=[]
for ori in ("FLIPY","RAW"):
 for bgname,bg in (("GRAY",(90,90,90)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
  for pct in (100,75,50):
   crops=[]
   for arr in (S,C,P,out):
    t0=arr[t:b,l:r].copy()
    if ori=="RAW": t0=np.flipud(t0).copy()
    im=composite(t0,bg)
    if pct<100: im=im.resize((round(im.width*pct/100),round(im.height*pct/100)),Image.Resampling.LANCZOS)
    crops.append(im)
   result=Image.new("RGB",(sum(v.width for v in crops)+12,max(v.height for v in crops)),bg)
   xx=0
   for im in crops:result.paste(im,(xx,0));xx+=im.width+4
   n=f"B337_CAR_SELECT_{ori}_{bgname}_{pct}_SOURCE_CLEAN_OLD_TRIAL.png"
   result.save(OUT/n,optimize=True);views.append(n)
for key,arr in (("SOURCE",S),("CLEAN",C),("OLD",P),("TRIAL",out)):
 Image.fromarray(arr[t:b,l:r],"RGBA").save(OUT/f"B337_CAR_SELECT_{key}_LOSSLESS.png")
recipe={"schema":"source-family-v1","run_key":RUN,"source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
 "source_sha256":SRC,"source_original_bbox":[l,t,r,b],"source_effect_sample_count":int(source_metal.sum()),
 "text_source":"CAR SELECT","text_korean":TEXT,"font_path":str(fontpath),"font_sha256":sha(fontdata),
 "font_face_index":1,"font_ppem":ppem,"glyph_coverage":{ch:hex(ord(ch)) for ch in chars},
 "renderer":"Pillow_native_mask__scipy_normal_bevel__source_scanline_reflection",
 "renderer_git_sha":os.getenv("GITHUB_SHA"),"raw_orientation":"MIRROR_Y","readable_shear_dx_per_y":shear,
 "glyph_bbox":glyph_box,"clean_source_path":str(G/"role_B/20261005-B-PRODUCTION68/E7F6_CLEAN_PLATE.png"),
 "rework_reason":"C317/C327: old Korean was hollow black while English source was filled silver beveled chrome",
 "non_target_regions":12,"trial_only":True,"C_pilot_qualification":"NOT_RUN"}
(OUT/"recipe.json").write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+"\n")
qa={"role":"B","run":"B337","run_key":RUN,"queue_index":228,"priority":"P1","user_regression":"IGR-038",
 "new_native_trial_dds":1,"new_promoted_dds":0,"source_sha256":SRC,"current_candidate_sha256":CUR,
 "trial_sha256":sha(dds),"bbox_source":[l,t,r,b],"bbox_trial":glyph_box,"required_margin_px":3,
 "outside_selected_rgba_changes":int((changed&~selected).sum()),"outside_selected_alpha_changes":0,
 "current_other_12_regions_preserved":True,"decoded_persisted_trial_matches_composite":True,
 "font_sha256":sha(fontdata),"source_palette_samples":int(source_metal.sum()),
 "source_clean_alpha_zero":True,"source_family_method":"new native glyph normal-bevel and per-row source silver reflectance",
 "producer_visual":"PENDING_DIRECT_NATIVE_AND_PRACTICAL_REVIEW","independent_C2":"NOT_RUN",
 "C3":"NOT_RUN","approval":"NOT_GRANTED","user_game":"IGR-038_OPEN_USER_INGAME_FAIL",
 "RUNTIME_VALIDATION":"UNTESTED","all_18_views":views,"backend":"GITHUB_ACTIONS",
 "excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B337_MECHANICAL_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print("B337_NATIVE_CHROME_TRIAL_PERSISTED",json.dumps({k:qa[k] for k in ("trial_sha256","bbox_trial","outside_selected_rgba_changes","source_palette_samples")}),flush=True)
