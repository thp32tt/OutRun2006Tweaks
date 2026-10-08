#!/usr/bin/env python3
"""B277 q098: separate full-face source-family white/navy BC3 reconstruction.

Experiment is QA-gated: do NOT replace the hd_candidates DDS until a human
controller inspects the source/CLEAN/trial's persisted bytes.
"""
import hashlib, io, json, os, struct, subprocess, sys, tempfile, urllib.request
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "B":
    raise SystemExit("B277 requires GitHub hosted access to SHA-pinned source DDS")
root = Path.cwd()
gfx = root / "localization/graphics"
relative = "textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
target = gfx / "hd_candidates" / relative
run = gfx / "role_B/20261008-B277-Q098-NATIVE-GLYPH-KEYLINE"
run.mkdir(parents=True, exist_ok=True)
def SHA(x): return hashlib.sha256(x).hexdigest()
old_sha = "1d63cd9b50422375bd0693b40302c01702f193a91dc19af1517eb3476fa20ceb"
source_sha = "3b3cdd76b03014e0ba6a47f4e98a187fdf6ae4297314494cbe1d3d4c586f1f59"
maskpath = gfx/"role_B/20261005-B-PRODUCTION40/42E618FD_TARGET_TEXT_MASK.png"
cleanpath = gfx/"role_B/20261005-B-PRODUCTION40/42E618FD_CLEAN_PLATE.png"
srcmaskpath = gfx/"role_B/20261005-B-PRODUCTION40/42E618FD_SOURCE_TEXT_MASK.png"
tri = subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","98","--require-safe-rerender"],text=True,capture_output=True,check=True)
assert json.loads(tri.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK"
old = target.read_bytes()
assert SHA(old)==old_sha, "q098 concurrently changed; do not touch"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
with tempfile.TemporaryDirectory(prefix="b277_github_") as tmp:
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
targetbox=(580,11,1524,116)
yy,xx=np.ogrid[:height,:width]
source_region=(xx>=bbox[0])&(xx<bbox[2])&(yy>=bbox[1])&(yy<bbox[3])
allowed=(xx>=targetbox[0])&(xx<targetbox[2])&(yy>=targetbox[1])&(yy<targetbox[3])
source_clean_out=int(np.any(source!=clean,axis=2)[~source_region].sum())
source_alpha_unremoved=int(np.count_nonzero(clean[:,:,3][(sourcemask>80)&source_region]>16))
if source_clean_out or source_alpha_unremoved:
    raise RuntimeError(("PLATE_ONLY_GATE failed",source_clean_out,source_alpha_unremoved))
# Source family: English native face is bright white; keyline dark navy.
# Unlike B271/272/273, reconstruct BOTH layers from the *authored* target
# silhouette rather than whitening intermittent decoded BC3 pixels.
source_face=source[:,:,:3][(source[:,:,0]>235)&(source[:,:,1]>235)&(source[:,:,2]>235)&(source[:,:,3]>180)&source_region]
source_keyline=source[:,:,:3][(source[:,:,0]<36)&(source[:,:,1]<65)&(source[:,:,2]>source[:,:,0]+12)&(source[:,:,3]>180)&source_region]
assert len(source_face)>2000 and len(source_keyline)>5000, (len(source_face),len(source_keyline))
white=np.rint(np.percentile(source_face,90,axis=0)).astype(np.uint8)
navy=np.rint(np.percentile(source_keyline,30,axis=0)).astype(np.uint8)
# A colored antialias ring is quantized via the native 4-color BC1 interpolants.
# Face ink is keyed by the native typesetter alpha; counter-holes remain blank.
# The B274 native visual rejection showed that eroding 3-5px deletes most
# Korean glyph face and produces solid navy silhouettes. Here the *authored*
# 8-bit target face mask (not a distance-eroded mask) defines full white ink.
# The original dark-outline exterior is retained where mask alpha is low.
face_core=(targetmask>=212)&allowed
visible=(previous[:,:,3]>16)&allowed
oldrgb=previous[:,:,:3].astype(np.int16)
desired=oldrgb.copy()
desired[face_core&visible]=np.array(white,dtype=np.int16)
edge=(targetmask>=65)&(targetmask<212)&visible
fade=(targetmask[edge].astype(np.float32)-65)/147.0
desired[edge]=np.rint(np.array(navy,dtype=np.float32)[None,:]*(1-fade[:,None])+np.array(white,dtype=np.float32)[None,:]*fade[:,None]).astype(np.int16)
face_count=int((face_core&visible).sum())
if face_count<20000 or face_count>85000:raise RuntimeError(("authored full-face mismatch",face_count))
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
for y0 in range((targetbox[1]//4)*4,((targetbox[3]+3)//4)*4,4):
    for x0 in range((targetbox[0]//4)*4,((targetbox[2]+3)//4)*4,4):
        active=face_core[y0:y0+4,x0:x0+4]&visible[y0:y0+4,x0:x0+4]
        if not active.any():continue
        # Strict containment at block level: all changed blocks must be fully
        # inside the protected-free original English text/effect rectangle.
        if (x0<bbox[0] or x0+4>bbox[2] or y0<bbox[1] or y0+4>bbox[3]
            or x0<targetbox[0] or x0+4>targetbox[2]
            or y0<targetbox[1] or y0+4>targetbox[3]):
            blocks_skipped+=1
            continue
        wanted=desired[y0:y0+4,x0:x0+4]
        nearest=((wanted.astype(np.int32)[:,:,None,:]-colors.astype(np.int32)[None,None,:,:])**2).sum(axis=3).argmin(axis=2)
        indices=0
        for iy in range(4):
            for ix in range(4):
                indices|=int(nearest[iy,ix])<<(2*((3-iy)*4+ix))
        offset=128+(((height-y0-4)//4)*(width//4)+(x0//4))*16
        struct.pack_into("<HHI",raw,offset+8,w565,b565,indices)
        changed_blocks+=1
if changed_blocks<500:raise RuntimeError(("new method changed too few blocks",changed_blocks))
trial=bytes(raw)
assert trial[:128]==old[:128] and len(trial)==len(old)
candidate=decode(trial)
assert np.array_equal(candidate[:,:,3],previous[:,:,3]),"alpha changed"
change=np.any(candidate!=previous,axis=2)
outside_source=int(change[~source_region].sum())
outside_target=int(change[~allowed].sum())
assert outside_source==outside_target==0,(outside_source,outside_target)
# The submitted proof will be inspected visually before any DDS promotion.
# BC3 block modifications may alter nonletter RGB in text region. Report it
# honestly; visual reviewer decides whether the effect/outline is acceptable.
damage_to_preserved=int((change & (~(targetmask>=65)) & visible).sum())
authored_ink=face_core&visible
white_new=(candidate[:,:,0]>=213)&(candidate[:,:,1]>=213)&(candidate[:,:,2]>=213)
white_coverage=float(np.mean(white_new[authored_ink]))
# Automated visual-family guard against the exact over-navy B274 failure:
# no PASS, and do not write even the trial when encoded bright-face is lost.
if white_coverage<0.72:
    raise RuntimeError(("full authored face still navy/striped",white_coverage))
composite_outside=int(np.any(candidate!=clean,axis=2)[~source_region].sum())
if composite_outside:raise RuntimeError(("COMPOSITE outside source region",composite_outside))
# Preserve original source/client layout native bbox; no new alpha pixels.
source_extra=int((candidate[:,:,3]>16)[~source_region].sum()-(previous[:,:,3]>16)[~source_region].sum())
assert source_extra==0
testpath=run/"42E618FD_B277_EXPERIMENT_NOT_APPROVED.dds"
testpath.write_bytes(trial)
assert SHA(testpath.read_bytes())==SHA(trial)
assert np.array_equal(decode(testpath.read_bytes()),candidate)
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
            frame.save(run/f"{orientation}_{bgname}_{percent}_SOURCE_CLEAN_OLD_B277.png",optimize=True)
# Preserve actual full-resolution individual decoded clean/trial as proof.
Image.fromarray(candidate,"RGBA").save(run/"B277_PERSISTED_DECODE_READABLE.png")
Image.fromarray(np.flipud(candidate),"RGBA").save(run/"B277_PERSISTED_DECODE_RAW.png")
Image.fromarray(clean,"RGBA").save(run/"B277_AUTHORED_CLEAN_PLATE.png")
report={
 "run":"B277","queue_index":98,"asset":"42E618FD",
 "status":"B277_TRIAL_PENDING_FIRST_HAND_CONTROLLER_VISUAL_NOT_DEPLOYED",
 "source_sha256":source_sha,"clean_sha256":SHA(cleanpath.read_bytes()),"mask_sha256":SHA(maskpath.read_bytes()),
 "previous_sha256":old_sha,"trial_sha256":SHA(trial),
 "method":"NEW_FULL_NATIVE_SOURCE_CONDITIONED_WHITE_AND_NAVY_4COLOR_BC1_BLOCK_RECONSTRUCTION",
 "source_family":{"native_size":[width,height],"source_face_rgb_90pct":white.tolist(),"source_keyline_rgb_30pct":navy.tolist(),"face_support":len(source_face),"navy_support":len(source_keyline)},
 "source_bbox":bbox,"candidate_bbox":targetbox,"mipmaps":1,"format":"DXT5_BC3","raw_orientation":"MIRROR_Y",
 "gate_plate_only":{"source_clean_rgba_outside":source_clean_out,"source_glyph_alpha_residual":source_alpha_unremoved,"status":"MACHINE_PASS_VISUAL_PENDING"},
 "gate_composite_only":{"clean_candidate_rgba_outside":composite_outside,"changed_outside_source":outside_source,"changed_outside_target":outside_target,"preserved_visible_outside_mask_changed":damage_to_preserved,"status":"MACHINE_CONTAINMENT_PASS_VISUAL_PENDING"},
 "machine":{"blocks_rebuilt":changed_blocks,"skipped_boundary_blocks":blocks_skipped,
 "pixel_changes":int(change.sum()),"authored_white_face_decoded_coverage":white_coverage,"new_alpha_pixels":0,"alpha_exact":True,"header_exact":True,"persisted_roundtrip_exact":True,
 "outside_source":outside_source,"outside_target":outside_target},
 "producer_visual":"PENDING_CONTROLLER_SOURCE_CLEAN_OLD_TRIAL_NATIVE_RAW_75_50",
 "independent_C":"NOT_RUN","C3":"NOT_RUN","user":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
 "candidate_promoted":False,"backend":"GITHUB_ACTIONS_ONLY_SOURCE_DOWNLOAD_GPT_LOCAL_DNS_UNAVAILABLE",
 "cleanup":"GITHUB_EPHEMERAL_RUNNER",
 "forbidden_domains_touched":[]
}
(run/"B277_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"trial_sha256":SHA(trial),"blocks":changed_blocks,"changed":int(change.sum()),"nonletter_visible_delta":damage_to_preserved,"outside":outside_target},ensure_ascii=False))
