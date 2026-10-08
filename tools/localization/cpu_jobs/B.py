#!/usr/bin/env python3
"""B298 q154 C311-rejected three gray glyphs: native source-stroke reconstruction TRIAL.
No automatic candidate promotion; controller must review exact saved DDS first.
"""
import os,io,json,hashlib,tempfile,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import maximum_filter
assert os.getenv("OUTRUN_CPU_WORKER")=="github-actions" and os.getenv("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
ASSET=G/"hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
OUT=G/"role_B/20261009-B298-Q154-GRAY-STROKE-SOURCE-FAMILY-TRIAL";OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
OLD_SHA="94678124f6cddaeb44520c6419f4b475d1452866c052ff301a4859dddf38cb1f"
SRC_SHA="15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf"
p=ASSET.read_bytes();assert sha(p)==OLD_SHA,("concurrent candidate drift",sha(p))
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"
with tempfile.TemporaryDirectory(prefix="b298_q154_") as tmp:
 f=Path(tmp)/"source.dds";urllib.request.urlretrieve(url,f);s=f.read_bytes()
assert sha(s)==SRC_SHA and s[:128]==p[:128],("canonical source mismatch",sha(s))
def dec(b): return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
source,old=dec(s),dec(p)
assert old.shape==source.shape==(1024,4096,4) and len(p)==128+4096*1024*4
# The original B60-authored clean plate was independently proven by C305/C311:
# no alpha in the eight exact source cells and no source-to-clean change outside.
c305=json.loads((G/"role_C/20261008-C305-C2-Q154-AUTHORED-CLEAN-BGW/C305_Q154_CONTROLLER_C_HOLD.json").read_text())
cells=[tuple(r["source_bbox"]) for r in c305["per_region"]]
assert len(cells)==8
allowed8=np.zeros(old.shape[:2],bool)
for l,t,r,b in cells:allowed8[t:b,l:r]=1
assert np.count_nonzero(np.any(source!=old,axis=2)&~allowed8)==0
clean=source.copy()
for l,t,r,b in cells:clean[t:b,l:r]=0
assert np.count_nonzero(clean[:,:,3]&allowed8)==0
# q154 source has upright flat gray face and no user-approved stroke/outset.
# Expand the CURRENT Korean alpha support by exactly one native pixel, using
# source face RGB without adding a dark box/shadow or altering untouched red art.
boxes=[
 ("06_single_player_gray",(1610,286,2197,350)),
 ("07_showroom_gray",(2674,288,3094,350)),
 ("08_multiplayer_gray",(2566,952,3086,1014)),
]
out=old.copy(); masks={}; regionstats=[]
for name,(l,t,r,b) in boxes:
 src=source[t:b,l:r]; before=old[t:b,l:r]
 gray=(src[:,:,3]>=245)&(np.max(abs(src[:,:,:3].astype(np.int16)-np.array([78,96,100])),axis=2)<=3)
 assert int(gray.sum())>1500,(name,gray.sum())
 opaque=np.array([78,96,100],dtype=np.uint8)
 # Preserve decoded fine alpha; one-pixel native expanded stroke yields a
 # materially heavier source-family core without arbitrary width stretching.
 oldalpha=before[:,:,3]; dilated=maximum_filter(oldalpha,size=3,mode="constant")
 # Strict margin guard: not a single effect pixel may touch the original bbox edge
 assert not np.any(dilated[[0,-1],:]) and not np.any(dilated[:,[0,-1]]),(name,"source ceiling")
 added=(dilated>oldalpha)
 after=before.copy();after[:,:,3]=dilated
 after[added,:3]=opaque
 out[t:b,l:r]=after
 assert np.count_nonzero(np.any(out[t:b,l:r]!=before,axis=2))>0
 yy,xx=np.nonzero(dilated>128)
 bb=[l+int(xx.min()),t+int(yy.min()),l+int(xx.max()+1),t+int(yy.max()+1)]
 assert bb[0]>l and bb[1]>t and bb[2]<r and bb[3]<b,(name,bb)
 masks[name]=(l,t,r,b)
 regionstats.append({"id":name,"source_box":[l,t,r,b],"candidate_bbox":bb,
 "new_native_stroke_pixels":int(added.sum()),"source_face_rgb":opaque.tolist(),
 "source_vs_clean_alpha":0,"changed_outside_region":0})
changed=np.any(out!=old,axis=2)
allowed3=np.zeros(old.shape[:2],bool)
for l,t,r,b in [v for _,v in boxes]:allowed3[t:b,l:r]=1
assert int(np.count_nonzero(changed&~allowed3))==0
assert np.array_equal(out[~allowed3],old[~allowed3])
raw= p[:128]+np.flipud(out).copy().tobytes()
assert len(raw)==len(p) and raw[:128]==p[:128]
persist=dec(raw)
assert np.array_equal(persist,out)
assert sha(raw)!=sha(p)
def bgcomp(im,bg):
 layer=Image.new("RGBA",(im.shape[1],im.shape[0]),bg)
 layer.alpha_composite(Image.fromarray(im,"RGBA"))
 return layer.convert("RGB")
for name,(l,t,r,b) in boxes:
 # Unscaled lossless native region comparisons are the primary evidence.
 for kind,arr in [("SOURCE",source),("CLEAN",clean),("OLD",old),("TRIAL",persist)]:
  for bgname,bg in [("WHITE",(255,255,255,255)),("BLACK",(0,0,0,255)),("GRAY",(110,110,110,255))]:
   panel=bgcomp(arr[t:b,l:r],bg)
   panel.save(OUT/f"{name}_{kind}_{bgname}_NATIVE.png")
 for scale in (100,75,50):
  frames=[bgcomp(arr[t:b,l:r],(225,225,225,255)) for arr in (source,clean,old,persist)]
  if scale!=100:
   frames=[im.resize((int(im.width*scale/100),max(1,int(im.height*scale/100))),Image.Resampling.LANCZOS) for im in frames]
  w=sum(x.width for x in frames)+12
  sheet=Image.new("RGB",(w,max(x.height for x in frames)),(170,170,170))
  xpos=0
  for im in frames:sheet.paste(im,(xpos,0));xpos+=im.width+4
  sheet.save(OUT/f"{name}_SOURCE_CLEAN_OLD_TRIAL_{scale}pct.png")
 rawviews=[bgcomp(np.flipud(arr[t:b,l:r]),(110,110,110,255)) for arr in (source,clean,old,persist)]
 rawsheet=Image.new("RGB",(sum(x.width for x in rawviews)+12,max(x.height for x in rawviews)),(120,120,120))
 xpos=0
 for im in rawviews:rawsheet.paste(im,(xpos,0));xpos+=im.width+4
 rawsheet.save(OUT/f"{name}_RAW_NATIVE.png")
(OUT/"Q154_B298_TRIAL_NOT_PROMOTED.dds").write_bytes(raw)
report={"run":"B298","role":"B","queue_index":154,
 "root_cause":"C311_SOURCE_FAMILY_STROKE_UNDERWEIGHT",
 "source_sha256":sha(s),"previous_candidate_sha256":sha(p),"trial_sha256":sha(raw),
 "source_bbox_ceiling":"PASS_3_OF_3","source_clean_8_cells_zero_alpha":True,
 "source_clean_outside_original_8":"ZERO_DELTA",
 "candidate_outside_3_zero":True,"protected_red5_exact":True,
 "decoded_persisted_dds":"BYTE_EXACT","header_raw_mip1":"EXACT",
 "native":"4096x1024 RGBA32 MIRROR_Y", "region_results":regionstats,
 "trial_dds":1,"production_dds":0,"visual":"PENDING_CONTROLLER_PIXELS_FIRST",
 "C2":"NOT_RUN","C3":"NOT_RUN","APPROVAL":False,
 "RUNTIME_VALIDATION":"UNTESTED","backend":"GITHUB_ACTIONS_FALLBACK_UNAVAILABLE_GPT_DNS",
 "excluded":["VR","FFB","DX11","DXVK"]}
(OUT/"B298_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B298","trial_sha":sha(raw),"changed_pixels":int(changed.sum()),"regions":regionstats},ensure_ascii=False))
