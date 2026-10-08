#!/usr/bin/env python3
# C269 C2 exact-byte evidence worker. Evidence only; no shared state or candidate writes.
import hashlib, io, json, os, secrets, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

ROOT=Path(".")
BASE=ROOT/"localization/graphics/role_C/20261008-C269-C2-Q154-Q172-Q214-EVIDENCE"
CAL=BASE/"calibration"
BASE.mkdir(parents=True,exist_ok=True); CAL.mkdir(parents=True,exist_ok=True)

def get(url):
    with urllib.request.urlopen(url, timeout=180) as r: return r.read()
def sha(b): return hashlib.sha256(b).hexdigest()
def rgba_bytes(b): return np.array(Image.open(io.BytesIO(b)).convert("RGBA"))
def rgba_file(p): return np.array(Image.open(p).convert("RGBA"))
def bbox(mask):
    y,x=np.where(mask)
    return None if len(x)==0 else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def neutral(a,bg=128):
    rgb=a[...,:3].astype(np.float32); al=a[...,3:4].astype(np.float32)/255.0
    return np.clip(rgb*al+bg*(1-al),0,255).astype(np.uint8)
def save_contact(asset_dir, rid, arrays, labels):
    ims=[Image.fromarray(neutral(x)) for x in arrays]
    w=max(i.width for i in ims); h=max(i.height for i in ims)
    card=Image.new("RGB",(w*len(ims),h+24),(70,70,70))
    d=ImageDraw.Draw(card)
    for i,(im,label) in enumerate(zip(ims,labels)):
        d.text((i*w+3,3),label,fill="white"); card.paste(im,(i*w,22))
    p=asset_dir/f"{rid}_CONTACT.png"; card.save(p)
    card.resize((card.width*2,card.height*2),Image.Resampling.NEAREST).save(asset_dir/f"{rid}_ZOOM2X.png")
    for pct in (75,50):
        card.resize((max(1,round(card.width*pct/100)),max(1,round(card.height*pct/100))),Image.Resampling.LANCZOS).save(asset_dir/f"{rid}_PRACTICAL_{pct}.png")

# ---------- q154 ----------
q154=BASE/"q154"; q154.mkdir(exist_ok=True)
src154_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
prior154_url="https://raw.githubusercontent.com/thp32tt/OutRun2006Tweaks/60b77e39589d91803ca684e3bf5b7c2f4b1b7bc7/localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
cand154=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
clean154=ROOT/"localization/graphics/role_C/20261005-C141-4D38BBB0/C141_EXACT_CLEAN_PLATE.png"
sb=get(src154_url); pb=get(prior154_url); cb=cand154.read_bytes()
assert sha(sb)=="15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf"
assert sha(pb)=="815f0112c772ef1a99b5cb86639415701582301edaaf3ac5bec276e69a475288"
assert sha(cb)=="94678124f6cddaeb44520c6419f4b475d1452866c052ff301a4859dddf38cb1f"
assert sb[:128]==cb[:128]
sraw=rgba_bytes(sb); praw=rgba_bytes(pb); craw=rgba_bytes(cb)
s=np.flipud(sraw).copy(); prior=np.flipud(praw).copy(); cur=np.flipud(craw).copy(); clean=rgba_file(clean154)
rows154=[
 ("single_player_gray","SINGLE PLAYER","싱글 플레이",[1610,286,2197,350]),
 ("showroom_gray","SHOWROOM","쇼룸",[2674,288,3094,350]),
 ("multiplayer_gray","MULTIPLAYER","멀티플레이",[2566,952,3086,1014])]
allow=np.zeros(cur.shape[:2],bool); details=[]
for rid,en,ko,b in rows154:
    x0,y0,x1,y1=b; allow[y0:y1,x0:x1]=1
    m=np.any(cur[y0:y1,x0:x1]!=clean[y0:y1,x0:x1],axis=2)
    z=bbox(m)
    if z: z=[z[0]+x0,z[1]+y0,z[2]+x0,z[3]+y0]
    det={"id":rid,"source":en,"korean":ko,"original_bbox":b,"localized_bbox":z}
    if z:
        det.update({"delta_left":z[0]-x0,"delta_right":x1-z[2],"delta_top":z[1]-y0,"delta_bottom":y1-z[3],
                    "containment":"PASS" if z[0]>=x0 and z[1]>=y0 and z[2]<=x1 and z[3]<=y1 else "FAIL"})
    details.append(det)
    pad=8; xx0=max(0,x0-pad); yy0=max(0,y0-pad); xx1=min(cur.shape[1],x1+pad); yy1=min(cur.shape[0],y1+pad)
    arrs=[a[yy0:yy1,xx0:xx1] for a in (s,clean,prior,cur)]
    for arr,name in zip(arrs,("SOURCE","CLEAN","B225_REJECTED","A182R_FINAL")):
        Image.fromarray(arr).save(q154/f"{rid}_{name}.png")
    save_contact(q154,rid,arrs,["SOURCE","CLEAN","B225","A182R"])
