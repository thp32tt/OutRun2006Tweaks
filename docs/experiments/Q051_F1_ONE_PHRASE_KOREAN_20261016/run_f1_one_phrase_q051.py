#!/usr/bin/env python3
"""F1 isolated single-label TEST_ONLY Korean overlay for Q051 with exact source constraints."""
from pathlib import Path
import json,hashlib,io
from PIL import Image,ImageDraw
import numpy as np
BASE=Path("/home/chatgpt-runner2/work/c_salvage_text_roi")
OUT=BASE/"F0_Q051_NATIVE_DDS_20261016"
SOURCE=BASE/"source_full_20261012"/"q051_FF2462BB_GITHUB_HD_SOURCE_20261015.dds"
CLEAN=OUT/"Q051_TIME_ONLY_CLEAN_F0_TEST_ONLY.dds"
SPRITE=OUT/"F1_Q051_TIME_KO_SOURCE_Q32_TEST_ONLY.png"
READ=BASE/"source_full_20261012"/"q051_FF2462BB_FLIPY_CHECK_ORIENTATION.png"
EXPECTED={"source":"5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67",
"clean":"7c1a81b1570ffc910d71ea25d05819d93c8ed0a80be7d2c0437fce6b43fbdd43",
"read":"2da1b6f01219356ddc6ea925bd8fcd4afd37d9040eb48081a40861cc649da6f0",
"sprite":"91ba2ec11302f468d1bf2a900fd35c6803d9852c9db1ba87c044c9916a67e474"}
def sha(b):return hashlib.sha256(b).hexdigest()
for name,p,key in (("SOURCE",SOURCE,"source"),("CLEAN",CLEAN,"clean"),("READABLE",READ,"read"),("SPRITE",SPRITE,"sprite")):
 if sha(p.read_bytes())!=EXPECTED[key]:raise RuntimeError(name+"_SHA_PIN_MISMATCH")
R=(1595,608,1845,727)
x0,y0,x1,y1=R
# Original effects mask extent in readable coords: (x+32,y+26,x+241,y+101), recovered from source alpha.
safe=(x0+32+2,y0+26+2,x0+241-2,y0+101-2)
SAFE_W=safe[2]-safe[0];SAFE_H=safe[3]-safe[1]
with Image.open(SPRITE) as s:
 s.load()
 sprite=s.convert("RGBA")
assert sprite.size==(299,126)
# FASTOCTREE palette changed original alpha 0->1..8 and 253->251..253.
# Restore exact transparent background and the nearly-opaque core;
# retain intermediate edge alpha, instead of baking black background.
rgba=np.asarray(sprite).copy()
a=rgba[:,:,3]
assert int((a<=8).sum())>5000 and int((a>=250).sum())>1000
rgba[:,:,3][a<=8]=0
rgba[:,:,3][a>=250]=255
rgba[:,:,:3][rgba[:,:,3]==0]=0
sprite=Image.fromarray(rgba,mode="RGBA")
a=np.asarray(sprite.getchannel("A"))
assert int((a==0).sum())>5000 and int((a==255).sum())>1000
bbox=sprite.getchannel("A").getbbox()
assert bbox is not None and bbox[0]>=0 and bbox[1]>=0
sprite=sprite.crop(bbox)
original_sprite_size=list(sprite.size)
factor=min(1.0,SAFE_W/sprite.width,SAFE_H/sprite.height)
nw=max(1,int(sprite.width*factor));nh=max(1,int(sprite.height*factor))
sprite=sprite.resize((nw,nh),resample=Image.Resampling.LANCZOS)
ix=safe[0]+(SAFE_W-nw)//2;iy=safe[1]+(SAFE_H-nh)//2
assert ix>=safe[0] and iy>=safe[1] and ix+nw<=safe[2] and iy+nh<=safe[3]
# The source CLEAN removed exactly the original TIME effect component; make sure
# no residual alpha remains in the full original cropped cell before paste.
with Image.open(CLEAN) as q:
 clean=q.convert("RGBA")
 native=clean.tobytes()
assert clean.size==(4096,2048)
with Image.open(SOURCE) as o:
 source=o.convert("RGBA")
 before=source.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop(R)
clean_R=clean.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop(R)
assert clean_R.getchannel("A").getbbox() is None
layer=Image.new("RGBA",(x1-x0,y1-y0),(0,0,0,0))
layer.alpha_composite(sprite,dest=(ix-x0,iy-y0))
bb=layer.getchannel("A").getbbox()
assert bb and bb[0]>=safe[0]-x0 and bb[1]>=safe[1]-y0 and bb[2]<=safe[2]-x0 and bb[3]<=safe[3]-y0
# A single DDS writer, native RAW pixels, exact original header and orientation.
clean_bytes=CLEAN.read_bytes()
raw=bytearray(clean_bytes)
rgba=np.asarray(layer)
changed_pixels=0
for rel_y in range(y1-y0):
 native_y=2048-1-(y0+rel_y)
 for rel_x in range(x1-x0):
  pixel=rgba[rel_y,rel_x]
  if pixel[3]==0: continue
  if clean_R.getpixel((rel_x,rel_y))[3] != 0:
   raise RuntimeError("TEXT_LAYER_OVERLAPS_UNCLEARED_SOURCE")
  ofs=128+(native_y*4096+(x0+rel_x))*4
  raw[ofs:ofs+4]=bytes(pixel)
  changed_pixels+=1
