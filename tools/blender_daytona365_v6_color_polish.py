import bpy,os,json,hashlib
from pathlib import Path
r=Path("/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender_v6")
for n,power in {"V6_Studio_Key":145,"V6_Studio_Fill":100,"V6_Studio_Rim":80}.items():
 bpy.data.objects[n].data.energy=power
bpy.context.scene.world.node_tree.nodes["Background"].inputs["Color"].default_value=(.20,.23,.27,1)
bpy.context.scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.45
scene=bpy.context.scene
scene.view_settings.view_transform="AgX"
scene.view_settings.look="AgX - Medium High Contrast"
scene.view_settings.view_settings if False else None
scene.view_settings.exposure=-.2
scene.view_settings.gamma=1.
for m in bpy.data.materials:
 if not m.use_nodes:continue
 shader=next((n for n in m.node_tree.nodes if n.type=="BSDF_PRINCIPLED"),None)
 if shader is None:continue
 if m.name in ("TanLeather","BlackDashLeather","BlackPiping"):
  shader.inputs["Sheen Weight"].default_value=.16 if m.name=="TanLeather" else .08
  shader.inputs["Coat Weight"].default_value=.03
 if m.name=="Chrome":
  shader.inputs["Coat Weight"].default_value=.25
path=r/"Daytona365_Cockpit_Blender_PBR_v6.blend"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
print(json.dumps({"saved":str(path),"size":path.stat().st_size,
 "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
 "meshes":len([o for o in bpy.data.objects if o.type=="MESH"]),
 "curves":len([o for o in bpy.data.objects if o.type=="CURVE"])}))