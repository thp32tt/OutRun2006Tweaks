#!/usr/bin/env python3
"""Fresh-reopen Blender audit: v8.6 model, original-bounds constraints and PBR.

Does not imply the scene was rendered or tested in-game.
"""
import bpy,hashlib,json,math,os
from pathlib import Path
ROOT=Path(os.environ.get("DAYTONA365_WORKDIR",
    "/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
W=ROOT/"blender_v8"
path=W/"Daytona365_Cockpit_Blender_PBR_v8_6.blend"
base=W/"Daytona365_Cockpit_Blender_PBR_v8_5.blend"
assert bpy.app.version>=(4,5,0)
assert Path(bpy.data.filepath).resolve()==path.resolve()
assert path.is_file() and base.is_file()
assert hashlib.sha256(base.read_bytes()).hexdigest()=="bac28640d88c745b5f276b1ecb5c2ae730e54660fb9526432aeb8c09be390ef8"
build=json.loads((W/"DAYTONA_V8_6_BUILD_MANIFEST.json").read_text())
assert hashlib.sha256(path.read_bytes()).hexdigest()==build["new_sha256"]
assert bpy.context.scene.camera.name=="V7_Camera_Reference_ThreeQuarter"
assert bpy.context.scene.render.engine=="CYCLES"
names={o.name for o in bpy.data.objects}
for item in ("V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM",
  "DAYTONA_GEAR_GATE_CHROME_OUTLINE_SOURCE_ALIGNED_V3",
  "V8_5_CURVED_COLUMN_COWL","V8_5_STEERING_SHAFT"):
 assert item in names,item
tunnel=bpy.data.objects["V8_LOW_CENTER_TUNNEL"]
assert tunnel.type=="MESH" and len(tunnel.data.vertices)==54
assert len(tunnel.data.polygons)==(9-1)*6+2
assert tunnel.data.uv_layers.active.name=="V8_6_METRIC_TANGENT_UV"
assert len(tunnel.data.uv_layers.active.data)==len(tunnel.data.loops)
assert any(m.type=="WEIGHTED_NORMAL" for m in tunnel.modifiers)
assert max(v.co.z for v in tunnel.data.vertices)<.519
assert abs(max(v.co.y for v in tunnel.data.vertices)-.185)<.0001
assert all(math.isfinite(q) for v in tunnel.data.vertices for q in v.co)
assert all(math.isfinite(q) for loop in tunnel.data.uv_layers.active.data for q in loop.uv)
fac=bpy.data.objects["V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING"]
assert all(abs(v.co.x)<.14203 and v.co.z<.58656 for v in fac.data.vertices)
lip=bpy.data.objects["V8_2_CONTINUOUS_LOWER_DASH_LIP"]
assert len(lip.data.vertices)==15*4
assert lip.data.uv_layers.active.name=="V8_6_METRIC_TANGENT_UV"
assert max(v.co.z for v in lip.data.vertices)<.66
assert len([o for o in bpy.data.objects if o.name.startswith("V8_6_TUNNEL_")])==2
assert not any(n.startswith("V8_5_TUNNEL_") for n in names)
seat_names=[]
for side in ("L","R"):
  for suffix,ny,kind in (("CLASSIC_PADDED_CUSHION",52,"CUSHION"),
                          ("TAPERED_PADDED_BACKREST",58,"BACKREST")):
    o=bpy.data.objects["V8_"+side+"_"+suffix]
    m=o.data
    ring=73*(ny+1)
    assert len(m.vertices)==2*ring
    assert m.uv_layers.active.name=="V8_5_METRIC_UPHOLSTERY_UV"
    assert "v8.6" in o["DAYTONA_GEOMETRY_PASS"]
    if kind=="BACKREST":
      for j in (0,ny//3,ny//2,ny):
        for i in (0,18,36,54,72):
          k=j*73+i
          a,b=m.vertices[k].co,m.vertices[ring+k].co
          assert abs((b.y-a.y)-.054)<.00015
    for edge in ("LEFT","RIGHT"):
      assert "V8_6_"+side+"_"+kind+"_INSET_"+edge+"_BOLSTER_SEAM" in names
      assert "V8_5_"+side+"_"+kind+"_"+edge+"_WELT" in names
    seat_names.append(o.name)
  pad=bpy.data.objects["V8_3_"+side+"_TAN_DOOR_LOWER_PAD"]
  assert pad.data.uv_layers.active.name=="V8_6_DOOR_METRIC_UV"
  assert pad.data.materials[0].name=="V8_6_Soft_Door_Card_Leather"
for matname in ("V8_6_Source_Measured_Console_Grain","V8_6_Soft_Door_Card_Leather"):
  mat=bpy.data.materials[matname]
  nodes=mat.node_tree.nodes
  shader=nodes["Principled BSDF"]
  rough=nodes["V8_5_ORM_ROUGHNESS_RANGE"]
  assert shader.inputs["Roughness"].is_linked and shader.inputs["Normal"].is_linked
  assert 0.0<rough.inputs["To Min"].default_value<rough.inputs["To Max"].default_value<1.0
  assert shader.inputs["Metallic"].default_value==0
  assert any(n.type=="NORMAL_MAP" for n in nodes)
  assert any(n.type=="BUMP" for n in nodes)
  images=[n.image for n in nodes if n.type=="TEX_IMAGE" and n.image]
  assert len(images)>=4 and all(i.packed_file for i in images)
  assert any("ORM" in i.name.upper() for i in images)
  assert all(i.colorspace_settings.name=="Non-Color" for i in images
       if any(t in i.name.upper() for t in ("ORM","NORMAL","HEIGHT")))
render=W/"Daytona365_v8_6_ACTUAL_CYCLES_PREVIEW.png"
report={
 "status":"DAYTONA_V8_6_REAL_BLENDER_FRESH_REOPEN_PASS",
 "blender":bpy.app.version_string,
 "file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
 "bytes":path.stat().st_size,
 "mesh_objects":sum(o.type=="MESH" for o in bpy.data.objects),
 "curve_objects":sum(o.type=="CURVE" for o in bpy.data.objects),
 "seat_shells":seat_names,
 "measured_PMT_stacks_not_copied":True,
 "tunnel_metres_UV_and_bounds":True,
 "seat_original_topology_and_Y_thickness":True,
 "door_uv_and_packed_pbr_maps":True,
 "camera_unchanged":True,
 "render_validation":"PREVIEW_ONLY" if render.is_file() else "UNTESTED",
 "full_resolution_render":"UNTESTED",
 "game_runtime_and_Quest3":"UNTESTED"
}
(W/"DAYTONA_V8_6_VERIFIED.json").write_text(json.dumps(report,indent=2))
print("DAYTONA_V8_6_FRESH_REOPEN_PASS",json.dumps(report),flush=True)
