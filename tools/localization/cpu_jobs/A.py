#!/usr/bin/env python3
"""A204 q175 independent source-chrome / geometric Hangul REPRESENTATIVE trial.

Read-only candidate preview, fail-closed before DDS promotion. The script
uses a geometrically distinct Hangul contour family and takes chrome bands
from the original English DDS pixels, not a generic blur/stretch/bevel.
"""
import hashlib
import json
import os
import struct
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter1d, grey_closing, distance_transform_edt

assert os.environ.get("OUTRUN_CPU_WORKER") == "github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE") == "A"
ROOT=Path.cwd()
RUN="20261009-A204-Q175-SOURCE-CHROME-GEOMETRIC-TRIAL"
OUT=ROOT/"localization/graphics/role_A"/RUN
OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/"localization/graphics/role_A/20261008-A188-Q175-CHROME-FACE-RECOVERY"
CAND=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
SRC_SHA="9314372585b8309f2f8b3e714076ef1ad1999d770422a570398ef20a80ac10a5"
OLD_SHA="b9f60b4582ddb4db525806454078471e1045f30a2d65e6da4d4681b87ee6ba73"
FONT_URL="https://raw.githubusercontent.com/JAMO-TYPEFACE/Orbit/main/Fonts/ttf/Orbit-Regular.ttf"
FONT_GIT_BLOB="5f7f97f84a88e2fa34c4afdc3ba69b08f13d0783"
ROWS=[
 ("stage_select","stage select","스테이지 선택",(6,254,1372,397)),
 ("showroom","showroom","쇼룸",(6,397,956,529)),
 ("single_player","single player","싱글 플레이",(2,566,1386,717))
]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_dds(path):
    data=Path(path).read_bytes()
    w,h=struct.unpack_from("<II",data,16)
    if data[:4]!=b"DDS " or (w,h)!=(2048,1024) or len(data)!=128+w*h*4:
        raise ValueError("unexpected DDS size/format")
    masks=struct.unpack_from("<IIII",data,92)
    if masks!=(16711680,65280,255,4278190080) or struct.unpack_from("<I",data,88)[0]!=32:
        raise ValueError("DDS is not expected BGRA32")
    if struct.unpack_from("<I",data,28)[0]!=1:
        raise ValueError("DDS mips unexpectedly changed")
    return data[:128],Image.frombytes("RGBA",(w,h),data[128:],"raw","BGRA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def gitblob(p):
    b=Path(p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def rgba_on_gray(im,color=(100,100,100)):
    bg=Image.new("RGBA",im.size,(*color,255))
    bg.alpha_composite(im)
    return bg.convert("RGB")
def make_font_mask(text, font, maxw, maxh):
    # Make Hangul from Orbit outlines at native 2048 resolution.
    # The original English techno geometry has long horizontal connections;
    # preserve geometric, distinct syllable counters; never enlarge a low-res raster.
    for sz in range(156,85,-1):
        f=ImageFont.truetype(str(font),sz)
        canvas=Image.new("L",(1900,260),0)
        dr=ImageDraw.Draw(canvas)
        dr.text((30,8),text,font=f,fill=255,stroke_width=3,stroke_fill=255)
        bbox=canvas.getbbox()
        if bbox is None:continue
        crop=canvas.crop(bbox)
        # Source-derived horizontal connection, very short (not across letters).
        array=np.array(crop)
        shaped=grey_closing(array,size=(1,4))
        out=Image.fromarray(shaped.astype(np.uint8),"L")
        if out.width <= maxw and out.height <= maxh and out.height >= maxh*0.78:
            return out,sz
    raise ValueError("no native geometric font fits original box")
def chrome_profile(source_box):
    pix=np.asarray(source_box.convert("RGBA"))
    al=pix[:,:,3]
    h=pix.shape[0]
    samples=[]
    for y in range(h):
        lum=pix[y,:,:3].astype(np.float32).mean(axis=1)
        good=al[y]>160
        samples.append(float(np.percentile(lum[good],55)) if good.sum()>20 else np.nan)
    samples=np.array(samples,dtype=np.float32)
    good=np.flatnonzero(np.isfinite(samples))
    if len(good)<25:raise ValueError("source color family missing")
    profile=np.interp(np.arange(h),good,samples[good])
    return np.clip(gaussian_filter1d(profile,1.6),38,252)
if not CAND.exists() or sha(CAND)!=OLD_SHA:
    raise RuntimeError("q175 current DDS SHA drift; do not retry prior bytes")
oldhead,old=load_dds(CAND)
clean=Image.open(BASE/"754F0599_HD_CLEAN_PLATE.png").convert("RGBA")
with tempfile.TemporaryDirectory(prefix="outrun_a204_") as t:
    srcp=Path(t)/"english.dds"
    fontp=Path(t)/"Orbit-Regular.ttf"
    urllib.request.urlretrieve(SRC_URL,srcp)
    urllib.request.urlretrieve(FONT_URL,fontp)
    if sha(srcp)!=SRC_SHA or gitblob(fontp)!=FONT_GIT_BLOB:
        raise RuntimeError("pinned source or licensed font drift")
    srch,source=load_dds(srcp)
    if srch!=oldhead or clean.size!=source.size or source.size!=old.size:
        raise RuntimeError("source/CLEAN/current structure drift")
    sa=np.asarray(source).copy()
    ca=np.asarray(clean).copy()
    previous=np.asarray(old).copy()
    allowed=np.zeros((1024,2048),dtype=bool)
    for _,_,_,(x0,y0,x1,y1) in ROWS:
        allowed[y0:y1,x0:x1]=True
    source_clean_out=int(np.count_nonzero(np.any(sa!=ca,axis=2)&~allowed))
    prior_current_out=int(np.count_nonzero(np.any(previous!=ca,axis=2)&~allowed))
    if source_clean_out or prior_current_out:
        raise RuntimeError(("plate/rework outside exact source",source_clean_out,prior_current_out))
    final=clean.copy()
    masks=[]
    rec=[]
    for key,english,korean,(x0,y0,x1,y1) in ROWS:
        h=y1-y0
        w=x1-x0
        glyph,size=make_font_mask(korean,fontp,w-18,h-16)
        gx=x0+8
        gy=y0+(h-glyph.height)//2
        ga=np.array(glyph,dtype=np.uint8)
        lum=chrome_profile(source.crop((x0,y0,x1,y1)))
        # Transfer metallic bands at source-normalized y; local 3px signed
        # contour bevel is clipped *inside* the Hangul glyph, never an added box.
        yy=np.clip((np.arange(ga.shape[0])+gy-y0),0,len(lum)-1)
        luma=lum[yy][:,None]
        d=distance_transform_edt(ga>=24)
        upper=np.clip(5-d,0,5)/5
        band=np.broadcast_to(luma,ga.shape)
        mapped=np.clip(band+14*upper-5*(d<2),25,252).astype(np.uint8)
        face=np.zeros((ga.shape[0],ga.shape[1],4),dtype=np.uint8)
        face[:,:,:3]=mapped[:,:,None]
        face[:,:,3]=ga
        # Shadow only within the previously source-measured effect box.
        fg=Image.fromarray(face,"RGBA")
        shad=Image.new("RGBA",fg.size,(28,28,33,0))
        shad.putalpha(Image.fromarray((ga.astype(np.uint16)*0.7).astype(np.uint8),"L"))
        for overlay,shift in ((shad,(3,5)),(fg,(0,0))):
            px,py=gx+shift[0],gy+shift[1]
            if px+overlay.width>=x1-1 or py+overlay.height>=y1-1:
                raise RuntimeError(("source bbox edge",key))
            final.alpha_composite(overlay,(px,py))
        scope=np.zeros((1024,2048),dtype=bool)
        scope[gy:gy+glyph.height,gx:gx+glyph.width]|=ga>0
        scope[gy+5:gy+5+glyph.height,gx+3:gx+3+glyph.width]|=ga>0
        for prev in masks:
            if (prev&scope).any():raise RuntimeError("title collision")
        masks.append(scope)
        by,bx=np.nonzero(scope)
        bbox=[int(bx.min()),int(by.min()),int(bx.max()+1),int(by.max()+1)]
        margins=[bbox[0]-x0,x1-bbox[2],bbox[1]-y0,y1-bbox[3]]
        if any(x<=0 for x in margins):raise RuntimeError(("bbox overflow",key,bbox))
        rec.append({"key":key,"english":english,"korean":korean,"source_bbox":[x0,y0,x1,y1],
                    "trial_bbox":bbox,"size":[bbox[2]-bbox[0],bbox[3]-bbox[1]],"source_size":[w,h],
                    "margins":margins,"font_size":size,"profile_sample":[float(lum[i]) for i in (10,len(lum)//2,len(lum)-10)]})
    fa=np.asarray(final)
    changed=np.any(ca!=fa,axis=2)
    union=np.logical_or.reduce(masks)
    metrics={"clean_to_trial_changed_outside_source":int((changed&~allowed).sum()),
             "clean_to_trial_changed_outside_glyph":int((changed&~union).sum()),
             "clean_to_trial_alpha_changed_outside_source":int(((ca[:,:,3]!=fa[:,:,3])&~allowed).sum()),
             "old_to_trial_changed_outside_source":int((np.any(previous!=fa,axis=2)&~allowed).sum()),
             "source_to_clean_changed_outside_source":source_clean_out}
    if any(metrics.values()):raise RuntimeError(("pre-DDS preview mask fail",metrics))
    for idx,(key,eng,kor,bb) in enumerate(ROWS):
        x0,y0,x1,y1=bb
        bb2=(max(0,x0-4),max(0,y0-5),min(2048,x1+8),min(1024,y1+8))
        crops=[rgba_on_gray(im).crop(bb2) for im in (source,clean,old,final)]
        w,h=crops[0].size
        sheet=Image.new("RGB",(w*4+24,h+32),"white")
        ImageDraw.Draw(sheet).text((3,5),f"A204 q175 {key}: ENGLISH | CLEAN | REJECTED A188 | NEW GEOMETRIC TRIAL",fill="black")
        for i,im in enumerate(crops):sheet.paste(im,(i*(w+8),32))
        for percent in (100,75,50):
            view=sheet if percent==100 else sheet.resize((sheet.width*percent//100,sheet.height*percent//100),Image.Resampling.LANCZOS)
            view.save(OUT/f"A204_{idx}_{key}_{percent}.jpg",quality=94)
    source.save(OUT/"A204_SOURCE_READABLE.png")
    final.save(OUT/"A204_TRIAL_FINAL_READABLE.png")
    clean.save(OUT/"A204_CLEAN_READABLE.png")
    raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    raw.resize((1024,512),Image.Resampling.LANCZOS).save(OUT/"A204_TRIAL_RAW_50.png")
    report={"role":"A","task":"A204","queue_index":175,"priority":"P1","user_report":"IGR-032",
        "status":"TRIAL_ONLY_PENDING_CONTROLLER_VISUAL_NOT_PROMOTED","source_sha256":SRC_SHA,
        "prior_exact_dds_sha256":OLD_SHA,"trial_method":"OFL Orbit geometric native Hangul outline plus measured English chrome y-band transfer + local inside-contour bevel; not stretched prior DDS",
        "font_origin":"JAMO-TYPEFACE/Orbit (OFL-1.1)","font_blob_sha1":FONT_GIT_BLOB,
        "rows":rec,"qa_preview":metrics,"dds_produced":0,"dds_replaced":False,
        "runtime_validation":"UNTESTED",
        "next_gate":"Controller SOURCE/CLEAN/OLD/TRIAL native+RAW+50 before any DDS promotion; reject if still unlike connected English techno letterform; then 10-stage persisted DDS QA and independent C1/C3"}
    (OUT/"A204_TRIAL_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("A204_TRIAL_PROOF",json.dumps({"source":SRC_SHA[:16],"rows":rec,"qa":metrics,"trial":"NOT_DDS"},ensure_ascii=False),flush=True)
