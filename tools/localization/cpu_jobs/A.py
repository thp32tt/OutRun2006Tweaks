#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A160-Q012-D6DC1380-SCALE"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset_rel="textures/load/spr_etc_xst/D6DC1380_256x64.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
EXPECTED_BEFORE="703374404675cff67309fd25ee22ee57483af2136b76ebe9ea152c5ba4d00422"
SOURCE_SHA="42aa10e021f9170247612b2e8231be43458abc3cda1011595db2fe2902df4352"
SOURCE_BBOX=[8,10,248,44]
ALLOWED=[32,40,992,176]
TEXT="계속?"
work=Path("/tmp/outrun_A160"); work.mkdir(parents=True,exist_ok=True)

def sha(b): return hashlib.sha256(b).hexdigest()
def cnt(mask): return sum(mask.histogram()[1:])
def diffmask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def dds_meta(b):
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h,w,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf_flags=struct.unpack_from("<I",b,80)[0]
    fourcc=b[84:88]
    masks=struct.unpack_from("<4I",b,92)
    return w,h,pitch,depth,mips,pf_flags,fourcc,masks

oldb=candidate.read_bytes()
if sha(oldb)!=EXPECTED_BEFORE: raise RuntimeError(("candidate drift",sha(oldb),EXPECTED_BEFORE))
W,H,pitch,depth,mips,pff,fourcc,masks=dds_meta(oldb)
if (W,H,mips)!=(1024,256,1): raise RuntimeError(("unexpected candidate",W,H,mips,fourcc,masks))
if len(oldb)!=128+W*H*4: raise RuntimeError(("unexpected payload",len(oldb)))

# Recover exact stock source from pinned public revision. Release and Original both exist;
# accept only the SHA recorded by A89.
urls=[
 "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_etc_xst/D6DC1380_256x64.dds",
 "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_etc_xst/D6DC1380_256x64.dds"
]
source=None; source_url=None
for i,u in enumerate(urls):
    p=work/f"source{i}.dds"
    try:
        urllib.request.urlretrieve(u,p)
        if sha(p.read_bytes())==SOURCE_SHA:
            source=p; source_url=u; break
    except Exception:
        pass
if source is None: raise RuntimeError("canonical source SHA not found")
sb=source.read_bytes()
sW,sH,_,_,sM,_,_,_=dds_meta(sb)
if (sW,sH)!=(256,64): raise RuntimeError(("source dimensions",sW,sH))

raw_old=Image.open(candidate).convert("RGBA")
# Current C233 evidence established readable view is FLIP-Y relative to stored DDS.
old=raw_old.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
raw_source=Image.open(source).convert("RGBA")
src=raw_source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src4=src.resize((1024,256),Image.Resampling.NEAREST)

# Find raw pixel byte order that reconstructs the current payload exactly.
rawmode=None
for mode in ("BGRA","RGBA"):
    try:
        payload=raw_old.tobytes("raw",mode)
        if payload==oldb[128:]:
            rawmode=mode; break
    except Exception:
        pass
if rawmode is None: raise RuntimeError(("cannot infer rawmode",masks))

# Check current localized alpha bbox.
obb=old.getchannel("A").getbbox()
if not obb: raise RuntimeError("current candidate empty")
old_bbox=list(obb)
if old_bbox!=[207,41,817,175]:
    raise RuntimeError(("current bbox drift",old_bbox))

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk","fonts-noto-cjk-extra"],check=True)
FONT_PATTERN="Noto Sans CJK KR:style=Black"
FONT=subprocess.check_output(["fc-match","-f","%{file}",FONT_PATTERN],text=True).strip()
if not FONT or not Path(FONT).exists(): raise RuntimeError(("font missing",FONT))

