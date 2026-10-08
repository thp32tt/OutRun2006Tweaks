#!/usr/bin/env python3
"""B301 q098: preserve exact B279 BC3-alpha; source-conditioned inner navy band.
This retries the *same task* after visual failure of B300 alpha re-encode.
"""
import hashlib,io,json,os,struct,subprocess,sys,urllib.request
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
DIR=G/"role_B/20261009-B301-Q098-ALPHA-PRESERVED-NAVY-DEPTH"
DIR.mkdir(parents=True,exist_ok=True)
R="textures/load/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds"
O_SHA="192d627428dfa4328035d5105dcfbd4395d8bbadfa154a9f533a1c48583eac4b"
S_SHA="3b3cdd76b03014e0ba6a47f4e98a187fdf6ae4297314494cbe1d3d4c586f1f59"
C_SHA="b5c9c07a2490abd055153f750b415193eb84ef14c298b3e3873fd915db3af9e8"
sha=lambda b:hashlib.sha256(b).hexdigest()
d=(G/"hd_candidates"/R).read_bytes()
assert sha(d)==O_SHA
tri=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","98","--require-safe-rerender"],capture_output=True,text=True,check=True)
assert json.loads(tri.stdout)["assets"][0]["next_action"]=="MATERIAL_REWORK"
with urllib.request.urlopen("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/42E618FD_512x32.dds",timeout=160) as f:sen=f.read()
assert sha(sen)==S_SHA and sen[:128]==d[:128]
cleanpath=G/"role_B/20261005-B-PRODUCTION40/42E618FD_CLEAN_PLATE.png"
assert sha(cleanpath.read_bytes())==C_SHA
def dec(by):
 return np.asarray(Image.open(io.BytesIO(by)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S=dec(sen);P=dec(d);C=np.asarray(Image.open(cleanpath).convert("RGBA"))
assert S.shape==P.shape==C.shape==(128,2048,4)
src=(431,6,1674,123)
xx,yy=np.meshgrid(np.arange(2048),np.arange(128))
source_region=(xx>=src[0])&(xx<src[2])&(yy>=src[1])&(yy<src[3])
assert int(np.count_nonzero(np.any(S!=C,axis=2)&~source_region))==0
assert int(np.count_nonzero(C[:,:,3]&source_region))==0
# B300 failed because re-encoding native BC3 alpha caused lost small Hangul
# counters + horizontal colored artifacts. This method never writes an alpha
# byte. It changes only 2-bit color indices of well-supported INNER WHITE
# edge pixels, preserving untouched already-encoded white/navy/antialias.
W=(P[:,:,:3].min(axis=2)>=215)&(P[:,:,3]>=170)
dist=distance_transform_edt(W)
band=W&(dist<=2.5)
# Exact original source limits with at least 2px positive margins.
safe=(xx>=580)&(xx<1524)&(yy>=9)&(yy<120)&source_region
band&=safe
assert band.sum()>3000,band.sum()
def rgb(v):
 return np.array([(((v>>11)&31)*255+15)//31,(((v>>5)&63)*255+31)//63,((v&31)*255+15)//31],dtype=np.int16)
data=bytearray(d)
changed=0;blocks=set();no_dark=0
# Unlike B300R, white-only BC3 blocks do not contain an addressable navy
# palette index. Rebuild only those 8-byte COLOR planes from source white/navy.
# Leave every ALPHA byte (offset +0..+7) untouched. This avoids B300's
# antialias/holes destroyed by DXT5 alpha re-quantization.
white565=0xffff
navy565=((0*31+127)//255<<11)|((12*63+127)//255<<5)|((57*31+127)//255)
def x565(v):
 return np.array([(((v>>11)&31)*255+15)//31,(((v>>5)&63)*255+31)//63,((v&31)*255+15)//31],dtype=np.int16)
p0,p1=x565(white565),x565(navy565)
palette=np.array([p0,p1,(2*p0+p1+1)//3,(p0+2*p1+1)//3],dtype=np.int16)
assert np.linalg.norm(p1-np.array([0,12,57]))<5
for by in range(8,120,4):
 for bx in range(576,1528,4):
  sub=band[by:by+4,bx:bx+4]
  if not sub.any():continue
  assert bx>=src[0] and bx+4<=src[2] and by>=src[1] and by+4<=src[3]
  desired=P[by:by+4,bx:bx+4,:3].astype(np.int16).copy()
  desired[sub]=p1
  distance=((desired[:,:,None,:]-palette[None,None,:,:])**2).sum(axis=3)
  nearest=distance.argmin(axis=2)
  bits=0
  for iy in range(4):
   for ix in range(4):
    bits|=int(nearest[iy,ix])<<(2*((3-iy)*4+ix))
  off=128+(((128-by-4)//4)*(2048//4)+(bx//4))*16
  struct.pack_into("<HHI",data,off+8,white565,navy565,bits)
  changed+=int(sub.sum());blocks.add((bx,by))
trial=bytes(data)
assert trial[:128]==d[:128] and len(trial)==len(d) and changed>3000,(changed,no_dark)
D=dec(trial)
assert np.array_equal(P[:,:,3],D[:,:,3]),"ALPHA MUST BE BYTE-IDENTICAL"
# Entire BC3 alpha plane cannot have changed because only the color index
# offset+12..+15 was written. Verify decoded visual outside protected scope.
diff=np.any(P!=D,axis=2)
assert not np.any(diff&~safe),("color changed outside safe",int((diff&~safe).sum()))
assert not np.any(diff&~source_region)
assert D[:,:,3].max()==P[:,:,3].max()
pixels=D[:,:,3]>16
ys,xs=np.where(pixels&safe)
bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
assert bbox[0]>src[0] and bbox[1]>src[1] and bbox[2]<src[2] and bbox[3]<src[3]
path=DIR/"B301_Q098_TRIAL_NOT_PROMOTED.dds"
path.write_bytes(trial)
assert sha(path.read_bytes())==sha(trial) and np.array_equal(dec(path.read_bytes()),D)
def count(im):
 rgb=im[:,:,:3];a=im[:,:,3]
 white=(rgb.min(axis=2)>220)&(a>120)&source_region
 navy=(rgb[:,:,0]<55)&(rgb[:,:,1]<80)&(rgb[:,:,2]>rgb[:,:,0]+12)&(a>80)&source_region
 return {"white":int(white.sum()),"navy":int(navy.sum()),"ratio":round(float(white.sum()/max(1,navy.sum())),3)}
def compose(im,bg):
 x=Image.new("RGBA",(2048,128),bg)
 x.alpha_composite(Image.fromarray(im,"RGBA"))
 return x.convert("RGB")
views=[]
for ori in ("READABLE","RAW"):
 seq=(S,C,P,D) if ori=="READABLE" else tuple(np.flipud(x).copy() for x in (S,C,P,D))
 for name,bg in [("GRAY",(120,120,120,255)),("WHITE",(255,255,255,255)),("BLACK",(0,0,0,255))]:
  for pct in (100,75,50):
   imgs=[compose(v,bg) for v in seq]
   if pct!=100:
    imgs=[im.resize((round(im.width*pct/100),round(im.height*pct/100)),Image.Resampling.LANCZOS) for im in imgs]
   out=Image.new("RGB",(sum(i.width for i in imgs)+12,max(i.height for i in imgs)),(120,120,120))
   px=0
   for im in imgs:out.paste(im,(px,0));px+=im.width+4
   nm=f"{ori}_{name}_{pct}_SOURCE_CLEAN_B279_B301.png"
   out.save(DIR/nm);views.append(nm)
for name,arr in [("SOURCE",S),("CLEAN",C),("OLD",P),("TRIAL",D)]:
 Image.fromarray(arr,"RGBA").save(DIR/(name+"_NATIVE_LOSSLESS.png"))
report={"role":"B","run":"B301","queue_index":98,"asset":R,
 "retry_of":"B300_AND_B300R_NONPROMOTED_ALPHA_ARTIFACT_AND_PALETTE_BLOCKED",
 "triage":"MATERIAL_REWORK","source_sha256":S_SHA,"clean_sha256":C_SHA,
 "prior_sha256":O_SHA,"trial_sha256":sha(trial),"new_trial_dds":1,"promoted_dds":0,
 "method":"native BC3 RGB palette 8-byte source white/navy block rebuild in a 2.5px inner-white border, untouched DXT5 ALPHA 8 bytes and existing alpha counters; avoids B300 alpha stripes and B300R white-only palette restriction; no raster upscaling",
 "source_counts":count(S),"prior_counts":count(P),"trial_counts":count(D),
 "candidate_bbox":bbox,"source_bbox":src,
 "changed_native_pixels":int(diff.sum()),"native_color_indices_replaced":changed,
 "changed_blocks":len(blocks),"blocked_non_navy":no_dark,
 "outside_source_rgba":0,"outside_safe_rgba":0,"alpha_exact":True,
 "header_exact":True,"source_clean_residue_alpha":0,"roundtrip_exact":True,
 "evidence_views":views,"producer_visual":"PENDING_CONTROLLER",
 "C2":"NOT_RUN","C3":"NOT_RUN","APPROVAL":False,
 "RUNTIME_VALIDATION":"UNTESTED","excluded":["VR","FFB","DX11","DXVK"]}
(DIR/"B301_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print("B301_TRIAL_OK",json.dumps({"sha":sha(trial),"changed":changed,"blocks":len(blocks),"ratio":count(D),"bbox":bbox},ensure_ascii=False))
