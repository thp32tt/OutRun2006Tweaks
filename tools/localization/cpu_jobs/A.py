#!/usr/bin/env python3
import json, os, urllib.parse, urllib.request, subprocess
from pathlib import Path

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-WORKSTEAL121-33491F83-PSD"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

subprocess.run(["python","-m","pip","install","--disable-pip-version-check","-q","psd-tools==1.10.8"],check=True)
from psd_tools import PSDImage

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
psd_rel="PSDs, XCFs, SVGs, and other Working Source Assets/OutRun2SP Mode UI/spr_sprani_loading_cvt_Exst/33491F83_512x256.psd"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit+"/"+urllib.parse.quote(psd_rel,safe="/")
psdp=Path("/tmp/33491F83_512x256.psd")
urllib.request.urlretrieve(url,psdp)

psd=PSDImage.open(psdp)
records=[]
def walk(layers,depth=0,parent=""):
    for i,layer in enumerate(layers):
        name=layer.name
        path=(parent+"/"+name).strip("/")
        rec={
          "depth":depth,"index":i,"name":name,"path":path,
          "kind":getattr(layer,"kind",None),
          "visible":bool(layer.is_visible()),
          "bbox":[int(layer.left),int(layer.top),int(layer.right),int(layer.bottom)],
          "size":[int(layer.width),int(layer.height)],
          "opacity":int(layer.opacity),
          "blend_mode":str(layer.blend_mode),
          "is_group":bool(layer.is_group())
        }
        # Text layers expose engine_dict/text.
        if getattr(layer,"kind",None)=="type":
            try: rec["text"]=layer.text
            except Exception as e: rec["text_error"]=repr(e)
        records.append(rec)
        if layer.is_group():
            walk(layer,depth+1,path)

walk(psd)
report={
 "schema_version":1,"role":"A","run":run,"queue_index":62,
 "asset":"textures/load/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds",
 "work_stolen_from_lane":"B",
 "psd_source":{"repo":"Sonic-TV/OR2006Sprites","commit":commit,"path":psd_rel,"url":url,"bytes":psdp.stat().st_size},
 "psd_canvas":[psd.width,psd.height],
 "layers":records,
 "text_layers":[r for r in records if r.get("kind")=="type"],
 "status":"A121_PSD_LAYER_INVENTORY_READY",
 "runtime_validation":"UNTESTED","no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"A121_33491F83_PSD_LAYERS.json"
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A121_33491F83_PSD.json").write_text(json.dumps({
 "role":"A","run":run,"queue_index":62,"report":str(rp.relative_to(repo)),
 "psd_canvas":[psd.width,psd.height],"layer_count":len(records),
 "text_layer_count":sum(1 for r in records if r.get("kind")=="type"),
 "status":"PSD_LAYER_INVENTORY_READY"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"canvas":[psd.width,psd.height],"layers":len(records),
 "text_layers":[{"path":r["path"],"text":r.get("text"),"bbox":r["bbox"],"visible":r["visible"]} for r in records if r.get("kind")=="type"]},ensure_ascii=False),flush=True)
