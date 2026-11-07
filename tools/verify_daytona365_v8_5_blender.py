#!/usr/bin/env python3
"""Fresh-reopen, real Blender verification of private Daytona v8.5 .blend.

Usage: blender -b Daytona365_Cockpit_Blender_PBR_v8_5.blend -t 2
               --python tools/verify_daytona365_v8_5_blender.py
Does NOT run a render; no GPU/game/Quest claims.
"""
import bpy,hashlib,json,math,os
from pathlib import Path

root=Path(os.environ.get("DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
out=root/"blender_v8"
expected=out/"Daytona365_Cockpit_Blender_PBR_v8_5.blend"
base=out/"Daytona365_Cockpit_Blender_PBR_v8_4.blend"
assert Path(bpy.data.filepath).resolve()==expected.resolve()
assert expected.is_file() and base.is_file()
assert hashlib.sha256(base.read_bytes()).hexdigest()=="97ff8618a4a16ac837e90e8aa9dd4434f41172c0b54c6894ec680aefa93025d4"
assert bpy.app.version>=(4,5,0)
names={o.name for o in bpy.data.objects}
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert "V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM" in names
assert "V8_5_CURVED_COLUMN_COWL" in names and "V8_5_STEERING_SHAFT" in names
assert "V8_4_SLIM_STEERING_COWL" not in names
assert "V8_4_STEERING_SHAFT" not in names
assert "V8_1_COMPACT_SHIFTER_LEATHER_DECK" in names
assert "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3" in names
assert len([o for o in bpy.data.objects if o.name.startswith("V8_5_TUNNEL_")])==2
tunnel=bpy.data.objects["V8_LOW_CENTER_TUNNEL"]
assert tunnel.type=="MESH" and len(tunnel.data.vertices)==30
assert any(m.type=="WEIGHTED_NORMAL" for m in tunnel.modifiers)
assert all(math.isfinite(p) for v in tunnel.data.vertices for p in v.co)
shells=[]
for side in ("L","R"):
 for kind,ny in (("CLASSIC_PADDED_CUSHION",52),("TAPERED_PADDED_BACKREST",58)):
  o=bpy.data.objects[f"V8_{side}_{kind}"]
  me=o.data
  ring=73*(ny+1)
  assert len(me.vertices)==2*ring
  uv=me.uv_layers.active
  assert uv and uv.name=="V8_5_METRIC_UPHOLSTERY_UV"
  assert len(uv.data)==len(me.loops)
  assert all(math.isfinite(x) for item in uv.data for x in item.uv)
  assert o.get("DAYTONA_GEOMETRY_PASS")
  if "BACKREST" in kind:
   # Back-of-seat is now behind the visible front in Y, not beneath it in Z.
   for j in (0,ny//4,ny//2,ny):
    for i in (0,12,36,60,72):
     vi=j*73+i
     front=me.vertices[vi].co
     rear=me.vertices[ring+vi].co
     assert abs((rear.y-front.y)-.054)<.0001
     assert abs((rear.z-front.z)+.004)<.0001
  shells.append(o.name)
for name in ("V7_Target_Tan_Leather_PBR","V7_Target_Black_Dashboard_PBR",
             "V7_Target_Walnut_Steering_Rim_PBR"):
 m=bpy.data.materials[name]
 nodes=m.node_tree.nodes
 shader=nodes["Principled BSDF"]
 assert shader.inputs["Normal"].is_linked
 assert shader.inputs["Roughness"].is_linked
 assert nodes.get("V8_5_ORM_ROUGHNESS_RANGE")
 assert any(n.type=="NORMAL_MAP" for n in nodes)
 assert any(n.type=="BUMP" for n in nodes)
 images=[n.image for n in nodes if n.type=="TEX_IMAGE" and n.image]
 assert len(images)>=4 and all(i.packed_file for i in images)
 for i in images:
  if any(v in i.name for v in ("_Normal","_ORM","_HeightOffline")):
   assert i.colorspace_settings.name=="Non-Color"
assert bpy.data.materials["V7_Machined_Aluminum"].node_tree.nodes.get("V8_BrushedMetalNormal")
rendered=out/"Daytona365_v8_5_ACTUAL_CYCLES_PREVIEW.png"
report={
 "status":"DAYTONA_V8_5_REAL_BLENDER_FRESH_REOPEN_PASS",
 "blender":bpy.app.version_string,
 "file":expected.name,
 "sha256":hashlib.sha256(expected.read_bytes()).hexdigest(),
 "bytes":expected.stat().st_size,
 "mesh_objects":sum(o.type=="MESH" for o in bpy.data.objects),
 "curve_objects":sum(o.type=="CURVE" for o in bpy.data.objects),
 "seat_shells_checked":shells,
 "backrest_thickness_y_corrected":True,
 "metric_uv_connected":True,
 "packed_pbr_normal_orm_height":True,
 "new_steering_cowl":True,
 "tapered_tunnel":True,
 "original_game_and_Quest3_tested":False,
 "render_validation":"LOWRES_CYCLES_PREVIEW_ONLY" if rendered.is_file() else "UNTESTED",
 "full_resolution_cycles_validation":"UNTESTED",
 "game_runtime_conversion":False,
}
(out/"DAYTONA_V8_5_VERIFIED.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("DAYTONA_V8_5_REAL_BLENDER_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
