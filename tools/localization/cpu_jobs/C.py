#!/usr/bin/env python3
"""C317 C2 EVEN q228: exact DDS 13-row lossless source/current evidence for NEW IGR-038.
Do not confer independent PASS, C3 approval or game acceptance.
"""
import os,io,json,hashlib,urllib.request,struct,csv
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions"
assert os.getenv("OUTRUN_CPU_ROLE")=="C"
ROOT=Path.cwd()
ASSET="textures/load/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds"
SRC_SHA="3f98c940c51d2f054934d4e0b7c7d9745f9f8ad71d68548b0b336c62c1cf5154"
FIN_SHA="28e814599105600eb0222eb1ffe0057dc1e108520580a958ae3b3b7ec08f2808"
DIR=ROOT/"localization/graphics/role_C/20261009-C317-C2-Q228-IGR038-NATIVE-SOURCE-FAMILY"
PREV=ROOT/"localization/graphics/role_C/20261008-C258-C2-Q198-Q226_Q228/C258_Q228_MACHINE_QA.json"
PREV=ROOT/"localization/graphics/role_C/20261008-C258-C2-Q198-Q226-Q228/C258_Q228_MACHINE_QA.json"
H=lambda bs:hashlib.sha256(bs).hexdigest()
with (ROOT/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(z for z in csv.DictReader(f) if z["index"].lstrip("\ufeff")=="228")
assert row["path"]==ASSET and row["artwork_status"]=="user_ingame_20261009_rework_required",row["artwork_status"]
with (ROOT/"localization/graphics/INGAME_REWORK_BACKLOG.csv").open(encoding="utf-8-sig",newline="") as f:
 igr=next(z for z in csv.DictReader(f) if z["id"]=="IGR-038")
assert igr["status"]=="OPEN_USER_INGAME_FAIL" and igr["queue_index"]=="228"
prev=json.loads(PREV.read_text(encoding="utf-8"))
assert prev["source_sha256"]==SRC_SHA and prev["candidate_sha256"]==FIN_SHA
assert len(prev["rows"])==13
uri="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/E7F6E9B7_512x512.dds"
s=urllib.request.urlopen(uri,timeout=180).read()
f=(ROOT/"localization/graphics/hd_candidates"/ASSET).read_bytes()
assert H(s)==SRC_SHA,("source",H(s))
assert H(f)==FIN_SHA,("candidate",H(f))
assert s[:128]==f[:128] and s[:4]==b"DDS "
assert struct.unpack_from("<II",s,12)==(2048,2048)
def decode(raw):
 im=Image.open(io.BytesIO(raw)).convert("RGBA")
 assert im.size==(2048,2048)
 return im
sraw,fraw=decode(s),decode(f)
S,F=sraw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),fraw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa,fa=np.asarray(S),np.asarray(F)
union=np.zeros((2048,2048),dtype=bool)
for row in prev["rows"]:
 l,t,r,b=row["source_bbox"]
 assert 0<=l<r<=2048 and 0<=t<b<=2048
 union[t:b,l:r]=True
mask=np.any(sa!=fa,axis=2)
outside=int(np.count_nonzero(mask &~union))
outside_alpha=int(np.count_nonzero((sa[:,:,3]!=fa[:,:,3])&~union))
assert outside==outside_alpha==0,(outside,outside_alpha)
DIR.mkdir(parents=True,exist_ok=True)
manifest=[]
def save(img,name):
 path=DIR/name;img.save(path,"PNG")
 manifest.append({"path":str(path.relative_to(ROOT)),"sha256":H(path.read_bytes()),"bytes":path.stat().st_size})
 return name
def composite(img,color):
 bg=Image.new("RGBA",img.size,(*color,255));bg.alpha_composite(img);return bg.convert("RGB")
def joined(left,right,scale,color,mode):
 a,b=composite(left,color),composite(right,color)
 if scale!=100:
  dims=(max(1,round(a.width*scale/100)),max(1,round(a.height*scale/100)))
  a=a.resize(dims,Image.Resampling.LANCZOS);b=b.resize(dims,Image.Resampling.LANCZOS)
 out=Image.new("RGB",(a.width+b.width+8,max(a.height,b.height)+24),(255,255,255))
 d=ImageDraw.Draw(out);d.text((2,3),"EN "+mode,fill=(0,0,0));d.text((a.width+10,3),"KO "+mode,fill=(0,0,0))
 out.paste(a,(0,24));out.paste(b,(a.width+8,24))
 return out
rows=[]
for i,row in enumerate(prev["rows"]):
 l,t,r,b=row["source_bbox"];pad=6
 box=(max(l-pad,0),max(t-pad,0),min(r+pad,2048),min(b+pad,2048))
 ss,ff=S.crop(box),F.crop(box)
 stem=f"{i:02d}_{row['key'].replace(' ','_')}"
 files=[]
 for suffix,img in (("SOURCE_RGBA",ss),("CURRENT_RGBA",ff)):
  files.append(save(img,stem+"_"+suffix+".png"))
 for scale in (100,75,50):
  files.append(save(joined(ss,ff,scale,(128,128,128),str(scale)+"pct"),stem+f"_GRAY_{scale}pct.png"))
 files.append(save(joined(ss,ff,100,(245,245,245),"WHITE_NATIVE"),stem+"_WHITE_NATIVE.png"))
 raw=(box[0],2048-box[3],box[2],2048-box[1])
 sr,fr=sraw.crop(raw),fraw.crop(raw)
 assert np.array_equal(np.asarray(sr),np.flipud(np.asarray(ss)))
 assert np.array_equal(np.asarray(fr),np.flipud(np.asarray(ff)))
 files.append(save(joined(sr,fr,100,(128,128,128),"RAW"),stem+"_RAW.png"))
 cl,ct,cr,cb=row["localized_bbox"]
 margins=[cl-l,r-cr,ct-t,b-cb]
 assert min(margins)>0
 rows.append({"i":i,"key":row["key"],"source_bbox":row["source_bbox"],"candidate_bbox":row["localized_bbox"],"margins":margins,"source_size":row["source_size"],"candidate_size":row["localized_size"],"files":files})
manifestfile=DIR/"C317_Q228_13ROW_NATIVE_LOSSLESS_MACHINE.json"
manifestfile.write_text(json.dumps({"schema_version":2,"run":"C317-C2","role":"C","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","index":228,
 "ingame":"IGR-038","priority":"P1","canonical_source_url":uri,"source_sha256":SRC_SHA,"candidate_sha256":FIN_SHA,
 "dimensions":[2048,2048],"dds_header_equal":True,"raw_flip_y_validated":True,
 "outside_13_original_bboxes_rgba":outside,"outside_13_original_bboxes_alpha":outside_alpha,
 "C":"EVIDENCE_ONLY_NO_PASS","C3":"BLOCKED","USER_INGAME":"OPEN_USER_INGAME_FAIL",
 "authored_clean":"NOT_AVAILABLE_IN_THIS_RUN; no plate-only PASS or CLEAN-vs-FINAL assumption",
 "current_approval":False,"RUNTIME_VALIDATION":"UNTESTED","rows":rows,"lossless_pngs":len(manifest),"manifest":manifest,
 "new_dds":0},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
assert len(manifest)==91
print("C317_C2_Q228_OK",json.dumps({"index":228,"png":len(manifest),"source_sha256":SRC_SHA,"candidate_sha256":FIN_SHA,"outside":outside,"outside_alpha":outside_alpha,"rows":len(rows)},ensure_ascii=False),flush=True)
