#!/usr/bin/env python3
"""A206 q193: remove three inherited English ghosts, rebuild actual native DDS.

Exact source pixel footprints, source-only plate, transparent glyph composite,
decode persisted DDS and compare RAW/FLIPY. Worker creates trial only until
controller inspects source/clean/old/new at native/50 on multiple backgrounds.
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
NAME="20261009-A206-Q193-RANK-HELP-SOURCE-GHOST-REMOVAL"
OUT=ROOT/"localization/graphics/role_A"/NAME
OUT.mkdir(parents=True,exist_ok=True)
ASSET="97E863AD_512x256.dds"
CAND=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst"/ASSET
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/"+ASSET
FONT_URL="https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/Korean/NotoSansCJKkr-Black.otf"
EXPECTED_SOURCE="d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451"
EXPECTED_OLD="1cea9015c02bfe80efb1538ba69218c2b505438c78eb31ff64b7677f883824a6"
EXPECTED_FONT_BLOB="b5b67bf293310a3648468a21ac829d6f2d58b2d5"
ROWS=[
 {"key":"online_rank_help","source":"View the online multiplayer rankings!","ko":"온라인 멀티플레이어 랭킹 보기!", "cell":[0,372,1160,452]},
 {"key":"outrun2sp_rank_help","source":"View OutRun2SP arcade rankings!","ko":"OutRun2SP 아케이드 랭킹 보기!", "cell":[0,534,1105,619]},
 {"key":"outrun_rank_help","source":"View OutRun single player rankings!","ko":"OutRun 싱글 플레이 랭킹 보기!", "cell":[0,694,1120,781]}
]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def blob(p):
    b=Path(p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ":raise RuntimeError("not DDS")
    h,w=struct.unpack_from("<II",b,12)
    if (w,h)!=(2048,1024) or len(b)!=(128+w*h*4):raise RuntimeError("unexpected DDS geometry")
    if struct.unpack_from("<I",b,28)[0]!=1:raise RuntimeError("unexpected DDS mip count")
    if struct.unpack_from("<I",b,88)[0]!=32 or struct.unpack_from("<IIII",b,92)!=(255,65280,16711680,4278190080):
        raise RuntimeError("unexpected RGBA channel masks")
    return b[:128],Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def save_dds(header,im,p):
    p.write_bytes(header+im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA"))
def flatten(im,bg):
    out=Image.new("RGBA",im.size,(*bg,255))
    out.alpha_composite(im)
    return out.convert("RGB")
def original_footprint(source,cell):
    x0,y0,x1,y1=cell
    rgba=np.asarray(source.crop((x0,y0,x1,y1)))
    on=rgba[:,:,3]>6
    if not on.any():raise RuntimeError(("no source glyph",cell))
    ys,xs=np.nonzero(on)
    bbox=[int(xs.min()+x0),int(ys.min()+y0),int(xs.max()+x0+1),int(ys.max()+y0+1)]
    # No source text may touch an arbitrary cell boundary: prove isolation.
    if bbox[0]<=x0 or bbox[1]<=y0+1 or bbox[2]>=x1-2 or bbox[3]>=y1-2:
        raise RuntimeError(("source footprint may spill/overlap cell",cell,bbox))
    return bbox
def draw_native(ko,fontfile,maxw,maxh,minheight):
    # Do not stretch compressed Korean pixel art. Keep the source weight/scale.
    for fontsize in range(100,20,-1):
        font=ImageFont.truetype(str(fontfile),fontsize)
        scratch=Image.new("L",(2600,180),0)
        ImageDraw.Draw(scratch).text((8,0),ko,font=font,fill=255)
        bb=scratch.getbbox()
        if not bb:continue
        image=scratch.crop(bb)
        if image.width<=maxw-8 and image.height<=maxh-4 and image.height>=minheight:
            return image,fontsize
    raise RuntimeError(("font cannot maintain source readable height in bbox",ko,maxw,maxh))
if not CAND.exists() or sha(CAND)!=EXPECTED_OLD:
    raise RuntimeError(("q193 exact candidate SHA changed, fail closed",sha(CAND)))
previous_header,previous=load_dds(CAND)
with tempfile.TemporaryDirectory(prefix="a206_") as tmp:
    sf=Path(tmp)/ASSET
    ff=Path(tmp)/"NotoSansCJKkr-Black.otf"
    urllib.request.urlretrieve(SRC_URL,sf)
    urllib.request.urlretrieve(FONT_URL,ff)
    if sha(sf)!=EXPECTED_SOURCE or blob(ff)!=EXPECTED_FONT_BLOB:
        raise RuntimeError("pinned canonical English source or font drift")
    source_header,source=load_dds(sf)
    if previous_header!=source_header:
        raise RuntimeError("source DDS 128byte header differs from candidate")
    old=np.asarray(previous)
    before=previous.copy()
    clean=previous.copy()
    cellmask=np.zeros((1024,2048),dtype=bool)
    for r in ROWS:
        x0,y0,x1,y1=r["cell"]
        if cellmask[y0:y1,x0:x1].any():raise RuntimeError("source edit cells overlap")
        cellmask[y0:y1,x0:x1]=True
        origin=original_footprint(source,r["cell"])
        r["source_glyph_bbox"]=origin
        s=np.asarray(source.crop((x0,y0,x1,y1)))
        rgb=s[:,:,:3][s[:,:,3]>200]
        if len(rgb)<100:raise RuntimeError("no opaque source text palette")
        r["source_rgb_median"]=[int(c) for c in np.median(rgb,axis=0)]
        r["english_height"]=origin[3]-origin[1]
        r["english_width"]=origin[2]-origin[0]
        # All English glyph/effects and all prior overlaid Korean/ghost reside
        # inside this isolated cell. Transparent atlas is the actual plate.
        clean.paste((0,0,0,0),(x0,y0,x1,y1))
    # The cleaned plate is a stage *without Korean* and must be evaluated
    # independently before glyph production, with the current outside intact.
    cleanpix=np.asarray(clean)
    if np.any(cleanpix[cellmask,3]):raise RuntimeError("plate still has alpha in source cells")
    if not np.array_equal(old[~cellmask],cleanpix[~cellmask]):
        raise RuntimeError("protected translated sprites modified during clean")
    final=clean.copy()
    glyphmask=np.zeros((1024,2048),dtype=bool)
    for i,r in enumerate(ROWS):
        x0,y0,x1,y1=r["cell"]
        ox0,oy0,ox1,oy1=r["source_glyph_bbox"]
        ew,eh=r["english_width"],r["english_height"]
        glyph,size=draw_native(r["ko"],ff,ew,eh,max(26,int(eh*0.78)))
        gx=ox0+2
        gy=oy0+(eh-glyph.height)//2
        if gx<=x0 or gy<=y0 or gx+glyph.width>=ox1-1 or gy+glyph.height>=oy1-1:
            raise RuntimeError(("new glyph outside original English source footprint",r["key"],(gx,gy,glyph.size),r["source_glyph_bbox"]))
        layer=Image.new("RGBA",glyph.size,tuple(r["source_rgb_median"])+(0,))
        layer.putalpha(glyph)
        final.alpha_composite(layer,(gx,gy))
        ga=np.asarray(glyph)
        gmask=ga>0
        if glyphmask[gy:gy+glyph.height,gx:gx+glyph.width].any():
            raise RuntimeError("font glyph overlap other source row")
        glyphmask[gy:gy+glyph.height,gx:gx+glyph.width]=gmask
        bbox=[gx,gy,gx+glyph.width,gy+glyph.height]
        r.update({"font_size":size,"new_bbox":bbox,"new_size":list(glyph.size),
            "actual_source_bbox_size":[ew,eh],"margin_original_bbox":[gx-ox0,ox1-(gx+glyph.width),gy-oy0,oy1-(gy+glyph.height)],
            "source_width_coverage":round(glyph.width/ew,4),"native_font":"NotoSansCJKkr-Black"})
        if min(r["margin_original_bbox"])<1:raise RuntimeError("new glyph touches source edge")
        # Independent plate-only and composite-only previews with source,
        # English/previous, clean, final; source top y and edges preserved.
        cx0=max(0,x0-1);cx1=min(2048,x1+6)
        cy0=max(0,y0-1);cy1=min(1024,y1+5)
        for bgname,bg in (("gray",(100,100,100)),("black",(0,0,0)),("white",(255,255,255))):
            imlist=[flatten(im,bg).crop((cx0,cy0,cx1,cy1)) for im in (source,previous,clean,final)]
            cw,ch=imlist[0].size
            contact=Image.new("RGB",(cw*4+18,ch+18),bg)
            for index,image in enumerate(imlist):contact.paste(image,(index*(cw+6),18))
            ImageDraw.Draw(contact).text((2,2),"ENGLISH | OLD GHOST | CLEAN PLATE | NEW DDS",fill=(255,255,0) if bgname!="white" else (0,0,0))
            for factor in (100,75,50):
                if factor==100:view=contact
                else:view=contact.resize((contact.width*factor//100,contact.height*factor//100),Image.Resampling.LANCZOS)
                view.save(OUT/f"A206_{i}_{r['key']}_{bgname}_{factor}.jpg",quality=95,subsampling=0)
    finpix=np.asarray(final)
    changed=np.any(finpix!=old,axis=2)
    composited_changed=np.any(finpix!=cleanpix,axis=2)
    metrics={
        "old_to_clean_changed_outside_source_cells":int(np.sum(np.any(old!=cleanpix,axis=2)&~cellmask)),
        "old_to_final_changed_outside_source_cells":int(np.sum(changed&~cellmask)),
        "old_to_final_alpha_changed_outside_source_cells":int(np.sum((old[:,:,3]!=finpix[:,:,3])&~cellmask)),
        "clean_to_final_changed_outside_new_Hangul":int(np.sum(composited_changed&~glyphmask)),
        "protected_source_sprites_changed":int(np.sum(changed&~cellmask)),
        "plate_alpha_nonzero_in_3_source_cells":int(np.count_nonzero(cleanpix[cellmask,3]))
    }
    if any(metrics.values()):raise RuntimeError(("DDS edit escaped exact bounds or glyph-only mask",metrics))
    trial=OUT/"A206_Q193_THREE_RANK_HELP_GHOST_REMOVED_RGBA32.dds"
    save_dds(previous_header,final,trial)
    persisted_header,persisted=load_dds(trial)
    if persisted_header!=previous_header or not np.array_equal(np.asarray(persisted),finpix):
        raise RuntimeError("actual on-disk DDS RAW/FLIPY byte roundtrip differs")
    source.save(OUT/"A206_SOURCE_FLIPY.png")
    before.save(OUT/"A206_OLD_FLIPY.png")
    clean.save(OUT/"A206_CLEAN_PLATE_FLIPY.png")
    persisted.save(OUT/"A206_NEW_PERSISTED_FLIPY.png")
    persisted.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT/"A206_NEW_PERSISTED_RAW.png")
    for bgname,bg in (("gray",(100,100,100)),("black",(0,0,0)),("white",(255,255,255))):
        vis=flatten(persisted,bg)
        vis.save(OUT/f"A206_FULL_FINAL_FLIPY_{bgname}_100.jpg",quality=94)
        vis.resize((1024,512),Image.Resampling.LANCZOS).save(OUT/f"A206_FULL_FINAL_FLIPY_{bgname}_50.jpg",quality=94)
    report={"schema_version":2,"role":"A","run":NAME,"index":193,
        "status":"TRIAL_PENDING_CONTROLLER_VISUAL_NOT_PROMOTED",
        "source_sha256":EXPECTED_SOURCE,"before_sha256":EXPECTED_OLD,"trial_sha256":sha(trial),
        "source_provenance":SRC_URL,"font_blob_sha1":EXPECTED_FONT_BLOB,
        "native_dims":[2048,1024],"source_dds_masks":[255,65280,16711680,4278190080],
        "mips":1,"raw_orientation":"mirror_y","rows":ROWS,"qa_numeric":metrics,
        "scope":"3 leftover rank/help English-source ghost overlapped legacy Korean",
        "source_plate_clean":"transparent alpha 0, before Korean insertion",
        "saved_dds_roundtrip":True,"new_dds_trial":1,"candidate_promoted":0,
        "consumer_screen_family":["Multiplayer ranking help","OutRun2SP arcade ranking help","OutRun single-player rankings help"],
        "first_unproven_consumer_link":"exact persisted candidate not yet entered reviewed patch manifest/build -> actual game load/texture sampling/composited screens",
        "runtime_validation":"UNTESTED"}
    (OUT/"A206_Q193_RANK_HELP_TRIAL_REPORT.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("A206 Q193 THREE NEW GHOST-FREE RANK HELP DDS",json.dumps({"sha":report["trial_sha256"],"rows":ROWS,"qa":metrics},ensure_ascii=False),flush=True)
