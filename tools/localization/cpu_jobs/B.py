#!/usr/bin/env python3
"""B367 q060: one distinct SHA-bound, unpromoted source-conditioned smooth metal face pilot.
No automatic C/C3/game approval. Preserve official candidate and other atlas cells.
"""
import os
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
import io, sys, json, hashlib, urllib.request, subprocess
from pathlib import Path
from PIL import Image
import numpy as np
from scipy.ndimage import binary_erosion
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
R=Path(".").resolve()
G=Path("localization/graphics")
P=G/"role_B/20261011-B367-Q060-SOURCE-CONDITIONED-CONTINUOUS-METAL-PILOT"
P.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
H=lambda data:hashlib.sha256(data).hexdigest()
def b(ref,expect):
    z=Path(ref).read_bytes()
    assert H(z)==expect,(str(ref),H(z),expect)
    return z
def dec(data):
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGBA"))[::-1].copy()
official=b(G/"hd_candidates"/asset,"d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01")
trial=b(G/"role_B/20261010-B360-Q060-SOURCE-PALETTE-LAYER-VECTOR/B360_Q060_SOURCE_LAYERED_FACE_KOREAN_UNAPPROVED.dds","930222103b57a3ecf6b1ea1eca86a8a639809e8ad80020313c14a9adce13bb1d")
cb=b(G/"role_B/20261010-B348-Q060-BEST-TIME-SOURCE-COMPONENT-PLATE/B348_BEST_TIME_SOURCE_FIRST_PLATE_READABLE.png","a03687d4cd23ede4323dca63f07961061b7ba850c19c3a2f69764020a538bb48")
mask=b(G/"plate_library/objects/25a898178ea3e4fc08a16adfa35fa8612d8cdd4da274baf244ea67e29c24cca9.png","25a898178ea3e4fc08a16adfa35fa8612d8cdd4da274baf244ea67e29c24cca9")
sourceurl="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
with urllib.request.urlopen(sourceurl,timeout=90) as stream:
    src=stream.read()
assert H(src)=="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
assert len(src)==len(trial)==len(official)==33554560 and src[:128]==official[:128]==trial[:128]
tr=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","60"],text=True,capture_output=True,check=True)
tri=json.loads(tr.stdout)["assets"][0]
assert tri["next_action"] in ("METHOD_CHANGE_REQUIRED","MATERIAL_REWORK"),tri
S=dec(src); O=dec(official); T=dec(trial)
C=np.asarray(Image.open(io.BytesIO(cb)).convert("RGBA"))
M=np.asarray(Image.open(io.BytesIO(mask)).convert("L"))>0
assert S.shape==O.shape==T.shape==C.shape==(2048,4096,4) and M.shape==(2048,4096)
assert np.count_nonzero(M)==89391
assert np.count_nonzero(np.any(S!=C,axis=2)&~M)==0
assert np.count_nonzero(C[:,:,3][M])==0
x0,y0,x1,y1=2179,340,3028,474
rx0,ry0,rx1,ry1=2090,337,3120,485
assert np.count_nonzero(np.any(T!=O,axis=2)[:ry0])==0
allowed=np.zeros(M.shape,bool);allowed[ry0:ry1,rx0:rx1]=True
assert np.count_nonzero(np.any(T!=O,axis=2)&~allowed)==0
# Geometry starts from the rejected B360 native face silhouette, but its 
# independent material is NOT the rejected pixel-classified 4-band matte.
# Preserve true Hangul counters instead of dilating/stretched low-res glyphs.
q=T[y0:y1,x0:x1]
face=(q[:,:,3]>0)&(q[:,:,0]>155)&(q[:,:,1]>65)&(q[:,:,0]>q[:,:,2]+25)
face_alpha=np.where(face,q[:,:,3],0).astype(np.uint8)
assert int(face.sum())>15000,int(face.sum())
ext_alpha=np.where(~face,q[:,:,3],0).astype(np.uint8)
# Smoothly interpolate physical source-authored orange and gold, no row-step
# color thresholds or solid horizontal source-fraction stripes.
# This is a METHOD pilot, not a claim that source-metal typography is matched.
yy=np.indices(face.shape)[0].astype(np.float32)
v=np.clip((yy+ y0-340)/134.0,0,1)
smooth=lambda t:t*t*(3-2*t)
t=smooth(v)
orange=np.array((255,134,0),np.float32)
gold=np.array((255,210,95),np.float32)
rgb=np.rint(orange[None,None,:]*(1-t[:,:,None])+gold[None,None,:]*t[:,:,None]).astype(np.uint8)
# Model highlight as a source-inspired contour effect, not a flat stripe.
edge=face & ~binary_erosion(face,iterations=2)
edge_top=edge & (v<0.8)
highlight_alpha=np.where(edge_top,np.minimum(face_alpha.astype(np.uint16),95),0).astype(np.uint8)
h,w=2048,4096
def raw_png(name,kind,crop):
    a=np.zeros((h,w,4),np.uint8)
    a[y0:y1,x0:x1]=crop
    if kind=="RGBA":
        Image.fromarray(a[::-1].copy(),"RGBA").save(P/name)
    return a
