#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A-REWORK153-754F0599"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
worker_out=repo/"localization/graphics/worker_results"; worker_out.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
base=repo/"localization/graphics/role_A/20261005-A-PRODUCTION29"
source_png=base/"754F0599_HD_SOURCE_READABLE.png"
clean_png=base/"754F0599_HD_CLEAN_PLATE.png"
allowed_png=base/"754F0599_HD_ALLOWED_TEXT_BBOX_MASK.png"
protected_png=base/"754F0599_HD_PROTECTED_VISIBLE_MASK.png"
validator=repo/"tools/localization/validate_clean_plate.py"

EXPECTED="f21970a3d6d8ae69954d0159524856b5019cd1445daa65c55d85213f73e431f5"
SOURCE_SHA="9314372585b8309f2f8b3e714076ef1ad1999d770422a570398ef20a80ac10a5"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if not candidate.exists() or sha(candidate)!=EXPECTED: raise RuntimeError(("candidate drift",sha(candidate) if candidate.exists() else None))
buf=candidate.read_bytes()
H,W,pitch,depth,mips=struct.unpack_from("<5I",buf,12)
pf=struct.unpack_from("<8I",buf,76)
masks=(pf[4],pf[5],pf[6],pf[7])
if masks==(16711680,65280,255,4278190080): raw_mode="BGRA"
elif masks==(255,65280,16711680,4278190080): raw_mode="RGBA"
else: raise RuntimeError(("masks",pf))
if (W,H)!=(2048,1024): raise RuntimeError((W,H))
source=Image.open(source_png).convert("RGBA")
clean=Image.open(clean_png).convert("RGBA")
allowed=Image.open(allowed_png).convert("L")
protected=Image.open(protected_png).convert("L")
a151_raw=Image.frombytes("RGBA",(W,H),buf[128:],"raw",raw_mode)
a151=a151_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

subprocess.run(["sudo","apt-get","update","-qq"],check=True)
subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-nanum"],check=True)
def font_path():
    for pat in ["NanumGothic:style=Bold","NanumGothic","Nanum Gothic:style=Bold","Nanum Gothic"]:
        try: p=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: p=""
        if p and Path(p).exists() and "Nanum" in Path(p).name: return p
    raise RuntimeError("NanumGothic unavailable")
FONT=font_path()

specs=[
 {"key":"stage_select","source":"stage select","ko":"스테이지 선택","bbox":[6,254,1372,397],"size":[1188,104],"shadow":[5,8]},
 {"key":"showroom","source":"showroom","ko":"쇼룸","bbox":[6,397,956,529],"size":[700,96],"shadow":[5,7]},
 {"key":"single_player","source":"single player","ko":"싱글 플레이","bbox":[2,566,1386,717],"size":[1208,110],"shadow":[5,8]}
]

def fresh_mask(text,target_w,target_h):
    font=ImageFont.truetype(FONT,120)
    t=Image.new("L",(1600,260),0); d=ImageDraw.Draw(t)
    bb=d.textbbox((0,0),text,font=font)
    m=Image.new("L",(bb[2]-bb[0]+20,bb[3]-bb[1]+20),0)
    ImageDraw.Draw(m).text((10-bb[0],10-bb[1]),text,font=font,fill=255)
    gb=m.getbbox(); m=m.crop(gb)
    # Extended techno proportion: fresh Nanum skeleton, deliberately lower and wider.
    m=m.resize((target_w-24,target_h-20),Image.Resampling.LANCZOS)
    # Source-direction readable right lean.
    shear=0.055
    m=m.transform((m.width+8,m.height),Image.Transform.AFFINE,(1,-shear,0,0,1,0),Image.Resampling.BICUBIC)
    gb=m.getbbox()
    return m.crop(gb) if gb else m

