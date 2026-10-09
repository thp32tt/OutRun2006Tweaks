#!/usr/bin/env python3
"""A216 q175 P1: source-conditioned *manual Hangul contours* plus welded chrome.

One genuinely different family pilot after A211's small isolated font glyphs.
No normal font stretch/rails reuse, no production promotion without direct review.
Source, current promoted DDS, A188 CLEAN are SHA-pinned. Writes role_A only.
"""
import hashlib,json,os,struct,subprocess,sys,tempfile,urllib.request,traceback
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter1d
assert os.environ.get("OUTRUN_CPU_WORKER") == "github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE") == "A"
ROOT=Path.cwd()
OUT=ROOT/"localization/graphics/role_A/20261010-A216-Q175-WELDED-MANUAL-SOURCE-CHROME"
OUT.mkdir(parents=True,exist_ok=True)
CAND=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
SOURCE_SHA="9314372585b8309f2f8b3e714076ef1ad1999d770422a570398ef20a80ac10a5"
PRIOR_SHA="b9f60b4582ddb4db525806454078471e1045f30a2d65e6da4d4681b87ee6ba73"
CLEAN=ROOT/"localization/graphics/role_A/20261008-A188-Q175-CHROME-FACE-RECOVERY/754F0599_HD_CLEAN_PLATE.png"
ORIGINAL=(6,397,956,529)
KEY="OUTRUN-KOR-A216-Q175-SOURCE-CONTOUR-WELDED-CHROME-PILOT-20261010-0400"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read_dds(path):
    b=Path(path).read_bytes()
    if b[:4]!=b"DDS " or len(b)!=128+2048*1024*4:raise ValueError("DDS signature/length differs")
    h,w=struct.unpack_from("<II",b,12)
    masks=struct.unpack_from("<IIII",b,92)
    if (w,h,masks,struct.unpack_from("<I",b,28)[0])!=(2048,1024,(16711680,65280,255,4278190080),1):
        raise ValueError("q175 DDS encoding/mips drift")
    return b[:128],Image.frombytes("RGBA",(w,h),b[128:],"raw","BGRA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def save_dds(header,im,path):
    Path(path).write_bytes(header+im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","BGRA"))
def comp(im,rgb):
    bg=Image.new("RGBA",im.size,(*rgb,255));bg.alpha_composite(im);return bg.convert("RGB")
def hand_contour():
    """Native target: actual Hangul letters ㅅ+ㅛ and ㄹ+ㅜ+ㅁ with open counters.

    Manually constructed wide connected display letters from source proportions,
    NOT a stretched low-resolution/generic font. 3x vector path AA downsample
    once. Two syllable counters stay open at native size.
    """
    scale=3;w,h=860,125
    im=Image.new("L",(w*scale,h*scale),0)
    draw=ImageDraw.Draw(im)
    def stroke(coords,width):
        pp=[(int(x*scale),int(y*scale)) for x,y in coords]
        draw.line(pp,fill=255,width=int(width*scale),joint="curve")
        rad=int(width*scale)//2
        for x,y in pp:
            draw.ellipse((x-rad,y-rad,x+rad,y+rad),fill=255)
    # SHO: wide, open triangle and two legitimate ㅛ vertical stems.
    stroke([(55,62),(211,14),(366,62)],18)
    stroke([(39,83),(381,83)],17)
    stroke([(151,83),(151,113)],18)
    stroke([(272,83),(272,113)],18)
    # ROOM: ㄹ stepped/open enclosure, ㅜ and an independent final ㅁ counter.
    stroke([(449,15),(824,15),(824,37),(466,37),(466,54),(824,54)],15)
    stroke([(455,69),(823,69)],14)
    stroke([(639,69),(639,83)],14)
    stroke([(463,94),(811,94),(811,114),(463,114),(463,94)],14)
    return im.resize((w,h),Image.Resampling.LANCZOS)
def source_bands(image):
    arr=np.asarray(image);a=arr[:,:,3];rgb=arr[:,:,:3]
    val=[]
    for y in range(len(a)):
        good=a[y]>160
        val.append(float(np.percentile(rgb[y,good].mean(axis=1),65)) if int(good.sum())>15 else np.nan)
    v=np.asarray(val,np.float32);g=np.where(np.isfinite(v))[0]
    if len(g)<30:raise ValueError("no measurable English metallic source profile")
    return gaussian_filter1d(np.interp(np.arange(len(v)),g,v[g]),1.3)
def execute():
    tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","175"],capture_output=True,text=True,check=True)
    decision=json.loads(tri.stdout)["assets"][0]
    if decision["next_action"] not in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"):
        raise ValueError("q175 no longer material rework: "+repr(decision))
    if sha(CAND)!=PRIOR_SHA:raise ValueError("promoted q175 changed; stop and refresh")
    header,prior=read_dds(CAND)
    with tempfile.TemporaryDirectory(prefix="A216_q175_") as temp:
        srcp=Path(temp)/"source.dds";urllib.request.urlretrieve(SOURCE_URL,srcp)
        if sha(srcp)!=SOURCE_SHA:raise ValueError("canonical English source hash changed")
        source_header,source=read_dds(srcp)
        if source_header!=header:raise ValueError("source/header drift")
        clean=Image.open(CLEAN).convert("RGBA")
        if clean.size!=source.size:raise ValueError("CLEAN size mismatch")
        x0,y0,x1,y1=ORIGINAL
        plate=prior.copy()
        plate.paste(clean.crop(ORIGINAL),(x0,y0))
        old=np.asarray(prior)
        p=np.asarray(plate)
        allow=np.zeros((1024,2048),np.bool_);allow[y0:y1,x0:x1]=True
        if np.count_nonzero(p[y0:y1,x0:x1,3]):
            raise ValueError("P1 failed original-source transparent CLEAN")
        if np.any(np.any(old!=p,axis=2)&~allow):
            raise ValueError("P1 outside requested source sprite")
        plate.save(OUT/"A216_P1_SOURCE_CLEAN_ONLY.png",compress_level=6)
        lettering=hand_contour()
        face=np.asarray(lettering,np.float32)
        if not np.any(face>150):raise ValueError("empty hand contour")
        # Measured source metal profile + bevel from local contour direction.
        # Neither arbitrary font stretch nor flat RGB rectangle.
        dist=distance_transform_edt(face>120)
        dy,dx=np.gradient(dist.astype(np.float32))
        x,y=x0+22,y0+1
        rows=np.clip(np.arange(face.shape[0])+y-y0,0,y1-y0-1)
        row_brightness=source_bands(source.crop(ORIGINAL))[rows][:,None]
        delta=21*np.clip(-dy-0.65*dx,-1,1)+8*np.clip(dist/7,0,1)-22*np.clip(dy+0.55*dx,-1,1)
        intensity=np.clip(row_brightness+delta,36,250)
        layer=np.zeros((face.shape[0],face.shape[1],4),np.uint8)
        layer[:,:,:3]=np.clip(np.stack([intensity+2,intensity+1,intensity],axis=2),0,255).astype(np.uint8)
        layer[:,:,3]=face.astype(np.uint8)
        face_layer=Image.fromarray(layer,"RGBA")
        final=plate.copy()
        shadow=Image.new("RGBA",lettering.size,(9,9,13,0))
        shadow.putalpha(lettering.point(lambda aa:int(aa*0.88)))
        final.alpha_composite(shadow,dest=(x+4,y+4))
        final.alpha_composite(face_layer,dest=(x,y))
        mask=np.zeros((1024,2048),bool)
        f=np.asarray(final)
        changes=np.any(f!=p,axis=2)
        yy,xx=np.nonzero(changes)
        if len(xx)==0:raise ValueError("missing changed face pixels")
        bbox=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
        margins=[bbox[0]-x0,x1-bbox[2],bbox[1]-y0,y1-bbox[3]]
        mask[y0:y1,x0:x1]=True
        gates={"source_to_clean_alpha_nonzero":int(np.count_nonzero(p[y0:y1,x0:x1,3])),
          "prior_to_new_rgba_changed_outside_source":int(np.count_nonzero(np.any(f!=old,axis=2)&~allow)),
          "prior_to_new_alpha_changed_outside_source":int(np.count_nonzero((f[:,:,3]!=old[:,:,3])&~allow)),
          "clean_to_final_rgba_changed_outside_original":int(np.count_nonzero(changes&~mask)),
          "margins":margins,"bbox":bbox,
          "width_relative_source":round((bbox[2]-bbox[0])/(x1-x0),4)}
        if min(margins)<2 or any(gates[k] for k in ("source_to_clean_alpha_nonzero","prior_to_new_rgba_changed_outside_source","prior_to_new_alpha_changed_outside_source","clean_to_final_rgba_changed_outside_original")):
            raise ValueError("P3 source-pixel and positive-margin gate FAIL "+repr(gates))
        path=OUT/"A216_Q175_MANUAL_SOURCE_WELDED_CHROME_TRIAL.dds"
        save_dds(header,final,path)
        h2,decoded=read_dds(path)
        if h2!=header or not np.array_equal(np.asarray(decoded),f):
            raise ValueError("persisted DDS encode/decode exact mismatch")
        decoded.save(OUT/"A216_SAVED_FLIPY_NATIVE.png",compress_level=6)
        decoded.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(OUT/"A216_SAVED_RAW_NATIVE.png",compress_level=6)
        lettering.save(OUT/"A216_HAND_VECTOR_MASK_NATIVE.png",compress_level=6)
        # Requested three separate stages and source vs new at actual scale.
        crop=(0,y0-10,x1+14,y1+12)
        for name,bg in (("GRAY",(100,100,100)),("BLACK",(0,0,0)),("WHITE",(255,255,255))):
            imgs=[comp(im,bg).crop(crop) for im in (source,plate,prior,decoded)]
            w,h=imgs[0].size
            sheet=Image.new("RGB",(4*w+3*9,h+24),bg)
            ImageDraw.Draw(sheet).text((7,4),"A216 CANONICAL ENGLISH | CLEAN | OLD | MANUAL KOREAN CHROME",fill=(238,203,8) if name!="WHITE" else (0,0,0))
            for i,im in enumerate(imgs):sheet.paste(im,(i*(w+9),24))
            for pct in (100,75,50):
                pp=sheet if pct==100 else sheet.resize((sheet.width*pct//100,sheet.height*pct//100),Image.Resampling.LANCZOS)
                pp.save(OUT/f"A216_{name}_{pct}.jpg",quality=94,optimize=True)
        report={"run":"A216","run_key":KEY,"role":"A","queue_index":175,"priority":"P1",
          "status":"TRIAL_ONLY_AWAITING_DIRECT_PRODUCER_VISUAL","triage":decision,
          "source_sha256":SOURCE_SHA,"current_candidate_sha256":PRIOR_SHA,
          "trial_sha256":sha(path),"trial_path":str(path.relative_to(ROOT)),
          "source_bbox":list(ORIGINAL),"trial_bbox":bbox,"numerical":gates,
          "construction":"Hand-designed 3x vector paths: ㅅ+ㅛ / ㄹ+ㅜ+ㅁ open contours, broad connected title silhouette at native 860x125, single AA downsample, independently sampled source English chrome color by row and contour-normal bevel/extrusion. Not A211 Noto glyph; not stretching earlier Hangul raster.",
          "pilot_family_only":True,"new_promoted_dds":0,"new_trial_dds":1,
          "independent_C1":"BLOCKED_UNTIL_PRODUCER_VISUAL",
          "C3":"NOT_RUN","user_game":"IGR032_OPEN","RUNTIME_VALIDATION":"UNTESTED"}
        (OUT/"A216_WORKER_TRIAL_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        print("A216_TRIAL_SHA",report["trial_sha256"],"BBOX",bbox,flush=True)
try:execute()
except Exception as e:
    data={"run":"A216","run_key":KEY,"status":"TRIAL_EXECUTION_FAIL_CURRENT_UNCHANGED",
          "error":type(e).__name__+":"+str(e),"traceback":traceback.format_exc(),"new_promoted_dds":0,"RUNTIME_VALIDATION":"UNTESTED"}
    (OUT/"A216_WORKER_HOLD.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    print("A216_HOLD",str(e),flush=True)
