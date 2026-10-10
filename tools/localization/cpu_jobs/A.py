#!/usr/bin/env python3
"""A220 q121: newly observed English 'the' residual; trial-only transparent cleanup.
Never promotes without whole-atlas source/protected mask and independent C1/C3.
"""
import hashlib, io, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
root=Path.cwd()
out=root/"localization/graphics/role_A/20261010-A220-Q121-THE-SOURCE-RESIDUE"
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
official=root/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
prior=root/"localization/graphics/role_A/20261010-A219-Q121-GOAL-SOURCE-RESIDUE-33/A219_Q121_SOURCE_GOAL_33_RESIDUE_REMOVAL_UNPROMOTED.dds"
proof=root/"localization/graphics/role_A/20261010-A215-Q121-P0-SOURCE-COMPONENT-LOSSLESS"
pold=official.read_bytes(); pfirst=prior.read_bytes()
official_sha="38d5c2c30ea813202051b191dc01de9d7804e52c1cbab0f46c5372b59ed6c844"
first_sha="9f5039dae7ee94cc33c118d5bd9e47c5720f165aa3c3c61a7c8dad992d0f62fb"
assert sha(pold)==official_sha and sha(pfirst)==first_sha,"Concurrent or unexpected DDS input"
assert pold[:128]==pfirst[:128] and len(pold)==len(pfirst)==128+4096*4096*4
W,H=struct.unpack_from("<II",pold,16)[0],struct.unpack_from("<I",pold,12)[0]
assert (W,H)==(4096,4096)
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","121"],check=True,text=True,capture_output=True).stdout
source_url=("https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/"
"Release/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds")
with urllib.request.urlopen(source_url,timeout=150) as r: source_bytes=r.read()
source_sha="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
assert sha(source_bytes)==source_sha,"Canonical original drift"
source=Image.open(io.BytesIO(source_bytes)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
official_img=Image.open(io.BytesIO(pold)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
first_img=Image.open(io.BytesIO(pfirst)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions=json.loads((proof/"A215_COMPONENT_QA.json").read_text(encoding="utf-8"))["regions"]
r24=next(x for x in regions if x["rank"]==24)
rect=tuple(r24["expanded_crop_readable"]); inner=tuple(r24["bbox_readable"])
assert rect==(3056,651,3205,743) and inner[0]>=rect[0] and inner[2]<=rect[2]
def png(which):
    return Image.open(proof/f"A215_component_24_{which}_NATIVE_RGBA.png").convert("RGBA")
src,clean,saved=[png(x) for x in ("SOURCE","CLEAN","FINAL")]
assert src.size==(rect[2]-rect[0],rect[3]-rect[1])
assert src.tobytes()==source.crop(rect).tobytes(),"A215 source proof is not canonical source"
assert saved.tobytes()==official_img.crop(rect).tobytes(),"A215 saved proof not official"
assert clean.tobytes()==saved.tobytes(),"Unexpected plate/candidate divergence in old rank24"
assert first_img.crop(rect).tobytes()==saved.tobytes(),"A219 changed unrelated rank24"
S,C=[np.asarray(x,dtype=np.uint8) for x in (src,clean)]
ys,xs=np.indices(C.shape[:2])
absolute_x=xs+rect[0]; absolute_y=ys+rect[1]
inside=(absolute_x>=inner[0])&(absolute_x<inner[2])&(absolute_y>=inner[1])&(absolute_y<inner[3])
same_rgba=np.all(C==S,axis=2)
orphan=(C[:,:,3]>0)&same_rgba&inside
oy,ox=np.nonzero(orphan); n=len(ox)
# If the exact source-matching remnants are absent, do not create a fake new trial.
assert 0<n<1000,("No bounded exact-source orphan pixels",n)
if np.count_nonzero((C[:,:,3]>0)&inside&(~same_rgba)):
    # Keep protected/ambiguous pixels, without falsely claiming full plate clean.
    ambiguous=int(np.count_nonzero((C[:,:,3]>0)&inside&(~same_rgba)))
else: ambiguous=0
trial=bytearray(pfirst)
spots=[]
for x0,y0 in zip(ox.tolist(),oy.tolist()):
    x,y=rect[0]+x0,rect[1]+y0
    ry=H-1-y; off=128+(ry*W+x)*4
    assert trial[off:off+4]!=bytes(4)
    trial[off:off+4]=bytes(4)
    spots.append([x,y,ry,off])
trial=bytes(trial)
saved_path=out/"A220_Q121_THE_RESIDUE_PLUS_GOAL33_UNPROMOTED.dds"
saved_path.write_bytes(trial)
assert trial[:128]==pold[:128] and sha(trial)!=first_sha
reopened=Image.open(saved_path).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
R=np.asarray(reopened.crop(rect))
assert np.all(R[oy,ox]==0)
diff2=np.flatnonzero(np.frombuffer(pfirst,dtype=np.uint8)!=np.frombuffer(trial,dtype=np.uint8))
allowed={int(off)+k for *_,off in spots for k in range(4)}
assert len(set(map(int,diff2))-allowed)==0
assert int(np.count_nonzero(np.any(R!=C,axis=2)))==n
assert len(diff2)<=4*n
first_diff=np.flatnonzero(np.frombuffer(pold,dtype=np.uint8)!=np.frombuffer(pfirst,dtype=np.uint8))
assert len(first_diff)==132 and set(map(int,first_diff)).isdisjoint(allowed)
mask=np.zeros(C.shape[:2],dtype=np.uint8);mask[oy,ox]=255
Image.fromarray(mask,"L").resize((mask.shape[1]*4,mask.shape[0]*4),Image.Resampling.NEAREST).save(out/"A220_THE_SOURCE_PIXEL_REMNANTS_MASK_4X.png")
def bg(im,color=(105,105,105,255)):
    return Image.alpha_composite(Image.new("RGBA",im.size,color),im.convert("RGBA")).convert("RGB")
ims=[src,clean,saved,reopened.crop(rect)]
contact=Image.new("RGB",(src.width*4,src.height+33),(105,105,105))
draw=ImageDraw.Draw(contact)
for i,(lab,im) in enumerate(zip(("CANONICAL SOURCE EN","PLATE OLD","OFFICIAL OLD","A220 TRIAL"),ims)):
    contact.paste(bg(im),(i*src.width,33));draw.text((i*src.width+4,8),lab,fill=(255,255,255))
contact.save(out/"A220_SOURCE_CLEAN_OFFICIAL_TRIAL_GRAY100.png")
contact.resize((contact.width*2,contact.height*2),Image.Resampling.NEAREST).save(out/"A220_SOURCE_CLEAN_OFFICIAL_TRIAL_GRAY200.png")
for name,col in (("BLACK",(0,0,0,255)),("WHITE",(255,255,255,255)),("GRAY",(105,105,105,255))):
    for fraction in (1.,.75,.5):
        img=bg(reopened.crop(rect),col)
        if fraction!=1:img=img.resize((round(img.width*fraction),round(img.height*fraction)),Image.Resampling.LANCZOS)
        img.save(out/f"A220_TRIAL_{name}_{round(fraction*100)}.png")
raw=Image.open(saved_path).convert("RGBA")
raw.crop((rect[0],H-rect[3],rect[2],H-rect[1])).save(out/"A220_TRIAL_RAW_NATIVE.png")
report={"schema_version":2,"run":"A220","run_key":"OUTRUN-KOR-A220-Q121-THE-SOURCE-ORPHAN-20261010-1000","role":"A",
"queue_index":121,"priority":"P0","user_reports":["IGR-030","IGR-031","IGR-040"],
"triage":triage[:2000],"canonical_source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
"source_sha256":source_sha,"official_sha256":official_sha,"A219_existing_trial_sha256":first_sha,
"new_distinct_trial_sha256":sha(trial),"native":[W,H],"DDS":"RGBA32 1 mip",
"source_rank":24,"source_english":"the","source_readable_crop":list(rect),"A215_rank24_source_exact":True,
"source_plate_final_old_exact":True,"new_source_identical_orphan_pixels_removed":n,
"ambiguous_alpha_pixels_in_inner_bbox_untouched":ambiguous,
"changed_pixels_vs_prior_trial":n,"changed_bytes_vs_prior_trial":int(len(diff2)),
"outside_selected_exact_source_pixels_changed":0,"A219_prior33_preserved":True,
"other_atlas_pixels_byte_identical_to_A219":True,
"new_candidate_published":False,"trial_only":True,
"self_machine":"SCOPED_SOURCE_RESIDUE_REMOVAL_PASS","visual":"CONTROLLER_FIRSTLOOK_REQUIRED",
"full_atlas":"HOLD_NEEDS_29_TEXT_SEGMENTS_PROTECTED_ART_MASK_FONT_CALIBRATION",
"c1":"PENDING_NEW_TRIAL","c3":"NOT_RUN","user_ingame":"OPEN_USER_INGAME_FAIL","RUNTIME_VALIDATION":"UNTESTED",
"backend":"GitHub Actions CPU worker, local container DNS unavailable; N100 not used"}
(out/"A220_MACHINE_TRIAL_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":"A220","new_orphan_pixels_removed":n,"new_trial_sha256":sha(trial),"ambiguous_preserved":ambiguous,"official_changed":False}))
