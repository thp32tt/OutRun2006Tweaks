#!/usr/bin/env python3
"""Actual (not synthetic) private PMT-derived Daytona r9 Cycles comparison.
Render only: transient preview camera, never save/edit production geometry.
"""
import bpy,hashlib,json,os
from pathlib import Path
from mathutils import Vector
W=Path(os.environ["SLOT_A_WORK"])
a=json.loads((W/"SLOT_A_DAYTONA_P0_R9_ORIGINAL_ARCH_STEERING_GEOMETRY.json").read_text())
f=W/a["after_blend"]
assert bpy.app.version_string.startswith("4.5.15")
assert Path(bpy.data.filepath).resolve()==f.resolve()
assert hashlib.sha256(f.read_bytes()).hexdigest()==a["after_blend_sha256"]
assert Path(a["original_pmt_resource"]).is_file()
assert hashlib.sha256(Path(a["original_pmt_resource"]).read_bytes()).hexdigest()==a["original_pmt_sha256"]
sc=bpy.context.scene
cd=bpy.data.cameras.new("SLOTA_R9_COMPARE_CAMERA_TRANSIENT_NOT_REAL_GAME")
eye=bpy.data.objects.new("SLOTA_R9_COMPARE_CAMERA_TRANSIENT_NOT_REAL_GAME",cd)
sc.collection.objects.link(eye)
eye.location=(-.35,-.92,1.055)
target=Vector((-.24,.19,.797))
eye.rotation_euler=(target-eye.location).to_track_quat("-Z","Y").to_euler()
cd.type="PERSP";cd.lens=28;cd.clip_start=.01
sc.camera=eye
sc.render.engine="CYCLES";sc.cycles.device="CPU"
sc.render.threads_mode="FIXED";sc.render.threads=2
sc.cycles.samples=3;sc.cycles.use_denoising=True
sc.render.resolution_x=720;sc.render.resolution_y=480
sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG"
sc.render.image_settings.color_mode="RGBA"
sc.view_settings.exposure=-.52
out=W/"SLOTA_DAYTONA_R9_AFTER_REAL_CYCLES_APPROX_EYE.png"
assert not out.exists()
sc.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.stat().st_size>12000
rec={"result":"SLOTA_R9_ACTUAL_NATIVE_SOURCE_CYCLES_RENDER_PASS",
 "private_blend_sha256":a["after_blend_sha256"],"native_pmt_sha256":a["original_pmt_sha256"],
 "actual_cycles_png":out.name,"png_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "width":720,"height":480,"samples":3,"blender":bpy.app.version_string,
 "same_camera_as_previous_r8_actual_scene":True,"original_game_driver_eye":"NOT_CALIBRATED",
 "hosted_actions_original_private_scene":"BLOCKED_INPUT","game_export":False,
 "source_blend_not_modified_by_render":True,"vehicle_complete":False}
(W/"SLOTA_R9_RENDER_AUDIT.json").write_text(json.dumps(rec,indent=2))
print(rec["result"],json.dumps(rec),flush=True)