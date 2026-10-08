#!/usr/bin/env python3
"""C298 C2 q154 exact-byte source-family glyph-band audit; EVIDENCE ONLY."""
import os, json, hashlib, urllib.request, subprocess
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image,ImageDraw
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions"
assert os.getenv("OUTRUN_CPU_ROLE")=="C"
R=Path(".")
O=R/"localization/graphics/role_C/20261008-C298-C2-Q154-ALL8-GLYPH-ANCHOR-PROFILE"
O.mkdir(parents=True,exist_ok=True)
triage=json.loads(subprocess.run(["python","tools/localization/rework_triage.py","--index","154"],capture_output=True,text=True,check=True).stdout)
assert triage["assets"][0]["next_action"]=="EVIDENCE_ONLY_HOLD",triage
source_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
source_bytes=urllib.request.urlopen(source_url,timeout=180).read()
candidate_bytes=(R/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds").read_bytes()
clean_bytes=(R/"localization/graphics/role_B/20261005-B-PRODUCTION60/4D38_HD_CLEAN_PLATE.png").read_bytes()
H=lambda s: hashlib.sha256(s).hexdigest()
sh="15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf"
ch="94678124f6cddaeb44520c6419f4b475d1452866c052ff301a4859dddf38cb1f"
kh="a4d707fa4376a7db4cc04fd1de51d9dc23b1874eac9a8b4988dc44c7f4c23380"
assert H(source_bytes)==sh and H(candidate_bytes)==ch and H(clean_bytes)==kh
assert source_bytes[:128]==candidate_bytes[:128]
raw_s=np.asarray(Image.open(BytesIO(source_bytes)).convert("RGBA")).copy()
raw_f=np.asarray(Image.open(BytesIO(candidate_bytes)).convert("RGBA")).copy()
s=np.flipud(raw_s).copy()
f=np.flipud(raw_f).copy()
k=np.asarray(Image.open(BytesIO(clean_bytes)).convert("RGBA")).copy()
assert s.shape==f.shape==k.shape==(1024,4096,4)
specs=[
("01_create_new_license","CREATE NEW LICENSE","새 라이선스 만들기",[13,548,1954,696]),
("02_select_license","SELECT LICENSE","라이선스 선택",[2007,541,3468,689]),
("03_single_player_red","SINGLE PLAYER","싱글 플레이",[12,374,1388,522]),
("04_default_license","DEFAULT LICENSE","기본 라이선스",[1772,374,3316,522]),
("05_multiplayer_red","MULTIPLAYER","멀티플레이",[15,203,1235,347]),
("06_single_player_gray","SINGLE PLAYER","싱글 플레이",[1610,286,2197,350]),
("07_showroom_gray","SHOWROOM","쇼룸",[2674,288,3094,350]),
("08_multiplayer_gray","MULTIPLAYER","멀티플레이",[2566,952,3086,1014])
]
mask=np.zeros((1024,4096),dtype=bool)
for _,_,_,(l,t,r,b) in specs:mask[t:b,l:r]=True
changed=np.any(s!=f,axis=2)
outside=int(np.count_nonzero(changed&~mask))
outside_alpha=int(np.count_nonzero((s[:,:,3]!=f[:,:,3])&~mask))
def bbox(aa):
 y,x=np.where(aa)
 return [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)] if len(x) else None
def glyph_band_metrics(alpha):
 # A separated ink-column run is only a silhouette proxy, not a semantic per-glyph anchor.
 columns=np.any(alpha>16,axis=0)
 spans=[];st=None
 for i,v in enumerate(columns):
  if v and st is None:st=i
  if (not v or i==len(columns)-1) and st is not None:
   en=i if not v else i+1
   if en-st>=3:spans.append((int(st),int(en)))
   st=None
 measures=[]
 for st,en in spans:
  region=alpha[:,st:en]>16
  yy,xx=np.where(region)
  if not len(yy):continue
  lo,hi=int(yy.min()),int(yy.max()+1)
  h=max(1,hi-lo)
  top=(yy<lo+h*.30)
  bottom=(yy>=hi-h*.30)
  if not np.any(top) or not np.any(bottom):continue
  t_x=float(np.mean(xx[top]+st))
  b_x=float(np.mean(xx[bottom]+st))
  measures.append({"x_columns":[st,en],"y":[lo,hi],
    "top_band_mean_x":round(t_x,3),"bottom_band_mean_x":round(b_x,3),
    "top_minus_bottom_dx":round(t_x-b_x,3),
    "warning":"Silhouette centroid proxy only; not a semantic glyph stem anchor."})
 return measures
