#!/usr/bin/env python3
"""A205 P1 q193 native source-weight showroom/intro typography rework trial.

Fail-closed: create QA proofs and an isolated trial DDS, *never* overwrite the
currently promoted DDS without controller-readable visual review.
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

assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
ROOT=Path.cwd()
BASE=ROOT/"localization/graphics/role_A/20261008-A171-Q121-Q193-CLEAN-PLATE"
CAND=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds"
OUT=ROOT/"localization/graphics/role_A/20261009-A205-Q193-SOURCE-WEIGHT-REWORK"
OUT.mkdir(parents=True,exist_ok=True)
ASSET="97E863AD_512x256.dds"
SRC_REPO_COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SRC_URL=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{SRC_REPO_COMMIT}/Release/spr_sprani_sumo_fe_cvt_Exst/{ASSET}"
SRC_SHA="d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451"
CAND_SHA="e21851f5d35ca41bdab1cbfa45db4c1266bc6d0ba03b8bc5791ff785bf313166"
FONT_URL="https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/Korean/NotoSansCJKkr-Black.otf"
FONT_BLOB="b5b67bf293310a3648468a21ac829d6f2d58b2d5"
ROWS=[
    {"key":"welcome","english":"WELCOME TO THE","text":"환영합니다","bbox":(3,148,476,195)},
    {"key":"multiplayer","english":"MULTIPLAYER","text":"멀티플레이어","bbox":(8,297,540,359)},
    {"key":"showroom","english":"SHOWROOM","text":"쇼룸","bbox":(1205,957,1594,1011)}
]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def gitblob(path):
    b=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def dds(path):
    b=Path(path).read_bytes()
    if b[:4]!=b"DDS " or len(b)<128:raise ValueError("invalid DDS")
    h,w=struct.unpack_from("<II",b,12)
    if (w,h)!=(2048,1024) or len(b)!=128+w*h*4:raise ValueError(("format/size drift",len(b),w,h))
    if struct.unpack_from("<I",b,88)[0]!=32 or struct.unpack_from("<IIII",b,92)!=(16711680,65280,255,4278190080):
        raise ValueError(f"unexpected channels bpp={struct.unpack_from('<I',b,88)[0]} masks={struct.unpack_from('<IIII',b,92)}")
    if struct.unpack_from("<I",b,28)[0]!=1:raise ValueError("unexpected mip count")
    im=Image.frombytes("RGBA",(w,h),b[128:],"raw","BGRA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],im
def encode(header,im):
    return header+im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","BGRA")
def render(text,fontpath, maxw,maxh):
    # Font glyph at native 2048-wide texture, no previously Korean raster reuse,
    # no width stretch, no shear, no resampling or font-family guessing.
    for size in range(int(maxh*1.65),18,-1):
        font=ImageFont.truetype(str(fontpath),size)
        scratch=Image.new("L",(maxw+300,maxh+160),0)
        ImageDraw.Draw(scratch).text((8,0),text,fill=255,font=font)
        bound=scratch.getbbox()
        if not bound:continue
        im=scratch.crop(bound)
        if im.height<=maxh-4 and im.width<=maxw-4 and im.height>=int(maxh*0.79):
            return im,size
    raise RuntimeError(("no accurate native font fit",text,maxw,maxh))
def onbg(im,col=(100,100,100)):
    b=Image.new("RGBA",im.size,(*col,255))
    b.alpha_composite(im)
    return b.convert("RGB")
if not CAND.is_file() or sha(CAND)!=CAND_SHA:
    raise RuntimeError("q193 current candidate changed; avoid reworking wrong bytes")
header,old=dds(CAND)
clean=Image.open(BASE/"A171_Q193_97E863AD_CLEAN.png").convert("RGBA")
with tempfile.TemporaryDirectory(prefix="a205_") as tmp:
    sf=Path(tmp)/ASSET
    tf=Path(tmp)/"NotoSansCJKkr-Black.otf"
    urllib.request.urlretrieve(SRC_URL,sf)
    urllib.request.urlretrieve(FONT_URL,tf)
    if sha(sf)!=SRC_SHA:raise RuntimeError(("source byte drift",sha(sf)))
    if gitblob(tf)!=FONT_BLOB:raise RuntimeError(("pinned source-licensed font drift",gitblob(tf)))
    orighead,source=dds(sf)
    if orighead!=header or clean.size!=old.size or clean.size!=source.size:
        raise RuntimeError("header/CLEAN geometry drift")
    S=np.asarray(source);C=np.asarray(clean);P=np.asarray(old)
    allowed=np.zeros((1024,2048),dtype=bool)
    for row in ROWS:
        x0,y0,x1,y1=row["bbox"]
        allowed[y0:y1,x0:x1]=True
    pre={
        "source_clean_changed_outside":int(np.sum(np.any(S!=C,axis=2)&~allowed)),
        "old_clean_changed_outside":int(np.sum(np.any(P!=C,axis=2)&~allowed)),
        "old_source_changed_outside":int(np.sum(np.any(S!=P,axis=2)&~allowed))
    }
    if any(pre.values()):raise RuntimeError(("old/CLEAN outside source drift",pre))
    final=clean.copy()
    regions=[]
    title_masks=[]
    for i,row in enumerate(ROWS):
        x0,y0,x1,y1=row["bbox"]
        width,height=x1-x0,y1-y0
        glyph,size=render(row["text"],tf,width,height)
        # Preserve the source RGB family; use median near-opaque source English
        # glyphs, never Noto default opaque black if source is colored.
        region=S[y0:y1,x0:x1]
        source_on=region[:,:,3]>200
        if source_on.sum()<100:raise RuntimeError(("canonical English source missing",row["key"]))
        rgb=tuple(int(x) for x in np.median(region[:,:,:3][source_on],axis=0))
        x=x0+2
        y=y0+(height-glyph.height)//2
        alpha=np.asarray(glyph)
        layer=Image.new("RGBA",glyph.size,(*rgb,0))
        layer.putalpha(glyph)
        if x+glyph.width>=x1 or y+glyph.height>=y1 or y<=y0:
            raise RuntimeError(("source bbox contains glyph without margin",row["key"]))
        final.alpha_composite(layer,(x,y))
        mb=np.zeros((1024,2048),dtype=bool)
        mb[y:y+glyph.height,x:x+glyph.width]=alpha>0
        for m in title_masks:
            if (m&mb).any():raise RuntimeError("overlapping translated glyphs")
        title_masks.append(mb)
        ys,xs=np.nonzero(mb)
        bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
        row.update({"font":"NotoSansCJKkr-Black","font_size":size,"source_color":rgb,"candidate_bbox":bbox,"candidate_size":[bbox[2]-bbox[0],bbox[3]-bbox[1]],
                    "original_size":[width,height],"margins":[bbox[0]-x0,x1-bbox[2],bbox[1]-y0,y1-bbox[3]],"coverage_ratio":round((bbox[2]-bbox[0])/width,4)})
        if min(row["margins"])<1:raise RuntimeError(("positive margins fail",row))
        # Human visual decision inputs: original, CLEAN, old exact current, new trial
        # on equally neutral background, keep consistent dimensions/source scaling.
        sx0=max(0,x0-4);sx1=min(2048,x1+8)
        sy0=max(0,y0-4);sy1=min(1024,y1+8)
        blocks=[onbg(z).crop((sx0,sy0,sx1,sy1)) for z in (source,clean,old,final)]
        W,H=blocks[0].size
        image=Image.new("RGB",(4*W+24,H+25),(110,110,110))
        ImageDraw.Draw(image).text((4,3),f"A205 q193 {row['key']} SOURCE/CLEAN/A171/NEW",fill="white")
        for n,b in enumerate(blocks):image.paste(b,(n*(W+8),25))
        for pct in (100,75,50):
            img=image if pct==100 else image.resize((image.width*pct//100,image.height*pct//100),Image.Resampling.LANCZOS)
            img.save(OUT/f"A205_{i}_{row['key']}_{pct}.jpg",quality=97,subsampling=0)
    F=np.asarray(final)
    changed=np.any(C!=F,axis=2)
    masks=np.logical_or.reduce(title_masks)
    metrics={**pre,
        "final_clean_changed_outside_source":int(np.sum(changed&~allowed)),
        "final_clean_changed_outside_translated_glyphs":int(np.sum(changed&~masks)),
        "final_clean_alpha_changed_outside_source":int(np.sum((C[:,:,3]!=F[:,:,3])&~allowed)),
        "final_old_changed_outside_source":int(np.sum(np.any(P!=F,axis=2)&~allowed)),
        "protected_art_changed":int(np.sum(np.any(S!=F,axis=2)&~allowed))}
    if any(metrics.values()):raise RuntimeError(("strict source/clean/old/final proof failed",metrics))
    # Exact source BGRA DDS header/pixel roundtrip and RAW/FLIPY proof.
    encoded=encode(header,final)
    trial=OUT/"A205_Q193_TRIAL_RGBA32_RAW_MIRRORY.dds"
    trial.write_bytes(encoded)
    newhead,decoded=dds(trial)
    if newhead!=header or not np.array_equal(np.asarray(decoded),F):
        raise RuntimeError("exact DDS decode roundtrip failed")
    readable=onbg(decoded)
    readable.save(OUT/"A205_FULL_TRIAL_FLIPY_100.jpg",quality=97,subsampling=0)
    decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT/"A205_FULL_TRIAL_RAW.png")
    readable.resize((1024,512),Image.Resampling.LANCZOS).save(OUT/"A205_FULL_TRIAL_FLIPY_50.jpg",quality=97,subsampling=0)
    for name,im in (("SOURCE",source),("CLEAN",clean),("PREVIOUS",old),("TRIAL",decoded)):
        im.save(OUT/f"A205_{name}_READABLE.png")
    report={"schema_version":1,"role":"A","run":"20261009-A205-Q193-SOURCE-WEIGHT-REWORK",
        "queue_index":193,"user_ingame_regressions":["IGR-003","IGR-019","IGR-033"],"priority":"P1",
        "source_sha256":SRC_SHA,"previous_sha256":CAND_SHA,"trial_sha256":sha(trial),"trial_path":str(trial.relative_to(ROOT)),
        "status":"TRIAL_ENCODDED_NOT_PROMOTED_PENDING_CONTROLLER_PIXEL_REVIEW",
        "method":"full-native NotoSansCJKkr-Black source-exact-color sampled letterform + idiomatic MULTIPLAYER->멀티플레이어, English CLEAN from A171; no resize/stretched Korean raster",
        "pinned_font_license":"SIL OFL-1.1","pinned_font_git_blob":FONT_BLOB,
        "rows":ROWS,"qa_numeric":metrics,"dds_trial_produced":1,
        "dds_promoted":0,"manual_review":"PENDING","runtime_validation":"UNTESTED",
        "next_action":"Read trial 100/75/50 and RAW vs source; promote only if full source-style visual hierarchy/no source residue proves acceptable. Fresh C1,C3,new game retest mandatory"}
    (OUT/"A205_Q193_TRIAL_MACHINE_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("A205 q193 SOURCE-FAITHFUL trial ready",json.dumps({"trial":report["trial_sha256"],"rows":[{"key":r["key"],"bbox":r["candidate_bbox"],"color":r["source_color"]} for r in ROWS],"qa":metrics},ensure_ascii=False),flush=True)
