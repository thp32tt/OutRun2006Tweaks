#!/usr/bin/env python3
"""B369 q060 P2: manually revised glyph topology of 최고 기록: after C2 B368 independent FAIL.

Unlike B360/B368 this builds a NEW Hangul alpha silhouette by four manually
specified jamo stroke graphs and source-authored forward-lean anchors. No prior
Korean bitmap is rescaled, sheared, or reused. Stage1 writes geometry, sources,
and comparison for firsthand producer visual review BEFORE any material layers.
"""
import io, os, json, sys, hashlib, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
digest=lambda z:hashlib.sha256(z).hexdigest()
G=Path("localization/graphics")
P=G/"role_B/20261011-B369-Q060-SOURCE-CONDITIONED-HEAVY-CONTOURS"
P.mkdir(parents=True,exist_ok=True)
repo=Path(".")
asset="textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
srcsha="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
offsha="d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01"
oldsha="11e081c7f3c12bd13cf100995ec533ce78a557ac97eb1135ff84fc1e0a2d5a6b"
clean_sha="a03687d4cd23ede4323dca63f07961061b7ba850c19c3a2f69764020a538bb48"
masksha="25a898178ea3e4fc08a16adfa35fa8612d8cdd4da274baf244ea67e29c24cca9"
def read(path,sha):
 d=Path(path).read_bytes()
 assert digest(d)==sha,(path,digest(d),sha)
 return d
official=read(G/"hd_candidates"/asset,offsha)
old=read(G/"role_B/20261011-B368-Q060-HAND-VECTOR-ITALIC-GLYPH-GEOMETRY/B368_Q060_HAND_VECTOR_LAYERED_UNAPPROVED.dds",oldsha)
clean_data=read(G/"plate_library/objects"/(clean_sha+".png"),clean_sha)
mask_data=read(G/"plate_library/objects"/(masksha+".png"),masksha)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
with urllib.request.urlopen(url, timeout=90) as fh:
 english=fh.read()
assert digest(english)==srcsha and len(english)==len(official)==len(old)==33554560
assert english[:128]==official[:128]==old[:128]
tri=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","60"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert tri["next_action"]=="METHOD_CHANGE_REQUIRED",tri
def dec(data):
 return np.asarray(Image.open(io.BytesIO(data)).convert("RGBA"))[::-1].copy()
S=dec(english);O=dec(official);T=dec(old)
C=np.asarray(Image.open(io.BytesIO(clean_data)).convert("RGBA"))
M=np.asarray(Image.open(io.BytesIO(mask_data)).convert("L"))>0
assert S.shape==O.shape==T.shape==C.shape==(2048,4096,4)
assert M.shape==(2048,4096) and np.count_nonzero(M)==89391
assert np.count_nonzero(np.any(S!=C,axis=2)&~M)==0
assert not np.any(C[:,:,3][M])
# Preserve all neighboring OUTRUN MILES and HOLLY WOLF atlas cells.
SOURCE_BBOX=(2179,340,3028,474)
X0,Y0=2187,342
W,H=833,130
SS=4
SLOPE=0.31 # source B forward-italic stem OLS approximately 0.3421
line=Image.new("L",(W*SS,H*SS),0)
draw=ImageDraw.Draw(line)
def point(x,y):return (round((x+SLOPE*(123-y))*SS),round(y*SS))
def stroke(pts,width=17):
 d=[point(*t) for t in pts]
 draw.line(d,fill=255,width=round(width*SS),joint="curve")
