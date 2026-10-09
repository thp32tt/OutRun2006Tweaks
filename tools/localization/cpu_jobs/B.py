#!/usr/bin/env python3
"""B344 q060: source-conditioned isolated English-outline cleanup after C347 trial FAIL.

One NEW small-component mask method after B343 exact-match cleanup. Never
promotes an unreviewed DDS or treats numeric PASS as producer/C PASS.
"""
import io, os, sys, json, struct, hashlib, subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, label
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
OUT=G/"role_B/20261010-B344-Q060-C347-DARK-OUTLINE-CLEAN"
OUT.mkdir(parents=True,exist_ok=True)
h=lambda b:hashlib.sha256(b).hexdigest()
SRC="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
OFF="d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01"
TRIAL="8774e3993fc5a13f455f2c95ea5b358b2f75eae0634ab54bed137aeea819c9f6"
c=json.loads((G/"role_C/20261010-C347-C2-Q060-B343-TRIAL-INDEPENDENT/C347_Q060_CONTROLLER_C2_TRIAL_REWORK.json").read_text())
assert c["queue_index"]==60 and c["firsthand_visual"].find("slivers")>=0 and c["current_C2_approval"] is False
r=subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","60"],capture_output=True,text=True,check=True)
tri=json.loads(r.stdout)["assets"][0]
assert tri["next_action"] in ("MATERIAL_REWORK","METHOD_CHANGE_REQUIRED")
assert subprocess.run([sys.executable,"tools/localization/rework_triage.py","--index","60","--require-safe-rerender"],stdout=subprocess.DEVNULL).returncode in (0,2)
p=G/"hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
old=p.read_bytes()
tp=G/"role_B/20261010-B343-Q060-BEST-TIME-RESIDUE-PILOT/B343_Q060_BEST_TIME_GLYPH_RESIDUE_UNAPPROVED.dds"
prev=tp.read_bytes()
sp=G/"hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
if sp.is_file(): src=sp.read_bytes()
else:
 import urllib.request
 u="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
 with urllib.request.urlopen(u,timeout=120) as f: src=f.read()
assert h(old)==OFF and h(prev)==TRIAL and h(src)==SRC
assert len(old)==len(src)==len(prev)==33554560
assert old[:128]==prev[:128]==src[:128]
def dec(b):return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
S,O,T=map(dec,(src,old,prev))
assert S.shape==O.shape==T.shape==(2048,4096,4)
# Restrict correction to C347 independently observed isolated dark reddish ghost
# slivers between source BEST TIME and the Korean face. Connected-component
# filtering avoids eroding large Korean outline components or adjacent sprites.
l,t,r,b=2090,337,3120,485
s,o,v=S[t:b,l:r],O[t:b,l:r],T[t:b,l:r]
removed_first=(o[:,:,3]>0)&(v[:,:,3]==0)
assert int(removed_first.sum())==19243
# Determine safe *above Korean* cutoff from actual persisted cyan face, not a
# hardcoded rectangle derived from the desired output difference.
rgb=v[:,:,:3].astype(np.int16)
cyan=(rgb[:,:,2]>170)&(rgb[:,:,1]>90)&(rgb[:,:,2]>rgb[:,:,0]+30)&(v[:,:,3]>100)
yy,xx=np.where(cyan & (np.indices(cyan.shape)[0]>=35))
assert yy.size>1000,("Korean/cyan source family not found",int(yy.size))
# Under no circumstances touch the Hangul outline or face.
first_face=int(np.percentile(yy,1))
cutoff=min(first_face-13,61)
assert 17<=cutoff<=61,("unsafe cyan separation",first_face,cutoff)
sy=s[:,:,:3].astype(np.int16)
warm=(sy[:,:,0]>160)&(sy[:,:,1]>60)&(sy[:,:,1]<240)&(sy[:,:,2]<140)&(sy[:,:,0]>sy[:,:,1]+35)&(s[:,:,3]>80)
english_support=binary_dilation(warm,iterations=17)
near_old=binary_dilation(removed_first,iterations=5)
reddish=(rgb[:,:,0]>rgb[:,:,1]+8)&(rgb[:,:,0]>rgb[:,:,2]+8)&(v[:,:,3]>10)
# Probe genuine isolated alpha-connected residuals; never cut a partial
# component connected to Korean or an adjacent original artwork region.
alpha=v[:,:,3]>10
components,n=label(alpha,np.ones((3,3),dtype=np.int8))
area=np.bincount(components.ravel(),minlength=n+1)
cand=np.zeros(alpha.shape,bool)
components_removed=[]
for idx in range(1,n+1):
 size=int(area[idx])
 if size>200 or size<1:continue
 comp=components==idx
 ys,xs=np.nonzero(comp)
 if ys.size==0:continue
 if int(ys.max())>=cutoff or int(ys.min())<0:continue
 if not np.any(comp&english_support&near_old&reddish):continue
 # Erase whole isolated alpha island, not just selective warm pixels.
 cand|=comp
 components_removed.append({"pixels":size,"native_readable_bbox":[l+int(xs.min()),t+int(ys.min()),l+int(xs.max()+1),t+int(ys.max()+1)]})
