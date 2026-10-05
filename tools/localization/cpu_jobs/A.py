#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261005-A-PRODUCTION37-PREFLIGHT"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
work=Path("/tmp/outrun_A37"); work.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
SOURCE_BLOB_SHA1="5263429e689933e1ebb5923773e5adc1a2e2b7e5"
ATLAS_BLOB_SHA1="00638ecb71316b9cf2a9d171053698c2296cf061"
source=work/"25F697C6_HD.dds"; atlasp=work/"4x_25F697C6_512x512_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/25F697C6_512x512.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_25F697C6_512x512_atlas.json",atlasp)

def blobsha(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
sb=source.read_bytes(); ab=atlasp.read_bytes()
if blobsha(sb)!=SOURCE_BLOB_SHA1: raise RuntimeError(("source drift",blobsha(sb)))
if blobsha(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError(("atlas drift",blobsha(ab)))
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76)
rgbm=(pf[4],pf[5],pf[6])
if pf[3]!=32: raise RuntimeError(("bpp",pf))
if rgbm==(0xff,0xff00,0xff0000): rawmode="RGBA"
elif rgbm==(0xff0000,0xff00,0xff): rawmode="BGRA"
else: raise RuntimeError(("masks",rgbm))
if (W,H)!=(2048,2048) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,len(sb)))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",rawmode)
src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
atlas=json.loads(ab.decode("utf-8")); regs=sorted(atlas["regions"],key=lambda r:int(r["idx"]))
if len(regs)!=24: raise RuntimeError(("regions",len(regs)))

def flatten(im):
    z=Image.new("RGBA",im.size,(100,100,100,255)); z.alpha_composite(im); return z.convert("RGB")
rows=[]; cards=[]
for r in regs:
    idx=int(r["idx"]); x,y,w,h=map(int,r["rect"]); crop=src.crop((x,y,x+w,y+h))
    a=np.asarray(crop); al=a[:,:,3]; vis=np.argwhere(al>0)
    bb=None
    if len(vis):
      y0,x0=vis.min(axis=0); y1,x1=vis.max(axis=0)+1; bb=[int(x0),int(y0),int(x1),int(y1)]
    rows.append({"idx":idx,"name":r.get("name"),"rect":[x,y,w,h],"alpha_bbox_local":bb,"visible_pixels":int((al>0).sum()),"opaque_pixels":int((al==255).sum())})
    flat=flatten(crop); sc=min(1.0,760/max(1,w),210/max(1,h))
    if sc<1: flat=flat.resize((max(1,int(w*sc)),max(1,int(h*sc))),Image.Resampling.LANCZOS)
    card=Image.new("RGB",(800,260),(230,230,230)); d=ImageDraw.Draw(card)
    d.text((8,8),f"idx {idx} rect={x},{y},{w},{h} visible={rows[-1]['visible_pixels']}",fill=(0,0,0))
    card.paste(flat,(8,40)); cards.append(card)
sheet=Image.new("RGB",(1600,math.ceil(len(cards)/2)*260),(215,215,215))
for i,c in enumerate(cards): sheet.paste(c,((i%2)*800,(i//2)*260))
sheet.save(out/"A37_25F_ALL_CELLS.jpg",quality=95)
flatten(src).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A37_25F_SOURCE_READABLE.jpg",quality=94)
flatten(raw).resize((1024,1024),Image.Resampling.LANCZOS).save(out/"A37_25F_SOURCE_RAW_MIRROR_Y.jpg",quality=94)
report={"schema_version":1,"role":"A","run":run,"index":133,"asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/25F697C6_512x512.dds",
"readiness":"ONE_STAGE_TO_RENDER","source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":sha256(source)},
"atlas_provenance":{"git_blob_sha1":ATLAS_BLOB_SHA1,"sha256":sha256(atlasp),"regions":len(regs)},
"structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":rawmode,"pitch":pitch,"mipmaps":mips,"raw_orientation":"mirror_y"},
"regions":rows,"reviewed_segments":9,
"policy":"Ferrari/model names protected. Stage names use canonical phonetic Hangul. Factory color names may be transliterated only where the canonical sprite cell positively binds.",
"status":"A37_PREFLIGHT_COMPLETE_CONTINUE_TO_RENDER","runtime_validation":"UNTESTED"}
(out/"A37_25F697C6_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A37_25F697C6_PREFLIGHT.json").write_text(json.dumps({"run":run,"index":133,"asset":"25F697C6","source_sha256":report["source_provenance"]["sha256"],"regions":24,"status":report["status"],"report":"localization/graphics/role_A/20261005-A-PRODUCTION37-PREFLIGHT/A37_25F697C6_PREFLIGHT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"index":133,"regions":24,"status":report["status"]},ensure_ascii=False))
