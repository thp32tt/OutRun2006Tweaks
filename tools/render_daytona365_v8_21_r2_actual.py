#!/usr/bin/env python3
"""Real Blender Cycles v8.21 preview; same source camera, not full PMT parity."""
import bpy,hashlib,json,os
from pathlib import Path
W=Path(os.environ["DAYTONA365_WORKDIR"])/"blender_v8"
m=json.loads((W/"DAYTONA_V8_21_R2_BUILD_MANIFEST.json").read_text())
assert Path(bpy.data.filepath).resolve()==(W/m["output"]).resolve()
assert hashlib.sha256((W/m["output"]).read_bytes()).hexdigest()==m["output_sha256"]
scene=bpy.context.scene
assert scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert os.environ.get("DAYTONA365_RENDER_PROFILE","preview")=="preview"
scene.render.engine="CYCLES";scene.cycles.device="CPU"
scene.render.threads_mode="FIXED";scene.render.threads=2
scene.render.resolution_x=480;scene.render.resolution_y=320
scene.render.resolution_percentage=100
scene.cycles.samples=4;scene.cycles.use_denoising=True
scene.view_settings.exposure=-.52
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
out=W/"Daytona365_v8_21_r2_ACTUAL_CYCLES_PREVIEW.png"
assert not out.exists(),out
scene.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.exists() and out.stat().st_size>15000
r={"status":"DAYTONA_V8_21_R2_ACTUAL_CYCLES_PASS",
 "source_sha256":m["output_sha256"],"blender":bpy.app.version_string,
 "camera":scene.camera.name,"engine":"CYCLES",
 "resolution":[480,320],"samples":4,"threads":2,
 "denoised":True,"exposure":scene.view_settings.exposure,
 "image":out.name,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "bytes":out.stat().st_size,"render_validation":"PREVIEW_ONLY",
 "original_full_sample_matched":"UNTESTED","OVC_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_21_R2_RENDER_PROVENANCE.json").write_text(json.dumps(r,indent=2))
print("DAYTONA_V8_21_R2_ACTUAL_CYCLES_PASS",json.dumps(r),flush=True)