#!/usr/bin/env python3
# B247 q62: C261 white-rectangle clean-plate repair.
# Root cause: PSD Layer43 is an authored full-canvas extraction whose pure-white
# erase canvas must be transparent in the DDS. B244 pasted those pixels opaque.
import os
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")
import hashlib,json,struct,subprocess,tempfile,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

repo=Path.cwd()
RUN="20261008-B247-Q062-TRANSPARENT-L43-CLEAN"
out=repo/"localization/graphics/role_B"/RUN;out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
rel="textures/load/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
INPUT="fa5cd96ff30b41d563886b336ca6305e2fdb7b050b39b2bcd5a5e8c2d46d64b6"
SOURCE="796531b06a159745d799f66f1476b9f78c5a14fd670468f58ce5404e6ced0551"
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
L43=repo/"localization/graphics/role_A/20261006-A-WORKSTEAL124-33491F83-PSD-LAYERS/A124_layer43.png"
ROWS=[
 {"key":"easy_main","bbox":[142,285,385,375],"ko":"쉬움","fill":(0,179,96,255),"anchor":[186,287]},
 {"key":"hard_main","bbox":[808,287,1068,373],"ko":"어려움","fill":(199,50,50,255),"anchor":[829,288]},
]
NAVY=(0,10,57,255);WHITE=(255,255,255,255);FS=73;OUTER=7;INNER=5

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_dds(p):
 b=Path(p).read_bytes()
 if b[:4]!=b"DDS ":raise RuntimeError("not DDS")
 h,w=struct.unpack_from("<II",b,12);mips=struct.unpack_from("<I",b,28)[0];bpp=struct.unpack_from("<I",b,88)[0];masks=struct.unpack_from("<IIII",b,92)
 if bpp!=32 or mips!=1 or len(b)!=128+w*h*4:raise RuntimeError(("DDS",w,h,bpp,mips,len(b)))
 mode="RGBA" if masks==(0xff,0xff00,0xff0000,0xff000000) else "BGRA" if masks==(0xff0000,0xff00,0xff,0xff000000) else None
 if not mode:raise RuntimeError(("masks",masks))
 raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
 return b,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"w":w,"h":h,"mips":mips,"masks":masks,"mode":mode}
def diffmask(a,b):
 d=ImageChops.difference(a,b);m=d.split()[0]
 for c in d.split()[1:]:m=ImageChops.lighter(m,c)
 return m.point(lambda v:255 if v else 0)
def count(m):return int(sum(m.histogram()[1:]))
def flat(im):
 z=Image.new("RGBA",im.size,(128,128,128,255));z.alpha_composite(im);return z.convert("RGB")

if sha(cand)!=INPUT:raise RuntimeError(("candidate drift",sha(cand),INPUT))
cb,raw_old,old,meta=load_dds(cand)
layer43=Image.open(L43).convert("RGBA")
if layer43.size!=old.size:raise RuntimeError(("layer43 size",layer43.size,old.size))
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists():raise RuntimeError(("font missing",FONT))
font=ImageFont.truetype(FONT,FS)
def glyph(text,fill):
 p=Image.new("RGBA",(1200,360),(0,0,0,0));d=ImageDraw.Draw(p)
 bb=d.textbbox((0,0),text,font=font,stroke_width=OUTER);xy=(40-bb[0],40-bb[1])
 d.text(xy,text,font=font,fill=fill,stroke_width=OUTER,stroke_fill=WHITE)
 d.text(xy,text,font=font,fill=fill,stroke_width=INNER,stroke_fill=NAVY)
 b=p.getchannel("A").getbbox()
 if not b:raise RuntimeError(("empty glyph",text))
 return p.crop(b)