assert raw[:128]==clean_bytes[:128] and len(raw)==len(clean_bytes)==33554560
output=OUT/"Q051_TIME_KO_F1_TEST_ONLY.dds"
if output.exists() and sha(output.read_bytes())!=sha(raw):
 raise RuntimeError("F1_DIFFERENT_EXISTING_CANDIDATE_NO_OVERWRITE")
if not output.exists():output.write_bytes(raw)
assert output.read_bytes()==raw
with Image.open(output) as decoded:
 decoded_rgba=decoded.convert("RGBA")
 check=decoded_rgba.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop(R)
# Transparent RGB in CLEAN DDS is genuine source-derived blue, not RGBA zero.
# Alpha and every visible pixel must match the newly generated layer.
cmp=np.asarray(check); ref=np.asarray(layer)
assert np.array_equal(cmp[:,:,3],ref[:,:,3])
assert np.array_equal(cmp[:,:,:3][ref[:,:,3]>0],ref[:,:,:3][ref[:,:,3]>0])
# Byte-range protection proof: every non-ROI DDS byte same as SOURCE except
# CLEAN removal already proven inside ROI. Compare difference with CLEAN and SOURCE.
with Image.open(output) as dec:
 f1_native=np.asarray(dec.convert("RGBA"))
with Image.open(SOURCE) as orig:
 src_native=np.asarray(orig.convert("RGBA"))
xor=np.any(f1_native!=src_native,axis=2)
native_y0=2048-y1;native_y1=2048-y0
assert not np.any(xor[:native_y0,:]) and not np.any(xor[native_y1:,:])
assert not np.any(xor[native_y0:native_y1,:x0]) and not np.any(xor[native_y0:native_y1,x1:])
# Also test no new visible pixels outside original text effect safe bbox.
f1_read=np.asarray(check)
sm=np.asarray(clean_R)
f1_alpha=f1_read[:,:,3]
assert not np.any(f1_alpha[:safe[1]-y0,:]) and not np.any(f1_alpha[safe[3]-y0:,:])
assert not np.any(f1_alpha[:, :safe[0]-x0]) and not np.any(f1_alpha[:,safe[2]-x0:])
# Source/new preview: navy mock backing exclusively for human viewing.
def render(im):
 back=Image.new("RGBA",im.size,(0,10,57,255))
 back.alpha_composite(im)
 return back.convert("RGB")
left=render(before);right=render(check)
w,h=left.size
panel=Image.new("RGB",(w*2+20,h+32),(17,21,38))
panel.paste(left,(0,32));panel.paste(right,(w+20,32))
d=ImageDraw.Draw(panel);d.text((3,7),"EN SOURCE",fill=(255,255,255));d.text((w+22,7),"KO F1 TEST_ONLY",fill=(255,255,255))
preview=OUT/"Q051_TIME_F1_KO_COMPARE_TEST_ONLY.png"
panel.save(preview)
png=OUT/"Q051_TIME_F1_KO_RGBA_LAYER_TEST_ONLY.png"
layer.save(png)
report={
"schema":"outrun-q051-f1-one-phrase-v1",
"source_dds_sha256":EXPECTED["source"],
"clean_dds_sha256":EXPECTED["clean"],
"user_supplied_generated_korean_sheet":"54.png (local ChatGPT attachment)",
"extracted_sprite_input_sha256":EXPECTED["sprite"],
"extracted_sprite_was_reduced_to_32_color_palette":"QUALITY_TRADEOFF_TEST_ONLY",
"source_translation":"TIME","korean":"시간",
"source_glyph_bbox_readable_xyxy":[x0+32,y0+26,x0+241,y0+101],
"safe_bbox_readable_xyxy":list(safe),
"source_label_bbox_readable_xyxy":list(R),
"sprite_original_size":original_sprite_size,
"sprite_scaled_to":[nw,nh],"scale_factor":factor,
"sprite_paste_readable_xy":[ix,iy],
"sprite_layer_alpha_positive_px":int((f1_alpha>0).sum()),
"dds_changed_pixel_count_vs_full_source":int(xor.sum()),
"outside_text_source_roi_protected_pixels_exact":True,
"saved_DDS_redecode_visible_pixel_and_alpha_exact":True,
"transparent_RGB_is_retained_from_CLEAN_not_forced_to_zero":True,
"raw_direction_restored":True,"source_header_preserved":True,
"mip_count":1,"DDS_FORMAT":"RGBA32_UNCOMPRESSED",
"artifacts":{p.name:sha(p.read_bytes()) for p in (output,preview,png)},
"F1_STATIC":"PASS_CANDIDATE",
"runtime_validation":"WAIVED_BY_USER_FOR_THIS_TEST_UNTESTED_NOT_PASS",
"C1":"NOT_RUN","C3":"NOT_RUN",
"approval":"TEST_ONLY_NOT_GAME_RELEASE","no_live_container_or_original_modified":True}
path=OUT/"Q051_TIME_F1_REPORT.json"
path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False,indent=2))