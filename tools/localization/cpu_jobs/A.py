#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd(); run="20261006-A-PROBE99-8B52FEEC"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="8B52FEEC_1024x512.dds"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_CLAR_RANK_Exst/"+asset
p=Path("/tmp")/asset; urllib.request.urlretrieve(url,p)
raw=p.read_bytes()
if raw[:4]!=b"DDS ": raise RuntimeError("not dds")
h=struct.unpack_from("<I",raw,12)[0]; w=struct.unpack_from("<I",raw,16)[0]
pitch_or_linear=struct.unpack_from("<I",raw,20)[0]; mips=struct.unpack_from("<I",raw,28)[0]
fourcc=raw[84:88]; bpp=struct.unpack_from("<I",raw,88)[0]; masks=struct.unpack_from("<IIII",raw,92)
im=Image.open(p).convert("RGBA")
if im.size!=(w,h): raise RuntimeError(("PIL size mismatch",im.size,(w,h)))
readable=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
readable.save(out/"A99_SOURCE_READABLE.png")
im.save(out/"A99_SOURCE_RAW.png")
alpha=np.asarray(readable.getchannel("A"))
visible=alpha>8
lab,n=ndimage.label(visible)
objs=ndimage.find_objects(lab); comps=[]
for i,sl in enumerate(objs,1):
    if sl is None: continue
    y,x=sl; area=int((lab[sl]==i).sum())
    if area<16: continue
    comps.append({"bbox":[int(x.start),int(y.start),int(x.stop),int(y.stop)],"area":area})
comps=sorted(comps,key=lambda z:z["area"],reverse=True)
ov=readable.copy(); d=ImageDraw.Draw(ov)
for c in comps[:240]:
    x0,y0,x1,y1=c["bbox"]; d.rectangle((x0,y0,x1-1,y1-1),outline=(255,0,255,255),width=max(1,w//2048))
ov.save(out/"A99_SOURCE_COMPONENTS.png")
meta={"width":w,"height":h,"mips":mips,"fourcc":fourcc.decode("latin1"),"bpp":bpp,
      "masks":[hex(x) for x in masks],"pitch_or_linear":pitch_or_linear,
      "sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"pil_mode":"RGBA"}
report={"run":run,"queue_index":27,"asset":"textures/load/spr_sprani_CLAR_RANK_Exst/"+asset,
        "source_url":url,"source":meta,"component_count":len(comps),"components":comps[:600],
        "status":"A99_SOURCE_PROBE_COMPLETE_CONTROLLER_CLASSIFICATION_REQUIRED"}
(out/"A99_8B52FEEC_PROBE.json").write_text(json.dumps(report,indent=2)+"\n")
(wr/"A99_8B52FEEC_PROBE.json").write_text(json.dumps({
    "run":run,"queue_index":27,"source_sha256":meta["sha256"],"source_meta":meta,
    "report":str((out/"A99_8B52FEEC_PROBE.json").relative_to(repo)),
    "status":report["status"]},indent=2)+"\n")
print("A99_PROBE",w,h,mips,fourcc,bpp,meta["sha256"],len(comps))
