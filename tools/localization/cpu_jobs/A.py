#!/usr/bin/env python3
"""A235 q121: measured English face/rim and Regular native vector construction.
P0 IGR030/031/040. Scope only rank20 Gas Pedal text cell, never claim
whole-atlas pass or user-game repair. No A230 ghost subtraction or inherited
Korean CLEAN is used. Source PNG extracted losslessly from canonical English.
"""
import csv, hashlib, io, json, os, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.dont_write_bytecode=True
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
root=Path.cwd()
run="20261011-A235R-Q121-SOURCE-CONTOUR-NATIVE-HEIGHT-REFIT"
out=root/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(o,n):(out/n).write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
def img(a):return Image.fromarray(a.astype(np.uint8),"RGBA")
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","121"],capture_output=True,text=True)
dump({"returncode":tri.returncode,"stdout":tri.stdout[-5000:],"stderr":tri.stderr[-2000:]},"A235R_REWORK_TRIAGE.json")
assert tri.returncode==0
with (root/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
    item=next(x for x in csv.DictReader(f) if x["index"]=="121")
assert item["action"]=="localize_text"
dds_path=root/"localization/graphics/hd_candidates"/item["path"]
dds_bytes=dds_path.read_bytes()
official_sha=sha(dds_bytes)
assert official_sha=="38d5c2c30ea813202051b191dc01de9d7804e52c1cbab0f46c5372b59ed6c844",("official changed; do not race concurrent author",official_sha)
assert dds_bytes[:4]==b"DDS " and len(dds_bytes)==128+4096*4096*4
source_path=root/"localization/graphics/role_A/20261010-A215-Q121-P0-SOURCE-COMPONENT-LOSSLESS/A215_component_20_SOURCE_NATIVE_RGBA.png"
src_bytes=source_path.read_bytes()
source_expanded=np.array(Image.open(io.BytesIO(src_bytes)).convert("RGBA"),dtype=np.uint8)
x0,y0,x1,y1=(3490,391,3722,440)
W,H=x1-x0,y1-y0
qa=json.loads((root/"localization/graphics/role_A/20261010-A215-Q121-P0-SOURCE-COMPONENT-LOSSLESS/A215_COMPONENT_QA.json").read_text())
assert qa["regions"][19]["expanded_crop_readable"]==[3478,379,3734,452]
assert source_expanded.shape==(H+24,W+24,4),source_expanded.shape
src=source_expanded[12:12+H,12:12+W].copy()
# First measure exact canonical English SOURCE, not the corrupt Korean CLEAN.
# It is a source-conditioned native vector-face method, not the rejected
# Noto Bold/2px-outline/2px-shadow and shear iteration.
opaque=src[:,:,3]>=72
face=opaque&(src[:,:,0]>174)&(src[:,:,1]>174)&(src[:,:,2]>170)
rim=opaque&(src[:,:,0]<120)&(src[:,:,1]<130)&(src[:,:,2]<155)
assert int(face.sum())>1300 and int(rim.sum())>170,(int(face.sum()),int(rim.sum()))
source_white=np.median(src[face,:3],axis=0).astype(np.uint8)
source_navy=np.median(src[rim,:3],axis=0).astype(np.uint8)
fy,fx=np.where(face)
face_bbox=[int(fx.min()),int(fy.min()),int(fx.max()+1),int(fy.max()+1)]
source_face_span=face_bbox[2]-face_bbox[0]
# Left-English G contour is an optical hint only; unlike corresponding
# Hangul strokes it is not a homologous calibrated anchor.
yy_grid,xx_grid=np.indices(face.shape)
g=face&(xx_grid<(W*.30))
def track(lo,hi):
    ys,xs=np.where(g&(yy_grid>=lo)&(yy_grid<hi))
    return float(np.percentile(xs,7)) if len(xs)>=15 else None
top_edge=track(7,20);bottom_edge=track(27,40)
source_dx=top_edge-bottom_edge if top_edge is not None and bottom_edge is not None else None
slant_hint=round(float(np.clip(source_dx/25,.08,.36)),3) if source_dx is not None else None
source_metrics={"source_white_pixels":int(face.sum()),"source_dark_rim_pixels":int(rim.sum()),
    "source_face_rgb":source_white.tolist(),"source_rim_rgb":source_navy.tolist(),
    "face_bbox":face_bbox,"english_G_top_left_x7pct":top_edge,
    "english_G_bottom_left_x7pct":bottom_edge,
    "english_G_top_minus_bottom_dx":source_dx,
    "optical_lean_hint_not_homologous":slant_hint,
    "source_anchor_not_independently_homologous":True}
dump(source_metrics,"A235R_SOURCE_FAMILY_MEASUREMENT.json")
assert qa["source_sha256"]=="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
assert qa["regions"][19]["bbox_readable"]==[x0,y0,x1,y1]
# Recreate original English-free plate from SOURCE background, not from corrupt
# A215 CLEAN or Korean official bytes. Source plate is a solid atlas color here;
# verify the flat-color hypothesis using the dominant pixel's support at edges.
rgba,counts=np.unique(src.reshape(-1,4),axis=0,return_counts=True)
best=rgba[int(np.argmax(counts))]
support=int(np.max(counts));fraction=support/(W*H)
# Background variations can reflect sprite pixels; without demonstrable solid
# plate, fail closed rather than erasing a foreground icon.
assert fraction>0.23,("unverified nonflat background",fraction,best.tolist())
edges=np.concatenate((src[0],src[-1],src[:,0],src[:,-1]),axis=0)
edge_support=float(np.mean(np.all(edges==best[None,:],axis=1)))
assert edge_support>0.26,("source region appears to contain protected border",edge_support)
plate=np.broadcast_to(best,(H,W,4)).copy()
# Source text is fully replaced only INSIDE the exact source text rectangle;
# this is a transparent lettering layer composited over source-derived plate.
# Native anti-alias is calculated once from vector type at 3x, not upscaled
# from previously low-resolution Korean sprites.
font_path=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
assert font_path.is_file()
font_sha=sha(font_path.read_bytes())
phrase="가속 페달"
S=3
font=ImageFont.truetype(str(font_path),41*S)
assert all(font.getmask(ch).getbbox() is not None for ch in phrase if ch.strip())
mask_h=Image.new("L",(W*S,H*S),0)
draw=ImageDraw.Draw(mask_h)
box=draw.textbbox((0,0),phrase,font=font,anchor="lt")
tw,th=box[2]-box[0],box[3]-box[1]
texttmp=Image.new("L",(tw+12*S,th+8*S),0)
d=ImageDraw.Draw(texttmp)
d.text((6*S-box[0],4*S-box[1]),phrase,font=font,fill=255,anchor="lt")
# Source-derived hierarchy: italic English face fills most of 232x49;
# avoid both a giant glyph and an undersized narrow hanging Korean.
targetW=int(W*S*0.83)
targetH=min(int(H*S*.77),texttmp.height)
if texttmp.width>targetW:
    resized=texttmp.resize((targetW,max(1,int(texttmp.height*targetW/texttmp.width))),Image.Resampling.LANCZOS)
else:resized=texttmp
if resized.height>H*S-9*S:
    scale=(H*S-9*S)/resized.height
    resized=resized.resize((max(1,int(resized.width*scale)),H*S-9*S),Image.Resampling.LANCZOS)
mask_h.paste(resized,((W*S-resized.width)//2,(H*S-resized.height)//2))
# Positive dx=top-bottom denotes source right italic in readable coordinates.
# PIL inverse mapping: x_in=x_out+shear*y-shear*height.
lean=slant_hint if slant_hint is not None else .18
mask_h=mask_h.transform(mask_h.size,Image.Transform.AFFINE,
    (1,lean,-lean*(H*S),0,1,0),resample=Image.Resampling.BICUBIC)
# Optical width fit to 82% of the source text width at high resolution
# BEFORE the one final downsample, avoiding the 60% underfill of first trial.
support=mask_h.getbbox()
assert support is not None
kx0,ky0,kx1,ky1=support
glyph_hi=mask_h.crop((kx0,ky0,kx1,ky1))
target_width=int(np.clip(round(source_face_span*.93),165,W-7)*S)
assert target_width<W*S-6*S
# A235 native saved DDS first-look: face 34px high vs English measured 46px.
# This is the SECOND and final source-profile adjustment. Scale the fresh
# native Regular vector mask once BEFORE its final 3x->1x downsample.
# Neither old Korean DDS nor old low-res lettering is rescaled.
source_face_height=face_bbox[3]-face_bbox[1]
target_height=int(np.clip(round(source_face_height*.88),36,H-8)*S)
glyph_hi=glyph_hi.resize((target_width,target_height),Image.Resampling.LANCZOS)
mask_fit=Image.new("L",(W*S,H*S),0)
mask_fit.paste(glyph_hi,((W*S-target_width)//2,(H*S-glyph_hi.height)//2))
mask=np.array(mask_fit.resize((W,H),Image.Resampling.LANCZOS),dtype=np.uint8)
# The original English uses white face, dark blue keyline + bottom-right dark
# extrusion. Recreate on CLEAN with genuinely separate transparent masks.
core=mask>28
yy,xx=np.nonzero(core)
assert len(xx)>250
minx,maxx,miny,maxy=int(xx.min()),int(xx.max()+1),int(yy.min()),int(yy.max()+1)
assert minx>=3 and miny>=2 and maxx<=W-3 and maxy<=H-2,(minx,miny,maxx,maxy)
def offset(a,dx,dy):
    z=np.zeros_like(a,dtype=np.uint8)
    xlo=max(0,dx);xhi=min(W,W+dx)
    ylo=max(0,dy);yhi=min(H,H+dy)
    z[ylo:yhi,xlo:xhi]=a[ylo-dy:yhi-dy,xlo-dx:xhi-dx]
    return z
from PIL import ImageFilter
# C1 rejected the fat Bold two-pixel navy rim. Follow original thin blue
# SOURCE edge: native Regular vector face and at most 1-pixel rim.
outline=np.array(Image.fromarray(mask,"L").filter(ImageFilter.MaxFilter(3)),dtype=np.uint8)
extrude=offset(outline,1,1)
bg=plate.astype(np.float32)
# All effects masks bounded with positive inset. Neither glyph nor shadow may
# enlarge source original bbox. This bbox is the exact A215 English bbox.
inside=np.zeros((H,W),dtype=bool);inside[1:-1,1:-1]=True
def paint(color,opacity):
    global bg
    a=(np.asarray(opacity,dtype=np.float32)/255.0)*inside
    old_a=bg[:,:,3]/255.0
    new_a=a+old_a*(1-a)
    rgb=np.array(color[:3],dtype=np.float32)
    numerator=rgb[None,None,:]*a[:,:,None]+bg[:,:,:3]*old_a[:,:,None]*(1-a[:,:,None])
    new_rgb=np.divide(numerator,new_a[:,:,None],out=np.zeros_like(numerator),where=new_a[:,:,None]>1e-8)
    bg[:,:,:3]=np.where(new_a[:,:,None]>1e-8,new_rgb,bg[:,:,:3])
    # A234 first trial was invisible: a transparent background must acquire
    # alpha from the Hangul face, outline and offset shadow layers.
    bg[:,:,3]=new_a*255.0
paint(tuple(int(x) for x in source_navy),extrude)
paint(tuple(int(x) for x in source_navy),outline)
paint(tuple(int(x) for x in source_white),mask)
final=np.rint(np.clip(bg,0,255)).astype(np.uint8)
assert np.array_equal(plate[0,0],best)
assert np.all(plate[:,:,3]==best[3])
assert int(np.count_nonzero(final[:,:,3]>0))>300
assert np.array_equal(final[:,:,3][~inside],plate[:,:,3][~inside])
prior=np.array(Image.open(io.BytesIO(dds_bytes)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
assert prior.shape==(4096,4096,4)
# DDS raw is first validated through Pillow; change only the rank20 row range.
data=bytearray(dds_bytes)
for y in range(y0,y1):
    begin=128+((4095-y)*4096+x0)*4
    data[begin:begin+W*4]=final[y-y0].tobytes()
new_bytes=bytes(data)
newsha=sha(new_bytes)
assert newsha!=official_sha
newpath=out/"A235R_Q121_SOURCE_CONTOUR_HEIGHT_REFIT_UNPROMOTED.dds"
newpath.write_bytes(new_bytes)
check=np.array(Image.open(newpath).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
roi=check[y0:y1,x0:x1]
assert np.array_equal(roi,final),"DDS round-trip incorrectly packed or channel format changed"
assert np.array_equal(check[:y0],prior[:y0])
assert np.array_equal(check[y1:],prior[y1:])
assert np.array_equal(check[y0:y1,:x0],prior[y0:y1,:x0])
assert np.array_equal(check[y0:y1,x1:],prior[y0:y1,x1:])
assert new_bytes[:128]==dds_bytes[:128]
assert len(new_bytes)==len(dds_bytes)
assert np.count_nonzero(np.any(roi!=src,axis=2))>0
# Save SOURCE / CLEAN / transparent lettering / persisted FINAL independently
img(src).save(out/"A235R_SOURCE_NATIVE_RGBA.png")
img(plate).save(out/"A235R_CLEAN_PLATE_NATIVE_RGBA.png")
layer=np.zeros((H,W,4),dtype=np.uint8);layer[:,:,:3]=255;layer[:,:,3]=mask
img(layer).save(out/"A235R_GLYPH_ONLY_TRANSPARENT_RGBA.png")
img(roi).save(out/"A235R_PERSISTED_FINAL_NATIVE_RGBA.png")
img(roi).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out/"A235R_PERSISTED_FINAL_RAW.png")
Image.fromarray(mask,"L").save(out/"A235R_GLYPH_MASK_NATIVE.png")
for bgname,bgc in (("GRAY",(105,105,105)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
    for percent in (100,75,50):
        frames=[]
        for ar in (src,plate,roi):
            rgba_img=img(ar)
            im=Image.alpha_composite(Image.new("RGBA",(W,H),bgc+(255,)),rgba_img).convert("RGB")
            if percent!=100:im=im.resize((round(W*percent/100),round(H*percent/100)),Image.Resampling.LANCZOS)
            frames.append(im)
        w,h=frames[0].size
        sheet=Image.new("RGB",(w*3,h+20),bgc)
        for i,frame in enumerate(frames):
            sheet.paste(frame,(i*w,20))
        d=ImageDraw.Draw(sheet)
        for i,name in enumerate(("SOURCE","CLEAN","NEW SAVED DDS")):
            d.text((i*w+3,2),name,fill="black" if bgname=="WHITE" else "white")
        sheet.save(out/f"A235R_COMPARE_{bgname}_{percent}.png")
recipe={"version":"source-native-flat-plate-v1","index":121,"cell_id":"rank20_Gas_Pedal",
    "source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
    "source_dds_sha256":qa["source_sha256"],"source_crop_path":str(source_path.relative_to(root)),
    "source_crop_sha256":sha(src_bytes),"source_bbox_readable":[x0,y0,x1,y1],
    "plate_from_source_modal_RGBA":best.tolist(),"modal_support_fraction":fraction,"alpha_layer_compositing":"straight_alpha_src_over",
    "border_source_modal_support":edge_support,"render_text":phrase,"font_path":str(font_path),
    "font_sha256":font_sha,"native_ppem":41,"english_face_profile":source_metrics,"native_target_face_height":int(target_height/S),"supersample_one_time":3,
    "readable_italic_shear":lean,"original_font_effect":"white italic face / navy outline and extrusion",
    "glyph_box_local":[minx,miny,maxx,maxy],"lettering_separate":True,
    "orient":"READABLE_FLIP_Y -> DDS RAW Y-MIRROR","background":"source-derived modal solid native pixels"}
dump(recipe,"recipe.json")
report={"run":"A235R","run_key":"OUTRUN-KOR-A235-Q121-REGULAR-SOURCE-CONTOUR-VECTOR-20261011-0700",
    "role":"A","index":121,"P0":["IGR-030","IGR-031","IGR-040"],
    "method_change":"A235 new Regular-vector source sampled face/rim family, then one FINAL optical source-HEIGHT correction of independently observed under-height (34 vs source native face 46) to measured 88% height on freshly rendered native vector before downsample. Earlier Bold 2px rim is not used; no more same-method retries after A235R.",
    "source_sha256":qa["source_sha256"],"source_crop_sha256":sha(src_bytes),
    "old_official_sha256":official_sha,"new_unpromoted_trial_sha256":newsha,
    "new_unpromoted_trial_path":str(newpath.relative_to(root)),
    "native_whole_atlas":[4096,4096],"source_region_bbox":[x0,y0,x1,y1],
    "plate_background_support":fraction,"plate_edge_support":edge_support,"new_alpha_visible_pixels":int(np.count_nonzero(final[:,:,3]>0)),
    "glyph_bbox_inside_source":[minx,miny,maxx,maxy],"english_face_profile":source_metrics,"source_face_height_refit_to_native":int(target_height/S),
    "non_target_pixels_exact":True,"dds_header_exact":True,"saved_DDS_decode_exact":True,
    "changed_outside_source_region":0,"other_29_regions_byte_exact":True,
    "P1_independent_plate_observation":"NOT_PERFORMED_BY_C1",
    "P2_source_slant_blind_anchors":"NOT_INDEPENDENTLY_CALIBRATED",
    "P3_mechanical":"SCOPED_SAVED_ROUNDTRIP_PASS",
    "producer_visual":"PENDING_DIRECT_SAVED_DDS_VIEW_NO_PRODUCER_PASS",
    "whole_atlas":"REWORK_REQUIRED_29_OTHER_REGIONS_NOT_REAPPROVED",
    "official_candidate_changed":False,"new_unpromoted_dds":1,
    "C1":"NOT_RUN_NEW_BYTES","C3":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
    "user_ingame_backlog":"OPEN","required_next":"Review SOURCE/CLEAN/FINAL 100/75/50 RAW and source typography independently; then C1 review if producer visual qualifies; keep official DDS unchanged"}
dump(report,"A235R_MACHINE_AND_HANDOFF.json")
print(json.dumps({"run":"A234","new_unpromoted_trial_sha":newsha,"source_plate_support":fraction,
 "glyph_bbox":[minx,miny,maxx,maxy],"outside_change":0,"published_to_official":False}))
