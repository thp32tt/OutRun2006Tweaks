#!/usr/bin/env python3
"""Real Blender Cycles wheel-only geometry diagnostic, NOT factory camera view.

Before/after use identical lights/camera and hide all unrelated meshes; it is
real existing Blender mesh geometry, not a fabricated product image.
"""
import bpy,json,hashlib,math,os
from pathlib import Path
from mathutils import Vector
W=Path(os.environ["DAYTONA365_WORKDIR"])/"blender_v8"
kind=os.environ.get("DAYTONA365_DETAIL_KIND")
assert kind in ("before","after")
source= W/("Daytona365_Cockpit_Blender_PBR_v8_22_r2.blend" if kind=="before" else "Daytona365_Cockpit_Blender_PBR_v8_23.blend")
assert Path(bpy.data.filepath).resolve()==source.resolve()
expect=("30ddcbd01ef7e969bb1e4220ff4318c2f75b7fd7ab70bc4d6dafedcdc7954437"
 if kind=="before" else "58c6404ec595392ab73358ec3b61aea3d971629f87d2d633b73918aaffa041bd")
assert hashlib.sha256(source.read_bytes()).hexdigest()==expect
include={
 "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
 "V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE",
 "V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE",
 "V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE",
 "V7_SHORT_SHAFT_AT_WHEEL_HUB"}
for ob in bpy.data.objects:
 if ob.type in ("MESH","CURVE"):
  ob.hide_render=not(ob.name.startswith("V5_ORIGINAL_THREESPOKE_WHEEL_") or ob.name in include)
cam_data=bpy.data.cameras.new("V823_TEMPORARY_STUDIO_DETAIL_CAMERA")
cam=bpy.data.objects.new("V823_TEMPORARY_STUDIO_DETAIL_CAMERA",cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location=(-.35,-.88,.792)
target=Vector((-.35,-.285,.792))
cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
cam_data.type="PERSP";cam_data.lens=51
cam_data.clip_start=.01
bpy.context.scene.camera=cam
light=bpy.data.lights.new("V823_TEMPORARY_STUDIO_SOFTBOX","AREA")
light.energy=215;light.shape="RECTANGLE";light.size=1.15;light.size_y=.8
lobj=bpy.data.objects.new("V823_TEMPORARY_STUDIO_SOFTBOX",light)
bpy.context.scene.collection.objects.link(lobj)
lobj.location=(-.53,-.70,1.25)
lobj.rotation_euler=(target-lobj.location).to_track_quat("-Z","Y").to_euler()
sc=bpy.context.scene
sc.render.engine="CYCLES";sc.cycles.device="CPU"
sc.render.threads_mode="FIXED";sc.render.threads=2
sc.render.resolution_x=480;sc.render.resolution_y=320
sc.render.resolution_percentage=100
sc.cycles.samples=4;sc.cycles.use_denoising=True
sc.view_settings.exposure=-.52
sc.render.image_settings.file_format="PNG"
sc.render.image_settings.color_mode="RGBA"
out=W/("Daytona365_"+("v8_22_r2" if kind=="before" else "v8_23")+"_SPOKE_ISOLATED_ACTUAL_CYCLES.png")
assert not out.exists(),out
sc.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
assert out.exists() and out.stat().st_size>12000
report={"status":"DAYTONA_V8_23_REAL_ISOLATED_DETAIL_CYCLES_PASS",
 "kind":kind,"input":source.name,"input_sha256":expect,
 "render":out.name,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "bytes":out.stat().st_size,
 "camera":"TEMPORARY_STUDIO_WHEEL_DETAIL_NOT_ORIGINAL_CAMERA",
 "camera_loc":list(cam.location),"camera_target":list(target),
 "geometry": "actual original-model wheel and v7.3 bridges, isolated",
 "render_engine":"CYCLES","resolution":[480,320],"samples":4,"cpu_threads":2,
 "reference_PMT_photometric_equivalent":False,
 "game_runtime_Quest3":"UNTESTED"}
(W/("DAYTONA_V8_23_DETAIL_"+kind.upper()+"_PROVENANCE.json")).write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_23_REAL_ISOLATED_DETAIL_CYCLES_PASS",json.dumps(report),flush=True)