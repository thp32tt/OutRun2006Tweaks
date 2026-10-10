#!/usr/bin/env python3
"""A231 q217: restore canonical opaque red badge pixels lost by the A189 CLEAN.
Producer works only inside the 425 C1-authenticated OUTSIDE-GLYPH pixels;
Korean glyph faces are byte-identical to A189. Make immutable shared CLEAN
and source removal mask, and an unpromoted exact DDS for independent C1.
"""
import hashlib,io,json,os,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
root=Path.cwd()
sys.path.insert(0,str(root/"tools/localization"))
import plate_library as pl
run="20261011-A231-Q217-SOURCE-RED-RIM-RESTORE"
out=root/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
dump=lambda x,p: (out/p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n")
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","217"],text=True,capture_output=True)
assert tri.returncode==0,(tri.returncode,tri.stderr)
d=json.loads(tri.stdout)
assert d["assets"][0]["index"]==217,d
dump({"cmd":"python tools/localization/rework_triage.py --index 217","json":d},"A231_TRIAGE.json")
c1=json.loads((root/"localization/graphics/role_C/20261011-C1-Q217-PROTECTED-RED-BADGE-425/C1_Q217_CONTROLLER_REWORK.json").read_text())
m=json.loads((root/"localization/graphics/role_C/20261011-C1-Q217-PROTECTED-RED-BADGE-425/C1_Q217_MACHINE_425_RED_BADGE.json").read_text())
assert c1["QA_decision"]=="REWORK_REQUIRED" and c1["reason_code"]=="PROTECTED_OPAQUE_RED_BADGE_OUTER_ART_RGB_RECOLOR"
assert m["measurements"]["outside_english_tight_bbox_changes_rgba"]==425
assert m["measurements"]["outside_source_clean_rgba"]==425
assert m["measurements"]["outside_clean_final_rgba"]==0
source_sha="d3d2d15540642d8315df8b38b77a34609e534ea042bce8e7e951e65ab219bcd0"
candidate_sha="a4d817db51c31ba6e7d22121add4dfee8bc151cdb229a6091c5ea324bca78204"
clean_sha="f937fbaa7fa2e055e62c56835b52a28cc6c091640d148487cb54097008035e41"
base=root/"localization/graphics/role_A/20261008-A189-Q217-SOURCE-GOLD-ITALIC"
source_png=base/"A189_SOURCE_READABLE.png"
clean_png=base/"A189_CLEAN_PLATE.png"
assert sha(clean_png.read_bytes())==clean_sha
with Image.open(source_png) as im:src=np.array(im.convert("RGBA"),dtype=np.uint8)
with Image.open(clean_png) as im:old_clean=np.array(im.convert("RGBA"),dtype=np.uint8)
current_path=root/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/D1039D6F_512x512.dds"
old_data=current_path.read_bytes()
assert sha(old_data)==candidate_sha and old_data[:4]==b"DDS "
assert len(old_data)==128+2048*2048*4
with Image.open(io.BytesIO(old_data)) as im:cur=np.array(im.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM),dtype=np.uint8)
assert cur.shape==old_clean.shape==src.shape==(2048,2048,4)
# Shared plate lookup is deliberately empty for q217; do not reuse q060.
matches=list((root/"localization/graphics/plate_library/entries").glob("*.json"))
for pp in matches:
  plate=pl.load(root,pp)
  assert not(plate["queue_index"]==217 and plate["source_sha256"]==source_sha and
    plate["region_id"]=="START_GOAL" and plate["orientation"]=="readable_flip_y"),"Existing q217 CLEAN: reuse rather than remake"
row=[]
outside_all=np.zeros((2048,2048),dtype=bool)
inside_all=np.zeros((2048,2048),dtype=bool)
diffSC=np.any(src!=old_clean,axis=2)
diffSF=np.any(src!=cur,axis=2)
diffCF=np.any(old_clean!=cur,axis=2)
for item in m["measurements"]["per_label"]:
 name=item["id"]
 x0,y0,x1,y1=item["source_bbox"]
 bx0,by0,bx1,by1=item["check_bbox"]
 roi=np.zeros((2048,2048),dtype=bool)
 roi[by0:by1,bx0:bx1]=True
 interior=np.zeros((2048,2048),dtype=bool)
 interior[y0:y1,x0:x1]=True
 outside=roi&~interior&diffSC
 assert int(outside.sum())==item["outside_changed"],(name,int(outside.sum()),item["outside_changed"])
 assert not np.any(outside&outside_all)
 assert not np.any(outside&diffCF),name
 assert np.array_equal(diffSC[outside],diffSF[outside])
 assert np.all(src[:,:,3][outside]==255) and np.all(cur[:,:,3][outside]==255),name
 outside_all|=outside
 inside_all|=interior
 row.append({"region":name,"source_bbox":[x0,y0,x1,y1],
             "scope_bbox":[bx0,by0,bx1,by1],"new_restored_pixels":int(outside.sum()),
             "restored_changed_alpha":0})
