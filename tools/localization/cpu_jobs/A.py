#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")
repo=Path.cwd(); run="20261006-A-PROBE109-ZOOM155157165"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
items=[
 (155,"spr_sprani_sumo_fe_cvt_Exst","4D49CA85_512x256.dds"),
 (157,"spr_sprani_sumo_fe_cvt_Exst","4DF4D7CD_512x512.dds"),
 (165,"spr_sprani_sumo_fe_cvt_Exst","5C98F2_512x512.dds"),
]
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release"
results=[]
for idx,folder,asset in items:
 p=Path("/tmp")/asset; url=f"{BASE}/{folder}/{asset}"; urllib.request.urlretrieve(url,p); raw=p.read_bytes()
 if raw[:4]!=b"DDS ": raise RuntimeError(("not dds",asset))
 h=struct.unpack_from("<I",raw,12)[0]; w=struct.unpack_from("<I",raw,16)[0]; mips=struct.unpack_from("<I",raw,28)[0]
 fourcc=raw[84:88]; bpp=struct.unpack_from("<I",raw,88)[0]; masks=struct.unpack_from("<IIII",raw,92)
 im=Image.open(p).convert("RGBA")
 if im.size!=(w,h): raise RuntimeError(("size mismatch",asset,im.size,(w,h)))
 readable=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM); stem=asset.split("_")[0]
 readable.save(out/f"A109_{stem}_READABLE.png"); im.save(out/f"A109_{stem}_RAW.png")
 proof=Image.new("RGBA",readable.size,(235,235,235,255)); proof.alpha_composite(readable); pr=proof.convert("RGB"); pr.thumbnail((2200,1800),Image.Resampling.LANCZOS); pr.save(out/f"A109_{stem}_READABLE_PROOF.jpg",quality=92,optimize=True)
 alpha=np.asarray(readable.getchannel("A")); vis=alpha>8; lab,n=ndimage.label(vis); objs=ndimage.find_objects(lab); comps=[]
 for i,sl in enumerate(objs,1):
  if sl is None: continue
  y,x=sl; area=int((lab[sl]==i).sum())
  if area<8: continue
  comps.append({"bbox":[int(x.start),int(y.start),int(x.stop),int(y.stop)],"area":area})
 comps=sorted(comps,key=lambda z:z["area"],reverse=True)
 results.append({"queue_index":idx,"folder":folder,"asset":asset,"source_url":url,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"width":w,"height":h,"mipmaps":mips,"fourcc":fourcc.decode("latin1"),"bpp":bpp,"masks":[hex(x) for x in masks],"component_count":len(comps),"components":comps[:1000]})
report={"schema_version":1,"role":"A","run":run,"items":results,"status":"A109_SOURCE_PROBE_BATCH_COMPLETE_CONTROLLER_CLASSIFICATION_REQUIRED"}
(out/"A109_ZOOM155157165_PROBE.json").write_text(json.dumps(report,indent=2)+"\n")
(wr/"A109_ZOOM155157165_PROBE.json").write_text(json.dumps({"run":run,"indices":[155,157,165],"items":[{"queue_index":x["queue_index"],"asset":x["asset"],"sha256":x["sha256"],"width":x["width"],"height":x["height"]} for x in results],"report":str((out/"A109_ZOOM155157165_PROBE.json").relative_to(repo)),"status":report["status"]},indent=2)+"\n")
print(json.dumps({"run":run,"items":[(x["queue_index"],x["asset"],x["width"],x["height"],x["fourcc"],x["sha256"],x["component_count"]) for x in results]},ensure_ascii=False),flush=True)
