#!/usr/bin/env python3
"""B368 q060 P3: compose APPROVED-BY-B P2 manual glyph geometry with separate
source-conditioned face/rim/extrusion/highlight and save one UNPROMOTED DDS.
Requires preexisting firsthand geometry review. Never claims independent C2.
"""
import os,sys,json,hashlib,io,urllib.request,subprocess
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter,binary_erosion
from PIL import Image
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
R=Path(".").resolve()
G=Path("localization/graphics")
P=G/"role_B/20261011-B368-Q060-HAND-VECTOR-ITALIC-GLYPH-GEOMETRY"
dig=lambda data:hashlib.sha256(data).hexdigest()
def ref(path):
 path=Path(path)
 return {"path":path.as_posix(),"sha256":dig(path.read_bytes())}
def pin(path,sha):
 b=Path(path).read_bytes()
 assert dig(b)==sha,(path,dig(b),sha)
 return b
def rgba(path):
 with Image.open(path) as im:
  return np.asarray(im.convert("RGBA")).copy()
asset="textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
source_sha="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
clean_sha="a03687d4cd23ede4323dca63f07961061b7ba850c19c3a2f69764020a538bb48"
off_sha="d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01"
old_sha="52d97f845b7b3e588ebe5136cd299882001d509320fd4f8cc910270f314142d9"
pp=json.loads((P/"B368_VECTOR_GEOMETRY_PROPOSAL.json").read_text())
gp=P/"B368_GEOMETRY_NATIVE_RAW_ALPHA.png"
sp=P/"SOURCE_NATIVE_RAW_RGBA.png"
review_path=P/"B368_GEOMETRY_REVIEW.json"
rev=json.loads(review_path.read_text())
assert rev["status"]=="GEOMETRY_READY" and rev["reviewer"]=="B" and rev["route"]=="layered_metal"
assert rev["source_sha256"]==pp["source_raw_png_sha256"]
assert rev["geometry_sha256"]==pp["geometry_sha256"]
assert rev.get("firsthand_visual_result")=="P2_SCOPED_GEOMETRY_READY_NO_C_APPROVAL"
assert set(("stroke","counterspace","proportions","slant","readability"))<=set(rev["observations"])
assert rev.get("evidence")
assert dig(gp.read_bytes())==pp["geometry_sha256"]
assert dig(sp.read_bytes())==pp["source_raw_png_sha256"]
off=pin(G/"hd_candidates"/asset,off_sha)
old=pin(G/"role_B/20261011-B367-Q060-SOURCE-CONDITIONED-CONTINUOUS-METAL-PILOT/B367_Q060_SMOOTH_METAL_UNAPPROVED.dds",old_sha)
cb=pin(G/"plate_library/objects"/(clean_sha+".png"),clean_sha)
sourceurl="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
with urllib.request.urlopen(sourceurl,timeout=90) as f:source=f.read()
assert dig(source)==source_sha and len(off)==len(source)==len(old)==33554560
tr=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","60"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert tr["next_action"]=="METHOD_CHANGE_REQUIRED"
def dec(data):
 return np.asarray(Image.open(io.BytesIO(data)).convert("RGBA"))[::-1].copy()
S=dec(source);O=dec(off);Old=dec(old)
C=np.asarray(Image.open(io.BytesIO(cb)).convert("RGBA"))
assert S.shape==O.shape==Old.shape==C.shape==(2048,4096,4)
assert np.array_equal(rgba(sp),S[::-1])
with Image.open(gp) as im:
 assert im.mode=="L" and im.size==(4096,2048)
 g=np.asarray(im)[::-1].copy()
assert int(np.count_nonzero(g))>10000
bbox=[2179,340,3028,474]
yx=np.argwhere(g>0);lo=yx.min(axis=0);hi=yx.max(axis=0)+1
native=[int(lo[1]),int(lo[0]),int(hi[1]),int(hi[0])]
assert native==pp["new_geometry_bbox"]
assert native[0]>bbox[0]+2 and native[1]>bbox[1]+2 and native[2]<bbox[2]-2 and native[3]<bbox[3]-2
fg=g>8
# Three independently rasterized source-specific effects, no font fallback.
border=maximum_filter(g,size=7,mode="constant") >8
def shift(a,dy,dx):
 b=np.zeros_like(a)
 b[dy:,dx:]=a[:-dy,:-dx]
 return b
