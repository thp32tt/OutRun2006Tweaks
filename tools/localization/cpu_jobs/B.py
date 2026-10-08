#!/usr/bin/env python3
"""B288 / q137 IGR-041: source-conditioned thin/angular native family trial.
No auto promotion: persist trial and evidence for controller pixel-first QA.
Unlike B285 heavy identical per-label stroke, use controlled 0/1/2 family strokes;
contours and follow the exact independent CLEAN, not text-crop background.
"""
import hashlib, io, json, os, struct, subprocess, sys, tempfile, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
G=Path("localization/graphics");P=G/"hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
OUT=G/"role_B/20261009-B288-Q137-P0-SOURCE-STROKE-CALIBRATION"; OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
SOURCE="11c90e063e83e485d15da16a157a7da7f4c99144b0ee9004205ef4ee724d21cc"
PRIOR="1b21b5ecd1229ce48f1e50e14cf6f1097f988362b741c1489aeb852e1ffd2ae2"
CLEAN_SHA="b128a8fd82f3ccae6300511c22e63bf40e2938e114b8417aada19bbd49bc9098"
CLEAN=G/"role_A/20261005-A-PRODUCTION22/30CF0D_HD_CLEAN_PLATE.png"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
tri=json.loads(subprocess.check_output([sys.executable,"tools/localization/rework_triage.py","--index","137","--require-safe-rerender"],text=True))["assets"][0]
assert tri["next_action"]=="MATERIAL_REWORK"
prior=P.read_bytes();assert sha(prior)==PRIOR,("concurrent candidate",sha(prior))
assert sha(CLEAN.read_bytes())==CLEAN_SHA
with tempfile.TemporaryDirectory(prefix="b287_") as tmp:
  dest=Path(tmp)/"source.dds";urllib.request.urlretrieve(source_url,dest);english=dest.read_bytes()