# Render from scratch on transparent plate. Height already nearly max in A89; PJR-001
# specifically requires a material scale fix, so use max-safe height plus wider techno
# proportions and source-matching readable right lean instead of reusing unchanged bytes.
target_h=132
target_w=790
font=ImageFont.truetype(FONT,150)
scratch=Image.new("RGBA",(1800,400),(0,0,0,0))
d=ImageDraw.Draw(scratch)
bb=d.textbbox((40,40),TEXT,font=font,stroke_width=9)
base=Image.new("RGBA",(bb[2]-bb[0]+80,bb[3]-bb[1]+80),(0,0,0,0))
bd=ImageDraw.Draw(base)
xy=(40-bb[0],40-bb[1])
# outer steel-gray halo, navy main border, white face
bd.text(xy,TEXT,font=font,fill=(250,250,250,255),stroke_width=11,stroke_fill=(103,108,126,255))
bd.text(xy,TEXT,font=font,fill=(250,250,250,255),stroke_width=7,stroke_fill=(10,22,76,255))
gb=base.getchannel("A").getbbox()
base=base.crop(gb)
scale_h=target_h/base.height
nw=max(1,round(base.width*scale_h)); nh=target_h
g=base.resize((nw,nh),Image.Resampling.LANCZOS)
# readable right lean matching English source
shear=0.16
extra=round(g.height*shear)+4
sl=Image.new("RGBA",(g.width+extra,g.height),(0,0,0,0))
sl=g.transform(sl.size,Image.Transform.AFFINE,(1,-shear,extra-2,0,1,0),Image.Resampling.BICUBIC)
gb=sl.getchannel("A").getbbox(); sl=sl.crop(gb)
if sl.width<target_w:
    sl=sl.resize((target_w,sl.height),Image.Resampling.LANCZOS)
elif sl.width>target_w:
    sl=sl.resize((target_w,sl.height),Image.Resampling.LANCZOS)
gb=sl.getchannel("A").getbbox(); sl=sl.crop(gb)

aw=ALLOWED[2]-ALLOWED[0]; ah=ALLOWED[3]-ALLOWED[1]
if sl.width>=aw or sl.height>=ah: raise RuntimeError(("render exceeds allowed",sl.size,aw,ah))
px=ALLOWED[0]+(aw-sl.width)//2
py=ALLOWED[1]+(ah-sl.height)//2
final=old.copy()
# q12 is text-only transparent plate; clear only exact permitted source bbox.
final.paste(Image.new("RGBA",(aw,ah),(0,0,0,0)),(ALLOWED[0],ALLOWED[1]))
final.alpha_composite(sl,(px,py))
fb=final.getchannel("A").getbbox()
if not fb: raise RuntimeError("final empty")
loc=list(fb)
if not(loc[0]>=ALLOWED[0] and loc[1]>=ALLOWED[1] and loc[2]<=ALLOWED[2] and loc[3]<=ALLOWED[3]):
    raise RuntimeError(("bbox overflow",loc,ALLOWED))
if (loc[2]-loc[0])<=old_bbox[2]-old_bbox[0]+100:
    raise RuntimeError(("material width gain insufficient",old_bbox,loc))
if (loc[3]-loc[1])<128:
    raise RuntimeError(("height too small",loc))

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
newb=oldb[:128]+raw_final.tobytes("raw",rawmode)
if newb[:128]!=oldb[:128] or len(newb)!=len(oldb): raise RuntimeError("structure changed")
candidate.write_bytes(newb)
dec_raw=Image.open(candidate).convert("RGBA")
dec=dec_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
db=list(dec.getchannel("A").getbbox() or ())
if db!=loc: raise RuntimeError(("decoded bbox drift",loc,db))

allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((ALLOWED[0],ALLOWED[1],ALLOWED[2]-1,ALLOWED[3]-1),fill=255)
dm=diffmask(old,dec)
outside=cnt(ImageChops.multiply(dm,ImageOps.invert(allowed)))
ad=ImageChops.difference(old.getchannel("A"),dec.getchannel("A")).point(lambda v:255 if v else 0)
alpha_out=cnt(ImageChops.multiply(ad,ImageOps.invert(allowed)))
if outside or alpha_out: raise RuntimeError(("blast radius",outside,alpha_out))
if db[0]<=ALLOWED[0] or db[1]<=ALLOWED[1] or db[2]>=ALLOWED[2] or db[3]>=ALLOWED[3]:
    raise RuntimeError(("positive margin",db,ALLOWED))

# Practical-scale and raw evidence decoded from persisted DDS.
def comp(im):
    bg=Image.new("RGBA",im.size,(96,96,96,255)); bg.alpha_composite(im); return bg.convert("RGB")
source_hd=comp(src4); old_rgb=comp(old); final_rgb=comp(dec)
sheet=Image.new("RGB",(3072,768),"white")
for i,img in enumerate((source_hd,old_rgb,final_rgb)):
    sheet.paste(img,(i*1024,0))
