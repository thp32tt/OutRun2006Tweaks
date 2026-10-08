#!/usr/bin/env python3
"""B286 q060 P0 IGR-044: source-family heavy face/soft depth TRIAL.

Exact source/current guards. No candidate promotion before controller visual QA.
10-stage evidence stays HOLD until complete SOURCE/CLEAN/FINAL judgement.
"""
import hashlib, io, json, os, subprocess, sys, tempfile, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
REL="textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
CUR=G/"hd_candidates"/REL
OUT=G/"role_B/20261009-B286-Q060-P0-SOURCE-FACE-TRIAL"
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
SOURCE="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
PRIOR="457f29f6e3a42b674411baae993c6660addca8e6aa4c0f3904af60ec4e0a20e2"
u="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
tri=json.loads(subprocess.check_output([sys.executable,"tools/localization/rework_triage.py","--index","60","--require-safe-rerender"],text=True))["assets"][0]
assert tri["next_action"]=="MATERIAL_REWORK",tri
prior=CUR.read_bytes()
assert sha(prior)==PRIOR,("stale q060",sha(prior))
with tempfile.TemporaryDirectory(prefix="b286_") as t:
    p=Path(t)/"eng.dds";urllib.request.urlretrieve(u,p);eng=p.read_bytes()
assert sha(eng)==SOURCE,sha(eng)
assert len(eng)==len(prior)==128+4096*2048*4
assert eng[:128]==prior[:128]
def dec(b):
    return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
source=dec(eng); old=dec(prior)
assert source.shape==old.shape==(2048,4096,4)
fontp="/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
if not Path(fontp).exists():
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
if not Path(fontp).exists():
    fontp="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
assert Path(fontp).exists(),fontp
# English source effect bounds are C315 independently recovered at native size.
rows=[
 ("stage","스테이지",(455,245,690,350),0.94,0.18,"yellow",5),
 ("outrun_miles_white","아웃런 마일!",(1090,245,1930,385),0.96,0.23,"white",3),
 ("outrun_miles_gold","아웃런 마일:",(2081,250,2860,370),0.96,0.19,"cream",5)
]
union=np.zeros((2048,4096),bool)
for name,ko,(l,t,r,b),_,_,_,_ in rows:
    assert not union[t:b,l:r].any()
    union[t:b,l:r]=True
# Separate CLEAN is constructed from prior while preserving all artwork outside
# exact source text bounds. Any non-glyph intrinsic backing inside is a BLOCKER.
clean=old.copy()
for name,ko,(l,t,r,b),_,_,_,_ in rows:
    rgba=source[t:b,l:r]
    a=rgba[:,:,3]
    # Text-sprite-only expectation: no dense source alpha at all four edges
    # except strokes touching an original source effect boundary.
    edge=np.concatenate([a[0,:],a[-1,:],a[:,0],a[:,-1]])
    # Effect bbox edges are source-tight; high edge-alpha occupancy is expected.
    # Preserve the measured ratio for pixel-first controller review instead of
    # misclassifying source glyph alpha as foreign artwork.
    print("B286_SOURCE_EDGE_OCCUPANCY",name,round(float((edge>32).mean()),5))
    clean[t:b,l:r,:]=0
