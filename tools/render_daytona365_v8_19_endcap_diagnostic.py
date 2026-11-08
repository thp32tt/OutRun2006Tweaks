#!/usr/bin/env python3
"""Additional real Cycles left door/dash endcap diagnostic, NOT source-camera PMT match."""
import bpy,json,hashlib,os
from mathutils import Vector
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v819_ai2_093x"))/"blender_v8"
m=json.loads((W/"DAYTONA_V8_19_R2_BUILD_MANIFEST.json").read_text())
assert Path(bpy.data.filepath).resolve()==(W/m["output"]).resolve()
assert hashlib.sha256((W/m["output"]).read_bytes()).hexdigest()==m["output_sha256"]
scene=bpy.context.scene
cam=bpy.data.cameras.new("V8_19_Door_Endcap_Diagnostic_Camera")
obj=bpy.data.objects.new("V8_19_Door_Endcap_Diagnostic_Camera",cam)
scene.collection.objects.link(obj)
obj.location=(-.275,-.34,1.075)
target=Vector((-.762,.25,.80))
obj.rotation_euler=(target-obj.location).to_track_quat("-Z","Y").to_euler()
cam.lens=47
scene.camera=obj
scene.render.engine="CYCLES"
scene.cycles.device="CPU";scene.cycles.use_denoising=True
scene.render.threads_mode="FIXED";scene.render.threads=2
scene.render.resolution_x=480;scene.render.resolution_y=320
scene.render.resolution_percentage=100;scene.cycles.samples=4
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
scene.view_settings.exposure=-.52
out=W/"Daytona365_v8_19_r2_ENDCAP_CLOSEUP_ACTUAL_CYCLES.png"
assert not out.exists()
scene.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.exists() and out.stat().st_size>15000
result={"status":"DAYTONA_V8_19_ENDCAP_DIAGNOSTIC_CYCLES_PASS",
 "scene_sha256":m["output_sha256"],"camera":obj.name,
 "camera_position":list(obj.location),"target":list(target),"lens_mm":cam.lens,
 "samples":4,"width":480,"height":320,"threads":2,
 "diagnostic_not_original_camera":True,"engine":"CYCLES",
 "png":out.name,"png_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "render_validation":"DIAGNOSTIC_ONLY","full_sample_matched":"UNTESTED",
 "OVC_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_19_ENDCAP_DIAGNOSTIC_PROVENANCE.json").write_text(json.dumps(result,indent=2))
print("DAYTONA_V8_19_ENDCAP_DIAGNOSTIC_CYCLES_PASS",json.dumps(result))