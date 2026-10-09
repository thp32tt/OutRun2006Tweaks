#!/usr/bin/env python3
"""B341 q212: material re-anchor of two independently rejected Korean title cells; trial."""
import os,io,hashlib,json,struct,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
P=G/"role_B/20261010-B341-Q212-PLACEMENT-REWORK"
P.mkdir(parents=True,exist_ok=True)
sha=lambda data:hashlib.sha256(data).hexdigest()
cdir=G/"role_C/20261010-C338-C2-Q212-ALL12-CURRENT-PERSISTED"
report=json.loads((cdir/"C338_Q212_CONTROLLER_C2_REWORK.json").read_text())
oldsha="e22ad5c46e81489123467783176dba1a040e0d2a36b6e6820349a9fcd87e9fea"
assert report["queue_index"]==212 and report["candidate_sha256"]==oldsha
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","212"],capture_output=True,text=True,check=True)
qa_tri=json.loads(tri.stdout)["assets"][0]
assert qa_tri["index"]==212
b=(G/"hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds").read_bytes()
assert sha(b)==oldsha
W,H=struct.unpack_from("<II",b,16)[0],struct.unpack_from("<I",b,12)[0]
assert (W,H,len(b))==(2048,2048,128+2048*2048)
assert struct.unpack_from("<IIII",b,92)==(0x00ff0000,0x0000ff00,0x000000ff,0xff000000)
def dec(v):return np.array(Image.open(io.BytesIO(v)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
O=dec(b);D=O.copy()
cp=G/"role_C/20261005-C158-BA0147DA/C158_VERIFIED_CLEAN_PLATE.png"
assert sha(cp.read_bytes())=="c13a24922d4d5e208b8c228fb51f9464d82b42442d9a14f08f7242305e314c67"
C=np.array(Image.open(cp).convert("RGBA"))
regions=[];scope=np.zeros((H,W),bool)
for idx,shift in ((43,236),(44,-61)):
 r=next(v for v in report["regions"] if v["id"]==idx)
 assert r["checks"]["placement"]["result"]=="FAIL"
 l,t,right,bottom=r["source_bbox"];x0,y0,x1,y1=r["candidate_alpha_bbox"]
 assert np.count_nonzero(C[t:bottom,l:right,3])==0
 new=(x0+shift,y0,x1+shift,y1)
 assert x0>=l and x1<=right and new[0]>l and new[2]<right
 glyph=O[y0:y1,x0:x1].copy()
 D[t:bottom,l:right]=C[t:bottom,l:right]
 D[y0:y1,new[0]:new[2]]=glyph
 assert np.array_equal(D[y0:y1,new[0]:new[2]],glyph)
 scope[t:bottom,l:right]=True
 regions.append(dict(id=idx,source_bbox=[l,t,right,bottom],old_bbox=[x0,y0,x1,y1],new_bbox=list(new),x_shift=shift))
assert np.count_nonzero(np.any(O!=D,axis=2)&~scope)==0
for r in report["regions"]:
 if r["id"] not in (43,44):
  l,t,right,bottom=r["source_bbox"]
  assert np.array_equal(D[t:bottom,l:right],O[t:bottom,l:right])
raw=b[:128]+np.flipud(D)[:,:,[2,1,0,3]].copy().tobytes()
assert len(raw)==len(b) and raw[:128]==b[:128] and np.array_equal(dec(raw),D)
(P/"B341_UNAPPROVED_Q212_TWO_ANCHOR_TRIAL.dds").write_bytes(raw)
def flatten(a,bg):
 im=Image.new("RGBA",(a.shape[1],a.shape[0]),tuple(bg)+(255,))
 im.alpha_composite(Image.fromarray(a,"RGBA"))
 return im.convert("RGB")
views=[]
for r in regions:
 id=r["id"];l,t,right,bottom=r["source_bbox"]
 src=(cdir/f"r{id}_SOURCE_CLEAN_FINAL_gray_100.png")
 exp=next(v["sha256"] for v in next(z for z in report["regions"] if z["id"]==id)["evidence"] if v["path"].endswith(src.name))
 assert sha(src.read_bytes())==exp
 original=Image.open(src).convert("RGB").crop((0,0,right-l,bottom-t))
 for orientation in ("FLIPY","RAW"):
  for scale in (100,75,50):
   bg=(128,128,128)
   panels=[original,flatten(C[t:bottom,l:right],bg),flatten(O[t:bottom,l:right],bg),flatten(D[t:bottom,l:right],bg)]
   if orientation=="RAW": panels=[im.transpose(Image.Transpose.FLIP_TOP_BOTTOM) for im in panels]
   if scale!=100:panels=[im.resize((round(im.width*scale/100),round(im.height*scale/100)),Image.Resampling.LANCZOS) for im in panels]
   out=Image.new("RGB",(sum(im.width for im in panels)+12,max(im.height for im in panels)),bg)
   pos=0
   for im in panels:out.paste(im,(pos,0));pos+=im.width+4
   name=f"r{id}_{orientation}_{scale}_SOURCE_CLEAN_OLD_TRIAL.png"
   out.save(P/name,optimize=True);views.append(str(P/name))
qa=dict(run="B341",queue_index=212,producer_decision="TRIAL_PENDING_DIRECT_VISUAL",source_historical_sha256=report["source_sha256_historical_independent_C325"],clean_sha256=sha(cp.read_bytes()),prior_candidate_sha256=oldsha,trial_sha256=sha(raw),regions=regions,other10_regions_exact=True,changed_outside_two_source_rois=0,decoded_dds_roundtrip="EXACT",source_png_provenance="C338_SHA_PINNED",native=[W,H],views=views,first_look="PENDING",promoted_dds=0,C2="PENDING",C3="BLOCKED",RUNTIME_VALIDATION="UNTESTED")
(P/"B341_TRIAL_MACHINE_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print("B341_Q212_TRIAL",qa["trial_sha256"],len(views),flush=True)
