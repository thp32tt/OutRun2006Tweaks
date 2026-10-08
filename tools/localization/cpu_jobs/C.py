#!/usr/bin/env python3
"""C310 C2 EVEN q98 fresh independent byte-bound native BC3 SOURCE/CLEAN/FINAL QA evidence.
Do not infer C PASS/C3 approval from machine metrics or producer reports.
"""
import hashlib,io,json,os,subprocess,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="C"
triage=json.loads(subprocess.run(["python","tools/localization/rework_triage.py","--index","98"],capture_output=True,text=True,check=True).stdout)["assets"][0]
assert triage["next_action"]=="FRESH_C_REVIEW",triage
queue=Path("localization/graphics/asset_queue.csv").read_text(encoding="utf-8-sig")
assert "98,textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds,localize_text,b279_producer_self_qa_pass_pending_fresh_c2_c3" in queue
c=Path("localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds").read_bytes()
cleanp=Path("localization/graphics/role_B/20261008-B279-Q098-NAVY-KEYLINE-WEIGHT/B279_AUTHORED_CLEAN_PLATE.png")
cleanb=cleanp.read_bytes()
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
s=urllib.request.urlopen(url,timeout=150).read()
sha=lambda b:hashlib.sha256(b).hexdigest()
expected={"source":"3b3cdd76b03014e0ba6a47f4e98a187fdf6ae4297314494cbe1d3d4c586f1f59",
"candidate":"192d627428dfa4328035d5105dcfbd4395d8bbadfa154a9f533a1c48583eac4b",
"clean":"b5c9c07a2490abd055153f750b415193eb84ef14c298b3e3873fd915db3af9e8"}
assert (sha(s),sha(c),sha(cleanb))==(expected["source"],expected["candidate"],expected["clean"])
assert s[:128]==c[:128] and c[84:88]==b"DXT5" and len(s)==len(c)==262272
S=np.flipud(np.asarray(Image.open(io.BytesIO(s)).convert("RGBA"))).copy()
C=np.asarray(Image.open(io.BytesIO(cleanb)).convert("RGBA")).copy()
F=np.flipud(np.asarray(Image.open(io.BytesIO(c)).convert("RGBA"))).copy()
assert S.shape==C.shape==F.shape==(128,2048,4)
allowed_source=np.zeros((128,2048),dtype=bool);allowed_source[6:123,431:1674]=True
allowed_target=np.zeros_like(allowed_source);allowed_target[11:116,580:1524]=True
def bbox(a):
 y,x=np.where(a[:,:,3]>16)
 return [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)] if len(x) else None
original=bbox(S);final=bbox(F)
def violation(a,b,mask):
 delta=np.any(a!=b,axis=2)
 return {"RGBA":int(np.count_nonzero(delta & ~mask)),
 "alpha":int(np.count_nonzero((a[:,:,3]!=b[:,:,3]) & ~mask)),
 "visible":int(np.count_nonzero(delta & ~mask & ((a[:,:,3]>0)|(b[:,:,3]>0))))}
v={"source_clean_outside_source":violation(S,C,allowed_source),
"clean_final_outside_target":violation(C,F,allowed_target),
"source_final_outside_source":violation(S,F,allowed_source)}
out=Path("localization/graphics/role_C/20261009-C310-C2-Q098-B279-FRESH-NATIVE")
out.mkdir(parents=True,exist_ok=True)
def pngsave(i,n):
 p=out/n;i.save(p,format="PNG")
 v=p.read_bytes()
 return {"path":str(p),"sha256":sha(v),"bytes":len(v)}
def composite(arr,rgb):
 i=Image.fromarray(arr,"RGBA")
 return Image.alpha_composite(Image.new("RGBA",i.size,(*rgb,255)),i).convert("RGB")
def panel(parts,bg):
 W=2048
 im=Image.new("RGB",(W*len(parts),152),(27,27,27));d=ImageDraw.Draw(im)
 for ix,(label,a) in enumerate(parts):
  im.paste(composite(a,bg),(ix*W,24));d.text((ix*W+4,5),label,fill="white")
 return im
