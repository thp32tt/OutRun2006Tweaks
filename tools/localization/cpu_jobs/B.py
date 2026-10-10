#!/usr/bin/env python3
"""B363 q092 P0/C364 optical rework: source-derived continuous soft glow.
Single representative Korean OutRun Mode row; second original Korean line
and ALL other atlas content preserved. This unpromoted BC3 pilot is not C PASS.
"""
import io,os,json,sys,struct,hashlib,subprocess,tempfile,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter,binary_dilation
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
BASE=G/"role_B/20261007-B-MANUALQA221-1A43E9D9"
OUT=G/"role_B/20261011-B363-Q092-SOURCE-GLOW-BC3-PILOT";OUT.mkdir(parents=True,exist_ok=True)
SHA=lambda b:hashlib.sha256(b).hexdigest()
SRC_SHA="d19e5191fb1e084fbeb182b5528738b4ad47ab56bef38fb1e1f027e0b6816774"
OFF_SHA="c23888347f446a0acd65667624bd3ee210f7d9a84b5f7adafeb746c94676a43a"
tri=json.loads(subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","92"],text=True,capture_output=True,check=True).stdout)["assets"][0]
assert tri["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED"),tri
# Reusable-plate lookup: no unqualified PSD substitution, no new made-up C approval.
lk=subprocess.run([sys.executable,"tools/localization/plate_library.py","inspect","--index","92",
 "--source-sha",SRC_SHA,"--region","outrun_mode","--orientation","readable_flip_y"],
 capture_output=True,text=True)
if lk.returncode==0:
 info=json.loads(lk.stdout)
 assert info.get("plate_review")=="PLATE_PASS",("LIBRARY_C2_REVIEW_REQUIRED",info)
 raise RuntimeError("PREPARE_EXACT_LIBRARY_CLEAN_BEFORE_NEW_PILOT")
assert "missing or ambiguous" in lk.stderr.lower(),("UNEXPECTED_PLATE_LIBRARY_FAILURE",lk.stderr[-300:])
plate_library="NOT_REGISTERED_REUSE_B221_EXISTING_CLEAN_WITH_SOURCE_PIXEL_QA"
rel="textures/load/spr_sprani_selector_cvt_Exst/1A43E9D9_512x64.dds"
old=(G/"hd_candidates"/rel).read_bytes()
assert SHA(old)==OFF_SHA,("CONCURRENT_OFFICIAL_CHANGE",SHA(old))
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/1A43E9D9_512x64.dds"
with urllib.request.urlopen(url,timeout=90) as stream:src=stream.read()
assert SHA(src)==SRC_SHA
assert src[:128]==old[:128] and src[84:88]==b"DXT5"
w,h=struct.unpack_from("<II",src,16)[0],struct.unpack_from("<I",src,12)[0]
assert (w,h,len(old),len(src))==(2048,256,524416,524416),(w,h,len(old),len(src))
assert struct.unpack_from("<I",src,28)[0]==1
def decode(data):
 return np.array(Image.open(io.BytesIO(data)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S=decode(src);O=decode(old)
p=(BASE/"1A43E9D9_CLEAN_PLATE.png")
platebytes=p.read_bytes();C=np.array(Image.open(io.BytesIO(platebytes)).convert("RGBA"))
assert C.shape==O.shape
# Existing B221 P1 source-conditioned removal is SHA-bound to this source.
rm=(BASE/"1A43E9D9_SOURCE_TEXT_MASK.png").read_bytes()
R=np.array(Image.open(io.BytesIO(rm)).convert("L"))>0
assert R.shape==(h,w)
changed_clean=np.any(C!=S,axis=2)
assert np.count_nonzero(changed_clean & ~R)==0,("P1_CLEAN_OUTSIDE_SOURCE_MASK",np.count_nonzero(changed_clean&~R))
assert np.count_nonzero(C[:,:,3][R])==0,("P1_ENGLISH_ALPHA_RESIDUE",np.count_nonzero(C[:,:,3][R]))
# q092 two known English source sprites; this run touches OutRun Mode only.
bbox=(387,13,1318,132)
second=(519,132,1589,245)
# Modify complete 4x4 BC3 blocks lying strictly inside English source bbox.
# source x coordinate can reach 387 but blocks start 388, source y 13 -> 16.
srcmask=np.zeros((h,w),bool);l,t,r,b=bbox;srcmask[t:b,l:r]=True
safe=np.zeros((h,w),bool);safe[16:132,388:1316]=True
xy=np.zeros((h,w),bool);xy[19:130,390:1118]=True
alpha=O[:,:,3]
rgb=O[:,:,:3]
seed=(alpha>70)&xy
assert 10000<int(seed.sum())<90000,("GLYPH_SEED_OUT_OF_RANGE",int(seed.sum()))
# Original English source has a diffuse near-white halo. Sample it at
# alpha 1..190 rather than drawing a hard/solid white stroke.
sr= S[:,:,:3].astype(np.int16)
bright=(np.min(sr,axis=2)>=190)&(S[:,:,3]>3)&srcmask
assert int(bright.sum())>8000,("SOURCE_WHITE_GLOW_UNRESOLVED",int(bright.sum()))
neutral=np.median(S[bright,:3],axis=0).astype(np.uint8)
# Apply source-like outer diffusion to existing Hangul shape, not regenerate
# lettering, distort source label, or repaint any other sprites.
soft=gaussian_filter(binary_dilation(seed,iterations=1).astype(np.float32),sigma=3.5)
glow=np.clip(np.rint(soft*150),0,146).astype(np.uint8)
glow[~safe]=0
# Hard failure when halo is painted atop the real source's protected region.
assert not np.any((glow>0)&~srcmask)
rgba=np.zeros_like(O)
rgba[:,:,:3]=neutral
rgba[:,:,3]=glow
# Single transparent-only compositing pass over PREVIOUS Korean text; plate
# verified separately and source alpha removed; source BG is transparent.
a=O[:,:,3].astype(np.float64)/255
g=glow.astype(np.float64)/255
outalpha=a+g*(1-a)
premult=np.zeros((h,w,3),np.float64)
premult[:]=O[:,:,:3].astype(np.float64)*a[:,:,None]+neutral[None,None,:]*g[:,:,None]*(1-a[:,:,None])
new=np.array(O,copy=True)
part=(g>0)
new[:,:,:3][part]=np.clip(np.rint(premult[part]/np.maximum(outalpha[part,None],1e-6)),0,255).astype(np.uint8)
new[:,:,3][part]=np.clip(np.rint(outalpha[part]*255),0,255).astype(np.uint8)
assert np.array_equal(new[~safe],O[~safe])
# Verify first full row only effect, second row exact preserved in readable RGBA.
assert np.array_equal(new[132:245],O[132:245])
assert np.count_nonzero((new[:,:,3]>0)&~srcmask&~(O[:,:,3]>0))==0
# CPU-only deterministic DXT5 encoder; preserve every unused original BC3 block.
def rgb565(c):
 return (int(c[0])//8<<11)|(int(c[1])//4<<5)|(int(c[2])//8)
def rgb8(v):
 return np.array([(v>>11&31)*255//31,(v>>5&63)*255//63,(v&31)*255//31],np.float64)
def block(rawrgba):
 pix=rawrgba.reshape(16,4).astype(np.float64)
 al=np.rint(pix[:,3]).astype(np.uint8)
 aa0,aa1=int(al.max()),int(al.min())
 if aa0==aa1:
  aa1=max(0,aa0-1)
 alut=np.array([aa0,aa1]+[( (7-k)*aa0+k*aa1+3)//7 for k in range(1,7)],np.float64)
 ai=np.argmin(abs(al[:,None]-alut[None,:]),axis=1)
 abits=sum(int(ai[i])<<(3*i) for i in range(16))
 # Source-bounded palette adapts neutral glow, orange original and navy.
 cols=pix[:,:3].copy()
 vis=al>=5
 if vis.any():
  color=cols[vis]
  pmin=np.min(color,axis=0);pmax=np.max(color,axis=0)
 else:pmin=np.zeros(3);pmax=np.zeros(3)
 e0=rgb565(pmax);e1=rgb565(pmin)
 if e0<=e1:
  e0,e1=max(e0,e1),min(e0,e1)
  if e0==e1:e0=min(65535,e1+1) if e1<65535 else e1;e1=max(0,e1-1)
 c0,c1=rgb8(e0),rgb8(e1)
 pal=np.array([c0,c1,(2*c0+c1)/3,(c0+2*c1)/3])
 ci=np.argmin(np.sum((cols[:,None,:]-pal[None,:,:])**2,axis=2),axis=1)
 cbits=sum(int(ci[i])<<(2*i) for i in range(16))
 return bytes((aa0,aa1))+abits.to_bytes(6,"little")+struct.pack("<HHI",e0,e1,cbits)
raw=bytearray(old);blocks=0
for y in range(16,132,4):
 for x in range(388,1316,4):
  region=new[y:y+4,x:x+4]
  prior=O[y:y+4,x:x+4]
  if np.array_equal(prior,region):continue
  # Stored raw rows are vertically flipped; reverse the per-block rows.
  payload=block(region[::-1].copy())
  off=128+(((h-y-4)//4)*(w//4)+x//4)*16
  raw[off:off+16]=payload;blocks+=1
assert blocks>50
candidate=bytes(raw);D=decode(candidate)
assert len(candidate)==len(old) and candidate[:128]==old[:128] and SHA(candidate)!=OFF_SHA
changed=np.any(D!=O,axis=2);outside=int(np.count_nonzero(changed&~srcmask))
assert outside==0,("BC3_CHANGED_OUTSIDE_SOURCE",outside)
assert np.array_equal(D[132:245],O[132:245]),"SECOND_ROW_CHANGED"
# Exactly preserve untouched original byte blocks (not only decoded pixels).
oldblocks=np.frombuffer(old[128:],np.uint8).reshape(h//4,w//4,16)
newblocks=np.frombuffer(candidate[128:],np.uint8).reshape(h//4,w//4,16)
bm=np.any(oldblocks!=newblocks,axis=2)
allowedblocks=np.zeros((h//4,w//4),bool);allowedblocks[(h-132)//4:(h-16)//4,388//4:1316//4]=True  # DDS block order is raw mirror-Y
assert not np.any(bm&~allowedblocks)
# Prove desired phenomenon appears in independently decoded persisted alpha.
src_trans=int(np.count_nonzero((S[:,:,3]>=1)&(S[:,:,3]<180)&srcmask))
old_trans=int(np.count_nonzero((O[:,:,3]>=1)&(O[:,:,3]<180)&srcmask))
new_trans=int(np.count_nonzero((D[:,:,3]>=1)&(D[:,:,3]<180)&srcmask))
assert new_trans>old_trans+1000,("DIFFUSE_GLOW_NOT_RESTORED",src_trans,old_trans,new_trans)
ddsf=OUT/"B363_Q092_OUTRUN_MODE_SOFT_GLOW_UNAPPROVED.dds"
ddsf.write_bytes(candidate)
assert SHA(ddsf.read_bytes())==SHA(candidate)
assert np.array_equal(decode(ddsf.read_bytes()),D)
# SOURCE/CLEAN/OLD/TRIAL pixel-layer comparison for native/75/50 and RAW.
evidence=[]
def composite(a,bg,mode):
 r0=Image.fromarray(a[8:139,380:1600],"RGBA")
 bk=Image.new("RGBA",r0.size,(bg,bg,bg,255));bk.alpha_composite(r0)
 im=bk.convert("RGB")
 return im if mode=="FLIPY" else im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
for mode in ["FLIPY","RAW"]:
 for bg in ([0,128,255] if mode=="FLIPY" else [128]):
  for pct in ([100,75,50] if mode=="FLIPY" else [100]):
   ims=[composite(v,bg,mode) for v in [S,C,O,D]]
   if pct!=100:ims=[v.resize((v.width*pct//100,v.height*pct//100),Image.Resampling.LANCZOS) for v in ims]
   cw,ch=ims[0].size
   sheet=Image.new("RGB",(cw*4+36,ch),(bg,bg,bg))
   for k,img in enumerate(ims):sheet.paste(img,(k*(cw+12),0))
   fn=f"B363_SOURCE_CLEAN_OFFICIAL_GLOW_{mode}_BG{bg}_{pct}.png"
   sheet.save(OUT/fn,optimize=True);evidence.append(fn)
Image.fromarray(np.where(changed,255,0).astype(np.uint8),"L").save(OUT/"B363_CHANGED_PIXEL_MASK.png")
Image.fromarray(C[8:139,380:1600],"RGBA").save(OUT/"B363_SOURCE_CLEAN_ONLY_ROI.png")
Image.fromarray(D[8:139,380:1600],"RGBA").save(OUT/"B363_PERSISTED_COMPOSITE_ROI.png")
qa={"role":"B","run":"B363","queue_index":92,"run_key":"OUTRUN-KOR-B363-Q092-SOURCE-DIFFUSE-GLOW-FIRST-20261011-0432",
"triage":tri["next_action"],"source_sha256":SRC_SHA,"official_sha256":OFF_SHA,
"source_clean_reused":"B221_SOURCE_CONDITIONED_ALPHA_ZERO_P1","clean_sha256":SHA(platebytes),
"plate_library_inspect":plate_library,"source_removal_mask_sha256":SHA(rm),
"material_method":"Separate SOURCE RGB white halo sample and native sigma3.5 continuous Gaussian transparent alpha BEFORE existing Korean lettering composite. Unlike B221 hard dotted white outline; BC3 recalibrates affected 4x4 only. Font/semantic Korean pixels preserved, no repeated glyph rerender.",
"new_unapproved_trial_sha256":SHA(candidate),"dds_format":"BC3_DXT5","native":[w,h],"mips":1,
"native_orientation":"RAW_MIRROR_Y","source_bbox":list(bbox),"changed_bc3_blocks":int(bm.sum()),
"changed_rgba_pixels":int(changed.sum()),"changed_rgba_outside_source_bbox":outside,
"protected_second_row_exact":True,"unchanged_blocks_outside_source":True,
"original_source_translucent_1_179":src_trans,"old_korean_translucent_1_179":old_trans,
"new_trial_translucent_1_179":new_trans,
"source_white_glow_median_rgb":neutral.tolist(),"mechanical_result":"PASS_SCOPED",
"producer_visual":"PENDING_ACTUAL_NATIVE_AND_50_PERCENT_INSPECTION","independent_C2":"NOT_RUN","C3":"BLOCKED",
"official_promoted_dds":0,"new_trial_dds":1,"RUNTIME_VALIDATION":"UNTESTED",
"evidence_previews":evidence,"excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B363_MACHINE.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
(OUT/"recipe.json").write_text(json.dumps({"source_sha256":SRC_SHA,"old_official_sha256":OFF_SHA,
 "material":"source-sampled diffused halo sigma3.5 + existing native Korean; transparent-only",
 "plate_SHA":SHA(platebytes),"BC3_codec":"deterministic-native-4x4-palette","scoped_sprite":"outrun_mode","source_original_bbox":list(bbox),"protected_row2":list(second)},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B363","trial_sha":SHA(candidate),"blocks":int(bm.sum()),"changed":int(changed.sum()),"glow_alpha":[src_trans,old_trans,new_trans],"outside":outside}),flush=True)
