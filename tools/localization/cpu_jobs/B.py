#!/usr/bin/env python3
"""B262 post-publish persisted-DDS native/practical/raw QA evidence; no pixel rewrite."""
import hashlib, io, json, os, struct, tempfile, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
if os.getenv("OUTRUN_CPU_WORKER")!="github-actions" or os.getenv("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub worker only")
root=Path.cwd();gfx=root/"localization/graphics";run=gfx/"role_B/20261008-B262-Q172-SOURCE-GOLD-BEVEL"
sha=lambda b:hashlib.sha256(b).hexdigest()
rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
asset=gfx/"hd_candidates"/rel
expected="15f58551dff16c000c57763a469c4ae1d6f2c8e35c9e5dd1b44259c25bc2e8d0"
source_sha="d5f4a36d5ef1285555ca8fc045e54d160876d1b3e33c6fbc45668c24566c2cf8"
prior_sha="7282687bbc3f5b4e7ea45c03043d84b27204a5b183a8eaa9a08c35bb63eb84e2"
b=asset.read_bytes()
if sha(b)!=expected:raise RuntimeError(("q172 changed concurrently",sha(b)))
url=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
 "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/"
 "Release/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds")
with tempfile.TemporaryDirectory(prefix="b262_validate_") as tmp:
    p=Path(tmp)/"source.dds";urllib.request.urlretrieve(url,p);e=p.read_bytes()
if sha(e)!=source_sha:raise RuntimeError("source SHA changed")
if b[:128]!=e[:128]:raise RuntimeError("header drift")
def decode(x):
    return Image.open(io.BytesIO(x)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src=decode(e);cur=decode(b)
curarr=np.asarray(cur);srcarr=np.asarray(src)
clean=Image.open(gfx/"role_B/20261008-B255-Q172-EXPLICIT-KOREAN-FONT-SHEAR/CLEAN.png").convert("RGBA")
clean_sha="9a0750d0db62345a21dbf4006f2da0b2fe7e96151f40dd5e3d1f5e422bd1d809"
if sha((gfx/"role_B/20261008-B255-Q172-EXPLICIT-KOREAN-FONT-SHEAR/CLEAN.png").read_bytes())!=clean_sha:raise RuntimeError("clean changed")
regions=[("START","출발",[55,373,136,396]),("GOAL","골",[595,635,672,659])]
allowed=np.zeros((1024,1024),bool)
for _,_,(x0,y0,x1,y1) in regions:allowed[y0:y1,x0:x1]=True
outside=int(np.count_nonzero(np.any(srcarr!=curarr,axis=2)&~allowed))
alpha=int(np.count_nonzero((srcarr[:,:,3]!=curarr[:,:,3])&~allowed))
if outside or alpha:raise RuntimeError(("out-of-bound change",outside,alpha))
if not np.array_equal(np.asarray(Image.open(run/"FINAL_DECODED.png").convert("RGBA")),curarr):
    raise RuntimeError("previous FINAL png did not equal persisted DDS")
if not np.array_equal(np.asarray(Image.open(run/"FINAL_RAW.png").convert("RGBA")),np.flipud(curarr)):
    raise RuntimeError("previous RAW png not flip equivalent")
observations=[]
for name,ko,bb in regions:
    x0,y0,x1,y1=bb
    t=[]
    for scale in [100,75,50]:
        images=[]
        for nameplate,im in [("SOURCE",src),("CLEAN",clean),("FINAL DDS",cur)]:
            crop=im.crop((x0-8,y0-8,x1+8,y1+8))
            back=Image.new("RGB",crop.size,(95,95,95))
            back.paste(crop,mask=crop.getchannel("A"))
            pix=back.resize((max(1,int(back.width*scale/100)),max(1,int(back.height*scale/100))),Image.Resampling.LANCZOS)
            images.append(pix)
        # Gray bar shows stage boundary, never overwrites source/full-res assets.
        gap=12;w=sum(x.width for x in images)+gap*2;h=max(x.height for x in images)
        card=Image.new("RGB",(w,h),(80,80,80));x=0
        for im in images:card.paste(im,(x,0));x+=im.width+gap
        card.save(run/f"{name}_PRACTICAL_{scale}.png")
        t.append(str((run/f"{name}_PRACTICAL_{scale}.png").relative_to(root)))
    for orientation,views in [("RAW",[src.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
                                          clean.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
                                          cur.transpose(Image.Transpose.FLIP_TOP_BOTTOM)])]:
        ry0=1024-y1;ry1=1024-y0
        tiles=[]
        for im in views:
            crop=im.crop((x0-8,ry0-8,x1+8,ry1+8))
            back=Image.new("RGB",crop.size,(95,95,95))
            back.paste(crop,mask=crop.getchannel("A"))
            tiles.append(back.resize((back.width*5,back.height*5),Image.Resampling.NEAREST))
        card=Image.new("RGB",(sum(x.width for x in tiles)+24,max(x.height for x in tiles)),(90,90,90));x=0
        for im in tiles:card.paste(im,(x,0));x+=im.width+12
        card.save(run/f"{name}_SOURCE_CLEAN_FINAL_RAW.png")
    observations.append({"label":name,"korean":ko,"source_bbox":bb,"practical_evidence":t,
                          "raw_evidence":str((run/f"{name}_SOURCE_CLEAN_FINAL_RAW.png").relative_to(root)),
                          "source_relative_style":"NOT_AUTO_APPROVED_CONTROLLER_VISUAL_PENDING"})
qa={"run":"B262","queue_index":172,"source_sha256":source_sha,"candidate_sha256":expected,
    "clean_plate_sha256":clean_sha,"candidate_prior_sha256":prior_sha,
    "decoded_current_exact":"PASS","native_size":[1024,1024],"mips":1,
    "changed_rgba_outside_source_regions":outside,"alpha_outside_source_regions":alpha,
    "native_100_75_50_raw":observations,
    "source_slant_per_glyph":"UNMEASURED; do not assert source-style PASS",
    "source_family_visual":"HOLD_FOR_CONTROLLER_JUDGMENT",
    "independent_c":"PENDING","c3":"PENDING","runtime_validation":"UNTESTED",
    "execution_backend":"GITHUB_ACTIONS_EPHEMERAL"}
(run/"B262_POST_ENCODE_NATIVE_PRACTICAL_RAW_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"qa":"PASS_NUMERIC_HOLD_VISUAL","asset_sha":expected,"native_100_75_50_raw":len(observations)},ensure_ascii=False))
