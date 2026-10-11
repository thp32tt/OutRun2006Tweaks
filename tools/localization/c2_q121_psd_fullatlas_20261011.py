from pathlib import Path
from PIL import Image,ImageOps
import numpy as np,json
r=Path.cwd();base=r/"localization/graphics/role_C/20261011-C2-Q121-PSD-V02-ENGLISH-CANONICAL-COMPARISON"
report=base/"C2_Q121_PSD_TO_CANONICAL_FIRSTHAND.json"
data=json.loads(report.read_text())
p=Image.open(r/data["source_psd_path"]).convert("RGBA")
dds=Image.open(r/data["canonical_game_dds_path"]).convert("RGBA")
w,h=p.size
changed=alpha=changed_outside=alpha_outside=0;minx=miny=10**9;maxx=maxy=-1
roi=data["roi_readable"];x0,y0,x1,y1=roi
for top in range(0,h,128):
 bot=min(h,top+128)
 a=np.asarray(p.crop((0,top,w,bot)))
 b=np.asarray(ImageOps.flip(dds.crop((0,h-bot,w,h-top))))
 hit=np.any(a!=b,axis=2);ha=a[:,:,3]!=b[:,:,3]
 n=int(np.count_nonzero(hit));changed+=n;alpha+=int(np.count_nonzero(ha))
 if n:
  yy,xx=np.nonzero(hit)
  minx=min(minx,int(xx.min()));maxx=max(maxx,int(xx.max()+1))
  miny=min(miny,int(top+yy.min()));maxy=max(maxy,int(top+yy.max()+1))
  out=hit.copy()
  if bot>y0 and top<y1:
   st=max(y0-top,0);en=min(y1-top,bot-top)
   out[st:en,x0:x1]=False
  changed_outside+=int(np.count_nonzero(out))
 if np.any(ha):
  ao=ha.copy()
  if bot>y0 and top<y1:ao[max(y0-top,0):min(y1-top,bot-top),x0:x1]=False
  alpha_outside+=int(np.count_nonzero(ao))
full={"native_wh":[w,h],"pixel_RGBA_differences":changed,"pixel_alpha_differences":alpha,
"outside_gas_pedal_roi_RGBA_differences":changed_outside,"outside_gas_pedal_roi_alpha_differences":alpha_outside,
"changed_bbox":[minx,miny,maxx,maxy] if changed else None,"tile_height":128}
data["full_atlas_readable_fidelity"]=full
data["assessment"]="PSD_V02_NATIVE_COMPOSITE_MATCHES_CANONICAL_FULL_CANVAS" if changed==0 else "PSD_V02_DIFFERS_CANONICAL_FULL_CANVAS"
data["note"]="Full-canvas PSD composited RGBA compared with exact English DDS decoded FLIP-Y; no CLEAN extracted or approved in this comparison, lettering and game consumer not re-reviewed."
report.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(full,ensure_ascii=False))
