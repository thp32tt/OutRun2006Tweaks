#!/usr/bin/env python3
"""C315 C2 EVEN q060: lossless exact-DDS evidence for NEW P0 in-game IGR-044.
No PASS approval, no user game closure, no shared queue mutations.
"""
import os,io,json,hashlib,urllib.request,struct,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="C"
ROOT=Path.cwd()
INDEX=60
ASSET="textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
OUT=ROOT/"localization/graphics/role_C/20261009-C315-C2-Q060-NEW-INGAME-P0-NATIVE"
RPT=ROOT/"localization/graphics/role_A/20261007-A167-WORKSTEAL-C251-Q060-Q212/A167_BATCH_REPORT.json"
prod=json.loads(RPT.read_text(encoding="utf-8"))["assets"]["q60"]
ES="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
EF="457f29f6e3a42b674411baae993c6660addca8e6aa4c0f3904af60ec4e0a20e2"
assert prod["source_sha256"]==ES and prod["candidate_sha256"]==EF
import csv
with (ROOT/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as file:
 row=next(r for r in csv.DictReader(file) if r["index"].lstrip("\ufeff")=="60")
assert row["path"]==ASSET and "user_ingame_20261009_rework_required" in row["artwork_status"],"q060 changed since selection"
with (ROOT/"localization/graphics/INGAME_REWORK_BACKLOG.csv").open(encoding="utf-8-sig",newline="") as file:
 igr=next(r for r in csv.DictReader(file) if r["id"].lstrip("\ufeff")=="IGR-044")
assert igr["status"]=="OPEN_USER_INGAME_FAIL" and igr["queue_index"]=="60"
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
H=lambda bs: hashlib.sha256(bs).hexdigest()
rawsource=urllib.request.urlopen(source_url,timeout=180).read()
rawfinal=(ROOT/"localization/graphics/hd_candidates"/ASSET).read_bytes()
assert H(rawsource)==ES,(H(rawsource),ES)
assert H(rawfinal)==EF,(H(rawfinal),EF)
assert rawsource[:4]==rawfinal[:4]==b"DDS "
w,h=struct.unpack_from("<II",rawsource,16)[0],struct.unpack_from("<I",rawsource,12)[0]
assert (w,h)==(4096,2048), (w,h)
assert rawsource[:128]==rawfinal[:128],"DDS header changed"
assert struct.unpack_from("<I",rawsource,28)[0] in (0,1)
def decoded(raw):
 image=Image.open(io.BytesIO(raw)).convert("RGBA")
 assert image.size==(4096,2048)
 return image
SRAW=decoded(rawsource)
FRAW=decoded(rawfinal)
SRC=SRAW.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
FIN=FRAW.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
OUT.mkdir(parents=True,exist_ok=True)
manifest=[]
def write(im,name):
 p=OUT/name; im.save(p,"PNG"); manifest.append({"path":str(p.relative_to(ROOT)),"sha256":H(p.read_bytes()),"size":p.stat().st_size})
 return name
def opaque(img,color):
 b=Image.new("RGBA",img.size,(*color,255));b.alpha_composite(img)
 return b.convert("RGB")
regions=[]
for row in prod["rows"]:
 k=row["key"];l,t,r,b=row["source_bbox"]
 assert 0<=l<r<=4096 and 0<=t<b<=2048
 box=(max(0,l-8),max(0,t-8),min(4096,r+8),min(2048,b+8))
 sa=SRC.crop(box);fa=FIN.crop(box)
 write(sa,k+"_SOURCE_NATIVE_RGBA.png")
 write(fa,k+"_CURRENT_NATIVE_RGBA.png")
 for scale in (100,75,50):
  pair=[]
  for label,im in (("EN",sa),("KO",fa)):
   c=opaque(im,(128,128,128))
   if scale!=100:c=c.resize((max(1,round(c.width*scale/100)),max(1,round(c.height*scale/100))),Image.Resampling.LANCZOS)
   pair.append(c)
  ww=max(x.width for x in pair);hh=max(x.height for x in pair)
  sheet=Image.new("RGB",(2*ww+8,hh+23),"white");d=ImageDraw.Draw(sheet)
  d.text((1,3),"EN "+str(scale)+"%",fill="black");d.text((ww+9,3),"KO "+str(scale)+"%",fill="black")
  for i,im in enumerate(pair):sheet.paste(im,(i*(ww+8),23))
  write(sheet,k+"_SOURCE_CURRENT_"+str(scale)+"pct_GRAY.png")
 rawbox=(box[0],2048-box[3],box[2],2048-box[1])
 sr=SRAW.crop(rawbox);fr=FRAW.crop(rawbox)
 assert np.array_equal(np.asarray(sr),np.flipud(np.asarray(sa)))
 assert np.array_equal(np.asarray(fr),np.flipud(np.asarray(fa)))
 pair=Image.new("RGB",(sr.width*2+8,sr.height+23),"white"); d=ImageDraw.Draw(pair)
 d.text((1,3),"EN RAW",fill="black");d.text((sr.width+9,3),"KO RAW",fill="black")
 pair.paste(opaque(sr,(128,128,128)),(0,23))
 pair.paste(opaque(fr,(128,128,128)),(sr.width+8,23))
 write(pair,k+"_SOURCE_CURRENT_RAW.png")
 arrS=np.asarray(sa);arrF=np.asarray(fa)
 changes=np.any(arrS!=arrF,axis=2)
 margin=row["localized_bbox"];ml=[margin[0]-l,r-margin[2],margin[1]-t,b-margin[3]]
 assert min(ml)>=0
 regions.append({"region":k,"english_bbox_readable":row["source_bbox"],"producer_korean_bbox_readable":row["localized_bbox"],
 "english_width":r-l,"english_height":b-t,"korean_width":margin[2]-margin[0],"korean_height":margin[3]-margin[1],
 "positive_margins":ml,"source_current_changed_pixel_count_cropped":int(changes.sum()),
 "views":[v["path"] for v in manifest if k+"_" in v["path"]]})
out={"run":"C315-C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","index":60,
 "regression":"IGR-044","screenshot":"스크린샷(203)(1).png","priority":"P0",
 "source_sha256":ES,"candidate_sha256":EF,"source_url":source_url,
 "current_dds":"localization/graphics/hd_candidates/"+ASSET,
 "native_dds":[4096,2048],"dds_header_exact":True,"raw_orientation":"mirror_y","candidate_unchanged":True,
 "triage":"MATERIAL_REWORK: active user in-game P0, missing authored plate evidence; no producer changes",
 "regions":regions,"lossless_png_files":manifest,
 "plate_only":"NOT_AVAILABLE: authentic clean plate not SHA-bound in this C315 run; no CLEAN-only PASS",
 "composite_only":"NOT_PROVEN: candidate contains additional legacy localized regions; cannot infer clean/final whole-atlas mask from English/current alone",
 "actual_game":"OPEN_USER_INGAME_FAIL; never close on static images",
 "C":"EVIDENCE_PENDING_CONTROLLER_PIXELS_FIRST","C3":"BLOCKED","APPROVAL":False,
 "RUNTIME_VALIDATION":"UNTESTED","new_dds":0}
p=OUT/"C315_Q060_MACHINE_AND_LOSSLESS_MANIFEST.json"
p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"job":"C315_C2_Q060","index":60,"source_sha256":ES,"current_sha256":EF,"png":len(manifest),
 "regions":[{"k":r["region"],"bbox":r["english_bbox_readable"],"margins":r["positive_margins"]} for r in regions],
 "role":"C2","result":"EVIDENCE_ONLY_NOT_PASS"},ensure_ascii=False),flush=True)