g=np.zeros((h,w),np.uint8)
g[y0:y1,x0:x1]=face_alpha
Image.fromarray(g[::-1].copy(),"L").save(P/"B367_GEOMETRY_NATIVE_RAW_ALPHA.png")
facep=np.zeros((134,849,4),np.uint8)
facep[:,:,:3]=rgb;facep[:,:,3]=face_alpha
ex=np.where((~face)[:,:,None],q,0).astype(np.uint8)
hi=np.zeros((134,849,4),np.uint8)
hi[:,:,:3]=np.array((255,228,171),np.uint8)
hi[:,:,3]=highlight_alpha
E=raw_png("B367_EXTRUSION_NATIVE_RAW_RGBA.png","RGBA",ex)
F=raw_png("B367_FACE_NATIVE_RAW_RGBA.png","RGBA",facep)
HI=raw_png("B367_HIGHLIGHT_NATIVE_RAW_RGBA.png","RGBA",hi)
assert np.array_equal(F[y0:y1,x0:x1,3],g[y0:y1,x0:x1])
letter=Image.new("RGBA",(w,h))
for layer in (E,F,HI):
    # Paste sparse native region without huge intermediate full-resolution images
    letter.alpha_composite(Image.fromarray(layer[y0:y1,x0:x1],"RGBA"),dest=(x0,y0))
L=np.asarray(letter)
Image.fromarray(L[::-1].copy(),"RGBA").save(P/"B367_LETTERING_UNAPPROVED_NATIVE_RAW_RGBA.png")
N=O.copy()
bg=Image.fromarray(C[ry0:ry1,rx0:rx1],"RGBA")
top=Image.fromarray(L[ry0:ry1,rx0:rx1],"RGBA")
N[ry0:ry1,rx0:rx1]=np.asarray(Image.alpha_composite(bg,top))
changed=np.any(N!=O,axis=2)
assert np.count_nonzero(changed&~allowed)==0
# The original protected source siblings are outside the BEST TIME ROI.
assert np.array_equal(N[:ry0],O[:ry0])
assert np.array_equal(N[ry1:],O[ry1:])
# Persist RAW as the DDS's actual vertical mirror, then read back exact bytes.
out=official[:128]+N[::-1].tobytes()
dp=P/"B367_Q060_SMOOTH_METAL_UNAPPROVED.dds"
dp.write_bytes(out)
D=dec(dp.read_bytes())
assert np.array_equal(D,N)
alpha=D[y0:y1,x0:x1,3]
# Geometry/face cannot extend outside original text-effect ceiling.
new_vis=np.any(L[y0:y1,x0:x1,:]!=0,axis=2)
ys,xs=np.nonzero(new_vis)
newbox=[x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1]
assert all([newbox[0]>=x0,newbox[1]>=y0,newbox[2]<=x1,newbox[3]<=y1])
evidence=[]
for typ,bgval,pct in [("FLIPY",128,100),("FLIPY",255,75),("FLIPY",0,50),("RAW",128,100)]:
    seq=[S,C,O,T,D] if typ=="FLIPY" else [x[::-1] for x in (S,C,O,T,D)]
    ystart,yend=(ry0,ry1) if typ=="FLIPY" else (h-ry1,h-ry0)
    ims=[]
    for ar in seq:
        img=Image.fromarray(ar[ystart:yend,rx0:rx1],"RGBA")
        backing=Image.new("RGBA",img.size,(bgval,bgval,bgval,255))
        backing.alpha_composite(img)
        z=backing.convert("RGB")
        if pct!=100:z=z.resize((int(z.width*pct/100),int(z.height*pct/100)),Image.Resampling.LANCZOS)
        ims.append(z)
    ww,hh=ims[0].size
    contact=Image.new("RGB",(ww*5+20*4,hh),(bgval,bgval,bgval))
    for k,img in enumerate(ims):contact.paste(img,(k*(ww+20),0))
    name=f"B367_SAVED_SOURCE_CLEAN_OFFICIAL_B360_NEW_{typ}_BG{bgval}_{pct}.png"
    contact.save(P/name)
    evidence.append({"path":str(P/name),"sha256":H((P/name).read_bytes())})
