#!/usr/bin/env python3
"""B302 B-even q236: genuinely native 2048px Black glyph reconstruction.
Trial-first: do not promote without independent controller SOURCE/CLEAN/PREV/TRIAL review.
"""
import csv,hashlib,io,json,os,struct,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
ASSET="textures/load/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds"
DIR=G/"role_B/20261009-B302-Q236-NATIVE-BLACK-FAMILY-RECONSTRUCTION"
DIR.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
CUR="e0a01c50df1aefb2a174dc318a1f6a041f0cf3b2759fff8fcafba7d134ec44c8"
SRC="a1c7f7d6ca5d2440076e49477cefecbf5084b4188072f3427ff13e5da24bc518"
CLEAN="c202f55e0de29e98d48e182f50cff8a94bcaa32bafc14c884644868db6552af7"
TRI=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","236","--require-safe-rerender"],capture_output=True,text=True,check=True)
assert json.loads(TRI.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK",TRI.stdout
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 q=next(x for x in csv.DictReader(f) if x["index"].lstrip("\ufeff")=="236")
assert q["artwork_status"]=="c313_c2_rework_required_q236_source_display_weight",q["artwork_status"]
candidate=(G/"hd_candidates"/ASSET).read_bytes()
assert sha(candidate)==CUR,("stale q236 candidate",sha(candidate))
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds"
with urllib.request.urlopen(url,timeout=150) as response:src=response.read()
assert sha(src)==SRC and src[:128]==candidate[:128]
clean_path=G/"role_B/20261005-B-PRODUCTION80/FEF_CLEAN_PLATE.png"
assert sha(clean_path.read_bytes())==CLEAN
fontpath="/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
assert Path(fontpath).exists(),fontpath
def decoded(b):
 x=Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 assert x.size==(2048,2048)
 return np.array(x,dtype=np.uint8)
S=decoded(src);P=decoded(candidate)
C=np.asarray(Image.open(clean_path).convert("RGBA"),dtype=np.uint8)
assert S.shape==P.shape==C.shape==(2048,2048,4)
# Exact C308 region metadata comes from a previous independent C pixel review.
proof=json.loads((G/"role_C/20261008-C308-C2-Q236-PLATE-COMPOSITE-14REGION/C308_Q236_14REGION_NATIVE_MACHINE.json").read_text())
assert proof["exact_sha256"]["source"]==SRC and proof["exact_sha256"]["candidate"]==CUR
assert proof["exact_sha256"]["authored_clean"]==CLEAN
rows=proof["regions"]
assert len(rows)==14
allowed=np.zeros((2048,2048),dtype=bool)
for r in rows:
 x0,y0,x1,y1=r["source_bbox"];allowed[y0:y1,x0:x1]=True
assert not np.any(np.any(S!=C,axis=2)&~allowed),"plate changes outside all source boxes"
assert not np.any(np.any(P!=C,axis=2)&~allowed),"candidate changes outside all source boxes"
for r in rows:
 x0,y0,x1,y1=r["source_bbox"]
 assert np.max(C[y0:y1,x0:x1,3])==0,("CLEAN plate not alpha-free",r["index"])
# Render native glyph masks at actual 2048px DDS size rather than B80's
# 18px glyphs x4 upscaling. The heavy Korean Black font is an actual face,
# not dilated C glyph or synthesized horizontal stripes.
OUT=C.copy()
info=[]
for row in rows:
 idx=int(row["index"]);l,t,rr,bb=map(int,row["source_bbox"])
 text=row["korean_text"]
 maxw=rr-l-8;maxh=bb-t-8
 im=None;used=None
 for fs in range(118,64,-1):
  font=ImageFont.truetype(fontpath,fs,index=1)
  bbox=font.getbbox(text)
  buf=Image.new("RGBA",(bbox[2]-bbox[0]+10,bbox[3]-bbox[1]+10),(0,0,0,0))
  ImageDraw.Draw(buf).text((5-bbox[0],5-bbox[1]),text,font=font,fill=(46,53,57,255))
  tight=buf.getchannel("A").getbbox()
  if not tight:raise AssertionError(("missing glyph",idx,text))
  crop=buf.crop(tight)
  if crop.width<=maxw and crop.height<=maxh:
   im=crop;used=fs;break
 assert im is not None,("not fitting source bbox",idx,text)
 x=rr-4-im.width;y=t+(bb-t-im.height)//2
 assert x>l and y>t and x+im.width<rr and y+im.height<bb,(idx,im.size,x,y)
 # Only glyph-mask compositing over transparent independently vetted clean plate.
 alpha=np.asarray(im.getchannel("A"))
 assert alpha.min()==0 or np.count_nonzero(alpha)>100
 assert np.max(OUT[y:y+im.height,x:x+im.width,3])==0
 OUT[y:y+im.height,x:x+im.width,:]=np.asarray(im)
 srw=rr-l;srh=bb-t
 info.append({"row":idx,"english":row["source_text"],"korean":text,
              "original_bbox":[l,t,rr,bb],"new_bbox":[x,y,x+im.width,y+im.height],
              "margins":[x-l,rr-x-im.width,y-t,bb-y-im.height],
              "font_native_size":used,"pixel_scale":1,"new_wh":[im.width,im.height],
              "source_wh":[srw,srh],"height_ratio":round(im.height/srh,4)})
# Encode exact original 32-bit BGRA byte layout, one mip, vertically mirrored RAW.
assert len(candidate)==128+2048*2048*4
assert struct.unpack_from("<I",candidate,28)[0]==1
raw=OUT[::-1].copy().tobytes("raw","BGRA")
trial=candidate[:128]+raw
assert sha(trial)!=CUR and trial[:128]==candidate[:128]
D=decoded(trial)
assert np.array_equal(D,OUT),"persisted BGRA/raw channel check"
diff=np.any(P!=D,axis=2)
assert int(np.count_nonzero(diff&~allowed))==0
assert int(np.count_nonzero((P[:,:,3]!=D[:,:,3])&~allowed))==0
assert int(np.count_nonzero((S!=D).any(axis=2)&~allowed))==0
assert int(np.count_nonzero((C!=D).any(axis=2)&~allowed))==0
assert int(np.count_nonzero(D[:,:,3]&~allowed))==int(np.count_nonzero(P[:,:,3]&~allowed))
for e in info:assert min(e["margins"])>=3,e
# Exact full source image against unchanged protected 'REVERSED' pixels is captured by outside.
outpath=DIR/"Q236_B302_NATIVE_TRIAL_NOT_PROMOTED.dds";outpath.write_bytes(trial)
assert sha(outpath.read_bytes())==sha(trial) and np.array_equal(decoded(outpath.read_bytes()),D)
def composite(arr,bg):
 z=Image.new("RGBA",(arr.shape[1],arr.shape[0]),bg)
 z.alpha_composite(Image.fromarray(arr,"RGBA"))
 return z.convert("RGB")
png_names=[]
for row in rows:
 i=int(row["index"]);l,t,r,b=map(int,row["source_bbox"])
 region=(slice(t,b),slice(l,r))
 for orientation in ("READABLE","RAW"):
  values=[S[region],C[region],P[region],D[region]]
  if orientation=="RAW":values=[np.flipud(x).copy() for x in values]
  for bgname,bg in [("GRAY",(128,128,128,255)),("WHITE",(255,255,255,255)),("BLACK",(0,0,0,255))]:
   for scale in (100,75,50):
    pieces=[composite(z,bg) for z in values]
    if scale!=100:
     pieces=[x.resize((max(1,round(x.width*scale/100)),max(1,round(x.height*scale/100))),Image.Resampling.LANCZOS) for x in pieces]
    canvas=Image.new("RGB",(sum(z.width for z in pieces)+12,max(z.height for z in pieces)),(128,128,128))
    px=0
    for z in pieces:canvas.paste(z,(px,0));px+=z.width+4
    fname=f"row{i:02}_{orientation}_{bgname}_{scale}_SOURCE_CLEAN_PREV_TRIAL.png"
    canvas.save(DIR/fname,optimize=True);png_names.append(fname)
for name,arr in [("SOURCE",S),("CLEAN",C),("PRIOR",P),("TRIAL",D)]:
 img=Image.fromarray(arr,"RGBA")
 img.save(DIR/f"{name}_FULL_ATLAS_DECODED.png")
meta={"role":"B","run":"B302","queue_index":236,"method":"independent 2048px native NotoSansCJK Black mask rebuilt from verified B80 CLEAN and C308 SHA-pinned source, no 4x lowres upscale, no dilation or box overlay","triage":"MATERIAL_REWORK","source_sha256":SRC,"clean_sha256":CLEAN,"prior_sha256":CUR,"trial_sha256":sha(trial),"new_trial_dds":1,"promoted_dds":0,"dds_native":[2048,2048],"dds_pixel_format":"BGRA32","mips":1,"raw":"FLIPY","glyphs":info,"changed_rgba_outside_14_source_bboxes":0,"changed_alpha_outside_14_source_bboxes":0,"protected_graphics_unchanged":True,"authored_clean_source_residue_alpha_14":0,"persisted_header_exact":True,"persisted_dds_roundtrip_exact":True,"evidence_png":len(png_names)+4,"controller_visual":"PENDING","C2":"NOT_RUN","C3":"NOT_RUN","USER_GAME":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED","excluded":["VR","FFB","DX11","DXVK"]}
(DIR/"B302_MACHINE_QA.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n")
print("B302_TRIAL_OK",json.dumps({"sha":sha(trial),"native":len(info),"changed_pixels":int(diff.sum()),"png":len(png_names)+4,"min_margins":min(min(x["margins"]) for x in info)},ensure_ascii=False),flush=True)
