#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261005-A-PRODUCTION46-PREFLIGHT"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
work=Path("/tmp/outrun_A46"); work.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="5263429e689933e1ebb5923773e5adc1a2e2b7e5"
ATLAS_BLOB_SHA1="00638ecb71316b9cf2a9d171053698c2296cf061"
SOURCE_SHA256="8b59df1eaccdba160cb321335954890d8c4d7d3e793cf83a554c62b707615b04"
ATLAS_SHA256="7f4fa4543810bc2f1f665f26ba8270573fa0bd7badb0643f3c014398483990fa"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
source=work/"25F697C6_HD.dds"; atlasp=work/"4x_25F697C6_512x512_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/25F697C6_512x512.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_25F697C6_512x512_atlas.json",atlasp)

def blobsha(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
sb=source.read_bytes(); ab=atlasp.read_bytes()
if blobsha(sb)!=SOURCE_BLOB_SHA1 or hashlib.sha256(sb).hexdigest()!=SOURCE_SHA256: raise RuntimeError("source drift")
if blobsha(ab)!=ATLAS_BLOB_SHA1 or hashlib.sha256(ab).hexdigest()!=ATLAS_SHA256: raise RuntimeError("atlas drift")
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(2048,2048,8192,1) or pf[3]!=32: raise RuntimeError((W,H,pitch,mips,pf))
rgbm=(pf[4],pf[5],pf[6])
RAWMODE="BGRA" if rgbm==(0xff0000,0xff00,0xff) else "RGBA" if rgbm==(0xff,0xff00,0xff0000) else None
if RAWMODE!="BGRA": raise RuntimeError(("rawmode",rgbm))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE)
src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
atlas=json.loads(ab.decode("utf-8")); regs={int(r["idx"]):r for r in atlas["regions"]}
if len(regs)!=24: raise RuntimeError(("region count",len(regs)))

def flatten(im):
    z=Image.new("RGBA",im.size,(72,72,72,255)); z.alpha_composite(im); return z.convert("RGB")

cards=[]
for idx in sorted(regs):
    r=regs[idx]; x,y,w,h=map(int,r["rect"]); q=flatten(src.crop((x,y,x+w,y+h)))
    scale=min(1.0,540/max(1,q.width),150/max(1,q.height))
    if scale<1: q=q.resize((max(1,int(q.width*scale)),max(1,int(q.height*scale))),Image.Resampling.LANCZOS)
    card=Image.new("RGB",(580,190),(205,205,205)); d=ImageDraw.Draw(card)
    d.text((6,5),f"idx {idx} {r.get('name','')} rect={x},{y},{w},{h}",fill=(0,0,0))
    card.paste(q,((580-q.width)//2,30+(150-q.height)//2)); cards.append(card)
cols=2; rows=(len(cards)+1)//2
sheet=Image.new("RGB",(cols*580,rows*190),(185,185,185))
for i,c in enumerate(cards): sheet.paste(c,((i%cols)*580,(i//cols)*190))
sheet.save(out/"A46_25F697C6_ALL_REGIONS.jpg",quality=94)

report={"schema_version":1,"role":"A","run":run,"index":133,"asset":"25F697C6",
 "readiness":"ONE_STAGE_TO_RENDER_BINDING_VISUALIZED",
 "source":{"commit":COMMIT,"blob_sha1":SOURCE_BLOB_SHA1,"sha256":SOURCE_SHA256},
 "atlas":{"blob_sha1":ATLAS_BLOB_SHA1,"sha256":ATLAS_SHA256,"regions":24},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":RAWMODE,"mipmaps":mips,"orientation":"mirror_y"},
 "required_semantics":["ALPINE","ANCIENT RUINS","BLU MIRABEAU","ARGENTO NURBURGRING","BIANCO AVUS","NERO","ROSSO SCUDERIA","GRIGIO ALLOY","GIALLO MODENA"],
 "protected":"Ferrari/model names and non-target artwork",
 "runtime_validation":"UNTESTED","status":"A46_BINDING_CONTACT_READY_CONTINUE_SAME_INVOCATION"}
(out/"A46_25F697C6_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A46_25F697C6.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False,indent=2))