N=T.copy()
if cand.any():N[t:b,l:r][cand]=0
changed=np.any(T!=N,axis=2)
assert int(changed.sum())==int(cand.sum())
assert int(changed.sum())<=2000
assert not np.any(changed[t+cutoff:,:])
assert np.array_equal(N[:t],T[:t]) and np.array_equal(N[t+b:],T[t+b:])
scope=np.zeros(changed.shape,bool);scope[t:t+b,l:r]=True
assert int(np.count_nonzero(changed&~scope))==0
# Restrict to the gap above Korean cyan face, protect all Korean pixels.
assert np.array_equal(N[t+cutoff:t+b,l:r],T[t+cutoff:t+b,l:r])
order=[0,1,2,3] if struct.unpack_from("<I",prev,92)[0]==255 else [2,1,0,3]
outbytes=prev[:128]+np.flipud(N)[:,:,order].copy().tobytes()
assert len(outbytes)==len(prev) and np.array_equal(dec(outbytes),N)
outname="B344_Q060_ISOLATED_ENGLISH_OUTLINE_UNAPPROVED.dds"
if cand.any():(OUT/outname).write_bytes(outbytes)
Image.fromarray((cand*255).astype(np.uint8),"L").save(OUT/"B344_ACTUAL_ERASURE_MASK_NATIVE_CROP.png")
# SHA-pinned SOURCE/OFFICIAL/B343/NEW: black/gray, both orientations, 100/75/50.
views=[]
def flat(a,bg):
 x=Image.new("RGBA",(a.shape[1],a.shape[0]),bg+(255,))
 x.alpha_composite(Image.fromarray(a,"RGBA"))
 return x.convert("RGB")
for orient in ("FLIPY","RAW"):
 for name,bg in (("GRAY",(128,128,128)),("BLACK",(0,0,0))):
  for pct in (100,75,50):
   samples=[S[285:530,1990:3190],O[285:530,1990:3190],T[285:530,1990:3190],N[285:530,1990:3190]]
   panels=[flat(z,bg) for z in samples]
   if orient=="RAW":panels=[z.transpose(Image.Transpose.FLIP_TOP_BOTTOM) for z in panels]
   if pct<100:panels=[z.resize((round(z.width*pct/100),round(z.height*pct/100)),Image.Resampling.LANCZOS) for z in panels]
   contact=Image.new("RGB",(panels[0].width*4+24,panels[0].height),bg)
   for i,pnl in enumerate(panels):contact.paste(pnl,(i*(pnl.width+8),0))
   file=f"B344_{orient}_{name}_{pct}_SOURCE_OFFICIAL_B343_TRIAL.png"
   contact.save(OUT/file,optimize=True);views.append(file)
qa={"schema_version":2,"run":"B344","role":"B","queue_index":60,
"run_key":"OUTRUN-KOR-B344-Q060-C347-SOURCE-CONDITIONED-OUTLINE-20261010",
"prior_rejection":"C347 scoped B343 trial visual FAIL residual reddish/navy slivers",
"new_method":"connected alpha island on persisted B343; source-warm + prior-erasure adjacency + reddish tone; strictly above 1st percentile Korean cyan; no glyph resizing, no opaque rectangle",
"input_source_sha256":SRC,"official_sha256":OFF,"B343_trial_sha256":TRIAL,
"new_trial_sha256":h(outbytes) if cand.any() else None,
"native":[4096,2048],"DDS":"RGBA32/mip1",
"first_korean_cyan_offset":first_face,"preserved_korean_offset_start":cutoff,
"remaining_alpha_components_removed":components_removed,
"pixels_removed":int(cand.sum()),"pixels_changed_outside_scope":0,
"source_q060_other_cells_preserved":True,"Korean_below_cutoff_identical":True,
"direct_producer_visual":"PENDING; numeric/mechanical evidence alone NOT PASS",
"P1":"PARTIAL_NOT_FAMILY_QUALIFIED","P2":"UNMODIFIED","P3":"UNAPPROVED_TRIAL",
"new_material_trial_dds":1 if cand.any() else 0,"new_promoted_dds":0,
"official_unchanged":True,"C2":"REWORK_REQUIRED","C3":"BLOCKED","APPROVAL":False,
"IGR044":"OPEN_USER_INGAME_FAIL","RUNTIME_VALIDATION":"UNTESTED",
"backend":"GITHUB_ACTIONS","comparison_views":views}
(OUT/"B344_TRIAL_MACHINE_AND_SCOPE.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n")
print("B344",qa["new_trial_sha256"],qa["pixels_removed"],"face",first_face,"cutoff",cutoff,"components",components_removed,flush=True)
