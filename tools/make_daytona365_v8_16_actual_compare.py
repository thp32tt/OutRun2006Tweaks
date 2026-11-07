#!/usr/bin/env python3
"""Actual-original PMT / verified v8.15 / new v8.16 real Cycles comparison."""
import os,hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
base=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
W=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v816_ai2_0817"))/"blender_v8"
paths=[base/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
base/"blender_v8/Daytona365_v8_15_ACTUAL_CYCLES_PREVIEW.png",
W/"Daytona365_v8_16_ACTUAL_CYCLES_PREVIEW.png"]
imgs=[Image.open(p).convert("RGB") for p in paths]
assert imgs[0].size==(960,640)
assert imgs[1].size==imgs[2].size==(480,320)
imgs[0]=imgs[0].resize((480,320),Image.Resampling.LANCZOS)
out=W/"Daytona365_ORIGINAL_vs_V8_15_V8_16_ACTUAL_CYCLES_COMPARE.png"
assert not out.exists()
canvas=Image.new("RGB",(1440,392),(20,24,29));draw=ImageDraw.Draw(canvas)
try:
 bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",15)
 font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:bold=font=ImageFont.load_default()
labels=[("Original PMT - actual Cycles","960x640, 10 spp downsampled"),
 ("v8.15 - original bounded cushion bolsters","480x320, 4 spp"),
 ("v8.16 - physical backrest wings / normal","480x320, 4 spp")]
for i,(img,(label,detail)) in enumerate(zip(imgs,labels)):
 x=i*480;canvas.paste(img,(x,72))
 draw.text((x+9,11),label,font=bold,fill=(239,239,240))
 draw.text((x+9,41),detail,font=font,fill=(184,192,202))
canvas.save(out,optimize=True)
roi=(18,78,192,298)
rgb=ImageStat.Stat(ImageChops.difference(imgs[1].crop(roi),imgs[2].crop(roi)))
report={"status":"DAYTONA_V8_16_REAL_PMT_CYCLES_THREE_WAY_PASS",
 "original":paths[0].name,"v815":paths[1].name,"v816":paths[2].name,
 "input_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
 "comparison":out.name,"comparison_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "comparison_bytes":out.stat().st_size,
 "camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,
 "candidate_480x320_4spp":True,
 "v815_v816_backrest_ROI_approx":list(roi),
 "v815_v816_backrest_ROI_abs_RGB_mean":[round(v,3) for v in rgb.mean],
 "photometric_equivalence":"NOT_ESTABLISHED",
 "attribution_note":"ROI pixel differences include independent stochastic noise; no per-pixel source attribution",
 "full_matched_resolution":"UNTESTED","game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_16_COMPARE_PROVENANCE.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("DAYTONA_V8_16_REAL_COMPARE_PASS",json.dumps(report),flush=True)