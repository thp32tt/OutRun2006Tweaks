#!/usr/bin/env python3
"""B327R q098: separate full-face source-family white/navy BC3 reconstruction.

Experiment is QA-gated: do NOT replace the hd_candidates DDS until a human
controller inspects the source/CLEAN/trial's persisted bytes.
"""
import hashlib, io, json, os, struct, subprocess, sys, tempfile, urllib.request
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image,ImageFont,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "B":
    raise SystemExit("B327 requires GitHub hosted access to SHA-pinned source DDS")
root = Path.cwd()
gfx = root / "localization/graphics"
relative = "textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
target = gfx / "hd_candidates" / relative
run = gfx / "role_B/20261009-B327R-Q098-NATIVE-NAVY-HALO-REBUILD"
run.mkdir(parents=True, exist_ok=True)
def SHA(x): return hashlib.sha256(x).hexdigest()
old_sha = "192d627428dfa4328035d5105dcfbd4395d8bbadfa154a9f533a1c48583eac4b"
source_sha = "3b3cdd76b03014e0ba6a47f4e98a187fdf6ae4297314494cbe1d3d4c586f1f59"
maskpath = gfx/"role_B/20261005-B-PRODUCTION40/42E618FD_TARGET_TEXT_MASK.png"
cleanpath = gfx/"role_B/20261005-B-PRODUCTION40/42E618FD_CLEAN_PLATE.png"
srcmaskpath = gfx/"role_B/20261005-B-PRODUCTION40/42E618FD_SOURCE_TEXT_MASK.png"
tri = subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","98"],text=True,capture_output=True,check=True)
old = target.read_bytes()
assert SHA(old)==old_sha, "q098 concurrently changed; do not touch"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
with tempfile.TemporaryDirectory(prefix="b327_github_") as tmp:
    original = Path(tmp)/"source.dds"
    urllib.request.urlretrieve(url,original)
    english = original.read_bytes()
