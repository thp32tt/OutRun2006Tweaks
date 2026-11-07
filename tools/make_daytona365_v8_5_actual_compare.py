#!/usr/bin/env python3
"""Side-by-side REAL render evidence; never fabricate or relabel images.

Original was already rendered at 960x640 10 samples; this script downsamples it
for the 480x320 4-sample v8.5 inspection preview. Rendering settings are NOT
identical, so this is directional shape inspection, not photometric validation.
"""
import hashlib,json,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(os.environ.get("DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
original=root/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png"
candidate=root/"blender_v8/Daytona365_v8_5_ACTUAL_CYCLES_PREVIEW.png"
output=root/"blender_v8/Daytona365_ORIGINAL_vs_V8_5_ACTUAL_PREVIEW_COMPARE.png"
assert original.is_file() and candidate.is_file()
assert not output.exists(), "Do not overwrite previous visual evidence"
a=Image.open(original).convert("RGB")
b=Image.open(candidate).convert("RGB")
assert a.size==(960,640) and b.size==(480,320)
a=a.resize((480,320),Image.Resampling.LANCZOS)
bar=62
im=Image.new("RGB",(960,320+bar),(23,25,29))
im.paste(a,(0,bar))
im.paste(b,(480,bar))
d=ImageDraw.Draw(im)
try:
 font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",17)
 small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",12)
except OSError:
 font=ImageFont.load_default()
 small=font
d.text((12,8),"ORIGINAL GAME PMT - actual Cycles",font=font,fill=(241,241,242))
d.text((492,8),"V8.5 REWORK - actual Cycles",font=font,fill=(241,241,242))
d.text((12,35),"960x640 render, reduced to 480x320",font=small,fill=(182,186,193))
d.text((492,35),"480x320, 4 spp - PREVIEW ONLY",font=small,fill=(182,186,193))
im.save(output,optimize=True)
meta={
 "status":"REAL_ORIGINAL_AND_REAL_V85_PREVIEW_COMPARE",
 "original_render_sha256":hashlib.sha256(original.read_bytes()).hexdigest(),
 "preview_render_sha256":hashlib.sha256(candidate.read_bytes()).hexdigest(),
 "compare":output.name,
 "compare_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
 "compare_bytes":output.stat().st_size,
 "matched_camera":True,
 "same_sample_count":False,
 "full_resolution_validation":"UNTESTED"
}
(root/"blender_v8/DAYTONA_V8_5_COMPARE_PROVENANCE.json").write_text(
 json.dumps(meta,indent=2),encoding="utf-8")
print("DAYTONA_V8_5_ACTUAL_COMPARE_PASS",json.dumps(meta),flush=True)
