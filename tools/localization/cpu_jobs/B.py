#!/usr/bin/env python3
"""B364 q236 source-family pilot: independently re-render ONE native row.
Unapproved artifact only; retain official DDS and all other 13 rows.
"""
import os,io,json,sys,hashlib,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
H=lambda b:hashlib.sha256(b).hexdigest()
G=Path("localization/graphics")
OUT=G/"role_B/20261011-B364-Q236-ROW05-SOURCE-NATIVE-PILOT"
OUT.mkdir(parents=True,exist_ok=True)
SRC_SHA="a1c7f7d6ca5d2440076e49477cefecbf5084b4188072f3427ff13e5da24bc518"
CLEAN_SHA="c202f55e0de29e98d48e182f50cff8a94bcaa32bafc14c884644868db6552af7"
CURRENT_SHA="9e2069ebe7eda210b2b9a0e39436724efc53932b3af7ba624b918056b24b6337"
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds"
tri=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","236"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert tri["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED","EVIDENCE_ONLY_HOLD"),tri
old=(G/"hd_candidates"/asset).read_bytes()
assert H(old)==CURRENT_SHA,("CONCURRENT_CANDIDATE_CHANGED",H(old))
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds"
with urllib.request.urlopen(url,timeout=90) as f: src=f.read()
assert H(src)==SRC_SHA,("SOURCE_SHA_MISMATCH",H(src))
assert src[:128]==old[:128] and len(src)==len(old)==128+2048*2048*4
def dec(b):
 return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S=dec(src);O=dec(old)
clean_path=G/"role_B/20261005-B-PRODUCTION80/FEF_CLEAN_PLATE.png"
cp=clean_path.read_bytes()
assert H(cp)==CLEAN_SHA,("B80_CLEAN_CHANGED",H(cp))
C=np.array(Image.open(io.BytesIO(cp)).convert("RGBA"))
assert C.shape==S.shape==O.shape==(2048,2048,4)
# C340 independently authenticated this exact plate for the 14 native rows.
box=(255,1356,1056,1451);x0,y0,x1,y1=box
assert np.max(C[y0:y1,x0:x1,3])==0, "CLEAN_ROW05_ALPHA_NOT_ZERO"
assert np.any(S[y0:y1,x0:x1,3]>0), "MISSING_ORIGINAL_STROKES"
# The contract prohibits scaling any previous Hangul raster; render native
# glyph contours afresh using the installed licensed Noto TTC.
fontpath=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
assert fontpath.exists(), "PINNED_HANGUL_FONT_NOT_INSTALLED"
txt="스카이스크레이퍼스"
# No generic fallback: check every syllable and require a source-sized result.
from fontTools.ttLib import TTCollection
ttc=TTCollection(str(fontpath))
assert any(all(ord(c) in font.getBestCmap() for c in txt if c!=" ") for font in ttc.fonts),"MISSING_GLYPH"
# Distinct from B302 Black at 82-91ppem: true native Bold outlines with a
# controlled 1px native stroke for source-family weight and full source-height.
choices=[]
for ppem in range(86,111):
 font=ImageFont.truetype(str(fontpath),ppem)
 sheet=Image.new("L",(1400,170),0)
 d=ImageDraw.Draw(sheet)
 d.text((10,10),txt,font=font,fill=255,stroke_width=1,stroke_fill=255)
 bb=sheet.getbbox()
 if bb:
  w,h=bb[2]-bb[0],bb[3]-bb[1]
  if w<=x1-x0-8 and h<=y1-y0-4:
   choices.append((abs(h-(y1-y0-4)), -h,ppem,bb,sheet))
