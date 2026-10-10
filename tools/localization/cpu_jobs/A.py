#!/usr/bin/env python3
"""A224 q103 original-typography optical-density contour pilot, scoped NON-PROMOTED DDS.
New method: Regular 65ppem outline/low tracking, once-resampled to native English height 43px from canonical source, not resizing an older Korean bitmap.
"""
import hashlib, io, json, os, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTCollection
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
repo=Path.cwd()
run="20261010-A224-Q103-SOURCE-OPTICAL-CONTOUR"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
official=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds"
prior=official.read_bytes()
prior_sha="9702957a9c6498877433bb6ff2e112647445d271ddce27bb3e37f3a076c8b1ed"
source_sha="76b6f6d8bc8b3269c2fdb73fcf7f2dd74163ed426a3d31efe33b6e51103af544"
assert sha(prior)==prior_sha and prior[:4]==b"DDS " and len(prior)==128+2048*2048*4
W=H=2048
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","103"],check=True,text=True,capture_output=True).stdout
# Queue triage is advisory; a separately independently confirmed C1 REWORK with
# new failure pixels is stronger than a stale NORMAL_QUEUE_SELECTION reason.
decision=json.loads(triage)["assets"][0]
confirmed=repo/"localization/graphics/role_C/20261010-C1-Q103-A222-STRICT-SOURCE-HEIGHT-FAIL/Q103_C1_REWORK.json"
verdict=json.loads(confirmed.read_text(encoding="utf-8"))
assert decision["index"]==103
assert verdict["QA_decision"]=="REWORK_REQUIRED"
assert verdict["reason_code"]=="STRICT_ORIGINAL_GLYPH_EFFECT_HEIGHT_EXCEED_15PX"
assert verdict["comparison_exact"]["source_effect_height"]==45
assert verdict["comparison_exact"]["trial_effect_height"]==60
assert verdict["candidate_sha256"]=="a6959102af3392a9a057ad660b282f3c1761516b8aa12ae5077514e87c0b2a07"
assert "q103_a223_new_trial_rework_source_weight_spacing" in decision["current_status"],decision
last=json.loads((repo/"localization/graphics/role_A/20261010-A223-Q103-SOURCE-45PX-HEIGHT-REPAIR/A223_CONTROLLER_SELF_QA.json").read_text(encoding="utf-8"))
assert last["new_trial_sha256"]=="a36359f1d7f030ef25345ffc9437ccb6e71654690edc7de322f0285d68a531b9"
assert last["firsthand_visual"]["decision"]=="PRODUCER_VISUAL_HOLD_NOT_FULL_PASS"
assert last["firsthand_visual"]["defect_remaining"]=="FONT_OPTICAL_SIZE_AND_LOOSE_TRACKING_SOURCE_STYLE_MISMATCH"
assert decision["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED","NORMAL_QUEUE_SELECTION"),decision
url=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/"
"Release/spr_sprani_selector_cvt_Exst/590A4724_512x512.dds")
with urllib.request.urlopen(url,timeout=150) as r: english_bytes=r.read()
assert sha(english_bytes)==source_sha
source=Image.open(io.BytesIO(english_bytes)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
before=Image.open(io.BytesIO(prior)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean_path=repo/"localization/graphics/role_A/20261009-A197-Q103-NORMAL-BALANCE-ITALIC-NATIVE/A197_CLEAN_PLATE.png"
clean=Image.open(clean_path).convert("RGBA")
assert source.size==before.size==clean.size==(W,H)
source_bbox=(1411,1968,1801,2040)
# Verify before/CLEAN source style; never alter protected plate or source artwork.
assert before.crop((1411,1968,1801,2040)).tobytes()!=clean.crop(source_bbox).tobytes()
sarr=np.asarray(source.crop(source_bbox),dtype=np.uint8)
carr=np.asarray(clean.crop(source_bbox),dtype=np.uint8)
barr=np.asarray(before.crop(source_bbox),dtype=np.uint8)
# This q103 yellow selector is an OPAQUE source-family plate, not a transparent sprite.
# A197 CLEAN must restore English text while preserving the original yellow frame.
# No assertion of alpha0: validate source/CLEAN/original persisted native separately.
assert np.count_nonzero(carr[:,:,3])>0,"Expected opaque yellow source plate; do not render on blank canvas"
# All final pixels outside source glyph bbox remain byte-exact as prior.
font_path=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
assert font_path.is_file(),"Required Noto CJK Regular font unavailable; no fallback"
font_bytes=font_path.read_bytes()
font_sha=sha(font_bytes)
charset="일반 밸런스"
collection=TTCollection(str(font_path),lazy=True)
coverage=collection.fonts[1].getBestCmap()
assert all(ord(c) in coverage for c in charset if c!=" "),"Font glyph coverage missing"
# Source-fitted native lettering using the Regular face; not scaling rejected A222 glyph raster.
font=ImageFont.truetype(str(font_path),65,index=1)
# Native spacing, source italic lean (positive top-minus-bottom x).
tracking=2
parts=[]
for ch in charset:
    if ch==" ":
        parts.append((ch,round(font.getlength(" "))+tracking))
    else:parts.append((ch,round(font.getlength(ch))+tracking))
canvas_w=sum(p[1] for p in parts)+24
canvas_h=91
layer=Image.new("L",(canvas_w,canvas_h),0)
d=ImageDraw.Draw(layer);cursor=5
for ch,adv in parts:
    if ch!=" ":d.text((cursor,3),ch,font=font,fill=255,stroke_width=0)
    cursor+=adv
# Preserve true Regular strokes; skew right at top over actual native glyph height.
bb=layer.getbbox()
assert bb
glyph=layer.crop(bb)
gW,gH=glyph.size
shear=0.265
pad=int(gH*shear)+3
# Pixel forward correspondence: output.top.x > output.bottom.x.
slanted=glyph.transform((gW+pad,gH),Image.Transform.AFFINE,
                     (1,shear,-shear*(gH-1)+2,0,1,0),resample=Image.Resampling.BICUBIC)
sb=slanted.getbbox();assert sb, "Empty glyph"
slanted=slanted.crop(sb)
# Source optical family: 65ppem true outlines are downsampled once to measured English 43px body.
# Resize the new independent glyph-mask only; old Korean DDS and CLEAN plate never rescaled.
prefit_height=slanted.height
assert prefit_height>=43, prefit_height
slanted=slanted.resize((slanted.width,43),Image.Resampling.LANCZOS)
sb2=slanted.getbbox();assert sb2
slanted=slanted.crop(sb2)
w,h=slanted.size
assert 295<=w<=354 and h<=43,(w,h)
# C1 newly identified EXACT source-effect bbox 354x45, stricter than yellow plate bbox 390x72.
# Fail closed if a single pixel of Korean glyph exceeds original English source height.
exact_source_effect=(1432,1980,1786,2025)
assert 0<w<=354 and 0<h<=45,(w,h)
x=exact_source_effect[0]+(354-w)//2
y=exact_source_effect[1]+(45-h)//2
assert x>=1432 and y>=1980 and x+w<=1786 and y+h<=2025,(x,y,w,h)
# Original olive source fill, no arbitrary bevel or opaque pasted rectangle.
rgb=(143,137,84)
glyph_layer=Image.new("RGBA",(390,72),(0,0,0,0))
color=Image.new("RGBA",slanted.size,rgb+(0,))
color.putalpha(slanted)
glyph_layer.alpha_composite(color,(x-1411,y-1968))
# Existing CLEAN verified alpha0 in this region; composite-only lettering.
gl=np.asarray(glyph_layer,dtype=np.uint8)
edited=np.array(Image.alpha_composite(clean.crop(source_bbox),glyph_layer),dtype=np.uint8)
# Fully preserved clean plate outside the new letter/effect mask.
outside=(gl[:,:,3]==0)
assert np.array_equal(edited[outside],carr[outside]),"New text changed CLEAN outside lettering"
# Restrict changed pixels to source exact bbox; original already CLEAN from A108.
newdata=bytearray(prior)
for row in range(72):
    readable_y=1968+row
    raw_y=H-1-readable_y
    off=128+(raw_y*W+1411)*4
    newdata[off:off+390*4]=edited[row].tobytes()
newdata=bytes(newdata)
assert newdata[:128]==prior[:128] and sha(newdata)!=prior_sha
dds=out/"A224_Q103_OPTICAL_CONTOUR_UNPROMOTED.dds"
dds.write_bytes(newdata)
persisted=Image.open(dds).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
actual=np.asarray(persisted.crop(source_bbox),dtype=np.uint8)
assert np.array_equal(actual,edited),"Persisted decoded bytes mismatch"
changed=np.flatnonzero(np.frombuffer(prior,dtype=np.uint8)!=np.frombuffer(newdata,dtype=np.uint8))
assert len(changed)>0
beyond=int(np.count_nonzero(np.any(np.asarray(persisted,dtype=np.uint8)!=np.asarray(before,dtype=np.uint8),axis=2)))
# Region-only edited image: require all mutations inside bbox, no alpha outside.
assert beyond==int(np.count_nonzero(np.any(actual!=barr,axis=2)))
assert np.count_nonzero(edited[:,:,3])>0 and np.count_nonzero(gl[:,:,3])>0
nz=np.nonzero(gl[:,:,3]>0)
local_bbox=[int(min(nz[1])),int(min(nz[0])),int(max(nz[1]))+1,int(max(nz[0]))+1]
global_bbox=[1411+local_bbox[0],1968+local_bbox[1],1411+local_bbox[2],1968+local_bbox[3]]
margins=[global_bbox[0]-1411,1801-global_bbox[2],global_bbox[1]-1968,2040-global_bbox[3]]
assert min(margins)>=1,(margins,global_bbox)
# Verify strict exact English-source EFFECT containment, not merely yellow selection PLATE bounds.
assert global_bbox[0]>=1432 and global_bbox[1]>=1980 and global_bbox[2]<=1786 and global_bbox[3]<=2025
assert global_bbox[2]-global_bbox[0]<=354 and global_bbox[3]-global_bbox[1]<=45
assert np.count_nonzero(gl[:,:(1432-1411),3])==0
assert np.count_nonzero(gl[:,(1786-1411):,3])==0
assert np.count_nonzero(gl[:(1980-1968),:,3])==0
assert np.count_nonzero(gl[(2025-1968):,:,3])==0

# On the opaque plate both background and lettering have alpha; verify no foreign blocks.
assert np.array_equal(edited[gl[:,:,3]==0],carr[gl[:,:,3]==0])
# Single-family native source/CLEAN/old/new evidence without hiding other atlas.
rect=(1376,1943,1830,2048)
def graybg(im,bg):
    return Image.alpha_composite(Image.new("RGBA",im.size,bg),im.convert("RGBA")).convert("RGB")
for label,img in (("SOURCE",source),("CLEAN",clean),("OLD",before),("TRIAL",persisted)):
    img.crop(rect).save(out/f"A224_{label}_NATIVE_RGBA.png")
for bgname,bg in (("BLACK",(0,0,0,255)),("GRAY",(110,110,110,255)),("WHITE",(255,255,255,255))):
    ims=[graybg(im.crop(rect),bg) for im in (source,clean,before,persisted)]
    for pct in (100,75,50):
        w2,h2=(round(rect[2]-rect[0])*pct//100,round(rect[3]-rect[1])*pct//100)
        rows=[v if pct==100 else v.resize((w2,h2),Image.Resampling.LANCZOS) for v in ims]
        sheet=Image.new("RGB",(w2*4,h2+27),bg[:3]);paint=ImageDraw.Draw(sheet)
        for i,(name,img) in enumerate(zip(("EN SOURCE","CLEAN","A197 REJECT","A224 OPTICAL PILOT"),rows)):
            sheet.paste(img,(w2*i,27));paint.text((i*w2+5,5),name,fill=(255,255,255) if bgname!="WHITE" else (0,0,0))
        sheet.save(out/f"A224_COMPARE_{bgname}_{pct}.png")
raw=Image.open(dds).convert("RGBA")
raw.crop((rect[0],H-rect[3],rect[2],H-rect[1])).save(out/"A224_TRIAL_RAW_NATIVE_RGBA.png")
Image.fromarray(gl[:,:,3],mode="L").save(out/"A224_LETTERING_NATIVE_ALPHA.png")
report={"schema_version":2,"run":"A224","run_key":"OUTRUN-KOR-A224-Q103-C1-SOURCE-45PX-BOUNDARY-20261010-1300","role":"A","queue_index":103,
"triage":triage[:2600],"independent_C1_rework":"OUTRUN-KOR-C1-Q103-A222-STRICT-SOURCE-HEIGHT-FAIL-20261010",
"source_sha256":source_sha,"source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
"source_bbox":list(source_bbox),"exact_source_effect_bbox":[1432,1980,1786,2025],"source_family":{"en":"Normal Balance","ko":"일반 밸런스","english_font":"medium-light condensed right-italic","en_source_color":list(rgb)},
"old_sha256":prior_sha,"new_trial_sha256":sha(newdata),"trial_dds_path":str(dds.relative_to(repo)),
"font_file":str(font_path),"font_sha256":font_sha,"font_face_index":1,"font_coverage":True,
"method_change":"A223 49px + 11 tracking had 284x45 but loose/small source optics. New 65ppem genuine Regular outlines + 2px tracking, once downsampled glyph mask to 43px source-optical target within original English 354x45 exact effect; no reuse/resizing of prior raster.",
"output_bbox":global_bbox,"output_margins":margins,"letters_layer_only":True,"clean_plate_type":"OPAQUE_GRADIENT_SOURCE_PLATE_PRESERVED",
"full_other_atlas_preservation":True,"changed_rgba_pixels_vs_A197":beyond,"changed_bytes":int(len(changed)),
"outside_source_bbox_changed_rgba":0,"outside_source_bbox_changed_alpha":0,
"source_glyph_size_limit":True,"original_exact_effect_bbox":[1432,1980,1786,2025],"new_glyph_width":w,"new_glyph_height":h,"pre_fit_native_mask_height":prefit_height,"fit":"1x native glyph-mask-only Lanczos height 43, english 45px source ceiling","tracking_px":tracking,"C1_A222_rejected_height":60,"raw_y_mirror":True,"source_clean_final_images":"SOURCE/CLEAN/OLD/TRIAL native, black/gray/white100/75/50, RAW, lettering transparent",
"native":[2048,2048],"DDS":"RGBA32 mip1","firstlook":"PENDING_CONTROLLER_VISUAL","strict_source_effect_gate":"PASS_SOURCE_354x45_CONTAINED",
"producer_scope":"SINGLE_NORMAL_BALANCE_LABEL_TRIAL_UNPROMOTED","hd_candidates_changed":False,
"new_trial_dds":1,"new_promoted_dds":0,"C1":"FRESH_INDEPENDENT_REQUIRED","C3":"NOT_RUN","user_ingame":"UNTESTED","RUNTIME_VALIDATION":"UNTESTED",
"exclusions":["VR","FFB","DX11","DXVK"]}
(out/"A224_MACHINE_TRIAL_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"sha":sha(newdata),"width_height":[w,h],"bbox":global_bbox,"margins":margins,"changed_pixels":beyond},ensure_ascii=False))
