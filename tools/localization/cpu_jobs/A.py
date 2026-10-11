#!/usr/bin/env python3
"""A249 q193 SHOWROOM only: genuine source CLEAN and extracted saved Hangul
without rerendering previously correct A246 or claiming independent approval."""
import os,hashlib,struct,json,csv,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="A"
R=Path.cwd(); OUT=R/"localization/graphics/role_A/20261012-A249-Q193-SHOWROOM-SOURCE-CLEAN"
OUT.mkdir(parents=True,exist_ok=True)
RUN="OUTRUN-KOR-A249-Q193-SHOWROOM-SOURCE-CLEAN-20261012-0200"
SRC=R/"localization/graphics/role_A/20261011-A243-Q193-15CONT-SOURCE-CLEAN-PILOT/A243_PINNED_CANONICAL_SOURCE.dds"
OLD=R/"localization/graphics/hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/97E863AD_512x256.dds"
NOW=R/"localization/graphics/role_A/20261011-A246-Q193-FOUR-GOALS-INTEGRATED-CLEAN/A246_Q193_SIX_LEGACY_SOURCE_CLEAN_INTEGRATED_TRIAL_UNPROMOTED.dds"
sha=lambda b:hashlib.sha256(b).hexdigest()
SHAS=["d308bf0558ed46ab531c869c65260e37a02f125ceaf7efd0f12524c3d0266451","9ea15d130693dd99bcd0ffa445b4799132665c5c93728c1c11783c94ba25b0f3","980662036fcdd75b0676890acc496c27e9322bc3c95999b8bfea3d2ee81c4b8f"]
BOX=(1205,957,1594,1011);W,H=2048,1024
def chk(x,msg):
 if not x:raise RuntimeError("A249_FAIL_CLOSED "+msg)
def refs(p):return {"path":str(p.relative_to(R)),"sha256":sha(p.read_bytes())}
def write(name,o):
 p=OUT/(name+".json");p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n");return refs(p)
def png(name,im):
 p=OUT/(name+".png");im.save(p);return refs(p)
