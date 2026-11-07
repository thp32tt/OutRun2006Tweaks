#!/usr/bin/env python3
"""Real official Blender Cycles v8.13: low-cost faithful same-camera preview."""
import bpy,hashlib,json,os
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=ROOT/"blender_v8"
model=w/"Daytona365_Cockpit_Blender_PBR_v8_13.blend"
m=json.loads((w/"DAYTONA_V8_13_BUILD_MANIFEST.json").read_text())
assert Path(bpy.data.filepath).resolve()==model.resolve()
assert hashlib.sha256(model.read_bytes()).hexdigest()==m["output_sha256"]
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
profile=os.environ.get("DAYTONA365_RENDER_PROFILE","preview")
assert profile in ("preview","matched")
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.render.threads_mode="FIXED";scene.render.threads=2
scene.cycles.use_denoising=True
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
scene.view_settings.exposure=-.52
if profile=="preview":
 scene.render.resolution_x=480
 scene.render.resolution_y=320
 scene.cycles.samples=4
 out=w/"Daytona365_v8_13_ACTUAL_CYCLES_PREVIEW.png"
else:
 assert os.environ.get("DAYTONA365_APPROVED_HEAVY_RENDER_HOST")=="1"
 scene.render.resolution_x=960
 scene.render.resolution_y=640
 scene.cycles.samples=10
 out=w/"Daytona365_v8_13_ACTUAL_CYCLES_MATCHED.png"
assert not out.exists(),"Never overwrite previous actual render evidence"
scene.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.is_file() and out.stat().st_size>12000
data={"status":"ACTUAL_BLENDER_CYCLES_RENDERED",
 "blender":bpy.app.version_string,"model_sha256":m["output_sha256"],
 "source_normal_sha256":m["generated_normal_sha256"],
 "camera":scene.camera.name,"engine":"CYCLES","device":scene.cycles.device,
 "width":scene.render.resolution_x,"height":scene.render.resolution_y,
 "samples":scene.cycles.samples,"threads":scene.render.threads,
 "denoising":True,"exposure":scene.view_settings.exposure,
 "profile":profile,"image":out.name,"bytes":out.stat().st_size,
 "sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "render_validation":"PREVIEW_ONLY" if profile=="preview" else "MATCHED_SAME_CAMERA",
 "game_runtime":"UNTESTED","Quest3":"UNTESTED"}
(w/("DAYTONA_V8_13_"+profile.upper()+"_RENDER_PROVENANCE.json")).write_text(json.dumps(data,indent=2))
print("DAYTONA_V8_13_ACTUAL_CYCLES_PREVIEW_PASS" if profile=="preview" else "DAYTONA_V8_13_ACTUAL_CYCLES_MATCHED_PASS",json.dumps(data),flush=True)