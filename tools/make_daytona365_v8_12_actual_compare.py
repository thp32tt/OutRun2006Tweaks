#!/usr/bin/env python3
"""Same camera: genuine PMT + immutable v8.10/v8.11/v8.12 Cycles previews."""
import hashlib,json,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
files=[root/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 w/"Daytona365_v8_10_ACTUAL_CYCLES_PREVIEW.png",
 w/"Daytona365_v8_11_ACTUAL_CYCLES_PREVIEW.png",
 w/"Daytona365_v8_12_ACTUAL_CYCLES_PREVIEW.png"]
dest=w/"Daytona365_ORIGINAL_vs_V8_10_V8_11_V8_12_ACTUAL_CYCLES_COMPARE.png"
assert all(p.is_file() for p in files)
assert not dest.exists(),"No comparison evidence overwrite"
imgs=[Image.open(p).convert("RGB") for p in files]
assert imgs[0].size==(960,640)
assert all(q.size==(480,320) for q in imgs[1:])
imgs[0]=imgs[0].resize((480,320),Image.Resampling.LANCZOS)
canvas=Image.new("RGB",(1920,390),(22,25,29));draw=ImageDraw.Draw(canvas)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",16)
 normal=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:bold=normal=ImageFont.load_default()
labels=[
 ("Original PMT - genuine Cycles","960x640, 10 spp downsampled"),
 ("v8.10 - original backrest protruding","480x320, 4 spp"),
 ("v8.11 - dark piping + crown","480x320, 4 spp"),
 ("v8.12 - native V5 back-shell correction","480x320, 4 spp")]
for j,(pic,(title,detail)) in enumerate(zip(imgs,labels)):
 x=j*480;canvas.paste(pic,(x,70))
 draw.text((x+9,10),title,font=bold,fill=(238,240,243))
 draw.text((x+9,41),detail,font=normal,fill=(180,187,193))
canvas.save(dest,optimize=True)
report={"status":"DAYTONA_V8_12_REAL_PMT_CYCLES_FOUR_WAY_COMPARE_PASS",
 "source_images":[p.name for p in files],
 "source_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in files],
 "comparison":dest.name,"comparison_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
 "comparison_bytes":dest.stat().st_size,
 "camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,
 "candidate_480x320_4spp":True,
 "photometric_equivalence":"NOT_ESTABLISHED",
 "full_resolution_matched":"UNTESTED","game_runtime_Quest3":"UNTESTED"}
(w/"DAYTONA_V8_12_COMPARE_PROVENANCE.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("DAYTONA_V8_12_REAL_FOUR_WAY_COMPARE_PASS",json.dumps(report),flush=True)