#!/usr/bin/env python3
"""Actual Cycles before/after on the original game-derived Daytona cockpit.

Uses IDENTICAL approximate seating camera for comparisons, not calibrated game
camera. Requires real PRIVATE source .blend, never CI smoke geometry.
Does not save the temporary camera to the production .blend.
"""
import bpy,sys,json,hashlib,os
from pathlib import Path
from mathutils import Vector
W=Path(os.environ["SLOT_A_WORK"])
mode=sys.argv[sys.argv.index("--")+1]
assert mode in ("before","after")
r=json.loads((W/"SLOT_A_DAYTONA_P0_R6_PHYSICAL_LIPS_GRIP_HUB_BEZEL.json").read_text())
name=r["input_blend"] if mode=="before" else r["output_blend"]
sha=r["input_blend_sha256"] if mode=="before" else r["output_blend_sha256"]
path=W/name
assert bpy.app.version_string.startswith("4.5.15")
assert Path(bpy.data.filepath).resolve()==path.resolve()
assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
sc=bpy.context.scene
camera_data=bpy.data.cameras.new("SLOTA_R6_TEMP_EYE_NOT_GAME")
camera=bpy.data.objects.new("SLOTA_R6_TEMP_EYE_NOT_GAME",camera_data)
sc.collection.objects.link(camera)
camera.location=(-.35,-.92,1.055)
target=Vector((-.24,.19,.797))
camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
camera_data.type="PERSP";camera_data.lens=28;camera_data.clip_start=.01
sc.camera=camera
sc.render.engine="CYCLES"
sc.cycles.device="CPU"
sc.render.threads_mode="FIXED";sc.render.threads=2
sc.cycles.samples=3;sc.cycles.use_denoising=True
sc.render.resolution_x=720;sc.render.resolution_y=480
sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG"
sc.render.image_settings.color_mode="RGBA"
sc.view_settings.exposure=-.52
output=W/("SLOTA_DAYTONA_R6_"+mode.upper()+"_ACTUAL_CYCLES_APPROX_EYE.png")
assert not output.exists(), "immutable comparison image"
sc.render.filepath=str(output)
bpy.ops.render.render(write_still=True)
assert output.is_file() and output.stat().st_size>12000
audit={
 "status":"DAYTONA_SLOT_A_R6_ACTUAL_PRIVATE_BLENDER_CYCLES_RENDER_PASS",
 "mode":mode,"source_blend_sha256":sha,"output_render_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
 "output_render":output.name,"resolution":[720,480],"spp":3,
 "camera":[-.35,-.92,1.055],"target":[-.24,.19,.797],"lens_mm":28,
 "same_approximate_camera":True,"game_camera_calibrated":False,
 "seven_exact_photo_views_complete":False,
 "production_blend_modified_by_render":False}
(W/("SLOTA_R6_"+mode.upper()+"_RENDER_AUDIT.json")).write_text(json.dumps(audit,indent=2))
print(audit["status"],json.dumps(audit),flush=True)
