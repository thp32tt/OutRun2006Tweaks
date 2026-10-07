#!/usr/bin/env python3
# B245: q212 follow-up after B243 producer visual fail.
# Goal: retain a mildly condensed whole-word Hangul family, materially reduce
# word separation again, and recover source title hierarchy through near-max height.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")
import hashlib,json,struct,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

repo=Path.cwd()
RUN="20261008-B245-Q212-HEART-COMPACT-HIERARCHY"
out=repo/"localization/graphics/role_B"/RUN;out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
INPUT="4b967ef09bbbb21d7ecc1496c2ee15395567b526af6cf68f1c22c7549850d518"
SOURCE="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"
HEART_BB=[21,1316,1780,1474]
COAST_BB=[0,964,1760,1124]
TARGET_H=154
HSCALE=0.97
WORD_GAP=170

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 b=Path(p).read_bytes()
 if b[:4]!=b"DDS ":raise RuntimeError("not DDS")
 h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12);masks=struct.unpack_from("<IIII",b,92)
 if b[84:88]!=b"\0\0\0\0" or struct.unpack_from("<I",b,88)[0]!=32 or mips!=1 or len(b)!=128+w*h*4:raise RuntimeError("DDS structure")
 mode="RGBA" if masks==(0xff,0xff00,0xff0000,0xff000000) else "BGRA" if masks==(0xff0000,0xff00,0xff,0xff000000) else None
 if not mode:raise RuntimeError(("masks",masks))
 raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
 return b,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"pitch":pitch,"mips":mips,"masks":masks,"mode":mode}
def fontspec():
 for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold"]:
  q=subprocess.check_output(["fc-match","-f","%{file}|%{index}",pat],text=True).strip()
  if "|" in q:
   p,ix=q.rsplit("|",1)
   if Path(p).exists() and "NotoSansCJK" in Path(p).name:return p,int(ix or 0),pat
 subprocess.run(["sudo","apt-get","update","-qq"],check=True)
 subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
 q=subprocess.check_output(["fc-match","-f","%{file}|%{index}","Noto Sans CJK KR:style=Black"],text=True).strip()
 p,ix=q.rsplit("|",1);return p,int(ix or 0),"Noto Sans CJK KR:style=Black"
FONT,FI,FPAT=fontspec()
def diffmask(a,b):
 d=ImageChops.difference(a,b);m=d.split()[0]
 for c in d.split()[1:]:m=ImageChops.lighter(m,c)
 return m.point(lambda v:255 if v else 0)
def count(m):return int(sum(m.histogram()[1:]))
def flat(im):
 z=Image.new("RGBA",im.size,(82,82,82,255));z.alpha_composite(im);return z.convert("RGB")
def word_layer(word):
 f=ImageFont.truetype(FONT,220,index=FI)
 p=Image.new("L",(1000,360),0);d=ImageDraw.Draw(p)
 bb=d.textbbox((0,0),word,font=f,stroke_width=2)
 d.text((20-bb[0],20-bb[1]),word,font=f,fill=255,stroke_width=2,stroke_fill=255)
 g=p.crop(p.getbbox());sc=TARGET_H/g.height
 g=g.resize((round(g.width*sc*HSCALE),TARGET_H),Image.Resampling.LANCZOS)
 rgba=Image.new("RGBA",g.size,(196,0,0,255));rgba.putalpha(g);return rgba

