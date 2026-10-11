#!/usr/bin/env python3
"""A251 q089 - source-chroma reconstruction of existing Korean Game Over glyphs.
An isolated NEW material DDS trial, never a self-awarded C2/C3/ingame PASS.
"""
import csv, hashlib, io, json, os, struct, subprocess, sys, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions"
assert os.getenv("OUTRUN_CPU_ROLE")=="A"
R=Path.cwd(); OUT=R/"localization/graphics/role_A/20261012-A251-Q089-SOURCE-CHROMA-NATIVE"
OUT.mkdir(parents=True,exist_ok=True)
RUN="OUTRUN-KOR-A251-Q089-C383-SOURCE-CHROMA-MATERIAL-20261012-0500"
ASSET=R/"localization/graphics/hd_candidates/textures/load/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds"
CLEAN=R/"localization/graphics/role_A/20261004-A-PRODUCTION12/43B07A77_HD_CLEAN_PLATE.png"
SRC_URL="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds"
SOURCE_HASH="906a17ef9534bcb43d8296ae1d2ac339a53910f7113b954a52475368ab9b4175"
PRIOR_HASH="741a05cb632e85a4fea783e51bb2f98678c0510f8b34fc7a73cc39c898c0749c"
CLEAN_HASH="0d3f46b6719366d5b337491117c585274b1e4d9d7fdc2a00cbc2c42b002437cd"
BOX=(1,13,1494,251); W,H=2048,256
def h(b):return hashlib.sha256(b).hexdigest()
def check(p,msg): 
 if not p: raise RuntimeError("A251_FAIL_CLOSED: "+msg)
def ref(p):
 return {"path":str(p.relative_to(R)),"sha256":h(p.read_bytes())}
def write_json(p,x):
 p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return ref(p)
def png(n,im):
 p=OUT/(n+".png");im.save(p);return ref(p)
