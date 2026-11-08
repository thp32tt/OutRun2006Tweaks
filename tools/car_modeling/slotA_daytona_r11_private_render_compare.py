#!/usr/bin/env python3
"""Compare genuine native-derived R10/R11 Cycles with private real Spider photo.

Never publish photographs, proprietary .blend, or PMT.
"""
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
import hashlib,json
W=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
PHOTO=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
SRC=W/"SLOTA_DAYTONA_R10_AFTER_REAL_CYCLES_APPROX_EYE.png"
DST=W/"SLOTA_DAYTONA_R11_AFTER_REAL_CYCLES_APPROX_EYE.png"
a=json.loads((W/"SLOT_A_DAYTONA_P0_R11_NATIVE_COWL_STEERING_RELIEF_GEOMETRY.json").read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(PHOTO)==a["exact_spider_photo_sha256"]
assert sha(SRC)=="788190a690426b9786642bf7cbb32b5a3d6416bb91e56db5ef35db7c0ad9d234"
assert sha(DST)=="0a169d07346c38bbc2b3892c75443c33f92e6970308269711d8728aa6d7a552d"
before=Image.open(SRC).convert("RGB")
after=Image.open(DST).convert("RGB")
assert before.size==after.size==(720,480)
difference=ImageChops.difference(before,after)
pixels=list(difference.getdata())
changed=sum(1 for px in pixels if max(px)>3)
assert changed>200,("R11 render may be unchanged",changed)
avg=[round(sum(px[i] for px in pixels)/len(pixels),6) for i in range(3)]
DIFF=W/"SLOTA_R11_R10_R11_ACTUAL_CYCLES_PIXEL_DIFF.png"
assert not DIFF.exists()
difference.point(lambda v:min(255,v*5)).save(DIFF)
contact=Image.new("RGB",(2160,540),(18,19,22))
draw=ImageDraw.Draw(contact)
photos=[Image.open(PHOTO).convert("RGB"),before,after]
for i,(img,label) in enumerate(zip(photos,[
"Real 1971 Daytona Spider LHD / photo is NOT game eye",
"R10 private native-derived Cycles / approximate eye",
"R11 private native-derived Cycles / same approximate eye"])):
 img.thumbnail((716,480),Image.Resampling.LANCZOS)
 contact.paste(img,(i*720+(720-img.width)//2,42+(480-img.height)//2))
 draw.text((i*720+12,15),label,fill=(245,245,245))
OUT=W/"SLOTA_R11_PRIVATE_REAL_SPIDER_PHOTO_R10_R11.jpg"
assert not OUT.exists()
contact.save(OUT,quality=92,optimize=True)
result={"result":"SLOTA_R11_REAL_SOURCE_PHOTO_R10_R11_COMPARISON_PASS",
"original_game_sha256":a["original_pmt_sha256"],
"original_import_sha256":a["original_import_sha256"],
"prior_scene_sha256":a["before_blend_sha256"],"r11_scene_sha256":a["after_blend_sha256"],
"photo_sha256":sha(PHOTO),"r10_render_sha256":sha(SRC),"r11_render_sha256":sha(DST),
"comparison_private_file":OUT.name,"comparison_sha256":sha(OUT),
"diff_file":DIFF.name,"diff_sha256":sha(DIFF),
"changed_pixels_gt3":changed,"total_pixels":len(pixels),"mean_abs_rgb":avg,
"same_approximate_camera":True,"original_game_eye":"NOT_CALIBRATED",
"seven_authentic_views":"INCOMPLETE","github_hosted_real_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
"no_game_export":True,"vehicle_complete":False}
(W/"SLOTA_R11_PRIVATE_RENDER_COMPARISON_AUDIT.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,ensure_ascii=False))