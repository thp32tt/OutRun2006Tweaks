import bpy,sys,time,json,os
from pathlib import Path
root=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender_v6")
scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=10
scene.cycles.use_denoising=True
scene.render.resolution_x=700
scene.render.resolution_y=480
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.threads_mode="FIXED"
scene.render.threads=2
rendered=[]
for name,camera_name in [("Daytona365_BLENDER_v6_CABIN.png","V6_Camera_Cabin_ThreeQuarter"),
                          ("Daytona365_BLENDER_v6_DRIVER.png","V6_Camera_Driver_ActualCockpit")]:
 scene.camera=bpy.data.objects[camera_name]
 scene.render.filepath=str(root/name)
 t=time.monotonic()
 try:
  bpy.ops.render.render(write_still=True)
 except Exception as e:
  print("RENDER_FAIL",name,repr(e),flush=True)
  raise
 rendered.append({"file":name,"seconds":round(time.monotonic()-t,2),
   "size":(root/name).stat().st_size})
 print("RENDER_PASS",json.dumps(rendered[-1]),flush=True)
(root/"BLENDER_V6_RENDER_REPORT.json").write_text(json.dumps(rendered,indent=2))