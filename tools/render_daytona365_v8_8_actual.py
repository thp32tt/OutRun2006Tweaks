#!/usr/bin/env python3
"""Real Cycles preview v8.8 with 2 CPU threads; full-res only on explicitly approved host."""
import bpy,hashlib,json,os
from pathlib import Path
root=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
w=root/"blender_v8"
model=w/"Daytona365_Cockpit_Blender_PBR_v8_8.blend"
build=json.loads((w/"DAYTONA_V8_8_BUILD_MANIFEST.json").read_text())
assert Path(bpy.data.filepath).resolve()==model.resolve()
assert hashlib.sha256(model.read_bytes()).hexdigest()==build["new_sha256"]
profile=os.environ.get("DAYTONA365_RENDER_PROFILE","preview")
assert profile in ("preview","matched")
s=bpy.context.scene
assert s.camera.name=="V7_Camera_Reference_ThreeQuarter"
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
    s.render.resolution_x=480
    s.render.resolution_y=320
    s.cycles.samples=4
    out=w/"Daytona365_v8_8_ACTUAL_CYCLES_PREVIEW.png"
else:
    assert os.environ.get("DAYTONA365_APPROVED_HEAVY_RENDER_HOST")=="1"
    s.render.resolution_x=960
    s.render.resolution_y=640
    s.cycles.samples=10
    out=w/"Daytona365_v8_8_ACTUAL_CYCLES_MATCHED.png"
assert not out.exists(), "No evidence overwrite"
s.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.is_file() and out.stat().st_size>15000
report={"status":"ACTUAL_BLENDER_CYCLES_RENDERED",
 "profile":profile,"blend_sha256":build["new_sha256"],
 "blender":bpy.app.version_string,"engine":s.render.engine,"device":s.cycles.device,
 "camera":s.camera.name,"width":s.render.resolution_x,"height":s.render.resolution_y,
 "samples":s.cycles.samples,"threads":s.render.threads,"denoising":True,
 "exposure":s.view_settings.exposure,"file":out.name,
 "bytes":out.stat().st_size,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "render_validation":"PREVIEW_ONLY" if profile=="preview" else "MATCHED_SAME_CAMERA",
 "game_runtime":"UNTESTED"}
(w/("DAYTONA_V8_8_"+profile.upper()+"_RENDER_PROVENANCE.json")).write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_8_ACTUAL_PREVIEW_RENDER_PASS" if profile=="preview" else "DAYTONA_V8_8_MATCHED_RENDER_PASS",
 json.dumps(report),flush=True)