def ref(name):
    path=P/name
    return {"path":path.as_posix(),"sha256":H(path.read_bytes())}
report={
    "run":"B367","role":"B","queue_index":60,"asset":asset,
    "method":"existing B360 native geometry reference -> independent smooth continuous source-orange/gold metal face, 2px contour light and separate dark extrusion; one unapproved family pilot",
    "method_change":"B360 rejected uniform horizontal source-frequency orange bars; this face has cubic continuous vertically graded source RGB and separate source-like contour highlight; no source-class row segmentation",
    "source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
    "source_sha256":H(src),"clean_sha256":H(cb),"removal_sha256":H(mask),
    "official_sha256":H(official),"rejected_B360_sha256":H(trial),"new_trial_sha256":H(out),
    "new_trial_dds":1,"official_promoted":0,"source_bbox":[x0,y0,x1,y1],
    "effect_bbox":newbox,"face_visible_pixels":int(face.sum()),"extrusion_visible_pixels":int(np.count_nonzero(ext_alpha)),
    "source_clean_removal_pixels":int(M.sum()),"source_clean_outside_rgba":0,"source_clean_inside_alpha":0,
    "current_official_to_trial_changed_rgba":int(changed.sum()),"changed_outside_declared_roi":0,
    "persisted_roundtrip_mismatch_pixels":0,"dimensions":[4096,2048],"format":"RGBA32","mips":1,"orientation":"RAW_MIRROR_Y",
    "geometry":ref("B367_GEOMETRY_NATIVE_RAW_ALPHA.png"),
    "layers":{"extrusion":ref("B367_EXTRUSION_NATIVE_RAW_RGBA.png"),"face":ref("B367_FACE_NATIVE_RAW_RGBA.png"),"highlight":ref("B367_HIGHLIGHT_NATIVE_RAW_RGBA.png")},
    "lettering":ref("B367_LETTERING_UNAPPROVED_NATIVE_RAW_RGBA.png"),
    "comparison":evidence,
    "PLATE_ONLY":"REUSED_C372_C2_PLATE_PASS",
    "GEOMETRY":"PENDING_CONTROLLER_FIRSTHAND_SOURCE_FAMILY_STYLE",
    "P3":"MECHANICAL_PERSISTED_EXACT_VISUAL_UNTESTED",
    "C2":"NOT_RUN","C3":"NOT_RUN","USER_INGAME":"OPEN_IGR044","RUNTIME_VALIDATION":"UNTESTED",
    "backend":"GITHUB_ACTIONS_CPU_WORKER","no_forbidden_domains":True,
}
(P/"B367_PILOT_MACHINE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B367","new_sha":H(out),"bbox":newbox,"face_pixels":int(face.sum()),"changed":int(changed.sum()),"evidence":len(evidence),"official_promoted":0},ensure_ascii=False),flush=True)
