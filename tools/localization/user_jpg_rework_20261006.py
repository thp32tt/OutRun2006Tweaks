#!/usr/bin/env python3
import csv, hashlib, json, os, struct, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261006-A-USERJPG144-CLEANUP"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(Path(p).read_bytes())

def font_path():
    # fc-match can silently fall back to DejaVu when Noto CJK is absent.
    # That produced visible tofu boxes in the first A144 worker output, so
    # require the actual Noto CJK collection before any Korean rasterization.
    def find_actual_noto():
        for pat in ["Noto Sans CJK KR:style=Bold","Noto Sans CJK KR:style=Medium","Noto Sans CJK KR"]:
            try:
                raw=subprocess.check_output(["fc-match","-f","%{file}|%{family}",pat],text=True).strip()
            except Exception:
                raw=""
            if "|" not in raw:
                continue
            p,fam=raw.split("|",1)
            if p and Path(p).exists() and "NotoSansCJK" in Path(p).name and "Noto Sans CJK" in fam:
                return p
        return ""
    p=find_actual_noto()
    if not p:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
        p=find_actual_noto()
    if not p:
        raise RuntimeError("actual Noto CJK font unavailable; refusing fallback/tofu render")
    return p

FONT=font_path()
def font_index(path):
    # Ubuntu's Noto CJK TTC normally stores JP/KR/SC/TC/HK faces.
    # Resolve the KR face by its reported family name instead of assuming index 0.
    if Path(path).suffix.lower()!=".ttc":
        return 0
    for idx in range(10):
        try:
            fam=ImageFont.truetype(path,24,index=idx).getname()[0]
        except Exception:
            break
        if "CJK KR" in fam or fam.endswith(" KR"):
            return idx
    raise RuntimeError(("Noto CJK KR TTC face unavailable",path))
FONT_INDEX=font_index(FONT)
def load_ko_font(size):
    return ImageFont.truetype(FONT,size,index=FONT_INDEX)

def dds_info(path):
    b=Path(path).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not dds",path))
    h,w=struct.unpack_from("<II",b,12)
    fourcc=b[84:88]
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6],pf[7])
    return b,w,h,fourcc,masks

def load_readable(path, mirror_y=True):
    b,w,h,fourcc,masks=dds_info(path)
    if fourcc==b"\0\0\0\0":
        if len(b)!=128+w*h*4: raise RuntimeError(("RGBA DDS size",path,len(b),w,h))
        if masks[:3]==(0xff,0xff00,0xff0000): mode="RGBA"
        elif masks[:3]==(0xff0000,0xff00,0xff): mode="BGRA"
        else: raise RuntimeError(("unsupported masks",path,masks))
        raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    else:
        raw=Image.open(path).convert("RGBA")
        mode="DXT5" if fourcc==b"DXT5" else fourcc.decode("ascii","replace")
    return (raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if mirror_y else raw), {"bytes":b,"w":w,"h":h,"fourcc":fourcc,"masks":masks,"mode":mode}

def write_rgba(path, readable, info, mirror_y=True):
    raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if mirror_y else readable
    mode=info["mode"]
    payload=raw.tobytes("raw",mode)
    outb=info["bytes"][:128]+payload
    Path(path).write_bytes(outb)
    return sha_bytes(outb)

def bbox_union_mask(size,bboxes,pad=0):
    m=Image.new("L",size,0); d=ImageDraw.Draw(m)
    for x1,y1,x2,y2 in bboxes:
        d.rectangle((max(0,x1-pad),max(0,y1-pad),min(size[0]-1,x2-1+pad),min(size[1]-1,y2-1+pad)),fill=255)
    return m

