#!/usr/bin/env python3
"""C2 q172 exact persisted B255 DDS evidence for source-family review; evidence only."""
import hashlib, io, json, os, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="C"
base=Path(".")
out=base/"localization/graphics/role_C/20261008-C291-C2-Q172-B255-SOURCE-FAMILY"
out.mkdir(parents=True,exist_ok=True)
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","172"],capture_output=True,text=True,check=True)
triage_report=json.loads(triage.stdout)
assert len(triage_report["assets"])==1 and triage_report["assets"][0]["index"]==172 and triage_report["assets"][0]["next_action"]=="EVIDENCE_ONLY_HOLD", t
(out/"C291_Q172_TRIAGE.json").write_text(json.dumps(t,ensure_ascii=False,indent=2)+"\n")
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
with urllib.request.urlopen(source_url,timeout=120) as f: source_bytes=f.read()
candidate=base/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
producer=base/"localization/graphics/role_B/20261008-B255-Q172-EXPLICIT-KOREAN-FONT-SHEAR"
final_bytes=candidate.read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
expected_source="d5f4a36d5ef1285555ca8fc045e54d160876d1b3e33c6fbc45668c24566c2cf8"
expected_final="7282687bbc3f5b4e7ea45c03043d84b27204a5b183a8eaa9a08c35bb63eb84e2"
assert sha(source_bytes)==expected_source
assert sha(final_bytes)==expected_final,sha(final_bytes)
assert source_bytes[:128]==final_bytes[:128]
def decode_bytes(b):return np.array(Image.open(io.BytesIO(b)).convert("RGBA"))
src_raw=decode_bytes(source_bytes);final_raw=decode_bytes(final_bytes)
src=np.flipud(src_raw).copy();fin=np.flipud(final_raw).copy()
clean=np.array(Image.open(producer/"CLEAN.png").convert("RGBA"))
src_producer=np.array(Image.open(producer/"SOURCE.png").convert("RGBA"))
fin_producer=np.array(Image.open(producer/"FINAL.png").convert("RGBA"))
assert src.shape==fin.shape==clean.shape==(1024,1024,4)
raw_match_source=bool(np.array_equal(src,src_producer))
raw_match_final=bool(np.array_equal(fin,fin_producer))
def changed(a,b):return np.any(a!=b,axis=2)
bboxes=[("start","START","출발",(55,373,136,396)),("goal","GOAL","골",(595,635,672,659))]
allowed=np.zeros((1024,1024),bool)
for _,_,_,(x0,y0,x1,y1) in bboxes:allowed[y0:y1,x0:x1]=1
rgbo=int(np.count_nonzero(changed(src,fin)&~allowed))
alphao=int(np.count_nonzero((src[...,3]!=fin[...,3])&~allowed))
cleano=int(np.count_nonzero(changed(src,clean)&~allowed))
clean_alpha_out=int(np.count_nonzero((src[...,3]!=clean[...,3])&~allowed))
def flatten(a,bg):
 alpha=a[...,3:4].astype(np.uint16);rgb=a[...,:3].astype(np.uint16)
 return ((rgb*alpha+bg*(255-alpha)+127)//255).astype(np.uint8)
def bb(mask):
 yy,xx=np.where(mask)
 return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
rows=[]
for name,en,ko,b in bboxes:
 x0,y0,x1,y1=b; pad=14;l=max(0,x0-pad);t=max(0,y0-pad);r=min(1024,x1+pad);bottom=min(1024,y1+pad)
 arrays=[a[t:bottom,l:r] for a in (src,clean,fin)]
 for tag,a in zip(("ORIGINAL_ENGLISH","B255_AUTHORED_CLEAN","PERSISTED_B255_KOREAN"),arrays):
  Image.fromarray(a).save(out/f"{name}_{tag}.png")
 for bg,cname in [(0,"BLACK"),(128,"GRAY"),(255,"WHITE")]:
  images=[Image.fromarray(flatten(a,bg)) for a in arrays]
  w,h=images[0].size
  contact=Image.new("RGB",(3*w,h+22),(45,45,45));d=ImageDraw.Draw(contact)
  for k,(im,title) in enumerate(zip(images,("ORIGINAL","B255 CLEAN","PERSISTED B255"))):
   contact.paste(im,(w*k,22));d.text((w*k+2,3),title,fill="white")
  contact.save(out/f"{name}_{cname}_CONTACT_NATIVE.png")
  if cname=="GRAY":
   contact.resize((contact.width*6,contact.height*6),Image.Resampling.NEAREST).save(out/f"{name}_GRAY_CONTACT_6X.png")
   for pct in (75,50):
    contact.resize((round(contact.width*pct/100),round(contact.height*pct/100)),Image.Resampling.LANCZOS).save(out/f"{name}_PRACTICAL_{pct}.png")
 # raw location = H - bottom : H - top
 Image.fromarray(src_raw[1024-bottom:1024-t,l:r]).save(out/f"{name}_ORIGINAL_RAW.png")
 Image.fromarray(final_raw[1024-bottom:1024-t,l:r]).save(out/f"{name}_CURRENT_RAW.png")
 region_src=src[y0:y1,x0:x1];region_fin=fin[y0:y1,x0:x1];region_clean=clean[y0:y1,x0:x1]
 # Source clean plate comparison is an effect delta, not glyph-only source bbox.
 src_effect=changed(region_src,region_clean);new_effect=changed(region_fin,region_clean)
 new_bbox=bb(new_effect)
 if new_bbox:new_bbox=[new_bbox[0]+x0,new_bbox[1]+y0,new_bbox[2]+x0,new_bbox[3]+y0]
 # Actual all-pixel drawing provenance, interior RGB and alpha; these metrics are
 # descriptive, not aesthetic acceptance thresholds.
 rows.append({"id":name,"english":en,"korean":ko,"source_effect_bbox":list(b),"source_vs_clean_pixels":int(src_effect.sum()),
 "candidate_vs_clean_pixels":int(new_effect.sum()),"candidate_vs_clean_bbox":new_bbox,
 "source_to_candidate_changes_inside":int(changed(region_src,region_fin).sum()),
 "source_bright_face_pixels_rgb_min_ge_205_alpha_ge_16":int(((region_src[...,:3].min(2)>=205)&(region_src[...,3]>=16)).sum()),
 "candidate_bright_face_pixels_rgb_min_ge_205_alpha_ge_16":int(((region_fin[...,:3].min(2)>=205)&(region_fin[...,3]>=16)).sum()),
 "actual_glyph_only_bbox":"UNMEASURED; source effect plate and clean comparison cannot certify precise glyph bounds",
 "raw_bbox":[l,1024-bottom,r,1024-t],
 "evidence":{k:f"{name}_{k}_CONTACT_NATIVE.png" for k in ("BLACK","GRAY","WHITE")},
 "zoom":f"{name}_GRAY_CONTACT_6X.png","practical50":f"{name}_PRACTICAL_50.png","raw":f"{name}_CURRENT_RAW.png"})
rep={"schema_version":1,"run":"C291","role":"C","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":172,
"source_provenance":source_url,"source_sha256":expected_source,"candidate_sha256":expected_final,
"clean_plate_path":str(producer/"CLEAN.png"),"clean_plate_sha256":sha((producer/"CLEAN.png").read_bytes()),
"native_dimensions":[1024,1024],"format":"RGBA32","raw_orientation":"mirror_y",
"source_candidate_dds_header_exact":True,"producer_source_png_exact_matches_persisted_source_decode":raw_match_source,
"producer_final_png_exact_matches_persisted_candidate_decode":raw_match_final,
"source_to_candidate_RGBA_outside_two_boxes":rgbo,"source_to_candidate_alpha_outside_two_boxes":alphao,
"source_to_authored_clean_RGBA_outside_two_boxes":cleano,"source_to_authored_clean_alpha_outside_two_boxes":clean_alpha_out,
"region_notes":rows,"triage_result":triage_report["assets"][0],"C_result":"PENDING_CONTROLLER_NEW_STYLE_INSPECTION",
"C3":"BLOCKED_PENDING_COMPLETE_C_EVIDENCE","runtime_validation":"UNTESTED"}
(out/"C291_Q172_NATIVE_MACHINE.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
print("C291 q172",expected_final,"SRC_PNG",raw_match_source,"FIN_PNG",raw_match_final,"outside",rgbo,alphao,"clean outside",cleano,clean_alpha_out)
