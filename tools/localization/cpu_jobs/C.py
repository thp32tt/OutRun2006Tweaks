#!/usr/bin/env python3
import hashlib,json,os,struct,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")
repo=Path.cwd(); run="20261005-C137-1F5FE6E9-DIAG"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/1F5FE6E9_1024x512.dds"
srczip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
with zipfile.ZipFile(srczip) as z: sb=z.read(asset)
if hashlib.sha256(sb).hexdigest()!="3656adbd699b7852cb5fcf4bb01fc4f1f65bbd9d7d39e12e7a1c2ac5a49fef1d":
    raise RuntimeError("source sha mismatch")
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
a=np.asarray(src,dtype=np.uint8)
hints=[
 ("REQUEST","요청",[649,148,756,171]),
 ("SPECIAL REQUEST 1","스페셜 요청 1",[649,172,873,195]),
 ("SPECIAL REQUEST 2","스페셜 요청 2",[649,196,877,219]),
 ("SPECIAL REQUEST 3","스페셜 요청 3",[649,219,877,243]),
]
rows=[]
vis=src.copy(); dvis=ImageDraw.Draw(vis)
for n,(en,ko,box) in enumerate(hints,1):
    x0,y0,x1,y1=box
    roi=a[y0:y1,x0:x1].astype(np.float32)
    # Use only the interior to estimate the row-panel background; this excludes
    # the known panel boundary at x<649 that broke B51.
    border=np.concatenate([
        roi[:2].reshape(-1,4),roi[-2:].reshape(-1,4),
        roi[:, :2].reshape(-1,4),roi[:, -2:].reshape(-1,4)
    ],axis=0)
    bg=np.median(border,axis=0)
    dist=np.sqrt(np.sum((roi[:,:,:3]-bg[:3])**2,axis=2))
    trials={}
    for th in (4,6,8,10,12,16,20):
        m=(dist>th)
        # Remove components that are horizontal/vertical panel lines.
        lab,num=ndimage.label(m,np.ones((3,3),dtype=np.uint8))
        comps=[]
        kept=np.zeros_like(m)
        for i in range(1,num+1):
            yy,xx=np.nonzero(lab==i)
            if len(xx)<2: continue
            bw=int(xx.max()-xx.min()+1); bh=int(yy.max()-yy.min()+1)
            if bw>=0.85*(x1-x0) and bh<=3: continue
            if bh>=0.85*(y1-y0) and bw<=3: continue
            if len(xx)>0.70*m.size: continue
            kept[yy,xx]=1
            comps.append({"area":int(len(xx)),"bbox":[x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max())+1,y0+int(yy.max())+1],"w":bw,"h":bh})
        yy,xx=np.nonzero(kept)
        kb=None if not len(xx) else [x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max())+1,y0+int(yy.max())+1]
        trials[str(th)]={"pixels":int(len(xx)),"bbox":kb,"components":sorted(comps,key=lambda c:c["bbox"][0])}
    rows.append({"n":n,"source":en,"korean":ko,"hint_bbox":box,"background_rgba":[float(x) for x in bg],"trials":trials})
    dvis.rectangle((x0,y0,x1-1,y1-1),outline=(255,0,0,255),width=1)
    dvis.text((x0,max(0,y0-12)),str(n),fill=(255,255,0,255))
report={"schema_version":1,"role":"C","run":run,"asset":"1F5FE6E9","queue_index":132,
        "structure":{"width":W,"height":H,"format":"RGBA32","raw_orientation":"mirror_y"},
        "rows":rows,"status":"SOURCE_ROW_COLOR_DIAGNOSTIC","runtime_validation":"UNTESTED"}
(out/"C137_1F5_SOURCE_ROW_DIAGNOSTIC.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
vis.convert("RGB").save(out/"C137_1F5_SOURCE_HINTS.jpg",quality=96)
summary={"run":run,"asset":"1F5FE6E9","index":132,"status":"SOURCE_ROW_COLOR_DIAGNOSTIC","report":f"localization/graphics/role_C/{run}/C137_1F5_SOURCE_ROW_DIAGNOSTIC.json","runtime_validation":"UNTESTED"}
(wr/"C137_1F5FE6E9_DIAG.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
