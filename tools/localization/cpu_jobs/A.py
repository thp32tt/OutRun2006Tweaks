#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-PROBE98-4AFC1BED"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="4AFC1BED_512x512.dds"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_CLAR_RANK_Exst/"+asset
p=Path("/tmp")/asset
urllib.request.urlretrieve(url,p)
raw=p.read_bytes()
if raw[:4]!=b"DDS ": raise RuntimeError("not dds")
h=struct.unpack_from("<I",raw,12)[0]; w=struct.unpack_from("<I",raw,16)[0]
mips=struct.unpack_from("<I",raw,28)[0]; fourcc=raw[84:88]; bpp=struct.unpack_from("<I",raw,88)[0]
masks=struct.unpack_from("<IIII",raw,92)
if bpp!=32 or fourcc!=b"\0\0\0\0" or len(raw)<128+w*h*4:
    raise RuntimeError(("unsupported",w,h,mips,fourcc,bpp,len(raw)))
if masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
elif masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
else: raise RuntimeError(("masks",masks))
raw_im=Image.frombytes("RGBA",(w,h),raw[128:128+w*h*4],"raw",mode)
readable=raw_im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
readable.save(out/"A98_SOURCE_READABLE.png")
raw_im.save(out/"A98_SOURCE_RAW.png")

a=np.asarray(readable.getchannel("A"))
mask=a>8
lab,n=ndimage.label(mask)
objs=ndimage.find_objects(lab)
components=[]
for i,sl in enumerate(objs,1):
    if sl is None: continue
    y,x=sl; area=int((lab[sl]==i).sum())
    if area<20: continue
    components.append({"bbox":[int(x.start),int(y.start),int(x.stop),int(y.stop)],"area":area})
components=sorted(components,key=lambda z:z["area"],reverse=True)
ov=readable.copy(); d=ImageDraw.Draw(ov)
for c in components[:160]:
    x0,y0,x1,y1=c["bbox"]; d.rectangle((x0,y0,x1-1,y1-1),outline=(255,0,255,255),width=max(1,w//2048))
ov.save(out/"A98_SOURCE_COMPONENTS.png")

meta={"width":w,"height":h,"mips":mips,"fourcc":fourcc.decode("latin1"),"bpp":bpp,
      "masks":[hex(x) for x in masks],"raw_mode":mode,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}
report={"run":run,"queue_index":25,"asset":"textures/load/spr_sprani_CLAR_RANK_Exst/"+asset,
        "source_url":url,"source":meta,"component_count":len(components),"components":components[:500],
        "status":"A98_SOURCE_PROBE_COMPLETE_CONTROLLER_CLASSIFICATION_REQUIRED"}
(out/"A98_4AFC1BED_PROBE.json").write_text(json.dumps(report,indent=2)+"\n")
(wr/"A98_4AFC1BED_PROBE.json").write_text(json.dumps({
    "run":run,"queue_index":25,"source_sha256":meta["sha256"],"source_meta":meta,
    "report":str((out/"A98_4AFC1BED_PROBE.json").relative_to(repo)),
    "status":report["status"]},indent=2)+"\n")
print("A98_PROBE",w,h,mips,mode,meta["sha256"],len(components))
