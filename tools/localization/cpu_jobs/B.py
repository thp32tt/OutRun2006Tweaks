#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd(); run="20261006-B-PROBE177-ZOOM62136144"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
items=[
 (62,"spr_sprani_loading_cvt_Exst","33491F83_512x256.dds"),
 (136,"spr_sprani_sumo_fe_cvt_Exst","2B785F6A_512x512.dds"),
 (144,"spr_sprani_sumo_fe_cvt_Exst","35361191_512x512.dds"),
]
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/"
results=[]
for idx,folder,asset in items:
    url=base+folder+"/"+asset
    p=Path("/tmp")/asset; urllib.request.urlretrieve(url,p)
    raw=p.read_bytes()
    if raw[:4]!=b"DDS ": raise RuntimeError(("not dds",asset))
    h=struct.unpack_from("<I",raw,12)[0]; w=struct.unpack_from("<I",raw,16)[0]
    pitch=struct.unpack_from("<I",raw,20)[0]; mips=struct.unpack_from("<I",raw,28)[0]
    fourcc=raw[84:88]; bpp=struct.unpack_from("<I",raw,88)[0]; masks=struct.unpack_from("<IIII",raw,92)
    im=Image.open(p).convert("RGBA")
    if im.size!=(w,h): raise RuntimeError(("PIL size mismatch",asset,im.size,(w,h)))
    readable=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    stem=asset.split("_")[0]
    readable.save(out/f"B177_{stem}_READABLE.png"); im.save(out/f"B177_{stem}_RAW.png")
    alpha=np.asarray(readable.getchannel("A")); visible=alpha>8
    lab,n=ndimage.label(visible); objs=ndimage.find_objects(lab); comps=[]
    for i,sl in enumerate(objs,1):
        if sl is None: continue
        y,x=sl; area=int((lab[sl]==i).sum())
        if area<16: continue
        comps.append({"bbox":[int(x.start),int(y.start),int(x.stop),int(y.stop)],"area":area})
    comps.sort(key=lambda z:z["area"],reverse=True)
    ov=readable.copy(); d=ImageDraw.Draw(ov)
    for c in comps[:500]:
        x0,y0,x1,y1=c["bbox"]; d.rectangle((x0,y0,x1-1,y1-1),outline=(255,0,255,255),width=max(1,w//2048))
    ov.save(out/f"B177_{stem}_COMPONENTS.png")
    proof=Image.new("RGBA",readable.size,(235,235,235,255)); proof.alpha_composite(readable)
    proof=proof.convert("RGB"); proof.thumbnail((2200,1600),Image.Resampling.LANCZOS)
    proof.save(out/f"B177_{stem}_READABLE_PROOF.jpg",quality=96)
    results.append({
      "queue_index":idx,"folder":folder,"asset":asset,"source_url":url,
      "width":w,"height":h,"mips":mips,"fourcc":fourcc.decode("latin1"),"bpp":bpp,
      "masks":[hex(x) for x in masks],"pitch_or_linear":pitch,
      "sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),
      "component_count":len(comps),"components":comps[:800]
    })
report={"schema_version":1,"role":"B","run":run,"items":results,
        "status":"B177_SOURCE_PROBE_BATCH_COMPLETE_CONTROLLER_CLASSIFICATION_REQUIRED",
        "no_vr_ffb_dx11_dxvk_work":True}
(out/"B177_ZOOM62136144_PROBE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B177_ZOOM62136144_PROBE.json").write_text(json.dumps({
  "role":"B","run":run,"indices":[62,136,144],
  "items":[{"queue_index":x["queue_index"],"asset":x["asset"],"sha256":x["sha256"],"width":x["width"],"height":x["height"]} for x in results],
  "report":str((out/"B177_ZOOM62136144_PROBE.json").relative_to(repo)),
  "status":report["status"]},ensure_ascii=False,indent=2)+"\n")
print("B177_PROBE",[(x["queue_index"],x["asset"],x["width"],x["height"],x["mips"],x["fourcc"],x["sha256"],x["component_count"]) for x in results])
