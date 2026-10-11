from pathlib import Path
from PIL import Image,ImageOps
import numpy as np,json,hashlib
r=Path.cwd()
b=r/"localization/graphics/role_C/20261011-C2-Q060-PSD-V02-SOURCE-FIDELITY"
f=b/"C2_Q060_PSD_CANONICAL_MACHINE.json";d=json.loads(f.read_text())
psd=np.asarray(Image.open(r/d["psd"]).convert("RGBA"))
src=np.flipud(np.asarray(Image.open(r/d["source"]).convert("RGBA"))).copy()
pix=np.any(psd!=src,axis=2)
ys,xs=np.nonzero(pix)
vis=pix & (src[:,:,3]>0)
zero=pix & (src[:,:,3]==0)
rgb=np.max(np.abs(psd.astype(np.int16)-src.astype(np.int16)),axis=2)
x0,y0,x1,y1=2179,340,3028,474
inside=np.zeros(pix.shape,dtype=bool);inside[y0:y1,x0:x1]=1
detail={
"mismatch_bbox":[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)],
"mismatch_visible_alpha_gt_0":int(vis.sum()),
"mismatch_alpha_zero":int(zero.sum()),
"mismatch_inside_BEST_TIME_bbox":int((pix&inside).sum()),
"mismatch_outside_BEST_TIME_bbox":int((pix&~inside).sum()),
"largest_channel_difference":int(rgb[pix].max()),
"mean_channel_difference_changed_pixels":float(np.mean(np.abs(psd[pix].astype(np.int16)-src[pix].astype(np.int16))))
}
# Transparent alpha zero: RGB changes invisible; positive-alpha palette difference risk quant.
d["pixel_mismatch_detail"]=detail
d["source_fidelity_status"]="NOT_BYTE_EQUAL_BUT_ALPHA_IDENTICAL" 
f.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(detail,ensure_ascii=False))
