#!/usr/bin/env python3
# C247 C1 fresh independent QA batch: q43/q47/q53
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import hashlib, io, json, struct, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw

OUT=Path("localization/graphics/role_C/20261007-C247-C1-BATCH-Q043-Q047-Q053")
OUT.mkdir(parents=True,exist_ok=True)
ASSETS=[
{"index":43,"key":"455717B2","path":"localization/graphics/hd_candidates/textures/load/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds","candidate_sha":"a2b0db36e0283244037dccae5b65558a70d5b8547da245d92c840e0da3b3327c","prior_sha":"c158430f8a4f3730fa3c7067b0d20db97af8fddf6c830ddeb80e2d16820368ae","source_png":"localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_SOURCE_READABLE.png","source_bboxes":[[4,256,558,351],[113,352,1302,560],[6,560,2024,788],[44,788,1579,1026]],"localized_bboxes":[[122,261,439,346],[495,359,920,552],[493,568,1537,779],[567,796,1056,1017]],"reason":"USER PRE_INGAME #009 TEXT_SCALE_TOO_SMALL_VS_SOURCE"},
{"index":47,"key":"AD720950","path":"localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/AD720950_1024x256.dds","candidate_sha":"6386a41ffa4af599cc7076be0cc4ce59729026b4882c437ac397270290b7e4bf","prior_sha":"6dad37489e7027b8f546c38b3729167697965fc8e33fcabff46f09aba1677955","source_png":"localization/graphics/role_A/20261004-A-PRODUCTION13/AD720950_HD_SOURCE_READABLE.png","source_bboxes":[[3757,176,3873,222]],"localized_bboxes":[[3759,178,3871,220]],"reason":"PRE_INGAME visible functional Shift remained English"},
{"index":53,"key":"568D3696","path":"localization/graphics/hd_candidates/textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds","candidate_sha":"7df7e0309c621f59d29cac0b1f91d21c5a4a05262c9b916a55c3d87ac5f90e33","prior_sha":"2e18e459005323b37413e404b3adf31501cc92bbc3cd2b994a1c05bbdf3cef4d","source_dds":"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds","source_bboxes":[[1988,2061,2445,2164]],"localized_bboxes":[[1992,2072,2440,2156]],"reason":"PRE_INGAME TEXT_SCALE/HIERARCHY false-negative"}
]
def sha(b): return hashlib.sha256(b).hexdigest()
def hist(path,wanted):
  for c in subprocess.check_output(["git","rev-list","HEAD","--",path],text=True).splitlines():
    try:b=subprocess.check_output(["git","show",f"{c}:{path}"])
    except subprocess.CalledProcessError:continue
    if sha(b)==wanted:return b,c
  raise RuntimeError(f"missing historical blob {wanted}")
def meta(b):
  if b[:4]!=b"DDS ":raise RuntimeError("not DDS")
  return {"h":struct.unpack_from("<I",b,12)[0],"w":struct.unpack_from("<I",b,16)[0],"mips":struct.unpack_from("<I",b,28)[0] or 1,"header":sha(b[:128])}
def dec(b): return Image.open(io.BytesIO(b)).convert("RGBA")
def mask(h,w,boxes):
  m=np.zeros((h,w),bool)
  for x0,y0,x1,y1 in boxes:m[y0:y1,x0:x1]=1
  return m
def mbbox(m):
  ys,xs=np.nonzero(m)
  return None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
def panel(im,maxw=950,maxh=650):
  im=im.convert("RGB"); s=min(maxw/im.width,maxh/im.height,1)
  return im if s>=1 else im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.Resampling.LANCZOS)
def trip(src,prior,cur,path,title):
  ims=[panel(x) for x in (src,prior,cur)]; labs=["SOURCE","PRIOR","CURRENT"]
  W=sum(i.width for i in ims)+36; H=max(i.height for i in ims)+42
  o=Image.new("RGB",(W,H),(28,28,28));d=ImageDraw.Draw(o);x=0
  for lab,im in zip(labs,ims):d.text((x+4,5),lab,fill="white");o.paste(im,(x,30));x+=im.width+18
  d.text((4,H-3),title,fill="white",anchor="ls");o.save(path,quality=93,subsampling=0)
