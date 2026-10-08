#!/usr/bin/env python3
"""C318 C2 EVEN q212 exact current DDS independent native source-family triage evidence."""
import os,io,hashlib,json,urllib.request,struct,csv
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="C"
R=Path.cwd();DIR=R/"localization/graphics/role_C/20261009-C318-C2-Q212-IGR029-UNDERFILL"
SRC="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"
FINAL="01c7aded0bbaa393351d1b191dc08cfbd24fa542160f6a60d5584abd1bc0f1e6"
ASSET="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
E=R/"localization/graphics/role_C/20261008-C264-C2-Q212-Q062-Q172/C264_BATCH_MACHINE_QA.json"
report=json.loads(E.read_text(encoding="utf-8"))["assets"][0]
assert report["queue_index"]==212 and len(report["rows"])==12
with (R/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as fh:
 q=next(x for x in csv.DictReader(fh) if x["index"].lstrip("\ufeff")=="212")
assert q["path"]==ASSET and q["artwork_status"]=="user_ingame_20261009_rework_required",q["artwork_status"]
with (R/"localization/graphics/INGAME_REWORK_BACKLOG.csv").open(encoding="utf-8-sig",newline="") as fh:
 ig=next(x for x in csv.DictReader(fh) if x["id"]=="IGR-029")
assert ig["status"]=="OPEN_USER_INGAME_FAIL" and ig["queue_index"]=="212" and "SUSPECTED" in ig["mapping_status"]
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
H=lambda b:hashlib.sha256(b).hexdigest()
src=urllib.request.urlopen(url,timeout=160).read()
fin=(R/"localization/graphics/hd_candidates"/ASSET).read_bytes()
assert H(src)==SRC and H(fin)==FINAL,(H(src),H(fin))
assert src[:128]==fin[:128] and src[:4]==b"DDS "
def dec(b):
 im=Image.open(io.BytesIO(b)).convert("RGBA")
 assert im.size==(2048,2048),im.size
 return im
sr,fr=dec(src),dec(fin)
S,F=sr.transpose(Image.Transpose.FLIP_TOP_BOTTOM),fr.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
a,b=np.asarray(S),np.asarray(F)
scope=np.zeros((2048,2048),dtype=bool)
for x in report["rows"]:
 l,t,r,bot=x["source_bbox"];scope[t:bot,l:r]=True
outside=int(np.count_nonzero(np.any(a!=b,axis=2)&~scope))
outside_alpha=int(np.count_nonzero((a[:,:,3]!=b[:,:,3])&~scope))
assert outside==0 and outside_alpha==0,(outside,outside_alpha)
DIR.mkdir(parents=True,exist_ok=True)
proof=[]
def save(im,file):
 p=DIR/file;im.save(p,"PNG")
 proof.append({"name":file,"sha256":H(p.read_bytes()),"bytes":p.stat().st_size})
def bg(im):
 x=Image.new("RGBA",im.size,(128,128,128,255));x.alpha_composite(im);return x.convert("RGB")
def comparison(left,right,scale,label):
 l,r=bg(left),bg(right)
 if scale!=100:
  dim=(max(1,round(l.width*scale/100)),max(1,round(l.height*scale/100)))
  l=l.resize(dim,Image.Resampling.LANCZOS);r=r.resize(dim,Image.Resampling.LANCZOS)
 out=Image.new("RGB",(l.width+r.width+8,l.height+23),"white");dr=ImageDraw.Draw(out)
 dr.text((2,3),"EN "+label,fill="black");dr.text((l.width+10,3),"KO "+label,fill="black")
 out.paste(l,(0,23));out.paste(r,(l.width+8,23));return out
selected=["showroom","enter_name","outrun_big","coast2coast","professional","outrun_small"]
region=[]
for row in report["rows"]:
 if row["key"] not in selected:continue
 k=row["key"];l,t,r,bot=row["source_bbox"];pad=5
 box=(max(l-pad,0),max(t-pad,0),min(r+pad,2048),min(bot+pad,2048))
 left,right=S.crop(box),F.crop(box)
 save(left,k+"_EN_NATIVE_RGBA.png");save(right,k+"_KO_NATIVE_RGBA.png")
 for scale in (100,75,50):
  save(comparison(left,right,scale,str(scale)+"pct"),k+"_EN_KO_GRAY_"+str(scale)+"pct.png")
 rawbox=(box[0],2048-box[3],box[2],2048-box[1])
 x,y=sr.crop(rawbox),fr.crop(rawbox)
 assert np.array_equal(np.asarray(x),np.flipud(np.asarray(left)))
 assert np.array_equal(np.asarray(y),np.flipud(np.asarray(right)))
 save(comparison(x,y,100,"RAW"),k+"_EN_KO_RAW.png")
 region.append({"label":k,"source":row["source"],"ko":row["korean"],"source_bbox":row["source_bbox"],
  "ko_bbox":row["derived_bbox"],"source_width":r-l,"ko_width":row["derived_bbox"][2]-row["derived_bbox"][0],
  "width_ratio":row["width_ratio"],"height_ratio":row["height_ratio"],"margins":row["margins"]})
assert len(proof)==36 and len(region)==6
manifest={"run":"C318","role":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":212,
 "user_regression":"IGR-029","mapping_status":"SUSPECTED_NOT_VERIFIED","native_size":[2048,2048],
 "source_url":url,"source_sha256":SRC,"candidate_sha256":FINAL,"header_match":True,
 "raw_flip_y_crop_parity":True,"changed_rgba_outside_12_bboxes":outside,
 "changed_alpha_outside_12_bboxes":outside_alpha,"region_count_existing":12,
 "selected_region_count":len(region),"selected_regions":region,
 "lossless_png_count":len(proof),"proof_sha_manifest":proof,
 "C":"EVIDENCE_ONLY_NOT_APPROVAL","C3":"BLOCKED_USER_FAIL",
 "source_clean":"NOT_NEWLY_EXAMINED; historical C264 contact only","user_game":"OPEN_USER_INGAME_FAIL",
 "RUNTIME_VALIDATION":"UNTESTED","new_dds":0}
(DIR/"C318_Q212_NATIVE_SOURCE_HIERARCHY_MACHINE.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C318_OK",json.dumps({"png":len(proof),"candidate":FINAL,"outside":outside,"selected":selected},ensure_ascii=False),flush=True)