side=shift(border,3,2)
rear=shift(border,5,3)
# All pixels of the EFFECT silhouette must fit within exact source effect
# footprint, not just the source's enormous sprite plate.
total=border|side|rear
ys,xs=np.nonzero(total)
effect_box=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
assert effect_box[0]>=bbox[0] and effect_box[1]>=bbox[1] and effect_box[2]<=bbox[2] and effect_box[3]<=bbox[3],effect_box
def save_layer(name,make):
 a=np.zeros((2048,4096,4),np.uint8)
 a[337:485,2090:3120]=make
 Image.fromarray(a[::-1].copy(),"RGBA").save(P/name)
 return ref(P/name)
a0,a1,b0,b1=337,485,2090,3120
gray=np.uint8
locslice=np.s_[a0:a1,b0:b1]
# Genuine source-palette navy underlay, source-right bottom 3px extrusion.
shadow=np.zeros((a1-a0,b1-b0,4),np.uint8)
shadow[:,:,:3]=[5,13,49]
shadow[:,:,3]=np.where(rear[locslice],152,0)
sidewall=np.zeros_like(shadow)
sidewall[:,:,:3]=[13,24,77]
sidewall[:,:,3]=np.where(side[locslice],215,0)
rim=np.zeros_like(shadow)
rim[:,:,:3]=[7,16,66]
rim[:,:,3]=np.where(border[locslice],243,0)
# Continuous source-oriented orange-to-gold face, not B360 row
# classification bands. The new MANUAL glyph geometry is independently new.
face=np.zeros_like(shadow)
yy=np.arange(a0,a1,dtype=np.float32)[:,None]
p=np.clip((yy-340)/134,0,1)
p=p*p*(3-2*p)
start=np.array([255,133,4],dtype=np.float32)
finish=np.array([255,207,78],dtype=np.float32)
color=np.rint(start[None,None,:]*(1-p[:,:,None])+finish[None,None,:]*p[:,:,None]).astype(np.uint8)
face[:,:,:3]=np.broadcast_to(color,face.shape[:2]+(3,))
face[:,:,3]=g[locslice]
# Highlights follow hand-authored glyph CONTOURS rather than horizontal
# rows so there are no artificial flat orange stripes on the face.
fmask=fg[locslice]
inner=binary_erosion(fmask,iterations=2)
edge=fmask&~inner
high=np.zeros_like(shadow)
high[:,:,:3]=[255,230,179]
high[:,:,3]=np.where(edge&((yy-340)<80),np.minimum(g[locslice],110),0).astype(np.uint8)
parts=[
 {"role":"shadow","input":save_layer("B368_SHADOW_NATIVE_RAW_RGBA.png",shadow)},
 {"role":"extrusion","input":save_layer("B368_EXTRUSION_NATIVE_RAW_RGBA.png",sidewall)},
 {"role":"rim","input":save_layer("B368_RIM_NATIVE_RAW_RGBA.png",rim)},
 {"role":"face","input":save_layer("B368_FACE_NATIVE_RAW_RGBA.png",face)},
 {"role":"highlight","input":save_layer("B368_HIGHLIGHT_NATIVE_RAW_RGBA.png",high)}
]
recipe={"version":"separated-lettering-v1","coordinates":"native_raw",
 "route":"layered_metal","source":ref(sp),"geometry":ref(gp),
 "geometry_recipe":ref("tools/localization/recipes/B368_q060_manual_racing_contours.py"),
 "geometry_review":ref(review_path),"layers":parts}
