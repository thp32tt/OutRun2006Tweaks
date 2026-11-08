#!/usr/bin/env python3
"""Actual before/after steering-only Cycles comparison, same temporary camera.
Source photo is NOT included; factory wheel and PMT original are not claimed
to have these studio-light conditions.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
import hashlib,json,os
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v823_ai2_20261108"))/"blender_v8"
p1=W/"Daytona365_v8_22_r2_SPOKE_ISOLATED_ACTUAL_CYCLES.png"
p2=W/"Daytona365_v8_23_SPOKE_ISOLATED_ACTUAL_CYCLES.png"
assert p1.is_file() and p2.is_file()
i1=Image.open(p1).convert("RGB");i2=Image.open(p2).convert("RGB")
assert i1.size==i2.size==(480,320)
out=W/"Daytona365_V8_22_R2_vs_V8_23_SPOKE_ISOLATED_ACTUAL_CYCLES_COMPARE.png"
assert not out.exists()
canvas=Image.new("RGB",(960,389),(20,24,29))
drawer=ImageDraw.Draw(canvas)
try:
 bf=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",14)
 sm=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:bf=sm=ImageFont.load_default()
for k,(im,title) in enumerate(((i1,"v8.22-r2 original rectangular spoke helpers"),(i2,"v8.23 formed 14-station tapered metal spokes"))):
 x=k*480
 canvas.paste(im,(x,69))
 drawer.text((x+8,8),title,font=bf,fill=(237,238,242))
 drawer.text((x+8,38),"Actual Cycles; isolated study camera, NOT factory/PMT framing",font=sm,fill=(184,191,202))
canvas.save(out,optimize=True)
delta=ImageStat.Stat(ImageChops.difference(i1,i2)).mean
report={"status":"DAYTONA_V8_23_REAL_SPOKE_DETAIL_COMPARE_PASS",
 "images":[p1.name,p2.name],
 "source_sha256":[hashlib.sha256(p.read_bytes()).hexdigest() for p in (p1,p2)],
 "output":out.name,"output_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "size_bytes":out.stat().st_size,
 "same_temp_studio_camera_lighting":True,
 "studio_view_is_not_original_PMT_reference_camera":True,
 "both_true_blender_cycles":True,"each_preview":[480,320,4,2],
 "pixel_difference_not_factory_fidelity":[round(x,5) for x in delta],
 "full_resolution_original_matched":"UNTESTED","original_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_23_SPOKE_DETAIL_COMPARE_PROVENANCE.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_23_REAL_SPOKE_DETAIL_COMPARE_PASS",json.dumps(report),flush=True)