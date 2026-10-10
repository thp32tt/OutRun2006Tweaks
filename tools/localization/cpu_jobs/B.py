#!/usr/bin/env python3
"""B355 q154 C356 overweight font correction: exact historical native contour halfway,
source-anchored alpha interpolation (not 1px dilation or tiny new text).
One final unapproved reference-family trial; current official unchanged.
"""
import os,io,sys,json,struct,hashlib,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
OUT=G/"role_B/20261010-B355-Q154-HISTORIC-NATIVE-COUNTER-INTERPOLATION";OUT.mkdir(parents=True,exist_ok=True)
ASSET="localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
CURRENT_SHA="c4d6c1515716476123b69dfb645dcc27a3cc7a69f31a1368a831004a0b40d524"
PRE_B298_SHA="94678124f6cddaeb44520c6419f4b475d1452866c052ff301a4859dddf38cb1f"
SOURCE_SHA="15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf"
BEFORE_COMMIT="85c1d2e0ce4a5299b1b3037dc9cfb612e0167ec4"
sha=lambda b:hashlib.sha256(b).hexdigest()
tri=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","154"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert tri["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),tri["next_action"]
p=Path(ASSET).read_bytes();assert sha(p)==CURRENT_SHA,("DRIFT",sha(p))
old=subprocess.run(["git","show",f"{BEFORE_COMMIT}:{ASSET}"],capture_output=True,check=True).stdout
assert sha(old)==PRE_B298_SHA and old[:128]==p[:128],("HISTORICAL_SOURCE_MISMATCH",sha(old))
srcpath=G/"hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
if srcpath.exists():s=srcpath.read_bytes()
else:
 url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
 with urllib.request.urlopen(url,timeout=90) as response:s=response.read()
