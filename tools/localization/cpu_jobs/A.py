#!/usr/bin/env python3
"""A254: q175 P1 SHOWROOM source-conditioned Korean metal type; isolated new DDS trial.

Replaces rejected A216 roof/rails strokes with individually readable source-height
Hangul contours. Whole-atlas C2/C3 and user game tests are not asserted.
"""
import csv, hashlib, json, os, struct, subprocess, sys, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import maximum_filter, gaussian_filter

R=Path.cwd()
D=R/"localization/graphics/role_A/20261012-A254-Q175-NATIVE-CHROME-GLYPH"
RUN="OUTRUN-KOR-A254-Q175-P1-REAL-GLYPH-SOURCE-METAL-20261012-0800"
Q=175; W,H=2048,1024; BOX=(6,397,956,529)
SOURCE_SHA="9314372585b8309f2f8b3e714076ef1ad1999d770422a570398ef20a80ac10a5"
REJECT_SHA="a5e921ab2563a1ec6a3a1954a247a07d0a9adb9e101c4d73682600476e39323c"
OFFICIAL_SHA="b9f60b4582ddb4db525806454078471e1045f30a2d65e6da4d4681b87ee6ba73"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
OLD=R/"localization/graphics/role_A/20261010-A216-Q175-WELDED-MANUAL-SOURCE-CHROME/A216_Q175_MANUAL_SOURCE_WELDED_CHROME_TRIAL.dds"
REVIEW=R/"localization/graphics/role_A/20261010-A216-Q175-WELDED-MANUAL-SOURCE-CHROME/A216_CONTROLLER_VISUAL_REJECT.json"
FONT=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="A"
def sha(b):return hashlib.sha256(b).hexdigest()
def require(ok,msg):
    if not ok:raise RuntimeError("A254_FAIL_CLOSED: "+msg)
def digest(p):return {"path":str(p.relative_to(R)),"sha256":sha(p.read_bytes())}
def store_img(name,img):
    p=D/(name+".png");img.save(p);return digest(p)
def store_json(name,obj):
    p=D/(name+".json")
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return digest(p)
def read_dds(b):
    require(len(b)==128+W*H*4 and b[:4]==b"DDS ","source/native RGBA32 dimensions")
    require(struct.unpack_from("<II",b,12)==(H,W) and struct.unpack_from("<I",b,28)[0]==1,
            "source/native dimensions or mip drift")
    require(struct.unpack_from("<I",b,88)[0]==32,"source/native bpp drift")
    rm=struct.unpack_from("<I",b,92)[0]
    bm=struct.unpack_from("<I",b,100)[0]
    require((rm,bm) in ((0x00ff0000,0x000000ff),(0x000000ff,0x00ff0000)),
            "unsupported channel masks")
    raw="BGRA" if rm==0x00ff0000 else "RGBA"
    decoded=Image.frombytes("RGBA",(W,H),b[128:],"raw",raw).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return np.asarray(decoded).copy(),raw
def pack_dds(header,rgba,raw):
    return header+Image.fromarray(rgba,"RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw",raw)
with (R/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
    queue=next(v for v in csv.DictReader(f) if v["index"]=="175")
require(queue["action"]=="localize_text" and "rework" in queue["artwork_status"].lower(),
        "q175 no longer in material REWORK")
tri=json.loads(subprocess.check_output([sys.executable,
    "tools/localization/rework_triage.py","--index","175"],text=True))
next_action=tri["assets"][0]["next_action"]
require(next_action in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),"triage forbids same-method rerender")
review=json.loads(REVIEW.read_text(encoding="utf-8"))
require(review["trial_dds_sha256"]==REJECT_SHA and
        review["decision"]=="PRODUCER_VISUAL_FAIL_TRIAL_ONLY_NO_PROMOTION" and
        review["source_sha256"]==SOURCE_SHA,"specific failed visual source evidence drift")
