#!/usr/bin/env python3
"""Compare genuine original PMT Cycles and consecutive actual v8.16/v8.17 Cycles."""
import hashlib,json,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageStat,ImageChops
base=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107")
older=Path("/home/chatgpt-runner/work_handoff/daytona365_v816_ai2_0817")
work=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v817_ai2_0917_gpt6"))/"blender_v8"
paths=[base/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 older/"blender_v8/Daytona365_v8_16_ACTUAL_CYCLES_PREVIEW.png",
 work/"Daytona365_v8_17_ACTUAL_CYCLES_PREVIEW.png"]
for p in paths:assert p.exists(),p
im=[Image.open(p).convert("RGB") for p in paths]
assert im[0].size==(960,640)
assert im[1].size==im[2].size==(480,320)
im[0]=im[0].resize((480,320),Image.Resampling.LANCZOS)
out=work/"Daytona365_ORIGINAL_vs_V8_16_V8_17_ACTUAL_CYCLES_COMPARE.png"
assert not out.exists()
canvas=Image.new("RGB",(1440,396),(20,24,30))
d=ImageDraw.Draw(canvas)
try:
 fb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",14)
 fs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:fb=fs=ImageFont.load_default()
labels=[("Genuine original PMT - real Cycles","960x640 / 10 spp, downsampled"),
 ("v8.16 original-bounded seats","480x320 / 4 spp"),
 ("v8.17 physical instrument cowl + dark PBR","480x320 / 4 spp")]
for idx,(bitmap,(headline,meta)) in enumerate(zip(im,labels)):
 x=idx*480;canvas.paste(bitmap,(x,76))
 d.text((x+10,10),headline,font=fb,fill=(238,240,243))
 d.text((x+10,42),meta,font=fs,fill=(182,191,206))
canvas.save(out,optimize=True)
# Numeric differences are NOT photometric fidelity because original rendering samples differ.
roi=(170,0,470,126)
stats=ImageStat.Stat(ImageChops.difference(im[1].crop(roi),im[2].crop(roi)))
report={"status":"DAYTONA_V8_17_REAL_PMT_CYCLES_COMPARE_PASS",
 "original":paths[0].name,"v816":paths[1].name,"v817":paths[2].name,
 "input_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
 "comparison":out.name,"comparison_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "comparison_bytes":out.stat().st_size,"camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,"candidate_480x320_4spp":True,
 "v816_v817_gauge_dash_ROI_approx":list(roi),
 "v816_v817_ROI_abs_RGB_mean":[round(t,3) for t in stats.mean],
 "photometric_equivalence":"NOT_ESTABLISHED",
 "attribution_note":"Differences include stochastic noise, not direct score or pixel-wise source attribution.",
 "full_resolution_sample_matched":"UNTESTED","OVC_game_Quest3":"UNTESTED"}
(work/"DAYTONA_V8_17_COMPARE_PROVENANCE.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_17_REAL_PMT_CYCLES_COMPARE_PASS",json.dumps(report))