blast=np.any(cur!=prior,axis=2)
rep154={
 "schema_version":1,"run":"C269","role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":154,
 "candidate_sha256":sha(cb),"source_sha256":sha(sb),"prior_candidate_sha256":sha(pb),"header_128_exact":sb[:128]==cb[:128],
 "dimensions":[cur.shape[1],cur.shape[0]],"raw_orientation":"mirror_y","rows":details,
 "rework_changed_outside_gray_bboxes":int(np.count_nonzero(blast&~allow)),
 "rework_alpha_changed_outside_gray_bboxes":int(np.count_nonzero((cur[...,3]!=prior[...,3])&~allow)),
 "machine_result":"PASS" if all(x.get("containment")=="PASS" for x in details) and int(np.count_nonzero(blast&~allow))==0 else "FAIL",
 "approval_result":"PENDING_CONTROLLER_VISUAL","runtime_validation":"UNTESTED"}
(q154/"C269_Q154_MACHINE_QA.json").write_text(json.dumps(rep154,ensure_ascii=False,indent=2)+"\n")

# ---------- q172 ----------
q172=BASE/"q172"; q172.mkdir(exist_ok=True)
src172_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
prior172_url="https://raw.githubusercontent.com/thp32tt/OutRun2006Tweaks/374b86ee958c6edef9616de596c02804651e5d70/localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
cand172=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds"
clean172=ROOT/"localization/graphics/role_B/20261006-B-PRODUCTION191-6C9B3611-START-GOAL/B191_CLEAN_PLATE.png"
sb=get(src172_url); pb=get(prior172_url); cb=cand172.read_bytes()
assert sha(sb)=="d5f4a36d5ef1285555ca8fc045e54d160876d1b3e33c6fbc45668c24566c2cf8"
assert sha(pb)=="963445a44888e75aa82df36aa7207fa8de819e155905153fd0c2a8847dd70fbc"
assert sha(cb)=="51a636b12d59a024c9eed4ea49b5c2f7a46145d39605f9264062284c9473ebdd"
assert sb[:128]==cb[:128]
sraw172=rgba_bytes(sb); praw172=rgba_bytes(pb); craw172=rgba_bytes(cb)
s172=np.flipud(sraw172).copy(); prior172=np.flipud(praw172).copy(); cur172=np.flipud(craw172).copy(); clean172a=rgba_file(clean172)
rows172=[("start","START","출발",[55,373,136,396]),("goal","GOAL","골",[595,635,672,659])]
allow172=np.zeros(cur172.shape[:2],bool); details172=[]
for rid,en,ko,b in rows172:
    x0,y0,x1,y1=b; allow172[y0:y1,x0:x1]=1
    m=np.any(cur172[y0:y1,x0:x1]!=clean172a[y0:y1,x0:x1],axis=2); z=bbox(m)
    if z:z=[z[0]+x0,z[1]+y0,z[2]+x0,z[3]+y0]
    det={"id":rid,"source":en,"korean":ko,"original_bbox":b,"localized_bbox":z}
    if z: det.update({"delta_left":z[0]-x0,"delta_right":x1-z[2],"delta_top":z[1]-y0,"delta_bottom":y1-z[3],
                       "containment":"PASS" if z[0]>=x0 and z[1]>=y0 and z[2]<=x1 and z[3]<=y1 else "FAIL"})
    details172.append(det)
    pad=14; xx0=max(0,x0-pad); yy0=max(0,y0-pad); xx1=min(cur172.shape[1],x1+pad); yy1=min(cur172.shape[0],y1+pad)
    arrs=[a[yy0:yy1,xx0:xx1] for a in (s172,clean172a,prior172,cur172)]
    for arr,name in zip(arrs,("SOURCE","CLEAN","B191_REJECTED","B248_FINAL")): Image.fromarray(arr).save(q172/f"{rid}_{name}.png")
    save_contact(q172,rid,arrs,["SOURCE","CLEAN","B191","B248"])
blast172=np.any(cur172!=prior172,axis=2)
rep172={"schema_version":1,"run":"C269","role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":172,
 "candidate_sha256":sha(cb),"source_sha256":sha(sb),"prior_candidate_sha256":sha(pb),"header_128_exact":sb[:128]==cb[:128],
 "dimensions":[cur172.shape[1],cur172.shape[0]],"raw_orientation":"mirror_y","rows":details172,
 "rework_changed_outside_source_bboxes":int(np.count_nonzero(blast172&~allow172)),
 "rework_alpha_changed_outside_source_bboxes":int(np.count_nonzero((cur172[...,3]!=prior172[...,3])&~allow172)),
 "machine_result":"PASS" if all(x.get("containment")=="PASS" for x in details172) and int(np.count_nonzero(blast172&~allow172))==0 else "FAIL",
 "approval_result":"PENDING_CONTROLLER_VISUAL","runtime_validation":"UNTESTED"}