rp=P/"B368_LETTERING_RECIPE.json"
rp.write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+"\n")
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path("tools/localization").resolve()))
from compose_lettering import compose
composed,stat=compose(R,recipe)
letterpath=P/"B368_LETTERING_NATIVE_RAW_RGBA.png"
composed.save(letterpath)
letterraw=np.asarray(composed)
letter=letterraw[::-1].copy()
letter_mask=letter[:,:,3]>0
assert np.all(~letter_mask|total) and not np.any(letter_mask&~(total))
yy,xx=np.nonzero(letter_mask)
eff=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
assert eff[0]>=bbox[0] and eff[1]>=bbox[1] and eff[2]<=bbox[2] and eff[3]<=bbox[3]
# Compare CLEAN vs FINAL separately from SOURCE vs CLEAN.
N=O.copy()
clean_roi=Image.fromarray(C[locslice].copy(),"RGBA")
letter_roi=Image.fromarray(letter[locslice].copy(),"RGBA")
N[locslice]=np.asarray(Image.alpha_composite(clean_roi,letter_roi))
allowed=np.zeros((2048,4096),bool);allowed[locslice]=True
changed=np.any(N!=O,axis=2)
assert not np.any(changed&~allowed)
contamination=np.any(N!=C,axis=2)&allowed&~letter_mask
assert not np.any(contamination),("COMPOSITE_OUTSIDE_GLYPH_EFFECT",int(contamination.sum()))
assert np.count_nonzero((N[:,:,3]>0)&~(C[:,:,3]>0)&~letter_mask)==0
out=off[:128]+N[::-1].tobytes()
ddsp=P/"B368_Q060_HAND_VECTOR_LAYERED_UNAPPROVED.dds"
ddsp.write_bytes(out)
D=dec(out)
assert np.array_equal(D,N) and len(out)==33554560
assert dig(out)!=old_sha
# Different geometry, not previous flat alpha relighting.
shape_delta=int(np.count_nonzero((D[:,:,3]>0)!=(Old[:,:,3]>0)))
assert shape_delta>12000,shape_delta
evidence=[]
for orient,bg,pct in [("FLIPY",128,100),("FLIPY",255,75),("FLIPY",0,50),("RAW",128,100)]:
 seq=[S,C,O,Old,D] if orient=="FLIPY" else [t[::-1] for t in [S,C,O,Old,D]]
 y0,y1=(a0,a1) if orient=="FLIPY" else (2048-a1,2048-a0)
 views=[]
 for img in seq:
  crop=Image.fromarray(img[y0:y1,b0:b1].copy(),"RGBA")
  base=Image.new("RGBA",crop.size,(bg,bg,bg,255));base.alpha_composite(crop)
  show=base.convert("RGB")
  if pct!=100: show=show.resize((show.width*pct//100,show.height*pct//100),Image.Resampling.LANCZOS)
  views.append(show)
 w,h=views[0].size
 combined=Image.new("RGB",(5*w+60,h),(bg,bg,bg))
 for i,frame in enumerate(views):combined.paste(frame,(i*(w+15),0))
 name=f"B368_SAVED_SOURCE_CLEAN_OFFICIAL_B367_NEW_{orient}_BG{bg}_{pct}.png"
 combined.save(P/name)
 evidence.append(ref(P/name))
report={
 "run":"B368","role":"B","queue_index":60,"run_key":"OUTRUN-KOR-B368-Q060-MANUAL-SOURCE-GLYPH-GEOMETRY-20261011-1130",
 "source_sha256":source_sha,"clean_sha256":clean_sha,
 "official_unchanged_sha256":off_sha,"previous_rejected_B367_sha256":old_sha,
 "new_saved_dds_sha256":dig(out),"persisted_bytes":len(out),
 "source_bbox":bbox,"hand_vector_geometry_bbox":native,"final_effect_bbox":eff,
 "mips":1,"format":"RGBA32","raw_orientation":"MIRROR_Y",
 "prior_B367_to_new_visible_alpha_delta":shape_delta,
 "official_to_new_changed_rgba":int(changed.sum()),
 "official_to_new_outside_besttime_roi_rgba":0,
 "clean_to_final_outside_layer_changed_rgba":int(contamination.sum()),
 "saved_dds_decoded_mismatch":0,
 "geometry_recipe":recipe["geometry_recipe"],"geometry_review":recipe["geometry_review"],
 "lettering_recipe":ref(rp),"lettering":ref(letterpath),"layers":parts,
 "compare_saved_dds":evidence,"compose":stat,
 "P1":"C372_C2_PLATE_PASS_REUSED","P2":"PRODUCER_GEOMETRY_READY_SCOPED",
 "P3":"PERSISTED_MECHANICAL_PASS_PENDING_DIRECT_VISUAL",
 "official_dds_promoted":0,"new_trial_dds":1,
 "C2":"NOT_RUN","C3":"NOT_RUN","INGAME":"IGR044_OPEN_NOT_RUN","RUNTIME_VALIDATION":"UNTESTED"
}
(P/"B368_PERSISTED_MACHINE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B368","trial_sha256":dig(out),"new_alpha_shape_pixels":shape_delta,"bbox":eff,"persisted_delta":0},ensure_ascii=False))
