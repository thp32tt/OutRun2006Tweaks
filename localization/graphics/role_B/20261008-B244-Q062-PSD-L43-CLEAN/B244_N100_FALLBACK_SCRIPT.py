#!/usr/bin/env python3
import hashlib,json,struct,subprocess,tempfile,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont

repo=Path.cwd()
RUN="20261008-B244-Q062-PSD-L43-CLEAN"
out=repo/"localization/graphics/role_B"/RUN
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
rel="textures/load/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
INPUT="58fe9ed97494a2026a671e777c2af7da75a33bdd9432e5ab1fa4b547f1cd54b2"
SOURCE="796531b06a159745d799f66f1476b9f78c5a14fd670468f58ce5404e6ced0551"
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
A132=repo/"localization/graphics/role_A/20261006-A-WORKSTEAL132-33491F83-GROUP16-CLEAN"
A124=repo/"localization/graphics/role_A/20261006-A-WORKSTEAL124-33491F83-PSD-LAYERS"
old_clean_p=A132/"A132_CLEAN_PLATE.png"
layer43_p=A124/"A124_layer43.png"

ROWS=[
 {"key":"easy_main","bbox":[142,285,385,375],"ko":"쉬움","fill":(0,179,96,255),"anchor":[186,287],"expected":[186,287,329,371]},
 {"key":"hard_main","bbox":[808,287,1068,373],"ko":"어려움","fill":(199,50,50,255),"anchor":[829,288],"expected":[829,288,1039,372]},
]
NAVY=(0,10,57,255);WHITE=(255,255,255,255);FS=73;OUTER=7;INNER=5

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()

def load_dds(p):
 b=Path(p).read_bytes()
 if b[:4]!=b"DDS ":raise RuntimeError("not DDS")
 h,w=struct.unpack_from("<II",b,12);mips=struct.unpack_from("<I",b,28)[0]
 bpp=struct.unpack_from("<I",b,88)[0];masks=struct.unpack_from("<IIII",b,92)
 if bpp!=32 or mips!=1 or len(b)!=128+w*h*4:raise RuntimeError(("DDS",w,h,bpp,mips,len(b)))
 if masks==(0xff,0xff00,0xff0000,0xff000000):mode="RGBA"
 elif masks==(0xff0000,0xff00,0xff,0xff000000):mode="BGRA"
 else:raise RuntimeError(("masks",masks))
 raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
 return b,raw,raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),{"width":w,"height":h,"mips":mips,"masks":masks,"mode":mode}

def diffmask(a,b):
 d=ImageChops.difference(a,b);cs=d.split();m=cs[0]
 for c in cs[1:]:m=ImageChops.lighter(m,c)
 return m.point(lambda v:255 if v else 0)

def count(m):return int(sum(m.histogram()[1:]))

def flat(im):
 z=Image.new("RGBA",im.size,(224,224,224,255));z.alpha_composite(im);return z.convert("RGB")

def bbox_alpha(im):
 b=im.getchannel("A").getbbox();return list(b) if b else None

if sha(cand)!=INPUT:raise RuntimeError(("candidate drift",sha(cand),INPUT))
cb,raw_old,old,meta=load_dds(cand)
old_clean=Image.open(old_clean_p).convert("RGBA")
layer43=Image.open(layer43_p).convert("RGBA")
if old.size!=old_clean.size or old.size!=layer43.size:raise RuntimeError("image shape mismatch")

# Locate exact A132 font family. Do not install or substitute silently.
FONT=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
if not FONT or not Path(FONT).exists():raise RuntimeError(("font missing",FONT))
font=ImageFont.truetype(FONT,FS)

def make_glyph(text,fill):
 probe=Image.new("RGBA",(1200,360),(0,0,0,0));d=ImageDraw.Draw(probe)
 tb=d.textbbox((0,0),text,font=font,stroke_width=OUTER)
 xy=(40-tb[0],40-tb[1])
 d.text(xy,text,font=font,fill=fill,stroke_width=OUTER,stroke_fill=WHITE)
 d.text(xy,text,font=font,fill=fill,stroke_width=INNER,stroke_fill=NAVY)
 gb=probe.getchannel("A").getbbox()
 if not gb:raise RuntimeError(("empty glyph",text))
 return probe.crop(gb)