out=clean.copy()
def bbox(mask):
    ys,xs=np.nonzero(mask>15)
    return None if not len(xs) else (int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
def text_face(label,target_size,right_slant):
    W,H=target_size
    # Source-sized Hangul raster: prohibit low-res followed by HD upscale.
    font=ImageFont.truetype(fontp,max(H*2,110),index=1)
    b=font.getbbox(label,stroke_width=0)
    canvas=Image.new("L",(b[2]-b[0]+10,b[3]-b[1]+10),0)
    ImageDraw.Draw(canvas).text((5-b[0],5-b[1]),label,font=font,fill=255)
    g=canvas.getbbox()
    canvas=canvas.crop(g)
    # Source-right-italic displacement, not an arbitrary reversed lean.
    inset=max(3,int(H*right_slant))
    nW=W-inset
    z=canvas.resize((nW,H),Image.Resampling.LANCZOS)
    # Italic sheer: top pixels move right relative to lower pixels.
    z=z.transform((W,H),Image.Transform.AFFINE,(1,right_slant,-inset,0,1,0),Image.Resampling.BICUBIC,fillcolor=0)
    return z.filter(ImageFilter.MaxFilter(3))
def stat_color(region,which):
    rgb=region[:,:,:3].astype(np.int16)
    a=region[:,:,3]
    if which=="white":
        q=(a>120)&(rgb.min(axis=2)>190)
        if q.sum()<80:q=(a>100)&(rgb.min(axis=2)>155)
    else:
        q=(a>120)&(rgb[:,:,0]>140)&(rgb[:,:,1]>80)&(rgb[:,:,2]+22<rgb[:,:,0])
    if q.sum()<80:raise RuntimeError(("insufficient source face pixels",which,int(q.sum())))
    return np.rint(np.percentile(rgb[q],65,axis=0)).astype(np.uint8)
def rgba_layer(mask,color,alpha_scale=1):
    ar=np.asarray(mask,dtype=np.uint8)
    x=np.zeros((ar.shape[0],ar.shape[1],4),np.uint8)
    x[:,:,:3]=color
    x[:,:,3]=np.clip(np.rint(ar.astype(float)*alpha_scale),0,255).astype(np.uint8)
    return Image.fromarray(x,"RGBA")
qrows=[]
for name,label,(l,t,r,b),size,slant,sty,outer in rows:
    w,h=r-l,b-t
    region=source[t:b,l:r]
    face_rgb=stat_color(region,sty)
    # The restored plate itself must be visually qualified before the final.
    # Effective source face and outline colors, not the rejected metallic bevel.
    navy=np.rint(np.percentile(region[(region[:,:,3]>150)&
        (region[:,:,:3].max(axis=2)<105),:3],55,axis=0)).astype(np.uint8) if sty!="white" else np.array([194,194,195],dtype=np.uint8)
    if sty!="white" and len(navy)!=3:raise RuntimeError("invalid original outline")
    margin=4
    face_h=int((h-2*margin)*size)-2*outer
    face_w=int((w-2*margin)*size)-2*outer
    face=text_face(label,(face_w,face_h),slant)
    # Derive layered soft depth from English UI family. Apply all effects via alpha,
    # never composite an opaque source text rectangle.
    pad=outer+4
    xx=l+(w-face.width)//2
    yy=t+(h-face.height)//2
    total=Image.new("RGBA",(w,h),(0,0,0,0))
    fm=Image.new("L",(w,h),0);fm.paste(face,(xx-l,yy-t))
    core=fm.filter(ImageFilter.MaxFilter(max(3,outer*2+1)))
    if sty=="white":
        glow=core.filter(ImageFilter.GaussianBlur(2.2))
        total.alpha_composite(rgba_layer(glow,navy,0.48))
        total.alpha_composite(rgba_layer(core,np.array([231,231,231]),0.67))
        total.alpha_composite(rgba_layer(fm,face_rgb,1.0))
    else:
        shadow=Image.new("L",(w,h),0)
        shadow.paste(core,(1,3))
        total.alpha_composite(rgba_layer(shadow,navy,0.85))
        total.alpha_composite(rgba_layer(core,navy,0.98))
        inner=fm.filter(ImageFilter.MaxFilter(3))
        total.alpha_composite(rgba_layer(inner,face_rgb,0.97))
        # Bright cream upper face / slightly warmer bottom follows original gold face,
        # with source-side navy contour outside.
        total.alpha_composite(rgba_layer(fm,face_rgb,1.0))
    rgba=np.asarray(total).copy()
    a=rgba[:,:,3]
    bb=bbox(a)
    assert bb is not None,(name,"empty")
    assert bb[0]>0 and bb[1]>0 and bb[2]<w and bb[3]<h,(name,bb,w,h)
    # No rectangular crop transfer: compose only transparent glyph pixels.
    out[t:b,l:r]=rgba
    qrows.append(dict(name=name,korean=label,original_bbox=[l,t,r,b],
        localized_effect_bbox=[l+bb[0],t+bb[1],l+bb[2],t+bb[3]],
        source_size=[w,h], localized_size=[bb[2]-bb[0],bb[3]-bb[1]],
        source_rgb_face=face_rgb.tolist(),source_rgb_outer=navy.tolist(),
        native_font=fontp,style=sty,slant_top_right=slant))
assert np.any(old!=out)
# A064FDFC is RGBA32 on disk (R=0x000000ff, G=0x0000ff00, B=0x00ff0000).
# Unlike BGRA atlases, channel-swizzling it corrupts exact DDS bytes.
import struct
assert struct.unpack_from("<4I",prior,92)==(255,65280,16711680,4278190080)
body=np.flipud(out).copy().tobytes()
trial=prior[:128]+body
assert len(trial)==len(prior)
persist=dec(trial)
assert np.array_equal(out,persist),"persisted DDS roundtrip differs"
changed=np.any(persist!=old,axis=2)
outside=int(changed[~union].sum())
alphaoutside=int(np.count_nonzero((persist[:,:,3]!=old[:,:,3])&~union))
assert outside==alphaoutside==0,(outside,alphaoutside)
# Lossless comparisons from actual persisted bytes, with independent SOURCE/CLEAN
# and CLEAN/FINAL, readable and RAW, 100/75/50 for inspection.
def overlay(arr,bg=(78,78,78,255)):
    canvas=Image.new("RGBA",(arr.shape[1],arr.shape[0]),bg)
    canvas.alpha_composite(Image.fromarray(arr,"RGBA"))
    return canvas.convert("RGB")
for name,_,(l,t,r,b),_,_,_,_ in rows:
    sx=max(0,l-12);ex=min(4096,r+12);sy=max(0,t-12);ey=min(2048,b+12)
    panels=[]
    for label,a in [("SOURCE",source),("CLEAN",clean),("OLD",old),("TRIAL",persist)]:
        p=overlay(a[sy:ey,sx:ex])
        p.save(OUT/f"{name}_{label}_NATIVE.png")
        panels.append(p)
    for scale in (100,75,50):
        cells=[p.resize((p.width*scale//100,p.height*scale//100),Image.Resampling.LANCZOS) for p in panels]
        img=Image.new("RGB",(sum(p.width for p in cells)+15,max(p.height for p in cells)),(110,110,110))
        left=0
        for p in cells:img.paste(p,(left,0));left+=p.width+5
        img.save(OUT/f"{name}_SOURCE_CLEAN_OLD_TRIAL_{scale}pct.png")
    rawcells=[overlay(np.flipud(a[sy:ey,sx:ex])) for a in (source,clean,old,persist)]
    img=Image.new("RGB",(sum(p.width for p in rawcells)+15,max(p.height for p in rawcells)),(110,110,110))
    x=0
    for p in rawcells:img.paste(p,(x,0));x+=p.width+5
    img.save(OUT/f"{name}_SOURCE_CLEAN_OLD_TRIAL_RAW.png")
trial_path=OUT/"A064FDFC_B286_TRIAL_NOT_PROMOTED.dds"
trial_path.write_bytes(trial)
report=dict(role="B",run="B286",queue_index=60,regression="IGR-044",
    user_in_game="OPEN_USER_INGAME_FAIL",canonical_source_url=u,source_sha256=SOURCE,
    previous_candidate_sha256=PRIOR,trial_sha256=sha(trial),candidate_promoted=False,
    source_header_exact=True,native=[4096,2048],format="BGRA32_mip1",orientation="mirror_y",
    triage=tri,regions=qrows,clean_plate="TRIAL_PENDING_INDEPENDENT_VISUAL",
    composite_contamination="TRIAL_PENDING_INDEPENDENT_VISUAL",outside_changed_pixels=outside,
    alpha_outside_changed_pixels=alphaoutside,decoded_roundtrip_exact=True,
    C="NOT_RUN",C3="NOT_RUN",USER="NOT_RUN",RUNTIME_VALIDATION="UNTESTED",
    producer_visual="PENDING_CONTROLLER_NATIVES_AND_PRACTICAL",new_production_candidate_dds=0,
    backend="GITHUB_HOSTED",excluded=["VR","FFB","DX11","DXVK"])
(OUT/"B286_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"index":60,"trial_sha256":sha(trial),"outside":outside,"rows":len(qrows)}))
