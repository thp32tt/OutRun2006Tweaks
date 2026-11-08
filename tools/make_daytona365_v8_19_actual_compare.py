#!/usr/bin/env python3
"""Genuine original PMT / actual v8.18 / actual v8.19 same-camera Cycles sheet."""
import json,hashlib,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
original=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png")
prior=Path("/home/chatgpt-runner/work_handoff/daytona365_v818_ai2_0926/blender_v8/Daytona365_v8_18_r2_ACTUAL_CYCLES_PREVIEW.png")
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v819_ai2_093x"))/"blender_v8"
new=W/"Daytona365_v8_19_r2_ACTUAL_CYCLES_PREVIEW.png"
ps=[original,prior,new]
im=[Image.open(p).convert("RGB") for p in ps]
assert im[0].size==(960,640)
assert im[1].size==im[2].size==(480,320)
im[0]=im[0].resize((480,320),Image.Resampling.LANCZOS)
out=W/"Daytona365_ORIGINAL_vs_V8_18_V8_19_R2_ACTUAL_CYCLES_COMPARE.png"
assert not out.exists()
canvas=Image.new("RGB",(1440,396),(20,24,29))
painter=ImageDraw.Draw(canvas)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",14)
 regular=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:bold=regular=ImageFont.load_default()
titles=[("Genuine original PMT -- actual Cycles","960x640 / 10 spp, downsampled"),
 ("v8.18 original switchbank surround","480x320 / 4 spp"),
 ("v8.19 formed dash-to-door endcaps","480x320 / 4 spp")]
for k,(image,labels) in enumerate(zip(im,titles)):
 x=480*k
 canvas.paste(image,(x,76))
 painter.text((x+8,11),labels[0],font=bold,fill=(237,238,242))
 painter.text((x+8,43),labels[1],font=regular,fill=(183,191,202))
canvas.save(out,optimize=True)
roi=(0,0,480,320)
stat=ImageStat.Stat(ImageChops.difference(im[1].crop(roi),im[2].crop(roi)))
data={"status":"DAYTONA_V8_19_REAL_PMT_CYCLES_COMPARE_PASS",
 "inputs":[p.name for p in ps],
 "input_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in ps],
 "comparison":out.name,"comparison_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "comparison_bytes":out.stat().st_size,
 "camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,"candidate_480x320_4spp":True,
 "candidate_RGB_delta_mean":[round(c,4) for c in stat.mean],
 "photometric_equivalence":"NOT_ESTABLISHED",
 "note":"Image deltas include sampling/denoiser variance. This is NOT a source-fidelity metric.",
 "full_resolution_matched":"UNTESTED","OVC_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_19_COMPARE_PROVENANCE.json").write_text(json.dumps(data,indent=2))
print("DAYTONA_V8_19_REAL_PMT_CYCLES_COMPARE_PASS",json.dumps(data))