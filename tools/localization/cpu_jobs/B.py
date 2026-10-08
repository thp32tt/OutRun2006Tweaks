#!/usr/bin/env python3
"""B290 q060 white-banner material-fix promotion with canonical CLEAN evidence.
ONLY the white OUTRUN MILES glyph material is touched; Stage/gold remain REWORK.
Run on hosted GitHub because native sandbox cannot download source binary.
"""
import hashlib, io, json, os, tempfile, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions" and os.environ.get("OUTRUN_CPU_ROLE")=="B"
G=Path("localization/graphics")
P=G/"hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
TRIAL=G/"role_B/20261009-B289-Q060-P0-WHITE-FACE-PIXEL-MATERIAL/A064FDFC_B289_TRIAL_NOT_PROMOTED.dds"
OLD="457f29f6e3a42b674411baae993c6660addca8e6aa4c0f3904af60ec4e0a20e2"
NEW="068b4f5795e85b960493efad832f9060984387c978c4936f9708133e6227fb85"
EN="6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc"
CLEAN_SHA="e4befa3f25ab2a90173224d7c4cd6ef2184b6c5a43ba4a307b321724870ed089"
CL=G/"role_B/20261004-B-RECOVERY09/A064FDFC_SELECTED_CLEAN_PLATE.png"
OUT=G/"role_B/20261009-B290-Q060-P0-WHITE-MATERIAL-PARTIAL-PROMOTION";OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
old=P.read_bytes();new=TRIAL.read_bytes();assert sha(old)==OLD and sha(new)==NEW
assert old[:128]==new[:128] and len(old)==len(new)
cleanbytes=CL.read_bytes();assert sha(cleanbytes)==CLEAN_SHA
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds"
with tempfile.TemporaryDirectory(prefix="b290_") as tmp:
 ep=Path(tmp)/"source.dds";urllib.request.urlretrieve(url,ep);sourcebytes=ep.read_bytes()
assert sha(sourcebytes)==EN and sourcebytes[:128]==old[:128]
def decode(b):return np.array(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM))
english=decode(sourcebytes);a=decode(old);b=decode(new);clean=np.array(Image.open(CL).convert("RGBA"))
assert english.shape==a.shape==b.shape==clean.shape==(2048,4096,4)
assert np.array_equal(a[:,:,3],b[:,:,3])
# Exact previously authored source text/candidate glyph bounds from C315/A167.
source_box=(1090,245,1930,385);loc_box=(1096,256,1816,374)
l,t,r,bt=loc_box;sl,st,sr,sb=source_box
changed=np.any(a!=b,axis=2)
allowed=np.zeros((2048,4096),bool);allowed[t:bt,l:r]=True
assert changed.any()
assert int(np.count_nonzero(changed&~allowed))==0
assert int(np.count_nonzero((a[:,:,3]!=b[:,:,3])))==0
# Independently check source-family English white text has been erased in the
# B_RECOVERY09 canonical plate on the isolated upper 70px unaffected by lower
# neighboring sprites. Preserve the native unrelated overlap below.
s=english[st:sb,sl:sr];c=clean[st:sb,sl:sr]
original_white=(s[:,:,:3].min(axis=2)>=190)&(s[:,:,3]>=80)
assert int(original_white.sum())>6000
upper=np.zeros(original_white.shape,bool);upper[:73,:]=True
upper_white=original_white&upper
residual_alpha=int(np.count_nonzero((c[:,:,3]>24)&upper_white))
residual_core=int(np.count_nonzero((c[:,:,:3].min(axis=2)>180)&(c[:,:,3]>90)&upper_white))
print("B290_PLATE_ALPHA_REMAINING_UPPER",residual_alpha,"of",int(upper_white.sum()))
# Permit any independently protected pixels to cause a HOLD instead of lying.
assert residual_alpha==0 and residual_core==0,("CLEAN_PLATE_SOURCE_RESIDUE_BLOCK",residual_alpha,residual_core)
# Check local unchanged nonlettered core and zero-added alpha/hard rectangle.
assert int(np.count_nonzero(changed[t:bt,l:r]))<int((r-l)*(bt-t)*0.75),"material correction exceeds isolated existing glyph region"
def composite(ar,bg=(80,80,80,255)):
 img=Image.new("RGBA",(ar.shape[1],ar.shape[0]),bg)
 img.alpha_composite(Image.fromarray(ar,"RGBA"))
 return img.convert("RGB")
