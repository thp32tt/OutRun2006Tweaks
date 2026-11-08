#!/usr/bin/env python3
"""Genuine PMT, actual v8.20 and actual v8.21 same-camera Cycles contact."""
import json,hashlib,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v821_ai2_20261108"))/"blender_v8"
original=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png")
prior=Path("/home/chatgpt-runner/work_handoff/daytona365_v820_ai2_102x/blender_v8/Daytona365_v8_20_ACTUAL_CYCLES_PREVIEW.png")
candidate=W/"Daytona365_v8_21_r2_ACTUAL_CYCLES_PREVIEW.png"
inputs=[original,prior,candidate]
images=[Image.open(p).convert("RGB") for p in inputs]
assert images[0].size==(960,640)
assert images[1].size==images[2].size==(480,320)
images[0]=images[0].resize((480,320),Image.Resampling.LANCZOS)
out=W/"Daytona365_ORIGINAL_vs_V8_20_V8_21_R2_ACTUAL_CYCLES_COMPARE.png"
assert not out.exists(),out
canvas=Image.new("RGB",(1440,396),(20,24,29))
d=ImageDraw.Draw(canvas)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",14)
 regular=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:bold=regular=ImageFont.load_default()
labels=[
 ("Genuine original PMT -- actual Cycles","960x640 / 10 spp, downsampled"),
 ("v8.20 original-bounded footwell mats","480x320 / 4 spp"),
 ("v8.21-r2 restrained dark hub / shroud","480x320 / 4 spp")]
for k,(image,meta) in enumerate(zip(images,labels)):
 x=480*k
 canvas.paste(image,(x,76))
 d.text((x+8,11),meta[0],font=bold,fill=(237,238,242))
 d.text((x+8,43),meta[1],font=regular,fill=(183,191,202))
canvas.save(out,optimize=True)
stats=ImageStat.Stat(ImageChops.difference(images[1],images[2]))
prov={"status":"DAYTONA_V8_21_R2_REAL_PMT_CYCLES_COMPARE_PASS",
 "inputs":[p.name for p in inputs],
 "input_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs],
 "comparison":out.name,
 "comparison_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "bytes":out.stat().st_size,
 "camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,
 "candidate_480x320_4spp":True,
 "candidate_RGB_abs_delta":[round(x,5) for x in stats.mean],
 "raw_diff_not_fidelity":True,
 "photometric_equivalence":"NOT_ESTABLISHED",
 "full_resolution_matched":"UNTESTED","original_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_21_R2_COMPARE_PROVENANCE.json").write_text(json.dumps(prov,indent=2))
print("DAYTONA_V8_21_REAL_PMT_CYCLES_COMPARE_PASS",json.dumps(prov))