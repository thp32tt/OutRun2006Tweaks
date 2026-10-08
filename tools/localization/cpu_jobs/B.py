#!/usr/bin/env python3
"""B303 q205: SHA-pinned original red-heading source-family rework, 2 P0 cells.

A material production trial, not a C/user/game approval. Rebuild only OPTIONS
and RANKINGS from the A76 independently clean native image, never upscale old
low-resolution glyphs. Keep all other A76/B240 cells pixel exact.
"""
import csv,hashlib,io,json,os,struct,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds"
DIR=G/"role_B/20261009-B303-Q205-P0-RED-HEADING-NATIVE-FAMILY"
DIR.mkdir(parents=True,exist_ok=True)
SHA=lambda b:hashlib.sha256(b).hexdigest()
SOURCE="58a75fe75b5672169dcc2ed1f9993d462d80b700d4e12dad453b70f2ab701a5f"
EXPECTED_PREVIOUS=["e3d421a165bdb6e7b3e1bda7b35a6d994d69017407e345d7a339a15d87f79088",
                   "2bbb9d19a833fb6c9ade243eb70132ef5ce46150d1fa1cb9423ff4e5101b770c"]
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","205","--require-safe-rerender"],capture_output=True,text=True,check=True)
assert json.loads(tri.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK",tri.stdout
with (G/"asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(x for x in csv.DictReader(f) if x["index"].lstrip("\ufeff")=="205")
assert row["artwork_status"]=="user_ingame_20261009_rework_required"
with (G/"INGAME_REWORK_BACKLOG.csv").open(encoding="utf-8-sig",newline="") as f:
 backlog=list(csv.DictReader(f))
assert all(any(z["id"]==k and z["status"]=="OPEN_USER_INGAME_FAIL" for z in backlog) for k in ["IGR-026","IGR-027"])
old=(G/"hd_candidates"/REL).read_bytes()
oldsha=SHA(old)
assert oldsha in EXPECTED_PREVIOUS,("q205 concurrent modified",oldsha)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/ACF61D7C_1024x512.dds"
with urllib.request.urlopen(url,timeout=160) as resp:sourceBytes=resp.read()
assert SHA(sourceBytes)==SOURCE
assert old[:128]==sourceBytes[:128] and len(old)==128+4096*2048*4
A=G/"role_A/20261006-A-PRODUCTION76-ACF"
manifest=json.loads((A/"A76_ACF61D7C_REPORT.json").read_text())
assert manifest["source_provenance"]["source_sha256"]==SOURCE
assert manifest["structure"]["dimensions"]==[4096,2048]
def dec(v):
 a=np.asarray(Image.open(io.BytesIO(v)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
 assert a.shape==(2048,4096,4)
 return a
S=dec(sourceBytes);P=dec(old)
C=np.asarray(Image.open(A/"A76_ACF_CLEAN_PLATE.png").convert("RGBA"),dtype=np.uint8)
assert C.shape==S.shape
rows=[r for r in manifest["rows"] if r["key"] in ("options","rankings")]
assert len(rows)==2 and all(r["kind"]=="red_heading" for r in rows)
boxes={r["key"]:tuple(r["original_bbox"]) for r in rows}
allowed=np.zeros((2048,4096),dtype=bool)
for r in rows:
 l,t,rr,b=boxes[r["key"]];allowed[t:b,l:rr]=True
 assert int(np.max(C[t:b,l:rr,3]))==0,("non-clean sprite plate",r["key"])
 assert np.count_nonzero(S[t:b,l:rr,3])>500
 assert r["source_median_rgba"][:3]==[186,0,0]
# Verify the A76 CLEAN plate preserves every pixel outside ALL edited source
# boxes (not just these two), as legacy candidate contains other modifications.
globalmask=np.zeros((2048,4096),dtype=bool)
for r in manifest["rows"]:
 l,t,rr,b=r["original_bbox"];globalmask[t:b,l:rr]=True
assert not np.any(np.any(C!=S,axis=2)&~globalmask),"CLEAN outside atlas source regions"
# Old candidate outside two P0 cells remains byte-exact; source CLEAN is only
# transplanted for the two selected cells so no old unrelated text is erased.
OUT=P.copy()
for r in rows:
 l,t,rr,b=boxes[r["key"]]
 OUT[t:b,l:rr]=C[t:b,l:rr]
# Profile source red face, dark ink contour and native italic slope before
# composing. The original red material, not gray or arbitrary boxed artwork.
family={}
for r in rows:
 name=r["key"];l,t,rr,b=boxes[name]
 tile=S[t:b,l:rr];alpha=tile[:,:,3]
 rgb=tile[:,:,:3];face=rgb[(alpha>=220)&(rgb[:,:,0]>120)&(rgb[:,:,1]<85)]
 # Original source may have red-only face RGB with antialias represented
 # by alpha rather than a separately authored black/dark RGB contour.
 # Do not invent a dark border when the source contains no such pixels.
 black=rgb[(alpha>=100)&(rgb[:,:,0]<65)&(rgb[:,:,1]<70)&(rgb[:,:,2]<80)]
 assert face.shape[0]>200,("missing original red face",name,len(face))
 faceRGB=np.median(face,axis=0).round().astype(int).tolist()
 darkRGB=np.percentile(black,25,axis=0).round().astype(int).tolist() if len(black)>50 else None
 # Original source alpha centroid shifts to right/left near top/bottom.
 y,x=np.where(alpha>130)
 top=x[y<=np.percentile(y,30)];bot=x[y>=np.percentile(y,70)]
 shift=float(np.median(top)-np.median(bot))
 family[name]={"face_rgb":faceRGB,"dark_rgb":darkRGB,"native_slope_px":round(shift,2),"original_bbox":[l,t,rr,b],
               "source_alpha_pixels":int((alpha>16).sum())}
font_candidates=[
 "/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc",
 "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"]
if not any(Path(p).exists() for p in font_candidates):
 subprocess.run(["sudo","apt-get","update","-qq"],check=True)
 subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk-extra"],check=True)
fontpath=next((p for p in font_candidates if Path(p).exists()),None)
assert fontpath,"native source-family heavy serif font unavailable"
records=[]
for r in rows:
 name=r["key"];ko=r["korean"];l,t,rr,b=boxes[name];f=family[name]
 maxw=rr-l-10;maxh=b-t-10
 chosen=None
 # Noto Serif CJK Black native at source ink height. Do not create lower-res
 # Korean and stretch it, and never force words to English width.
 for size in range(166,85,-1):
  font=ImageFont.truetype(fontpath,size,index=1)
  bbox=font.getbbox(ko,stroke_width=3)
  tmp=Image.new("RGBA",(bbox[2]-bbox[0]+14,bbox[3]-bbox[1]+14),(0,0,0,0))
  draw=ImageDraw.Draw(tmp)
  draw.text((7-bbox[0],7-bbox[1]),ko,font=font,
            fill=(*f["face_rgb"],255),stroke_width=(3 if f["dark_rgb"] else 0),
            stroke_fill=(*f["dark_rgb"],255) if f["dark_rgb"] else None)
  bb=tmp.getchannel("A").getbbox()
  if bb:
   tile=tmp.crop(bb)
   if tile.width<=maxw and tile.height<=maxh:chosen=(tile,size);break
 assert chosen is not None,("font does not fit original source bbox",name)
 im,size=chosen
 x=l+5;y=t+(b-t-im.height)//2
 assert x>l and x+im.width<rr and y>t and y+im.height<b
 patch=np.asarray(im,dtype=np.uint8)
 assert np.max(OUT[y:y+im.height,x:x+im.width,3])==0
 OUT[y:y+im.height,x:x+im.width]=patch
 records.append({"key":name,"source_text":r["source"],"korean":ko,
                 "original_bbox":[l,t,rr,b],"candidate_bbox":[x,y,x+im.width,y+im.height],
                 "margins":[x-l,rr-x-im.width,y-t,b-y-im.height],
                 "face":f["face_rgb"],"edge":f["dark_rgb"],"font_size":size,
                 "font_file":Path(fontpath).name,"rendering":"native_transparent_rgba_serif_black_source_red_face; dark_keyline_only_if_measured"})
assert all(min(r["margins"])>=2 for r in records)
# Serialize in the same native channel order proven by the source DDS.
# Determine this empirically instead of assuming DDS header RGB masks.
raw_source=np.frombuffer(sourceBytes[128:],dtype=np.uint8).reshape(2048,4096,4)
as_rgba=raw_source[::-1]
if np.array_equal(as_rgba,S):mode="RGBA";encoded=OUT[::-1].copy().tobytes()
else:
 as_bgra=as_rgba[:,:,[2,1,0,3]]
 assert np.array_equal(as_bgra,S),"unknown native 32-bit DDS layout"
 mode="BGRA";encoded=Image.fromarray(OUT[::-1].copy(),"RGBA").tobytes("raw","BGRA")
trial=old[:128]+encoded
assert trial[:128]==old[:128] and len(trial)==len(old) and SHA(trial)!=oldsha
D=dec(trial)
assert np.array_equal(D,OUT),"saved DDS decode differs from authored RGBA"
changed=np.any(P!=D,axis=2);alphaChanged=P[:,:,3]!=D[:,:,3]
assert not np.any(changed&~allowed)
assert not np.any(alphaChanged&~allowed)
# A76 plate-only and composite-only evaluated independently, never cover source
# residual glyphs behind Korean or count a flat edit rect as a game artefact.
for r in rows:
 l,t,rr,b=boxes[r["key"]]
 assert not np.any(C[t:b,l:rr,3]),r["key"]
 assert np.any(D[t:b,l:rr,3]),r["key"]
assert np.array_equal(P[~allowed],D[~allowed])
file=DIR/"Q205_B303_P0_RED_HEADING_TRIAL_NOT_PROMOTED.dds"
file.write_bytes(trial)
assert SHA(file.read_bytes())==SHA(trial) and np.array_equal(dec(file.read_bytes()),D)
def on_bg(arr,bg):
 p=Image.new("RGBA",(arr.shape[1],arr.shape[0]),bg)
 p.alpha_composite(Image.fromarray(arr,"RGBA"))
 return p.convert("RGB")
views=[]
for name in ("rankings","options"):
 l,t,rr,b=boxes[name];s=(slice(t,b),slice(l,rr))
 for orientation in ("READABLE","RAW"):
  imgs=[S[s],C[s],P[s],D[s]]
  if orientation=="RAW":imgs=[np.flipud(a).copy() for a in imgs]
  for bgname,bg in [("GRAY",(128,128,128,255)),("WHITE",(255,255,255,255)),("BLACK",(0,0,0,255))]:
   for pct in (100,75,50):
    chunks=[on_bg(z,bg) for z in imgs]
    if pct!=100:chunks=[z.resize((round(z.width*pct/100),round(z.height*pct/100)),Image.Resampling.LANCZOS) for z in chunks]
    out=Image.new("RGB",(sum(z.width for z in chunks)+12,max(z.height for z in chunks)),(128,128,128))
    p=0
    for z in chunks:out.paste(z,(p,0));p+=z.width+4
    filename=f"{name}_{orientation}_{bgname}_{pct}_SOURCE_CLEAN_OLD_TRIAL.png"
    out.save(DIR/filename,optimize=True)
    views.append(filename)
for name,img in [("SOURCE",S),("CLEAN",C),("OLD",P),("TRIAL",D)]:
 Image.fromarray(img,"RGBA").save(DIR/f"{name}_FULL_ATLAS.png",optimize=True)
report={"role":"B","run":"B303","queue_index":205,"work":"IGR-026+IGR-027 P0 original red heading materially rebuilt",
 "source_sha256":SOURCE,"old_sha256":oldsha,"trial_sha256":SHA(trial),
 "new_trial_dds":1,"promoted_dds":0,"dds_size":[4096,2048],"dds_mode":mode,"mips":1,"raw_orientation":"mirror_y",
 "font":"NotoSerifCJK Black native RGBA; red original face and dark contour only when source RGB proves it",
 "source_family":family,"regions":records,
 "saved_dds_roundtrip":"EXACT","saved_dds_header":"EXACT","outside_two_source_bbox_rgba_changed_pixels":0,
 "outside_two_source_bbox_alpha_changed_pixels":0,"all_other_regions":"PIXEL_EXACT",
 "source_clean_outside_A76_union":"PASS_ZERO","source_clean_alpha_selected":"PASS_ZERO",
 "preview_png_count":len(views)+4,
 "preview_files":views,"producer_visual":"PENDING_DIRECT_NATIVE_50_RAW",
 "C2":"NOT_RUN","C3":"NOT_RUN","user_game":"OPEN_UNTESTED","RUNTIME_VALIDATION":"UNTESTED",
 "backend":"GITHUB_ACTIONS","excluded":["VR","FFB","DX11","DXVK"]}
(DIR/"B303_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print("B303_TRIAL_OK",json.dumps({"sha":SHA(trial),"old":oldsha,"mode":mode,"pixels":int(changed.sum()),"records":records},ensure_ascii=False),flush=True)
