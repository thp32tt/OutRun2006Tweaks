#!/usr/bin/env python3
"""Real Cycles preview of saved v8.11, low-N100-cost 480x320 4 spp only."""
import bpy,json,hashlib,os
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
scene=W/"Daytona365_Cockpit_Blender_PBR_v8_11.blend"
manifest=json.loads((W/"DAYTONA_V8_11_BUILD_MANIFEST.json").read_text())
assert Path(bpy.data.filepath).resolve()==scene.resolve()
assert hashlib.sha256(scene.read_bytes()).hexdigest()==manifest["new_sha256"]
profile=os.environ.get("DAYTONA365_RENDER_PROFILE","preview")
assert profile in ("preview","matched")
sc=bpy.context.scene
assert sc.camera.name=="V7_Camera_Reference_ThreeQuarter"
sc.render.engine="CYCLES";sc.cycles.device="CPU"
sc.cycles.use_denoising=True
sc.render.threads_mode="FIXED";sc.render.threads=2
sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
sc.view_settings.exposure=-.52
if profile=="preview":
 sc.render.resolution_x=480;sc.render.resolution_y=320;sc.cycles.samples=4
 output=W/"Daytona365_v8_11_ACTUAL_CYCLES_PREVIEW.png"
else:
 assert os.environ.get("DAYTONA365_APPROVED_HEAVY_RENDER_HOST")=="1","No high-load CPU render on N100"
 sc.render.resolution_x=960;sc.render.resolution_y=640;sc.cycles.samples=10
 output=W/"Daytona365_v8_11_ACTUAL_CYCLES_MATCHED.png"
assert not output.exists(),"Immutable image overwrite forbidden"
sc.render.filepath=str(output)
bpy.ops.render.render(write_still=True)
assert output.is_file() and output.stat().st_size>15000
report={"status":"ACTUAL_BLENDER_CYCLES_RENDERED",
 "source_blend_sha256":manifest["new_sha256"],
 "blender":bpy.app.version_string,"engine":sc.render.engine,
 "device":sc.cycles.device,"camera":sc.camera.name,"profile":profile,
 "width":sc.render.resolution_x,"height":sc.render.resolution_y,
 "samples":sc.cycles.samples,"threads":sc.render.threads,
 "denoising":True,"exposure":sc.view_settings.exposure,
 "image":output.name,"bytes":output.stat().st_size,
 "sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
 "render_validation":"PREVIEW_ONLY" if profile=="preview" else "MATCHED_SAME_CAMERA",
 "game_runtime":"UNTESTED"}
(W/("DAYTONA_V8_11_"+profile.upper()+"_RENDER_PROVENANCE.json")).write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_11_ACTUAL_CYCLES_PREVIEW_PASS" if profile=="preview" else "DAYTONA_V8_11_MATCHED_CYCLES_PASS",json.dumps(report),flush=True)