assert int(outside_all.sum())==425
assert int((diffSC&~inside_all).sum())==425,"Unexpected plate source changes beyond the 425 sanctioned pixels"
assert int((diffCF&~inside_all).sum())==0,"New glyph effect outside original bbox needs separate classification"
new_clean=old_clean.copy();new_clean[outside_all]=src[outside_all]
new_final=cur.copy();new_final[outside_all]=src[outside_all]
assert int(np.count_nonzero(np.any(src!=new_clean,axis=2)&~inside_all))==0
assert np.array_equal(new_final[~outside_all],cur[~outside_all])
assert np.array_equal(new_clean[~outside_all],old_clean[~outside_all])
assert int(np.count_nonzero(np.any(src!=new_final,axis=2)&~inside_all))==0
assert np.array_equal(new_clean[outside_all],src[outside_all])
assert np.array_equal(new_final[outside_all],src[outside_all])
# Plate means source conditioned to same legitimate original English glyph
# bboxes only; keep all OTHER source art and exact source red badge rim bytes.
plate_bytes=io.BytesIO()
Image.fromarray(new_clean,mode="RGBA").save(plate_bytes,format="PNG")
plate_bytes=plate_bytes.getvalue()
new_plate_path=out/"A231_CLEAN_FULL_NATIVE_READABLE.png"
new_plate_path.write_bytes(plate_bytes)
removal=(np.any(src!=new_clean,axis=2).astype(np.uint8)*255)
assert np.count_nonzero(removal)>0 and np.count_nonzero(removal[~inside_all])==0
mask=Image.fromarray(removal,mode="L")
mask_buf=io.BytesIO();mask.save(mask_buf,format="PNG")
mask_path=out/"A231_AUTHORED_ORIGINAL_GLYPH_ONLY_MASK_NATIVE.png"
mask_path.write_bytes(mask_buf.getvalue())
Image.fromarray(outside_all.astype(np.uint8)*255,mode="L").save(out/"A231_RESTORED_425_PROTECTED_MASK_NATIVE.png")
# Identify exact DDS raw component order; wrong-packing must abort publication.
def raw_offset(y,x):return 128+((2047-y)*2048+x)*4
probes=[(int(y),int(x)) for y,x in list(zip(*np.nonzero(outside_all)))[:12]]
test_order=None
for ordering in ("RGBA","BGRA","ARGB","ABGR"):
 def ordered(pixel):return bytes(pixel["RGBA".index(ch)] for ch in ordering)
 if all(old_data[raw_offset(y,x):raw_offset(y,x)+4]==ordered(cur[y,x]) for y,x in probes):
  test_order=ordering;break
assert test_order is not None,"Unknown DDS channel packing; refuse byte patch"
after=bytearray(old_data)
yy,xx=np.nonzero(outside_all)
for y,x in zip(yy,xx):
 pix=src[y,x];start=raw_offset(int(y),int(x))
 after[start:start+4]=bytes(int(pix["RGBA".index(ch)]) for ch in test_order)
