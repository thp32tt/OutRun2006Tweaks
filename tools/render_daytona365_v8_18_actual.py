#!/usr/bin/env python3
"""Genuine official Blender 4.5 CPU Cycles preview, v8.18 source SHA pinned."""
import bpy,hashlib,json,os
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v818_ai2_0926"))/"blender_v8"
m=json.loads((W/"DAYTONA_V8_18_R2_BUILD_MANIFEST.json").read_text())
model=W/m["output"]
assert Path(bpy.data.filepath).resolve()==model.resolve()
assert hashlib.sha256(model.read_bytes()).hexdigest()==m["output_sha256"]
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert scene.render.engine=="CYCLES"
profile=os.environ.get("DAYTONA365_RENDER_PROFILE","preview")
assert profile in ("preview","matched")
if profile=="matched":assert os.environ.get("DAYTONA365_APPROVED_HEAVY_RENDER_HOST")=="1"
scene.cycles.device="CPU";scene.render.threads_mode="FIXED";scene.render.threads=2
scene.cycles.use_denoising=True;scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG";scene.render.image_settings.color_mode="RGBA"
scene.view_settings.exposure=-.52
if profile=="preview":
 scene.render.resolution_x=480;scene.render.resolution_y=320;scene.cycles.samples=4
else:
 scene.render.resolution_x=960;scene.render.resolution_y=640;scene.cycles.samples=10
out=W/("Daytona365_v8_18_r2_ACTUAL_CYCLES_PREVIEW.png" if profile=="preview" else "Daytona365_v8_18_r2_ACTUAL_CYCLES_MATCHED.png")
assert not out.exists()
scene.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.is_file() and out.stat().st_size>15000
r={"status":"DAYTONA_V8_18_ACTUAL_CYCLES_PASS",
 "model_sha256":m["output_sha256"],"blender":bpy.app.version_string,
 "engine":"CYCLES","profile":profile,"camera":scene.camera.name,
 "width":scene.render.resolution_x,"height":scene.render.resolution_y,
 "samples":scene.cycles.samples,"threads":scene.render.threads,
 "denoising":True,"exposure":scene.view_settings.exposure,
 "image":out.name,"image_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "bytes":out.stat().st_size,
 "render_validation":"PREVIEW_ONLY" if profile=="preview" else "MATCHED_SAME_CAMERA",
 "full_resolution_matched":"UNTESTED" if profile=="preview" else "PASS",
 "OVC_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_18_PREVIEW_RENDER_PROVENANCE.json").write_text(json.dumps(r,indent=2))
print("DAYTONA_V8_18_ACTUAL_CYCLES_PASS",json.dumps(r),flush=True)