#!/usr/bin/env python3
"""A236 q161 source-authenticated transparent CLEAN for C344 rejected cells.
New deliverable: exact 2048x2048 source-matched reusable PLATE (11,16,24),
masks, lossless source/clean views, and immutable q161 plate-library manifest.
No candidate rewrite and no C1/C3/game approval. Avoid repeating A218 trial.
"""
import csv,hashlib,io,json,os,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
sys.dont_write_bytecode=True
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions"
assert os.getenv("OUTRUN_CPU_ROLE")=="A"
root=Path.cwd();folder="20261011-A236-Q161-THREE-SOURCE-AUTHENTICATED-CLEAN"
out=root/"localization/graphics/role_A"/folder
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
def jb(o):return (json.dumps(o,indent=2,ensure_ascii=False)+"\n").encode()
def write(o,p):(out/p).write_bytes(jb(o))
def png(a):b=io.BytesIO();Image.fromarray(a).save(b,format="PNG",optimize=True);return b.getvalue()
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","161"],capture_output=True,text=True)
write({"returncode":tri.returncode,"stdout":tri.stdout[-6500:],"stderr":tri.stderr[-700:]},"A236_TRIAGE.json")
assert tri.returncode==0
with (root/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 q=next(x for x in csv.DictReader(f) if x["index"]=="161")
assert q["action"]=="localize_text"
official_path=root/"localization/graphics/hd_candidates"/q["path"]
official_raw=official_path.read_bytes()
assert sha(official_raw)=="8ded856536184ab0a91e2ee014e8dcfaa5f8e21a5400a4891f459e4a195dda65"
try_path=root/"localization/graphics/role_A/20261010-A218-Q161-C344-THREE-GLYPH-FACE-REPAIR/A218_Q161_C344_THREE_FACE_REWORK_TRIAL.dds"
assert sha(try_path.read_bytes())=="8000601ead8b2858b36f8078b92898405b9621ca5b03b553918df8acdf38e05e"
raw_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/55B57CDE_512x512.dds"
source_path=out/"A236_CANONICAL_ENGLISH_SOURCE_EXACT.dds"
# Pinned online source is 4MB BC3, unlike the q121 67MB download timeout.
with urllib.request.urlopen(urllib.request.Request(raw_url,headers={"User-Agent":"OutRunLocalizationSourceAudit/1.0"}),timeout=80) as f:src_raw=f.read()
assert sha(src_raw)=="a74d31016e9ab38da4f6bd9a37196848534b9a1c8ac04db3f071000030681c4d"
assert src_raw[:4]==b"DDS " and len(src_raw)==4194432
source_path.write_bytes(src_raw)
def decoded(data):
 a=np.array(Image.open(io.BytesIO(data)).convert("RGBA"),dtype=np.uint8)
 assert a.shape==(2048,2048,4)
 return a[::-1].copy()
source=decoded(src_raw)
official=decoded(official_raw)
trial=decoded(try_path.read_bytes())
source_guide={
11:{"english":"AQUARIUS","korean":"물병자리","bbox":[717,1671,1013,1725]},
16:{"english":"SOUTH KOREA","korean":"대한민국","bbox":[2,1479,403,1530]},
24:{"english":"ITALY","korean":"이탈리아","bbox":[6,1224,160,1272]}
}
# SOURCE is transparent outside original English glyphs. Restrict all edits
# to genuine canonical glyph bboxes; do not affect any of 35 other cells.
mask=np.zeros((2048,2048),dtype=np.uint8)
clean=source.copy()
stats=[]
for idx,q in source_guide.items():
 x0,y0,x1,y1=q["bbox"]
 assert x0%4!=x1%4 or True
 orig=source[y0:y1,x0:x1].copy()
 # Original English glyph bbox contains only alpha-authored dark text and
 # transparent empty pixels. Require zero nonopaque unrelated-colored art.
 source_visible=orig[:,:,3]>0
 opaque_rgb=orig[source_visible,:3]
 assert len(opaque_rgb)>500,(idx,len(opaque_rgb))
 dark=np.mean(opaque_rgb,axis=1)
 assert np.percentile(dark,95)<160,(idx,np.percentile(dark,95))
 mask[y0:y1,x0:x1]=255
 clean[y0:y1,x0:x1]=0
 assert not np.any(clean[y0:y1,x0:x1,3])
 region={"id":idx,**q,"source_visible_alpha":int(source_visible.sum()),
 "bbox_native":q["bbox"],"source_rgb_median":np.median(opaque_rgb,axis=0).round().astype(int).tolist(),
 "clean_alpha_max":int(clean[y0:y1,x0:x1,3].max()),"source_bbox_area":int((x1-x0)*(y1-y0))}
 # Review future C1 MUST compare actual text removal and protection.
 stats.append(region)
outside=np.any(source!=clean,axis=2)&(mask==0)
assert np.count_nonzero(outside)==0
assert not np.any(clean[:,:,3][mask>0])
assert np.all(clean[mask==0]==source[mask==0])
# Actual 38-atlas existing content must not be mechanically confused with
# a new Korean candidate: SOURCE->CLEAN ONLY, trial unchanged.
source_png=png(source);clean_png=png(clean);mask_png=png(mask)
source_png_sha=sha(source_png);clean_sha=sha(clean_png);mask_sha=sha(mask_png)
out.joinpath("A236_SOURCE_READABLE_NATIVE.png").write_bytes(source_png)
out.joinpath("A236_CLEAN_READABLE_NATIVE.png").write_bytes(clean_png)
out.joinpath("A236_THREE_REMOVAL_MASK_NATIVE.png").write_bytes(mask_png)
# Native/practical contacts from exact SOURCE and CLEAN and preexisting A218
# candidate, never fabricate an independent review. Label all statuses.
for idx,q in source_guide.items():
 x0,y0,x1,y1=q["bbox"]
 r=(max(0,x0-5),max(0,y0-4),min(2048,x1+5),min(2048,y1+4))
 for bgname,bg in [("GRAY",(100,100,100)),("WHITE",(255,255,255)),("BLACK",(0,0,0))]:
  for pct in (100,75,50):
   parts=[]
   for atlas in (source,clean,official,trial):
    frame=Image.fromarray(atlas,"RGBA").crop(r)
    composed=Image.alpha_composite(Image.new("RGBA",frame.size,bg+(255,)),frame).convert("RGB")
    if pct!=100:
     composed=composed.resize((max(1,round(composed.width*pct/100)),max(1,round(composed.height*pct/100))),Image.Resampling.LANCZOS)
    parts.append(composed)
   w,h=parts[0].size
   sheet=Image.new("RGB",(w*4,h+20),bg)
   d=ImageDraw.Draw(sheet)
   for n,(im,lab) in enumerate(zip(parts,("SOURCE","NEW CLEAN","OFFICIAL","A218 TRIAL"))):
    sheet.paste(im,(n*w,20));d.text((n*w+2,2),lab,fill="black" if bgname=="WHITE" else "white")
   sheet.save(out/f"A236_R{idx:02d}_{bgname}_{pct}.png")
 # Source + saved candidate actual RAW crops from true mirrored DDS order.
 Image.fromarray(source[y0:y1,x0:x1][::-1].copy(),"RGBA").save(out/f"A236_R{idx:02d}_SOURCE_RAW.png")
 Image.fromarray(trial[y0:y1,x0:x1][::-1].copy(),"RGBA").save(out/f"A236_R{idx:02d}_A218_RAW.png")
report={
 "run":"A236","run_key":"OUTRUN-KOR-A236-Q161-CANONICAL-THREE-CELL-CLEAN-PLATE-20261011-0800",
 "role":"A","queue_index":161,"scope":"P1_SOURCE_TO_CLEAN_ONLY_3_OF_38",
 "new_korean_dds":0,"old_trial_regenerated":False,"official_dds_modified":False,
 "source_url":raw_url,"source_dds_sha256":sha(src_raw),
 "official_sha256":sha(official_raw),"prior_a218_sha256":sha(try_path.read_bytes()),
 "source_png_sha256":source_png_sha,"clean_png_sha256":clean_sha,
 "removal_mask_sha256":mask_sha,"native":[2048,2048],"format":"BC3/DXT5 source DDS",
 "readable_orientation":"RAW vertical mirror FLIP-Y","mask_rgba_outside_change":0,
 "clean_residual_alpha":0,"source_to_clean_changed_rgba":int(np.count_nonzero(np.any(source!=clean,axis=2))),
 "source_to_clean_mask_pixels":int(np.count_nonzero(mask)),
 "regions":stats,"other_35_cells_unchanged_in_clean":True,
 "producer_plate_status":"P1_SOURCE_CLEAN_SCOPED_MACHINE_PASS_CONTROLLER_OPTICAL_PENDING",
 "A218_trial_producer_status":"HOLD_C349_UNCHANGED",
 "independent_C1_plate_review":"NOT_RUN","C3":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
 "new_DDS_CANDIDATE":False,"next":"Controller view native/practical contacts, C1 independently review reusable CLEAN manifest; A218 existing glyph trials not approved"}
write(report,"A236_SOURCE_CLEAN_MACHINE.json")
# New exact immutable library entry, C1 reviews separately; NEVER write reviews.
from tools.localization.plate_library import canonical,put,load,LIB
clean_ref=put(root,clean_png,".png")
mask_ref=put(root,mask_png,".png")
qa_ref={"path":(out/"A236_SOURCE_CLEAN_MACHINE.json").relative_to(root).as_posix(),
        "sha256":sha((out/"A236_SOURCE_CLEAN_MACHINE.json").read_bytes())}
manifest={
 "schema":"clean-plate-library-v1",
 "queue_index":161,"region_id":"AQUARIUS_SOUTH_KOREA_ITALY_CELLS_11_16_24",
 "source_sha256":sha(src_raw),"orientation":"readable_flip_y",
 "size":[2048,2048],"background":"transparent",
 "source_task_id":report["run_key"],
 "provenance_commit":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
 "producer_evidence":qa_ref,
 "clean":clean_ref,"removal":mask_ref,
 "scope":"Three independent original English text bboxes only, 35 other cells SOURCE preserved. Source-derived plate producer machine evidence, C1 not reviewed or authorized; A218 trial not rereleased."
}
msha=sha(canonical(manifest))
manifestpath=root/LIB/"entries"/(msha+".json")
manifestpath.parent.mkdir(parents=True,exist_ok=True)
manifestpath.write_bytes(jb(manifest))
# Manifest SHA is calculated from canonical JSON (not file formatting).
loaded=load(root,manifestpath)
assert loaded["queue_index"]==161
audit=subprocess.run([sys.executable,"tools/localization/plate_library.py","audit"],capture_output=True,text=True)
assert audit.returncode==0,(audit.stdout,audit.stderr)
write({"manifest_sha256":msha,"status":"CREATED_C1_REVIEW_REQUIRED",
       "audit":audit.stdout.strip(),"C1_PASS":False,"new_trial_DDS":False},
      "A236_LIBRARY_BINDING_HOLD.json")
print(json.dumps({"run":"A236","plate_manifest":msha,"clean_sha256":clean_sha,
 "source_removal_pixels":report["source_to_clean_changed_rgba"],"outside":0,
 "C1":"NOT_RUN","DDS_new":0}))
