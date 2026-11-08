#!/usr/bin/env python3
"""Compare actual original PMT, real v8.19-r2 and v8.20 same-camera Cycles.
Original and candidates are NOT sample- or photometrically matched.
"""
from pathlib import Path
import os,json,hashlib
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v820_ai2_102x"))/"blender_v8"
orig=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png")
previous=Path("/home/chatgpt-runner/work_handoff/daytona365_v819_ai2_093x/blender_v8/Daytona365_v8_19_r2_ACTUAL_CYCLES_PREVIEW.png")
new=W/"Daytona365_v8_20_ACTUAL_CYCLES_PREVIEW.png"
paths=[orig,previous,new]
images=[Image.open(p).convert("RGB") for p in paths]
assert images[0].size==(960,640)
assert images[1].size==images[2].size==(480,320)
images[0]=images[0].resize((480,320),Image.Resampling.LANCZOS)
out=W/"Daytona365_ORIGINAL_vs_V8_19_R2_V8_20_ACTUAL_CYCLES_COMPARE.png"
assert not out.exists()
canvas=Image.new("RGB",(1440,396),(20,24,29))
draw=ImageDraw.Draw(canvas)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",14)
 regular=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:bold=regular=ImageFont.load_default()
labels=[
 ("Genuine original PMT -- actual Cycles","960x640 / 10 spp, downsampled"),
 ("v8.19-r2 physical dash-to-door endcaps","480x320 / 4 spp"),
 ("v8.20 physical formed footwell mats","480x320 / 4 spp")]
for i,(im,(title,sub)) in enumerate(zip(images,labels)):
 x=i*480
 canvas.paste(im,(x,76))
 draw.text((x+8,11),title,fill=(236,237,242),font=bold)
 draw.text((x+8,43),sub,fill=(185,193,202),font=regular)
canvas.save(out,optimize=True)
diff=ImageStat.Stat(ImageChops.difference(images[1],images[2]))
result={"status":"DAYTONA_V8_20_REAL_PMT_CYCLES_COMPARE_PASS",
 "inputs":[p.name for p in paths],
 "input_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
 "comparison":out.name,"comparison_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "comparison_bytes":out.stat().st_size,
 "camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,
 "candidate_480x320_4spp":True,
 "candidate_RGB_mean_absolute_delta":[round(x,4) for x in diff.mean],
 "delta_is_not_source_fidelity_score":True,
 "photometric_equivalence":"NOT_ESTABLISHED",
 "full_resolution_matched":"UNTESTED","OVC_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_20_COMPARE_PROVENANCE.json").write_text(json.dumps(result,indent=2))
print("DAYTONA_V8_20_REAL_PMT_CYCLES_COMPARE_PASS",json.dumps(result),flush=True)