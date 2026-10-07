#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A-MANUALQA159-568D3696-FEED"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
clean_png=repo/"localization/graphics/role_A/20261004-A-RECOVERY02/568D3696_CLEAN_PLATE.png"
source_mask_png=repo/"localization/graphics/role_A/20261004-A-RECOVERY02/568D3696_SOURCE_TEXT_MASK.png"

EXPECTED_BEFORE="2e18e459005323b37413e404b3adf31501cc92bbc3cd2b994a1c05bbdf3cef4d"
SOURCE_SHA="65bc5e88e7b01f8148bcbbb2dc4b2225bf53c8501801e329c51ecb274e8cd813"
SOURCE_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_fruity_cvt_Exst/568D3696_1024x1024.dds"
work=Path("/tmp/outrun_A159"); work.mkdir(parents=True,exist_ok=True)
source=work/"source.dds"
subprocess.run(["python3","-c",f"import urllib.request; urllib.request.urlretrieve('{SOURCE_URL}','{source}')"],check=True)

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def changed_mask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def count(mask): return sum(mask.histogram()[1:])
def dds_meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    fourcc=b[84:88]
    return w,h,pitch,depth,mips,fourcc

sb=source.read_bytes()
if sha_bytes(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha_bytes(sb),SOURCE_SHA))
oldb=candidate.read_bytes()
if sha_bytes(oldb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha_bytes(oldb),EXPECTED_BEFORE))
W,H,pitch,depth,mips,fourcc=dds_meta(sb)
if (W,H,mips,fourcc)!=(4096,4096,13,b"DXT5"):
    raise RuntimeError(("unexpected source structure",W,H,mips,fourcc))
if oldb[:128]!=sb[:128] or len(oldb)!=len(sb):
    raise RuntimeError("candidate structure/header drift")
if not clean_png.exists() or not source_mask_png.exists():
    raise RuntimeError("validated clean evidence missing")

raw_source=Image.open(source).convert("RGBA")
source_readable=raw_source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
raw_old=Image.open(candidate).convert("RGBA")
old=raw_old.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean=Image.open(clean_png).convert("RGBA")
source_mask=Image.open(source_mask_png).convert("L")
if clean.size!=(W,H) or source_mask.size!=(W,H): raise RuntimeError("evidence size drift")