def dec(b):
 chk(b[:4]==b"DDS " and len(b)==128+W*H*4,"DDS size")
 chk(struct.unpack_from("<II",b,12)==(H,W),"dimensions")
 chk(struct.unpack_from("<I",b,28)[0]==1 and struct.unpack_from("<I",b,88)[0]==32,"format")
 chk(struct.unpack_from("<IIII",b,92)==(255,65280,16711680,4278190080),"RGBA mask")
 return np.asarray(Image.frombytes("RGBA",(W,H),b[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)).copy()
im=lambda a:Image.fromarray(a,"RGBA")
def flatten(a,bg):return Image.alpha_composite(Image.new("RGBA",a.size,(*bg,255)),a).convert("RGB")
with (R/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 q=next(x for x in csv.DictReader(f) if x["index"]=="193")
chk(q["action"]=="localize_text" and "rework" in q["artwork_status"].lower(),"rework ownership changed")
chk("A247" in q["notes"],"missing previous SHA chain")
proc=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","193"],capture_output=True,text=True,check=True)
write("A249_TRIAGE",{"run_key":RUN,"triage_stdout":proc.stdout,"triage_stderr":proc.stderr,"target":"missing showroom CLEAN stage; reuse existing good Korean bytes"})
blobs=[p.read_bytes() for p in (SRC,OLD,NOW)]
for p,b,h in zip((SRC,OLD,NOW),blobs,SHAS):chk(sha(b)==h,"SHA drift "+str(p))
chk(blobs[0][:128]==blobs[1][:128]==blobs[2][:128],"header drift")
S,O,T=[dec(b) for b in blobs]
x0,y0,x1,y1=BOX;A=S[y0:y1,x0:x1];B=O[y0:y1,x0:x1];Z=T[y0:y1,x0:x1]
chk(np.array_equal(B,Z),"SHOWROOM text differs from official in A246")
chk(np.count_nonzero(A[:,:,3])>1000 and np.count_nonzero(Z[:,:,3])>500,"SHOWROOM missing")
clean=np.zeros_like(A);letter=Z.copy()
mask=np.zeros((H,W),bool);mask[y0:y1,x0:x1]=True
C=S.copy();C[y0:y1,x0:x1]=clean
changed=np.any(C!=S,axis=2);outside=int(np.count_nonzero(changed&~mask))
chk(outside==0 and np.count_nonzero(C[y0:y1,x0:x1,3])==0,"CLEAN overflow/residue")
mixed=C.copy();mixed[y0:y1,x0:x1]=letter
chk(np.array_equal(mixed[mask],T[mask]) and np.array_equal(mixed[~mask],S[~mask]),"CLEAN+letter exact integrity fail")
ys,xs=np.nonzero(letter[:,:,3]>0)
bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
margins=[bbox[0],bbox[1],x1-x0-bbox[2],y1-y0-bbox[3]]
chk(min(margins)>0,"saved Korean exceeds original source area")
proof={}
for name,arr in [("SOURCE",A),("OFFICIAL",B),("CLEAN",clean),("EXTRACTED_KOREAN",letter),("SAVED_A246",Z)]:
 proof[name]=png("A249_SHOWROOM_"+name+"_NATIVE",im(arr))
 if name!="OFFICIAL":proof[name+"_RAW"]=png("A249_SHOWROOM_"+name+"_RAW",im(arr).transpose(Image.Transpose.FLIP_TOP_BOTTOM))
for label,bg,pct in [("GRAY100",(105,105,105),100),("WHITE75",(255,255,255),75),("BLACK50",(0,0,0),50)]:
 stages=[flatten(im(a),bg) for a in (A,B,clean,letter,Z)]
 w=max(1,round((x1-x0)*pct/100));h=max(1,round((y1-y0)*pct/100))
 card=Image.new("RGB",(w*5,h),bg)
 for k,stage in enumerate(stages):card.paste(stage.resize((w,h),Image.Resampling.LANCZOS),(k*w,0))
 proof[label]=png("A249_SHOWROOM_"+label+"_SOURCE_OFFICIAL_CLEAN_LETTER_SAVED",card)
info={"schema_version":2,"run_key":RUN,"role":"A","queue_index":193,"priority":"P1",
"source_text":"SHOWROOM (neighboring OUTRUN preserved)","korean_text":"쇼룸",
"source_path":str(SRC.relative_to(R)),"source_sha256":SHAS[0],"official_sha256":SHAS[1],
"saved_trial_sha256_unchanged":SHAS[2],"source_bbox_readable":list(BOX),
"source_alpha_pixels":int(np.count_nonzero(A[:,:,3])),"saved_alpha_pixels":int(np.count_nonzero(Z[:,:,3])),
"saved_alpha_bbox_local":bbox,"positive_margins":margins,"new_source_clean_alpha_pixels":0,
"source_to_clean_changed_rgba_pixels":int(np.count_nonzero(changed)),
"source_to_clean_changed_outside":outside,
"clean_plus_extracted_letter_recomposite_exact":True,"other_atlas_source_pixels_preserved":True,
"native_dimensions":[W,H],"format":"RGBA32","mips":1,"readable_to_raw":"mirror_y",
"authored_new_Korean_text":False,"new_dds":0,"official_promoted_dds":0,
"qa":"SCOPED_MACHINE_PASS_PENDING_FIRSTHAND_AND_C2_INDEPENDENT","whole_q193_C2":"HOLD",
"C3":"NOT_RUN","user_IGR":["IGR003","IGR019","IGR033"],"RUNTIME_VALIDATION":"UNTESTED",
"proofs":proof,"excluded":["VR","FFB","DX11","DXVK"]}
write("A249_SHOWROOM_SOURCE_CLEAN_GLYPH_MACHINE",info)
print(json.dumps({"run":"A249","source_to_clean":info["source_to_clean_changed_rgba_pixels"],"outside":outside,"bbox":bbox,"margins":margins,"new_dds":0},ensure_ascii=False))