views=[]
for color,bg in (("BLACK",(14,14,14)),("GRAY",(105,105,105)),("WHITE",(245,245,245))):
 base=panel([("PINNED ENGLISH",S),("B279 CLEAN",C),("B279 PERSISTED KR",F)],bg)
 for percent in (100,75,50):
  i=base if percent==100 else base.resize((round(base.width*percent/100),round(base.height*percent/100)),Image.Resampling.LANCZOS)
  views.append({"mode":"READABLE","background":color,"percent":percent,**pngsave(i,f"q098_{color}_{percent}_SOURCE_CLEAN_FINAL.png")})
raw=panel([("SOURCE DDS RAW",np.flipud(S)),("CANDIDATE DDS RAW",np.flipud(F))],(105,105,105))
views.append({"mode":"RAW","background":"GRAY","percent":100,**pngsave(raw,"q098_RAW_SOURCE_FINAL.png")})
white=panel([("ORIGINAL NATIVE",S),("NEW KOREAN NATIVE",F)],(245,245,245))
zoom=white.resize((white.width*2,white.height*2),Image.Resampling.NEAREST)
views.append({"mode":"ZOOM200","background":"WHITE","percent":200,**pngsave(zoom,"q098_ZOOM200_SOURCE_FINAL.png")})
for kind,parts in (("PLATE_ONLY",[("ENGLISH",S),("INDEPENDENT CLEAN",C)]),("COMPOSITE_ONLY",[("CLEAN",C),("PERSISTED KOREAN",F)])):
 views.append({"mode":kind,"background":"GRAY","percent":100,**pngsave(panel(parts,(105,105,105)),f"q098_{kind}.png")})
Sface=(S[:,:,0]>235)&(S[:,:,1]>235)&(S[:,:,2]>235)&(S[:,:,3]>16)
Fface=(F[:,:,0]>235)&(F[:,:,1]>235)&(F[:,:,2]>235)&(F[:,:,3]>16)
Snavy=(S[:,:,2]>S[:,:,0]+20)&(S[:,:,3]>16)
Fnavy=(F[:,:,2]>F[:,:,0]+20)&(F[:,:,3]>16)
report={"run":"C310-C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":98,"policy_version":"visual-evidence-v1-20261008",
 "triage":triage,"sha256":expected,"source_provenance":"Sonic-TV/OR2006Sprites@a95efe01d1f136514cef94b0d9e9fd61df021754",
 "native":[2048,128],"format":"DXT5 BC3 mip1 RAW mirrored-Y","header_exact":True,
 "alpha_nonzero_clean_in_english_region":int(np.count_nonzero(C[:,:,3][allowed_source])),
 "original_alpha_bbox":original,"new_candidate_alpha_bbox":final,
 "bounding_box_source_ceiling_pass":bool(original and final and final[0]>=original[0] and final[1]>=original[1] and final[2]<=original[2] and final[3]<=original[3]),
 "full_atlas_comparisons":v,
 "source_white_face_pixels":int(np.count_nonzero(Sface)),"candidate_white_face_pixels":int(np.count_nonzero(Fface)),
 "source_blue_greater_red_pixels":int(np.count_nonzero(Snavy)),"candidate_blue_greater_red_pixels":int(np.count_nonzero(Fnavy)),
 "color_metric_limitation":"white/navy thresholds are approximate BC3-decoded category counts, not source-family perceptual/style C approval",
 "views":views,"new_lossless_png":len(views),
 "C":"CONTROLLER_FIRST_LOOK_REQUIRED","C3":"BLOCKED","RUNTIME_VALIDATION":"UNTESTED"}
(out/"C310_Q098_MACHINE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"C310","images":len(views),"bbox":final,"limits":v,
 "clean_source_alpha":report["alpha_nonzero_clean_in_english_region"],
 "faces":[report["source_white_face_pixels"],report["candidate_white_face_pixels"]],
 "navy":[report["source_blue_greater_red_pixels"],report["candidate_blue_greater_red_pixels"]]},ensure_ascii=False))
