#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd()
run="20261006-A-WORKSTEAL120-DIAG-33491F83"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_loading_cvt_Exst/33491F83_512x256.dds"
SOURCE_SHA="796531b06a159745d799f66f1476b9f78c5a14fd670468f58ce5404e6ced0551"
p=Path("/tmp/A120D.dds"); urllib.request.urlretrieve(url,p)
raw=p.read_bytes()
if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA: raise RuntimeError("source drift")
im=Image.open(p).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
a=np.asarray(im,dtype=np.uint8)
specs=[
 ("diverge","yellow",[430,0,820,120]),
 ("left","green",[290,110,570,235]),
 ("right","red",[680,110,995,235]),
 ("easy_main","green",[80,220,430,385]),
 ("hard_main","red",[790,220,1170,385]),
 ("hard_arrow","red",[1320,0,1690,125]),
 ("easy_arrow","green",[1320,125,1690,255]),
 ("hard_alone","red",[1690,0,2040,125]),
 ("easy_alone","green",[1690,125,2040,255])
]
def seed(arr,fam):
    r=arr[:,:,0].astype(np.int16);g=arr[:,:,1].astype(np.int16);b=arr[:,:,2].astype(np.int16);al=arr[:,:,3]>8
    if fam=="green": return al&(g>110)&(g>r+35)&(g>b+20)
    if fam=="red": return al&(r>125)&(r>g+45)&(r>b+25)
    return al&(r>155)&(g>145)&(b<120)&(r>g-45)

records=[]
sheet=Image.new("RGB",(2048,1024),"black")
for name,fam,win in specs:
    x0,y0,x1,y1=win; sub=a[y0:y1,x0:x1,:]
    s=seed(sub,fam)
    lab,n=ndimage.label(s,structure=np.ones((3,3),dtype=np.uint8))
    comps=[]
    for k in range(1,n+1):
        m=lab==k; area=int(m.sum())
        if area<4: continue
        ys,xs=np.nonzero(m)
        bb=[x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max()+1),y0+int(ys.max()+1)]
        comps.append({"id":k,"area":area,"bbox":bb,"centroid":[x0+float(xs.mean()),y0+float(ys.mean())]})
    comps.sort(key=lambda x:x["area"],reverse=True)
    records.append({"name":name,"family":fam,"window":win,"components":comps[:40]})
    # show component boxes with id for controller diagnosis
    vis=im.convert("RGB")
    d=ImageDraw.Draw(vis)
    d.rectangle(win,outline="magenta",width=2)
    for comp in comps[:20]:
        bb=comp["bbox"]; d.rectangle(bb,outline="cyan",width=2)
        d.text((bb[0],max(0,bb[1]-12)),f'{name}:{comp["id"]}/{comp["area"]}',fill="black",stroke_width=2,stroke_fill="white")
    # composite only corresponding region
    sheet.paste(vis.crop(win),(x0,y0))
sheet.save(out/"A120D_FILL_COMPONENTS.jpg",quality=96)
report={
 "schema_version":1,"role":"A","run":run,"work_stolen_from_lane":"B","queue_index":62,
 "source_sha256":SOURCE_SHA,"purpose":"diagnose fill-seed connected components after A120 clean-plate visual rejection; no candidate mutation",
 "records":records,"candidate_written":False,"runtime_validation":"UNTESTED",
 "status":"A120D_COMPONENT_DIAGNOSTIC_READY","no_vr_ffb_dx11_dxvk_work":True
}
rp=out/"A120D_COMPONENT_DIAGNOSTIC.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A120D_33491F83.json").write_text(json.dumps({"role":"A","run":run,"queue_index":62,"report":str(rp.relative_to(repo)),"status":"DIAGNOSTIC_READY_NO_CANDIDATE"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(records,ensure_ascii=False),flush=True)
