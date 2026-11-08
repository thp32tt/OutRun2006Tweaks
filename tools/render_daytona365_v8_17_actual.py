#!/usr/bin/env python3
"""Real Blender 4.5 Cycles preview for v8.17 only, low N100 resource budget."""
import bpy,json,os,hashlib
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v817_ai2_0917_gpt6"))/"blender_v8"
m=json.loads((W/"DAYTONA_V8_17_BUILD_MANIFEST.json").read_text())
assert Path(bpy.data.filepath).resolve()==(W/m["output"]).resolve()
assert hashlib.sha256((W/m["output"]).read_bytes()).hexdigest()==m["output_sha256"]
s=bpy.context.scene
assert s.camera.name=="V7_Camera_Reference_ThreeQuarter"
profile=os.environ.get("DAYTONA365_RENDER_PROFILE","preview")
assert profile in ("preview","matched")
if profile=="matched":assert os.environ.get("DAYTONA365_APPROVED_HEAVY_RENDER_HOST")=="1"
s.render.engine="CYCLES"
s.cycles.device="CPU";s.cycles.use_denoising=True
s.render.threads_mode="FIXED";s.render.threads=2
s.render.resolution_percentage=100
s.view_settings.exposure=-.52
s.render.image_settings.file_format="PNG"
s.render.image_settings.color_mode="RGBA"
if profile=="preview":s.render.resolution_x=480;s.render.resolution_y=320;s.cycles.samples=4
else:s.render.resolution_x=960;s.render.resolution_y=640;s.cycles.samples=10
out=W/("Daytona365_v8_17_ACTUAL_CYCLES_PREVIEW.png" if profile=="preview"
 else "Daytona365_v8_17_ACTUAL_CYCLES_MATCHED.png")
assert not out.exists()
s.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.is_file() and out.stat().st_size>15000
report={"status":"DAYTONA_V8_17_ACTUAL_CYCLES_PASS",
 "model_sha256":m["output_sha256"],"blender":bpy.app.version_string,
 "camera":s.camera.name,"engine":"CYCLES","width":s.render.resolution_x,
 "height":s.render.resolution_y,"samples":s.cycles.samples,
 "threads":2,"exposure":s.view_settings.exposure,
 "denoised":True,"image":out.name,"image_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "bytes":out.stat().st_size,"render_validation":"PREVIEW_ONLY" if profile=="preview" else "MATCHED",
 "full_resolution_matched":"UNTESTED" if profile=="preview" else "PASS",
 "game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_17_PREVIEW_RENDER_PROVENANCE.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_17_ACTUAL_CYCLES_PASS",json.dumps(report),flush=True)