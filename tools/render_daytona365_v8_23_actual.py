#!/usr/bin/env python3
"""Actual Cycles reference-camera v8.23 preview, 480x320 4 spp 2 CPU."""
import bpy,json,hashlib,os
from pathlib import Path
W=Path(os.environ["DAYTONA365_WORKDIR"])/"blender_v8"
m=json.loads((W/"DAYTONA_V8_23_BUILD_MANIFEST.json").read_text())
assert Path(bpy.data.filepath).resolve()==(W/m["output"]).resolve()
assert hashlib.sha256((W/m["output"]).read_bytes()).hexdigest()==m["output_sha256"]
sc=bpy.context.scene
assert sc.camera.name=="V7_Camera_Reference_ThreeQuarter"
sc.render.engine="CYCLES";sc.cycles.device="CPU"
sc.render.threads_mode="FIXED";sc.render.threads=2
sc.render.resolution_x=480;sc.render.resolution_y=320
sc.render.resolution_percentage=100
sc.cycles.samples=4;sc.cycles.use_denoising=True
sc.view_settings.exposure=-.52
sc.render.image_settings.file_format="PNG"
sc.render.image_settings.color_mode="RGBA"
out=W/"Daytona365_v8_23_ACTUAL_CYCLES_PREVIEW.png"
assert not out.exists(),str(out)
sc.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.exists() and out.stat().st_size>15000
result={"status":"DAYTONA_V8_23_ACTUAL_CYCLES_PASS",
 "scene_sha256":m["output_sha256"],"blender":bpy.app.version_string,
 "camera":sc.camera.name,"engine":"CYCLES","resolution":[480,320],
 "samples":4,"threads":2,"denoised":True,"exposure":-.52,
 "preview":out.name,"preview_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "bytes":out.stat().st_size,"render_validation":"PREVIEW_ONLY",
 "original_full_sample_matched":"UNTESTED","OVC_game_Quest3":"UNTESTED"}
(W/"DAYTONA_V8_23_RENDER_PROVENANCE.json").write_text(json.dumps(result,indent=2))
print("DAYTONA_V8_23_ACTUAL_CYCLES_PASS",json.dumps(result),flush=True)