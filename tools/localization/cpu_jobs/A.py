#!/usr/bin/env python3
"""A247 q193: native canonical SOURCE-to-CLEAN separation of THREE unchanged,
C2-identified inherited Korean regions. Preserves exact A246 DDS bytes.
Not an independent C2 approval and not a new DDS."""
import csv, hashlib, json, os, struct, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image

assert os.environ.get("OUTRUN_CPU_WORKER") == "github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE") == "A"
ROOT=Path.cwd()
DIR=ROOT/"localization/graphics/role_A/20261012-A247-Q193-THREE-SOURCE-CLEAN-RECONSTRUCTION"
DIR.mkdir(parents=True,exist_ok=True)
RUN="OUTRUN-KOR-A247-Q193-C2-THREE-MISSING-CLEAN-20261012-0000"
SRC=ROOT/"localization/graphics/role_A/20261011-A243-Q193-15CONT-SOURCE-CLEAN-PILOT/A243_PINNED_CANONICAL_SOURCE.dds"
TRIAL=ROOT/"localization/graphics/role_A/20261011-A246-Q193-FOUR-GOALS-INTEGRATED-CLEAN/A246_Q193_SIX_LEGACY_SOURCE_CLEAN_INTEGRATED_TRIAL_UNPROMOTED.dds"
OFF=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds"
SHAS={"source":"d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451",
      "trial":"980662036fcdd75b0676890acc496c27e9322bc3c95999b8bfea3d2ee81c4b8f",
      "official":"9ea15d130693dd99bcd0ffa445b4799132665c5c93728c1c11783c94ba25b0f3"}
REGIONS=[
 {"id":"WELCOME_TO_THE","english":"WELCOME TO THE","korean":"환영합니다","bbox":(3,148,476,195)},
 {"id":"MULTIPLAYER","english":"MULTIPLAYER","korean":"멀티플레이어","bbox":(8,297,540,359)},
 {"id":"ONLINE_RANKING_HELP","english":"View the online multiplayer rankings!","korean":"온라인 멀티플레이어 랭킹 보기!","bbox":(7,384,1137,450)},
]
W,H=2048,1024
def sh(b): return hashlib.sha256(b).hexdigest()
def check(cond,msg):
 if not cond: raise RuntimeError("A247_FAIL_CLOSED "+msg)
def ref(p): return {"path":str(p.relative_to(ROOT)),"sha256":sh(p.read_bytes())}
def save_img(stem,img):
 p=DIR/(stem+".png");img.save(p,format="PNG");return ref(p)
def save_data(stem,obj):
 p=DIR/(stem+".json");p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");return ref(p)