assert SHA(english)==source_sha, "canonical source SHA mismatch"
assert english[:128]==old[:128] and old[84:88]==b"DXT5", "native DXT5 header"
width,height=struct.unpack_from("<II",old,16)[0],struct.unpack_from("<I",old,12)[0]
assert (width,height,struct.unpack_from("<I",old,28)[0],len(old))==(2048,128,1,262272)
def decode(bs):
    return np.asarray(Image.open(io.BytesIO(bs)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
source=decode(english)
previous=decode(old)
clean=np.asarray(Image.open(cleanpath).convert("RGBA"),dtype=np.uint8)
targetmask=np.asarray(Image.open(maskpath).convert("L"),dtype=np.uint8)
sourcemask=np.asarray(Image.open(srcmaskpath).convert("L"),dtype=np.uint8)
assert source.shape==previous.shape==clean.shape==(height,width,4)
assert targetmask.shape==sourcemask.shape==(height,width)
bbox=(431,6,1674,123)
targetbox=(475,9,1580,120)
yy,xx=np.ogrid[:height,:width]
source_region=(xx>=bbox[0])&(xx<bbox[2])&(yy>=bbox[1])&(yy<bbox[3])
allowed=(xx>=targetbox[0])&(xx<targetbox[2])&(yy>=targetbox[1])&(yy<targetbox[3])
source_clean_out=int(np.any(source!=clean,axis=2)[~source_region].sum())
source_alpha_unremoved=int(np.count_nonzero(clean[:,:,3][(sourcemask>80)&source_region]>16))
if source_clean_out or source_alpha_unremoved:
    raise RuntimeError(("PLATE_ONLY_GATE failed",source_clean_out,source_alpha_unremoved))
# B327 METHOD CHANGE after C310/B300/B301. Native face, navy keyline, and
# diffuse glow are generated together from a fresh CJK vector raster on CLEAN.
# Unlike B301's RGB recolor, ALPHA geometry changes too; no old-pixel whitening.
triread=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","98"],capture_output=True,text=True,check=True)
triage=json.loads(triread.stdout)["assets"][0]
assert triage["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),triage
old_producer_status=triage["current_status"]
subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
fc=subprocess.check_output(["fc-match","-f","%{file}|%{index}|%{family}","Noto Sans CJK KR:style=Bold"],text=True).strip().split("|")
fontpath,faceindex,family=fc[0],int(fc[1] or 0),fc[2]
assert "NotoSansCJK" in Path(fontpath).name and "Noto Sans CJK KR" in family
font=ImageFont.truetype(fontpath,330,index=faceindex)
tofu=bytes(font.getmask(chr(0x10ffff)))
for ch in "코스 기록에 도전하세요.":
 if ch!=" ":
  assert bytes(font.getmask(ch))!=tofu and any(font.getmask(ch)),("missing glyph",ch)
stamp=Image.new("L",(7400,530),0)
draw=ImageDraw.Draw(stamp)
text="코스 기록에 도전하세요."
bb=draw.textbbox((0,0),text,font=font)
draw.text((35-bb[0],35-bb[1]),text,font=font,fill=255)
crop=stamp.getbbox()
assert crop, "empty native lettering"
# Original vector at 330 px is supersampled into a 2048-native 850x72
# composition. This is NOT an old / upscaled low-resolution Korean raster.
native=stamp.crop(crop).resize((980,72),Image.Resampling.LANCZOS)
# Source title is forward-leaning; measured English comparison remains C's task.
native=native.transform((996,72),Image.Transform.AFFINE,
  (1,14/71,-14,0,1,0),resample=Image.Resampling.BICUBIC)
ink=np.asarray(native,dtype=np.uint8)
core=np.zeros((height,width),np.uint8)
left=(width-native.width)//2;top=(height-native.height)//2
core[top:top+72,left:left+996]=ink
native_face=core>=150
distance=distance_transform_edt(~native_face)
# Blue/navy edge is geometric, not compressed RGBA palette painting. The
# original alpha extent exceeds its white support: similarly give a separate
# full-depth navy rim and diffuse falloff around smaller white strokes.
dist_exp=np.maximum(0,distance.astype(np.float32)-0.75)
outer_alpha=np.clip(230*np.exp(-((dist_exp/8.0)**1.60))+
                    30*np.exp(-((dist_exp/14.0)**2.0)),0,248).astype(np.uint8)
inner_alpha=np.maximum(core,outer_alpha)
keyline=(distance>0.0)&(outer_alpha>=25)
face_core=(core>=215)
visible=(inner_alpha>24)&allowed
assert not np.any((inner_alpha>24)&(~allowed)), "glyph/halo exceeds old localized effect bbox"
source_face=source[:,:,:3][(source[:,:,0]>235)&(source[:,:,1]>235)&(source[:,:,2]>235)&(source[:,:,3]>180)&source_region]
source_keyline=source[:,:,:3][(source[:,:,0]<36)&(source[:,:,1]<65)&(source[:,:,2]>source[:,:,0]+12)&(source[:,:,3]>180)&source_region]
assert len(source_face)>2000 and len(source_keyline)>5000
white=np.rint(np.percentile(source_face,90,axis=0)).astype(np.uint8)
navy=np.rint(np.percentile(source_keyline,30,axis=0)).astype(np.uint8)
desired=clean[:,:,:3].copy().astype(np.int16)
desired[visible]=navy
desired[native_face]=white
target_alpha=np.array(clean[:,:,3],copy=True)
target_alpha[visible]=inner_alpha[visible]
target_alpha[native_face]=255
# Keep all source-aligned protected artwork from CLEAN elsewhere.
clean_protected=(clean[:,:,3]>16)&allowed
assert np.count_nonzero(clean_protected&visible)==0,"true protected artwork under new text"
face_count=int(np.count_nonzero(native_face))
assert 12000<face_count<50000,face_count
def rgb565(px):
    r,g,b=[int(t) for t in px]
    return ((r*31+127)//255<<11)|((g*63+127)//255<<5)|((b*31+127)//255)
def expand(v):
    return np.array([(((v>>11)&31)*255+15)//31,(((v>>5)&63)*255+31)//63,((v&31)*255+15)//31],dtype=np.int16)
w565=rgb565(white)
b565=rgb565(navy)
assert w565>b565
p0,p1=expand(w565),expand(b565)
colors=np.array([p0,p1,(2*p0+p1+1)//3,(p0+2*p1+1)//3],dtype=np.int16)
raw=bytearray(old)
changed_blocks=0
blocks_skipped=0
# Exact lossless original DDS color endpoints, entirely new source-conditioned
# alpha geometry. Encode both DXT5 alpha and DXT1 RGB with global pinned
# source white/navy endpoints, avoiding per-block palette-color seams.
alpha_levels=np.array([255,0,218.57,182.14,145.71,109.29,72.86,36.43])
for y0 in range((targetbox[1]//4)*4,((targetbox[3]+3)//4)*4,4):
 for x0 in range((targetbox[0]//4)*4,((targetbox[2]+3)//4)*4,4):
  inbbox=(x0>=targetbox[0] and x0+4<=targetbox[2] and
          y0>=targetbox[1] and y0+4<=targetbox[3] and
          x0>=bbox[0] and x0+4<=bbox[2] and
          y0>=bbox[1] and y0+4<=bbox[3])
  if not inbbox:
   blocks_skipped+=1
   continue
  pix=desired[y0:y0+4,x0:x0+4].astype(np.int32)
  pal=colors.astype(np.int32)
  rgb_idx=((pix[:,:,None,:]-pal[None,None,:,:])**2).sum(axis=3).argmin(axis=2)
  alpha=target_alpha[y0:y0+4,x0:x0+4].astype(np.float32)
  alpha_idx=np.abs(alpha[:,:,None]-alpha_levels[None,None,:]).argmin(axis=2)
  a_bits=0;c_bits=0
  for iy in range(4):
   for ix in range(4):
    idx=(3-iy)*4+ix
    a_bits |= int(alpha_idx[iy,ix]) <<(3*idx)
    c_bits |= int(rgb_idx[iy,ix]) <<(2*idx)
  offset=128+(((height-y0-4)//4)*(width//4)+(x0//4))*16
  chunk=bytes((255,0))+a_bits.to_bytes(6,"little")+struct.pack("<HHI",w565,b565,c_bits)
  raw[offset:offset+16]=chunk
  changed_blocks+=1
assert changed_blocks>3500,changed_blocks
trial=bytes(raw)
assert trial[:128]==old[:128] and len(trial)==len(old)
candidate=decode(trial)
change=np.any(candidate!=previous,axis=2)
outside_source=int(change[~source_region].sum())
outside_target=int(change[~allowed].sum())
assert outside_source==outside_target==0,(outside_source,outside_target)
assert not np.any((candidate[:,:,3]!=source[:,:,3])&~source_region)
assert not np.any((candidate[:,:,3]!=previous[:,:,3])&~allowed)
# Within source we have an entirely new native clean/font-glow composite.
distance_saved=distance_transform_edt(~(candidate[:,:,3]>16))
white_new=(candidate[:,:,0]>=213)&(candidate[:,:,1]>=213)&(candidate[:,:,2]>=213)
white_coverage=float(np.mean(white_new[face_core]))
if white_coverage<0.89:raise RuntimeError(("decoded native white core torn",white_coverage))
damage_to_preserved=int(np.count_nonzero((candidate[:,:,3]>16)&clean_protected))
composite_outside=int(np.any(candidate!=clean,axis=2)[~source_region].sum())
assert composite_outside==0
source_extra=0
testpath=run/"42E618FD_B327R_EXPERIMENT_NOT_APPROVED.dds"
testpath.write_bytes(trial)
assert SHA(testpath.read_bytes())==SHA(trial)
assert np.array_equal(decode(testpath.read_bytes()),candidate)
# BC3-alpha/source hue support is descriptive, never standalone C PASS.
src_white=int(np.count_nonzero((source[:,:,0]>225)&(source[:,:,1]>225)&(source[:,:,2]>225)&source_region&(source[:,:,3]>16)))
src_navy=int(np.count_nonzero((source[:,:,2]>source[:,:,0]+10)&source_region&(source[:,:,3]>16)))
dst_white=int(np.count_nonzero((candidate[:,:,0]>225)&(candidate[:,:,1]>225)&(candidate[:,:,2]>225)&allowed&(candidate[:,:,3]>16)))
dst_navy=int(np.count_nonzero((candidate[:,:,2]>candidate[:,:,0]+10)&allowed&(candidate[:,:,3]>16)))
# Independent clean-only and composite-only visual evidence; 3 backgrounds,
# readable FLIP-Y and RAW, native, practical 75/50%, high zoom.
for orientation in ("READABLE","RAW"):
    ims=[source,clean,previous,candidate] if orientation=="READABLE" else [np.flipud(a) for a in (source,clean,previous,candidate)]
    for bgname,bg in (("BLACK",(0,0,0,255)),("GRAY",(72,72,72,255)),("WHITE",(255,255,255,255))):
        for percent in (100,75,50):
            chunks=[]
            for a in ims:
                tile=Image.fromarray(a,"RGBA")
                canvas=Image.new("RGBA",(width,height),bg)
                canvas.alpha_composite(tile)
                if percent!=100:canvas=canvas.resize((round(width*percent/100),round(height*percent/100)),Image.Resampling.LANCZOS)
                chunks.append(canvas.convert("RGB"))
            frame=Image.new("RGB",(sum(z.width for z in chunks)+12,max(z.height for z in chunks)),(87,87,87))
            pos=0
            for z in chunks:frame.paste(z,(pos,0));pos+=z.width+4
            frame.save(run/f"{orientation}_{bgname}_{percent}_SOURCE_CLEAN_OLD_B327.png",optimize=True)
# Preserve actual full-resolution individual decoded clean/trial as proof.
Image.fromarray(candidate,"RGBA").save(run/"B327R_PERSISTED_DECODE_READABLE.png")
Image.fromarray(np.flipud(candidate),"RGBA").save(run/"B327R_PERSISTED_DECODE_RAW.png")
Image.fromarray(clean,"RGBA").save(run/"B327R_AUTHORED_CLEAN_PLATE.png")
report={
 "run":"B327","queue_index":98,"asset":"42E618FD",
 "status":"B327R_NATIVE_HALO_TRIAL_PENDING_CONTROLLER_VISUAL",
 "source_sha256":source_sha,"clean_sha256":SHA(cleanpath.read_bytes()),"mask_sha256":SHA(maskpath.read_bytes()),
 "previous_sha256":old_sha,"trial_sha256":SHA(trial),
 "method":"NEW_NATIVE_VECTOR_ALPHA_PLUS_SOURCE_FAMILY_DIFFUSE_NAVY_GLOW_RGBA_DXT5_RECONSTRUCTION",
 "source_family":{"native_size":[width,height],"source_face_rgb_90pct":white.tolist(),"source_keyline_rgb_30pct":navy.tolist(),"face_support":len(source_face),"navy_support":len(source_keyline),"native_keyline_pixels":int(keyline.sum()),"keyline_inner_distance_px":8.0,"source_white_to_navy_count_ratio":float(len(source_face)/(len(source_face)+len(source_keyline)))},
 "source_bbox":bbox,"candidate_bbox":targetbox,"source_white_navy": [src_white,src_navy],"candidate_white_navy":[dst_white,dst_navy],"mipmaps":1,"format":"DXT5_BC3","raw_orientation":"MIRROR_Y",
 "gate_plate_only":{"source_clean_rgba_outside":source_clean_out,"source_glyph_alpha_residual":source_alpha_unremoved,"status":"MACHINE_PASS_VISUAL_PENDING"},
 "gate_composite_only":{"clean_candidate_rgba_outside":composite_outside,"changed_outside_source":outside_source,"changed_outside_target":outside_target,"preserved_visible_outside_mask_changed":damage_to_preserved,"status":"MACHINE_CONTAINMENT_PASS_VISUAL_PENDING"},
 "machine":{"blocks_rebuilt":changed_blocks,"skipped_boundary_blocks":blocks_skipped,
 "pixel_changes":int(change.sum()),"authored_white_face_decoded_coverage":white_coverage,"new_alpha_pixels":int(np.count_nonzero((candidate[:,:,3]>16)&(previous[:,:,3]<=16))),"alpha_exact_outside_effect":True,"header_exact":True,"persisted_roundtrip_exact":True,
 "outside_source":outside_source,"outside_target":outside_target},
 "producer_visual":"PENDING_CONTROLLER_SOURCE_CLEAN_OLD_TRIAL_NATIVE_RAW_75_50",
 "independent_C":"NOT_RUN","C3":"NOT_RUN","user":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
 "candidate_promoted":False,"backend":"GITHUB_ACTIONS_ONLY_SOURCE_DOWNLOAD_GPT_LOCAL_DNS_UNAVAILABLE",
 "cleanup":"GITHUB_EPHEMERAL_RUNNER",
 "forbidden_domains_touched":[]
}
(run/"B327R_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"trial_sha256":SHA(trial),"blocks":changed_blocks,"changed":int(change.sum()),"nonletter_visible_delta":damage_to_preserved,"outside":outside_target},ensure_ascii=False))
