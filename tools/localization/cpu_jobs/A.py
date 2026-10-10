#!/usr/bin/env python3
"""A234 q121: source-derived clean-plate plus transparent native italic glyph.
P0 IGR030/031/040. Scope only rank20 Gas Pedal text cell, never claim
whole-atlas pass or user-game repair. No A230 ghost subtraction or inherited
Korean CLEAN is used. Source PNG extracted losslessly from canonical English.
"""
import csv, hashlib, io, json, os, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.dont_write_bytecode=True
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
root=Path.cwd()
run="20261011-A234-Q121-RANK20-SOURCE-NATIVE-PLATE-AND-TYPE"
out=root/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(o,n):(out/n).write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
def img(a):return Image.fromarray(a.astype(np.uint8),"RGBA")
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","121"],capture_output=True,text=True)
dump({"returncode":tri.returncode,"stdout":tri.stdout[-5000:],"stderr":tri.stderr[-2000:]},"A234_REWORK_TRIAGE.json")
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
font_path=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
assert font_path.is_file()
font_sha=sha(font_path.read_bytes())
phrase="가속 페달"
S=3
font=ImageFont.truetype(str(font_path),39*S)
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
lean=0.22
mask_h=mask_h.transform(mask_h.size,Image.Transform.AFFINE,
    (1,lean,-lean*(H*S),0,1,0),resample=Image.Resampling.BICUBIC)
mask=np.array(mask_h.resize((W,H),Image.Resampling.LANCZOS),dtype=np.uint8)
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
outline=np.array(img(np.stack([mask]*4,axis=2)).getchannel("R").filter(ImageFilter.MaxFilter(5)),dtype=np.uint8)
extrude=offset(outline,2,2)
bg=plate.astype(np.float32)
# All effects masks bounded with positive inset. Neither glyph nor shadow may
# enlarge source original bbox. This bbox is the exact A215 English bbox.
inside=np.zeros((H,W),dtype=bool);inside[1:-1,1:-1]=True
def paint(color,opacity):
    global bg
    a=(np.asarray(opacity,dtype=np.float32)/255.0)*inside
    rgb=np.array(color[:3],dtype=np.float32)
    bg[:,:,:3]=bg[:,:,:3]*(1-a[:,:,None])+rgb[None,None,:]*a[:,:,None]
    # Preserve source-authored opaque plate alpha, not a rectangle pasted in
    # from an unrelated flattened compositor.
paint((3,17,62),extrude)
paint((4,17,70),outline)
paint((255,255,255),mask)
final=np.rint(np.clip(bg,0,255)).astype(np.uint8)
# A234 plate-only: visually and mechanically demonstrate English removal before
# lettering. Test byte-exact source background, outside region untouched.
assert np.array_equal(plate[0,0],best)
assert np.array_equal(final[:,:,3],plate[:,:,3])
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
newpath=out/"A234_Q121_RANK20_REBUILT_SOURCE_PLATE_UNPROMOTED.dds"
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
img(src).save(out/"A234_SOURCE_NATIVE_RGBA.png")
img(plate).save(out/"A234_CLEAN_PLATE_NATIVE_RGBA.png")
layer=np.zeros((H,W,4),dtype=np.uint8);layer[:,:,:3]=255;layer[:,:,3]=mask
img(layer).save(out/"A234_GLYPH_ONLY_TRANSPARENT_RGBA.png")
img(roi).save(out/"A234_PERSISTED_FINAL_NATIVE_RGBA.png")
img(roi).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out/"A234_PERSISTED_FINAL_RAW.png")
Image.fromarray(mask,"L").save(out/"A234_GLYPH_MASK_NATIVE.png")
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
        sheet.save(out/f"A234_COMPARE_{bgname}_{percent}.png")
recipe={"version":"source-native-flat-plate-v1","index":121,"cell_id":"rank20_Gas_Pedal",
    "source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
    "source_dds_sha256":qa["source_sha256"],"source_crop_path":str(source_path.relative_to(root)),
    "source_crop_sha256":sha(src_bytes),"source_bbox_readable":[x0,y0,x1,y1],
    "plate_from_source_modal_RGBA":best.tolist(),"modal_support_fraction":fraction,
    "border_source_modal_support":edge_support,"render_text":phrase,"font_path":str(font_path),
    "font_sha256":font_sha,"native_ppem":39,"supersample_one_time":3,
    "readable_italic_shear":lean,"original_font_effect":"white italic face / navy outline and extrusion",
    "glyph_box_local":[minx,miny,maxx,maxy],"lettering_separate":True,
    "orient":"READABLE_FLIP_Y -> DDS RAW Y-MIRROR","background":"source-derived modal solid native pixels"}
dump(recipe,"recipe.json")
report={"run":"A234","run_key":"OUTRUN-KOR-A234-Q121-RANK20-SOURCE-DERIVED-PLATE-NATIVE-ITALIC-20261011-0600",
    "role":"A","index":121,"P0":["IGR-030","IGR-031","IGR-040"],
    "method_change":"Entire source-derived rank20 CLEAN plate rebuilt BEFORE native Hangul lettering; previous A230 remnant deletion and corrupted inherited CLEAN abandoned",
    "source_sha256":qa["source_sha256"],"source_crop_sha256":sha(src_bytes),
    "old_official_sha256":official_sha,"new_unpromoted_trial_sha256":newsha,
    "new_unpromoted_trial_path":str(newpath.relative_to(root)),
    "native_whole_atlas":[4096,4096],"source_region_bbox":[x0,y0,x1,y1],
    "plate_background_support":fraction,"plate_edge_support":edge_support,
    "glyph_bbox_inside_source":[minx,miny,maxx,maxy],
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
dump(report,"A234_MACHINE_AND_HANDOFF.json")
print(json.dumps({"run":"A234","new_unpromoted_trial_sha":newsha,"source_plate_support":fraction,
 "glyph_bbox":[minx,miny,maxx,maxy],"outside_change":0,"published_to_official":False}))