(q172/"C269_Q172_MACHINE_QA.json").write_text(json.dumps(rep172,ensure_ascii=False,indent=2)+"\n")
# readable + raw full evidence for orientation
Image.fromarray(sraw172).save(q172/"SOURCE_RAW.png"); Image.fromarray(craw172).save(q172/"FINAL_RAW.png")
Image.fromarray(s172).save(q172/"SOURCE_READABLE.png"); Image.fromarray(cur172).save(q172/"FINAL_READABLE.png")

# ---------- q214 ----------
q214=BASE/"q214"; q214.mkdir(exist_ok=True)
src214_url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3da79726739ac631d8e2703a65330dbb0c310770/Release/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds"
cand214=ROOT/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds"
clean214=ROOT/"localization/graphics/role_B/20261006-B-PRODUCTION194-BF229CF4-START-GOAL/B194_CLEAN_PLATE.png"
sb=get(src214_url); cb=cand214.read_bytes()
assert sha(sb)=="9a2e428bdb87399a7589338053b49efdcfd103d14f12a33a4bcde7705ab76c6b"
assert sha(cb)=="3d292729007cacb909782ad6c38fe463ba1ff4705772c69f930d4a30f14a839b"
assert sb[:128]==cb[:128]
sraw214=rgba_bytes(sb); craw214=rgba_bytes(cb); s214=np.flipud(sraw214).copy(); cur214=np.flipud(craw214).copy(); clean214a=rgba_file(clean214)
rows214=[("start","START","출발",[815,495,899,517],[842,497,872,515]),("goal","GOAL","골",[1343,764,1417,787],[1371,766,1389,785])]
details214=[]
for rid,en,ko,b,z in rows214:
    x0,y0,x1,y1=b
    det={"id":rid,"source":en,"korean":ko,"original_bbox":b,"localized_bbox":z,
      "source_size":[x1-x0,y1-y0],"localized_size":[z[2]-z[0],z[3]-z[1]],
      "width_ratio_pct":round(100*(z[2]-z[0])/(x1-x0),2),
      "height_ratio_pct":round(100*(z[3]-z[1])/(y1-y0),2),
      "containment":"PASS" if z[0]>=x0 and z[1]>=y0 and z[2]<=x1 and z[3]<=y1 else "FAIL"}
    details214.append(det)
    pad=16; xx0=max(0,x0-pad); yy0=max(0,y0-pad); xx1=min(cur214.shape[1],x1+pad); yy1=min(cur214.shape[0],y1+pad)
    arrs=[a[yy0:yy1,xx0:xx1] for a in (s214,clean214a,cur214)]
    for arr,name in zip(arrs,("SOURCE","CLEAN","FINAL")): Image.fromarray(arr).save(q214/f"{rid}_{name}.png")
    save_contact(q214,rid,arrs,["SOURCE","CLEAN","FINAL"])
Image.fromarray(sraw214).save(q214/"SOURCE_RAW.png"); Image.fromarray(craw214).save(q214/"FINAL_RAW.png")
rep214={"schema_version":1,"run":"C269","role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN","queue_index":214,
 "candidate_sha256":sha(cb),"source_sha256":sha(sb),"header_128_exact":sb[:128]==cb[:128],"dimensions":[cur214.shape[1],cur214.shape[0]],
 "format":"DXT5","raw_orientation":"mirror_y","rows":details214,
 "machine_result":"SOURCE_CANDIDATE_IDENTITY_AND_KNOWN_BBOX_CONTAINMENT_REDERIVED; BC3 block-level producer metrics remain historical support only",
 "approval_result":"PENDING_CONTROLLER_VISUAL","runtime_validation":"UNTESTED"}
(q214/"C269_Q214_MACHINE_QA.json").write_text(json.dumps(rep214,ensure_ascii=False,indent=2)+"\n")

