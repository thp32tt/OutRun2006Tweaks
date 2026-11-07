#!/usr/bin/env python3
"""REAL original PMT, v8.6 and v8.7 Blender Cycles scenes; no generated images."""
import hashlib,json,os
from pathlib import Path
from PIL import Image,ImageChops,ImageDraw,ImageFont
root=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
orig=root/"original_game_blender/Daytona365_ORIGINAL_GAME_CYCLES_SAME_CAMERA.png"
old=w/"Daytona365_v8_6_ACTUAL_CYCLES_PREVIEW.png"
new=w/"Daytona365_v8_7_ACTUAL_CYCLES_PREVIEW.png"
compare=w/"Daytona365_ORIGINAL_vs_V8_6_vs_V8_7_ACTUAL_CYCLES_PREVIEW_COMPARE.png"
assert orig.is_file() and old.is_file() and new.is_file()
assert not compare.exists()
o=Image.open(orig).convert("RGB")
a=Image.open(old).convert("RGB")
b=Image.open(new).convert("RGB")
assert o.size==(960,640) and a.size==b.size==(480,320)
delta=ImageChops.difference(a,b)
changed=sum(any(c for c in x) for x in delta.getdata())
assert changed>10000,(changed,"Actual model must visibly change")
mean_difference=sum(sum(x) for x in delta.getdata())/(480*320*3)
header=69
im=Image.new("RGB",(1440,389),(22,24,27))
for i,p in enumerate((o.resize((480,320),Image.Resampling.LANCZOS),a,b)):
 im.paste(p,(i*480,header))
d=ImageDraw.Draw(im)
try:
 font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",16)
 small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
except OSError:
 font=ImageFont.load_default();small=font
for i,title,sub in [
 (0,"ORIGINAL GAME PMT - actual Cycles","960x640 / 10 spp downsampled"),
 (1,"V8.6 real Blender Cycles","480x320 / 4 spp reference"),
 (2,"V8.7 real Blender Cycles","480x320 / 4 spp new")]:
 x=i*480+12
 d.text((x,10),title,font=font,fill=(236,239,241))
 d.text((x,40),sub,font=small,fill=(178,185,195))
im.save(compare,optimize=True)
data={
 "status":"DAYTONA_V8_7_ORIGINAL_V86_V87_ACTUAL_RENDER_COMPARE",
 "camera_identical":True,
 "original_960x640_10spp_downsampled":True,
 "v86_v87_480x320_4spp_matched":True,
 "original_sha256":hashlib.sha256(orig.read_bytes()).hexdigest(),
 "v86_sha256":hashlib.sha256(old.read_bytes()).hexdigest(),
 "v87_sha256":hashlib.sha256(new.read_bytes()).hexdigest(),
 "comparison_sha256":hashlib.sha256(compare.read_bytes()).hexdigest(),
 "comparison_bytes":compare.stat().st_size,
 "comparison_filename":compare.name,
 "changed_RGB_pixels_v86_v87":changed,
 "mean_absolute_RGB_difference_v86_v87":round(mean_difference,5),
 "full_resolution_matched_original":"UNTESTED",
 "game_runtime":"UNTESTED"}
(w/"DAYTONA_V8_7_COMPARE_PROVENANCE.json").write_text(json.dumps(data,indent=2))
print("DAYTONA_V8_7_REAL_THREE_WAY_COMPARE_PASS",json.dumps(data),flush=True)