after=bytes(after)
assert after[:128]==old_data[:128] and len(after)==len(old_data) and sha(after)!=candidate_sha
trialpath=out/"A231_Q217_RED_RIM_RESTORED_UNPROMOTED.dds"
trialpath.write_bytes(after)
with Image.open(trialpath) as im:redecoded=np.array(im.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
assert np.array_equal(redecoded,new_final),"Persisted DDS mismatched intended RGBA"
origraw=np.frombuffer(old_data[128:],np.uint8).reshape(2048,2048,4)
newraw=np.frombuffer(after[128:],np.uint8).reshape(2048,2048,4)
changeRaw=np.any(origraw!=newraw,axis=2)
assert np.array_equal(changeRaw,outside_all[::-1])
assert int(changeRaw.sum())==425
assert np.array_equal(new_final[:,:,3],cur[:,:,3]),"alpha changed unexpectedly"
# Native and practical full-glyph/source-red plate proofs. All source changes
# outside text bboxes are fully restored before potentially new lettering.
def opaque(image,bg):
 color=Image.new("RGBA",image.size,bg+(255,))
 return Image.alpha_composite(color,image).convert("RGB")
evidence=[]
for i,item in enumerate(row):
 name=item["region"]; x0,y0,x1,y1=item["scope_bbox"]
 imgs=[Image.fromarray(im[y0:y1,x0:x1],"RGBA") for im in (src,old_clean,new_clean,cur,new_final)]
 for bgname,bg in [("GRAY",(110,110,110)),("BLACK",(0,0,0)),("WHITE",(255,255,255))]:
  for pct in (100,75,50):
   tiles=[opaque(im,bg) for im in imgs]
   if pct!=100:tiles=[v.resize((round(v.width*pct/100),round(v.height*pct/100)),Image.Resampling.LANCZOS) for v in tiles]
   w,h=tiles[0].size
   canvas=Image.new("RGB",(w*5,h+23),bg)
   d=ImageDraw.Draw(canvas)
   for j,(title,v) in enumerate(zip(("EN_SOURCE","OLD_CLEAN","RESTORED_CLEAN","OLD_KO","NEW_KO"),tiles)):
    canvas.paste(v,(j*w,23))
    d.text((j*w+1,3),title,fill="black" if bgname=="WHITE" else "white")
   path=out/f"A231_{name}_{bgname}_{pct}.png"
   canvas.save(path)
   evidence.append(str(path.relative_to(root)))
 Image.fromarray(new_final[y0:y1,x0:x1],"RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(out/f"A231_{name}_RAW.png")
# Assert exact removal mask includes ONLY source bbox; source->clean changes are
# isolated text effects, not broad rectangular red badge recoloring.
qa={
 "run":"A231","run_key":"OUTRUN-KOR-A231-Q217-C1-RED-BADGE-425-PROTECTED-RGB-RESTORE-20261011-0310",
 "role":"A","queue_index":217,"source_sha256":source_sha,
 "source_png_sha256":sha(source_png.read_bytes()),
 "previous_official_sha256":candidate_sha,
 "prior_clean_sha256":clean_sha,
 "new_clean_sha256":sha(plate_bytes),"new_trial_sha256":sha(after),
 "canonical_source":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
 "native_format":"2048x2048 RGBA32 mip1, raw mirror_y",
 "raw_channel_order":test_order,
 "rows":row,"source_opaque_protected_pixels_restored":425,
 "source_clean_rgba_outside_both_original_text_boxes":0,
 "source_final_rgba_outside_both_original_text_boxes":0,
 "prior_official_to_trial_changed_rgba":425,
 "prior_official_to_trial_changed_alpha":0,
 "prior_official_to_trial_changed_other_atlas":0,
 "redecoded_rgba_exact":True,"DDS_header_exact":True,
 "source_red_rim_restored_from_original_bytes":True,
 "korean_rendering_preserved_exact_unchanged":True,
 "clean_bounded_removal_pixels":int(np.count_nonzero(removal)),
 "clean_plate_stage":"P1_BOUNDED_SOURCE_CONDITIONED_MACHINE_PASS_VISUAL_REVIEW_REQUIRED",
 "producer_optical":"PENDING_CONTROLLER_FIRSTHAND",
 "independent_C1":"PENDING","C3":"NOT_RUN","USER_GAME":"NOT_TESTED",
 "official_candidate_updated":False,"new_trial_dds_count":1,
 "RUNTIME_VALIDATION":"UNTESTED","evidence":evidence,
 "excluded":["VR","FFB","DX11","DXVK"]
}
dump(qa,"A231_MACHINE_QA.json")
# Immutable reusable CLEAN is production input only. Store no fabricated
# C1 PLATE_PASS; actual C1 must independently inspect the manifest and bytes.
ev=out/"A231_MACHINE_QA.json"
evidence_ref={"path":ev.relative_to(root).as_posix(),"sha256":sha(ev.read_bytes())}
clean_ref=pl.put(root,plate_bytes,".png")
mask_ref=pl.put(root,mask_buf.getvalue(),".png")
manifest={
 "schema":pl.VERSION,"queue_index":217,"region_id":"START_GOAL",
 "source_sha256":source_sha,"orientation":"readable_flip_y",
 "size":[2048,2048],"background":"opaque_red_badge",
 "source_task_id":qa["run_key"],
 "provenance_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
 "producer_evidence":evidence_ref,"clean":clean_ref,"removal":mask_ref,
 "scope":"START/GOAL only, source-exact rim restoration 425, trial only; no independent C1 review/approval"
}
manifest_sha=sha(pl.canonical(manifest))
entry=root/"localization/graphics/plate_library/entries"/(manifest_sha+".json")
pl.immutable(entry,json.dumps(manifest,ensure_ascii=False,indent=2).encode()+b"\n")
pl.load(root,entry)
dump({"manifest_sha256":manifest_sha,"entry":str(entry.relative_to(root)),
      "plate_C1":"UNREVIEWED","candidate_C1":"UNREVIEWED",
      "source_exact_protected_rgb_restored":425,"trial":str(trialpath.relative_to(root)),
      "trial_sha256":sha(after)},"A231_PUBLISH_RESULT.json")
print(json.dumps({"A231":"NEW_Q217_RED_RIM_TRIAL","restored":425,
 "trial_sha":sha(after),"new_plate_manifest":manifest_sha,"approval":"HOLD_C1",
 "official_promoted":0}))
