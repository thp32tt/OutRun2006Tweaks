#!/usr/bin/env python3
import json,os,subprocess,urllib.parse,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")
subprocess.run(["python","-m","pip","install","--disable-pip-version-check","-q","psd-tools==1.10.8"],check=True)
from psd_tools import PSDImage

repo=Path.cwd();run="20261006-A-WORKSTEAL123-33491F83-PSD-BUNKI"
out=repo/"localization/graphics/role_A"/run;out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
psd_rel="PSDs, XCFs, SVGs, and other Working Source Assets/OutRun2SP Mode UI/spr_sprani_loading_cvt_Exst/33491F83_512x256.psd"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit+"/"+urllib.parse.quote(psd_rel,safe="/")
p=Path("/tmp/A123.psd");urllib.request.urlretrieve(url,p)
psd=PSDImage.open(p)
target_path="objects/**Put any graphic and text art inside this folder**/Manual Work/Bunki - Remastered/Bunki graphic"
found=None
def walk(g,parent=""):
    global found
    for l in g:
        path=(parent+"/"+l.name).strip("/")
        if path==target_path: found=l
        if l.is_group():walk(l,path)
walk(psd)
if found is None:raise RuntimeError("Bunki graphic group missing")
im=found.composite(force=True,apply_icc=False)
if im is None:raise RuntimeError("Bunki composite failed")
im=im.convert("RGBA")
canvas=Image.new("RGBA",(psd.width,psd.height),(0,0,0,0))
canvas.alpha_composite(im,(int(found.left),int(found.top)))
arr=np.asarray(canvas)
# Exact five main-label PSD rasterized bboxes from A121.
boxes={
 "diverge":[456,14,755,113],
 "left":[322,161,478,245],
 "right":[682,163,885,257],
 "easy":[142,285,385,375],
 "hard":[808,287,1068,373]
}
stats={}
for k,(x0,y0,x1,y1) in boxes.items():
    a=arr[y0:y1,x0:x1,3]
    stats[k]={"pixels":int(a.size),"opaque_or_visible":int(np.count_nonzero(a>0)),
              "coverage":float(np.count_nonzero(a>0)/a.size)}
canvas.save(out/"A123_BUNKI_GRAPHIC_FULL.png")
# White proof.
bg=Image.new("RGBA",canvas.size,(235,235,235,255));bg.alpha_composite(canvas)
v=bg.convert("RGB").crop((0,0,1200,820));v.thumbnail((1600,1200),Image.Resampling.LANCZOS)
v.save(out/"A123_BUNKI_GRAPHIC_PROOF.jpg",quality=97)
report={"schema_version":1,"role":"A","run":run,"queue_index":62,
 "psd_group_path":target_path,"group_bbox":[found.left,found.top,found.right,found.bottom],
 "main_label_bbox_alpha_coverage":stats,
 "status":"A123_BUNKI_CLEAN_LAYER_PROBE_COMPLETE",
 "runtime_validation":"UNTESTED","no_vr_ffb_dx11_dxvk_work":True}
rp=out/"A123_33491F83_BUNKI_LAYER_REPORT.json";rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A123_33491F83_BUNKI.json").write_text(json.dumps({"role":"A","run":run,"queue_index":62,"report":str(rp.relative_to(repo)),"coverage":stats,"status":"BUNKI_CLEAN_LAYER_PROBE_COMPLETE"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False),flush=True)
