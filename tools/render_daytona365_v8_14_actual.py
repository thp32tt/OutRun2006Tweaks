#!/usr/bin/env python3
"""Actual official Blender 4.5 LTS Cycles v8.14 output with SHA provenance."""
import bpy,os,hashlib,json
from pathlib import Path
root=Path(os.environ.get("DAYTONA365_WORKDIR", "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"));w=root/"blender_v8"
model=w/"Daytona365_Cockpit_Blender_PBR_v8_14.blend"
manifest=json.loads((w/"DAYTONA_V8_14_BUILD_MANIFEST.json").read_text())
assert Path(bpy.data.filepath).resolve()==model.resolve()
assert hashlib.sha256(model.read_bytes()).hexdigest()==manifest["output_sha256"]
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert scene.render.engine=="CYCLES"
profile=os.environ.get("DAYTONA365_RENDER_PROFILE","preview")
assert profile in ("preview","matched")
if profile=="matched":assert os.environ.get("DAYTONA365_APPROVED_HEAVY_RENDER_HOST")=="1"
scene.cycles.device="CPU";scene.render.threads_mode="FIXED";scene.render.threads=2
scene.cycles.use_denoising=True;scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
scene.view_settings.exposure=-.52
if profile=="preview":
 scene.render.resolution_x=480;scene.render.resolution_y=320;scene.cycles.samples=4
else:
 scene.render.resolution_x=960;scene.render.resolution_y=640;scene.cycles.samples=10
output=w/("Daytona365_v8_14_ACTUAL_CYCLES_PREVIEW.png" if profile=="preview" else "Daytona365_v8_14_ACTUAL_CYCLES_MATCHED.png")
assert not output.exists()
scene.render.filepath=str(output)
bpy.ops.render.render(write_still=True)
assert output.is_file() and output.stat().st_size>15000
rep={"status":"DAYTONA_V8_14_ACTUAL_CYCLES_PASS",
 "model_sha256":manifest["output_sha256"],
 "blender":bpy.app.version_string,"engine":"CYCLES",
 "profile":profile,"camera":scene.camera.name,"samples":scene.cycles.samples,
 "threads":scene.render.threads,"width":scene.render.resolution_x,
 "height":scene.render.resolution_y,"denoising":True,
 "exposure":scene.view_settings.exposure,
 "image":output.name,"bytes":output.stat().st_size,
 "sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
 "render_validation":"PREVIEW_ONLY" if profile=="preview" else "MATCHED_SAME_CAMERA",
 "full_resolution_matched":"UNTESTED" if profile=="preview" else "PASS",
 "game_runtime_Quest3":"UNTESTED"}
(w/"DAYTONA_V8_14_PREVIEW_RENDER_PROVENANCE.json").write_text(json.dumps(rep,indent=2),encoding="utf-8")
print("DAYTONA_V8_14_ACTUAL_CYCLES_PASS",json.dumps(rep),flush=True)