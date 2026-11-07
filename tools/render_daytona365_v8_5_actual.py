#!/usr/bin/env python3
"""Render actual private v8.5 Blender scene with reproducible camera/settings.

preview: strictly bounded 480x320 / 4-sample Cycles (light inspection only).
matched: 960x640 / 10-sample Cycles, same framing/studio as v8.4.
The matched profile should run on a Windows workstation or suitable runner,
not a resource-constrained N100 controller.
"""
import bpy,hashlib,json,os
from pathlib import Path
root=Path(os.environ.get(
    "DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
out=root/"blender_v8"
source=out/"Daytona365_Cockpit_Blender_PBR_v8_5.blend"
assert Path(bpy.data.filepath).resolve()==source.resolve()
assert source.is_file()
profile=os.environ.get("DAYTONA365_RENDER_PROFILE","preview")
assert profile in ("preview","matched"),profile
s=bpy.context.scene
assert s.camera and s.camera.name=="V7_Camera_Reference_ThreeQuarter"
s.render.engine="CYCLES"
s.cycles.device="CPU"
s.cycles.use_denoising=True
s.render.resolution_percentage=100
s.render.image_settings.file_format="PNG"
s.render.image_settings.color_mode="RGBA"
s.view_settings.exposure=-.52
if profile=="preview":
 s.render.resolution_x=480
 s.render.resolution_y=320
 s.cycles.samples=4
 image=out/"Daytona365_v8_5_ACTUAL_CYCLES_PREVIEW.png"
else:
 s.render.resolution_x=960
 s.render.resolution_y=640
 s.cycles.samples=10
 image=out/"Daytona365_v8_5_ACTUAL_CYCLES_SAME_CAMERA.png"
assert not image.exists(), "Refuse to overwrite real evidence"
s.render.filepath=str(image)
bpy.ops.render.render(write_still=True)
assert image.is_file() and image.stat().st_size>15000,(image,image.stat().st_size if image.exists() else 0)
data={
 "status":"ACTUAL_BLENDER_CYCLES_RENDERED",
 "profile":profile,
 "blender":bpy.app.version_string,
 "scene_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
 "engine":s.render.engine,
 "device":s.cycles.device,
 "camera":s.camera.name,
 "width":s.render.resolution_x,
 "height":s.render.resolution_y,
 "samples":s.cycles.samples,
 "denoise":True,
 "exposure":s.view_settings.exposure,
 "image":image.name,
 "image_sha256":hashlib.sha256(image.read_bytes()).hexdigest(),
 "image_bytes":image.stat().st_size,
 "render_validation":"PREVIEW_ONLY" if profile=="preview" else "MATCHED_SAME_CAMERA",
 "game_runtime_validation":"UNTESTED"
}
(out/f"DAYTONA_V8_5_{profile.upper()}_RENDER_PROVENANCE.json").write_text(
 json.dumps(data,indent=2),encoding="utf-8")
print("DAYTONA_V8_5_ACTUAL_RENDER_PREVIEW_PASS" if profile=="preview" else
      "DAYTONA_V8_5_MATCHED_RENDER_PASS",json.dumps(data),flush=True)
