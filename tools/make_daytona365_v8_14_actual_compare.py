#!/usr/bin/env python3
"""Same-camera actual PMT/v8.13/v8.14 Cycles comparison; mixed spp disclosed."""
import hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
base=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
w=base/"blender_v8"
source=base/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png"
prev=base/"blender_v8/Daytona365_v8_13_ACTUAL_CYCLES_PREVIEW.png"
new=w/"Daytona365_v8_14_ACTUAL_CYCLES_PREVIEW.png"
for p in (source,prev,new):assert p.is_file(),p
imgs=[Image.open(p).convert("RGB") for p in (source,prev,new)]
assert imgs[0].size==(960,640) and imgs[1].size==imgs[2].size==(480,320)
imgs[0]=imgs[0].resize((480,320),Image.Resampling.LANCZOS)
dest=w/"Daytona365_ORIGINAL_vs_V8_13_V8_14_ACTUAL_CYCLES_COMPARE.png"
assert not dest.exists()
canvas=Image.new("RGB",(1440,392),(20,24,29));draw=ImageDraw.Draw(canvas)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",15)
 font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:bold=font=ImageFont.load_default()
labels=[("Original PMT - real Cycles","960x640, 10 spp downsampled"),
        ("v8.13 - 7 seat pleats","480x320, 4 spp"),
        ("v8.14 - fitted H-gate underdeck","480x320, 4 spp")]
for j,(img,(t,s)) in enumerate(zip(imgs,labels)):
 x=j*480;canvas.paste(img,(x,72))
 draw.text((x+9,11),t,font=bold,fill=(239,239,240))
 draw.text((x+9,41),s,font=font,fill=(184,192,202))
canvas.save(dest,optimize=True)
roi=(202,173,378,308)
delta=ImageChops.difference(imgs[1].crop(roi),imgs[2].crop(roi))
stats=ImageStat.Stat(delta)
p={"status":"DAYTONA_V8_14_REAL_PMT_CYCLES_THREE_WAY_PASS",
 "original":source.name,"v813":prev.name,"v814":new.name,
 "input_sha256":[hashlib.sha256(t.read_bytes()).hexdigest() for t in (source,prev,new)],
 "comparison":dest.name,"comparison_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
 "comparison_bytes":dest.stat().st_size,
 "camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,
 "candidate_480x320_4spp":True,
 "v813_v814_gear_area_roi_approx":list(roi),
 "v813_v814_roi_abs_rgb_mean":[round(x,3) for x in stats.mean],
 "photometric_equivalence":"NOT_ESTABLISHED",
 "attribution_note":"ROI pixel differences not attributable solely to geometry given independent 4spp stochastic renders",
 "matched_full_res":"UNTESTED","game_Quest3":"UNTESTED"}
(w/"DAYTONA_V8_14_COMPARE_PROVENANCE.json").write_text(json.dumps(p,indent=2),encoding="utf-8")
print("DAYTONA_V8_14_REAL_COMPARE_PASS",json.dumps(p),flush=True)