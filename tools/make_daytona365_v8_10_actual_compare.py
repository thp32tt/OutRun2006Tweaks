#!/usr/bin/env python3
"""Actual original PMT and v8.8 / v8.9 / v8.10 Cycles 4-panel comparison."""
import hashlib,json,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
files=[root/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 w/"Daytona365_v8_8_ACTUAL_CYCLES_PREVIEW.png",
 w/"Daytona365_v8_9_ACTUAL_CYCLES_PREVIEW.png",
 w/"Daytona365_v8_10_ACTUAL_CYCLES_PREVIEW.png"]
dest=w/"Daytona365_ORIGINAL_vs_V8_8_V8_9_V8_10_ACTUAL_CYCLES_COMPARE.png"
assert all(f.is_file() for f in files)
assert not dest.exists(),"Preserve immutable comparison evidence"
pics=[Image.open(f).convert("RGB") for f in files]
assert pics[0].size==(960,640)
assert all(q.size==(480,320) for q in pics[1:])
pics[0]=pics[0].resize((480,320),Image.Resampling.LANCZOS)
canvas=Image.new("RGB",(1920,390),(23,25,29))
d=ImageDraw.Draw(canvas)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",16)
 small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:
 bold=small=ImageFont.load_default()
labels=[
 ("Original PMT - actual Cycles","960x640, 10 spp downsampled"),
 ("v8.8 - source console baseline","480x320, 4 spp"),
 ("v8.9 - source seats + headrest","480x320, 4 spp"),
 ("v8.10 - dark doors / wheel + normals","480x320, 4 spp")]
for j,(pic,(a,b)) in enumerate(zip(pics,labels)):
 x=j*480
 canvas.paste(pic,(x,70))
 d.text((x+10,10),a,font=bold,fill=(239,241,243))
 d.text((x+10,41),b,font=small,fill=(181,186,192))
canvas.save(dest,optimize=True)
report={"status":"DAYTONA_V8_10_REAL_PMT_CYCLES_FOUR_WAY_COMPARE_PASS",
 "source_images":[p.name for p in files],
 "source_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in files],
 "comparison":dest.name,"comparison_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
 "comparison_bytes":dest.stat().st_size,
 "camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,
 "candidate_480x320_4spp":True,
 "photometric_equivalence":"NOT_ESTABLISHED",
 "full_resolution_matched":"UNTESTED","game_runtime_Quest3":"UNTESTED"}
(w/"DAYTONA_V8_10_COMPARE_PROVENANCE.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_10_REAL_FOUR_WAY_COMPARE_PASS",json.dumps(report),flush=True)