assert sha(s)==SOURCE_SHA and s[:128]==p[:128]
def dec(b):return np.asarray(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S,C,P=dec(s),dec(p),dec(old)
assert S.shape==C.shape==P.shape==(1024,4096,4)
c344=json.loads((G/"role_C/20261010-C344-C2-Q154-EXACT-FULL-CLEAN-PLATE/C344_Q154_EXACT_FULL_CLEAN_MACHINE.json").read_text())
assert c344["sha256"]["SOURCE"]==SOURCE_SHA and c344["sha256"]["FINAL"]==CURRENT_SHA
regions={r["id"]:tuple(r["bbox"]) for r in c344["regions"]}
assert len(regions)==8
clean=S.copy()
for l,t,r,b in regions.values():clean[t:b,l:r]=0
targets=["06_single_player_gray","07_showroom_gray","08_multiplayer_gray"]
O=C.copy();stat=[]
allowed=np.zeros(C.shape[:2],bool)
for name in targets:
 l,t,r,b=regions[name]
 allowed[t:b,l:r]=True
 cur=C[t:b,l:r].copy(); pre=P[t:b,l:r].copy()
 # C311 original trial was too weak; B298 full one-pixel maximum-alpha
 # filter was independently rejected for thick slab/counter-space. Half
 # subpixel RGBA alpha interpolation retains exact original contour
 # placement and source color while recovering negative space at native pixels.
 a=(cur[:,:,3].astype(np.uint16)+pre[:,:,3].astype(np.uint16)+1)//2
 assert np.all(cur[:,:,3]>=pre[:,:,3]),(name,"B298_NOT_SUPERSET")
 out=cur.copy();out[:,:,3]=a.astype(np.uint8)
 # current RGB used only where nontransparent; newly translucent pixels retain
 # original B298 source-conditioned gray [78,96,100], never paint a rectangle.
 mask=out[:,:,3]>0
 assert np.all(np.max(np.abs(out[mask,:3].astype(np.int16)-[78,96,100]),axis=1)<20),(name,"UNEXPECTED_FAMILY_RGB")
 O[t:b,l:r]=out
 yy,xx=np.nonzero(out[:,:,3]>128)
 bb=[l+int(xx.min()),t+int(yy.min()),l+int(xx.max()+1),t+int(yy.max()+1)]
 assert bb[0]>l and bb[1]>t and bb[2]<r and bb[3]<b,(name,bb)
 stat.append({"id":name,"source_bbox":[l,t,r,b],"candidate_alpha_gt128_bbox":bb,
 "changed_native_alpha_pixels":int(np.sum(out[:,:,3]!=cur[:,:,3])),
 "previous_original_alpha_pixels":int(np.sum(pre[:,:,3]>0)),
 "current_rejected_alpha_pixels":int(np.sum(cur[:,:,3]>0)),
 "interpolated_alpha_pixels":int(np.sum(out[:,:,3]>0)),
 "remaining_positive_bbox_margins":[bb[0]-l,r-bb[2],bb[1]-t,b-bb[3]]})
changed=np.any(O!=C,axis=2)
assert changed.any() and not np.any(changed&~allowed)
assert np.array_equal(O[~allowed],C[~allowed])
masks=struct.unpack_from("<IIII",p,92)
assert masks in ((255,65280,16711680,4278190080),(16711680,65280,255,4278190080)),masks
order=[0,1,2,3] if masks[0]==255 else [2,1,0,3]
raw=p[:128]+np.flipud(O)[:,:,order].copy().tobytes()
assert len(raw)==len(p) and sha(raw)!=CURRENT_SHA
D=dec(raw);assert np.array_equal(D,O)
(OUT/"B355_Q154_GRAY_FAMILY_HALF_PIXEL_UNAPPROVED.dds").write_bytes(raw)
def bgvis(ar,box,color=(110,110,110),raw_view=False):
 l,t,r,b=box
 if raw_view:
  ar=np.flipud(ar);t,b=1024-b,1024-t
 im=Image.fromarray(ar[t:b,l:r],"RGBA")
 out=Image.new("RGBA",im.size,color+(255,));out.alpha_composite(im)
 return out.convert("RGB")
views=[]
for name in targets:
 box=regions[name]
 for mode in ("FLIPY","RAW"):
  for scale in ((100,75,50) if mode=="FLIPY" else (100,)):
   frames=[bgvis(a,box,raw_view=(mode=="RAW")) for a in (S,clean,P,C,D)]
   if scale!=100:frames=[im.resize((round(im.width*scale/100),round(im.height*scale/100)),Image.Resampling.LANCZOS) for im in frames]
   W=sum(im.width for im in frames)+4*(len(frames)-1);H=max(im.height for im in frames)
   panel=Image.new("RGB",(W,H),(110,110,110));off=0
   for im in frames:panel.paste(im,(off,0));off+=im.width+4
   file=f"B355_{name}_SOURCE_CLEAN_C311_C356_NEW_GRAY_{scale}_{mode}.png"
   panel.save(OUT/file,optimize=True);views.append(file)
 l,t,r,b=box
 Image.fromarray(clean[t:b,l:r],"RGBA").save(OUT/f"B355_{name}_PLATE_ONLY.png")
 # COMPOSITE_ONLY excludes inherited other five colored regions
 Image.fromarray(D[t:b,l:r],"RGBA").save(OUT/f"B355_{name}_COMPOSITE_ONLY.png")
report={"schema_version":2,"role":"B","run":"B355","index":154,
 "run_key":"OUTRUN-KOR-B355-Q154-EXACT-C311-C356-SUBPIXEL-FAMILY-20261010",
 "triage":tri["next_action"],"method":"Exact historical C311 underweight native silhouette (SHA946...) and C356 B298 overweight glyph silhouette (SHAc4d6..) non-destructively alpha-interpolated 50% at original 4096x1024 pixels, with source-conditioned gray face retained. Source-derived native stem weight repair; never rescale old lowres raster.",
 "canonical_source_sha256":SOURCE_SHA,"pre_B298_sha256":PRE_B298_SHA,
 "current_official_sha256":CURRENT_SHA,"authored_C344_clean_sha256":"a4d707fa4376a7db4cc04fd1de51d9dc23b1874eac9a8b4988dc44c7f4c23380",
 "new_unapproved_saved_dds_sha256":sha(raw),"dds_size_bytes":len(raw),
 "new_saved_unapproved_trials":1,"promoted_official_dds":0,
 "changed_visible_rgba":int(changed.sum()),"outside_gray3_changed":int(np.sum(changed&~allowed)),
 "decoded_persisted_diff_pixels":int(np.sum(np.any(D!=O,axis=2))),
 "native":[4096,1024],"format":"RGBA32","mip_count":1,"raw_transform":"MIRROR_Y",
 "regions":stat,"evidence_images":views,
 "producer_static":"MECHANICAL_PASS_OPTICAL_SOURCE_FAMILY_CONTROLLER_REVIEW_PENDING",
 "C2":"NOT_RUN","C3":"BLOCKED","RUNTIME_VALIDATION":"UNTESTED"}
(OUT/"B355_Q154_MACHINE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(OUT/"recipe.json").write_text(json.dumps({"source_SHA":SOURCE_SHA,"reference_C311_alpha_SHA":PRE_B298_SHA,
 "reference_C356_alpha_SHA":CURRENT_SHA,"subpixel_core_alpha_formula":"(C311+C356+1)//2",
 "native_source_face_RGB":[78,96,100],"protected_original_red5":True,
 "review_required":"native100/75/50 RAW source-relative gray family and C2 first-look; no promotion until producer PASS"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B355","sha":sha(raw),"changed":int(changed.sum()),"regions":stat},ensure_ascii=False))