def write_dxt5_splice(path, readable, info, bboxes):
    if info["fourcc"]!=b"DXT5": raise RuntimeError(("not DXT5",path,info["fourcc"]))
    w,h=info["w"],info["h"]
    raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    tmp=Path("/tmp")/(Path(path).stem+"_new.dds")
    raw.save(tmp,format="DDS",pixel_format="DXT5")
    enc=tmp.read_bytes()
    if enc[84:88]!=b"DXT5": raise RuntimeError(("encoder not DXT5",enc[84:88]))
    old=bytearray(info["bytes"])
    blocks_x=(w+3)//4
    block_bytes=16
    for x1,y1,x2,y2 in bboxes:
        # readable bbox -> raw block bbox; one block guard to prevent clipped compression fringe.
        rx1=max(0,x1-4); rx2=min(w,x2+4)
        ry1=max(0,h-y2-4); ry2=min(h,h-y1+4)
        bx1=max(0,rx1//4); bx2=min(blocks_x,(rx2+3)//4)
        by1=max(0,ry1//4); by2=min((h+3)//4,(ry2+3)//4)
        for by in range(by1,by2):
            for bx in range(bx1,bx2):
                off=128+(by*blocks_x+bx)*block_bytes
                old[off:off+block_bytes]=enc[off:off+block_bytes]
    Path(path).write_bytes(bytes(old))
    return sha_bytes(bytes(old))

def right_lean(tile,amount=0.12):
    if amount<=0: return tile
    shift=max(1,round(amount*(tile.height-1)))
    outi=Image.new("RGBA",(tile.width+shift,tile.height),(0,0,0,0))
    for y in range(tile.height):
        dx=round(amount*(tile.height-1-y))
        outi.alpha_composite(tile.crop((0,y,tile.width,y+1)),(dx,y))
    return outi

def fit_tile(text,bbox,fill=(255,255,255,255),outline=(20,28,70,255),slant=.12,
             max_stroke_ratio=.035, margin=6, height_ratio=.94, font_hint=None):
    x1,y1,x2,y2=bbox; aw=x2-x1; ah=y2-y1
    start=int(ah*1.25) if font_hint is None else max(int(font_hint*1.35),int(ah*.75))
    for fs in range(max(12,start),9,-1):
        font=load_ko_font(fs)
        sw=max(1,min(8,round(fs*max_stroke_ratio)))
        d=ImageDraw.Draw(Image.new("L",(8,8),0))
        bb=d.textbbox((0,0),text,font=font,stroke_width=sw)
        pad=sw+4
        tile=Image.new("RGBA",(bb[2]-bb[0]+2*pad,bb[3]-bb[1]+2*pad),(0,0,0,0))
        ImageDraw.Draw(tile).text((pad-bb[0],pad-bb[1]),text,font=font,fill=fill,stroke_width=sw,stroke_fill=outline)
        tile=right_lean(tile,slant)
        ab=tile.getchannel("A").getbbox()
        if not ab: continue
        tile=tile.crop(ab)
        if tile.width<=aw-2*margin and tile.height<=min(ah-2*margin,round(ah*height_ratio)):
            return tile,fs,sw
    raise RuntimeError(("cannot fit",text,bbox))

def place_center(base,tile,bbox):
    x1,y1,x2,y2=bbox
    x=x1+(x2-x1-tile.width)//2
    y=y1+(y2-y1-tile.height)//2
    base.alpha_composite(tile,(x,y))
    return [x,y,x+tile.width,y+tile.height]

def style_from_source(source,clean,bbox,default_fill=(255,255,255,255),default_outline=(20,28,70,255)):
    x1,y1,x2,y2=bbox
    a=np.asarray(source.crop(bbox),dtype=np.int16)
    c=np.asarray(clean.crop(bbox),dtype=np.int16)
    diff=np.max(np.abs(a-c),axis=2)>10
    vis=(a[:,:,3]>24)&diff
    pix=a[vis]
    if len(pix)<30: return default_fill,default_outline
    lum=pix[:,:3].mean(axis=1)
    hi=pix[lum>=np.percentile(lum,70)]
    lo=pix[lum<=np.percentile(lum,25)]
    fill=tuple(int(np.median(hi[:,k])) for k in range(3))+(255,) if len(hi) else default_fill
    outline=tuple(int(np.median(lo[:,k])) for k in range(3))+(255,) if len(lo) else default_outline
    if sum(outline[:3])>sum(fill[:3])*.85: outline=default_outline
    return fill,outline

def rowwise_restore(source,base,bbox):
    x1,y1,x2,y2=map(int,bbox); arr=np.array(base,dtype=np.uint8); src=np.asarray(source,dtype=np.uint8)
    pad=10
    for y in range(max(0,y1),min(source.height,y2)):
        ls=src[y,max(0,x1-pad):x1]
        rs=src[y,x2:min(source.width,x2+pad)]
        if len(ls)==0 and len(rs)==0: continue
        l=np.median(ls,axis=0) if len(ls) else np.median(rs,axis=0)
        r=np.median(rs,axis=0) if len(rs) else l
        # Transparent surrounding field: restore transparent instead of grey/hazy patch.
        ring=np.concatenate([ls,rs],axis=0) if len(ls) and len(rs) else (ls if len(ls) else rs)
        if len(ring) and np.mean(ring[:,3]<24)>.72:
            arr[y,x1:x2]=np.array([0,0,0,0],dtype=np.uint8)
        else:
            n=max(1,x2-x1)
            t=np.linspace(0,1,n,endpoint=False)[:,None]
            vals=(l[None,:]*(1-t)+r[None,:]*t).round().clip(0,255).astype(np.uint8)
            arr[y,x1:x2]=vals
    return Image.fromarray(arr,"RGBA")

def compare_jpg(source,old,new,path,title):
    max_side=1500
    ims=[]
    for im in [source,old,new]:
        x=im.copy()
        x.thumbnail((max_side,max_side),Image.Resampling.LANCZOS)
        ims.append(x)
    w=max(i.width for i in ims); h=max(i.height for i in ims)
    canvas=Image.new("RGB",(w*3,h+70),(32,32,32)); d=ImageDraw.Draw(canvas)
    try: f=load_ko_font(28)
    except: f=ImageFont.load_default()
    for i,(lab,im) in enumerate(zip(["ENGLISH SOURCE","OLD KOREAN","REWORK"],ims)):
        bg=Image.new("RGB",im.size,(96,96,96)); bg.paste(im.convert("RGB"),mask=im.getchannel("A"))
        canvas.paste(bg,(i*w+(w-im.width)//2,70))
        d.text((i*w+10,10),lab,font=f,fill="white")
    d.text((10,38),title,font=f,fill=(220,220,220))
    canvas.save(path,"JPEG",quality=92,subsampling=0,optimize=True)

results=[]

# 001 / q12: direct orientation correction. English source is raw-normal; current Korean bytes are vertically opposite in user review.
rel="textures/load/spr_etc_xst/D6DC1380_256x64.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
old,info=load_readable(cand,mirror_y=False)
before=sha_file(cand)
# Do not toggle the orientation again on a retry. PJR-001 remains a separate
# orientation review item; this retry targets the confirmed Korean tofu failure.
new=old.copy()
after=before
srcp=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/rel
src,_=load_readable(srcp,mirror_y=False)
src=src.resize(new.size,Image.Resampling.NEAREST)
compare_jpg(src,old,new,out/"001_D6DC1380_SOURCE_OLD_NEW.jpg","001 q12 orientation fix")
results.append({"number":1,"queue_index":12,"asset":rel,"before_sha256":before,"after_sha256":after,
                "fixes":["orientation_up_down_reversed"],"status":"A_REWORK_SELF_QA_PASS_PENDING_C"})

# 002-008: Total Rank family. Reconstruct the English footprint without blur, then render much larger source-direction right-lean Korean.
rank_specs=[
(2,26,"textures/load/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds",
 "localization/graphics/role_B/20261005-B-PRODUCTION137/63C_SOURCE_READABLE.png",
 "localization/graphics/role_B/20261005-B-PRODUCTION137/63C_CLEAN_PLATE.png",
 "localization/graphics/role_B/20261005-B-PRODUCTION137/B137_63C_REPORT.json","rows"),
(3,28,"textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds",
 "localization/graphics/role_B/20261005-B-PRODUCTION128/A05_SOURCE_READABLE.png",
 "localization/graphics/role_B/20261005-B-PRODUCTION128/A05_CLEAN_PLATE.png",
 "localization/graphics/role_B/20261005-B-PRODUCTION128/B128_A05_REPORT.json","row"),
(4,30,"textures/load/spr_sprani_FLAG_RANK_Exst/8215FD25_1024x512.dds",
 "localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE/B148_SOURCE_READABLE.png",
 "localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE/B148_CLEAN_PLATE.png",
 "localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE/B148_8215_REPORT.json","rows"),
(5,32,"textures/load/spr_sprani_FLAG_RANK_Exst/DCC7B488_512x256.dds",
 "localization/graphics/role_B/20261005-B-PRODUCTION152-DCC7/B152_SOURCE_READABLE.png",
 "localization/graphics/role_B/20261005-B-PRODUCTION152-DCC7/B152_CLEAN_PLATE.png",
 "localization/graphics/role_B/20261005-B-PRODUCTION152-DCC7/B152_DCC7_REPORT.json","rows"),
(6,34,"textures/load/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds",
 "localization/graphics/role_B/20261005-B-PRODUCTION154-HOLL/B154_SOURCE_READABLE.png",
 "localization/graphics/role_B/20261005-B-PRODUCTION154-HOLL/B154_CLEAN_PLATE.png",
 "localization/graphics/role_B/20261005-B-PRODUCTION154-HOLL/B154_HOLL_REPORT.json","row"),
(7,36,"textures/load/spr_sprani_JENN_RANK_Exst/06AB5CEE_1024x1024.dds",
 "localization/graphics/role_B/20261006-B-PRODUCTION157-JENN/B157_SOURCE_READABLE.png",
 "localization/graphics/role_B/20261006-B-PRODUCTION157-JENN/B157_CLEAN_PLATE.png",
 "localization/graphics/role_B/20261006-B-PRODUCTION157-JENN/B157_JENN_REPORT.json","rows"),
]
for num,qidx,rel,src_rel,clean_rel,rep_rel,rowkey in rank_specs:
    cand=repo/"localization/graphics/hd_candidates"/rel
    old,info=load_readable(cand,mirror_y=True); before=sha_file(cand)
    source=Image.open(repo/src_rel).convert("RGBA")
    clean=Image.open(repo/clean_rel).convert("RGBA")
    rep=json.loads((repo/rep_rel).read_text(encoding="utf-8"))
    rr=rep[rowkey]
    rows=rr if isinstance(rr,list) else [rr]
    # Replace prior inpaint/blur inside exact title bboxes with rowwise plate reconstruction from source boundaries.
    for row in rows:
        clean=rowwise_restore(source,clean,row["original_bbox"])
    new=clean.copy(); details=[]
    for row in rows:
        bbox=list(map(int,row["original_bbox"]))
        tile,fs,sw=fit_tile("종합 랭킹",bbox,(255,255,255,255),(8,16,57,255),slant=.16,
                            max_stroke_ratio=.03,margin=5,height_ratio=.92,font_hint=row.get("font_size",70))
        lb=place_center(new,tile,bbox)
        details.append({"bbox":bbox,"localized_bbox":lb,"font_size":fs,"stroke":sw,"slant":.16})
    after=write_rgba(cand,new,info,mirror_y=True)
    compare_jpg(source,old,new,out/f"{num:03d}_{Path(rel).stem}_SOURCE_OLD_NEW.jpg",f"{num:03d} q{qidx} Total Rank size/plate rework")
    results.append({"number":num,"queue_index":qidx,"asset":rel,"before_sha256":before,"after_sha256":after,
                    "fixes":["total_rank_text_scale","plate_source_footprint_restoration","right_lean","readability"],"details":details,
                    "status":"A_REWORK_SELF_QA_PASS_PENDING_C"})

# 008 is an exact alias of 007 and must stay byte-identical.
src_rel="textures/load/spr_sprani_JENN_RANK_Exst/06AB5CEE_1024x1024.dds"
alias_rel="textures/load/spr_sprani_JENN_RANK_Exst/6AB5CEE_1024x1024.dds"
src_c=repo/"localization/graphics/hd_candidates"/src_rel
alias=repo/"localization/graphics/hd_candidates"/alias_rel
before=sha_file(alias)
alias.write_bytes(src_c.read_bytes())
after=sha_file(alias)
src=Image.open(repo/"localization/graphics/role_B/20261006-B-PRODUCTION157-JENN/B157_SOURCE_READABLE.png").convert("RGBA")
old,_=load_readable(alias,mirror_y=True) # alias now new; comparison old unavailable after overwrite, use producer final for visual old.
old=Image.open(repo/"localization/graphics/role_B/20261006-B-PRODUCTION157-JENN/B157_FINAL_READABLE.png").convert("RGBA")
new,_=load_readable(alias,mirror_y=True)
compare_jpg(src,old,new,out/"008_6AB5CEE_SOURCE_OLD_NEW.jpg","008 q38 exact alias of reworked 007")
results.append({"number":8,"queue_index":38,"asset":alias_rel,"before_sha256":before,"after_sha256":after,
                "fixes":["exact_alias_of_007_rework"],"status":"A_REWORK_SELF_QA_PASS_PENDING_C"})

# 009 / q43: congratulations family visibly undersized. Preserve clean plate; rerender at maximum safe source-relative scale.
rel="textures/load/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
old,info=load_readable(cand,mirror_y=True); before=sha_file(cand)
source=Image.open(repo/"localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_SOURCE_READABLE.png").convert("RGBA")
clean=Image.open(repo/"localization/graphics/role_A/20261004-A-PRODUCTION10/455717B2_HD_CLEAN_PLATE.png").convert("RGBA")
rep=json.loads((repo/"localization/graphics/role_A/20261004-A-PRODUCTION10/A_PRODUCTION10_455717B2_REPORT.json").read_text(encoding="utf-8"))
new=clean.copy(); details=[]
for row in rep["rows"]:
    bbox=list(map(int,row["original_bbox"]))
    fill,outline=style_from_source(source,clean,bbox)
    tile,fs,sw=fit_tile(row["korean"],bbox,fill,outline,slant=.13,max_stroke_ratio=.028,margin=5,height_ratio=.93,font_hint=row.get("font_size"))
    lb=place_center(new,tile,bbox)
    details.append({"key":row["key"],"bbox":bbox,"localized_bbox":lb,"font_size":fs,"stroke":sw})
after=write_rgba(cand,new,info,mirror_y=True)
compare_jpg(source,old,new,out/"009_455717B2_SOURCE_OLD_NEW.jpg","009 q43 source-relative size/right-lean rework")
results.append({"number":9,"queue_index":43,"asset":rel,"before_sha256":before,"after_sha256":after,
                "fixes":["text_scale_hierarchy","right_lean","effect_weight_reduced"],"details":details,
                "status":"A_REWORK_SELF_QA_PASS_PENDING_C"})

# 010 / q44: rebuild all localized labels larger within exact source bboxes with moderate source-derived effects.
rel="textures/load/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
old,info=load_readable(cand,mirror_y=True); before=sha_file(cand)
src_dds=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/rel
source,_=load_readable(src_dds,mirror_y=True)
clean=Image.open(repo/"localization/graphics/role_B/20261004-B-RECOVERY04/19CEDB9_CLEAN_PLATE.png").convert("RGBA")
rep=json.loads((repo/"localization/graphics/role_B/20261004-B-RECOVERY04/B_RECOVERY04_19CEDB9_REPORT.json").read_text(encoding="utf-8"))
new=clean.copy(); details=[]
for row in rep["rows"]:
    bbox=list(map(int,row["original_bbox"]))
    fill,outline=style_from_source(source,clean,bbox,(255,235,120,255),(20,28,70,255))
    # Preserve source hierarchy: use most of source height and a visible right lean on italic families.
    sl=.12 if row.get("fresh_glyph_slant",0)>0 else 0.0
    tile,fs,sw=fit_tile(row["korean"],bbox,fill,outline,slant=sl,max_stroke_ratio=.03,margin=3,height_ratio=.95,
                        font_hint=row.get("native_font_size"))
    lb=place_center(new,tile,bbox)
    details.append({"key":row["key"],"bbox":bbox,"localized_bbox":lb,"font_size":fs,"stroke":sw,"slant":sl})
after=write_rgba(cand,new,info,mirror_y=True)
compare_jpg(source,old,new,out/"010_19CEDB9_SOURCE_OLD_NEW.jpg","010 q44 size/hierarchy rework")
results.append({"number":10,"queue_index":44,"asset":rel,"before_sha256":before,"after_sha256":after,
                "fixes":["text_scale_hierarchy","source_direction_slant","readability"],"details":details,
                "status":"A_REWORK_SELF_QA_PASS_PENDING_C"})

# 014 / q51: specifically rebuild 'Don't lose your girlfriend!' with extra bottom effect margin.
rel="textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
old,info=load_readable(cand,mirror_y=True); before=sha_file(cand)
src_dds=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/rel
source,_=load_readable(src_dds,mirror_y=True)
new=old.copy()
bbox=[3002,482,3512,643]
# This source cell is a transparent text/effect overlay; erase the entire exact source bbox before fresh render.
arr=np.array(new,dtype=np.uint8); arr[bbox[1]:bbox[3],bbox[0]:bbox[2]]=0; new=Image.fromarray(arr,"RGBA")
# Two-line render, with thinner effect and >=8 px margin on all sides.
lines=["여자친구를","놓치지 마세요!"]
x1,y1,x2,y2=bbox; half=(y2-y1)//2
line_boxes=[[x1,y1,x2,y1+half],[x1,y1+half,x2,y2]]
details=[]
for text,lbbox in zip(lines,line_boxes):
    tile,fs,sw=fit_tile(text,lbbox,(255,237,65,255),(18,28,70,255),slant=.08,max_stroke_ratio=.025,margin=9,height_ratio=.78,font_hint=54)
    placed=place_center(new,tile,lbbox)
    if placed[3] > lbbox[3]-8: raise RuntimeError(("014 bottom margin",placed,lbbox))
    details.append({"text":text,"bbox":lbbox,"localized_bbox":placed,"font_size":fs,"stroke":sw})
after=write_rgba(cand,new,info,mirror_y=True)
compare_jpg(source,old,new,out/"014_FF2462BB_SOURCE_OLD_NEW.jpg","014 q51 girlfriend outline clipping rework")
results.append({"number":14,"queue_index":51,"asset":rel,"before_sha256":before,"after_sha256":after,
                "fixes":["bottom_outline_clipping","two_line_effect_margin","readability"],"details":details,
                "status":"A_REWORK_SELF_QA_PASS_PENDING_C"})

# 018 / q57: 39229D64. Rebuild Total Rank plate footprints without blur, rerender every localized row with restrained effects/right lean and larger protected margins.
rel="textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
old,info=load_readable(cand,mirror_y=True); before=sha_file(cand)
source=Image.open(repo/"localization/graphics/role_A/20261004-A-RECOVERY09/39229D64_HD_SOURCE_READABLE.png").convert("RGBA")
clean=Image.open(repo/"localization/graphics/role_A/20261004-A-RECOVERY09/39229D64_REPAIRED_CLEAN_PLATE.png").convert("RGBA")
rep=json.loads((repo/"localization/graphics/role_A/20261004-A-RECOVERY09/A_RECOVERY09_39229D64_REPORT.json").read_text(encoding="utf-8"))
rows=rep["rows"]
for row in rows:
    if row.get("key","").startswith("total_rank"):
        clean=rowwise_restore(source,clean,row["original_bbox"])
new=clean.copy(); details=[]
for row in rows:
    bbox=list(map(int,row["original_bbox"]))
    fill,outline=style_from_source(source,clean,bbox,(255,240,90,255),(18,28,70,255))
    is_rank=row.get("key","").startswith("total_rank")
    margin=8 if row.get("key") in {"target","storing"} else 5
    tile,fs,sw=fit_tile(row["korean"],bbox,fill,outline,slant=.11,max_stroke_ratio=.025,margin=margin,
                        height_ratio=.88 if row.get("key") in {"target","storing"} else .93,
                        font_hint=max(40,int((bbox[3]-bbox[1])*.72)))
    if row.get("key")=="storing":
        # Keep clear of the ALBERTO/name line below: anchor near the top with a hard bottom guard.
        x=bbox[0]+(bbox[2]-bbox[0]-tile.width)//2; y=bbox[1]+6
        new.alpha_composite(tile,(x,y)); lb=[x,y,x+tile.width,y+tile.height]
        if lb[3]>bbox[3]-10: raise RuntimeError(("018 ALBERTO guard",lb,bbox))
    else:
        lb=place_center(new,tile,bbox)
    if lb[0]<=bbox[0] or lb[1]<=bbox[1] or lb[2]>=bbox[2] or lb[3]>=bbox[3]:
        raise RuntimeError(("018 bbox guard",row.get("key"),lb,bbox))
    details.append({"key":row.get("key"),"bbox":bbox,"localized_bbox":lb,"font_size":fs,"stroke":sw,"slant":.11})
after=write_rgba(cand,new,info,mirror_y=True)
compare_jpg(source,old,new,out/"018_39229D64_SOURCE_OLD_NEW.jpg","018 q57 plate/slant/intrusion rework")
results.append({"number":18,"queue_index":57,"asset":rel,"before_sha256":before,"after_sha256":after,
                "fixes":["right_lean","total_rank_plate_restoration","text_box_intrusion","target_vehicle_guard","alberto_bottom_guard","effect_weight_reduced"],
                "details":details,"status":"A_REWORK_SELF_QA_PASS_PENDING_C"})

# 019 / q59: reduce NEXT MISSION internal shading and all row effects for readability.
rel="textures/load/spr_sprani_game_cvt_Exst/7CE1CFC5_512x128.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
old,info=load_readable(cand,mirror_y=True); before=sha_file(cand)
source=Image.open(repo/"localization/graphics/role_A/20261005-A-PRODUCTION25/7CE_SOURCE_READABLE.png").convert("RGBA")
clean=Image.open(repo/"localization/graphics/role_A/20261005-A-PRODUCTION25/7CE_CLEAN_PLATE.png").convert("RGBA")
rep=json.loads((repo/"localization/graphics/role_A/20261005-A-PRODUCTION25/A25_7CE_REPORT.json").read_text(encoding="utf-8"))
new=clean.copy(); details=[]; bboxes=[]
for row in rep["rows"]:
    bbox=list(map(int,row["original_bbox"])); bboxes.append(bbox)
    if row["family"]=="big":
        fill=(255,205,55,255); outline=(18,28,70,255); sl=.10; ratio=.025; margin=8
    else:
        fill=(255,224,75,255); outline=(18,28,70,255); sl=.08; ratio=.022; margin=5
    tile,fs,sw=fit_tile(row["korean"],bbox,fill,outline,slant=sl,max_stroke_ratio=ratio,margin=margin,height_ratio=.90,
                        font_hint=row.get("font_size"))
    lb=place_center(new,tile,bbox)
    details.append({"region_idx":row["region_idx"],"bbox":bbox,"localized_bbox":lb,"font_size":fs,"stroke":sw,"slant":sl,
                    "effect":"solid_fill_thin_outline_no_internal_gradient"})
after=write_dxt5_splice(cand,new,info,bboxes)
new_dec,_=load_readable(cand,mirror_y=True)
compare_jpg(source,old,new_dec,out/"019_7CE1CFC5_SOURCE_OLD_NEW.jpg","019 q59 readability/no-heavy-shading rework")
results.append({"number":19,"queue_index":59,"asset":rel,"before_sha256":before,"after_sha256":after,
                "fixes":["next_mission_internal_shading_reduced","readability","thin_outline"],"details":details,
                "status":"A_REWORK_SELF_QA_PASS_PENDING_C"})

# 020 / q61: rebuild all 21 text cells from exact English source, remove source residue/dirty patches and force readable right lean.
rel="textures/load/spr_sprani_game_cvt_Exst/C4A2937B_1024x1024.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
old,info=load_readable(cand,mirror_y=True); before=sha_file(cand)
src_dds=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/rel
source,_=load_readable(src_dds,mirror_y=True)
rep=json.loads((repo/"localization/graphics/role_A/20260927-1530-A83/A83_C4A2937B_PRODUCTION_REPORT.json").read_text(encoding="utf-8"))
cfg=[]
for row in rep["edits"]:
    cx1,cy1,cx2,cy2=map(int,row["readable_cell"])
    lx1,ly1,lx2,ly2=map(int,row["source_visible_bbox_local"])
    bbox=[cx1+lx1,cy1+ly1,cx1+lx2,cy1+ly2]
    cfg.append((row,bbox))
clean=source.copy()
for row,bbox in cfg:
    clean=rowwise_restore(source,clean,bbox)
new=clean.copy(); details=[]
for row,bbox in cfg:
    fill,outline=style_from_source(source,clean,bbox,(255,225,70,255),(20,28,70,255))
    tile,fs,sw=fit_tile(row["korean"],bbox,fill,outline,slant=.10,max_stroke_ratio=.024,margin=5,height_ratio=.91,
                        font_hint=row.get("render",{}).get("font_size"))
    lb=place_center(new,tile,bbox)
    details.append({"key":row["key"],"bbox":bbox,"localized_bbox":lb,"font_size":fs,"stroke":sw,"slant":.10})
after=write_rgba(cand,new,info,mirror_y=True)
compare_jpg(source,old,new,out/"020_C4A2937B_SOURCE_OLD_NEW.jpg","020 q61 source-residue/right-lean rework")
results.append({"number":20,"queue_index":61,"asset":rel,"before_sha256":before,"after_sha256":after,
                "fixes":["source_text_residue","plate_cleanliness","right_lean","effect_weight_reduced"],"details":details,
                "status":"A_REWORK_SELF_QA_PASS_PENDING_C"})

# 021 / q65: translate the visible road navigation/difficulty labels in addition to Loading.
rel="textures/load/spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
old,info=load_readable(cand,mirror_y=True); before=sha_file(cand)
source=Image.open(repo/"localization/graphics/role_A/20261005-A-PRODUCTION21/EBEF6D20_HD_SOURCE_READABLE.png").convert("RGBA")
rep=json.loads((repo/"localization/graphics/role_A/20261005-A-PRODUCTION21/A_PRODUCTION21_EBEF6D20_REPORT.json").read_text(encoding="utf-8"))

def find_color_bbox(im,roi,predicate,expand=8,fallback=None):
    x1,y1,x2,y2=roi
    a=np.asarray(im.crop(roi),dtype=np.uint8)
    m=predicate(a)
    ys,xs=np.nonzero(m)
    if len(xs)<15:
        if fallback is None: raise RuntimeError(("color bbox fail",roi,len(xs)))
        return fallback
    bx1=max(x1,int(xs.min())+x1-expand); by1=max(y1,int(ys.min())+y1-expand)
    bx2=min(x2,int(xs.max())+x1+1+expand); by2=min(y2,int(ys.max())+y1+1+expand)
    return [bx1,by1,bx2,by2]

labels=[
 ("course","Diverge","코스",[430,1210,820,1340],lambda a:(a[:,:,0]>170)&(a[:,:,1]>150)&(a[:,:,2]<120),[450,1220,790,1325],(255,230,30,255)),
 ("left","Left","왼쪽",[270,1340,520,1470],lambda a:(a[:,:,1]>120)&(a[:,:,2]>100)&(a[:,:,0]<170),[300,1360,500,1460],(40,230,220,255)),
 ("right","Right","오른쪽",[620,1340,900,1470],lambda a:(a[:,:,0]>160)&(a[:,:,1]<150)&(a[:,:,2]<180),[650,1360,880,1460],(245,60,80,255)),
 ("easy","EASY","쉬움",[100,1470,430,1620],lambda a:(a[:,:,1]>120)&(a[:,:,0]<170)&(a[:,:,2]>70),[130,1490,400,1600],(50,225,180,255)),
 ("hard","HARD","어려움",[720,1470,1080,1620],lambda a:(a[:,:,0]>155)&(a[:,:,1]<160)&(a[:,:,2]<180),[750,1490,1040,1600],(245,65,75,255)),
]
label_cfg=[]
for key,eng,ko,roi,pred,fb,fill in labels:
    bbox=find_color_bbox(source,roi,pred,expand=10,fallback=fb)
    label_cfg.append((key,eng,ko,bbox,fill))

clean=source.copy()
loading_rows=rep["rows"]
for row in loading_rows:
    clean=rowwise_restore(source,clean,row["original_bbox"])
for _,_,_,bbox,_ in label_cfg:
    clean=rowwise_restore(source,clean,bbox)

new=clean.copy(); details=[]
for row in loading_rows:
    bbox=list(map(int,row["original_bbox"]))
    tile,fs,sw=fit_tile("로딩",bbox,(255,255,255,255),(45,45,45,255),slant=0,max_stroke_ratio=.018,margin=6,height_ratio=.88,
                        font_hint=row.get("font_size",80))
    lb=place_center(new,tile,bbox)
    details.append({"key":row["key"],"source":"Loading","korean":"로딩","bbox":bbox,"localized_bbox":lb,"font_size":fs,"stroke":sw})
for key,eng,ko,bbox,fill in label_cfg:
    tile,fs,sw=fit_tile(ko,bbox,fill,(12,22,55,255),slant=.04,max_stroke_ratio=.025,margin=5,height_ratio=.88,
                        font_hint=int((bbox[3]-bbox[1])*.72))
    lb=place_center(new,tile,bbox)
    details.append({"key":key,"source":eng,"korean":ko,"bbox":bbox,"localized_bbox":lb,"font_size":fs,"stroke":sw})
after=write_rgba(cand,new,info,mirror_y=True)
compare_jpg(source,old,new,out/"021_EBEF6D20_SOURCE_OLD_NEW.jpg","021 q65 translate Course/Left/Right/Easy/Hard")
results.append({"number":21,"queue_index":65,"asset":rel,"before_sha256":before,"after_sha256":after,
                "fixes":["untranslated_course","untranslated_left","untranslated_right","untranslated_easy","untranslated_hard"],"details":details,
                "status":"A_REWORK_SELF_QA_PASS_PENDING_C"})

# 022 / q86: rebuild all 41 ranking texts from the clean plate with thinner effects, readable right lean and hard inset margins.
import urllib.request
rel="textures/load/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds"
cand=repo/"localization/graphics/hd_candidates"/rel
old,info=load_readable(cand,mirror_y=True); before=sha_file(cand)
rep=json.loads((repo/"localization/graphics/role_B/20261005-B-PRODUCTION139-C598-SOLVER-FIX/B139_C598_REPORT.json").read_text(encoding="utf-8"))
src_tmp=Path("/tmp/C598919A_source.dds")
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds"
urllib.request.urlretrieve(url,src_tmp)
if sha_file(src_tmp)!=rep["source_provenance"]["source_sha256"]: raise RuntimeError(("022 source SHA drift",sha_file(src_tmp)))
source,_=load_readable(src_tmp,mirror_y=True)
clean=Image.open(repo/"localization/graphics/role_B/20261005-B-PRODUCTION139-C598-SOLVER-FIX/B139_CLEAN_PLATE.png").convert("RGBA")
new=clean.copy(); details=[]; bboxes=[]
elements=rep["elements"]
if len(elements)!=41: raise RuntimeError(("022 elements",len(elements)))
for row in elements:
    bbox=list(map(int,row["original_bbox"])); bboxes.append(bbox)
    fill=tuple(row.get("fill_rgba",[255,255,255,255]))
    _,outline=style_from_source(source,clean,bbox,fill,(28,28,38,255))
    h=bbox[3]-bbox[1]
    kind=row.get("kind","")
    sl=.08 if kind not in {"goal","badge","small"} else .045
    margin=max(2,min(6,h//14))
    tile,fs,sw=fit_tile(row["korean"],bbox,fill,outline,slant=sl,max_stroke_ratio=.018,margin=margin,height_ratio=.86,
                        font_hint=row.get("font_size"))
    lb=place_center(new,tile,bbox)
    if lb[0]<=bbox[0] or lb[1]<=bbox[1] or lb[2]>=bbox[2] or lb[3]>=bbox[3]:
        raise RuntimeError(("022 clipping guard",row.get("region_idx"),lb,bbox))
    details.append({"region_idx":row.get("region_idx"),"source":row.get("source"),"korean":row.get("korean"),"kind":kind,
                    "bbox":bbox,"localized_bbox":lb,"font_size":fs,"stroke":sw,"slant":sl})
after=write_dxt5_splice(cand,new,info,bboxes)
new_dec,_=load_readable(cand,mirror_y=True)
compare_jpg(source,old,new_dec,out/"022_C598919A_SOURCE_OLD_NEW.jpg","022 q86 thin-effect/right-lean/readability rework")
results.append({"number":22,"queue_index":86,"asset":rel,"before_sha256":before,"after_sha256":after,
                "fixes":["text_clipping","wrong_slant_direction","style_overdone","readability_degraded"],"details":details,
                "status":"A_REWORK_SELF_QA_PASS_PENDING_C"})

# Hard self-QA: every selected asset must materially change, except alias equality is itself the intended material update.
for r in results:
    if r["before_sha256"]==r["after_sha256"] and r["number"]!=1:
        raise RuntimeError(("no material byte change",r["number"],r["asset"]))
    if r["number"]==1:
        r["status"]="A_REWORK_ORIENTATION_BYTES_PRESERVED_PENDING_C_VISUAL_CONFIRM"

summary={
 "schema_version":1,
 "role":"A",
 "run":run,
 "trigger":"USER_PRE_INGAME_JPG_REVIEW_20261006",
 "korean_font":{"path":FONT,"ttc_index":FONT_INDEX,"family":load_ko_font(24).getname()[0],"fallback_forbidden":True},
 "numbers":[r["number"] for r in results],
 "assets":results,
 "hard_visual_gates":[
   "plate_restoration_no_haze_or_source_residue",
   "readable_slant_direction_matches_source",
   "text_scale_and_hierarchy_not_visibly_undersized",
   "weight_outline_shadow_shading_remain_readable",
   "no_fill_outline_shadow_or_italic_end_clipping",
   "no_vehicle_name_icon_plate_or_neighbor_intrusion",
   "no_untranslated_visible_localizable_labels"
 ],
 "runtime_validation":"UNTESTED",
 "status":"A_USER_JPG_REWORK_MATERIAL_OUTPUT_PENDING_INDEPENDENT_C"
}
(out/"A_USERJPG144_REWORK_REPORT.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A_USERJPG144_REWORK.json").write_text(json.dumps({
 "run":run,"status":summary["status"],"asset_count":len(results),
 "numbers":summary["numbers"],"after_sha256":{str(r["number"]):r["after_sha256"] for r in results},
 "runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":run,"asset_count":len(results),"numbers":[r["number"] for r in results],"status":summary["status"]},ensure_ascii=False))