results=[]
for name,en,ko,(l,t,r,b) in specs:
 sr=s[t:b,l:r,:].copy();fr=f[t:b,l:r,:].copy();kr=k[t:b,l:r,:].copy()
 source_alpha=sr[:,:,3]>0
 final_alpha=fr[:,:,3]>0
 abs_sb=bbox(source_alpha);abs_fb=bbox(final_alpha)
 sb=[abs_sb[0]+l,abs_sb[1]+t,abs_sb[2]+l,abs_sb[3]+t]
 fb=[abs_fb[0]+l,abs_fb[1]+t,abs_fb[2]+l,abs_fb[3]+t]
 margins=[fb[0]-l,r-fb[2],fb[1]-t,b-fb[3]]
 assert min(margins)>0,(name,margins)
 assert np.count_nonzero(kr[:,:,3])==0,(name,"clean alpha remaining")
 # A full-width lossless native source/final comparison with optional proxies marked.
 ref=Image.new("RGBA",(2*(r-l),b-t+28),(52,52,52,255))
 ref.paste(Image.fromarray(sr,"RGBA"),(0,28))
 ref.paste(Image.fromarray(fr,"RGBA"),(r-l,28))
 d=ImageDraw.Draw(ref)
 d.text((3,7),"PINNED ENGLISH ORIGINAL",fill="white")
 d.text((r-l+3,7),"CURRENT PERSISTED KOREAN DDS",fill="white")
 source_runs=glyph_band_metrics(sr[:,:,3])
 final_runs=glyph_band_metrics(fr[:,:,3])
 for n,arr,offset in (("source",source_runs,0),("candidate",final_runs,r-l)):
  for v in arr:
   mid=int(round((v["top_band_mean_x"]+v["bottom_band_mean_x"])/2))
   ymin=max(28,28+v["y"][0])
   ymax=min(ref.height-1,28+v["y"][1])
   if ymax<=ymin:continue
   d.line((offset+mid,ymin,offset+mid,ymax),fill=(0,245,245,150),width=1)
 ref.convert("RGB").save(O/(name+"_NATIVE_SOURCE_FINAL_MARKED.png"))
 # Practical 50% proof matching exact full width without truncating Korean suffixes.
 ref.resize((ref.width//2,ref.height//2),Image.Resampling.LANCZOS).convert("RGB").save(O/(name+"_PRACTICAL50_MARKED.png"))
 raw_t,raw_b=1024-b,1024-t
 assert np.array_equal(np.flipud(raw_s[raw_t:raw_b,l:r]),sr)
 assert np.array_equal(np.flipud(raw_f[raw_t:raw_b,l:r]),fr)
 # alpha-free clean image check prior separately; no assertion of source-family aesthetic fidelity
 results.append({"id":name,"english":en,"korean":ko,"source_bbox":sb,"candidate_bbox":fb,
  "margins_LRTB":margins,"source_area_alpha":int(np.count_nonzero(source_alpha)),
  "candidate_area_alpha":int(np.count_nonzero(final_alpha)),"clean_alpha_in_source_bbox":0,
  "source_column_runs":source_runs,"candidate_column_runs":final_runs,
  "counts":{"source_runs":len(source_runs),"candidate_runs":len(final_runs)},
  "source_candidate_native":name+"_NATIVE_SOURCE_FINAL_MARKED.png",
  "source_candidate_practical50":name+"_PRACTICAL50_MARKED.png",
  "raw_y_mirror_exact":True,"per_glyph_slant_certified":False})
out={"run":"C298","role":"C","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "queue_index":154,"policy_version":"visual-evidence-v1-20261008",
 "source_sha256":sh,"candidate_sha256":ch,"authored_clean_sha256":kh,
 "readable_size":[4096,1024],"dds_header_identical":True,
 "outside_8_source_bbox_RGBA_changed":outside,
 "outside_8_source_bbox_alpha_changed":outside_alpha,
 "triage":triage["assets"][0],
 "metric_limit":"Projection runs do not identify semantic syllables; top-minus-bottom centroid proxies do not establish genuine stem-anchor slant, family equivalence or C PASS.",
 "regions":results,"visual_C":"REQUIRES_CONTROLLER_FIRST_LOOK_AFTER_THIS_EVIDENCE","C3":"BLOCKED","RUNTIME_VALIDATION":"UNTESTED"}
(O/"C298_ALL8_FAMILY_ANCHOR_MACHINE.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"C298","source":sh,"candidate":ch,"outside":outside,
"alpha_outside":outside_alpha,"regions":len(results),"column_runs":{z["id"]:z["counts"] for z in results},
"output_path":str(O)}))
