#!/usr/bin/env python3
"""A207: source-authored Goal A small-menu *single family pilot*, q193.

Stage P1 SOURCE->CLEAN is completed and saved before any lettering.  Produces
a non-promoted trial DDS plus auditable native RAW masks/evidence and recipe.
New production-reset forbids candidate promotion before controller sees pixels,
and requires the final pixel guard for any later promotion.
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
R=Path.cwd()
OUT=R/"localization/graphics/role_A/20261009-A207-Q193-GOAL-A-FLAT-UI-PILOT"
OUT.mkdir(parents=True,exist_ok=True)
ASSET="97E863AD_512x256.dds"
CAND=R/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst"/ASSET
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/"+ASSET
FONT_URL="https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/Korean/NotoSansCJKkr-Black.otf"
SRC_SHA="d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451"
OLD_SHA="d90dada6007b0bba719889e8025c8aff332ddd21da296be540485536981859aa"
FONT_BLOB="b5b67bf293310a3648468a21ac829d6f2d58b2d5"
CELL=(770,167,1085,248)
PROTECTED=[(744,118,1117,169),(0,797,929,1022)]
TEXT="골 A"
SOURCE_TEXT="Goal A"
def hashfile(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def gitblob(p):
    b=Path(p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS " or len(b)!=(128+2048*1024*4):raise RuntimeError("unexpected DDS header/length")
    h,w=struct.unpack_from("<II",b,12)
    if (w,h)!=(2048,1024) or struct.unpack_from("<I",b,28)[0]!=1 or struct.unpack_from("<I",b,88)[0]!=32:
        raise RuntimeError("native dimensions/mips/bitcount changed")
    if struct.unpack_from("<IIII",b,92)!=(255,65280,16711680,4278190080):raise RuntimeError("q193 is RGBA, not BGRA")
    readable=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128],readable
def save(header,readable,p):
    p.write_bytes(header+readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA"))
def flatten(im,rgb):
    a=Image.new("RGBA",im.size,(*rgb,255))
    a.alpha_composite(im)
    return a.convert("RGB")
def showmasks(arr,p):
    Image.fromarray((arr.astype(np.uint8)*255),"L").transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT/p)
def colored_alpha(im,alpha,p):
    im.putalpha(Image.fromarray(alpha.astype("uint8"),"L"));im.save(OUT/p)
if not CAND.exists() or hashfile(CAND)!=OLD_SHA:raise RuntimeError("q193 last promoted exact bytes changed; fail closed")
header,old=load(CAND)
with tempfile.TemporaryDirectory(prefix="a207_") as tmp:
    src=Path(tmp)/ASSET
    font=Path(tmp)/"NotoSansCJKkr-Black.otf"
    urllib.request.urlretrieve(SRC_URL,src)
    urllib.request.urlretrieve(FONT_URL,font)
    if hashfile(src)!=SRC_SHA or gitblob(font)!=FONT_BLOB:raise RuntimeError("pinned SOURCE/FONT drift")
    shead,source=load(src)
    if header!=shead:raise RuntimeError("DDS header source/old unequal")
    x0,y0,x1,y1=CELL
    S=np.asarray(source).copy();B=np.asarray(old).copy()
    segment=S[y0:y1,x0:x1]
    mask_source=segment[:,:,3]>0
    if mask_source.sum()<100:raise RuntimeError("English Goal A absent from requested cell")
    ys,xs=np.nonzero(mask_source)
    english=(int(xs.min()+x0),int(ys.min()+y0),int(xs.max()+x0+1),int(ys.max()+y0+1))
    if english[0]<x0+4 or english[1]<y0+2 or english[2]>x1-5 or english[3]>y1-6:
        raise RuntimeError(("SOURCE GOAL A not isolated; protected next row/neighbor might overlap",english,CELL))
    if english[2]-english[0]>275 or english[3]-english[1]>73:raise RuntimeError("Source cell probably contains other art")
    print("A207 measured English source bbox",english,flush=True)
    allowed=np.zeros((1024,2048),bool)
    allowed[y0:y1,x0:x1]=True
    protected=np.zeros((1024,2048),bool)
    for a,b,c,d in PROTECTED:
        protected[b:d,a:c]|=S[b:d,a:c,3]>0
    if (allowed&protected).any():raise RuntimeError("Protected family collision; tighten cell")
    # Critical: protect SOURCE art (not only previously damaged candidate).
    protect_delta=int(np.sum(np.any(S!=B,axis=2)&protected))
    if protect_delta:raise RuntimeError(("SOURCE protected original art is already lost",protect_delta))
    removal=np.zeros((1024,2048),bool)
    # pre-lettering mask is derived from English-original and prior visible
    # alpha in this exact isolated sprite, NOT final changed pixels.
    removal[y0:y1,x0:x1]|=(S[y0:y1,x0:x1,3]!=0)|(B[y0:y1,x0:x1,3]!=0)
    if removal.sum()<100:raise RuntimeError("source lettering removal mask empty")
    transparent=removal.copy()
    cleanarr=B.copy()
    cleanarr[removal]=0
    if np.any(cleanarr[transparent,3]):raise RuntimeError("CLEAN PLATE alpha ghost")
    if np.any(np.any(cleanarr!=B,axis=2)&~removal):raise RuntimeError("PLATE changed out of removal mask")
    if np.any(np.any(cleanarr!=S,axis=2)&protected):raise RuntimeError("SOURCE protected art lost in CLEAN")
    clean=Image.fromarray(cleanarr,"RGBA")
    raw=source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    # Publication guard needs a pinned canonical DDS inside Git evidence.
    (OUT/"A207_SOURCE_CANONICAL_RGBA32.dds").write_bytes(src.read_bytes())
    clean.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT/"A207_CLEAN_NATIVE_RAW.png")
    source.save(OUT/"A207_SOURCE_READABLE.png")
    clean.save(OUT/"A207_CLEAN_READABLE.png")
    old.save(OUT/"A207_OLD_READABLE.png")
    showmasks(removal,"A207_MASK_SOURCE_AND_EXISTING_REMOVAL_RAW.png")
    showmasks(allowed,"A207_MASK_SOURCE_BOUNDED_EDIT_RAW.png")
    showmasks(protected,"A207_MASK_SOURCE_PROTECTED_RAW.png")
    showmasks(transparent,"A207_MASK_TRANSPARENT_PLATE_RAW.png")
    showmasks(np.zeros_like(removal),"A207_MASK_NONE_RAW.png")
    # P1 evidence is saved now, independently of the eventual Korean.
    for name,bg in [("GRAY",(105,105,105)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
        x2=max(0,x0-15);y2=max(0,y0-10);x3=min(2048,x1+25);y3=min(1024,y1+15)
        parts=[flatten(im,bg).crop((x2,y2,x3,y3)) for im in (source,old,clean)]
        w,h=parts[0].size
        sheet=Image.new("RGB",(3*w+12,h+21),bg)
        ImageDraw.Draw(sheet).text((3,2),"SOURCE | CURRENT A206 | INDEPENDENT EMPTY CLEAN",fill=(255,200,0) if name!="WHITE" else (0,0,0))
        for i,v in enumerate(parts):sheet.paste(v,(i*(w+6),21))
        for pct in (100,75,50):
            t=sheet if pct==100 else sheet.resize((sheet.width*pct//100,sheet.height*pct//100),Image.Resampling.LANCZOS)
            t.save(OUT/f"A207_PLATE_ONLY_{name}_{pct}.jpg",quality=95)
    # P2 only after SOURCE/CLEAN mechanical stage and plate proof created.
    ew,eh=english[2]-english[0],english[3]-english[1]
    glyph=fs=None
    for size in range(95,17,-1):
        f=ImageFont.truetype(str(font),size)
        trial=Image.new("L",(500,170),0)
        ImageDraw.Draw(trial).text((8,0),TEXT,font=f,fill=255)
        bb=trial.getbbox()
        if not bb:continue
        w=trial.crop(bb)
        if w.width<ew-8 and w.height<eh-4 and w.height>=0.78*eh:
            glyph=w;fs=size;break
    if glyph is None:raise RuntimeError(("font not compatible with English height/width",ew,eh))
    gx=english[0]+3;gy=english[1]+(eh-glyph.height)//2
    if gx+glyph.width>=english[2]-2 or gy+glyph.height>=english[3]-1:raise RuntimeError("new glyph violates source bbox")
    srcpix=S[english[1]:english[3],english[0]:english[2]]
    rgb=srcpix[:,:,:3][srcpix[:,:,3]>200]
    if len(rgb)<20:raise RuntimeError("SOURCE foreground insufficient")
    color=tuple(int(v) for v in np.median(rgb,axis=0))
    alpha=np.asarray(glyph)
    letter=Image.new("RGBA",(2048,1024),(0,0,0,0))
    layer=Image.new("RGBA",glyph.size,(*color,0))
    layer.putalpha(glyph)
    letter.alpha_composite(layer,(gx,gy))
    lraw=letter.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    lraw.save(OUT/"A207_LETTER_ONLY_NATIVE_RAW.png")
    letter.save(OUT/"A207_LETTER_ONLY_READABLE.png")
    effect=np.asarray(letter)[:,:,3]>0
    showmasks(effect,"A207_MASK_NEW_GLYPH_EFFECT_RAW.png")
    if (effect&protected).any() or (effect&~allowed).any():raise RuntimeError("new lettering enters protected art")
    final=Image.alpha_composite(clean,letter)
    saved=OUT/"A207_Q193_GOAL_A_NATIVE_FLAT_UI_PILOT.dds"
    save(header,final,saved)
    head,persist=load(saved)
    if head!=header or not np.array_equal(np.asarray(persist),np.asarray(final)):
        raise RuntimeError("saved RGBA DDS differs from expected alpha composite")
    F=np.asarray(persist)
    metrics={
       "source_protected_vs_previous":protect_delta,
       "source_protected_vs_clean":int(np.sum(np.any(S!=cleanarr,axis=2)&protected)),
       "source_protected_vs_final":int(np.sum(np.any(S!=F,axis=2)&protected)),
       "prior_vs_new_outside_edit":int(np.sum(np.any(B!=F,axis=2)&~allowed)),
       "clean_changed_outside_removal":int(np.sum(np.any(B!=cleanarr,axis=2)&~removal)),
       "clean_to_final_outside_letter_alpha":int(np.sum(np.any(F!=cleanarr,axis=2)&~effect)),
       "transparent_clean_nonzero_alpha":int(np.count_nonzero(cleanarr[transparent,3]))
    }
    if any(metrics.values()):raise RuntimeError(("P3 mechanical mask fail",metrics))
    persist.save(OUT/"A207_NEW_PERSISTED_READABLE.png")
    persist.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT/"A207_NEW_PERSISTED_RAW.png")
    for name,bg in [("GRAY",(105,105,105)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
        x2=max(0,x0-15);y2=max(0,y0-10);x3=min(2048,x1+25);y3=min(1024,y1+15)
        parts=[flatten(im,bg).crop((x2,y2,x3,y3)) for im in (source,clean,old,persist)]
        w,h=parts[0].size
        sheet=Image.new("RGB",(4*w+18,h+21),bg)
        ImageDraw.Draw(sheet).text((3,2),"SOURCE | CLEAN | OLD GHOST | NEW NATIVE",fill=(255,200,0) if name!="WHITE" else (0,0,0))
        for i,v in enumerate(parts):sheet.paste(v,(i*(w+6),21))
        for pct in (100,75,50):
            t=sheet if pct==100 else sheet.resize((sheet.width*pct//100,sheet.height*pct//100),Image.Resampling.LANCZOS)
            t.save(OUT/f"A207_COMPOSITE_{name}_{pct}.jpg",quality=95)
    report={"role":"A","run":"20261009-A207-Q193-GOAL-A-FLAT-UI-PILOT","queue_index":193,
       "status":"SOURCE_DERIVED_PILOT_TRIAL_PENDING_CONTROLLER_VISUAL_AND_C_FAMILY",
       "english":SOURCE_TEXT,"korean":TEXT,"source_sha256":SRC_SHA,"baseline_sha256":OLD_SHA,
       "trial_sha256":hashfile(saved),"source_cell":CELL,"source_bbox":english,
       "candidate_bbox":[gx,gy,gx+glyph.width,gy+glyph.height],"source_rgb":color,
       "font_size":fs,"font_blob_sha":FONT_BLOB,"qa_numeric":metrics,
       "original_protected_art_rects":PROTECTED,"original_protected_nonzero_pixels":int(protected.sum()),
       "original_english_bbox_size":[ew,eh],"candidate_natural_size":list(glyph.size),
       "new_dds_trial":1,"promoted_candidate":0,"runtime_validation":"UNTESTED",
       "consumer_first_unproven_link":"promoted candidate/preview manifest->game atlas load->Goal A focus state; not game tested"}
    (OUT/"A207_PILOT_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    recipe={
      "schema_version":1,"family":"small dark flat Goal rank menu labels", "run":report["run"],
      "source":{"url":SRC_URL,"revision":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6","sha256":SRC_SHA},
      "source_atlas_labels":["WELCOME TO THE","MULTIPLAYER","3x ranking help","Goal A","Goal B","Goal C","Goal D","Goal E","15 Cont.","ONLINE","OUTRUN SHOWROOM"],
      "protected":["TESTAROSSA title","large red OUTRUN2SP artwork","every remaining translated/title/help label outside Goal A"],
      "source_semantics":SOURCE_TEXT,"canonical_korean":TEXT,
      "font":{"source_url":FONT_URL,"git_blob":FONT_BLOB,"license":"SIL-OFL-1.1","name":"NotoSansCJKkr-Black","native_size":fs,"missing_fallback_not_allowed":True,"glyph_coverage":"verified render nonempty, separate formal cmap pending"},
      "renderer":"Pillow ImageDraw native RGBA, no shear/stretch/extrusion/downsample, one mip","source_rgb_median":color,
      "flat_effects":{"outline_px":0,"shadow_px":0,"slant_dx_top_minus_bottom":0},
      "readable_to_RAW":"single FLIP_TOP_BOTTOM at saved DDS writer only",
      "source_cell":CELL,"source_bbox":english,"candidate_bbox":report["candidate_bbox"],
      "mask_files":["A207_MASK_SOURCE_AND_EXISTING_REMOVAL_RAW.png","A207_MASK_SOURCE_BOUNDED_EDIT_RAW.png","A207_MASK_SOURCE_PROTECTED_RAW.png","A207_MASK_NEW_GLYPH_EFFECT_RAW.png"],
      "prior_failure":"English Goal label underlaid by thin/stretched Korean glyph in whole atlas; q193 A205/A206 only six other labels redrawn",
      "method_changed":"First dedicated SMALL Goal A native flat font-family pilot; source-derived removal; exact protected source checks",
      "pilot_status":"NOT_YET_INDEPENDENT_C_QUALIFIED_DO_NOT_MULTIPLY_INTO_GOAL_B-E"
    }
    (OUT/"recipe.json").write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("A207 PILOT_READY_FOR_CONTROLLER",json.dumps({"trial":report["trial_sha256"],"source_bbox":english,"candidate_bbox":report["candidate_bbox"],"protected_pixels":report["original_protected_nonzero_pixels"],"numeric":metrics},ensure_ascii=False),flush=True)
