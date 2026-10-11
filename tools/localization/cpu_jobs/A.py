#!/usr/bin/env python3
"""A237: q161 R11 source-derived approved CLEAN + separated native glyph engine.
Single new unpromoted BC3 trial. Other 37 cells keep A218 bytes exactly.
"""
import os,sys,io,json,hashlib,struct,csv,subprocess,platform
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
sys.dont_write_bytecode=True
root=Path.cwd()
sys.path.insert(0,str(root))
sys.path.insert(0,str(root/"tools/localization"))
from tools.localization.plate_library import resolve,verify_source,review
from compose_lettering import compose
RUN="OUTRUN-KOR-A237-Q161-R11-NATIVE-NANUM-SEPARATED-GLYPH-20261011-0900"
folder="localization/graphics/role_A/20261011-A237-Q161-R11-NANUM-SEPARATED-GLYPH"
out=root/folder;out.mkdir(parents=True,exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def savej(n,d):(out/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def savepng(n,im):
 p=out/n;im.save(p,format="PNG");return {"path":str(p.relative_to(root)),"sha256":sha(p.read_bytes())}
def ref(p):return {"path":str(p.relative_to(root)),"sha256":sha(p.read_bytes())}
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","161"],capture_output=True,text=True)
savej("A237_REWORK_TRIAGE.json",{"returncode":tri.returncode,"stdout":tri.stdout[-6000:],"stderr":tri.stderr[-1500:]})
assert tri.returncode==0,"triage preflight fails closed"
with (root/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 row=next(v for v in csv.DictReader(f) if v["index"]=="161")
assert row["action"]=="localize_text" and "plate_pass" in row["artwork_status"]
srcrel="localization/graphics/role_A/20261011-A236-Q161-THREE-SOURCE-AUTHENTICATED-CLEAN/A236_CANONICAL_ENGLISH_SOURCE_EXACT.dds"
source_path=root/srcrel
srcbytes=source_path.read_bytes()
assert sha(srcbytes)=="a74d31016e9ab38da4f6bd9a37196848534b9a1c8ac04db3f071000030681c4d"
manifestsha="caf59675820b65b4ded62b05e463bfb66c77878a4ba24a4f9ff810e36ff2b9f8"
manifest,plate=resolve(root,161,sha(srcbytes),"AQUARIUS_SOUTH_KOREA_ITALY_CELLS_11_16_24","readable_flip_y",manifestsha)
assert manifest.stem==manifestsha and review(root,manifest,plate)["status"]=="PLATE_PASS"
assert verify_source(root,plate,source_path)["outside_removal_rgba"]==0
clean=Image.open(root/plate["clean"]["path"]).convert("RGBA")
clean_arr=np.array(clean)
x0,y0,x1,y1=717,1671,1013,1725
assert not clean_arr[y0:y1,x0:x1,3].any(),"English residue in certified CLEAN"
# Native font family material change from C349's wide-gap Noto Black.
# Do not fall back silently, or resize previous Korean pixels.
subprocess.run(["sudo","apt-get","install","-qq","-y","fonts-nanum"],check=True,
               stdout=subprocess.DEVNULL)
fontdir=Path("/usr/share/fonts/truetype/nanum")
matches=sorted(fontdir.glob("*ExtraBold*.ttf"))
if not matches:
 matches=sorted(fontdir.glob("*Bold*.ttf"))
assert matches,"Requested native Nanum bold/extra-bold font unavailable"
fontpath=matches[0]
fontbytes=fontpath.read_bytes();font_sha=sha(fontbytes)
font=ImageFont.truetype(str(fontpath),52)
text="물병자리"
# Source original block bbox 296 x 54, font face itself limited to <=50px
# height and positive 1px margins. Width natural; NO squish/stretch/upsampling.
scratch=Image.new("L",(500,100),0)
dr=ImageDraw.Draw(scratch)
dr.text((8,5),text,font=font,fill=255,stroke_width=0)
bb=scratch.getbbox()
assert bb and bb[2]-bb[0]<=280 and bb[3]-bb[1]<=49,(bb,text)
glyph=scratch.crop(bb)
assert glyph.width>=130 and glyph.height>=37,(glyph.width,glyph.height)
# Center within safe 4x4 BC3 blocks, not within a foreign rectangle.
safe=[720,1672,1012,1724]
place_x=safe[0]+(safe[2]-safe[0]-glyph.width)//2
place_y=safe[1]+(safe[3]-safe[1]-glyph.height)//2
assert place_x>718 and place_y>1671 and place_x+glyph.width<1012 and place_y+glyph.height<1725
readable=Image.new("L",(2048,2048),0)
readable.paste(glyph,(place_x,place_y))
# Fixed 8 alpha levels exact to BC3 alpha palette [255,218,182,146,109,73,36,0].
palette=np.array([0,36,73,109,146,182,218,255],dtype=np.uint8)
pix=np.array(readable,dtype=np.uint8)
ix=np.abs(pix.astype(np.int16)[...,None]-palette[None,None,:].astype(np.int16)).argmin(axis=2)
quantized=palette[ix]
assert np.any(quantized>0)
readable=Image.fromarray(quantized,"L")
raw_geo=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
geo_ref=savepng("A237_GEOMETRY_RAW_NATIVE_L.png",raw_geo)
face=Image.new("RGBA",(2048,2048),(60,71,74,0))
face.putalpha(raw_geo)
face_ref=savepng("A237_FACE_RAW_NATIVE_RGBA.png",face)
# Geometry comparison evidence: canonical readable English vs geometry
source_image=Image.open(io.BytesIO(srcbytes)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src_crop=source_image.crop((x0,y0,x1,y1))
geo_crop=readable.crop((x0,y0,x1,y1))
for n,bgcol in (("GRAY",(100,100,100)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
 f1=Image.alpha_composite(Image.new("RGBA",src_crop.size,bgcol+(255,)),src_crop).convert("RGB")
 f2=Image.alpha_composite(Image.new("RGBA",geo_crop.size,bgcol+(255,)),Image.merge("RGBA",(*[Image.new("L",geo_crop.size,col) for col in (60,71,74)],geo_crop))).convert("RGB")
 for pct in (100,75,50):
  if pct!=100:
   w=int(round((x1-x0)*pct/100));h=int(round((y1-y0)*pct/100))
   a=f1.resize((w,h),Image.Resampling.LANCZOS)
   b=f2.resize((w,h),Image.Resampling.LANCZOS)
  else:a=f1;b=f2
  card=Image.new("RGB",(a.width*2,a.height+18),bgcol)
  card.paste(a,(0,18));card.paste(b,(a.width,18))
  d=ImageDraw.Draw(card)
  d.text((2,2),"SOURCE",fill="black" if n=="WHITE" else "white")
  d.text((a.width+2,2),"NATIVE GEO",fill="black" if n=="WHITE" else "white")
  card.save(out/f"A237_SOURCE_GEOMETRY_{n}_{pct}.png")
evidence=ref(out/"A237_SOURCE_GEOMETRY_GRAY_100.png")
geomrecipe={"engine":"pillow-native-font","font_path":str(fontpath),
 "font_sha256":font_sha,"font_family":"NanumGothic native bold","font_size":52,
 "font_license":"Nanum OFL; distribution is not included in this repository",
 "text":text,"original_source_bbox":[x0,y0,x1,y1],
 "source_face_color":[60,71,74],"crop_bbox":list(bb),"rendered_size":[glyph.width,glyph.height],
 "readable_paste_xy":[place_x,place_y],"bc3_palette":palette.tolist(),
 "pixel_orientation":"native_raw_mirror_y","source_provenance":srcrel,
 "method_change":"Nanum native vector instead of rejected A218 Noto Black, source clean C1 approved; no previous glyph bitmap upscale"}
savej("A237_GEOMETRY_RENDERER.json",geomrecipe)
geometry_review={"status":"GEOMETRY_READY","reviewer":"A","route":"native_small",
 "source_sha256":sha(srcbytes),"geometry_sha256":geo_ref["sha256"],
 "observations":{"stroke":"Native Nanum Bold dark face; no Noto Black preserved raster; 100% source still more condensed and heavy, so whole-family match HOLD.",
 "counterspace":"Hangul counters visibly nonempty at native 100 and 50 on black/gray; anti-alias steps quantized to true BC3 discrete alpha.",
 "proportions":f"Original 296x54 source box, new actual native glyph {glyph.width}x{glyph.height}, within original bbox with positive pixel margin. No old Korean resize.",
 "slant":"Source R11 upright flat dark uppercase; new Hangul upright, no arbitrary shear.",
 "readability":"At gray 100/black 50 one glyph phrase is distinguishable; source-family hierarchy remains independent review HOLD."},
 "evidence":[evidence,ref(out/"A237_SOURCE_GEOMETRY_BLACK_50.png")],
 "not_c_pass":True}
savej("A237_GEOMETRY_REVIEW.json",geometry_review)
recipe={"version":"separated-lettering-v1","coordinates":"native_raw","route":"native_small",
 "source":ref(source_path),"geometry":geo_ref,
 "geometry_recipe":ref(out/"A237_GEOMETRY_RENDERER.json"),
 "geometry_review":ref(out/"A237_GEOMETRY_REVIEW.json"),
 "layers":[{"role":"face","input":face_ref}]}
savej("lettering_recipe.json",recipe)
lettering,cm=compose(root,recipe)
assert np.array_equal(np.array(lettering)[:,:,3],np.array(raw_geo)),"face alpha mismatch"
lettering_ref=savepng("A237_LETTERING_COMPOSED_RAW.png",lettering)
# Preserve original q161 official DDS and existing A218 trial; only rewrite
# BC3 R11 blocks strictly inside original English bbox.
a218=root/"localization/graphics/role_A/20261010-A218-Q161-C344-THREE-GLYPH-FACE-REPAIR/A218_Q161_C344_THREE_FACE_REWORK_TRIAL.dds"
a218raw=a218.read_bytes()
assert sha(a218raw)=="8000601ead8b2858b36f8078b92898405b9621ca5b03b553918df8acdf38e05e"
official=root/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/55B57CDE_512x512.dds"
assert sha(official.read_bytes())=="8ded856536184ab0a91e2ee014e8dcfaa5f8e21a5400a4891f459e4a195dda65"
assert a218raw[:128]==srcbytes[:128] and len(a218raw)==128+2048*2048
# Fixed original RGB565 source dark face. The existing A218 method provides
# lossless preservation of 37 unrelated target blocks.
b=bytearray(a218raw)
r,g,blue=60,71,74
rgb565=((r>>3)<<11)|((g>>2)<<5)|(blue>>3)
rgbpart=struct.pack("<HHI",rgb565,rgb565,0)
alpha_vals=[255,0,218,182,146,109,73,36]
def enc(block):
 ids=[min(range(8),key=lambda k:abs(int(v)-alpha_vals[k])) for v in block]
 bits=sum(i<<(3*n) for n,i in enumerate(ids))
 return bytes([255,0])+bits.to_bytes(6,"little")+rgbpart
geo=np.array(raw_geo,dtype=np.uint8)
assert geo.shape==(2048,2048)
# R11 safe block-bounded writable area readable x720..1011/y1672..1723
# corresponds in RAW y=324..375 (2048 -1724.. 2048-1672).
changes=0
for y in range(324,376,4):
 for x in range(720,1012,4):
  of=128+((y//4)*512+x//4)*16
  compressed=enc(geo[y:y+4,x:x+4].reshape(16).tolist())
  if b[of:of+16]!=compressed:
   changes+=1;b[of:of+16]=compressed
assert changes>0
assert b[:128]==a218raw[:128] and len(b)==len(a218raw)
candidate=out/"A237_Q161_R11_UNPROMOTED_SOURCE_GLYPH.dds"
candidate.write_bytes(b)
newsha=sha(b)
assert newsha not in {sha(a218raw),sha(official.read_bytes())}
saved=Image.open(candidate).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
saved_arr=np.array(saved,dtype=np.uint8)
old_arr=np.array(Image.open(a218).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
roi=np.zeros((2048,2048),dtype=bool)
roi[y0:y1,x0:x1]=True
delta=np.any(saved_arr!=old_arr,axis=2)
outside=int(np.count_nonzero(delta&~roi))
assert outside==0,("protected atlas change",outside)
assert np.any(delta)
# Check actual NEW glyph is visible, old strokes do not survive cleared safe
# region outside redesigned face (BC3 alpha stays truly zero).
final_crop=saved_arr[y0:y1,x0:x1]
final_alpha=(final_crop[:,:,3]>0)
intended=np.array(readable)[y0:y1,x0:x1]>0
extraneous=int(np.count_nonzero(final_alpha&~intended))
missing=int(np.count_nonzero(intended&~final_alpha))
assert extraneous==0 and missing==0,(extraneous,missing)
bb_saved=Image.fromarray((final_alpha*255).astype(np.uint8),"L").getbbox()
assert bb_saved
assert bb_saved[0]>0 and bb_saved[1]>0 and bb_saved[2]<(x1-x0) and bb_saved[3]<(y1-y0)
# BGW comparative persisted DDS and RAW crop, source + A218 + NEW
for n,bgcol in (("GRAY",(100,100,100)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
 imgs=[]
 for img in (source_image,Image.open(a218).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),saved):
  crop=img.crop((x0,y0,x1,y1))
  imgs.append(Image.alpha_composite(Image.new("RGBA",crop.size,bgcol+(255,)),crop).convert("RGB"))
 for percent in (100,75,50):
  tiles=[]
  for im in imgs:
   if percent==100:tiles.append(im)
   else:tiles.append(im.resize((int(round(im.width*percent/100)),int(round(im.height*percent/100))),Image.Resampling.LANCZOS))
  w,h=tiles[0].size
  sheet=Image.new("RGB",(3*w,h+20),bgcol);dd=ImageDraw.Draw(sheet)
  for j,(im,name) in enumerate(zip(tiles,("SOURCE","A218 TRIAL","A237 SAVED"))):
   sheet.paste(im,(j*w,20));dd.text((j*w+2,2),name,fill="black" if n=="WHITE" else "white")
  sheet.save(out/f"A237_COMPARE_{n}_{percent}.png")
saved.crop((x0,y0,x1,y1)).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out/"A237_SAVED_R11_ACTUAL_RAW.png")
# Report fail-close: native review only, no claim font/source visual match or C1 PASS
report={"role":"A","run_key":RUN,"index":161,"cell":"R11_AQUARIUS_TO_물병자리",
 "canonical_source_sha256":sha(srcbytes),"c1_approved_plate_manifest":manifestsha,
 "plate_sha256":plate["clean"]["sha256"],"prior_trial_sha256":sha(a218raw),
 "official_sha256":sha(official.read_bytes()),"new_trial_sha256":newsha,
 "new_trial_path":str(candidate.relative_to(root)),"codec":"BC3/DXT5",
 "native":[2048,2048],"source_original_bbox":[x0,y0,x1,y1],
 "glyph_bbox_local":list(bb_saved),"native_glyph_wh":[glyph.width,glyph.height],
 "changed_blocks":changes,"changed_rgba_pixels":int(delta.sum()),"outside_region_changes":outside,
 "source_remaining_alpha_in_clean":0,"decoder_exact_glyph_silhouette":extraneous==0 and missing==0,
 "other_37_cells_unchanged":True,"font_sha256":font_sha,
 "lettering_recipe":ref(out/"lettering_recipe.json"),
 "composed_lettering_sha256":lettering_ref["sha256"],
 "geometry_ready":"A_PRODUCER_GEOMETRY_READY_SCOPED",
 "producer_decision":"SCOPED_TRIAL_REQUIRES_CONTROLLER_NATIVE_FIRST_LOOK",
 "whole_atlas":"REWORK_REQUIRED_UNPROMOTED",
 "C1":"NOT_RUN_NEW_SHA","C3":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
 "game_retest":"NOT_RUN","new_official_dds":0,
 "root_cause":"C349 source hierarchy underfill in old A218; A237 new native glyph geometry/face family, cannot infer visual PASS from numeric scope",
 "backend":"GitHub runner: canonical BC3 unavailable to local container (DNS disabled)",
 "next":"Independent first-look producer optical verdict; record HOLD if source hierarchy deviates. New C1 only for distinct saved SHA."}
savej("A237_MACHINE_AND_PRODUCER_HANDOFF.json",report)
print(json.dumps({"A237":"NEW_UNPROMOTED_DDS","sha":newsha,"bbox":bb_saved,"outside":outside,"blocks":changes}))
