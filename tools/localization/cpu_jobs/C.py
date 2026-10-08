#!/usr/bin/env python3
"""C307 C2 EVEN q230: exact SHA native source/previously-authored clean/final visual proof.
Worker produces pixel evidence only; NEVER writes queue approvals or claims C/C3 PASS.
"""
import hashlib, json, os, subprocess, urllib.request
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image,ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="C"
report=json.loads(subprocess.run(["python","tools/localization/rework_triage.py","--index","230"],capture_output=True,text=True,check=True).stdout)
assert report["assets"][0]["next_action"]=="EVIDENCE_ONLY_HOLD",report
Q=Path("localization/graphics/asset_queue.csv").read_text(encoding="utf-8-sig")
assert "230,textures/load/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds,localize_text,c301_c2_c3_hold" in Q
URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds"
srcb=urllib.request.urlopen(URL,timeout=180).read()
finb=Path("localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds").read_bytes()
cleanb=Path("localization/graphics/role_B/20261007-B-MANUALQA228-E95DA5-HELP/B228_E95_HELP_CLEAN_PLATE.png").read_bytes()
sha=lambda v:hashlib.sha256(v).hexdigest()
SHA={"source":"33077919771f580491b8ea1011401dc22df640f87b5b0e6f602b112dbdb07b81",
     "candidate":"a680ae4b7b7c48e2e6200ca766431a725e189297c6acf31badf677b98270428f",
     "authored_clean":sha(cleanb)}
assert sha(srcb)==SHA["source"] and sha(finb)==SHA["candidate"]
assert len(srcb)==len(finb)==8388736 and srcb[:128]==finb[:128], "different DDS header"
src=np.flipud(np.asarray(Image.open(BytesIO(srcb)).convert("RGBA"))).copy()
fin=np.flipud(np.asarray(Image.open(BytesIO(finb)).convert("RGBA"))).copy()
clean=np.asarray(Image.open(BytesIO(cleanb)).convert("RGBA")).copy()
assert src.shape==fin.shape==clean.shape==(1024,2048,4)
specs=[
 ("20_unavailable_help","You cannot buy this item yet","아직 구매할 수 없습니다",(1,182,618,232)),
 ("21_owned_help","You already own this item","이미 보유 중입니다",(867,182,1422,232))]
allowed=np.zeros(src.shape[:2],dtype=bool)
for _,_,_,(l,t,r,b) in specs:allowed[t:b,l:r]=True
out=Path("localization/graphics/role_C/20261008-C307-C2-Q230-PLATE-COMPOSITE-NATIVE")
out.mkdir(parents=True,exist_ok=True)
def composite(arr,color):
 aa=Image.fromarray(arr,"RGBA")
 return Image.alpha_composite(Image.new("RGBA",aa.size,color+(255,)),aa).convert("RGB")
def write(img,name):
 p=out/name
 img.save(p,format="PNG")
 return {"path":str(p),"sha256":sha(p.read_bytes()),"bytes":p.stat().st_size}
def bbox_alpha(arr,threshold=0):
 yy,xx=np.where(arr[:,:,3]>threshold)
 return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)] if len(xx) else None
