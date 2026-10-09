#!/usr/bin/env python3
"""B306: C324-rejected q205 P0 red headings, reconstruct as native heavy BLOCK SANS.

Only OPTIONS and RANKINGS source glyph areas. The source is massive rectilinear
red sans, never tapered CJK serif; no source-alpha residue or opaque box.
A produced candidate is B self-QA only; independent C1/C3/user game still open.
"""
import csv,hashlib,io,json,os,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds"
D=G/"role_B/20261009-B306-Q205-P0-SOURCE-BLOCK-SANS";D.mkdir(parents=True,exist_ok=True)
digest=lambda v:hashlib.sha256(v).hexdigest()
SRC="58a75fe75b5672169dcc2ed1f9993d462d80b700d4e12dad453b70f2ab701a5f"
PREVIOUS="fba4037f93f825a51834c306e8a4821791ce1ed72fc2f4304e74fd732a1891ae"
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","205","--require-safe-rerender"],capture_output=True,text=True,check=True)
assert json.loads(tri.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK"
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:row=next(r for r in csv.DictReader(f) if r["index"].lstrip("\ufeff")=="205")
assert "rework_required" in row["artwork_status"],row["artwork_status"]
with (G/"INGAME_REWORK_BACKLOG.csv").open(encoding="utf-8-sig",newline="") as f:backlog=list(csv.DictReader(f))
assert all(any(r["id"]==item and r["status"]=="OPEN_USER_INGAME_FAIL" for r in backlog) for item in ("IGR-026","IGR-027"))
old=(G/"hd_candidates"/REL).read_bytes()
assert digest(old)==PREVIOUS, "concurrent q205 candidate changed: abort rather than overwrite"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds"
with urllib.request.urlopen(url,timeout=140) as r:source=r.read()
assert digest(source)==SRC and source[:128]==old[:128]
assert len(source)==len(old)==128+4096*2048*4
def decode(b):
 a=np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
 assert a.shape==(2048,4096,4)
 return a
S=decode(source);P=decode(old)
base=G/"role_A/20261006-A-PRODUCTION76-ACF"
report=json.loads((base/"A76_ACF61D7C_REPORT.json").read_text())
assert report["source_provenance"]["source_sha256"]==SRC
C=np.array(Image.open(base/"A76_ACF_CLEAN_PLATE.png").convert("RGBA"),dtype=np.uint8)
assert C.shape==S.shape
rows=[r for r in report["rows"] if r["key"] in ("options","rankings")]
assert len(rows)==2 and all(r["kind"]=="red_heading" for r in rows)
allmask=np.zeros((2048,4096),bool)
for r in report["rows"]:
 l,t,rr,b=r["original_bbox"];allmask[t:b,l:rr]=True
assert not np.any(np.any(C!=S,axis=2)&~allmask),"CLEAN not source-correct outside source text regions"
fontpath="/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
if not Path(fontpath).is_file():
 subprocess.run(["sudo","apt-get","update","-qq"],check=True)
 subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
assert Path(fontpath).is_file(),"native Black block-sans unavailable"
output=P.copy()
allowed=np.zeros((2048,4096),bool)
records=[]
# Explicit text, no previous bitmap reuse; source-heavy sans only.
for r in rows:
 key,ko=r["key"],r["korean"];l,t,rr,b=r["original_bbox"]
 assert (key,ko) in (("options","옵션"),("rankings","랭킹"))
 tile=S[t:b,l:rr].copy()
 face=tile[(tile[:,:,3]>=230)&(tile[:,:,0]>120)&(tile[:,:,1]<60)]
 assert len(face)>15000,("source true red fill missing",key)
 median=np.median(face,axis=0).round().astype(int).tolist()
 assert median[:3]==[186,0,0],("wrong source red family",key,median)
 assert not np.any(C[t:b,l:rr,3]),("source glyph residue under text",key)
 allowed[t:b,l:rr]=True
 # Compare English source height and derive native Hangul max target height;
 # render at DDS resolution, no scaling, shear, serif or fake stroke.
 original_h=b-t
 chosen=None
 for px in range(182,90,-1):
  font=ImageFont.truetype(fontpath,px,index=1)
  bb=font.getbbox(ko)
  im=Image.new("RGBA",(bb[2]-bb[0]+16,bb[3]-bb[1]+16),(0,0,0,0))
  ImageDraw.Draw(im).text((8-bb[0],8-bb[1]),ko,font=font,fill=tuple(median))
  ink=im.getchannel("A").getbbox()
  if not ink:continue
  glyph=im.crop(ink)
  if glyph.width<=rr-l-12 and glyph.height<=original_h-12 and glyph.height>=int(0.83*original_h):
   chosen=(px,glyph);break
 assert chosen is not None,("cannot produce near-source-height block sans",key)
 px,glyph=chosen
 x=l+6;y=t+(original_h-glyph.height)//2
 assert x-l>=5 and rr-x-glyph.width>=5 and y-t>=5 and b-y-glyph.height>=5
 output[t:b,l:rr]=C[t:b,l:rr]
 assert not np.any(output[y:y+glyph.height,x:x+glyph.width,3])
 output[y:y+glyph.height,x:x+glyph.width]=np.asarray(glyph,np.uint8)
 records.append({"key":key,"source":r["source"],"korean":ko,
                 "source_bbox":[l,t,rr,b],"final_bbox":[x,y,x+glyph.width,y+glyph.height],
                 "positive_margins_px":[x-l,rr-x-glyph.width,y-t,b-y-glyph.height],
                 "source_red_rgba":median,"font":"NotoSansCJK Black native CJK sans",
                 "native_font_size":px,"serif":False,"scale":1.0,"slope":0,
                 "original_source_height":original_h,"new_height":glyph.height,
                 "source_alpha_pixels":int(np.count_nonzero(tile[:,:,3]>16))})
# Verify untouched all other physical localization and protected source textures.
changed=np.any(P!=output,axis=2)
assert int(np.count_nonzero(changed))>1000
assert not np.any(changed&~allowed),"unrelated artwork altered!"
assert not np.any((P[:,:,3]!=output[:,:,3])&~allowed)
assert np.array_equal(P[~allowed],output[~allowed])
native=np.frombuffer(source[128:],dtype=np.uint8).reshape(2048,4096,4)
if np.array_equal(native[::-1],S):
 mode="RGBA";payload=output[::-1].copy().tobytes()
else:
 assert np.array_equal(native[::-1,:,[2,1,0,3]],S),"unexpected DDS channel order"
 mode="BGRA";payload=output[::-1,:,[2,1,0,3]].copy().tobytes()
final=old[:128]+payload
assert digest(final)!=PREVIOUS and len(final)==len(old) and final[:128]==source[:128]
Ddecoded=decode(final)
assert np.array_equal(Ddecoded,output)
DDS=G/"hd_candidates"/REL
DDS.write_bytes(final)
assert digest(DDS.read_bytes())==digest(final)
def onbg(arr,bg):
 im=Image.new("RGBA",(arr.shape[1],arr.shape[0]),bg+(255,))
 im.alpha_composite(Image.fromarray(arr,"RGBA"))
 return im.convert("RGB")
views=[]
for r in rows:
 k=r["key"];l,t,rr,b=r["original_bbox"]
 imgs=[S[t:b,l:rr],C[t:b,l:rr],P[t:b,l:rr],Ddecoded[t:b,l:rr]]
 for direction in ("FLIPY","RAW"):
  tiles=[np.flipud(i).copy() for i in imgs] if direction=="RAW" else imgs
  for background,bg in (("GRAY",(128,128,128)),("WHITE",(255,255,255)),("BLACK",(0,0,0))):
   for scale in (100,75,50):
    pieces=[onbg(i,bg) for i in tiles]
    if scale!=100:
     pieces=[im.resize((max(1,round(im.width*scale/100)),max(1,round(im.height*scale/100))),Image.Resampling.LANCZOS) for im in pieces]
    sheet=Image.new("RGB",(sum(p.width for p in pieces)+12,max(p.height for p in pieces)),(128,128,128))
    x=0
    for p in pieces:sheet.paste(p,(x,0));x+=p.width+4
    filename=f"{k}_{direction}_{background}_{scale}_SOURCE_CLEAN_OLD_FINAL.png"
    sheet.save(D/filename,optimize=True);views.append(filename)
 for name,arr in [("SOURCE",S),("CLEAN",C),("PREVIOUS",P),("FINAL_SAVED",Ddecoded)]:
  Image.fromarray(arr[t:b,l:rr],"RGBA").save(D/f"{k}_{name}_NATIVE_RGBA.png",optimize=True)
 Image.fromarray(np.uint8(changed[t:b,l:rr])*255,"L").save(D/f"{k}_CHANGED_MASK.png")
machine={"role":"B","run":"B306","queue_index":205,"priority":"P0",
 "IGR":["IGR-026","IGR-027"],"canonical_source_sha256":SRC,
 "previous_candidate_sha256":PREVIOUS,"new_candidate_sha256":digest(final),
 "new_dds":1,"promoted_dds":1,"source_vs_clean_outside_source_union":0,
 "source_clean_alpha_selected":"ZERO_BOTH","changed_rgba_outside_two_bboxes":0,
 "changed_alpha_outside_two_bboxes":0,"other_atlas_bytes":"PIXEL_EXACT",
 "persisted_dds_roundtrip":"EXACT","header_byte_exact":True,
 "native_dimensions":[4096,2048],"format":mode,"mips":1,"raw_orientation":"mirror_y",
 "method":"Native heavy block sans directly at source resolution, original measured red; replaces independently rejected tapered NotoSerif Black",
 "regions":records,"lossless_proof_files":views,
 "producer_visual":"PENDING_DIRECT_REVIEW_NATIVE_75_50_RAW",
 "C1":"NOT_RUN","C3":"NOT_RUN","USER_GAME":"OPEN",
 "RUNTIME_VALIDATION":"UNTESTED","backend":"github-actions",
 "excluded":["VR","FFB","DX11","DXVK"]}
(D/"B306_MACHINE_QA.json").write_text(json.dumps(machine,ensure_ascii=False,indent=2)+"\n")
print("B306_NATIVE_DDS",json.dumps({"new_sha":digest(final),"prior":PREVIOUS,"source":SRC,"records":records,"changed_rgba_px":int(changed.sum()),"views":len(views)},ensure_ascii=False),flush=True)
