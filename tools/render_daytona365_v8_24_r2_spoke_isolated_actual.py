#!/usr/bin/env python3
"""True wheel-only official Blender Cycles v8.24-r2 study: same temp camera as saved v8.23."""
import bpy,json,hashlib,math,os
from pathlib import Path
from mathutils import Vector
W=Path(os.environ.get("DAYTONA365_WORKDIR","/home/chatgpt-runner/work_handoff/daytona365_v824_ai2_1226"))/"blender_v8"
manifest=json.loads((W/"DAYTONA_V8_24_R2_BUILD_MANIFEST.json").read_text())
p=W/manifest["output"]
assert Path(bpy.data.filepath).resolve()==p.resolve()
assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest["output_sha256"]
include={"V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
 "V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
 "V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE",
 "V7_SHORT_SHAFT_AT_WHEEL_HUB"}
for ob in bpy.data.objects:
 if ob.type in ("MESH","CURVE"):
  ob.hide_render=not(ob.name.startswith("V5_ORIGINAL_THREESPOKE_WHEEL_") or ob.name in include)
cam_data=bpy.data.cameras.new("V824_TEMPORARY_STUDIO_DETAIL_CAMERA")
cam=bpy.data.objects.new("V824_TEMPORARY_STUDIO_DETAIL_CAMERA",cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location=(-.35,-.88,.792)
target=Vector((-.35,-.285,.792))
cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
cam_data.type="PERSP";cam_data.lens=51;cam_data.clip_start=.01
bpy.context.scene.camera=cam
light=bpy.data.lights.new("V824_TEMPORARY_STUDIO_SOFTBOX","AREA")
light.energy=215;light.shape="RECTANGLE";light.size=1.15;light.size_y=.8
lobj=bpy.data.objects.new("V824_TEMPORARY_STUDIO_SOFTBOX",light)
bpy.context.scene.collection.objects.link(lobj)
lobj.location=(-.53,-.70,1.25)
lobj.rotation_euler=(target-lobj.location).to_track_quat("-Z","Y").to_euler()
sc=bpy.context.scene
sc.render.engine="CYCLES";sc.cycles.device="CPU"
sc.render.threads_mode="FIXED";sc.render.threads=2
sc.render.resolution_x=480;sc.render.resolution_y=320;sc.render.resolution_percentage=100
sc.cycles.samples=4;sc.cycles.use_denoising=True
sc.view_settings.exposure=-.52
sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGBA"
out=W/"Daytona365_v8_24_r2_SPOKE_ISOLATED_ACTUAL_CYCLES.png"
assert not out.exists()
sc.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.is_file() and out.stat().st_size>12000
r={"status":"DAYTONA_V8_24_R2_ISOLATED_CYCLES_PASS",
 "input":p.name,"source_sha256":manifest["output_sha256"],
 "render":out.name,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"bytes":out.stat().st_size,
 "camera":"TEMPORARY_STUDIO_WHEEL_DETAIL_NOT_ORIGINAL_CAMERA",
 "camera_location":list(cam.location),"camera_target":list(target),
 "actual_native_and_helper_wheel_only":True,"engine":"CYCLES","resolution":[480,320],
 "samples":4,"cpu_threads":2,"full_reference_matched":"UNTESTED","Quest3":"UNTESTED"}
(W/"DAYTONA_V8_24_R2_STUDIO_RENDER_PROVENANCE.json").write_text(json.dumps(r,indent=2))
print("DAYTONA_V8_24_R2_ISOLATED_CYCLES_PASS",json.dumps(r),flush=True)