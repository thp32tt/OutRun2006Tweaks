#!/usr/bin/env python3
"""Actual PMT/v8.14/v8.15 same-camera Cycles contact sheet, no invented image."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
import hashlib,json,os
base=Path(os.environ.get("DAYTONA365_SOURCE_ARCHIVE",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=Path(os.environ.get("DAYTONA365_WORKDIR",str(base)))/"blender_v8"
pictures=[
 base/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png",
 base/"blender_v8/Daytona365_v8_14_ACTUAL_CYCLES_PREVIEW.png",
 w/"Daytona365_v8_15_ACTUAL_CYCLES_PREVIEW.png"]
dest=w/"Daytona365_ORIGINAL_vs_V8_14_V8_15_ACTUAL_CYCLES_COMPARE.png"
assert all(p.is_file() for p in pictures),pictures
assert not dest.exists(),"Do not overwrite real render evidence"
imgs=[Image.open(p).convert("RGB") for p in pictures]
assert imgs[0].size==(960,640)
assert imgs[1].size==imgs[2].size==(480,320)
imgs[0]=imgs[0].resize((480,320),Image.Resampling.LANCZOS)
canvas=Image.new("RGB",(1440,392),(22,25,29))
draw=ImageDraw.Draw(canvas)
try:
 font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",16)
 detail=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:font=detail=ImageFont.load_default()
captions=[
 ("Original PMT - actual Cycles","960x640, 10 spp, downsampled"),
 ("v8.14 - before outer bolster/apron","480x320, 4 spp"),
 ("v8.15 - physical outer bolster/apron","480x320, 4 spp")]
for k,(image,(caption,sub)) in enumerate(zip(imgs,captions)):
 x=480*k
 canvas.paste(image,(x,72))
 draw.text((x+8,8),caption,font=font,fill=(237,242,246))
 draw.text((x+8,40),sub,font=detail,fill=(174,187,198))
canvas.save(dest,optimize=True)
# ROI intentionally approximate; stochastic denoise/pixel diffs never
# interpreted as material provenance or quantitative visual-improvement grade.
roi=(20,184,470,316)
delta=ImageChops.difference(imgs[1].crop(roi),imgs[2].crop(roi))
stats=[round(v,5) for v in ImageStat.Stat(delta).mean]
report={"status":"DAYTONA_V8_15_REAL_PMT_CYCLES_COMPARE_PASS",
 "images":[p.name for p in pictures],
 "source_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in pictures],
 "comparison":dest.name,"comparison_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
 "comparison_bytes":dest.stat().st_size,
 "camera":"V7_Camera_Reference_ThreeQuarter",
 "original_960x640_10spp_downsampled":True,
 "candidate_480x320_4spp":True,
 "visual_bolster_apron_roi_approx":list(roi),
 "roi_abs_rgb_mean":[float(v) for v in stats],
 "photometric_equivalence":"NOT_ESTABLISHED",
 "roi_difference_is_not_quality_score":True,
 "original_pmt_image_is_actual_blender_not_ai_art":True,
 "full_matched_resolution":"UNTESTED","game_Quest3":"UNTESTED"}
out=w/"DAYTONA_V8_15_COMPARE_PROVENANCE.json"
assert not out.exists()
out.write_text(json.dumps(report,indent=2),encoding="utf-8")
print("DAYTONA_V8_15_REAL_COMPARE_PASS",json.dumps(report),flush=True)