assert sha(english)==SOURCE
assert english[:128]==prior[:128] and len(english)==len(prior)==128+2048*1024*4
assert struct.unpack_from("<II",english,12)==(1024,2048)
def dec(buf):return np.array(Image.open(io.BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
source=dec(english);old=dec(prior);clean=np.array(Image.open(CLEAN).convert("RGBA"))
assert source.shape==old.shape==clean.shape==(1024,2048,4)
fontp=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
if not fontp.exists():
 subprocess.run(["sudo","apt-get","update","-qq"],check=True)
 subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
assert fontp.is_file()
# SHA-pinned C1 source/effect region bounds.
rows=[
 ("select_transmission","SELECT TRANSMISSION","변속기 선택",(5,67,868,130),1,255),
 ("transmission_small","TRANSMISSION","변속기",(1288,96,1569,128),0,170),
 ("manual_small","MANUAL","수동",(14,148,339,210),1,170),
 ("automatic_small","AUTOMATIC","자동",(822,147,1376,216),1,170),
 ("manual_large","MANUAL","수동",(1,235,397,315),2,255),
 ("automatic_large","AUTOMATIC","자동",(889,233,1775,315),2,255)
]
allowed=np.zeros((1024,2048),bool)
for _,_,_,(l,t,r,b),_,_ in rows:
 assert not allowed[t:b,l:r].any();allowed[t:b,l:r]=True
assert not np.any(source[~allowed]!=clean[~allowed]),"source/clean plate leaks outside localized cells"
# Retained thin separator on MANUAL large is protected original, not source text.
out=old.copy()
notes=[]
def bbox_alpha(x):
 yy,xx=np.nonzero(x>15)
 return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
for name,en,ko,(l,t,r,b),native_stroke,opacity in rows:
 w,h=r-l,b-t
 # Separate PLATE_ONLY evidence; inspect before lettering.
 tile=clean[t:b,l:r].copy()
 src=source[t:b,l:r]
 # Derive source face RGB from the same exact English pixels, retaining the
 # English white vs gray hierarchy, without arbitrary bold stroke/outline.
 face=src[(src[:,:,3]>40)&(src[:,:,:3].max(axis=2)>=20)]
 if len(face)<100:raise RuntimeError(("insufficient English palette",name))
 rgb=np.rint(np.percentile(face[:,:3],70 if opacity==255 else 55,axis=0)).astype(np.uint8)
 # Compare native source line height; bound by exact source font row height,
 # 1px+ positive margins and never exceed source bbox.
 requested=max(13,h-6)
 draw=None; chosen=None
 for px in range(int(requested*1.55),12,-1):
  f=ImageFont.truetype(str(fontp),px,index=1)
  bb=f.getbbox(ko,stroke_width=native_stroke)
  tw,th=bb[2]-bb[0],bb[3]-bb[1]
  if th<=h-5 and tw<=w-6:
   img=Image.new("L",(tw,th),0)
   ImageDraw.Draw(img).text((-bb[0],-bb[1]),ko,font=f,fill=255,stroke_width=native_stroke,stroke_fill=255)
   if img.getbbox() is not None:draw=img;chosen=px;break
 if draw is None:raise RuntimeError(("no native font fit",name))
 # Native family contour correction informed by C1 (smalls 0/1; big 2), B285 big 3px rejected.
 # Existing native glyph stays vector-antialiased, not raster-upscaled.
 ww,hh=draw.size
 x=l+(w-ww)//2;y=t+(h-hh)//2
 assert x>l and y>t and x+ww<r and y+hh<b
 tileP=Image.fromarray(tile,"RGBA")
 glyph=Image.new("RGBA",draw.size,tuple(map(int,rgb))+(0,))
 alpha=draw.point(lambda p:(p*opacity+127)//255)
 glyph.putalpha(alpha)
 tileP.alpha_composite(glyph,(x-l,y-t))
 merged=np.array(tileP)
 out[t:b,l:r]=merged
 # Actual decode bbox of CHANGED GLYPH ONLY relative to the clean plate.
 mask=np.any(merged!=tile,axis=2).astype(np.uint8)*255
 bb=bbox_alpha(mask)
 assert bb is not None and bb[0]>0 and bb[1]>0 and bb[2]<w and bb[3]<h
 notes.append(dict(key=name,english=en,korean=ko,source_effect_bbox=[l,t,r,b],
  candidate_effect_bbox=[l+bb[0],t+bb[1],l+bb[2],t+bb[3]],font_px=chosen,
  font_family="Noto Sans CJK KR Regular native vector, no dilation",added_stroke_px=native_stroke,
  source_derived_face_rgb=rgb.tolist(),source_derived_alpha=opacity,
  positive_margins=[bb[0],w-bb[2],bb[1],h-bb[3]]))
# Native BGRA32 with RAW Y mirror; preserve source exact mask + header and mip.
raw_rgba=np.flipud(out)
trial=prior[:128]+raw_rgba[:,:,[2,1,0,3]].copy().tobytes()
assert trial[:128]==prior[:128] and len(trial)==len(prior)
persist=dec(trial)
assert np.array_equal(out,persist),"native persisted DDS roundtrip"
assert sha(trial)!=PRIOR,"did not rework material pixels"
diff=np.any(old!=persist,axis=2)
outside=int(diff[~allowed].sum())
alphaoutside=int(((old[:,:,3]!=persist[:,:,3])&~allowed).sum())
assert outside==alphaoutside==0
assert np.all(old[~allowed]==persist[~allowed])
# Retain RAW/source/clean/old/persisted for controller visual 10-stage gate.
def panel(a,bg):
 z=Image.new("RGBA",(a.shape[1],a.shape[0]),bg)
 z.alpha_composite(Image.fromarray(a,"RGBA"))
 return z.convert("RGB")
views=[("SOURCE",source),("CLEAN",clean),("B285",old),("B288",persist)]
for name,_,_,(l,t,r,b),_,_ in rows:
 crop=(max(0,l-3),max(0,t-3),min(2048,r+3),min(1024,b+3))
 ll,tt,rr,bb=crop
 for percent in (100,75,50):
  panels=[]
  for label,arr in views:
   p=panel(arr[tt:bb,ll:rr],(65,65,65,255))
   if percent!=100:p=p.resize((max(1,p.width*percent//100),max(1,p.height*percent//100)),Image.Resampling.LANCZOS)
   panels.append(p)
  c=Image.new("RGB",(sum(p.width for p in panels)+12,max(p.height for p in panels)),(107,107,107))
  x=0
  for p in panels:c.paste(p,(x,0));x+=p.width+4
  c.save(OUT/f"{name}_SOURCE_CLEAN_B285_B288_{percent}.png")
 panels=[panel(np.flipud(arr[tt:bb,ll:rr]),(65,65,65,255)) for _,arr in views]
 c=Image.new("RGB",(sum(p.width for p in panels)+12,max(p.height for p in panels)),(107,107,107))
 x=0
 for p in panels:c.paste(p,(x,0));x+=p.width+4
 c.save(OUT/f"{name}_SOURCE_CLEAN_B285_B288_RAW.png")
# High-level exact native/50 grid for all six regions; no font overlap/boxes.
for name,arr in views:
 panel(arr,(65,65,65,255)).resize((1024,512),Image.Resampling.LANCZOS).save(OUT/f"FULL_{name}_50.png")
(OUT/"30CF0D_B288_TRIAL_NOT_PROMOTED.dds").write_bytes(trial)
qa=dict(role="B",run="B288",queue_index=137,priority="P0",regression="IGR-041",
 source_url=source_url,source_sha256=SOURCE,clean_sha256=CLEAN_SHA,
 old_candidate_sha256=PRIOR,trial_sha256=sha(trial),rework_triage=tri,
 new_working_trial_dds=1,new_production_candidate_dds=0,
 source_clean_changed_outside_6_bboxes=0,clean_plate_provenance="A22 exact SOURCE/CLEAN",
 bbox_source_ceiling="6of6 PASS",decode_exact=True,header_exact=True,raw_mirror_y=True,
 native=[2048,1024],codec="BGRA32",mips=1,
 changed_outside_source_bbox=outside,alpha_changed_outside_source_bbox=alphaoutside,
 rows=notes,method="SOURCE_REGION_NATIVE_CONTOUR_STROKE_BALANCE_FROM_C1_VISUAL",
 previous_method="B285 C1-rejected 1/2/3px bold dilations and B287 overly thin zero-stroke trial",
 producer_visual="PENDING_CONTROLLER_NATIVE_AND_PRACTICAL",candidate_promoted=False,
 C="NOT_RUN",C3="NOT_RUN",USER="NOT_RUN",RUNTIME_VALIDATION="UNTESTED",
 backend="GITHUB_HOSTED_INPUTS_CANONICAL_PUBLIC_SOURCE_AND_GIT_DDS_UNAVAILABLE_CHATGPT_LOCAL",
 excluded_domains=["VR","FFB","DX11","DXVK"])
(OUT/"B288_MACHINE_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B288","trial_sha256":sha(trial),"outside":outside,"rows":len(notes)},ensure_ascii=False))
