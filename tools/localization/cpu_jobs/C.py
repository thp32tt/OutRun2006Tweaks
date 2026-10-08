#!/usr/bin/env python3
"""C308 C2 EVEN q236 14-row independent SOURCE/B80 CLEAN/current persisted DDS plate/composite audit.
Worker produces exact-byte evidence only; all C/C3 visual approvals require controller review.
"""
import os, json, hashlib, subprocess, urllib.request
from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="C"
root=Path(".")
triage=json.loads(subprocess.run(["python","tools/localization/rework_triage.py","--index","236"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert triage["next_action"]=="EVIDENCE_ONLY_HOLD",triage
queue=root/"localization/graphics/asset_queue.csv"
assert "236,textures/load/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds,localize_text,c304_c2_c3_hold_all14_native_done_clean_calibration_pending" in queue.read_text(encoding="utf-8-sig")
native=(root/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds").read_bytes()
clean_path=root/"localization/graphics/role_B/20261005-B-PRODUCTION80/FEF_CLEAN_PLATE.png"
clean_bytes=clean_path.read_bytes()
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/FEF70E85_512x512.dds"
source=urllib.request.urlopen(url,timeout=160).read()
sha=lambda v:hashlib.sha256(v).hexdigest()
expected={"source":"a1c7f7d6ca5d2440076e49477cefecbf5084b4188072f3427ff13e5da24bc518",
          "candidate":"e0a01c50df1aefb2a174dc318a1f6a041f0cf3b2759fff8fcafba7d134ec44c8",
          "authored_clean":sha(clean_bytes)}
assert (sha(source),sha(native))==(expected["source"],expected["candidate"])
assert source[:128]==native[:128],"DDS header mismatch"
s=np.flipud(np.asarray(Image.open(BytesIO(source)).convert("RGBA"))).copy()
f=np.flipud(np.asarray(Image.open(BytesIO(native)).convert("RGBA"))).copy()
c=np.asarray(Image.open(BytesIO(clean_bytes)).convert("RGBA")).copy()
assert s.shape==f.shape==c.shape==(2048,2048,4)
report=json.loads((root/"localization/graphics/role_B/20261007-B-MANUALQA217-FEF70E85/B217_FEF70E85_REPORT.json").read_text(encoding="utf-8"))
assert report["source_sha256"]==expected["source"] and len(report["rows"])==14
assert report["candidate_sha256"]!=expected["candidate"], "This historical B217 row/bbox reference is from a superseded candidate; never reuse its candidate SHA"
dir=root/"localization/graphics/role_C/20261008-C308-C2-Q236-PLATE-COMPOSITE-14REGION"
dir.mkdir(parents=True,exist_ok=True)
def save(im,name):
 p=dir/name
 im.save(p,format="PNG",optimize=True)
 b=p.read_bytes()
 return {"path":str(p),"sha256":sha(b),"size":len(b)}
def composite(arr,rgb):
 aa=Image.fromarray(arr,"RGBA")
 return Image.alpha_composite(Image.new("RGBA",aa.size,(*rgb,255)),aa).convert("RGB")
def visible_bbox(arr,thr=0):
 y,x=np.where(arr[:,:,3]>thr)
 if not len(x):return None
 return [int(x.min()),int(y.min()),int(x.max())+1,int(y.max())+1]
mask=np.zeros((2048,2048),dtype=bool)
for row in report["rows"]:
 l,t,r,b=row["original_bbox"];mask[t:b,l:r]=True
outside_src_clean=int(np.count_nonzero(np.any(s!=c,axis=2)&~mask))
outside_cln_final=int(np.count_nonzero(np.any(c!=f,axis=2)&~mask))
outside_src_final=int(np.count_nonzero(np.any(s!=f,axis=2)&~mask))
outside_alpha_src_clean=int(np.count_nonzero((s[:,:,3]!=c[:,:,3])&~mask))
outside_alpha_clean_final=int(np.count_nonzero((c[:,:,3]!=f[:,:,3])&~mask))
outside_alpha_src_final=int(np.count_nonzero((s[:,:,3]!=f[:,:,3])&~mask))
regions=[]
for idx,row in enumerate(report["rows"]):
 l,t,r,b=row["original_bbox"]
 S,C,F=(a[t:b,l:r].copy() for a in (s,c,f))
 bb=visible_bbox(F,0);sb=visible_bbox(S,0)
 bounded=bool(bb and sb and bb[0]>=0 and bb[1]>=0 and bb[2]<=(r-l) and bb[3]<=(b-t) and
              (bb[2]-bb[0])<=(sb[2]-sb[0]) and (bb[3]-bb[1])<=(sb[3]-sb[1]))
 rec={"index":idx,"source_text":row["source"],"korean_text":row["korean"],
      "source_bbox":row["original_bbox"],"source_visible_bbox_local":sb,"candidate_visible_bbox_local":bb,
      "all_candidate_alpha_within_source_bbox":bounded,
      "authored_clean_nonzero_alpha":int(np.count_nonzero(C[:,:,3])),
      "source_clean_changed_RGBA":int(np.count_nonzero(np.any(S!=C,axis=2))),
      "clean_final_changed_RGBA":int(np.count_nonzero(np.any(C!=F,axis=2))),
      "region_alpha_source":int(np.count_nonzero(S[:,:,3]>0)),
      "region_alpha_candidate":int(np.count_nonzero(F[:,:,3]>0)),
      "source_vs_clean_inside_bbox_identity":"Exact B80 authored CLEAN only, independent calibration required; B217 is ROW METADATA ONLY (superseded candidate)",
      "views":[]}
 for label,bg,scale in (("WHITE_NATIVE",(245,245,245),1.0),
                        ("BLACK_NATIVE",(12,12,12),1.0),
                        ("GRAY_NATIVE",(110,110,110),1.0),
                        ("GRAY_75",(110,110,110),0.75),
                        ("GRAY_50",(110,110,110),0.50)):
  W=r-l;H=b-t
  panel=Image.new("RGB",(W*3,H+25),(29,29,29))
  for ii,(text,arr) in enumerate((("CANONICAL ENGLISH",S),("B80 AUTHORED CLEAN",C),("PERSISTED KOREAN",F))):
   panel.paste(composite(arr,bg),(ii*W,25))
   ImageDraw.Draw(panel).text((ii*W+3,5),text,fill=(255,255,255))
  if scale!=1.0:panel=panel.resize((round(panel.width*scale),round(panel.height*scale)),Image.Resampling.LANCZOS)
  rec["views"].append({"kind":label,**save(panel,f"row{idx:02d}_{label}_SOURCE_CLEAN_FINAL.png")})
 W=r-l;H=b-t
 raw=Image.new("RGB",(W*2,H+25),(29,29,29))
 for ii,(label,a) in enumerate((("ENGLISH RAW",np.flipud(S)),("KOREAN RAW",np.flipud(F)))):
  raw.paste(composite(a,(110,110,110)),(ii*W,25))
  ImageDraw.Draw(raw).text((ii*W+3,5),label,fill=(255,255,255))
 rec["views"].append({"kind":"RAW",**save(raw,f"row{idx:02d}_RAW_SOURCE_FINAL.png")})
 regions.append(rec)
machine={"run":"C308-C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":236,
 "policy_version":"visual-evidence-v1-20261008","execution_backend":"GitHub Actions ubuntu-latest; inputs unavailable from ChatGPT local due raw.githubusercontent.com DNS failure",
 "exact_sha256":expected,"triage":triage,"native_size":[2048,2048],"header_equal":True,"dds_source_candidate_format":"RGBA32 mirror_y mip1",
 "full_atlas_changed_pixels_outside_14_exact_source_bbox_union":{"source_clean_RGBA":outside_src_clean,
  "clean_final_RGBA":outside_cln_final,"source_final_RGBA":outside_src_final,
  "source_clean_alpha":outside_alpha_src_clean,
  "clean_final_alpha":outside_alpha_clean_final,"source_final_alpha":outside_alpha_src_final},
 "regions":regions,"evidence_png_count":sum(len(r["views"]) for r in regions),
 "interpretation":"Exact pixel evidence only. Visual source-family, clean reconstruction, high-zoom, protected-art, blind calibration and in-game NOT automatically passed.",
 "C":"CONTROLLER_PENDING","C3":"NOT_APPROVED","RUNTIME_VALIDATION":"UNTESTED"}
(dir/"C308_Q236_14REGION_NATIVE_MACHINE.json").write_text(json.dumps(machine,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"C308","regions":len(regions),"png_count":machine["evidence_png_count"],
 "outside":machine["full_atlas_changed_pixels_outside_14_exact_source_bbox_union"],
 "clean_nonzero":[z["authored_clean_nonzero_alpha"] for z in regions],"all_within":all(z["all_candidate_alpha_within_source_bbox"] for z in regions),
 "output":str(dir)},ensure_ascii=False))
