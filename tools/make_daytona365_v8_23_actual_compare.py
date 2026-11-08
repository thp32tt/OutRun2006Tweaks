#!/usr/bin/env python3
"""Genuine original PMT vs final v8.22-r2 and new v8.23 same-camera Cycles."""
import json,hashlib,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v823_ai2_20261108"))/"blender_v8"
original=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png")
prior=Path("/home/chatgpt-runner/work_handoff/daytona365_v822_ai2_20261108/blender_v8/Daytona365_v8_22_r2_ACTUAL_CYCLES_PREVIEW.png")
new=W/"Daytona365_v8_23_ACTUAL_CYCLES_PREVIEW.png"
files=[original,prior,new]
images=[Image.open(p).convert("RGB") for p in files]
assert images[0].size==(960,640)
assert images[1].size==images[2].size==(480,320)
images[0]=images[0].resize((480,320),Image.Resampling.LANCZOS)
out=W/"Daytona365_ORIGINAL_vs_V8_22_R2_V8_23_ACTUAL_CYCLES_COMPARE.png"
assert not out.exists(),out
canvas=Image.new("RGB",(1440,396),(20,24,29))
drawer=ImageDraw.Draw(canvas)
try:
 title=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",14)
 tiny=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:title=tiny=ImageFont.load_default()
labels=[
 ("Genuine original PMT -- actual Cycles","960x640 / 10 spp, downsampled"),
 ("v8.22-r2 source-shifter boot","480x320 / 4 spp"),
 ("v8.23 formed 3-spoke bridge geometry","480x320 / 4 spp")]
for i,(im,(txt,meta)) in enumerate(zip(images,labels)):
 x=i*480;canvas.paste(im,(x,76))
 drawer.text((x+8,11),txt,font=title,fill=(237,238,242))
 drawer.text((x+8,43),meta,font=tiny,fill=(183,191,202))
canvas.save(out,optimize=True)
delta=ImageStat.Stat(ImageChops.difference(images[1],images[2])).mean
r={"status":"DAYTONA_V8_23_REAL_PMT_CYCLES_COMPARE_PASS",
 "inputs":[f.name for f in files],
 "input_sha256":[hashlib.sha256(f.read_bytes()).hexdigest() for f in files],
 "comparison":out.name,"comparison_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "bytes":out.stat().st_size,"camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,
 "candidate_480x320_4spp":True,
 "previous_current_abs_RGB":[round(x,5) for x in delta],
 "difference_is_not_fidelity_score":True,
 "photometric_equivalence":"NOT_ESTABLISHED",
 "full_resolution_matched":"UNTESTED","original_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_23_COMPARE_PROVENANCE.json").write_text(json.dumps(r,indent=2))
print("DAYTONA_V8_23_REAL_PMT_CYCLES_COMPARE_PASS",json.dumps(r),flush=True)