# Each jamo is intentionally authored with its OWN contours, terminals,
# counter-spaces and source-conditioned diagonal forward strokes.
# 최 (ㅊ + ㅗ + ㅣ): three heavy stepped horizontal heads and descending ㅈ.
x=14
stroke([(x+40,11),(x+89,11)],18)
stroke([(x+17,37),(x+99,37)],24)
stroke([(x+59,39),(x+27,71)],25)
stroke([(x+61,39),(x+96,72)],25)
stroke([(x+60,76),(x+60,110)],24)
stroke([(x+13,112),(x+105,112)],22)
stroke([(x+129,16),(x+129,111)],27)
# 고 (ㄱ + ㅗ): independent wide round-corner roof, open vowel counter.
x=193
stroke([(x+13,18),(x+124,18),(x+124,72)],28)
stroke([(x+75,74),(x+75,112)],26)
stroke([(x+7,112),(x+143,112)],24)
# 기 (ㄱ + ㅣ): two strictly separated source-angle large stems.
x=413
stroke([(x+10,19),(x+97,19),(x+97,102)],27)
stroke([(x+131,18),(x+131,111)],27)
# 록 (ㄹ + ㅗ + ㄱ): stacked upper ㄹ, centered vowel ㅗ, lower ㄱ.
x=591
stroke([(x+11,14),(x+127,14),(x+127,35),(x+15,35),(x+15,60),(x+128,60)],19)
stroke([(x+73,62),(x+73,84)],23)
stroke([(x+7,87),(x+143,87)],23)
stroke([(x+16,106),(x+128,106),(x+128,117)],19)
# Colon as two actual visible native circles; short PIL thick lines produce
# 1px slashes rather than dots when length < stroke width (B369 P2 first look).
def punctuation_dot(x,y,r=8):
 px,py=point(x,y)
 draw.ellipse((px-r*SS,py-r*SS,px+r*SS,py+r*SS),fill=255)
punctuation_dot(780,53)
punctuation_dot(780,100)
# B369 material method change: native per-stroke polygonal wedge terminals and
# letter-specific joins. These contours alter topology at the source-native
# frame; no image dilation, prior-raster reuse, overall shear, or palette change.
def wedge(pts):
 draw.polygon([point(*v) for v in pts],fill=255)