if sha(cand)!=INPUT:raise RuntimeError(("candidate drift",sha(cand),INPUT))
srcp=Path("/tmp/B245_BA0147DA_source.dds")
urllib.request.urlretrieve("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds",srcp)
if sha(srcp)!=SOURCE:raise RuntimeError(("source drift",sha(srcp)))
cb,cr,old,meta=load(cand);sb,sr,src,smeta=load(srcp)
if cb[:128]!=sb[:128] or meta!=smeta:raise RuntimeError("header/meta drift")
clean=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_CLEAN_PLATE.png").convert("RGBA")
protected=np.asarray(Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION85/BA_PROTECTED_MASK.png").convert("L"))>0

final=old.copy();x0,y0,x1,y1=HEART_BB
final.paste(clean.crop(tuple(HEART_BB)),(x0,y0))
layers=[word_layer("하트"),word_layer("어택")]
phrase_w=sum(g.width for g in layers)+WORD_GAP
x=x0+5;y=y0+(y1-y0-TARGET_H)//2
boxes=[]
for word,g in zip(["하트","어택"],layers):
 lm=np.asarray(g.getchannel("A"))>0
 if np.any(lm&protected[y:y+g.height,x:x+g.width]):raise RuntimeError(("protected",word))
 final.alpha_composite(g,(x,y));boxes.append([x,y,x+g.width,y+g.height]);x+=g.width+WORD_GAP
if x-WORD_GAP>x1-5:raise RuntimeError(("phrase overflow",x-WORD_GAP,x1))
m=diffmask(clean.crop(tuple(HEART_BB)),final.crop(tuple(HEART_BB)));bb=m.getbbox()
if not bb:raise RuntimeError("empty localized title")
loc=[x0+bb[0],y0+bb[1],x0+bb[2],y0+bb[3]]
sw,sh=x1-x0,y1-y0;lw,lh=loc[2]-loc[0],loc[3]-loc[1]
margins=[loc[0]-x0,x1-loc[2],loc[1]-y0,y1-loc[3]]
if min(margins)<=0 or lw>sw or lh>sh:raise RuntimeError(("containment",loc,margins))
# Fail closed unless this iteration materially addresses both B243 defects.
if WORD_GAP>=195:raise RuntimeError(("gap not improved",WORD_GAP))
if lw<=718:raise RuntimeError(("hierarchy width not improved over B242",lw))
if lh<154:raise RuntimeError(("height hierarchy not improved",lh))

allowed=Image.new("L",final.size,0);ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
dm=diffmask(old,final);outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)))
am=ImageChops.difference(old.getchannel("A"),final.getchannel("A")).point(lambda v:255 if v else 0)
alpha_out=count(ImageChops.multiply(am,ImageChops.invert(allowed)))
if outside or alpha_out:raise RuntimeError(("scope",outside,alpha_out))
if ImageChops.difference(old.crop(tuple(COAST_BB)),final.crop(tuple(COAST_BB))).getbbox() is not None:raise RuntimeError("C2C changed")

raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cand.write_bytes(cb[:128]+raw.tobytes("raw",meta["mode"]));csha=sha(cand)
rb,rr,dec,rm=load(cand)
if rb[:128]!=cb[:128] or rm!=meta or ImageChops.difference(dec,final).getbbox() is not None:raise RuntimeError("roundtrip")

# Controller evidence.
crop=(max(0,x0-30),max(0,y0-30),min(src.width,x1+30),min(src.height,y1+30))
cards=[]
for lab,im in [("SOURCE",src),("B243_REJECT",old),("CLEAN",clean),("B245",dec)]:
 z=flat(im.crop(crop));z.thumbnail((760,270),Image.Resampling.LANCZOS)
 c=Image.new("RGB",(z.width,z.height+26),(22,22,22));c.paste(z,(0,26));ImageDraw.Draw(c).text((4,4),lab,fill="white");cards.append(c)
sheet=Image.new("RGB",(sum(c.width for c in cards)+36,max(c.height for c in cards)),(16,16,16));xx=0
for c in cards:sheet.paste(c,(xx,0));xx+=c.width+12
sheet.save(out/"B245_Q212_HEART_CONTACTS.jpg","JPEG",quality=96,subsampling=0)

parts=[]
for sc in [1.0,.75,.5]:
 for lab,im in [("SOURCE",src),("B243",old),("B245",dec)]:
  z=flat(im.crop(tuple(HEART_BB)))
  if sc!=1:z=z.resize((round(z.width*sc),round(z.height*sc)),Image.Resampling.LANCZOS)
  z.thumbnail((760,220),Image.Resampling.LANCZOS)
  c=Image.new("RGB",(z.width,z.height+24),(20,20,20));c.paste(z,(0,24));ImageDraw.Draw(c).text((4,4),f"{lab} {int(sc*100)}%",fill="white");parts.append(c)
