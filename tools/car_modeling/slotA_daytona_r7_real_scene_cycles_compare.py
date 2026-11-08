#!/usr/bin/env python3
"""Slot A r7 REAL private-source Cycles before/after from identical approximate eye.

Requires actual native PMT-derived .blend files; no mock/cube. Render only, never
save a modified production .blend or export a game model.
"""
import bpy,hashlib,json,os,sys
from pathlib import Path
from mathutils import Vector
W=Path(os.environ["SLOT_A_WORK"])
a=sys.argv[sys.argv.index("--")+1]
assert a in ("before","after")
r=json.loads((W/"SLOT_A_DAYTONA_P0_R7_ORIGINAL_BINNACLE_SPOKE.json").read_text())
n=r["input_blend"] if a=="before" else r["output_blend"]
h=r["input_sha256"] if a=="before" else r["output_sha256"]
f=W/n
assert bpy.app.version_string.startswith("4.5.15")
assert Path(bpy.data.filepath).resolve()==f.resolve()
assert hashlib.sha256(f.read_bytes()).hexdigest()==h
sc=bpy.context.scene
data=bpy.data.cameras.new("SLOTA_R7_TRANSIENT_COMPARE_EYE_NOT_GAME")
cam=bpy.data.objects.new("SLOTA_R7_TRANSIENT_COMPARE_EYE_NOT_GAME",data)
sc.collection.objects.link(cam)
cam.location=(-.35,-.92,1.055)
target=Vector((-.24,.19,.797))
cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
data.type="PERSP";data.lens=28;data.clip_start=.01
sc.camera=cam
sc.render.engine="CYCLES";sc.cycles.device="CPU"
sc.render.threads_mode="FIXED";sc.render.threads=2
sc.cycles.samples=3;sc.cycles.use_denoising=True
sc.render.resolution_x=720;sc.render.resolution_y=480
sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
sc.view_settings.exposure=-.52
out=W/("SLOTA_DAYTONA_R7_"+a.upper()+"_REAL_CYCLES_APPROX_EYE.png")
assert not out.exists()
sc.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.is_file() and out.stat().st_size>12000
q={"result":"SLOTA_R7_ACTUAL_PRIVATE_SCENE_CYCLES_RENDER_PASS",
   "mode":a,"input_sha256":h,"render":out.name,
   "render_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
   "resolution":[720,480],"samples":3,
   "same_approximate_camera":True,"driver_eye_game_calibrated":False,
   "photo_7_views":"INCOMPLETE","model_source":r["original_game_sha256"],
   "production_blend_not_resaved":True,"game_export":False}
(W/("SLOTA_R7_"+a.upper()+"_RENDER_AUDIT.json")).write_text(json.dumps(q,indent=2))
print(q["result"],json.dumps(q),flush=True)