# ---------- blind calibration ----------
# Use exact q172 START source/clean pixels as reference; create labeled synthetic defects only for calibration.
b=[55,373,136,396]; pad=18; x0,y0,x1,y1=b; x0-=pad; y0-=pad; x1+=pad; y1+=pad
srcp=Image.fromarray(s172[y0:y1,x0:x1]).convert("RGBA"); cleanp=Image.fromarray(clean172a[y0:y1,x0:x1]).convert("RGBA")
sa=np.array(srcp); ca=np.array(cleanp); mask=np.any(sa!=ca,axis=2)
layer=np.zeros_like(sa); layer[mask]=sa[mask]; layer_im=Image.fromarray(layer)
normal=srcp.copy()
# opposite slant: apply a strong shear to isolated source text in opposite visual direction over clean plate
shear=-0.45
shift=int(abs(shear)*layer_im.height)+8
can=Image.new("RGBA",(layer_im.width+2*shift,layer_im.height),(0,0,0,0)); can.paste(layer_im,(shift,0))
trans=can.transform(can.size,Image.Transform.AFFINE,(1,shear,-shear*can.height/2,0,1,0),Image.Resampling.BICUBIC).crop((shift,0,shift+layer_im.width,layer_im.height))
opposite=cleanp.copy(); opposite.alpha_composite(trans)
# clipped: remove bottom and right edge pixels from isolated text
cl=np.array(layer_im); mm=cl[...,3]>0
yy,xx=np.where(mm)
if len(xx):
    cl[max(0,yy.max()-4):yy.max()+1,:,:]=0
    cl[:,max(0,xx.max()-3):xx.max()+1,:]=0
clipped=cleanp.copy(); clipped.alpha_composite(Image.fromarray(cl))
# residue: faint offset duplicate beneath exact source
ghost=Image.new("RGBA",srcp.size,(0,0,0,0)); ghost.alpha_composite(layer_im,(4,3))
ga=np.array(ghost); ga[...,3]=(ga[...,3].astype(np.float32)*0.38).astype(np.uint8)
residue=cleanp.copy(); residue.alpha_composite(Image.fromarray(ga)); residue.alpha_composite(layer_im)
# excessive weight: dilate source-text alpha/color footprint
la=np.array(layer_im); alpha=Image.fromarray(la[...,3]).filter(ImageFilter.MaxFilter(5))
heavy_layer=Image.new("RGBA",srcp.size,(245,220,180,0)); heavy_layer.putalpha(alpha)
heavy=cleanp.copy(); heavy.alpha_composite(heavy_layer)
items=[("normal",normal),("opposite_slant",opposite),("clipped_stroke",clipped),("residue",residue),("excessive_weight",heavy)]
secrets.SystemRandom().shuffle(items); answer={}
for i,(kind,test) in enumerate(items):
    card=Image.new("RGB",(srcp.width*2,srcp.height+24),(60,60,60)); d=ImageDraw.Draw(card)
    d.text((2,2),"SOURCE",fill="white"); d.text((srcp.width+2,2),"TEST",fill="white")
    card.paste(srcp.convert("RGB"),(0,22)); card.paste(test.convert("RGB"),(srcp.width,22))
    name=f"case_{i:02d}.png"; card.save(CAL/name); answer[name]=kind
(CAL/"ANSWER_KEY_DO_NOT_READ_BEFORE_FIRST_LOOK.json").write_text(json.dumps(answer,indent=2)+"\n")
(CAL/"CALIBRATION_GENERATION.json").write_text(json.dumps({
 "policy_version":"visual-evidence-v1-20261008","source_asset":"q172 6C9B3611 START exact source pixels",
 "source_sha256":"d5f4a36d5ef1285555ca8fc045e54d160876d1b3e33c6fbc45668c24566c2cf8",
 "cases":5,"answer_key_separate":True,"synthetic_variants_are_calibration_only":True
},indent=2)+"\n")

summary={"run":"20261008-C269-C2-Q154-Q172-Q214-EVIDENCE","role":"C","lane":"C2","TEMP_BACKLOG_RELIEF":"C2","SHARD":"EVEN",
 "selection_head":"daf009b94a8406c281d3dece7e0a8400d729416d","q154":rep154,"q172":rep172,"q214":rep214,
 "calibration_cases":[f"calibration/case_{i:02d}.png" for i in range(5)],"controller_visual_qa":"PENDING","runtime_validation":"UNTESTED"}
(BASE/"C269_WORKER_EVIDENCE_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
wr=ROOT/"localization/graphics/worker_results/C269_C2_Q154_Q172_Q214.json"
wr.write_text(json.dumps({"role":"C","run":"20261008-C269-C2-Q154-Q172-Q214-EVIDENCE","status":"EVIDENCE_WRITTEN_PENDING_CONTROLLER_VISUAL","report":str(BASE/"C269_WORKER_EVIDENCE_SUMMARY.json").replace("\\","/"),"runtime_validation":"UNTESTED"},indent=2)+"\n")
print(json.dumps({"q154_candidate":rep154["candidate_sha256"],"q154_machine":rep154["machine_result"],"q172_candidate":rep172["candidate_sha256"],"q172_machine":rep172["machine_result"],"q214_candidate":rep214["candidate_sha256"],"calibration_cases":5}))
