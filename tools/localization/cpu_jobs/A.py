#!/usr/bin/env python3
"""A219: exact-source verified removal of 33 orphan English 'goal.' pixels.
The output is a NON-PROMOTED DDS trial; independent C1, C3, and game remain HOLD.
No hd_candidates/queue/shared-state writes from this CPU worker.
"""
import hashlib, io, json, os, struct, urllib.request, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("Role-A GitHub CPU worker only")
repo=Path.cwd()
run="20261010-A219-Q121-GOAL-SOURCE-RESIDUE-33"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
path="textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
official=repo/"localization/graphics/hd_candidates"/path
inputs=repo/"localization/graphics/role_A/20261010-A215-Q121-P0-SOURCE-COMPONENT-LOSSLESS"
sha=lambda v:hashlib.sha256(v).hexdigest()
prev=official.read_bytes()
expected_current="38d5c2c30ea813202051b191dc01de9d7804e52c1cbab0f46c5372b59ed6c844"
assert sha(prev)==expected_current,("concurrent q121 candidate change: fail closed",sha(prev))
W,H=struct.unpack_from("<II",prev,16)[0],struct.unpack_from("<I",prev,12)[0]
assert (W,H)==(4096,4096)
assert prev[:4]==b"DDS " and len(prev)==128+W*H*4
assert struct.unpack_from("<I",prev,88)[0]==32, "unexpected uncompressed DDS bitcount"
# Required owner-lane rework triage, not a substitute for C visual review.
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","121"],
                     capture_output=True,text=True,check=True).stdout
url=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
     "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/"
     "Release/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds")
