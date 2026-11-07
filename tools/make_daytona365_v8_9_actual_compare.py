#!/usr/bin/env python3
"""Actual (not generated) PMT / v8.7 / v8.8 / v8.9 Cycles frame comparison.
Original source frame was 960x640 10 spp downsampled; candidates 480x320 4 spp.
Same physical reference camera, unequal samples (visual only).
"""
from pathlib import Path
import json,hashlib,os
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
files=[
 ROOT/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 W/"Daytona365_v8_7_ACTUAL_CYCLES_PREVIEW.png",
 W/"Daytona365_v8_8_ACTUAL_CYCLES_PREVIEW.png",
 W/"Daytona365_v8_9_ACTUAL_CYCLES_PREVIEW.png"]
DEST=W/"Daytona365_ORIGINAL_vs_V8_7_V8_8_V8_9_ACTUAL_CYCLES_COMPARE.png"
assert all(p.is_file() for p in files)
assert not DEST.exists(),"Never overwrite previous comparison evidence"
frames=[Image.open(f).convert("RGB") for f in files]
assert frames[0].size==(960,640)
assert all(i.size==(480,320) for i in frames[1:])
frames[0]=frames[0].resize((480,320),Image.Resampling.LANCZOS)
sheet=Image.new("RGB",(1920,390),(23,25,29))
draw=ImageDraw.Draw(sheet)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",16)
 small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:
 bold=ImageFont.load_default()
 small=bold
labels=[
 ("Original game PMT - real Cycles","960x640 10 spp downsampled"),
 ("v8.7 - measured seat silhouette","480x320 4 spp original candidate"),
 ("v8.8 - PMT console / leather","480x320 4 spp baseline"),
 ("v8.9 - headrest / pleats / charcoal","480x320 4 spp new scene")]
for n,(im,(title,detail)) in enumerate(zip(frames,labels)):
 x=n*480
 sheet.paste(im,(x,70))
 draw.text((x+10,10),title,font=bold,fill=(239,241,243))
 draw.text((x+10,41),detail,font=small,fill=(181,186,192))
sheet.save(DEST,optimize=True)
info={
 "status":"ACTUAL_ORIGINAL_PMT_V87_V88_V89_CYCLES_COMPARE_PASS",
 "source_images":[f.name for f in files],
 "source_sha256":[hashlib.sha256(f.read_bytes()).hexdigest() for f in files],
 "comparison":DEST.name,
 "comparison_sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(),
 "comparison_bytes":DEST.stat().st_size,
 "camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,
 "candidate_480x320_4spp":True,
 "photometric_equivalence":"NOT_ESTABLISHED",
 "full_resolution_matched":"UNTESTED",
 "game_runtime_Quest3":"UNTESTED"
}
(W/"DAYTONA_V8_9_COMPARE_PROVENANCE.json").write_text(json.dumps(info,indent=2))
print("DAYTONA_V8_9_REAL_FOUR_WAY_COMPARE_PASS",json.dumps(info),flush=True)