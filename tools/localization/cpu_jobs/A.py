#!/usr/bin/env python3
"""A229: P0 q121 source-exact visual atlas inventory for unsafe unclassified remnant cells.
Perform a new scoped native source/official/A220 audit over all 30 A215 component
ROIs, rather than blindly repeating A221's two no-remnant rework attempts.
Do not alter candidate bytes until exact user-failed label/neighbor identity
and its protected pixels can be separated in a follow-up real production step.
"""
import hashlib,io,json,os,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
repo=Path.cwd()
out=repo/"localization/graphics/role_A/20261010-A229-Q121-P0-ALL30-SOURCE-REMAINDER-INVENTORY"
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
diag=json.loads((repo/"localization/graphics/role_A/20261010-A215-Q121-P0-SOURCE-COMPONENT-LOSSLESS/A215_COMPONENT_QA.json").read_text())
assert diag["source_sha256"]=="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
assert len(diag["regions"])==30
prior=json.loads((repo/"localization/graphics/role_A/20261010-A221-Q121-SOURCE-BOUNDARY-HOLD/A221_SOURCE_BOUNDARY_FAIL_CLOSED.json").read_text())
assert prior["reason_for_no_new_dds"].startswith("Candidate exact-source pixel mask is empty")
b=repo/"localization/graphics/role_A/20261010-A220-Q121-THE-SOURCE-RESIDUE/A220_Q121_THE_RESIDUE_PLUS_GOAL33_UNPROMOTED.dds"
trial=b.read_bytes();assert sha(trial)==prior["previous_A219_A220_trial_sha256"]
official_path=repo/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
official=official_path.read_bytes();assert sha(official)==prior["official_candidate_sha256"]
with urllib.request.urlopen(diag["source_url"],timeout=180) as res: src=res.read()
assert sha(src)==prior["source_dds_sha256"]
assert len(src)==len(trial)==len(official)==128+4096*4096*4
assert src[:4]==trial[:4]==official[:4]==b"DDS "
def im(data):
 return Image.open(io.BytesIO(data)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
source,off,t=im(src),im(official),im(trial)
assert source.size==off.size==t.size==(4096,4096)
# This is a detection/inventory experiment, not a source-to-clean QA approval:
# source identical alpha-positive candidate pixels may be legitimate preserved art.
rows=[]
for reg in diag["regions"]:
 rank=reg["rank"]; x0,y0,x1,y1=reg["bbox_readable"]
 assert 0<=x0<x1<=4096 and 0<=y0<y1<=4096
 sa=np.array(source.crop((x0,y0,x1,y1)))
 ca=np.array(t.crop((x0,y0,x1,y1)))
 oa=np.array(off.crop((x0,y0,x1,y1)))
 src_alpha=sa[:,:,3]>0
 exact=src_alpha & (ca[:,:,3]>0) & np.all(sa==ca,axis=2)
 prev_exact=src_alpha & (oa[:,:,3]>0) & np.all(sa==oa,axis=2)
 changed=np.any(oa!=ca,axis=2)
 # Pixel-complete exact-sha comparison, not heuristic 'it looks like English'.
 only_src=np.count_nonzero(src_alpha&~(ca[:,:,3]>0))
 added=np.count_nonzero(~src_alpha&(ca[:,:,3]>0))
 ys,xs=np.nonzero(exact)
 contact_bbox=[int(x0+xs.min()),int(y0+ys.min()),int(x0+xs.max()+1),int(y0+ys.max()+1)] if len(xs) else None
 regions_extra=(int(y1-y0),int(x1-x0))
 cells={"rank":rank,"source_bbox":[x0,y0,x1,y1],"roi_hw":regions_extra,
  "source_visible_alpha":int(src_alpha.sum()),
  "official_exact_source_rgba_alpha_positive":int(prev_exact.sum()),
  "a220_exact_source_rgba_alpha_positive":int(exact.sum()),
  "exact_source_remaining_bbox":contact_bbox,
  "official_to_trial_changed_rgba_pixels":int(changed.sum()),
  "a220_nonoriginal_alpha_positive":int(added),
  "source_removed_alpha_positive":int(only_src),
  "semantic":"UNCLASSIFIED_NEIGHBOR_AND_TEXT_MAY_COEXIST",
  "machine_verdict":"SOURCE_EXACT_RESIDUE_CANDIDATE_NOT_ERASURE_APPROVAL" if len(xs) else "NO_SOURCE_EXACT_RGBA_CANDIDATE_IN_ROI"}
 rows.append(cells)
 # Persist contacts for novel remaining exact source >0 and the two known ambiguous
 # boundary ROIs; cap to avoid clutter. Visual observation must classify neighbors.
 if len(xs)>0 or rank in (21,26):
  comps=[]
  for img in (source,off,t):
   layer=img.crop((x0,y0,x1,y1))
   bg=Image.new("RGBA",layer.size,(95,95,95,255))
   comps.append(Image.alpha_composite(bg,layer).convert("RGB"))
  w,h=comps[0].size
  # cap size for first 30 full atlas cells, yet preserve a truly native proof.
  if w>900 or h>400:
   k=min(900/w,400/h)
   preview=[e.resize((round(w*k),round(h*k)),Image.Resampling.LANCZOS) for e in comps]
   scale=f"PREVIEW_ONLY_{k:.3f}"
  else:preview=comps;scale="NATIVE"
  pw,ph=preview[0].size
  sheet=Image.new("RGB",(3*pw,ph+28),(95,95,95))
  d=ImageDraw.Draw(sheet)
  for col,(name,img) in enumerate(zip(("ENGLISH SOURCE","CURRENT OFFICIAL","UNPROMOTED A220"),preview)):
   sheet.paste(img,(col*pw,28))
   d.text((col*pw+4,4),name,fill="white")
  sheet.save(out/f"A229_rank{rank:02d}_SOURCE_OFFICIAL_A220_{scale}.png")
  if rank in (21,26):
   Image.fromarray((exact.astype(np.uint8)*255),mode="L").save(out/f"A229_rank{rank:02d}_EXACT_SOURCE_MATCH_MASK_NATIVE.png")
# Unchanged original/current bytes; no unqualified remediation.
report={"run":"A229","run_key":"OUTRUN-KOR-A229-Q121-P0-ALL30-SOURCE-EXACT-20261010-2200",
 "role":"A","queue_index":121,"priority":"P0","owner_lane":"A",
 "triage":"A221 rework blocked unsafe same-region rerender; expanded genuine-source classification to other 28 native source ROIs",
 "source_sha256":sha(src),"official_sha256":sha(official),"a220_trial_sha256":sha(trial),
 "sha_verified_all_three":True,"native":"4096x4096 RGBA32 mip1 readable=FLIP_TOP_BOTTOM",
 "regions_total":len(rows),"rows_with_exact_source_rgba":sum(i["a220_exact_source_rgba_alpha_positive"]>0 for i in rows),
 "sum_exact_source_rgba_by_overlapping_ROIs_not_distinct_pixels":sum(i["a220_exact_source_rgba_alpha_positive"] for i in rows),
 "source_defects_inferred":False,"candidate_changed":False,"new_DDS":0,
 "decision":"MAPPING_AND_PROTECTED_NEIGHBOR_TRIAGE_ONLY_NO_PIXEL_FIX",
 "C1":"NOT_RUN","C3":"NOT_RUN","user_regressions":["IGR-030","IGR-031","IGR-040"],
 "RUNTIME_VALIDATION":"UNTESTED","next_action":"Visually classify residual contours in each rank-specific source/current contact first, then reconstruct only confirmed English lettering from true source CLEAN; protect neighboring artwork. A221 rank21/26 no blind deletion.",
 "rows":rows}
(out/"A229_ALL30_SOURCE_EXACT_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"rows":len(rows),"source_exact_remaining":report["rows_with_exact_source_rgba"],
"top":sorted([{"rank":r["rank"],"pixels":r["a220_exact_source_rgba_alpha_positive"]}
 for r in rows if r["a220_exact_source_rgba_alpha_positive"]],key=lambda x:-x["pixels"])[:12]},ensure_ascii=False))