wedge([(18,33),(31,29),(36,37),(29,50)]) # 최 angled leading cut
wedge([(95,64),(111,82),(110,91),(88,75)]) # ㅊ diagonal flourish
wedge([(206,19),(221,12),(229,24),(218,35)]) # 고 roof serif
wedge([(318,68),(333,71),(340,84),(318,82)]) # 고 descending angle
wedge([(426,17),(443,11),(451,24),(433,32)]) # 기 slanted roof
wedge([(511,97),(531,110),(526,119),(504,105)]) # 기 terminal
wedge([(602,14),(618,8),(621,21),(605,29)]) # 록 top-left corner
wedge([(714,103),(731,115),(731,121),(710,119)]) # 록 base turn
glyph=np.asarray(line.resize((W,H),Image.Resampling.LANCZOS))
glyph=np.where(glyph<4,0,glyph).astype(np.uint8)
assert glyph.shape==(H,W)
Y1,X1=Y0+H,X0+W
assert X0>=SOURCE_BBOX[0] and Y0>=SOURCE_BBOX[1] and X1<=SOURCE_BBOX[2] and Y1<=SOURCE_BBOX[3]
g=np.zeros((2048,4096),np.uint8)
g[Y0:Y1,X0:X1]=glyph
yx=np.argwhere(g>0)
yx0,yx1=yx.min(axis=0),yx.max(axis=0)+1
bbox=[int(yx0[1]),int(yx0[0]),int(yx1[1]),int(yx1[0])]
assert bbox[0]>=SOURCE_BBOX[0] and bbox[1]>=SOURCE_BBOX[1] and bbox[2]<=SOURCE_BBOX[2] and bbox[3]<=SOURCE_BBOX[3],bbox
# Materially new topology proof: compare alpha masks independently before effects.
prior=T[:,:,3]
# Restrict geometry novelty to the source text itself; inherited official
# atlas neighbors would otherwise create a false 3-million-pixel delta.
source_scope=np.zeros(g.shape,bool)
source_scope[SOURCE_BBOX[1]:SOURCE_BBOX[3],SOURCE_BBOX[0]:SOURCE_BBOX[2]]=True
different=int(np.count_nonzero(((g>0)!=(prior>0)) & source_scope))
assert different>9000,("NOT_DISTINCT_FROM_B368",different)
# source native RAW and proposed new alpha RAW are pinned for common compose.
Image.fromarray(S[::-1].copy(),"RGBA").save(P/"SOURCE_NATIVE_RAW_RGBA.png")
Image.fromarray(g[::-1].copy(),"L").save(P/"B369_GEOMETRY_NATIVE_RAW_ALPHA.png")
# Unaffected outside target native ROI is defined as an immutable region for P3.
N=C.copy(); N[Y0:Y1,X0:X1]=0
plain=np.zeros((2048,4096,4),np.uint8)
plain[:,:,0]=248;plain[:,:,1]=221;plain[:,:,2]=174;plain[:,:,3]=g
# Scoped P2 preview alpha-compose the NEW shape over independent CLEAN.
patch=Image.fromarray(C[337:485,2090:3120],"RGBA")
layer=Image.fromarray(plain[337:485,2090:3120],"RGBA")
N[337:485,2090:3120]=np.asarray(Image.alpha_composite(patch,layer))
proof=[]
for orient,bg,pct in [("FLIPY",128,100),("FLIPY",255,75),("FLIPY",0,50),("RAW",128,100)]:
 y0,y1=(337,485) if orient=="FLIPY" else (2048-485,2048-337)
 seq=[S,C,O,T,N] if orient=="FLIPY" else [x[::-1] for x in [S,C,O,T,N]]
 views=[]
 for a in seq:
  image=Image.fromarray(a[y0:y1,2090:3120].copy(),"RGBA")
  bgim=Image.new("RGBA",image.size,(bg,bg,bg,255));bgim.alpha_composite(image)
  frame=bgim.convert("RGB")
  if pct!=100:frame=frame.resize((max(1,frame.width*pct//100),max(1,frame.height*pct//100)),Image.Resampling.LANCZOS)
  views.append(frame)
 w,h=views[0].size
 contact=Image.new("RGB",(5*w+4*15,h),(bg,bg,bg))
 for i,v in enumerate(views):contact.paste(v,(i*(w+15),0))
 name=f"B369_SOURCE_CLEAN_OFFICIAL_B368_MANUAL_GEOMETRY_{orient}_BG{bg}_{pct}.png"
 contact.save(P/name)
 proof.append({"path":str(P/name),"sha256":digest((P/name).read_bytes())})
anchor_top=point(143,18)
anchor_bottom=point(143,111)
manifest={
 "run":"B369","producer_role":"B","queue_index":60,"stage":"P2_NEW_SOURCE_CONDITIONED_CONTOUR_GEOMETRY_ONLY",
 "status":"GEOMETRY_REVIEW_PENDING_CONTROLLER","P1":"C372_INDEPENDENT_PLATE_PASS_REUSED",
 "source_sha256":srcsha,"clean_sha256":clean_sha,"official_sha256":offsha,"rejected_prior_B368_sha256":oldsha,
 "geometry_sha256":digest((P/"B369_GEOMETRY_NATIVE_RAW_ALPHA.png").read_bytes()),
 "source_raw_png_sha256":digest((P/"SOURCE_NATIVE_RAW_RGBA.png").read_bytes()),
 "original_effect_bbox":SOURCE_BBOX,"new_geometry_bbox":bbox,
 "new_shape_vs_B368_binary_symmetric_difference_pixels":different,
 "native_ppem":"source-contour wedge/topology + per-stroke native widths -> explicit 4x one native L downsample",
 "font":"NONE_HAND_AUTHORED","glyph_inventory":["최","고","기","록",":"],
 "source_B_stem_top_minus_bottom_slope":0.3421,
 "manual_Korean_reference_stem_top_minus_bottom_normalized_slope":SLOPE,
 "anchor_top_native_S4":anchor_top,"anchor_bottom_native_S4":anchor_bottom,
 "source_bounding_ceiling":"PASS","P2_firsthand_controller_visual":"NOT_YET_REVIEWED",
 "C2":"NOT_RUN","C3":"NOT_RUN","USER_GAME":"NOT_RUN_IGR044_OPEN","RUNTIME_VALIDATION":"UNTESTED",
 "official_dds_promoted":0,"new_dds":0,"preview_is_only_flat_unlit_ink":True,
 "evidence":proof,
 "producer_next":"Controller must inspect shape and counters at native/50/RAW before constructing separate face/rim/extrusion/highlight and encoding saved DDS."
}
(P/"B369_VECTOR_GEOMETRY_PROPOSAL.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B369","geometry_bbox":bbox,"diff_prior_alpha":different,"evidence":len(proof)},ensure_ascii=False),flush=True)
