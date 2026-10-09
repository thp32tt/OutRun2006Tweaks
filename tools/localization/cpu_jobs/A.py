#!/usr/bin/env python3
"""A208: Goal A native-width typography corrective pilot (one family only), q193.

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
OUT=R/"localization/graphics/role_A/20261009-A208-Q193-GOAL-A-FLAT-UI-PILOT"
OUT.mkdir(parents=True,exist_ok=True)
ASSET="97E863AD_512x256.dds"
CAND=R/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst"/ASSET
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/"+ASSET
FONT_URL="https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/Korean/NotoSansCJKkr-Black.otf"
SRC_SHA="d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451"
OLD_SHA="d90dada6007b0bba719889e8025c8aff332ddd21da296be540485536981859aa"
FONT_BLOB="b5b67bf293310a3648468a21ac829d6f2d58b2d5"
CELL=(930,206,1142,292)
EXPECTED_SOURCE_GOAL_A_BBOX=(950,221,1115,268)
PROTECTED=[(744,118,1117,169),(0,797,929,1022)]
TEXT="목표 A"
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
    if english!=EXPECTED_SOURCE_GOAL_A_BBOX or english[0]<x0+4 or english[1]<y0+2 or english[2]>x1-5 or english[3]>y1-6:
        raise RuntimeError(("SOURCE GOAL A not isolated; protected next row/neighbor might overlap",english,CELL))
    if english[2]-english[0]>275 or english[3]-english[1]>73:raise RuntimeError("Source cell probably contains other art")
    print("A208 measured English source bbox",english,flush=True)
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
    (OUT/"A208_SOURCE_CANONICAL_RGBA32.dds").write_bytes(src.read_bytes())
    clean.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT/"A208_CLEAN_NATIVE_RAW.png")
    source.save(OUT/"A208_SOURCE_READABLE.png")
    clean.save(OUT/"A208_CLEAN_READABLE.png")
    old.save(OUT/"A208_OLD_READABLE.png")
    showmasks(removal,"A208_MASK_SOURCE_AND_EXISTING_REMOVAL_RAW.png")
    showmasks(allowed,"A208_MASK_SOURCE_BOUNDED_EDIT_RAW.png")
    showmasks(protected,"A208_MASK_SOURCE_PROTECTED_RAW.png")
    showmasks(transparent,"A208_MASK_TRANSPARENT_PLATE_RAW.png")
    showmasks(np.zeros_like(removal),"A208_MASK_NONE_RAW.png")
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
            t.save(OUT/f"A208_PLATE_ONLY_{name}_{pct}.jpg",quality=95)
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
    if glyph.width / ew < 0.72:raise RuntimeError(("Source-relative phrase width underfill, reject before writing DDS",glyph.width,ew))
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
    lraw.save(OUT/"A208_LETTER_ONLY_NATIVE_RAW.png")
    letter.save(OUT/"A208_LETTER_ONLY_READABLE.png")
    effect=np.asarray(letter)[:,:,3]>0
    showmasks(effect,"A208_MASK_NEW_GLYPH_EFFECT_RAW.png")
    if (effect&protected).any() or (effect&~allowed).any():raise RuntimeError("new lettering enters protected art")
    final=Image.alpha_composite(clean,letter)
    saved=OUT/"A208_Q193_GOAL_A_NATIVE_FLAT_UI_PILOT.dds"
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
    persist.save(OUT/"A208_NEW_PERSISTED_READABLE.png")
    persist.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT/"A208_NEW_PERSISTED_RAW.png")
    for name,bg in [("GRAY",(105,105,105)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
        x2=max(0,x0-15);y2=max(0,y0-10);x3=min(2048,x1+25);y3=min(1024,y1+15)
        parts=[flatten(im,bg).crop((x2,y2,x3,y3)) for im in (source,clean,old,persist)]
        w,h=parts[0].size
        sheet=Image.new("RGB",(4*w+18,h+21),bg)
        ImageDraw.Draw(sheet).text((3,2),"SOURCE | CLEAN | OLD GHOST | NEW NATIVE",fill=(255,200,0) if name!="WHITE" else (0,0,0))
        for i,v in enumerate(parts):sheet.paste(v,(i*(w+6),21))
        for pct in (100,75,50):
            t=sheet if pct==100 else sheet.resize((sheet.width*pct//100,sheet.height*pct//100),Image.Resampling.LANCZOS)
            t.save(OUT/f"A208_COMPOSITE_{name}_{pct}.jpg",quality=95)
    report={"role":"A","run":"20261009-A208-Q193-GOAL-A-FLAT-UI-PILOT","queue_index":193,
       "status":"SOURCE_DERIVED_PILOT_TRIAL_PENDING_CONTROLLER_VISUAL_AND_C_FAMILY",
       "english":SOURCE_TEXT,"korean":TEXT,"source_sha256":SRC_SHA,"baseline_sha256":OLD_SHA,
       "trial_sha256":hashfile(saved),"source_cell":CELL,"source_bbox":english,
       "candidate_bbox":[gx,gy,gx+glyph.width,gy+glyph.height],"source_rgb":color,
       "font_size":fs,"font_blob_sha":FONT_BLOB,"qa_numeric":metrics,
       "original_protected_art_rects":PROTECTED,"original_protected_nonzero_pixels":int(protected.sum()),
       "original_english_bbox_size":[ew,eh],"candidate_natural_size":list(glyph.size),
       "new_dds_trial":1,"promoted_candidate":0,"runtime_validation":"UNTESTED",
       "consumer_first_unproven_link":"promoted candidate/preview manifest->game atlas load->Goal A focus state; not game tested"}
    (OUT/"A208_PILOT_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
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
      "mask_files":["A208_MASK_SOURCE_AND_EXISTING_REMOVAL_RAW.png","A208_MASK_SOURCE_BOUNDED_EDIT_RAW.png","A208_MASK_SOURCE_PROTECTED_RAW.png","A208_MASK_NEW_GLYPH_EFFECT_RAW.png"],
      "prior_failure":"English Goal label underlaid by thin/stretched Korean glyph in whole atlas; q193 A205/A206 only six other labels redrawn",
      "method_changed":"A208 natural-width goal phrase rebuild, source-derived removal/protected checks; no geometric glyph stretch",
      "pilot_status":"NOT_YET_INDEPENDENT_C_QUALIFIED_DO_NOT_MULTIPLY_INTO_GOAL_B-E"
    }
    (OUT/"recipe.json").write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("A208 PILOT_READY_FOR_CONTROLLER",json.dumps({"trial":report["trial_sha256"],"source_bbox":english,"candidate_bbox":report["candidate_bbox"],"protected_pixels":report["original_protected_nonzero_pixels"],"numeric":metrics},ensure_ascii=False),flush=True)

# A208 phase 2: producer draft requires SOURCE/CLEAN/OLD/NEW black/gray/white
# at 100 and 50 plus the isolated plate. Promote ONLY this one qualified
# material pilot, using the exact saved trial and a strict publisher manifest.
import sys
import shutil
from scipy.ndimage import label

BASELINE_GIT_REVISION="fa838e2178959fb3ccf7ac408ba9132139b101aa"
TRIAL_SHA=report["trial_sha256"]
trial=OUT/"A208_Q193_GOAL_A_NATIVE_FLAT_UI_PILOT.dds"
if hashfile(trial)!=TRIAL_SHA:raise RuntimeError("A208 trial SHA drift at promotion")
if hashfile(CAND)!=OLD_SHA:raise RuntimeError("A208 unchanged A206 base drift; reject rather than overwrite unrelated producer")
# Anchors are independent alpha-measured corresponding ORIGINAL AND REBUILT
# Latin 'A' outer *left diagonal* strokes, not an invented numeric slant.
def latin_a_left_stem_alpha_anchors(rgba,coord):
    x0,y0,x1,y1=coord
    source_mask=(rgba[y0:y1,x0:x1,3]>=64)
    labeled,n=label(source_mask,np.ones((3,3),dtype=int))
    options=[]
    for i in range(1,n+1):
        ys,xs=np.nonzero(labeled==i)
        if len(xs)<35:continue
        xx0,xx1=int(xs.min()),int(xs.max()+1)
        yy0,yy1=int(ys.min()),int(ys.max()+1)
        if yy1-yy0>=30 and xx1-xx0>=16:
            options.append((xx1,xx0,xx1,yy0,yy1,i))
    if not options:raise RuntimeError("No literal A stem to anchor")
    # Last connected letter is the shared Latin A in Goal A and 골 A.
    _,cx0,cx1,cy0,cy1,i=max(options)
    off=max(5,int((cy1-cy0)*.17))
    upper,lower=cy0+off,cy1-1-off
    xt=np.flatnonzero(labeled[upper]==i)
    xb=np.flatnonzero(labeled[lower]==i)
    if not len(xt) or not len(xb):raise RuntimeError("A diagonal edge not observed")
    anchor={"top":[x0+int(xt.min()),y0+upper],"bottom":[x0+int(xb.min()),y0+lower]}
    anchor_bbox=[x0+cx0,y0+cy0,x0+cx1,y0+cy1]
    return anchor,anchor_bbox
source_alpha=np.asarray(source)
final_alpha=np.asarray(persist)
sa,sbox=latin_a_left_stem_alpha_anchors(source_alpha,english)
ca,cbox=latin_a_left_stem_alpha_anchors(final_alpha,(gx,gy,gx+glyph.width,gy+glyph.height))
source_dx=sa["top"][0]-sa["bottom"][0]
target_dx=ca["top"][0]-ca["bottom"][0]
if (source_dx>0)-(source_dx<0)!=(target_dx>0)-(target_dx<0):
    raise RuntimeError(("Measured common Latin A edge slant sign mismatch",sa,ca))
evidence=Image.new("RGB",(940,245),(106,106,106))
pen=ImageDraw.Draw(evidence)
scale=3
for k,(im,bbox,anchors,title) in enumerate([
    (source,sbox,sa,"SOURCE LATIN A LEFT LEG"),
    (persist,cbox,ca,"KOREAN REBUILT LATIN A LEFT LEG")]):
    ex0,ey0,ex1,ey1=bbox
    cropped=flatten(im,(106,106,106)).crop((ex0-5,ey0-5,ex1+5,ey1+5))
    cropped=cropped.resize((cropped.width*scale,cropped.height*scale),Image.Resampling.NEAREST)
    dst=(k*470+10,30)
    evidence.paste(cropped,dst)
    pen.text((dst[0],5),title,fill=(250,250,250))
    for a,color in [(anchors["top"],(255,230,0)),(anchors["bottom"],(0,250,145))]:
        sx=dst[0]+(a[0]-ex0+5)*scale
        sy=dst[1]+(a[1]-ey0+5)*scale
        pen.ellipse((sx-5,sy-5,sx+5,sy+5),fill=color,outline=(0,0,0))
    pen.text((dst[0],220),str(anchors),fill=(250,250,250))
evidence_path=OUT/"A208_SOURCE_AND_KOREAN_LATIN_A_ANCHORS.png"
evidence.save(evidence_path)
# Publication manifest uses the raw pinned English DDS, correct prior Git bytes
# and full-native RAW PNG for clean/letter/masks, no screenshot/JPG substitution.
target_path=str(CAND.relative_to(R))
def pathsha(p):
    return {"path":str(Path(p).relative_to(R)),"sha256":hashfile(p)}
def masksha(name):
    return pathsha(OUT/name)
shutil.copyfile(trial,CAND)
manifest={
    "version":"production-pixels-v1-20261009",
    "coordinates":"native_raw",
    "stage":"final",
    "inputs":{
        "source":pathsha(OUT/"A208_SOURCE_CANONICAL_RGBA32.dds"),
        "baseline":{"path":target_path,"sha256":OLD_SHA,
                    "git_revision":BASELINE_GIT_REVISION},
        "clean":pathsha(OUT/"A208_CLEAN_NATIVE_RAW.png"),
        "lettering":pathsha(OUT/"A208_LETTER_ONLY_NATIVE_RAW.png"),
        "candidate":pathsha(CAND)
    },
    "masks":{
        "removal":masksha("A208_MASK_SOURCE_AND_EXISTING_REMOVAL_RAW.png"),
        "protected":masksha("A208_MASK_SOURCE_PROTECTED_RAW.png"),
        "edit":masksha("A208_MASK_SOURCE_BOUNDED_EDIT_RAW.png"),
        "transparent":masksha("A208_MASK_TRANSPARENT_PLATE_RAW.png"),
        "restore":masksha("A208_MASK_NONE_RAW.png"),
        "effect":masksha("A208_MASK_NEW_GLYPH_EFFECT_RAW.png")
    },
    "regions":[{
       "id":"Goal A / 골 A, shared actual Latin A outer left edge",
       "source_anchors":sa,
       "candidate_anchors":ca,
       "anchor_evidence":pathsha(evidence_path)
    }]
}
manifestdir=R/"localization/graphics/worker_results/production_manifests"
manifestdir.mkdir(parents=True,exist_ok=True)
manifestpath=manifestdir/(TRIAL_SHA+".json")
manifestpath.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
sys.path.insert(0,str(R/"tools/localization"))
sys.dont_write_bytecode=True
import production_pixel_guard
guard=production_pixel_guard.verify(R,manifest)
(OUT/"A208_FINAL_MANIFEST_MECHANICAL_REPORT.json").write_text(json.dumps(guard,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
if guard["result"]!="MECHANICAL_PASS_VISUAL_REVIEW_REQUIRED" or guard["errors"]:
    raise RuntimeError(("Production reset pixel guard failed, abort publication",guard))
recipe=json.loads((OUT/"recipe.json").read_text(encoding="utf8"))
recipe["font"]["glyph_coverage"]="native full Hangul syllable glyph visible at source height; OFL exact font blob pinned"
recipe["renderer_code_sha256"]=hashfile(Path(__file__))
recipe["source_actual_slope_anchor"]=sa
recipe["candidate_actual_slope_anchor"]=ca
recipe["anchor_evidence"]=str(evidence_path.relative_to(R))
recipe["state"]="FAMILY_PILOT_SCOPED_PRODUCER_PASS_PENDING_C1_METHOD_QUALIFICATION"
(OUT/"recipe.json").write_text(json.dumps(recipe,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
report["status"]="A208_NEW_PROMOTED_GOAL_A_SOURCE_PROTECTED_SCOPED_PRODUCER_PASS_PENDING_FRESH_C1"
report["promoted_candidate"]=1
report["baseline_git_revision"]=BASELINE_GIT_REVISION
report["anchor_source"]=sa
report["anchor_candidate"]=ca
report["source_dx"]=source_dx
report["candidate_dx"]=target_dx
report["production_pixel_guard"]=guard
report["final_manifest"]=str(manifestpath.relative_to(R))
(OUT/"A208_PILOT_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("A208 PRODUCTION_PIXEL_GUARD_GOAL_A",json.dumps({"candidate":TRIAL_SHA,"source_anchor":sa,"new_anchor":ca,"guard":guard["result"],"counts":guard["counts"]},ensure_ascii=False),flush=True)
