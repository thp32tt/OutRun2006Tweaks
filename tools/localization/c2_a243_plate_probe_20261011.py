#!/usr/bin/env python3
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,ImageDraw
root=Path.cwd()
p=root/"localization/graphics/role_A/20261011-A243-Q193-15CONT-SOURCE-CLEAN-PILOT"
o=root/"localization/graphics/role_C/20261011-C2-Q193-A243-FIRST-PIXEL-INDEPENDENT"
im=lambda file:np.asarray(Image.open(file).convert("RGBA")).copy()
src=np.flipud(im(p/"A243_PINNED_CANONICAL_SOURCE.dds")).copy()
trial=np.flipud(im(p/"A243_Q193_15CONT_TRUE_CLEAN_NATIVE_TRIAL_UNPROMOTED.dds")).copy()
clean=im(p/"A243_PLATE_ONLY_READABLE.png")
glyph=im(p/"A243_LETTERING_ONLY_READABLE.png")
x0,y0,x1,y1=1413,221,1622,268
rect=(slice(y0,y1),slice(x0,x1))
auth=np.zeros(src.shape[:2],bool);auth[rect]=1
delta_sp=np.any(src!=clean,axis=2)
delta_pf=np.any(clean!=trial,axis=2)
new_alpha=((src[:,:,3]==0)&(clean[:,:,3]>0))
src_alpha_cell=int(np.count_nonzero(src[rect][:,:,3]))
clean_alpha_cell=int(np.count_nonzero(clean[rect][:,:,3]))
glyph_alpha_out=int(np.count_nonzero((glyph[:,:,3]>0)&~auth))
plate_out=int(np.count_nonzero(delta_sp&~auth))
final_out=int(np.count_nonzero(delta_pf&~auth))
intrusion=int(np.count_nonzero(new_alpha))
roundtrip=np.asarray(Image.alpha_composite(Image.fromarray(clean),Image.fromarray(glyph)))
compose_mismatch=int(np.count_nonzero(np.any(roundtrip!=trial,axis=2)))
# PNGs source vs CLEAN and CLEAN vs saved actual DDs on same canvas, including original bg/alpha
def montage(labels,arrays,path,bg):
 ch=y1-y0; cw=x1-x0;w=cw*len(labels)
 pic=Image.new("RGB",(w,ch+23),bg);d=ImageDraw.Draw(pic)
 for i,(label,a) in enumerate(zip(labels,arrays)):
  crop=Image.fromarray(a[rect],"RGBA")
  base=Image.new("RGBA",crop.size,bg+(255,));base.alpha_composite(crop)
  pic.paste(base.convert("RGB"),(i*cw,23));d.text((i*cw+2,2),label,fill=(0,0,0) if sum(bg)>350 else (255,255,255))
 pic.save(o/path)
for bg,name in [((175,175,175),"GRAY_100"),((255,255,255),"WHITE_100"),((0,0,0),"BLACK_100")]:
 montage(["SOURCE","CLEAN","GLYPH ONLY","SAVED DDS"],[src,clean,glyph,trial],f"C2_PLATE_GLYPH_FINAL_{name}.png",bg)
# white/gray practical 75/50 for each native isolated line
for ratio in [75,50]:
 base=Image.open(o/"C2_PLATE_GLYPH_FINAL_WHITE_100.png")
 resized=base.resize((round(base.width*ratio/100),round(base.height*ratio/100)),Image.Resampling.LANCZOS)
 resized.save(o/f"C2_PLATE_GLYPH_FINAL_WHITE_{ratio}.png")
meas={"src_alpha_in_exact_roi":src_alpha_cell,"clean_alpha_in_exact_roi":clean_alpha_cell,
"new_plate_alpha_where_canonical_source_transparent_full_atlas":intrusion,
"source_clean_changed_outside_target_roi":plate_out,
"clean_persisted_final_changed_outside_target_roi":final_out,
"glyph_only_alpha_outside_target_roi":glyph_alpha_out,
"source_clean_changed_inside_roi":int(np.count_nonzero(delta_sp&auth)),
"clean_persisted_final_changed_inside_roi":int(np.count_nonzero(delta_pf&auth)),
"alpha_composite_clean_plus_glyph_vs_saved_DDS_diff_pixels":compose_mismatch}
report=o/"C2_Q193_A243_MECHANICAL.json"
data=json.loads(report.read_text())
data["plate_composite_metrics"]=meas
data["independent_evidence"] += [str((o/f).relative_to(root)) for f in ["C2_PLATE_GLYPH_FINAL_GRAY_100.png","C2_PLATE_GLYPH_FINAL_WHITE_100.png","C2_PLATE_GLYPH_FINAL_BLACK_100.png","C2_PLATE_GLYPH_FINAL_WHITE_75.png","C2_PLATE_GLYPH_FINAL_WHITE_50.png"]]
report.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(meas,ensure_ascii=False))