def effect(text,target_w,target_h,shadow_xy):
    m=fresh_mask(text,target_w,target_h)
    # Fit centrally inside requested effect footprint.
    if m.width>target_w-14 or m.height>target_h-14:
        sc=min((target_w-14)/m.width,(target_h-14)/m.height)
        m=m.resize((round(m.width*sc),round(m.height*sc)),Image.Resampling.LANCZOS)
    edge=m.filter(ImageFilter.MaxFilter(5))
    layer=Image.new("RGBA",(target_w,target_h),(0,0,0,0))
    ox=(target_w-m.width)//2; oy=(target_h-m.height)//2-2
    sx,sy=ox+shadow_xy[0],oy+shadow_xy[1]
    sh=Image.new("RGBA",layer.size,(0,0,0,0)); sh.paste((8,8,8,245),(sx,sy,sx+m.width,sy+m.height),edge)
    layer=Image.alpha_composite(layer,sh)
    ol=Image.new("RGBA",layer.size,(0,0,0,0)); ol.paste((18,18,18,255),(ox,oy,ox+m.width,oy+m.height),edge)
    layer=Image.alpha_composite(layer,ol)
    grad=Image.new("RGBA",(m.width,m.height),(0,0,0,0)); gp=grad.load()
    for y in range(m.height):
        t=y/max(1,m.height-1)
        v=int(250-190*t) if t<0.75 else int(108-58*((t-0.75)/0.25))
        v=max(42,min(250,v))
        for x in range(m.width): gp[x,y]=(v,v,v,255)
    body=Image.new("RGBA",layer.size,(0,0,0,0)); body.paste(grad,(ox,oy),m)
    layer=Image.alpha_composite(layer,body)
    gb=layer.getchannel("A").getbbox()
    if not gb: raise RuntimeError("empty")
    return layer.crop(gb)

final=clean.copy(); rows=[]
for sp in specs:
    x1,y1,x2,y2=sp["bbox"]; tw,th=sp["size"]
    lay=effect(sp["ko"],tw,th,sp["shadow"])
    tx=x1+4
    ty=y1+(y2-y1-lay.height)//2
    if tx+lay.width>=x2: tx=x2-lay.width-2
    if ty<=y1: ty=y1+2
    if ty+lay.height>=y2: ty=y2-lay.height-2
    final.alpha_composite(lay,(tx,ty))
    loc=[tx,ty,tx+lay.width,ty+lay.height]
    rows.append({"key":sp["key"],"source":sp["source"],"korean":sp["ko"],"original_bbox":sp["bbox"],"localized_bbox":loc,
      "source_size":[x2-x1,y2-y1],"localized_size":[lay.width,lay.height],
      "delta_left":loc[0]-x1,"delta_right":x2-loc[2],"delta_top":loc[1]-y1,"delta_bottom":y2-loc[3],
      "containment":"PASS" if loc[0]>=x1 and loc[1]>=y1 and loc[2]<=x2 and loc[3]<=y2 else "FAIL",
      "size_ceiling":"PASS" if lay.width<=x2-x1 and lay.height<=y2-y1 else "FAIL",
      "positive_margin":"PASS" if loc[0]>x1 and loc[1]>y1 and loc[2]<x2 and loc[3]<y2 else "FAIL",
      "style":"NanumGothic Bold fresh glyph skeleton; extended low-profile techno transform; metallic grayscale; right lean; dark lower extrusion"})

raw=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
new=buf[:128]+raw.tobytes("raw",raw_mode)
candidate.write_bytes(new); cand=sha(candidate)
decraw=Image.frombytes("RGBA",(W,H),new[128:],"raw",raw_mode)
dec=decraw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox() is not None: raise RuntimeError("roundtrip")
fp=out/"754F0599_HD_FINAL_DECODED_READABLE.png"; dec.save(fp)
source.save(out/"754F0599_HD_SOURCE_READABLE.png"); clean.save(out/"754F0599_HD_CLEAN_PLATE.png")
subprocess.run(["python3",str(validator),str(source_png),str(fp),str(allowed_png),"--protected-mask",str(protected_png),"--report",str(out/"A153_FINAL_MASK_VALIDATION.json")],check=True)
v=json.loads((out/"A153_FINAL_MASK_VALIDATION.json").read_text())

def count(m): return sum(m.histogram()[1:])
def ch(a,b):
    d=ImageChops.difference(a,b); bs=d.split(); m=bs[0]
    for z in bs[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda q:255 if q else 0)
