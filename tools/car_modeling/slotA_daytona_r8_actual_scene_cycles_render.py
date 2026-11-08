#!/usr/bin/env python3
"""Render real ORIGINAL-derived Daytona private r8 scene, no synthetic substitute.
Same approximate non-game eye as the already verified immutable r7 Cycles frame.
"""
import bpy,hashlib,json,os
from pathlib import Path
from mathutils import Vector
W=Path(os.environ["SLOT_A_WORK"])
a=json.loads((W/"SLOT_A_DAYTONA_P0_R8_PHOTO_GUIDED_EXISTING_MESH.json").read_text())
f=W/a["output_blend"]
assert bpy.app.version_string.startswith("4.5.15")
assert Path(bpy.data.filepath).resolve()==f.resolve()
assert hashlib.sha256(f.read_bytes()).hexdigest()==a["output_sha256"]
sc=bpy.context.scene
data=bpy.data.cameras.new("SLOTA_R8_TRANSIENT_COMPARE_EYE_NOT_GAME")
cam=bpy.data.objects.new("SLOTA_R8_TRANSIENT_COMPARE_EYE_NOT_GAME",data)
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
sc.render.image_settings.file_format="PNG"
sc.render.image_settings.color_mode="RGBA"
sc.view_settings.exposure=-.52
out=W/"SLOTA_DAYTONA_R8_AFTER_REAL_CYCLES_APPROX_EYE.png"
assert not out.exists(),"no overwrite of previous real render"
sc.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.is_file() and out.stat().st_size>10000
record={"result":"SLOTA_R8_REAL_SOURCE_CYCLES_RENDER_PASS",
"blender":bpy.app.version_string,
"input_private_blend_sha256":a["output_sha256"],
"actual_cycles_png":out.name,
"png_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
"render_resolution":[720,480],"samples":3,
"same_camera_as_r7_real_scene":True,"camera_calibrated_to_game":False,
"model_source_original_game_sha256":a["original_game_sha256"],
"public_github_host_private_scene":"BLOCKED_INPUT_NOT_TRANSFERRED",
"game_export":False,"production_source_unmodified_by_render":True}
(W/"SLOTA_R8_REAL_RENDER_AUDIT.json").write_text(json.dumps(record,indent=2))
print(record["result"],json.dumps(record),flush=True)