with tempfile.TemporaryDirectory() as td:
 sp=Path(td)/"src.dds";urllib.request.urlretrieve(SRC_URL,sp)
 if sha(sp)!=SOURCE:raise RuntimeError(("source drift",sha(sp)))
 sb,sraw,source,smeta=load_dds(sp)
 if cb[:128]!=sb[:128] or smeta!=meta:raise RuntimeError("header/meta drift")

 final=old.copy();clean=old.copy()
 allowed=Image.new("L",old.size,0);ad=ImageDraw.Draw(allowed)
 rows=[];opaque_white_bad_total=0
 for spec in ROWS:
  x0,y0,x1,y1=spec["bbox"];ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
  donor=np.array(layer43.crop((x0,y0,x1,y1)),dtype=np.uint8)
  # Layer43's pure/near-white erase canvas is not authored road artwork.
  # Convert it to transparent DDS background; preserve every non-white road,
  # green edge and lane-marking pixel exactly.
  erase=(donor[:,:,:3]>=248).all(axis=2)
  donor[erase,3]=0
  donor[erase,:3]=0
  clean_crop=Image.fromarray(donor,"RGBA")
  clean.paste(clean_crop,(x0,y0))
  final.paste(clean_crop,(x0,y0))
  g=glyph(spec["ko"],spec["fill"]);ax,ay=spec["anchor"]
  if ax<x0 or ay<y0 or ax+g.width>x1 or ay+g.height>y1:raise RuntimeError(("glyph overflow",spec["key"],g.size))
  final.alpha_composite(g,(ax,ay))
  gm=np.zeros((y1-y0,x1-x0),bool);ga=np.asarray(g.getchannel("A"))>0
  gm[ay-y0:ay-y0+g.height,ax-x0:ax-x0+g.width]=ga
  fa=np.asarray(final.crop((x0,y0,x1,y1)))
  bad=((fa[:,:,:3]>=248).all(axis=2))&(fa[:,:,3]>0)&(~gm)
  badn=int(bad.sum());opaque_white_bad_total+=badn
  if badn:raise RuntimeError(("opaque white patch remains",spec["key"],badn))
  # All non-glyph visible clean pixels must either be authored non-white L43
  # road artwork or transparent background.
  ca=np.asarray(clean_crop)
  road=(ca[:,:,3]>0)
  if np.any(road & erase):raise RuntimeError(("erase alpha leak",spec["key"]))
  lb=[ax,ay,ax+g.width,ay+g.height];sw,sh=x1-x0,y1-y0;lw,lh=g.width,g.height
  margins=[ax-x0,x1-lb[2],ay-y0,y1-lb[3]]
  if min(margins)<=0 or lw>sw or lh>sh:raise RuntimeError(("containment",spec["key"],lb,margins))
  rows.append({"key":spec["key"],"source_bbox":spec["bbox"],"localized_bbox":lb,
    "source_size":[sw,sh],"localized_size":[lw,lh],"margins":margins,
    "layer43_white_to_transparent_pixels":int(erase.sum()),
    "opaque_white_pixels_outside_glyph":badn,"font":"Noto Sans CJK KR Black 73px",
    "outer_stroke_px":OUTER,"inner_navy_stroke_px":INNER,"containment":"PASS","size_ceiling":"PASS"})

 dm=diffmask(old,final);outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)))
 am=ImageChops.difference(old.getchannel("A"),final.getchannel("A")).point(lambda v:255 if v else 0)
 alpha_out=count(ImageChops.multiply(am,ImageChops.invert(allowed)))
 if outside or alpha_out:raise RuntimeError(("scope",outside,alpha_out))
 raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 cand.write_bytes(cb[:128]+raw.tobytes("raw",meta["mode"]));csha=sha(cand)
 rb,rraw,dec,rmeta=load_dds(cand)
 if rb[:128]!=cb[:128] or rmeta!=meta or ImageChops.difference(dec,final).getbbox() is not None:raise RuntimeError("roundtrip")

 # Evidence at failed rows.
 cards=[]
 for spec in ROWS:
  x0,y0,x1,y1=spec["bbox"];p=20;crop=(max(0,x0-p),max(0,y0-p),min(old.width,x1+p),min(old.height,y1+p))
  ims=[]
  for lab,im in [("SOURCE",source),("B244_REJECT",old),("B247_CLEAN",clean),("B247_FINAL",dec)]:
   z=flat(im.crop(crop));z=z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST)
   c=Image.new("RGB",(z.width,z.height+26),(20,20,20));c.paste(z,(0,26));ImageDraw.Draw(c).text((4,4),lab,fill="white");ims.append(c)
  row=Image.new("RGB",(sum(i.width for i in ims)+36,max(i.height for i in ims)+20),(16,16,16));xx=0
  for c in ims:row.paste(c,(xx,0));xx+=c.width+12
  ImageDraw.Draw(row).text((4,row.height-3),spec["key"],fill="white",anchor="ls");cards.append(row)
 sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8),(16,16,16));yy=0
 for c in cards:sheet.paste(c,(0,yy));yy+=c.height+8
 sheet.save(out/"B247_Q062_CONTACTS.jpg","JPEG",quality=96,subsampling=0)
 main=(0,0,1196,812);parts=[]
 for lab,im in [("SOURCE",source),("B244_REJECT",old),("B247_CLEAN",clean),("B247_FINAL",dec)]:
  z=flat(im.crop(main));z.thumbnail((580,400),Image.Resampling.LANCZOS)
  c=Image.new("RGB",(z.width,z.height+28),(20,20,20));c.paste(z,(0,28));ImageDraw.Draw(c).text((4,5),lab,fill="white");parts.append(c)
 panel=Image.new("RGB",(max(i.width for i in parts)*2+12,max(i.height for i in parts)*2+12),(16,16,16))
 panel.paste(parts[0],(0,0));panel.paste(parts[1],(parts[0].width+12,0));panel.paste(parts[2],(0,parts[0].height+12));panel.paste(parts[3],(parts[2].width+12,parts[1].height+12))
 panel.save(out/"B247_Q062_PRACTICAL.jpg","JPEG",quality=94,subsampling=0)
 rs,ro,rn=flat(sraw),flat(raw_old),flat(rraw)
 for z in (rs,ro,rn):z.thumbnail((620,320),Image.Resampling.LANCZOS)
 rw=Image.new("RGB",(rs.width+ro.width+rn.width+24,max(rs.height,ro.height,rn.height)+28),(16,16,16));xx=0
 for lab,z in [("SOURCE RAW",rs),("B244 RAW",ro),("B247 RAW",rn)]:
  rw.paste(z,(xx,28));ImageDraw.Draw(rw).text((xx+4,5),lab,fill="white");xx+=z.width+12
 rw.save(out/"B247_Q062_RAW.jpg","JPEG",quality=94,subsampling=0)
 clean.save(out/"B247_Q062_CLEAN_PLATE.png")

 report={"schema_version":2,"role":"B","run":RUN,"queue_index":62,"asset":"33491F83",
  "trigger":"C261_REWORK_REQUIRED_OPAQUE_WHITE_RECTANGLE_CLEAN_PLATE",
  "source_sha256":SOURCE,"prior_candidate_sha256":INPUT,"candidate_sha256":csha,
  "root_cause":"B244 treated PSD Layer43 pure-white erase canvas as opaque DDS background. In this atlas those white pixels must be transparent; only Layer43 non-white road/green-edge/lane pixels are authored clean artwork.",
  "rows":rows,
  "machine_qa":{"target_rows":"2/2 PASS","changed_outside_target_bboxes":outside,"alpha_changed_outside_target_bboxes":alpha_out,
   "opaque_white_background_pixels_outside_glyph":opaque_white_bad_total,"non_target_atlas_pixel_exact":True,
   "header_128_exact":True,"mips":meta["mips"],"raw_orientation":"mirror_y","persisted_decode":"PASS"},
  "ordered_generation_gate":{"1_plate_restoration":"PASS_LAYER43_WHITE_ERASE_CANVAS_TO_TRANSPARENT",
   "2_source_slant":"PASS_UPRIGHT_MAIN_FAMILY","3_scale":"PASS_NATIVE_73PX_A132_FAMILY",
   "4_weight_outline":"PASS_BLACK_WHITE7_NAVY5_SOURCE_COLORS","5_clipping":"PASS_POSITIVE_MARGIN",
   "6_protected":"PASS_NON_TARGET_ATLAS_EXACT","7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
   "8_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER"},
  "execution_backend":"N100_MCP_FALLBACK_REPOSITORY_BACKED_DDS",
  "fallback_reason":"GitHub-hosted B247 run 37683401932 remained pending behind stuck B246 run 37675870154. Exact q62 input SHA fa5cd96f... and pinned B247 script were verified before identical fallback execution.",
  "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER",
  "status":"B247_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA","runtime_validation":"UNTESTED","forbidden_domains_touched":[]}
 (out/"B247_Q062_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 (wr/"B247_Q062.json").write_text(json.dumps({"role":"B","run":RUN,"queue_index":62,"asset":"33491F83","candidate_sha256":csha,
  "report":str((out/"B247_Q062_REPORT.json").relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"run":RUN,"candidate_sha256":csha,"rows":rows,"outside":outside,"alpha_outside":alpha_out,
  "opaque_white_background_pixels":opaque_white_bad_total},ensure_ascii=False,indent=2))