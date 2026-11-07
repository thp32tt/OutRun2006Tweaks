#!/usr/bin/env python3
"""Four genuine Cycles frames: original PMT versus verified v8.6/v8.7/v8.8.
Same camera/framing; original 960x640 10 spp downsized to 480x320,
candidate previews 480x320 at 4 spp (not photometric equivalence).
"""
import hashlib,json,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
files=(
 root/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 w/"Daytona365_v8_6_ACTUAL_CYCLES_PREVIEW.png",
 w/"Daytona365_v8_7_ACTUAL_CYCLES_PREVIEW.png",
 w/"Daytona365_v8_8_ACTUAL_CYCLES_PREVIEW.png")
dest=w/"Daytona365_ORIGINAL_vs_V8_6_V8_7_V8_8_ACTUAL_CYCLES_COMPARE.png"
assert all(p.is_file() for p in files)
assert not dest.exists(),"Never overwrite original comparison image"
ims=[Image.open(p).convert("RGB") for p in files]
assert ims[0].size==(960,640)
assert all(im.size==(480,320) for im in ims[1:])
ims[0]=ims[0].resize((480,320),Image.Resampling.LANCZOS)
sheet=Image.new("RGB",(1920,390),(23,25,29))
d=ImageDraw.Draw(sheet)
try:
 title=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",16)
 sub=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:
 title=ImageFont.load_default();sub=title
labels=(("ORIGINAL PMT (real Blender)","960x640 10spp -> 480x320"),
 ("v8.6 actual Blender","480x320, 4 spp"),
 ("v8.7 actual Blender","480x320, 4 spp"),
 ("v8.8 new actual Blender","480x320, 4 spp"))
for j,(im,(name,detail)) in enumerate(zip(ims,labels)):
 x=j*480
 sheet.paste(im,(x,70))
 d.text((x+10,11),name,font=title,fill=(238,240,242))
 d.text((x+10,42),detail,font=sub,fill=(186,191,198))
sheet.save(dest,optimize=True)
report={
 "status":"ACTUAL_ORIGINAL_PMT_V86_V87_V88_COMPARISON",
 "same_camera_framing":True,
 "original_960x640_10spp_downsampled":True,
 "candidate_480x320_4spp":True,
 "source_images":[p.name for p in files],
 "source_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in files],
 "comparison_file":dest.name,
 "comparison_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
 "comparison_bytes":dest.stat().st_size,
 "photometric_equivalence":"NOT_ESTABLISHED",
 "full_resolution_matched_cycles":"UNTESTED",
 "game_runtime":"UNTESTED"}
(w/"DAYTONA_V8_8_COMPARE_PROVENANCE.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_8_REAL_FOUR_WAY_COMPARE_PASS",json.dumps(report))