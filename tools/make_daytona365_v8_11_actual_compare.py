#!/usr/bin/env python3
"""Actual unchanged PMT Cycles vs real v8.9, v8.10, v8.11 preview frames."""
import hashlib,json,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
files=[
 ROOT/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 W/"Daytona365_v8_9_ACTUAL_CYCLES_PREVIEW.png",
 W/"Daytona365_v8_10_ACTUAL_CYCLES_PREVIEW.png",
 W/"Daytona365_v8_11_ACTUAL_CYCLES_PREVIEW.png"]
dst=W/"Daytona365_ORIGINAL_vs_V8_9_V8_10_V8_11_ACTUAL_CYCLES_COMPARE.png"
assert not dst.exists()
assert all(f.is_file() for f in files)
frames=[Image.open(f).convert("RGB") for f in files]
assert frames[0].size==(960,640)
assert all(x.size==(480,320) for x in frames[1:])
frames[0]=frames[0].resize((480,320),Image.Resampling.LANCZOS)
sheet=Image.new("RGB",(1920,390),(23,25,29))
dr=ImageDraw.Draw(sheet)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",16)
 small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:
 bold=small=ImageFont.load_default()
labels=[
 ("ORIGINAL GAME PMT - real Cycles","960x640 / 10 spp downsampled"),
 ("v8.9 - padded seats and charcoal","480x320 / 4 spp preview"),
 ("v8.10 - dark door and wheel","480x320 / 4 spp preview"),
 ("v8.11 - conformal piping + crown","480x320 / 4 spp preview")]
for j,(frame,(title,detail)) in enumerate(zip(frames,labels)):
 x=480*j
 sheet.paste(frame,(x,70))
 dr.text((x+10,10),title,font=bold,fill=(235,239,243))
 dr.text((x+10,41),detail,font=small,fill=(181,186,192))
sheet.save(dst,optimize=True)
diff=ImageStat.Stat(ImageChops.difference(frames[2],frames[3]))
mean_abs_rgb=sum(diff.mean)/3.
r={"status":"DAYTONA_V8_11_ACTUAL_PMT_V89_V810_V811_COMPARE_PASS",
 "source_images":[p.name for p in files],
 "source_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in files],
 "comparison":dst.name,"comparison_bytes":dst.stat().st_size,
 "comparison_sha256":hashlib.sha256(dst.read_bytes()).hexdigest(),
 "previous_v810_to_v811_rgb_abs_diff_per_channel":mean_abs_rgb,
 "camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,
 "candidates_480x320_4spp":True,
 "photometric_equivalence":"NOT_ESTABLISHED",
 "full_resolution_matched":"UNTESTED",
 "game_runtime_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_11_COMPARE_PROVENANCE.json").write_text(json.dumps(r,indent=2))
print("DAYTONA_V8_11_REAL_FOUR_WAY_COMPARE_PASS",json.dumps(r),flush=True)