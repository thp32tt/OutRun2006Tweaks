#!/usr/bin/env python3
"""Actual private v8.6 low-load Cycles preview; same camera as real PMT render.

Full resolution must be run on a suitable Windows/Actions machine supplied
with authorized private input; do not fake matching-resolution results.
"""
import bpy,hashlib,json,os
from pathlib import Path
root=Path(os.environ.get("DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
source=w/"Daytona365_Cockpit_Blender_PBR_v8_6.blend"
assert Path(bpy.data.filepath).resolve()==source.resolve()
build=json.loads((w/"DAYTONA_V8_6_BUILD_MANIFEST.json").read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==build["new_sha256"]
profile=os.environ.get("DAYTONA365_RENDER_PROFILE","preview")
assert profile in ("preview","matched"),profile
s=bpy.context.scene
assert s.camera and s.camera.name=="V7_Camera_Reference_ThreeQuarter"
s.render.engine="CYCLES"
s.cycles.device="CPU"
s.cycles.use_denoising=True
s.render.threads_mode="FIXED"
s.render.threads=2
s.render.image_settings.file_format="PNG"
s.render.image_settings.color_mode="RGBA"
s.render.resolution_percentage=100
s.view_settings.exposure=-.52
if profile=="preview":
 s.render.resolution_x,s.render.resolution_y,s.cycles.samples=480,320,4
 image=w/"Daytona365_v8_6_ACTUAL_CYCLES_PREVIEW.png"
else:
 # Only intended for an authorized non-N100 render host.
 assert os.environ.get("DAYTONA365_APPROVED_HEAVY_RENDER_HOST")=="1", "no high resolution on controller"
 s.render.resolution_x,s.render.resolution_y,s.cycles.samples=960,640,10
 image=w/"Daytona365_v8_6_ACTUAL_CYCLES_MATCHED.png"
assert not image.exists(), "Never overwrite provenance evidence"
s.render.filepath=str(image)
bpy.ops.render.render(write_still=True)
assert image.is_file() and image.stat().st_size>15000
data={
 "status":"ACTUAL_BLENDER_CYCLES_RENDERED",
 "profile":profile,
 "scene_sha256":build["new_sha256"],
 "blender":bpy.app.version_string,
 "engine":s.render.engine,
 "device":s.cycles.device,
 "camera":s.camera.name,
 "width":s.render.resolution_x,
 "height":s.render.resolution_y,
 "samples":s.cycles.samples,
 "threads":s.render.threads,
 "denoising":True,
 "exposure":s.view_settings.exposure,
 "image":image.name,
 "image_bytes":image.stat().st_size,
 "image_sha256":hashlib.sha256(image.read_bytes()).hexdigest(),
 "render_validation":"PREVIEW_ONLY" if profile=="preview" else "MATCHED_SAME_CAMERA",
 "game_runtime":"UNTESTED"
}
(w/("DAYTONA_V8_6_"+profile.upper()+"_RENDER_PROVENANCE.json")).write_text(json.dumps(data,indent=2))
print("DAYTONA_V8_6_ACTUAL_PREVIEW_RENDER_PASS" if profile=="preview" else "DAYTONA_V8_6_MATCHED_RENDER_PASS",json.dumps(data),flush=True)
