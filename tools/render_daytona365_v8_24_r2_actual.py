#!/usr/bin/env python3
"""v8.24-r2 genuine Cycles low-load original-camera preview."""
import bpy,hashlib,json,os
from pathlib import Path
W=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v824_ai2_1226"))/"blender_v8"
m=json.loads((W/"DAYTONA_V8_24_R2_BUILD_MANIFEST.json").read_text())
assert Path(bpy.data.filepath).resolve()==(W/m["output"]).resolve()
assert hashlib.sha256((W/m["output"]).read_bytes()).hexdigest()==m["output_sha256"]
sc=bpy.context.scene
assert sc.camera.name=="V7_Camera_Reference_ThreeQuarter"
sc.render.engine="CYCLES";sc.cycles.device="CPU";sc.render.threads_mode="FIXED";sc.render.threads=2
sc.render.resolution_x=480;sc.render.resolution_y=320;sc.render.resolution_percentage=100
sc.cycles.samples=4;sc.cycles.use_denoising=True;sc.view_settings.exposure=-.52
sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
out=W/"Daytona365_v8_24_r2_ACTUAL_CYCLES_PREVIEW.png"
assert not out.exists()
sc.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.is_file() and out.stat().st_size>15000
r={"status":"DAYTONA_V8_24_R2_ACTUAL_CYCLES_PASS","input_sha256":m["output_sha256"],
 "blender":bpy.app.version_string,"camera":sc.camera.name,"engine":"CYCLES",
 "resolution":[480,320],"samples":4,"cpu_threads":2,"denoise":True,"exposure":-.52,
 "preview":out.name,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "bytes":out.stat().st_size,"validation":"PREVIEW_ONLY",
 "full_resolution_sample_matched_PMT":"UNTESTED","original_game_OVC_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_24_R2_RENDER_PROVENANCE.json").write_text(json.dumps(r,indent=2))
print("DAYTONA_V8_24_R2_ACTUAL_CYCLES_PASS",json.dumps(r),flush=True)