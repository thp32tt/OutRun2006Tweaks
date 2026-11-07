#!/usr/bin/env python3
"""Official real v8.15 Cycles preview; source and no-overwrite provenance."""
import bpy,hashlib,json,os
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))/"blender_v8"
model=W/"Daytona365_Cockpit_Blender_PBR_v8_15.blend"
m=json.loads((W/"DAYTONA_V8_15_BUILD_MANIFEST.json").read_text())
assert Path(bpy.data.filepath).resolve()==model.resolve()
assert hashlib.sha256(model.read_bytes()).hexdigest()==m["output_sha256"]
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
profile=os.environ.get("DAYTONA365_RENDER_PROFILE","preview")
assert profile in ("preview","matched")
if profile=="matched":assert os.environ.get("DAYTONA365_APPROVED_HEAVY_RENDER_HOST")=="1"
scene.render.engine="CYCLES";scene.cycles.device="CPU"
scene.render.threads_mode="FIXED";scene.render.threads=2
scene.cycles.use_denoising=True
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
scene.view_settings.exposure=-.52
if profile=="preview":
 scene.render.resolution_x=480;scene.render.resolution_y=320;scene.cycles.samples=4
else:
 scene.render.resolution_x=960;scene.render.resolution_y=640;scene.cycles.samples=10
dest=W/("Daytona365_v8_15_ACTUAL_CYCLES_PREVIEW.png" if profile=="preview"
 else "Daytona365_v8_15_ACTUAL_CYCLES_MATCHED.png")
assert not dest.exists(),"No render evidence overwrite"
scene.render.filepath=str(dest)
bpy.ops.render.render(write_still=True)
assert dest.is_file() and dest.stat().st_size>15000
result={"status":"DAYTONA_V8_15_ACTUAL_CYCLES_RENDER_PASS",
 "blend_sha256":m["output_sha256"],"blender":bpy.app.version_string,
 "engine":"CYCLES","device":"CPU","profile":profile,
 "camera":scene.camera.name,"width":scene.render.resolution_x,
 "height":scene.render.resolution_y,"samples":scene.cycles.samples,
 "threads":scene.render.threads,"denoising":True,
 "exposure":scene.view_settings.exposure,
 "image":dest.name,"bytes":dest.stat().st_size,
 "sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
 "render_validation":"PREVIEW_ONLY" if profile=="preview" else "MATCHED_SAME_CAMERA",
 "game_Quest3":"UNTESTED"}
(W/("DAYTONA_V8_15_"+profile.upper()+"_RENDER_PROVENANCE.json")).write_text(json.dumps(result,indent=2),encoding="utf-8")
print("DAYTONA_V8_15_ACTUAL_CYCLES_PASS",json.dumps(result),flush=True)