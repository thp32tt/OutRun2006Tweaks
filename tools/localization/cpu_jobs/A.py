#!/usr/bin/env python3
"""A221: targeted source-matching CLEAN residue inspection and trial only, q121 P0.
Do not promote or claim whole-atlas pass. Keep old A219/A220 edits exact.
"""
from pathlib import Path
import hashlib, io, json, os, struct, subprocess, urllib.request
import numpy as np
from PIL import Image, ImageDraw
assert os.environ.get("OUTRUN_CPU_WORKER")=="github-actions"
assert os.environ.get("OUTRUN_CPU_ROLE")=="A"
root=Path.cwd(); name="20261010-A221-Q121-ADDITIONAL-SOURCE-REMAINDER"
out=root/"localization/graphics/role_A"/name;out.mkdir(parents=True,exist_ok=True)
sha=lambda x:hashlib.sha256(x).hexdigest()
official=root/"localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
old=root/"localization/graphics/role_A/20261010-A220-Q121-THE-SOURCE-RESIDUE/A220_Q121_THE_RESIDUE_PLUS_GOAL33_UNPROMOTED.dds"
proof=root/"localization/graphics/role_A/20261010-A215-Q121-P0-SOURCE-COMPONENT-LOSSLESS"
official_sha="38d5c2c30ea813202051b191dc01de9d7804e52c1cbab0f46c5372b59ed6c844"
old_sha="6db7c40864f44dcb1a07568ae1717b7ecf4720b253f963fe5fbb38e90b1ede06"
o=official.read_bytes(); previous=old.read_bytes()
assert sha(o)==official_sha and sha(previous)==old_sha
assert o[:128]==previous[:128] and len(o)==len(previous)==128+4096*4096*4
triage=subprocess.run(["python","tools/localization/rework_triage.py","--index","121"],capture_output=True,text=True,check=True).stdout
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
with urllib.request.urlopen(url,timeout=150) as response:en=response.read()
source_sha="f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e"
assert sha(en)==source_sha
source=Image.open(io.BytesIO(en)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
before=Image.open(io.BytesIO(o)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
start=Image.open(io.BytesIO(previous)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
rows=json.loads((proof/"A215_COMPONENT_QA.json").read_text(encoding="utf-8"))["regions"]
# Direct first-look source-contact list. 19/24 already repaired, do not repeat.
# 26 English 'Do' has a dark-blue retained fragment at the native bottom.
# 21 English 'race?' has an isolated right-edge question-mark remnant.
targets=[(26,"Do"),(21,"race?")]
samples=[]
for rank,text_en in targets:
    row=next(r for r in rows if r["rank"]==rank)
    rect=tuple(row["expanded_crop_readable"]);inner=tuple(row["bbox_readable"])
    def pp(tag):return Image.open(proof/f"A215_component_{rank:02d}_{tag}_NATIVE_RGBA.png").convert("RGBA")
    S,C,F=[pp(tag) for tag in ("SOURCE","CLEAN","FINAL")]
    assert S.size==(rect[2]-rect[0],rect[3]-rect[1])
    assert S.tobytes()==source.crop(rect).tobytes()
    assert F.tobytes()==before.crop(rect).tobytes() and C.tobytes()==F.tobytes()
    assert start.crop(rect).tobytes()==F.tobytes(),"A220 changed this region; no blind overwrite"
    so,cl=np.asarray(S),np.asarray(C)
    y,x=np.indices(cl.shape[:2]); xx=x+rect[0];yy=y+rect[1]
    inside=(xx>=inner[0])&(xx<inner[2])&(yy>=inner[1])&(yy<inner[3])
    exact=(cl[:,:,3]>0)&inside&np.all(cl==so,axis=2)
    cy,cx=np.nonzero(exact)
    # Report all exact source fragments; do not redefine a mask to create PASS.
    samples.append(dict(rank=rank,english=text_en,rect=rect,inner=inner,S=S,C=C,F=F,
                        x=cx,y=cy,count=int(len(cx)),
                        other_alpha=int(np.count_nonzero((cl[:,:,3]>0)&inside&(~np.all(cl==so,axis=2))))))
assert any(x["count"] for x in samples),"No new source-exact residual found; fail closed."
# Fail-closed if the source-matching candidate count is implausibly high.
qualified=[x for x in samples if 0<x["count"]<=400]
assert qualified,"Exact source remnants exceed narrow triage boundary"
# Only one asset region is edited this run; prefer first observed English 'Do'.
target=qualified[0]; rank=target["rank"]; xx=target["x"];yy=target["y"]; rect=target["rect"]
patched=bytearray(previous);spots=[]
for lx,ly in zip(xx.tolist(),yy.tolist()):
    x,y=rect[0]+lx,rect[1]+ly
    off=128+((4095-y)*4096+x)*4
    assert patched[off:off+4]!=bytes(4)
    patched[off:off+4]=bytes(4)
    spots.append((x,y,off))
patched=bytes(patched)
assert sha(patched)!=old_sha and patched[:128]==o[:128]
diff=np.flatnonzero(np.frombuffer(previous,dtype=np.uint8)!=np.frombuffer(patched,dtype=np.uint8))
allowed={off+k for _,_,off in spots for k in range(4)}
assert set(map(int,diff))<=allowed and 0<len(diff)<=4*len(spots)
assert set(int(i) for i in np.flatnonzero(np.frombuffer(o,dtype=np.uint8)!=np.frombuffer(previous,dtype=np.uint8))).isdisjoint(allowed)
dds=out/"A221_Q121_SOURCE_TEXT_REMNANT_UNPROMOTED.dds";dds.write_bytes(patched)
decoded=Image.open(dds).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
new=np.asarray(decoded.crop(rect),dtype=np.uint8)
oldregion=np.asarray(target["F"],dtype=np.uint8)
assert np.all(new[yy,xx]==0)
assert int(np.count_nonzero(np.any(new!=oldregion,axis=2)))==len(xx)
def bg(im,rgba=(100,100,100,255)):
    return Image.alpha_composite(Image.new("RGBA",im.size,rgba),im.convert("RGBA")).convert("RGB")
contact=Image.new("RGB",(target["S"].width*4,target["S"].height+32),(100,100,100))
drawer=ImageDraw.Draw(contact)
for k,(label,img) in enumerate(zip(["EN SOURCE","OLD CLEAN","OFFICIAL","TRIAL"],[target["S"],target["C"],target["F"],decoded.crop(rect)])):
    contact.paste(bg(img),(k*target["S"].width,32))
    drawer.text((k*target["S"].width+4,7),label,fill=(255,255,255))
contact.save(out/"A221_SOURCE_CLEAN_OFFICIAL_TRIAL_GRAY100.png")
mask=np.zeros(oldregion.shape[:2],dtype=np.uint8);mask[yy,xx]=255
Image.fromarray(mask,"L").resize((mask.shape[1]*4,mask.shape[0]*4),Image.Resampling.NEAREST).save(out/"A221_EXACT_SOURCE_MASK_4X.png")
for title,rgb in [("BLACK",(0,0,0,255)),("GRAY",(100,100,100,255)),("WHITE",(255,255,255,255))]:
    for pct in (100,75,50):
        im=bg(decoded.crop(rect),rgb)
        if pct!=100:im=im.resize((round(im.width*pct/100),round(im.height*pct/100)),Image.Resampling.LANCZOS)
        im.save(out/f"A221_TRIAL_{title}_{pct}.png")
Image.open(dds).convert("RGBA").crop((rect[0],4096-rect[3],rect[2],4096-rect[1])).save(out/"A221_TRIAL_RAW_NATIVE.png")
# Show the other suspected fragment separately: it is not silently patched.
for item in samples:
    if item["rank"]==rank:continue
    im=bg(item["C"])
    im.save(out/f"A221_UNMODIFIED_RANK{item['rank']:02d}_CLEAN_GRAY.png")
report={
"run":"A221","run_key":"OUTRUN-KOR-A221-Q121-FRESH-ENGLISH-REMAINDER-20261010-1100",
"role":"A","queue_index":121,"priority":"P0","source_revision":"Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
"source_sha256":source_sha,"official_sha256":official_sha,"previous_A220_trial_sha256":old_sha,
"new_unpromoted_trial_sha256":sha(patched),"target_rank":rank,"english_source_label":target["english"],
"source_english_bbox_readable":list(target["inner"]),"expanded_rect_readable":list(rect),
"source_exact_pixel_count_removed":len(spots),"changed_bytes_vs_A220":len(diff),"other_atlas_pixels_changed":0,
"A219_goal33_and_A220_the24_preserved":True,"native_dds":[4096,4096,"RGBA32","mip1"],
"candidates_scanned":[{"rank":x["rank"],"label":x["english"],"exact_source_pixels":x["count"],"other_alpha_ambiguous":x["other_alpha"]} for x in samples],
"machine":"SCOPED_SOURCE_EXACT_REMOVAL_PASS",
"visual_status":"PENDING_CONTROLLER_BG_NATIVE_SCALE_REVIEW",
"whole_atlas":"HOLD_SEMANTIC_29_CELLS_PROTECTED_MASK_AND_NEW_C1",
"new_trial_dds":1,"promoted_dds":0,
"C1":"PENDING","C3":"NOT_RUN","user_IGR":["IGR-030","IGR-031","IGR-040"],"RUNTIME_VALIDATION":"UNTESTED",
"backend":"GitHub Actions CPU worker, local GitHub raw network inaccessible; N100 unused"}
(out/"A221_MACHINE_TRIAL_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"trial_sha":sha(patched),"rank":rank,"new_source_pixels_removed":len(spots),"changed_bytes":len(diff),"other_region":report["candidates_scanned"]},ensure_ascii=False))
