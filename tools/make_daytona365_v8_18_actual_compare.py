#!/usr/bin/env python3
"""Genuine original PMT/v8.17/v8.18 same-camera actual Cycles image contact."""
import hashlib,json,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
base=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v818_ai2_0926"))/"blender_v8"
paths=[base/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 Path("/home/chatgpt-runner/work_handoff/daytona365_v817_ai2_0917_gpt6/blender_v8/Daytona365_v8_17_ACTUAL_CYCLES_PREVIEW.png"),
 W/"Daytona365_v8_18_r2_ACTUAL_CYCLES_PREVIEW.png"]
for p in paths:assert p.is_file(),p
imgs=[Image.open(p).convert("RGB") for p in paths]
assert imgs[0].size==(960,640)
assert imgs[1].size==imgs[2].size==(480,320)
imgs[0]=imgs[0].resize((480,320),Image.Resampling.LANCZOS)
dest=W/"Daytona365_ORIGINAL_vs_V8_17_V8_18_R2_ACTUAL_CYCLES_COMPARE.png"
assert not dest.exists()
canvas=Image.new("RGB",(1440,392),(20,24,29));d=ImageDraw.Draw(canvas)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",15)
 font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:bold=font=ImageFont.load_default()
labels=[("Original PMT - actual Cycles","960x640, 10 spp downsampled"),
 ("v8.17 - physical instrument cowl","480x320, 4 spp"),
 ("v8.18 - restrained source surround","480x320, 4 spp")]
for i,(img,(label,detail)) in enumerate(zip(imgs,labels)):
 x=i*480;canvas.paste(img,(x,72))
 d.text((x+9,11),label,font=bold,fill=(239,239,240))
 d.text((x+9,41),detail,font=font,fill=(184,192,202))
canvas.save(dest,optimize=True)
roi=(242,94,361,249)
delta=ImageStat.Stat(ImageChops.difference(imgs[1].crop(roi),imgs[2].crop(roi)))
rep={"status":"DAYTONA_V8_18_REAL_PMT_CYCLES_THREE_WAY_PASS",
 "original":paths[0].name,"v817":paths[1].name,"v818":paths[2].name,
 "input_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
 "comparison":dest.name,"comparison_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
 "comparison_bytes":dest.stat().st_size,
 "camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,"candidate_480x320_4spp":True,
 "center_switchbank_ROI_approx":list(roi),
 "v817_v818_roi_abs_rgb_mean":[round(float(x),4) for x in delta.mean],
 "photometric_equivalence":"NOT_ESTABLISHED",
 "attribution_note":"Independent stochastic Cycles 4spp means ROI delta is not a PMT likeness score.",
 "full_resolution_matched":"UNTESTED","game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_18_COMPARE_PROVENANCE.json").write_text(json.dumps(rep,indent=2))
print("DAYTONA_V8_18_REAL_COMPARE_PASS",json.dumps(rep),flush=True)