pr=Image.new("RGB",(max(c.width for c in parts),sum(c.height for c in parts)+5*(len(parts)-1)),(16,16,16));yy=0
for c in parts:pr.paste(c,(0,yy));yy+=c.height+5
pr.save(out/"B245_Q212_HEART_PRACTICAL.jpg","JPEG",quality=94,subsampling=0)

s=flat(src.transpose(Image.Transpose.FLIP_TOP_BOTTOM));o=flat(old.transpose(Image.Transpose.FLIP_TOP_BOTTOM));f=flat(dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
for z in (s,o,f):z.thumbnail((700,700),Image.Resampling.LANCZOS)
rw=Image.new("RGB",(s.width+o.width+f.width+24,max(s.height,o.height,f.height)+26),(16,16,16));xx=0
for lab,z in [("SOURCE RAW",s),("B243 RAW",o),("B245 RAW",f)]:
 rw.paste(z,(xx,26));ImageDraw.Draw(rw).text((xx+4,4),lab,fill="white");xx+=z.width+12
rw.save(out/"B245_Q212_RAW.jpg","JPEG",quality=94,subsampling=0)

report={"schema_version":2,"role":"B","run":RUN,"queue_index":212,"asset":"BA0147DA",
 "trigger":"B243_CONTROLLER_VISUAL_FAIL_GAP_REDUCED_BUT_HIERARCHY_WIDTH_REGRESSED",
 "source_sha256":SOURCE,"prior_candidate_sha256":INPUT,"candidate_sha256":csha,
 "heart_attack":{"source_bbox":HEART_BB,"localized_bbox":loc,"source_size":[sw,sh],"localized_size":[lw,lh],
  "width_ratio":round(lw/sw,4),"height_ratio":round(lh/sh,4),"word_gap_px":WORD_GAP,
  "b242_word_gap_px":300,"b243_word_gap_px":195,"font":FPAT,"hscale":HSCALE,"target_h":TARGET_H,
  "word_boxes":boxes,"margins":margins,
  "construction":"whole-word groups only; no per-syllable tracking; mildly condensed 0.97 aspect; near-source-max 154px height; reduced 170px word gap"},
 "improvement_gate":{"gap_vs_b243_px":195-WORD_GAP,"gap_vs_b242_px":300-WORD_GAP,
  "width_vs_b243_px":lw-707,"width_vs_b242_px":lw-718,"height_vs_b243_px":lh-150},
 "coast2coast_region_pixel_exact":True,
 "machine_qa":{"containment":"PASS","changed_outside_heart_bbox":outside,"alpha_changed_outside_heart_bbox":alpha_out,
  "header_128_exact":True,"mips":meta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS"},
 "ordered_generation_gate":{"1_plate_restoration":"PASS_B85_VERIFIED_CLEAN","2_source_slant":"PASS_UPRIGHT",
  "3_scale_hierarchy":"PASS_154PX_NEAR_SOURCE_MAX","4_weight_effect":"PASS_BLACK_MILD_CONDENSE_0.97",
  "5_clipping":"PASS_POSITIVE_MARGIN","6_protected":"PASS_ZERO","7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
  "8_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER"},
 "execution_backend":"GITHUB_HOSTED_CPU_WORKER","controller_visual_qa":"PENDING_CHATGPT_CONTROLLER",
 "status":"B245_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
(out/"B245_Q212_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B245_Q212.json").write_text(json.dumps({"role":"B","run":RUN,"queue_index":212,"candidate_sha256":csha,
 "report":str((out/"B245_Q212_REPORT.json").relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":RUN,"candidate_sha256":csha,"localized_size":[lw,lh],"width_ratio":report["heart_attack"]["width_ratio"],
 "gap":WORD_GAP,"improvement":report["improvement_gate"],"outside":outside,"alpha_outside":alpha_out},ensure_ascii=False,indent=2))
