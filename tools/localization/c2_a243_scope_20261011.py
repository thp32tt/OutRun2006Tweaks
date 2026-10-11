#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import numpy as np,json,csv
r=Path.cwd()
p=r/"localization/graphics/role_A/20261011-A243-Q193-15CONT-SOURCE-CLEAN-PILOT"
o=r/"localization/graphics/role_C/20261011-C2-Q193-A243-FIRST-PIXEL-INDEPENDENT"
orig=np.flipud(np.asarray(Image.open(r/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds").convert("RGBA"))).copy()
clean=np.asarray(Image.open(p/"A243_PLATE_ONLY_READABLE.png").convert("RGBA"))
new=np.flipud(np.asarray(Image.open(p/"A243_Q193_15CONT_TRUE_CLEAN_NATIVE_TRIAL_UNPROMOTED.dds").convert("RGBA"))).copy()
box=np.zeros(orig.shape[:2],bool);box[221:268,1413:1622]=1
df=np.any(orig!=clean,axis=2)
meas={"official_to_clean_changed_inside":int(np.count_nonzero(df&box)),"official_to_clean_changed_outside":int(np.count_nonzero(df&~box)),"official_to_clean_alpha_changed_outside":int(np.count_nonzero((orig[:,:,3]!=clean[:,:,3])&~box)),"clean_roi_nonzero_alpha":int(np.count_nonzero(clean[221:268,1413:1622,3])),"official_vs_clean_source_removal": "source-derived producer plate vs prior official, not entire English atlas"}
data=json.loads((o/"C2_Q193_A243_MECHANICAL.json").read_text())
data["source_plate_scope_correction"]=meas
data["interpretation"]="SOURCE canonical vs CLEAN full-atlas pixels differ outside q193 ROI due inherited translations already in original official candidate. Correct relevant baseline for protected siblings is official-vs-CLEAN and official-vs-SAVED, NOT canonical SOURCE vs CLEAN across entire atlas."
(o/"C2_Q193_A243_MECHANICAL.json").write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
with (r/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 q=[x for x in csv.DictReader(f) if x.get("index")=="193"]
print(json.dumps({"measures":meas,"queue_row":{k:(v[:400] if k=="notes" else v) for k,v in q[0].items()} if q else None},ensure_ascii=False))
