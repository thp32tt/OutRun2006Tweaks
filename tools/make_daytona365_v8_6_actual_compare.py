#!/usr/bin/env python3
"""Three-way comparison of *actual* images, no AI generation or redrawn content.

Original PMT frame has 960x640 10 spp; both reworks 480x320 4 spp. All three
use the same calibrated Blender camera. Only the two rework previews have
identical sample counts/resolutions. Preserve these caveats in provenance.
"""
import hashlib,json,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(os.environ.get("DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
pmt=root/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png"
prev=w/"Daytona365_v8_5_ACTUAL_CYCLES_PREVIEW.png"
new=w/"Daytona365_v8_6_ACTUAL_CYCLES_PREVIEW.png"
out=w/"Daytona365_ORIGINAL_vs_V8_5_vs_V8_6_ACTUAL_CYCLES_PREVIEW_COMPARE.png"
assert pmt.is_file() and prev.is_file() and new.is_file()
assert not out.exists(), "Do not overwrite genuine comparison evidence"
a=Image.open(pmt).convert("RGB")
b=Image.open(prev).convert("RGB")
c=Image.open(new).convert("RGB")
assert a.size==(960,640) and b.size==(480,320) and c.size==(480,320)
a=a.resize((480,320),Image.Resampling.LANCZOS)
header=70
sheet=Image.new("RGB",(1440,320+header),(23,25,29))
for idx,img in enumerate((a,b,c)):
 sheet.paste(img,(idx*480,header))
draw=ImageDraw.Draw(sheet)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",16)
 small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:
 bold=ImageFont.load_default()
 small=bold
for idx,title,sub in (
 (0,"ORIGINAL GAME PMT - real Cycles","960x640 10 spp, scaled to 480x320"),
 (1,"V8.5 ACTUAL BLENDER - real Cycles","480x320 4 spp, baseline preview"),
 (2,"V8.6 ACTUAL BLENDER - real Cycles","480x320 4 spp, new preview")):
 x=idx*480+10
 draw.text((x,11),title,font=bold,fill=(239,240,241))
 draw.text((x,41),sub,font=small,fill=(180,186,196))
sheet.save(out,optimize=True)
meta={
 "status":"REAL_ORIGINAL_V85_V86_RENDER_COMPARISON",
 "same_camera":True,
 "original_960x640_10spp_downsampled":True,
 "v85_v86_same_480x320_4spp":True,
 "original_sha256":hashlib.sha256(pmt.read_bytes()).hexdigest(),
 "v85_sha256":hashlib.sha256(prev.read_bytes()).hexdigest(),
 "v86_sha256":hashlib.sha256(new.read_bytes()).hexdigest(),
 "comparison_file":out.name,
 "comparison_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "comparison_bytes":out.stat().st_size,
 "full_resolution_matched_samples":"UNTESTED",
 "game_runtime":"UNTESTED"
}
(w/"DAYTONA_V8_6_COMPARE_PROVENANCE.json").write_text(json.dumps(meta,indent=2))
print("DAYTONA_V8_6_REAL_THREE_WAY_COMPARE_PASS",json.dumps(meta),flush=True)
