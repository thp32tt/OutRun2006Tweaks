#!/usr/bin/env python3
"""Actual PMT/v8.23/v8.24 source camera and v8.23/v8.24 wheel-only comparisons."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
import json,hashlib,os
W=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v824_ai2_1226"))/"blender_v8"
PMT=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png")
OLD=Path("/home/chatgpt-runner/work_handoff/daytona365_v823_ai2_20261108/blender_v8/Daytona365_v8_23_ACTUAL_CYCLES_PREVIEW.png")
NEW=W/"Daytona365_v8_24_r2_ACTUAL_CYCLES_PREVIEW.png"
STUDIO_OLD=Path("/home/chatgpt-runner/work_handoff/daytona365_v823_ai2_20261108/blender_v8/Daytona365_v8_23_SPOKE_ISOLATED_ACTUAL_CYCLES.png")
STUDIO_NEW=W/"Daytona365_v8_24_r2_SPOKE_ISOLATED_ACTUAL_CYCLES.png"
def font(size,bold=False):
 try:return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans"+("-Bold" if bold else "")+".ttf",size)
 except OSError:return ImageFont.load_default()
def compare(paths,titles,out,orig=False):
 images=[Image.open(p).convert("RGB") for p in paths]
 if orig:
  assert images[0].size==(960,640)
  images[0]=images[0].resize((480,320),Image.Resampling.LANCZOS)
 assert all(im.size==(480,320) for im in images)
 assert not out.exists()
 canvas=Image.new("RGB",(480*len(images),390),(20,24,29))
 draw=ImageDraw.Draw(canvas)
 for i,(im,title) in enumerate(zip(images,titles)):
  x=i*480
  canvas.paste(im,(x,70))
  draw.text((x+8,9),title,font=font(14,True),fill=(237,238,242))
  draw.text((x+8,39),"Real Cycles; "+("PMT source camera" if orig else "identical temporary studio camera"),font=font(11),fill=(184,191,202))
 canvas.save(out,optimize=True)
 delta=ImageStat.Stat(ImageChops.difference(images[-2],images[-1])).mean
 return {"output":out.name,"output_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "inputs":[str(p.name) for p in paths],
 "source_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
 "bytes":out.stat().st_size,"old_new_rgb_mean_absolute":[round(x,5) for x in delta],
 "delta_not_fidelity_score":True}
first=compare([PMT,OLD,NEW],
 ["Original game PMT, 960x640 10spp downsampled","v8.23 source 480x320 4spp",
  "v8.24-r2 nine true punched spoke holes"],
 W/"Daytona365_ORIGINAL_vs_V8_23_V8_24_R2_ACTUAL_CYCLES_COMPARE.png",True)
second=compare([STUDIO_OLD,STUDIO_NEW],
 ["v8.23 physical wheel bridges","v8.24-r2 9 actual drilled through-holes"],
 W/"Daytona365_V8_23_vs_V8_24_R2_SPOKE_ISOLATED_ACTUAL_CYCLES_COMPARE.png",False)
r={"status":"DAYTONA_V8_24_R2_ACTUAL_CYCLES_COMPARE_PASS",
 "source_camera_original_v823_v824":first,"temporary_studio_spoke_only":second,
 "all_genuine_cycles":True,"candidate":[480,320,4,2],
 "PMT_original":[960,640,10],"original_downsampled":True,
 "studio_camera_not_original_camera":True,
 "photometric_equivalence":"NOT_ESTABLISHED",
 "full_resolution_matched":"UNTESTED","original_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_24_R2_COMPARE_PROVENANCE.json").write_text(json.dumps(r,indent=2))
print("DAYTONA_V8_24_R2_ACTUAL_CYCLES_COMPARE_PASS",json.dumps(r),flush=True)