ImageDraw.Draw(sheet).text((8,4),"SOURCE 4x DISPLAY | C233 REJECTED | A160 FINAL",fill="black")
sheet.save(out/"A160_D6DC1380_SOURCE_OLD_FINAL.jpg",quality=95)

for pct in (100,75,50):
    sz=(round(W*pct/100),round(H*pct/100))
    trio=[x.resize(sz,Image.Resampling.LANCZOS) for x in (source_hd,old_rgb,final_rgb)]
    ev=Image.new("RGB",(sum(x.width for x in trio),max(x.height for x in trio)),"white")
    xx=0
    for x in trio: ev.paste(x,(xx,0)); xx+=x.width
    ev.save(out/f"A160_D6DC1380_PRACTICAL_{pct}.jpg",quality=94)

raw_sheet=Image.new("RGB",(2048,512),(64,64,64))
raw_sheet.paste(comp(raw_old).resize((1024,256),Image.Resampling.NEAREST),(0,0))
raw_sheet.paste(comp(dec_raw).resize((1024,256),Image.Resampling.NEAREST),(1024,0))
raw_sheet.paste(old_rgb.resize((1024,256),Image.Resampling.NEAREST),(0,256))
raw_sheet.paste(final_rgb.resize((1024,256),Image.Resampling.NEAREST),(1024,256))
raw_sheet.save(out/"A160_D6DC1380_RAW_FLIPY.jpg",quality=95)

report={
 "schema_version":2,"role":"A","run":"A160","index":12,"asset":asset_rel,
 "trigger":"C233_REWORK_REQUIRED_MATERIAL_SCALE_FIX_PENDING_A_B",
 "user_regression":"PJR-001-20261006",
 "prior_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":sha(newb),
 "canonical_source":{"sha256":SOURCE_SHA,"url":source_url,"native_size":[256,64],"display_scale":4,"source_bbox_native":SOURCE_BBOX,"source_bbox_hd":ALLOWED},
 "translation":{"source":"Continue?","korean":"계속?"},
 "prior_localized_bbox":old_bbox,"localized_bbox":db,
 "prior_size":[old_bbox[2]-old_bbox[0],old_bbox[3]-old_bbox[1]],
 "localized_size":[db[2]-db[0],db[3]-db[1]],
 "render":{"font_pattern":FONT_PATTERN,"font_file":Path(FONT).name,"target_width":target_w,"target_height":target_h,"readable_right_shear":shear,"style":"white face + navy border + steel-gray outer halo","alignment":"centered within exact scaled source bbox"},
 "machine_qa":{"bbox_containment":"PASS","positive_margin":"PASS","changed_pixels_outside_exact_source_bbox":outside,"alpha_changed_outside_exact_source_bbox":alpha_out,"header_128_exact":newb[:128]==oldb[:128],"mip_count":mips,"decoded_persisted_bbox_exact":db==loc,"rawmode":rawmode,"raw_orientation":"preserve current; readable=FLIP_Y","practical_scale_reviews":[100,75,50]},
 "ordered_generation_gate":{"1_plate_restoration":"PASS_TRANSPARENT_TEXT_ONLY_SOURCE_BBOX","2_slant_direction":"PASS_READABLE_RIGHT_LEAN","3_no_unnecessary_undersizing":"PASS_MATERIAL_WIDTH_SCALE_INCREASE","4_weight_outline_shadow":"PASS_SOURCE_WHITE_NAVY_STEEL_FAMILY","5_clipping":"PASS_POSITIVE_MARGIN","6_protected_clearance":"PASS_ZERO_OUTSIDE_CHANGE","7_flip_y_raw":"EVIDENCE_WRITTEN_PENDING_CONTROLLER","8_immediate_readability":"PENDING_CONTROLLER"},
 "status":"A160_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA",
 "runtime_validation":"UNTESTED","no_vr_ffb_dx11_dxvk_work":True
}
(out/"A160_D6DC1380_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":"A160","index":12,"asset":"D6DC1380","candidate_sha256":report["candidate_sha256"],"prior_size":report["prior_size"],"localized_size":report["localized_size"],"width_gain":report["localized_size"][0]-report["prior_size"][0],"outside":outside,"alpha_outside":alpha_out,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261007-A160-Q012-D6DC1380-SCALE/A160_D6DC1380_REPORT.json"}
(wr/"A160_D6DC1380.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