oldbytes=OLD.read_bytes()
require(sha(oldbytes)==REJECT_SHA,"rejected A216 old trial changed")
req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"OutRun-A254-source-verified"})
with urllib.request.urlopen(req,timeout=60) as f:sb=f.read()
require(sha(sb)==SOURCE_SHA,"canonical English source mismatch")
S,source_raw=read_dds(sb)
P,raw=read_dds(oldbytes)
require(raw==source_raw,"incompatible source/save DDS encoding")
x0,y0,x1,y1=BOX;h=y1-y0;w=x1-x0
src=S[y0:y1,x0:x1]
require(np.count_nonzero(src[:,:,3]>20)>30000,"canonical source English lettering absent")
require(np.count_nonzero(P[y0:y1,x0:x1,3]>20)>10000,"rejected trial glyph area absent")
require(FONT.is_file(),"no native Korean font")
# New canonical native Korean outlines (not A216 hand rails, an old DDS raster,
# an ImageGen scene, or horizontally stretched old Hangul).
scale=4
font=ImageFont.truetype(str(FONT),169*scale,index=1)
temp=Image.new("L",(2200*scale,400*scale),0)
ImageDraw.Draw(temp).text((30*scale,10*scale),"쇼룸",font=font,fill=255)
bbox=temp.getbbox()
require(bbox is not None,"new Korean vector outlines missing")
glyph=temp.crop(bbox)
target_h=112
target_w=round(glyph.width*target_h/glyph.height)
require(170<=target_w<=320,"new glyph natural aspect outside Korean source-family")
smooth=glyph.resize((target_w*scale,target_h*scale),Image.Resampling.LANCZOS)
# Keep natural Korean syllable shapes, avoid roof/rail false strokes. A light
# round-off operates on genuine glyph masks, not disconnected handmade paths.
smooth=smooth.filter(ImageFilter.GaussianBlur(0.5*scale))
face=smooth.resize((target_w,target_h),Image.Resampling.LANCZOS)
mask=np.asarray(face,dtype=np.uint8)
require((mask>100).sum()>8000,"new native lettering too sparse")
ink=np.zeros((h,w),np.float32)
px=(w-target_w)//2
py=(h-target_h)//2
ink[py:py+target_h,px:px+target_w]=mask.astype(np.float32)/255.0
outer=maximum_filter(ink,size=5)
shadow=np.zeros_like(ink);shadow[3:,3:]=ink[:-3,:-3]
# Verify first pixel production stage, BEFORE constructing effects.
ys,xs=np.where(ink>0.01)
require(len(xs)>6000 and px>=4 and py>=4,"face geometry safety")
face_bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
# Source silver gradient: use actual median English face RGB at native y.
samples=[]
for yy in range(h):
    line=src[yy,:,:]
    sel=line[:,3]>=210
    samples.append(np.median(line[sel,:3],axis=0) if np.count_nonzero(sel)>=16
                   else [np.nan,np.nan,np.nan])
pal=np.asarray(samples,np.float32)
valid=np.isfinite(pal[:,0])
require(valid.sum()>=35,"not enough source chrome rows for source-derived profile")
for c in range(3):
    pal[:,c]=np.interp(np.arange(h),np.where(valid)[0],pal[valid,c])
pal=gaussian_filter(pal,sigma=(2.5,0))
pal=np.clip(pal,45,245).astype(np.uint8)
# Preserve original metal-facing contrast and continuous counters.
rgba=np.zeros((h,w,4),np.uint8)
def add(pixels):
    global rgba
    rgba=np.asarray(Image.alpha_composite(Image.fromarray(rgba,"RGBA"),
                                          Image.fromarray(pixels,"RGBA")),dtype=np.uint8).copy()
