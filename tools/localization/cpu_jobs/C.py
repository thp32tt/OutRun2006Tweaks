#!/usr/bin/env python3
"""C314 C1 ODD q161: first independent 38-region exact-DDS lossless presentation evidence.

No approval via code; screenshot controls must be interpreted independently.
"""
import os, io, json, hashlib, urllib.request, subprocess, struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER") == "github-actions"
assert os.getenv("OUTRUN_CPU_ROLE") == "C"
ROOT=Path.cwd()
INDEX=161
ASSET="textures/load/spr_sprani_sumo_fe_cvt_Exst/55B57CDE_512x512.dds"
P=ROOT/"localization/graphics/role_A/20261007-A-MANUALQA157-55B57CDE-HIERARCHY/A157_55B57CDE_REPORT.json"
OUT=ROOT/"localization/graphics/role_C/20261009-C314-C1-Q161-38REGION-NATIVE-PROOF"
H=lambda b:hashlib.sha256(b).hexdigest()
queue=(ROOT/"localization/graphics/asset_queue.csv").read_text(encoding="utf-8-sig")
assert "161,"+ASSET+",localize_text,c273_hold_strict_recheck_pixels_first_lossless_region_evidence" in queue,"q161 queue changed"
tri=json.loads(subprocess.check_output(["python","tools/localization/rework_triage.py","--index","161"],text=True))["assets"][0]
assert tri["next_action"]=="EVIDENCE_ONLY_HOLD",tri
A=json.loads(P.read_text(encoding="utf-8"))
assert len(A["elements"])==38
expected_source="a74d31016e9ab38da4f6bd9a37196848534b9a1c8ac04db3f071000030681c4d"
expected_current="66a893853d812ff1bad90a5838d33876847bf0b677ee2ba48f76a0f24e9e772d"
assert A["source_provenance"]["sha256"]==expected_source and A["candidate_sha256"]==expected_current
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/55B57CDE_512x512.dds"
source=urllib.request.urlopen(url,timeout=180).read()
final=(ROOT/"localization/graphics/hd_candidates"/ASSET).read_bytes()
assert H(source)==expected_source and H(final)==expected_current
assert len(source)==len(final)==4194432 and source[:128]==final[:128]
def decode(buf):
 assert buf[:4]==b"DDS " and buf[84:88]==b"DXT5"
 h,w=struct.unpack_from("<II",buf,12)
 m=struct.unpack_from("<I",buf,28)[0]
 assert (w,h,m)==(2048,2048,1)
 return Image.open(io.BytesIO(buf)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src=decode(source);fin=decode(final)
S=np.asarray(src);F=np.asarray(fin)
assert S.shape==F.shape==(2048,2048,4)
OUT.mkdir(parents=True,exist_ok=True)
union=np.zeros((2048,2048),dtype=bool)
for e in A["elements"]:
 l,t,r,b=e["original_bbox"]
 assert 0<=l<r<=2048 and 0<=t<b<=2048
 union[t:b,l:r]=True
difference=np.any(S!=F,axis=2)
outside=int(np.count_nonzero(difference&~union))
outside_alpha=int(np.count_nonzero((S[:,:,3]!=F[:,:,3])&~union))
assert outside==0 and outside_alpha==0,(outside,outside_alpha)
def vis(im,background):
 bg=Image.new("RGBA",im.size,(*background,255));bg.alpha_composite(im);return bg.convert("RGB")
rows=[]; manifests=[]
def add(fp):
 manifests.append({"path":str(fp.relative_to(ROOT)),"sha256":H(fp.read_bytes()),"size_bytes":fp.stat().st_size})
for e in A["elements"]:
 i=int(e["idx"]);l,t,r,b=e["original_bbox"]
 old=e["prior_localized_bbox"];new=e["localized_bbox"]
 assert l<=new[0]<new[2]<=r and t<=new[1]<new[3]<=b
 pad=8; x0=max(0,l-pad);y0=max(0,t-pad);x1=min(2048,r+pad);y1=min(2048,b+pad)
 bb=(x0,y0,x1,y1)
 ss=src.crop(bb);ff=fin.crop(bb)
 pfx=f"q161_{i:02d}"
 for stage,img in (("SOURCE",ss),("CURRENT",ff)):
  file=OUT/f"{pfx}_{stage}_READABLE_NATIVE.png";img.save(file);add(file)
 panels=[];labels=[]
 for cname,color in (("BLACK",(0,0,0)),("GRAY",(127,127,127)),("WHITE",(245,245,245))):
  panels.extend([vis(ss,color),vis(ff,color)])
  labels.extend([f"EN {cname}",f"KO {cname}"])
 w,h=panels[0].size
 sheet=Image.new("RGB",(w*2+8,h*3+66),"white")
 dr=ImageDraw.Draw(sheet)
 for k,p in enumerate(panels):
  x=(k%2)*(w+8);y=(k//2)*(h+22)
  dr.text((x+3,y+3),labels[k],fill="black")
  sheet.paste(p,(x,y+19))
 file=OUT/f"{pfx}_SOURCE_CURRENT_BGW_NATIVE.png";sheet.save(file);add(file)
 # Exact native individual PNGs above; practical + RAW are additional views.
 ss50=vis(ss,(127,127,127)).resize((max(1,w//2),max(1,h//2)),Image.Resampling.LANCZOS)
 ff50=vis(ff,(127,127,127)).resize((max(1,w//2),max(1,h//2)),Image.Resampling.LANCZOS)
 practical=Image.new("RGB",(ss50.width*2+8,ss50.height+25),"white")
 d=ImageDraw.Draw(practical);d.text((3,3),"EN",fill="black");d.text((ss50.width+11,3),"KO",fill="black")
 practical.paste(ss50,(0,25));practical.paste(ff50,(ss50.width+8,25))
 file=OUT/f"{pfx}_SOURCE_CURRENT_PRACTICAL50.png";practical.save(file);add(file)
 # RAW means exact mirror-Y of the full DDS, then extraction from equivalent mirrored coordinates.
 ys=2048-y1; ye=2048-y0
 sraw=src.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop((x0,ys,x1,ye))
 fraw=fin.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop((x0,ys,x1,ye))
 assert np.array_equal(np.asarray(sraw),np.flipud(np.asarray(ss)))
 assert np.array_equal(np.asarray(fraw),np.flipud(np.asarray(ff)))
 raw=Image.new("RGB",(2*w+8,h+25),"white")
 d=ImageDraw.Draw(raw);d.text((3,3),"EN RAW",fill="black");d.text((w+11,3),"KO RAW",fill="black")
 raw.paste(vis(sraw,(127,127,127)),(0,25));raw.paste(vis(fraw,(127,127,127)),(w+8,25))
 file=OUT/f"{pfx}_SOURCE_CURRENT_RAW.png";raw.save(file);add(file)
 # Native cropped alpha is not equal to changed-text mask; score with exact changed RGBA.
 region_difference=difference[t:b,l:r]
 outside_row_bbox=int(np.count_nonzero(difference[y0:y1,x0:x1]&~((np.indices((y1-y0,x1-x0))[0]>=t-y0)&(np.indices((y1-y0,x1-x0))[0]<b-y0)&(np.indices((y1-y0,x1-x0))[1]>=l-x0)&(np.indices((y1-y0,x1-x0))[1]<r-x0))))
 rows.append({"id":f"{i:02d}","english":e["source"],"korean":e["korean"],"original_bbox":e["original_bbox"],
  "candidate_bbox_from_A157":new,"prior_bbox_from_A56":old,
  "source_width":r-l,"korean_width":new[2]-new[0],
  "source_height":b-t,"korean_height":new[3]-new[1],
  "width_ratio":round((new[2]-new[0])/(r-l),4),
  "height_ratio":round((new[3]-new[1])/(b-t),4),
  "glyph_count":len(e["korean"].replace(" ","")),"horizontal_scale_from_producer":e["horizontal_scale"],
  "region_changed_RGBA":int(np.count_nonzero(region_difference)),
  "framing_changed_outside_original_bbox":outside_row_bbox,
  "margin":[new[0]-l,r-new[2],new[1]-t,b-new[3]],
  "native_scope_png":pfx+"_SOURCE_CURRENT_BGW_NATIVE.png",
  "source_native":pfx+"_SOURCE_READABLE_NATIVE.png",
  "final_native":pfx+"_CURRENT_READABLE_NATIVE.png",
  "practical50_png":pfx+"_SOURCE_CURRENT_PRACTICAL50.png",
  "raw_png":pfx+"_SOURCE_CURRENT_RAW.png"})
assert len(rows)==38
assert all(v["framing_changed_outside_original_bbox"]==0 for v in rows)
assert all(min(v["margin"])>0 for v in rows)
manifest={"run":"C314","lane":"C1","TEMP_BACKLOG_RELIEF":"C1","SHARD":"ODD(+UNINDEXED_SPECIAL)",
 "index":161,"original_sha256":expected_source,"current_sha256":expected_current,
 "original_location":url,"candidate_path":A["candidate_path"],
 "format":"DXT5/BC3","dimensions":[2048,2048],"mips":1,"raw_orientation":"mirror_y",
 "triage":tri,"changed_rgba_outside_38_original_regions":outside,
 "alpha_changed_outside_38_original_regions":outside_alpha,
 "source_clean_proof":"NOT_PRODUCED; exact authored clean plate missing, do not infer from source/candidate alpha",
 "source_family_style_calibration":"REQUIRES BLIND HUMAN REVIEW, numeric machine cannot approve",
 "native_source_candidate_images":len(manifests),
 "region_count":len(rows),"regions":rows,"sha256_manifest":manifests,
 "C":"EVIDENCE_ONLY_HOLD_PENDING_INDEPENDENT_VISUAL",
 "C3":"BLOCKED","APPROVALS":"NOT_APPROVED",
 "RUNTIME_VALIDATION":"UNTESTED","new_dds":0}
(OUT/"C314_Q161_38_REGION_MACHINE_AND_PNG_MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
print("C314_Q161_OK",json.dumps({"rows":len(rows),"new_png":len(manifests),"outside_rgba":outside,"outside_alpha":outside_alpha,
 "most_condensed":sorted([{"id":r["id"],"text":r["korean"],"scale":r["horizontal_scale_from_producer"]} for r in rows],key=lambda z:z["scale"])[:8]},ensure_ascii=False),flush=True)