def im(a):return Image.fromarray(np.asarray(a,dtype=np.uint8),"RGBA")
def decode(b):
 check(b[:4]==b"DDS " and len(b)==128+W*H*4,"exact RGBA32 DDS 2048x256")
 check(struct.unpack_from("<II",b,12)==(H,W),"DDS dimensions")
 check(struct.unpack_from("<I",b,28)[0]==1,"only one authored mip")
 check(struct.unpack_from("<I",b,88)[0]==32,"must be 32-bit source format")
 return np.array(Image.frombytes("RGBA",(W,H),b[128:],"raw","RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
def bg(image,color):
 return Image.alpha_composite(Image.new("RGBA",image.size,(*color,255)),image).convert("RGB")
def palette(label,a,sel):
 v=a[sel][:,:3].astype(np.float64)
 check(len(v)>30,"original SOURCE has no "+label+" palette pixels")
 return np.median(v,axis=0)
with (R/"localization/graphics/asset_queue.csv").open(encoding="utf-8-sig",newline="") as f:
 q=next(x for x in csv.DictReader(f) if x["index"]=="89")
check(q["action"]=="localize_text" and "rework" in q["artwork_status"].lower(),
      "q089 no longer source-style rework at current Git revision")
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","89"],capture_output=True,text=True,check=True)
decision=json.loads(tri.stdout)["assets"][0]
check(decision["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),
      "triage says no material revision; do not rerender")
oldb=ASSET.read_bytes()
check(h(oldb)==PRIOR_HASH,"concurrent q089 official DDS bytes changed")
cleanb=CLEAN.read_bytes()
check(h(cleanb)==CLEAN_HASH,"clean background evidence changed")
# GitHub Actions runner has network access; pin exact public upstream commit AND full native file SHA.
req=urllib.request.Request(SRC_URL,headers={"User-Agent":"OutRun-localization-pinned-source-A251"})
with urllib.request.urlopen(req,timeout=45) as resp: srcb=resp.read()
check(h(srcb)==SOURCE_HASH,"canonical source SHA mismatch; stop, do not substitute another image")
S=decode(srcb);O=decode(oldb)
C=np.asarray(Image.open(CLEAN).convert("RGBA"))
check(C.shape==S.shape and np.count_nonzero(C[:,:,3])==0,"source English CLEAN is not transparent")
y,x=np.nonzero(S[:,:,3]>0)
check((int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1))==BOX,
      "source glyph/effect permitted bbox changed")
check(np.count_nonzero(np.any(S[:,:]!=C[:,:],axis=2)[:BOX[1],:])==0,
      "source->CLEAN unexpected top external changes")
inside=np.zeros((H,W),bool);inside[BOX[1]:BOX[3],BOX[0]:BOX[2]]=True
check(np.count_nonzero(np.any(S!=C,axis=2)&~inside)==0,"SOURCE CLEAN modifies protected outside")
check(np.count_nonzero((O[:,:,3]>0)&~inside)==0,"old candidate alpha outside original source")
# Derive every palette anchor from SHA-verified original pixels, not arbitrary guessed RGB.
sr=S[:,:,0].astype(np.int16);sg=S[:,:,1].astype(np.int16);sb=S[:,:,2].astype(np.int16)
a=S[:,:,3];vis=a>=190
warm=vis&(sr>=190)&(sg>=60)&(sg<=175)&(sb<=160)&(sr>=sg+35)
yellow=vis&(sr>=190)&(sg>=150)&(sb<175)&(sr>=sg)
cream=vis&(sr>=220)&(sg>=180)&(sb>=160)
purple=vis&(sb>=sr+7)&(sr>=50)&(sr<=205)
deep=vis&(sr<90)&(sg<85)&(sb<120)
colors={k:palette(k,S,mask) for k,mask in
        [("warm",warm),("yellow",yellow),("cream",cream),("purple",purple),("deep",deep)]}
# Smooth continuous face gradient follows the ORIGINAL y-dependent face material;
# only material/edge color changes; same Korean native contours and same alpha bytes.
T=O.copy()
pix=O[:,:,:3].astype(np.float32)
alpha=O[:,:,3]
bright=(alpha>0)&(pix[:,:,0]>160)&(pix[:,:,1]>125)&(pix[:,:,2]>100)
g=np.clip((np.arange(H,dtype=np.float32)-BOX[1])/(BOX[3]-BOX[1]),0,1)
# Original source has peach/cream highlights above an orange/gold lower band.
knots=np.array([0.0,0.32,0.51,0.65,0.84,1.0],np.float32)
anchors=np.array([colors["cream"],colors["cream"],colors["yellow"],
                  colors["warm"],colors["warm"],colors["purple"]],np.float32)
smooth=np.stack([np.interp(g,knots,anchors[:,ch]) for ch in range(3)],axis=1)
# Source bevel visible at side boundaries. Preserve old dark outer alpha contour,
# recolor the face, not every pixel in the padded image.
dist=distance_transform_edt(alpha>90)
rim=bright&(dist<=2.5)
face=bright&~rim
check(int(face.sum())>10000 and int(rim.sum())>200,"not enough original Korean material to rework")
T[:,:,:3][face]=np.broadcast_to(np.clip(smooth[:,None,:]+0.5,0,255).astype(np.uint8),(H,W,3))[face]
# Use actual original purple/deep for compact edge relief, never introduce new alpha.
rim_c=np.clip(colors["purple"]*0.82+colors["deep"]*0.18+0.5,0,255).astype(np.uint8)
T[:,:,:3][rim]=rim_c
changed=np.any(T!=O,axis=2)
check(np.count_nonzero(changed)>10000,"not a distinct material revision")
check(np.count_nonzero(changed&~inside)==0,"changed pixels outside original glyph effect bbox")
check(np.array_equal(T[:,:,3],O[:,:,3]),"source alpha / geometry changed")
check(np.array_equal(T[~inside],O[~inside]),"protected atlas bytes changed")
check(np.array_equal(T[alpha==0],O[alpha==0]),"invisible rgb should remain preserved")
ddsp=OUT/"A251_Q089_SOURCE_CHROMA_UNPROMOTED.dds"
ddsp.write_bytes(oldb[:128]+im(T).transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes("raw","RGBA"))
D=decode(ddsp.read_bytes())
check(np.array_equal(D,T) and len(ddsp.read_bytes())==len(oldb),"actual saved DDS lossless roundtrip failed")
# Evidence: ORIGINAL, CLEAN, OLD, TRIAL plus complete different matte/practical scales,
# and RAW to avoid a one-view orientation assertion.
proof={}
original=im(S);clear=im(C);old=im(O);fresh=im(D)
proof["source"]=png("A251_ENGLISH_SOURCE_READABLE",original)
proof["clean"]=png("A251_ORIGINAL_CLEAN_READABLE",clear)
proof["old"]=png("A251_PRIOR_KOREAN_READABLE",old)
proof["new"]=png("A251_NEW_PERSISTED_KOREAN_READABLE",fresh)
proof["new_raw"]=png("A251_NEW_PERSISTED_KOREAN_RAW",fresh.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
proof["source_raw"]=png("A251_ENGLISH_SOURCE_RAW",original.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
for name,clr,pct in (("GRAY100",(100,100,100),100),("WHITE75",(255,255,255),75),("BLACK50",(0,0,0),50)):
 width,height=int(W*pct/100),int(H*pct/100)
 card=Image.new("RGB",(4*width,height),clr)
 for j,layer in enumerate((original,clear,old,fresh)):
  card.paste(bg(layer,clr).resize((width,height),Image.Resampling.LANCZOS),(j*width,0))
 proof[name]=png("A251_"+name+"_SOURCE_CLEAN_OLD_SAVED",card)
changed_visible=int(np.count_nonzero(changed&(alpha>0)))
warm_source=int(warm.sum())
orange_new=((D[:,:,3]>=190)&(D[:,:,0]>=190)&(D[:,:,1]>=60)&
            (D[:,:,1]<=175)&(D[:,:,2]<=160)&(D[:,:,0]>=D[:,:,1]+35))
report={"version":1,"run_key":RUN,"role":"A","queue_index":89,"priority":"A_OWNED_C3_OPTICAL_REWORK",
 "source_origin":SRC_URL,"canonical_source_sha256":SOURCE_HASH,
 "clean_sha256":CLEAN_HASH,"prior_official_sha256":PRIOR_HASH,
 "new_trial_dds":ref(ddsp),"official_promoted":0,"new_saved_dds_trial":1,
 "independent_root_cause":"C3 q089 source warm-orange/purple missing, official SHA741a05",
 "method_change":"SOURCE_DERIVED_NATIVE_PIXEL_MATERIAL_RECONSTRUCTION not width stretch or old flat face rerender",
 "source_palette_anchors":{k:[float(round(z,2)) for z in v] for k,v in colors.items()},
 "candidate_geometry_alpha_changed":0,"rgba_changed_outside_source_bbox":0,
 "source_clean_outside_bbox":0,"persisted_roundtrip_channel_mismatch":0,
 "changed_rgba_pixels":int(changed.sum()),"changed_visible_pixels":changed_visible,
 "source_bbox":BOX,"practical_reviews_created":["GRAY100","WHITE75","BLACK50","SOURCE_RAW","FINAL_RAW"],
 "source_warm_orange_pixels":warm_source,
 "trial_warm_orange_pixels":int(orange_new.sum()),
 "no_form_invention":"Existing native Korean silhouette/alpha unchanged. Material-chroma-only revision; morphology still requires independent C2 review.",
 "producer_machine":"PASS_SCOPED_NATIVE_PERSISTED_BYTES__OPTICAL_REVIEW_PENDING",
 "C2":"NOT_RUN","C3":"NOT_RUN","USER_INGAME":"NOT_RUN","RUNTIME_VALIDATION":"UNTESTED",
 "run_again_credit":0,"exclusions":["VR","FFB","DX11","DXVK"],"proofs":proof}
write_json(OUT/"A251_MACHINE_AND_HANDOFF.json",report)
print(json.dumps({"run":"A251","new_saved_trial_sha":report["new_trial_dds"]["sha256"],
 "changed_visible":changed_visible,"outside":0,"warm_source":warm_source,
 "warm_new":report["trial_warm_orange_pixels"]},ensure_ascii=False),flush=True)
