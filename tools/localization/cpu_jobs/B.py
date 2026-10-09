#!/usr/bin/env python3
"""B323 q228: chrome luminance reconstruction on native B322 face silhouette.
NO prior glyph upscale, NO flat bands, transparent CLEAN composite, strict fail-closed.
The previous B322 hand-gradient trial was controller rejected for sharp bands/
underfilled silver, even though original-header and zero-outside tests passed.
"""
import csv, hashlib, io, json, os, sys, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, gaussian_filter, distance_transform_edt
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds"
OUT=G/"role_B/20261009-B323-Q228-CONTINUOUS-CHROME-TRANSFER"
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
SRC="3f98c940c51d2f054934d4e0b7c7d9745f9f8ad71d68548b0b336c62c1cf5154"
OLD="28e814599105600eb0222eb1ffe0057dc1e108520580a958ae3b3b7ec08f2808"
B322="ffb982af70aadf36a2f954d1de29bb045385ec0524ab5763a1ae363de370a2dd"
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(x for x in csv.DictReader(f) if x["index"].lstrip("\ufeff")=="228")
assert "rework_required" in row["artwork_status"],"q228 not an active rework"
with (G/"INGAME_REWORK_BACKLOG.csv").open(encoding="utf-8-sig",newline="") as f:
 assert any(r["id"]=="IGR-038" and r["status"]=="OPEN_USER_INGAME_FAIL" for r in csv.DictReader(f))
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","228","--require-safe-rerender"],capture_output=True,text=True)
assert tri.returncode==0 and json.loads(tri.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK",tri.stdout+tri.stderr
old=(G/"hd_candidates"/REL).read_bytes()
assert sha(old)==OLD,"Concurrent q228 candidate changed; fail closed"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds"
with urllib.request.urlopen(url,timeout=120) as r: source=r.read()
assert sha(source)==SRC and len(source)==len(old)==128+2048*2048*4
def dec(buf):
 x=np.asarray(Image.open(io.BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
 assert x.shape==(2048,2048,4)
 return x
S=dec(source);P=dec(old)
base=G/"role_B/20261005-B-PRODUCTION68"
manifest=json.loads((base/"B68_E7F6_REPORT.json").read_text())
assert manifest["source_sha256"]==SRC and len(manifest["rows"])==13
C=np.asarray(Image.open(base/"E7F6_CLEAN_PLATE.png").convert("RGBA"),dtype=np.uint8)
assert C.shape==S.shape
allowed=np.zeros(S.shape[:2],bool)
for r in manifest["rows"]:
 l,t,rr,b=r["original_bbox"];allowed[t:b,l:rr]=True
assert not np.any(np.any(S!=C,axis=2)&~allowed)
region=next(x for x in manifest["rows"] if x["source"]=="coast 2 coast")
l,t,rr,b=region["original_bbox"]
W=rr-l;H=b-t
assert [l,t,rr,b]==[5,26,1456,145]
assert not np.any(C[t:b,l:rr,3])
bdir=G/"role_B/20261009-B322-Q228-SOURCE-CHROME-REPRESENTATIVE"
meta=json.loads((bdir/"B322_MACHINE_GATE.json").read_text())
assert meta["trial_sha256"]==B322 and meta["source_sha256"]==SRC
# Preserve native letter topology from the newly created B322 mask, which
# was rendered at 2048x2048 and is never scaled or enlarged in this pass.
# Transfer entirely new chrome construction (a measured source effect).
B=np.asarray(Image.open(bdir/"COAST2COAST_TRIAL_LOSSLESS.png").convert("RGBA"),dtype=np.uint8)
assert B.shape==(H,W,4)
br=B[:,:,:3].mean(axis=2)
face=(B[:,:,3]>=220)&(br>=68)
assert 15000<=int(face.sum())<=110000,("unexpected source-native face",face.sum())
safe=np.zeros((H,W),bool);safe[5:-5,5:-5]=True
assert not np.any(face&~safe)
SRCroi=S[t:b,l:rr].astype(np.float32)
# Learn real English diffuse body where it actually exists: alpha-weighted
# gaussian normalized RGB rather than global seven-bands or hard stripes.
weight=(SRCroi[:,:,3].astype(np.float32)/255.0)*np.clip((SRCroi[:,:,:3].mean(axis=2)-50)/135,0,1)
denom=gaussian_filter(weight,sigma=(10,23),mode="nearest")+0.0001
local=np.stack([gaussian_filter(SRCroi[:,:,i]*weight,sigma=(10,23),mode="nearest")/denom for i in range(3)],axis=2)
# The source band's glints are measured then softened (no hard 34-RGB rows).
# Keep local source modulation subtle to avoid transferring literal English
# strokes into the new Hangul silhouette.
v=np.linspace(0,1,H,dtype=np.float32)
stops=np.asarray(meta["source_color_stops"],dtype=np.float32)
lin=np.stack([np.interp(v,np.linspace(0,1,len(stops)),stops[:,i]) for i in range(3)],axis=1)
lin=gaussian_filter(lin,sigma=(2.5,0),mode="nearest")
effect=(0.65*local+0.35*lin[:,None,:])
effect=gaussian_filter(effect,sigma=(1.15,2.5,0),mode="nearest")
effect=np.clip(effect,72,251)
dist=distance_transform_edt(face)
out=P.copy();block=C[t:b,l:rr].copy()
# Contained soft extrusion in lower right only and one-pixel black steel rim.
shift=np.zeros_like(face);shift[3:,2:]=face[:-3,:-2]
shadow=binary_dilation(shift,iterations=2)&safe
rim=binary_dilation(face,iterations=1)&safe
block[shadow,:3]=np.uint8([24,24,25]);block[shadow,3]=np.maximum(block[shadow,3],np.uint8(125))
block[rim,:3]=np.uint8([32,33,36]);block[rim,3]=np.maximum(block[rim,3],np.uint8(220))
# Continuous top edge catches source-like silver diffuse highlight,
# lower edge deepens. Round off artificially angular/pure horizontal bars.
up=np.zeros_like(face);up[1:]=face[1:]&~face[:-1]
down=np.zeros_like(face);down[:-1]=face[:-1]&~face[1:]
up=binary_dilation(up,iterations=2)&face&(dist<=3)
down=binary_dilation(down,iterations=2)&face&(dist<=3)
shade=effect.copy()
shade[up]=np.clip(shade[up]*0.69+np.array([249,249,249])*0.31,0,255)
shade[down]=np.clip(shade[down]*0.7+np.array([67,69,75])*0.30,0,255)
block[face,:3]=np.clip(np.rint(shade[face]),0,255).astype(np.uint8)
block[face,3]=255
# True native supersampling: recovered source-native silhouette remains exact
# size; subpixel front-edge antialias only inside the original face's 2px rim.
soft=gaussian_filter(face.astype(np.float32),sigma=.45)
feather=(soft>.06)&(~face)&rim
if feather.any():
 alpha=np.uint8(np.clip(np.rint(soft[feather]*140),0,120))
 block[feather,:3]=np.uint8([160,161,164])
 block[feather,3]=np.maximum(block[feather,3],alpha)
assert np.count_nonzero(face)>14000 and not np.any(block[~safe,3])
out[t:b,l:rr]=block
changed=np.any(P!=out,axis=2)
allowed_rework=np.zeros(S.shape[:2],bool);allowed_rework[t:b,l:rr]=True
assert np.count_nonzero(changed)>12000
assert not np.any(changed&~allowed_rework)
assert not np.any((out[:,:,3]!=P[:,:,3])&~allowed_rework)
assert np.array_equal(out[~allowed_rework],P[~allowed_rework])
raw=np.frombuffer(source[128:],dtype=np.uint8).reshape(2048,2048,4)
if np.array_equal(raw[::-1],S):
 mode="RGBA"; body=out[::-1].copy().tobytes()
else:
 assert np.array_equal(raw[::-1,:,[2,1,0,3]],S)
 mode="BGRA";body=out[::-1,:,[2,1,0,3]].copy().tobytes()
dds=old[:128]+body
assert len(dds)==len(old) and sha(dds) not in (OLD,B322)
D=dec(dds)
bad=np.any(D!=out,axis=2)
if np.any(bad):
 ys,xs=np.where(bad)
 sample=[(int(y),int(x),D[y,x].tolist(),out[y,x].tolist()) for y,x in list(zip(ys,xs))[:8]]
 print("ROUNDTRIP_DIFF",int(bad.sum()),sample, "source/raw equality",np.array_equal(raw[::-1],S),flush=True)
 assert False,"saved native DDS exact roundtrip FAILED"
assert np.array_equal(D,out)
(OUT/"B323_TRIAL_NOT_PROMOTED.dds").write_bytes(dds)
def flatten(v,bg):
 bgimg=Image.new("RGBA",(v.shape[1],v.shape[0]),(*bg,255))
 bgimg.alpha_composite(Image.fromarray(v,"RGBA"))
 return bgimg.convert("RGB")
views=[]
for orientation in ("FLIPY","RAW"):
 crops=[x[t:b,l:rr].copy() for x in (S,C,P,out)]
 if orientation=="RAW":crops=[np.flipud(x).copy() for x in crops]
 for bgname,bg in (("GRAY",(128,128,128)),("WHITE",(255,255,255)),("BLACK",(0,0,0))):
  for scale in (100,75,50):
   imgs=[flatten(x,bg) for x in crops]
   if scale!=100:imgs=[im.resize((round(im.width*scale/100),round(im.height*scale/100)),Image.Resampling.LANCZOS) for im in imgs]
   sheet=Image.new("RGB",(sum(im.width for im in imgs)+12,max(im.height for im in imgs)),bg)
   xx=0
   for im in imgs:sheet.paste(im,(xx,0));xx+=im.width+4
   n=f"COAST2COAST_{orientation}_{bgname}_{scale}_SOURCE_CLEAN_OLD_B323.png";sheet.save(OUT/n,optimize=True);views.append(n)
for n,src in (("SOURCE",S),("CLEAN",C),("OLD",P),("TRIAL",out)):
 Image.fromarray(src[t:b,l:rr],"RGBA").save(OUT/f"COAST2COAST_{n}_LOSSLESS.png")
report=dict(run="B323",role="B",queue_index=228,regression="IGR-038",
 status="NATIVE_TRANSFER_TRIAL_PENDING_CONTROLLER_VISUAL",source_sha256=SRC,
 current_sha256=OLD,rejected_B322_sha256=B322,trial_sha256=sha(dds),
 source_bbox=[l,t,rr,b],native=[2048,2048],format=mode,mips=1,
 method="native B322 letter silhouette with continuous normalized local English silver reflectance + SOURCE dark rim and soft morphologic rounded bevel, NOT scaled, NO seven hard bands",
 silhouette_native_pixels=int(face.sum()),silhouette_width_px=int(np.ptp(np.where(face)[1])+1),
 source_width_px=W,protected_safety_inset_px=5,byte_exact_header=True,
 changed_rgba_outside_representative=0,changed_alpha_outside_representative=0,
 original_protected_pixels_modified=0,persisted_roundtrip_exact=True,
 views=views,promoted_dds=0,producer_visual="NOT_RUN",independent_C2="NOT_RUN",
 C3="NOT_RUN",user_game="OPEN_USER_INGAME_FAIL",
 RUNTIME_VALIDATION="UNTESTED",backend="github-actions",excluded=["VR","FFB","DX11","DXVK"])
(OUT/"B323_MACHINE_GATE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print("B323 READY",sha(dds),report["silhouette_native_pixels"],len(views),flush=True)