with urllib.request.urlopen(url,timeout=120) as response: en=response.read()
en_hash="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
assert sha(en)==en_hash,("source SHA drift",sha(en))
source=Image.open(io.BytesIO(en)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
base=Image.open(io.BytesIO(prev)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
# Source, pre-lettering CLEAN and saved candidate are the exact 2026-10-10 A215 native proofs.
rect=(3184,651,3391,756)
def stored(k):
    p=inputs/f"A215_component_19_{k}_NATIVE_RGBA.png"
    return Image.open(p).convert("RGBA")
proof_s,proof_c,proof_f=[stored(k) for k in ("SOURCE","CLEAN","FINAL")]
assert proof_s.size==(207,105) and proof_c.size==proof_s.size
assert source.crop(rect).tobytes()==proof_s.tobytes(),"source crop provenance drift"
assert base.crop(rect).tobytes()==proof_f.tobytes(),"current DDS crop provenance drift"
ss,cc,ff=[np.asarray(a,dtype=np.uint8) for a in (proof_s,proof_c,proof_f)]
# Every stale pixel is fully opaque, pure WHITE, source-identical, and still in FINAL.
ys,xs=np.nonzero(cc[:,:,3]>0)
assert len(xs)==33,("unexpected cleanup scope",len(xs))
assert np.all(cc[ys,xs]==np.array([255,255,255,255],np.uint8))
assert np.array_equal(cc[ys,xs],ss[ys,xs]) and np.array_equal(cc[ys,xs],ff[ys,xs])
# Preserve every other pixel in the DDS byte-for-byte; patch exact native RAW mirrored Y.
trial=bytearray(prev)
spots=[]
for xx,yy in zip(xs.tolist(),ys.tolist()):
    x,y=rect[0]+xx,rect[1]+yy
    ry=H-1-y
    offset=128+(ry*W+x)*4
    assert prev[offset:offset+4]!=b"\\0"*4
    trial[offset:offset+4]=b"\\0"*4
    spots.append({"readable_xy":[x,y],"native_raw_xy":[x,ry],"byte_offset":offset,
                  "prior_readable_rgba":[255,255,255,255],"new_readable_rgba":[0,0,0,0]})
trial=bytes(trial)
assert sha(trial)!=expected_current and trial[:128]==prev[:128]
path_trial=out/"A219_Q121_SOURCE_GOAL_33_RESIDUE_REMOVAL_UNPROMOTED.dds"
path_trial.write_bytes(trial)
check=Image.open(path_trial).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
post=np.asarray(check.crop(rect),dtype=np.uint8)
want=np.array(ff,copy=True)
want[ys,xs]=0
assert np.array_equal(post,want),"persisted decoded target mismatch"
# Confirm exact changed count/full-byte blast radius even when texture has other labels.
diff=np.flatnonzero(np.frombuffer(prev,dtype=np.uint8)!=np.frombuffer(trial,dtype=np.uint8))
allowed={s["byte_offset"]+k for s in spots for k in range(4)}
assert len(set(diff)-allowed)==0 and len(diff)<=132
assert len(diff)>=33
assert np.count_nonzero(np.any(post!=ff,axis=2))==33
def gray(img):
    v=Image.new("RGBA",img.size,(105,105,105,255))
    return Image.alpha_composite(v,img.convert("RGBA")).convert("RGB")
p=[gray(x) for x in [proof_s,proof_c,proof_f,check.crop(rect)]]
canvas=Image.new("RGB",(207*4,105+36),(105,105,105))
d=ImageDraw.Draw(canvas)
for n,(label,im) in enumerate(zip(("SOURCE EN","CLEAN before","OFFICIAL before","A219 TRIAL after"),p)):
    canvas.paste(im,(n*207,36))
    d.text((n*207+8,8),label,fill="white")
canvas.save(out/"A219_SOURCE_CLEAN_OFFICIAL_TRIAL_NATIVE_RGB.png")
canvas.resize((canvas.width*2,canvas.height*2),Image.Resampling.NEAREST).save(out/"A219_SOURCE_CLEAN_OFFICIAL_TRIAL_2X.png")
mask=np.zeros((105,207),dtype=np.uint8);mask[ys,xs]=255
Image.fromarray(mask,"L").save(out/"A219_ORIGINAL_GLYPH_RESIDUE_33_MASK.png")
# RAW and practical 75/50: encoded DDS saved then re-decoded above. No authored MIPs.
raw=Image.open(path_trial).convert("RGBA")
bx0,by0,bx1,by1=rect
raw_crop=raw.crop((bx0,H-by1,bx1,H-by0))
raw_crop.save(out/"A219_PERSISTED_DDS_RAW_GOAL_CROP.png")
for factor in (0.75,0.5):
    w,h=int(round(207*factor)),int(round(105*factor))
    gray(check.crop(rect)).resize((w,h),Image.Resampling.LANCZOS).save(out/f"A219_PERSISTED_DDS_{int(factor*100)}PCT_GRAY.png")
report={
 "run":"A219","run_key":"OUTRUN-KOR-A219-Q121-GOAL-33-SOURCE-RESIDUE-20261010",
 "role":"A","queue_index":121,"priority":"P0","user_reports":["IGR-030","IGR-031","IGR-040"],
 "status":"ISOLATED_TRIAL_PRODUCER_SCOPED_ONLY_FULL_ATLAS_C1_HOLD",
 "source_url":url,"canonical_english_source_sha256":en_hash,
 "official_before_candidate_sha256":expected_current,
 "unpromoted_trial_candidate_sha256":sha(trial),
 "official_hd_candidate_changed":False,
 "native_dimensions":[W,H],"dds_format":"RGBA32 uncompressed mip1 exact header reused",
 "readable_crop":list(rect),"source_clean_crop_exact_verified":True,
 "saved_candidate_crop_exact_verified":True,"residue_mechanism":"33 fully opaque SOURCE-identical white glyph specks incorrectly retained on CLEAN+FINAL from 'goal.'",
 "source_residue_pixels_removed":33,"changed_pixel_count":33,"changed_byte_count":int(len(diff)),
 "outside_33_pixels_changed":0,"previous_dds_byte_identical_outside_33_pixels":True,
 "persisted_DDS_decoded_matches_intended_pixel_edit":True,
 "native_raw_y_transform":"readable y -> 4095-y",
 "machine_decision":"SCOPED_REMOVE_SOURCE_REMAINDER_VERIFIED_NO_FULL_ATLAS_APPROVAL",
 "triage_before":triage[:2500],
 "new_pixel_writes":[s for s in spots],
 "visual_review":"PENDING_CONTROLLER_100_75_50_RAW_AND_BGW",
 "plate_gate":"SCOPED_ORIGINAL_REMNANT_CORRECTION_NOT_FULL_ATLAS_PLATE_PASS",
 "composite_gate":"NOT_APPLICABLE_NO_NEW_LETTERING",
 "final_manifest":"NOT_PUBLISHED_OFFICIAL_CANDIDATE_UNCHANGED_NO_HD_CANDIDATES_WRITE",
 "candidate_approval":"BLOCKED_NEEDS_FULL_29_SEGMENT_SOURCE_ART_MASK_AND_C1_C3",
 "user_ingame_regressions":"OPEN_USER_INGAME_FAIL",
 "RUNTIME_VALIDATION":"UNTESTED",
 "backend":"GitHub Actions CPU worker; no N100 heavy",
 "exclusions":["VR","FFB","DX11","DXVK"]}
(out/"A219_Q121_MACHINE_TRIAL_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ("run","unpromoted_trial_candidate_sha256","source_residue_pixels_removed","outside_33_pixels_changed")},ensure_ascii=False))