# Canonical English source for evidence.
with tempfile.TemporaryDirectory() as td:
 sp=Path(td)/"source.dds";urllib.request.urlretrieve(SRC_URL,sp)
 if sha(sp)!=SOURCE:raise RuntimeError(("source drift",sha(sp)))
 sb,sraw,source,smeta=load_dds(sp)
 if cb[:128]!=sb[:128] or smeta!=meta:raise RuntimeError("structure drift")

 corrected_clean=old_clean.copy()
 final=old.copy()
 allowed=Image.new("L",old.size,0);ad=ImageDraw.Draw(allowed)
 report_rows=[]
 for row in ROWS:
  x0,y0,x1,y1=row["bbox"];ad.rectangle((x0,y0,x1-1,y1-1),fill=255)
  donor=layer43.crop((x0,y0,x1,y1))
  oldc=old_clean.crop((x0,y0,x1,y1))
  patch_px=count(diffmask(oldc,donor))
  if patch_px<=0:raise RuntimeError(("no authored clean delta",row["key"]))
  corrected_clean.paste(donor,(x0,y0))
  # Start from authored text-free Layer43 clean, then rerender the exact A132
  # Korean style parameters. This intentionally discards A132 Group16 white patch pixels.
  final.paste(donor,(x0,y0))
  g=make_glyph(row["ko"],row["fill"])
  ax,ay=row["anchor"]
  if ax<x0 or ay<y0 or ax+g.width>x1 or ay+g.height>y1:raise RuntimeError(("glyph bbox",row["key"],g.size,row["bbox"]))
  final.alpha_composite(g,(ax,ay))
  lb=[ax,ay,ax+g.width,ay+g.height]
  sw,sh=x1-x0,y1-y0;lw,lh=g.width,g.height
  margins=[ax-x0,x1-(ax+g.width),ay-y0,y1-(ay+g.height)]
  if min(margins)<=0 or lw>sw or lh>sh:raise RuntimeError(("containment",row["key"],lb,margins))
  report_rows.append({
   "key":row["key"],"source_bbox":row["bbox"],"localized_bbox":lb,
   "a132_expected_bbox":row["expected"],"source_size":[sw,sh],"localized_size":[lw,lh],
   "delta_left":margins[0],"delta_right":margins[1],"delta_top":margins[2],"delta_bottom":margins[3],
   "font":"Noto Sans CJK KR Black","font_path":FONT,"font_size":FS,
   "outer_stroke_px":OUTER,"navy_stroke_px":INNER,
   "a132_clean_to_layer43_patch_pixels":patch_px,"containment":"PASS","size_ceiling":"PASS"
  })

 dm=diffmask(old,final)
 outside=count(ImageChops.multiply(dm,ImageChops.invert(allowed)))
 am=ImageChops.difference(old.getchannel("A"),final.getchannel("A")).point(lambda v:255 if v else 0)
 alpha_out=count(ImageChops.multiply(am,ImageChops.invert(allowed)))
 changed=count(dm)
 if outside or alpha_out or changed<=0:raise RuntimeError(("scope/change",outside,alpha_out,changed))

 raw_new=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
 cand.write_bytes(cb[:128]+raw_new.tobytes("raw",meta["mode"]))
 csha=sha(cand)
 rb,rraw,decoded,rmeta=load_dds(cand)
 if rb[:128]!=cb[:128] or rmeta!=meta or ImageChops.difference(decoded,final).getbbox() is not None:
  raise RuntimeError("persisted decode mismatch")

 # Background proof: outside newly rendered glyph alpha within each target bbox,
 # B244 final must be pixel-identical to authored Layer43 clean.
 bg_mismatch_total=0
 for rr,row in zip(report_rows,ROWS):
  x0,y0,x1,y1=row["bbox"];g=make_glyph(row["ko"],row["fill"])
  gm=np.zeros((y1-y0,x1-x0),bool)
  gx=row["anchor"][0]-x0;gy=row["anchor"][1]-y0
  ga=np.array(g.getchannel("A"))>0
  gm[gy:gy+g.height,gx:gx+g.width]=ga
  fa=np.array(decoded.crop((x0,y0,x1,y1)));da=np.array(layer43.crop((x0,y0,x1,y1)))
  mism=np.any(fa!=da,axis=2)&~gm
  rr["background_mismatch_vs_layer43_outside_glyph"]=int(mism.sum())
  bg_mismatch_total+=int(mism.sum())
 if bg_mismatch_total:raise RuntimeError(("background mismatch",bg_mismatch_total))

 corrected_clean.save(out/"B244_Q062_CLEAN_PLATE.png")

 # Evidence: SOURCE / A132 rejected clean / authored clean / B244 final.
 cards=[]
 for rr,row in zip(report_rows,ROWS):
  x0,y0,x1,y1=row["bbox"];p=20
  crop=(max(0,x0-p),max(0,y0-p),min(old.width,x1+p),min(old.height,y1+p))
  ims=[]
  for lab,im in [("SOURCE",source),("A132_CLEAN_FAIL",old_clean),("PSD_LAYER43_CLEAN",corrected_clean),("B244_FINAL",decoded)]:
   z=flat(im.crop(crop));z=z.resize((z.width*2,z.height*2),Image.Resampling.NEAREST)
   c=Image.new("RGB",(z.width,z.height+26),(26,26,26));c.paste(z,(0,26));ImageDraw.Draw(c).text((4,4),lab,fill="white");ims.append(c)
  c=Image.new("RGB",(sum(x.width for x in ims)+36,max(x.height for x in ims)+20),(18,18,18));xx=0
  for z in ims:c.paste(z,(xx,0));xx+=z.width+12
  ImageDraw.Draw(c).text((4,c.height-3),row["key"],fill="white",anchor="ls");cards.append(c)
 sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+8),(18,18,18));yy=0
 for c in cards:sheet.paste(c,(0,yy));yy+=c.height+8
 sheet.save(out/"B244_Q062_EASY_HARD_ZOOM.jpg","JPEG",quality=96,subsampling=0)

 main=(0,0,1196,812);ims=[]
 for lab,im in [("SOURCE",source),("A132_CLEAN_FAIL",old_clean),("PSD_LAYER43_CLEAN",corrected_clean),("B244_FINAL",decoded)]:
  z=flat(im.crop(main));z.thumbnail((580,400),Image.Resampling.LANCZOS)
  c=Image.new("RGB",(z.width,z.height+28),(26,26,26));c.paste(z,(0,28));ImageDraw.Draw(c).text((4,5),lab,fill="white");ims.append(c)
 panel=Image.new("RGB",(max(x.width for x in ims)*2+12,max(x.height for x in ims)*2+12),(18,18,18))
 panel.paste(ims[0],(0,0));panel.paste(ims[1],(ims[0].width+12,0))
 panel.paste(ims[2],(0,ims[0].height+12));panel.paste(ims[3],(ims[2].width+12,ims[1].height+12))
 panel.save(out/"B244_Q062_MAIN_COMPARE.jpg","JPEG",quality=94,subsampling=0)

 rs,ro,rn=flat(sraw),flat(raw_old),flat(rraw)
 for z in (rs,ro,rn):z.thumbnail((620,320),Image.Resampling.LANCZOS)
 rw=Image.new("RGB",(rs.width+ro.width+rn.width+24,max(rs.height,ro.height,rn.height)+28),(18,18,18));xx=0
 for lab,z in [("SOURCE RAW",rs),("A132 RAW",ro),("B244 RAW",rn)]:
  rw.paste(z,(xx,28));ImageDraw.Draw(rw).text((xx+4,5),lab,fill="white");xx+=z.width+12
 rw.save(out/"B244_Q062_RAW.jpg","JPEG",quality=92,subsampling=0)

 report={
  "schema_version":2,"role":"B","run":RUN,"queue_index":62,"asset":"33491F83",
  "trigger":"C259_REWORK_REQUIRED_CLEAN_PLATE_WHITE_OVAL_PATCHES",
  "source_sha256":SOURCE,"prior_candidate_sha256":INPUT,"candidate_sha256":csha,
  "repair_basis":{"rejected":"A132 Layer43+Group16 produced visible white rounded EASY/HARD plate patches",
   "replacement":"PSD-authored Layer43 clean road/background only inside exact EASY/HARD source-effect bboxes",
   "lettering":"fresh native rerender using exact A132 family/style parameters: Noto Sans CJK KR Black 73px, white outer 7px, navy inner 5px, source colors and A132 anchors"},
  "rows":report_rows,
  "machine_qa":{"target_rows":"2/2 PASS","changed_pixels_vs_a132":changed,
   "changed_outside_target_bboxes":outside,"alpha_changed_outside_target_bboxes":alpha_out,
   "background_mismatch_vs_authored_layer43_outside_glyph":bg_mismatch_total,
   "non_target_atlas_pixel_exact":True,"header_128_exact":True,"mips":meta["mips"],
   "raw_orientation":"mirror_y","persisted_decode":"PASS"},
  "ordered_generation_gate":{"1_plate_restoration":"PASS_AUTHORED_PSD_LAYER43_CONTINUOUS_ROAD_NO_WHITE_PATCH",
   "2_source_matching_slant":"PASS_UPRIGHT_MAIN_LABEL_FAMILY","3_no_undersized_lettering":"PASS_A132_73PX_NATIVE_FAMILY",
   "4_source_faithful_weight_effect":"PASS_A132_BLACK_WHITE_NAVY_STROKE_FAMILY",
   "5_no_clipped_pixels":"PASS_POSITIVE_MARGIN","6_protected_art_clearance":"PASS_NON_TARGET_ATLAS_PIXEL_EXACT",
   "7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER","8_immediate_readability":"EVIDENCE_WRITTEN_PENDING_CONTROLLER"},
  "execution_backend":"N100_MCP_FALLBACK_REPOSITORY_BACKED_DDS",
  "fallback_reason":"GitHub-hosted B244 run 37667995926 stayed queued behind unrelated C260 PRE_INGAME exporter for >15 minutes. Exact q62 input SHA 58fe9ed9... and authored A132/A124 evidence hashes were verified before fallback.",
  "controller_visual_qa":"PENDING_CHATGPT_CONTROLLER","status":"B244_MACHINE_PASS_PENDING_CONTROLLER_SELF_QA",
  "runtime_validation":"UNTESTED","forbidden_domains_touched":[]
 }
 (out/"B244_Q062_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 (wr/"B244_Q062.json").write_text(json.dumps({"role":"B","run":RUN,"queue_index":62,"asset":"33491F83","candidate_sha256":csha,
  "report":str((out/"B244_Q062_REPORT.json").relative_to(repo)),"status":report["status"],"runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"run":RUN,"candidate_sha256":csha,"rows":report_rows,"changed_pixels":changed,
  "outside":outside,"alpha_outside":alpha_out,"backend":report["execution_backend"]},ensure_ascii=False,indent=2))