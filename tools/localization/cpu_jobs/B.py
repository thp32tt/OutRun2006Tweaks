#!/usr/bin/env python3
"""B342 q212 P1: authenticate canonical English atlas and trial source-CLEAN layers.

New source-bound construction evidence for B341 placement-repaired trial.
Production cannot advance on C338 screenshot RGB alone: verify exact source
DDS, full region alpha, prior-candidate/clean blast radius, saved DDS and source
style. Fail closed on any mismatch. Never silently promote a trial.
"""
import os,io,sys,hashlib,struct,json,urllib.request,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
P=G/"role_B/20261010-B342-Q212-CANONICAL-SOURCE-PLATE-RECHECK"
P.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
base=G/"role_C/20261010-C338-C2-Q212-ALL12-CURRENT-PERSISTED"
rep=json.loads((base/"C338_Q212_CONTROLLER_C2_REWORK.json").read_text())
machine=json.loads((base/"C338_Q212_MACHINE_ALL12.json").read_text())
oldsha="e22ad5c46e81489123467783176dba1a040e0d2a36b6e6820349a9fcd87e9fea"
trialsha="fa0acb5629318d772eb6e7cb989e5d6840c63b3e699f51073ac201f1210b43e7"
sourcesha="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"
cleansha="c13a24922d4d5e208b8c228fb51f9464d82b42442d9a14f08f7242305e314c67"
assert rep["queue_index"]==212 and rep["candidate_sha256"]==oldsha
assert machine["candidate_sha256"]==oldsha and len(machine["regions"])==12
q=(G/"hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds").read_bytes()
trial=(G/"role_B/20261010-B341-Q212-PLACEMENT-REWORK/B341_UNAPPROVED_Q212_TWO_ANCHOR_TRIAL.dds").read_bytes()
assert sha(q)==oldsha and sha(trial)==trialsha
subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","212"],check=True,capture_output=True)
url=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
    "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/"
    "Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds")
with urllib.request.urlopen(url,timeout=100) as r: raw=r.read()
assert sha(raw)==sourcesha,(len(raw),sha(raw))
assert raw[:128]==q[:128]==trial[:128], "Source/native DDS header changed"
assert len(raw)==len(q)==len(trial)==16777344
assert struct.unpack_from("<II",raw,12)==(2048,2048)
def dec(b):
 return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S,O,T=map(dec,[raw,q,trial])
cp=G/"role_C/20261005-C158-BA0147DA/C158_VERIFIED_CLEAN_PLATE.png"
assert sha(cp.read_bytes())==cleansha
C=np.array(Image.open(cp).convert("RGBA"))
assert S.shape==O.shape==T.shape==C.shape==(2048,2048,4)
# Use all 12 exact C338 source regions. Never substitute per-glyph guessed bboxes.
regions=machine["regions"];allmask=np.zeros(S.shape[:2],bool)
for r in regions:
 l,t,rr,bb=r["source_bbox"]
 assert min(l,t)>=0 and rr<=2048 and bb<=2048
 assert not np.any(allmask[t:bb,l:rr]),"region overlap"
 allmask[t:bb,l:rr]=True
two=np.zeros(S.shape[:2],bool)
for i in (43,44):
 r=next(z for z in regions if z["id"]==i)
 l,t,rr,bb=r["source_bbox"];two[t:bb,l:rr]=True
count=lambda z:int(np.count_nonzero(z))
anydiff=lambda x,y:np.any(x!=y,axis=2)
check={
 "source_to_clean_outside_12_rgba":count(anydiff(S,C)&~allmask),
 "current_to_clean_outside_12_rgba":count(anydiff(O,C)&~allmask),
 "trial_to_source_outside_12_rgba":count(anydiff(T,S)&~allmask),
 "trial_to_current_outside_r43_r44_rgba":count(anydiff(T,O)&~two),
 "trial_to_current_outside_r43_r44_alpha":count((T[:,:,3]!=O[:,:,3])&~two),
 "clean_alpha_inside_12":count((C[:,:,3]>0)&allmask),
 "trial_changed_inside_two":count(anydiff(T,O)&two),
}
assert all(check[k]==0 for k in check if k!="trial_changed_inside_two"),check
assert check["trial_changed_inside_two"]>0
stats=[]
for r in regions:
 l,t,rr,bb=r["source_bbox"]
 a=T[t:bb,l:rr,3]
 yy,xx=np.nonzero(a)
 if not len(xx): raise AssertionError(("missing candidate label",r["id"]))
 box=(l+int(xx.min()),t+int(yy.min()),l+int(xx.max())+1,t+int(yy.max())+1)
 assert box[0]>=l and box[1]>=t and box[2]<=rr and box[3]<=bb
 assert min(box[0]-l,box[1]-t,rr-box[2],bb-box[3])>=1
 stats.append({"id":r["id"],"source_bbox":r["source_bbox"],"trial_bbox":list(box),
  "clean_alpha_nonzero":count(C[t:bb,l:rr,3]>0),"target_source_diff":count(anydiff(S[t:bb,l:rr],T[t:bb,l:rr])),
  "candidate_changed_from_old":count(anydiff(O[t:bb,l:rr],T[t:bb,l:rr]))})