dm=ch(source,dec)
outside=count(ImageChops.multiply(dm,ImageOps.invert(allowed)))
ad=ImageChops.difference(source.getchannel("A"),dec.getchannel("A")).point(lambda q:255 if q else 0)
alpha_out=count(ImageChops.multiply(ad,ImageOps.invert(allowed)))
prot=count(ImageChops.multiply(dm,protected))

def gray(im):
    bg=Image.new("RGBA",im.size,(96,96,96,255)); bg.alpha_composite(im); return bg.convert("RGB")
contacts=[]; lab=ImageFont.truetype(FONT,18)
for r in rows:
    x1,y1,x2,y2=r["original_bbox"]; box=(max(0,x1-8),max(0,y1-8),min(W,x2+8),min(H,y2+8))
    parts=[gray(source.crop(box)),gray(a151.crop(box)),gray(dec.crop(box))]
    parts=[p.resize((max(1,p.width//2),max(1,p.height//2)),Image.Resampling.LANCZOS) for p in parts]
    rr=Image.new("RGB",(sum(p.width for p in parts)+12,max(p.height for p in parts)+24),(230,230,230))
    xx=0
    for p in parts: rr.paste(p,(xx,24)); xx+=p.width+6
    ImageDraw.Draw(rr).text((3,2),r["key"]+" SOURCE | A151 rejected | A153",font=lab,fill=(0,0,0))
    contacts.append(rr)
cw=max(p.width for p in contacts); chh=sum(p.height for p in contacts)+6*(len(contacts)-1)
sheet=Image.new("RGB",(cw,chh),(235,235,235)); yy=0
for p in contacts: sheet.paste(p,(0,yy)); yy+=p.height+6
sheet.save(out/"A153_ROW_CONTACT.jpg",quality=95)

full=Image.new("RGB",(W,H*3),(80,80,80))
full.paste(gray(source),(0,0)); full.paste(gray(a151),(0,H)); full.paste(gray(dec),(0,H*2))
full.thumbnail((1600,1800),Image.Resampling.LANCZOS); full.save(out/"A153_SOURCE_A151_FINAL.jpg",quality=95)
rawcmp=Image.new("RGB",(W*3,H),(80,80,80))
rawcmp.paste(gray(source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)),(0,0)); rawcmp.paste(gray(a151_raw),(W,0)); rawcmp.paste(gray(decraw),(W*2,0))
rawcmp.thumbnail((1800,500),Image.Resampling.LANCZOS); rawcmp.save(out/"A153_SOURCE_A151_FINAL_RAW.jpg",quality=95)

ok=(v.get("status")=="PASS" and all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and r["positive_margin"]=="PASS" for r in rows)
    and outside==0 and alpha_out==0 and prot==0)
report={"schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),"queue_index":175,"asset":asset_rel,
 "trigger":"C227R_REWORK_REQUIRED_SOURCE_TYPOGRAPHY_FAMILY_MISMATCH","source_sha256":SOURCE_SHA,
 "prior_candidate_sha256":EXPECTED,"candidate_sha256":cand,
 "rework":"Replace generic Noto skeleton with fresh NanumGothic Bold skeleton, then apply low-profile extended techno proportions while preserving A151 width hierarchy, right lean and metallic effects.",
 "structure":{"dimensions":[W,H],"raw_mode":raw_mode,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "rows":rows,"final_mask_validator":v,
 "machine":{"outside":outside,"alpha_outside":alpha_out,"protected_changed":prot},
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A153_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if ok else "A153_WORKER_REWORK_REQUIRED",
 "no_vr_ffb_dx11_dxvk_work":True}
(out/"A153_754F0599_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"754F0599","queue_index":175,"prior_candidate_sha256":EXPECTED,"candidate_sha256":cand,
 "bbox_size_positive_margin":"3/3 PASS" if ok else "FAIL","outside":outside,"alpha_outside":alpha_out,"protected_changed":prot,
 "worker_status":report["status"],"runtime_validation":"UNTESTED","report":"localization/graphics/role_A/20261007-A-REWORK153-754F0599/A153_754F0599_REPORT.json"}
(worker_out/"A153_754F0599.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not ok: raise SystemExit(2)