assert choices,"NATIVE_SOURCE_CEILING_PREVENTS_PILOT"
choices.sort(key=lambda z:z[:3])
_,_,ppem,bb,sheet=choices[0]
letter=sheet.crop(bb)
lw,lh=letter.size
assert (lw>0 and 89<=lh<=91),("NATIVE_HEIGHT_DID_NOT_CLOSE_C358_GAP",lw,lh,ppem)
left=x1-4-lw;top=y0+(y1-y0-lh)//2
assert left>=x0+4 and top>=y0+2 and top+lh<=y1-2
# Exact source family: sample original fully opaque dark lettering ink in this
# row, not a made-up style or older low-resolution Korean colors.
sroi=S[y0:y1,x0:x1];samples=sroi[(sroi[:,:,3]>=200)]
assert len(samples)>1000
ink=np.median(samples[:,:3],axis=0).round().astype(np.uint8)
# Target is a transparent sprite. Compose directly from verified B80 clean,
# replacing only the rejected row. Other 13 rows are immutable current bytes.
N=O.copy()
N[y0:y1,x0:x1]=C[y0:y1,x0:x1]
alpha=np.array(letter,dtype=np.uint8)
patch=N[top:top+lh,left:left+lw]
patch[:,:,:3]=ink
patch[:,:,3]=alpha
# Ensure only approved row and no additional pixels outside the English bbox.
ch=np.any(N!=O,axis=2)
allow=np.zeros((2048,2048),bool);allow[y0:y1,x0:x1]=True
assert int(np.count_nonzero(ch&~allow))==0,"UNAUTHORIZED_ATLAS_DELTA"
assert int(np.count_nonzero(N[y0:y1,x0:x1,3]))>0
bpx=np.argwhere(N[:,:,3]>0)  # global artwork is preserved, so measure row separately
loc=np.argwhere(N[y0:y1,x0:x1,3]>0)
assert len(loc)>0
by0,bx0=loc.min(axis=0);by1,bx1=loc.max(axis=0)+1
nb=(x0+int(bx0),y0+int(by0),x0+int(bx1),y0+int(by1))
assert nb[0]>=x0+4 and nb[1]>=y0+2 and nb[2]<=x1-4 and nb[3]<=y1-2
# Raw DDS stores bottom-to-top BGRA32, exact header and original format.
raw=old[:128]+N[::-1][:,:,[2,1,0,3]].tobytes()
D=dec(raw)
assert raw[:128]==old[:128] and len(raw)==len(old)
assert np.array_equal(D,N), "PERSISTED_DDS_ROUNDTRIP_FAIL"
assert np.count_nonzero(np.any(D!=O,axis=2)&~allow)==0
fname="B364_Q236_ROW05_NATIVE_BOLD_UNAPPROVED.dds"
(OUT/fname).write_bytes(raw)
assert H((OUT/fname).read_bytes())==H(raw)
# Readable orientation and raw mirrored byte-based views at true native /75/50.
evidence=[]
for orient in ["FLIPY","RAW"]:
 for bg,pct in ([(0,100),(128,100),(128,75),(255,50)] if orient=="FLIPY" else [(128,100)]):
  ar=[S,C,O,D] if orient=="FLIPY" else [v[::-1].copy() for v in [S,C,O,D]]
  yy0,yy1=(y0-4,y1+4) if orient=="FLIPY" else (2048-y1-4,2048-y0+4)
  xlo,xhi=(x0-6,x1+6)
  imgs=[]
  for a in ar:
   z=Image.fromarray(a[yy0:yy1,xlo:xhi],"RGBA")
   paper=Image.new("RGBA",z.size,(bg,bg,bg,255));paper.alpha_composite(z)
   im=paper.convert("RGB")
   if pct!=100:im=im.resize((im.width*pct//100,im.height*pct//100),Image.Resampling.LANCZOS)
   imgs.append(im)
  w,h=imgs[0].size;board=Image.new("RGB",(w*4+30,h),(bg,bg,bg))
  for j,im in enumerate(imgs):board.paste(im,(j*(w+10),0))
  fn=f"B364_ROW05_SOURCE_CLEAN_CURRENT_PILOT_{orient}_BG{bg}_{pct}.png"
  board.save(OUT/fn);evidence.append(fn)
Image.fromarray(np.where(ch,255,0).astype("uint8"),"L").save(OUT/"B364_CHANGED_PIXEL_MASK.png")
qa={"role":"B","run":"B364","queue_index":236,"priority":"C358_CONFIRMED_REWORK_AFTER_P0_P1_METHOD_BLOCKERS",
 "source_sha256":SRC_SHA,"clean_sha256":CLEAN_SHA,"official_unchanged_sha256":CURRENT_SHA,
 "new_unapproved_saved_dds_sha256":H(raw),"source_box":list(box),"new_bbox":list(nb),
 "method":"Independent row05 new native Bold TTC with 1px source-family stroke; target 91px source height, original English sampled ink; no prior Korean raster scaling.",
 "native_ppem":ppem,"font_sha256":H(fontpath.read_bytes()),"text":txt,
 "native":[2048,2048],"dds":"BGRA32","mips":1,"orientation":"RAW_FLIP_Y",
 "machine_bbox_containment":"PASS_SCOPED","changed_rgba":int(ch.sum()),
 "changed_outside_row05":0,"persisted_roundtrip_mismatch":0,
 "source_family":"PILOT_UNQUALIFIED_NEEDS_FIRST_LOOK","producer_visual":"PENDING_FIRST_HAND_EXACT_PIXEL_REVIEW",
 "plate_stage":"REUSED_C340_PINNED_SOURCE_B80_CLEAN_SCOPED",
 "remaining13":"UNCHANGED_FROM_C2_REJECTED_OFFICIAL","official_promoted_dds":0,"new_trial_dds":1,
 "C2":"NOT_RUN","C3":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
 "evidence":evidence,"excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B364_MACHINE.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
(OUT/"recipe.json").write_text(json.dumps({"index":236,"region":"row05_SKYSCRAPERS","source":SRC_SHA,"clean":CLEAN_SHA,"previous":CURRENT_SHA,
 "font_path":str(fontpath),"font_sha256":qa["font_sha256"],"ppem":ppem,"native_stroke_px":1,
 "glyph":"스카이스크레이퍼스","source_bbox":list(box),"result_bbox":list(nb),
 "source_ink_median_rgb":ink.tolist(),"method":"fresh_native_bold_stroke_source_bbox_target"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B364","sha":H(raw),"bbox":nb,"changed":int(ch.sum()),"outside":0}),flush=True)
