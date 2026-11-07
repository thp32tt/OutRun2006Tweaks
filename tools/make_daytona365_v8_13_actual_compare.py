#!/usr/bin/env python3
"""Genuine original PMT vs immutable real v8.9/v8.12/v8.13 Cycles evidence."""
import hashlib,json,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
root=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
files=[root/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 w/"Daytona365_v8_9_ACTUAL_CYCLES_PREVIEW.png",
 w/"Daytona365_v8_12_ACTUAL_CYCLES_PREVIEW.png",
 w/"Daytona365_v8_13_ACTUAL_CYCLES_PREVIEW.png"]
dest=w/"Daytona365_ORIGINAL_vs_V8_9_V8_12_V8_13_ACTUAL_CYCLES_COMPARE.png"
assert not dest.exists(),"Do not overwrite old comparison evidence"
assert all(f.is_file() for f in files)
pics=[Image.open(f).convert("RGB") for f in files]
assert pics[0].size==(960,640)
assert all(p.size==(480,320) for p in pics[1:])
pics[0]=pics[0].resize((480,320),Image.Resampling.LANCZOS)
canvas=Image.new("RGB",(1920,390),(22,25,29))
draw=ImageDraw.Draw(canvas)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",15)
 small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:
 bold=small=ImageFont.load_default()
labels=[
 ("Original PMT - real Cycles","960x640, 10 spp downsampled"),
 ("v8.9 - previous five broad pads","480x320, 4 spp"),
 ("v8.12 - back-shell correction","480x320, 4 spp"),
 ("v8.13 - 7 channels + packed normals","480x320, 4 spp")]
for j,(pic,(a,b)) in enumerate(zip(pics,labels)):
 x=j*480
 canvas.paste(pic,(x,70))
 draw.text((x+8,10),a,font=bold,fill=(236,240,245))
 draw.text((x+8,41),b,font=small,fill=(183,187,195))
canvas.save(dest,optimize=True)
delta=ImageStat.Stat(ImageChops.difference(pics[2],pics[3])).mean
report={
 "status":"DAYTONA_V8_13_REAL_PMT_CYCLES_FOUR_WAY_COMPARE_PASS",
 "source_images":[f.name for f in files],
 "source_sha256":[hashlib.sha256(f.read_bytes()).hexdigest() for f in files],
 "comparison":dest.name,
 "comparison_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
 "comparison_bytes":dest.stat().st_size,
 "candidate_v812_to_v813_RGB_mean_abs_delta":[round(x,4) for x in delta],
 "delta_is_NOT_quality_score":True,
 "same_camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,
 "candidate_480x320_4spp":True,
 "photometric_equivalence":"NOT_ESTABLISHED",
 "full_matched":"UNTESTED","game_runtime_Quest3":"UNTESTED"}
(w/"DAYTONA_V8_13_COMPARE_PROVENANCE.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_13_REAL_FOUR_WAY_COMPARE_PASS",json.dumps(report),flush=True)