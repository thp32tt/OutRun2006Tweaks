#!/usr/bin/env python3
# C250V C1 alpha-composited visual helper for q57/q61/q65
# TEMP_BACKLOG_RELIEF=C1 / SHARD=ODD(+UNINDEXED_SPECIAL)
import io, json, os
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

BASE=Path("localization/graphics/role_C/20261007-C250-C1-BATCH-Q057-Q061-Q065")
CFG={
57:("39229D64","localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds","localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds",False,["mission_cleared","total_rank_green","special_request","target","mission_failed","total_rank_brown","total_rank_pink"]),
61:("C4A2937B","localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/C4A2937B_1024x1024.dds","localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/C4A2937B_1024x1024.dds",False,["go_gate","cut_line","keep_passing","double_speed","red","blue","get","next_stage","position"]),
65:("EBEF6D20","localization/graphics/hd_candidates/textures/load/spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds","localization/graphics/role_A/20261005-A-PRODUCTION21/EBEF6D20_HD_SOURCE_READABLE.png",True,["loading_left","loading_right","course","left","right","easy","hard"])
}
def old(path,want):
 import hashlib, subprocess
 H=lambda b:hashlib.sha256(b).hexdigest()
 for c in subprocess.check_output(["git","rev-list","HEAD","--",path],text=True).splitlines():
  try:b=subprocess.check_output(["git","show",f"{c}:{path}"])
  except subprocess.CalledProcessError:continue
  if H(b)==want:return Image.open(io.BytesIO(b)).convert("RGBA")
 raise RuntimeError("prior not found")
def flat(im,bg=(96,96,96)):
 base=Image.new("RGBA",im.size,bg+(255,));return Image.alpha_composite(base,im.convert("RGBA")).convert("RGB")
def fit(im,mw,mh):
 s=min(mw/im.width,mh/im.height,1);return im if s==1 else im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.Resampling.LANCZOS)
def overview(src,prior,cur,path):
 ims=[fit(flat(x),900,900) for x in (src,prior,cur)];W=sum(i.width for i in ims)+40;H=max(i.height for i in ims)+36
 o=Image.new("RGB",(W,H),(25,25,25));d=ImageDraw.Draw(o);x=0
 for lab,im in zip(["SOURCE","PRIOR","CURRENT"],ims):d.text((x+3,3),lab,fill="white");o.paste(im,(x,24));x+=im.width+20
 o.save(path,quality=92,subsampling=0,optimize=True)
def contacts(src,prior,cur,rows,keys,path):
 cards=[]
 for r in rows:
  if r["key"] not in keys:continue
  x0,y0,x1,y1=r["original_bbox"];p=32;bb=(max(0,x0-p),max(0,y0-p),min(src.width,x1+p),min(src.height,y1+p))
  ims=[fit(flat(x.crop(bb)),620,260) for x in (src,prior,cur)];W=sum(i.width for i in ims)+32;H=max(i.height for i in ims)+42
  c=Image.new("RGB",(W,H),(30,30,30));d=ImageDraw.Draw(c);xx=0
  for lab,im in zip(["SRC","PRIOR","CUR"],ims):d.text((xx+3,3),lab,fill="white");c.paste(im,(xx,24));xx+=im.width+16
  d.text((4,H-3),r["key"],fill="white",anchor="ls");cards.append(c)
 W=max(c.width for c in cards);H=sum(c.height for c in cards)+8*(len(cards)-1);o=Image.new("RGB",(W,H),(18,18,18));y=0
 for c in cards:o.paste(c,(0,y));y+=c.height+8
 o.save(path,quality=94,subsampling=0,optimize=True)
for idx,(key,cpath,spath,source_is_readable,crit) in CFG.items():
 rep=json.loads((BASE/f"C250_q{idx:03d}_{key}_MACHINE_QA.json").read_text(encoding="utf-8"))
 cur_raw=Image.open(cpath).convert("RGBA");cur=ImageOps.flip(cur_raw)
 prior_raw=old(cpath,rep["prior_candidate_sha256"]);prior=ImageOps.flip(prior_raw)
 src0=Image.open(spath).convert("RGBA");src=src0 if source_is_readable else ImageOps.flip(src0)
 overview(src,prior,cur,BASE/f"C250V_q{idx:03d}_{key}_ALPHA_OVERVIEW.jpg")
 contacts(src,prior,cur,rep["machine_qa"]["per_region"],crit,BASE/f"C250V_q{idx:03d}_{key}_ALPHA_CONTACTS.jpg")
 rep["alpha_composited_visual_evidence"]=[f"C250V_q{idx:03d}_{key}_ALPHA_OVERVIEW.jpg",f"C250V_q{idx:03d}_{key}_ALPHA_CONTACTS.jpg"]
 (BASE/f"C250_q{idx:03d}_{key}_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
