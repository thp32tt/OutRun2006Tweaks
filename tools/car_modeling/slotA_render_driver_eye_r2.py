#!/usr/bin/env python3
"""Read-only genuine Blender driver-eye *approximation* comparison, same temporary camera.
QA diagnostics only; never save or export source/model/game files.
"""
import bpy,hashlib,json,math,os,sys
from pathlib import Path
from mathutils import Vector
W=Path(os.environ["SLOT_A_WORK"])
mode=sys.argv[sys.argv.index("--")+1]
assert mode in ("before","after")
manifest=json.loads((W/"SLOT_A_P0_DASH_WHEEL_V1_R2.json").read_text())
name=manifest["input_blend"] if mode=="before" else manifest["output_blend"]
sha=manifest["input_blend_sha256"] if mode=="before" else manifest["output_blend_sha256"]
src=W/name
assert Path(bpy.data.filepath).resolve()==src.resolve()
assert hashlib.sha256(src.read_bytes()).hexdigest()==sha

sc=bpy.context.scene
camera=bpy.data.cameras.new("SLOTA_TEMP_DRIVER_EYE_NOT_GAME_CAMERA")
ob=bpy.data.objects.new("SLOTA_TEMP_DRIVER_EYE_NOT_GAME_CAMERA",camera)
sc.collection.objects.link(ob)
ob.location=(-.35,-.92,1.055)
target=Vector((-.24,.19,.797))
ob.rotation_euler=(target-ob.location).to_track_quat("-Z","Y").to_euler()
camera.type="PERSP";camera.lens=28.;camera.clip_start=.01
sc.camera=ob
sc.render.engine="CYCLES";sc.cycles.device="CPU"
sc.render.threads_mode="FIXED";sc.render.threads=2
sc.cycles.samples=4;sc.cycles.use_denoising=True
sc.render.resolution_x=480;sc.render.resolution_y=320;sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
sc.view_settings.exposure=-.52
out=W/("SLOTA_DAYTONA_P0_R2_"+mode.upper()+"_APPROX_DRIVER_EYE_ACTUAL_CYCLES.png")
assert not out.exists()
sc.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.is_file() and out.stat().st_size>10000
rep={"status":"SLOTA_DAYTONA_REAL_CYCLES_PREVIEW_PASS","which":mode,
"input_blend_sha256":sha,"render":out.name,"render_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
"camera":"APPROX_LEFT_HAND_DRIVER_EYE_NOT_GAME_CAMERA",
"eye_xyz":[-.35,-.92,1.055],"look_target":[-.24,.19,.797],
"engine":"CYCLES","resolution":[480,320],"samples":4,"cpu_threads":2,
"photo_comparison_full_QA":"UNTESTED","driver_camera_alignment":"APPROXIMATE",
"new_blend_saved_during_render":False,"game_export":"NONE"}
(W/("SLOTA_P0_R2_"+mode.upper()+"_RENDER_PROVENANCE.json")).write_text(json.dumps(rep,indent=2))
print("SLOTA_DAYTONA_REAL_CYCLES_PREVIEW_PASS",json.dumps(rep),flush=True)