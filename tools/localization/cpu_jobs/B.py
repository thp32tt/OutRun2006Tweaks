#!/usr/bin/env python3
import hashlib, json, os, urllib.request, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")
repo=Path.cwd(); run="20261006-B-PROBE197-75C-TEXT-CELLS"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds"
p=Path("/tmp/75C3586A.dds"); urllib.request.urlretrieve(url,p)
raw=p.read_bytes(); got=hashlib.sha256(raw).hexdigest()
exp="8ba40915abca8b7022acbcc743e93186970fdf7e29f0eb80e84903d31074c708"
if got!=exp: raise RuntimeError(("source drift",got))
src=Image.open(p).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); H,W=sa.shape[:2]
cells=[
 ("idx35",0,1508,892,1676),("idx36",892,1508,1772,1676),
 ("idx37",0,1676,580,1844),("idx38",580,1676,1040,1844),
 ("idx39",0,1844,1036,2008),("idx40",1036,1844,1312,1956),
]
recs=[]; cards=[]
for name,x0,y0,x1,y1 in cells:
 sub=sa[y0:y1,x0:x1,:]
 r=sub[:,:,0].astype(np.int16); g=sub[:,:,1].astype(np.int16); b=sub[:,:,2].astype(np.int16); a=sub[:,:,3]>8
 masks={}
 for label,mask in [
   ("red65",a&(r>65)&(r>g+28)&(r>b+28)&((r-g)>35)),
   ("red40",a&(r>40)&(r>g+18)&(r>b+18)&((r-g)>20)),
   ("bright_red",a&(r>100)&(g<100)&(b<100)&(r>g+40))
 ]:
   lab,n=ndimage.label(mask)
   keep=np.zeros_like(mask)
   comps=[]
   for i in range(1,n+1):
     cm=lab==i; ar=int(cm.sum())
     if ar<4: continue
     yy,xx=np.nonzero(cm); bb=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
     comps.append([ar,bb]); keep|=cm
   if np.any(keep):
     yy,xx=np.nonzero(keep); bb=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
   else: bb=None
   masks[label]={"pixels":int(keep.sum()),"bbox_local":bb,"components":comps}
 im=Image.fromarray(sub,"RGBA").convert("RGB")
 scale=max(1,min(3,1200//max(1,im.width)))
 im=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
 card=Image.new("RGB",(im.width,im.height+42),"white"); card.paste(im,(0,42))
 ImageDraw.Draw(card).text((6,8),f"{name} ROI={[x0,y0,x1,y1]} red65={masks['red65']['pixels']} bb={masks['red65']['bbox_local']}",fill="black")
 cards.append(card)
 recs.append({"cell":name,"roi_readable":[x0,y0,x1,y1],"red_masks":masks})
mw=max(c.width for c in cards); total=sum(c.height for c in cards)+8*(len(cards)-1)
sheet=Image.new("RGB",(mw,total),"white"); y=0
for c in cards: sheet.paste(c,(0,y)); y+=c.height+8
sheet.thumbnail((1800,5000),Image.Resampling.LANCZOS)
sheet.save(out/"B197_TEXT_CELL_CONTACT.jpg",quality=96)
report={"schema_version":1,"role":"B","run":run,"base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"queue_index":176,"asset":"75C3586A","source_sha256":got,"cells":recs,"status":"TEXT_CELL_DIAGNOSTIC_READY","no_vr_ffb_dx11_dxvk_work":True}
rp=out/"B197_TEXT_CELL_REPORT.json"; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B197_75C_TEXT_CELLS.json").write_text(json.dumps({"role":"B","run":run,"report":str(rp.relative_to(repo)),"status":"TEXT_CELL_DIAGNOSTIC_READY"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B197_DONE",[(x["cell"],x["red_masks"]["red65"]["pixels"],x["red_masks"]["red65"]["bbox_local"]) for x in recs])