shade=np.zeros_like(rgba)
shade[:,:,:3]=[23,24,25];shade[:,:,3]=np.round(shadow*174).astype(np.uint8)
add(shade)
rim=np.zeros_like(rgba)
rim[:,:,:3]=[37,39,42];rim[:,:,3]=np.round(outer*245).astype(np.uint8)
add(rim)
face_layer=np.zeros_like(rgba)
face_layer[:,:,:3]=pal[:,None,:]
face_layer[:,:,3]=np.round(ink*255).astype(np.uint8)
add(face_layer)
# Source-reflective top keyline: the actual source uses bright silver at top.
# Constrain the 1px edge inside the original face, so no decorative foreign roof.
high=np.maximum(ink-np.pad(ink[:-1,:],((1,0),(0,0))),0)
glint=np.zeros_like(rgba)
glint[:,:,:3]=np.clip(pal[:,None,:].astype(np.int16)+14,0,255).astype(np.uint8)
glint[:,:,3]=np.round(high*100).astype(np.uint8)
add(glint)
ys,xs=np.where(rgba[:,:,3]>0)
require(len(xs)>11000,"composed text disappeared")
bb=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
margins=[bb[0],bb[1],w-bb[2],h-bb[3]]
require(min(margins)>=2,"native chrome outside exact English source bbox "+str(margins))
require(bb[3]-bb[1]>=112,"new source-sized lettering too small")
# SOURCE/CLEAN/LETTER/FINAL separation: this sprite's original background is
# alpha-transparent. Replace ONLY A216 rejected region; no resized full atlas.
clean=np.zeros((h,w,4),np.uint8)
T=P.copy()
T[y0:y1,x0:x1]=rgba
delta=np.any(T!=P,axis=2)
allowed=np.zeros((H,W),bool);allowed[y0:y1,x0:x1]=True
changed=int(delta.sum())
require(changed>8000,"not materially different from independently rejected A216")
require(not np.any(delta&~allowed),"protected atlas art mutated")
D.mkdir(parents=True,exist_ok=True)
out=D/"A254_Q175_REAL_HANGUL_METALLIC_UNPROMOTED.dds"
out.write_bytes(pack_dds(oldbytes[:128],T,raw))
V,check_raw=read_dds(out.read_bytes())
require(check_raw==raw and np.array_equal(V,T),"persisted DDS roundtrip changed pixels")
proof={}
proof["source"]=store_img("A254_SOURCE_NATIVE",Image.fromarray(src,"RGBA"))
proof["clean"]=store_img("A254_CLEAN_NATIVE",Image.fromarray(clean,"RGBA"))
proof["face"]=store_img("A254_FACE_NATIVE",Image.fromarray(face_layer,"RGBA"))
proof["rim"]=store_img("A254_RIM_NATIVE",Image.fromarray(rim,"RGBA"))
proof["shadow"]=store_img("A254_SHADOW_NATIVE",Image.fromarray(shade,"RGBA"))
proof["letter"]=store_img("A254_LETTER_NATIVE",Image.fromarray(rgba,"RGBA"))
proof["saved"]=store_img("A254_SAVED_READABLE_NATIVE",Image.fromarray(V[y0:y1,x0:x1],"RGBA"))
proof["raw"]=store_img("A254_SAVED_RAW_NATIVE",Image.fromarray(V[y0:y1,x0:x1],"RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
for name,bg,pct in [("GRAY100",(110,110,110),100),
                    ("WHITE75",(255,255,255),75),
                    ("BLACK50",(0,0,0),50)]:
    nW=max(1,round(w*pct/100));nH=max(1,round(h*pct/100))
    panel=Image.new("RGB",(4*nW,nH),bg)
    for i,arr in enumerate([src,clean,P[y0:y1,x0:x1],V[y0:y1,x0:x1]]):
        im=Image.alpha_composite(Image.new("RGBA",(w,h),(*bg,255)),Image.fromarray(arr,"RGBA"))
        panel.paste(im.convert("RGB").resize((nW,nH),Image.Resampling.LANCZOS),(i*nW,0))
    proof[name]=store_img("A254_"+name+"_SOURCE_CLEAN_A216_NEW",panel)
recipe={
  "version":"a254-native-source-conditioned-metal-v1",
  "queue_index":175,"run_key":RUN,"source_sha256":SOURCE_SHA,
  "source_english":"showroom","new_korean":"쇼룸",
  "source_bbox_readable":BOX,"face_bbox_readable":[x0+face_bbox[0],y0+face_bbox[1],
                                                x0+face_bbox[2],y0+face_bbox[3]],
  "complete_effect_bbox_readable":[x0+bb[0],y0+bb[1],x0+bb[2],y0+bb[3]],
  "font":str(FONT),"font_sha256":sha(FONT.read_bytes()),
  "font_face_index":1,"source_derived_face_palette":pal.tolist(),
  "geometry_method":"new true Noto CJK Korean Hangul outlines at native source-height, natural glyph aspect; AA rounded at 4x; no width stretch or handmade rails",
  "effects":["shadow3x3","outer_rim2px","source_chrome_native_row_median","face_keyline"],
  "source_english_sha_binding":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
  "target":"unpromoted trial only; independent C2 / C3 and user game still mandatory"
}
recipe_ref=store_json("A254_SHA_BOUND_LETTERING_RECIPE",recipe)
report={
  "schema_version":2,"run_key":RUN,"role":"A","queue_index":175,"priority":"P1",
  "reason":"C286 chrome topology/source-family REWORK; A216 manual rail/roof unreadable native/50%",
  "triage":next_action,"A216_independent_producer_reject":str(REVIEW.relative_to(R)),
  "source_sha256":SOURCE_SHA,"source_uri":SOURCE_URL,
  "superseded_rejected_trial_sha256":REJECT_SHA,"official_unchanged_sha256":OFFICIAL_SHA,
  "new_unpromoted_persisted_dds":digest(out),"new_saved_dds":1,"official_promoted_dds":0,
  "source_effect_bbox":BOX,"persisted_glyph_effect_bbox":[x0+bb[0],y0+bb[1],x0+bb[2],y0+bb[3]],
  "effect_margins":margins,"native_size":[W,H],"format":raw+"32","mips":1,
  "source_to_clean_remaining_alpha":0,"saved_dds_roundtrip_mismatch":int(np.count_nonzero(V!=T)),
  "changed_rgba_pixels":changed,"changed_rgba_outside_source_effect_bbox":int(np.count_nonzero(delta&~allowed)),
  "other_ui_protected":"SOURCE_AND_A216_OUTSIDE_ROI_UNCHANGED",
  "pixel_check":"PASS_SCOPED_MACHINE","producer_visual":"PENDING_CONTROLLER_NATIVE_READABLE_AND_RAW",
  "plate":"SOURCE_ROI_ALPHA_CLEAN_ONLY_PRODUCER; independent C2 PLATE_PASS not granted",
  "qa_status":"TRIAL_PENDING_PRODUCER_FIRSTHAND_VISUAL_AND_C2",
  "C2":"NOT_RUN","C3":"NOT_RUN","USER_GAME":"OPEN_IGR032","RUNTIME_VALIDATION":"UNTESTED",
  "lettering_recipe":recipe_ref,"proof":proof,
  "excluded":["VR","FFB","DX11","DXVK"]
}
store_json("A254_MACHINE_AND_HANDOFF",report)
print(json.dumps({"run_key":RUN,"index":175,"new_sha256":digest(out)["sha256"],
                  "changed":changed,"margins":margins},ensure_ascii=False),flush=True)
