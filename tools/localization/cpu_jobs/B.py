#!/usr/bin/env python3
"""B320 P0 q137 TRANSMISSION small: source-family native gray small-label trial.

Exact source and A22 plate are pinned. Rebuild only the small upper gray transmission cell,
never auto-promote before direct persisted-DDS SOURCE/CLEAN/FINAL review.
"""
import csv, hashlib, io, json, os, subprocess, sys, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageFont, ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
OUT=G/"role_B/20261009-B320-Q137-P0-SMALL-MODE-HIERARCHY"
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
SRC="11c90e063e83e485d15da16a157a7da7f4c99144b0ee9004205ef4ee724d21cc"
CLEAN="b128a8fd82f3ccae6300511c22e63bf40e2938e114b8417aada19bbd49bc9098"
OLD="0c988e8b06010a0f003445d8b068a45871202bf0c3bcbf61dd5c203954458d22"
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(r for r in csv.DictReader(f) if r["index"].lstrip("\ufeff")=="137")
assert "b319" in row["artwork_status"] and "one_upper_small_rework_required" in row["artwork_status"]
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","137","--require-safe-rerender"],text=True,capture_output=True)
assert tri.returncode==0 and json.loads(tri.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK",tri.stdout+tri.stderr
current=(G/"hd_candidates"/REL).read_bytes()
assert sha(current)==OLD,"q137 current candidate changed; do not overwrite concurrent work"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/30CF0D_512x256.dds"
with urllib.request.urlopen(url,timeout=160) as f:src=f.read()
assert sha(src)==SRC and src[:128]==current[:128]
platebytes=(G/"role_B/20261009-B285-Q137-SOURCE-ALPHA-FAMILY/B285_PLATE_ONLY_RGBA.png").read_bytes()
assert sha(platebytes)==CLEAN
def decode(buf):
 a=np.asarray(Image.open(io.BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
 assert a.shape==(1024,2048,4)
 return a
S=decode(src); P=decode(current)
C=np.asarray(Image.open(io.BytesIO(platebytes)).convert("RGBA"),dtype=np.uint8)
assert C.shape==P.shape
allregions=[(5,67,868,130),(1288,96,1569,128),(14,148,339,210),(822,147,1376,216),(1,235,397,315),(889,233,1775,315)]
scope=np.zeros(P.shape[:2],bool)
for l,t,r,b in allregions: scope[t:b,l:r]=True
assert np.count_nonzero(np.any(S!=C,axis=2)&~scope)==0
assert np.count_nonzero(C[:,:,3][scope])==3579
assert np.count_nonzero(np.any(P!=S,axis=2)&~scope)==0
l,t,r,b=allregions[1]
maskbox=np.zeros(P.shape[:2],bool);maskbox[t:b,l:r]=True
font="/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
if not Path(font).exists():
 subprocess.run(["sudo","apt-get","update","-qq"],check=True)
 subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
assert Path(font).exists()
# Reconstruct small English TRANSMISSION as meaningful 변속기 유형 선택.
# Avoid stretched old Korean raster, and render gray 170-alpha from source.
word="변속기 유형 선택"
picked=None
for px in range(40,22,-1):
 ft=ImageFont.truetype(font,px,index=1)
 bb=ft.getbbox(word,stroke_width=0)
 layer=Image.new("L",(bb[2]-bb[0]+16,bb[3]-bb[1]+16),0)
 ImageDraw.Draw(layer).text((8-bb[0],8-bb[1]),word,font=ft,fill=255)
 bounds=layer.getbbox()
 if not bounds:continue
 glyph=layer.crop(bounds)
 if glyph.height<=b-t-6 and glyph.width<=r-l-8:
  picked=(px,glyph);break
assert picked, "no safe native Hangul small gray label fits original source bbox"
px,glyph=picked
out=P.copy(); out[t:b,l:r]=C[t:b,l:r]
nx=l+(r-l-glyph.width)//2; ny=t+(b-t-glyph.height)//2
margins=[nx-l,r-nx-glyph.width,ny-t,b-ny-glyph.height]
assert min(margins)>=3,margins
alpha=np.asarray(glyph,dtype=np.uint8)
assert not np.any((C[ny:ny+glyph.height,nx:nx+glyph.width,3]>0)&(alpha>0)),"protected source plate collision"
rgba=np.zeros((glyph.height,glyph.width,4),dtype=np.uint8)
rgba[:,:,:3]=255;rgba[:,:,3]=np.round(alpha.astype(np.float32)*170/255).astype(np.uint8)
out[ny:ny+glyph.height,nx:nx+glyph.width]=rgba
changed=np.any(P!=out,axis=2)
assert np.count_nonzero(changed)>1000 and not np.any(changed&~maskbox)
assert not np.any((P[:,:,3]!=out[:,:,3])&~maskbox)
assert np.array_equal(out[~maskbox],P[~maskbox])
raw=np.frombuffer(current[128:],dtype=np.uint8).reshape(1024,2048,4)
if np.array_equal(raw[::-1],P):
 order="RGBA";body=out[::-1].copy().tobytes()
else:
 assert np.array_equal(raw[::-1,:,[2,1,0,3]],P)
 order="BGRA";body=out[::-1,:,[2,1,0,3]].copy().tobytes()
data=current[:128]+body
assert len(data)==len(current) and sha(data)!=OLD
D=decode(data);assert np.array_equal(D,out)
(OUT/"B320_TRIAL_NOT_PROMOTED.dds").write_bytes(data)
def onbg(a,bg):
 layer=Image.new("RGBA",(a.shape[1],a.shape[0]),tuple(bg)+(255,))
 layer.alpha_composite(Image.fromarray(a,"RGBA"))
 return layer.convert("RGB")
views=[]
for orientation in ("FLIPY","RAW"):
 crops=[a[t:b,l:r].copy() for a in (S,C,P,D)]
 if orientation=="RAW":crops=[np.flipud(a).copy() for a in crops]
 for name,bg in (("GRAY",(110,110,110)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
  for scale in (100,75,50):
   frames=[onbg(a,bg) for a in crops]
   if scale!=100:frames=[im.resize((max(1,round(im.width*scale/100)),max(1,round(im.height*scale/100))),Image.Resampling.LANCZOS) for im in frames]
   sheet=Image.new("RGB",(sum(im.width for im in frames)+12,max(im.height for im in frames)),bg)
   x=0
   for im in frames:sheet.paste(im,(x,0));x+=im.width+4
   nameout=f"transmission_small_{orientation}_{name}_{scale}_SOURCE_CLEAN_B319_B320.png"
   sheet.save(OUT/nameout,optimize=True);views.append(nameout)
meta={"role":"B","run":"B320","queue_index":137,"regression":"IGR-041","production_status":"TRIAL_PENDING_DIRECT_VISUAL","source_sha256":SRC,
 "clean_png_sha256":CLEAN,"old_candidate_sha256":OLD,"trial_sha256":sha(data),"promoted_dds":0,
 "source_clean_outside_six":0,"plate_protected_pixels":3579,"changed_outside_small_rgba":0,"changed_outside_small_alpha":0,
 "preserved_other_five_regions":"PIXEL_EXACT","original_bbox":[l,t,r,b],"trial_bbox":[nx,ny,nx+glyph.width,ny+glyph.height],
 "positive_margins":margins,"source_dimensions":[2048,1024],"dds_format":order,"mips":1,
 "saved_decoded_equals_trial":True,"header_exact":True,"raw_mirror_y":True,
 "semantic_change":"small TRANSMISSION -> 변속기 유형 선택, expanded native label versus undersized 변속기",
 "font":"Native Noto Sans CJK KR Black with original gray170 alpha, transparent glyph-only mask, no box or unsupported effects",
 "font_px":px,"glyph_size":[glyph.width,glyph.height],"glyph_width_fraction_source":round(glyph.width/(r-l),4),
 "glyph_height_fraction_source":round(glyph.height/(b-t),4),"contacts":views,"producer_visual":"HOLD_PENDING_CONTROLLER_DIRECT_REVIEW",
 "C1":"NOT_RUN","C3":"NOT_RUN","APPROVAL":False,"user_game":"OPEN_USER_INGAME_FAIL",
 "RUNTIME_VALIDATION":"UNTESTED","backend":"github-actions (GitHub-sourced pinned DDS unavailable in disconnected local sandbox)",
 "excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B320_MACHINE_QA.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n")
print("B320 TRIAL",sha(data),"font px",px,"glyph",glyph.size,"source",(r-l,b-t),"visuals",len(views))
