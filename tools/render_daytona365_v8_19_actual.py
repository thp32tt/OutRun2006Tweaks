#!/usr/bin/env python3
"""Real Cycles v8.19 preview only; full same-sample rendering requires explicit approval."""
import bpy,hashlib,json,os
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR",
 "/home/chatgpt-runner/work_handoff/daytona365_v819_ai2_093x"))/"blender_v8"
m=json.loads((W/"DAYTONA_V8_19_R2_BUILD_MANIFEST.json").read_text())
assert Path(bpy.data.filepath).resolve()==(W/m["output"]).resolve()
assert hashlib.sha256((W/m["output"]).read_bytes()).hexdigest()==m["output_sha256"]
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
profile=os.environ.get("DAYTONA365_RENDER_PROFILE","preview")
assert profile in ("preview","matched")
if profile=="matched":assert os.environ.get("DAYTONA365_APPROVED_HEAVY_RENDER_HOST")=="1"
scene.render.engine="CYCLES"
scene.cycles.device="CPU";scene.cycles.use_denoising=True
scene.render.threads_mode="FIXED";scene.render.threads=2
scene.render.resolution_percentage=100
scene.view_settings.exposure=-.52
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
if profile=="preview":
 scene.render.resolution_x=480;scene.render.resolution_y=320;scene.cycles.samples=4
else:
 scene.render.resolution_x=960;scene.render.resolution_y=640;scene.cycles.samples=10
out=W/("Daytona365_v8_19_r2_ACTUAL_CYCLES_PREVIEW.png" if profile=="preview"
 else "Daytona365_v8_19_r2_ACTUAL_CYCLES_MATCHED.png")
assert not out.exists()
scene.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.exists() and out.stat().st_size>15000
p={"status":"DAYTONA_V8_19_ACTUAL_CYCLES_PASS",
 "blender":bpy.app.version_string,"scene_sha256":m["output_sha256"],
 "camera":scene.camera.name,"engine":"CYCLES","width":scene.render.resolution_x,
 "height":scene.render.resolution_y,"samples":scene.cycles.samples,
 "threads":2,"exposure":scene.view_settings.exposure,"denoising":True,
 "render_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "render_bytes":out.stat().st_size,"render_image":out.name,
 "render_validation":"PREVIEW_ONLY" if profile=="preview" else "MATCHED_RESOLUTION",
 "sample_matched_original":"UNTESTED" if profile=="preview" else "UNTESTED_ORIGINAL_RENDER",
 "OVC_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_19_RENDER_PROVENANCE.json").write_text(json.dumps(p,indent=2))
print("DAYTONA_V8_19_ACTUAL_CYCLES_PASS",json.dumps(p),flush=True)