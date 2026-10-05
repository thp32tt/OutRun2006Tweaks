#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-PROBE92-PENDING3"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
items=[
 (227,"E596B7AC_512x512.dds"),
 (231,"EBE401C8_512x256.dds"),
 (237,"FF514CEB_512x512.dds"),
]
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/"
allr=[]
for idx,asset in items:
    p=Path("/tmp")/asset
    urllib.request.urlretrieve(base+asset,p)
    raw=p.read_bytes()
    if raw[:4]!=b"DDS ": raise RuntimeError(("not dds",asset))
    h=struct.unpack_from("<I",raw,12)[0]; w=struct.unpack_from("<I",raw,16)[0]
    mips=struct.unpack_from("<I",raw,28)[0]; fourcc=raw[84:88]; bpp=struct.unpack_from("<I",raw,88)[0]
    masks=struct.unpack_from("<IIII",raw,92)
    if bpp==32 and fourcc==b"\0\0\0\0" and len(raw)>=128+w*h*4:
        if masks==(0xff,0xff00,0xff0000,0xff000000): mode="RGBA"
        elif masks==(0xff0000,0xff00,0xff,0xff000000): mode="BGRA"
        else: raise RuntimeError(("unknown masks",asset,masks))
        raw_im=Image.frombytes("RGBA",(w,h),raw[128:128+w*h*4],"raw",mode)
    else:
        raw_im=Image.open(p).convert("RGBA"); mode="PIL"
    read=raw_im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    stem=asset.split("_")[0]
    read.save(out/f"A92_{stem}_READABLE.png")
    raw_im.save(out/f"A92_{stem}_RAW.png")
    a=np.asarray(read.getchannel("A")); mask=a>8
    lab,n=ndimage.label(mask); objs=ndimage.find_objects(lab)
    comps=[]
    for i,sl in enumerate(objs,1):
        if sl is None: continue
        y,x=sl; area=int((lab[sl]==i).sum())
        if area<20: continue
        comps.append({"bbox":[int(x.start),int(y.start),int(x.stop),int(y.stop)],"area":area})
    comps=sorted(comps,key=lambda z:z["area"],reverse=True)[:400]
    ov=read.copy(); d=ImageDraw.Draw(ov)
    for c in comps[:120]:
        x0,y0,x1,y1=c["bbox"]; d.rectangle((x0,y0,x1-1,y1-1),outline=(255,0,255,255),width=max(1,w//1024))
    ov.save(out/f"A92_{stem}_COMPONENTS.png")
    meta={"queue_index":idx,"asset":asset,"width":w,"height":h,"mips":mips,"fourcc":fourcc.decode("latin1"),
      "bpp":bpp,"masks":[hex(x) for x in masks],"decode_mode":mode,"sha256":hashlib.sha256(raw).hexdigest(),
      "component_count":len(comps),"components":comps}
    allr.append(meta)
report={"run":run,"items":allr,"status":"A92_SOURCE_PROBE_COMPLETE_RENDER_DECISION_PENDING_CONTROLLER"}
(out/"A92_PENDING3_PROBE.json").write_text(json.dumps(report,indent=2)+"\n")
(wr/"A92_PENDING3_PROBE.json").write_text(json.dumps({
  "run":run,"indices":[227,231,237],"status":report["status"],
  "report":str((out/"A92_PENDING3_PROBE.json").relative_to(repo))
},indent=2)+"\n")
print("A92_DONE",[(x["queue_index"],x["width"],x["height"],x["sha256"]) for x in allr])
