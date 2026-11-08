#!/usr/bin/env python3
"""PRIVATE reference + two actual original-source Cycles views, never game export."""
from pathlib import Path
from PIL import Image,ImageChops,ImageDraw,ImageFont
import hashlib,json
W=Path("/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108")
P=Path("/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg")
R9=W/"SLOTA_DAYTONA_R9_AFTER_REAL_CYCLES_APPROX_EYE.png"
R10=W/"SLOTA_DAYTONA_R10_AFTER_REAL_CYCLES_APPROX_EYE.png"
A=json.loads((W/"SLOT_A_DAYTONA_P0_R10_ORIGINAL_SPIDER_DASH_WHEEL_GEOMETRY.json").read_text())
assert all(p.is_file() for p in [P,R9,R10])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P)==A["exact_spider_photo_sha256"]
assert sha(R9)=="089a47d69917935716905699a8f45a47e0b1217f07fd48cf1c45fbef4b1260e9"
assert sha(R10)=="788190a690426b9786642bf7cbb32b5a3d6416bb91e56db5ef35db7c0ad9d234"
a=Image.open(R9).convert("RGB")
b=Image.open(R10).convert("RGB")
difference=ImageChops.difference(a,b)
pixels=list(difference.getdata())
changed=sum(1 for r,g,blue in pixels if max(r,g,blue)>3)
assert changed>150,("no meaningful image difference",changed)
mean_abs=[round(sum(px[i] for px in pixels)/len(pixels),6) for i in range(3)]
diff=difference.point(lambda val:min(255,val*5))
D=W/"SLOTA_R10_R9_R10_ACTUAL_CYCLES_PIXEL_DIFF.png"
D.parent.mkdir(parents=True,exist_ok=True);assert not D.exists()
diff.save(D)
images=[Image.open(P).convert("RGB"),Image.open(R9).convert("RGB"),Image.open(R10).convert("RGB")]
canvas=Image.new("RGB",(2160,535),(20,22,25))
labels=["1971 real 365 GTS/4 Spider LHD (NOT matched eye)","R9 native-derived Cycles / approximate eye","R10 native-derived Cycles / identical approximate eye"]
draw=ImageDraw.Draw(canvas)
for i,(im,label) in enumerate(zip(images,labels)):
 im.thumbnail((720,480),Image.Resampling.LANCZOS)
 ox=i*720+(720-im.width)//2;oy=42+(480-im.height)//2
 canvas.paste(im,(ox,oy))
 draw.text((i*720+12,13),label,fill=(235,235,235))
C=W/"SLOTA_R10_PRIVATE_REAL_SPIDER_PHOTO_R9_R10.jpg"
assert not C.exists()
canvas.save(C,quality=91,optimize=True)
rec={"result":"SLOTA_R10_PRIVATE_REFERENCE_R9_R10_ACTUAL_RENDER_DIFF_PASS",
"original_pmt_sha256":A["original_pmt_sha256"],"r9_blend_sha256":A["before_blend_sha256"],"r10_blend_sha256":A["after_blend_sha256"],
"reference_photo_sha256":sha(P),"r9_render_sha256":sha(R9),"r10_render_sha256":sha(R10),
"compare_image":C.name,"compare_sha256":sha(C),"pixel_diff_image":D.name,"pixel_diff_sha256":sha(D),
"render_width":720,"render_height":480,"changed_pixels_gt3":changed,"total_pixels":len(pixels),
"mean_abs_diff_channels":mean_abs,
"same_approximate_camera":True,"true_game_driver_eye":"NOT_CALIBRATED","seven_exact_model_views":"INCOMPLETE",
"no_public_photo_and_no_original_blend_upload":True,"no_game_export":True,"complete":False}
(W/"SLOTA_R10_PRIVATE_RENDER_COMPARISON_AUDIT.json").write_text(json.dumps(rec,indent=2))
print(json.dumps(rec,ensure_ascii=False))