#!/usr/bin/env python3
import json,os,subprocess,urllib.parse,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")
subprocess.run(["python","-m","pip","install","--disable-pip-version-check","-q","psd-tools==1.10.8"],check=True)
from psd_tools import PSDImage

repo=Path.cwd();run="20261006-A-WORKSTEAL124-33491F83-PSD-LAYERS"
out=repo/"localization/graphics/role_A"/run;out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results";wr.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
rel="PSDs, XCFs, SVGs, and other Working Source Assets/OutRun2SP Mode UI/spr_sprani_loading_cvt_Exst/33491F83_512x256.psd"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit+"/"+urllib.parse.quote(rel,safe="/")
p=Path("/tmp/A124.psd");urllib.request.urlretrieve(url,p);psd=PSDImage.open(p)
want={
 "basic":"objects/**Put any graphic and text art inside this folder**/Manual Work/Bunki - Remastered/Bunki graphic/Bunki - Basic Fix",
 "erase":"objects/**Put any graphic and text art inside this folder**/Manual Work/Bunki - Remastered/Bunki graphic/Erase AI Typography/Erase Left and Right and Diverge",
 "layer43":"objects/**Put any graphic and text art inside this folder**/Manual Work/Bunki - Remastered/Bunki graphic/Erase AI Typography/4xHDcube3/Layer 43",
 "paint":"objects/**Put any graphic and text art inside this folder**/Manual Work/Bunki - Remastered/Bunki graphic/Paintover"
}
found={}
def walk(g,parent=""):
    for l in g:
        path=(parent+"/"+l.name).strip("/")
        for k,v in want.items():
            if path==v: found[k]=l
        if l.is_group():walk(l,path)
walk(psd)
if set(found)!=set(want):raise RuntimeError(("missing layers",set(want)-set(found)))
recs=[]
cards=[]
for k,l in found.items():
    if l.is_group(): im=l.composite(force=True,apply_icc=False)
    else: im=l.topil()
    if im is None:raise RuntimeError(("no image",k))
    im=im.convert("RGBA")
    canvas=Image.new("RGBA",(2048,1024),(0,0,0,0));canvas.alpha_composite(im,(int(l.left),int(l.top)))
    canvas.save(out/f"A124_{k}.png")
    bg=Image.new("RGBA",canvas.size,(235,235,235,255));bg.alpha_composite(canvas)
    v=bg.convert("RGB").crop((0,0,1200,820));v.thumbnail((1200,820),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+30),"white");c.paste(v,(0,30));ImageDraw.Draw(c).text((6,7),k,fill="black");cards.append(c)
    recs.append({"key":k,"path":want[k],"kind":l.kind,"bbox":[l.left,l.top,l.right,l.bottom],"image_size":im.size})
mw=max(c.width for c in cards);mh=sum(c.height+6 for c in cards)
s=Image.new("RGB",(mw,mh),"white");y=0
for c in cards:s.paste(c,(0,y));y+=c.height+6
s.thumbnail((1700,3600),Image.Resampling.LANCZOS);s.save(out/"A124_PSD_LAYER_CONTACT.jpg",quality=97)
report={"schema_version":1,"role":"A","run":run,"queue_index":62,"layers":recs,
"status":"A124_PSD_CLEAN_COMPONENTS_READY","runtime_validation":"UNTESTED","no_vr_ffb_dx11_dxvk_work":True}
rp=out/"A124_33491F83_LAYER_REPORT.json";rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A124_33491F83_LAYERS.json").write_text(json.dumps({"role":"A","run":run,"queue_index":62,"report":str(rp.relative_to(repo)),"status":"PSD_CLEAN_COMPONENTS_READY"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False),flush=True)