L,T,R,B=(1075,236,1950,399)
views=[("EN",english),("CLEAN",clean),("CURRENT",a),("B290",b)]
for scale in (100,75,50):
 imgs=[]
 for name,ar in views:
  im=composite(ar[T:B,L:R])
  if scale!=100:im=im.resize((max(1,im.width*scale//100),max(1,im.height*scale//100)),Image.Resampling.LANCZOS)
  im.save(OUT/f"{name}_GRAY_{scale}pct.png")
  imgs.append(im)
 sheet=Image.new("RGB",(sum(x.width for x in imgs)+12,max(x.height for x in imgs)),(80,80,80))
 x=0
 for im in imgs:sheet.paste(im,(x,0));x+=im.width+4
 sheet.save(OUT/f"B290_SOURCE_CLEAN_CURRENT_FINAL_{scale}pct.png")
 # RAW orientation reviewed separately, mirror-Y persisted bytes.
raws=[composite(np.flipud(ar[T:B,L:R])) for _,ar in views]
rs=Image.new("RGB",(sum(x.width for x in raws)+12,max(x.height for x in raws)),(80,80,80))
x=0
for im in raws:rs.paste(im,(x,0));x+=im.width+4
rs.save(OUT/"B290_SOURCE_CLEAN_CURRENT_FINAL_RAW.png")
assert np.array_equal(decode(new),b)
# Promote ONLY after fixed-bbox/clean/source/alpha native checks; no claim
# that q060 total asset is C/USER approved (Stage and yellow remain defects).
P.write_bytes(new)
assert sha(P.read_bytes())==NEW
report={
 "schema_version":2,"role":"B","run":"B290","run_key":"OUTRUN-KOR-B290-Q060-IGR044-WHITE-MATERIAL-20261009",
 "index":60,"priority":"P0","regression":"IGR-044 OPEN_USER_INGAME_FAIL",
 "source_sha256":EN,"source_url":url,"canonical_white_clean_png_sha256":CLEAN_SHA,
 "old_candidate_sha256":OLD,"new_candidate_sha256":NEW,
 "candidate_path":str(P),"modified_region":"outrun_miles_white_ONLY",
 "other_failed_regions":["stage","outrun_miles_gold"],
 "changes_vs_previous":int(changed.sum()),"changes_outside_current_white_bbox":0,
 "alpha_changed_pixels_full_atlas":0,"dds_header_exact":True,"native":[4096,2048],
 "mips":1,"format":"RGBA32","RAW":"mirror_y","persisted_roundtrip":"PASS",
 "source_clean_white_upper_mask_pixels":int(upper_white.sum()),
 "clean_residual_source_alpha_upper":residual_alpha,
 "clean_residual_source_face_upper":residual_core,
 "plate_only":"PASS_WHITE_UPPER_REGION_ONLY; lower 67px preserve overlapping artwork; no full asset clean claim",
 "composite_only":"PASS_WHITE_MATERIAL_GLYPH_ONLY_OUTSIDE_ZERO",
 "producer_visual":"B289_SOURCE_CURRENT_TRIAL_100p_DIRECT_CONTROLLER_IMPROVED_WHITE_FACE_AND_RIGHT_LEAN; followup independent review pending",
 "producer_rework_status":"PARTIAL_PASS_WHITE_ONLY_STAGE_GOLD_REWORK_REQUIRED",
 "C":"PENDING_FRESH_C2","C3":"PENDING_AFTER_COMPLETE_ASSET",
 "USER_INGAME":"OPEN_USER_INGAME_FAIL","APPROVAL":False,"RUNTIME_VALIDATION":"UNTESTED",
 "new_material_production_dds":1,
 "execution_backend":"GITHUB_RUNNER_BCAUSE_LOCAL_SANDBOX_SOURCE_NETWORK_DNS_UNAVAILABLE",
 "excluded":["VR","FFB","DX11","DXVK"]
}
(OUT/"B290_PRODUCER_SELF_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"q":60,"candidate":NEW,"changed":int(changed.sum()),"plate_alpha":residual_alpha},ensure_ascii=False))