# Exact SOURCE vs CLEAN remains 12-cell scoped, not whole-family typography approval.
def flatten(z,bg):
 o=Image.new("RGBA",(z.shape[1],z.shape[0]),bg+(255,))
 o.alpha_composite(Image.fromarray(z,"RGBA"))
 return o.convert("RGB")
viewpaths=[]
for r in regions:
 l,t,rr,bb=r["source_bbox"]
 for side in ("FLIPY","RAW"):
  if r["id"] not in (43,44) and side=="RAW":continue
  parts=[]
  for z in (S,C,O,T):
   rgb=flatten(z[t:bb,l:rr].copy(),(128,128,128))
   if side=="RAW":rgb=rgb.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
   parts.append(rgb)
  w=sum(im.width for im in parts)+12;hh=max(im.height for im in parts)
  out=Image.new("RGB",(w,hh),(128,128,128));dx=0
  for im in parts:
   out.paste(im,(dx,0));dx+=im.width+4
  n=f"q212_r{r['id']}_{side}_native_SOURCE_CLEAN_OLD_B341.png"
  out.save(P/n,optimize=True);viewpaths.append(str(P/n))
# Preserve authenticated canonical original bytes for independently reproducible
# P1 checks and eventual final production-manifest source binding.
original=P/"B342_EXACT_ENGLISH_SOURCE_2048_RGBA32.dds"
original.write_bytes(raw)
assert sha(original.read_bytes())==sourcesha
# Saved candidate letter layer can contain non-displayed transparent RGB.
# Determine whether exact clean+alpha composition is representable without
# changing unrelated historical approved glyph pixels; do not fake P3 PASS.
letter=T.copy();letter[~allmask]=0
composed=np.array(Image.alpha_composite(Image.fromarray(C,"RGBA"),Image.fromarray(letter,"RGBA")))
composite_difference=count(anydiff(composed,T))
check["full_clean_plus_trial_alpha_composite_rgba_mismatch_pixels"]=composite_difference
gate="P1_CANONICAL_SOURCE_CLEAN_SCOPED_PASS"
if composite_difference:gate="P1_PASS_P3_EXACT_COMPOSITE_REQUIRES_HIDDEN_RGB_RECONCILIATION"
report={
 "run":"B342","role":"B","index":212,"run_key":"OUTRUN-KOR-B342-Q212-ENGLISH-SOURCE-12-REGION-PLATE-20261010",
 "status":gate,"source_url":url,"source_sha256":sourcesha,"source_path":str(original),
 "clean_sha256":cleansha,"old_candidate_sha256":oldsha,"B341_trial_sha256":trialsha,
 "native":[2048,2048],"format":"RGBA32","mips":1,"exact_header_match":True,
 "source_clean_saved_trial_all12":stats,"counts":check,
 "view_files":viewpaths,"canonical_source_newly_verified":True,
 "source_to_clean_visual_approval":"PENDING_CONTROLLER_VISUAL",
 "next":"Inspect source/CLEAN/old/trial exact source family and correct any P3 hidden-RGB composition mismatch without changing protected/other 10 cells. P2 anchors, final manifest and changed-since guard required BEFORE promotion.",
 "promoted_DDS":0,"new_trial_DDS":0,"source_archive_dds":1,
 "C2":"C338_REWORK_UNCHANGED_SHA","C3":"BLOCKED","IGR029":"OPEN",
 "RUNTIME_VALIDATION":"UNTESTED","backend":"GITHUB_ACTIONS_REQUIRED_CANONICAL_SOURCE_BYTES"
}
(P/"B342_SOURCE_PLATE_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print("B342_Q212",gate,check,flush=True)
