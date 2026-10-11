from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json,hashlib
r=Path.cwd()
o=r/"localization/graphics/role_C/20261011-C2-Q060-PSD-V02-SOURCE-FIDELITY"
f=o/"C2_Q060_PSD_CANONICAL_MACHINE.json"
x=json.loads(f.read_text())
psd=Image.open(r/x["psd"]).convert("RGBA")
src=Image.open(r/x["source"]).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean=Image.open(r/x["existing_clean"]).convert("RGBA")
m=Image.open(r/x["removal_mask"]).convert("L")
b=x["metrics"]["removal_mask_bbox"]
# Exact original target, all-channel equality, source removal fidelity, per-alpha safety.
p=np.asarray(psd.crop(tuple(b)))
s=np.asarray(src.crop(tuple(b)))
c=np.asarray(clean.crop(tuple(b)))
mr=np.asarray(m.crop(tuple(b)))>0
assert p.shape==s.shape==c.shape
q={
"BEST_TIME_PSD_vs_CANONICAL_RGBA_changed":int(np.count_nonzero(np.any(p!=s,axis=2))),
"BEST_TIME_PSD_vs_CANONICAL_alpha_changed":int(np.count_nonzero(p[:,:,3]!=s[:,:,3])),
"BEST_TIME_alpha_present_in_CLEAN_mask":int(np.count_nonzero(c[:,:,3][mr])),
"BEST_TIME_alpha_present_in_SOURCE_mask":int(np.count_nonzero(s[:,:,3][mr])),
"BEST_TIME_alpha_change_outside_removal_mask":int(np.count_nonzero((s[:,:,3]!=c[:,:,3])&~mr)),
"BEST_TIME_CLEAN_persisted_alpha_masked_pixels":int(mr.sum())}
assert q["BEST_TIME_PSD_vs_CANONICAL_RGBA_changed"]==0
assert q["BEST_TIME_alpha_present_in_CLEAN_mask"]==0
# independent native, black 50, white 75
bb=(max(0,b[0]-28),max(0,b[1]-30),min(psd.width,b[2]+28),min(psd.height,b[3]+30))
w=bb[2]-bb[0];h=bb[3]-bb[1]
for name,color,ratio in [("BLACK_100",(0,0,0),1),("WHITE_75",(255,255,255),.75),("GRAY_50",(160,160,160),.5)]:
 pane=Image.new("RGB",(3*w,h+26),color)
 dr=ImageDraw.Draw(pane)
 for i,(title,im) in enumerate([("PSD",psd),("CANONICAL",src),("CLEAN",clean)]):
  crop=im.crop(bb)
  bg=Image.new("RGBA",crop.size,color+(255,));bg.alpha_composite(crop)
  pane.paste(bg.convert("RGB"),(i*w,26))
  dr.text((i*w+4,5),title,fill=(255,255,255) if name.startswith("BLACK") else (0,0,0))
 if ratio!=1:pane=pane.resize((int(pane.width*ratio),int(pane.height*ratio)),Image.Resampling.LANCZOS)
 pane.save(o/f"C2_Q060_PSD_SOURCE_CLEAN_{name}.png")
# Actual visible mismatches at (3868,1110)-(3965,1206) (no ROI overlap)
delta=x["pixel_mismatch_detail"]["mismatch_bbox"]
d=(max(0,delta[0]-15),max(0,delta[1]-15),min(psd.width,delta[2]+15),min(psd.height,delta[3]+15))
a=psd.crop(d);g=src.crop(d)
pane=Image.new("RGB",(a.width*2,a.height+24),(150,150,150))
for i,(title,im) in enumerate([("PSD",a),("CANONICAL",g)]):
 mask=Image.new("RGBA",im.size,(165,165,165,255));mask.alpha_composite(im)
 pane.paste(mask.convert("RGB"),(i*a.width,24))
 ImageDraw.Draw(pane).text((i*a.width+2,4),title,fill=(0,0,0))
pane.save(o/"C2_Q060_PSD_494PIXEL_RISK_RAW_NATIVE.png")
x["verified_roi_detail"]=q
x["evidence"]=sorted(str(y.relative_to(r)) for y in o.glob("*.png"))
x["orientation_comment"]="PSD merged matches actual source DDS after FLIP-Y exactly inside BEST_TIME. Global difference 494 RGB pixels only at source-native readable bbox [3868,1110,3965,1206], outside BEST_TIME, alpha unchanged, max channel difference 2. PSD whole texture is NOT bit exact; original canonical DDS remains authority."
f.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(q,ensure_ascii=False))
