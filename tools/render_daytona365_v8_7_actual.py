#!/usr/bin/env python3
"""Real Blender Cycles render v8.7; never label preview as matched original."""
import bpy,hashlib,json,os
from pathlib import Path
root=Path(os.environ.get("DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8";src=w/"Daytona365_Cockpit_Blender_PBR_v8_7.blend"
build=json.loads((w/"DAYTONA_V8_7_BUILD_MANIFEST.json").read_text())
assert Path(bpy.data.filepath).resolve()==src.resolve()
assert hashlib.sha256(src.read_bytes()).hexdigest()==build["new_sha256"]
mode=os.environ.get("DAYTONA365_RENDER_PROFILE","preview")
assert mode in ("preview","matched")
s=bpy.context.scene
assert s.camera.name=="V7_Camera_Reference_ThreeQuarter"
s.render.engine="CYCLES";s.cycles.device="CPU";s.cycles.use_denoising=True
s.render.threads_mode="FIXED";s.render.threads=2
s.render.image_settings.file_format="PNG"
s.render.image_settings.color_mode="RGBA"
s.render.resolution_percentage=100;s.view_settings.exposure=-.52
if mode=="preview":
 s.render.resolution_x,s.render.resolution_y,s.cycles.samples=480,320,4
 image=w/"Daytona365_v8_7_ACTUAL_CYCLES_PREVIEW.png"
else:
 assert os.environ.get("DAYTONA365_APPROVED_HEAVY_RENDER_HOST")=="1"
 s.render.resolution_x,s.render.resolution_y,s.cycles.samples=960,640,10
 image=w/"Daytona365_v8_7_ACTUAL_CYCLES_MATCHED.png"
assert not image.exists(),"Do not overwrite genuine render evidence"
s.render.filepath=str(image)
bpy.ops.render.render(write_still=True)
assert image.is_file() and image.stat().st_size>15000
data={
 "status":"DAYTONA_V8_7_ACTUAL_CYCLES_RENDERED",
 "scene_sha256":build["new_sha256"],
 "blender":bpy.app.version_string,"engine":"CYCLES","device":"CPU",
 "profile":mode,"camera":s.camera.name,
 "width":s.render.resolution_x,"height":s.render.resolution_y,
 "samples":s.cycles.samples,"threads":s.render.threads,"denoising":True,
 "exposure":s.view_settings.exposure,
 "image":image.name,"image_bytes":image.stat().st_size,
 "image_sha256":hashlib.sha256(image.read_bytes()).hexdigest(),
 "render_validation":"PREVIEW_ONLY" if mode=="preview" else "MATCHED_SAME_CAMERA",
 "game_runtime":"UNTESTED"}
(w/("DAYTONA_V8_7_"+mode.upper()+"_RENDER_PROVENANCE.json")).write_text(json.dumps(data,indent=2))
print("DAYTONA_V8_7_CYCLES_PREVIEW_PASS" if mode=="preview" else
      "DAYTONA_V8_7_MATCHED_RENDER_PASS",json.dumps(data),flush=True)
