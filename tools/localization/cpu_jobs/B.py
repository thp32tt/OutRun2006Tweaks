#!/usr/bin/env python3
import hashlib, json, os, urllib.request, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")
repo=Path.cwd(); run="20261006-B-PROBE198-75C-ALL-CELLS"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
pre=json.loads((repo/"localization/graphics/role_B/20261005-B-PRODUCTION74-PREFLIGHT/B74_75C_PREFLIGHT.json").read_text(encoding="utf-8"))
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
p=Path("/tmp/75C3586A.dds"); urllib.request.urlretrieve(url,p)
raw=p.read_bytes(); got=hashlib.sha256(raw).hexdigest()
if got!=pre["source_sha256"]: raise RuntimeError(("source drift",got,pre["source_sha256"]))
src=Image.open(p).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); H,W=sa.shape[:2]

records=[]; candidate_cards=[]
for reg in pre["regions"]:
    idx=reg["idx"]; x,y,w,h=reg["cell"]
    y0=H-(y+h); y1=H-y; x0=x; x1=x+w
    sub=sa[y0:y1,x0:x1,:]
    r=sub[:,:,0].astype(np.int16); g=sub[:,:,1].astype(np.int16); b=sub[:,:,2].astype(np.int16); a=sub[:,:,3]>8
    red=a&(r>55)&(r>g+24)&(r>b+24)&((r-g)>28)
    lab,n=ndimage.label(red)
    comps=[]
    keep=np.zeros_like(red)
    for i in range(1,n+1):
        cm=lab==i; ar=int(cm.sum())
        if ar<8: continue
        yy,xx=np.nonzero(cm); bb=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
        comps.append([ar,bb]); keep|=cm
    if np.any(keep):
        yy,xx=np.nonzero(keep); rb=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
    else: rb=None
    neutral=a&(np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b])<24)
    rec={"idx":idx,"name":reg["name"],"roi_readable":[x0,y0,x1,y1],"size":[w,h],
         "red_pixels":int(keep.sum()),"red_fraction":float(keep.mean()),"red_bbox_local":rb,
         "red_component_count":len(comps),"red_components":comps,
         "neutral_fraction":float(neutral.mean())}
    # Text-like: multiple red glyph islands over a mostly neutral cell, not a solid red panel.
    rec["textlike"]=bool(len(comps)>=3 and int(keep.sum())>=80 and float(keep.mean())<0.45 and float(neutral.mean())>0.15)
    records.append(rec)
    if rec["textlike"]:
        im=Image.fromarray(sub,"RGBA").convert("RGB")
        scale=max(1,min(4,1400//max(1,im.width)))
        im=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
        card=Image.new("RGB",(im.width,im.height+48),"white"); card.paste(im,(0,48))
        ImageDraw.Draw(card).text((6,8),f"idx{idx} {reg['name']} rawcell={[x,y,w,h]} readROI={[x0,y0,x1,y1]} red={rec['red_pixels']} comps={len(comps)}",fill="black")
        candidate_cards.append(card)

records.sort(key=lambda z:(not z["textlike"],-z["red_component_count"],-z["red_pixels"]))
if not candidate_cards: raise RuntimeError("no textlike cells")
mw=max(c.width for c in candidate_cards); total=sum(c.height for c in candidate_cards)+8*(len(candidate_cards)-1)
sheet=Image.new("RGB",(mw,total),"white"); yy=0
for c in candidate_cards: sheet.paste(c,(0,yy)); yy+=c.height+8
sheet.thumbnail((1800,6000),Image.Resampling.LANCZOS)
sheet.save(out/"B198_TEXTLIKE_CELL_CONTACT.jpg",quality=96)
report={"schema_version":1,"role":"B","run":run,"base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"queue_index":176,"asset":"75C3586A","source_sha256":got,"records":records,"textlike_indices":[r["idx"] for r in records if r["textlike"]],"status":"ALL_CELL_TEXTLIKE_DIAGNOSTIC_READY","no_vr_ffb_dx11_dxvk_work":True}
rp=out/"B198_ALL_CELL_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B198_75C_ALL_CELLS.json").write_text(json.dumps({"role":"B","run":run,"report":str(rp.relative_to(repo)),"textlike_indices":report["textlike_indices"],"status":"ALL_CELL_TEXTLIKE_DIAGNOSTIC_READY"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B198_DONE",[(r["idx"],r["red_pixels"],r["red_component_count"],r["neutral_fraction"],r["red_bbox_local"]) for r in records if r["textlike"]])
