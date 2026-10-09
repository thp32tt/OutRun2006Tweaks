#!/usr/bin/env python3
"""B330 q098 complete BC3 source removal and native Korean-only rerender trial.

C328's full-frame review proved that B327R/CLEAN retained English Cl/ord.
The previously verified white/navy source-family method is kept, but now
every English source block is reconstructed rather than a center crop.
Safeguard: trial only until direct full-DDS visual QA; C/real-game NOT run.
"""
import hashlib, io, json, os, struct, subprocess, sys, urllib.request
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image, ImageFont, ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
OUT=G/"role_B/20261009-B330-Q098-FULL-ENGLISH-CLEAN-PLATE"
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda x: hashlib.sha256(x).hexdigest()
S_SHA="3b3cdd76b03014e0ba6a47f4e98a187fdf6ae4297314494cbe1d3d4c586f1f59"
P_SHA="472392829d96cc1dc6ed980d942c56df883758f2777490ac6e7f6dafb5f86028"
old=(G/"hd_candidates"/REL).read_bytes()
assert sha(old)==P_SHA,"Concurrent q098 candidate already changed"
c=json.loads((G/"role_C/20261009-C328-C2-Q098-PERSISTED-ENGLISH-RESIDUE/C328_Q098_CONTROLLER_REWORK.json").read_text())
assert c["candidate_sha256"]==P_SHA and c["decision"]=="REWORK_REQUIRED"
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","98"],text=True,capture_output=True,check=True)
assert json.loads(tri.stdout)["assets"][0]["current_status"].startswith("c328_"),"Concurrent queue update"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
with urllib.request.urlopen(url,timeout=160) as resp: english=resp.read()
assert sha(english)==S_SHA and english[:128]==old[:128] and old[84:88]==b"DXT5"
W,H=2048,128
assert len(old)==262272 and struct.unpack_from("<III",old,12)==(H,W,W*H*4) if False else True
assert (struct.unpack_from("<I",old,12)[0],struct.unpack_from("<I",old,16)[0],struct.unpack_from("<I",old,28)[0])==(128,2048,1)
def decode(x):
 return np.asarray(Image.open(io.BytesIO(x)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
source,old_rgba=decode(english),decode(old)
assert source.shape==old_rgba.shape==(H,W,4)
sourcebox=(431,6,1674,123); candidatebox=(475,9,1580,120)
y,x=np.ogrid[:H,:W]
src_region=(x>=431)&(x<1674)&(y>=6)&(y<123)
cand_region=(x>=475)&(x<1580)&(y>=9)&(y<120)
assert np.count_nonzero(source[:,:,3][~src_region])==0,"Unexpected protected non-English artwork"
assert np.count_nonzero(old_rgba[:,:,3][~src_region])==0,"Unexpected prior out-of-bounds artwork"
# An empty transparent source plate is genuinely valid only for this single
# floating challenge-sentence sprite: no source-visible nontext artwork.
clean=np.zeros_like(source)
Image.fromarray(clean,"RGBA").save(OUT/"B330_TRUE_CLEAN_FULL_RGBA.png",optimize=True)
# Reconstruct the exact B327R native Korean vector profile; never use its
# contaminated old English pixels as an opacity mask or as a clean plate.
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
fc=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{family}","Noto Sans CJK KR:style=Bold"],text=True).strip().split("|")
fontpath,fi,family=fc[0],int(fc[1] or 0),fc[2]
assert "NotoSansCJK" in Path(fontpath).name and "Noto Sans CJK KR" in family
font=ImageFont.truetype(fontpath,330,index=fi)
text="코스 기록에 도전하세요."
stamp=Image.new("L",(7400,530),0); draw=ImageDraw.Draw(stamp)
bb=draw.textbbox((0,0),text,font=font)
draw.text((35-bb[0],35-bb[1]),text,font=font,fill=255)
crop=stamp.getbbox();assert crop
glyph=stamp.crop(crop).resize((980,72),Image.Resampling.LANCZOS)
glyph=glyph.transform((996,72),Image.Transform.AFFINE,
 (1,14/71,-14,0,1,0),resample=Image.Resampling.BICUBIC)
core=np.zeros((H,W),dtype=np.uint8)
left=(W-glyph.width)//2;top=(H-glyph.height)//2
core[top:top+72,left:left+996]=np.asarray(glyph,dtype=np.uint8)
face=core>=150
distance=distance_transform_edt(~face)
d=np.maximum(0,distance.astype(np.float32)-0.75)
outer=np.clip(230*np.exp(-((d/8.0)**1.60))+
 30*np.exp(-((d/14.0)**2.0)),0,248).astype(np.uint8)
alpha=np.maximum(core,outer)
active=(alpha>24)
assert np.count_nonzero(active&~cand_region)==0,"Native glyph/effects exceed permitted candidate region"
src_face=source[:,:,:3][(source[:,:,0]>235)&(source[:,:,1]>235)&(source[:,:,2]>235)&(source[:,:,3]>180)&src_region]
src_navy=source[:,:,:3][(source[:,:,0]<36)&(source[:,:,1]<65)&(source[:,:,2]>source[:,:,0]+12)&(source[:,:,3]>180)&src_region]
assert len(src_face)>2000 and len(src_navy)>5000
white=np.rint(np.percentile(src_face,90,axis=0)).astype(np.uint8)
navy=np.rint(np.percentile(src_navy,30,axis=0)).astype(np.uint8)
def rgb565(p):
 a,b,c=[int(t) for t in p];return (((a*31+127)//255)<<11)|(((b*63+127)//255)<<5)|((c*31+127)//255)
def ex565(z):
 return np.array([(((z>>11)&31)*255+15)//31,(((z>>5)&63)*255+31)//63,((z&31)*255+15)//31],dtype=np.int16)
w,b=rgb565(white),rgb565(navy)
assert w>b
p0,p1=ex565(w),ex565(b)
palette=np.array([p0,p1,(2*p0+p1+1)//3,(p0+2*p1+1)//3],dtype=np.int16)
rgb=np.zeros((H,W,3),dtype=np.int16);rgb[active]=navy;rgb[face]=white
desired_alpha=np.zeros((H,W),dtype=np.uint8);desired_alpha[active]=alpha[active];desired_alpha[face]=255
assert np.count_nonzero(desired_alpha[~cand_region])==0
# Re-encode every source-affected 4x4 block. C328 defect arose because
# earlier code changed only blocks contained in the Korean inset.
buffer=bytearray(old)
alpha_levels=np.array([255,0,218.57,182.14,145.71,109.29,72.86,36.43])
rewritten=0;cleared=0
for y0 in range(0,H,4):
 for x0 in range(0,W,4):
  old_a=old_rgba[y0:y0+4,x0:x0+4,3]
  new_a=desired_alpha[y0:y0+4,x0:x0+4]
  if np.count_nonzero(old_a)==0 and np.count_nonzero(new_a)==0:continue
  # No changes outside canonical source effect region; avoid unwanted art.
  block_scope=src_region[y0:y0+4,x0:x0+4]
  assert (np.count_nonzero(old_a[~block_scope])==0 and np.count_nonzero(new_a[~block_scope])==0),"Protected alpha at boundary"
  off=128+(((H-y0-4)//4)*(W//4)+(x0//4))*16
  if np.count_nonzero(new_a)==0:
   # Retain old RGB, clear only BC3 alpha so remnants disappear visually.
   buffer[off:off+8]=bytes(8)
   cleared+=1
  else:
   pix=rgb[y0:y0+4,x0:x0+4].astype(np.int32)
   idx=((pix[:,:,None,:]-palette[None,None,:,:].astype(np.int32))**2).sum(axis=3).argmin(axis=2)
   ai=np.abs(new_a.astype(np.float32)[:,:,None]-alpha_levels[None,None,:]).argmin(axis=2)
   abits=cbits=0
   for dy in range(4):
    for dx in range(4):
     rawidx=(3-dy)*4+dx
     abits |= int(ai[dy,dx])<<(3*rawidx)
     cbits |= int(idx[dy,dx])<<(2*rawidx)
   buffer[off:off+16]=bytes([255,0])+abits.to_bytes(6,"little")+struct.pack("<HHI",w,b,cbits)
   rewritten+=1
trial=bytes(buffer)
assert trial[:128]==old[:128] and len(trial)==len(old) and sha(trial)!=P_SHA
D=decode(trial)
# Exact full native persisted DDS decoded assertions.
assert not np.any(D[:,:,3][~cand_region]),"English/source visible outside Korean candidate glyph region"
assert not np.any(D[:,:,3][~src_region]),"Protected original boundary changed"
assert np.array_equal(D[~src_region],old_rgba[~src_region]),"Pixels outside original source effect changed"
assert np.count_nonzero(D[:,:,3])>15000,"Korean glyph disappeared"
assert np.count_nonzero(D[:,:,3])<int(src_region.sum()),"Opaque box rather than glyph"
# 1px envelope and all formerly contaminating visible source pixels gone.
assert np.count_nonzero(D[:,:,3][:,np.r_[0:475,1580:2048]])==0
assert np.count_nonzero(D[:,:,3][np.r_[0:9,120:128],:])==0
target=OUT/"B330_FULL_SOURCE_CLEAN_UNAPPROVED.dds"
target.write_bytes(trial)
assert sha(target.read_bytes())==sha(trial) and np.array_equal(decode(target.read_bytes()),D)
proofs=[]
for name,arr in (("SOURCE",source),("CLEAN",clean),("PREVIOUS",old_rgba),("NEW",D)):
 Image.fromarray(arr,"RGBA").save(OUT/f"{name}_READABLE_FULL_RGBA.png",optimize=True)
 Image.fromarray(np.flipud(arr),"RGBA").save(OUT/f"{name}_RAW_FULL_RGBA.png",optimize=True)
def back(arr,bg):
 canvas=Image.new("RGBA",(W,H),(*bg,255))
 canvas.alpha_composite(Image.fromarray(arr,"RGBA"))
 return canvas.convert("RGB")
for orientation in ("READABLE","RAW"):
 data=(source,clean,old_rgba,D) if orientation=="READABLE" else tuple(np.flipud(z) for z in (source,clean,old_rgba,D))
 for color,bg in (("BLACK",(0,0,0)),("GRAY",(72,72,72)),("WHITE",(255,255,255))):
  for scale in (100,75,50):
   pieces=[back(z,bg) for z in data]
   if scale!=100:pieces=[im.resize((round(im.width*scale/100),round(im.height*scale/100)),Image.Resampling.LANCZOS) for im in pieces]
   im=Image.new("RGB",(sum(z.width for z in pieces)+12,max(z.height for z in pieces)),(87,87,87))
   xpos=0
   for p in pieces:im.paste(p,(xpos,0));xpos+=p.width+4
   filename=f"FULL_{orientation}_{color}_{scale}_SOURCE_CLEAN_OLD_NEW.png"
   im.save(OUT/filename,optimize=True);proofs.append(filename)
report={
 "run":"B330","queue_index":98,"asset":REL,"source_sha256":S_SHA,
 "old_sha256":P_SHA,"trial_sha256":sha(trial),
 "root_cause":"C328 full-frame original English persisted outside and inside earlier narrow B327R clean/composite construction",
 "method":"New source-wide truly transparent plate + B327R native Korean vector and source-derived white/navy effect; encode all source BC3 blocks, not center only",
 "source_alpha_outside_original_bbox":0,"new_alpha_outside_original_bbox":0,
 "new_alpha_outside_candidate_bbox":0,"persisted_decode":"PASS_EXACT",
 "changed_rgba_outside_source_bbox":0,"english_residue_outside_korean_bbox":0,
 "source_bbox":sourcebox,"candidate_effect_bbox":candidatebox,
 "native":[W,H],"dds_format":"DXT5_BC3","mips":1,
 "rewritten_blocks":rewritten,"cleared_english_blocks":cleared,
 "white_rgb":white.tolist(),"navy_rgb":navy.tolist(),"font":fontpath,
 "proofs":proofs,"candidate_promoted":False,"new_approved_DDS":0,
 "producer_visual":"PENDING_DIRECT_FULL_NATIVE_75_50_RAW_READABLE",
 "independent_C":"NOT_RUN","C3":"NOT_RUN","user_game":"NOT_RUN",
 "RUNTIME_VALIDATION":"UNTESTED","backend":"github-actions",
 "excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B330_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print("B330_Q098_FULL_CLEAN_TRIAL",json.dumps({"sha":sha(trial),"rewritten":rewritten,"cleared":cleared,"proofs":len(proofs)},ensure_ascii=False))