rows=[]
for rid,en,ko,(l,t,r,b) in specs:
 s=src[t:b,l:r].copy();c=clean[t:b,l:r].copy();f=fin[t:b,l:r].copy()
 sr=bbox_alpha(s,0);fr=bbox_alpha(f,0)
 assert sr is not None and fr is not None
 margin=[fr[0],(r-l)-fr[2],fr[1],(b-t)-fr[3]]
 items=[]
 for bgname,color in [("BLACK",(12,12,12)),("GRAY",(104,104,104)),("WHITE",(245,245,245))]:
  panel=Image.new("RGB",((r-l)*3,(b-t)+30),(25,25,25))
  d=ImageDraw.Draw(panel)
  for idx,(label,ar) in enumerate((("ENGLISH SOURCE",s),("AUTHORED CLEAN",c),("KOREAN DDS",f))):
   panel.paste(composite(ar,color),(idx*(r-l),30))
   d.text((idx*(r-l)+4,7),label,fill=(255,255,255))
  for ratio in [100,75,50]:
   pic=panel if ratio==100 else panel.resize((max(1,int(panel.width*ratio/100)),max(1,int(panel.height*ratio/100))),Image.Resampling.LANCZOS)
   items.append({**write(pic,f"{rid}_{bgname}_{ratio}pct_SOURCE_CLEAN_FINAL.png"),"background":bgname,"scale":ratio})
 # RAW orientation is exact DDS inverse Y for both source and candidate.
 rawpanel=Image.new("RGB",((r-l)*2,(b-t)+30),(25,25,25))
 rd=ImageDraw.Draw(rawpanel)
 for idx,(label,arr) in enumerate((("SOURCE RAW",np.flipud(s)),("CANDIDATE RAW",np.flipud(f)))):
  rawpanel.paste(composite(arr,(104,104,104)),(idx*(r-l),30));rd.text((idx*(r-l)+4,7),label,fill=(255,255,255))
 rawref=write(rawpanel,f"{rid}_RAW_SOURCE_FINAL.png")
 # 2x scale nearest to reveal missing strokes and antialias clusters, not proof of native-resolution game rendering.
 native=Image.new("RGB",((r-l)*2,(b-t)),(104,104,104))
 native.paste(composite(s,(245,245,245)),(0,0));native.paste(composite(f,(245,245,245)),(r-l,0))
 zoom=write(native.resize((native.width*2,native.height*2),Image.Resampling.NEAREST),f"{rid}_ZOOM200_SOURCE_FINAL.png")
 rows.append({"id":rid,"english":en,"korean":ko,"source_effect_bbox_readable":[l,t,r,b],
  "source_visible_bbox_crop":sr,"korean_visible_bbox_crop":fr,"margins_lrtb":margin,
  "source_visible_pixels_alpha_gt16":int(np.count_nonzero(s[:,:,3]>16)),
  "korean_visible_pixels_alpha_gt16":int(np.count_nonzero(f[:,:,3]>16)),
  "clean_nonzero_alpha_pixels":int(np.count_nonzero(c[:,:,3]>0)),
  "source_clean_changed_RGBA":int(np.count_nonzero(np.any(s!=c,axis=2))),
  "clean_candidate_changed_RGBA":int(np.count_nonzero(np.any(c!=f,axis=2))),
  "source_candidate_changed_RGBA":int(np.count_nonzero(np.any(s!=f,axis=2))),
  "native_and_practical_proofs":items,"raw":rawref,"zoom_200":zoom,
  "native_pixel_evidence_only_not_visual_pass":True})
 # no automated approval inferred even for all positive margins.
rawmirror=bool(np.array_equal(np.flipud(np.flipud(np.asarray(Image.open(BytesIO(srcb)).convert("RGBA")))),src))
outside_c_f=int(np.count_nonzero(np.any(clean!=fin,axis=2)&~allowed))
outside_alpha=int(np.count_nonzero((clean[:,:,3]!=fin[:,:,3])&~allowed))
outside_visible=int(np.count_nonzero(((clean[:,:,3]>0)|(fin[:,:,3]>0))&np.any(clean!=fin,axis=2)&~allowed))
machine={"role":"C","run":"C307-C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":230,
 "policy_version":"visual-evidence-v1-20261008","triage":report["assets"][0],
 "source_commit":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
 "authored_clean_provenance":"B228_E95_HELP_CLEAN_PLATE.png carries earlier B73 localized regions; clean-vs-final only is full-atlas two-help scope, while source-vs-clean outside help is NOT a protected-art equivalence test.",
 "SHA256":SHA,"dds_header_128_identical":True,"dds_size":[2048,1024],"dds_mips":1,
 "full_atlas_clean_final_changed_RGBA_outside_two_help_bbox":outside_c_f,
 "full_atlas_clean_final_alpha_changed_outside_two_help_bbox":outside_alpha,
 "full_atlas_clean_final_visible_changed_outside_two_help_bbox":outside_visible,
 "regions":rows,"images_count":sum(len(z["native_and_practical_proofs"])+2 for z in rows),
 "result":"EVIDENCE_ONLY_NOT_VISUAL_APPROVAL","C":"CONTROLLER_REVIEW_REQUIRED","C3":"BLOCKED","RUNTIME_VALIDATION":"UNTESTED"}
p=out/"C307_Q230_PLATE_COMPOSITE_NATIVE_MACHINE.json";p.write_text(json.dumps(machine,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"C307-C2","triage":report["assets"][0]["next_action"],"images":machine["images_count"],
"outside_clean_final_RGBA":outside_c_f,"outside_clean_final_alpha":outside_alpha,
"clean_alpha_regions":[r["clean_nonzero_alpha_pixels"] for r in rows],
"margins":[r["margins_lrtb"] for r in rows],"output":str(out)},ensure_ascii=False))