# Current-policy false negative: A80 preserved the "Feed the girl!" Korean row at only 67px
# high versus a 103px source footprint. Rebuild only this row from the already validated
# A_RECOVERY02 clean plate.
ob=[1988,2061,2445,2164]
old_loc=[2005,2074,2426,2142]
x0,y0,x1,y1=ob
bx0=((x0+3)//4)*4; by0=((y0+3)//4)*4; bx1=(x1//4)*4; by1=(y1//4)*4
if [bx0,by0,bx1,by1] != [1988,2064,2444,2164]:
    raise RuntimeError(("block interior drift",[bx0,by0,bx1,by1]))
safe=[bx0+6,by0+4,bx1-4,by1-4]
sx0,sy0,sx1,sy1=safe
maxw,maxh=sx1-sx0,sy1-sy0

# Verify old target bbox still contains the historical row and clean plate has no source alpha residue.
bb_old=old.crop(tuple(ob)).getchannel("A").getbbox()
if not bb_old: raise RuntimeError("old row missing")
actual_old=[x0+bb_old[0],y0+bb_old[1],x0+bb_old[2],y0+bb_old[3]]
if actual_old!=old_loc: raise RuntimeError(("old bbox drift",actual_old,old_loc))
mask_crop=source_mask.crop(tuple(ob)).point(lambda v:255 if v else 0)
clean_alpha=clean.crop(tuple(ob)).getchannel("A")
clean_source_residue=count(ImageChops.multiply(clean_alpha,mask_crop))
if clean_source_residue!=0: raise RuntimeError(("validated clean plate residue",clean_source_residue))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","nvidia-texture-tools"],check=True)
FONT_PATTERN="Noto Sans CJK KR:style=Black"
FONT=subprocess.check_output(["fc-match","-f","%{file}",FONT_PATTERN],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font missing",FONT))
if not Path("/usr/bin/nvcompress").exists(): raise RuntimeError("nvcompress missing")

text="여자친구에게 먹이세요!"
# Source style from A79/A80/A_RECOVERY02: yellow fill + navy/white/navy layered outline.
# Maximize source-height while condensing only if exact source width requires it.
NAVY=(20,34,64,255)
WHITE=(245,245,245,255)
YELLOW=(255,215,72,255)

def render_layered(fs):
    font=ImageFont.truetype(FONT,fs)
    pad=16
    tmp=Image.new("RGBA",(maxw*3,maxh*3),(0,0,0,0))
    d=ImageDraw.Draw(tmp)
    bb=d.textbbox((pad,pad),text,font=font,stroke_width=8)
    ox,oy=-bb[0]+pad,-bb[1]+pad
    d.text((ox,oy),text,font=font,fill=YELLOW,stroke_width=8,stroke_fill=NAVY)
    d.text((ox,oy),text,font=font,fill=YELLOW,stroke_width=6,stroke_fill=WHITE)
    d.text((ox,oy),text,font=font,fill=YELLOW,stroke_width=3,stroke_fill=NAVY)
    gb=tmp.getchannel("A").getbbox()
    if not gb: return None
    return tmp.crop(gb)

best=None
for fs in range(84,36,-1):
    g=render_layered(fs)
    if g is None: continue
    if g.height>maxh: continue
    hscale=1.0
    if g.width>maxw:
        hscale=maxw/g.width
        if hscale<0.65: continue
        g=g.resize((maxw,g.height),Image.Resampling.LANCZOS)
        gb=g.getchannel("A").getbbox()
        if gb: g=g.crop(gb)
    if g.width<=maxw and g.height<=maxh:
        best=(fs,g,hscale); break
if best is None: raise RuntimeError(("no fit",maxw,maxh))
fs,glyph,hscale=best
px=sx0
py=sy0+(maxh-glyph.height)//2
if px+glyph.width>sx1 or py+glyph.height>sy1: raise RuntimeError("placement overflow")
pre=[px,py,px+glyph.width,py+glyph.height]
if not(pre[0]>x0 and pre[1]>y0 and pre[2]<x1 and pre[3]<y1):
    raise RuntimeError(("no positive source margin",ob,pre))
if glyph.height <= (old_loc[3]-old_loc[1])+8:
    raise RuntimeError(("insufficient material height improvement",glyph.height,old_loc[3]-old_loc[1]))

# Rebuild only blocks needed by the union of old/new glyphs, leaving a full
# source-bbox margin block untouched at the left/top where possible.
ux0=min(old_loc[0],pre[0]); uy0=min(old_loc[1],pre[1]); ux1=max(old_loc[2],pre[2]); uy1=max(old_loc[3],pre[3])
pbx0=max(bx0,(ux0//4)*4); pby0=max(by0,(uy0//4)*4)
pbx1=min(bx1,((ux1+3)//4)*4); pby1=min(by1,((uy1+3)//4)*4)
if not(pbx0>x0 and pby0>y0 and pbx1<x1 and pby1<=y1):
    raise RuntimeError(("patch block margin",ob,[pbx0,pby0,pbx1,pby1]))
final=old.copy()
final.paste(clean.crop((pbx0,pby0,pbx1,pby1)),(pbx0,pby0))
final.alpha_composite(glyph,(px,py))

# Encode top level only, then splice only full BC3 blocks wholly inside exact source bbox.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
png=work/"final_raw.png"; raw_final.save(png)
enc=work/"encoded.dds"
subprocess.run(["/usr/bin/nvcompress","-bc3","-nomips",str(png),str(enc)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
eb=enc.read_bytes()
eW,eH,_,_,eM,eFour=dds_meta(eb)
if (eW,eH,eFour)!=(W,H,b"DXT5"): raise RuntimeError(("nvcompress structure",eW,eH,eM,eFour))
top_size=(W//4)*(H//4)*16
if len(eb)<128+top_size: raise RuntimeError("encoded top level short")
outb=bytearray(oldb)
src_payload=eb[128:128+top_size]
bw=W//4
changed_blocks=0
# readable y -> raw y conversion for the same block-aligned rectangle
raw_y0=H-pby1; raw_y1=H-pby0
for ry in range(raw_y0//4,raw_y1//4):
    for rx in range(pbx0//4,pbx1//4):
        off=128+(ry*bw+rx)*16
        noff=(ry*bw+rx)*16
        nb=src_payload[noff:noff+16]
        if outb[off:off+16]!=nb:
            changed_blocks+=1
            outb[off:off+16]=nb
if bytes(outb[:128])!=oldb[:128] or len(outb)!=len(oldb): raise RuntimeError("splice structure drift")
candidate.write_bytes(outb)

raw_dec=Image.open(candidate).convert("RGBA")
dec=raw_dec.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
diff=changed_mask(old,dec)
allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1),fill=255)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_delta=ImageChops.difference(old.getchannel("A"),dec.getchannel("A")).point(lambda v:255 if v else 0)
alpha_out=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed)))
if outside or alpha_out: raise RuntimeError(("outside change",outside,alpha_out))

db=dec.crop(tuple(ob)).getchannel("A").getbbox()
if not db: raise RuntimeError("decoded row empty")
loc=[x0+db[0],y0+db[1],x0+db[2],y0+db[3]]
if not(loc[0]>x0 and loc[1]>y0 and loc[2]<x1 and loc[3]<y1):
    raise RuntimeError(("decoded positive margin",ob,loc))
newh=loc[3]-loc[1]
if newh <= (old_loc[3]-old_loc[1])+8:
    raise RuntimeError(("decoded improvement too small",newh,old_loc[3]-old_loc[1]))

# Verify all bytes/pixels outside r4 remain unchanged.
pixel_exact_outside=(outside==0 and alpha_out==0)

def comp(im):
    bg=Image.new("RGBA",im.size,(72,72,72,255)); bg.alpha_composite(im); return bg.convert("RGB")
m=24; cr=(x0-m,y0-m,x1+m,y1+m)
views=[comp(z).crop(cr) for z in (source_readable,old,clean,dec)]
scale=3
views=[v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST) for v in views]
labels=["SOURCE Feed the girl!","C old 67px","CLEAN","A159 여자친구에게 먹이세요!"]
sheet=Image.new("RGB",(sum(v.width for v in views)+30,max(v.height for v in views)+36),"white")
d=ImageDraw.Draw(sheet); xx=0
for lab,v in zip(labels,views):
    d.text((xx+2,2),lab,fill="black")
    sheet.paste(v,(xx,36)); xx+=v.width+10
sheet.save(out/"A159_568D_R4_SOURCE_OLD_CLEAN_FINAL.jpg",quality=95)

full=Image.new("RGB",(2048,1024),(50,50,50))
full.paste(comp(old).resize((1024,1024),Image.Resampling.LANCZOS),(0,0))
full.paste(comp(dec).resize((1024,1024),Image.Resampling.LANCZOS),(1024,0))
full.save(out/"A159_568D_OLD_FINAL_FULL.jpg",quality=93)
rawsheet=Image.new("RGB",(2048,1024),(50,50,50))
rawsheet.paste(comp(raw_old).resize((1024,1024),Image.Resampling.LANCZOS),(0,0))
rawsheet.paste(comp(raw_dec).resize((1024,1024),Image.Resampling.LANCZOS),(1024,0))
rawsheet.save(out/"A159_568D_OLD_FINAL_RAW.jpg",quality=93)

report={
 "schema_version":1,"role":"A","run":"A159","index":53,"asset":asset_rel,
 "trigger":"PRE_INGAME_CURRENT_POLICY_R4_TEXT_SCALE_HIERARCHY_FALSE_NEGATIVE",
 "prior_c_status":"C_USERPOLICY02_PASS_PENDING_INGAME","prior_candidate_sha256":EXPECTED_BEFORE,
 "source_sha256":SOURCE_SHA,"candidate_sha256":sha_bytes(bytes(outb)),
 "source_bbox":ob,"prior_localized_bbox":old_loc,"localized_bbox":loc,
 "source_size":[x1-x0,y1-y0],"prior_localized_size":[old_loc[2]-old_loc[0],old_loc[3]-old_loc[1]],"localized_size":[loc[2]-loc[0],loc[3]-loc[1]],
 "translation_change":{"source":"Feed the girl!","prior":"여자친구에게 먹여 주세요!","korean":"여자친구에게 먹이세요!"},
 "render":{"font_pattern":FONT_PATTERN,"font_file":Path(FONT).name,"font_size":fs,"horizontal_scale":round(hscale,4),"style":"yellow fill + navy/white/navy layered outline","alignment":"source-left block-safe +2px"},
 "machine_qa":{"bbox_size_positive_margin":"1/1 PASS","changed_pixels_outside_exact_source_bbox":outside,"alpha_changed_outside_exact_source_bbox":alpha_out,"clean_source_residue":clean_source_residue,"prior_candidate_exact_outside_target":pixel_exact_outside,"changed_top_level_bc3_blocks":changed_blocks,"header_128_exact":bytes(outb[:128])==oldb[:128],"mip_count_preserved":mips,"raw_orientation":"mirror_y"},
 "ordered_generation_gate":{"1_plate_restoration":"PASS_VALIDATED_A_RECOVERY02_CLEAN","2_slant_direction":"PASS_UPRIGHT_SOURCE_FAMILY","3_no_unnecessary_undersizing":"PASS_MATERIAL_HEIGHT_IMPROVEMENT","4_weight_outline_shadow":"PASS_SOURCE_YELLOW_NAVY_WHITE_FAMILY","5_clipping":"PASS_POSITIVE_MARGIN","6_protected_clearance":"PASS_ZERO_OUTSIDE_CHANGE","7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER","8_immediate_readability":"PENDING_CONTROLLER"},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","status":"A159_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA","runtime_validation":"UNTESTED","no_vr_ffb_dx11_dxvk_work":True
}
(out/"A159_568D3696_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":"A159","index":53,"asset":"568D3696","candidate_sha256":report["candidate_sha256"],"source_height":103,"prior_height":67,"new_height":newh,"bbox_size_positive_margin":"1/1 PASS","outside":outside,"alpha_outside":alpha_out,"clean_residue":clean_source_residue,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261007-A-MANUALQA159-568D3696-FEED/A159_568D3696_REPORT.json"}
(wr/"A159_568D3696.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
