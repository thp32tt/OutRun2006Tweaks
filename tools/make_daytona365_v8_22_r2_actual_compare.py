#!/usr/bin/env python3
"""Contact sheet of actual original PMT / verified v8.21 / new v8.22."""
import json,hashlib,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageStat,ImageChops
W=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v822_ai2_20261108"))/"blender_v8"
original=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png")
before=Path("/home/chatgpt-runner/work_handoff/daytona365_v821_ai2_20261108/blender_v8/Daytona365_v8_21_r2_ACTUAL_CYCLES_PREVIEW.png")
after=W/"Daytona365_v8_22_r2_ACTUAL_CYCLES_PREVIEW.png"
paths=[original,before,after]
images=[Image.open(p).convert("RGB") for p in paths]
assert images[0].size==(960,640)
assert images[1].size==images[2].size==(480,320)
images[0]=images[0].resize((480,320),Image.Resampling.LANCZOS)
out=W/"Daytona365_ORIGINAL_vs_V8_21_R2_V8_22_R2_ACTUAL_CYCLES_COMPARE.png"
assert not out.exists()
canvas=Image.new("RGB",(1440,396),(20,24,29))
d=ImageDraw.Draw(canvas)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",14)
 small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:bold=small=ImageFont.load_default()
labs=[("Genuine original PMT -- actual Cycles","960x640 / 10 spp, downsampled"),
 ("v8.21-r2 verified shaft + gauge under-shroud","480x320 / 4 spp"),
 ("v8.22 physically folded gear-shifter boot","480x320 / 4 spp")]
for k,(im,(title,meta)) in enumerate(zip(images,labs)):
 x=480*k;canvas.paste(im,(x,76))
 d.text((x+8,11),title,font=bold,fill=(237,238,242))
 d.text((x+8,43),meta,font=small,fill=(183,191,202))
canvas.save(out,optimize=True)
delta=ImageStat.Stat(ImageChops.difference(images[1],images[2])).mean
r={"status":"DAYTONA_V8_22_REAL_PMT_CYCLES_COMPARE_PASS",
 "inputs":[p.name for p in paths],
 "input_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
 "comparison":out.name,"comparison_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "bytes":out.stat().st_size,"camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,"new_480x320_4spp":True,
 "v821_v822_mean_abs_RGB":[round(x,5) for x in delta],
 "delta_not_fidelity_score":True,"photometric_equivalence":"NOT_ESTABLISHED",
 "matched_full_resolution":"UNTESTED","original_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_22_R2_COMPARE_PROVENANCE.json").write_text(json.dumps(r,indent=2))
print("DAYTONA_V8_22_REAL_PMT_CYCLES_COMPARE_PASS",json.dumps(r),flush=True)