def decode(b):
 check(b[:4]==b"DDS " and len(b)==128+W*H*4,"unexpected DDS header/size")
 check(struct.unpack_from("<II",b,12)==(H,W),"DDS native resolution")
 check(struct.unpack_from("<I",b,28)[0]==1,"mip count changed")
 check(struct.unpack_from("<I",b,88)[0]==32,"DDS channel depth")
 check(struct.unpack_from("<IIII",b,92)==(255,65280,16711680,4278190080),"RGBA native mask")
 return np.array(Image.frombytes("RGBA",(W,H),b[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
def rgba(arr):return Image.fromarray(arr.astype("uint8"),"RGBA")
def opaque(arr,bg):
 return Image.alpha_composite(Image.new("RGBA",arr.size,(*bg,255)),arr).convert("RGB")
with (ROOT/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as fh:
 q=next(x for x in csv.DictReader(fh) if x["index"]=="193")
check(q["action"]=="localize_text" and "rework" in q["artwork_status"].lower(),"queue changed; no longer A rework")
check("A246" in q["notes"],"C2 target A246 absent from queue")
p=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","193"],capture_output=True,text=True,check=True)
tri=save_data("A247_READ_ONLY_TRIAGE",{"command":"rework_triage --index 193","stdout":p.stdout,"stderr":p.stderr,"only_missing_clean_evidence_no_same_sha_rerender":True})
sb,tb,ob=SRC.read_bytes(),TRIAL.read_bytes(),OFF.read_bytes()
for key,blob in (("source",sb),("trial",tb),("official",ob)):
 check(sh(blob)==SHAS[key],key+" SHA drift")
check(sb[:128]==tb[:128]==ob[:128],"DDS header format drift")
S,T,O=decode(sb),decode(tb),decode(ob)
target=np.zeros((H,W),bool)
for item in REGIONS:
 x0,y0,x1,y1=item["bbox"]
 check(x1<=W and y1<=H and x0>=0 and y0>=0,"bad source bbox")
 check(not target[y0:y1,x0:x1].any(),"source bboxes overlap")
 target[y0:y1,x0:x1]=True
 check(np.array_equal(T[y0:y1,x0:x1],O[y0:y1,x0:x1]),"A246 region no longer inherited exact unchanged official")
check(np.count_nonzero(target)>0,"no targets")
C=S.copy();C[target]=0
check(np.count_nonzero(np.any(C!=S,axis=2)&~target)==0,"CLEAN changed protected pixels")
check(np.count_nonzero(C[:,:,3][target])==0,"CLEAN glyph alpha remains")
# This is an exact source-derived transparent-only CLEAN. Letter masks are
# isolated from saved candidate bytes, not invented as independently rendered.
# No changed/trial DDS is created or published here.
LL=np.zeros_like(S);LL[target]=T[target]
R=S.copy();R[target]=T[target]
check(np.array_equal(R[target],T[target]),"composite target mismatch")
check(np.array_equal(R[~target],S[~target]),"other source artwork altered")
check(np.array_equal(LL[~target],np.zeros_like(LL[~target])),"lettering outside source ROI")
rows=[]
for item in REGIONS:
 x0,y0,x1,y1=item["bbox"]; b=item["bbox"]
 sq=S[y0:y1,x0:x1];tq=T[y0:y1,x0:x1];cq=C[y0:y1,x0:x1];lq=LL[y0:y1,x0:x1]
 check(np.count_nonzero(sq[:,:,3])>200,"source region transparent unexpected "+item["id"])
 check(np.count_nonzero(tq[:,:,3])>100,"localized candidate blank "+item["id"])
 check(np.count_nonzero(cq[:,:,3])==0,"not clean: "+item["id"])
 src_alpha=int(np.count_nonzero(sq[:,:,3]))
 tr_alpha=int(np.count_nonzero(tq[:,:,3]))
 check(src_alpha<tr_alpha*8 and tr_alpha<src_alpha*8,"abnormal native letter alpha "+item["id"])
 evidence={}
 for stage,arr in (("SOURCE",sq),("CLEAN",cq),("EXTRACTED_SAVED_LETTERING",lq),("A246_PERSISTED_FINAL",tq)):
  evidence[stage]=save_img("A247_"+item["id"]+"_"+stage+"_NATIVE",rgba(arr))
 for color,bg,pct in (("GRAY", (105,105,105),100),("WHITE",(255,255,255),75),("BLACK",(0,0,0),50)):
  imgs=[rgba(arr) for arr in (sq,cq,lq,tq)]
  imgs=[opaque(v,bg) for v in imgs]
  w=max(1,round((x1-x0)*pct/100));h=max(1,round((y1-y0)*pct/100))
  panel=Image.new("RGB",(4*w,h),bg)
  for i,im in enumerate(imgs):
   panel.paste(im.resize((w,h),Image.Resampling.LANCZOS),(w*i,0))
  evidence[color+str(pct)]=save_img("A247_"+item["id"]+"_"+color+str(pct)+"_SOURCE_CLEAN_LAYER_SAVED",panel)
 for stage,arr in (("RAW_CLEAN",cq),("RAW_SAVED",tq)):
  evidence[stage]=save_img("A247_"+item["id"]+"_"+stage,rgb:=rgba(arr).transpose(Image.Transpose.FLIP_TOP_BOTTOM))
 rows.append({"id":item["id"],"source_english":item["english"],"existing_korean":item["korean"],
              "source_bbox_readable":list(b),
              "source_alpha_pixels":src_alpha,"saved_candidate_alpha_pixels":tr_alpha,
              "fresh_clean_alpha_pixels":int(np.count_nonzero(cq[:,:,3])),
              "source_to_clean_changed_outside_three_boxes":0,
              "persisted_trial_exact_in_region":True,
              "raw_flipy_confirmed_by_actual_transpose":True,
              "new_relettered_glyph":False,"evidence":evidence})
SAVE_CLEAN=save_img("A247_THREE_REGIONS_SOURCE_DERIVED_CLEAN_FLIPY_NATIVE",rgba(C))
SAVE_LAYER=save_img("A247_THREE_REGIONS_EXACT_SAVED_GLYPH_ONLY_FLIPY_NATIVE",rgba(LL))
SAVE_RAW=save_img("A247_THREE_REGIONS_SOURCE_DERIVED_CLEAN_RAW",rgba(C).transpose(Image.Transpose.FLIP_TOP_BOTTOM))
machine={
 "schema":"outrun-a247-three-real-clean-stage-v1","run_key":RUN,"role":"A","queue_index":193,
 "priority":"P1","target_c2_finding":"C2-Q193-THREE-UNTOUCHED-LEGACY-CELLS-FIRST-STAGE-AUDIT-20261012-0002",
 "source_sha256":SHAS["source"],"candidate_sha256":SHAS["trial"],"official_sha256":SHAS["official"],
 "source_to_clean_changed_pixels":int(np.count_nonzero(np.any(S!=C,axis=2))),
 "source_to_clean_changed_outside_scopes":int(np.count_nonzero(np.any(S!=C,axis=2)&~target)),
 "source_to_clean_alpha_inside_scopes":int(np.count_nonzero(C[:,:,3][target])),
 "lettering_layer_outside_scopes":int(np.count_nonzero(LL[:,:,3][~target])),
 "scope_only_trial_vs_official_pixels":int(np.count_nonzero(np.any(T[target]!=O[target],axis=1))),
 "exact_region_recomposite_match":bool(np.array_equal(R[target],T[target])),
 "other_original_pixels_preserved":bool(np.array_equal(R[~target],S[~target])),
 "regions":rows,
 "clean_plate":SAVE_CLEAN,"extracted_existing_lettering":SAVE_LAYER,"raw_clean":SAVE_RAW,
 "new_DDS":0,"official_DDS_changed":0,
 "producer_gate":"SOURCE_CLEAN_STAGE_SCOPED_MACHINE_PASS_VISUAL_REVIEW_REQUIRED",
 "C2":"REVIEW_NEW_CLEAN_SEPARATELY_NO_AUTO_PASS",
 "C3":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
 "user_IGR":["IGR003","IGR019","IGR033"],
 "excluded":["VR","FFB","DX11","DXVK"]}
save_data("A247_SOURCE_CLEAN_MACHINE_AND_HANDOFF",machine)
print(json.dumps({"run":"A247","source_sha256":SHAS["source"],
                   "candidate_sha256":SHAS["trial"],"clean_source_alpha":machine["source_to_clean_alpha_inside_scopes"],
                   "outside":machine["source_to_clean_changed_outside_scopes"],
                   "region_count":len(rows),"new_DDS":0},ensure_ascii=False),flush=True)
