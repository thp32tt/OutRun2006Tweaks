#!/usr/bin/env python3
"""C2 q214 NEW B259: independently decoded, source-bound lossless QA evidence ONLY."""
import hashlib, io, json, os, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

if os.getenv("OUTRUN_CPU_WORKER") != "github-actions" or os.getenv("OUTRUN_CPU_ROLE") != "C":
    raise SystemExit("Only approved GitHub Actions role C worker")
R=Path(".")
O=R/"localization/graphics/role_C/20261008-C289-C2-Q214-B259-PERSISTED"
O.mkdir(parents=True,exist_ok=True)
TRIAGE=subprocess.run(["python","tools/localization/rework_triage.py","--index","214"],capture_output=True,text=True)
if TRIAGE.returncode:
    raise SystemExit("q214 rework triage failed: "+TRIAGE.stderr.strip())
triage=json.loads(TRIAGE.stdout)
assert len(triage["assets"])==1 and triage["assets"][0]["index"]==214
(O/"C289_TRIAGE.json").write_text(json.dumps(triage,ensure_ascii=False,indent=2)+"\n")
p=R/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds"
cleanp=R/"localization/graphics/role_B/20261006-B-PRODUCTION194-BF229CF4-START-GOAL/B194_CLEAN_PLATE.png"
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3da79726739ac631d8e2703a65330dbb0c310770/Release/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds"
with urllib.request.urlopen(url,timeout=160) as f: sb=f.read()
cb=p.read_bytes()
H=lambda b:hashlib.sha256(b).hexdigest()
assert H(sb)=="9a2e428bdb87399a7589338053b49efdcfd103d14f12a33a4bcde7705ab76c6b"
assert H(cb)=="ace42cb3d539df7c538c6d93b6c3f001e3d18e4f41aaa29bdab1466fe412fc30"
assert sb[:128]==cb[:128], "DDS header drift"
decode=lambda b:np.asarray(Image.open(io.BytesIO(b)).convert("RGBA")).copy()
raws=decode(sb);rawf=decode(cb)
s=np.flipud(raws).copy();f=np.flipud(rawf).copy()
clean=np.asarray(Image.open(cleanp).convert("RGBA")).copy()
assert s.shape==f.shape==clean.shape==(2048,2048,4)
def comps(a,b):return np.any(a!=b,axis=2)
def flatten(a,bg):
  A=a[...,3:4].astype(np.uint16);rgb=a[...,:3].astype(np.uint16)
  return ((rgb*A+bg*(255-A)+127)//255).astype(np.uint8)
rows=[("start","START","출발",(815,495,899,517)),("goal","GOAL","골",(1343,764,1417,787))]
allow=np.zeros((2048,2048),dtype=bool)
for _id,en,ko,(x0,y0,x1,y1) in rows:allow[y0:y1,x0:x1]=True
off=int(np.count_nonzero(comps(s,f)&~allow))
alpha_off=int(np.count_nonzero((s[:,:,3]!=f[:,:,3])&~allow))
clean_off=int(np.count_nonzero(comps(s,clean)&~allow))
def get_bbox(mask):
  yy,xx=np.where(mask)
  return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
evidence=[]
for rid,en,ko,box in rows:
  x0,y0,x1,y1=box
  gap=14
  l=max(0,x0-gap);t=max(0,y0-gap);r=min(2048,x1+gap);b=min(2048,y1+gap)
  arr=[a[t:b,l:r] for a in (s,clean,f)]
  for a,tag in zip(arr,("SOURCE_ENGLISH","CLEAN_B194","FINAL_B259_DECODED")):
    Image.fromarray(a,"RGBA").save(O/f"{rid}_{tag}_LOSSLESS.png")
  for bg,name in [(0,"BLACK"),(128,"GRAY"),(255,"WHITE")]:
    imgs=[Image.fromarray(flatten(a,bg),"RGB") for a in arr]
    w,h=imgs[0].size
    montage=Image.new("RGB",(3*w,h+22),(60,60,60));d=ImageDraw.Draw(montage)
    for n,(im,label) in enumerate(zip(imgs,("ENGLISH SOURCE","AUTHORED CLEAN","PERSISTED B259 DDS"))):
      montage.paste(im,(n*w,22));d.text((n*w+2,4),label,fill="white")
    montage.save(O/f"{rid}_{name}_SOURCE_CLEAN_FINAL_NATIVE.png")
    if name=="GRAY":
      montage.resize((montage.width*4,montage.height*4),Image.Resampling.NEAREST).save(O/f"{rid}_GRAY_SOURCE_CLEAN_FINAL_ZOOM4X.png")
      for factor in (0.75,0.5):
        montage.resize((round(montage.width*factor),round(montage.height*factor)),Image.Resampling.LANCZOS).save(O/f"{rid}_GRAY_PRACTICAL_{int(factor*100)}.png")
  rt,rb=2048-b,2048-t
  Image.fromarray(raws[rt:rb,l:r],"RGBA").save(O/f"{rid}_ENGLISH_RAW.png")
  Image.fromarray(rawf[rt:rb,l:r],"RGBA").save(O/f"{rid}_B259_RAW.png")
  # Raw candidate min/max vs clean is an effect + restored plate delta,
  # NOT a glyph-only bounding box and NOT a strict positive-margin proof.
  changed=comps(s[y0:y1,x0:x1],f[y0:y1,x0:x1])
  delta=comps(clean[y0:y1,x0:x1],f[y0:y1,x0:x1])
  bb=get_bbox(delta)
  if bb:bb=[bb[0]+x0,bb[1]+y0,bb[2]+x0,bb[3]+y0]
  evidence.append({"id":rid,"source":en,"korean":ko,"source_effect_bbox":list(box),
   "candidate_vs_clean_effect_delta_bbox":bb,
   "clean_delta_not_a_glyph_mask":True,
   "decoded_source_vs_candidate_changed_inside_bbox":int(changed.sum()),
   "source_alpha_pixels":int(np.count_nonzero(s[y0:y1,x0:x1,3])),
   "candidate_alpha_pixels":int(np.count_nonzero(f[y0:y1,x0:x1,3])),
   "raw_flipY_crop_coords":[l,rt,r,rb],
   "evidence_native":[f"{rid}_GRAY_SOURCE_CLEAN_FINAL_NATIVE.png",f"{rid}_BLACK_SOURCE_CLEAN_FINAL_NATIVE.png",f"{rid}_WHITE_SOURCE_CLEAN_FINAL_NATIVE.png"],
   "evidence_practical":[f"{rid}_GRAY_PRACTICAL_75.png",f"{rid}_GRAY_PRACTICAL_50.png"],
   "evidence_raw":[f"{rid}_ENGLISH_RAW.png",f"{rid}_B259_RAW.png"]})
m={"run":"C289","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":214,
"source_sha256":H(sb),"candidate_sha256":H(cb),"clean_plate_sha256":H(cleanp.read_bytes()),"source_provenance":url,
"native_dimensions":[2048,2048],"dds_format":"DXT5_BC3","readable_orientation":"FLIP_Y","raw_orientation":"MIRROR_Y",
"header_128_equal":True,"source_vs_candidate_changed_outside_2_exact_effect_bboxes":off,
"source_vs_candidate_alpha_outside_2_exact_effect_bboxes":alpha_off,
"source_vs_authored_clean_changed_outside_2_exact_effect_bboxes":clean_off,
"regions":evidence,"rework_triage":triage["assets"][0],
"triage_note":"Current queue status contains material_rework historically but new B259 exact SHA awaits independent fresh C; do not auto-rerender.",
"machine_result":"OUTSIDE_ZERO" if off==alpha_off==0 else "OUTSIDE_FAIL",
"glyph_only_bbox":"UNPROVEN_SOURCE_EFFECT_AND_CLEAN_DELTA_ARE_NOT_GLYPH_ONLY_MASKS",
"calibration":"NOT_PERFORMED_BY_SCRIPT","visual_result":"PENDING_INDEPENDENT_CONTROLLER",
"c3":"BLOCKED_UNTIL_C_VISUAL_AND_PER_REGION_POLICY_EVIDENCE",
"runtime_validation":"UNTESTED","no_candidate_modified":True}
(O/"C289_Q214_NATIVE_MACHINE.json").write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n")
print("C289 candidate",H(cb),"region outside RGBA",off,"alpha",alpha_off,
      "clean_outside",clean_off,"triage",triage["assets"][0]["next_action"])