def contacts(src,prior,cur,boxes,path):
  rows=[]
  for sb in boxes:
    x0,y0,x1,y1=sb;pad=24;bb=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad))
    ims=[src.crop(bb),prior.crop(bb),cur.crop(bb)]
    sc=min(1,320/max(i.height for i in ims)); ims=[i.resize((max(1,int(i.width*sc)),max(1,int(i.height*sc))),Image.Resampling.NEAREST).convert("RGB") for i in ims]
    W=sum(i.width for i in ims)+24;H=max(i.height for i in ims)+25;o=Image.new("RGB",(W,H),(35,35,35));d=ImageDraw.Draw(o);x=0
    for lab,im in zip(["SRC","PRIOR","CUR"],ims):d.text((x+3,3),lab,fill="white");o.paste(im,(x,20));x+=im.width+12
    rows.append(o)
  W=max(r.width for r in rows);H=sum(r.height for r in rows)+8*(len(rows)-1);o=Image.new("RGB",(W,H),(20,20,20));y=0
  for r in rows:o.paste(r,(0,y));y+=r.height+8
  o.save(path,quality=95,subsampling=0)

summary={"schema_version":1,"role":"C","run":"C247","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)","assets":[]}
for a in ASSETS:
  cb=Path(a["path"]).read_bytes(); actual=sha(cb)
  if actual!=a["candidate_sha"]:raise RuntimeError(("candidate drift",a["index"],actual))
  pb,pc=hist(a["path"],a["prior_sha"]); cm,pm=meta(cb),meta(pb)
  if (cm["w"],cm["h"],cm["header"])!=(pm["w"],pm["h"],pm["header"]):raise RuntimeError(("header/dim drift",a["index"]))
  craw,praw=dec(cb),dec(pb); cur,prior=ImageOps.flip(craw),ImageOps.flip(praw)
  ca,pa=np.array(cur),np.array(prior); allowed=mask(cm["h"],cm["w"],a["source_bboxes"])
  diff=np.any(ca!=pa,axis=2); adiff=ca[:,:,3]!=pa[:,:,3]
  outside=int((diff & ~allowed).sum()); alpha_out=int((adiff & ~allowed).sum())
  if outside or alpha_out:raise RuntimeError(("blast outside",a["index"],outside,alpha_out,mbbox(diff)))
  per=[]
  for sb,lb in zip(a["source_bboxes"],a["localized_bboxes"]):
    x0,y0,x1,y1=sb; lx0,ly0,lx1,ly1=lb
    margins=[lx0-x0,x1-lx1,ly0-y0,y1-ly1]
    d={"source_bbox":sb,"localized_bbox":lb,"source_size":[x1-x0,y1-y0],"localized_size":[lx1-lx0,ly1-ly0],"margins":margins,
       "containment":"PASS" if min(margins)>=0 else "FAIL","size_ceiling":"PASS" if lx1-lx0<=x1-x0 and ly1-ly0<=y1-y0 else "FAIL","positive_margin":"PASS" if min(margins)>0 else "FAIL"}
    if "FAIL" in d.values():raise RuntimeError(("bbox",a["index"],d))
    per.append(d)
  if a.get("source_png"):src=Image.open(a["source_png"]).convert("RGBA")
  else:src=ImageOps.flip(Image.open(a["source_dds"]).convert("RGBA"))
  if src.size!=cur.size:raise RuntimeError(("source dims",a["index"],src.size,cur.size))
  trip(src,prior,cur,OUT/f"C247_Q{a['index']:03d}_{a['key']}_FLIPY.jpg",f"q{a['index']} readable/FLIP-Y")
  trip(ImageOps.flip(src),praw,craw,OUT/f"C247_Q{a['index']:03d}_{a['key']}_RAW.jpg",f"q{a['index']} RAW")
  contacts(src,prior,cur,a["source_bboxes"],OUT/f"C247_Q{a['index']:03d}_{a['key']}_CONTACTS.jpg")
  rep={"schema_version":2,"role":"C","run":"C247","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)","queue_index":a["index"],"asset_key":a["key"],"candidate_path":a["path"],"candidate_sha256":actual,"prior_candidate_sha256":a["prior_sha"],"prior_blob_commit":pc,"high_risk_reason":a["reason"],"independent_machine_qa":{"candidate_sha_exact":True,"dimensions":[cm["w"],cm["h"]],"mips":cm["mips"],"header_128_exact_to_prior":True,"decoded_changed_pixels":int(diff.sum()),"decoded_changed_bbox":mbbox(diff),"changed_pixels_outside_exact_source_bboxes":outside,"alpha_changed_outside_exact_source_bboxes":alpha_out,"bbox_size_positive_margin":f"{len(per)}/{len(per)} PASS","per_region":per,"raw_and_flip_y_evidence":"WRITTEN"},"controller_visual_qa":"PENDING_CONTROLLER","C3_STRICT_AUDIT":"PENDING_CONTROLLER","runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
  (OUT/f"C247_Q{a['index']:03d}_{a['key']}_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  summary["assets"].append({"index":a["index"],"key":a["key"],"candidate_sha256":actual,"machine_qa":"PASS","visual":"PENDING","c3":"PENDING"})
(OUT/"C247_BATCH_MACHINE_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
